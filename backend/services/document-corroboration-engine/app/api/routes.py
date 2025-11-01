from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import os
import uuid

from app.database.connection import get_db
from app.database.models import Document, AuditTrail
from app.api.models import (
    DocumentUploadRequest, DocumentUploadResponse, DocumentAnalysisResponse,
    AuditTrailResponse, HealthResponse
)
from app.workflows.workflow import process_document_workflow
from app.utils.logger import setup_logger

router = APIRouter()
logger = setup_logger(__name__)

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    upload_request: DocumentUploadRequest = Depends(),
    db: Session = Depends(get_db)
):
    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.txt', '.jpg', '.jpeg', '.png']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(400, f"File type {file_extension} not supported")
        
        # Generate document ID
        document_id = str(uuid.uuid4())
        
        # Save file
        upload_dir = "data/uploads"
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, f"{document_id}{file_extension}")
        
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Create document record
        db_document = Document(
            id=document_id,
            filename=file.filename,
            file_type=file_extension[1:],  # Remove dot
            file_size=len(content),
            uploader_id=upload_request.uploader_id,
            status="pending"
        )
        db.add(db_document)
        
        # Create audit trail
        audit = AuditTrail(
            document_id=document_id,
            action="document_uploaded",
            user_id=upload_request.uploader_id,
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
        
        return DocumentUploadResponse(
            document_id=document_id,
            status="processing",
            message="Document uploaded and processing started",
            estimated_processing_time=30
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(500, f"Upload failed: {str(e)}")

@router.get("/documents/{document_id}", response_model=DocumentAnalysisResponse)
async def get_document_analysis(document_id: str, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(404, "Document not found")
    
    return DocumentAnalysisResponse(
        document_id=document.id,
        filename=document.filename,
        status=document.status,
        extracted_text=document.extracted_text,
        structure_analysis=document.structure_analysis,
        format_issues=document.format_issues or [],
        spelling_errors=document.spelling_errors or [],
        missing_sections=document.missing_sections or [],
        image_analysis=document.image_analysis,
        risk_score=document.risk_score,
        risk_level=document.risk_level,
        processing_time=document.processing_time,
        processed_at=document.processed_at
    )

@router.get("/documents/{document_id}/audit", response_model=list[AuditTrailResponse])
async def get_audit_trail(document_id: str, db: Session = Depends(get_db)):
    audits = db.query(AuditTrail).filter(AuditTrail.document_id == document_id).order_by(AuditTrail.timestamp).all()
    
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

@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    try:
        # Test database connection
        db.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return HealthResponse(
        status="healthy",
        database=db_status,
        services={
            "ocr": "available",
            "docling": "available",
            "vision": "available"
        }
    )