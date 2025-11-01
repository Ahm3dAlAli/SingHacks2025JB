"""
RuleAttribute model for storing additional attributes of rules.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING, Any

from sqlalchemy import Column, String, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.rule import Rule

class RuleAttribute(BaseModel):
    """
    Represents an attribute of a rule, such as thresholds, conditions, or other metadata.
    """
    __tablename__ = "rule_attributes"
    __table_args__ = (
        {"comment": "Stores additional attributes for rules, such as thresholds and conditions"},
    )
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id", ondelete="CASCADE"), nullable=False)
    attribute_name = Column(String(100), nullable=False, comment="Name of the attribute")
    attribute_value = Column(String, nullable=True, comment="Value of the attribute (stored as text)")
    data_type = Column(String(50), nullable=True, comment="Data type of the attribute value")
    confidence_score = Column(Float, nullable=True, comment="Confidence score (0-1) of the attribute value")
    extraction_method = Column(String(50), nullable=True, comment="How the attribute was extracted (e.g., 'MANUAL', 'NLP', 'LLM')")
    
    # Relationships
    rule = relationship("Rule", back_populates="attributes")
    
    def __repr__(self) -> str:
        return f"<RuleAttribute(rule_id='{self.rule_id}', name='{self.attribute_name}')>"
    
    @classmethod
    def create(
        cls,
        rule_id: uuid.UUID,
        attribute_name: str,
        attribute_value: Any,
        data_type: Optional[str] = None,
        confidence_score: Optional[float] = None,
        extraction_method: Optional[str] = None
    ) -> 'RuleAttribute':
        """
        Create a new rule attribute.
        
        Args:
            rule_id: ID of the parent rule
            attribute_name: Name of the attribute
            attribute_value: Value of the attribute
            data_type: Data type of the attribute value
            confidence_score: Confidence score (0-1)
            extraction_method: How the attribute was extracted
            
        Returns:
            RuleAttribute: The created attribute
        """
        # Convert value to string for storage
        if attribute_value is not None and not isinstance(attribute_value, str):
            if isinstance(attribute_value, (dict, list)):
                import json
                attribute_value = json.dumps(attribute_value)
            else:
                attribute_value = str(attribute_value)
        
        # Infer data type if not provided
        if not data_type and attribute_value is not None:
            data_type = cls._infer_data_type(attribute_value)
        
        return cls(
            rule_id=rule_id,
            attribute_name=attribute_name,
            attribute_value=attribute_value,
            data_type=data_type,
            confidence_score=confidence_score,
            extraction_method=extraction_method
        )
    
    @staticmethod
    def _infer_data_type(value: str) -> str:
        """
        Infer the data type of a string value.
        
        Args:
            value: The value to infer the type of
            
        Returns:
            str: The inferred data type
        """
        if not value:
            return "STRING"
            
        # Check for JSON
        if (value.startswith('{') and value.endswith('}')) or (value.startswith('[') and value.endswith(']')):
            try:
                import json
                json.loads(value)
                return "JSON"
            except (json.JSONDecodeError, ValueError):
                pass
                
        # Check for boolean
        if value.lower() in ('true', 'false', 'yes', 'no', '1', '0', 't', 'f', 'y', 'n'):
            return "BOOLEAN"
            
        # Check for number (int or float)
        try:
            float(value)
            return "FLOAT" if '.' in value else "INTEGER"
        except ValueError:
            pass
            
        # Check for date/datetime
        try:
            from dateutil import parser
            parser.parse(value)
            return "DATETIME"
        except (ValueError, OverflowError):
            pass
            
        # Default to string
        return "STRING"
    
    def get_value(self) -> Any:
        """
        Get the attribute value with the appropriate type.
        
        Returns:
            The typed value of the attribute
        """
        if self.attribute_value is None:
            return None
            
        if not self.data_type:
            return self.attribute_value
            
        try:
            if self.data_type == "BOOLEAN":
                return self.attribute_value.lower() in ('true', 'yes', '1', 't', 'y')
            elif self.data_type == "INTEGER":
                return int(self.attribute_value)
            elif self.data_type == "FLOAT":
                return float(self.attribute_value)
            elif self.data_type in ("JSON", "DICT", "LIST"):
                import json
                return json.loads(self.attribute_value)
            elif self.data_type == "DATETIME":
                from dateutil import parser
                return parser.parse(self.attribute_value)
            elif self.data_type == "DATE":
                from datetime import datetime
                return datetime.strptime(self.attribute_value, "%Y-%m-%d").date()
            else:
                return self.attribute_value
        except (ValueError, TypeError):
            # If conversion fails, return the raw value
            return self.attribute_value
