import asyncio
import os
import re
from pathlib import Path

from app.config import Settings

try:
    from funasr import AutoModel
except ImportError:  # pragma: no cover - optional dependency
    AutoModel = None

try:
    from funasr.utils.postprocess_utils import rich_transcription_postprocess
except ImportError:  # pragma: no cover - optional dependency
    rich_transcription_postprocess = None


class SenseVoiceService:
    LANGUAGE_TAGS = {"zh", "en", "yue", "ja", "ko", "nospeech"}
    EMOTION_MAP = {
        "neutral": "neutral",
        "happy": "happy",
        "sad": "sad",
        "angry": "angry",
        "fearful": "fear",
        "fear": "fear",
        "surprised": "surprised",
        "disgusted": "disgust",
        "emo_unk": "neutral",
    }

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = None

    @property
    def enabled(self) -> bool:
        return self.settings.voice_understanding_provider.lower() == "sensevoice"

    @property
    def provider_status(self) -> str:
        if not self.enabled:
            return "disabled"
        if AutoModel is None:
            return "missing funasr dependency"
        return f"configured ({self.settings.sensevoice_model_name})"

    def _load_model(self):
        if AutoModel is None:
            raise RuntimeError("FunASR is not installed. Install requirements and try again.")
        if self.model is None:
            cache_dir = str(Path(self.settings.sensevoice_cache_dir).resolve())
            os.environ.setdefault("MODELSCOPE_CACHE", cache_dir)
            kwargs = {
                "model": self.settings.sensevoice_model_name,
                "trust_remote_code": True,
                "device": self.settings.sensevoice_device,
                "disable_update": True,
            }
            if self.settings.sensevoice_vad_model:
                kwargs["vad_model"] = self.settings.sensevoice_vad_model
                kwargs["vad_kwargs"] = {
                    "max_single_segment_time": self.settings.sensevoice_max_single_segment_time_ms,
                }
            self.model = AutoModel(**kwargs)
        return self.model

    @staticmethod
    def _extract_tags(raw_text: str) -> list[str]:
        return [match.lower() for match in re.findall(r"<\|([^|]+)\|>", raw_text)]

    @classmethod
    def _extract_language(cls, tags: list[str]) -> str | None:
        for tag in tags:
            if tag in cls.LANGUAGE_TAGS:
                return tag
        return None

    @classmethod
    def _extract_emotion(cls, tags: list[str]) -> str:
        for tag in tags:
            if tag in cls.EMOTION_MAP:
                return cls.EMOTION_MAP[tag]
        return "neutral"

    @staticmethod
    def _extract_event(tags: list[str]) -> str | None:
        ignored = {
            "withitn",
            "withoutitn",
            "woitn",
            "en",
            "zh",
            "yue",
            "ja",
            "ko",
            "nospeech",
            "neutral",
            "happy",
            "sad",
            "angry",
            "fearful",
            "fear",
            "surprised",
            "disgusted",
            "emo_unk",
        }
        for tag in tags:
            if tag not in ignored:
                return tag
        return None

    @staticmethod
    def _fallback_transcript(raw_text: str) -> str:
        return re.sub(r"<\|[^|]+\|>", " ", raw_text).strip()

    def _process_sync(self, audio_path: Path) -> dict[str, object]:
        model = self._load_model()
        result = model.generate(
            input=str(audio_path),
            cache={},
            language=self.settings.sensevoice_language,
            use_itn=self.settings.sensevoice_use_itn,
            batch_size_s=self.settings.sensevoice_batch_size_s,
            merge_vad=self.settings.sensevoice_merge_vad,
            merge_length_s=self.settings.sensevoice_merge_length_s,
        )
        if not result:
            raise RuntimeError("SenseVoice returned no result.")

        item = result[0] if isinstance(result, list) else result
        if not isinstance(item, dict):
            item = {"text": str(item)}

        raw_text = str(item.get("text", "")).strip()
        if rich_transcription_postprocess is not None:
            transcript = rich_transcription_postprocess(raw_text).strip()
        else:
            transcript = self._fallback_transcript(raw_text)

        tags = self._extract_tags(raw_text)
        final_emotion = self._extract_emotion(tags)

        return {
            "transcript": transcript,
            "final_emotion": final_emotion,
            "audio_emotion": final_emotion,
            "audio_score": 1.0,
            "text_emotion": final_emotion,
            "text_score": 1.0,
            "decision_source": "sensevoice",
            "provider": "sensevoice",
            "language": self._extract_language(tags),
            "audio_event": self._extract_event(tags),
            "raw_output": raw_text,
        }

    async def process(self, audio_path: Path) -> dict[str, object]:
        return await asyncio.to_thread(self._process_sync, audio_path)
