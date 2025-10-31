from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any, List
import json
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..state import WorkflowState
from services.email_service import EmailService
from services.document_service import DocumentService

class ActionExecutor:
    def __init__(self, groq_client, email_service: EmailService, document_service: DocumentService):
        self.groq_client = groq_client
        self.email_service = email_service
        self.document_service = document_service
        self.action_templates = self._load_action_templates()
    
    def _load_action_templates(self) -> Dict[str, Any]:
        """Load action execution templates"""
        return {
            "request_edd_docs": {
                "type": "email",
                "template": "edd_document_request",
                "recipients": ["customer_email", "relationship_manager"],
                "sla": "24h",
                "auto_reminder": True
            },
            "block_transactions": {
                "type": "system",
                "target": "core_banking",
                "action": "block_transactions",
                "sla": "1h",
                "immediate": True
            },
            "notify_critical": {
                "type": "notification", 
                "channels": ["email", "slack", "sms"],
                "recipients": ["senior_management", "compliance_team"],
                "sla": "2h",
                "urgent": True
            }
        }
    
    async def execute_action(self, state: WorkflowState, action: str, parameters: Dict[str, Any]) -> WorkflowState:
        """Execute specific workflow action"""
        
        action_result = {
            "action": action,
            "parameters": parameters,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        
        try:
            if action == "request_edd_docs":
                result = await self._request_edd_documents(state, parameters)
            elif action == "block_transactions":
                result = await self._block_transactions(state, parameters)
            elif action == "notify_critical":
                result = await self._notify_critical_stakeholders(state, parameters)
            elif action == "validate_documents":
                result = await self._validate_documents(state, parameters)
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
        
        # Add to audit trail
        state["audit_trail"].append({
            "timestamp": datetime.now().isoformat(),
            "action": f"action_executed_{action}",
            "details": f"Executed {action} with status {action_result['status']}",
            "user": "system",
            "workflow_instance_id": state["workflow_instance_id"]
        })
        
        return state
    
    async def _request_edd_documents(self, state: WorkflowState, parameters: Dict) -> Dict[str, Any]:
        """Execute EDD document request action"""
        
        # Generate personalized document request using Groq
        prompt = ChatPromptTemplate.from_template("""
        Create a professional document request email for Enhanced Due Diligence.
        
        CUSTOMER: {customer_name}
        CUSTOMER ID: {customer_id}
        RISK LEVEL: {risk_level}
        JURISDICTION: {jurisdiction}
        
        Required documents based on risk assessment:
        {required_docs}
        
        Write a professional, compliant email that:
        1. Explains the regulatory requirement
        2. Lists required documents clearly
        3. Provides submission instructions
        4. Includes deadline (7 days)
        5. Maintains professional tone
        
        Return the email subject and body.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "customer_name": state["customer_profile"].get("name", "Valued Customer"),
            "customer_id": state["customer_id"],
            "risk_level": state["severity"],
            "jurisdiction": state["jurisdiction"],
            "required_docs": json.dumps([
                "Passport copy (certified)",
                "Proof of address (last 3 months)",
                "Source of funds declaration", 
                "Source of wealth documentation",
                "Business registration (if applicable)"
            ], indent=2)
        })
        
        email_content = json.loads(response.content)
        
        # Send email via email service
        email_result = await self.email_service.send_edd_request(
            to=parameters.get("customer_email"),
            subject=email_content["subject"],
            body=email_content["body"],
            cc=parameters.get("relationship_manager")
        )
        
        return {
            "action_type": "email",
            "recipients": [parameters.get("customer_email")],
            "email_subject": email_content["subject"],
            "email_sent": email_result["success"],
            "message_id": email_result.get("message_id")
        }
    
    async def _block_transactions(self, state: WorkflowState, parameters: Dict) -> Dict[str, Any]:
        """Execute transaction blocking action"""
        
        # In production, this would integrate with core banking API
        blocked_transactions = []
        
        for tx_id in state["transaction_ids"]:
            # Simulate API call to core banking system
            block_result = {
                "transaction_id": tx_id,
                "action": "blocked",
                "timestamp": datetime.now().isoformat(),
                "reason": f"AML alert {state['alert_id']}",
                "blocked_by": "system"
            }
            blocked_transactions.append(block_result)
        
        return {
            "action_type": "system_block",
            "transactions_blocked": len(blocked_transactions),
            "block_details": blocked_transactions,
            "system": "core_banking"
        }
    
    async def _validate_documents(self, state: WorkflowState, parameters: Dict) -> Dict[str, Any]:
        """Validate uploaded documents using AI"""
        
        prompt = ChatPromptTemplate.from_template("""
        Validate these EDD documents for compliance requirements:
        
        DOCUMENTS TO VALIDATE:
        {documents}
        
        CUSTOMER CONTEXT:
        {customer_context}
        
        Validation checklist:
        ✓ Document authenticity and legibility
        ✓ Expiry dates (if applicable)  
        ✓ Name matching customer records
        ✓ Address verification
        ✓ Completeness of information
        ✓ Consistency across documents
        
        Return JSON with validation results for each document.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "documents": json.dumps(parameters.get("documents", []), indent=2),
            "customer_context": json.dumps(state["customer_profile"], indent=2)
        })
        
        validation_results = json.loads(response.content)
        
        return {
            "action_type": "document_validation",
            "documents_validated": len(parameters.get("documents", [])),
            "validation_results": validation_results,
            "overall_status": "valid" if all(r.get("valid", False) for r in validation_results) else "invalid"
        }