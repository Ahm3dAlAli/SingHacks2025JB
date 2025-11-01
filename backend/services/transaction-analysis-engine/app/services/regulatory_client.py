"""
Regulatory Service HTTP client for fetching rules from Regulatory Ingestion Engine.

Provides async interface to Regulatory Service API with retry logic, timeout handling,
schema transformation, and in-memory caching.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date

import httpx

from app.config import settings
from app.database.models import RegulatoryRule
from app.utils.logger import logger


class RegulatoryServiceError(Exception):
    """Base exception for regulatory service errors"""
    pass


class RegulatoryClient:
    """
    Async HTTP client for Regulatory Ingestion Engine API.

    Features:
    - Fetches rules from GET /api/v1/regulatory/rules
    - Transforms Regulatory Service schema to TAE schema
    - Retry with exponential backoff (3 attempts)
    - In-memory caching with 1-hour TTL
    - Timeout handling (10s default)
    - Structured logging for all operations

    Example:
        >>> client = RegulatoryClient()
        >>> rules = await client.fetch_rules(jurisdiction="HK", status="ACTIVE")
        >>> tae_rules = [client.transform_rule(r) for r in rules]
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = 10,
        max_retries: int = 3
    ):
        """
        Initialize Regulatory Service client.

        Args:
            base_url: Base URL for Regulatory Service (default: from settings)
            timeout: Request timeout in seconds (default: 10)
            max_retries: Maximum retry attempts (default: 3)
        """
        self.base_url = base_url or settings.REGULATORY_SERVICE_URL
        self.timeout = timeout
        self.max_retries = max_retries
        self._cache: Dict[str, tuple[List[Dict[str, Any]], datetime]] = {}
        self._cache_ttl = timedelta(hours=1)

        logger.info(
            "RegulatoryClient initialized",
            extra={
                "extra_data": {
                    "base_url": self.base_url,
                    "timeout": self.timeout,
                    "max_retries": self.max_retries,
                    "cache_ttl_hours": 1
                }
            }
        )

    async def fetch_rules(
        self,
        jurisdiction: Optional[str] = None,
        status: str = "ACTIVE",
        use_cache: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Fetch rules from Regulatory Service API with retry logic and caching.

        Args:
            jurisdiction: Filter by jurisdiction (HK, SG, CH, etc.) - optional
            status: Filter by status (default: ACTIVE)
            use_cache: Use cached response if available (default: True)

        Returns:
            List of rules in Regulatory Service format

        Raises:
            RegulatoryServiceError: If all retries fail or HTTP error occurs

        Example:
            >>> rules = await client.fetch_rules(jurisdiction="HK")
            >>> print(f"Fetched {len(rules)} rules")
        """
        cache_key = f"rules_{jurisdiction}_{status}"

        # Check cache
        if use_cache and cache_key in self._cache:
            cached_data, cached_time = self._cache[cache_key]
            if datetime.utcnow() - cached_time < self._cache_ttl:
                logger.info(
                    f"Using cached rules for {cache_key}",
                    extra={"extra_data": {"cache_key": cache_key, "cached_count": len(cached_data)}}
                )
                return cached_data

        # Build request params
        params: Dict[str, Any] = {"status": status}
        if jurisdiction:
            params["jurisdiction"] = jurisdiction

        # Retry loop with exponential backoff
        for attempt in range(self.max_retries):
            try:
                logger.info(
                    f"Calling Regulatory Service API (attempt {attempt + 1}/{self.max_retries})",
                    extra={
                        "extra_data": {
                            "url": f"{self.base_url}/api/v1/regulatory/rules",
                            "params": params,
                            "attempt": attempt + 1
                        }
                    }
                )

                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(
                        f"{self.base_url}/api/v1/regulatory/rules",
                        params=params
                    )
                    response.raise_for_status()

                    data = response.json()
                    rules = data.get("rules", [])

                    logger.info(
                        "Regulatory Service API call successful",
                        extra={
                            "extra_data": {
                                "jurisdiction": jurisdiction,
                                "status": status,
                                "count": len(rules),
                                "total": data.get("total", len(rules)),
                                "attempt": attempt + 1
                            }
                        }
                    )

                    # Cache response
                    self._cache[cache_key] = (rules, datetime.utcnow())

                    return rules

            except httpx.TimeoutException as e:
                logger.warning(
                    f"Timeout fetching rules (attempt {attempt + 1}/{self.max_retries})",
                    extra={"extra_data": {"error": str(e), "timeout": self.timeout}}
                )
                if attempt < self.max_retries - 1:
                    # Exponential backoff: 2^0=1s, 2^1=2s, 2^2=4s
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise RegulatoryServiceError(
                        f"Timeout after {self.max_retries} attempts"
                    ) from e

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"HTTP error fetching rules: {e.response.status_code}",
                    extra={"extra_data": {"status_code": e.response.status_code, "url": str(e.request.url)}}
                )
                raise RegulatoryServiceError(
                    f"HTTP {e.response.status_code}: {e.response.text}"
                ) from e

            except Exception as e:
                logger.error(
                    f"Unexpected error fetching rules (attempt {attempt + 1}/{self.max_retries}): {e}",
                    extra={"extra_data": {"error": str(e), "error_type": type(e).__name__}},
                    exc_info=True
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    raise RegulatoryServiceError(f"Unexpected error: {e}") from e

        # Should never reach here due to raises above, but just in case
        raise RegulatoryServiceError("Max retries exceeded")

    def transform_rule(self, regulatory_rule: Dict[str, Any]) -> RegulatoryRule:
        """
        Transform Regulatory Service rule to TAE RegulatoryRule model.

        Schema Mapping:
        - Regulatory.rule_number → TAE.rule_id
        - Regulatory.jurisdiction → TAE.jurisdiction
        - Regulatory.regulator → TAE.regulator
        - Regulatory.rule_type → TAE.rule_type (mapped via dict)
        - Regulatory.full_text → TAE.rule_text + extract parameters
        - Regulatory.summary + category → TAE.severity (keyword matching)

        Args:
            regulatory_rule: Rule from Regulatory Service API

        Returns:
            RegulatoryRule model instance for TAE database

        Example:
            >>> api_rule = {"rule_number": "HKMA-001", "jurisdiction": "HK", ...}
            >>> tae_rule = client.transform_rule(api_rule)
            >>> print(tae_rule.rule_id, tae_rule.severity)
        """
        # Generate TAE rule_id from regulatory rule_number
        rule_id = regulatory_rule.get("rule_number") or f"AUTO-{regulatory_rule['id'][:8]}"

        # Map rule_type from Regulatory Service to TAE
        rule_type_mapping = {
            "OBLIGATION": "compliance_check",
            "PROHIBITION": "prohibition_check",
            "REQUIREMENT": "requirement_check",
            "THRESHOLD": "threshold_check",
            "EXEMPTION": "exemption_check",
            "GUIDANCE": "guidance_check",
            "DEFINITION": "definition_check",
            "OTHER": "compliance_check"
        }

        regulatory_type = regulatory_rule.get("rule_type", "REQUIREMENT")
        tae_rule_type = rule_type_mapping.get(regulatory_type, "compliance_check")

        # Extract rule parameters from full_text
        full_text = regulatory_rule.get("full_text", "")
        parameters = self._extract_parameters(full_text)

        # Determine severity based on keywords
        severity = self._determine_severity(
            regulatory_rule.get("summary", ""),
            regulatory_rule.get("category", "")
        )

        # Map priority based on severity
        priority_map = {
            "CRITICAL": 100,
            "HIGH": 75,
            "MEDIUM": 50,
            "LOW": 25
        }
        priority = priority_map.get(severity, 50)

        # Parse effective_date and expiry_date
        effective_date_str = regulatory_rule.get("effective_date")
        expiry_date_str = regulatory_rule.get("expiry_date")

        try:
            effective_date = date.fromisoformat(effective_date_str) if effective_date_str else date.today()
        except (ValueError, TypeError):
            effective_date = date.today()

        try:
            expiry_date = date.fromisoformat(expiry_date_str) if expiry_date_str else None
        except (ValueError, TypeError):
            expiry_date = None

        # Build tags from category
        tags = []
        if regulatory_rule.get("category"):
            tags.append(regulatory_rule["category"])

        # Create RegulatoryRule instance
        return RegulatoryRule(
            rule_id=rule_id,
            jurisdiction=regulatory_rule.get("jurisdiction", "UNKNOWN"),
            regulator=regulatory_rule.get("regulator", "UNKNOWN"),
            rule_type=tae_rule_type,
            rule_text=full_text,
            rule_parameters=parameters,
            severity=severity,
            priority=priority,
            effective_date=effective_date,
            expiry_date=expiry_date,
            is_active=regulatory_rule.get("status") == "ACTIVE",
            version=1,
            source_url=None,  # Could add document URL if available
            tags=tags
        )

    def _extract_parameters(self, rule_text: str) -> Dict[str, Any]:
        """
        Extract structured parameters from rule text using regex patterns.

        Patterns:
        - Currency amounts: "HKD 8,000" → {"threshold": 8000.0, "currency": "HKD"}
        - Day counts: "30 days" → {"days": 30}

        Args:
            rule_text: Rule text to extract parameters from

        Returns:
            Dictionary of extracted parameters (empty dict if no matches)

        Example:
            >>> params = client._extract_parameters("HKD 8,000 within 30 days")
            >>> print(params)
            {"currency": "HKD", "threshold": 8000.0, "days": 30}
        """
        parameters: Dict[str, Any] = {}

        # Extract currency amounts (e.g., "HKD 8,000", "SGD 20,000.00")
        currency_pattern = r'([A-Z]{3})\s*([\d,]+(?:\.\d{2})?)'
        matches = re.findall(currency_pattern, rule_text)
        if matches:
            currency, amount = matches[0]
            parameters["currency"] = currency
            # Remove commas and convert to float
            parameters["threshold"] = float(amount.replace(',', ''))

        # Extract day counts (e.g., "30 days", "7 day")
        day_pattern = r'(\d+)\s*days?'
        day_match = re.search(day_pattern, rule_text, re.IGNORECASE)
        if day_match:
            parameters["days"] = int(day_match.group(1))

        # Log if parameters extracted
        if parameters:
            logger.debug(
                "Extracted parameters from rule text",
                extra={"extra_data": {"parameters": parameters, "text_length": len(rule_text)}}
            )

        return parameters

    def _determine_severity(self, summary: str, category: str) -> str:
        """
        Determine severity level based on keywords in summary and category.

        Severity Keywords:
        - CRITICAL: "must", "shall", "prohibited", "mandatory"
        - HIGH: "limit", "threshold", "exceed", "violation"
        - MEDIUM: "should", "recommended", "advised"
        - LOW: default (no matching keywords)

        Args:
            summary: Rule summary text
            category: Rule category

        Returns:
            Severity level: "CRITICAL", "HIGH", "MEDIUM", or "LOW"

        Example:
            >>> severity = client._determine_severity("Must comply with AML", "Compliance")
            >>> print(severity)
            "CRITICAL"
        """
        text = f"{summary} {category}".lower()

        # Critical severity keywords
        if any(word in text for word in ["must", "shall", "prohibited", "mandatory", "required"]):
            return "CRITICAL"

        # High severity keywords
        if any(word in text for word in ["limit", "threshold", "exceed", "violation", "breach"]):
            return "HIGH"

        # Medium severity keywords
        if any(word in text for word in ["should", "recommended", "advised", "guideline"]):
            return "MEDIUM"

        # Default to LOW
        return "LOW"


# Global client instance (singleton pattern)
_regulatory_client: Optional[RegulatoryClient] = None


def get_regulatory_client() -> RegulatoryClient:
    """
    Get or create global RegulatoryClient instance (singleton).

    Returns:
        Initialized RegulatoryClient instance

    Example:
        >>> client = get_regulatory_client()
        >>> rules = await client.fetch_rules()
    """
    global _regulatory_client
    if _regulatory_client is None:
        _regulatory_client = RegulatoryClient()
    return _regulatory_client


# Convenience export
regulatory_client = get_regulatory_client()
