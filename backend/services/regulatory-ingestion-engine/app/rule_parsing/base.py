"""
Base classes and interfaces for rule parsing and transformation.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from pydantic import BaseModel, Field


class RuleType(str, Enum):
    """Types of regulatory rules."""
    OBLIGATION = "OBLIGATION"      # Something that must be done
    PROHIBITION = "PROHIBITION"   # Something that must not be done
    PERMISSION = "PERMISSION"     # Something that is allowed
    REQUIREMENT = "REQUIREMENT"   # A specific requirement
    CONDITION = "CONDITION"       # A condition that affects other rules
    DEFINITION = "DEFINITION"     # A definition of a term
    

class RuleStatus(str, Enum):
    """Status of a rule."""
    DRAFT = "DRAFT"               # Initial state
    ACTIVE = "ACTIVE"             # Currently in effect
    SUPERSEDED = "SUPERSEDED"     # Replaced by another rule
    REPEALED = "REPEALED"         # No longer in effect
    

class RuleSeverity(str, Enum):
    """Severity of non-compliance with a rule."""
    CRITICAL = "CRITICAL"         # Severe regulatory impact
    HIGH = "HIGH"                 # Significant regulatory impact
    MEDIUM = "MEDIUM"             # Moderate regulatory impact
    LOW = "LOW"                   # Minor regulatory impact
    

class RuleAttribute(BaseModel):
    """An attribute of a rule."""
    name: str                     # Attribute name (e.g., "effective_date", "jurisdiction")
    value: Any                    # Attribute value
    data_type: str                # Data type of the value
    source: str                   # Source of this attribute (e.g., "extracted", "inferred")
    confidence: float = 1.0       # Confidence score (0.0 to 1.0)
    

class RuleReference(BaseModel):
    """A reference to another rule or document."""
    ref_type: str                 # Type of reference (e.g., "regulation", "section", "document")
    ref_id: str                   # Unique identifier of the reference
    description: Optional[str] = None  # Description of the reference
    

class ExtractedRule(BaseModel):
    """A rule extracted from a document."""
    rule_id: str                  # Unique identifier for the rule
    rule_type: RuleType           # Type of rule
    status: RuleStatus = RuleStatus.DRAFT  # Current status
    
    # Core rule information
    title: str                    # Short title/description
    description: str              # Full description of the rule
    
    # Source information
    source_document_id: str       # ID of the source document
    source_text: str              # The original text this rule was extracted from
    source_location: Dict[str, Any] = Field(
        default_factory=dict       # Location in source (page, paragraph, etc.)
    )
    
    # Rule metadata
    jurisdiction: Optional[str] = None  # Jurisdiction this rule applies to
    regulator: Optional[str] = None     # Regulatory body
    effective_date: Optional[str] = None  # When the rule comes into effect
    expiry_date: Optional[str] = None    # When the rule expires (if applicable)
    
    # Relationships
    attributes: List[RuleAttribute] = Field(default_factory=list)  # Additional attributes
    references: List[RuleReference] = Field(default_factory=list)  # Related rules/documents
    
    # Compliance information
    severity: RuleSeverity = RuleSeverity.MEDIUM
    category: Optional[str] = None      # Category/topic of the rule
    keywords: List[str] = Field(default_factory=list)  # Keywords for search
    
    # Processing metadata
    confidence: float = 1.0       # Confidence score (0.0 to 1.0)
    extraction_method: Optional[str] = None  # How this rule was extracted
    
    # Versioning
    version: str = "1.0"          # Version of this rule
    previous_version: Optional[str] = None  # Previous version ID if updated
    
    # Audit fields
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class RuleExtractor(ABC):
    """Interface for rule extraction from documents."""
    
    @abstractmethod
    async def extract_rules(self, document: 'ProcessedDocument') -> List[ExtractedRule]:
        """Extract rules from a processed document.
        
        Args:
            document: The processed document to extract rules from
            
        Returns:
            List of extracted rules
        """
        pass


class RuleTransformer(ABC):
    """Interface for transforming rules into different formats."""
    
    @abstractmethod
    async def transform(self, rule: ExtractedRule, target_format: str) -> Any:
        """Transform a rule into the specified format.
        
        Args:
            rule: The rule to transform
            target_format: Target format (e.g., 'json', 'yaml', 'sql')
            
        Returns:
            The transformed rule in the target format
        """
        pass


class RuleValidator(ABC):
    """Interface for validating extracted rules."""
    
    @abstractmethod
    def validate(self, rule: ExtractedRule) -> dict:
        """Validate an extracted rule.
        
        Args:
            rule: The rule to validate
            
        Returns:
            Dictionary with validation results including 'is_valid' and 'issues'
        """
