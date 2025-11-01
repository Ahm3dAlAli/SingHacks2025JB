from groq import Groq
from typing import Dict, Any, List
import os
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            logger.warning("GROQ_API_KEY not found. Some AI features will be disabled.")
            self.client = None
        else:
            self.client = Groq(api_key=api_key)
            logger.info("Groq client initialized")
    
    def analyze_text_advanced(self, text: str, analysis_type: str) -> Dict[str, Any]:
        """Advanced text analysis using Groq"""
        if not self.client:
            return self._get_fallback_analysis(analysis_type)
        
        try:
            prompts = {
                "risk_assessment": f"""
                Analyze the following document text for compliance and risk indicators.
                Identify potential issues related to money laundering, fraud, or regulatory compliance.
                
                Document Text:
                {text[:4000]}  # Limit text length
                
                Provide analysis in this format:
                - Overall risk level: low/medium/high/critical
                - Key risk factors: list of specific issues found
                - Recommendations: suggested actions
                - Confidence: 0-1 score
                """,
                
                "format_validation": f"""
                Analyze the document structure and formatting for consistency and professionalism.
                Identify formatting issues, inconsistencies, and potential red flags.
                
                Document Text:
                {text[:3000]}
                
                Provide analysis in this format:
                - Formatting issues: list of specific problems
                - Structural problems: missing sections, inconsistent numbering, etc.
                - Professionalism score: 0-1
                - Recommendations: specific improvements needed
                """,
                
                "content_validation": f"""
                Validate the document content for completeness, accuracy, and compliance.
                Check for missing information, contradictory statements, and compliance gaps.
                
                Document Text:
                {text[:4000]}
                
                Provide analysis in this format:
                - Completeness: percentage and missing elements
                - Accuracy issues: contradictions or incorrect information
                - Compliance gaps: regulatory requirements not met
                - Overall validation score: 0-1
                """
            }
            
            if analysis_type not in prompts:
                raise ValueError(f"Unknown analysis type: {analysis_type}")
            
            response = self.client.chat.completions.create(
                model="llama3-70b-8192",  # Using Llama 3 70B model
                messages=[{"role": "user", "content": prompts[analysis_type]}],
                temperature=0.1,
                max_tokens=1000
            )
            
            return self._parse_groq_response(response.choices[0].message.content, analysis_type)
            
        except Exception as e:
            logger.error(f"Groq analysis failed: {str(e)}")
            return self._get_fallback_analysis(analysis_type)
    
    def _parse_groq_response(self, response: str, analysis_type: str) -> Dict[str, Any]:
        """Parse Groq API response"""
        # Simple parsing - in production, use more robust parsing
        lines = response.split('\n')
        result = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('-'):
                key_value = line[1:].strip().split(':', 1)
                if len(key_value) == 2:
                    key = key_value[0].strip().lower().replace(' ', '_')
                    value = key_value[1].strip()
                    result[key] = value
        
        # Add raw response for debugging
        result["raw_response"] = response
        
        return result
    
    def _get_fallback_analysis(self, analysis_type: str) -> Dict[str, Any]:
        """Provide fallback analysis when Groq is unavailable"""
        fallbacks = {
            "risk_assessment": {
                "overall_risk_level": "medium",
                "key_risk_factors": ["AI analysis unavailable - manual review required"],
                "recommendations": ["Please review document manually"],
                "confidence": 0.5
            },
            "format_validation": {
                "formatting_issues": ["AI validation unavailable"],
                "structural_problems": ["Manual structure review required"],
                "professionalism_score": 0.5,
                "recommendations": ["Manual format validation needed"]
            },
            "content_validation": {
                "completeness": "unknown",
                "accuracy_issues": ["AI content validation unavailable"],
                "compliance_gaps": ["Manual compliance check required"],
                "overall_validation_score": 0.5
            }
        }
        
        return fallbacks.get(analysis_type, {"error": "analysis_type_not_supported"})