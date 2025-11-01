"""
Unit tests for Agent 3: Behavioral Pattern Analyzer
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.workflows.agents.behavioral import (
    analyze_velocity,
    detect_smurfing,
    detect_clustering,
    check_geographic_risk,
    check_profile_mismatch,
    behavioral_agent,
)
from app.api.models import SeverityLevel
from app.agent_config_module.agent_config import (
    AgentConfig,
    BehavioralThresholdsConfig,
    GeographicRiskConfig,
    set_agent_config,
)


@pytest.mark.asyncio
class TestVelocityAnalysis:
    """Test velocity anomaly detection"""

    async def test_velocity_high_frequency(
        self, sample_transaction, mock_db_session, high_velocity_transactions
    ):
        """Test high velocity anomaly detection (12 txns in 24h vs avg 3/day)"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = high_velocity_transactions

            flags = await analyze_velocity(sample_transaction, mock_db_session)

            assert len(flags) == 1
            assert flags[0].flag_type == "VELOCITY_ANOMALY"
            assert flags[0].severity in [SeverityLevel.MEDIUM, SeverityLevel.HIGH]
            assert (
                "x normal" in flags[0].description.lower()
                or "multiplier" in flags[0].description.lower()
            )
            assert flags[0].detection_details["transactions_24h"] == 12

    async def test_velocity_normal_rate(
        self, sample_transaction, mock_db_session, historical_transactions
    ):
        """Test normal velocity doesn't flag"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = historical_transactions

            flags = await analyze_velocity(sample_transaction, mock_db_session)

            assert len(flags) == 0

    async def test_velocity_insufficient_history(
        self, sample_transaction, mock_db_session, historical_transactions
    ):
        """Test insufficient history returns no flags"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            # Return only 3 transactions (below min_history_for_analysis default of 5)
            mock_get.return_value = historical_transactions[:3]

            flags = await analyze_velocity(sample_transaction, mock_db_session)

            assert len(flags) == 0

    async def test_velocity_custom_threshold(
        self, sample_transaction, mock_db_session, high_velocity_transactions
    ):
        """Test custom velocity threshold"""
        # Set higher threshold (10x instead of 3x default)
        # Data has 9x multiplier, so 10x threshold should not flag
        custom_config = AgentConfig(
            behavioral_thresholds=BehavioralThresholdsConfig(velocity_multiplier_threshold=10.0)
        )
        set_agent_config(custom_config)

        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = high_velocity_transactions

            flags = await analyze_velocity(sample_transaction, mock_db_session)

            # Should not flag at 9x with 10x threshold
            assert len(flags) == 0

    async def test_velocity_handles_exception(self, sample_transaction, mock_db_session):
        """Test velocity analysis handles exceptions gracefully"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = Exception("Database error")

            flags = await analyze_velocity(sample_transaction, mock_db_session)

            assert len(flags) == 0  # Fail gracefully


@pytest.mark.asyncio
class TestSmurfingDetection:
    """Test smurfing pattern detection"""

    async def test_smurfing_detection_same_day(
        self, sample_transaction, mock_db_session, smurfing_transactions
    ):
        """Test smurfing pattern: 5 × HKD 7,000 on same day"""
        with patch(
            "app.workflows.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = smurfing_transactions

            flags = await detect_smurfing(sample_transaction, mock_db_session)

            assert len(flags) == 1
            assert flags[0].flag_type == "SMURFING_PATTERN"
            assert flags[0].severity in [SeverityLevel.MEDIUM, SeverityLevel.HIGH]
            assert flags[0].detection_details["transaction_count"] == 5
            assert flags[0].detection_details["total_amount"] == 35000.0
            assert "7,000" in flags[0].description

    async def test_smurfing_insufficient_transactions(
        self, sample_transaction, mock_db_session, smurfing_transactions
    ):
        """Test insufficient transactions (< 3) doesn't flag"""
        with patch(
            "app.workflows.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_get:
            # Only 2 transactions
            mock_get.return_value = smurfing_transactions[:2]

            flags = await detect_smurfing(sample_transaction, mock_db_session)

            assert len(flags) == 0

    async def test_smurfing_transactions_above_threshold(
        self, sample_transaction, mock_db_session, smurfing_transactions
    ):
        """Test transactions above threshold don't flag as smurfing"""
        # Make amounts above threshold
        for txn in smurfing_transactions:
            txn.amount = Decimal("9000.00")  # Above HKD 8,000

        with patch(
            "app.workflows.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = smurfing_transactions

            flags = await detect_smurfing(sample_transaction, mock_db_session)

            assert len(flags) == 0

    async def test_smurfing_high_variation_amounts(
        self, sample_transaction, mock_db_session, smurfing_transactions
    ):
        """Test high variation in amounts doesn't flag"""
        # Make amounts varied
        for i, txn in enumerate(smurfing_transactions):
            txn.amount = Decimal(str(1000 + i * 2000))  # 1K, 3K, 5K, 7K, 9K

        with patch(
            "app.workflows.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = smurfing_transactions

            flags = await detect_smurfing(sample_transaction, mock_db_session)

            assert len(flags) == 0


@pytest.mark.asyncio
class TestClusteringDetection:
    """Test clustering pattern detection"""

    async def test_clustering_similar_amounts(
        self, sample_transaction, mock_db_session, historical_transactions
    ):
        """Test clustering detection with similar amounts"""
        # Use historical transactions but modify amounts to be similar (low variation)
        clustering_txns = historical_transactions[:7]
        for i, txn in enumerate(clustering_txns):
            txn.amount = Decimal("5000.00") + Decimal(str(i * 10))  # 5000, 5010, 5020...
            txn.currency = "HKD"

        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = clustering_txns

            flags = await detect_clustering(sample_transaction, mock_db_session)

            assert len(flags) == 1
            assert flags[0].flag_type == "CLUSTERING_PATTERN"
            assert flags[0].severity == SeverityLevel.MEDIUM
            assert flags[0].detection_details["coeff_variation_pct"] < 15

    async def test_clustering_insufficient_transactions(
        self, sample_transaction, mock_db_session, historical_transactions
    ):
        """Test insufficient transactions for clustering"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = historical_transactions[:3]  # < 5 transactions

            flags = await detect_clustering(sample_transaction, mock_db_session)

            assert len(flags) == 0

    async def test_clustering_high_variation(
        self, sample_transaction, mock_db_session, historical_transactions
    ):
        """Test high variation doesn't flag clustering"""
        # Normal transactions have high variation
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = historical_transactions

            flags = await detect_clustering(sample_transaction, mock_db_session)

            assert len(flags) == 0


@pytest.mark.asyncio
class TestGeographicRisk:
    """Test geographic risk detection"""

    async def test_geographic_high_risk_originator(self, sample_transaction, mock_db_session):
        """Test high-risk originator country (Iran)"""
        sample_transaction.originator_country = "IR"
        sample_transaction.beneficiary_country = "US"

        flags = await check_geographic_risk(sample_transaction, mock_db_session)

        assert len(flags) == 1
        assert flags[0].flag_type == "GEOGRAPHIC_RISK"
        assert flags[0].severity == SeverityLevel.HIGH
        assert flags[0].score == 70
        assert "IR" in flags[0].description

    async def test_geographic_high_risk_beneficiary(self, sample_transaction, mock_db_session):
        """Test high-risk beneficiary country (North Korea)"""
        sample_transaction.originator_country = "US"
        sample_transaction.beneficiary_country = "KP"

        flags = await check_geographic_risk(sample_transaction, mock_db_session)

        assert len(flags) == 1
        assert "KP" in flags[0].description

    async def test_geographic_both_high_risk(self, sample_transaction, mock_db_session):
        """Test both originator and beneficiary high-risk"""
        sample_transaction.originator_country = "IR"
        sample_transaction.beneficiary_country = "SY"

        flags = await check_geographic_risk(sample_transaction, mock_db_session)

        assert len(flags) == 1
        assert "IR" in flags[0].description
        assert "SY" in flags[0].description
        assert len(flags[0].detection_details["high_risk_parties"]) == 2

    async def test_geographic_low_risk(self, sample_transaction, mock_db_session):
        """Test low-risk countries don't flag"""
        sample_transaction.originator_country = "US"
        sample_transaction.beneficiary_country = "GB"

        flags = await check_geographic_risk(sample_transaction, mock_db_session)

        assert len(flags) == 0

    async def test_geographic_custom_high_risk_list(self, sample_transaction, mock_db_session):
        """Test custom high-risk country list"""
        custom_config = AgentConfig(
            geographic_risk=GeographicRiskConfig(high_risk_countries=["CN", "RU"])
        )
        set_agent_config(custom_config)

        sample_transaction.originator_country = "CN"
        sample_transaction.beneficiary_country = "US"

        flags = await check_geographic_risk(sample_transaction, mock_db_session)

        assert len(flags) == 1
        assert "CN" in flags[0].description


@pytest.mark.asyncio
class TestProfileMismatch:
    """Test profile mismatch detection"""

    async def test_profile_mismatch_low_risk_complex_product(
        self, sample_transaction, mock_db_session
    ):
        """Test low-risk customer trading complex products"""
        sample_transaction.customer_risk_rating = "LOW"
        sample_transaction.product_complex = True
        sample_transaction.suitability_assessed = False

        flags = await check_profile_mismatch(sample_transaction, mock_db_session)

        assert len(flags) == 1
        assert flags[0].flag_type == "PROFILE_MISMATCH"
        assert flags[0].severity == SeverityLevel.MEDIUM
        assert flags[0].score == 40
        assert "LOW" in flags[0].description
        assert "complex" in flags[0].description.lower()

    async def test_profile_mismatch_with_suitability(self, sample_transaction, mock_db_session):
        """Test suitability assessed prevents flag"""
        sample_transaction.customer_risk_rating = "LOW"
        sample_transaction.product_complex = True
        sample_transaction.suitability_assessed = True

        flags = await check_profile_mismatch(sample_transaction, mock_db_session)

        assert len(flags) == 0

    async def test_profile_mismatch_high_risk_complex_ok(self, sample_transaction, mock_db_session):
        """Test high-risk customer can trade complex products"""
        sample_transaction.customer_risk_rating = "HIGH"
        sample_transaction.product_complex = True
        sample_transaction.suitability_assessed = False

        flags = await check_profile_mismatch(sample_transaction, mock_db_session)

        assert len(flags) == 0

    async def test_profile_mismatch_simple_product_ok(self, sample_transaction, mock_db_session):
        """Test simple products don't flag"""
        sample_transaction.customer_risk_rating = "LOW"
        sample_transaction.product_complex = False

        flags = await check_profile_mismatch(sample_transaction, mock_db_session)

        assert len(flags) == 0


@pytest.mark.asyncio
class TestBehavioralAgent:
    """Test full behavioral agent integration"""

    async def test_clean_transaction(self, sample_transaction, mock_db_session):
        """Test clean transaction returns no flags"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get_hist, patch(
            "app.workflows.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_get_time, patch(
            "app.workflows.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:

            # Return insufficient history (< 5 transactions)
            mock_get_hist.return_value = []
            mock_get_time.return_value = []

            flags = await behavioral_agent(sample_transaction, mock_db_session)

            assert len(flags) == 0
            mock_save_log.assert_called_once()

            # Verify log entry
            log_call = mock_save_log.call_args[0][1]
            assert log_call.agent_name == "behavioral_analyzer"
            assert log_call.status == "success"

    async def test_multiple_flags(
        self, sample_transaction, mock_db_session, high_velocity_transactions, smurfing_transactions
    ):
        """Test transaction triggering multiple behavioral flags"""
        sample_transaction.originator_country = "IR"  # Geographic risk
        sample_transaction.customer_risk_rating = "LOW"
        sample_transaction.product_complex = True
        sample_transaction.suitability_assessed = False  # Profile mismatch

        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get_hist, patch(
            "app.workflows.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_get_time, patch(
            "app.workflows.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ):

            mock_get_hist.return_value = high_velocity_transactions
            mock_get_time.return_value = smurfing_transactions

            flags = await behavioral_agent(sample_transaction, mock_db_session)

            # Should have velocity, smurfing, geographic, and profile flags
            assert len(flags) >= 2
            flag_types = [f.flag_type for f in flags]
            assert any(
                "VELOCITY" in ft or "SMURFING" in ft or "GEOGRAPHIC" in ft or "PROFILE" in ft
                for ft in flag_types
            )

    async def test_agent_handles_exception(self, sample_transaction, mock_db_session):
        """Test behavioral agent handles exceptions gracefully"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get, patch(
            "app.workflows.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:

            mock_get.side_effect = Exception("Database error")

            flags = await behavioral_agent(sample_transaction, mock_db_session)

            # Should return empty list (fail gracefully)
            assert len(flags) == 0

            # Individual checks log errors but agent completes successfully
            # This is graceful degradation - the agent doesn't fail completely
            log_call = mock_save_log.call_args[0][1]
            assert log_call.status == "success"
            assert log_call.output_data["flags_count"] == 0

    async def test_agent_logs_execution_time(self, sample_transaction, mock_db_session):
        """Test behavioral agent logs execution time"""
        with patch(
            "app.workflows.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_get, patch(
            "app.workflows.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_get_time, patch(
            "app.workflows.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:

            mock_get.return_value = []
            mock_get_time.return_value = []

            await behavioral_agent(sample_transaction, mock_db_session)

            log_call = mock_save_log.call_args[0][1]
            assert log_call.execution_time_ms is not None
            assert log_call.execution_time_ms >= 0
