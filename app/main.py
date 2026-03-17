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
from fastapi.responses import FileResponse
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.api.endpoints import router
from app.api.websocket import ws_router

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
    pass


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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# Serve built React frontend if dist/ exists (packaged / production mode)
_FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
# Also check next to the exe (PyInstaller _MEIPASS or cwd)
import sys as _sys
_MEIPASS_DIST = Path(getattr(_sys, "_MEIPASS", ".")) / "frontend_dist"

def _get_dist() -> Path | None:
    if _MEIPASS_DIST.exists():
        return _MEIPASS_DIST
    if _FRONTEND_DIST.exists():
        return _FRONTEND_DIST
    return None

_dist = _get_dist()
if _dist:
    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(_dist / "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve React SPA — fall back to index.html for client-side routes."""
        candidate = _dist / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"name": "CardioXNet API", "version": "0.1.0", "status": "running", "docs": "/docs"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
