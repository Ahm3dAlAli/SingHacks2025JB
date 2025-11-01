"""
Models package - imports all models to register them with SQLAlchemy.
"""
from sqlalchemy.orm import configure_mappers

# Import base first
from app.models.base import BaseModel

# Import all models to ensure they are registered with SQLAlchemy
# Order matters to avoid circular dependencies
from app.models.document_source import DocumentSource
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.rule_attribute import RuleAttribute
from app.models.rule import Rule, RuleType, RuleStatus

# Configure all mappers to resolve relationships
configure_mappers()

# Export commonly used items
__all__ = [
    "BaseModel",
    "Document",
    "DocumentSource",
    "DocumentVersion",
    "Rule",
    "RuleType",
    "RuleStatus",
    "RuleAttribute",
]
