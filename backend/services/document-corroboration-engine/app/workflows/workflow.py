from celery import Celery
from typing import Dict, Any
import os
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.database.models import Document, AuditTrail
from app.agents.document_processor import DocumentProcessorAgent
from app.agents.format_validator import FormatValidatorAgent
from app.agents.image_analyzer import ImageAnalyzerAgent
from app.agents.risk_scorer import RiskScorerAgent
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

# Celery configuration
celery_app = Celery('document_workflows')
celery_app.conf.broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
celery_app.conf.result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
)

@celery_app.task(name='process_document_workflow')
def process_document_workflow(document_id: str, file_path: str):
    """Main document processing workflow"""
    try:
        logger.info(f"Starting workflow for document {document_id}")
        
        # Initialize agents
        doc_processor = DocumentProcessorAgent()
        format_validator = FormatValidatorAgent()
        image_analyzer = ImageAnalyzerAgent()
        risk_scorer = RiskScorerAgent()
        
        # Update document status
        db = next(get_db())
        document = db.query(Document).filter(Document.id == document_id).first()
        if not document:
            logger.error(f"Document {document_id} not found")
            return
        
        document.status = "processing"
        db.commit()
        
        # Step 1: Document Processing
        logger.info("Step 1: Document Processing")
        document_analysis = doc_processor.process_document(file_path)
        
        # Step 2: Format Validation
        logger.info("Step 2: Format Validation")
        extracted_text = document_analysis.get("extracted_text", "")
        structure_analysis = document_analysis.get("structure_analysis", {})
        format_validation = format_validator.validate_format(extracted_text, structure_analysis)
        
        # Step 3: Image Analysis (if applicable)
        logger.info("Step 3: Image Analysis")
        file_extension = os.path.splitext(file_path)[1].lower()
        image_analysis = {}
        if file_extension in ['.jpg', '.jpeg', '.png']:
            image_analysis = image_analyzer.analyze_image(file_path)
        
        # Step 4: Risk Scoring
        logger.info("Step 4: Risk Scoring")
        risk_assessment = risk_scorer.calculate_comprehensive_risk(
            document_analysis, format_validation, image_analysis
        )
        
        # Step 5: Update Database
        logger.info("Step 5: Updating Database")
        document.extracted_text = extracted_text
        document.structure_analysis = structure_analysis
        document.format_issues = format_validation.get("basic_checks", {}).get("issues", [])
        document.spelling_errors = []  # Would be populated by spell check
        document.missing_sections = document_analysis.get("missing_sections", [])
        document.image_analysis = image_analysis
        document.risk_score = risk_assessment["overall_risk_score"]
        document.risk_level = risk_assessment["risk_level"]
        document.status = "completed"
        document.processed_at = func.now()
        
        # Create audit trail
        audit = AuditTrail(
            document_id=document_id,
            action="processing_completed",
            user_id="system",
            details={
                "risk_score": document.risk_score,
                "processing_time": 0,  # Would calculate actual time
                "analysis_summary": {
                    "format_score": format_validation.get("overall_format_score"),
                    "authenticity_score": image_analysis.get("overall_trust_score"),
                    "primary_concerns": risk_assessment.get("primary_concerns", [])
                }
            }
        )
        db.add(audit)
        db.commit()
        
        logger.info(f"Workflow completed for document {document_id}")
        
        return {
            "document_id": document_id,
            "status": "completed",
            "risk_score": document.risk_score,
            "risk_level": document.risk_level
        }
        
    except Exception as e:
        logger.error(f"Workflow failed for document {document_id}: {str(e)}")
        
        # Update document status to failed
        try:
            db = next(get_db())
            document = db.query(Document).filter(Document.id == document_id).first()
            if document:
                document.status = "failed"
                
                # Create failure audit trail
                audit = AuditTrail(
                    document_id=document_id,
                    action="processing_failed",
                    user_id="system",
                    details={"error": str(e)}
                )
                db.add(audit)
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update database on error: {str(db_error)}")
        
        raise e

# Additional workflow tasks
@celery_app.task(name='batch_process_documents')
def batch_process_documents(document_ids: list):
    """Batch process multiple documents"""
    results = []
    for doc_id in document_ids:
        try:
            # This would need file path lookup
            result = process_document_workflow.delay(doc_id, "path_to_file")
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to queue document {doc_id}: {str(e)}")
    
    return [result.id for result in results]

@celery_app.task(name='reprocess_document')
def reprocess_document(document_id: str):
    """Reprocess a document (e.g., after template updates)"""
    # Implementation similar to process_document_workflow
    # but with potential for different parameters or validation rules
    pass