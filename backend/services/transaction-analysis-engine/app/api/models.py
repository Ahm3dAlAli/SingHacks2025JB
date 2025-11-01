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


# ============================================================================
# BATCH PROCESSING MODELS
# ============================================================================


class BatchUploadResponse(BaseModel):
    """Response model for batch CSV upload"""

    batch_id: UUID = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Batch status (PENDING/PROCESSING/COMPLETED/FAILED)")
    total_transactions: int = Field(..., description="Total transactions in batch")
    status_url: str = Field(..., description="URL to check batch status")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "PENDING",
                "total_transactions": 1000,
                "status_url": "/api/v1/tae/batch/550e8400-e29b-41d4-a716-446655440000/status",
                "estimated_completion": "2025-11-01T15:45:00Z",
            }
        }
    }


class BatchStatusResponse(BaseModel):
    """Response model for batch status check"""

    batch_id: UUID = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Current batch status")
    total_transactions: int = Field(..., description="Total transactions")
    processed_count: int = Field(..., description="Number of transactions processed")
    failed_count: int = Field(..., description="Number of transactions failed")
    progress_percent: float = Field(..., description="Progress percentage (0-100)")
    started_at: datetime = Field(..., description="Batch processing start time")
    estimated_completion: Optional[datetime] = Field(
        None, description="Estimated completion time"
    )
    completed_at: Optional[datetime] = Field(None, description="Actual completion time")
    error_message: Optional[str] = Field(None, description="Error message if failed")

    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "PROCESSING",
                "total_transactions": 1000,
                "processed_count": 450,
                "failed_count": 2,
                "progress_percent": 45.0,
                "started_at": "2025-11-01T15:30:00Z",
                "estimated_completion": "2025-11-01T15:45:00Z",
                "completed_at": None,
                "error_message": None,
            }
        }
    }


class BatchResultsSummary(BaseModel):
    """Summary statistics for batch results"""

    total: int = Field(..., description="Total transactions")
    critical: int = Field(..., description="CRITICAL alert level count")
    high: int = Field(..., description="HIGH alert level count")
    medium: int = Field(..., description="MEDIUM alert level count")
    low: int = Field(..., description="LOW alert level count")


class BatchResultItem(BaseModel):
    """Individual result item in batch results"""

    transaction_id: UUID = Field(..., description="Transaction UUID")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    alert_level: AlertLevel = Field(..., description="Alert level")
    explanation_summary: str = Field(..., description="Brief explanation")
    recommended_action: str = Field(..., description="Recommended action")


class BatchResultsPagination(BaseModel):
    """Pagination metadata for batch results"""

    total: int = Field(..., description="Total results")
    limit: int = Field(..., description="Results per page")
    offset: int = Field(..., description="Current offset")
    next: Optional[str] = Field(None, description="Next page URL")


class BatchResultsResponse(BaseModel):
    """Response model for batch results"""

    batch_id: UUID = Field(..., description="Unique batch identifier")
    status: str = Field(..., description="Batch status")
    summary: BatchResultsSummary = Field(..., description="Summary statistics")
    processing_duration_seconds: Optional[int] = Field(
        None, description="Total processing time in seconds"
    )
    results: List[BatchResultItem] = Field(..., description="Result items")
    pagination: BatchResultsPagination = Field(..., description="Pagination metadata")

    model_config = {
        "json_schema_extra": {
            "example": {
                "batch_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "COMPLETED",
                "summary": {
                    "total": 1000,
                    "critical": 15,
                    "high": 87,
                    "medium": 234,
                    "low": 664,
                },
                "processing_duration_seconds": 238,
                "results": [
                    {
                        "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                        "risk_score": 85,
                        "alert_level": "CRITICAL",
                        "explanation_summary": "PEP status + cash limit violation",
                        "recommended_action": "FILE_STR",
                    }
                ],
                "pagination": {
                    "total": 1000,
                    "limit": 100,
                    "offset": 0,
                    "next": "/api/v1/tae/batch/550e8400.../results?offset=100",
                },
            }
        }
    }


# ============================================================================
# SINGLE TRANSACTION ANALYSIS MODELS
# ============================================================================


class TransactionAnalysisRequest(BaseModel):
    """Request model for single transaction analysis"""

    transaction_id: Optional[UUID] = Field(None, description="Optional transaction ID")
    customer_id: str = Field(..., description="Customer identifier")
    amount: float = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(..., min_length=3, max_length=3, description="Currency code")
    booking_jurisdiction: str = Field(..., description="Booking jurisdiction (HK/SG/CH)")
    booking_datetime: datetime = Field(..., description="Transaction booking time")

    # Optional fields
    customer_is_pep: Optional[bool] = Field(False, description="Is customer a PEP")
    customer_risk_rating: Optional[str] = Field(None, description="Customer risk rating")
    originator_country: Optional[str] = Field(None, description="Originator country")
    beneficiary_country: Optional[str] = Field(None, description="Beneficiary country")
    product_type: Optional[str] = Field(None, description="Product type")

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("booking_jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: str) -> str:
        valid = ["HK", "SG", "CH"]
        if v.upper() not in valid:
            raise ValueError(f"Jurisdiction must be one of {valid}")
        return v.upper()

    model_config = {
        "json_schema_extra": {
            "example": {
                "customer_id": "CUST12345",
                "amount": 150000.00,
                "currency": "HKD",
                "booking_jurisdiction": "HK",
                "booking_datetime": "2025-11-01T10:30:00Z",
                "customer_is_pep": True,
                "customer_risk_rating": "HIGH",
                "originator_country": "HK",
                "beneficiary_country": "SG",
                "product_type": "FX",
            }
        }
    }


class TransactionAnalysisResponse(BaseModel):
    """Response model for single transaction analysis"""

    transaction_id: UUID = Field(..., description="Transaction UUID")
    risk_score: int = Field(..., ge=0, le=100, description="Risk score (0-100)")
    alert_level: AlertLevel = Field(..., description="Alert classification")
    explanation: str = Field(..., description="Risk assessment explanation")
    rules_violated: List[RuleViolation] = Field(
        default_factory=list, description="Regulatory violations"
    )
    behavioral_flags: List[BehavioralFlag] = Field(
        default_factory=list, description="Behavioral patterns"
    )
    recommended_action: str = Field(..., description="Recommended action")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "risk_score": 75,
                "alert_level": "HIGH",
                "explanation": "Transaction flagged due to PEP status and amount exceeding daily cash limit",
                "rules_violated": [
                    {
                        "rule_id": "HKMA-CASH-001",
                        "rule_type": "cash_limit",
                        "severity": "HIGH",
                        "score": 70,
                        "description": "Cash transaction exceeds HKD 8,000 threshold",
                        "jurisdiction": "HK",
                    }
                ],
                "behavioral_flags": [
                    {
                        "flag_type": "VELOCITY_HIGH",
                        "severity": "MEDIUM",
                        "score": 40,
                        "description": "Transaction frequency 4x normal",
                    }
                ],
                "recommended_action": "ENHANCED_DUE_DILIGENCE",
                "processing_time_ms": 1850,
            }
        }
    }


class RiskDetailResponse(BaseModel):
    """Response model for detailed risk breakdown"""

    transaction_id: UUID = Field(..., description="Transaction UUID")
    risk_score: int = Field(..., description="Final risk score")
    alert_level: AlertLevel = Field(..., description="Alert level")
    explanation: str = Field(..., description="Explanation")

    # Agent outputs
    static_violations: List[RuleViolation] = Field(
        default_factory=list, description="Static rule violations"
    )
    behavioral_flags: List[BehavioralFlag] = Field(
        default_factory=list, description="Behavioral flags"
    )
    static_rules_score: int = Field(..., description="Total static rules score")
    behavioral_score: int = Field(..., description="Total behavioral score")

    # Agent execution logs
    agent_execution_timeline: List[Dict[str, Any]] = Field(
        default_factory=list, description="Agent execution timeline"
    )

    analyzed_at: datetime = Field(..., description="Analysis timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "risk_score": 85,
                "alert_level": "HIGH",
                "explanation": "High risk due to multiple violations",
                "static_violations": [],
                "behavioral_flags": [],
                "static_rules_score": 65,
                "behavioral_score": 40,
                "agent_execution_timeline": [
                    {
                        "agent": "rule_parser",
                        "execution_time_ms": 200,
                        "status": "success",
                    }
                ],
                "analyzed_at": "2025-11-01T10:30:00Z",
            }
        }
    }


class ExplanationResponse(BaseModel):
    """Response model for natural language explanation"""

    transaction_id: UUID = Field(..., description="Transaction UUID")
    explanation: str = Field(..., description="Human-readable explanation")
    regulatory_citations: List[str] = Field(
        default_factory=list, description="Regulatory citations"
    )
    evidence: List[str] = Field(default_factory=list, description="Evidence list")
    recommended_action: str = Field(..., description="Recommended action")
    confidence: str = Field(..., description="Confidence level (HIGH/MEDIUM/LOW)")

    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "123e4567-e89b-12d3-a456-426614174000",
                "explanation": "This transaction requires enhanced due diligence due to...",
                "regulatory_citations": [
                    "HKMA AML/CFT Guideline 3.1.2",
                    "FATF Recommendation 10",
                ],
                "evidence": [
                    "Customer is classified as PEP",
                    "Cash transaction exceeds HKD 8,000 threshold",
                    "Transaction frequency 4x above customer's normal pattern",
                ],
                "recommended_action": "ENHANCED_DUE_DILIGENCE",
                "confidence": "HIGH",
            }
        }
    }


# ============================================================================
# RULE SYNC MODELS
# ============================================================================


class RuleSyncRequest(BaseModel):
    """Request model for regulatory rules synchronization"""

    jurisdiction: Optional[str] = Field(
        None,
        pattern="^(HK|SG|CH|US|UK)$",
        description="Sync rules for specific jurisdiction only",
    )
    force: bool = Field(
        False, description="Force sync even if cached rules exist (bypass cache)"
    )
    dry_run: bool = Field(
        False, description="Preview changes without applying to database"
    )

    @field_validator("jurisdiction")
    @classmethod
    def validate_jurisdiction(cls, v: Optional[str]) -> Optional[str]:
        """Ensure jurisdiction is uppercase if provided"""
        return v.upper() if v else None

    model_config = {
        "json_schema_extra": {
            "example": {
                "jurisdiction": "HK",
                "force": False,
                "dry_run": False,
            }
        }
    }


class RuleSyncResponse(BaseModel):
    """Response model for regulatory rules synchronization"""

    status: str = Field(..., description="Sync status: success/partial/failed")
    jurisdiction: Optional[str] = Field(
        None, description="Jurisdiction that was synced (if filtered)"
    )
    total_fetched: int = Field(..., description="Total rules fetched from service")
    rules_added: int = Field(..., description="Number of new rules added")
    rules_updated: int = Field(..., description="Number of existing rules updated")
    rules_failed: int = Field(..., description="Number of rules that failed to process")
    errors: List[str] = Field(
        default_factory=list, description="Error messages (limited to first 10)"
    )
    duration_seconds: float = Field(..., description="Total sync duration in seconds")
    timestamp: datetime = Field(..., description="Sync completion timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "success",
                "jurisdiction": "HK",
                "total_fetched": 15,
                "rules_added": 5,
                "rules_updated": 10,
                "rules_failed": 0,
                "errors": [],
                "duration_seconds": 2.5,
                "timestamp": "2025-11-01T15:30:00Z",
            }
        }
    }
