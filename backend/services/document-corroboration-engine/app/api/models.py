from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DocumentType(str, Enum):
    PDF = "pdf"
    DOCX = "docx"
    TXT = "txt"
    JPG = "jpg"
    JPEG = "jpeg"
    PNG = "png"

class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class DocumentUploadRequest(BaseModel):
    uploader_id: str = Field(..., description="ID of the user uploading the document")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")

class DocumentUploadResponse(BaseModel):
    document_id: str
    status: ProcessingStatus
    message: str
    estimated_processing_time: Optional[int] = None

class DocumentAnalysisResponse(BaseModel):
    document_id: str
    filename: str
    status: ProcessingStatus
    extracted_text: Optional[str] = None
    structure_analysis: Optional[Dict[str, Any]] = None
    format_issues: List[str] = Field(default_factory=list)
    spelling_errors: List[str] = Field(default_factory=list)
    missing_sections: List[str] = Field(default_factory=list)
    image_analysis: Optional[Dict[str, Any]] = None
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    risk_level: RiskLevel
    processing_time: Optional[float] = None
    processed_at: Optional[datetime] = None

class AuditTrailResponse(BaseModel):
    audit_id: str
    document_id: str
    action: str
    user_id: str
    timestamp: datetime
    details: Dict[str, Any]
    risk_score_change: Optional[float] = None

class HealthResponse(BaseModel):
    status: str
    database: str
    services: Dict[str, str]