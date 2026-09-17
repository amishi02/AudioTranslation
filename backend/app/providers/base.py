"""Base provider — P6-MODEL-001."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ModelError(Exception):
    """Base model error mapped to WS error codes."""

    def __init__(self, message: str, code: str = "MODEL_ERROR") -> None:
        super().__init__(message)
        self.code = code


class ModelNotReady(ModelError):
    def __init__(self, message: str = "Model not ready") -> None:
        super().__init__(message, code="MODEL_NOT_READY")


class ModelInitError(ModelError):
    def __init__(self, message: str = "Model init failed") -> None:
        super().__init__(message, code="MODEL_ERROR")


class InferenceError(ModelError):
    def __init__(self, message: str = "Inference failed") -> None:
        super().__init__(message, code="MODEL_ERROR")


class BaseProvider(ABC):
    """Common lifecycle for all providers."""

    @abstractmethod
    async def initialize(self) -> None:
        """Load weights / prepare runtime. Idempotent."""

    @abstractmethod
    def is_ready(self) -> bool:
        """True if provider can serve requests."""

    @abstractmethod
    async def close(self) -> None:
        """Release resources."""

    async def health(self) -> dict[str, object]:
        return {"ready": self.is_ready()}
