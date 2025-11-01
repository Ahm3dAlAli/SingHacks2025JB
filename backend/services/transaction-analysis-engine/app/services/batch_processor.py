"""
Batch Processor Service for CSV uploads.
Handles CSV parsing, validation, and background batch processing.
"""

import io
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional
from uuid import UUID, uuid4

import pandas as pd
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Transaction, BatchMetadata, RiskAssessment
from app.database.queries import (
    save_transaction,
    save_risk_assessment,
    save_batch_metadata,
    update_batch_status,
    update_batch_progress,
)
from app.workflows.workflow import execute_workflow
from app.utils.logger import logger
from app.config import settings


class BatchProcessor:
    """
    Handles batch CSV processing for transaction analysis.
    Validates CSV format, parses transactions, and processes them through TAE workflow.
    """

    # Expected column count in CSV (actual count from data/transactions_mock_1000_for_participants.csv)
    EXPECTED_COLUMN_COUNT = 54

    # Maximum file size: 10MB
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, session: AsyncSession):
        """
        Initialize batch processor with database session.

        Args:
            session: AsyncSession for database operations
        """
        self.session = session

    async def parse_csv(self, file: UploadFile) -> tuple[List[Dict[str, Any]], str]:
        """
        Parse and validate CSV file.

        Args:
            file: UploadFile from FastAPI

        Returns:
            Tuple of (list of transaction dicts, filename)

        Raises:
            ValueError: If CSV is invalid (wrong columns, bad data, etc.)
        """
        # Check file size
        contents = await file.read()
        if len(contents) > self.MAX_FILE_SIZE:
            raise ValueError(
                f"File size {len(contents)} bytes exceeds maximum {self.MAX_FILE_SIZE} bytes (10MB)"
            )

        # Parse CSV with pandas
        try:
            df = pd.read_csv(io.BytesIO(contents))
        except Exception as e:
            raise ValueError(f"Failed to parse CSV: {str(e)}")

        # Validate column count
        if len(df.columns) != self.EXPECTED_COLUMN_COUNT:
            raise ValueError(
                f"CSV has {len(df.columns)} columns, expected {self.EXPECTED_COLUMN_COUNT}. "
                f"Please ensure your CSV matches the required format."
            )

        # Convert DataFrame to list of dicts
        transactions = df.to_dict("records")

        logger.info(
            f"CSV parsed successfully: {file.filename}",
            extra={
                "extra_data": {
                    "filename": file.filename,
                    "rows": len(transactions),
                    "columns": len(df.columns),
                }
            },
        )

        return transactions, file.filename or "unknown.csv"

    def validate_transaction_row(self, row: Dict[str, Any], row_index: int) -> bool:
        """
        Validate a single transaction row.

        Args:
            row: Transaction data dict
            row_index: Row number (for error messages)

        Returns:
            True if valid

        Raises:
            ValueError: If validation fails
        """
        # Check required fields
        required_fields = [
            "transaction_id",
            "booking_jurisdiction",
            "booking_datetime",
            "amount",
            "currency",
            "customer_id",
        ]

        for field in required_fields:
            if field not in row or pd.isna(row[field]):
                raise ValueError(
                    f"Row {row_index}: Missing required field '{field}'"
                )

        # Validate amount is positive
        try:
            amount = float(row["amount"])
            if amount <= 0:
                raise ValueError(f"Row {row_index}: Amount must be positive")
        except (ValueError, TypeError) as e:
            raise ValueError(f"Row {row_index}: Invalid amount: {row['amount']}")

        return True

    async def process_batch(self, batch_id: UUID) -> None:
        """
        Background task to process a batch of transactions.
        This runs asynchronously after batch upload.

        Args:
            batch_id: UUID of the batch to process

        Note:
            This function commits the session at the end.
        """
        from app.database.queries import get_batch_metadata, get_transactions_by_batch
        from app.database.connection import get_async_session

        start_time = datetime.utcnow()

        # Create new session for background task
        async with get_async_session() as session:
            try:
                # Get batch metadata
                batch = await get_batch_metadata(session, batch_id)
                if not batch:
                    logger.error(f"Batch not found: {batch_id}")
                    return

                # Update status to PROCESSING
                await update_batch_status(session, batch_id, "PROCESSING")
                await session.commit()

                logger.info(
                    f"Starting batch processing: {batch_id}",
                    extra={
                        "extra_data": {
                            "batch_id": str(batch_id),
                            "total_transactions": batch.total_transactions,
                        }
                    },
                )

                # Get all transactions for this batch
                transactions = await get_transactions_by_batch(
                    session, str(batch_id), limit=10000
                )

                processed_count = 0
                failed_count = 0

                # Process each transaction
                for transaction in transactions:
                    try:
                        # Execute TAE workflow
                        result = await execute_workflow(transaction, session)

                        # Save risk assessment
                        assessment = RiskAssessment(
                            transaction_id=transaction.transaction_id,
                            risk_score=result["risk_score"],
                            alert_level=result["alert_level"],
                            explanation=result["explanation"],
                            rules_triggered={
                                "violations": [
                                    v.model_dump()
                                    for v in result.get("static_violations", [])
                                ]
                            },
                            patterns_detected={
                                "flags": [
                                    f.model_dump()
                                    for f in result.get("behavioral_flags", [])
                                ]
                            },
                            static_rules_score=sum(
                                v.score for v in result.get("static_violations", [])
                            ),
                            behavioral_score=sum(
                                f.score for f in result.get("behavioral_flags", [])
                            ),
                        )
                        await save_risk_assessment(session, assessment)

                        processed_count += 1

                        # Update progress every 10 transactions
                        if processed_count % 10 == 0:
                            await update_batch_progress(
                                session, batch_id, processed_count, failed_count
                            )
                            await session.commit()

                    except Exception as e:
                        failed_count += 1
                        logger.error(
                            f"Failed to process transaction in batch {batch_id}",
                            extra={
                                "extra_data": {
                                    "batch_id": str(batch_id),
                                    "transaction_id": str(transaction.transaction_id),
                                    "error": str(e),
                                }
                            },
                            exc_info=True,
                        )

                # Final progress update
                await update_batch_progress(
                    session, batch_id, processed_count, failed_count
                )

                # Mark as completed
                duration = (datetime.utcnow() - start_time).total_seconds()
                await update_batch_status(
                    session, batch_id, "COMPLETED", completed_at=datetime.utcnow()
                )

                await session.commit()

                logger.info(
                    f"Batch processing completed: {batch_id}",
                    extra={
                        "extra_data": {
                            "batch_id": str(batch_id),
                            "processed": processed_count,
                            "failed": failed_count,
                            "duration_seconds": duration,
                        }
                    },
                )

            except Exception as e:
                # Mark batch as failed
                try:
                    await update_batch_status(
                        session,
                        batch_id,
                        "FAILED",
                        error_message=str(e),
                        completed_at=datetime.utcnow(),
                    )
                    await session.commit()
                except Exception as commit_error:
                    logger.error(
                        f"Failed to update batch status: {commit_error}",
                        exc_info=True,
                    )

                logger.error(
                    f"Batch processing failed: {batch_id}",
                    extra={
                        "extra_data": {
                            "batch_id": str(batch_id),
                            "error": str(e),
                        }
                    },
                    exc_info=True,
                )

    async def create_batch_from_csv(
        self, file: UploadFile, batch_id: Optional[UUID] = None
    ) -> tuple[BatchMetadata, List[Transaction]]:
        """
        Parse CSV and create batch metadata + transaction records.

        Args:
            file: Uploaded CSV file
            batch_id: Optional batch ID (will generate if not provided)

        Returns:
            Tuple of (BatchMetadata, List of Transaction objects)

        Raises:
            ValueError: If CSV is invalid
        """
        # Parse CSV
        transaction_dicts, filename = await self.parse_csv(file)

        # Generate batch ID if not provided
        if batch_id is None:
            batch_id = uuid4()

        # Create batch metadata
        batch = BatchMetadata(
            batch_id=batch_id,
            filename=filename,
            total_transactions=len(transaction_dicts),
            processed_count=0,
            failed_count=0,
            status="PENDING",
        )

        await save_batch_metadata(self.session, batch)

        # Create transaction objects
        transactions = []
        for i, row in enumerate(transaction_dicts):
            try:
                self.validate_transaction_row(row, i + 1)

                # Create Transaction object from row
                # Note: This is simplified - in production you'd map all 54 columns
                transaction = Transaction(
                    transaction_id=uuid4()
                    if pd.isna(row.get("transaction_id"))
                    else row["transaction_id"],
                    batch_id=str(batch_id),
                    booking_jurisdiction=row["booking_jurisdiction"],
                    regulator=row.get("regulator", "UNKNOWN"),
                    booking_datetime=pd.to_datetime(row["booking_datetime"]),
                    amount=Decimal(str(row["amount"])),
                    currency=row["currency"],
                    customer_id=row["customer_id"],
                    customer_is_pep=bool(row.get("customer_is_pep", False)),
                    customer_risk_rating=row.get("customer_risk_rating"),
                    # Add more field mappings as needed
                )

                await save_transaction(self.session, transaction)
                transactions.append(transaction)

            except Exception as e:
                logger.error(
                    f"Failed to create transaction from row {i+1}",
                    extra={"extra_data": {"error": str(e), "row": i + 1}},
                )
                raise ValueError(f"Row {i+1}: {str(e)}")

        await self.session.commit()

        logger.info(
            f"Batch created: {batch_id}",
            extra={
                "extra_data": {
                    "batch_id": str(batch_id),
                    "filename": filename,
                    "transactions": len(transactions),
                }
            },
        )

        return batch, transactions
