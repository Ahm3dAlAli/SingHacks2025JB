import os
from groq import Groq
from langchain_groq import ChatGroq
from typing import Dict, Any, List
import json
import logging

logger = logging.getLogger(__name__)

class GroqClient:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        
        self.client = Groq(api_key=api_key)
        self.chat_client = ChatGroq(
            groq_api_key=api_key,
            model_name="llama-3.3-70b-versatile",
            temperature=0.1
        )
    
    async def analyze_workflow_selection(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use Groq to analyze and select appropriate workflow"""
        
        prompt = f"""
        As an AML compliance expert, analyze this alert and select the most appropriate remediation workflow.
        
        ALERT DETAILS:
        - Alert ID: {alert_data['alert_id']}
        - Risk Score: {alert_data['risk_score']}/100
        - Severity: {alert_data['severity']}
        - Customer ID: {alert_data['customer_id']}
        - Jurisdiction: {alert_data['jurisdiction']}
        - Triggered Rules: {', '.join(alert_data['triggered_rules'])}
        
        CUSTOMER PROFILE:
        {json.dumps(alert_data.get('customer_profile', {}), indent=2)}
        
        Available Workflows:
        1. CRITICAL_BLOCK_WORKFLOW - For immediate high-risk transactions (risk_score >= 85)
        2. EDD_STANDARD_WORKFLOW - Standard enhanced due diligence (risk_score >= 60)
        3. EDD_PEP_WORKFLOW - For Politically Exposed Persons (PEPs)
        4. CUSTOMER_REVIEW_WORKFLOW - For pattern-based alerts
        5. ENHANCED_MONITORING_WORKFLOW - For lower risk cases needing monitoring
        
        Based on the risk factors, customer profile, and regulatory requirements, select the most appropriate workflow.
        Provide clear rationale for your decision.
        
        Return JSON with:
        - selected_workflow: template key
        - decision_rationale: explanation of choice
        - urgency_level: immediate/high/medium/low
        - estimated_completion_hours: estimated time to complete
        - key_risk_factors: list of primary risk factors
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            result = json.loads(response.choices[0].message.content)
            logger.info(f"Workflow selection completed: {result['selected_workflow']}")
            return result
            
        except Exception as e:
            logger.error(f"Groq workflow selection failed: {e}")
            # Fallback logic
            risk_score = alert_data['risk_score']
            is_pep = alert_data.get('customer_profile', {}).get('is_pep', False)
            
            if risk_score >= 85:
                selected = "CRITICAL_BLOCK_WORKFLOW"
            elif is_pep:
                selected = "EDD_PEP_WORKFLOW"
            elif risk_score >= 60:
                selected = "EDD_STANDARD_WORKFLOW"
            else:
                selected = "ENHANCED_MONITORING_WORKFLOW"
                
            return {
                "selected_workflow": selected,
                "decision_rationale": f"Fallback selection based on risk score {risk_score} and PEP status {is_pep}",
                "urgency_level": "high" if risk_score >= 70 else "medium",
                "estimated_completion_hours": 48,
                "key_risk_factors": ["automated_fallback"]
            }
    
    async def generate_email_content(self, template: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate email content using Groq"""
        
        prompt = f"""
        Generate professional email content for AML compliance communication.
        
        Template: {template}
        Context: {json.dumps(context, indent=2)}
        
        Requirements:
        - Professional and compliant tone
        - Clear explanation of requirements
        - Specific document requests if applicable
        - Deadline information
        - Contact information placeholder
        
        Return JSON with:
        - subject: Email subject line
        - body: Professional email body
        - key_points: List of main points covered
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Groq email generation failed: {e}")
            return {
                "subject": f"AML Compliance Request - {context.get('customer_id', 'Unknown')}",
                "body": f"Dear Customer,\n\nThis is an automated message regarding AML compliance requirements.\n\nPlease contact your relationship manager for details.\n\nBest regards,\nCompliance Team",
                "key_points": ["fallback_generated"]
            }
    
    async def validate_documents(self, documents: List[Dict], customer_context: Dict) -> Dict[str, Any]:
        """Validate documents using AI analysis"""
        
        prompt = f"""
        Validate these AML compliance documents for completeness and authenticity.
        
        Documents to validate:
        {json.dumps(documents, indent=2)}
        
        Customer Context:
        {json.dumps(customer_context, indent=2)}
        
        Validation checklist:
        - Document authenticity and legibility
        - Expiry dates (if applicable)
        - Name matching customer records
        - Address verification
        - Completeness of information
        - Consistency across documents
        - Regulatory compliance
        
        Return JSON with validation results for each document and overall status.
        """
        
        try:
            response = self.client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"Groq document validation failed: {e}")
            return {
                "overall_status": "validation_failed",
                "documents": [],
                "errors": ["AI validation service unavailable"]
            }