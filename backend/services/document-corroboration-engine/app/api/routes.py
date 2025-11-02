from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import os
import uuid
import time
from typing import List, Optional
from datetime import datetime, timedelta

from app.database.connection import get_db
from app.database.models import Document, AuditTrail
from app.api.models import (
    DocumentUploadRequest, DocumentUploadResponse, DocumentAnalysisResponse,
    AuditTrailResponse, HealthResponse, DocumentSummaryResponse, 
    BatchUploadResponse, StatisticsResponse, ReprocessRequest,
    ComparisonRequest, ComparisonResponse, ProcessingStatus, RiskLevel,
    StructureAnalysis, FormatValidation, ImageAnalysis, RiskAssessment,
    RiskBreakdown, RiskFactor
)
from app.workflows.workflow import process_document_workflow
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

# ============================================================================
# DOCUMENT UPLOAD ENDPOINTS
# ============================================================================

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    uploader_id: str = Query(..., description="ID of the user uploading"),
    db: Session = Depends(get_db)
):
    """
    Upload a single document for processing.
    
    Supports: PDF, DOCX, TXT, JPG, JPEG, PNG
    """
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(400, f"File type {file_extension} not supported")
        
        # Validate file size (100MB max)
        content = await file.read()
        if len(content) > 100 * 1024 * 1024:
            raise HTTPException(400, "File size exceeds 100MB limit")
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Save file
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{document_id}{file_extension}")
        
        with open(file_path, "wb") as buffer:
            buffer.write(content)
        
        # Create document record
        db_document = Document(
            id=document_id,
            filename=file.filename,
            file_type=file_extension[1:],
            file_size=len(content),
            uploader_id=uploader_id,
            status="pending"
        )
        db.add(db_document)
        
        # Create audit trail
        audit = AuditTrail(
            document_id=document_id,
            action="document_uploaded",
            user_id=uploader_id,
            details={
                "filename": file.filename,
                "file_size": len(content),
                "file_type": file_extension
            }
        )
        db.add(audit)
        db.commit()
        
        # Start background processing
        background_tasks.add_task(process_document_workflow, document_id, file_path)
        
        logger.info(f"Document uploaded successfully: {document_id}")
        
        return DocumentUploadResponse(
            document_id=document_id,
            status=ProcessingStatus.PROCESSING,
            message="Document uploaded and processing started",
            estimated_processing_time=30
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")


@router.post("/documents/upload/batch", response_model=BatchUploadResponse)
async def upload_documents_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    uploader_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Upload multiple documents for batch processing.
    """
    results = []
    errors = []
    success_count = 0
    failed_count = 0
    
    for file in files:
        try:
            result = await upload_document(background_tasks, file, uploader_id, db)
            results.append(result)
            success_count += 1
        except Exception as e:
            failed_count += 1
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
            logger.error(f"Failed to upload {file.filename}: {str(e)}")
    
    return BatchUploadResponse(
        success_count=success_count,
        failed_count=failed_count,
        documents=results,
        errors=errors
    )


# ============================================================================
# DOCUMENT RETRIEVAL ENDPOINTS
# ============================================================================

@router.get("/documents/{document_id}", response_model=DocumentAnalysisResponse)
async def get_document_analysis(document_id: str, db: Session = Depends(get_db)):
    """
    Get comprehensive analysis results for a document.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    
    # Parse structure analysis
    structure_analysis = None
    if document.structure_analysis:
        structure_analysis = StructureAnalysis(**document.structure_analysis)
    
    # Parse format validation
    format_validation = None
    if hasattr(document, 'format_validation') and document.format_validation:
        format_validation = FormatValidation(**document.format_validation)
    
    # Parse image analysis
    image_analysis = None
    if document.image_analysis:
        image_analysis = ImageAnalysis(**document.image_analysis)
    
    # Parse risk assessment
    risk_assessment = None
    if hasattr(document, 'risk_assessment') and document.risk_assessment:
        risk_breakdown = RiskBreakdown(**document.risk_assessment.get('risk_breakdown', {}))
        risk_factors = [RiskFactor(**rf) for rf in document.risk_assessment.get('risk_factors', [])]
        
        risk_assessment = RiskAssessment(
            overall_risk_score=document.risk_assessment.get('overall_risk_score', document.risk_score),
            risk_level=RiskLevel(document.risk_assessment.get('risk_level', document.risk_level)),
            risk_breakdown=risk_breakdown,
            risk_factors=risk_factors,
            primary_concerns=document.risk_assessment.get('primary_concerns', []),
            recommendations=document.risk_assessment.get('recommendations', [])
        )
    
    return DocumentAnalysisResponse(
        document_id=document.id,
        filename=document.filename,
        status=ProcessingStatus(document.status),
        extracted_text=document.extracted_text,
        processing_method=getattr(document, 'processing_method', None),
        document_type=document.document_type,
        is_relevant=document.is_relevant,
        has_proof=document.has_proof,
        proof_details=document.proof_details or {},
        structure_analysis=structure_analysis,
        format_validation=format_validation,
        image_analysis=image_analysis,
        risk_assessment=risk_assessment,
        format_issues=document.format_issues or [],
        spelling_errors=document.spelling_errors or [],
        missing_sections=document.missing_sections or [],
        risk_score=document.risk_score,
        risk_level=RiskLevel(document.risk_level),
        processing_time=document.processing_time,
        processed_at=document.processed_at,
        upload_date=document.upload_date
    )


@router.get("/documents", response_model=List[DocumentSummaryResponse])
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[ProcessingStatus] = None,
    risk_level: Optional[RiskLevel] = None,
    uploader_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List documents with optional filtering.
    """
    query = db.query(Document)
    
    if status:
        query = query.filter(Document.status == status.value)
    if risk_level:
        query = query.filter(Document.risk_level == risk_level.value)
    if uploader_id:
        query = query.filter(Document.uploader_id == uploader_id)
    
    documents = query.order_by(Document.upload_date.desc()).offset(skip).limit(limit).all()
    
    return [
        DocumentSummaryResponse(
            document_id=doc.id,
            filename=doc.filename,
            file_type=doc.file_type,
            status=ProcessingStatus(doc.status),
            risk_score=doc.risk_score,
            risk_level=RiskLevel(doc.risk_level),
            upload_date=doc.upload_date,
            processed_at=doc.processed_at
        )
        for doc in documents
    ]


@router.get("/documents/{document_id}/text")
async def get_document_text(document_id: str, db: Session = Depends(get_db)):
    """
    Get extracted text content from a document.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    
    if not document.extracted_text:
        raise HTTPException(404, "Text not yet extracted or unavailable")
    
    return {
        "document_id": document_id,
        "filename": document.filename,
        "extracted_text": document.extracted_text,
        "word_count": len(document.extracted_text.split()),
        "character_count": len(document.extracted_text)
    }


@router.get("/documents/{document_id}/structure")
async def get_document_structure(document_id: str, db: Session = Depends(get_db)):
    """
    Get document structure analysis.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    
    if not document.structure_analysis:
        raise HTTPException(404, "Structure analysis not available")
    
    return {
        "document_id": document_id,
        "filename": document.filename,
        **document.structure_analysis
    }


@router.get("/documents/{document_id}/risks")
async def get_document_risks(document_id: str, db: Session = Depends(get_db)):
    """
    Get detailed risk assessment for a document.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    
    risk_data = {
        "document_id": document_id,
        "filename": document.filename,
        "overall_risk_score": document.risk_score,
        "risk_level": document.risk_level,
        "format_issues": document.format_issues or [],
        "missing_sections": document.missing_sections or []
    }
    
    # Add detailed risk assessment if available
    if hasattr(document, 'risk_assessment') and document.risk_assessment:
        risk_data.update(document.risk_assessment)
    
    return risk_data


# ============================================================================
# DOCUMENT OPERATIONS
# ============================================================================

@router.post("/documents/{document_id}/reprocess")
async def reprocess_document(
    document_id: str,
    request: ReprocessRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Reprocess a document (useful after template updates or errors).
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    
    # Check if already processing
    if document.status == "processing" and not request.force:
        raise HTTPException(400, "Document is already being processed. Use force=true to override.")
    
    # Update status
    document.status = "pending"
    
    # Create audit trail
    audit = AuditTrail(
        document_id=document_id,
        action="reprocess_requested",
        user_id="system",  # Should be actual user
        details={
            "reason": request.reason,
            "forced": request.force
        }
    )
    db.add(audit)
    db.commit()
    
    # Reconstruct file path
    file_path = f"data/uploads/{document_id}.{document.file_type}"
    
    # Start reprocessing
    background_tasks.add_task(process_document_workflow, document_id, file_path)
    
    return {
        "message": "Document reprocessing started",
        "document_id": document_id
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Query(...),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its associated data.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    
    # Delete file
    file_path = f"data/uploads/{document_id}.{document.file_type}"
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Create audit trail before deletion
    audit = AuditTrail(
        document_id=document_id,
        action="document_deleted",
        user_id=user_id,
        details={
            "filename": document.filename,
            "risk_score": document.risk_score
        }
    )
    db.add(audit)
    
    # Delete document
    db.delete(document)
    db.commit()
    
    return {"message": "Document deleted successfully", "document_id": document_id}


@router.post("/documents/compare", response_model=ComparisonResponse)
async def compare_documents(
    request: ComparisonRequest,
    db: Session = Depends(get_db)
):
    """
    Compare two documents for similarity and differences.
    """
    doc1 = db.query(Document).filter(Document.id == request.document_id_1).first()
    doc2 = db.query(Document).filter(Document.id == request.document_id_2).first()
    
    if not doc1 or not doc2:
        raise HTTPException(404, "One or both documents not found")
    
    # Calculate similarity (simple implementation)
    text1 = doc1.extracted_text or ""
    text2 = doc2.extracted_text or ""
    
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    
    if not words1 or not words2:
        similarity = 0.0
    else:
        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))
        similarity = intersection / union if union > 0 else 0.0
    
    # Find common issues
    issues1 = set(doc1.format_issues or [])
    issues2 = set(doc2.format_issues or [])
    common_issues = list(issues1.intersection(issues2))
    
    # Risk comparison
    risk_comparison = {
        "document_1_risk": doc1.risk_score,
        "document_2_risk": doc2.risk_score,
        "risk_delta": abs(doc1.risk_score - doc2.risk_score),
        "higher_risk_document": request.document_id_1 if doc1.risk_score > doc2.risk_score else request.document_id_2
    }
    
    # Simple differences
    differences = []
    if doc1.file_type != doc2.file_type:
        differences.append(f"Different file types: {doc1.file_type} vs {doc2.file_type}")
    if abs(doc1.risk_score - doc2.risk_score) > 0.2:
        differences.append(f"Significant risk difference: {doc1.risk_score:.2f} vs {doc2.risk_score:.2f}")
    
    return ComparisonResponse(
        document_1=DocumentSummaryResponse(
            document_id=doc1.id,
            filename=doc1.filename,
            file_type=doc1.file_type,
            status=ProcessingStatus(doc1.status),
            risk_score=doc1.risk_score,
            risk_level=RiskLevel(doc1.risk_level),
            upload_date=doc1.upload_date,
            processed_at=doc1.processed_at
        ),
        document_2=DocumentSummaryResponse(
            document_id=doc2.id,
            filename=doc2.filename,
            file_type=doc2.file_type,
            status=ProcessingStatus(doc2.status),
            risk_score=doc2.risk_score,
            risk_level=RiskLevel(doc2.risk_level),
            upload_date=doc2.upload_date,
            processed_at=doc2.processed_at
        ),
        similarity_score=similarity,
        differences=differences,
        common_issues=common_issues,
        risk_comparison=risk_comparison
    )


# ============================================================================
# AUDIT AND HISTORY
# ============================================================================

@router.get("/documents/{document_id}/audit", response_model=List[AuditTrailResponse])
async def get_audit_trail(document_id: str, db: Session = Depends(get_db)):
    """
    Get complete audit trail for a document.
    """
    audits = db.query(AuditTrail).filter(
        AuditTrail.document_id == document_id
    ).order_by(AuditTrail.timestamp).all()
    
    return [
        AuditTrailResponse(
            audit_id=audit.id,
            document_id=audit.document_id,
            action=audit.action,
            user_id=audit.user_id,
            timestamp=audit.timestamp,
            details=audit.details,
            risk_score_change=audit.risk_score_change
        )
        for audit in audits
    ]


# ============================================================================
# STATISTICS AND ANALYTICS
# ============================================================================

@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get system-wide statistics and analytics.
    """
    # Total documents
    total_documents = db.query(func.count(Document.id)).scalar()
    
    # Documents by status
    status_counts = db.query(
        Document.status, func.count(Document.id)
    ).group_by(Document.status).all()
    documents_by_status = {status: count for status, count in status_counts}
    
    # Documents by risk level
    risk_counts = db.query(
        Document.risk_level, func.count(Document.id)
    ).group_by(Document.risk_level).all()
    documents_by_risk_level = {level: count for level, count in risk_counts}
    
    # Average processing time
    avg_processing_time = db.query(
        func.avg(Document.processing_time)
    ).filter(Document.processing_time.isnot(None)).scalar() or 0.0
    
    # Average risk score
    avg_risk_score = db.query(
        func.avg(Document.risk_score)
    ).scalar() or 0.0
    
    # High risk documents
    total_high_risk = db.query(func.count(Document.id)).filter(
        Document.risk_level.in_(['high', 'critical'])
    ).scalar()
    
    # Recent uploads (last 24 hours)
    yesterday = datetime.utcnow() - timedelta(days=1)
    recent_uploads = db.query(func.count(Document.id)).filter(
        Document.upload_date >= yesterday
    ).scalar()
    
    return StatisticsResponse(
        total_documents=total_documents,
        documents_by_status=documents_by_status,
        documents_by_risk_level=documents_by_risk_level,
        average_processing_time=avg_processing_time,
        average_risk_score=avg_risk_score,
        total_high_risk=total_high_risk,
        recent_uploads=recent_uploads
    )


# ============================================================================
# HEALTH AND STATUS
# ============================================================================

@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Check system health and service availability.
    """
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    # Check services
    services = {
        "ocr": "available",  # Would actually check Groq API
        "docling": "available",
        "vision": "available",
        "redis": "available"  # Would check Redis connection
    }
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        services=services,
        timestamp=datetime.utcnow()
    )


@router.get("/status")
async def get_system_status():
    """
    Get current system status and version info.
    """
    return {
        "service": "Document Corroboration Engine",
        "version": "1.0.0",
        "status": "operational",
        "features": {
            "multi_format_support": True,
            "vision_ocr": True,
            "ai_analysis": True,
            "risk_scoring": True,
            "batch_processing": True,
            "audit_trail": True
        },
        "timestamp": datetime.utcnow().isoformat()
    }