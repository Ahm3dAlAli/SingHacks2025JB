"""
Simple connector for regulatory documents with local file system fallback.
This is a simplified version for demo purposes.
"""
import asyncio
import hashlib
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, BinaryIO

from pydantic import HttpUrl

from .base import (
    BaseConnector, DocumentMetadata, DocumentContent, DocumentType,
    DocumentSource, DocumentNotFoundError
)

logger = logging.getLogger(__name__)

class SimpleConnector(BaseConnector):
    """
    A simplified connector that works with the existing directory structure.
    
    Directory structure expected:
    regulatory-docs/
    ├── hkma/     # Hong Kong Monetary Authority
    │   └── *.pdf
    ├── mas/      # Monetary Authority of Singapore
    │   └── *.pdf
    ├── finma/    # Swiss Financial Market Supervisory Authority
    │   └── *.pdf
    └── bafin/    # German Federal Financial Supervisory Authority
        └── *.pdf
    """
    
    # Map directory names to DocumentSource enums
    SOURCE_MAPPING = {
        'hkma': DocumentSource.HKMA,
        'mas': DocumentSource.MAS,
        'finma': DocumentSource.FINMA,
        'bafin': DocumentSource.LOCAL  # Adding BAFIN as a local source
    }
    
    # Map jurisdiction codes to full names
    JURISDICTION_NAMES = {
        'hkma': 'Hong Kong',
        'mas': 'Singapore',
        'finma': 'Switzerland',
        'bafin': 'Germany'
    }
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.base_path = Path(config.get("base_path", "regulatory-docs"))
        if not self.base_path.exists():
            logger.warning(f"Base path {self.base_path} does not exist. Creating directory.")
            self.base_path.mkdir(parents=True, exist_ok=True)
            
    @property
    def source(self) -> str:
        """Return the source identifier for this connector."""
        return "simple_local"
    
    def _discover_sources(self) -> Dict[str, DocumentSource]:
        """Discover available regulatory sources in the base directory."""
        sources = {}
        if not self.base_path.exists():
            logger.warning(f"Base path {self.base_path} does not exist")
            return sources
            
        for item in self.base_path.iterdir():
            if item.is_dir():
                source_name = item.name.lower()
                if source_name in self.SOURCE_MAPPING:
                    sources[source_name] = self.SOURCE_MAPPING[source_name]
                else:
                    logger.info(f"Found unknown source directory: {source_name}")
                    
        logger.info(f"Discovered {len(sources)} regulatory sources: {', '.join(sources.keys())}")
        return sources
    
    async def list_documents(self, **filters) -> List[DocumentMetadata]:
        """List all available documents from all sources."""
        all_docs = []
        
        for source_name, source_type in self.sources.items():
            try:
                source_docs = await self._list_source_documents(source_name, source_type)
                all_docs.extend(source_docs)
            except Exception as e:
                logger.error(f"Error listing documents from {source_name}: {str(e)}")
                continue
                
        return self._apply_filters(all_docs, filters)
    
    async def get_document(self, document_id: str) -> DocumentContent:
        """Get a document by ID."""
        # Document ID format: {source}/{filename}
        if '/' not in document_id:
            raise DocumentNotFoundError(f"Invalid document ID format: {document_id}")
            
        source_name, filename = document_id.split('/', 1)
        if source_name not in self.sources:
            raise DocumentNotFoundError(f"Unknown source: {source_name}")
            
        file_path = self.base_path / source_name / filename
        if not file_path.exists() or not file_path.is_file():
            raise DocumentNotFoundError(f"Document not found: {document_id}")
            
        return await self._read_document_file(file_path, source_name)
    
    async def _list_source_documents(self, source_name: str, source_type: DocumentSource) -> List[DocumentMetadata]:
        """List documents from a specific source."""
        source_dir = self.base_path / source_name
        if not source_dir.exists():
            return []
            
        documents = []
        for file_path in source_dir.glob("*.*"):  # Match all files with extensions
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    metadata = self._extract_metadata(file_path, source_name, source_type)
                    documents.append(metadata)
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {str(e)}")
                    continue
                    
        return documents
    
    def _extract_metadata(self, file_path: Path, source_name: str, source_type: DocumentSource) -> DocumentMetadata:
        """Extract metadata from a file."""
        file_name = file_path.name
        file_size = file_path.stat().st_size
        file_extension = file_path.suffix[1:].upper() if file_path.suffix else 'UNKNOWN'
        
        # Basic metadata extraction
        doc_type = self._infer_document_type(file_name)
        doc_date = self._extract_date_from_filename(file_name)
        
        # Create a document ID that includes the source
        document_id = f"{source_name}/{file_name}"
        
        return DocumentMetadata(
            source=source_type,
            document_id=document_id,
            title=self._clean_filename(file_name),
            document_type=doc_type,
            jurisdiction=self.JURISDICTION_NAMES.get(source_name, source_name.upper()),
            regulator=source_name.upper(),
            document_date=doc_date,
            file_name=file_name,
            file_type=file_extension,
            file_size=file_size,
            checksum=self._calculate_checksum(file_path),
            metadata={
                "path": str(file_path.relative_to(self.base_path)),
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
        )
    
    async def _read_document_file(self, file_path: Path, source_name: str) -> DocumentContent:
        """Read a document file and return its content."""
        is_binary = self._is_binary_file(file_path)
        mode = 'rb' if is_binary else 'r'
        encoding = None if is_binary else 'utf-8'
        
        with open(file_path, mode, encoding=encoding) as f:
            content = f.read()
        
        # Get metadata
        source_type = self.SOURCE_MAPPING.get(source_name, DocumentSource.LOCAL)
        metadata = self._extract_metadata(file_path, source_name, source_type)
        
        return DocumentContent(
            metadata=metadata,
            content=content,
            is_binary=is_binary
        )
    
    def _clean_filename(self, filename: str) -> str:
        """Clean up a filename to create a readable title."""
        # Remove file extension
        name = Path(filename).stem
        # Replace common separators with spaces
        for sep in ['_', '-', '.']:
            name = name.replace(sep, ' ')
        # Title case and clean up
        return ' '.join(part.capitalize() for part in name.split())
    
    def _infer_document_type(self, filename: str) -> DocumentType:
        """Infer document type from filename."""
        filename_lower = filename.lower()
        
        if 'regulation' in filename_lower or 'reg' in filename_lower.split('_'):
            return DocumentType.REGULATION
        elif 'guideline' in filename_lower or 'guidance' in filename_lower:
            return DocumentType.GUIDELINE
        elif 'circular' in filename_lower:
            return DocumentType.CIRCULAR
        elif 'notice' in filename_lower or 'announcement' in filename_lower:
            return DocumentType.NOTICE
        elif 'rule' in filename_lower:
            return DocumentType.RULE
        else:
            return DocumentType.OTHER
    
    def _extract_date_from_filename(self, filename: str) -> Optional[datetime]:
        """Extract date from filename if it follows a common pattern."""
        import re
        
        # Try YYYYMMDD pattern
        match = re.search(r'(\d{4})(\d{2})(\d{2})', filename)
        if match:
            try:
                return datetime.strptime(match.group(0), '%Y%m%d')
            except ValueError:
                pass
        
        # Try YYYY-MM-DD pattern
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', filename)
        if match:
            try:
                return datetime.strptime(match.group(0), '%Y-%m-%d')
            except ValueError:
                pass
                
        return None
    
    def _calculate_checksum(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """Calculate checksum of a file."""
        hash_func = getattr(hashlib, algorithm, hashlib.sha256)()
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_func.update(chunk)
                
        return hash_func.hexdigest()
    
    def _is_binary_file(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        # Consider all non-text extensions as binary for now
        binary_extensions = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip'}
        return file_path.suffix.lower() in binary_extensions
    
    def _apply_filters(self, documents: List[DocumentMetadata], filters: Dict[str, Any]) -> List[DocumentMetadata]:
        """Apply filters to a list of documents."""
        if not filters:
            return documents
            
        filtered = []
        for doc in documents:
            match = True
            for key, value in filters.items():
                if not hasattr(doc, key):
                    continue
                    
                attr_value = getattr(doc, key)
                
                # Handle date range filters
                if key.endswith('_after') and isinstance(attr_value, datetime):
                    if attr_value <= value:
                        match = False
                        break
                elif key.endswith('_before') and isinstance(attr_value, datetime):
                    if attr_value >= value:
                        match = False
                        break
                # Handle exact match
                elif attr_value != value:
                    match = False
                    break
                    
            if match:
                filtered.append(doc)
                
        return filtered
