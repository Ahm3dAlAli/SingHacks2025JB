"""
Unit tests for Groq API client wrapper.
"""

import pytest
import asyncio
import json
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.groq_client import (
    GroqClient,
    get_groq_client,
    GroqAPIError,
    GroqRateLimitError,
    GroqTimeoutError,
)


@pytest.mark.asyncio
class TestGroqClient:
    """Test GroqClient functionality"""

    async def test_groq_client_success(self, mock_groq_response_rule_parser):
        """Test successful API call"""
        client = GroqClient()

        # Mock the async chat completions create method
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(mock_groq_response_rule_parser)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_usage = MagicMock()
        mock_usage.completion_tokens = 100
        mock_response.usage = mock_usage

        with patch.object(
            client.client.chat.completions, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await client.complete("Parse this rule: Cash over $10k")

            assert result["rule_id"] == "TEST-RULE-001"
            assert "conditions" in result
            assert result["severity_score"] == 85

    async def test_groq_client_timeout(self):
        """Test timeout handling"""
        client = GroqClient()

        # Mock timeout
        with patch.object(
            client.client.chat.completions, "create", new=AsyncMock(side_effect=asyncio.TimeoutError())
        ):
            with pytest.raises(GroqTimeoutError):
                await client.complete("Test prompt", timeout=1)

    async def test_groq_client_rate_limit(self):
        """Test rate limit handling"""
        client = GroqClient()

        # Mock rate limit error
        rate_limit_error = Exception("429 rate_limit_exceeded")
        with patch.object(
            client.client.chat.completions, "create", new=AsyncMock(side_effect=rate_limit_error)
        ):
            with pytest.raises(GroqRateLimitError):
                await client.complete("Test prompt")

    async def test_groq_client_retry_logic(self, mock_groq_response_rule_parser):
        """Test retry logic with exponential backoff"""
        client = GroqClient()

        # Mock response that succeeds on second attempt
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps(mock_groq_response_rule_parser)
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_usage = MagicMock()
        mock_usage.completion_tokens = 100
        mock_response.usage = mock_usage

        mock_create = AsyncMock(side_effect=[Exception("Temporary error"), mock_response])

        with patch.object(client.client.chat.completions, "create", new=mock_create):
            result = await client.complete("Test prompt")

            assert result["rule_id"] == "TEST-RULE-001"
            assert mock_create.call_count == 2  # Failed once, then succeeded

    async def test_groq_client_malformed_json(self):
        """Test handling of malformed JSON response"""
        client = GroqClient()

        # Mock response with invalid JSON
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "This is not valid JSON"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_response.usage = None

        with patch.object(
            client.client.chat.completions, "create", new=AsyncMock(return_value=mock_response)
        ):
            with pytest.raises(GroqAPIError, match="Invalid JSON response"):
                await client.complete("Test prompt")

    async def test_groq_client_json_markdown_extraction(self, mock_groq_response_rule_parser):
        """Test extraction of JSON from markdown code blocks"""
        client = GroqClient()

        # Mock response with JSON in markdown
        markdown_content = f"```json\n{json.dumps(mock_groq_response_rule_parser)}\n```"
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = markdown_content
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        mock_usage = MagicMock()
        mock_usage.completion_tokens = 100
        mock_response.usage = mock_usage

        with patch.object(
            client.client.chat.completions, "create", new=AsyncMock(return_value=mock_response)
        ):
            result = await client.complete("Test prompt")

            assert result["rule_id"] == "TEST-RULE-001"

    def test_get_groq_client_singleton(self):
        """Test that get_groq_client returns singleton"""
        client1 = get_groq_client()
        client2 = get_groq_client()

        assert client1 is client2
