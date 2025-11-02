from typing import Optional, Dict, Any, List
import base64
import io
from pathlib import Path
from PIL import Image
import httpx
from pydantic import BaseModel, Field

class VisionOCRResult(BaseModel):
    """Result from Vision OCR processing"""
    text: str
    confidence: float
    language: str
    page_count: int
    metadata: Dict[str, Any] = Field(default_factory=dict)

class GroqVisionOCRService:
    """Service for performing OCR using Groq's Vision API"""
    
    def __init__(self, api_key: str, model: str = "llava-3.1-8b"):
        """Initialize the Groq Vision OCR service.
        
        Args:
            api_key: Groq API key
            model: The Groq model to use (default: "llava-3.1-8b")
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer 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",
            "Content-Type": "application/json"
        }
    
    async def _encode_image_to_base64(self, image_path: str) -> str:
        """Encode an image file to base64.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Base64 encoded string of the image
        """
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    async def extract_text_from_image(self, image_path: str) -> VisionOCRResult:
        """Extract text from an image using Groq's Vision API.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            VisionOCRResult containing the extracted text and metadata
            
        Raises:
            Exception: If the API request fails
        """
        try:
            # Encode the image to base64
            base64_image = await self._encode_image_to_base64(image_path)
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Extract all text from this image."},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 4000
            }
            
            # Make the API request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract the text from the response
                text_content = result['choices'][0]['message']['content']
                
                return VisionOCRResult(
                    text=text_content,
                    confidence=1.0,  # Groq doesn't provide confidence scores
                    language="en",   # Default to English, can be enhanced with language detection
                    page_count=1,    # Single page by default
                    metadata={
                        "model": self.model,
                        "response_id": result.get("id", ""),
                        "usage": result.get("usage", {})
                    }
                )
                
        except Exception as e:
            raise Exception(f"Failed to extract text from image: {str(e)}")
    
    async def extract_text_from_pdf(self, pdf_path: str) -> VisionOCRResult:
        """Extract text from a PDF file.
        
        Note: Groq Vision API doesn't natively support PDFs, so we'll convert
        each page to an image first.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            VisionOCRResult containing the extracted text and metadata
        """
        try:
            from pdf2image import convert_from_path
            
            # Convert PDF to images (one per page)
            pages = convert_from_path(pdf_path)
            
            # Process each page
            all_text = []
            for i, page in enumerate(pages):
                # Save page as image
                img_path = f"{pdf_path}_page_{i+1}.jpg"
                page.save(img_path, 'JPEG')
                
                # Process the image
                result = await self.extract_text_from_image(img_path)
                all_text.append(result.text)
                
                # Clean up the temporary image file
                Path(img_path).unlink()
            
            # Combine results from all pages
            combined_text = "\n\n--- Page Break ---\n\n".join(all_text)
            
            return VisionOCRResult(
                text=combined_text,
                confidence=1.0,  # Groq doesn't provide confidence scores
                language="en",   # Default to English
                page_count=len(pages),
                metadata={
                    "model": self.model,
                    "source": "pdf",
                    "page_count": len(pages)
                }
            )
            
        except Exception as e:
            raise Exception(f"Failed to extract text from PDF: {str(e)}")

# Example usage:
# async def main():
#     service = GroqVisionOCRService(api_key="your-groq-api-key")
#     
#     # For images
#     result = await service.extract_text_from_image("path/to/image.jpg")
#     print(result.text)
#     
#     # For PDFs
#     result = await service.extract_text_from_pdf("path/to/document.pdf")
#     print(result.text)

# import asyncio
# asyncio.run(main())
