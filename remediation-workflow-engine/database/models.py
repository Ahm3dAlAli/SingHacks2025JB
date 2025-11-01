from sqlalchemy import Column, String, Integer, Float, DateTime, Boolean, JSON, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class WorkflowInstance(Base):
    __tablename__ = "workflow_instances"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    alert_id = Column(String, nullable=False, index=True)
    workflow_template = Column(String, nullable=False)
    status = Column(String, default="active")  # active, completed, escalated, failed
    current_step = Column(String, default="initialize")
    risk_score = Column(Float, nullable=False)
    severity = Column(String, nullable=False)
    customer_id = Column(String, nullable=False, index=True)
    jurisdiction = Column(String, nullable=False)
    
    # Workflow state
    state_data = Column(JSON, default=dict)
    selected_workflow = Column(String)
    decision_rationale = Column(Text)
    
    # Assignment & tracking
    assigned_to = Column(String)
    escalation_level = Column(Integer, default=0)
    sla_breach = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    actions = relationship("WorkflowAction", back_populates="workflow", cascade="all, delete-orphan")
    audit_entries = relationship("AuditEntry", back_populates="workflow", cascade="all, delete-orphan")

class WorkflowAction(Base):
    __tablename__ = "workflow_actions"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_instance_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    action_type = Column(String, nullable=False)
    action_name = Column(String, nullable=False)
    parameters = Column(JSON, default=dict)
    status = Column(String, default="pending")  # pending, in_progress, completed, failed
    result_data = Column(JSON, default=dict)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Relationships
    workflow = relationship("WorkflowInstance", back_populates="actions")

class AuditEntry(Base):
    __tablename__ = "audit_entries"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_instance_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    action = Column(String, nullable=False)
    user = Column(String, default="system")
    details = Column(Text)
    metadata = Column(JSON, default=dict)
    
    # Relationships
    workflow = relationship("WorkflowInstance", back_populates="audit_entries")

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    workflow_instance_id = Column(String, ForeignKey("workflow_instances.id"), nullable=False)
    document_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_path = Column(String)
    status = Column(String, default="pending")  # pending, validated, rejected
    validation_result = Column(JSON, default=dict)
    
    # Timestamps
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    validated_at = Column(DateTime)
    
    # Relationships
    workflow = relationship("WorkflowInstance")

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(String, primary_key=True, default=generate_uuid)
    template_name = Column(String, nullable=False, unique=True)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    variables = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)