"""FastAPI app: the API under /api and, when built, the React UI at /."""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db
from .api.routes import router
from .auth import router as auth_router

# Analysis never touches the network: model libraries must use local files only.
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def create_app() -> FastAPI:
    app = FastAPI(title="TruthLens", version=config.APP_VERSION,
                  docs_url=None if config.MODE == "hosted" else "/docs", redoc_url=None)
    app.add_middleware(CORSMiddleware, allow_origins=config.ALLOWED_ORIGINS, allow_origin_regex=config.ALLOWED_ORIGIN_REGEX,
                       allow_methods=["GET", "POST", "PATCH", "PUT"], allow_headers=["Authorization", "Content-Type"],
                       max_age=600)

    @app.middleware("http")
    async def security_headers(request, call_next):
        resp = await call_next(request)
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("Referrer-Policy", "no-referrer")
        resp.headers.setdefault("X-Frame-Options", "DENY")
        if request.url.path.startswith("/api/"):
            resp.headers.setdefault("Cache-Control", "no-store")
        return resp

    app.include_router(auth_router)
    app.include_router(router)

    @app.on_event("startup")
    def _startup() -> None:
        db.engine()

    dist = config.ROOT / "dist"
    if dist.exists():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str):
            target = dist / path
            return FileResponse(target if path and target.is_file() else dist / "index.html")

    return app


app = create_app()
