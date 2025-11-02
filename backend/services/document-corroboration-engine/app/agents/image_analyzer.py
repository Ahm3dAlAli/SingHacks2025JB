from typing import Dict, Any, List
from app.services.vision_service import AdvancedVisionService
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class ImageAnalyzerAgent:
    def __init__(self):
        self.vision_service = AdvancedVisionService()
        logger.info("Image Analyzer Agent initialized with Advanced Vision")
    
    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Comprehensive image analysis using Groq Vision"""
        try:
            logger.info(f"Starting advanced image analysis: {image_path}")
            
            # Full vision analysis using Groq
            vision_analysis = self.vision_service.comprehensive_image_analysis(image_path)
            
            # Calculate risk factors based on analysis
            risk_factors = self._calculate_image_risk_factors(vision_analysis)
            
            # Overall image trust score
            trust_score = vision_analysis.get("overall_trust_score", 0.5)
            
            return {
                **vision_analysis,
                "risk_factors": risk_factors,
                "overall_trust_score": trust_score,
                "trust_rating": self._get_trust_rating(trust_score),
                "recommendations": self._generate_recommendations(vision_analysis, risk_factors)
            }
            
        except Exception as e:
            logger.error(f"Image analysis failed: {str(e)}")
            return self._get_fallback_analysis()
    
    def _calculate_image_risk_factors(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk factors from advanced vision analysis"""
        risk_factors = {}
        
        # Authenticity risks
        authenticity = analysis.get("authenticity_analysis", {})
        authenticity_conf = authenticity.get("confidence", 0.5)
        risk_factors["authenticity_risk"] = 1.0 - authenticity_conf
        
        # Tampering risks
        tampering = analysis.get("tampering_analysis", {})
        tampering_conf = tampering.get("tampering_confidence", 0.0)
        risk_factors["tampering_risk"] = tampering_conf
        
        # Quality risks
        quality = analysis.get("quality_analysis", {})
        quality_score = quality.get("quality_score", 0.5)
        risk_factors["quality_risk"] = 1.0 - quality_score
        
        # Content risks
        content = analysis.get("content_analysis", {})
        if content.get("content_consistency") == "inconsistent":
            risk_factors["content_risk"] = 0.3
        
        # Calculate overall risk
        total_risk = sum(risk_factors.values())
        risk_factors["overall_risk"] = min(total_risk, 1.0)
        
        return risk_factors
    
    def _get_trust_rating(self, score: float) -> str:
        """Convert trust score to human-readable rating"""
        if score >= 0.8:
            return "high_trust"
        elif score >= 0.6:
            return "moderate_trust"
        elif score >= 0.4:
            return "low_trust"
        else:
            return "untrustworthy"
    
    def _generate_recommendations(self, analysis: Dict[str, Any], risk_factors: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on analysis results"""
        recommendations = []
        
        # Authenticity recommendations
        authenticity = analysis.get("authenticity_analysis", {})
        if authenticity.get("confidence", 0.5) < 0.6:
            recommendations.append("Low authenticity confidence - verify document source")
        
        # Tampering recommendations
        tampering = analysis.get("tampering_analysis", {})
        if tampering.get("tampering_confidence", 0.0) > 0.3:
            recommendations.append("Potential tampering detected - manual review recommended")
        
        # Quality recommendations
        quality = analysis.get("quality_analysis", {})
        if quality.get("quality_score", 0.5) < 0.6:
            recommendations.append("Poor image quality - consider requesting a better version")
        
        # Content recommendations
        content = analysis.get("content_analysis", {})
        if content.get("content_consistency") == "inconsistent":
            recommendations.append("Content inconsistencies detected - review carefully")
        
        if not recommendations:
            recommendations.append("No significant issues detected - document appears genuine")
        
        return recommendations
    
    def _get_fallback_analysis(self) -> Dict[str, Any]:
        """Fallback analysis when image analysis fails"""
        return {
            "authenticity_analysis": {"error": "analysis_failed", "confidence": 0.5},
            "content_analysis": {"error": "analysis_failed"},
            "quality_analysis": {"error": "analysis_failed", "quality_score": 0.5},
            "tampering_analysis": {"error": "analysis_failed", "tampering_confidence": 0.0},
            "risk_factors": {"overall_risk": 0.5},
            "overall_trust_score": 0.5,
            "trust_rating": "unknown",
            "recommendations": ["Image analysis failed - manual review required"]
        }