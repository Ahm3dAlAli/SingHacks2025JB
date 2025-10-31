from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from langchain.schema import BaseOutputParser
from typing import Dict, List, Any
import json
from datetime import datetime, timedelta
import uuid

from langgraph.graph import StateGraph, END
from ..state import WorkflowState

class WorkflowOrchestrator:
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.workflow_templates = self._load_workflow_templates()
        
    def _load_workflow_templates(self) -> Dict[str, Any]:
        """Load predefined workflow templates"""
        return {
            "CRITICAL_BLOCK_WORKFLOW": {
                "name": "Critical Transaction Blocking",
                "description": "Immediate action for high-risk transactions",
                "steps": [
                    {"id": "assess_urgency", "action": "assess_critical_risk", "sla": "0h"},
                    {"id": "block_transactions", "action": "block_transactions", "sla": "1h"},
                    {"id": "notify_stakeholders", "action": "notify_critical", "sla": "2h"},
                    {"id": "initiate_investigation", "action": "start_investigation", "sla": "4h"}
                ],
                "triggers": ["risk_score >= 85", "sanctions_match", "terrorism_financing"]
            },
            "EDD_STANDARD_WORKFLOW": {
                "name": "Standard Enhanced Due Diligence",
                "description": "Comprehensive customer review for medium-high risk",
                "steps": [
                    {"id": "request_documents", "action": "request_edd_docs", "sla": "24h"},
                    {"id": "validate_documents", "action": "validate_documents", "sla": "4h"},
                    {"id": "compliance_review", "action": "compliance_assessment", "sla": "48h"},
                    {"id": "update_risk_rating", "action": "update_customer_risk", "sla": "2h"}
                ],
                "triggers": ["risk_score >= 60", "unusual_behavior", "jurisdiction_risk"]
            },
            "EDD_PEP_WORKFLOW": {
                "name": "PEP Enhanced Due Diligence", 
                "description": "Specialized workflow for Politically Exposed Persons",
                "steps": [
                    {"id": "pep_verification", "action": "verify_pep_status", "sla": "2h"},
                    {"id": "senior_approval", "action": "get_senior_approval", "sla": "24h"},
                    {"id": "source_of_wealth", "action": "validate_source_wealth", "sla": "72h"},
                    {"id": "ongoing_monitoring", "action": "setup_enhanced_monitoring", "sla": "48h"}
                ],
                "triggers": ["customer_is_pep = true", "risk_score >= 40"]
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
        """Initialize workflow instance with template"""
        template = self.workflow_templates[state["selected_workflow"]]
        
        # Generate workflow instance ID
        state["workflow_instance_id"] = f"WF_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
        state["created_at"] = datetime.now()
        state["updated_at"] = datetime.now()
        state["assigned_to"] = self._determine_initial_assignment(state)
        
        # Initialize audit trail
        state["audit_trail"] = [{
            "timestamp": datetime.now().isoformat(),
            "action": "workflow_initialized",
            "details": f"Started {template['name']} for alert {state['alert_id']}",
            "user": "system",
            "workflow_template": state["selected_workflow"]
        }]
        
        return state

    def _determine_initial_assignment(self, state: WorkflowState) -> str:
        """Determine initial assignment based on risk and workflow"""
        if state["severity"] == "critical":
            return "senior_compliance_officer"
        elif state["customer_profile"].get("is_pep", False):
            return "compliance_team_lead"
        elif state["risk_score"] >= 70:
            return "compliance_analyst_senior"
        else:
            return "compliance_analyst"