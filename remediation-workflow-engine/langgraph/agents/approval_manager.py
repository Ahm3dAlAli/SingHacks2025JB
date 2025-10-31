from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List
import json
from datetime import datetime
from enum import Enum

from ..state import WorkflowState, ApprovalStatus

class ApprovalManager:
    def __init__(self, groq_client):
        self.groq_client = groq_client
    
    async def request_approval(self, state: WorkflowState, role: str, context: Dict[str, Any]) -> WorkflowState:
        """Request approval from a specific role"""
        
        # Generate approval request using Groq
        approval_request = await self._generate_approval_request(state, role, context)
        
        # Update approval state
        if role == "relationship_manager":
            state["rm_approval"] = {
                "status": ApprovalStatus.PENDING.value,
                "requested_at": datetime.now().isoformat(),
                "request_context": approval_request,
                "approved_at": None,
                "approved_by": None,
                "notes": None
            }
            state["assigned_to"] = "relationship_manager"
            
        elif role == "compliance_officer":
            state["compliance_approval"] = {
                "status": ApprovalStatus.PENDING.value,
                "requested_at": datetime.now().isoformat(),
                "request_context": approval_request,
                "approved_at": None,
                "approved_by": None, 
                "notes": None
            }
            state["assigned_to"] = "compliance_officer"
            
        elif role == "legal":
            state["legal_approval"] = {
                "status": ApprovalStatus.PENDING.value,
                "requested_at": datetime.now().isoformat(),
                "request_context": approval_request,
                "approved_at": None,
                "approved_by": None,
                "notes": None
            }
            state["assigned_to"] = "legal"
        
        # Add to pending approvals
        state["pending_approvals"].append({
            "role": role,
            "requested_at": datetime.now().isoformat(),
            "context": approval_request,
            "workflow_step": state.get("current_step")
        })
        
        # Log approval request
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": f"{role}_approval_requested",
            "details": f"Approval requested from {role} for step {state.get('current_step')}",
            "user": "system",
            "approval_context": approval_request
        })
        
        return state
    
    async def process_approval_response(self, state: WorkflowState, role: str, decision: str, notes: str = None, user: str = None) -> WorkflowState:
        """Process approval response from a role"""
        
        approval_data = {
            "decision": decision,
            "decided_at": datetime.now().isoformat(),
            "decided_by": user or f"{role}_user",
            "notes": notes
        }
        
        if role == "relationship_manager":
            state["rm_approval"].update(approval_data)
            state["rm_approval"]["status"] = decision
            
        elif role == "compliance_officer":
            state["compliance_approval"].update(approval_data)
            state["compliance_approval"]["status"] = decision
            
        elif role == "legal":
            state["legal_approval"].update(approval_data)
            state["legal_approval"]["status"] = decision
        
        # Remove from pending approvals
        state["pending_approvals"] = [
            approval for approval in state["pending_approvals"]
            if approval["role"] != role
        ]
        
        # Add to approval history
        state["approval_history"].append({
            "role": role,
            "decision": decision,
            "timestamp": datetime.now().isoformat(),
            "user": user or f"{role}_user",
            "notes": notes,
            "workflow_step": state.get("current_step")
        })
        
        # Log approval decision
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": f"{role}_approval_{decision}",
            "details": f"Approval {decision} by {user or role}",
            "user": user or role,
            "notes": notes
        })
        
        return state
    
    async def _generate_approval_request(self, state: WorkflowState, role: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate approval request content using Groq"""
        
        prompt = ChatPromptTemplate.from_template("""
        Create a professional approval request for {role} in an AML compliance workflow.
        
        WORKFLOW CONTEXT:
        - Workflow: {workflow_name}
        - Alert ID: {alert_id}
        - Customer: {customer_id}
        - Risk Score: {risk_score}
        - Current Step: {current_step}
        
        SPECIFIC CONTEXT:
        {specific_context}
        
        Create a clear, professional approval request that:
        1. Explains what needs approval
        2. Provides necessary context and risk assessment
        3. States the deadline (SLA: {sla})
        4. Explains consequences of approval/rejection
        5. Provides clear options for response
        
        Return JSON with approval request content.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "role": role,
            "workflow_name": state["selected_workflow"],
            "alert_id": state["alert_id"],
            "customer_id": state["customer_id"],
            "risk_score": state["risk_score"],
            "current_step": state.get("current_step", "unknown"),
            "specific_context": json.dumps(context, indent=2),
            "sla": context.get("sla", "24 hours")
        })
        
        return json.loads(response.content)
    
    def get_approval_summary(self, state: WorkflowState) -> Dict[str, Any]:
        """Get summary of all approval statuses"""
        return {
            "relationship_manager": state["rm_approval"],
            "compliance_officer": state["compliance_approval"],
            "legal": state["legal_approval"],
            "pending_approvals": state["pending_approvals"],
            "approval_history": state["approval_history"]
        }
    
    async def should_escalate_to_legal(self, state: WorkflowState) -> bool:
        """Determine if case should be escalated to legal based on criteria"""
        
        criteria = [
            state["risk_score"] >= 80,
            state["customer_profile"].get("is_pep", False),
            "SANCTIONS" in state["triggered_rules"],
            state["jurisdiction"] in ["IR", "KP", "SY"],  # High-risk jurisdictions
            any(amount > 1000000 for amount in state.get("transaction_amounts", [])),  # Large amounts
        ]
        
        return any(criteria)