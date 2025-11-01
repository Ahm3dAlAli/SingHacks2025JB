"""
Alert Service - FastAPI Application
Main entry point for the Alert Service providing REST API endpoints.
"""

from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app import __version__
from app.config import settings
from app.utils.logger import logger
from app.database.connection import test_connection, close_db_connection


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Lifespan context manager for FastAPI app.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info(
        "Starting Alert Service",
        extra={
            "extra_data": {
                "version": __version__,
                "environment": settings.ENVIRONMENT,
                "port": settings.ALERT_SERVICE_PORT,
            }
        },
    )

    # Test database connection
    db_connected = await test_connection()
    if not db_connected:
        logger.error("Failed to connect to database on startup!")
        # Don't raise exception - let health check report unhealthy state
    else:
        logger.info("Database connection established successfully")

    yield

    # Shutdown
    logger.info("Shutting down Alert Service")
    await close_db_connection()


# Create FastAPI application
app = FastAPI(
    title="Alert Service",
    description="AML Alert Service - Real-time risk alert notifications and management",
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)


# CORS Middleware - allow configured origins for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages"""
    logger.warning(
        f"Validation error on {request.url.path}", extra={"extra_data": {"errors": exc.errors()}}
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all uncaught exceptions"""
    logger.error(
        f"Unhandled exception on {request.url.path}: {exc}",
        extra={"extra_data": {"error_type": type(exc).__name__, "url": str(request.url)}},
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_type": type(exc).__name__ if settings.is_development else "ServerError",
        },
    )


# Health check endpoint
@app.get(
    "/health",
    tags=["Health"],
    summary="Health check endpoint",
    response_description="Service health status",
)
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.

    Returns:
        dict: Service health status including database connectivity
    """
    # Test database connection
    db_connected = await test_connection()

    health_status = {
        "status": "healthy" if db_connected else "unhealthy",
        "service": "Alert Service",
        "version": __version__,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "database": "connected" if db_connected else "disconnected",
        "environment": settings.ENVIRONMENT,
        "port": settings.ALERT_SERVICE_PORT,
    }

    logger.info("Health check performed", extra={"extra_data": health_status})

    return JSONResponse(
        status_code=status.HTTP_200_OK if db_connected else status.HTTP_503_SERVICE_UNAVAILABLE,
        content=health_status,
    )


# Root endpoint
@app.get(
    "/",
    tags=["Info"],
    summary="Service information",
)
async def root():
    """
    Root endpoint providing basic service information.

    Returns:
        dict: Service name, version, and documentation links
    """
    return {
        "service": "Alert Service",
        "version": __version__,
        "status": "running",
        "docs": "/docs",
        "health": "/health",
    }


if __name__ == "__main__":
    # This block is for direct execution only (not used in Docker)
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.ALERT_SERVICE_PORT,
        reload=settings.is_development,
        log_level=settings.LOG_LEVEL.lower(),
    )
