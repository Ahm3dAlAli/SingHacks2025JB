from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class SeverityLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class WorkflowStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ESCALATED = "escalated"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ActionStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class AlertRequest(BaseModel):
    alert_id: str = Field(..., description="Unique identifier for the alert")
    risk_score: float = Field(..., ge=0, le=100, description="Risk score from 0-100")
    severity: SeverityLevel = Field(..., description="Alert severity level")
    customer_id: str = Field(..., description="Unique customer identifier")
    transaction_ids: List[str] = Field(..., description="List of related transaction IDs")
    triggered_rules: List[str] = Field(..., description="List of AML rules that were triggered")
    customer_profile: Dict[str, Any] = Field(
        default_factory=dict,
        description="Customer profile information"
    )
    jurisdiction: str = Field(..., description="Jurisdiction code (e.g., CH, SG, HK)")
    alert_type: str = Field(..., description="Type of alert")
    additional_context: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional context for the alert"
    )

    @validator('risk_score')
    def validate_risk_score(cls, v):
        if not 0 <= v <= 100:
            raise ValueError('Risk score must be between 0 and 100')
        return v

    @validator('transaction_ids')
    def validate_transaction_ids(cls, v):
        if not v:
            raise ValueError('At least one transaction ID is required')
        return v

    @validator('triggered_rules')
    def validate_triggered_rules(cls, v):
        if not v:
            raise ValueError('At least one triggered rule is required')
        return v

class WorkflowStartResponse(BaseModel):
    workflow_instance_id: str = Field(..., description="Unique workflow instance ID")
    alert_id: str = Field(..., description="Original alert ID")
    status: WorkflowStatus = Field(..., description="Initial workflow status")
    selected_workflow: str = Field(..., description="Selected workflow template")
    assigned_to: str = Field(..., description="Initial assignment")
    decision_rationale: str = Field(..., description="AI decision rationale")
    estimated_completion_hours: int = Field(..., description="Estimated completion time in hours")
    created_at: datetime = Field(..., description="Workflow creation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WorkflowStatusResponse(BaseModel):
    workflow_instance_id: str = Field(..., description="Unique workflow instance ID")
    alert_id: str = Field(..., description="Original alert ID")
    status: WorkflowStatus = Field(..., description="Current workflow status")
    current_step: str = Field(..., description="Current workflow step")
    progress: float = Field(..., ge=0, le=100, description="Progress percentage")
    selected_workflow: str = Field(..., description="Selected workflow template")
    risk_score: float = Field(..., description="Current risk score")
    severity: SeverityLevel = Field(..., description="Current severity level")
    escalation_level: int = Field(..., ge=0, description="Current escalation level")
    assigned_to: str = Field(..., description="Currently assigned to")
    sla_breach: bool = Field(..., description="Whether SLA is breached")
    created_at: datetime = Field(..., description="Workflow creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    next_deadline: Optional[datetime] = Field(..., description="Next step deadline")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WorkflowActionRequest(BaseModel):
    action: str = Field(..., description="Action to execute")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action parameters"
    )
    user: str = Field(..., description="User executing the action")
    notes: Optional[str] = Field(None, description="Additional notes")

class WorkflowActionResponse(BaseModel):
    action_id: str = Field(..., description="Unique action ID")
    workflow_instance_id: str = Field(..., description="Workflow instance ID")
    action: str = Field(..., description="Action executed")
    status: ActionStatus = Field(..., description="Action status")
    result_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Action result data"
    )
    executed_by: str = Field(..., description="User who executed the action")
    executed_at: datetime = Field(..., description="Execution timestamp")
    completion_time: Optional[datetime] = Field(..., description="Completion timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class AuditEntryResponse(BaseModel):
    id: str = Field(..., description="Audit entry ID")
    workflow_instance_id: str = Field(..., description="Workflow instance ID")
    timestamp: datetime = Field(..., description="Audit timestamp")
    action: str = Field(..., description="Audited action")
    user: str = Field(..., description="User who performed the action")
    details: str = Field(..., description="Action details")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WorkflowListResponse(BaseModel):
    workflows: List[WorkflowStatusResponse] = Field(..., description="List of workflows")
    total_count: int = Field(..., description="Total number of workflows")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Page size")
    total_pages: int = Field(..., description="Total number of pages")

class ErrorResponse(BaseModel):
    error: str = Field(..., description="Error message")
    code: str = Field(..., description="Error code")
    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error details"
    )
    timestamp: datetime = Field(..., description="Error timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class DocumentUploadRequest(BaseModel):
    document_type: str = Field(..., description="Type of document")
    file_name: str = Field(..., description="Original file name")
    description: Optional[str] = Field(None, description="Document description")

class DocumentResponse(BaseModel):
    document_id: str = Field(..., description="Unique document ID")
    workflow_instance_id: str = Field(..., description="Workflow instance ID")
    document_type: str = Field(..., description="Type of document")
    file_name: str = Field(..., description="Stored file name")
    original_name: str = Field(..., description="Original file name")
    status: str = Field(..., description="Document status")
    validation_result: Dict[str, Any] = Field(
        default_factory=dict,
        description="Validation results"
    )
    uploaded_at: datetime = Field(..., description="Upload timestamp")
    validated_at: Optional[datetime] = Field(..., description="Validation timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class WorkflowStepUpdate(BaseModel):
    step_name: str = Field(..., description="Step to update")
    status: ActionStatus = Field(..., description="New status")
    notes: Optional[str] = Field(None, description="Update notes")
    result_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Step result data"
    )

class WorkflowSearchFilters(BaseModel):
    status: Optional[WorkflowStatus] = Field(None, description="Filter by status")
    severity: Optional[SeverityLevel] = Field(None, description="Filter by severity")
    customer_id: Optional[str] = Field(None, description="Filter by customer ID")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned user")
    created_after: Optional[datetime] = Field(None, description="Filter by creation date")
    created_before: Optional[datetime] = Field(None, description="Filter by creation date")
    jurisdiction: Optional[str] = Field(None, description="Filter by jurisdiction")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class SystemMetricsResponse(BaseModel):
    total_workflows: int = Field(..., description="Total workflows")
    active_workflows: int = Field(..., description="Active workflows")
    completed_today: int = Field(..., description="Workflows completed today")
    average_completion_time_hours: float = Field(..., description="Average completion time")
    sla_breach_count: int = Field(..., description="Number of SLA breaches")
    workflow_distribution: Dict[str, int] = Field(
        ...,
        description="Distribution by workflow type"
    )
    risk_distribution: Dict[str, int] = Field(
        ...,
        description="Distribution by risk level"
    )
    timestamp: datetime = Field(..., description="Metrics timestamp")

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }