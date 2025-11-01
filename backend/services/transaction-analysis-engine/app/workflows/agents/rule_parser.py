"""
Agent 1: Rule Parser
Parses natural language regulatory rules into structured JSON using Groq LLM.

This agent takes regulatory rule text and extracts:
- Rule conditions (what triggers the rule)
- Thresholds (amounts, timeframes, limits)
- Severity score (0-100)
- Applicable transaction types
- Required compliance actions
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.models import Transaction, RegulatoryRule, AgentExecutionLog
from app.database.queries import save_agent_log, get_regulatory_rules
from app.services.groq_client import get_groq_client, GroqAPIError
from app.utils.logger import logger


async def parse_regulatory_rule(
    rule: RegulatoryRule,
    session: AsyncSession,
) -> Dict[str, Any]:
    """
    Parse a single regulatory rule using Groq LLM.

    Args:
        rule: RegulatoryRule object with rule_text to parse
        session: Database session for logging

    Returns:
        Dictionary with parsed rule structure:
        - rule_id: str
        - conditions: List[str]
        - thresholds: Dict[str, Any]
        - severity_score: int (0-100)
        - applies_to: List[str]
        - required_actions: List[str]

    Example:
        >>> rule = RegulatoryRule(rule_text="Cash transactions over HKD 8,000 require CTR", ...)
        >>> parsed = await parse_regulatory_rule(rule, session)
        >>> parsed["thresholds"]
        {"amount": 8000, "currency": "HKD"}
    """
    start_time = datetime.utcnow()
    groq_client = get_groq_client()

    try:
        logger.info(
            f"Starting rule parser for rule {rule.rule_id}",
            extra={
                "extra_data": {
                    "rule_id": rule.rule_id,
                    "jurisdiction": rule.jurisdiction,
                    "rule_type": rule.rule_type,
                }
            },
        )

        # Build prompt
        system_prompt = "You are a regulatory compliance expert specializing in AML/CFT regulations. Parse regulatory rules into structured JSON format."

        user_prompt = f"""Parse the following regulatory rule into structured JSON.

Regulation Text:
{rule.rule_text}

Jurisdiction: {rule.jurisdiction}
Regulator: {rule.regulator}
Rule Type: {rule.rule_type}

Return ONLY valid JSON (no markdown, no explanation):
{{
  "rule_id": "{rule.rule_id}",
  "conditions": ["list of conditions that trigger this rule"],
  "thresholds": {{"amount": number, "timeframe": "string", "currency": "string", etc.}},
  "severity_score": {0 if rule.severity == "LOW" else 35 if rule.severity == "MEDIUM" else 65 if rule.severity == "HIGH" else 90},
  "applies_to": ["list of transaction types this rule applies to"],
  "required_actions": ["what must be done if this rule is triggered"]
}}

Be precise with threshold values extracted from the text. If no threshold is mentioned, use empty dict."""

        # Call Groq API
        parsed_response = await groq_client.complete(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=settings.GROQ_RULE_PARSER_TEMPERATURE,
            max_tokens=settings.GROQ_RULE_PARSER_MAX_TOKENS,
            timeout=settings.GROQ_RULE_PARSER_TIMEOUT,
        )

        # Validate response structure
        required_fields = ["rule_id", "conditions", "thresholds", "severity_score", "applies_to", "required_actions"]
        for field in required_fields:
            if field not in parsed_response:
                logger.warning(
                    f"Missing field '{field}' in parsed rule response",
                    extra={"extra_data": {"rule_id": rule.rule_id, "missing_field": field}},
                )
                # Provide default
                if field == "conditions":
                    parsed_response[field] = []
                elif field == "thresholds":
                    parsed_response[field] = {}
                elif field == "severity_score":
                    parsed_response[field] = 50
                elif field in ["applies_to", "required_actions"]:
                    parsed_response[field] = []
                else:
                    parsed_response[field] = rule.rule_id

        # Ensure severity_score is in valid range
        if not isinstance(parsed_response["severity_score"], (int, float)):
            parsed_response["severity_score"] = 50
        parsed_response["severity_score"] = max(0, min(100, int(parsed_response["severity_score"])))

        # Calculate execution time
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log to database (use a generated UUID since this is not transaction-specific)
        from uuid import uuid4
        log_entry = AgentExecutionLog(
            transaction_id=uuid4(),  # Generate UUID for rule parsing logs
            agent_name="rule_parser",
            input_data={
                "rule_id": rule.rule_id,
                "rule_text": rule.rule_text[:200],  # Truncate long text
                "jurisdiction": rule.jurisdiction,
            },
            output_data={
                "parsed_rule": parsed_response,
            },
            execution_time_ms=execution_time_ms,
            status="success",
        )
        await save_agent_log(session, log_entry)

        logger.info(
            f"Rule parser completed for rule {rule.rule_id}",
            extra={
                "extra_data": {
                    "rule_id": rule.rule_id,
                    "execution_time_ms": execution_time_ms,
                    "severity_score": parsed_response["severity_score"],
                }
            },
        )

        return parsed_response

    except GroqAPIError as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error to database
        from uuid import uuid4
        log_entry = AgentExecutionLog(
            transaction_id=uuid4(),  # Generate UUID for rule parsing error logs
            agent_name="rule_parser",
            input_data={"rule_id": rule.rule_id, "rule_text": rule.rule_text[:200]},
            output_data=None,
            execution_time_ms=execution_time_ms,
            status="error",
            error_message=str(e),
        )
        await save_agent_log(session, log_entry)

        logger.error(
            f"Error in rule parser for rule {rule.rule_id}: {str(e)}",
            extra={"extra_data": {"rule_id": rule.rule_id, "error": str(e)}},
        )

        # Return fallback (literal interpretation)
        return {
            "rule_id": rule.rule_id,
            "conditions": [rule.rule_text[:100]],  # Use rule text as condition
            "thresholds": rule.rule_parameters or {},  # Use existing parameters
            "severity_score": 50,  # Default medium severity
            "applies_to": [rule.rule_type],  # Use rule type
            "required_actions": ["Review transaction", "Document decision"],
        }

    except Exception as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error
        from uuid import uuid4
        log_entry = AgentExecutionLog(
            transaction_id=uuid4(),  # Generate UUID for rule parsing exception logs
            agent_name="rule_parser",
            input_data={"rule_id": rule.rule_id},
            output_data=None,
            execution_time_ms=execution_time_ms,
            status="error",
            error_message=str(e),
        )
        await save_agent_log(session, log_entry)

        logger.error(
            f"Unexpected error in rule parser for rule {rule.rule_id}: {str(e)}",
            extra={"extra_data": {"rule_id": rule.rule_id, "error": str(e)}},
        )

        # Return safe fallback
        return {
            "rule_id": rule.rule_id,
            "conditions": [],
            "thresholds": {},
            "severity_score": 50,
            "applies_to": [],
            "required_actions": [],
        }


async def rule_parser_agent(
    transaction: Transaction,
    session: AsyncSession,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Agent 1: Rule Parser
    Parse all applicable regulatory rules for the transaction's jurisdiction.

    This agent:
    1. Fetches active regulatory rules for the transaction's jurisdiction
    2. Parses each rule using Groq LLM into structured format
    3. Returns parsed rules for use by downstream agents

    Args:
        transaction: Transaction to analyze
        session: Database session for queries and logging

    Returns:
        Dictionary with:
        - parsed_rules: List of parsed rule dictionaries

    Example:
        >>> transaction = Transaction(booking_jurisdiction="HK", ...)
        >>> result = await rule_parser_agent(transaction, session)
        >>> len(result["parsed_rules"])
        5
    """
    start_time = datetime.utcnow()

    try:
        logger.info(
            f"Starting rule parser agent for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "jurisdiction": transaction.booking_jurisdiction,
                }
            },
        )

        # Fetch applicable regulatory rules
        rules = await get_regulatory_rules(
            session=session,
            jurisdiction=transaction.booking_jurisdiction,
        )

        logger.info(
            f"Found {len(rules)} regulatory rules for jurisdiction {transaction.booking_jurisdiction}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "rule_count": len(rules),
                }
            },
        )

        # Parse each rule
        parsed_rules = []
        for rule in rules:
            parsed_rule = await parse_regulatory_rule(rule, session)
            parsed_rules.append(parsed_rule)

        # Calculate total execution time
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log aggregate execution to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="rule_parser_agent",
            input_data={
                "transaction_id": str(transaction.transaction_id),
                "jurisdiction": transaction.booking_jurisdiction,
                "rule_count": len(rules),
            },
            output_data={
                "parsed_rules_count": len(parsed_rules),
                "sample_rule": parsed_rules[0] if parsed_rules else None,
            },
            execution_time_ms=execution_time_ms,
            status="success",
        )
        await save_agent_log(session, log_entry)

        logger.info(
            f"Rule parser agent completed for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "parsed_rules_count": len(parsed_rules),
                    "execution_time_ms": execution_time_ms,
                }
            },
        )

        return {"parsed_rules": parsed_rules}

    except Exception as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="rule_parser_agent",
            input_data={
                "transaction_id": str(transaction.transaction_id),
                "jurisdiction": transaction.booking_jurisdiction,
            },
            output_data=None,
            execution_time_ms=execution_time_ms,
            status="error",
            error_message=str(e),
        )
        await save_agent_log(session, log_entry)

        logger.error(
            f"Error in rule parser agent for transaction {transaction.transaction_id}: {str(e)}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "error": str(e),
                }
            },
        )

        # Return empty parsed rules (fail gracefully)
        return {"parsed_rules": []}
