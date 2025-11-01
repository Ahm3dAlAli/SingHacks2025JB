"""
Regulatory Ingestion Engine - FastAPI Application

This module initializes the FastAPI application and includes all the API routes.
"""
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

# Import rule processing components
from app.rule_parsing.groq_rule_extractor import GroqRuleExtractor
from app.rule_parsing.service import rule_processor

from app.api.v1.api import api_router
from app.api.v1.endpoints import documents
from app.core.config import settings

# Set up base directory
BASE_DIR = Path("/Users/smitshah/Documents/singhack/SingHacks2025JB").resolve()

# Initialize FastAPI application
app = FastAPI(
    title="Regulatory Ingestion Engine",
    description="API for processing and analyzing regulatory documents",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set up CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(api_router, prefix=settings.API_V1_STR)
app.include_router(documents.router, prefix=settings.API_V1_STR, tags=["documents"])

# Health check endpoint with more detailed information
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and readiness probes."""
    try:
        # Check if the regulatory-docs directory exists
        docs_dir = BASE_DIR / "regulatory-docs"
        docs_exist = docs_dir.exists() and docs_dir.is_dir()
        
        # Count documents if directory exists
        doc_count = 0
        sources = {}
        
        if docs_exist:
            for source_dir in docs_dir.iterdir():
                if source_dir.is_dir():
                    try:
                        count = len(list(source_dir.glob("*.*")))
                        sources[source_dir.name] = count
                        doc_count += count
                    except Exception as e:
                        logger.error(f"Error counting documents in {source_dir}: {str(e)}")
        
        return {
            "status": "healthy",
            "service": "regulatory-ingestion-engine",
            "version": "0.1.0",
            "environment": settings.ENVIRONMENT,
            "docs_available": docs_exist,
            "document_count": doc_count,
            "sources": sources
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "error": str(e)
            }
        )

# Log application startup
@app.on_event("startup")
async def startup_event():
    """Initialize application services and log startup information."""
    logger.info("Starting Regulatory Ingestion Engine...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"API Version: {settings.API_V1_STR}")
    
    # Register the GroqRuleExtractor if API key is available
    try:
        groq_extractor = GroqRuleExtractor()
        rule_processor.register_extractor(groq_extractor)
        logger.info("Successfully registered GroqRuleExtractor")
    except Exception as e:
        logger.warning(f"Failed to register GroqRuleExtractor: {str(e)}")
    
    # Log available document sources
    try:
        docs_dir = BASE_DIR / "regulatory-docs"
        if docs_dir.exists() and docs_dir.is_dir():
            sources = [d.name for d in docs_dir.iterdir() if d.is_dir()]
            logger.info(f"Found {len(sources)} document sources: {', '.join(sources) if sources else 'None'}")
            
            # Log document counts per source
            for source in sources:
                count = len(list((docs_dir / source).glob("*.*")))
                logger.info(f"  - {source}: {count} documents")
        else:
            logger.warning(f"Document directory not found: {docs_dir}")
    except Exception as e:
        logger.error(f"Error scanning document directory: {str(e)}")

# Log application shutdown
@app.on_event("shutdown")
async def shutdown_event():
    """Log application shutdown."""
    logger.info("Shutting down Regulatory Ingestion Engine...")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8003,
        reload=True,
        log_level="info"
    )
