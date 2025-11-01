"""
Groq API client wrapper for Transaction Analysis Engine.
Provides async interface to Groq LLM API with retry logic, timeout handling, and rate limiting.
"""

import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

from groq import AsyncGroq
from groq.types.chat import ChatCompletion

from app.config import settings
from app.utils.logger import logger


class GroqAPIError(Exception):
    """Custom exception for Groq API errors"""
    pass


class GroqRateLimitError(GroqAPIError):
    """Exception for rate limit errors"""
    pass


class GroqTimeoutError(GroqAPIError):
    """Exception for timeout errors"""
    pass


class GroqClient:
    """
    Async Groq API client with retry logic and error handling.

    Features:
    - Exponential backoff retry (3 attempts: 1s, 2s, 4s)
    - Timeout handling (30s default)
    - Rate limit detection and queuing
    - Structured logging
    - JSON response validation

    Example:
        >>> client = GroqClient()
        >>> response = await client.complete("Parse this rule: ...")
        >>> print(response)
        {"rule_id": "TEST-001", ...}
    """

    def __init__(self):
        """Initialize Groq client with API key from settings"""
        self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL
        self.default_timeout = settings.GROQ_DEFAULT_TIMEOUT
        self.retry_delays = settings.groq_retry_delays_list

        logger.info(
            "GroqClient initialized",
            extra={
                "extra_data": {
                    "model": self.model,
                    "timeout": self.default_timeout,
                    "retry_delays": self.retry_delays,
                }
            },
        )

    async def complete(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000,
        timeout: Optional[int] = None,
        system_prompt: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Call Groq API with retry logic and error handling.

        Args:
            prompt: User prompt to send to the model
            temperature: Sampling temperature (0.0-1.0). Lower = more deterministic
            max_tokens: Maximum tokens in response
            timeout: Timeout in seconds (default: 30s)
            system_prompt: Optional system prompt to set context

        Returns:
            Parsed JSON response as dictionary

        Raises:
            GroqRateLimitError: If rate limit exceeded after retries
            GroqTimeoutError: If request times out after retries
            GroqAPIError: For other API errors after retries

        Example:
            >>> response = await client.complete(
            ...     "Parse this rule: Cash transactions over $10k require CTR",
            ...     temperature=0.1
            ... )
        """
        timeout = timeout or self.default_timeout
        start_time = datetime.utcnow()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Retry loop with exponential backoff
        for attempt in range(len(self.retry_delays) + 1):
            try:
                logger.info(
                    f"Calling Groq API (attempt {attempt + 1}/{len(self.retry_delays) + 1})",
                    extra={
                        "extra_data": {
                            "model": self.model,
                            "temperature": temperature,
                            "max_tokens": max_tokens,
                            "prompt_length": len(prompt),
                        }
                    },
                )

                # Make API call with timeout
                response: ChatCompletion = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ),
                    timeout=timeout,
                )

                # Calculate latency
                latency_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)

                # Extract content
                content = response.choices[0].message.content

                # Parse JSON response
                try:
                    parsed_response = json.loads(content)

                    logger.info(
                        "Groq API call successful",
                        extra={
                            "extra_data": {
                                "latency_ms": latency_ms,
                                "response_tokens": response.usage.completion_tokens if response.usage else 0,
                                "attempt": attempt + 1,
                            }
                        },
                    )

                    return parsed_response

                except json.JSONDecodeError as e:
                    logger.warning(
                        f"Failed to parse JSON response from Groq: {str(e)}",
                        extra={
                            "extra_data": {
                                "raw_content": content[:200],
                                "error": str(e),
                            }
                        },
                    )

                    # Try to extract JSON from markdown code blocks
                    if "```json" in content:
                        try:
                            json_str = content.split("```json")[1].split("```")[0].strip()
                            parsed_response = json.loads(json_str)
                            logger.info("Successfully extracted JSON from markdown")
                            return parsed_response
                        except (IndexError, json.JSONDecodeError):
                            pass

                    # If last attempt, raise error
                    if attempt == len(self.retry_delays):
                        raise GroqAPIError(f"Invalid JSON response: {content[:200]}")

                    # Otherwise, retry
                    logger.info(f"Retrying after malformed JSON (attempt {attempt + 1})")
                    await asyncio.sleep(self.retry_delays[attempt])
                    continue

            except asyncio.TimeoutError:
                logger.warning(
                    f"Groq API timeout on attempt {attempt + 1}",
                    extra={
                        "extra_data": {
                            "timeout": timeout,
                            "attempt": attempt + 1,
                        }
                    },
                )

                # If last attempt, raise error
                if attempt == len(self.retry_delays):
                    raise GroqTimeoutError(f"Groq API timeout after {len(self.retry_delays) + 1} attempts")

                # Wait before retry
                await asyncio.sleep(self.retry_delays[attempt])

            except Exception as e:
                error_message = str(e)

                # Check for rate limit error (429)
                if "429" in error_message or "rate_limit" in error_message.lower():
                    logger.warning(
                        f"Groq API rate limit hit on attempt {attempt + 1}",
                        extra={
                            "extra_data": {
                                "error": error_message,
                                "attempt": attempt + 1,
                            }
                        },
                    )

                    # If last attempt, raise error
                    if attempt == len(self.retry_delays):
                        raise GroqRateLimitError("Groq API rate limit exceeded")

                    # Wait longer for rate limits (2x normal backoff)
                    await asyncio.sleep(self.retry_delays[attempt] * 2)
                else:
                    # Other errors
                    logger.error(
                        f"Groq API error on attempt {attempt + 1}: {error_message}",
                        extra={
                            "extra_data": {
                                "error": error_message,
                                "attempt": attempt + 1,
                            }
                        },
                    )

                    # If last attempt, raise error
                    if attempt == len(self.retry_delays):
                        raise GroqAPIError(f"Groq API error: {error_message}")

                    # Wait before retry
                    await asyncio.sleep(self.retry_delays[attempt])

        # Should never reach here due to raises above, but just in case
        raise GroqAPIError("Unexpected error in Groq API retry loop")


# Global client instance (singleton pattern)
_groq_client: Optional[GroqClient] = None


def get_groq_client() -> GroqClient:
    """
    Get or create global GroqClient instance (singleton).

    Returns:
        Initialized GroqClient instance

    Example:
        >>> client = get_groq_client()
        >>> response = await client.complete("...")
    """
    global _groq_client
    if _groq_client is None:
        _groq_client = GroqClient()
    return _groq_client
