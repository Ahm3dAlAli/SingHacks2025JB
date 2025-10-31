"""
Agent 4: Risk Scorer
Aggregates all findings from static rules and behavioral analysis into final risk score.

This agent:
- Combines static rule violation scores
- Combines behavioral flag scores
- Applies jurisdiction-specific weights
- Calculates final risk score (0-100)
- Classifies alert level (CRITICAL/HIGH/MEDIUM/LOW)
- Generates human-readable explanation
"""

from typing import List, Tuple
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction, AgentExecutionLog
from app.database.queries import save_agent_log
from app.api.models import RuleViolation, BehavioralFlag, AlertLevel
from app.utils.logger import logger
from app.agent_config_module.agent_config import get_agent_config


def aggregate_static_scores(violations: List[RuleViolation]) -> int:
    """
    Aggregate all static rule violation scores.

    Args:
        violations: List of RuleViolation objects

    Returns:
        Total static rules score

    Example:
        >>> violations = [
        ...     RuleViolation(score=65, ...),
        ...     RuleViolation(score=40, ...),
        ...     RuleViolation(score=30, ...)
        ... ]
        >>> aggregate_static_scores(violations)
        135
    """
    return sum(v.score for v in violations)


def aggregate_behavioral_scores(flags: List[BehavioralFlag]) -> int:
    """
    Aggregate all behavioral flag scores.

    Args:
        flags: List of BehavioralFlag objects

    Returns:
        Total behavioral score

    Example:
        >>> flags = [
        ...     BehavioralFlag(score=45, ...),
        ...     BehavioralFlag(score=25, ...)
        ... ]
        >>> aggregate_behavioral_scores(flags)
        70
    """
    return sum(f.score for f in flags)


def apply_jurisdiction_weight(combined_score: float, jurisdiction: str) -> float:
    """
    Apply jurisdiction-specific weight multiplier.

    Jurisdiction weights:
    - HK (HKMA): 1.2x (stricter regulations)
    - SG (MAS): 1.0x (baseline)
    - CH (FINMA): 1.1x (moderate)

    Args:
        combined_score: Combined score before weighting
        jurisdiction: Jurisdiction code (HK/SG/CH)

    Returns:
        Weighted score

    Example:
        >>> apply_jurisdiction_weight(100, "HK")
        120.0
        >>> apply_jurisdiction_weight(100, "SG")
        100.0
    """
    config = get_agent_config()
    weight = config.jurisdiction.get_weight(jurisdiction)
    return combined_score * weight


def calculate_final_score(
    static_score: int, behavioral_score: int, jurisdiction: str
) -> Tuple[int, float]:
    """
    Calculate final risk score (0-100) with jurisdiction weighting.

    Algorithm:
    1. Calculate combined score: (static + behavioral) / 2
    2. Apply jurisdiction weight
    3. Cap at 100

    Args:
        static_score: Total static rules score
        behavioral_score: Total behavioral score
        jurisdiction: Jurisdiction code

    Returns:
        Tuple of (final_score, jurisdiction_weight)

    Example:
        >>> calculate_final_score(135, 70, "HK")
        (100, 1.2)  # Capped at 100
        >>> calculate_final_score(50, 30, "SG")
        (40, 1.0)
    """
    # Average the two scores
    combined = (static_score + behavioral_score) / 2

    # Apply jurisdiction weight
    config = get_agent_config()
    jurisdiction_weight = config.jurisdiction.get_weight(jurisdiction)
    weighted = apply_jurisdiction_weight(combined, jurisdiction)

    # Cap at 100
    final_score = min(100, int(weighted))

    return final_score, jurisdiction_weight


def classify_alert_level(risk_score: int) -> AlertLevel:
    """
    Classify alert level based on risk score.

    Thresholds:
    - CRITICAL: 76-100
    - HIGH: 51-75
    - MEDIUM: 26-50
    - LOW: 0-25

    Args:
        risk_score: Final risk score (0-100)

    Returns:
        AlertLevel enum value

    Example:
        >>> classify_alert_level(100)
        AlertLevel.CRITICAL
        >>> classify_alert_level(45)
        AlertLevel.MEDIUM
    """
    config = get_agent_config()
    alert_level_str = config.alert_thresholds.classify_alert_level(risk_score)
    return AlertLevel(alert_level_str)


def generate_explanation(
    risk_score: int,
    alert_level: AlertLevel,
    violations: List[RuleViolation],
    flags: List[BehavioralFlag],
    static_score: int,
    behavioral_score: int,
) -> str:
    """
    Generate human-readable explanation of risk assessment.

    Args:
        risk_score: Final risk score
        alert_level: Alert classification
        violations: Static rule violations
        flags: Behavioral flags
        static_score: Total static score
        behavioral_score: Total behavioral score

    Returns:
        Human-readable explanation string

    Example:
        >>> explanation = generate_explanation(100, AlertLevel.CRITICAL, violations, flags, 135, 70)
        >>> print(explanation)
        Risk score 100 (CRITICAL): 3 regulatory violations detected (score 135):...
    """
    parts = [f"Risk score {risk_score} ({alert_level.value}):"]

    # Summarize static violations
    if violations:
        violation_summary = ", ".join(
            [
                f"{v.rule_type} ({v.severity.value})" for v in violations[:3]
            ]  # Show first 3
        )
        more = f" and {len(violations) - 3} more" if len(violations) > 3 else ""
        parts.append(
            f"{len(violations)} regulatory violation(s) detected (score {static_score}): "
            f"{violation_summary}{more}"
        )
    else:
        parts.append("No regulatory violations")

    # Summarize behavioral flags
    if flags:
        flag_summary = ", ".join(
            [f"{f.flag_type} ({f.severity.value})" for f in flags[:3]]  # Show first 3
        )
        more = f" and {len(flags) - 3} more" if len(flags) > 3 else ""
        parts.append(
            f"{len(flags)} behavioral pattern(s) detected (score {behavioral_score}): "
            f"{flag_summary}{more}"
        )
    else:
        parts.append("No suspicious behavioral patterns")

    return ". ".join(parts)


async def risk_scorer_agent(
    transaction: Transaction,
    violations: List[RuleViolation],
    flags: List[BehavioralFlag],
    session: AsyncSession,
) -> Tuple[int, str, str]:
    """
    Agent 4: Risk Scorer
    Main entry point for risk score calculation and alert classification.

    Aggregates all findings from static rules and behavioral analysis,
    applies jurisdiction weights, calculates final score, and generates explanation.
    Logs execution to agent_execution_logs table.

    Args:
        transaction: Transaction being analyzed
        violations: Static rule violations from Agent 2
        flags: Behavioral flags from Agent 3
        session: Database session for logging

    Returns:
        Tuple of (risk_score, alert_level, explanation)

    Example:
        >>> score, level, explanation = await risk_scorer_agent(
        ...     transaction, violations, flags, session
        ... )
        >>> score
        100
        >>> level
        'CRITICAL'
    """
    start_time = datetime.utcnow()

    try:
        logger.info(
            f"Starting risk scoring for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "violations_count": len(violations),
                    "flags_count": len(flags),
                }
            },
        )

        # Aggregate scores
        static_score = aggregate_static_scores(violations)
        behavioral_score = aggregate_behavioral_scores(flags)

        # Calculate final score with jurisdiction weighting
        final_score, jurisdiction_weight = calculate_final_score(
            static_score, behavioral_score, transaction.booking_jurisdiction
        )

        # Classify alert level
        alert_level = classify_alert_level(final_score)

        # Generate explanation
        explanation = generate_explanation(
            final_score, alert_level, violations, flags, static_score, behavioral_score
        )

        # Calculate execution time
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log execution to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="risk_scorer",
            input_data={
                "violations_count": len(violations),
                "flags_count": len(flags),
                "static_score": static_score,
                "behavioral_score": behavioral_score,
                "jurisdiction": transaction.booking_jurisdiction,
            },
            output_data={
                "risk_score": final_score,
                "alert_level": alert_level.value,
                "jurisdiction_weight": jurisdiction_weight,
                "explanation": explanation,
            },
            execution_time_ms=execution_time_ms,
            status="success",
        )
        await save_agent_log(session, log_entry)

        logger.info(
            f"Risk scoring completed for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "risk_score": final_score,
                    "alert_level": alert_level.value,
                    "static_score": static_score,
                    "behavioral_score": behavioral_score,
                    "jurisdiction_weight": jurisdiction_weight,
                    "execution_time_ms": execution_time_ms,
                }
            },
        )

        return final_score, alert_level.value, explanation

    except Exception as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="risk_scorer",
            input_data={"violations_count": len(violations), "flags_count": len(flags)},
            output_data=None,
            execution_time_ms=execution_time_ms,
            status="error",
            error_message=str(e),
        )
        await save_agent_log(session, log_entry)

        logger.error(
            f"Error in risk scoring for transaction {transaction.transaction_id}: {str(e)}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "error": str(e),
                }
            },
        )

        # Return default safe values on error (fail gracefully)
        return 0, AlertLevel.LOW.value, "Error calculating risk score"
