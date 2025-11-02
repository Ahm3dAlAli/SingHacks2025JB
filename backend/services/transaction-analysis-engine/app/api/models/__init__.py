"""
API request and response models for Transaction Analysis Engine API.
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
    """Represents a regulatory rule violation detected by Agent 1 (Rule Parser).

    Attributes:
        rule_id: Unique identifier for the rule
        rule_type: Type of rule (e.g., "cash_limit", "pep_check")
        severity: Severity level of the violation
        score: Numeric score for risk calculation (0-100)
        description: Human-readable description of the violation
        jurisdiction: Jurisdiction code (HK/SG/CH)
        parameters: Additional parameters for the rule (optional)
    """

    rule_id: str = Field(..., description="Unique rule identifier")
    rule_type: str = Field(..., description="Type of rule")
    severity: SeverityLevel = Field(..., description="Severity level")
    score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    description: str = Field(..., description="Violation description")
    jurisdiction: str = Field(..., description="Jurisdiction code (HK/SG/CH)")
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Rule parameters"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "rule_id": "HKMA-CASH-001",
                "rule_type": "cash_limit",
                "severity": "HIGH",
                "score": 70,
                "description": "Cash transaction exceeds HKD 8,000 threshold",
                "jurisdiction": "HK",
                "parameters": {"limit": 8000, "currency": "HKD"},
            }
        }
    }


class BehavioralFlag(BaseModel):
    """Represents a suspicious behavioral pattern detected by Agent 3 (Behavioral Analyzer).

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

    @field_validator("score")
    @classmethod
    def validate_score(cls, v: int) -> int:
        """Ensure score is within valid range"""
        if not 0 <= v <= 100:
            raise ValueError("Score must be between 0 and 100")
        return v


class RiskAssessmentOutput(BaseModel):
    """Final risk assessment output from Agent 4 (Risk Scorer).
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

    @field_validator("risk_score")
    @classmethod
    def validate_risk_score(cls, v: int) -> int:
        """Ensure risk score is within valid range"""
        if not 0 <= v <= 100:
            raise ValueError("Risk score must be between 0 and 100")
        return v


class TransactionInput(BaseModel):
    """Input model for transaction analysis (optional - for API validation).
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
    originator_country: Optional[str] = Field(
        None, description="Originator country code"
    )
    beneficiary_country: Optional[str] = Field(
        None, description="Beneficiary country code"
    )
    product_type: Optional[str] = Field(None, description="Product type")

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

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Ensure currency is uppercase"""
        return v.upper()

    @field_validator("booking_jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        """Validate jurisdiction code"""
        if v.upper() not in ["HK", "SG", "CH"]:
            raise ValueError("Jurisdiction must be one of: HK, SG, CH")
        return v.upper()


# Import rule models
from .rule_models import (
    RuleBase,
    RuleResponse,
    RuleDetailResponse,
    RuleListResponse,
    RuleSyncRequest,
    RuleSyncResponse
)

# Import batch models
from .batch_models import (
    BatchUploadResponse,
    BatchStatusResponse,
    BatchResultsResponse,
    BatchResultsSummary,
    BatchResultItem,
    BatchResultsPagination
)

# Import transaction models
from .transaction_models import (
    TransactionType,
    TransactionStatus,
    CustomerType,
    TransactionParty,
    TransactionInput,
    TransactionAnalysisRequest,
    TransactionAnalysisResponse,
    RiskDetailResponse,
    ExplanationResponse
)

# Re-export all models for easier imports
__all__ = [
    # Core enums
    'SeverityLevel',
    'AlertLevel',
    'TransactionType',
    'TransactionStatus',
    'CustomerType',
    
    # Core models
    'RuleViolation',
    'BehavioralFlag',
    'RiskAssessmentOutput',
    'TransactionParty',
    'TransactionInput',
    
    # Rule models
    'RuleBase',
    'RuleResponse',
    'RuleDetailResponse',
    'RuleListResponse',
    'RuleSyncRequest',
    'RuleSyncResponse',
    
    # Batch models
    'BatchUploadResponse',
    'BatchStatusResponse',
    'BatchResultsResponse',
    'BatchResultsSummary',
    'BatchResultItem',
    'BatchResultsPagination',
    
    # Transaction models
    'TransactionAnalysisRequest',
    'TransactionAnalysisResponse',
    'RiskDetailResponse',
    'ExplanationResponse',
    'TransactionInput',
    'TransactionParty'
]
