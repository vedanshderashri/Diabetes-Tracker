"""
MedAI Assistant - FastAPI Application
Main application factory with middleware, startup events, and route registration.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.core.config import get_settings
from app.core.database import init_db, close_db
from app.api.router import api_router
from app import models
from app.services.rag_engine import rag_engine
from app.services.disease_predictor import disease_predictor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info("=" * 60)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info("=" * 60)

    # Initialize database
    await init_db()
    logger.info("✓ Database initialized")

    # Initialize RAG engine
    try:
        await rag_engine.initialize()
        stats = rag_engine.get_collection_stats()
        logger.info(f"✓ RAG Engine initialized ({stats.get('count', 0)} documents)")

        # Seed if empty
        if stats.get("count", 0) == 0:
            import os
            datasets_dir = os.path.join(settings.BASE_DIR.parent, "")
            if os.path.exists(os.path.join(datasets_dir, "dataset.csv")):
                await rag_engine.seed_medical_knowledge(datasets_dir)
                logger.info("✓ Medical knowledge seeded into vector store")
    except Exception as e:
        logger.warning(f"⚠ RAG Engine initialization failed: {e}")

    # Load ML models
    try:
        disease_predictor.load_models()
        status = disease_predictor.get_model_status()
        logger.info(f"✓ ML Models: {status}")
    except Exception as e:
        logger.warning(f"⚠ ML model loading failed: {e}")

    # Create upload directory
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    logger.info("✓ Upload directory ready")

    logger.info("=" * 60)
    logger.info("🚀 MedAI Assistant is ready!")
    logger.info(f"📡 API: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info("=" * 60)

    yield

    # Shutdown
    await close_db()
    logger.info("MedAI Assistant shutdown complete")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        description=(
            "AI-powered healthcare platform with medical chatbot, "
            "report analysis, disease prediction, and patient management."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ── CORS Middleware ──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Cache Control Middleware ──
    @app.middleware("http")
    async def add_no_cache_headers(request: Request, call_next):
        response = await call_next(request)
        if request.method == "GET" and request.url.path.startswith("/api/v1"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response

    # ── Rate Limiting ──
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # ── Register Routes ──
    app.include_router(api_router)

    # ── Health Check ──
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "app": settings.APP_NAME,
            "version": settings.APP_VERSION,
        }

    return app


app = create_app()
