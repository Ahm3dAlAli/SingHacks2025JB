"""
Unit tests for regulatory rules synchronization endpoint.
Tests the /api/v1/tae/rules/sync endpoint including success, dry_run, and error cases.
"""

import pytest
from datetime import datetime, date
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select, func

from app.api.routes import sync_regulatory_rules, _sync_lock
from app.api.models import RuleSyncRequest, RuleSyncResponse
from app.database.models import RegulatoryRule, AuditTrail
from app.services.regulatory_client import RegulatoryServiceError


@pytest.mark.asyncio
async def test_sync_rules_success(async_session):
    """Test successful rule sync with mixed new and existing rules"""
    # Mock RegulatoryClient.fetch_rules
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        mock_fetch.return_value = [
            {
                "id": "123",
                "rule_number": "HKMA-CASH-001",
                "jurisdiction": "HK",
                "regulator": "HKMA",
                "rule_type": "THRESHOLD",
                "full_text": "Cash limit HKD 8,000",
                "status": "ACTIVE",
                "summary": "Must comply with cash limits",
                "category": "AML",
            },
            {
                "id": "456",
                "rule_number": "HKMA-KYC-001",
                "jurisdiction": "HK",
                "regulator": "HKMA",
                "rule_type": "REQUIREMENT",
                "full_text": "KYC must be updated every 24 months",
                "status": "ACTIVE",
                "summary": "Required KYC updates",
                "category": "Compliance",
            },
        ]

        # Mock database query to simulate one existing rule
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.side_effect = [
            None,  # First rule doesn't exist
            MagicMock(id=1, rule_id="HKMA-KYC-001"),  # Second rule exists
        ]
        async_session.execute.return_value = mock_result

        # Call endpoint
        request = RuleSyncRequest(jurisdiction="HK", force=False, dry_run=False)
        response = await sync_regulatory_rules(request, async_session)

        # Verify response
        assert response.status == "success"
        assert response.jurisdiction == "HK"
        assert response.total_fetched == 2
        assert response.rules_added == 1
        assert response.rules_updated == 1
        assert response.rules_failed == 0
        assert len(response.errors) == 0
        assert response.duration_seconds > 0

        # Verify fetch_rules was called with correct params
        mock_fetch.assert_called_once()
        call_kwargs = mock_fetch.call_args[1]
        assert call_kwargs["jurisdiction"] == "HK"
        assert call_kwargs["status"] == "ACTIVE"
        assert call_kwargs["use_cache"] is True

        # Verify commit was called
        async_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_rules_dry_run(async_session):
    """Test dry_run mode doesn't modify database"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        mock_fetch.return_value = [
            {
                "id": "123",
                "rule_number": "TEST-001",
                "jurisdiction": "HK",
                "regulator": "HKMA",
                "rule_type": "THRESHOLD",
                "full_text": "Test rule",
                "status": "ACTIVE",
                "summary": "Test",
                "category": "Test",
            }
        ]

        # Call endpoint with dry_run=True
        request = RuleSyncRequest(jurisdiction="HK", force=False, dry_run=True)
        response = await sync_regulatory_rules(request, async_session)

        # Verify response
        assert response.status == "success"
        assert response.total_fetched == 1
        assert response.rules_added == 1  # In dry run, all count as "added"
        assert response.rules_updated == 0
        assert response.rules_failed == 0

        # Verify database was NOT modified
        async_session.add.assert_not_called()
        async_session.commit.assert_not_called()
        async_session.execute.assert_not_called()  # No SELECT queries in dry run


@pytest.mark.asyncio
async def test_sync_rules_partial_failure(async_session):
    """Test handling of partial failures (some rules succeed, some fail)"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        with patch("app.api.routes.regulatory_client.transform_rule") as mock_transform:
            mock_fetch.return_value = [
                {"id": "1", "rule_number": "RULE-001"},
                {"id": "2", "rule_number": "RULE-002"},
                {"id": "3", "rule_number": "RULE-003"},
            ]

            # First and third succeed, second fails
            mock_rule_1 = MagicMock(rule_id="RULE-001")
            mock_rule_3 = MagicMock(rule_id="RULE-003")
            mock_transform.side_effect = [
                mock_rule_1,
                Exception("Transformation failed for RULE-002"),
                mock_rule_3,
            ]

            # Mock database to return None (no existing rules)
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            async_session.execute.return_value = mock_result

            # Call endpoint
            request = RuleSyncRequest()
            response = await sync_regulatory_rules(request, async_session)

            # Verify partial success
            assert response.status == "partial"
            assert response.total_fetched == 3
            assert response.rules_added == 2
            assert response.rules_updated == 0
            assert response.rules_failed == 1
            assert len(response.errors) == 1
            assert "RULE-002" in response.errors[0]

            # Verify commit still happened (successful rules committed)
            async_session.commit.assert_called()


@pytest.mark.asyncio
async def test_sync_rules_service_unavailable(async_session):
    """Test handling of Regulatory Service unavailability (503 error)"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        mock_fetch.side_effect = RegulatoryServiceError("Connection timeout")

        # Call endpoint and expect HTTPException
        request = RuleSyncRequest()
        with pytest.raises(Exception) as exc_info:
            await sync_regulatory_rules(request, async_session)

        # Verify 503 error raised
        assert exc_info.value.status_code == 503
        assert "unavailable" in exc_info.value.detail.lower()

        # Verify no database operations
        async_session.add.assert_not_called()
        async_session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_sync_rules_cache_behavior(async_session):
    """Test cache bypass with force=True"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        mock_fetch.return_value = []

        # Test with force=False (use cache)
        request = RuleSyncRequest(force=False)
        await sync_regulatory_rules(request, async_session)
        assert mock_fetch.call_args[1]["use_cache"] is True

        # Test with force=True (bypass cache)
        request = RuleSyncRequest(force=True)
        await sync_regulatory_rules(request, async_session)
        assert mock_fetch.call_args[1]["use_cache"] is False


@pytest.mark.asyncio
async def test_sync_rules_creates_audit_trail(async_session):
    """Test that audit trail is created after successful sync"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        mock_fetch.return_value = [
            {
                "id": "123",
                "rule_number": "TEST-001",
                "jurisdiction": "HK",
                "regulator": "HKMA",
                "rule_type": "THRESHOLD",
                "full_text": "Test",
                "status": "ACTIVE",
                "summary": "Test",
                "category": "Test",
            }
        ]

        # Mock database query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        async_session.execute.return_value = mock_result

        # Call endpoint
        request = RuleSyncRequest(jurisdiction="HK")
        response = await sync_regulatory_rules(request, async_session)

        # Verify audit trail was added
        # Check that session.add was called with AuditTrail object
        add_calls = [call[0][0] for call in async_session.add.call_args_list]
        audit_entries = [obj for obj in add_calls if isinstance(obj, AuditTrail)]

        assert len(audit_entries) == 1
        audit_entry = audit_entries[0]
        assert audit_entry.service_name == "TAE"
        assert audit_entry.action == "rules_sync"
        assert audit_entry.resource_type == "regulatory_rules"
        assert "total_fetched" in audit_entry.details
        assert audit_entry.details["jurisdiction"] == "HK"


@pytest.mark.asyncio
async def test_sync_rules_jurisdiction_filter(async_session):
    """Test that jurisdiction filter is passed to fetch_rules"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        mock_fetch.return_value = []

        # Test with jurisdiction filter
        request = RuleSyncRequest(jurisdiction="SG")
        await sync_regulatory_rules(request, async_session)

        # Verify jurisdiction passed to fetch_rules
        mock_fetch.assert_called_once()
        assert mock_fetch.call_args[1]["jurisdiction"] == "SG"


@pytest.mark.asyncio
async def test_sync_rules_error_limit(async_session):
    """Test that errors are limited to first 10 + truncation message"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        with patch("app.api.routes.regulatory_client.transform_rule") as mock_transform:
            # Create 15 rules
            mock_fetch.return_value = [
                {"id": str(i), "rule_number": f"RULE-{i:03d}"} for i in range(15)
            ]

            # Make all transformations fail
            mock_transform.side_effect = Exception("Transform failed")

            # Call endpoint
            request = RuleSyncRequest()
            response = await sync_regulatory_rules(request, async_session)

            # Verify errors are limited
            assert response.rules_failed == 15
            assert len(response.errors) == 11  # 10 errors + 1 truncation message
            assert "truncated" in response.errors[-1]


@pytest.mark.asyncio
async def test_sync_rules_concurrent_sync_blocked(async_session):
    """Test that concurrent syncs are blocked with 409 error"""
    # Manually lock the sync lock
    await _sync_lock.acquire()

    try:
        request = RuleSyncRequest()
        with pytest.raises(Exception) as exc_info:
            await sync_regulatory_rules(request, async_session)

        # Verify 409 Conflict error
        assert exc_info.value.status_code == 409
        assert "already in progress" in exc_info.value.detail.lower()

    finally:
        # Release lock
        _sync_lock.release()


@pytest.mark.asyncio
async def test_sync_rules_database_error_per_rule_failure(async_session):
    """Test that database errors during rule processing are treated as per-rule failures"""
    with patch("app.api.routes.regulatory_client.fetch_rules") as mock_fetch:
        # Simulate database error for one rule
        mock_fetch.return_value = [{"id": "1", "rule_number": "TEST"}]

        # Make session.execute raise an error (simulate database failure during SELECT)
        async_session.execute.side_effect = Exception("Database connection lost")

        # Call endpoint - should NOT raise exception, but report failure
        request = RuleSyncRequest()
        response = await sync_regulatory_rules(request, async_session)

        # Verify the error is treated as a rule failure, not a critical error
        assert response.status == "failed"
        assert response.total_fetched == 1
        assert response.rules_failed == 1
        assert len(response.errors) >= 1
        assert "Database connection lost" in response.errors[0]

        # Verify commit was still attempted (for any successful rules)
        # In this case, all failed, but commit is still called (no-op)
        async_session.commit.assert_called()
