from typing import Dict, List, Optional, Any, Annotated
from typing_extensions import TypedDict
from datetime import datetime
from langgraph.graph import add_messages

class WorkflowState(TypedDict):
    # Input from alert system
    alert_id: str
    risk_score: float
    severity: str
    customer_id: str
    transaction_ids: List[str]
    triggered_rules: List[str]
    customer_profile: Dict[str, Any]
    jurisdiction: str
    alert_type: str
    
    # Workflow execution state
    workflow_instance_id: str
    workflow_template: str
    current_step: str
    step_status: str
    step_start_time: datetime
    step_deadline: datetime
    
    # Decision engine outputs
    selected_workflow: str
    risk_assessment: Dict[str, Any]
    context_enrichment: Dict[str, Any]
    decision_rationale: str
    
    # Action execution
    actions_taken: List[Dict[str, Any]]
    pending_actions: List[Dict[str, Any]]
    action_results: List[Dict[str, Any]]
    
    # Compliance & Audit
    compliance_checks: List[Dict[str, Any]]
    audit_trail: List[Dict[str, Any]]
    regulatory_references: List[str]
    
    # Escalation & Resolution
    escalation_level: int
    assigned_to: str
    resolution_status: str
    resolution_notes: Optional[str]
    
    # Groq AI responses
    ai_analysis: Annotated[List[str], add_messages]
    ai_recommendations: List[str]
    
    # System metadata
    created_at: datetime
    updated_at: datetime
    sla_breach: bool