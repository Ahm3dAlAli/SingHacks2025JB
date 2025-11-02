from typing import Dict, Any, List
import os
from app.services.docling_service import DoclingService
from app.services.vision_service import GroqVisionOCRService
from app.services.vision_service import AdvancedVisionService
from app.services.groq_client import GroqClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class DocumentProcessorAgent:
    def __init__(self):
        self.docling_service = DoclingService()
        self.vision_ocr_service = GroqVisionOCRService()
        self.advanced_vision_service = AdvancedVisionService()
        self.groq_client = GroqClient()
        logger.info("Document Processor Agent initialized with Groq Vision")
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Main document processing pipeline with Groq Vision"""
        try:
            logger.info(f"Starting document processing: {file_path}")
            
            file_extension = os.path.splitext(file_path)[1].lower()
            
            # Route processing based on file type
            if file_extension in ['.pdf', '.docx', '.txt']:
                return self._process_structured_document(file_path)
            elif file_extension in ['.jpg', '.jpeg', '.png']:
                return self._process_image_document(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
                
        except Exception as e:
            logger.error(f"Document processing failed: {str(e)}")
            raise
    
    def _process_structured_document(self, file_path: str) -> Dict[str, Any]:
        """Process structured documents (PDF, DOCX, TXT)"""
        # Use Docling for structured documents
        docling_result = self.docling_service.process_document(file_path)
        
        # Enhanced analysis with Groq
        enhanced_analysis = self.groq_client.analyze_text_advanced(
            docling_result["extracted_text"], 
            "risk_assessment"
        )
        
        return {
            **docling_result,
            "enhanced_analysis": enhanced_analysis,
            "processing_method": "docling_with_ai_enhancement"
        }
    
    def _process_image_document(self, file_path: str) -> Dict[str, Any]:
        """Process image-based documents using Groq Vision"""
        # Use Groq Vision OCR for text extraction
        ocr_result = self.vision_ocr_service.extract_text_from_image(file_path)
        
        # Advanced vision analysis
        vision_analysis = self.advanced_vision_service.comprehensive_image_analysis(file_path)
        
        # Enhanced text analysis with Groq
        enhanced_analysis = self.groq_client.analyze_text_advanced(
            ocr_result["extracted_text"],
            "risk_assessment"
        )
        
        return {
            **ocr_result,
            "vision_analysis": vision_analysis,
            "enhanced_analysis": enhanced_analysis,
            "processing_method": "groq_vision_ocr_with_advanced_analysis"
        }