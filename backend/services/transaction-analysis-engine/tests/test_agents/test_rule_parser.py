"""
Unit tests for Agent 1: Rule Parser
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import date

from app.workflows.agents.rule_parser import rule_parser_agent, parse_regulatory_rule
from app.database.models import RegulatoryRule


@pytest.mark.asyncio
class TestRuleParser:
    """Test rule parser agent functionality"""

    async def test_parse_regulatory_rule_success(
        self, mock_db_session, mock_groq_response_rule_parser, sample_regulatory_rules
    ):
        """Test successful rule parsing"""
        rule = sample_regulatory_rules[0]  # HKMA-CASH-001

        with patch("app.workflows.agents.rule_parser.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value=mock_groq_response_rule_parser)
            mock_get_client.return_value = mock_client

            result = await parse_regulatory_rule(rule, mock_db_session)

            assert result["rule_id"] == "TEST-RULE-001"
            assert "conditions" in result
            assert isinstance(result["conditions"], list)
            assert "thresholds" in result
            assert result["severity_score"] == 85

    async def test_parse_regulatory_rule_missing_fields(
        self, mock_db_session, sample_regulatory_rules
    ):
        """Test handling of missing fields in response"""
        rule = sample_regulatory_rules[0]

        incomplete_response = {
            "rule_id": "TEST-001",
            # Missing other required fields
        }

        with patch("app.workflows.agents.rule_parser.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(return_value=incomplete_response)
            mock_get_client.return_value = mock_client

            result = await parse_regulatory_rule(rule, mock_db_session)

            # Should provide defaults for missing fields
            assert result["rule_id"] == "TEST-001"
            assert "conditions" in result
            assert "thresholds" in result
            assert "severity_score" in result

    async def test_parse_regulatory_rule_groq_api_error(
        self, mock_db_session, sample_regulatory_rules
    ):
        """Test fallback when Groq API fails"""
        from app.services.groq_client import GroqAPIError

        rule = sample_regulatory_rules[0]

        with patch("app.workflows.agents.rule_parser.get_groq_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.complete = AsyncMock(side_effect=GroqAPIError("API Error"))
            mock_get_client.return_value = mock_client

            result = await parse_regulatory_rule(rule, mock_db_session)

            # Should return fallback
            assert result["rule_id"] == rule.rule_id
            assert len(result["conditions"]) > 0
            assert result["severity_score"] == 50  # Default medium

    async def test_rule_parser_agent_success(
        self, mock_db_session, sample_transaction, mock_groq_response_rule_parser
    ):
        """Test complete rule parser agent execution"""
        # Mock get_regulatory_rules to return sample rules
        sample_rules = [
            RegulatoryRule(
                id=1,
                rule_id="HKMA-CASH-001",
                jurisdiction="HK",
                regulator="HKMA",
                rule_type="cash_limit",
                rule_text="Cash transactions exceeding HKD 8,000 require CTR",
                severity="HIGH",
                effective_date=date.today(),
                is_active=True,
                version=1,
            )
        ]

        with patch("app.workflows.agents.rule_parser.get_regulatory_rules") as mock_get_rules:
            mock_get_rules.return_value = sample_rules

            with patch("app.workflows.agents.rule_parser.get_groq_client") as mock_get_client:
                mock_client = AsyncMock()
                mock_client.complete = AsyncMock(return_value=mock_groq_response_rule_parser)
                mock_get_client.return_value = mock_client

                result = await rule_parser_agent(sample_transaction, mock_db_session)

                assert "parsed_rules" in result
                assert len(result["parsed_rules"]) == 1
                assert result["parsed_rules"][0]["rule_id"] == "TEST-RULE-001"

    async def test_rule_parser_agent_no_rules(self, mock_db_session, sample_transaction):
        """Test agent with no applicable rules"""
        with patch("app.workflows.agents.rule_parser.get_regulatory_rules") as mock_get_rules:
            mock_get_rules.return_value = []

            result = await rule_parser_agent(sample_transaction, mock_db_session)

            assert "parsed_rules" in result
            assert len(result["parsed_rules"]) == 0

    async def test_rule_parser_agent_error_handling(self, mock_db_session, sample_transaction):
        """Test agent error handling"""
        with patch("app.workflows.agents.rule_parser.get_regulatory_rules") as mock_get_rules:
            mock_get_rules.side_effect = Exception("Database error")

            result = await rule_parser_agent(sample_transaction, mock_db_session)

            # Should fail gracefully
            assert "parsed_rules" in result
            assert result["parsed_rules"] == []
