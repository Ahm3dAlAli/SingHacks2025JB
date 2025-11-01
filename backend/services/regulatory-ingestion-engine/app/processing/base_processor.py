"""
Base interfaces for document processors.
"""
from abc import ABC, abstractmethod
from typing import Optional, Union, BinaryIO, List, Dict, Any
from pathlib import Path
from ..processing.models import ProcessedDocument, DocumentMetadata, ExtractedContent


class DocumentProcessor(ABC):
    """Abstract base class for document processors."""
    
    @abstractmethod
    async def process(
        self,
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """
        Process a document file and return structured content.
        
        Args:
            file_path: Path to the document file
            metadata: Additional metadata to include
            
        Returns:
            ProcessedDocument with extracted content and metadata
        """
        pass
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of supported file extensions (without leading .)
        
        Returns:
            List of supported file extensions (e.g., ['pdf', 'docx', 'txt'])
        """
        pass
    
    def can_process(self, file_path: Union[str, Path]) -> bool:
        """
        Check if this processor can handle the given file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if this processor can handle the file
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        return file_path.suffix.lower().lstrip('.') in self.get_supported_extensions()


class TextExtractor(ABC):
    """Interface for text extraction from documents."""
    
    @abstractmethod
    async def extract_text(self, file_path: Union[str, Path]) -> str:
        """Extract raw text from a document."""
        pass


class MetadataExtractor(ABC):
    """Interface for metadata extraction from documents."""
    
    @abstractmethod
    async def extract_metadata(
        self, 
        file_path: Union[str, Path],
        content: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract metadata from a document.
        
        Args:
            file_path: Path to the document
            content: Optional pre-extracted text content
            
        Returns:
            Dictionary of metadata key-value pairs
        """
        pass


class DocumentParser(ABC):
    """Interface for parsing document structure."""
    
    @abstractmethod
    async def parse_document(
        self, 
        file_path: Union[str, Path],
        content: Optional[str] = None
    ) -> ExtractedContent:
        """
        Parse a document into structured content.
        
        Args:
            file_path: Path to the document
            content: Optional pre-extracted text content
            
        Returns:
            ExtractedContent with document structure
        """
        pass
