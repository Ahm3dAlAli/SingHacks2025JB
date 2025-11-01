"""
API endpoints for document processing and rule extraction.
"""
import logging
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Depends
from fastapi.responses import JSONResponse

from app.processing.service import document_processor
from app.rule_parsing.service import rule_processor
from app.processing.models import ProcessedDocument
from app.rule_parsing.base import ExtractedRule
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/process/upload")
async def process_uploaded_file(
    file: Optional[UploadFile] = File(None),
    metadata: Optional[Dict[str, Any]] = None,
    extract_rules: bool = Query(False, description="Whether to extract rules from the document")
):
    """
    Process an uploaded document file.
    
    This endpoint accepts a document file, processes it, and optionally extracts rules.
    """
    try:
        # Create a temporary directory for uploads
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            if file is None:
                # Use default file from data/uploads directory if no file is uploaded
                default_file = Path("data/uploads/mas.pdf")
                logger.info(f"No file uploaded, trying to use default file at: {default_file.absolute()}")
                if not default_file.exists():
                    error_msg = f"Default file not found at {default_file.absolute()}. Current working directory: {Path.cwd()}"
                    logger.error(error_msg)
                    raise HTTPException(status_code=404, detail=error_msg)
                file_path = default_file
            else:
                # Process the uploaded file
                file_path = upload_dir / file.filename
                logger.info(f"Processing uploaded file: {file_path}")
                with open(file_path, "wb") as buffer:
                    content = await file.read()
                    if not content:
                        raise ValueError("Uploaded file is empty")
                    buffer.write(content)
        except HTTPException:
            raise
        except Exception as e:
            error_msg = f"Error processing uploaded file: {str(e)}. Type: {type(e).__name__}"
            logger.exception(error_msg)  # This will log the full traceback
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Process the document
        try:
            logger.info(f"Starting to process document: {file_path}")
            processed_doc = await document_processor.process_document(
                file_path=str(file_path.absolute()),
                metadata=metadata or {}
            )
            logger.info("Document processed successfully")
        except Exception as e:
            error_msg = f"Error in document processing: {str(e)}. Type: {type(e).__name__}"
            logger.exception(error_msg)
            raise HTTPException(status_code=500, detail=error_msg)
        
        # Extract rules if requested
        extracted_rules = []
        if extract_rules:
            try:
                logger.info("Starting rule extraction")
                extracted_rules = await rule_processor.extract_rules(processed_doc)
                logger.info(f"Extracted {len(extracted_rules)} rules")
                
                if not hasattr(processed_doc.metadata, 'extra_metadata'):
                    processed_doc.metadata.extra_metadata = {}
                processed_doc.metadata.extra_metadata["extracted_rules"] = [
                    rule.dict() if hasattr(rule, 'dict') else str(rule) for rule in extracted_rules
                ]
                
                # Return both document and rules
                response = {
                    "document": processed_doc,
                    "extracted_rules": [rule.dict() if hasattr(rule, 'dict') else str(rule) 
                                      for rule in extracted_rules]
                }
                logger.info("Rule extraction completed successfully")
                return response
            except Exception as e:
                error_msg = f"Error during rule extraction: {str(e)}. Type: {type(e).__name__}"
                logger.exception(error_msg)
                # Still return the document even if rule extraction fails
                return {
                    "document": processed_doc,
                    "error": error_msg
                }
        
        # Return just the document if rules extraction was not requested
        return processed_doc
        
    except Exception as e:
        logger.error(f"Error processing uploaded file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Clean up the temporary file if it was created from an upload
        if 'file' in locals() and file is not None and 'file_path' in locals() and file_path.exists() and str(file_path).startswith(settings.UPLOAD_DIR):
            try:
                file_path.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {file_path}: {e}")

@router.post("/process/path", response_model=ProcessedDocument)
async def process_file_by_path(
    file_path: str,
    metadata: Optional[Dict[str, Any]] = None,
    extract_rules: bool = Query(False, description="Whether to extract rules from the document")
):
    """
    Process a document from a file path.
    
    The file path should be accessible by the server.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {file_path}")
        
        # Process the document
        processed_doc = await document_processor.process_document(
            file_path=path,
            metadata=metadata or {}
        )
        
        # Extract rules if requested
        if extract_rules:
            rules = await rule_processor.extract_rules(processed_doc)
            processed_doc.metadata.extra_metadata["extracted_rules"] = [
                rule.dict() for rule in rules
            ]
        
        return processed_doc
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def ensure_document_metadata(document: ProcessedDocument) -> ProcessedDocument:
    """Ensure document has all required metadata fields with sensible defaults."""
    # Create a copy of the metadata to avoid modifying the original
    metadata = document.metadata.dict()
    
    # Set default title if missing
    if not metadata.get('title'):
        # Try to get title from document content if available
        if document.content and document.content.sections:
            first_section = document.content.sections[0]
            if first_section.title:
                metadata['title'] = first_section.title
            elif first_section.content:
                # Use first 50 chars of content as title
                metadata['title'] = first_section.content[:50].strip() + '...' \
                    if len(first_section.content) > 50 else first_section.content.strip()
        
        # Fallback to document ID or default
        if not metadata.get('title'):
            metadata['title'] = metadata.get('document_id', 'Untitled Document')
    
    # Set default source if missing
    if not metadata.get('source'):
        metadata['source'] = 'api_upload'
    
    # Set default document type if missing
    if not metadata.get('document_type'):
        metadata['document_type'] = 'REGULATION'
    
    # Create a new document with updated metadata
    return ProcessedDocument(
        metadata=DocumentMetadata(**metadata),
        content=document.content,
        raw_content=document.raw_content,
        processing_log=document.processing_log
    )

@router.post("/extract-rules", response_model=List[Dict[str, Any]])
async def extract_rules_from_document(
    document: ProcessedDocument,
    extractor_names: Optional[List[str]] = Query(None, description="Specific extractors to use")
):
    """
    Extract rules from a processed document.
    
    This endpoint accepts a processed document and returns the extracted rules.
    """
    try:
        # Ensure document has all required metadata
        validated_document = ensure_document_metadata(document)
        
        # Extract rules
        rules = await rule_processor.extract_rules(
            document=validated_document,
            extractor_names=extractor_names
        )
        print(rules)
        return [rule.dict() for rule in rules]
        
    except Exception as e:
        logger.error(f"Error extracting rules: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/process-directory")
async def process_directory(
    directory_path: str,
    recursive: bool = Query(True, description="Whether to process subdirectories"),
    extract_rules: bool = Query(False, description="Whether to extract rules from documents")
):
    """
    Process all supported documents in a directory.
    
    Returns a summary of processed documents and any extracted rules.
    """
    try:
        path = Path(directory_path)
        if not path.exists() or not path.is_dir():
            raise HTTPException(status_code=404, detail=f"Directory not found: {directory_path}")
        
        # Process all documents in the directory
        processed_docs = await document_processor.process_directory(
            directory=path,
            recursive=recursive
        )
        
        # Extract rules if requested
        all_rules = []
        if extract_rules:
            for doc in processed_docs:
                try:
                    rules = await rule_processor.extract_rules(doc)
                    all_rules.extend(rules)
                except Exception as e:
                    logger.error(f"Error extracting rules from {doc.metadata.document_id}: {e}")
        
        # Prepare response
        response = {
            "directory": str(path),
            "documents_processed": len(processed_docs),
            "rules_extracted": len(all_rules),
            "documents": [
                {
                    "document_id": doc.metadata.document_id,
                    "title": doc.metadata.title,
                    "source": doc.metadata.source,
                    "page_count": len(doc.content.sections) if doc.content else 0,
                    "processing_status": "success"
                }
                for doc in processed_docs
            ]
        }
        
        if extract_rules:
            response["rules"] = [rule.dict() for rule in all_rules]
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing directory {directory_path}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/supported-formats")
async def get_supported_formats():
    """Get a list of supported document formats."""
    # This would be dynamically generated based on registered processors
    return {
        "supported_formats": [
            {"extension": "pdf", "description": "Portable Document Format"},
            {"extension": "docx", "description": "Microsoft Word Document"},
            {"extension": "xlsx", "description": "Microsoft Excel Spreadsheet"},
            {"extension": "txt", "description": "Plain Text"},
        ],
        "extractors": [
            {"name": "RegexRuleExtractor", "description": "Extracts rules using pattern matching"}
        ]
    }
