"""
Document model for storing regulatory documents.
"""
from datetime import date, datetime
from typing import Optional, List, TYPE_CHECKING
from enum import Enum

from sqlalchemy import Column, String, Text, Date, Enum as SQLEnum, ForeignKey, Integer, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.document_version import DocumentVersion
    from app.models.rule import Rule
    from app.models.document_source import DocumentSource

class DocumentStatus(str, Enum):
    """Status of a regulatory document."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"
    SUPERSEDED = "SUPERSEDED"

class DocumentType(str, Enum):
    """Type of regulatory document."""
    REGULATION = "REGULATION"
    GUIDELINE = "GUIDELINE"
    CIRCULAR = "CIRCULAR"
    NOTICE = "NOTICE"
    RULE = "RULE"
    OTHER = "OTHER"

class Jurisdiction(str, Enum):
    """Jurisdiction of the regulatory document."""
    HK = "HK"  # Hong Kong
    SG = "SG"  # Singapore
    CH = "CH"  # Switzerland
    UK = "UK"  # United Kingdom
    EU = "EU"  # European Union
    US = "US"  # United States
    OTHER = "OTHER"

class Document(BaseModel):
    """
    Represents a regulatory document from a specific jurisdiction and regulator.
    """
    __tablename__ = "documents"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_id = Column(UUID(as_uuid=True), ForeignKey("document_sources.id"), nullable=True)
    external_id = Column(String(255), index=True)
    title = Column(Text, nullable=False)
    document_type = Column(SQLEnum(DocumentType), nullable=False)
    jurisdiction = Column(SQLEnum(Jurisdiction), nullable=False)
    regulator = Column(String(100), nullable=False)  # e.g., 'HKMA', 'MAS', 'FINMA'
    document_date = Column(Date)
    effective_date = Column(Date)
    expiry_date = Column(Date, nullable=True)
    status = Column(SQLEnum(DocumentStatus), default=DocumentStatus.DRAFT)
    raw_content = Column(Text, nullable=True)  # Raw text content if extracted
    file_path = Column(Text, nullable=True)  # Path to stored file if any
    file_type = Column(String(50), nullable=True)  # 'pdf', 'docx', 'html', etc.
    file_size = Column(Integer, nullable=True)  # Size in bytes
    checksum = Column(String(64), nullable=True)  # For change detection
    metadata = Column(JSONB, default=dict)  # Additional metadata
    
    # Relationships
    source = relationship("DocumentSource", back_populates="documents")
    versions = relationship(
        "DocumentVersion", 
        back_populates="document",
        order_by="desc(DocumentVersion.version_number)",
        cascade="all, delete-orphan"
    )
    rules = relationship(
        "Rule", 
        back_populates="document",
        cascade="all, delete-orphan"
    )
    
    def __repr__(self) -> str:
        return f"<Document(title='{self.title[:50]}...', type='{self.document_type}')>"
    
    @property
    def current_version(self) -> Optional['DocumentVersion']:
        """Get the current version of the document."""
        return self.versions[0] if self.versions else None
    
    @property
    def is_active(self) -> bool:
        """Check if the document is currently active."""
        if self.status != DocumentStatus.ACTIVE:
            return False
            
        today = date.today()
        if self.effective_date and self.effective_date > today:
            return False
            
        if self.expiry_date and self.expiry_date < today:
            return False
            
        return True
    
    def add_version(
        self, 
        version_number: int, 
        version_date: datetime,
        change_summary: Optional[str] = None,
        raw_content: Optional[str] = None,
        checksum: Optional[str] = None
    ) -> 'DocumentVersion':
        """
        Add a new version of the document.
        
        Args:
            version_number: Version number (should increment)
            version_date: When this version was created
            change_summary: Summary of changes in this version
            raw_content: Raw content of this version
            checksum: Checksum of the content
            
        Returns:
            DocumentVersion: The created version
        """
        from app.models.document_version import DocumentVersion
        
        version = DocumentVersion(
            document_id=self.id,
            version_number=version_number,
            version_date=version_date,
            change_summary=change_summary,
            raw_content=raw_content or self.raw_content,
            checksum=checksum or self.checksum
        )
        
        self.versions.insert(0, version)  # Add to beginning to maintain order
        self.updated_at = datetime.utcnow()
        
        # Update document with version data if not set
        if raw_content and not self.raw_content:
            self.raw_content = raw_content
        if checksum and not self.checksum:
            self.checksum = checksum
            
        return version
    
    def get_rules_by_type(self, rule_type: str) -> List['Rule']:
        """
        Get all rules of a specific type from this document.
        
        Args:
            rule_type: Type of rules to retrieve
            
        Returns:
            List[Rule]: Matching rules
        """
        return [rule for rule in self.rules if rule.rule_type == rule_type]
