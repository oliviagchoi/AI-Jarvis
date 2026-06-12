import asyncio
import importlib
import os
from pathlib import Path
from uuid import uuid4

from app.config import Settings

try:
    import torch
except ImportError:  # pragma: no cover - optional dependency
    torch = None

# Coqui imports can pull in matplotlib/fontconfig during module import.
# Point caches to writable local directories so the import doesn't get stuck
# on user-level cache paths that are unavailable in some environments.
cache_root = Path(".cache")
cache_root.mkdir(parents=True, exist_ok=True)
matplotlib_cache = cache_root / "matplotlib"
fontconfig_cache = cache_root / "fontconfig"
matplotlib_cache.mkdir(parents=True, exist_ok=True)
fontconfig_cache.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(matplotlib_cache.resolve()))
os.environ.setdefault("XDG_CACHE_HOME", str(cache_root.resolve()))

class TextToSpeechService:
    def __init__(self, settings: Settings, output_dir: Path) -> None:
        self.settings = settings
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.model = None
        self.tts_class = None
        self.import_error = None

    def _get_tts_class(self):
        if self.tts_class is not None:
            return self.tts_class
        try:
            module = importlib.import_module("TTS.api")
            self.tts_class = getattr(module, "TTS")
            self.import_error = None
            return self.tts_class
        except Exception as exc:  # pragma: no cover - optional dependency
            self.import_error = exc
            return None

    @property
    def provider_status(self) -> str:
        if self._get_tts_class() is None:
            if self.import_error is not None:
                return f"fallback text-output only ({type(self.import_error).__name__})"
            return "fallback text-output only"
        return "configured"

    def _resolve_device(self) -> str:
        if self.settings.coqui_device:
            return self.settings.coqui_device
        if torch is not None and torch.cuda.is_available():
            return "cuda"
        return "cpu"

    def _load_model(self):
        tts_class = self._get_tts_class()
        if tts_class is None:
            raise RuntimeError("Coqui TTS is not installed.")
        if self.model is None:
            self.model = tts_class(
                model_name=self.settings.coqui_model_name,
                progress_bar=False,
            ).to(self._resolve_device())
        return self.model

    def _synthesize_sync(self, session_id: str, text: str) -> str:
        tts_model = self._load_model()
        safe_name = session_id.replace("/", "-")
        target = self.output_dir / f"{safe_name}-response-{uuid4().hex}.wav"
        tts_model.tts_to_file(text=text, file_path=str(target))
        return str(target)

    async def synthesize(self, session_id: str, text: str) -> str:
        if self._get_tts_class() is None:
            safe_name = session_id.replace("/", "-")
            target = self.output_dir / f"{safe_name}-response-{uuid4().hex}.txt"
            target.write_text(text, encoding="utf-8")
            return str(target)
        return await asyncio.to_thread(self._synthesize_sync, session_id, text)
