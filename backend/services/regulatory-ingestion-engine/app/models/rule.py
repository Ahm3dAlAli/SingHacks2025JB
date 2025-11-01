"""
Rule model for extracted compliance rules from regulatory documents.
"""
from datetime import date, datetime
from enum import Enum
from typing import Optional, List, Dict, Any, TYPE_CHECKING

from sqlalchemy import Column, String, Text, Date, ForeignKey, Enum as SQLEnum, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.document_version import DocumentVersion
    from app.models.rule_attribute import RuleAttribute
    from app.models.rule_relationship import RuleRelationship

class RuleType(str, Enum):
    """Type of regulatory rule."""
    OBLIGATION = "OBLIGATION"
    PROHIBITION = "PROHIBITION"
    REQUIREMENT = "REQUIREMENT"
    EXEMPTION = "EXEMPTION"
    GUIDANCE = "GUIDANCE"
    DEFINITION = "DEFINITION"
    OTHER = "OTHER"

class RuleStatus(str, Enum):
    """Status of a rule."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUPERSEDED = "SUPERSEDED"

class Rule(BaseModel):
    """
    Represents an extracted rule from a regulatory document.
    """
    __tablename__ = "rules"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    document_version_id = Column(UUID(as_uuid=True), ForeignKey("document_versions.id"), nullable=False)
    rule_number = Column(String(50), index=True)
    rule_type = Column(SQLEnum(RuleType), nullable=False)
    category = Column(String(100), index=True)
    subcategory = Column(String(100), index=True, nullable=True)
    summary = Column(Text, nullable=False)
    full_text = Column(Text, nullable=False)
    effective_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    status = Column(SQLEnum(RuleStatus), default=RuleStatus.DRAFT)
    metadata = Column(JSONB, default=dict)  # Additional metadata
    
    # Relationships
    document = relationship("Document", back_populates="rules")
    document_version = relationship("DocumentVersion", back_populates="rules")
    attributes = relationship(
        "RuleAttribute", 
        back_populates="rule",
        cascade="all, delete-orphan"
    )
    source_relationships = relationship(
        "RuleRelationship", 
        foreign_keys="[RuleRelationship.source_rule_id]",
        back_populates="source_rule"
    )
    target_relationships = relationship(
        "RuleRelationship", 
        foreign_keys="[RuleRelationship.target_rule_id]",
        back_populates="target_rule"
    )
    
    def __repr__(self) -> str:
        return f"<Rule(id='{self.id}', type='{self.rule_type}', summary='{self.summary[:50]}...')>"
    
    @property
    def is_active(self) -> bool:
        """Check if the rule is currently active."""
        if self.status != RuleStatus.ACTIVE:
            return False
            
        today = date.today()
        if self.effective_date and self.effective_date > today:
            return False
            
        if self.expiry_date and self.expiry_date < today:
            return False
            
        return True
    
    def get_attribute(self, name: str) -> Optional[Any]:
        """
        Get an attribute value by name.
        
        Args:
            name: Name of the attribute
            
        Returns:
            The attribute value or None if not found
        """
        for attr in self.attributes:
            if attr.attribute_name == name:
                return attr.attribute_value
        return None
    
    def set_attribute(
        self, 
        name: str, 
        value: Any, 
        data_type: Optional[str] = None,
        confidence_score: Optional[float] = None,
        extraction_method: Optional[str] = None
    ) -> 'RuleAttribute':
        """
        Set an attribute value, creating or updating as needed.
        
        Args:
            name: Name of the attribute
            value: Value to set
            data_type: Data type of the attribute
            confidence_score: Confidence score (0-1)
            extraction_method: How the attribute was extracted
            
        Returns:
            The created or updated RuleAttribute
        """
        from app.models.rule_attribute import RuleAttribute
        
        # Try to find existing attribute
        for attr in self.attributes:
            if attr.attribute_name == name:
                attr.attribute_value = value
                if data_type:
                    attr.data_type = data_type
                if confidence_score is not None:
                    attr.confidence_score = confidence_score
                if extraction_method:
                    attr.extraction_method = extraction_method
                attr.updated_at = datetime.utcnow()
                return attr
        
        # Create new attribute if not found
        attr = RuleAttribute(
            rule_id=self.id,
            attribute_name=name,
            attribute_value=value,
            data_type=data_type or self._infer_data_type(value),
            confidence_score=confidence_score,
            extraction_method=extraction_method or "MANUAL"
        )
        self.attributes.append(attr)
        return attr
    
    def _infer_data_type(self, value: Any) -> str:
        """Infer the data type of a value."""
        if isinstance(value, bool):
            return "BOOLEAN"
        elif isinstance(value, (int, float)):
            return "NUMBER"
        elif isinstance(value, (list, dict)):
            return "JSON"
        elif isinstance(value, (date, datetime)):
            return "DATE"
        return "STRING"
    
    def to_dict(self, include_attributes: bool = True) -> Dict[str, Any]:
        """
        Convert rule to dictionary, optionally including attributes.
        
        Args:
            include_attributes: Whether to include rule attributes
            
        Returns:
            Dictionary representation of the rule
        """
        result = {
            "id": str(self.id),
            "document_id": str(self.document_id),
            "document_version_id": str(self.document_version_id),
            "rule_number": self.rule_number,
            "rule_type": self.rule_type,
            "category": self.category,
            "subcategory": self.subcategory,
            "summary": self.summary,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "status": self.status,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "metadata": self.metadata or {}
        }
        
        if include_attributes:
            result["attributes"] = {
                attr.attribute_name: {
                    "value": attr.attribute_value,
                    "data_type": attr.data_type,
                    "confidence_score": attr.confidence_score,
                    "extraction_method": attr.extraction_method
                }
                for attr in self.attributes
            }
            
        return result
