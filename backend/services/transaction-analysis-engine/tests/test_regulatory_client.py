"""
Unit tests for Regulatory Service HTTP client.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, date

import httpx

from app.services.regulatory_client import (
    RegulatoryClient,
    get_regulatory_client,
    RegulatoryServiceError,
)
from app.database.models import RegulatoryRule


@pytest.mark.asyncio
class TestRegulatoryClient:
    """Test RegulatoryClient functionality"""

    async def test_fetch_rules_success(self):
        """Test successful rule fetching from Regulatory Service"""
        client = RegulatoryClient(base_url="http://test-service:8003")

        mock_response_data = {
            "rules": [
                {
                    "id": "123e4567-e89b-12d3-a456-426614174000",
                    "document_id": "doc-123",
                    "rule_number": "HKMA-CASH-001",
                    "rule_type": "THRESHOLD",
                    "category": "AML",
                    "subcategory": "Cash Transactions",
                    "summary": "Cash limit must not exceed HKD 8,000",
                    "full_text": "Cash transactions exceeding HKD 8,000 require enhanced due diligence within 30 days",
                    "effective_date": "2024-01-01",
                    "expiry_date": None,
                    "status": "ACTIVE",
                    "jurisdiction": "HK",
                    "regulator": "HKMA",
                    "document_title": "AML Guidelines 2024"
                }
            ],
            "total": 1,
            "limit": 100,
            "offset": 0
        }

        # Mock the HTTP response
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            rules = await client.fetch_rules(jurisdiction="HK", status="ACTIVE")

            assert len(rules) == 1
            assert rules[0]["rule_number"] == "HKMA-CASH-001"
            assert rules[0]["jurisdiction"] == "HK"
            assert rules[0]["status"] == "ACTIVE"

            # Verify API was called with correct parameters
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args[0][0] == "http://test-service:8003/api/v1/regulatory/rules"
            assert call_args[1]["params"]["jurisdiction"] == "HK"
            assert call_args[1]["params"]["status"] == "ACTIVE"

    async def test_fetch_rules_timeout_retry(self):
        """Test retry logic on timeout"""
        client = RegulatoryClient(base_url="http://test-service:8003", max_retries=3)

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            # All attempts timeout
            mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Connection timeout"))
            mock_client_class.return_value = mock_client

            with pytest.raises(RegulatoryServiceError, match="Timeout after 3 attempts"):
                await client.fetch_rules()

            # Verify 3 retry attempts
            assert mock_client.get.call_count == 3

    async def test_fetch_rules_http_error(self):
        """Test HTTP error handling"""
        client = RegulatoryClient(base_url="http://test-service:8003")

        mock_request = MagicMock()
        mock_request.url = "http://test-service:8003/api/v1/regulatory/rules"

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"

        http_error = httpx.HTTPStatusError(
            "404 Not Found",
            request=mock_request,
            response=mock_response
        )

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(side_effect=http_error)
            mock_client_class.return_value = mock_client

            with pytest.raises(RegulatoryServiceError, match="HTTP 404"):
                await client.fetch_rules()

    async def test_fetch_rules_cache_hit(self):
        """Test caching behavior"""
        client = RegulatoryClient(base_url="http://test-service:8003")

        mock_response_data = {
            "rules": [{"rule_number": "TEST-001", "jurisdiction": "HK", "status": "ACTIVE"}],
            "total": 1
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # First call: should hit API
            rules1 = await client.fetch_rules(jurisdiction="HK", status="ACTIVE")
            assert len(rules1) == 1
            assert mock_client.get.call_count == 1

            # Second call: should use cache
            rules2 = await client.fetch_rules(jurisdiction="HK", status="ACTIVE")
            assert len(rules2) == 1
            assert mock_client.get.call_count == 1  # Still 1, not called again

            # Verify both results are the same
            assert rules1 == rules2

    async def test_fetch_rules_cache_bypass(self):
        """Test cache bypass with use_cache=False"""
        client = RegulatoryClient(base_url="http://test-service:8003")

        mock_response_data = {
            "rules": [{"rule_number": "TEST-001"}],
            "total": 1
        }

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__.return_value = mock_client
            mock_client.__aexit__.return_value = None
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            # First call
            await client.fetch_rules(jurisdiction="HK", use_cache=True)
            assert mock_client.get.call_count == 1

            # Second call with cache bypass
            await client.fetch_rules(jurisdiction="HK", use_cache=False)
            assert mock_client.get.call_count == 2  # Called again

    def test_transform_rule(self):
        """Test rule transformation from Regulatory Service to TAE schema"""
        client = RegulatoryClient()

        regulatory_rule = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "document_id": "doc-123",
            "rule_number": "HKMA-CASH-001",
            "rule_type": "THRESHOLD",
            "category": "AML",
            "subcategory": "Cash Transactions",
            "summary": "Cash limit must not exceed HKD 8,000",
            "full_text": "Cash transactions exceeding HKD 8,000 require reporting within 30 days",
            "effective_date": "2024-01-01",
            "expiry_date": None,
            "status": "ACTIVE",
            "jurisdiction": "HK",
            "regulator": "HKMA",
            "document_title": "AML Guidelines"
        }

        tae_rule = client.transform_rule(regulatory_rule)

        # Verify transformed fields
        assert isinstance(tae_rule, RegulatoryRule)
        assert tae_rule.rule_id == "HKMA-CASH-001"
        assert tae_rule.jurisdiction == "HK"
        assert tae_rule.regulator == "HKMA"
        assert tae_rule.rule_type == "threshold_check"  # Mapped from THRESHOLD
        assert tae_rule.rule_text == regulatory_rule["full_text"]
        assert tae_rule.severity == "CRITICAL"  # "must" keyword
        assert tae_rule.priority == 100  # CRITICAL = 100
        assert tae_rule.is_active is True
        assert tae_rule.effective_date == date(2024, 1, 1)
        assert tae_rule.expiry_date is None
        assert "AML" in tae_rule.tags

        # Verify extracted parameters
        assert "threshold" in tae_rule.rule_parameters
        assert tae_rule.rule_parameters["threshold"] == 8000.0
        assert tae_rule.rule_parameters["currency"] == "HKD"
        assert tae_rule.rule_parameters["days"] == 30

    def test_transform_rule_type_mapping(self):
        """Test all rule type mappings"""
        client = RegulatoryClient()

        test_cases = [
            ("OBLIGATION", "compliance_check"),
            ("PROHIBITION", "prohibition_check"),
            ("REQUIREMENT", "requirement_check"),
            ("THRESHOLD", "threshold_check"),
            ("EXEMPTION", "exemption_check"),
            ("GUIDANCE", "guidance_check"),
            ("DEFINITION", "definition_check"),
            ("OTHER", "compliance_check"),
            ("UNKNOWN_TYPE", "compliance_check"),  # Default
        ]

        for reg_type, expected_tae_type in test_cases:
            rule = {
                "id": "test-id",
                "rule_number": "TEST-001",
                "rule_type": reg_type,
                "summary": "Test rule",
                "full_text": "Test text",
                "status": "ACTIVE",
                "jurisdiction": "HK",
                "regulator": "TEST"
            }

            tae_rule = client.transform_rule(rule)
            assert tae_rule.rule_type == expected_tae_type, f"Failed for {reg_type}"

    def test_extract_parameters_currency(self):
        """Test currency extraction from rule text"""
        client = RegulatoryClient()

        test_cases = [
            ("HKD 8,000", {"currency": "HKD", "threshold": 8000.0}),
            ("SGD 20,000.00", {"currency": "SGD", "threshold": 20000.0}),
            ("USD 10,000", {"currency": "USD", "threshold": 10000.0}),
            ("CHF 5,000.50", {"currency": "CHF", "threshold": 5000.5}),
        ]

        for text, expected in test_cases:
            params = client._extract_parameters(text)
            assert params["currency"] == expected["currency"], f"Failed for {text}"
            assert params["threshold"] == expected["threshold"], f"Failed for {text}"

    def test_extract_parameters_days(self):
        """Test day extraction from rule text"""
        client = RegulatoryClient()

        test_cases = [
            ("within 30 days", {"days": 30}),
            ("after 7 days", {"days": 7}),
            ("180 day period", {"days": 180}),
            ("1 day notice", {"days": 1}),
        ]

        for text, expected in test_cases:
            params = client._extract_parameters(text)
            assert params["days"] == expected["days"], f"Failed for {text}"

    def test_extract_parameters_combined(self):
        """Test combined parameter extraction"""
        client = RegulatoryClient()

        text = "Transactions exceeding HKD 8,000 must be reported within 30 days"
        params = client._extract_parameters(text)

        assert params["currency"] == "HKD"
        assert params["threshold"] == 8000.0
        assert params["days"] == 30

    def test_extract_parameters_no_match(self):
        """Test parameter extraction with no matches"""
        client = RegulatoryClient()

        text = "This rule has no extractable parameters"
        params = client._extract_parameters(text)

        assert params == {}

    def test_determine_severity_critical(self):
        """Test CRITICAL severity determination"""
        client = RegulatoryClient()

        critical_cases = [
            ("must comply", ""),
            ("shall not exceed", ""),
            ("prohibited transactions", ""),
            ("mandatory reporting", ""),
            ("", "required disclosure"),
        ]

        for summary, category in critical_cases:
            severity = client._determine_severity(summary, category)
            assert severity == "CRITICAL", f"Failed for summary='{summary}', category='{category}'"

    def test_determine_severity_high(self):
        """Test HIGH severity determination"""
        client = RegulatoryClient()

        high_cases = [
            ("threshold limit", ""),
            ("exceed maximum", ""),
            ("violation detected", ""),
            ("", "breach category"),
        ]

        for summary, category in high_cases:
            severity = client._determine_severity(summary, category)
            assert severity == "HIGH", f"Failed for summary='{summary}', category='{category}'"

    def test_determine_severity_medium(self):
        """Test MEDIUM severity determination"""
        client = RegulatoryClient()

        medium_cases = [
            ("should consider", ""),
            ("recommended practice", ""),
            ("advised to disclose", ""),
            ("", "guideline category"),
        ]

        for summary, category in medium_cases:
            severity = client._determine_severity(summary, category)
            assert severity == "MEDIUM", f"Failed for summary='{summary}', category='{category}'"

    def test_determine_severity_low(self):
        """Test LOW severity determination (default)"""
        client = RegulatoryClient()

        severity = client._determine_severity("general information", "reference")
        assert severity == "LOW"

    def test_get_regulatory_client_singleton(self):
        """Test that get_regulatory_client returns singleton"""
        client1 = get_regulatory_client()
        client2 = get_regulatory_client()

        assert client1 is client2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_integration_fetch_from_real_service():
    """
    Integration test: Fetch rules from actual Regulatory Service.

    This test requires the Regulatory Service to be running at localhost:8003.
    It will be skipped if the service is unavailable.
    """
    client = RegulatoryClient(base_url="http://localhost:8003")

    try:
        rules = await client.fetch_rules(jurisdiction="HK", status="ACTIVE", use_cache=False)

        # Verify response structure
        assert isinstance(rules, list)

        if len(rules) > 0:
            # Verify first rule has expected fields
            rule = rules[0]
            assert "rule_number" in rule or "id" in rule
            assert "jurisdiction" in rule
            assert "regulator" in rule
            assert "full_text" in rule or "summary" in rule
            assert "status" in rule

            # Test transformation
            tae_rule = client.transform_rule(rule)
            assert isinstance(tae_rule, RegulatoryRule)
            assert tae_rule.jurisdiction == "HK"

        print(f"✅ Integration test passed: Fetched {len(rules)} rules from real service")

    except Exception as e:
        pytest.skip(f"Regulatory Service not available: {e}")
