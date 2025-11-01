from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any
import json
from datetime import datetime

from ..state import WorkflowState

class ComplianceChecker:
    def __init__(self, groq_client):
        self.groq_client = groq_client
        self.regulatory_frameworks = {
            "CH": ["FINMA", "Swiss AML Act"],
            "SG": ["MAS", "Singapore AML Regulations"], 
            "HK": ["HKMA", "Hong Kong AML Ordinance"]
        }
    
    async def verify_compliance(self, state: WorkflowState) -> WorkflowState:
        """Verify workflow compliance with regulatory requirements"""
        
        jurisdiction = state["jurisdiction"]
        frameworks = self.regulatory_frameworks.get(jurisdiction, ["FATF", "International Standards"])
        
        prompt = ChatPromptTemplate.from_template("""
        Verify AML compliance for this workflow execution.
        
        WORKFLOW DETAILS:
        - Workflow: {workflow_template}
        - Jurisdiction: {jurisdiction}
        - Regulatory Frameworks: {frameworks}
        - Customer Type: {customer_type}
        - Risk Level: {risk_level}
        
        WORKFLOW ACTIONS:
        {workflow_actions}
        
        Verify compliance with:
        1. Documentation requirements
        2. Timeline adherence (SLA)
        3. Escalation procedures
        4. Record keeping
        5. Regulatory reporting requirements
        
        Return JSON with:
        - overall_compliant: true/false
        - compliance_checks: list of specific checks with status
        - regulatory_references: specific regulations referenced
        - recommendations: any compliance improvements needed
        - audit_ready: true/false (whether workflow is ready for audit)
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "workflow_template": state["selected_workflow"],
            "jurisdiction": jurisdiction,
            "frameworks": json.dumps(frameworks, indent=2),
            "customer_type": state["customer_profile"].get("customer_type", "unknown"),
            "risk_level": state["severity"],
            "workflow_actions": json.dumps(state.get("actions_taken", []), indent=2)
        })
        
        compliance_result = json.loads(response.content)
        state["compliance_checks"] = compliance_result.get("compliance_checks", [])
        state["regulatory_references"] = compliance_result.get("regulatory_references", [])
        
        # Add to audit trail
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "compliance_verification",
            "details": f"Compliance check completed: {compliance_result.get('overall_compliant', False)}",
            "user": "system",
            "metadata": compliance_result
        })
        
        return state
    
    async def generate_compliance_report(self, state: WorkflowState) -> Dict[str, Any]:
        """Generate comprehensive compliance report"""
        
        prompt = ChatPromptTemplate.from_template("""
        Generate a regulatory compliance report for this AML workflow.
        
        WORKFLOW EXECUTION:
        {workflow_summary}
        
        COMPLIANCE CHECKS:
        {compliance_checks}
        
        Create a professional compliance report suitable for regulatory examination.
        Include:
        - Executive summary
        - Regulatory framework alignment
        - Documentation completeness
        - Timeline adherence
        - Risk assessment validity
        - Recommendations for improvement
        
        Return JSON report.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "workflow_summary": json.dumps({
                "workflow_instance_id": state["workflow_instance_id"],
                "alert_id": state["alert_id"],
                "workflow_template": state["selected_workflow"],
                "jurisdiction": state["jurisdiction"],
                "start_time": state["created_at"].isoformat(),
                "completion_time": datetime.now().isoformat()
            }, indent=2),
            "compliance_checks": json.dumps(state.get("compliance_checks", []), indent=2)
        })
        
        return json.loads(response.content)