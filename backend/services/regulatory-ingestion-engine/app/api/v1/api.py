"""
Main API router that includes all version 1 API endpoints.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import documents, processing, rules

# Create the main API router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(processing.router, prefix="/process", tags=["processing"])
api_router.include_router(rules.router, prefix="/rules", tags=["rules"])
