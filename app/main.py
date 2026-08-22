"""FastAPI application entry point for CardioXNet."""

import sys
import io

# Ensure UTF-8 output on Windows to avoid charmap encoding errors with Unicode characters
if hasattr(sys.stdout, 'buffer'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'buffer'):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.endpoints import router
from app.api.websocket import ws_router
from app.web.routes import web_router

# Initialize logging
logger = setup_logging()

# Get application settings
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    # Startup
    logger.info("Starting CardioXNet API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")
    
    # Initialize services - FAST, eager loading
    logger.info("Initializing services (fast mode)...")
    try:
        from app.services.fast_service_init import initialize_services_fast
        from app.core.service_registry import register_service
        services = initialize_services_fast()
        
        # Register all services with the service registry for modular pipeline
        for name, service_factory in services.items():
            service_instance = service_factory()  # Call the factory to get the instance
            register_service(name, service_instance)
        
        logger.info(f"Services initialized and registered successfully ({len(services)} services)")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise
    
    logger.info("CardioXNet API ready")
    
    yield
    
    # Shutdown - simplified to avoid issues


# Create FastAPI application
app = FastAPI(
    title="CardioXNet API",
    description="Cardiac Repair Pathway Discovery Platform - NETS Pipeline",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)
app.include_router(ws_router)  # WebSocket for real-time progress

# Mount static assets (CSS + vendored htmx/alpine/cytoscape) for the server-rendered UI
_STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")

# Include the server-rendered web UI (home, progress, results, docs).
# Registered last so the JSON API (/api/v1/*) and OpenAPI routes take precedence.
app.include_router(web_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
