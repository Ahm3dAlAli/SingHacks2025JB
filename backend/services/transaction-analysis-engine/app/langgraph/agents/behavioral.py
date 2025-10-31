"""
Agent 3: Behavioral Pattern Analyzer
Detects suspicious behavioral patterns using historical transaction data.

This agent analyzes:
- Velocity anomalies (transaction frequency/volume)
- Smurfing patterns (structured transactions below thresholds)
- Clustering (similar amounts, timing patterns)
- Geographic risk (high-risk country corridors)
- Profile mismatches (complex products for low-risk customers)
"""

from typing import List
from datetime import datetime, timedelta
import pandas as pd

from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction, AgentExecutionLog
from app.database.queries import (
    get_customer_transactions,
    get_transactions_by_timeframe,
    save_agent_log,
)
from app.api.models import BehavioralFlag, SeverityLevel
from app.utils.logger import logger
from app.agent_config_module.agent_config import get_agent_config


async def analyze_velocity(
    transaction: Transaction, session: AsyncSession
) -> List[BehavioralFlag]:
    """
    Analyze transaction velocity (frequency and volume).
    Flags transactions that exceed normal customer behavior by 3x or more.

    Checks:
    - Last 24 hours
    - Last 7 days
    - Last 30 days

    Args:
        transaction: Current transaction to analyze
        session: Database session

    Returns:
        List of BehavioralFlag objects (empty if no anomalies)
    """
    flags = []

    try:
        config = get_agent_config()

        # Get historical transactions for this customer
        historical = await get_customer_transactions(
            session,
            customer_id=transaction.customer_id,
            days=config.execution.max_historical_days,
            limit=config.execution.max_historical_transactions,
        )

        if len(historical) < config.behavioral_thresholds.min_history_for_analysis:
            logger.debug(
                f"Insufficient transaction history for velocity analysis: {len(historical)} transactions"
            )
            return flags

        # Convert to pandas DataFrame for analysis
        df = pd.DataFrame(
            [
                {
                    "transaction_id": str(t.transaction_id),
                    "booking_datetime": t.booking_datetime,
                    "amount": float(t.amount),
                    "currency": t.currency,
                }
                for t in historical
            ]
        )

        # Calculate transactions in last 24 hours
        now = datetime.utcnow()
        last_24h = now - timedelta(hours=24)
        txns_24h = len(df[df["booking_datetime"] >= last_24h])

        # Calculate average daily transactions (excluding current transaction)
        days_with_data = (now - df["booking_datetime"].min()).days
        avg_daily = len(df) / max(days_with_data, 1)

        # Check if current rate is significantly higher than normal
        threshold_multiplier = (
            config.behavioral_thresholds.velocity_multiplier_threshold
        )
        if avg_daily > 0 and txns_24h > (avg_daily * threshold_multiplier):
            multiplier = txns_24h / avg_daily

            flags.append(
                BehavioralFlag(
                    flag_type="VELOCITY_ANOMALY",
                    severity=(
                        SeverityLevel.MEDIUM if multiplier < 5 else SeverityLevel.HIGH
                    ),
                    score=min(
                        int(30 + (multiplier * 10)), 80
                    ),  # Score scales with multiplier
                    description=(
                        f"Transaction frequency {multiplier:.1f}x normal "
                        f"({txns_24h} transactions in 24h vs avg {avg_daily:.1f}/day)"
                    ),
                    detection_details={
                        "transactions_24h": txns_24h,
                        "normal_daily_rate": round(avg_daily, 1),
                        "multiplier": round(multiplier, 2),
                    },
                    historical_context={
                        "total_transactions_analyzed": len(df),
                        "days_analyzed": days_with_data,
                    },
                )
            )

            logger.warning(
                f"Velocity anomaly detected for customer {transaction.customer_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(transaction.transaction_id),
                        "customer_id": transaction.customer_id,
                        "transactions_24h": txns_24h,
                        "avg_daily": round(avg_daily, 2),
                        "multiplier": round(multiplier, 2),
                    }
                },
            )

    except Exception as e:
        logger.error(f"Error in velocity analysis: {str(e)}")

    return flags


async def detect_smurfing(
    transaction: Transaction, session: AsyncSession
) -> List[BehavioralFlag]:
    """
    Detect smurfing patterns: multiple transactions below threshold on same day.

    Smurfing is structuring transactions to avoid reporting thresholds.
    Example: 5 transactions of HKD 7,500 instead of 1 transaction of HKD 37,500.

    Args:
        transaction: Current transaction to analyze
        session: Database session

    Returns:
        List of BehavioralFlag objects (empty if no pattern detected)
    """
    flags = []

    try:
        # Get transactions from same day
        today_start = datetime.combine(
            transaction.booking_datetime.date(), datetime.min.time()
        )
        today_end = datetime.combine(
            transaction.booking_datetime.date(), datetime.max.time()
        )

        same_day_txns = await get_transactions_by_timeframe(
            session,
            customer_id=transaction.customer_id,
            start_date=today_start,
            end_date=today_end,
            limit=100,
        )

        config = get_agent_config()
        min_txns = config.behavioral_thresholds.smurfing_min_transactions

        if len(same_day_txns) < min_txns:
            return flags

        # Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "transaction_id": str(t.transaction_id),
                    "amount": float(t.amount),
                    "currency": t.currency,
                }
                for t in same_day_txns
            ]
        )

        # Group by currency
        for currency, group in df.groupby("currency"):
            txn_count = len(group)
            total_amount = group["amount"].sum()
            avg_amount = group["amount"].mean()
            std_amount = group["amount"].std()

            # Define threshold based on jurisdiction
            thresholds = {"HKD": 8000, "SGD": 20000, "CHF": 15000}
            threshold = thresholds.get(currency, 10000)

            # Check for smurfing pattern:
            # - Multiple transactions (min_txns+)
            # - Each below threshold
            # - Similar amounts (low std deviation)
            # - Total would exceed threshold
            max_amount = group["amount"].max()
            smurfing_threshold_pct = (
                config.behavioral_thresholds.smurfing_threshold_percent
            )

            if (
                txn_count >= min_txns
                and max_amount
                < (threshold * smurfing_threshold_pct)  # Each txn < threshold %
                and total_amount > threshold
                and std_amount < (avg_amount * 0.3)
            ):  # Low variation suggests structuring

                flags.append(
                    BehavioralFlag(
                        flag_type="SMURFING_PATTERN",
                        severity=(
                            SeverityLevel.HIGH
                            if txn_count >= 5
                            else SeverityLevel.MEDIUM
                        ),
                        score=min(int(40 + (txn_count * 5)), 80),
                        description=(
                            f"Smurfing pattern detected: {txn_count} similar transactions on same day, "
                            f"each {currency} {avg_amount:,.2f} (below {threshold:,.0f} threshold), "
                            f"total {currency} {total_amount:,.2f}"
                        ),
                        detection_details={
                            "transaction_count": txn_count,
                            "currency": currency,
                            "total_amount": round(total_amount, 2),
                            "avg_amount": round(avg_amount, 2),
                            "threshold": threshold,
                        },
                        historical_context={
                            "date": transaction.booking_datetime.date().isoformat()
                        },
                    )
                )

                logger.warning(
                    f"Smurfing pattern detected for customer {transaction.customer_id}",
                    extra={
                        "extra_data": {
                            "transaction_id": str(transaction.transaction_id),
                            "customer_id": transaction.customer_id,
                            "transaction_count": txn_count,
                            "currency": currency,
                            "total_amount": round(total_amount, 2),
                            "threshold": threshold,
                        }
                    },
                )

    except Exception as e:
        logger.error(f"Error in smurfing detection: {str(e)}")

    return flags


async def detect_clustering(
    transaction: Transaction, session: AsyncSession
) -> List[BehavioralFlag]:
    """
    Detect clustering patterns: similar amounts or structured timing.

    Args:
        transaction: Current transaction to analyze
        session: Database session

    Returns:
        List of BehavioralFlag objects (empty if no pattern detected)
    """
    flags = []

    try:
        config = get_agent_config()

        # Get historical transactions (last 7 days for clustering analysis)
        historical = await get_customer_transactions(
            session, customer_id=transaction.customer_id, days=7, limit=500
        )

        if len(historical) < config.behavioral_thresholds.clustering_min_transactions:
            return flags

        # Convert to DataFrame
        df = pd.DataFrame(
            [
                {
                    "transaction_id": str(t.transaction_id),
                    "booking_datetime": t.booking_datetime,
                    "amount": float(t.amount),
                    "currency": t.currency,
                }
                for t in historical
            ]
        )

        # Group by currency for amount clustering analysis
        for currency, group in df.groupby("currency"):
            if len(group) < 5:
                continue

            amounts = group["amount"]
            mean_amount = amounts.mean()
            std_amount = amounts.std()

            # Check for suspiciously low variation
            if std_amount > 0:
                coeff_variation = (std_amount / mean_amount) * 100
                clustering_threshold = (
                    config.behavioral_thresholds.clustering_variation_threshold
                )
                min_clustering_txns = (
                    config.behavioral_thresholds.clustering_min_transactions
                )

                if (
                    coeff_variation < clustering_threshold
                    and len(group) >= min_clustering_txns
                ):
                    flags.append(
                        BehavioralFlag(
                            flag_type="CLUSTERING_PATTERN",
                            severity=SeverityLevel.MEDIUM,
                            score=35,
                            description=(
                                f"Amount clustering detected: {len(group)} transactions with similar amounts "
                                f"({currency} {mean_amount:,.2f} ± {std_amount:,.2f}, variation {coeff_variation:.1f}%)"
                            ),
                            detection_details={
                                "transaction_count": len(group),
                                "currency": currency,
                                "mean_amount": round(mean_amount, 2),
                                "std_deviation": round(std_amount, 2),
                                "coeff_variation_pct": round(coeff_variation, 1),
                            },
                            historical_context={"days_analyzed": 7},
                        )
                    )

                    logger.warning(
                        f"Clustering pattern detected for customer {transaction.customer_id}",
                        extra={
                            "extra_data": {
                                "transaction_id": str(transaction.transaction_id),
                                "customer_id": transaction.customer_id,
                                "currency": currency,
                                "coeff_variation": round(coeff_variation, 2),
                            }
                        },
                    )

    except Exception as e:
        logger.error(f"Error in clustering detection: {str(e)}")

    return flags


async def check_geographic_risk(
    transaction: Transaction, session: AsyncSession
) -> List[BehavioralFlag]:
    """
    Check for high-risk geographic corridors (sanctioned countries, high-risk jurisdictions).

    Args:
        transaction: Current transaction to analyze
        session: Database session (not used but kept for consistency)

    Returns:
        List of BehavioralFlag objects (empty if no risk detected)
    """
    flags = []

    try:
        config = get_agent_config()

        # Check originator and beneficiary countries
        originator = transaction.originator_country
        beneficiary = transaction.beneficiary_country

        high_risk_detected = []

        if originator and config.geographic_risk.is_high_risk(originator):
            high_risk_detected.append(f"Originator: {originator}")

        if beneficiary and config.geographic_risk.is_high_risk(beneficiary):
            high_risk_detected.append(f"Beneficiary: {beneficiary}")

        if high_risk_detected:
            flags.append(
                BehavioralFlag(
                    flag_type="GEOGRAPHIC_RISK",
                    severity=SeverityLevel.HIGH,
                    score=70,
                    description=(
                        f"High-risk country corridor detected. {', '.join(high_risk_detected)}. "
                        f"Route: {originator or 'Unknown'} → {beneficiary or 'Unknown'}"
                    ),
                    detection_details={
                        "originator_country": originator,
                        "beneficiary_country": beneficiary,
                        "high_risk_parties": high_risk_detected,
                    },
                    historical_context=None,
                )
            )

            logger.warning(
                f"Geographic risk detected for transaction {transaction.transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(transaction.transaction_id),
                        "originator": originator,
                        "beneficiary": beneficiary,
                        "high_risk": high_risk_detected,
                    }
                },
            )

    except Exception as e:
        logger.error(f"Error in geographic risk check: {str(e)}")

    return flags


async def check_profile_mismatch(
    transaction: Transaction, session: AsyncSession
) -> List[BehavioralFlag]:
    """
    Check for mismatches between customer risk profile and product complexity.
    Low-risk customers shouldn't trade complex products without proper suitability assessment.

    Args:
        transaction: Current transaction to analyze
        session: Database session (not used but kept for consistency)

    Returns:
        List of BehavioralFlag objects (empty if no mismatch)
    """
    flags = []

    try:
        # Check for profile mismatch
        customer_risk = transaction.customer_risk_rating
        product_complex = transaction.product_complex
        suitability_assessed = transaction.suitability_assessed

        # Flag if low-risk customer trading complex products without assessment
        if (
            customer_risk
            and customer_risk.upper() in ["LOW", "LOW-RISK"]
            and product_complex
            and not suitability_assessed
        ):

            flags.append(
                BehavioralFlag(
                    flag_type="PROFILE_MISMATCH",
                    severity=SeverityLevel.MEDIUM,
                    score=40,
                    description=(
                        f"Profile mismatch: {customer_risk} risk customer trading complex products "
                        f"without suitability assessment. Product: {transaction.product_type}"
                    ),
                    detection_details={
                        "customer_risk_rating": customer_risk,
                        "product_complex": product_complex,
                        "suitability_assessed": suitability_assessed,
                        "product_type": transaction.product_type,
                    },
                    historical_context=None,
                )
            )

            logger.warning(
                f"Profile mismatch detected for transaction {transaction.transaction_id}",
                extra={
                    "extra_data": {
                        "transaction_id": str(transaction.transaction_id),
                        "customer_id": transaction.customer_id,
                        "customer_risk": customer_risk,
                        "product_type": transaction.product_type,
                    }
                },
            )

    except Exception as e:
        logger.error(f"Error in profile mismatch check: {str(e)}")

    return flags


async def behavioral_agent(
    transaction: Transaction, session: AsyncSession
) -> List[BehavioralFlag]:
    """
    Agent 3: Behavioral Pattern Analyzer
    Main entry point for behavioral pattern detection.

    Executes all behavioral analyses and returns aggregated flags.
    Logs execution to agent_execution_logs table.

    Args:
        transaction: Transaction to analyze
        session: Database session for queries and logging

    Returns:
        List of BehavioralFlag objects detected

    Example:
        >>> flags = await behavioral_agent(transaction, session)
        >>> len(flags)
        2
        >>> flags[0].flag_type
        'VELOCITY_ANOMALY'
    """
    start_time = datetime.utcnow()
    flags = []

    try:
        logger.info(
            f"Starting behavioral analysis for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "customer_id": transaction.customer_id,
                }
            },
        )

        # Execute all behavioral analyses
        flags.extend(await analyze_velocity(transaction, session))
        flags.extend(await detect_smurfing(transaction, session))
        flags.extend(await detect_clustering(transaction, session))
        flags.extend(await check_geographic_risk(transaction, session))
        flags.extend(await check_profile_mismatch(transaction, session))

        # Calculate execution time
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log execution to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="behavioral_analyzer",
            input_data={
                "customer_id": transaction.customer_id,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
            },
            output_data={
                "flags_count": len(flags),
                "flags": [f.model_dump() for f in flags],
            },
            execution_time_ms=execution_time_ms,
            status="success",
        )
        await save_agent_log(session, log_entry)

        logger.info(
            f"Behavioral analysis completed for transaction {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "flags_count": len(flags),
                    "execution_time_ms": execution_time_ms,
                }
            },
        )

    except Exception as e:
        execution_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        # Log error to database
        log_entry = AgentExecutionLog(
            transaction_id=transaction.transaction_id,
            agent_name="behavioral_analyzer",
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
            f"Error in behavioral analysis for transaction {transaction.transaction_id}: {str(e)}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "error": str(e),
                }
            },
        )

        # Return empty list on error (fail gracefully)
        return []

    return flags
