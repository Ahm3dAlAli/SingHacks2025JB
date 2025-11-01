"""
Unit tests for BatchProcessor service.
Tests CSV parsing, validation, and batch processing logic.
"""

import io
from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
import pandas as pd
from fastapi import UploadFile

from app.services.batch_processor import BatchProcessor
from app.database.models import BatchMetadata, Transaction


@pytest.fixture
def mock_csv_content():
    """Create a valid mock CSV content with 54 columns"""
    # Create a minimal CSV with required columns
    csv_data = {
        "transaction_id": [str(uuid4()) for _ in range(3)],
        "booking_jurisdiction": ["HK", "SG", "CH"],
        "regulator": ["HKMA", "MAS", "FINMA"],
        "booking_datetime": ["2025-11-01 10:00:00"] * 3,
        "amount": [100000.00, 50000.00, 75000.00],
        "currency": ["HKD", "SGD", "CHF"],
        "customer_id": ["CUST001", "CUST002", "CUST003"],
        "customer_is_pep": [True, False, False],
        "customer_risk_rating": ["HIGH", "MEDIUM", "LOW"],
    }

    # Add dummy columns to reach 54 total
    for i in range(45):
        csv_data[f"dummy_col_{i}"] = [""] * 3

    df = pd.DataFrame(csv_data)
    return df.to_csv(index=False).encode('utf-8')


@pytest.fixture
def mock_upload_file(mock_csv_content):
    """Create a mock UploadFile"""
    from unittest.mock import MagicMock, AsyncMock
    file = MagicMock(spec=UploadFile)
    file.filename = "test_transactions.csv"
    file.file = io.BytesIO(mock_csv_content)
    file.content_type = "text/csv"
    file.size = len(mock_csv_content)
    # Make read() async and return the content
    file.read = AsyncMock(return_value=mock_csv_content)
    return file


class TestBatchProcessor:
    """Test suite for BatchProcessor"""

    @pytest.mark.asyncio
    async def test_parse_csv_valid(self, mock_upload_file, async_session):
        """Test parsing valid CSV file"""
        processor = BatchProcessor(async_session)

        transactions, filename = await processor.parse_csv(mock_upload_file)

        assert len(transactions) == 3
        assert filename == "test_transactions.csv"
        assert transactions[0]["customer_id"] == "CUST001"
        assert float(transactions[0]["amount"]) == 100000.00

    @pytest.mark.asyncio
    async def test_parse_csv_wrong_column_count(self, async_session):
        """Test CSV with wrong number of columns fails"""
        # Create CSV with only 10 columns
        csv_data = pd.DataFrame({
            "col1": [1, 2, 3],
            "col2": [4, 5, 6],
        })
        content = csv_data.to_csv(index=False).encode('utf-8')

        file = UploadFile(
            filename="bad.csv",
            file=io.BytesIO(content)
        )

        processor = BatchProcessor(async_session)

        with pytest.raises(ValueError) as exc_info:
            await processor.parse_csv(file)

        assert "has 2 columns, expected 54" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_csv_file_too_large(self, async_session):
        """Test file size limit enforcement"""
        # Create 11MB file
        large_content = b"x" * (11 * 1024 * 1024)

        file = UploadFile(
            filename="large.csv",
            file=io.BytesIO(large_content)
        )

        processor = BatchProcessor(async_session)

        with pytest.raises(ValueError) as exc_info:
            await processor.parse_csv(file)

        assert "exceeds maximum" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_parse_csv_invalid_format(self, async_session):
        """Test invalid CSV format"""
        # Not a valid CSV
        content = b"This is not a CSV file at all!"

        file = UploadFile(
            filename="bad.csv",
            file=io.BytesIO(content)
        )

        processor = BatchProcessor(async_session)

        with pytest.raises(ValueError) as exc_info:
            await processor.parse_csv(file)

        assert "CSV has" in str(exc_info.value) or "Failed to parse CSV" in str(exc_info.value)

    def test_validate_transaction_row_valid(self, async_session):
        """Test validating a valid transaction row"""
        processor = BatchProcessor(async_session)

        row = {
            "transaction_id": str(uuid4()),
            "booking_jurisdiction": "HK",
            "booking_datetime": "2025-11-01 10:00:00",
            "amount": 100000.00,
            "currency": "HKD",
            "customer_id": "CUST001",
        }

        assert processor.validate_transaction_row(row, 1) is True

    def test_validate_transaction_row_missing_field(self, async_session):
        """Test validation fails for missing required field"""
        processor = BatchProcessor(async_session)

        row = {
            "transaction_id": str(uuid4()),
            "booking_jurisdiction": "HK",
            # Missing booking_datetime
            "amount": 100000.00,
            "currency": "HKD",
            "customer_id": "CUST001",
        }

        with pytest.raises(ValueError) as exc_info:
            processor.validate_transaction_row(row, 1)

        assert "Missing required field 'booking_datetime'" in str(exc_info.value)

    def test_validate_transaction_row_negative_amount(self, async_session):
        """Test validation fails for negative amount"""
        processor = BatchProcessor(async_session)

        row = {
            "transaction_id": str(uuid4()),
            "booking_jurisdiction": "HK",
            "booking_datetime": "2025-11-01 10:00:00",
            "amount": -100.00,  # Negative!
            "currency": "HKD",
            "customer_id": "CUST001",
        }

        with pytest.raises(ValueError) as exc_info:
            processor.validate_transaction_row(row, 1)

        assert "Invalid amount" in str(exc_info.value)

    def test_validate_transaction_row_invalid_amount(self, async_session):
        """Test validation fails for invalid amount"""
        processor = BatchProcessor(async_session)

        row = {
            "transaction_id": str(uuid4()),
            "booking_jurisdiction": "HK",
            "booking_datetime": "2025-11-01 10:00:00",
            "amount": "not_a_number",
            "currency": "HKD",
            "customer_id": "CUST001",
        }

        with pytest.raises(ValueError) as exc_info:
            processor.validate_transaction_row(row, 1)

        assert "Invalid amount" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_batch_from_csv_success(
        self, mock_upload_file, async_session, mocker
    ):
        """Test creating batch and transactions from CSV"""
        # Mock the database save functions
        mock_save_batch = mocker.patch('app.services.batch_processor.save_batch_metadata', new_callable=AsyncMock)
        mock_save_transaction = mocker.patch('app.services.batch_processor.save_transaction', new_callable=AsyncMock)

        # Mock session.commit to be an AsyncMock
        async_session.commit = AsyncMock()

        processor = BatchProcessor(async_session)

        batch, transactions = await processor.create_batch_from_csv(mock_upload_file)

        # Verify batch metadata
        assert isinstance(batch, BatchMetadata)
        assert batch.filename == "test_transactions.csv"
        assert batch.total_transactions == 3
        assert batch.status == "PENDING"
        assert batch.processed_count == 0
        assert batch.failed_count == 0

        # Verify transactions created
        assert len(transactions) == 3
        assert all(isinstance(t, Transaction) for t in transactions)
        assert transactions[0].customer_id == "CUST001"
        assert transactions[0].amount == Decimal("100000.00")

        # Verify database functions were called
        assert mock_save_batch.called
        assert mock_save_transaction.call_count == 3

    @pytest.mark.asyncio
    async def test_create_batch_from_csv_with_custom_batch_id(
        self, mock_upload_file, async_session, mocker
    ):
        """Test creating batch with custom batch_id"""
        # Mock the database save functions
        mock_save_batch = mocker.patch('app.services.batch_processor.save_batch_metadata', new_callable=AsyncMock)
        mock_save_transaction = mocker.patch('app.services.batch_processor.save_transaction', new_callable=AsyncMock)

        # Mock session.commit to be an AsyncMock
        async_session.commit = AsyncMock()

        processor = BatchProcessor(async_session)
        custom_batch_id = uuid4()

        batch, transactions = await processor.create_batch_from_csv(
            mock_upload_file, batch_id=custom_batch_id
        )

        assert batch.batch_id == custom_batch_id
        assert all(t.batch_id == str(custom_batch_id) for t in transactions)

        # Verify database functions were called
        assert mock_save_batch.called
        assert mock_save_transaction.call_count == 3

    @pytest.mark.asyncio
    async def test_process_batch_success(self, async_session, mocker):
        """Test successful batch processing"""
        # Mock the execute_workflow function that's imported in batch_processor
        from app.workflows.workflow import execute_workflow
        mock_execute_workflow = mocker.patch('app.services.batch_processor.execute_workflow', new_callable=AsyncMock)

        # Mock database functions at batch_processor level where they're imported
        mock_save_assessment = mocker.patch('app.services.batch_processor.save_risk_assessment', new_callable=AsyncMock)
        mock_update_status = mocker.patch('app.services.batch_processor.update_batch_status', new_callable=AsyncMock)
        mock_update_progress = mocker.patch('app.services.batch_processor.update_batch_progress', new_callable=AsyncMock)

        # These are imported inside process_batch function, so patch at queries level
        mock_get_batch = mocker.patch('app.database.queries.get_batch_metadata', new_callable=AsyncMock)
        mock_get_transactions = mocker.patch('app.database.queries.get_transactions_by_batch', new_callable=AsyncMock)
        mock_get_async_session = mocker.patch('app.database.connection.get_async_session')

        # Setup mock data
        test_batch_id = uuid4()
        mock_batch = BatchMetadata(
            batch_id=test_batch_id,
            filename="test.csv",
            total_transactions=2,
            status="PENDING"
        )
        mock_get_batch.return_value = mock_batch

        mock_transactions = [
            Transaction(
                transaction_id=uuid4(),
                customer_id="CUST001",
                amount=Decimal("10000"),
                currency="HKD",
                booking_jurisdiction="HK",
                booking_datetime=datetime.utcnow(),
                batch_id=str(test_batch_id)
            ),
            Transaction(
                transaction_id=uuid4(),
                customer_id="CUST002",
                amount=Decimal("20000"),
                currency="SGD",
                booking_jurisdiction="SG",
                booking_datetime=datetime.utcnow(),
                batch_id=str(test_batch_id)
            )
        ]
        mock_get_transactions.return_value = mock_transactions

        mock_execute_workflow.return_value = {
            "risk_score": 50,
            "alert_level": "MEDIUM",
            "explanation": "Test explanation",
            "static_violations": [],
            "behavioral_flags": []
        }

        # Setup async context manager mock
        mock_session_context = mocker.MagicMock()
        mock_session_context.__aenter__.return_value = async_session
        mock_session_context.__aexit__.return_value = AsyncMock()
        mock_get_async_session.return_value = mock_session_context

        # Run the batch processor
        processor = BatchProcessor(async_session)
        await processor.process_batch(test_batch_id)

        # Verify workflow was executed for each transaction
        assert mock_execute_workflow.call_count == 2
        assert mock_save_assessment.call_count == 2
        assert mock_update_progress.called
        assert mock_update_status.called

    @pytest.mark.asyncio
    async def test_process_batch_handles_individual_failures(
        self, async_session, mocker
    ):
        """Test batch processing continues after individual transaction failures"""
        # Mock the execute_workflow function at batch_processor level
        mock_execute_workflow = mocker.patch('app.services.batch_processor.execute_workflow', new_callable=AsyncMock)

        # Mock database functions at batch_processor level where they're imported
        mock_save_assessment = mocker.patch('app.services.batch_processor.save_risk_assessment', new_callable=AsyncMock)
        mock_update_status = mocker.patch('app.services.batch_processor.update_batch_status', new_callable=AsyncMock)
        mock_update_progress = mocker.patch('app.services.batch_processor.update_batch_progress', new_callable=AsyncMock)

        # These are imported inside process_batch function, so patch at queries level
        mock_get_batch = mocker.patch('app.database.queries.get_batch_metadata', new_callable=AsyncMock)
        mock_get_transactions = mocker.patch('app.database.queries.get_transactions_by_batch', new_callable=AsyncMock)
        mock_get_async_session = mocker.patch('app.database.connection.get_async_session')

        # Setup mock data
        test_batch_id = uuid4()
        mock_batch = BatchMetadata(
            batch_id=test_batch_id,
            filename="test.csv",
            total_transactions=3,
            status="PENDING"
        )
        mock_get_batch.return_value = mock_batch

        mock_transactions = [
            Transaction(
                transaction_id=uuid4(),
                customer_id="CUST001",
                amount=Decimal("10000"),
                currency="HKD",
                booking_jurisdiction="HK",
                booking_datetime=datetime.utcnow(),
                batch_id=str(test_batch_id)
            ),
            Transaction(
                transaction_id=uuid4(),
                customer_id="CUST002",
                amount=Decimal("20000"),
                currency="SGD",
                booking_jurisdiction="SG",
                booking_datetime=datetime.utcnow(),
                batch_id=str(test_batch_id)
            ),
            Transaction(
                transaction_id=uuid4(),
                customer_id="CUST003",
                amount=Decimal("30000"),
                currency="CHF",
                booking_jurisdiction="CH",
                booking_datetime=datetime.utcnow(),
                batch_id=str(test_batch_id)
            )
        ]
        mock_get_transactions.return_value = mock_transactions

        # Make second transaction fail
        mock_execute_workflow.side_effect = [
            {
                "risk_score": 50,
                "alert_level": "MEDIUM",
                "explanation": "Test",
                "static_violations": [],
                "behavioral_flags": []
            },
            Exception("Workflow failed"),
            {
                "risk_score": 30,
                "alert_level": "LOW",
                "explanation": "Test",
                "static_violations": [],
                "behavioral_flags": []
            }
        ]

        # Setup async context manager mock
        mock_session_context = mocker.MagicMock()
        mock_session_context.__aenter__.return_value = async_session
        mock_session_context.__aexit__.return_value = AsyncMock()
        mock_get_async_session.return_value = mock_session_context

        # Run the batch processor
        processor = BatchProcessor(async_session)
        await processor.process_batch(test_batch_id)

        # Verify processing continued despite failure
        assert mock_execute_workflow.call_count == 3
        assert mock_save_assessment.call_count == 2  # Only 2 successful
        assert mock_update_progress.called


# ============================================================================
# FIXTURES
# ============================================================================
# Note: async_session fixture is defined in conftest.py
