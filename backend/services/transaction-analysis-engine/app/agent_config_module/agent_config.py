"""
Configuration for Transaction Analysis Engine agents.
Centralizes all configurable parameters for SOLID compliance (Open/Closed Principle).

This allows extending behavior through configuration without modifying agent code.
"""

from pydantic import BaseModel, Field


class SeverityConfig(BaseModel):
    """Severity level to score mapping configuration"""

    critical: int = Field(100, ge=0, le=100, description="CRITICAL severity score")
    high: int = Field(65, ge=0, le=100, description="HIGH severity score")
    medium: int = Field(40, ge=0, le=100, description="MEDIUM severity score")
    low: int = Field(20, ge=0, le=100, description="LOW severity score")

    def get_score(self, severity: str) -> int:
        """Get score for severity level"""
        severity_map = {
            "CRITICAL": self.critical,
            "HIGH": self.high,
            "MEDIUM": self.medium,
            "LOW": self.low,
        }
        return severity_map.get(severity.upper(), self.medium)


class JurisdictionConfig(BaseModel):
    """Jurisdiction-specific weight multipliers configuration"""

    hk_weight: float = Field(1.2, gt=0, description="Hong Kong (HKMA) weight multiplier")
    sg_weight: float = Field(1.0, gt=0, description="Singapore (MAS) weight multiplier")
    ch_weight: float = Field(1.1, gt=0, description="Switzerland (FINMA) weight multiplier")
    default_weight: float = Field(1.0, gt=0, description="Default weight for unknown jurisdictions")

    def get_weight(self, jurisdiction: str) -> float:
        """Get weight multiplier for jurisdiction"""
        weight_map = {"HK": self.hk_weight, "SG": self.sg_weight, "CH": self.ch_weight}
        return weight_map.get(jurisdiction.upper(), self.default_weight)


class AlertThresholdsConfig(BaseModel):
    """Alert level classification thresholds configuration"""

    critical_threshold: int = Field(
        76, ge=0, le=100, description="Minimum score for CRITICAL alert"
    )
    high_threshold: int = Field(51, ge=0, le=100, description="Minimum score for HIGH alert")
    medium_threshold: int = Field(26, ge=0, le=100, description="Minimum score for MEDIUM alert")
    low_threshold: int = Field(0, ge=0, le=100, description="Minimum score for LOW alert")

    def classify_alert_level(self, risk_score: int) -> str:
        """Classify alert level based on risk score"""
        if risk_score >= self.critical_threshold:
            return "CRITICAL"
        elif risk_score >= self.high_threshold:
            return "HIGH"
        elif risk_score >= self.medium_threshold:
            return "MEDIUM"
        else:
            return "LOW"


class GeographicRiskConfig(BaseModel):
    """Geographic risk configuration for high-risk countries"""

    high_risk_countries: list[str] = Field(
        default=[
            "IR",  # Iran
            "KP",  # North Korea
            "SY",  # Syria
            "CU",  # Cuba
            "MM",  # Myanmar
            "BY",  # Belarus
            "VE",  # Venezuela
        ],
        description="List of high-risk country codes (ISO 3166-1 alpha-2)",
    )

    def is_high_risk(self, country_code: str) -> bool:
        """Check if country is high-risk"""
        return country_code.upper() in [c.upper() for c in self.high_risk_countries]


class BehavioralThresholdsConfig(BaseModel):
    """Thresholds for behavioral pattern detection"""

    velocity_multiplier_threshold: float = Field(
        3.0, gt=0, description="Velocity anomaly threshold (Nx normal)"
    )
    smurfing_threshold_percent: float = Field(
        0.9, gt=0, le=1, description="Smurfing detection threshold (% of limit)"
    )
    smurfing_min_transactions: int = Field(
        3, ge=2, description="Minimum transactions for smurfing pattern"
    )
    clustering_variation_threshold: float = Field(
        15.0, gt=0, description="Max coefficient of variation for clustering (%)"
    )
    clustering_min_transactions: int = Field(
        5, ge=3, description="Minimum transactions for clustering"
    )
    min_history_for_analysis: int = Field(
        5, ge=1, description="Minimum historical transactions for analysis"
    )


class AgentExecutionConfig(BaseModel):
    """Agent execution configuration"""

    max_historical_days: int = Field(
        30, ge=1, le=365, description="Maximum days to look back for historical data"
    )
    max_historical_transactions: int = Field(
        1000, ge=10, le=10000, description="Maximum historical transactions to analyze"
    )
    enable_logging: bool = Field(True, description="Enable agent execution logging to database")
    fail_gracefully: bool = Field(
        True, description="Return empty results on error instead of raising"
    )


class AgentConfig(BaseModel):
    """
    Centralized configuration for all TAE agents.
    Implements Open/Closed Principle - extend through configuration, not code modification.
    """

    severity: SeverityConfig = Field(default_factory=SeverityConfig)
    jurisdiction: JurisdictionConfig = Field(default_factory=JurisdictionConfig)
    alert_thresholds: AlertThresholdsConfig = Field(default_factory=AlertThresholdsConfig)
    geographic_risk: GeographicRiskConfig = Field(default_factory=GeographicRiskConfig)
    behavioral_thresholds: BehavioralThresholdsConfig = Field(
        default_factory=BehavioralThresholdsConfig
    )
    execution: AgentExecutionConfig = Field(default_factory=AgentExecutionConfig)

    model_config = {
        "json_schema_extra": {
            "example": {
                "severity": {"critical": 100, "high": 65, "medium": 40, "low": 20},
                "jurisdiction": {"hk_weight": 1.2, "sg_weight": 1.0, "ch_weight": 1.1},
                "alert_thresholds": {
                    "critical_threshold": 76,
                    "high_threshold": 51,
                    "medium_threshold": 26,
                },
            }
        }
    }


# Global singleton configuration instance
_agent_config: AgentConfig = AgentConfig()


def get_agent_config() -> AgentConfig:
    """
    Get the global agent configuration instance.

    Returns:
        AgentConfig singleton

    Example:
        >>> config = get_agent_config()
        >>> config.severity.get_score("HIGH")
        65
    """
    return _agent_config


def set_agent_config(config: AgentConfig) -> None:
    """
    Set the global agent configuration (for testing or custom configuration).

    Args:
        config: New AgentConfig instance

    Example:
        >>> custom_config = AgentConfig(
        ...     severity=SeverityConfig(critical=90)
        ... )
        >>> set_agent_config(custom_config)
    """
    global _agent_config
    _agent_config = config


def reset_agent_config() -> None:
    """Reset agent configuration to defaults"""
    global _agent_config
    _agent_config = AgentConfig()
