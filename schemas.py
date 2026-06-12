from datetime import datetime
from pydantic import BaseModel, Field


class SimulatedWellnessSignal(BaseModel):
    heart_rate: int | None = Field(default=None, ge=40, le=180)
    stress_level: str | None = None
    source: str = "manual_demo"


class ChatRequest(BaseModel):
    session_id: str = Field(default="default-session", min_length=1, max_length=100)
    persona_id: str | None = "default_danny"
    message: str = Field(min_length=1)
    wellness_signal: SimulatedWellnessSignal | None = None


class VoiceRequest(BaseModel):
    session_id: str = Field(default="default-session", min_length=1, max_length=100)
    persona_id: str | None = "default_danny"
    transcript_override: str | None = None
    wellness_signal: SimulatedWellnessSignal | None = None


class EmotionDebug(BaseModel):
    final_emotion: str
    audio_emotion: str | None = None
    audio_score: float | None = None
    text_emotion: str | None = None
    text_score: float | None = None
    decision_source: str
    provider: str | None = None
    language: str | None = None
    audio_event: str | None = None
    raw_output: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    persona_id: str = "default_danny"
    user_message: str
    assistant_message: str
    detected_emotion: str
    emotion_debug: EmotionDebug | None = None
    transcript: str | None = None
    audio_path: str | None = None
    wellness_signal: SimulatedWellnessSignal | None = None


class ConversationTurnOut(BaseModel):
    role: str
    content: str
    emotion: str | None = None
    created_at: datetime


class ConversationHistoryResponse(BaseModel):
    session_id: str
    turns: list[ConversationTurnOut] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
    providers: dict[str, str]
