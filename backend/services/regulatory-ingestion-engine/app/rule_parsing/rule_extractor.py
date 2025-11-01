"""
Rule extraction from processed documents using NLP.
"""
import re
import logging
import spacy
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from ..processing.models import ProcessedDocument, DocumentSection
from .base import (
    ExtractedRule, RuleType, RuleStatus, RuleSeverity,
    RuleAttribute, RuleReference, RuleExtractor
)

logger = logging.getLogger(__name__)

class RegexRuleExtractor(RuleExtractor):
    """Extracts rules using regular expression patterns."""
    
    def __init__(self, nlp_model: str = "en_core_web_sm"):
        """Initialize the rule extractor.
        
        Args:
            nlp_model: Name of the spaCy model to use
        """
        try:
            self.nlp = spacy.load(nlp_model)
        except OSError:
            logger.warning(f"spaCy model '{nlp_model}' not found. Downloading...")
            import spacy.cli
            spacy.cli.download(nlp_model)
            self.nlp = spacy.load(nlp_model)
        
        # Common patterns for identifying regulatory rules
        self.patterns = {
            'obligation': [
                r'(?i)(must|shall|will|is required to|are required to|is to|are to)',
                r'(?i)required to',
                r'(?i)must not',
                r'(?i)shall not',
                r'(?i)is prohibited from',
            ],
            'prohibition': [
                r'(?i)must not',
                r'(?i)shall not',
                r'(?i)may not',
                r'(?i)is prohibited from',
                r'(?i)are prohibited from',
                r'(?i)not permitted to',
                r'(?i)not allowed to',
            ],
            'permission': [
                r'(?i)may',
                r'(?i)is permitted to',
                r'(?i)are permitted to',
                r'(?i)is allowed to',
                r'(?i)are allowed to',
            ],
            'requirement': [
                r'(?i)must contain',
                r'(?i)must include',
                r'(?i)shall contain',
                r'(?i)shall include',
                r'(?i)requires? that',
            ],
            'condition': [
                r'(?i)if\s+',
                r'(?i)when\s+',
                r'(?i)in case of\s+',
                r'(?i)provided that\s+',
            ],
            'definition': [
                r'(?i)means?\s+',
                r'(?i)refers? to\s+',
                r'(?i)is defined as\s+',
            ]
        }
        
        # Compile all patterns
        self.compiled_patterns = {
            rule_type: [re.compile(p) for p in patterns]
            for rule_type, patterns in self.patterns.items()
        }
        
        # Keywords that indicate important sections
        self.section_keywords = [
            'obligation', 'requirement', 'prohibition', 'permission',
            'condition', 'definition', 'rule', 'regulation', 'standard',
            'policy', 'procedure', 'guideline', 'compliance', 'must', 'shall'
        ]
    
    async def extract_rules(self, document: ProcessedDocument) -> List[ExtractedRule]:
        """Extract rules from a processed document."""
        rules = []
        
        # Process each section of the document
        for section in document.content.sections:
            # Skip very short sections (likely not meaningful rules)
            if len(section.content.strip()) < 50:
                continue
                
            # Check if section title indicates it might contain rules
            if not self._is_relevant_section(section.title):
                continue
                
            # Process the section content
            section_rules = await self._process_section(section, document)
            rules.extend(section_rules)
        
        return rules
    
    def _is_relevant_section(self, title: str) -> bool:
        """Check if a section title suggests it contains rules."""
        if not title:
            return False
            
        title_lower = title.lower()
        return any(keyword in title_lower for keyword in self.section_keywords)
    
    async def _process_section(
        self, 
        section: DocumentSection,
        document: ProcessedDocument
    ) -> List[ExtractedRule]:
        """Process a document section to extract rules."""
        rules = []
        
        # Split content into sentences
        doc = self.nlp(section.content)
        sentences = [sent.text.strip() for sent in doc.sents]
        
        # Process each sentence
        for sent in sentences:
            # Skip very short sentences
            if len(sent) < 30:
                continue
                
            # Check for rule indicators
            rule_type, confidence = self._classify_sentence(sent)
            if rule_type:
                rule = self._create_rule(
                    sentence=sent,
                    rule_type=rule_type,
                    confidence=confidence,
                    section=section,
                    document=document
                )
                if rule:
                    rules.append(rule)
        
        return rules
    
    def _classify_sentence(self, sentence: str) -> Tuple[Optional[str], float]:
        """Classify a sentence to determine if it contains a rule and what type."""
        # Skip if the sentence is a question
        if '?' in sentence:
            return None, 0.0
            
        # Check for each rule type
        for rule_type, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(sentence):
                    # Higher confidence for more specific patterns
                    confidence = 0.7 + (0.3 * (len(patterns) - patterns.index(pattern)) / len(patterns))
                    return rule_type.upper(), min(confidence, 1.0)
        
        return None, 0.0
    
    def _create_rule(
        self,
        sentence: str,
        rule_type: str,
        confidence: float,
        section: DocumentSection,
        document: ProcessedDocument
    ) -> Optional[ExtractedRule]:
        """Create a rule object from a sentence."""
        try:
            # Generate a unique ID for the rule
            rule_id = f"{document.metadata.document_id}_{hash(sentence) & 0xffffffff:08x}"
            
            # Determine severity based on rule type and content
            severity = self._determine_severity(sentence, rule_type)
            
            # Create the rule
            rule = ExtractedRule(
                rule_id=rule_id,
                rule_type=rule_type,
                status=RuleStatus.ACTIVE,
                title=self._generate_rule_title(sentence, rule_type),
                description=sentence,
                source_document_id=document.metadata.document_id,
                source_text=sentence,
                source_location={
                    "section": section.title,
                    "page": section.page_number or 1
                },
                jurisdiction=document.metadata.jurisdiction,
                regulator=document.metadata.regulator,
                effective_date=document.metadata.published_date,
                severity=severity,
                confidence=confidence,
                extraction_method="regex_pattern_matching"
            )
            
            # Add attributes
            self._extract_attributes(rule, sentence, document)
            
            return rule
            
        except Exception as e:
            logger.error(f"Error creating rule from sentence: {e}")
            return None
    
    def _determine_severity(self, sentence: str, rule_type: str) -> str:
        """Determine the severity of a rule based on its content."""
        # Default severity based on rule type
        severity_map = {
            "OBLIGATION": RuleSeverity.HIGH,
            "PROHIBITION": RuleSeverity.HIGH,
            "REQUIREMENT": RuleSeverity.MEDIUM,
            "PERMISSION": RuleSeverity.LOW,
            "CONDITION": RuleSeverity.MEDIUM,
            "DEFINITION": RuleSeverity.LOW,
        }
        
        severity = severity_map.get(rule_type, RuleSeverity.MEDIUM)
        
        # Adjust based on keywords
        if any(word in sentence.lower() for word in ["must", "shall", "prohibit", "forbid"]):
            severity = RuleSeverity.HIGH
        elif any(word in sentence.lower() for word in ["should", "recommend", "encourage"]):
            severity = RuleSeverity.MEDIUM
            
        return severity
    
    def _generate_rule_title(self, sentence: str, rule_type: str) -> str:
        """Generate a concise title for a rule."""
        # Take first 10 words or first 60 characters, whichever is shorter
        words = sentence.split()
        title = ' '.join(words[:10])
        if len(title) > 60:
            title = title[:57] + '...'
        
        # Add rule type for clarity
        return f"[{rule_type}] {title}"
    
    def _extract_attributes(self, rule: ExtractedRule, sentence: str, document: ProcessedDocument) -> None:
        """Extract additional attributes from the sentence."""
        # Add document source as an attribute
        rule.attributes.append(RuleAttribute(
            name="source",
            value=document.metadata.source,
            data_type="string",
            source="document_metadata"
        ))
        
        # Extract potential dates
        doc = self.nlp(sentence)
        for ent in doc.ents:
            if ent.label_ == "DATE":
                rule.attributes.append(RuleAttribute(
                    name="mentioned_date",
                    value=ent.text,
                    data_type="date",
                    source="nlp_entity_extraction",
                    confidence=0.8
                ))
        
        # Extract potential monetary values
        if any(char in sentence for char in ['$', '€', '£', '¥']):
            # Simple regex for monetary values
            import re
            money_matches = re.findall(r'[\$€£¥]\s*\d+(?:[\.,]\d+)?', sentence)
            for i, match in enumerate(money_matches):
                rule.attributes.append(RuleAttribute(
                    name=f"monetary_value_{i+1}",
                    value=match,
                    data_type="string",
                    source="regex_extraction",
                    confidence=0.9
                ))
        
        # Add document type as a keyword
        if document.metadata.document_type:
            rule.keywords.append(document.metadata.document_type.value)
            
        # Add jurisdiction and regulator as keywords if available
        if document.metadata.jurisdiction:
            rule.keywords.append(document.metadata.jurisdiction)
        if document.metadata.regulator:
            rule.keywords.append(document.metadata.regulator)
