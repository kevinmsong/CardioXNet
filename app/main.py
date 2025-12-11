"""FastAPI application entry point for CardioXNet."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    description="Cardiac Repair Pathway Discovery Platform - NETS (Neighborhood Enrichment Triage and Scoring) Pipeline",
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
# app.include_router(ws_router)  # Temporarily disabled


@app.get("/")
async def root():
    """Root endpoint - health check."""
    return {
        "name": "CardioXNet API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs"
    }


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
