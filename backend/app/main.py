from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import warm_up_database
from app.core.exceptions import install_exception_handlers
from app.core.logging import configure_logging
from app.middleware.request_logging import RequestLoggingMiddleware
from app.scripts.bootstrap_db import bootstrap_database

settings = get_settings()
configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    warm_up_database()
    if settings.auto_db_bootstrap:
        bootstrap_database()
    yield


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_origin_regex=settings.frontend_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
install_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health/live",
            "ready": "/health/ready",
            "api": settings.api_v1_prefix
        }
    }


@app.get("/health/live")
def live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def ready() -> dict[str, str]:
    return {"status": "ready"}
