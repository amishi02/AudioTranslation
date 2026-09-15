---
applyTo: "backend/**/*.py"
---

# Backend Instructions

Use FastAPI.

Follow the layered structure:

api
services
providers
schemas
models
core
utils

Keep API/WebSocket handlers thin.

Put application logic in services.

Keep external AI integrations inside providers.

Use async programming for I/O-bound operations.

Use type hints.

Use Pydantic for structured data.

Do not introduce a database during Phase 1.

Do not introduce Celery or Redis into the real-time audio pipeline.