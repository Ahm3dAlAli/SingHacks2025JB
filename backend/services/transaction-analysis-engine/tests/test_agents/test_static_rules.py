"""
Unit tests for Agent 2: Static Rules Engine
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.langgraph.agents.static_rules import (
    check_cash_limits,
    check_kyc_expiry,
    check_pep_status,
    check_sanctions,
    check_travel_rule,
    check_fx_spreads,
    check_edd_requirements,
    static_rules_agent,
)
from app.api.models import SeverityLevel
from app.agent_config_module.agent_config import AgentConfig, SeverityConfig, set_agent_config


@pytest.mark.asyncio
class TestCashLimits:
    """Test cash limit violation detection"""

    async def test_cash_limit_hkma_violation(self, high_value_transaction, sample_regulatory_rules):
        """Test HKD cash limit violation (HKD 150K > HKD 8K)"""
        violations = await check_cash_limits(high_value_transaction, sample_regulatory_rules)

        assert len(violations) == 1
        assert violations[0].rule_id == "HKMA-CASH-001"
        assert violations[0].severity == SeverityLevel.HIGH
        assert violations[0].score == 65
        assert "150,000" in violations[0].description
        assert "8,000" in violations[0].description

    async def test_cash_limit_pass(self, sample_transaction, sample_regulatory_rules):
        """Test transaction below cash limit passes"""
        sample_transaction.amount = Decimal("5000.00")
        sample_transaction.currency = "HKD"

        violations = await check_cash_limits(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_cash_limit_no_rules(self, high_value_transaction):
        """Test with no regulatory rules returns empty"""
        violations = await check_cash_limits(high_value_transaction, [])

        assert len(violations) == 0

    async def test_cash_limit_different_currency(self, sample_transaction, sample_regulatory_rules):
        """Test different currency doesn't trigger HKD rule"""
        sample_transaction.amount = Decimal("150000.00")
        sample_transaction.currency = "USD"  # Not HKD

        violations = await check_cash_limits(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_cash_limit_custom_severity_config(
        self, high_value_transaction, sample_regulatory_rules
    ):
        """Test custom severity configuration affects score"""
        custom_config = AgentConfig(severity=SeverityConfig(high=80))
        set_agent_config(custom_config)

        violations = await check_cash_limits(high_value_transaction, sample_regulatory_rules)

        assert len(violations) == 1
        assert violations[0].score == 80  # Custom config


@pytest.mark.asyncio
class TestKYCExpiry:
    """Test KYC expiry detection"""

    async def test_kyc_expiry_detection(self, expired_kyc_transaction, sample_regulatory_rules):
        """Test expired KYC is detected"""
        violations = await check_kyc_expiry(expired_kyc_transaction, sample_regulatory_rules)

        assert len(violations) == 1
        assert violations[0].rule_id == "HKMA-KYC-001"
        assert violations[0].severity == SeverityLevel.HIGH
        assert "expired" in violations[0].description.lower()
        assert "30 days ago" in violations[0].description

    async def test_kyc_valid(self, sample_transaction, sample_regulatory_rules):
        """Test valid KYC passes"""
        sample_transaction.kyc_due_date = date.today() + timedelta(days=100)

        violations = await check_kyc_expiry(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_kyc_expiry_no_due_date(self, sample_transaction, sample_regulatory_rules):
        """Test transaction with no KYC due date"""
        sample_transaction.kyc_due_date = None

        violations = await check_kyc_expiry(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_kyc_expiry_today(self, sample_transaction, sample_regulatory_rules):
        """Test KYC expiring today"""
        sample_transaction.kyc_due_date = date.today()

        violations = await check_kyc_expiry(sample_transaction, sample_regulatory_rules)

        # Should not be flagged yet (only past dates)
        assert len(violations) == 0


@pytest.mark.asyncio
class TestPEPStatus:
    """Test PEP screening detection"""

    async def test_pep_flagging(self, pep_transaction, sample_regulatory_rules):
        """Test PEP customer is flagged"""
        violations = await check_pep_status(pep_transaction, sample_regulatory_rules)

        assert len(violations) == 1
        assert violations[0].rule_id == "HKMA-PEP-001"
        assert violations[0].severity == SeverityLevel.CRITICAL
        assert violations[0].score == 100
        assert "PEP" in violations[0].description
        assert "enhanced due diligence" in violations[0].description.lower()

    async def test_non_pep_pass(self, sample_transaction, sample_regulatory_rules):
        """Test non-PEP customer passes"""
        sample_transaction.customer_is_pep = False

        violations = await check_pep_status(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_pep_with_edd_performed(self, pep_transaction, sample_regulatory_rules):
        """Test PEP with EDD performed still flagged"""
        pep_transaction.edd_performed = True

        violations = await check_pep_status(pep_transaction, sample_regulatory_rules)

        # Still flagged because PEP requires ongoing monitoring
        assert len(violations) == 1


@pytest.mark.asyncio
class TestSanctionsScreening:
    """Test sanctions screening"""

    async def test_sanctions_hit(self, sanctions_hit_transaction, sample_regulatory_rules):
        """Test sanctions hit is flagged as CRITICAL"""
        violations = await check_sanctions(sanctions_hit_transaction, sample_regulatory_rules)

        assert len(violations) == 1
        assert violations[0].severity == SeverityLevel.CRITICAL
        assert violations[0].score == 100
        assert "Sanctions screening HIT" in violations[0].description
        assert "immediate escalation" in violations[0].description.lower()

    async def test_sanctions_clear_pass(self, sample_transaction, sample_regulatory_rules):
        """Test clear sanctions screening passes"""
        sample_transaction.sanctions_screening = "CLEAR"

        violations = await check_sanctions(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_sanctions_pending(self, sample_transaction, sample_regulatory_rules):
        """Test pending sanctions doesn't flag"""
        sample_transaction.sanctions_screening = "PENDING"

        violations = await check_sanctions(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0


@pytest.mark.asyncio
class TestTravelRule:
    """Test Travel Rule compliance"""

    async def test_travel_rule_missing_fields(
        self, travel_rule_violation_transaction, sample_regulatory_rules
    ):
        """Test missing SWIFT fields for transaction > SGD 1,500"""
        violations = await check_travel_rule(
            travel_rule_violation_transaction, sample_regulatory_rules
        )

        assert len(violations) == 1
        assert violations[0].rule_id == "MAS-TRAVEL-001"
        assert violations[0].severity == SeverityLevel.HIGH
        assert "Travel Rule violation" in violations[0].description
        assert "F50" in violations[0].description
        assert "F59" in violations[0].description

    async def test_travel_rule_compliant(self, sample_transaction, sample_regulatory_rules):
        """Test compliant travel rule transaction"""
        sample_transaction.currency = "SGD"
        sample_transaction.amount = Decimal("2000.00")
        sample_transaction.swift_f50_present = True
        sample_transaction.swift_f59_present = True
        sample_transaction.travel_rule_complete = True

        violations = await check_travel_rule(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_travel_rule_below_threshold(self, sample_transaction, sample_regulatory_rules):
        """Test transaction below threshold doesn't require travel rule"""
        sample_transaction.currency = "SGD"
        sample_transaction.amount = Decimal("1000.00")
        sample_transaction.swift_f50_present = False
        sample_transaction.swift_f59_present = False

        violations = await check_travel_rule(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0


@pytest.mark.asyncio
class TestFXSpreads:
    """Test FX spread violation detection"""

    async def test_fx_spread_violation(
        self, fx_spread_violation_transaction, sample_regulatory_rules
    ):
        """Test FX spread > 300 bps is flagged"""
        violations = await check_fx_spreads(
            fx_spread_violation_transaction, sample_regulatory_rules
        )

        assert len(violations) == 1
        assert violations[0].rule_id == "MAS-FX-001"
        assert violations[0].severity == SeverityLevel.MEDIUM
        assert "350 bps" in violations[0].description
        assert "300 bps" in violations[0].description

    async def test_fx_spread_acceptable(self, sample_transaction, sample_regulatory_rules):
        """Test FX spread within limit passes"""
        sample_transaction.fx_indicator = True
        sample_transaction.fx_spread_bps = 250

        violations = await check_fx_spreads(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_non_fx_transaction(self, sample_transaction, sample_regulatory_rules):
        """Test non-FX transaction is not checked"""
        sample_transaction.fx_indicator = False
        sample_transaction.fx_spread_bps = None

        violations = await check_fx_spreads(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0


@pytest.mark.asyncio
class TestEDDRequirements:
    """Test EDD requirement detection"""

    async def test_edd_required_not_performed(self, sample_transaction, sample_regulatory_rules):
        """Test EDD required but not performed is flagged"""
        sample_transaction.edd_required = True
        sample_transaction.edd_performed = False

        violations = await check_edd_requirements(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 1
        assert "Enhanced Due Diligence required but not performed" in violations[0].description

    async def test_edd_performed(self, sample_transaction, sample_regulatory_rules):
        """Test EDD performed passes"""
        sample_transaction.edd_required = True
        sample_transaction.edd_performed = True

        violations = await check_edd_requirements(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0

    async def test_edd_not_required(self, sample_transaction, sample_regulatory_rules):
        """Test no EDD required passes"""
        sample_transaction.edd_required = False

        violations = await check_edd_requirements(sample_transaction, sample_regulatory_rules)

        assert len(violations) == 0


@pytest.mark.asyncio
class TestStaticRulesAgent:
    """Test full static rules agent integration"""

    async def test_clean_transaction(self, sample_transaction, mock_db_session):
        """Test clean transaction returns no violations"""
        # Mock database queries
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_get_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:

            mock_get_rules.return_value = []

            violations = await static_rules_agent(sample_transaction, mock_db_session)

            assert len(violations) == 0
            mock_get_rules.assert_called_once()
            mock_save_log.assert_called_once()

            # Verify log entry
            log_call = mock_save_log.call_args[0][1]
            assert log_call.agent_name == "static_rules"
            assert log_call.status == "success"

    async def test_multiple_violations(
        self, pep_transaction, mock_db_session, sample_regulatory_rules
    ):
        """Test transaction with multiple violations"""
        # Make it violate multiple rules
        pep_transaction.amount = Decimal("150000.00")  # Cash limit
        pep_transaction.kyc_due_date = date.today() - timedelta(days=30)  # Expired KYC

        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_get_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ):

            mock_get_rules.return_value = sample_regulatory_rules

            violations = await static_rules_agent(pep_transaction, mock_db_session)

            # Should have 4 violations: cash, PEP, KYC, EDD
            assert len(violations) == 4
            rule_ids = [v.rule_id for v in violations]
            assert "HKMA-CASH-001" in rule_ids
            assert "HKMA-PEP-001" in rule_ids
            assert "HKMA-KYC-001" in rule_ids
            assert "HKMA-EDD-001" in rule_ids

    async def test_agent_handles_exception(self, sample_transaction, mock_db_session):
        """Test agent handles exceptions gracefully"""
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_get_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:

            # Simulate error
            mock_get_rules.side_effect = Exception("Database error")

            violations = await static_rules_agent(sample_transaction, mock_db_session)

            # Should return empty list (fail gracefully)
            assert len(violations) == 0

            # Should log error
            log_call = mock_save_log.call_args[0][1]
            assert log_call.status == "error"
            assert "Database error" in log_call.error_message

    async def test_agent_logs_execution_time(self, sample_transaction, mock_db_session):
        """Test agent logs execution time"""
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_get_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:

            mock_get_rules.return_value = []

            await static_rules_agent(sample_transaction, mock_db_session)

            log_call = mock_save_log.call_args[0][1]
            assert log_call.execution_time_ms is not None
            assert log_call.execution_time_ms >= 0
