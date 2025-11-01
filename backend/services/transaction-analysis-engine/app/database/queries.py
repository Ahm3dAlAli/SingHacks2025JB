"""
Database query operations for TAE service.
Provides async CRUD operations for all database tables.
"""

from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction, RiskAssessment, RegulatoryRule, AgentExecutionLog, BatchMetadata
from app.utils.logger import logger


async def get_regulatory_rules(
    session: AsyncSession, jurisdiction: Optional[str] = None, is_active: bool = True
) -> List[RegulatoryRule]:
    """
    Get regulatory rules, optionally filtered by jurisdiction.

    Args:
        session: Database session
        jurisdiction: Optional jurisdiction filter (e.g., "HK", "SG", "CH")
        is_active: Filter for active rules only (default True)

    Returns:
        List of RegulatoryRule objects
    """
    query = select(RegulatoryRule).where(RegulatoryRule.is_active == is_active)

    if jurisdiction:
        query = query.where(RegulatoryRule.jurisdiction == jurisdiction)

    query = query.order_by(RegulatoryRule.priority.desc())

    result = await session.execute(query)
    rules = result.scalars().all()

    logger.info(
        f"Retrieved {len(rules)} regulatory rules",
        extra={"extra_data": {"jurisdiction": jurisdiction, "count": len(rules)}},
    )

    return list(rules)


async def save_transaction(session: AsyncSession, transaction: Transaction) -> Transaction:
    """
    Save a transaction to the database.

    Args:
        session: Database session
        transaction: Transaction object to save

    Returns:
        Saved Transaction object with ID populated
    """
    session.add(transaction)
    await session.flush()  # Get the ID without committing

    logger.info(
        f"Transaction saved: {transaction.transaction_id}",
        extra={
            "extra_data": {
                "transaction_id": str(transaction.transaction_id),
                "customer_id": transaction.customer_id,
                "amount": float(transaction.amount),
                "currency": transaction.currency,
            }
        },
    )

    return transaction


async def save_risk_assessment(session: AsyncSession, assessment: RiskAssessment) -> RiskAssessment:
    """
    Save a risk assessment to the database.

    Args:
        session: Database session
        assessment: RiskAssessment object to save

    Returns:
        Saved RiskAssessment object with ID populated
    """
    session.add(assessment)
    await session.flush()

    logger.info(
        f"Risk assessment saved for transaction: {assessment.transaction_id}",
        extra={
            "extra_data": {
                "transaction_id": str(assessment.transaction_id),
                "risk_score": assessment.risk_score,
                "alert_level": assessment.alert_level,
            }
        },
    )

    return assessment


async def get_transaction_by_id(
    session: AsyncSession, transaction_id: UUID
) -> Optional[Transaction]:
    """
    Get a transaction by its UUID.

    Args:
        session: Database session
        transaction_id: Transaction UUID

    Returns:
        Transaction object or None if not found
    """
    query = select(Transaction).where(Transaction.transaction_id == transaction_id)
    result = await session.execute(query)
    transaction = result.scalar_one_or_none()

    if transaction:
        logger.info(f"Transaction retrieved: {transaction_id}")
    else:
        logger.warning(f"Transaction not found: {transaction_id}")

    return transaction


async def save_agent_log(session: AsyncSession, log: AgentExecutionLog) -> AgentExecutionLog:
    """
    Save an agent execution log entry.

    Args:
        session: Database session
        log: AgentExecutionLog object to save

    Returns:
        Saved AgentExecutionLog object
    """
    session.add(log)
    await session.flush()

    logger.debug(
        f"Agent log saved: {log.agent_name} for transaction {log.transaction_id}",
        extra={
            "extra_data": {
                "agent_name": log.agent_name,
                "status": log.status,
                "execution_time_ms": log.execution_time_ms,
            }
        },
    )

    return log


async def get_transactions_by_batch(
    session: AsyncSession, batch_id: str, limit: int = 100, offset: int = 0
) -> List[Transaction]:
    """
    Get transactions by batch ID with pagination.

    Args:
        session: Database session
        batch_id: Batch identifier
        limit: Maximum number of results
        offset: Number of results to skip

    Returns:
        List of Transaction objects
    """
    query = (
        select(Transaction)
        .where(Transaction.batch_id == batch_id)
        .order_by(Transaction.created_at)
        .limit(limit)
        .offset(offset)
    )

    result = await session.execute(query)
    transactions = result.scalars().all()

    logger.info(
        f"Retrieved {len(transactions)} transactions for batch {batch_id}",
        extra={
            "extra_data": {
                "batch_id": batch_id,
                "limit": limit,
                "offset": offset,
                "count": len(transactions),
            }
        },
    )

    return list(transactions)


async def get_customer_transactions(
    session: AsyncSession, customer_id: str, days: int = 30, limit: int = 1000
) -> List[Transaction]:
    """
    Get historical transactions for a customer within a specified timeframe.
    Used by Agent 3 (Behavioral Analyzer) for pattern detection.

    Args:
        session: Database session
        customer_id: Customer identifier
        days: Number of days to look back (default 30)
        limit: Maximum number of transactions to return (default 1000)

    Returns:
        List of Transaction objects ordered by booking_datetime (most recent first)

    Example:
        >>> transactions = await get_customer_transactions(session, "CUST-001", days=30)
        >>> len(transactions)
        45
    """
    # Calculate start date (days ago from now)
    start_date = datetime.utcnow() - timedelta(days=days)

    query = (
        select(Transaction)
        .where(
            and_(Transaction.customer_id == customer_id, Transaction.booking_datetime >= start_date)
        )
        .order_by(Transaction.booking_datetime.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    transactions = result.scalars().all()

    logger.info(
        f"Retrieved {len(transactions)} historical transactions for customer {customer_id}",
        extra={
            "extra_data": {
                "customer_id": customer_id,
                "days": days,
                "limit": limit,
                "count": len(transactions),
                "start_date": start_date.isoformat(),
            }
        },
    )

    return list(transactions)


async def get_transactions_by_timeframe(
    session: AsyncSession,
    customer_id: str,
    start_date: datetime,
    end_date: datetime,
    limit: int = 1000,
) -> List[Transaction]:
    """
    Get transactions for a customer within a specific date range.
    Used for precise timeframe analysis (e.g., last 24 hours, last 7 days).

    Args:
        session: Database session
        customer_id: Customer identifier
        start_date: Start of timeframe (inclusive)
        end_date: End of timeframe (inclusive)
        limit: Maximum number of transactions to return (default 1000)

    Returns:
        List of Transaction objects ordered by booking_datetime (most recent first)

    Example:
        >>> from datetime import datetime, timedelta
        >>> now = datetime.utcnow()
        >>> yesterday = now - timedelta(days=1)
        >>> transactions = await get_transactions_by_timeframe(
        ...     session, "CUST-001", yesterday, now
        ... )
        >>> len(transactions)
        12
    """
    query = (
        select(Transaction)
        .where(
            and_(
                Transaction.customer_id == customer_id,
                Transaction.booking_datetime >= start_date,
                Transaction.booking_datetime <= end_date,
            )
        )
        .order_by(Transaction.booking_datetime.desc())
        .limit(limit)
    )

    result = await session.execute(query)
    transactions = result.scalars().all()

    logger.info(
        f"Retrieved {len(transactions)} transactions for customer {customer_id} in timeframe",
        extra={
            "extra_data": {
                "customer_id": customer_id,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "limit": limit,
                "count": len(transactions),
            }
        },
    )

    return list(transactions)


# ============================================================================
# BATCH PROCESSING QUERIES
# ============================================================================


async def save_batch_metadata(session: AsyncSession, batch: BatchMetadata) -> BatchMetadata:
    """
    Save batch metadata to the database.

    Args:
        session: Database session
        batch: BatchMetadata object to save

    Returns:
        Saved BatchMetadata object

    Example:
        >>> batch = BatchMetadata(
        ...     filename="transactions.csv",
        ...     total_transactions=1000,
        ...     status="PENDING"
        ... )
        >>> saved = await save_batch_metadata(session, batch)
        >>> saved.batch_id
        UUID('550e8400-e29b-41d4-a716-446655440000')
    """
    session.add(batch)
    await session.flush()

    logger.info(
        f"Batch metadata saved: {batch.batch_id}",
        extra={
            "extra_data": {
                "batch_id": str(batch.batch_id),
                "filename": batch.filename,
                "total_transactions": batch.total_transactions,
                "status": batch.status,
            }
        },
    )

    return batch


async def get_batch_metadata(session: AsyncSession, batch_id: UUID) -> Optional[BatchMetadata]:
    """
    Get batch metadata by batch_id.

    Args:
        session: Database session
        batch_id: UUID of the batch

    Returns:
        BatchMetadata object or None if not found

    Example:
        >>> batch = await get_batch_metadata(session, batch_id)
        >>> batch.status
        'PROCESSING'
    """
    query = select(BatchMetadata).where(BatchMetadata.batch_id == batch_id)
    result = await session.execute(query)
    batch = result.scalar_one_or_none()

    if batch:
        logger.info(
            f"Batch metadata retrieved: {batch_id}",
            extra={
                "extra_data": {
                    "batch_id": str(batch_id),
                    "status": batch.status,
                    "processed_count": batch.processed_count,
                    "total_transactions": batch.total_transactions,
                }
            },
        )
    else:
        logger.warning(f"Batch metadata not found: {batch_id}")

    return batch


async def update_batch_status(
    session: AsyncSession,
    batch_id: UUID,
    status: str,
    error_message: Optional[str] = None,
    completed_at: Optional[datetime] = None,
) -> Optional[BatchMetadata]:
    """
    Update batch status.

    Args:
        session: Database session
        batch_id: UUID of the batch
        status: New status (PENDING/PROCESSING/COMPLETED/FAILED)
        error_message: Optional error message if failed
        completed_at: Optional completion timestamp

    Returns:
        Updated BatchMetadata object or None if not found

    Example:
        >>> batch = await update_batch_status(
        ...     session, batch_id, "COMPLETED", completed_at=datetime.utcnow()
        ... )
        >>> batch.status
        'COMPLETED'
    """
    batch = await get_batch_metadata(session, batch_id)
    if not batch:
        return None

    batch.status = status
    if error_message:
        batch.error_message = error_message
    if completed_at:
        batch.completed_at = completed_at

    await session.flush()

    logger.info(
        f"Batch status updated: {batch_id} -> {status}",
        extra={
            "extra_data": {
                "batch_id": str(batch_id),
                "status": status,
                "error_message": error_message,
            }
        },
    )

    return batch


async def update_batch_progress(
    session: AsyncSession,
    batch_id: UUID,
    processed_count: Optional[int] = None,
    failed_count: Optional[int] = None,
) -> Optional[BatchMetadata]:
    """
    Update batch progress counters.

    Args:
        session: Database session
        batch_id: UUID of the batch
        processed_count: Number of transactions processed
        failed_count: Number of transactions failed

    Returns:
        Updated BatchMetadata object or None if not found

    Example:
        >>> batch = await update_batch_progress(
        ...     session, batch_id, processed_count=450, failed_count=2
        ... )
        >>> batch.processed_count
        450
    """
    batch = await get_batch_metadata(session, batch_id)
    if not batch:
        return None

    if processed_count is not None:
        batch.processed_count = processed_count
    if failed_count is not None:
        batch.failed_count = failed_count

    await session.flush()

    logger.debug(
        f"Batch progress updated: {batch_id}",
        extra={
            "extra_data": {
                "batch_id": str(batch_id),
                "processed_count": batch.processed_count,
                "failed_count": batch.failed_count,
                "total_transactions": batch.total_transactions,
            }
        },
    )

    return batch
