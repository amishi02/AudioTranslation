"""Application configuration via pydantic-settings.

Loads from environment variables and ``backend/.env``.
All Phase-1-visible keys have safe defaults; future phase keys are
``Optional`` so unknown envs are ignored (``extra="ignore"``).

See ``backend/.env.example`` for the full template and
``AGENTS.md`` / ``implementation-plan/phase1.md`` P1-BE-001.
"""

from typing import Literal

from pydantic import Field
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
    translation_model: str | None = None
    unified_model: str | None = None
    tts_model: str | None = None

    # --- Audio / WS (Phase 4-5) ---
    audio_target_sample_rate: int | None = None
    audio_channels: int | None = None
    audio_chunk_ms: int | None = None
    audio_queue_maxsize: int = Field(default=64, ge=1, le=1024)
    max_audio_frame_bytes: int = Field(default=65536, ge=1024, le=1048576)
    max_json_bytes: int = Field(default=65536, ge=1024, le=1048576)

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
