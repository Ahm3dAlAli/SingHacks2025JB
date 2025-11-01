"""
DocumentVersion model for versioning regulatory documents.
"""
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Column, Text, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.rule import Rule

class DocumentVersion(BaseModel):
    """
    Represents a specific version of a regulatory document.
    """
    __tablename__ = "document_versions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    version_number = Column(Integer, nullable=False)
    version_date = Column(DateTime(timezone=True), nullable=False)
    change_summary = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_by = Column(String(100), default="system")
    
    # Relationships
    document = relationship("Document", back_populates="versions")
    rules = relationship(
        "Rule", 
        back_populates="document_version",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<DocumentVersion(document_id='{self.document_id}', version={self.version_number})>"
    
    @classmethod
    def create(
        cls,
        document_id: uuid.UUID,
        version_number: int,
        version_date: datetime,
        raw_content: str,
        checksum: str,
        change_summary: Optional[str] = None,
        created_by: str = "system"
    ) -> 'DocumentVersion':
        """
        Create a new document version.
        
        Args:
            document_id: ID of the parent document
            version_number: Version number (should increment)
            version_date: When this version was created
            raw_content: Raw content of this version
            checksum: Checksum of the content
            change_summary: Summary of changes in this version
            created_by: Who created this version
            
        Returns:
            DocumentVersion: The created version
        """
        return cls(
            document_id=document_id,
            version_number=version_number,
            version_date=version_date,
            raw_content=raw_content,
            checksum=checksum,
            change_summary=change_summary,
            created_by=created_by
        )
    
    def get_changes_from_previous(self) -> Optional[str]:
        """
        Get the changes from the previous version.
        
        Returns:
            Optional[str]: Description of changes or None if no previous version
        """
        if not self.document or len(self.document.versions) < 2:
            return None
            
        # The current version is at index 0, so the previous is at 1
        previous_version = self.document.versions[1] if len(self.document.versions) > 1 else None
        
        if not previous_version:
            return None
            
        # This is a simplified diff - in production, you'd want a proper diff algorithm
        if len(self.raw_content) != len(previous_version.raw_content):
            return f"Content length changed from {len(previous_version.raw_content)} to {len(self.raw_content)} characters"
            
        return "Content modified" if self.checksum != previous_version.checksum else "No content changes"
    
    def get_rules_by_type(self, rule_type: str) -> List['Rule']:
        """
        Get all rules of a specific type from this version.
        
        Args:
            rule_type: Type of rules to retrieve
            
        Returns:
            List[Rule]: Matching rules
        """
        return [rule for rule in self.rules if rule.rule_type == rule_type]
