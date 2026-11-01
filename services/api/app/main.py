import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.v1 import admin, ai, auth, community, contests, problems, submissions
from app.core.config import get_settings
from app.core.errors import install_error_handlers
from app.db import SessionLocal

logging.basicConfig(level=logging.INFO)


def create_app() -> FastAPI:
    s = get_settings()
    s.validate_for_runtime()
    app = FastAPI(title="CodeArena API", version="0.1.0", docs_url="/docs")
    install_error_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[s.web_origin],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request.state.request_id = request.headers.get("x-request-id", uuid.uuid4().hex)[:64]
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        return response

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.get("/ready")
    def ready():
        with SessionLocal() as db:
            db.execute(text("select 1"))
        return {"status": "ready"}

    for module in (auth, problems, submissions, contests, community, admin, ai):
        app.include_router(module.router, prefix="/api/v1")
    return app


app = create_app()
