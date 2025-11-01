from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any
import json
from datetime import datetime, timedelta

from ..state import WorkflowState, ApprovalStatus
from .approval_manager import ApprovalManager

class ActionExecutor:
    def __init__(self, groq_client, email_service, document_service, approval_manager: ApprovalManager):
        self.groq_client = groq_client
        self.email_service = email_service
        self.document_service = document_service
        self.approval_manager = approval_manager
        
    async def execute_action(self, state: WorkflowState, action: str, parameters: Dict[str, Any]) -> WorkflowState:
        """Execute specific workflow action including approval steps"""
        
        action_result = {
            "action": action,
            "parameters": parameters,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        
        try:
            if action.startswith("wait_"):
                # This is an approval waiting action
                result = await self._handle_approval_action(state, action, parameters)
            elif action == "rm_initiate_edd":
                result = await self._rm_initiate_edd(state, parameters)
            elif action == "rm_pep_acknowledgment":
                result = await self._rm_pep_acknowledgment(state, parameters)
            elif action == "conditional_legal_review":
                result = await self._conditional_legal_review(state, parameters)
            else:
                result = await self._execute_custom_action(state, action, parameters)
            
            action_result.update(result)
            action_result["status"] = "completed"
            action_result["end_time"] = datetime.now().isoformat()
            
        except Exception as e:
            action_result.update({
                "status": "failed",
                "error": str(e),
                "end_time": datetime.now().isoformat()
            })
        
        # Update state with action result
        state["actions_taken"].append(action_result)
        state["updated_at"] = datetime.now()
        
        return state
    
    async def _handle_approval_action(self, state: WorkflowState, action: str, parameters: Dict) -> Dict[str, Any]:
        """Handle approval waiting actions"""
        
        if action == "wait_rm_approval":
            role = "relationship_manager"
        elif action == "wait_compliance_approval":
            role = "compliance_officer"
        elif action == "wait_legal_approval":
            role = "legal"
        else:
            role = "relationship_manager"  # default
        
        # Request approval from the role
        context = {
            "sla": parameters.get("sla", "24h"),
            "workflow_step": state.get("current_step"),
            "risk_factors": state.get("risk_assessment", {}).get("key_risk_factors", []),
            "customer_context": state["customer_profile"]
        }
        
        state = await self.approval_manager.request_approval(state, role, context)
        
        return {
            "action_type": "approval_request",
            "role": role,
            "status": "requested",
            "requested_at": datetime.now().isoformat()
        }
    
    async def _rm_initiate_edd(self, state: WorkflowState, parameters: Dict) -> Dict[str, Any]:
        """Relationship Manager initiates EDD process"""
        
        # Generate EDD initiation request using Groq
        prompt = ChatPromptTemplate.from_template("""
        Create an EDD initiation request for a Relationship Manager.
        
        CUSTOMER: {customer_id}
        RISK SCORE: {risk_score}
        JURISDICTION: {jurisdiction}
        TRIGGERED RULES: {triggered_rules}
        
        The Relationship Manager needs to:
        1. Acknowledge the EDD requirement
        2. Initiate contact with the customer
        3. Coordinate document collection
        4. Provide initial assessment
        
        Create a clear request with context and required actions.
        
        Return JSON with request details.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "customer_id": state["customer_id"],
            "risk_score": state["risk_score"],
            "jurisdiction": state["jurisdiction"],
            "triggered_rules": state["triggered_rules"]
        })
        
        initiation_request = json.loads(response.content)
        
        # Request RM approval
        state = await self.approval_manager.request_approval(
            state, 
            "relationship_manager",
            {
                "action": "initiate_edd",
                "request_details": initiation_request,
                "sla": "24h"
            }
        )
        
        return {
            "action_type": "rm_edd_initiation",
            "status": "approval_requested",
            "initiation_request": initiation_request
        }
    
    async def _rm_pep_acknowledgment(self, state: WorkflowState, parameters: Dict) -> Dict[str, Any]:
        """Relationship Manager acknowledges PEP relationship"""
        
        # Generate PEP acknowledgment request
        prompt = ChatPromptTemplate.from_template("""
        Create a PEP acknowledgment request for a Relationship Manager.
        
        CUSTOMER: {customer_id}
        PEP STATUS: {pep_status}
        RISK LEVEL: {risk_level}
        
        The Relationship Manager must:
        1. Acknowledge the PEP relationship
        2. Confirm they understand enhanced due diligence requirements
        3. Provide any additional context about the relationship
        4. Acknowledge potential reputational risks
        
        Return JSON with acknowledgment request.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "customer_id": state["customer_id"],
            "pep_status": state["customer_profile"].get("is_pep", False),
            "risk_level": state["severity"]
        })
        
        acknowledgment_request = json.loads(response.content)
        
        # Request RM approval
        state = await self.approval_manager.request_approval(
            state,
            "relationship_manager",
            {
                "action": "pep_acknowledgment",
                "request_details": acknowledgment_request,
                "sla": "2h"
            }
        )
        
        return {
            "action_type": "rm_pep_acknowledgment",
            "status": "approval_requested",
            "acknowledgment_request": acknowledgment_request
        }
    
    async def _conditional_legal_review(self, state: WorkflowState, parameters: Dict) -> Dict[str, Any]:
        """Conditionally route to legal review based on criteria"""
        
        should_escalate = await self.approval_manager.should_escalate_to_legal(state)
        
        if should_escalate:
            # Request legal approval
            state = await self.approval_manager.request_approval(
                state,
                "legal",
                {
                    "action": "legal_review",
                    "escalation_reason": "Met criteria for mandatory legal review",
                    "criteria_met": [
                        "High risk score",
                        "PEP customer",
                        "Sanctions triggers",
                        "High-risk jurisdiction",
                        "Large transaction amounts"
                    ],
                    "sla": "72h"
                }
            )
            
            return {
                "action_type": "conditional_legal_escalation",
                "decision": "escalated_to_legal",
                "reason": "Met escalation criteria"
            }
        else:
            # Continue without legal review
            return {
                "action_type": "conditional_legal_escalation",
                "decision": "no_escalation_needed",
                "reason": "Did not meet escalation criteria"
            }