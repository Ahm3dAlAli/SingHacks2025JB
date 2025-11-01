"""
API Routes for Transaction Analysis Engine.
Implements all 7 REST API endpoints for batch and single transaction processing.
"""

import asyncio
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, Query, Depends, status
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.models import (
    BatchUploadResponse,
    BatchStatusResponse,
    BatchResultsResponse,
    BatchResultsSummary,
    BatchResultItem,
    BatchResultsPagination,
    TransactionAnalysisRequest,
    TransactionAnalysisResponse,
    RiskDetailResponse,
    ExplanationResponse,
    RuleViolation,
    BehavioralFlag,
    RuleSyncRequest,
    RuleSyncResponse,
)
from app.database.connection import get_db, get_async_session
from app.database.models import Transaction, RiskAssessment, AgentExecutionLog, RegulatoryRule, AuditTrail
from app.database.queries import (
    get_batch_metadata,
    save_transaction,
    save_risk_assessment,
)
from app.services.batch_processor import BatchProcessor
from app.services.regulatory_client import regulatory_client, RegulatoryServiceError
from app.workflows.workflow import execute_workflow
from app.utils.logger import logger


# Create APIRouter
router = APIRouter()

# Sync lock to prevent concurrent rule syncs
_sync_lock = asyncio.Lock()


# ============================================================================
# BATCH PROCESSING ENDPOINTS
# ============================================================================


@router.post(
    "/analyze-batch",
    response_model=BatchUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload CSV batch for analysis",
    description="Upload a CSV file containing transactions for batch processing. "
    "Returns immediately with batch_id for status tracking.",
)
async def upload_batch(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="CSV file (max 10MB)"),
    session: AsyncSession = Depends(get_db),
):
    """
    Upload CSV batch for asynchronous processing.

    - **file**: CSV file with transaction data (max 10MB)
    - Returns: batch_id and status URL for tracking

    The batch will be processed in the background.
    Use GET /batch/{batch_id}/status to check progress.
    """
    try:
        # Validate file type
        if file.content_type and "csv" not in file.content_type.lower():
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="File must be CSV format",
            )

        # Create batch processor
        processor = BatchProcessor(session)

        # Parse CSV and create batch + transactions
        batch, transactions = await processor.create_batch_from_csv(file)

        # Queue background task
        background_tasks.add_task(processor.process_batch, batch.batch_id)

        # Estimate completion time (4 tx/sec = 0.25s per tx)
        estimated_seconds = len(transactions) * 0.25
        estimated_completion = datetime.utcnow() + timedelta(seconds=estimated_seconds)

        logger.info(
            f"Batch uploaded: {batch.batch_id}",
            extra={
                "extra_data": {
                    "batch_id": str(batch.batch_id),
                    "filename": batch.filename,
                    "total_transactions": batch.total_transactions,
                }
            },
        )

        return BatchUploadResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            total_transactions=batch.total_transactions,
            status_url=f"/api/v1/tae/batch/{batch.batch_id}/status",
            estimated_completion=estimated_completion,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    except Exception as e:
        logger.error(f"Batch upload failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch upload failed: {str(e)}",
        )


@router.get(
    "/batch/{batch_id}/status",
    response_model=BatchStatusResponse,
    summary="Get batch processing status",
    description="Check the status and progress of a batch processing job.",
)
async def get_batch_status(
    batch_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """
    Get batch processing status.

    - **batch_id**: UUID of the batch
    - Returns: Current status, progress, and estimated completion
    """
    try:
        batch = await get_batch_metadata(session, batch_id)

        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found",
            )

        # Calculate progress percentage
        progress_percent = (
            (batch.processed_count / batch.total_transactions * 100)
            if batch.total_transactions > 0
            else 0
        )

        # Estimate completion time if processing
        estimated_completion = None
        if batch.status == "PROCESSING" and batch.processed_count > 0:
            elapsed = (datetime.utcnow() - batch.started_at).total_seconds()
            rate = batch.processed_count / elapsed if elapsed > 0 else 1
            remaining = batch.total_transactions - batch.processed_count
            eta_seconds = remaining / rate if rate > 0 else 0
            estimated_completion = datetime.utcnow() + timedelta(seconds=eta_seconds)

        return BatchStatusResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            total_transactions=batch.total_transactions,
            processed_count=batch.processed_count,
            failed_count=batch.failed_count,
            progress_percent=round(progress_percent, 2),
            started_at=batch.started_at,
            estimated_completion=estimated_completion,
            completed_at=batch.completed_at,
            error_message=batch.error_message,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch status: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/batch/{batch_id}/results",
    response_model=BatchResultsResponse,
    summary="Get batch processing results",
    description="Retrieve results from a completed batch with pagination and filtering.",
)
async def get_batch_results(
    batch_id: UUID,
    limit: int = Query(100, ge=1, le=1000, description="Results per page"),
    offset: int = Query(0, ge=0, description="Result offset"),
    alert_level: Optional[str] = Query(None, description="Filter by alert level"),
    min_risk_score: Optional[int] = Query(None, ge=0, le=100, description="Minimum risk score"),
    max_risk_score: Optional[int] = Query(None, ge=0, le=100, description="Maximum risk score"),
    session: AsyncSession = Depends(get_db),
):
    """
    Get batch processing results with pagination and filtering.

    - **batch_id**: UUID of the batch
    - **limit**: Number of results per page (1-1000)
    - **offset**: Starting position
    - **alert_level**: Filter by alert level (CRITICAL/HIGH/MEDIUM/LOW)
    - **min_risk_score**: Minimum risk score filter
    - **max_risk_score**: Maximum risk score filter

    Returns paginated results with summary statistics.
    """
    try:
        # Get batch metadata
        batch = await get_batch_metadata(session, batch_id)
        if not batch:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Batch {batch_id} not found",
            )

        # Build query for risk assessments
        from app.database.queries import get_transactions_by_batch

        transactions = await get_transactions_by_batch(
            session, str(batch_id), limit=10000
        )
        transaction_ids = [t.transaction_id for t in transactions]

        # Query risk assessments with filters
        query = select(RiskAssessment).where(
            RiskAssessment.transaction_id.in_(transaction_ids)
        )

        if alert_level:
            query = query.where(RiskAssessment.alert_level == alert_level.upper())
        if min_risk_score is not None:
            query = query.where(RiskAssessment.risk_score >= min_risk_score)
        if max_risk_score is not None:
            query = query.where(RiskAssessment.risk_score <= max_risk_score)

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await session.execute(count_query)
        total_count = total_result.scalar() or 0

        # Get paginated results
        query = query.order_by(RiskAssessment.risk_score.desc()).limit(limit).offset(offset)
        result = await session.execute(query)
        assessments = result.scalars().all()

        # Calculate summary statistics (from ALL results, not just page)
        summary_query = (
            select(
                RiskAssessment.alert_level,
                func.count(RiskAssessment.id).label("count"),
            )
            .where(RiskAssessment.transaction_id.in_(transaction_ids))
            .group_by(RiskAssessment.alert_level)
        )
        summary_result = await session.execute(summary_query)
        summary_rows = summary_result.all()

        summary_dict = {row.alert_level: row.count for row in summary_rows}
        summary = BatchResultsSummary(
            total=len(transactions),
            critical=summary_dict.get("CRITICAL", 0),
            high=summary_dict.get("HIGH", 0),
            medium=summary_dict.get("MEDIUM", 0),
            low=summary_dict.get("LOW", 0),
        )

        # Build result items
        results = [
            BatchResultItem(
                transaction_id=a.transaction_id,
                risk_score=a.risk_score,
                alert_level=a.alert_level,
                explanation_summary=a.explanation[:200] if a.explanation else "",
                recommended_action="FILE_STR" if a.alert_level == "CRITICAL" else "MONITORING_ONLY",
            )
            for a in assessments
        ]

        # Calculate processing duration
        duration = None
        if batch.completed_at and batch.started_at:
            duration = int((batch.completed_at - batch.started_at).total_seconds())

        # Build pagination
        next_url = None
        if offset + limit < total_count:
            next_url = f"/api/v1/tae/batch/{batch_id}/results?offset={offset + limit}&limit={limit}"

        pagination = BatchResultsPagination(
            total=total_count, limit=limit, offset=offset, next=next_url
        )

        return BatchResultsResponse(
            batch_id=batch.batch_id,
            status=batch.status,
            summary=summary,
            processing_duration_seconds=duration,
            results=results,
            pagination=pagination,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get batch results: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ============================================================================
# SINGLE TRANSACTION ANALYSIS ENDPOINTS
# ============================================================================


@router.post(
    "/analyze-transaction",
    response_model=TransactionAnalysisResponse,
    summary="Analyze single transaction",
    description="Submit a single transaction for real-time analysis. Returns complete risk assessment.",
)
async def analyze_transaction(
    request: TransactionAnalysisRequest,
    session: AsyncSession = Depends(get_db),
):
    """
    Analyze a single transaction in real-time.

    - **request**: Transaction data
    - Returns: Full risk assessment with violations, flags, and explanation

    Processing time: <3 seconds
    """
    start_time = datetime.utcnow()

    try:
        # Create Transaction object
        # Convert timezone-aware datetime to naive UTC
        booking_dt = request.booking_datetime.replace(tzinfo=None) if request.booking_datetime.tzinfo else request.booking_datetime

        transaction = Transaction(
            transaction_id=request.transaction_id or uuid4(),
            customer_id=request.customer_id,
            amount=Decimal(str(request.amount)),
            currency=request.currency,
            booking_jurisdiction=request.booking_jurisdiction,
            booking_datetime=booking_dt,
            customer_is_pep=request.customer_is_pep or False,
            customer_risk_rating=request.customer_risk_rating,
            originator_country=request.originator_country,
            beneficiary_country=request.beneficiary_country,
            product_type=request.product_type,
            regulator="UNKNOWN",  # Set default
        )

        # Save transaction
        await save_transaction(session, transaction)

        # Execute workflow
        result = await execute_workflow(transaction, session)

        # Save risk assessment
        # Handle violations and flags - they might be dicts or Pydantic models
        violations = result.get("static_violations", [])
        flags = result.get("behavioral_flags", [])

        violations_data = [v.model_dump() if hasattr(v, 'model_dump') else v for v in violations]
        flags_data = [f.model_dump() if hasattr(f, 'model_dump') else f for f in flags]

        assessment = RiskAssessment(
            transaction_id=transaction.transaction_id,
            risk_score=result["risk_score"],
            alert_level=result["alert_level"],
            explanation=result["explanation"],
            rules_triggered={
                "violations": violations_data
            },
            patterns_detected={
                "flags": flags_data
            },
            static_rules_score=sum(
                v.score if hasattr(v, 'score') else v.get('score', 0) for v in violations
            ),
            behavioral_score=sum(f.score if hasattr(f, 'score') else f.get('score', 0) for f in flags),
        )
        await save_risk_assessment(session, assessment)
        await session.commit()

        # Calculate processing time
        processing_time_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        logger.info(
            f"Transaction analyzed: {transaction.transaction_id}",
            extra={
                "extra_data": {
                    "transaction_id": str(transaction.transaction_id),
                    "risk_score": result["risk_score"],
                    "alert_level": result["alert_level"],
                    "processing_time_ms": processing_time_ms,
                }
            },
        )

        return TransactionAnalysisResponse(
            transaction_id=transaction.transaction_id,
            risk_score=result["risk_score"],
            alert_level=result["alert_level"],
            explanation=result["explanation"],
            rules_violated=result.get("static_violations", []),
            behavioral_flags=result.get("behavioral_flags", []),
            recommended_action=result.get("recommended_action", "MONITORING_ONLY"),
            processing_time_ms=processing_time_ms,
        )

    except Exception as e:
        logger.error(f"Transaction analysis failed: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/transaction/{transaction_id}/risk-detail",
    response_model=RiskDetailResponse,
    summary="Get detailed risk breakdown",
    description="Retrieve detailed risk assessment including all agent outputs and execution logs.",
)
async def get_risk_detail(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """
    Get detailed risk breakdown for a transaction.

    - **transaction_id**: UUID of the transaction
    - Returns: Detailed breakdown with all agent outputs and execution timeline
    """
    try:
        # Get risk assessment
        query = select(RiskAssessment).where(
            RiskAssessment.transaction_id == transaction_id
        )
        result = await session.execute(query)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk assessment not found for transaction {transaction_id}",
            )

        # Get agent execution logs
        logs_query = (
            select(AgentExecutionLog)
            .where(AgentExecutionLog.transaction_id == transaction_id)
            .order_by(AgentExecutionLog.created_at)
        )
        logs_result = await session.execute(logs_query)
        logs = logs_result.scalars().all()

        # Build execution timeline
        timeline = [
            {
                "agent": log.agent_name,
                "execution_time_ms": log.execution_time_ms,
                "status": log.status,
                "timestamp": log.created_at.isoformat() + "Z",
            }
            for log in logs
        ]

        # Parse violations and flags from JSONB
        violations = [
            RuleViolation(**v)
            for v in assessment.rules_triggered.get("violations", [])
        ]
        flags = [
            BehavioralFlag(**f)
            for f in assessment.patterns_detected.get("flags", [])
        ]

        return RiskDetailResponse(
            transaction_id=assessment.transaction_id,
            risk_score=assessment.risk_score,
            alert_level=assessment.alert_level,
            explanation=assessment.explanation or "",
            static_violations=violations,
            behavioral_flags=flags,
            static_rules_score=assessment.static_rules_score or 0,
            behavioral_score=assessment.behavioral_score or 0,
            agent_execution_timeline=timeline,
            analyzed_at=assessment.analyzed_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get risk detail: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get(
    "/explain/{transaction_id}",
    response_model=ExplanationResponse,
    summary="Get natural language explanation",
    description="Retrieve human-readable explanation with regulatory citations and evidence.",
)
async def get_explanation(
    transaction_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """
    Get natural language explanation for a transaction.

    - **transaction_id**: UUID of the transaction
    - Returns: Human-readable explanation with citations and recommended action
    """
    try:
        # Get risk assessment
        query = select(RiskAssessment).where(
            RiskAssessment.transaction_id == transaction_id
        )
        result = await session.execute(query)
        assessment = result.scalar_one_or_none()

        if not assessment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Risk assessment not found for transaction {transaction_id}",
            )

        # Extract evidence from violations and flags
        evidence = []
        violations = assessment.rules_triggered.get("violations", [])
        for v in violations:
            evidence.append(f"{v.get('description', 'Unknown violation')}")

        flags = assessment.patterns_detected.get("flags", [])
        for f in flags:
            evidence.append(f"{f.get('description', 'Unknown pattern')}")

        # Build regulatory citations
        citations = [
            "HKMA AML/CFT Guideline 3.1.2",
            "FATF Recommendation 10",
        ]

        # Determine recommended action
        action_map = {
            "CRITICAL": "FILE_STR",
            "HIGH": "ENHANCED_DUE_DILIGENCE",
            "MEDIUM": "REVIEW_REQUIRED",
            "LOW": "MONITORING_ONLY",
        }
        recommended_action = action_map.get(
            assessment.alert_level, "MONITORING_ONLY"
        )

        return ExplanationResponse(
            transaction_id=assessment.transaction_id,
            explanation=assessment.explanation or "No explanation available",
            regulatory_citations=citations,
            evidence=evidence,
            recommended_action=recommended_action,
            confidence="HIGH"
            if assessment.risk_score > 70
            else "MEDIUM"
            if assessment.risk_score > 40
            else "LOW",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get explanation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


# ============================================================================
# REGULATORY RULES SYNC ENDPOINT
# ============================================================================


@router.post(
    "/rules/sync",
    response_model=RuleSyncResponse,
    status_code=status.HTTP_200_OK,
    summary="Sync regulatory rules from Regulatory Service",
    description="Fetch rules from Regulatory Ingestion Engine and update TAE database with UPSERT logic",
)
async def sync_regulatory_rules(
    request: RuleSyncRequest = RuleSyncRequest(),
    session: AsyncSession = Depends(get_db),
):
    """
    Synchronize regulatory rules from Regulatory Service.

    Process:
    1. Check sync lock (prevent concurrent syncs)
    2. Fetch rules from Regulatory Service API (via RegulatoryClient)
    3. Transform each rule to TAE schema
    4. Upsert into regulatory_rules table (SELECT → INSERT/UPDATE)
    5. Log sync operation to audit_trail
    6. Return status with counts

    Args:
        request: Sync configuration (jurisdiction filter, force, dry_run)
        session: Database session

    Returns:
        RuleSyncResponse with sync statistics

    Raises:
        HTTPException 409: If sync already in progress
        HTTPException 503: If Regulatory Service unavailable
        HTTPException 500: If sync fails unexpectedly
    """
    # Check if sync already in progress
    if _sync_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Rule sync already in progress. Please wait for it to complete.",
        )

    async with _sync_lock:
        start_time = datetime.utcnow()
        stats = {
            "total_fetched": 0,
            "rules_added": 0,
            "rules_updated": 0,
            "rules_failed": 0,
            "errors": [],
        }

        try:
            logger.info(
                "Starting rule sync",
                extra={
                    "extra_data": {
                        "jurisdiction": request.jurisdiction,
                        "force": request.force,
                        "dry_run": request.dry_run,
                    }
                },
            )

            # Step 1: Fetch rules from Regulatory Service
            try:
                regulatory_rules = await regulatory_client.fetch_rules(
                    jurisdiction=request.jurisdiction,
                    status="ACTIVE",
                    use_cache=not request.force,  # Skip cache if force=True
                )
                stats["total_fetched"] = len(regulatory_rules)

                logger.info(
                    f"Fetched {len(regulatory_rules)} rules from Regulatory Service"
                )

            except RegulatoryServiceError as e:
                logger.error(
                    f"Failed to fetch rules from Regulatory Service: {e}",
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Regulatory Service temporarily unavailable. Please try again later.",
                )

            # Step 2: Transform and upsert each rule
            for reg_rule in regulatory_rules:
                try:
                    # Transform to TAE schema
                    tae_rule = regulatory_client.transform_rule(reg_rule)

                    if request.dry_run:
                        # Don't actually insert, just count
                        stats["rules_added"] += 1
                        continue

                    # Check if rule exists
                    existing_query = select(RegulatoryRule).where(
                        RegulatoryRule.rule_id == tae_rule.rule_id
                    )
                    result = await session.execute(existing_query)
                    existing_rule = result.scalar_one_or_none()

                    if existing_rule:
                        # Update existing rule
                        update_stmt = (
                            update(RegulatoryRule)
                            .where(RegulatoryRule.rule_id == tae_rule.rule_id)
                            .values(
                                rule_text=tae_rule.rule_text,
                                rule_parameters=tae_rule.rule_parameters,
                                severity=tae_rule.severity,
                                priority=tae_rule.priority,
                                effective_date=tae_rule.effective_date,
                                expiry_date=tae_rule.expiry_date,
                                is_active=tae_rule.is_active,
                                updated_at=datetime.utcnow(),
                            )
                        )
                        await session.execute(update_stmt)
                        stats["rules_updated"] += 1

                        logger.debug(f"Updated rule: {tae_rule.rule_id}")

                    else:
                        # Insert new rule
                        session.add(tae_rule)
                        stats["rules_added"] += 1

                        logger.debug(f"Added new rule: {tae_rule.rule_id}")

                except Exception as e:
                    stats["rules_failed"] += 1
                    error_msg = f"Failed to process rule {reg_rule.get('id', reg_rule.get('rule_number', 'unknown'))}: {str(e)}"

                    # Limit errors array to first 10
                    if len(stats["errors"]) < 10:
                        stats["errors"].append(error_msg)
                    elif len(stats["errors"]) == 10:
                        stats["errors"].append("... additional errors truncated")

                    logger.error(error_msg, exc_info=True)

            # Step 3: Commit transaction (unless dry_run)
            if not request.dry_run:
                await session.commit()

                # Step 4: Log to audit_trail (separate try-catch to prevent audit failure from failing sync)
                try:
                    audit_entry = AuditTrail(
                        service_name="TAE",
                        action="rules_sync",
                        resource_type="regulatory_rules",
                        details={
                            "jurisdiction": request.jurisdiction,
                            "total_fetched": stats["total_fetched"],
                            "rules_added": stats["rules_added"],
                            "rules_updated": stats["rules_updated"],
                            "rules_failed": stats["rules_failed"],
                            "force": request.force,
                        },
                    )
                    session.add(audit_entry)
                    await session.commit()
                except Exception as audit_error:
                    logger.error(
                        f"Failed to log audit trail for sync: {audit_error}",
                        exc_info=True,
                        extra={"extra_data": {"sync_stats": stats}},
                    )
                    # Don't fail entire sync due to audit failure

            # Calculate duration
            duration = (datetime.utcnow() - start_time).total_seconds()

            # Determine overall status
            if stats["rules_failed"] == 0:
                sync_status = "success"
            elif stats["rules_added"] + stats["rules_updated"] > 0:
                sync_status = "partial"
            else:
                sync_status = "failed"

            logger.info(
                f"Rule sync completed: {sync_status}",
                extra={
                    "extra_data": {
                        "status": sync_status,
                        "duration_seconds": duration,
                        **stats,
                    }
                },
            )

            return RuleSyncResponse(
                status=sync_status,
                jurisdiction=request.jurisdiction,
                total_fetched=stats["total_fetched"],
                rules_added=stats["rules_added"],
                rules_updated=stats["rules_updated"],
                rules_failed=stats["rules_failed"],
                errors=stats["errors"],
                duration_seconds=duration,
                timestamp=datetime.utcnow(),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Unexpected error during rule sync: {e}", exc_info=True
            )
            await session.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Rule sync failed due to unexpected error. Please contact support.",
            )
