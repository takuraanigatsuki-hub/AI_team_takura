"""MVP REST API — FastAPI, JWT auth, PostgreSQL CRUD."""

from api.app import api_router, init_api, shutdown_api

__all__ = ["api_router", "init_api", "shutdown_api"]
