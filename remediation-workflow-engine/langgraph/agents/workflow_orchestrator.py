from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain.schema import BaseOutputParser
from typing import Dict, List, Any
import json
from datetime import datetime, timedelta
import uuid

from langgraph.graph import StateGraph, END
from ..state import WorkflowState, ApprovalStatus

class WorkflowOrchestrator:
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.workflow_templates = self._load_workflow_templates()
        
    def _load_workflow_templates(self) -> Dict[str, Any]:
        """Load predefined workflow templates with human approval steps"""
        return {
            "CRITICAL_BLOCK_WORKFLOW": {
                "name": "Critical Transaction Blocking",
                "description": "Immediate action for high-risk transactions with rapid approvals",
                "steps": [
                    {"id": "assess_urgency", "action": "assess_critical_risk", "sla": "0h", "auto": True},
                    {"id": "rm_approval_block", "action": "wait_rm_approval", "sla": "1h", "auto": False, "role": "relationship_manager"},
                    {"id": "block_transactions", "action": "block_transactions", "sla": "1h", "auto": True},
                    {"id": "compliance_review", "action": "wait_compliance_approval", "sla": "4h", "auto": False, "role": "compliance_officer"},
                    {"id": "notify_stakeholders", "action": "notify_critical", "sla": "2h", "auto": True}
                ],
                "triggers": ["risk_score >= 85", "sanctions_match", "terrorism_financing"]
            },
            "EDD_STANDARD_WORKFLOW": {
                "name": "Standard Enhanced Due Diligence",
                "description": "Comprehensive customer review with sequential approvals",
                "steps": [
                    {"id": "rm_document_request", "action": "rm_initiate_edd", "sla": "24h", "auto": False, "role": "relationship_manager"},
                    {"id": "document_validation", "action": "validate_documents", "sla": "4h", "auto": True},
                    {"id": "compliance_assessment", "action": "wait_compliance_approval", "sla": "48h", "auto": False, "role": "compliance_officer"},
                    {"id": "legal_review_if_needed", "action": "conditional_legal_review", "sla": "24h", "auto": False, "role": "legal"},
                    {"id": "update_risk_rating", "action": "update_customer_risk", "sla": "2h", "auto": True}
                ],
                "triggers": ["risk_score >= 60", "unusual_behavior", "jurisdiction_risk"]
            },
            "EDD_PEP_WORKFLOW": {
                "name": "PEP Enhanced Due Diligence", 
                "description": "Specialized workflow for Politically Exposed Persons with mandatory legal review",
                "steps": [
                    {"id": "rm_pep_acknowledge", "action": "rm_pep_acknowledgment", "sla": "2h", "auto": False, "role": "relationship_manager"},
                    {"id": "compliance_pep_approval", "action": "wait_compliance_approval", "sla": "24h", "auto": False, "role": "compliance_officer"},
                    {"id": "legal_pep_review", "action": "wait_legal_approval", "sla": "72h", "auto": False, "role": "legal"},
                    {"id": "source_of_wealth", "action": "validate_source_wealth", "sla": "72h", "auto": True},
                    {"id": "final_approval", "action": "wait_compliance_approval", "sla": "24h", "auto": False, "role": "compliance_officer"}
                ],
                "triggers": ["customer_is_pep = true", "risk_score >= 40"]
            },
            "LEGAL_ESCALATION_WORKFLOW": {
                "name": "Legal Escalation Workflow",
                "description": "Mandatory legal review for high-risk or complex cases",
                "steps": [
                    {"id": "rm_assessment", "action": "rm_initial_assessment", "sla": "24h", "auto": False, "role": "relationship_manager"},
                    {"id": "compliance_recommendation", "action": "wait_compliance_approval", "sla": "48h", "auto": False, "role": "compliance_officer"},
                    {"id": "legal_mandatory_review", "action": "wait_legal_approval", "sla": "72h", "auto": False, "role": "legal"},
                    {"id": "final_decision", "action": "executive_decision", "sla": "24h", "auto": False, "role": "compliance_officer"}
                ],
                "triggers": ["risk_score >= 80", "regulatory_violation", "large_amount"]
            }
        }
    
    async def select_workflow_template(self, state: WorkflowState) -> WorkflowState:
        """AI-powered workflow template selection"""
        
        prompt = ChatPromptTemplate.from_template("""
        As an AML compliance expert, analyze this alert and select the most appropriate remediation workflow.
        
        ALERT DETAILS:
        - Alert ID: {alert_id}
        - Risk Score: {risk_score}/100
        - Severity: {severity}
        - Customer Type: {customer_type}
        - PEP Status: {pep_status}
        - Jurisdiction: {jurisdiction}
        - Triggered Rules: {triggered_rules}
        
        CUSTOMER PROFILE:
        {customer_profile}
        
        AVAILABLE WORKFLOWS:
        {workflow_templates}
        
        Based on the risk factors and regulatory requirements, select the most appropriate workflow template.
        Consider: risk level, customer type, jurisdiction requirements, and urgency.
        
        Return JSON with:
        - selected_workflow: template key
        - decision_rationale: explanation of choice
        - urgency_level: immediate/high/medium/low
        - estimated_completion: hours
        """)
        
        chain = prompt | self.groq_client
        response = await chain.ainvoke({
            "alert_id": state["alert_id"],
            "risk_score": state["risk_score"],
            "severity": state["severity"],
            "customer_type": state["customer_profile"].get("customer_type", "unknown"),
            "pep_status": state["customer_profile"].get("is_pep", False),
            "jurisdiction": state["jurisdiction"],
            "triggered_rules": state["triggered_rules"],
            "customer_profile": json.dumps(state["customer_profile"], indent=2),
            "workflow_templates": json.dumps(list(self.workflow_templates.keys()), indent=2)
        })
        
        decision = json.loads(response.content)
        
        # Update state with workflow selection
        state["selected_workflow"] = decision["selected_workflow"]
        state["decision_rationale"] = decision["decision_rationale"]
        state["workflow_template"] = decision["selected_workflow"]
        state["current_step"] = "initialize"
        
        return state
    
    async def initialize_workflow(self, state: WorkflowState) -> WorkflowState:
        """Initialize workflow instance with template and approval states"""
        template = self.workflow_templates[state["selected_workflow"]]
        
        # Generate workflow instance ID
        state["workflow_instance_id"] = f"WF_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        state["created_at"] = datetime.now()
        state["updated_at"] = datetime.now()
        
        # Initialize approval states
        state["rm_approval"] = {
            "status": ApprovalStatus.PENDING.value,
            "requested_at": None,
            "approved_at": None,
            "approved_by": None,
            "notes": None
        }
        
        state["compliance_approval"] = {
            "status": ApprovalStatus.PENDING.value,
            "requested_at": None,
            "approved_at": None, 
            "approved_by": None,
            "notes": None
        }
        
        state["legal_approval"] = {
            "status": ApprovalStatus.PENDING.value,
            "requested_at": None,
            "approved_at": None,
            "approved_by": None,
            "notes": None
        }
        
        state["pending_approvals"] = []
        state["approval_history"] = []
        
        # Set initial assignment based on first step
        first_step = template["steps"][0]
        if not first_step.get("auto", False):
            state["assigned_to"] = first_step.get("role", "relationship_manager")
        else:
            state["assigned_to"] = "system"
        
        # Initialize audit trail
        state["audit_trail"] = [{
            "timestamp": datetime.now().isoformat(),
            "action": "workflow_initialized",
            "details": f"Started {template['name']} for alert {state['alert_id']}",
            "user": "system",
            "workflow_template": state["selected_workflow"]
        }]
        
        return state

    async def check_approval_status(self, state: WorkflowState) -> WorkflowState:
        """Check if current step requires approval and its status"""
        template = self.workflow_templates[state["selected_workflow"]]
        current_step = state.get("current_step")
        
        if not current_step:
            return state
            
        # Find current step definition
        current_step_def = next(
            (step for step in template["steps"] if step["id"] == current_step), 
            None
        )
        
        if not current_step_def or current_step_def.get("auto", True):
            return state
            
        # This is an approval step - check if approved
        role = current_step_def.get("role")
        approval_status = self._get_approval_status(state, role)
        
        if approval_status == ApprovalStatus.APPROVED.value:
            # Approval received, move to next step
            state = await self._move_to_next_step(state, template)
        elif approval_status == ApprovalStatus.REJECTED.value:
            # Approval rejected, handle accordingly
            state = await self._handle_approval_rejection(state, role)
        elif approval_status == ApprovalStatus.ESCALATED.value:
            # Approval escalated
            state = await self._handle_approval_escalation(state, role)
        # If pending, state remains unchanged - waiting for approval
        
        return state
    
    def _get_approval_status(self, state: WorkflowState, role: str) -> str:
        """Get approval status for a specific role"""
        if role == "relationship_manager":
            return state["rm_approval"]["status"]
        elif role == "compliance_officer":
            return state["compliance_approval"]["status"]
        elif role == "legal":
            return state["legal_approval"]["status"]
        return ApprovalStatus.PENDING.value
    
    async def _move_to_next_step(self, state: WorkflowState, template: Dict[str, Any]) -> WorkflowState:
        """Move workflow to next step after approval"""
        current_step = state["current_step"]
        current_index = next(
            i for i, step in enumerate(template["steps"]) 
            if step["id"] == current_step
        )
        
        if current_index + 1 < len(template["steps"]):
            next_step = template["steps"][current_index + 1]
            state["current_step"] = next_step["id"]
            state["step_start_time"] = datetime.now()
            state["step_deadline"] = datetime.now() + timedelta(hours=self._parse_sla(next_step["sla"]))
            
            # Set assignment for next step
            if not next_step.get("auto", False):
                state["assigned_to"] = next_step.get("role", "relationship_manager")
            else:
                state["assigned_to"] = "system"
                
            # Log step transition
            state["audit_trail"].append({
                "timestamp": datetime.now().isoformat(),
                "action": "step_transition",
                "details": f"Moving from {current_step} to {next_step['id']}",
                "user": "system"
            })
        else:
            state["current_step"] = "completed"
            state["step_status"] = "all_steps_completed"
        
        return state
    
    async def _handle_approval_rejection(self, state: WorkflowState, role: str) -> WorkflowState:
        """Handle approval rejection"""
        rejection_notes = self._get_rejection_notes(state, role)
        
        # Log rejection
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": f"{role}_approval_rejected",
            "details": f"Approval rejected by {role}: {rejection_notes}",
            "user": role
        })
        
        # For now, we'll escalate to compliance if RM rejects
        if role == "relationship_manager":
            state["escalation_level"] = state.get("escalation_level", 0) + 1
            state["assigned_to"] = "compliance_officer"
            
            # Update compliance approval to pending
            state["compliance_approval"]["status"] = ApprovalStatus.PENDING.value
            state["compliance_approval"]["requested_at"] = datetime.now().isoformat()
        
        return state
    
    async def _handle_approval_escalation(self, state: WorkflowState, role: str) -> WorkflowState:
        """Handle approval escalation"""
        # Log escalation
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": f"{role}_approval_escalated",
            "details": f"Approval escalated by {role}",
            "user": role
        })
        
        # Move to next appropriate step based on escalation
        if role == "compliance_officer":
            state["assigned_to"] = "legal"
            state["legal_approval"]["status"] = ApprovalStatus.PENDING.value
            state["legal_approval"]["requested_at"] = datetime.now().isoformat()
        
        return state
    
    def _get_rejection_notes(self, state: WorkflowState, role: str) -> str:
        """Get rejection notes for a role"""
        if role == "relationship_manager":
            return state["rm_approval"].get("notes", "No notes provided")
        elif role == "compliance_officer":
            return state["compliance_approval"].get("notes", "No notes provided")
        elif role == "legal":
            return state["legal_approval"].get("notes", "No notes provided")
        return "No notes provided"
    
    def _parse_sla(self, sla_string: str) -> int:
        """Parse SLA string to hours"""
        if sla_string.endswith('h'):
            return int(sla_string[:-1])
        elif sla_string.endswith('d'):
            return int(sla_string[:-1]) * 24
        else:
            return 24  # Default 24 hours