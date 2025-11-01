"""
Local file system connector for regulatory documents.
"""
import hashlib
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, BinaryIO

from .base import (
    BaseConnector, DocumentMetadata, DocumentContent, DocumentType,
    DocumentSource, DocumentNotFoundError
)


class LocalConnector(BaseConnector):
    """Connector for local file system storage of regulatory documents."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the local connector.
        
        Args:
            config: Configuration dictionary with:
                - base_path: Base directory for document storage
                - source: Source identifier (e.g., 'HKMA', 'MAS', 'FINMA')
        """
        super().__init__(config)
        self.base_path = Path(self.config.get("base_path", "regulatory-docs"))
        self.source = DocumentSource(self.config.get("source", "LOCAL"))
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    @property
    def source(self) -> DocumentSource:
        return self._source
    
    @source.setter
    def source(self, value: Union[DocumentSource, str]):
        """Set the document source with validation."""
        self._source = value if isinstance(value, DocumentSource) else DocumentSource(value)
    
    async def list_documents(self, **filters) -> List[DocumentMetadata]:
        """List available documents in the local directory."""
        documents = []
        
        # Find all files in the source directory
        source_dir = self.base_path / self.source.value.lower()
        if not source_dir.exists():
            return []
            
        for file_path in source_dir.rglob("*"):
            if file_path.is_file() and not file_path.name.startswith('.'):
                try:
                    metadata = self._extract_metadata(file_path)
                    if self._matches_filters(metadata, filters):
                        documents.append(metadata)
                except Exception as e:
                    # Skip files that can't be processed
                    continue
        
        return documents
    
    async def get_document(self, document_id: str) -> DocumentContent:
        """Get a document by ID from the local file system."""
        # Look for the file in the source directory
        source_dir = self.base_path / self.source.value.lower()
        file_path = source_dir / document_id
        
        # If not found by exact ID, try to find by partial match
        if not file_path.exists():
            matches = list(source_dir.glob(f"*{document_id}*"))
            if not matches:
                raise DocumentNotFoundError(f"Document {document_id} not found in {source_dir}")
            file_path = matches[0]  # Take the first match
        
        # Read file content
        try:
            is_binary = self._is_binary_file(file_path)
            mode = 'rb' if is_binary else 'r'
            encoding = None if is_binary else 'utf-8'
            
            with open(file_path, mode, encoding=encoding) as f:
                content = f.read()
                
            metadata = self._extract_metadata(file_path)
            
            return DocumentContent(
                metadata=metadata,
                content=content,
                is_binary=is_binary
            )
        except Exception as e:
            raise DocumentNotFoundError(f"Error reading document {document_id}: {str(e)}")
    
    def _extract_metadata(self, file_path: Path) -> DocumentMetadata:
        """Extract metadata from a file path."""
        file_name = file_path.name
        file_size = file_path.stat().st_size
        file_type = file_path.suffix[1:].upper() if file_path.suffix else 'UNKNOWN'
        
        # Try to extract document type from file name
        doc_type = self._infer_document_type(file_name)
        
        # Try to extract date from file name (common pattern: YYYYMMDD or YYYY-MM-DD)
        doc_date = self._extract_date_from_filename(file_name)
        
        # Generate a checksum of the file
        checksum = self._calculate_checksum(file_path)
        
        return DocumentMetadata(
            source=self.source,
            document_id=file_name,
            title=file_path.stem.replace('_', ' ').title(),
            document_type=doc_type,
            jurisdiction=self.source.value,  # Default to source as jurisdiction
            regulator=self.source.value,
            document_date=doc_date,
            file_name=file_name,
            file_type=file_type,
            file_size=file_size,
            checksum=checksum,
            metadata={
                "path": str(file_path.relative_to(self.base_path)),
                "last_modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            }
        )
    
    def _infer_document_type(self, file_name: str) -> DocumentType:
        """Infer document type from file name."""
        file_lower = file_name.lower()
        
        if any(term in file_lower for term in ['regulation', 'regs', 'reg']):
            return DocumentType.REGULATION
        elif any(term in file_lower for term in ['guideline', 'guidance']):
            return DocumentType.GUIDELINE
        elif 'circular' in file_lower:
            return DocumentType.CIRCULAR
        elif any(term in file_lower for term in ['notice', 'announcement']):
            return DocumentType.NOTICE
        elif 'rule' in file_lower:
            return DocumentType.RULE
        else:
            return DocumentType.OTHER
    
    def _extract_date_from_filename(self, file_name: str) -> Optional[datetime]:
        """Extract date from file name if it follows a common pattern."""
        import re
        from datetime import datetime
        
        # Try YYYYMMDD pattern
        match = re.search(r'(\d{4})(\d{2})(\d{2})', file_name)
        if match:
            try:
                return datetime.strptime(match.group(0), '%Y%m%d')
            except ValueError:
                pass
        
        # Try YYYY-MM-DD pattern
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})', file_name)
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
        # List of common text file extensions
        text_extensions = {
            '.txt', '.md', '.markdown', '.rst',
            '.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp',
            '.html', '.css', '.scss', '.sass', '.less',
            '.json', '.yaml', '.yml', '.toml', '.ini', '.cfg', '.conf',
            '.csv', '.tsv', '.xml', '.svg',
            '.sh', '.bash', '.zsh', '.fish',
            '.sql', '.graphql', '.gql'
        }
        
        # Check file extension first
        if file_path.suffix.lower() in text_extensions:
            return False
            
        # For files without extension or with unknown extensions, check content
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                # If we find a null byte, it's likely a binary file
                if b'\0' in chunk:
                    return True
                # Try to decode as text
                try:
                    chunk.decode('utf-8')
                    return False
                except UnicodeDecodeError:
                    return True
        except Exception:
            return True
    
    def _matches_filters(self, metadata: DocumentMetadata, filters: Dict[str, Any]) -> bool:
        """Check if document metadata matches all filters."""
        for key, value in filters.items():
            if not hasattr(metadata, key):
                continue
                
            attr_value = getattr(metadata, key)
            
            # Handle date range filters (e.g., document_date_after, document_date_before)
            if key.endswith('_after') and isinstance(attr_value, datetime):
                if attr_value <= value:
                    return False
            elif key.endswith('_before') and isinstance(attr_value, datetime):
                if attr_value >= value:
                    return False
            # Handle exact match
            elif attr_value != value:
                return False
                
        return True
