"""FastAPI application factory for the AIGRO AI News API.

Routes are mounted without an extra /v1 prefix so paths match
docs/03-http-api-spec.md exactly (``/news/...``, ``/insights/...``, ``/meta/...``).
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import admin, insights, meta, news


def _cors_origins() -> list[str]:
    """Allow-origins from the CORS_ORIGINS env var (comma-separated); default ``*``."""
    raw = os.getenv("CORS_ORIGINS", "*")
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def create_app() -> FastAPI:
    app = FastAPI(title="AIGRO AI News API")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(news.router)
    app.include_router(insights.router)
    app.include_router(meta.router)
    app.include_router(admin.router)

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
