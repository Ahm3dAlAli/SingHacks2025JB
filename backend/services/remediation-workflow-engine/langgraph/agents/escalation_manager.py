from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any
import json
from datetime import datetime, timedelta

from ..state import WorkflowState

class EscalationManager:
    def __init__(self, groq_client, audit_service):
        self.groq_client = groq_client
        self.audit_service = audit_service
        self.escalation_paths = {
            1: "compliance_analyst",
            2: "compliance_team_lead", 
            3: "senior_compliance_officer",
            4: "head_of_compliance",
            5: "chief_risk_officer"
        }
    
    async def check_escalation(self, state: WorkflowState) -> WorkflowState:
        """Check if workflow needs escalation"""
        
        escalation_triggers = await self._assess_escalation_triggers(state)
        
        if escalation_triggers["needs_escalation"]:
            return await self._escalate_workflow(state, escalation_triggers)
        
        return state
    
    async def _assess_escalation_triggers(self, state: WorkflowState) -> Dict[str, Any]:
        """Assess escalation triggers using AI"""
        
        prompt = ChatPromptTemplate.from_template("""
        Assess if this AML workflow needs escalation.
        
        WORKFLOW STATE:
        - Current Step: {current_step}
        - Risk Score: {risk_score}
        - SLA Status: {sla_status}
        - Actions Taken: {actions_count}
        - Failed Actions: {failed_actions}
        - Current Escalation Level: {escalation_level}
        
        ESCALATION TRIGGERS TO CONSIDER:
        - SLA breach (steps taking too long)
        - Multiple failed actions
        - High-risk transactions not resolved
        - Regulatory deadlines approaching
        - Complex investigation required
        
        Return JSON with:
        - needs_escalation: true/false
        - escalation_reason: primary reason if needed
        - recommended_level: suggested escalation level (1-5)
        - urgency: immediate/high/medium/low
        - specific_issues: list of issues requiring attention
        """)
        
        chain = prompt | self.groq_client
        
        # Calculate SLA status
        sla_status = "on_track"
        if state.get("step_deadline") and datetime.now() > state["step_deadline"]:
            sla_status = "breached"
        
        response = await chain.ainvoke({
            "current_step": state.get("current_step", "unknown"),
            "risk_score": state["risk_score"],
            "sla_status": sla_status,
            "actions_count": len(state.get("actions_taken", [])),
            "failed_actions": len([a for a in state.get("actions_taken", []) if a.get("status") == "failed"]),
            "escalation_level": state.get("escalation_level", 0)
        })
        
        return json.loads(response.content)
    
    async def _escalate_workflow(self, state: WorkflowState, escalation_data: Dict[str, Any]) -> WorkflowState:
        """Execute workflow escalation"""
        
        current_level = state.get("escalation_level", 0)
        new_level = escalation_data.get("recommended_level", current_level + 1)
        
        if new_level <= current_level:
            new_level = current_level + 1
        
        # Update escalation level
        state["escalation_level"] = new_level
        state["assigned_to"] = self.escalation_paths.get(new_level, "senior_compliance_officer")
        
        # Log escalation
        await self.audit_service.log_escalation(
            workflow_instance_id=state["workflow_instance_id"],
            escalation_reason=escalation_data.get("escalation_reason", "Automated escalation"),
            level=new_level
        )
        
        # Add to audit trail in state
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "workflow_escalated",
            "details": f"Escalated to level {new_level}: {escalation_data.get('escalation_reason')}",
            "user": "system",
            "metadata": escalation_data
        })
        
        # Generate escalation notification using Groq
        notification = await self._generate_escalation_notification(state, escalation_data)
        state["actions_taken"].append(notification)
        
        return state
    
    async def _generate_escalation_notification(self, state: WorkflowState, escalation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate escalation notification"""
        
        prompt = ChatPromptTemplate.from_template("""
        Create an escalation notification for AML workflow.
        
        WORKFLOW: {workflow_instance_id}
        ESCALATION LEVEL: {escalation_level}
        REASON: {escalation_reason}
        URGENCY: {urgency}
        
        Create a professional notification that:
        - Clearly states the escalation
        - Explains the reason
        - Specifies required actions
        - Includes relevant context
        - Maintains professional tone
        
        Return JSON with notification content.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "workflow_instance_id": state["workflow_instance_id"],
            "escalation_level": state["escalation_level"],
            "escalation_reason": escalation_data.get("escalation_reason"),
            "urgency": escalation_data.get("urgency", "medium")
        })
        
        notification_content = json.loads(response.content)
        
        return {
            "action": "escalation_notification",
            "status": "completed",
            "timestamp": datetime.now().isoformat(),
            "result_data": notification_content
        }