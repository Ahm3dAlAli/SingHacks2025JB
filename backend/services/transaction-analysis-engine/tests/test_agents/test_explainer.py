"""
Unit tests for Agent 5: Explainer
"""

import pytest
from unittest.mock import AsyncMock, patch

from app.workflows.agents.explainer import explainer_agent
from app.api.models import RuleViolation, BehavioralFlag, SeverityLevel


@pytest.mark.asyncio
class TestExplainer:
    """Test explainer agent functionality"""

    async def test_explainer_critical_alert(
        self,
        mock_db_session,
        high_value_transaction,
        mock_groq_response_explainer,
        sample_rule_violations,
        sample_behavioral_flags,
    ):
        """Test explanation generation for CRITICAL alert"""
        with patch("app.workflows.agents.explainer.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value=mock_groq_response_explainer)
            mock_get_client.return_value = mock_client

            result = await explainer_agent(
                transaction=high_value_transaction,
                session=mock_db_session,
                risk_score=85,
                alert_level="CRITICAL",
                static_violations=sample_rule_violations[:2],
                behavioral_flags=sample_behavioral_flags[:1],
            )

            assert "explanation" in result
            assert len(result["explanation"]) > 50  # Should be substantive
            assert result["recommended_action"] == "ENHANCED_DUE_DILIGENCE"
            assert result["confidence"] == "HIGH"
            assert len(result["regulatory_basis"]) > 0

    async def test_explainer_low_risk(
        self, mock_db_session, sample_transaction, mock_groq_response_explainer
    ):
        """Test explanation generation for LOW risk transaction"""
        low_risk_response = {
            "explanation": "Transaction presents low risk with no significant violations.",
            "regulatory_basis": [],
            "evidence": [],
            "recommended_action": "MONITORING_ONLY",
            "confidence": "HIGH",
        }

        with patch("app.workflows.agents.explainer.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value=low_risk_response)
            mock_get_client.return_value = mock_client

            result = await explainer_agent(
                transaction=sample_transaction,
                session=mock_db_session,
                risk_score=15,
                alert_level="LOW",
                static_violations=[],
                behavioral_flags=[],
            )

            assert result["recommended_action"] == "MONITORING_ONLY"
            assert result["confidence"] == "HIGH"

    async def test_explainer_missing_fields(self, mock_db_session, sample_transaction):
        """Test handling of missing fields in response"""
        incomplete_response = {
            "explanation": "Transaction flagged",
            # Missing other fields
        }

        with patch("app.workflows.agents.explainer.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value=incomplete_response)
            mock_get_client.return_value = mock_client

            result = await explainer_agent(
                transaction=sample_transaction,
                session=mock_db_session,
                risk_score=50,
                alert_level="MEDIUM",
                static_violations=[],
                behavioral_flags=[],
            )

            # Should provide defaults
            assert "explanation" in result
            assert "regulatory_basis" in result
            assert "recommended_action" in result
            assert "confidence" in result

    async def test_explainer_invalid_recommended_action(self, mock_db_session, sample_transaction):
        """Test validation of recommended_action field"""
        invalid_response = {
            "explanation": "Transaction flagged",
            "regulatory_basis": [],
            "evidence": [],
            "recommended_action": "INVALID_ACTION",  # Invalid
            "confidence": "HIGH",
        }

        with patch("app.workflows.agents.explainer.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value=invalid_response)
            mock_get_client.return_value = mock_client

            result = await explainer_agent(
                transaction=sample_transaction,
                session=mock_db_session,
                risk_score=50,
                alert_level="MEDIUM",
                static_violations=[],
                behavioral_flags=[],
            )

            # Should default to valid action
            assert result["recommended_action"] in [
                "HOLD_TRANSACTION",
                "ENHANCED_DUE_DILIGENCE",
                "FILE_STR",
                "MONITORING_ONLY",
            ]

    async def test_explainer_groq_api_error(
        self, mock_db_session, sample_transaction, sample_rule_violations, sample_behavioral_flags
    ):
        """Test fallback when Groq API fails"""
        from app.services.groq_client import GroqAPIError

        with patch("app.workflows.agents.explainer.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(side_effect=GroqAPIError("API Error"))
            mock_get_client.return_value = mock_client

            result = await explainer_agent(
                transaction=sample_transaction,
                session=mock_db_session,
                risk_score=75,
                alert_level="HIGH",
                static_violations=sample_rule_violations[:1],
                behavioral_flags=sample_behavioral_flags[:1],
            )

            # Should return fallback explanation
            assert "explanation" in result
            assert len(result["explanation"]) > 0
            assert result["recommended_action"] in [
                "HOLD_TRANSACTION",
                "ENHANCED_DUE_DILIGENCE",
                "FILE_STR",
                "MONITORING_ONLY",
            ]
            assert result["confidence"] == "MEDIUM"

    async def test_explainer_regulatory_citations(
        self,
        mock_db_session,
        sample_transaction,
        mock_groq_response_explainer,
        sample_rule_violations,
    ):
        """Test that regulatory citations are extracted correctly"""
        with patch("app.workflows.agents.explainer.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value=mock_groq_response_explainer)
            mock_get_client.return_value = mock_client

            result = await explainer_agent(
                transaction=sample_transaction,
                session=mock_db_session,
                risk_score=85,
                alert_level="CRITICAL",
                static_violations=sample_rule_violations,
                behavioral_flags=[],
            )

            assert len(result["regulatory_basis"]) > 0
            assert any("HKMA" in citation for citation in result["regulatory_basis"])
