"""
Pydantic models for Transaction Analysis Engine API.
Defines data transfer objects for agent outputs and risk assessments.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class SeverityLevel(str, Enum):
    """Severity levels for violations and flags"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AlertLevel(str, Enum):
    """Alert levels for risk assessments"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RuleViolation(BaseModel):
    """
    Represents a regulatory rule violation detected by Agent 2 (Static Rules).

    Attributes:
        rule_id: Unique identifier for the regulatory rule (e.g., "HKMA-CASH-001")
        rule_type: Type of rule (e.g., "cash_limit", "kyc_expiry", "pep_screening")
        severity: Severity level of the violation
        score: Numeric score for risk calculation (0-100)
        description: Human-readable explanation of the violation
        jurisdiction: Jurisdiction where rule applies (HK, SG, CH)
        parameters: Rule parameters that were violated (optional)
    """

    rule_id: str = Field(..., description="Regulatory rule identifier")
    rule_type: str = Field(..., description="Type of regulatory rule")
    severity: SeverityLevel = Field(..., description="Severity level")
    score: int = Field(..., ge=0, le=100, description="Risk score contribution (0-100)")
    description: str = Field(..., description="Violation description")
    jurisdiction: str = Field(..., description="Jurisdiction code (HK/SG/CH)")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Rule parameters that were violated"
    )

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        """Ensure score is within valid range"""
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "rule_id": "HKMA-CASH-001",
                "rule_type": "cash_limit",
                "severity": "HIGH",
                "score": 65,
                "description": "Cash transaction HKD 150,000 exceeds HKD 8,000 threshold",
                "jurisdiction": "HK",
                "parameters": {"threshold": 8000, "currency": "HKD"},
            }
        }
    }


class BehavioralFlag(BaseModel):
    """
    Represents a suspicious behavioral pattern detected by Agent 3 (Behavioral Analyzer).

    Attributes:
        flag_type: Type of behavioral pattern (e.g., "VELOCITY_ANOMALY", "SMURFING_PATTERN")
        severity: Severity level of the pattern
        score: Numeric score for risk calculation (0-100)
        description: Human-readable explanation of the pattern
        detection_details: Additional details about the detection (optional)
        historical_context: Context from historical transactions (optional)
    """

    flag_type: str = Field(..., description="Type of behavioral pattern detected")
    severity: SeverityLevel = Field(..., description="Severity level")
    score: int = Field(..., ge=0, le=100, description="Risk score contribution (0-100)")
    description: str = Field(..., description="Pattern description")
    detection_details: Optional[Dict[str, Any]] = Field(
        default=None, description="Details about pattern detection"
    )
    historical_context: Optional[Dict[str, Any]] = Field(
        default=None, description="Historical transaction context"
    )

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        """Ensure score is within valid range"""
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "flag_type": "VELOCITY_ANOMALY",
                "severity": "MEDIUM",
                "score": 45,
                "description": "Transaction frequency 4x normal (12 transactions in 24h)",
                "detection_details": {
                    "transactions_24h": 12,
                    "normal_rate": 3,
                    "multiplier": 4.0,
                },
                "historical_context": {
                    "avg_daily_transactions": 3,
                    "days_analyzed": 30,
                },
            }
        }
    }


class RiskAssessmentOutput(BaseModel):
    """
    Final risk assessment output from Agent 4 (Risk Scorer).
    Aggregates all violations and flags into a final risk score and alert level.

    Attributes:
        transaction_id: UUID of the analyzed transaction
        risk_score: Final risk score (0-100)
        alert_level: Alert classification (CRITICAL/HIGH/MEDIUM/LOW)
        explanation: Human-readable summary of the risk assessment
        static_violations: List of regulatory violations detected
        behavioral_flags: List of behavioral patterns detected
        static_rules_score: Aggregated score from static rules
        behavioral_score: Aggregated score from behavioral analysis
        jurisdiction_weight: Applied jurisdiction weight multiplier
        analyzed_at: Timestamp when analysis was performed
    """

    transaction_id: UUID = Field(..., description="Transaction UUID")
    risk_score: int = Field(..., ge=0, le=100, description="Final risk score (0-100)")
    alert_level: AlertLevel = Field(..., description="Alert classification")
    explanation: str = Field(..., description="Risk assessment summary")

    static_violations: List[RuleViolation] = Field(
        default_factory=list, description="Regulatory violations detected"
    )
    behavioral_flags: List[BehavioralFlag] = Field(
        default_factory=list, description="Behavioral patterns detected"
    )

    static_rules_score: int = Field(..., ge=0, description="Total static rules score")
    behavioral_score: int = Field(..., ge=0, description="Total behavioral score")
    jurisdiction_weight: float = Field(..., gt=0, description="Jurisdiction multiplier")

    analyzed_at: datetime = Field(
        default_factory=datetime.utcnow, description="Analysis timestamp"
    )

    @field_validator("risk_score")
    @classmethod
    def validate_risk_score(cls, v: int) -> int:
        """Ensure risk score is within valid range"""
        if not 0 <= v <= 100:
            raise ValueError("Risk score must be between 0 and 100")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "risk_score": 100,
                "alert_level": "CRITICAL",
                "explanation": "Risk score 100 (CRITICAL): Cash limit violation (HKD 150K), PEP status requires EDD, expired KYC, velocity anomaly (12 txns/24h), smurfing pattern detected",
                "static_violations": [],
                "behavioral_flags": [],
                "static_rules_score": 135,
                "behavioral_score": 70,
                "jurisdiction_weight": 1.2,
                "analyzed_at": "2025-10-31T10:30:00Z",
            }
        }
    }


class TransactionInput(BaseModel):
    """
    Input model for transaction analysis (optional - for API validation).
    Can be used when accepting transactions via API endpoints.
    """

    customer_id: str = Field(..., description="Customer identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(
        ..., min_length=3, max_length=3, description="Currency code (ISO 4217)"
    )
    booking_jurisdiction: str = Field(
        ..., description="Booking jurisdiction (HK/SG/CH)"
    )

    # Optional fields for enhanced validation
    originator_country: Optional[str] = Field(
        None, description="Originator country code"
    )
    beneficiary_country: Optional[str] = Field(
        None, description="Beneficiary country code"
    )
    product_type: Optional[str] = Field(None, description="Product type")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is uppercase"""
        return v.upper()

    @field_validator("booking_jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        """Validate jurisdiction code"""
        valid_jurisdictions = ["HK", "SG", "CH"]
        if v.upper() not in valid_jurisdictions:
            raise ValueError(f"Jurisdiction must be one of {valid_jurisdictions}")
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "CUST-001",
                "amount": 150000.00,
                "currency": "HKD",
                "booking_jurisdiction": "HK",
                "originator_country": "HK",
                "beneficiary_country": "SG",
                "product_type": "FX",
            }
        }
    }
