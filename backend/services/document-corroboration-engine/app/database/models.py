from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_size = Column(Integer, nullable=False)
    uploader_id = Column(String(100), nullable=False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(String(20), default="pending")
    
    # Processing results
    extracted_text = Column(Text)
    structure_analysis = Column(JSON)
    format_issues = Column(JSON)
    spelling_errors = Column(JSON)
    missing_sections = Column(JSON)
    image_analysis = Column(JSON)
    
    # Risk assessment
    risk_score = Column(Float, default=0.0)
    risk_level = Column(String(20), default="low")
    
    # Document classification
    document_type = Column(String(50), nullable=True)  # legal, compliance, financial, etc.
    is_relevant = Column(Boolean, default=True)  # Whether document is relevant for review
    has_proof = Column(Boolean, default=False)  # Whether document contains verifiable proof
    proof_details = Column(JSON, default=dict)  # Details about the proof found
    
    # Metadata
    processing_time = Column(Float)
    processed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class AuditTrail(Base):
    __tablename__ = "audit_trails"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    document_id = Column(String(36), nullable=False)
    action = Column(String(100), nullable=False)
    user_id = Column(String(100), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    details = Column(JSON)
    risk_score_change = Column(Float)
    ip_address = Column(String(45))

class ProcessingTemplate(Base):
    __tablename__ = "processing_templates"
    
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    document_type = Column(String(50), nullable=False)
    required_sections = Column(JSON)
    validation_rules = Column(JSON)
    risk_thresholds = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    is_active = Column(Boolean, default=True)