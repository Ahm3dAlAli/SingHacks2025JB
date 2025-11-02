"""
Batch processing models for Transaction Analysis Engine API.
Defines data transfer objects for batch upload, status, and results.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator

from . import SeverityLevel, AlertLevel, RuleViolation, BehavioralFlag


class BatchUploadResponse(BaseModel):
    """Response model for batch upload"""
    batch_id: UUID = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Batch status (PENDING/PROCESSING/COMPLETED/FAILED)")
    total_transactions: int = Field(..., description="Total transactions in batch")
    status_url: str = Field(..., description="URL to check batch status")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "PENDING",
                "total_transactions": 1000,
                "status_url": "/api/v1/tae/batch/550e8400-e29b-41d4-a716-446655440000/status",
                "estimated_completion": "2025-11-01T15:45:00Z",
            }
        }
    }


class BatchStatusResponse(BaseModel):
    """Response model for batch status check"""
    batch_id: UUID = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Current batch status")
    total_transactions: int = Field(..., description="Total transactions")
    processed_count: int = Field(..., description="Number of transactions processed")
    failed_count: int = Field(..., description="Number of transactions failed")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    started_at: datetime = Field(..., description="Batch processing start time")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )
    completed_at: Optional[datetime] = Field(None, description="Actual completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "PROCESSING",
                "total_transactions": 1000,
                "processed_count": 450,
                "failed_count": 2,
                "progress_percent": 45.0,
                "started_at": "2025-11-01T15:30:00Z",
                "estimated_completion": "2025-11-01T15:45:00Z",
                "completed_at": None,
                "error_message": None,
            }
        }
    }


class BatchResultsSummary(BaseModel):
    """Summary statistics for batch results"""
    total: int = Field(..., description="Total transactions")
    critical: int = Field(..., description="CRITICAL alert level count")
    high: int = Field(..., description="HIGH alert level count")
    medium: int = Field(..., description="MEDIUM alert level count")
    low: int = Field(..., description="LOW alert level count")


class BatchResultItem(BaseModel):
    """Individual result item in batch results"""
    transaction_id: UUID = Field(..., description="Transaction UUID")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    alert_level: AlertLevel = Field(..., description="Alert level")
    explanation_summary: str = Field(..., description="Brief explanation")
    recommended_action: str = Field(..., description="Recommended action")


class BatchResultsPagination(BaseModel):
    """Pagination metadata for batch results"""
    total: int = Field(..., description="Total results")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Current offset")
    next: Optional[str] = Field(None, description="Next page URL")


class BatchResultsResponse(BaseModel):
    """Response model for batch results"""
    batch_id: UUID = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Batch status")
    summary: BatchResultsSummary = Field(..., description="Summary statistics")
    processing_duration_seconds: Optional[int] = Field(
        None, description="Total processing time in seconds"
    )
    results: List[BatchResultItem] = Field(..., description="Result items")
    pagination: BatchResultsPagination = Field(..., description="Pagination metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "COMPLETED",
                "summary": {
                    "total": 1000,
                    "critical": 15,
                    "high": 87,
                    "medium": 234,
                    "low": 664,
                },
                "processing_duration_seconds": 238,
                "results": [
                    {
                        "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                        "risk_score": 85,
                        "alert_level": "CRITICAL",
                        "explanation_summary": "PEP status + cash limit violation",
                        "recommended_action": "FILE_STR",
                    }
                ],
                "pagination": {
                    "total": 1000,
                    "limit": 100,
                    "offset": 0,
                    "next": "/api/v1/tae/batch/550e8400.../results?offset=100",
                },
            }
        }
    }
