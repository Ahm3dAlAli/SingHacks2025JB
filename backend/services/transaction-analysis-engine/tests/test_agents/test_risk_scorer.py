"""
Unit tests for Agent 4: Risk Scorer
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.workflows.agents.risk_scorer import (
    aggregate_static_scores,
    aggregate_behavioral_scores,
    apply_jurisdiction_weight,
    calculate_final_score,
    classify_alert_level,
    generate_explanation,
    risk_scorer_agent,
)
from app.api.models import AlertLevel
from app.agent_config_module.agent_config import (
    AgentConfig,
    JurisdictionConfig,
    AlertThresholdsConfig,
    set_agent_config,
)


class TestScoreAggregation:
    """Test score aggregation functions"""

    def test_aggregate_static_scores(self, sample_rule_violations):
        """Test aggregation of static rule violation scores"""
        total = aggregate_static_scores(sample_rule_violations)

        # 65 + 100 + 65 = 230
        assert total == 230

    def test_aggregate_static_scores_empty(self):
        """Test aggregation with no violations"""
        total = aggregate_static_scores([])
        assert total == 0

    def test_aggregate_behavioral_scores(self, sample_behavioral_flags):
        """Test aggregation of behavioral flag scores"""
        total = aggregate_behavioral_scores(sample_behavioral_flags)

        # 45 + 60 = 105
        assert total == 105

    def test_aggregate_behavioral_scores_empty(self):
        """Test aggregation with no flags"""
        total = aggregate_behavioral_scores([])
        assert total == 0


class TestJurisdictionWeights:
    """Test jurisdiction weight application"""

    def test_jurisdiction_weight_hk(self):
        """Test Hong Kong weight (1.2x)"""
        weighted = apply_jurisdiction_weight(100, "HK")
        assert weighted == 120.0

    def test_jurisdiction_weight_sg(self):
        """Test Singapore weight (1.0x - baseline)"""
        weighted = apply_jurisdiction_weight(100, "SG")
        assert weighted == 100.0

    def test_jurisdiction_weight_ch(self):
        """Test Switzerland weight (1.1x)"""
        import pytest

        weighted = apply_jurisdiction_weight(100, "CH")
        assert weighted == pytest.approx(110.0)

    def test_jurisdiction_weight_unknown(self):
        """Test unknown jurisdiction defaults to 1.0x"""
        weighted = apply_jurisdiction_weight(100, "XX")
        assert weighted == 100.0

    def test_jurisdiction_weight_case_insensitive(self):
        """Test jurisdiction code is case insensitive"""
        weighted_lower = apply_jurisdiction_weight(100, "hk")
        weighted_upper = apply_jurisdiction_weight(100, "HK")
        assert weighted_lower == weighted_upper == 120.0

    def test_custom_jurisdiction_weights(self):
        """Test custom jurisdiction weights configuration"""
        custom_config = AgentConfig(
            jurisdiction=JurisdictionConfig(hk_weight=1.5, sg_weight=1.2, ch_weight=1.3)
        )
        set_agent_config(custom_config)

        weighted = apply_jurisdiction_weight(100, "HK")
        assert weighted == 150.0


class TestFinalScoreCalculation:
    """Test final score calculation"""

    def test_calculate_final_score_basic(self):
        """Test basic final score calculation"""
        # (100 + 50) / 2 = 75 * 1.0 = 75
        score, weight = calculate_final_score(100, 50, "SG")
        assert score == 75
        assert weight == 1.0

    def test_calculate_final_score_hk_jurisdiction(self):
        """Test HK jurisdiction with weight multiplier"""
        # (100 + 50) / 2 = 75 * 1.2 = 90
        score, weight = calculate_final_score(100, 50, "HK")
        assert score == 90
        assert weight == 1.2

    def test_calculate_final_score_capped_at_100(self):
        """Test score is capped at 100"""
        # (200 + 100) / 2 = 150 * 1.2 = 180, capped at 100
        score, weight = calculate_final_score(200, 100, "HK")
        assert score == 100
        assert weight == 1.2

    def test_calculate_final_score_zero(self):
        """Test zero scores"""
        score, weight = calculate_final_score(0, 0, "SG")
        assert score == 0
        assert weight == 1.0

    def test_calculate_final_score_unbalanced(self):
        """Test unbalanced scores (high static, low behavioral)"""
        # (150 + 10) / 2 = 80 * 1.0 = 80
        score, weight = calculate_final_score(150, 10, "SG")
        assert score == 80


class TestAlertLevelClassification:
    """Test alert level classification"""

    def test_alert_level_critical(self):
        """Test CRITICAL classification (76-100)"""
        assert classify_alert_level(100) == AlertLevel.CRITICAL
        assert classify_alert_level(90) == AlertLevel.CRITICAL
        assert classify_alert_level(76) == AlertLevel.CRITICAL

    def test_alert_level_high(self):
        """Test HIGH classification (51-75)"""
        assert classify_alert_level(75) == AlertLevel.HIGH
        assert classify_alert_level(65) == AlertLevel.HIGH
        assert classify_alert_level(51) == AlertLevel.HIGH

    def test_alert_level_medium(self):
        """Test MEDIUM classification (26-50)"""
        assert classify_alert_level(50) == AlertLevel.MEDIUM
        assert classify_alert_level(35) == AlertLevel.MEDIUM
        assert classify_alert_level(26) == AlertLevel.MEDIUM

    def test_alert_level_low(self):
        """Test LOW classification (0-25)"""
        assert classify_alert_level(25) == AlertLevel.LOW
        assert classify_alert_level(10) == AlertLevel.LOW
        assert classify_alert_level(0) == AlertLevel.LOW

    def test_alert_level_boundary_values(self):
        """Test boundary values between classifications"""
        # Test boundaries
        assert classify_alert_level(76) == AlertLevel.CRITICAL  # Just above HIGH
        assert classify_alert_level(75) == AlertLevel.HIGH  # Just below CRITICAL
        assert classify_alert_level(51) == AlertLevel.HIGH  # Just above MEDIUM
        assert classify_alert_level(50) == AlertLevel.MEDIUM  # Just below HIGH
        assert classify_alert_level(26) == AlertLevel.MEDIUM  # Just above LOW
        assert classify_alert_level(25) == AlertLevel.LOW  # Just below MEDIUM

    def test_alert_level_custom_thresholds(self):
        """Test custom alert thresholds"""
        custom_config = AgentConfig(
            alert_thresholds=AlertThresholdsConfig(
                critical_threshold=80, high_threshold=60, medium_threshold=30
            )
        )
        set_agent_config(custom_config)

        assert classify_alert_level(85) == AlertLevel.CRITICAL
        assert classify_alert_level(70) == AlertLevel.HIGH
        assert classify_alert_level(40) == AlertLevel.MEDIUM
        assert classify_alert_level(20) == AlertLevel.LOW


class TestExplanationGeneration:
    """Test explanation text generation"""

    def test_explanation_with_violations_and_flags(
        self, sample_rule_violations, sample_behavioral_flags
    ):
        """Test explanation with both violations and flags"""
        explanation = generate_explanation(
            risk_score=85,
            alert_level=AlertLevel.CRITICAL,
            violations=sample_rule_violations,
            flags=sample_behavioral_flags,
            static_score=230,
            behavioral_score=105,
        )

        assert "Risk score 85" in explanation
        assert "CRITICAL" in explanation
        assert "3 regulatory violation" in explanation
        assert "2 behavioral pattern" in explanation
        assert "230" in explanation
        assert "105" in explanation

    def test_explanation_violations_only(self, sample_rule_violations):
        """Test explanation with violations only"""
        explanation = generate_explanation(
            risk_score=65,
            alert_level=AlertLevel.HIGH,
            violations=sample_rule_violations,
            flags=[],
            static_score=230,
            behavioral_score=0,
        )

        assert "Risk score 65" in explanation
        assert "HIGH" in explanation
        assert "3 regulatory violation" in explanation
        assert "No suspicious behavioral patterns" in explanation

    def test_explanation_flags_only(self, sample_behavioral_flags):
        """Test explanation with behavioral flags only"""
        explanation = generate_explanation(
            risk_score=50,
            alert_level=AlertLevel.MEDIUM,
            violations=[],
            flags=sample_behavioral_flags,
            static_score=0,
            behavioral_score=105,
        )

        assert "Risk score 50" in explanation
        assert "MEDIUM" in explanation
        assert "No regulatory violations" in explanation
        assert "2 behavioral pattern" in explanation

    def test_explanation_clean_transaction(self):
        """Test explanation for clean transaction"""
        explanation = generate_explanation(
            risk_score=5,
            alert_level=AlertLevel.LOW,
            violations=[],
            flags=[],
            static_score=0,
            behavioral_score=0,
        )

        assert "Risk score 5" in explanation
        assert "LOW" in explanation
        assert "No regulatory violations" in explanation
        assert "No suspicious behavioral patterns" in explanation

    def test_explanation_truncates_long_lists(
        self, sample_rule_violations, sample_behavioral_flags
    ):
        """Test explanation truncates lists longer than 3 items"""
        # Add more violations
        many_violations = sample_rule_violations * 3  # 9 violations

        explanation = generate_explanation(
            risk_score=100,
            alert_level=AlertLevel.CRITICAL,
            violations=many_violations,
            flags=sample_behavioral_flags,
            static_score=690,
            behavioral_score=105,
        )

        assert "9 regulatory violation" in explanation
        assert "and 6 more" in explanation  # Shows first 3, then "and 6 more"


@pytest.mark.asyncio
class TestRiskScorerAgent:
    """Test full risk scorer agent integration"""

    async def test_clean_transaction_scoring(self, sample_transaction, mock_db_session):
        """Test scoring clean transaction (no violations or flags)"""
        with patch(
            "app.workflows.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:
            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations=[], flags=[], session=mock_db_session
            )

            assert score == 0
            assert level == "LOW"
            assert "No regulatory violations" in explanation
            assert "No suspicious behavioral patterns" in explanation

            mock_save_log.assert_called_once()
            log_call = mock_save_log.call_args[0][1]
            assert log_call.agent_name == "risk_scorer"
            assert log_call.status == "success"

    async def test_high_risk_transaction(
        self, sample_transaction, mock_db_session, sample_rule_violations, sample_behavioral_flags
    ):
        """Test scoring high-risk transaction"""
        with patch("app.workflows.agents.risk_scorer.save_agent_log", new_callable=AsyncMock):
            score, level, explanation = await risk_scorer_agent(
                sample_transaction,
                violations=sample_rule_violations,
                flags=sample_behavioral_flags,
                session=mock_db_session,
            )

            # (230 + 105) / 2 = 167.5 * 1.2 (HK) = 201, capped at 100
            assert score == 100
            assert level == "CRITICAL"
            assert "3 regulatory violation" in explanation
            assert "2 behavioral pattern" in explanation

    async def test_medium_risk_transaction(
        self, sample_transaction, mock_db_session, sample_rule_violations
    ):
        """Test scoring medium-risk transaction"""
        # Take only 1 violation
        single_violation = [sample_rule_violations[0]]

        with patch("app.workflows.agents.risk_scorer.save_agent_log", new_callable=AsyncMock):
            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations=single_violation, flags=[], session=mock_db_session
            )

            # (65 + 0) / 2 = 32.5 * 1.2 = 39
            assert 30 <= score <= 50
            assert level in ["MEDIUM", "HIGH"]

    async def test_jurisdiction_weight_affects_score(
        self, sample_transaction, mock_db_session, sample_rule_violations
    ):
        """Test different jurisdictions affect final score"""
        # Use only one violation to avoid hitting the 100 cap
        single_violation = [sample_rule_violations[0]]  # Score: 65

        with patch("app.workflows.agents.risk_scorer.save_agent_log", new_callable=AsyncMock):
            # HK (1.2x): (65 + 0) / 2 = 32.5 * 1.2 = 39
            sample_transaction.booking_jurisdiction = "HK"
            score_hk, _, _ = await risk_scorer_agent(
                sample_transaction,
                violations=single_violation,
                flags=[],
                session=mock_db_session,
            )

            # SG (1.0x): (65 + 0) / 2 = 32.5 * 1.0 = 32.5
            sample_transaction.booking_jurisdiction = "SG"
            score_sg, _, _ = await risk_scorer_agent(
                sample_transaction,
                violations=single_violation,
                flags=[],
                session=mock_db_session,
            )

            # HK should have higher score due to weight (39 vs 32)
            assert score_hk > score_sg

    async def test_agent_handles_exception(self, sample_transaction, mock_db_session):
        """Test risk scorer handles exceptions gracefully"""
        with patch(
            "app.workflows.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:
            # Cause error by making violations None
            mock_save_log.side_effect = [None, Exception("Database error")]

            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations=[], flags=[], session=mock_db_session
            )

            # First call succeeds, second call (error log) fails
            # But we already got results from first call
            assert score == 0
            assert level == "LOW"

    async def test_agent_logs_execution_time(self, sample_transaction, mock_db_session):
        """Test risk scorer logs execution time"""
        with patch(
            "app.workflows.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:
            await risk_scorer_agent(
                sample_transaction, violations=[], flags=[], session=mock_db_session
            )

            log_call = mock_save_log.call_args[0][1]
            assert log_call.execution_time_ms is not None
            assert log_call.execution_time_ms >= 0

    async def test_agent_logs_all_details(
        self, sample_transaction, mock_db_session, sample_rule_violations, sample_behavioral_flags
    ):
        """Test risk scorer logs all relevant details"""
        with patch(
            "app.workflows.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ) as mock_save_log:
            await risk_scorer_agent(
                sample_transaction,
                violations=sample_rule_violations,
                flags=sample_behavioral_flags,
                session=mock_db_session,
            )

            log_call = mock_save_log.call_args[0][1]
            assert log_call.input_data["violations_count"] == 3
            assert log_call.input_data["flags_count"] == 2
            assert "risk_score" in log_call.output_data
            assert "alert_level" in log_call.output_data
            assert "jurisdiction_weight" in log_call.output_data
