import base64
from groq import Groq
from PIL import Image
import cv2
import numpy as np
from typing import Dict, Any, List
import os
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class AdvancedVisionService:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not found. Advanced vision features will be disabled.")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
            logger.info("Advanced Vision Service initialized with Groq")
    
    def comprehensive_image_analysis(self, image_path: str) -> Dict[str, Any]:
        """Comprehensive image analysis using Groq Vision"""
        if not self.client:
            return self._get_fallback_analysis()
        
        try:
            logger.info(f"Starting comprehensive image analysis: {image_path}")
            
            # Read and encode image
            with open(image_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Multi-stage analysis using Groq Vision
            authenticity_analysis = self._analyze_authenticity(base64_image)
            content_analysis = self._analyze_content(base64_image)
            quality_analysis = self._analyze_quality(base64_image)
            tampering_analysis = self._analyze_tampering_indicators(base64_image)
            
            # Combine analyses
            combined_analysis = {
                "authenticity_analysis": authenticity_analysis,
                "content_analysis": content_analysis,
                "quality_analysis": quality_analysis,
                "tampering_analysis": tampering_analysis,
                "overall_trust_score": self._calculate_trust_score(
                    authenticity_analysis, 
                    tampering_analysis, 
                    quality_analysis
                )
            }
            
            logger.info("Comprehensive image analysis completed")
            return combined_analysis
            
        except Exception as e:
            logger.error(f"Advanced image analysis failed: {str(e)}")
            return self._get_fallback_analysis()
    
    def _analyze_authenticity(self, base64_image: str) -> Dict[str, Any]:
        """Analyze image authenticity using Groq Vision"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze this image for authenticity indicators. Consider:
                            1. Lighting consistency and shadows
                            2. Perspective and proportions
                            3. Image quality and noise patterns
                            4. Any signs of AI generation or manipulation
                            5. Overall visual coherence
                            
                            Provide analysis in this format:
                            - Authenticity Confidence: 0-100%
                            - Suspicious Indicators: list of potential issues
                            - Overall Assessment: genuine/suspicious/uncertain
                            - Key Findings: brief explanation"""
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
            
            response = self.client.chat.completions.create(
                model="llava-v1.5-7b-4096-preview",
                messages=messages,
                max_tokens=1024,
                temperature=0.1
            )
            
            return self._parse_authenticity_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Authenticity analysis failed: {str(e)}")
            return {"error": "authenticity_analysis_failed", "confidence": 0.5}
    
    def _analyze_content(self, base64_image: str) -> Dict[str, Any]:
        """Analyze image content and context"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Analyze the content of this image. Identify:
                            1. Type of document or image (ID, invoice, contract, etc.)
                            2. Key visual elements and their consistency
                            3. Text presence and layout
                            4. Overall image purpose and context
                            5. Any unusual or noteworthy elements
                            
                            Provide analysis in this format:
                            - Document Type: classification
                            - Primary Content: description
                            - Layout Assessment: professional/casual/irregular
                            - Content Consistency: consistent/inconsistent/mixed
                            - Notable Elements: list of important findings"""
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
            
            response = self.client.chat.completions.create(
                model="llava-v1.5-7b-4096-preview",
                messages=messages,
                max_tokens=1024,
                temperature=0.1
            )
            
            return self._parse_content_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Content analysis failed: {str(e)}")
            return {"error": "content_analysis_failed"}
    
    def _analyze_quality(self, base64_image: str) -> Dict[str, Any]:
        """Analyze image quality and technical aspects"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Assess the technical quality of this image. Evaluate:
                            1. Sharpness and focus
                            2. Lighting and exposure
                            3. Color accuracy and balance
                            4. Noise levels and compression artifacts
                            5. Overall technical quality for document processing
                            
                            Provide analysis in this format:
                            - Quality Score: 0-100%
                            - Technical Issues: list of quality problems
                            - Processing Suitability: excellent/good/fair/poor
                            - Improvement Recommendations: suggestions if needed"""
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
            
            response = self.client.chat.completions.create(
                model="llava-v1.5-7b-4096-preview",
                messages=messages,
                max_tokens=1024,
                temperature=0.1
            )
            
            return self._parse_quality_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Quality analysis failed: {str(e)}")
            return {"error": "quality_analysis_failed", "quality_score": 0.5}
    
    def _analyze_tampering_indicators(self, base64_image: str) -> Dict[str, Any]:
        """Analyze image for tampering indicators"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Look for signs of image manipulation or tampering. Check for:
                            1. Inconsistent lighting or shadows
                            2. Irregular edges or alignment
                            3. Texture inconsistencies
                            4. Copy-paste artifacts
                            5. Unnatural blurring or sharpening
                            6. Metadata inconsistencies (if visible)
                            
                            Provide analysis in this format:
                            - Tampering Confidence: 0-100%
                            - Detected Indicators: list of potential tampering signs
                            - Manipulation Likelihood: low/medium/high
                            - Forensic Notes: technical observations"""
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
            
            response = self.client.chat.completions.create(
                model="llava-v1.5-7b-4096-preview",
                messages=messages,
                max_tokens=1024,
                temperature=0.1
            )
            
            return self._parse_tampering_response(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Tampering analysis failed: {str(e)}")
            return {"error": "tampering_analysis_failed", "tampering_confidence": 0.0}
    
    def _parse_authenticity_response(self, response: str) -> Dict[str, Any]:
        """Parse authenticity analysis response"""
        lines = response.split('\n')
        result = {"confidence": 0.5, "suspicious_indicators": [], "assessment": "uncertain"}
        
        for line in lines:
            line = line.strip().lower()
            if "authenticity confidence:" in line:
                try:
                    confidence_str = line.split(":")[1].strip().replace('%', '')
                    result["confidence"] = float(confidence_str) / 100.0
                except:
                    pass
            elif "suspicious indicators:" in line:
                indicators = line.split(":")[1].strip().split(',')
                result["suspicious_indicators"] = [ind.strip() for ind in indicators if ind.strip()]
            elif "overall assessment:" in line:
                result["assessment"] = line.split(":")[1].strip()
        
        return result
    
    def _parse_content_response(self, response: str) -> Dict[str, Any]:
        """Parse content analysis response"""
        lines = response.split('\n')
        result = {"document_type": "unknown", "layout_assessment": "unknown", "content_consistency": "unknown"}
        
        for line in lines:
            line = line.strip().lower()
            if "document type:" in line:
                result["document_type"] = line.split(":")[1].strip()
            elif "layout assessment:" in line:
                result["layout_assessment"] = line.split(":")[1].strip()
            elif "content consistency:" in line:
                result["content_consistency"] = line.split(":")[1].strip()
        
        return result
    
    def _parse_quality_response(self, response: str) -> Dict[str, Any]:
        """Parse quality analysis response"""
        lines = response.split('\n')
        result = {"quality_score": 0.5, "technical_issues": [], "processing_suitability": "fair"}
        
        for line in lines:
            line = line.strip().lower()
            if "quality score:" in line:
                try:
                    score_str = line.split(":")[1].strip().replace('%', '')
                    result["quality_score"] = float(score_str) / 100.0
                except:
                    pass
            elif "technical issues:" in line:
                issues = line.split(":")[1].strip().split(',')
                result["technical_issues"] = [issue.strip() for issue in issues if issue.strip()]
            elif "processing suitability:" in line:
                result["processing_suitability"] = line.split(":")[1].strip()
        
        return result
    
    def _parse_tampering_response(self, response: str) -> Dict[str, Any]:
        """Parse tampering analysis response"""
        lines = response.split('\n')
        result = {"tampering_confidence": 0.0, "detected_indicators": [], "manipulation_likelihood": "low"}
        
        for line in lines:
            line = line.strip().lower()
            if "tampering confidence:" in line:
                try:
                    confidence_str = line.split(":")[1].strip().replace('%', '')
                    result["tampering_confidence"] = float(confidence_str) / 100.0
                except:
                    pass
            elif "detected indicators:" in line:
                indicators = line.split(":")[1].strip().split(',')
                result["detected_indicators"] = [ind.strip() for ind in indicators if ind.strip()]
            elif "manipulation likelihood:" in line:
                result["manipulation_likelihood"] = line.split(":")[1].strip()
        
        return result
    
    def _calculate_trust_score(self, authenticity: Dict, tampering: Dict, quality: Dict) -> float:
        """Calculate overall trust score from multiple analyses"""
        authenticity_score = authenticity.get("confidence", 0.5)
        tampering_risk = tampering.get("tampering_confidence", 0.0)
        quality_score = quality.get("quality_score", 0.5)
        
        # Trust score formula
        trust_score = (
            authenticity_score * 0.4 +
            (1 - tampering_risk) * 0.4 +
            quality_score * 0.2
        )
        
        return max(0.0, min(1.0, trust_score))
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback when advanced analysis is unavailable"""
        return {
            "authenticity_analysis": {"error": "service_unavailable", "confidence": 0.5},
            "content_analysis": {"error": "service_unavailable"},
            "quality_analysis": {"error": "service_unavailable", "quality_score": 0.5},
            "tampering_analysis": {"error": "service_unavailable", "tampering_confidence": 0.0},
            "overall_trust_score": 0.5
        }