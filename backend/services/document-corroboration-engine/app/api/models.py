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
    MINIMAL = "minimal"
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

# Detailed Analysis Response Models
class StructureAnalysis(BaseModel):
    total_pages: int = 0
    total_paragraphs: int = 0
    total_words: int = 0
    total_characters: int = 0
    average_line_length: float = 0.0
    headings_count: int = 0
    sections: List[Dict[str, Any]] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    images: List[Dict[str, Any]] = Field(default_factory=list)

class FormatValidation(BaseModel):
    overall_format_score: float = Field(0.0, ge=0.0, le=1.0)
    format_rating: str = "unknown"
    basic_checks: Dict[str, Any] = Field(default_factory=dict)
    ai_analysis: Dict[str, Any] = Field(default_factory=dict)
    content_validation: Dict[str, Any] = Field(default_factory=dict)

class ImageAnalysis(BaseModel):
    overall_trust_score: float = Field(0.0, ge=0.0, le=1.0)
    trust_rating: str = "unknown"
    authenticity_analysis: Dict[str, Any] = Field(default_factory=dict)
    content_analysis: Dict[str, Any] = Field(default_factory=dict)
    quality_analysis: Dict[str, Any] = Field(default_factory=dict)
    tampering_analysis: Dict[str, Any] = Field(default_factory=dict)
    risk_factors: Dict[str, Any] = Field(default_factory=dict)
    recommendations: List[str] = Field(default_factory=list)

class RiskBreakdown(BaseModel):
    format_risk: float = Field(0.0, ge=0.0, le=1.0)
    content_risk: float = Field(0.0, ge=0.0, le=1.0)
    authenticity_risk: float = Field(0.0, ge=0.0, le=1.0)
    compliance_risk: float = Field(0.0, ge=0.0, le=1.0)
    structural_risk: float = Field(0.0, ge=0.0, le=1.0)

class RiskFactor(BaseModel):
    category: str
    description: str
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    severity: str

class RiskAssessment(BaseModel):
    overall_risk_score: float = Field(0.0, ge=0.0, le=1.0)
    risk_level: RiskLevel
    risk_breakdown: RiskBreakdown
    risk_factors: List[RiskFactor] = Field(default_factory=list)
    primary_concerns: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)

class DocumentAnalysisResponse(BaseModel):
    document_id: str
    filename: str
    status: ProcessingStatus
    
    # Core extraction
    extracted_text: Optional[str] = None
    processing_method: Optional[str] = None
    
    # Document classification
    document_type: Optional[str] = Field(
        None, 
        description="Type of document (e.g., legal, compliance, financial, identification, contract)"
    )
    is_relevant: Optional[bool] = Field(
        True, 
        description="Whether the document is relevant for legal/compliance review"
    )
    has_proof: Optional[bool] = Field(
        False, 
        description="Whether the document contains verifiable proof"
    )
    proof_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Details about the proof found in the document"
    )
    
    # Structure analysis
    structure_analysis: Optional[StructureAnalysis] = None
    
    # Format validation
    format_validation: Optional[FormatValidation] = None
    
    # Image analysis (for image documents)
    image_analysis: Optional[ImageAnalysis] = None
    
    # Risk assessment
    risk_assessment: Optional[RiskAssessment] = None
    
    # Legacy fields for backward compatibility
    format_issues: List[str] = Field(default_factory=list)
    spelling_errors: List[str] = Field(default_factory=list)
    missing_sections: List[str] = Field(default_factory=list)
    risk_score: float = Field(0.0, ge=0.0, le=1.0)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    
    # Metadata
    processing_time: Optional[float] = None
    processed_at: Optional[datetime] = None
    upload_date: Optional[datetime] = None

class DocumentSummaryResponse(BaseModel):
    document_id: str
    filename: str
    file_type: str
    status: ProcessingStatus
    risk_score: float
    risk_level: RiskLevel
    upload_date: datetime
    processed_at: Optional[datetime] = None

class BatchUploadResponse(BaseModel):
    success_count: int
    failed_count: int
    documents: List[DocumentUploadResponse]
    errors: List[Dict[str, str]] = Field(default_factory=list)

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
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatisticsResponse(BaseModel):
    total_documents: int
    documents_by_status: Dict[str, int]
    documents_by_risk_level: Dict[str, int]
    average_processing_time: float
    average_risk_score: float
    total_high_risk: int
    recent_uploads: int

class ReprocessRequest(BaseModel):
    document_id: str
    force: bool = False
    reason: Optional[str] = None

class ComparisonRequest(BaseModel):
    document_id_1: str
    document_id_2: str

class ComparisonResponse(BaseModel):
    document_1: DocumentSummaryResponse
    document_2: DocumentSummaryResponse
    similarity_score: float
    differences: List[str]
    common_issues: List[str]
    risk_comparison: Dict[str, Any]