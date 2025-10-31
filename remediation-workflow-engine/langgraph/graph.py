from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from typing import Dict, Any
import asyncio

from .state import WorkflowState
from .agents.workflow_orchestrator import WorkflowOrchestrator
from .agents.decision_engine import DecisionEngine
from .agents.action_executor import ActionExecutor
from .agents.approval_manager import ApprovalManager
from .agents.compliance_checker import ComplianceChecker
from .agents.escalation_manager import EscalationManager

import json
from datetime import datetime, timedelta
from langchain_core.prompts import ChatPromptTemplate


class RemediationWorkflowGraph:
    def __init__(self, groq_client, email_service, document_service, audit_service):
        self.groq_client = groq_client
        self.workflow_orchestrator = WorkflowOrchestrator(groq_client)
        self.decision_engine = DecisionEngine(groq_client)
        self.approval_manager = ApprovalManager(groq_client)
        self.action_executor = ActionExecutor(groq_client, email_service, document_service, self.approval_manager)
        self.compliance_checker = ComplianceChecker(groq_client)
        self.escalation_manager = EscalationManager(groq_client, audit_service)
        
        
        # Build the graph
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow with approval steps"""
        workflow = StateGraph(WorkflowState)
        
        # Define nodes
        workflow.add_node("receive_alert", self._receive_alert)
        workflow.add_node("enrich_context", self.decision_engine.enrich_context)
        workflow.add_node("assess_risk", self.decision_engine.assess_risk_factors)
        workflow.add_node("select_workflow", self.workflow_orchestrator.select_workflow_template)
        workflow.add_node("initialize_workflow", self.workflow_orchestrator.initialize_workflow)
        workflow.add_node("execute_workflow", self._execute_workflow_steps)
        workflow.add_node("check_approvals", self.workflow_orchestrator.check_approval_status)
        workflow.add_node("check_compliance", self.compliance_checker.verify_compliance)
        workflow.add_node("handle_escalation", self.escalation_manager.check_escalation)
        workflow.add_node("finalize_workflow", self._finalize_workflow)
        
        # Define edges
        workflow.set_entry_point("receive_alert")
        
        workflow.add_edge("receive_alert", "enrich_context")
        workflow.add_edge("enrich_context", "assess_risk")
        workflow.add_edge("assess_risk", "select_workflow")
        workflow.add_edge("select_workflow", "initialize_workflow")
        workflow.add_edge("initialize_workflow", "execute_workflow")
        
        # Conditional edges from workflow execution
        workflow.add_conditional_edges(
            "execute_workflow",
            self._should_wait_for_approval,
            {
                "wait_approval": "check_approvals",
                "continue": "check_compliance",
                "escalate": "handle_escalation",
                "complete": "finalize_workflow"
            }
        )
        
        workflow.add_conditional_edges(
            "check_approvals",
            self._approval_status_check,
            {
                "approved": "execute_workflow",
                "rejected": "handle_escalation",
                "pending": "check_approvals"  # Wait longer
            }
        )
        
        workflow.add_edge("handle_escalation", "execute_workflow")
        workflow.add_edge("check_compliance", "finalize_workflow")
        workflow.add_edge("finalize_workflow", END)
        
        return workflow.compile()
    
    def _should_wait_for_approval(self, state: WorkflowState) -> str:
        """Determine if workflow should wait for approval"""
        
        # Check if current step requires approval
        template = self.workflow_orchestrator.workflow_templates[state["selected_workflow"]]
        current_step = state.get("current_step")
        
        if not current_step or current_step == "completed":
            return "complete"
            
        current_step_def = next(
            (step for step in template["steps"] if step["id"] == current_step), 
            None
        )
        
        if not current_step_def:
            return "complete"
            
        # Check if this is an approval step
        if not current_step_def.get("auto", True):
            role = current_step_def.get("role")
            approval_status = self.workflow_orchestrator._get_approval_status(state, role)
            
            if approval_status == "pending":
                return "wait_approval"
            elif approval_status == "rejected":
                return "escalate"
            elif approval_status == "approved":
                return "continue"
        
        return "continue"
    
    def _approval_status_check(self, state: WorkflowState) -> str:
        """Check approval status and determine next step"""
        
        # Check if any approvals are still pending
        pending_approvals = state.get("pending_approvals", [])
        if pending_approvals:
            # Check if any SLA breaches
            for approval in pending_approvals:
                requested_at = datetime.fromisoformat(approval["requested_at"].replace('Z', '+00:00'))
                if datetime.now() - requested_at > timedelta(hours=24):  # 24h SLA
                    return "escalate"
            
            return "pending"  # Continue waiting
        
        return "approved"  # All approvals received
    
    async def _receive_alert(self, state: WorkflowState) -> WorkflowState:
        """Receive and validate alert input"""
        print(f"📥 Received alert: {state['alert_id']}")
        
        # Validate required fields
        required_fields = ['alert_id', 'risk_score', 'customer_id', 'triggered_rules']
        for field in required_fields:
            if not state.get(field):
                raise ValueError(f"Missing required field: {field}")
        
        # Initialize action tracking
        state["actions_taken"] = []
        state["pending_actions"] = []
        state["action_results"] = []
        state["compliance_checks"] = []
        state["audit_trail"] = []
        state["regulatory_references"] = []
        state["ai_recommendations"] = []
        
        return state
    
    async def _execute_workflow_steps(self, state: WorkflowState) -> WorkflowState:
        """Execute workflow steps based on selected template"""
        template = self.workflow_orchestrator.workflow_templates[state["selected_workflow"]]
        
        # Get current step
        current_step = state.get("current_step", "initialize")
        
        if current_step == "initialize":
            # Start with first step
            next_step = template["steps"][0]
            state["current_step"] = next_step["id"]
            state["step_start_time"] = datetime.now()
            state["step_deadline"] = datetime.now() + timedelta(hours=self._parse_sla(next_step["sla"]))
        
        # Execute current step
        current_step_def = next((step for step in template["steps"] if step["id"] == state["current_step"]), None)
        
        if current_step_def:
            # Execute the action
            state = await self.action_executor.execute_action(
                state, 
                current_step_def["action"],
                {"workflow_step": current_step_def["id"]}
            )
            
            # Move to next step or complete
            current_index = template["steps"].index(current_step_def)
            if current_index + 1 < len(template["steps"]):
                next_step = template["steps"][current_index + 1]
                state["current_step"] = next_step["id"]
                state["step_start_time"] = datetime.now()
                state["step_deadline"] = datetime.now() + timedelta(hours=self._parse_sla(next_step["sla"]))
            else:
                state["current_step"] = "completed"
                state["step_status"] = "all_steps_completed"
        
        return state
    
    def _should_escalate(self, state: WorkflowState) -> str:
        """Determine if workflow should escalate"""
        if state.get("escalation_level", 0) >= 3:
            return "complete"  # Max escalation reached
        
        # Check for escalation triggers
        escalation_triggers = [
            state.get("sla_breach", False),
            len([a for a in state.get("actions_taken", []) if a.get("status") == "failed"]) >= 2,
            state.get("risk_score", 0) >= 85,
            state.get("customer_profile", {}).get("is_pep", False) and state.get("escalation_level", 0) == 0
        ]
        
        if any(escalation_triggers):
            return "escalate"
        elif state.get("current_step") == "completed":
            return "complete"
        else:
            return "continue"
    
    async def _finalize_workflow(self, state: WorkflowState) -> WorkflowState:
        """Finalize workflow and generate report"""
        
        # Generate completion report using Groq
        prompt = ChatPromptTemplate.from_template("""
        Generate a comprehensive workflow completion report for this AML remediation case.
        
        WORKFLOW EXECUTION SUMMARY:
        {workflow_summary}
        
        ACTIONS TAKEN:
        {actions_taken}
        
        COMPLIANCE CHECKS:
        {compliance_checks}
        
        Create a professional report including:
        1. Executive summary
        2. Risk assessment findings
        3. Actions completed
        4. Compliance status
        5. Recommendations for ongoing monitoring
        6. Regulatory compliance statement
        
        Return JSON report.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "workflow_summary": json.dumps({
                "workflow_instance_id": state["workflow_instance_id"],
                "alert_id": state["alert_id"],
                "workflow_template": state["selected_workflow"],
                "start_time": state["created_at"].isoformat(),
                "completion_time": datetime.now().isoformat(),
                "total_steps": len(state["actions_taken"])
            }, indent=2),
            "actions_taken": json.dumps(state["actions_taken"], indent=2),
            "compliance_checks": json.dumps(state["compliance_checks"], indent=2)
        })
        
        completion_report = json.loads(response.content)
        
        # Update final state
        state["resolution_status"] = "completed"
        state["resolution_notes"] = completion_report.get("executive_summary", "")
        state["updated_at"] = datetime.now()
        
        # Final audit entry
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "workflow_completed",
            "details": f"Workflow {state['workflow_instance_id']} completed successfully",
            "user": "system",
            "completion_report": completion_report
        })
        
        return state
    
    def _parse_sla(self, sla_string: str) -> int:
        """Parse SLA string to hours"""
        if sla_string.endswith('h'):
            return int(sla_string[:-1])
        elif sla_string.endswith('d'):
            return int(sla_string[:-1]) * 24
        else:
            return 24  # Default 24 hours
    
    async def process_alert(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Main entry point to process an alert through the workflow"""
        initial_state = WorkflowState(**alert_data)
        final_state = await self.graph.ainvoke(initial_state)
        return final_state