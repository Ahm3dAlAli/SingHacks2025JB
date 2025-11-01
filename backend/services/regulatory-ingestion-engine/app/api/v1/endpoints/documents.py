"""
API endpoints for document management.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.connectors.simple_connector import SimpleConnector
from app.connectors.base import DocumentMetadata, DocumentContent
from app.core.config import settings

router = APIRouter()

# Initialize the connector
connector = SimpleConnector({
    "base_path": "/Users/smitshah/Documents/singhack/SingHacks2025JB/regulatory-docs"
})

@router.get("/documents", response_model=List[DocumentMetadata])
async def list_documents(
    source: Optional[str] = Query(None, description="Filter by source (e.g., hkma, mas, finma, bafin)"),
    doc_type: Optional[str] = Query(None, description="Filter by document type (e.g., REGULATION, GUIDELINE, CIRCULAR)"),
    after_date: Optional[datetime] = Query(None, description="Filter documents after this date"),
    before_date: Optional[datetime] = Query(None, description="Filter documents before this date"),
    limit: int = Query(100, description="Maximum number of documents to return")
):
    """
    List all available regulatory documents with optional filtering.
    """
    filters = {}
    if source:
        filters["source"] = source.upper()
    if doc_type:
        filters["document_type"] = doc_type.upper()
    if after_date:
        filters["document_date_after"] = after_date
    if before_date:
        filters["document_date_before"] = before_date
    
    try:
        documents = await connector.list_documents(**filters)
        return documents[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents/{document_id}", response_model=DocumentContent)
async def get_document(document_id: str):
    """
    Get a specific document by ID.
    Document ID format: {source}/{filename} (e.g., hkma/sample.pdf)
    """
    try:
        return await connector.get_document(document_id)
    except Exception as e:
        if "not found" in str(e).lower():
            raise HTTPException(status_code=404, detail="Document not found")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources")
async def list_sources():
    """
    List all available regulatory sources.
    """
    try:
        # Get a sample document from each source to show source info
        sources = {}
        documents = await connector.list_documents()
        
        for doc in documents:
            source = doc.source.lower()
            if source not in sources:
                sources[source] = {
                    "name": doc.regulator,
                    "jurisdiction": doc.jurisdiction,
                    "document_count": 0,
                    "document_types": set(),
                    "last_updated": None
                }
            
            sources[source]["document_count"] += 1
            sources[source]["document_types"].add(doc.document_type.value)
            
            # Track the most recent update
            if hasattr(doc, 'metadata') and 'last_modified' in doc.metadata:
                last_modified = datetime.fromisoformat(doc.metadata['last_modified'])
                if (sources[source]["last_updated"] is None or 
                    last_modified > sources[source]["last_updated"]):
                    sources[source]["last_updated"] = last_modified.isoformat()
        
        # Convert sets to lists for JSON serialization
        for source in sources.values():
            source["document_types"] = list(source["document_types"])
            
        return {"sources": sources}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
