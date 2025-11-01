"""
Agent 5: Explainer
Generates audit-ready natural language explanations for transaction risk assessments using Groq LLM.

This agent takes complete analysis results and produces:
- Professional explanation (2-4 sentences)
- Specific regulatory citations
- Evidence from transaction data
- Recommended compliance actions
- Confidence level
"""

from typing import Dict, Any, List
from datetime import datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Transaction, AgentExecutionLog
from app.database.queries import save_agent_log
from app.api.models import RuleViolation, BehavioralFlag
from app.services.groq_client import get_groq_client, GroqAPIError
from app.utils.logger import logger


async def explainer_agent(
    transaction: Transaction,
    session: AsyncSession,
    risk_score: int,
    alert_level: str,
    static_violations: List[RuleViolation],
    behavioral_flags: List[BehavioralFlag],
) -> Dict[str, Any]:
    """
    Agent 5: Explainer
    Generate audit-ready explanation for transaction risk assessment.

    This agent:
    1. Takes complete analysis results (risk score, violations, flags)
    2. Generates professional 2-4 sentence explanation
    3. Cites specific regulatory rules violated
    4. Lists evidence from transaction data
    5. Recommends compliance action (HOLD/EDD/STR/MONITOR)
    6. Assigns confidence level (HIGH/MEDIUM/LOW)

    Args:
        transaction: Transaction that was analyzed
        session: Database session for logging
        risk_score: Final risk score (0-100)
        alert_level: Alert classification (CRITICAL/HIGH/MEDIUM/LOW)
        static_violations: Rule violations detected by Agent 2
        behavioral_flags: Behavioral patterns detected by Agent 3

    Returns:
        Dictionary with:
        - explanation: Natural language explanation (2-4 sentences)
        - regulatory_basis: List of specific rules cited
        - evidence: List of red flags from transaction
        - recommended_action: Compliance action to take
        - confidence: Confidence level (HIGH/MEDIUM/LOW)

    Example:
        >>> result = await explainer_agent(transaction, session, 85, "CRITICAL", violations, flags)
        >>> result["recommended_action"]
        "ENHANCED_DUE_DILIGENCE"
    """
    start_time = datetime.utcnow()
    groq_client = get_groq_client()

    try:
        logger.info(
            f"Starting explainer agent for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "risk_score": risk_score,
                    "alert_level": alert_level,
                    "violations_count": len(static_violations),
                    "flags_count": len(behavioral_flags),
                }
            },
        )

        # Build transaction summary
        transaction_summary = f"""
- ID: {transaction.transaction_id}
- Amount: {float(transaction.amount):,.2f} {transaction.currency}
- Customer: {transaction.customer_id} (Risk: {transaction.customer_risk_rating or 'Unknown'}, PEP: {transaction.customer_is_pep})
- Route: {transaction.originator_country or 'N/A'} → {transaction.beneficiary_country or 'N/A'}
- Channel: {transaction.channel or 'Unknown'}
- Jurisdiction: {transaction.booking_jurisdiction}
""".strip()

        # Build violations summary
        violations_summary = []
        for v in static_violations:
            violations_summary.append(f"- {v.rule_id}: {v.description} (Score: {v.score}, Severity: {v.severity})")

        # Build behavioral flags summary
        flags_summary = []
        for f in behavioral_flags:
            flags_summary.append(f"- {f.flag_type}: {f.description} (Score: {f.score}, Severity: {f.severity})")

        # Build prompt
        system_prompt = "You are an experienced AML compliance officer writing an audit report. Generate clear, professional explanations for transaction alerts that are suitable for regulatory review."

        user_prompt = f"""Generate an audit-ready explanation for this transaction alert.

Transaction Details:
{transaction_summary}

Analysis Results:
- Risk Score: {risk_score}/100
- Alert Level: {alert_level}

Rules Violated ({len(static_violations)}):
{chr(10).join(violations_summary) if violations_summary else "None"}

Behavioral Flags ({len(behavioral_flags)}):
{chr(10).join(flags_summary) if flags_summary else "None"}

Provide:
1. EXPLANATION: Why was this transaction flagged? Write 2-4 professional sentences explaining the risk. Be specific about amounts, thresholds, and customer context.
2. REGULATORY_BASIS: List specific regulations violated (use the rule_ids from violations)
3. EVIDENCE: List specific transaction characteristics that triggered the alert
4. RECOMMENDED_ACTION: Choose ONE of:
   - HOLD_TRANSACTION (for CRITICAL alerts with sanctions/fraud indicators)
   - ENHANCED_DUE_DILIGENCE (for HIGH/CRITICAL alerts requiring investigation)
   - FILE_STR (Suspicious Transaction Report - for confirmed suspicious activity)
   - MONITORING_ONLY (for MEDIUM/LOW alerts or informational)
5. CONFIDENCE: HIGH (clear violations), MEDIUM (some ambiguity), or LOW (borderline case)

Return ONLY valid JSON (no markdown, no explanation):
{{
  "explanation": "Professional 2-4 sentence explanation...",
  "regulatory_basis": ["RULE-001: Description", "RULE-002: Description"],
  "evidence": ["Specific red flag 1", "Specific red flag 2"],
  "recommended_action": "ACTION",
  "confidence": "HIGH|MEDIUM|LOW"
}}

Be precise with numbers and percentages. Use a formal, compliance-ready tone."""

        # Call Groq API
        parsed_response = await groq_client.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=settings.GROQ_EXPLAINER_TEMPERATURE,
            max_tokens=settings.GROQ_EXPLAINER_MAX_TOKENS,
            timeout=settings.GROQ_EXPLAINER_TIMEOUT,
        )

        # Validate response structure
        required_fields = ["explanation", "regulatory_basis", "evidence", "recommended_action", "confidence"]
        for field in required_fields:
            if field not in parsed_response:
                logger.warning(
                    f"Missing field '{field}' in explainer response",
                    extra={
                        "extra_data": {
                            "transaction_id": str(transaction.transaction_id),
                            "missing_field": field,
                        }
                    },
                )
                # Provide defaults
                if field == "explanation":
                    parsed_response[field] = f"Transaction flagged with risk score {risk_score} ({alert_level} alert) due to {len(static_violations)} rule violations and {len(behavioral_flags)} behavioral patterns."
                elif field in ["regulatory_basis", "evidence"]:
                    parsed_response[field] = []
                elif field == "recommended_action":
                    # Default action based on alert level
                    if alert_level == "CRITICAL":
                        parsed_response[field] = "ENHANCED_DUE_DILIGENCE"
                    elif alert_level == "HIGH":
                        parsed_response[field] = "ENHANCED_DUE_DILIGENCE"
                    elif alert_level == "MEDIUM":
                        parsed_response[field] = "MONITORING_ONLY"
                    else:
                        parsed_response[field] = "MONITORING_ONLY"
                elif field == "confidence":
                    parsed_response[field] = "MEDIUM"

        # Validate recommended_action
        valid_actions = ["HOLD_TRANSACTION", "ENHANCED_DUE_DILIGENCE", "FILE_STR", "MONITORING_ONLY"]
        if parsed_response["recommended_action"] not in valid_actions:
            logger.warning(
                f"Invalid recommended_action: {parsed_response['recommended_action']}, defaulting",
                extra={"extra_data": {"transaction_id": str(transaction.transaction_id)}},
            )
            parsed_response["recommended_action"] = "MONITORING_ONLY"

        # Validate confidence
        valid_confidence = ["HIGH", "MEDIUM", "LOW"]
        if parsed_response["confidence"] not in valid_confidence:
            parsed_response["confidence"] = "MEDIUM"

        # Calculate execution time
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="explainer",
            input_data={
                "transaction_id": str(transaction.transaction_id),
                "risk_score": risk_score,
                "alert_level": alert_level,
                "violations_count": len(static_violations),
                "flags_count": len(behavioral_flags),
            },
            output_data={
                "explanation_length": len(parsed_response["explanation"]),
                "regulatory_basis_count": len(parsed_response["regulatory_basis"]),
                "evidence_count": len(parsed_response["evidence"]),
                "recommended_action": parsed_response["recommended_action"],
                "confidence": parsed_response["confidence"],
            },
            execution_time_ms=execution_time_ms,
            status="success",
        )
        await save_agent_log(session, log_entry)

        logger.info(
            f"Explainer agent completed for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "execution_time_ms": execution_time_ms,
                    "recommended_action": parsed_response["recommended_action"],
                    "confidence": parsed_response["confidence"],
                }
            },
        )

        return parsed_response

    except GroqAPIError as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="explainer",
            input_data={
                "transaction_id": str(transaction.transaction_id),
                "risk_score": risk_score,
                "alert_level": alert_level,
            },
            output_data=None,
            execution_time_ms=execution_time_ms,
            status="error",
            error_message=str(e),
        )
        await save_agent_log(session, log_entry)

        logger.error(
            f"Error in explainer agent for transaction {transaction.transaction_id}: {str(e)}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "error": str(e),
                }
            },
        )

        # Return fallback explanation
        violations_text = ", ".join([v.rule_id for v in static_violations[:3]])
        flags_text = ", ".join([f.flag_type for f in behavioral_flags[:3]])

        return {
            "explanation": f"This transaction received a risk score of {risk_score} ({alert_level} alert) based on regulatory compliance analysis. {len(static_violations)} rule violations were detected{f' including {violations_text}' if violations_text else ''}. {len(behavioral_flags)} behavioral patterns were identified{f' including {flags_text}' if flags_text else ''}. Further investigation is recommended.",
            "regulatory_basis": [f"{v.rule_id}: {v.rule_type}" for v in static_violations[:5]],
            "evidence": [v.description for v in static_violations[:3]] + [f.description for f in behavioral_flags[:3]],
            "recommended_action": "ENHANCED_DUE_DILIGENCE" if alert_level in ["CRITICAL", "HIGH"] else "MONITORING_ONLY",
            "confidence": "MEDIUM",
        }

    except Exception as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="explainer",
            input_data={"transaction_id": str(transaction.transaction_id)},
            output_data=None,
            execution_time_ms=execution_time_ms,
            status="error",
            error_message=str(e),
        )
        await save_agent_log(session, log_entry)

        logger.error(
            f"Unexpected error in explainer agent for transaction {transaction.transaction_id}: {str(e)}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "error": str(e),
                }
            },
        )

        # Return minimal fallback
        return {
            "explanation": f"Transaction analysis completed with risk score {risk_score} ({alert_level} alert). Review required.",
            "regulatory_basis": [],
            "evidence": [],
            "recommended_action": "MONITORING_ONLY",
            "confidence": "LOW",
        }
