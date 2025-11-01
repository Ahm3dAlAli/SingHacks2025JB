"""
Rule extraction using Groq's language model API.
"""
import json
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
import os

from groq import Groq
from pydantic import ValidationError

from ..processing.models import ProcessedDocument, DocumentSection
from .base import (
    ExtractedRule, RuleType, RuleStatus, RuleSeverity,
    RuleAttribute, RuleReference, RuleExtractor
)

logger = logging.getLogger(__name__)

class GroqRuleExtractor(RuleExtractor):
    """Extracts rules using Groq's language model API."""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """Initialize the Groq rule extractor.
        
        Args:
            api_key: Groq API key. If not provided, will try to get from GROQ_API_KEY env var.
            model: The Groq model to use for rule extraction.
        """
        self.api_key = api_key or os.getenv("GROQ_API_KEY", "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")
        if not self.api_key:
            raise ValueError("Groq API key is required. Either pass it to the constructor "
                           "or set the GROQ_API_KEY environment variable.")
        
        self.client = Groq(api_key=self.api_key)
        self.model = model
        
        # Default prompt template - using double curly braces to escape them in the JSON example
        self.prompt_template = """
        You are a regulatory compliance expert. Your task is to analyze the following document and extract all relevant regulatory rules, requirements, and compliance obligations.
        
        IMPORTANT: The document may contain multiple sections. Pay attention to the section headers (marked with ===== SECTION: [title] =====) as they provide important context.
        
        Return the results as a JSON array with the following structure for each rule:
        [
            {{
                "category": "The type of rule (e.g., 'Transaction Monitoring', 'Reporting', 'Record Keeping')",
                "rule": "The specific regulatory requirement or rule text",
                "key_elements": ["Important elements or conditions of the rule"],
                "examples": ["Example scenarios or applications of the rule"],
                "notes": "Any additional context or implementation guidance"
            }}
        ]
        
        Focus on extracting:
        1. Explicit rules and requirements
        2. Implied obligations
        3. Quantitative thresholds or limits
        4. Required procedures or processes
        5. Reporting requirements
        6. Record-keeping obligations
        
        Be thorough and extract as many rules as possible. Include rules that are explicitly stated as well as those that can be reasonably inferred from the text.
        
        DOCUMENT CONTENT:
        {document_text}
        
        Return ONLY valid JSON. Do not include any explanatory text before or after the JSON array.
        """
    
    async def _generate_document_title(self, text: str) -> str:
        """Generate a title for the document based on its content."""
        # Use the first sentence or first 100 characters as title
        first_period = text.find('.')
        if first_period > 0:
            title = text[:first_period].strip()
            if len(title) > 10:  # Ensure title has reasonable length
                return title
        
        # Fallback to first 100 characters
        return text[:100].strip() + ('...' if len(text) > 100 else '')
    
    async def ensure_document_metadata(self, document: ProcessedDocument) -> None:
        """Ensure document has required metadata fields."""
        # Generate a title if missing
        if not document.metadata.title and document.content and document.content.raw_text:
            document.metadata.title = await self._generate_document_title(document.content.raw_text)
        
        # Ensure required fields have defaults
        if not document.metadata.document_type:
            document.metadata.document_type = "REGULATION"
        if not document.metadata.source:
            document.metadata.source = "groq_extraction"
    
    async def extract_rules(self, document: ProcessedDocument) -> List[ExtractedRule]:
        """Extract rules from a processed document using Groq's API."""
        # Ensure document has required metadata
        await self.ensure_document_metadata(document)
        
        if not document.content or not document.content.sections:
            logger.warning("No content or sections found in the document")
            return []
        
        # Combine all sections into a single text with clear section headers
        full_text = "\n\n".join(
            f"===== SECTION: {section.title} =====\n{section.content}"
            for section in document.content.sections
            if section.content.strip()
        )
        
        # Add raw text if available
        if document.content.raw_text:
            full_text = f"{document.content.raw_text}\n\n{full_text}"
        
        if not full_text.strip():
            logger.warning("No text content found in document sections")
            return []
        
        try:
            # Generate the prompt
            # Truncate the text if it's too long (Groq has token limits)
            max_length = 100000  # Leave some room for the prompt
            if len(full_text) > max_length:
                logger.warning(f"Document text too long ({len(full_text)} chars), truncating to {max_length} chars")
                full_text = full_text[:max_length] + "\n[CONTENT TRUNCATED]"
                
            prompt = self.prompt_template.format(document_text=full_text)
            logger.info(f"Sending prompt to Groq (length: {len(prompt)} chars)")
                
            # Call Groq API
            try:
                response = self.client.chat.completions.create(
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    model=self.model,
                    temperature=0.2,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
            except Exception as e:
                logger.error(f"Error calling Groq API: {str(e)}")
                raise ValueError(f"Failed to call Groq API: {str(e)}")
            
            # Extract and parse the response
            response_content = response.choices[0].message.content
            if not response_content:
                logger.error("Empty response from Groq API")
                return []
                
            # Parse the JSON response
            try:
                rules_data = json.loads(response_content)
                if 'rules' in rules_data:
                    rules_data = rules_data['rules']
                else:
                    rules_data = [rules_data]
                
                # Convert the extracted rules to ExtractedRule objects
                document_id = document.metadata.document_id if document.metadata else "unknown_document"
                return [
                    self._create_rule(rule_data, document_id)
                    for rule_data in rules_data
                    if rule_data.get("rule")  # Only include rules with actual content
                ]
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Groq response as JSON: {e}\nResponse: {response_content}")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting rules with Groq: {str(e)}", exc_info=True)
            return []
    
    def _create_rule(self, rule_data: Dict[str, Any], document_id: str) -> ExtractedRule:
        """Convert a rule dictionary to an ExtractedRule object."""
        # Default values
        rule_text = rule_data.get('rule', '')
        category = rule_data.get('category', 'Uncategorized')
        key_elements = rule_data.get('key_elements', [])
        examples = rule_data.get('examples', [])
        notes = rule_data.get('notes', '')
        
        # Map category to rule type
        rule_type = self._infer_rule_type(rule_text, category)
        
        # Create a hashable version of the rule data for the ID
        rule_data_copy = rule_data.copy()
        for key, value in rule_data_copy.items():
            if isinstance(value, (list, dict)):
                rule_data_copy[key] = str(value)  # Convert lists/dicts to strings for hashing
        
        # Create the rule
        rule = ExtractedRule(
            rule_id=f"groq_{hash(frozenset(rule_data_copy.items())):x}",
            rule_type=rule_type,
            status=RuleStatus.ACTIVE,
            title=f"{category}: {rule_text[:50]}..." if len(rule_text) > 50 else f"{category}: {rule_text}",
            description=rule_text,
            source_document_id=document_id,
            source_text=rule_text,
            source_location={"type": "extracted_from_document"},
            category=category,
            keywords=key_elements,
            extraction_method="groq_api",
            confidence=0.9,  # High confidence as we're using an LLM
        )
        
        # Add key elements and examples as attributes
        if key_elements:
            rule.attributes.append(RuleAttribute(
                name="key_elements",
                value=", ".join(key_elements),
                data_type="list[str]",
                source="groq_extraction"
            ))
            
        if examples:
            rule.attributes.append(RuleAttribute(
                name="examples",
                value="\n".join(examples),
                data_type="list[str]",
                source="groq_extraction"
            ))
            
        if notes:
            rule.attributes.append(RuleAttribute(
                name="notes",
                value=notes,
                data_type="str",
                source="groq_extraction"
            ))
            
        return rule
    
    def _infer_rule_type(self, rule_text: str, category: str) -> RuleType:
        """Infer the rule type from the rule text and category."""
        rule_text = rule_text.lower()
        category = category.lower()
        
        if any(word in rule_text for word in ["must", "shall", "required to", "is to"]):
            if any(word in rule_text for word in ["not", "no ", "prohibited", "forbidden"]):
                return RuleType.PROHIBITION
            return RuleType.OBLIGATION
            
        if any(word in rule_text for word in ["may", "can", "allowed to", "permitted to"]):
            return RuleType.PERMISSION
            
        if any(word in category for word in ["prohib", "forbid", "ban", "restrict"]):
            return RuleType.PROHIBITION
            
        if any(word in category for word in ["require", "obligation", "must"]):
            return RuleType.OBLIGATION
            
        if any(word in category for word in ["permit", "allow", "may"]):
            return RuleType.PERMISSION
            
        if any(word in category for word in ["condition", "if", "when"]):
            return RuleType.CONDITION
            
        if any(word in category for word in ["define", "definition", "term"]):
            return RuleType.DEFINITION
            
        # Default to REQUIREMENT if we can't determine the type
        return RuleType.REQUIREMENT
