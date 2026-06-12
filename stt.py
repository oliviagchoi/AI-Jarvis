import asyncio
import ssl
import urllib.error
from pathlib import Path

from app.config import Settings

try:
    import whisper
except ImportError:  # pragma: no cover - optional dependency
    whisper = None


class SpeechToTextService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = None

    @property
    def provider_status(self) -> str:
        if whisper is None:
            return "missing whisper dependency"
        return "configured"

    def _load_model(self):
        if whisper is None:
            raise RuntimeError("Whisper is not installed.")
        if self.model is None:
            self.model = whisper.load_model(
                self.settings.whisper_model_size,
                device=self.settings.whisper_device,
            )
        return self.model

    def _transcribe_sync(self, audio_path: Path) -> str:
        try:
            model = self._load_model()
            result = model.transcribe(
                str(audio_path),
                task=self.settings.whisper_task,
                language=self.settings.whisper_language,
            )
            return result["text"].strip()
        except urllib.error.URLError as exc:
            reason = getattr(exc, "reason", None)
            if isinstance(reason, ssl.SSLCertVerificationError):
                raise RuntimeError(
                    "Whisper model download failed because Python could not verify the SSL certificate chain. "
                    "Use Transcript Override for now, or fix local certificate trust so Whisper can download its model."
                ) from exc
            raise

    async def transcribe(
        self, audio_path: Path, *, transcript_override: str | None = None
    ) -> str:
        if transcript_override:
            return transcript_override.strip()
        if whisper is None:
            raise RuntimeError(
                "Whisper is not installed. Install requirements and try again."
            )
        return await asyncio.to_thread(self._transcribe_sync, audio_path)
