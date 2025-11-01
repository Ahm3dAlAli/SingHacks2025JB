import re
from typing import Dict, Any, List, Tuple
from app.services.groq_client import GroqClient
from app.utils.logger import setup_logger

logger = setup_logger(__name__)

class FormatValidatorAgent:
    def __init__(self):
        self.groq_client = GroqClient()
        logger.info("Format Validator Agent initialized")
    
    def validate_format(self, extracted_text: str, structure_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Comprehensive format validation"""
        try:
            logger.info("Starting format validation")
            
            # Basic format checks
            basic_checks = self._perform_basic_checks(extracted_text, structure_analysis)
            
            # AI-enhanced format analysis
            ai_analysis = self.groq_client.analyze_text_advanced(extracted_text, "format_validation")
            
            # Content validation
            content_validation = self.groq_client.analyze_text_advanced(extracted_text, "content_validation")
            
            # Calculate overall format score
            format_score = self._calculate_format_score(basic_checks, ai_analysis)
            
            return {
                "basic_checks": basic_checks,
                "ai_analysis": ai_analysis,
                "content_validation": content_validation,
                "overall_format_score": format_score,
                "format_rating": self._get_format_rating(format_score)
            }
            
        except Exception as e:
            logger.error(f"Format validation failed: {str(e)}")
            return self._get_fallback_validation()
    
    def _perform_basic_checks(self, text: str, structure: Dict[str, Any]) -> Dict[str, Any]:
        """Perform basic format and structure checks"""
        issues = []
        warnings = []
        
        # Check for multiple consecutive newlines (formatting issue)
        if '\n\n\n' in text:
            issues.append("multiple_consecutive_blank_lines")
        
        # Check paragraph length consistency
        paragraphs = [p.strip() for p in text.split('\n\n') if p.strip()]
        if paragraphs:
            word_counts = [len(p.split()) for p in paragraphs]
            avg_words = sum(word_counts) / len(word_counts)
            
            for i, count in enumerate(word_counts):
                if count > avg_words * 3:
                    warnings.append(f"paragraph_{i+1}_extremely_long")
                elif count < avg_words * 0.1:
                    warnings.append(f"paragraph_{i+1}_extremely_short")
        
        # Check for inconsistent numbering
        numbering_issues = self._check_numbering_consistency(text)
        issues.extend(numbering_issues)
        
        # Check heading consistency
        heading_issues = self._check_heading_consistency(structure)
        issues.extend(heading_issues)
        
        return {
            "issues": issues,
            "warnings": warnings,
            "paragraph_count": len(paragraphs),
            "average_paragraph_length": avg_words if paragraphs else 0,
            "total_issues_count": len(issues) + len(warnings)
        }
    
    def _check_numbering_consistency(self, text: str) -> List[str]:
        """Check for consistent numbering in document"""
        issues = []
        
        # Find all numbered items
        numbered_patterns = [
            r'\n\d+\.\s',  # 1. 
            r'\n\(\d+\)\s',  # (1)
            r'\n[a-z]\)\s',  # a)
            r'\n\([a-z]\)\s',  # (a)
        ]
        
        found_patterns = []
        for pattern in numbered_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_patterns.append(pattern)
        
        # Check for mixed numbering styles
        if len(found_patterns) > 1:
            issues.append("mixed_numbering_styles")
        
        return issues
    
    def _check_heading_consistency(self, structure: Dict[str, Any]) -> List[str]:
        """Check heading consistency"""
        issues = []
        
        sections = structure.get('sections', [])
        heading_levels = [section.get('level', 1) for section in sections]
        
        # Check for heading level skipping
        if heading_levels:
            max_level = max(heading_levels)
            for level in range(1, max_level + 1):
                if level not in heading_levels and level < max_level:
                    issues.append(f"heading_level_{level}_skipped")
        
        return issues
    
    def _calculate_format_score(self, basic_checks: Dict, ai_analysis: Dict) -> float:
        """Calculate overall format quality score"""
        base_score = 1.0
        
        # Deduct for basic issues
        issue_count = basic_checks.get('total_issues_count', 0)
        base_score -= min(issue_count * 0.05, 0.3)  # Max 30% deduction for basic issues
        
        # Incorporate AI analysis score
        ai_score = float(ai_analysis.get('professionalism_score', 0.5))
        base_score = (base_score * 0.6) + (ai_score * 0.4)
        
        return max(0.0, min(1.0, base_score))
    
    def _get_format_rating(self, score: float) -> str:
        """Convert format score to rating"""
        if score >= 0.9:
            return "excellent"
        elif score >= 0.7:
            return "good"
        elif score >= 0.5:
            return "fair"
        else:
            return "poor"
    
    def _get_fallback_validation(self) -> Dict[str, Any]:
        """Fallback validation when analysis fails"""
        return {
            "basic_checks": {"issues": [], "warnings": ["validation_failed"], "total_issues_count": 1},
            "ai_analysis": {"error": "validation_failed"},
            "content_validation": {"error": "validation_failed"},
            "overall_format_score": 0.5,
            "format_rating": "unknown"
        }