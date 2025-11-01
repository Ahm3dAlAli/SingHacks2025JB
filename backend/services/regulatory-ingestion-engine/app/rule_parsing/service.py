"""
Rule processing service that coordinates rule extraction and transformation.
"""
import logging
import os
from typing import List, Dict, Any, Optional, Type
from pathlib import Path

from ..processing.models import ProcessedDocument
from .base import ExtractedRule, RuleExtractor, RuleTransformer, RuleValidator
from .rule_extractor import RegexRuleExtractor
from .groq_rule_extractor import GroqRuleExtractor

logger = logging.getLogger(__name__)

class RuleProcessingService:
    """Service for processing documents to extract and manage rules."""
    
    def __init__(self):
        self.extractors: List[RuleExtractor] = []
        self.transformers: Dict[str, RuleTransformer] = {}
        self.validators: List[RuleValidator] = []
        
        # Register default extractors
        self.register_extractor(RegexRuleExtractor())
        
        # Register Groq extractor if API key is available
        groq_api_key = os.getenv("GROQ_API_KEY")
        if groq_api_key:
            try:
                self.register_extractor(GroqRuleExtractor(api_key=groq_api_key))
            except Exception as e:
                logger.warning(f"Failed to initialize GroqRuleExtractor: {str(e)}")
        else:
            logger.warning("GROQ_API_KEY not found in environment variables. GroqRuleExtractor will not be available.")
    
    def register_extractor(self, extractor: RuleExtractor) -> None:
        """Register a rule extractor.
        
        Args:
            extractor: The rule extractor to register
        """
        self.extractors.append(extractor)
        logger.info(f"Registered rule extractor: {extractor.__class__.__name__}")
    
    def register_transformer(self, name: str, transformer: RuleTransformer) -> None:
        """Register a rule transformer.
        
        Args:
            name: Name to identify the transformer
            transformer: The rule transformer to register
        """
        self.transformers[name.lower()] = transformer
        logger.info(f"Registered rule transformer: {name}")
    
    def register_validator(self, validator: RuleValidator) -> None:
        """Register a rule validator.
        
        Args:
            validator: The rule validator to register
        """
        self.validators.append(validator)
        logger.info(f"Registered rule validator: {validator.__class__.__name__}")
    
    async def extract_rules(
        self, 
        document: ProcessedDocument,
        extractor_names: Optional[List[str]] = None
    ) -> List[ExtractedRule]:
        """Extract rules from a processed document.
        
        Args:
            document: The processed document to extract rules from
            extractor_names: Optional list of extractor names to use
            
        Returns:
            List of extracted rules
        """
        all_rules = []
        
        # Filter extractors if names are provided
        extractors = self.extractors
        if extractor_names:
            extractors = [e for e in extractors 
                         if e.__class__.__name__ in extractor_names]
        
        if not extractors:
            logger.warning("No rule extractors registered or matched the filter")
            return []
        
        # Extract rules using all registered extractors
        for extractor in extractors:
            try:
                logger.info(f"Extracting rules with {extractor.__class__.__name__}")
                rules = await extractor.extract_rules(document)
                all_rules.extend(rules)
                logger.info(f"Extracted {len(rules)} rules using {extractor.__class__.__name__}")
            except Exception as e:
                logger.error(f"Error extracting rules with {extractor.__class__.__name__}: {e}")
        
        # Remove duplicates (based on rule content)
        unique_rules = self._deduplicate_rules(all_rules)
        
        # Validate rules
        validated_rules = []
        for rule in unique_rules:
            is_valid = await self._validate_rule(rule)
            if is_valid:
                validated_rules.append(rule)
            else:
                logger.warning(f"Rule validation failed for rule: {rule.rule_id}")
        
        return validated_rules
    
    async def transform_rules(
        self, 
        rules: List[ExtractedRule], 
        target_format: str = "json"
    ) -> List[Dict[str, Any]]:
        """Transform rules to the specified format.
        
        Args:
            rules: List of rules to transform
            target_format: Target format (must be registered)
            
        Returns:
            List of transformed rules
        """
        transformed = []
        
        if target_format.lower() not in self.transformers:
            logger.error(f"No transformer registered for format: {target_format}")
            return []
        
        transformer = self.transformers[target_format.lower()]
        
        for rule in rules:
            try:
                transformed_rule = await transformer.transform(rule, target_format)
                transformed.append(transformed_rule)
            except Exception as e:
                logger.error(f"Error transforming rule {rule.rule_id}: {e}")
        
        return transformed
    
    async def process_document(
        self, 
        document: ProcessedDocument,
        extractor_names: Optional[List[str]] = None,
        output_format: Optional[str] = None
    ) -> Dict[str, Any]:
        """Process a document to extract and optionally transform rules.
        
        Args:
            document: The processed document
            extractor_names: Optional list of extractor names to use
            output_format: Optional format to transform rules to
            
        Returns:
            Dictionary with processing results
        """
        # Extract rules
        rules = await self.extract_rules(document, extractor_names)
        
        result = {
            "document_id": document.metadata.document_id,
            "rule_count": len(rules),
            "rules": rules
        }
        
        # Transform rules if format specified
        if output_format:
            transformed = await self.transform_rules(rules, output_format)
            result["transformed_rules"] = transformed
        
        return result
    
    async def _validate_rule(self, rule: ExtractedRule) -> bool:
        """Validate a rule using all registered validators.
        
        Args:
            rule: The rule to validate
            
        Returns:
            bool: True if all validations pass, False otherwise
        """
        if not self.validators:
            return True  # No validators, so consider it valid
        
        all_valid = True
        for validator in self.validators:
            try:
                result = await validator.validate(rule)
                if not result.get('is_valid', False):
                    logger.warning(f"Validator {validator.__class__.__name__} failed for rule {rule.rule_id}")
                    all_valid = False
            except Exception as e:
                logger.error(f"Error in validator {validator.__class__.__name__}: {e}")
                all_valid = False
        
        return all_valid
    
    def _deduplicate_rules(self, rules: List[ExtractedRule]) -> List[ExtractedRule]:
        """Remove duplicate rules based on content similarity.
        
        Args:
            rules: List of rules to deduplicate
            
        Returns:
            List of unique rules
        """
        # Simple deduplication based on rule description
        seen = set()
        unique_rules = []
        
        for rule in rules:
            # Create a unique key based on the rule content
            # This is a simple approach - could be enhanced with more sophisticated similarity detection
            key = (
                rule.description[:200],  # First 200 chars of description
                rule.rule_type,
                rule.source_document_id
            )
            
            if key not in seen:
                seen.add(key)
                unique_rules.append(rule)
        
        logger.info(f"Deduplicated {len(rules)} rules to {len(unique_rules)} unique rules")
        return unique_rules


# Global instance for easy import
rule_processor = RuleProcessingService()
