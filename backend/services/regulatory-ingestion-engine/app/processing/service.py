"""
Document processing service that coordinates different processors.
"""
import logging
from pathlib import Path
from typing import Dict, List, Optional, Type, Any, Union

from .base_processor import DocumentProcessor
from .models import ProcessedDocument
from .pdf_processor import PDFProcessor

logger = logging.getLogger(__name__)

class DocumentProcessingService:
    """Service for processing documents using appropriate processors."""
    
    def __init__(self):
        self.processors: Dict[str, DocumentProcessor] = {}
        self._register_default_processors()
    
    def _register_default_processors(self) -> None:
        """Register default document processors."""
        self.register_processor(PDFProcessor())
        # Add other default processors here (e.g., DOCX, XLSX, etc.)
    
    def register_processor(self, processor: DocumentProcessor) -> None:
        """Register a document processor.
        
        Args:
            processor: The document processor to register
        """
        for ext in processor.get_supported_extensions():
            self.processors[ext.lower()] = processor
        logger.info(f"Registered processor for extensions: {', '.join(processor.get_supported_extensions())}")
    
    def get_processor(self, file_path: Union[str, Path]) -> Optional[DocumentProcessor]:
        """Get the appropriate processor for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            DocumentProcessor or None if no suitable processor found
        """
        if isinstance(file_path, str):
            file_path = Path(file_path)
        
        ext = file_path.suffix.lower().lstrip('.')
        return self.processors.get(ext)
    
    async def process_document(
        self, 
        file_path: Union[str, Path],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ProcessedDocument:
        """Process a document using the appropriate processor.
        
        Args:
            file_path: Path to the document file
            metadata: Additional metadata to include
            
        Returns:
            ProcessedDocument with extracted content and metadata
            
        Raises:
            ValueError: If no suitable processor is found for the file
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        processor = self.get_processor(file_path)
        if not processor:
            raise ValueError(f"No processor found for file: {file_path}")
        
        logger.info(f"Processing document: {file_path}")
        return await processor.process(file_path, metadata=metadata)
    
    async def process_directory(
        self, 
        directory: Union[str, Path],
        recursive: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ProcessedDocument]:
        """Process all supported documents in a directory.
        
        Args:
            directory: Directory path to process
            recursive: Whether to process subdirectories
            metadata: Additional metadata to include with all documents
            
        Returns:
            List of ProcessedDocument objects
        """
        directory = Path(directory)
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")
        
        processed_docs = []
        
        # Get all supported extensions
        supported_extensions = list(self.processors.keys())
        if not supported_extensions:
            logger.warning("No document processors registered")
            return []
        
        # Build glob pattern for all supported extensions
        glob_pattern = "**/*.{" + ",".join(supported_extensions) + "}"
        
        # Find all matching files
        files = directory.glob(glob_pattern) if recursive else directory.glob("*")
        
        for file_path in files:
            if file_path.is_file():
                try:
                    processed_doc = await self.process_document(file_path, metadata)
                    processed_docs.append(processed_doc)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
        
        return processed_docs


# Global instance for easy import
document_processor = DocumentProcessingService()
