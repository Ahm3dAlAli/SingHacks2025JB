"""
Agent 2: Static Rules Engine
Checks transactions against regulatory compliance rules from database.

This agent validates transactions against predefined regulatory rules for:
- Cash limit violations
- KYC expiry
- PEP screening
- Sanctions screening
- Travel rule compliance (SWIFT fields)
- FX spread violations
- EDD requirements
"""

from typing import List
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction, RegulatoryRule, AgentExecutionLog
from app.database.queries import get_regulatory_rules, save_agent_log
from app.api.models import RuleViolation, SeverityLevel
from app.utils.logger import logger
from app.agent_config_module.agent_config import get_agent_config


async def check_cash_limits(
    transaction: Transaction, rules: List[RegulatoryRule]
) -> List[RuleViolation]:
    """
    Check if transaction exceeds cash limit thresholds for the jurisdiction.

    Regulatory thresholds (from rules in database):
    - HKMA: HKD 8,000
    - MAS: SGD 20,000
    - FINMA: CHF 15,000

    Args:
        transaction: Transaction to check
        rules: Regulatory rules from database

    Returns:
        List of RuleViolation objects (empty if no violations)
    """
    violations = []

    # Find cash limit rules for this jurisdiction
    cash_rules = [r for r in rules if r.rule_type == "cash_limit"]

    for rule in cash_rules:
        # Get threshold from rule parameters
        threshold = rule.rule_parameters.get("threshold", 0)
        currency_check = rule.rule_parameters.get("currency")

        # Check if amount exceeds threshold and currency matches
        if transaction.currency == currency_check and transaction.amount > Decimal(
            threshold
        ):

            violations.append(
                RuleViolation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    severity=SeverityLevel(rule.severity),
                    score=get_agent_config().severity.get_score(rule.severity),
                    description=(
                        f"Cash transaction {transaction.currency} {transaction.amount:,.2f} "
                        f"exceeds {currency_check} {threshold:,.2f} threshold"
                    ),
                    jurisdiction=rule.jurisdiction,
                    parameters=rule.rule_parameters,
                )
            )

            logger.warning(
                f"Cash limit violation detected for transaction {transaction.transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(transaction.transaction_id),
                        "amount": float(transaction.amount),
                        "currency": transaction.currency,
                        "threshold": threshold,
                        "rule_id": rule.rule_id,
                    }
                },
            )

    return violations


async def check_kyc_expiry(
    transaction: Transaction, rules: List[RegulatoryRule]
) -> List[RuleViolation]:
    """
    Check if customer's KYC is expired.

    Args:
        transaction: Transaction to check
        rules: Regulatory rules from database

    Returns:
        List of RuleViolation objects (empty if no violations)
    """
    violations = []

    # Find KYC expiry rules
    kyc_rules = [r for r in rules if r.rule_type == "kyc_expiry"]

    if not kyc_rules:
        return violations

    # Check if KYC due date has passed
    if transaction.kyc_due_date and transaction.kyc_due_date < date.today():
        rule = kyc_rules[0]  # Use first matching rule

        days_expired = (date.today() - transaction.kyc_due_date).days

        config = get_agent_config()
        violations.append(
            RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                severity=SeverityLevel(rule.severity),
                score=config.severity.get_score(SeverityLevel(rule.severity)),
                description=(
                    f"KYC expired since {transaction.kyc_due_date.isoformat()} "
                    f"({days_expired} days ago)"
                ),
                jurisdiction=rule.jurisdiction,
                parameters=rule.rule_parameters,
            )
        )

        logger.warning(
            f"KYC expiry violation detected for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "customer_id": transaction.customer_id,
                    "kyc_due_date": transaction.kyc_due_date.isoformat(),
                    "days_expired": days_expired,
                    "rule_id": rule.rule_id,
                }
            },
        )

    return violations


async def check_pep_status(
    transaction: Transaction, rules: List[RegulatoryRule]
) -> List[RuleViolation]:
    """
    Check if customer is a Politically Exposed Person (PEP).
    PEPs require enhanced due diligence.

    Args:
        transaction: Transaction to check
        rules: Regulatory rules from database

    Returns:
        List of RuleViolation objects (empty if no violations)
    """
    violations = []

    # Find PEP screening rules
    pep_rules = [r for r in rules if r.rule_type == "pep_screening"]

    if not pep_rules:
        return violations

    # Check if customer is PEP
    if transaction.customer_is_pep:
        rule = pep_rules[0]
        config = get_agent_config()

        violations.append(
            RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                severity=SeverityLevel(rule.severity),
                score=config.severity.get_score(SeverityLevel(rule.severity)),
                description=(
                    f"Customer is PEP - enhanced due diligence required. "
                    f"EDD performed: {transaction.edd_performed}"
                ),
                jurisdiction=rule.jurisdiction,
                parameters=rule.rule_parameters,
            )
        )

        logger.warning(
            f"PEP status detected for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "customer_id": transaction.customer_id,
                    "edd_performed": transaction.edd_performed,
                    "rule_id": rule.rule_id,
                }
            },
        )

    return violations


async def check_sanctions(
    transaction: Transaction, rules: List[RegulatoryRule]
) -> List[RuleViolation]:
    """
    Check if transaction involves sanctioned entities.

    Args:
        transaction: Transaction to check
        rules: Regulatory rules from database

    Returns:
        List of RuleViolation objects (empty if no violations)
    """
    violations = []

    # Find sanctions screening rules
    sanctions_rules = [r for r in rules if r.rule_type == "sanctions_screening"]

    if not sanctions_rules:
        return violations

    # Check sanctions screening result
    if (
        transaction.sanctions_screening
        and transaction.sanctions_screening.upper() == "HIT"
    ):
        rule = sanctions_rules[0]
        config = get_agent_config()

        violations.append(
            RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                severity=SeverityLevel(rule.severity),
                score=config.severity.get_score(SeverityLevel(rule.severity)),
                description=(
                    f"Sanctions screening HIT - immediate escalation required. "
                    f"Originator: {transaction.originator_country}, "
                    f"Beneficiary: {transaction.beneficiary_country}"
                ),
                jurisdiction=rule.jurisdiction,
                parameters=rule.rule_parameters,
            )
        )

        logger.critical(
            f"SANCTIONS HIT detected for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "customer_id": transaction.customer_id,
                    "originator_country": transaction.originator_country,
                    "beneficiary_country": transaction.beneficiary_country,
                    "rule_id": rule.rule_id,
                }
            },
        )

    return violations


async def check_travel_rule(
    transaction: Transaction, rules: List[RegulatoryRule]
) -> List[RuleViolation]:
    """
    Check Travel Rule compliance for virtual asset transfers.
    SWIFT F50 (Originator) and F59 (Beneficiary) fields must be present.

    Args:
        transaction: Transaction to check
        rules: Regulatory rules from database

    Returns:
        List of RuleViolation objects (empty if no violations)
    """
    violations = []

    # Find travel rule requirements
    travel_rules = [r for r in rules if r.rule_type == "travel_rule"]

    if not travel_rules:
        return violations

    rule = travel_rules[0]

    # Check if transaction requires travel rule compliance
    threshold = rule.rule_parameters.get("threshold", 0)
    currency_check = rule.rule_parameters.get("currency")

    if transaction.currency == currency_check and transaction.amount > Decimal(
        threshold
    ):

        # Check if required SWIFT fields are present
        if not transaction.travel_rule_complete or not (
            transaction.swift_f50_present and transaction.swift_f59_present
        ):
            violations.append(
                RuleViolation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    severity=SeverityLevel(rule.severity),
                    score=get_agent_config().severity.get_score(rule.severity),
                    description=(
                        f"Travel Rule violation: Transaction {transaction.currency} {transaction.amount:,.2f} "
                        f"exceeds {currency_check} {threshold:,.2f} but SWIFT fields incomplete. "
                        f"F50: {transaction.swift_f50_present}, F59: {transaction.swift_f59_present}"
                    ),
                    jurisdiction=rule.jurisdiction,
                    parameters=rule.rule_parameters,
                )
            )

            logger.warning(
                f"Travel Rule violation detected for transaction {transaction.transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(transaction.transaction_id),
                        "amount": float(transaction.amount),
                        "currency": transaction.currency,
                        "swift_f50_present": transaction.swift_f50_present,
                        "swift_f59_present": transaction.swift_f59_present,
                        "rule_id": rule.rule_id,
                    }
                },
            )

    return violations


async def check_fx_spreads(
    transaction: Transaction, rules: List[RegulatoryRule]
) -> List[RuleViolation]:
    """
    Check if FX spread exceeds regulatory limits (>300 bps).

    Args:
        transaction: Transaction to check
        rules: Regulatory rules from database

    Returns:
        List of RuleViolation objects (empty if no violations)
    """
    violations = []

    # Find FX spread rules
    fx_rules = [r for r in rules if r.rule_type == "fx_spread"]

    if not fx_rules:
        return violations

    # Check if this is an FX transaction with spread data
    if transaction.fx_indicator and transaction.fx_spread_bps is not None:
        rule = fx_rules[0]
        max_spread = rule.rule_parameters.get("max_spread_bps", 300)

        if transaction.fx_spread_bps > max_spread:
            violations.append(
                RuleViolation(
                    rule_id=rule.rule_id,
                    rule_type=rule.rule_type,
                    severity=SeverityLevel(rule.severity),
                    score=get_agent_config().severity.get_score(rule.severity),
                    description=(
                        f"FX spread {transaction.fx_spread_bps} bps exceeds maximum {max_spread} bps. "
                        f"Applied rate: {transaction.fx_applied_rate}, Market rate: {transaction.fx_market_rate}"
                    ),
                    jurisdiction=rule.jurisdiction,
                    parameters=rule.rule_parameters,
                )
            )

            logger.warning(
                f"FX spread violation detected for transaction {transaction.transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(transaction.transaction_id),
                        "fx_spread_bps": transaction.fx_spread_bps,
                        "max_allowed": max_spread,
                        "fx_applied_rate": (
                            float(transaction.fx_applied_rate)
                            if transaction.fx_applied_rate
                            else None
                        ),
                        "rule_id": rule.rule_id,
                    }
                },
            )

    return violations


async def check_edd_requirements(
    transaction: Transaction, rules: List[RegulatoryRule]
) -> List[RuleViolation]:
    """
    Check if Enhanced Due Diligence (EDD) is required but not performed.

    Args:
        transaction: Transaction to check
        rules: Regulatory rules from database

    Returns:
        List of RuleViolation objects (empty if no violations)
    """
    violations = []

    # Find EDD rules
    edd_rules = [r for r in rules if r.rule_type == "edd_required"]

    if not edd_rules:
        return violations

    # Check if EDD is required but not performed
    if transaction.edd_required and not transaction.edd_performed:
        rule = edd_rules[0]
        config = get_agent_config()

        violations.append(
            RuleViolation(
                rule_id=rule.rule_id,
                rule_type=rule.rule_type,
                severity=SeverityLevel(rule.severity),
                score=config.severity.get_score(SeverityLevel(rule.severity)),
                description=(
                    f"Enhanced Due Diligence required but not performed. "
                    f"Customer: {transaction.customer_id}, Risk: {transaction.customer_risk_rating}"
                ),
                jurisdiction=rule.jurisdiction,
                parameters=rule.rule_parameters,
            )
        )

        logger.warning(
            f"EDD requirement violation detected for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "customer_id": transaction.customer_id,
                    "customer_risk_rating": transaction.customer_risk_rating,
                    "rule_id": rule.rule_id,
                }
            },
        )

    return violations


async def static_rules_agent(
    transaction: Transaction, session: AsyncSession
) -> List[RuleViolation]:
    """
    Agent 2: Static Rules Engine
    Main entry point for static rules checking.

    Executes all compliance checks and returns aggregated violations.
    Logs execution to agent_execution_logs table.

    Args:
        transaction: Transaction to analyze
        session: Database session for queries and logging

    Returns:
        List of RuleViolation objects detected

    Example:
        >>> violations = await static_rules_agent(transaction, session)
        >>> len(violations)
        3
        >>> violations[0].severity
        'CRITICAL'
    """
    start_time = datetime.utcnow()
    violations = []

    try:
        logger.info(
            f"Starting static rules analysis for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "customer_id": transaction.customer_id,
                    "jurisdiction": transaction.booking_jurisdiction,
                }
            },
        )

        # Load regulatory rules from database for this jurisdiction
        rules = await get_regulatory_rules(
            session, jurisdiction=transaction.booking_jurisdiction, is_active=True
        )

        if not rules:
            logger.warning(
                f"No regulatory rules found for jurisdiction {transaction.booking_jurisdiction}",
                extra={
                    "extra_data": {
                        "transaction_id": str(transaction.transaction_id),
                        "jurisdiction": transaction.booking_jurisdiction,
                    }
                },
            )

        # Execute all checks
        violations.extend(await check_cash_limits(transaction, rules))
        violations.extend(await check_kyc_expiry(transaction, rules))
        violations.extend(await check_pep_status(transaction, rules))
        violations.extend(await check_sanctions(transaction, rules))
        violations.extend(await check_travel_rule(transaction, rules))
        violations.extend(await check_fx_spreads(transaction, rules))
        violations.extend(await check_edd_requirements(transaction, rules))

        # Calculate execution time
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log execution to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="static_rules",
            input_data={
                "customer_id": transaction.customer_id,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
                "jurisdiction": transaction.booking_jurisdiction,
            },
            output_data={
                "violations_count": len(violations),
                "violations": [v.model_dump() for v in violations],
            },
            execution_time_ms=execution_time_ms,
            status="success",
        )
        await save_agent_log(session, log_entry)

        logger.info(
            f"Static rules analysis completed for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "violations_count": len(violations),
                    "execution_time_ms": execution_time_ms,
                }
            },
        )

    except Exception as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="static_rules",
            input_data={
                "customer_id": transaction.customer_id,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
            },
            output_data=None,
            execution_time_ms=execution_time_ms,
            status="error",
            error_message=str(e),
        )
        await save_agent_log(session, log_entry)

        logger.error(
            f"Error in static rules analysis for transaction {transaction.transaction_id}: {str(e)}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "error": str(e),
                }
            },
        )

        # Return empty list on error (fail gracefully)
        return []

    return violations
