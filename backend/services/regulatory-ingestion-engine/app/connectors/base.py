"""
Base connector interface for regulatory document sources.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, BinaryIO
from urllib.parse import urlparse

from pydantic import BaseModel, HttpUrl


class DocumentType(str, Enum):
    """Types of regulatory documents."""
    REGULATION = "REGULATION"
    GUIDELINE = "GUIDELINE"
    CIRCULAR = "CIRCULAR"
    NOTICE = "NOTICE"
    RULE = "RULE"
    OTHER = "OTHER"


class DocumentSource(str, Enum):
    """Source of the document."""
    HKMA = "HKMA"  # Hong Kong Monetary Authority
    MAS = "MAS"    # Monetary Authority of Singapore
    FINMA = "FINMA"  # Swiss Financial Market Supervisory Authority
    LOCAL = "LOCAL"  # Local file system


class DocumentMetadata(BaseModel):
    """Metadata for a regulatory document."""
    source: DocumentSource
    document_id: str
    title: str
    document_type: DocumentType
    jurisdiction: str
    regulator: str
    document_date: Optional[datetime] = None
    effective_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    url: Optional[HttpUrl] = None
    file_name: Optional[str] = None
    file_type: Optional[str] = None
    file_size: Optional[int] = None
    checksum: Optional[str] = None
    metadata: Dict[str, Any] = {}


class DocumentContent(BaseModel):
    """Content of a regulatory document."""
    metadata: DocumentMetadata
    content: Union[str, bytes]
    is_binary: bool = False


class BaseConnector(ABC):
    """Base class for all regulatory document connectors."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the connector with configuration."""
        self.config = config or {}
        self.local_fallback_path = self.config.get("local_fallback_path", "regulatory-docs")
    
    @abstractmethod
    async def list_documents(self, **filters) -> List[DocumentMetadata]:
        """List available documents with optional filtering.
        
        Args:
            **filters: Filters to apply (e.g., date ranges, document types)
            
        Returns:
            List of document metadata
        """
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> DocumentContent:
        """Retrieve a document by ID.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            Document content and metadata
            
        Raises:
            DocumentNotFoundError: If the document is not found
            ConnectionError: If there's a connection error
        """
        pass
    
    async def get_document_with_fallback(self, document_id: str) -> DocumentContent:
        """Get a document with fallback to local storage.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            Document content and metadata from either the source or local fallback
            
        Raises:
            DocumentNotFoundError: If the document is not found in either source
        """
        try:
            return await self.get_document(document_id)
        except (ConnectionError, TimeoutError) as e:
            # Fall back to local storage
            local_connector = LocalConnector({
                "base_path": self.local_fallback_path,
                "source": self.source
            })
            return await local_connector.get_document(document_id)
    
    @property
    @abstractmethod
    def source(self) -> DocumentSource:
        """Get the source identifier for this connector."""
        pass


class DocumentNotFoundError(Exception):
    """Raised when a document is not found."""
    pass


class ConnectionError(Exception):
    """Raised when there's a connection error with the source."""
    pass
