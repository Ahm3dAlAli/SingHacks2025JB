import logging
import io
from typing import Optional

logger = logging.getLogger(__name__)

def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a PDF file using PyPDF2 or similar library"""
    try:
        # Try to use PyPDF2 if available
        try:
            from PyPDF2 import PdfReader
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
                
        except ImportError:
            logger.warning("PyPDF2 not available, falling back to basic text extraction")
            
            # Fallback: try to read as text if it's not a binary PDF
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()
                
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        return ""  # Return empty string if extraction fails
