"""Application configuration via pydantic-settings.

Loads from environment variables and ``backend/.env``.
All Phase-1-visible keys have safe defaults; future phase keys are
``Optional`` so unknown envs are ignored (``extra="ignore"``).

See ``backend/.env.example`` for the full template and
``AGENTS.md`` / ``implementation-plan/phase1.md`` P1-BE-001.
"""

from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central typed settings.

    Note: raw audio bytes must NEVER be logged — see ``app.core.logging``.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Core (Phase 1-2) ---
    app_name: str = Field(default="Real-Time Audio Translation API")
    app_version: str = Field(default="0.1.0")
    app_env: Literal["development", "production", "test"] = Field(default="development")
    log_level: str = Field(default="INFO")
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)

    # Comma-separated in env, e.g. ``CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173``
    # Stored as raw string to avoid pydantic-settings JSON-decode for list (Phase 1).
    cors_origins_raw: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        alias="CORS_ORIGINS",
        validation_alias="CORS_ORIGINS",
    )

    # Supported languages — comma-separated (Phase 2 stub)
    supported_languages_raw: str = Field(
        default="en,hi,es,fr,de",
        alias="SUPPORTED_LANGUAGES",
        validation_alias="SUPPORTED_LANGUAGES",
    )

    # --- Phase-2+ placeholders (kept Optional to avoid hard failure) ---
    pipeline_type: str | None = None
    stt_provider: str | None = None
    translation_provider: str | None = None
    tts_provider: str | None = None
    unified_provider: str | None = None

    # --- Model / device placeholders (Phase 7-9) ---
    stt_model: str | None = None
    stt_device: str | None = None
    stt_compute_type: str | None = None
    stt_min_decode_seconds: float = Field(default=1.0, ge=0.25, le=10.0)
    stt_vad_filter: bool = True
    stt_vad_min_speech_ms: int = Field(default=250, ge=50, le=2000)
    stt_vad_min_silence_ms: int = Field(default=500, ge=100, le=3000)
    stt_vad_speech_pad_ms: int = Field(default=100, ge=0, le=1000)
    stt_no_speech_threshold: float = Field(default=0.6, ge=0.0, le=1.0)
    translation_model: str | None = None
    unified_model: str | None = None
    tts_model: str | None = None

    @field_validator("stt_provider", mode="before")
    @classmethod
    def _validate_stt_provider(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"whisper", "faster_whisper", "faster-whisper", "mock"}
        if vv not in allowed:
            raise ValueError(f"STT_PROVIDER must be one of {sorted(allowed)}, got '{v}'")
        # normalize faster_whisper variants to whisper
        if vv in {"faster_whisper", "faster-whisper"}:
            return "whisper"
        return vv

    @field_validator("stt_device", mode="before")
    @classmethod
    def _validate_stt_device(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"cpu", "cuda"}
        if vv not in allowed:
            raise ValueError(f"STT_DEVICE must be one of {sorted(allowed)}, got '{v}'")
        return vv

    @field_validator("stt_compute_type", mode="before")
    @classmethod
    def _validate_stt_compute(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"int8", "float16", "float32", "int8_float16", "int8_float32"}
        if vv not in allowed:
            raise ValueError(f"STT_COMPUTE_TYPE must be one of {sorted(allowed)}, got '{v}'")
        return vv

    @field_validator("translation_provider", mode="before")
    @classmethod
    def _validate_translation_provider(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"mock", "opus", "nllb"}
        if vv not in allowed:
            raise ValueError(f"TRANSLATION_PROVIDER must be one of {sorted(allowed)}, got '{v}'")
        return vv

    @field_validator("translation_device", mode="before")
    @classmethod
    def _validate_translation_device(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"cpu", "cuda"}
        if vv not in allowed:
            raise ValueError(f"TRANSLATION_DEVICE must be one of {sorted(allowed)}, got '{v}'")
        return vv

    @field_validator("pipeline_type", mode="before")
    @classmethod
    def _validate_pipeline_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"cascaded", "unified"}
        if vv not in allowed:
            raise ValueError(f"PIPELINE_TYPE must be one of {sorted(allowed)}, got '{v}'")
        return vv

    @field_validator("tts_provider", mode="before")
    @classmethod
    def _validate_tts_provider(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"mock", "piper", "coqui", "xtts", "vits"}
        if vv not in allowed:
            raise ValueError(f"TTS_PROVIDER must be one of {sorted(allowed)}, got '{v}'")
        # normalize xtts/vits -> piper? keep as is for now, but map coqui variants
        if vv in {"xtts", "vits"}:
            return "piper"
        return vv

    @field_validator("unified_provider", mode="before")
    @classmethod
    def _validate_unified_provider(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"mock", "seamless", "seamless-m4t", "seamless_streaming"}
        if vv not in allowed:
            raise ValueError(f"UNIFIED_PROVIDER must be one of {sorted(allowed)}, got '{v}'")
        if vv == "seamless_streaming":
            return "seamless"
        return vv

    @field_validator("tts_device", mode="before")
    @classmethod
    def _validate_tts_device(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"cpu", "cuda"}
        if vv not in allowed:
            raise ValueError(f"TTS_DEVICE must be one of {sorted(allowed)}, got '{v}'")
        return vv

    @field_validator("unified_device", mode="before")
    @classmethod
    def _validate_unified_device(cls, v: str | None) -> str | None:
        if v is None:
            return v
        vv = str(v).strip().lower()
        allowed = {"cpu", "cuda"}
        if vv not in allowed:
            raise ValueError(f"UNIFIED_DEVICE must be one of {sorted(allowed)}, got '{v}'")
        return vv

    # --- Paths ---
    ws_v1_path: str = Field(default="/ws/v1/translate")
    api_v1_prefix: str = Field(default="/api/v1")
    health_path: str = Field(default="/health")
    health_ready_path: str = Field(default="/health/ready")

    # --- Device extras (Phase 7-9) ---
    translation_device: str | None = None
    translation_compute_type: str | None = None
    translation_max_length: int | None = Field(default=128, ge=1, le=512)
    translation_num_beams: int | None = Field(default=1, ge=1, le=8)
    translation_pair_map: str | None = None
    unified_device: str | None = None
    unified_target_sample_rate: int | None = Field(default=16000, ge=8000, le=48000)
    tts_device: str | None = None
    tts_sample_rate: int | None = Field(default=22050, ge=8000, le=48000)

    # --- Audio / WS (Phase 4-5) ---
    audio_target_sample_rate: int | None = Field(default=16000)
    audio_channels: int | None = Field(default=1)
    audio_chunk_ms: int | None = Field(default=60)
    audio_queue_maxsize: int = Field(default=128, ge=1, le=1024)
    max_audio_frame_bytes: int = Field(default=65536, ge=1024, le=1048576)
    max_json_bytes: int = Field(default=65536, ge=1024, le=1048576)

    # --- Observability ---
    metrics_enabled: bool = Field(default=False)

    @property
    def cors_origins(self) -> list[str]:
        """Parsed ``CORS_ORIGINS`` as list."""
        return [o.strip() for o in self.cors_origins_raw.split(",") if o.strip()]

    @property
    def supported_languages(self) -> list[str]:
        """Parsed ``SUPPORTED_LANGUAGES`` as list."""
        return [
            s.strip().lower()
            for s in self.supported_languages_raw.split(",")
            if s.strip()
        ]


settings = Settings()
