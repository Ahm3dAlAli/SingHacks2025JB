from typing import Dict, Any, List
from enum import Enum
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class RiskCategory(str, Enum):
    FORMAT = "format"
    CONTENT = "content"
    AUTHENTICITY = "authenticity"
    COMPLIANCE = "compliance"
    STRUCTURAL = "structural"

class RiskScorerAgent:
    def __init__(self):
        self.risk_weights = {
            RiskCategory.FORMAT: 0.15,
            RiskCategory.CONTENT: 0.25,
            RiskCategory.AUTHENTICITY: 0.30,
            RiskCategory.COMPLIANCE: 0.20,
            RiskCategory.STRUCTURAL: 0.10
        }
        logger.info("Risk Scorer Agent initialized")
    
    def calculate_comprehensive_risk(self, 
                                   document_analysis: Dict[str, Any],
                                   format_validation: Dict[str, Any],
                                   image_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive risk score"""
        try:
            logger.info("Calculating comprehensive risk score")
            
            # Calculate individual risk components
            format_risk = self._calculate_format_risk(format_validation)
            content_risk = self._calculate_content_risk(document_analysis)
            authenticity_risk = self._calculate_authenticity_risk(image_analysis)
            compliance_risk = self._calculate_compliance_risk(document_analysis)
            structural_risk = self._calculate_structural_risk(document_analysis)
            
            # Weighted overall risk
            overall_risk = (
                format_risk * self.risk_weights[RiskCategory.FORMAT] +
                content_risk * self.risk_weights[RiskCategory.CONTENT] +
                authenticity_risk * self.risk_weights[RiskCategory.AUTHENTICITY] +
                compliance_risk * self.risk_weights[RiskCategory.COMPLIANCE] +
                structural_risk * self.risk_weights[RiskCategory.STRUCTURAL]
            )
            
            # Risk factors and evidence
            risk_factors = self._compile_risk_factors(
                format_risk, content_risk, authenticity_risk, 
                compliance_risk, structural_risk
            )
            
            return {
                "overall_risk_score": overall_risk,
                "risk_level": self._get_risk_level(overall_risk),
                "risk_breakdown": {
                    "format_risk": format_risk,
                    "content_risk": content_risk,
                    "authenticity_risk": authenticity_risk,
                    "compliance_risk": compliance_risk,
                    "structural_risk": structural_risk
                },
                "risk_factors": risk_factors,
                "primary_concerns": self._identify_primary_concerns(risk_factors),
                "recommendations": self._generate_risk_recommendations(overall_risk, risk_factors)
            }
            
        except Exception as e:
            logger.error(f"Risk calculation failed: {str(e)}")
            return self._get_fallback_risk_assessment()
    
    def _calculate_format_risk(self, format_validation: Dict[str, Any]) -> float:
        """Calculate format-related risk"""
        format_score = format_validation.get("overall_format_score", 0.5)
        return 1.0 - format_score  # Invert score (lower format quality = higher risk)
    
    def _calculate_content_risk(self, document_analysis: Dict[str, Any]) -> float:
        """Calculate content-related risk"""
        enhanced_analysis = document_analysis.get("enhanced_analysis", {})
        
        # Extract risk level from AI analysis
        risk_level = enhanced_analysis.get("overall_risk_level", "medium").lower()
        
        risk_mapping = {
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8,
            "critical": 0.95
        }
        
        return risk_mapping.get(risk_level, 0.5)
    
    def _calculate_authenticity_risk(self, image_analysis: Dict[str, Any]) -> float:
        """Calculate authenticity-related risk"""
        trust_score = image_analysis.get("overall_trust_score", 0.5)
        return 1.0 - trust_score  # Lower trust = higher risk
    
    def _calculate_compliance_risk(self, document_analysis: Dict[str, Any]) -> float:
        """Calculate compliance-related risk"""
        # Use content validation results
        format_validation = document_analysis.get("format_validation", {})
        content_validation = format_validation.get("content_validation", {})
        
        validation_score = float(content_validation.get("overall_validation_score", 0.5))
        return 1.0 - validation_score
    
    def _calculate_structural_risk(self, document_analysis: Dict[str, Any]) -> float:
        """Calculate structural risk"""
        structure = document_analysis.get("structure_analysis", {})
        missing_sections = document_analysis.get("missing_sections", [])
        
        base_risk = 0.0
        
        # Missing sections increase risk
        base_risk += len(missing_sections) * 0.1
        
        # Poor structure increases risk
        headings_count = structure.get("headings_count", 0)
        if headings_count == 0:
            base_risk += 0.2
        
        return min(base_risk, 1.0)
    
    def _compile_risk_factors(self, *risk_components: float) -> List[Dict[str, Any]]:
        """Compile detailed risk factors"""
        categories = [
            (RiskCategory.FORMAT, "Formatting and Presentation Issues"),
            (RiskCategory.CONTENT, "Content Quality and Accuracy"),
            (RiskCategory.AUTHENTICITY, "Document Authenticity"),
            (RiskCategory.COMPLIANCE, "Regulatory Compliance"),
            (RiskCategory.STRUCTURAL, "Document Structure")
        ]
        
        risk_factors = []
        for (category, description), risk_score in zip(categories, risk_components):
            risk_factors.append({
                "category": category,
                "description": description,
                "risk_score": risk_score,
                "severity": self._get_severity_level(risk_score)
            })
        
        return sorted(risk_factors, key=lambda x: x["risk_score"], reverse=True)
    
    def _get_severity_level(self, risk_score: float) -> str:
        """Get severity level for risk score"""
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        elif risk_score >= 0.2:
            return "low"
        else:
            return "minimal"
    
    def _identify_primary_concerns(self, risk_factors: List[Dict[str, Any]]) -> List[str]:
        """Identify primary concerns from risk factors"""
        concerns = []
        
        for factor in risk_factors[:3]:  # Top 3 risk factors
            if factor["risk_score"] > 0.5:
                concerns.append(f"{factor['description']} ({factor['severity']} risk)")
        
        if not concerns:
            concerns = ["No significant concerns identified"]
        
        return concerns
    
    def _generate_risk_recommendations(self, overall_risk: float, risk_factors: List[Dict[str, Any]]) -> List[str]:
        """Generate risk-based recommendations"""
        recommendations = []
        
        if overall_risk >= 0.8:
            recommendations.append("IMMEDIATE ACTION REQUIRED: High-risk document detected")
            recommendations.append("Escalate to senior compliance officer for review")
            recommendations.append("Consider blocking associated transactions")
        elif overall_risk >= 0.6:
            recommendations.append("Enhanced due diligence required")
            recommendations.append("Verify document with secondary sources")
            recommendations.append("Review within 24 hours")
        elif overall_risk >= 0.4:
            recommendations.append("Standard review process applicable")
            recommendations.append("Monitor for similar patterns")
        else:
            recommendations.append("Low risk - standard processing applicable")
        
        # Add specific recommendations based on risk factors
        for factor in risk_factors[:2]:
            if factor["risk_score"] > 0.6:
                if factor["category"] == RiskCategory.AUTHENTICITY:
                    recommendations.append("Verify document authenticity with source")
                elif factor["category"] == RiskCategory.COMPLIANCE:
                    recommendations.append("Conduct compliance gap analysis")
        
        return recommendations
    
    def _get_risk_level(self, risk_score: float) -> str:
        """Convert risk score to level"""
        if risk_score >= 0.8:
            return "critical"
        elif risk_score >= 0.6:
            return "high"
        elif risk_score >= 0.4:
            return "medium"
        elif risk_score >= 0.2:
            return "low"
        else:
            return "minimal"
    
    def _get_fallback_risk_assessment(self) -> Dict[str, Any]:
        """Fallback risk assessment when calculation fails"""
        return {
            "overall_risk_score": 0.5,
            "risk_level": "medium",
            "risk_breakdown": {
                "format_risk": 0.5,
                "content_risk": 0.5,
                "authenticity_risk": 0.5,
                "compliance_risk": 0.5,
                "structural_risk": 0.5
            },
            "risk_factors": [{
                "category": "system",
                "description": "Risk assessment system error",
                "risk_score": 0.5,
                "severity": "medium"
            }],
            "primary_concerns": ["Risk assessment temporarily unavailable"],
            "recommendations": ["Manual risk assessment required"]
        }