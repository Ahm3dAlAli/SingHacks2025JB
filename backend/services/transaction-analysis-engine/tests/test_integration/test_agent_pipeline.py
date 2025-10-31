"""
Integration tests for full agent pipeline (Agent 2 → Agent 3 → Agent 4)
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from app.langgraph.agents.static_rules import static_rules_agent
from app.langgraph.agents.behavioral import behavioral_agent
from app.langgraph.agents.risk_scorer import risk_scorer_agent


@pytest.mark.asyncio
class TestAgentPipeline:
    """Test full agent pipeline integration"""

    async def test_clean_transaction_pipeline(
        self, sample_transaction, mock_db_session, sample_regulatory_rules
    ):
        """Test clean transaction through full pipeline"""
        # Mock database calls
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ):

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = []  # No history
            mock_time.return_value = []

            # Agent 2: Static Rules
            violations = await static_rules_agent(sample_transaction, mock_db_session)
            assert len(violations) == 0

            # Agent 3: Behavioral
            flags = await behavioral_agent(sample_transaction, mock_db_session)
            assert len(flags) == 0

            # Agent 4: Risk Scorer
            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations, flags, mock_db_session
            )

            assert score == 0
            assert level == "LOW"
            assert "No regulatory violations" in explanation
            assert "No suspicious behavioral patterns" in explanation

    async def test_sanctions_hit_pipeline(
        self, sanctions_hit_transaction, mock_db_session, sample_regulatory_rules
    ):
        """Test sanctions hit (CRITICAL) through pipeline"""
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ):

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = []
            mock_time.return_value = []

            # Agent 2: Should detect sanctions hit
            violations = await static_rules_agent(sanctions_hit_transaction, mock_db_session)
            assert len(violations) >= 1
            assert any(v.severity.value == "CRITICAL" for v in violations)

            # Agent 3: Should detect geographic risk (Iran)
            flags = await behavioral_agent(sanctions_hit_transaction, mock_db_session)
            assert len(flags) >= 1
            assert any(f.flag_type == "GEOGRAPHIC_RISK" for f in flags)

            # Agent 4: Should classify as CRITICAL
            score, level, explanation = await risk_scorer_agent(
                sanctions_hit_transaction, violations, flags, mock_db_session
            )

            assert score >= 76
            assert level == "CRITICAL"
            assert "Sanctions" in explanation or "GEOGRAPHIC" in explanation

    async def test_smurfing_pattern_pipeline(
        self, sample_transaction, mock_db_session, sample_regulatory_rules, smurfing_transactions
    ):
        """Test smurfing pattern detection (HIGH) through pipeline"""
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ):

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = smurfing_transactions
            mock_time.return_value = smurfing_transactions

            # Agent 2: No static violations (amounts below threshold individually)
            violations = await static_rules_agent(sample_transaction, mock_db_session)
            assert len(violations) == 0

            # Agent 3: Should detect smurfing pattern
            flags = await behavioral_agent(sample_transaction, mock_db_session)
            assert len(flags) >= 1
            assert any(f.flag_type == "SMURFING_PATTERN" for f in flags)

            # Agent 4: Should classify as HIGH or MEDIUM
            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations, flags, mock_db_session
            )

            assert score >= 26  # At least MEDIUM
            assert level in ["HIGH", "MEDIUM"]
            assert "SMURFING" in explanation or "behavioral pattern" in explanation.lower()

    async def test_expired_kyc_pipeline(
        self, expired_kyc_transaction, mock_db_session, sample_regulatory_rules
    ):
        """Test expired KYC (HIGH) through pipeline"""
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ):

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = []
            mock_time.return_value = []

            # Agent 2: Should detect expired KYC
            violations = await static_rules_agent(expired_kyc_transaction, mock_db_session)
            assert len(violations) >= 1
            assert any("KYC" in v.rule_id for v in violations)

            # Agent 3: No behavioral issues
            flags = await behavioral_agent(expired_kyc_transaction, mock_db_session)
            # May or may not have flags depending on data

            # Agent 4: Should classify as HIGH or MEDIUM
            score, level, explanation = await risk_scorer_agent(
                expired_kyc_transaction, violations, flags, mock_db_session
            )

            assert score >= 26
            assert level in ["HIGH", "MEDIUM"]
            assert "KYC" in explanation or "regulatory violation" in explanation.lower()

    async def test_multiple_violations_high_velocity_pipeline(
        self, pep_transaction, mock_db_session, sample_regulatory_rules, high_velocity_transactions
    ):
        """Test multiple violations + high velocity (CRITICAL) through pipeline"""
        # Make PEP transaction also have high value and expired KYC
        pep_transaction.amount = Decimal("150000.00")
        pep_transaction.kyc_due_date = date.today() - timedelta(days=30)

        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ):

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = high_velocity_transactions
            mock_time.return_value = []

            # Agent 2: Should detect PEP, cash limit, expired KYC
            violations = await static_rules_agent(pep_transaction, mock_db_session)
            assert len(violations) >= 3

            # Agent 3: Should detect velocity anomaly
            flags = await behavioral_agent(pep_transaction, mock_db_session)
            assert len(flags) >= 1
            assert any(f.flag_type == "VELOCITY_ANOMALY" for f in flags)

            # Agent 4: Should classify as CRITICAL (high scores)
            score, level, explanation = await risk_scorer_agent(
                pep_transaction, violations, flags, mock_db_session
            )

            assert score >= 76
            assert level == "CRITICAL"
            assert "PEP" in explanation or "regulatory violation" in explanation.lower()
            assert "VELOCITY" in explanation or "behavioral pattern" in explanation.lower()

    async def test_pipeline_state_flow(
        self, sample_transaction, mock_db_session, sample_regulatory_rules
    ):
        """Test state flows correctly through pipeline"""
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ):

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = []
            mock_time.return_value = []

            # Simulate state flow
            state = {
                "transaction": sample_transaction,
                "regulatory_rules": [],
                "static_violations": [],
                "behavioral_flags": [],
                "risk_score": 0,
                "alert_level": "LOW",
                "explanation": "",
            }

            # Agent 2 updates state
            violations = await static_rules_agent(sample_transaction, mock_db_session)
            state["static_violations"] = violations
            state["regulatory_rules"] = mock_rules.return_value

            # Agent 3 updates state
            flags = await behavioral_agent(sample_transaction, mock_db_session)
            state["behavioral_flags"] = flags

            # Agent 4 updates state
            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations, flags, mock_db_session
            )
            state["risk_score"] = score
            state["alert_level"] = level
            state["explanation"] = explanation

            # Verify complete state
            assert state["transaction"] == sample_transaction
            assert isinstance(state["static_violations"], list)
            assert isinstance(state["behavioral_flags"], list)
            assert isinstance(state["risk_score"], int)
            assert state["alert_level"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
            assert isinstance(state["explanation"], str)

    async def test_pipeline_all_agents_log_execution(
        self, sample_transaction, mock_db_session, sample_regulatory_rules
    ):
        """Test all agents log their execution"""
        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ) as mock_log1, patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ) as mock_log2, patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ) as mock_log3:

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = []
            mock_time.return_value = []

            # Run full pipeline
            violations = await static_rules_agent(sample_transaction, mock_db_session)
            flags = await behavioral_agent(sample_transaction, mock_db_session)
            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations, flags, mock_db_session
            )

            # Verify all agents logged
            mock_log1.assert_called_once()
            mock_log2.assert_called_once()
            mock_log3.assert_called_once()

            # Verify log entries have correct agent names
            assert mock_log1.call_args[0][1].agent_name == "static_rules"
            assert mock_log2.call_args[0][1].agent_name == "behavioral_analyzer"
            assert mock_log3.call_args[0][1].agent_name == "risk_scorer"

    async def test_pipeline_performance(
        self, sample_transaction, mock_db_session, sample_regulatory_rules
    ):
        """Test pipeline completes within reasonable time"""
        import time

        with patch(
            "app.langgraph.agents.static_rules.get_regulatory_rules", new_callable=AsyncMock
        ) as mock_rules, patch(
            "app.langgraph.agents.static_rules.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.behavioral.get_customer_transactions", new_callable=AsyncMock
        ) as mock_hist, patch(
            "app.langgraph.agents.behavioral.get_transactions_by_timeframe", new_callable=AsyncMock
        ) as mock_time, patch(
            "app.langgraph.agents.behavioral.save_agent_log", new_callable=AsyncMock
        ), patch(
            "app.langgraph.agents.risk_scorer.save_agent_log", new_callable=AsyncMock
        ):

            mock_rules.return_value = sample_regulatory_rules
            mock_hist.return_value = []
            mock_time.return_value = []

            start = time.time()

            # Run full pipeline
            violations = await static_rules_agent(sample_transaction, mock_db_session)
            flags = await behavioral_agent(sample_transaction, mock_db_session)
            score, level, explanation = await risk_scorer_agent(
                sample_transaction, violations, flags, mock_db_session
            )

            elapsed = time.time() - start

            # Should complete in less than 1 second (with mocks)
            assert elapsed < 1.0
