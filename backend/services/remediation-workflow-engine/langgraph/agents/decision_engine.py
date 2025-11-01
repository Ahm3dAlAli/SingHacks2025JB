from langchain_core.prompts import ChatPromptTemplate
from typing import Dict, Any
import json
from datetime import datetime, timedelta

from ..state import WorkflowState

class DecisionEngine:
    def __init__(self, groq_client):
        self.groq_client = groq_client
    
    async def enrich_context(self, state: WorkflowState) -> WorkflowState:
        """AI-powered context enrichment for decision making"""
        
        prompt = ChatPromptTemplate.from_template("""
        As an AML analyst, enrich the context for this alert by analyzing historical patterns and risk factors.
        
        CURRENT ALERT:
        - Alert ID: {alert_id}
        - Risk Score: {risk_score}
        - Customer: {customer_id}
        - Transactions: {transaction_count}
        - Jurisdiction: {jurisdiction}
        
        CUSTOMER PROFILE:
        {customer_profile}
        
        TRIGGERED RULES:
        {triggered_rules}
        
        Analyze and provide enriched context including:
        1. Historical pattern analysis
        2. Similar past cases
        3. Regulatory implications
        4. Potential risk scenarios
        5. Recommended investigation focus areas
        
        Return JSON with:
        - historical_analysis: patterns and trends
        - similar_cases: references to past similar alerts
        - regulatory_impact: specific regulations affected
        - risk_scenarios: potential money laundering scenarios
        - investigation_focus: priority areas to investigate
        - confidence_score: 0-1 confidence in analysis
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "alert_id": state["alert_id"],
            "risk_score": state["risk_score"],
            "customer_id": state["customer_id"],
            "transaction_count": len(state["transaction_ids"]),
            "jurisdiction": state["jurisdiction"],
            "customer_profile": json.dumps(state["customer_profile"], indent=2),
            "triggered_rules": state["triggered_rules"]
        })
        
        enrichment = json.loads(response.content)
        state["context_enrichment"] = enrichment
        
        return state
    
    async def assess_risk_factors(self, state: WorkflowState) -> WorkflowState:
        """Comprehensive risk factor assessment using Groq"""
        
        prompt = ChatPromptTemplate.from_template("""
        Conduct detailed risk assessment for this AML case.
        
        ALERT CONTEXT:
        {alert_context}
        
        ENRICHED ANALYSIS:
        {enriched_context}
        
        Assess the following risk dimensions (score 0-10 each):
        1. Transaction Risk - unusual patterns, amounts, frequencies
        2. Customer Risk - profile, behavior, history
        3. Jurisdiction Risk - source/destination countries
        4. Product Risk - complexity, anonymity
        5. Behavioral Risk - deviations from normal patterns
        
        Calculate overall risk score and provide:
        - risk_breakdown: scores for each dimension
        - key_risk_indicators: specific red flags
        - mitigation_priority: immediate/short-term/long-term
        - regulatory_urgency: compliance deadlines
        
        Return JSON response.
        """)
        
        chain = prompt | self.groq_client
        
        response = await chain.ainvoke({
            "alert_context": json.dumps({
                "alert_id": state["alert_id"],
                "risk_score": state["risk_score"],
                "severity": state["severity"],
                "customer_id": state["customer_id"],
                "jurisdiction": state["jurisdiction"]
            }, indent=2),
            "enriched_context": json.dumps(state["context_enrichment"], indent=2)
        })
        
        risk_assessment = json.loads(response.content)
        state["risk_assessment"] = risk_assessment
        
        return state