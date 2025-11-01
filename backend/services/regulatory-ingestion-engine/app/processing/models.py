"""
Document processing data models and interfaces.
"""
from enum import Enum
from typing import List, Dict, Any, Optional, Union, BinaryIO
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from pathlib import Path


class DocumentType(str, Enum):
    """Supported document types."""
    REGULATION = "REGULATION"
    GUIDELINE = "GUIDELINE"
    CIRCULAR = "CIRCULAR"
    NOTICE = "NOTICE"
    POLICY = "POLICY"
    OTHER = "OTHER"


class DocumentSection(BaseModel):
    """A section within a document."""
    title: str
    content: str
    level: int = 1
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedTable(BaseModel):
    """A table extracted from a document."""
    title: Optional[str] = None
    headers: List[str] = Field(default_factory=list)
    rows: List[List[str]] = Field(default_factory=list)
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ExtractedContent(BaseModel):
    """Structured content extracted from a document."""
    raw_text: str
    sections: List[DocumentSection] = Field(default_factory=list)
    tables: List[ExtractedTable] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentMetadata(BaseModel):
    """Metadata for a processed document."""
    document_id: str = "unknown_document"
    source: str = "unknown_source"
    document_type: DocumentType = DocumentType.OTHER
    title: Optional[str] = None
    published_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    jurisdiction: Optional[str] = None
    regulator: Optional[str] = None
    file_extension: Optional[str] = None
    file_size: Optional[int] = None
    page_count: Optional[int] = None
    language: str = "en"
    checksum: Optional[str] = None
    source_url: Optional[HttpUrl] = None
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        # Allow creating model with extra fields
        extra = "ignore"
        # Allow populating by field name
        allow_population_by_field_name = True


class ProcessedDocument(BaseModel):
    """A fully processed document with content and metadata."""
    metadata: DocumentMetadata
    content: ExtractedContent
    raw_content: Optional[bytes] = None
    processing_log: List[Dict[str, Any]] = Field(default_factory=list)
