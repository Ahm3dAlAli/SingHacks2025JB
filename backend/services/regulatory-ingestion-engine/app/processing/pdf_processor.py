"""
PDF document processor implementation.
"""
import fitz  # PyMuPDF
import re
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import logging

from .base_processor import DocumentProcessor, TextExtractor, MetadataExtractor, DocumentParser
from .models import (
    ProcessedDocument, 
    DocumentMetadata, 
    ExtractedContent, 
    DocumentSection, 
    ExtractedTable,
    DocumentType
)

logger = logging.getLogger(__name__)

class PDFTextExtractor(TextExtractor):
    """Extracts text from PDF documents."""
    
    async def extract_text(self, file_path: Path) -> str:
        """Extract text from a PDF file."""
        try:
            doc = fitz.open(file_path)
            text = ""
            for page in doc:
                text += page.get_text() + "\n\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            raise


class PDFMetadataExtractor(MetadataExtractor):
    """Extracts metadata from PDF documents."""
    
    # Common regulatory document patterns
    DOCUMENT_PATTERNS = {
        r'(?i)circular': DocumentType.CIRCULAR,
        r'(?i)guideline': DocumentType.GUIDELINE,
        r'(?i)regulation': DocumentType.REGULATION,
        r'(?i)notice': DocumentType.NOTICE,
        r'(?i)policy': DocumentType.POLICY,
    }
    
    # Common date patterns in filenames
    DATE_PATTERNS = [
        r'(\d{4})[-_](\d{1,2})[-_](\d{1,2})',  # YYYY-MM-DD or YYYY_MM_DD
        r'(\d{1,2})[-_](\d{1,2})[-_](\d{4})',  # DD-MM-YYYY or DD_MM_YYYY
        r'(\d{4})(\d{2})(\d{2})',              # YYYYMMDD
    ]
    
    def __init__(self):
        self.compiled_patterns = {
            doc_type: re.compile(pattern) 
            for pattern, doc_type in self.DOCUMENT_PATTERNS.items()
        }
        self.date_patterns = [re.compile(p) for p in self.DATE_PATTERNS]
    
    async def extract_metadata(self, file_path: Path, content: Optional[str] = None) -> Dict[str, Any]:
        """Extract metadata from a PDF file."""
        try:
            metadata = {
                'file_name': file_path.name,
                'file_extension': file_path.suffix.lower().lstrip('.'),
                'file_size': file_path.stat().st_size,
            }
            
            # Extract basic file metadata
            with fitz.open(file_path) as doc:
                metadata['page_count'] = len(doc)
                
                # Get PDF metadata
                pdf_meta = doc.metadata
                if pdf_meta:
                    if pdf_meta.get('title'):
                        metadata['title'] = pdf_meta['title']
                    if pdf_meta.get('author'):
                        metadata['author'] = pdf_meta['author']
                    if pdf_meta.get('creationDate'):
                        metadata['creation_date'] = pdf_meta['creationDate']
                    if pdf_meta.get('modDate'):
                        metadata['modification_date'] = pdf_meta['modDate']
            
            # Extract metadata from filename
            self._extract_from_filename(file_path.name, metadata)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error extracting metadata from {file_path}: {str(e)}")
            return {}
    
    def _extract_from_filename(self, filename: str, metadata: Dict[str, Any]) -> None:
        """Extract metadata from filename patterns."""
        # Try to determine document type from filename
        for doc_type, pattern in self.DOCUMENT_PATTERNS.items():
            if re.search(doc_type, filename, re.IGNORECASE):
                metadata['document_type'] = pattern
                break
        
        # Try to extract dates from filename
        for pattern in self.date_patterns:
            match = pattern.search(filename)
            if match:
                try:
                    # Try to parse the date
                    if len(match.groups()) >= 3:
                        # Handle different date formats
                        if len(match.group(1)) == 4:  # YYYY-MM-DD
                            year, month, day = match.groups()[:3]
                        else:  # DD-MM-YYYY
                            day, month, year = match.groups()[:3]
                        
                        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
                        metadata['document_date'] = date_str
                        break
                except (IndexError, ValueError):
                    continue
        
        # Extract source/regulator from filename (first part before _ or -)
        source_match = re.match(r'^([^_\-]+)', filename)
        if source_match:
            metadata['source'] = source_match.group(1).upper()
            metadata['regulator'] = metadata.get('source')  # Default regulator to source if not set


class PDFDocumentParser(DocumentParser):
    """Parses PDF documents into structured content."""
    
    async def parse_document(self, file_path: Path, content: Optional[str] = None) -> ExtractedContent:
        """Parse a PDF document into structured content."""
        try:
            if content is None:
                extractor = PDFTextExtractor()
                content = await extractor.extract_text(file_path)
            
            # Basic section detection - can be enhanced with more sophisticated parsing
            sections = self._detect_sections(content)
            tables = await self._extract_tables(file_path)
            
            return ExtractedContent(
                raw_text=content,
                sections=sections,
                tables=tables
            )
        except Exception as e:
            logger.error(f"Error parsing PDF {file_path}: {str(e)}")
            raise
    
    def _detect_sections(self, content: str) -> List[Dict[str, Any]]:
        """Basic section detection based on common heading patterns."""
        sections = []
        lines = content.split('\n')
        current_section = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
                
            # Check for section headers (simple heuristic)
            if line.isupper() and len(line) < 100 and not line.endswith('.'):
                if current_section:
                    sections.append(current_section)
                current_section = {
                    'title': line,
                    'content': '',
                    'level': 1 if len(sections) == 0 else 2,
                    'page_number': 1  # This would need page tracking
                }
            elif current_section:
                current_section['content'] += line + '\n'
        if current_section:
            sections.append(current_section)
            
        return [DocumentSection(**section) for section in sections]
    
    async def _extract_tables(self, file_path: Path) -> List[Dict[str, Any]]:
        """Extract tables from PDF."""
        tables = []
        try:
            doc = fitz.open(file_path)
            for page_num, page in enumerate(doc, 1):
                # This is a simplified example - real implementation would use 
                # more sophisticated table detection
                text = page.get_text("text")
                
                # Simple table detection - look for lines with consistent spacing
                lines = [line for line in text.split('\n') if line.strip()]
                if len(lines) > 2:  # At least header + 1 data row
                    # Check if we have multiple columns (simple check)
                    if any('  ' in line for line in lines[:3]):
                        # Simple table extraction - split on multiple spaces
                        headers = [h.strip() for h in lines[0].split('  ') if h.strip()]
                        if len(headers) > 1:  # At least 2 columns
                            rows = []
                            for line in lines[1:]:
                                cells = [c.strip() for c in line.split('  ') if c.strip()]
                                if len(cells) >= len(headers):
                                    rows.append(cells[:len(headers)])
                            
                            if rows:
                                tables.append({
                                    'title': f"Table on page {page_num}",
                                    'headers': headers,
                                    'rows': rows,
                                    'page_number': page_num
                                })
        except Exception as e:
            logger.warning(f"Error extracting tables from {file_path}: {str(e)}")
        
        return [ExtractedTable(**table) for table in tables]


class PDFProcessor(DocumentProcessor):
    """Process PDF documents using PyMuPDF."""
    
    def __init__(self):
        self.text_extractor = PDFTextExtractor()
        self.metadata_extractor = PDFMetadataExtractor()
        self.document_parser = PDFDocumentParser()
    
    async def process(self, file_path: Path, metadata: Optional[Dict[str, Any]] = None) -> ProcessedDocument:
        """Process a PDF document."""
        if metadata is None:
            metadata = {}
        
        # Extract basic file info
        file_metadata = await self.metadata_extractor.extract_metadata(file_path)
        
        # Extract text content
        text_content = await self.text_extractor.extract_text(file_path)
        
        # Parse document structure
        extracted_content = await self.document_parser.parse_document(file_path, text_content)
        
        # Generate document ID
        doc_id = self._generate_document_id(file_path, file_metadata)
        
        # Create document metadata
        doc_metadata = DocumentMetadata(
            document_id=doc_id,
            **{k: v for k, v in {**file_metadata, **metadata}.items() 
               if k in DocumentMetadata.__annotations__}
        )
        
        # Create processing log
        processing_log = [{"status": "success", "message": "Document processed successfully"}]
        
        return ProcessedDocument(
            metadata=doc_metadata,
            content=extracted_content,
            processing_log=processing_log
        )
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions."""
        return ['pdf']
    
    def _generate_document_id(self, file_path: Path, metadata: Dict[str, Any]) -> str:
        """Generate a unique document ID."""
        # Use source and filename as base
        source = metadata.get('source', 'unknown').lower()
        filename = file_path.stem.lower()
        
        # Create a hash of the file content for uniqueness
        file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()[:8]
        
        return f"{source}/{filename}_{file_hash}"
