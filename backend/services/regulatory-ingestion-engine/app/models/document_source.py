"""
DocumentSource model for tracking sources of regulatory documents.
"""
from datetime import datetime
from typing import Optional, List

from sqlalchemy import Column, String, Text, Boolean, JSON, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.base import BaseModel

class DocumentSource(BaseModel):
    """
    Represents a source of regulatory documents (e.g., HKMA API, MAS Email, etc.).
    """
    __tablename__ = "document_sources"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    source_type = Column(String(50), nullable=False)  # 'API', 'EMAIL', 'RSS', 'UPLOAD', etc.
    config = Column(JSON)  # Configuration specific to the source type
    is_active = Column(Boolean, default=True)
    
    # Relationships
    documents = List["Document"]  # Will be set up by backref in Document model
    
    def __repr__(self) -> str:
        return f"<DocumentSource(name='{self.name}', type='{self.source_type}')>"
    
    @classmethod
    def create(
        cls,
        name: str,
        source_type: str,
        description: Optional[str] = None,
        config: Optional[dict] = None,
        is_active: bool = True
    ) -> 'DocumentSource':
        """
        Create a new document source.
        
        Args:
            name: Name of the source
            source_type: Type of source (API, EMAIL, RSS, etc.)
            description: Optional description
            config: Configuration dictionary
            is_active: Whether the source is active
            
        Returns:
            DocumentSource: The created source
        """
        return cls(
            name=name,
            description=description,
            source_type=source_type,
            config=config or {},
            is_active=is_active
        )
    
    def update_config(self, config_updates: dict) -> None:
        """
        Update the source configuration.
        
        Args:
            config_updates: Dictionary of configuration updates
        """
        if not self.config:
            self.config = {}
        self.config.update(config_updates)
        self.updated_at = datetime.utcnow()
    
    def activate(self) -> None:
        """Activate the document source."""
        self.is_active = True
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate the document source."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
