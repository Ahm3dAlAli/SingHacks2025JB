"""
LangGraph state definition for Transaction Analysis Engine.
Defines the TAEState TypedDict that flows through all agents in the workflow.
"""

from typing import TypedDict, List, Optional, Dict, Any
from app.database.models import Transaction, RegulatoryRule
from app.api.models import RuleViolation, BehavioralFlag


class TAEState(TypedDict):
    """
    Transaction Analysis Engine state that flows through the LangGraph workflow.

    This state is passed between all 5 agents and accumulates information
    as each agent processes the transaction.

    Workflow:
        1. Initial state created with transaction data
        2. Agent 1 (Rule Parser) adds parsed_rules
        3. Agent 2 (Static Rules) adds regulatory_rules and static_violations
        4. Agent 3 (Behavioral) adds behavioral_flags (runs parallel with Agent 2)
        5. Agent 4 (Risk Scorer) adds risk_score, alert_level, explanation
        6. Agent 5 (Explainer) enhances explanation, adds regulatory_citations, recommended_action, confidence
        7. Final state saved to database as RiskAssessment

    Attributes:
        transaction: Transaction ORM model from database
        regulatory_rules: List of applicable regulatory rules from database
        static_violations: Rule violations detected by Agent 2
        behavioral_flags: Behavioral patterns detected by Agent 3
        risk_score: Final risk score (0-100) calculated by Agent 4
        alert_level: Alert classification (CRITICAL/HIGH/MEDIUM/LOW) by Agent 4
        explanation: Human-readable summary (Agent 4 basic, Agent 5 enhanced)
        parsed_rules: Structured rule data parsed by Agent 1 (NEW)
        regulatory_citations: Specific rules cited by Agent 5 (NEW)
        recommended_action: Compliance action recommended by Agent 5 (NEW)
        confidence: Confidence level from Agent 5 (NEW)
    """

    # Input data
    transaction: Transaction
    """Transaction being analyzed (from database or API input)"""

    # Agent 1 outputs (NEW)
    parsed_rules: Optional[Dict[str, Any]]
    """Parsed regulatory rules with structured conditions and thresholds"""

    # Agent 2 outputs
    regulatory_rules: List[RegulatoryRule]
    """Applicable regulatory rules loaded from database"""

    static_violations: List[RuleViolation]
    """Regulatory rule violations detected by Static Rules Engine"""

    # Agent 3 outputs
    behavioral_flags: List[BehavioralFlag]
    """Suspicious behavioral patterns detected by Behavioral Analyzer"""

    # Agent 4 outputs
    risk_score: int
    """Final aggregated risk score (0-100)"""

    alert_level: str
    """Alert classification: CRITICAL (76-100), HIGH (51-75), MEDIUM (26-50), LOW (0-25)"""

    explanation: str
    """Human-readable summary (basic from Agent 4, enhanced by Agent 5)"""

    # Agent 5 outputs (NEW)
    regulatory_citations: List[str]
    """Specific regulatory rules cited in explanation"""

    recommended_action: Optional[str]
    """Recommended compliance action: HOLD_TRANSACTION, ENHANCED_DUE_DILIGENCE, FILE_STR, MONITORING_ONLY"""

    confidence: Optional[str]
    """Confidence level: HIGH, MEDIUM, LOW"""


def create_initial_state(transaction: Transaction) -> TAEState:
    """
    Create initial TAEState with transaction data and empty fields.

    This function initializes the state before any agents run.
    All output fields are set to default/empty values.

    Args:
        transaction: Transaction ORM model to analyze

    Returns:
        TAEState with transaction and empty output fields

    Example:
        >>> from app.database.models import Transaction
        >>> txn = Transaction(customer_id="CUST-001", amount=100000)
        >>> state = create_initial_state(txn)
        >>> state["transaction"]
        <Transaction object>
        >>> state["static_violations"]
        []
    """
    return TAEState(
        transaction=transaction,
        parsed_rules=None,
        regulatory_rules=[],
        static_violations=[],
        behavioral_flags=[],
        risk_score=0,
        alert_level="LOW",
        explanation="",
        regulatory_citations=[],
        recommended_action=None,
        confidence=None,
    )


def update_state_with_static_violations(
    state: TAEState, rules: List[RegulatoryRule], violations: List[RuleViolation]
) -> TAEState:
    """
    Update state with Agent 2 (Static Rules) outputs.

    Args:
        state: Current TAEState
        rules: Regulatory rules loaded from database
        violations: Rule violations detected

    Returns:
        Updated TAEState with regulatory_rules and static_violations
    """
    state["regulatory_rules"] = rules
    state["static_violations"] = violations
    return state


def update_state_with_behavioral_flags(
    state: TAEState, flags: List[BehavioralFlag]
) -> TAEState:
    """
    Update state with Agent 3 (Behavioral) outputs.

    Args:
        state: Current TAEState
        flags: Behavioral patterns detected

    Returns:
        Updated TAEState with behavioral_flags
    """
    state["behavioral_flags"] = flags
    return state


def update_state_with_risk_assessment(
    state: TAEState, risk_score: int, alert_level: str, explanation: str
) -> TAEState:
    """
    Update state with Agent 4 (Risk Scorer) outputs.

    Args:
        state: Current TAEState
        risk_score: Final calculated risk score (0-100)
        alert_level: Alert classification (CRITICAL/HIGH/MEDIUM/LOW)
        explanation: Human-readable summary

    Returns:
        Updated TAEState with risk_score, alert_level, explanation
    """
    state["risk_score"] = risk_score
    state["alert_level"] = alert_level
    state["explanation"] = explanation
    return state


def update_state_with_parsed_rules(
    state: TAEState, parsed_rules: Dict[str, Any]
) -> TAEState:
    """
    Update state with Agent 1 (Rule Parser) outputs.

    Args:
        state: Current TAEState
        parsed_rules: Parsed regulatory rules with structured conditions

    Returns:
        Updated TAEState with parsed_rules

    Example:
        >>> parsed_rules = {"parsed_rules": [{"rule_id": "TEST-001", ...}]}
        >>> state = update_state_with_parsed_rules(state, parsed_rules)
    """
    state["parsed_rules"] = parsed_rules
    return state


def update_state_with_explanation_details(
    state: TAEState,
    enhanced_explanation: str,
    regulatory_citations: List[str],
    recommended_action: str,
    confidence: str,
) -> TAEState:
    """
    Update state with Agent 5 (Explainer) outputs.

    Args:
        state: Current TAEState
        enhanced_explanation: Audit-ready explanation (replaces basic explanation)
        regulatory_citations: Specific rules cited
        recommended_action: Recommended compliance action
        confidence: Confidence level (HIGH/MEDIUM/LOW)

    Returns:
        Updated TAEState with enhanced explanation and new fields

    Example:
        >>> state = update_state_with_explanation_details(
        ...     state,
        ...     "This transaction...",
        ...     ["HKMA-CASH-001"],
        ...     "ENHANCED_DUE_DILIGENCE",
        ...     "HIGH"
        ... )
    """
    state["explanation"] = enhanced_explanation
    state["regulatory_citations"] = regulatory_citations
    state["recommended_action"] = recommended_action
    state["confidence"] = confidence
    return state


def state_to_dict(state: TAEState) -> dict:
    """
    Convert TAEState to a plain dictionary for serialization.

    Useful for logging, API responses, or database storage.
    Converts Pydantic models to dicts and ORM models to minimal representation.

    Args:
        state: TAEState to convert

    Returns:
        Plain dictionary representation

    Example:
        >>> state_dict = state_to_dict(state)
        >>> state_dict["risk_score"]
        85
    """
    return {
        "transaction_id": str(state["transaction"].transaction_id),
        "customer_id": state["transaction"].customer_id,
        "amount": float(state["transaction"].amount),
        "currency": state["transaction"].currency,
        "jurisdiction": state["transaction"].booking_jurisdiction,
        "parsed_rules": state.get("parsed_rules"),
        "static_violations": [v.model_dump() for v in state["static_violations"]],
        "behavioral_flags": [f.model_dump() for f in state["behavioral_flags"]],
        "risk_score": state["risk_score"],
        "alert_level": state["alert_level"],
        "explanation": state["explanation"],
        "regulatory_citations": state.get("regulatory_citations", []),
        "recommended_action": state.get("recommended_action"),
        "confidence": state.get("confidence"),
    }
