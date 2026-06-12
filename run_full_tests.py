import argparse
import asyncio
import json
import sqlite3
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import httpx
    import websockets
except ImportError as exc:
    missing_name = getattr(exc, "name", "a required package")
    print(f"Missing dependency: {missing_name}")
    print("Install test dependencies with the same interpreter you use to run the script:")
    print("  python3 -m pip install httpx websockets")
    print("Or activate your project venv first and then rerun the script.")
    raise SystemExit(1) from exc


@dataclass
class TestResult:
    name: str
    status: str
    detail: str


class TestRunner:
    def __init__(self, base_url: str, workspace: Path) -> None:
        self.base_url = base_url.rstrip("/")
        self.ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.workspace = workspace
        self.generated_dir = workspace / "generated_audio"
        self.sqlite_db = workspace / "jarvis.db"
        self.results: list[TestResult] = []
        self.health_payload: dict[str, Any] = {}
        self.personas_payload: list[dict[str, Any]] = []
        self.chat_payload: dict[str, Any] = {}
        self.voice_payload: dict[str, Any] = {}
        self.successful_sessions: list[str] = []

    def add_result(self, name: str, status: str, detail: str) -> None:
        self.results.append(TestResult(name=name, status=status, detail=detail))

    async def run(self) -> int:
        async with httpx.AsyncClient(timeout=60.0) as client:
            await self.test_root(client)
            await self.test_health(client)
            await self.test_personas(client)
            await self.test_chat(client)
            await self.test_voice(client)
        await self.test_websocket()
        self.test_generated_output()
        self.test_database()
        self.print_summary()
        return 0 if all(result.status in {"PASS", "SKIP"} for result in self.results) else 1

    async def test_root(self, client: httpx.AsyncClient) -> None:
        name = "Root Endpoint"
        try:
            response = await client.get(f"{self.base_url}/")
            response.raise_for_status()
            payload = response.json()
            if payload.get("message"):
                self.add_result(name, "PASS", payload.get("message", "Root endpoint responded."))
            else:
                self.add_result(name, "FAIL", f"Unexpected payload: {payload}")
        except Exception as exc:
            self.add_result(name, "FAIL", str(exc))

    async def test_personas(self, client: httpx.AsyncClient) -> None:
        name = "Personas Endpoint"
        try:
            response = await client.get(f"{self.base_url}/api/personas")
            if response.status_code >= 400:
                self.add_result(
                    name,
                    "FAIL",
                    await self.response_error_detail(response, "Personas request failed."),
                )
                return

            payload = response.json()
            self.personas_payload = payload
            persona_ids = {
                str(persona.get("persona_id"))
                for persona in payload
                if isinstance(persona, dict)
            }
            if {"default_danny", "priya_shah"}.issubset(persona_ids):
                self.add_result(name, "PASS", f"{len(payload)} persona profiles returned.")
            else:
                self.add_result(name, "FAIL", f"Unexpected persona payload: {payload}")
        except Exception as exc:
            self.add_result(name, "FAIL", str(exc))

    async def test_health(self, client: httpx.AsyncClient) -> None:
        name = "Health Endpoint"
        try:
            response = await client.get(f"{self.base_url}/health")
            response.raise_for_status()
            payload = response.json()
            self.health_payload = payload
            providers = payload.get("providers", {})
            detail = (
                f"status={payload.get('status')} "
                f"database={providers.get('database')} "
                f"llm={providers.get('llm')} "
                f"tts={providers.get('tts')}"
            )
            if payload.get("status") == "ok":
                self.add_result(name, "PASS", detail)
            else:
                self.add_result(name, "FAIL", detail)
        except Exception as exc:
            self.add_result(name, "FAIL", str(exc))

    async def test_chat(self, client: httpx.AsyncClient) -> None:
        name = "Chat Endpoint"
        try:
            payload = {
                "session_id": "test-chat-session",
                "persona_id": "priya_shah",
                "message": "What time is it? Keep your answer short.",
            }
            response = await client.post(f"{self.base_url}/api/chat", json=payload)
            if response.status_code >= 400:
                self.add_result(
                    name,
                    "FAIL",
                    await self.response_error_detail(response, "Chat request failed."),
                )
                return

            body = response.json()
            self.chat_payload = body

            assistant_message = body.get("assistant_message")
            audio_path = body.get("audio_path")
            if assistant_message and audio_path:
                self.successful_sessions.append("test-chat-session")
                self.add_result(
                    name,
                    "PASS",
                    f"assistant_message received, audio_path={audio_path}",
                )
            else:
                self.add_result(name, "FAIL", f"Unexpected payload: {body}")
        except Exception as exc:
            self.add_result(name, "FAIL", str(exc))

    async def test_voice(self, client: httpx.AsyncClient) -> None:
        name = "Voice Endpoint"
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = Path(temp_file.name)

            self._write_silent_wav(temp_path)

            with temp_path.open("rb") as audio_file:
                files = {"audio": (temp_path.name, audio_file, "audio/wav")}
                data = {
                    "session_id": "test-voice-session",
                    "persona_id": "priya_shah",
                    "transcript_override": "Please remember I like concise answers.",
                }
                response = await client.post(
                    f"{self.base_url}/api/voice",
                    data=data,
                    files=files,
                )
            temp_path.unlink(missing_ok=True)

            if response.status_code >= 400:
                self.add_result(
                    name,
                    "FAIL",
                    await self.response_error_detail(response, "Voice request failed."),
                )
                return

            body = response.json()
            self.voice_payload = body
            if body.get("transcript") and body.get("assistant_message") and body.get("audio_path"):
                self.successful_sessions.append("test-voice-session")
                self.add_result(
                    name,
                    "PASS",
                    f"transcript processed, audio_path={body.get('audio_path')}",
                )
            else:
                self.add_result(name, "FAIL", f"Unexpected payload: {body}")
        except Exception as exc:
            self.add_result(name, "FAIL", str(exc))

    async def test_websocket(self) -> None:
        name = "WebSocket Endpoint"
        try:
            async with websockets.connect(f"{self.ws_url}/ws/chat") as websocket:
                await websocket.send("hello jarvis")
                raw_response = await websocket.recv()
            payload = json.loads(raw_response)
            if payload.get("assistant_message"):
                self.add_result(name, "PASS", "assistant_message received over websocket")
            else:
                self.add_result(name, "FAIL", f"Unexpected payload: {payload}")
        except Exception as exc:
            self.add_result(name, "FAIL", str(exc))

    def test_generated_output(self) -> None:
        name = "Generated Output Artifact"
        candidate_paths = [
            self.chat_payload.get("audio_path"),
            self.voice_payload.get("audio_path"),
        ]
        existing_paths = [Path(path) for path in candidate_paths if path]
        missing_paths = [str(path) for path in existing_paths if not path.exists()]

        if existing_paths and not missing_paths:
            self.add_result(
                name,
                "PASS",
                ", ".join(str(path.name) for path in existing_paths),
            )
            return

        if missing_paths:
            self.add_result(name, "FAIL", f"Missing artifact(s): {', '.join(missing_paths)}")
            return

        if not self.successful_sessions:
            self.add_result(
                name,
                "SKIP",
                "No chat or voice turn completed, so no output artifact was expected.",
            )
            return

        self.add_result(name, "FAIL", "No audio_path values were returned by completed API turns.")

    def test_database(self) -> None:
        name = "Database Persistence"
        providers = self.health_payload.get("providers", {})
        database_provider = providers.get("database", "")

        if "sqlite" not in database_provider:
            self.add_result(
                name,
                "SKIP",
                f"Active database is {database_provider or 'unknown'}, SQLite file check skipped.",
            )
            return

        if not self.sqlite_db.exists():
            self.add_result(name, "FAIL", f"SQLite database not found at {self.sqlite_db}")
            return

        if not self.successful_sessions:
            self.add_result(
                name,
                "SKIP",
                "No chat or voice turn completed, so no database turns were expected.",
            )
            return

        try:
            with sqlite3.connect(self.sqlite_db) as connection:
                placeholders = ", ".join("?" for _ in self.successful_sessions)
                cursor = connection.execute(
                    (
                        "select count(*) from conversation_turns "
                        f"where session_id in ({placeholders})"
                    ),
                    tuple(self.successful_sessions),
                )
                row_count = cursor.fetchone()[0]
            expected_turns = len(self.successful_sessions) * 2
            if row_count >= expected_turns:
                self.add_result(name, "PASS", f"Found {row_count} stored conversation turns.")
            else:
                self.add_result(
                    name,
                    "FAIL",
                    f"Expected at least {expected_turns} stored turns, found {row_count}.",
                )
        except Exception as exc:
            self.add_result(name, "FAIL", str(exc))

    def print_summary(self) -> None:
        print()
        print("Jarvis Assistant Test Results")
        print("=" * 28)
        for result in self.results:
            print(f"[{result.status}] {result.name}")
            print(f"  {result.detail}")
        print()

        pass_count = sum(result.status == "PASS" for result in self.results)
        fail_count = sum(result.status == "FAIL" for result in self.results)
        skip_count = sum(result.status == "SKIP" for result in self.results)
        print(f"Passed: {pass_count}")
        print(f"Failed: {fail_count}")
        print(f"Skipped: {skip_count}")

    @staticmethod
    def _write_silent_wav(target: Path) -> None:
        with wave.open(str(target), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            wav_file.writeframes(b"\x00\x00" * 16000)

    @staticmethod
    async def response_error_detail(
        response: httpx.Response,
        fallback_message: str,
    ) -> str:
        raw_text = await response.aread()
        try:
            payload = json.loads(raw_text.decode("utf-8"))
        except Exception:
            payload = {"detail": raw_text.decode("utf-8", errors="replace")}

        message_parts = [
            str(payload.get("detail") or fallback_message),
            str(payload.get("message") or "").strip(),
        ]
        provider = payload.get("provider")
        if provider:
            message_parts.append(f"provider={provider}")
        return " | ".join(part for part in message_parts if part)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run end-to-end checks for the Jarvis starter.")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for the running FastAPI server.",
    )
    return parser.parse_args()


async def async_main() -> int:
    args = parse_args()
    workspace = Path(__file__).resolve().parent.parent
    runner = TestRunner(base_url=args.base_url, workspace=workspace)
    return await runner.run()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(async_main()))
