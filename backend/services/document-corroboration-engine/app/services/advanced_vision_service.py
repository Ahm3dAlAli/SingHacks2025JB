from typing import Optional, Dict, Any, List, Union
import base64
import io
from pathlib import Path
from PIL import Image
import httpx
from pydantic import BaseModel, Field

class VisionAnalysisResult(BaseModel):
    """Result from advanced vision analysis"""
    text: str
    confidence: float
    objects: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AdvancedVisionService:
    """Service for advanced vision analysis using Groq's Vision API"""
    
    def __init__(self, api_key: str, model: str = "llava-3.1-8b"):
        """Initialize the Advanced Vision service.
        
        Args:
            api_key: Groq API key
            model: The Groq model to use (default: "llava-3.1-8b")
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
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
    
    async def analyze_image(
        self, 
        image_path: str, 
        prompt: str = "Analyze this image in detail.",
        max_tokens: int = 2000
    ) -> VisionAnalysisResult:
        """Analyze an image using Groq's Vision API.
        
        Args:
            image_path: Path to the image file
            prompt: The prompt to use for analysis
            max_tokens: Maximum number of tokens to generate
            
        Returns:
            VisionAnalysisResult containing the analysis results
            
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
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": max_tokens
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
                
                # Extract the analysis from the response
                analysis_text = result['choices'][0]['message']['content']
                
                return VisionAnalysisResult(
                    text=analysis_text,
                    confidence=1.0,  # Groq doesn't provide confidence scores
                    objects=[],  # Can be enhanced with object detection
                    metadata={
                        "model": self.model,
                        "response_id": result.get("id", ""),
                        "usage": result.get("usage", {})
                    }
                )
                
        except Exception as e:
            raise Exception(f"Failed to analyze image: {str(e)}")
    
    async def extract_text_from_image(
        self, 
        image_path: str, 
        language: str = "eng"
    ) -> VisionAnalysisResult:
        """Extract text from an image using OCR.
        
        Args:
            image_path: Path to the image file
            language: Language code for OCR (default: "eng" for English)
            
        Returns:
            VisionAnalysisResult containing the extracted text
        """
        prompt = (
            "Extract all text from this image. "
            "Return only the raw text with no additional commentary or formatting. "
            "If no text is found, return an empty string."
        )
        
        result = await self.analyze_image(image_path, prompt=prompt)
        return result
    
    async def analyze_document(
        self, 
        document_path: str, 
        document_type: Optional[str] = None
    ) -> VisionAnalysisResult:
        """Analyze a document (image or PDF) and extract structured information.
        
        Args:
            document_path: Path to the document file
            document_type: Optional document type (e.g., 'invoice', 'contract', 'receipt')
            
        Returns:
            VisionAnalysisResult containing the analysis
        """
        # Determine document type from extension if not provided
        if document_type is None:
            ext = Path(document_path).suffix.lower()
            if ext == '.pdf':
                return await self.analyze_pdf(document_path)
            else:
                return await self.analyze_image(document_path)
        
        # Custom analysis based on document type
        if document_type.lower() in ['invoice', 'bill']:
            prompt = (
                "Analyze this invoice and extract key information including "
                "invoice number, date, total amount, vendor name, and line items. "
                "Return the information in a structured JSON format."
            )
        elif document_type.lower() in ['contract', 'agreement']:
            prompt = (
                "Analyze this contract and extract key information including "
                "parties involved, effective dates, termination clauses, "
                "and key obligations. Return the information in a structured format."
            )
        elif document_type.lower() == 'receipt':
            prompt = (
                "Analyze this receipt and extract key information including "
                "vendor name, date, total amount, payment method, and items purchased. "
                "Return the information in a structured JSON format."
            )
        else:
            prompt = "Analyze this document and extract all relevant information."
        
        return await self.analyze_image(document_path, prompt=prompt)
    
    async def analyze_pdf(self, pdf_path: str) -> VisionAnalysisResult:
        """Analyze a PDF document by processing each page.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Combined analysis of all pages
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
                
                # Analyze the page
                result = await self.analyze_image(img_path)
                all_text.append(result.text)
                
                # Clean up the temporary image file
                Path(img_path).unlink()
            
            # Combine results from all pages
            combined_text = "\n\n--- Page Break ---\n\n".join(all_text)
            
            return VisionAnalysisResult(
                text=combined_text,
                confidence=1.0,  # Groq doesn't provide confidence scores
                metadata={
                    "source": "pdf",
                    "page_count": len(pages)
                }
            )
            
        except Exception as e:
            raise Exception(f"Failed to analyze PDF: {str(e)}")

# Example usage:
# async def main():
#     service = AdvancedVisionService(api_key="your-groq-api-key")
#     
#     # Analyze an image
#     result = await service.analyze_image("path/to/image.jpg")
#     print(result.text)
#     
#     # Extract text from an image
#     text_result = await service.extract_text_from_image("path/to/image.jpg")
#     print(text_result.text)
#     
#     # Analyze a document
#     doc_result = await service.analyze_document("path/to/document.pdf", "invoice")
#     print(doc_result.text)

# import asyncio
# asyncio.run(main())
