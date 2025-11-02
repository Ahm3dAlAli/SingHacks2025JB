import docling
# Classification functionality is now handled by FigureClassificationPrediction in newer versions
from docling.datamodel.base_models import FigureClassificationPrediction
from typing import Dict, Any, List
import os
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class DoclingService:
    def __init__(self):
        self.pipeline = docling.DoclingPipeline()
        logger.info("Docling pipeline initialized")
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process document using IBM Docling"""
        try:
            logger.info(f"Processing document with Docling: {file_path}")
            
            # Run Docling pipeline
            result = self.pipeline.run(file_path)
            
            # Extract structured information
            docling_result = {
                "extracted_text": result.document.text,
                "document_type": self._classify_document(result.document),
                "sections": self._extract_sections(result.document),
                "tables": self._extract_tables(result.document),
                "images": self._extract_images_info(result.document),
                "metadata": self._extract_metadata(result.document),
                "structure_analysis": self._analyze_structure(result.document)
            }
            
            logger.info("Docling processing completed successfully")
            return docling_result
            
        except Exception as e:
            logger.error(f"Docling processing failed: {str(e)}")
            raise Exception(f"Docling processing failed: {str(e)}")
    
    def _classify_document(self, document) -> str:
        """Classify document type"""
        # Simple classification based on content and structure
        text = document.text.lower()
        
        if "agreement" in text or "contract" in text:
            return "contract"
        elif "invoice" in text or "payment" in text:
            return "invoice"
        elif "report" in text or "analysis" in text:
            return "report"
        else:
            return "general"
    
    def _extract_sections(self, document) -> List[Dict[str, Any]]:
        """Extract document sections"""
        sections = []
        
        # Extract headings and their content
        for i, item in enumerate(document.items):
            if hasattr(item, 'heading') and item.heading:
                section = {
                    "heading": item.heading.text if hasattr(item.heading, 'text') else str(item.heading),
                    "level": getattr(item, 'level', 1),
                    "content": item.text if hasattr(item, 'text') else "",
                    "position": i
                }
                sections.append(section)
        
        return sections
    
    def _extract_tables(self, document) -> List[Dict[str, Any]]:
        """Extract tables from document"""
        tables = []
        
        for item in document.items:
            if hasattr(item, 'table') and item.table:
                table_data = []
                for row in item.table.rows:
                    row_data = [cell.text for cell in row.cells]
                    table_data.append(row_data)
                
                tables.append({
                    "rows": len(table_data),
                    "columns": len(table_data[0]) if table_data else 0,
                    "data": table_data
                })
        
        return tables
    
    def _extract_images_info(self, document) -> List[Dict[str, Any]]:
        """Extract information about images in document"""
        images = []
        
        for item in document.items:
            if hasattr(item, 'figure') and item.figure:
                image_info = {
                    "caption": getattr(item.figure, 'caption', ''),
                    "position": getattr(item, 'position', 0),
                    "size": getattr(item.figure, 'size', {})
                }
                images.append(image_info)
        
        return images
    
    def _extract_metadata(self, document) -> Dict[str, Any]:
        """Extract document metadata"""
        return {
            "page_count": getattr(document, 'page_count', 1),
            "language": getattr(document, 'language', 'en'),
            "creation_date": getattr(document, 'creation_date', None),
            "modification_date": getattr(document, 'modification_date', None)
        }
    
    def _analyze_structure(self, document) -> Dict[str, Any]:
        """Analyze document structure"""
        text = document.text
        lines = text.split('\n')
        
        return {
            "total_pages": getattr(document, 'page_count', 1),
            "total_paragraphs": len([p for p in text.split('\n\n') if p.strip()]),
            "total_words": len(text.split()),
            "total_characters": len(text),
            "average_line_length": sum(len(line) for line in lines) / len(lines) if lines else 0,
            "headings_count": len([item for item in document.items if hasattr(item, 'heading') and item.heading])
        }
