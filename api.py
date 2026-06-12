from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

from app import db as db_state
from app.config import get_settings
from app.db import clear_all_conversation_history, get_db_session, init_db
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationHistoryResponse,
    ConversationTurnOut,
    HealthResponse,
    SimulatedWellnessSignal,
)
from app.services.llm import LLMService, LLMServiceError
from app.services.memory import MemoryService
from app.services.orchestrator import AssistantOrchestrator
from app.services.rag import DEFAULT_PERSONA, list_personas

settings = get_settings()
llm_service = LLMService(settings)
orchestrator = AssistantOrchestrator(settings=settings, llm_service=llm_service)
memory_service = MemoryService()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    await clear_all_conversation_history()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    static_dir = Path("app/static")
    generated_audio_dir = Path(settings.audio_output_dir)
    generated_audio_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    app.mount(
        "/generated_audio",
        StaticFiles(directory=generated_audio_dir),
        name="generated_audio",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(_, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "error": type(exc).__name__,
                "message": str(exc),
            },
        )

    @app.exception_handler(LLMServiceError)
    async def llm_service_exception_handler(_, exc: LLMServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "error": type(exc).__name__,
                "message": str(exc),
                "provider": settings.llm_provider,
            },
        )

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "message": "Jarvis assistant starter is running.",
        }

    @app.get("/ui", include_in_schema=False)
    async def ui() -> FileResponse:
        return FileResponse(static_dir / "index.html")

    @app.get("/health", response_model=HealthResponse, tags=["meta"])
    async def health() -> HealthResponse:
        providers = {
            "llm": llm_service.provider_status,
            "stt": orchestrator.stt_provider_status,
            "emotion": orchestrator.emotion_provider_status,
            "tts": orchestrator.tts_service.provider_status,
            "database": db_state.active_database_url.split("://", maxsplit=1)[0],
        }
        return HealthResponse(
            status="ok",
            app_name=settings.app_name,
            environment=settings.environment,
            providers=providers,
        )

    @app.post(f"{settings.api_prefix}/chat", response_model=ChatResponse, tags=["chat"])
    async def chat(
        payload: ChatRequest,
        db: AsyncSession = Depends(get_db_session),
    ) -> ChatResponse:
        return await orchestrator.handle_chat(
            db=db,
            session_id=payload.session_id,
            message=payload.message,
            persona_id=payload.persona_id,
            wellness_signal=payload.wellness_signal,
        )

    @app.get(f"{settings.api_prefix}/personas", tags=["chat"])
    async def personas() -> list[dict]:
        return list_personas()

    @app.get(
        f"{settings.api_prefix}/history/{{session_id}}",
        response_model=ConversationHistoryResponse,
        tags=["chat"],
    )
    async def history(
        session_id: str,
        db: AsyncSession = Depends(get_db_session),
    ) -> ConversationHistoryResponse:
        turns = await memory_service.get_recent_turns(
            db,
            session_id=session_id,
            limit=12,
        )
        return ConversationHistoryResponse(
            session_id=session_id,
            turns=[
                ConversationTurnOut(
                    role=turn.role,
                    content=turn.content,
                    emotion=turn.emotion,
                    created_at=turn.created_at,
                )
                for turn in turns
            ],
        )

    @app.delete(f"{settings.api_prefix}/history/{{session_id}}", tags=["chat"])
    async def clear_history(
        session_id: str,
        db: AsyncSession = Depends(get_db_session),
    ) -> dict[str, int | str]:
        deleted_turns = await memory_service.clear_session(db, session_id=session_id)
        return {
            "session_id": session_id,
            "deleted_turns": deleted_turns,
            "status": "cleared",
        }

    @app.post(f"{settings.api_prefix}/voice", response_model=ChatResponse, tags=["voice"])
    async def voice(
        session_id: str = Form(...),
        persona_id: str | None = Form(default=DEFAULT_PERSONA),
        transcript_override: str | None = Form(default=None),
        wellness_heart_rate: int | None = Form(default=None),
        wellness_stress_level: str | None = Form(default=None),
        audio: UploadFile = File(...),
        db: AsyncSession = Depends(get_db_session),
    ) -> ChatResponse:
        uploads_dir = Path(settings.upload_dir)
        uploads_dir.mkdir(parents=True, exist_ok=True)
        target = uploads_dir / f"{uuid4()}-{audio.filename}"
        target.write_bytes(await audio.read())
        wellness_signal = None
        if wellness_heart_rate is not None or wellness_stress_level:
            wellness_signal = SimulatedWellnessSignal(
                heart_rate=wellness_heart_rate,
                stress_level=wellness_stress_level,
            )

        return await orchestrator.handle_voice(
            db=db,
            session_id=session_id,
            audio_path=target,
            persona_id=persona_id,
            transcript_override=transcript_override,
            wellness_signal=wellness_signal,
        )

    @app.websocket("/ws/chat")
    async def websocket_chat(websocket: WebSocket) -> None:
        await websocket.accept()
        try:
            while True:
                incoming = await websocket.receive_text()
                try:
                    reply = await llm_service.generate_response(
                        user_message=incoming,
                        emotion="neutral",
                        conversation_context=[],
                        persona_id=DEFAULT_PERSONA,
                    )
                    await websocket.send_json(
                        {
                            "user_message": incoming,
                            "assistant_message": reply,
                        }
                    )
                except LLMServiceError as exc:
                    await websocket.send_json(
                        {
                            "error": type(exc).__name__,
                            "message": str(exc),
                            "provider": settings.llm_provider,
                        }
                    )
        except WebSocketDisconnect:
            return

    return app
