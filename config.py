from functools import lru_cache
from typing import List

from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Jarvis Assistant Starter"
    environment: str = "development"
    debug: bool = True
    api_prefix: str = "/api"

    llm_provider: str = "bedrock"
    llm_temperature: float = 0.4
    llm_max_tokens: int = 300
    llm_top_k: int | None = None
    llm_top_p: float | None = None
    llm_prompt_template_path: str = "prompts/jarvis_chat.txt"

    groq_api_key: str | None = None
    groq_model: str = "llama-3.3-70b-versatile"

    bedrock_region: str = "us-west-2"
    bedrock_model_id: str = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    aws_profile_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("aws_profile_name", "AWS_PROFILE_NAME", "AWS_PROFILE"),
    )

    openai_api_key: str | None = None
    realtime_model: str = "gpt-4o-mini-realtime-preview"

    database_url: str = "mysql+aiomysql://root:password@localhost:3306/jarvis"
    sqlite_fallback_url: str = "sqlite+aiosqlite:///./jarvis.db"
    allow_sqlite_fallback: bool = True
    whisper_model_size: str = "base"
    whisper_language: str | None = "en"
    whisper_task: str = "transcribe"
    whisper_device: str | None = None
    voice_understanding_provider: str = "legacy"
    emotion_model_name: str = "Dpngtm/wav2vec2-emotion-recognition"
    emotion_device: int = -1
    sensevoice_model_name: str = "iic/SenseVoiceSmall"
    sensevoice_device: str = "cpu"
    sensevoice_language: str = "auto"
    sensevoice_use_itn: bool = True
    sensevoice_vad_model: str | None = "fsmn-vad"
    sensevoice_cache_dir: str = ".cache/modelscope"
    sensevoice_max_single_segment_time_ms: int = 30000
    sensevoice_batch_size_s: int = 60
    sensevoice_merge_vad: bool = True
    sensevoice_merge_length_s: int = 15
    coqui_model_name: str = "tts_models/en/ljspeech/tacotron2-DDC"
    coqui_device: str | None = None
    audio_output_dir: str = "generated_audio"
    upload_dir: str = "uploads"

    cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"]
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator(
        "llm_provider",
        "llm_prompt_template_path",
        "llm_top_k",
        "llm_top_p",
        "groq_api_key",
        "openai_api_key",
        "aws_profile_name",
        "whisper_language",
        "whisper_device",
        "sensevoice_vad_model",
        "coqui_device",
        mode="before",
    )
    @classmethod
    def empty_strings_to_none(cls, value: str | None):
        if value is None:
            return value
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("debug", mode="before")
    @classmethod
    def debug_strings_to_bool(cls, value: bool | str):
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"dev", "development"}:
                return True
        return value

    @field_validator("groq_api_key", "openai_api_key", mode="before")
    @classmethod
    def placeholder_api_keys_to_none(cls, value: str | None):
        value = cls.empty_strings_to_none(value)
        if not isinstance(value, str):
            return value

        normalized = value.strip().lower()
        placeholder_values = {
            "your_key_here",
            "your_groq_api_key_here",
            "your_openai_api_key_here",
            "replace_me",
            "changeme",
        }
        if normalized in placeholder_values:
            return None
        if normalized.startswith("your_") and normalized.endswith("_here"):
            return None
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
