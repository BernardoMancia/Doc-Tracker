import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from core.database import init_db
from api.routes import dashboard, findings, scans, stream

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logger.info("Initializing database...")
    await init_db()
    logger.info("OSINT/DLP System online — port %d", settings.api_port)
    yield
    logger.info("Shutting down OSINT/DLP System")


def create_app() -> FastAPI:
    app = FastAPI(
        title="OSINT & DLP System — Grupo Roullier",
        version="2.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url=None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

    app.include_router(dashboard.router)
    app.include_router(findings.router, prefix="/api")
    app.include_router(scans.router, prefix="/api")
    app.include_router(stream.router, prefix="/api")

    return app
