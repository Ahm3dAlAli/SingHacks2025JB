import base64
from groq import Groq
from PIL import Image
import os
from typing import Dict, Any
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class GroqVisionOCRService:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not found. Groq Vision OCR will be disabled.")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
            logger.info("Groq Vision OCR service initialized")
    
    def extract_text_from_image(self, image_path: str) -> Dict[str, Any]:
        """Extract text from image using Groq Vision models"""
        if not self.client:
            return self._get_fallback_ocr_result()
        
        try:
            logger.info(f"Extracting text from image using Groq Vision: {image_path}")
            
            # Read and encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Prepare messages for Groq Vision
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Extract all text from this image with high accuracy. 
                            Preserve the exact formatting, line breaks, and structure.
                            Include headers, paragraphs, lists, and any visible text.
                            Return the text as clean, well-structured content."""
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ]
            
            # Call Groq Vision API
            response = self.client.chat.completions.create(
                model="llava-v1.5-7b-4096-preview",  # Groq's vision model
                messages=messages,
                max_tokens=4096,
                temperature=0.1
            )
            
            extracted_text = response.choices[0].message.content
            
            # Analyze text quality and structure
            text_analysis = self._analyze_extracted_text(extracted_text)
            
            result = {
                "extracted_text": extracted_text,
                "confidence_score": text_analysis["confidence_score"],
                "word_count": text_analysis["word_count"],
                "line_count": text_analysis["line_count"],
                "structure_analysis": text_analysis["structure_analysis"],
                "processing_method": "groq_vision",
                "model_used": "llava-v1.5-7b-4096-preview"
            }
            
            logger.info(f"Groq Vision OCR completed. Words extracted: {text_analysis['word_count']}")
            return result
            
        except Exception as e:
            logger.error(f"Groq Vision OCR failed: {str(e)}")
            return self._get_fallback_ocr_result()
    
    def _analyze_extracted_text(self, text: str) -> Dict[str, Any]:
        """Analyze the quality and structure of extracted text"""
        lines = text.split('\n')
        words = text.split()
        
        # Basic quality assessment
        non_empty_lines = [line for line in lines if line.strip()]
        avg_line_length = sum(len(line) for line in non_empty_lines) / len(non_empty_lines) if non_empty_lines else 0
        
        # Structure analysis
        structure_analysis = {
            "has_headers": any(len(line) < 100 and line.strip().isupper() for line in lines),
            "has_lists": any(line.strip().startswith(('-', '*', '•', '1.', '2.')) for line in lines),
            "has_paragraphs": len([p for p in text.split('\n\n') if p.strip()]) > 1,
            "line_length_variation": self._calculate_line_variation(non_empty_lines)
        }
        
        # Confidence score based on text characteristics
        confidence_factors = []
        if len(words) > 10:
            confidence_factors.append(0.3)
        if structure_analysis["has_paragraphs"]:
            confidence_factors.append(0.2)
        if avg_line_length > 20:
            confidence_factors.append(0.2)
        if len(non_empty_lines) > 3:
            confidence_factors.append(0.3)
        
        confidence_score = sum(confidence_factors) if confidence_factors else 0.5
        
        return {
            "confidence_score": min(confidence_score, 1.0),
            "word_count": len(words),
            "line_count": len(non_empty_lines),
            "average_line_length": avg_line_length,
            "structure_analysis": structure_analysis
        }
    
    def _calculate_line_variation(self, lines: list) -> float:
        """Calculate variation in line lengths (indicates structured content)"""
        if len(lines) < 2:
            return 0.0
        
        lengths = [len(line) for line in lines]
        avg_length = sum(lengths) / len(lengths)
        variance = sum((x - avg_length) ** 2 for x in lengths) / len(lengths)
        return variance
    
    def _get_fallback_ocr_result(self) -> Dict[str, Any]:
        """Fallback when Groq Vision is unavailable"""
        return {
            "extracted_text": "",
            "confidence_score": 0.0,
            "word_count": 0,
            "line_count": 0,
            "structure_analysis": {},
            "processing_method": "fallback",
            "error": "Groq Vision unavailable"
        }