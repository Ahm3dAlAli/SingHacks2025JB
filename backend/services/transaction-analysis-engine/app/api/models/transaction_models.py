"""
Transaction analysis models for Transaction Analysis Engine API.
Defines data transfer objects for transaction processing and analysis.
"""
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, validator
from decimal import Decimal

from . import SeverityLevel, AlertLevel, RuleViolation, BehavioralFlag


class TransactionType(str, Enum):
    """Supported transaction types"""
    CASH_DEPOSIT = "CASH_DEPOSIT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"
    FUNDS_TRANSFER = "FUNDS_TRANSFER"
    BILL_PAYMENT = "BILL_PAYMENT"
    CARD_PAYMENT = "CARD_PAYMENT"
    MOBILE_WALLET = "MOBILE_WALLET"
    CRYPTO_TRADE = "CRYPTO_TRADE"
    SECURITIES_TRADE = "SECURITIES_TRADE"
    LOAN_DISBURSEMENT = "LOAN_DISBURSEMENT"
    LOAN_REPAYMENT = "LOAN_REPAYMENT"


class TransactionStatus(str, Enum):
    """Transaction status values"""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    HOLD = "HOLD"
    CANCELLED = "CANCELLED"


class CustomerType(str, Enum):
    """Customer type classification"""
    INDIVIDUAL = "INDIVIDUAL"
    BUSINESS = "BUSINESS"
    FINANCIAL_INSTITUTION = "FINANCIAL_INSTITUTION"
    GOVERNMENT = "GOVERNMENT"
    NON_PROFIT = "NON_PROFIT"


class TransactionParty(BaseModel):
    """Represents a party involved in a transaction"""
    id: str = Field(..., description="Unique identifier for the party")
    name: str = Field(..., description="Full name of the party")
    type: CustomerType = Field(..., description="Type of customer")
    account_number: Optional[str] = Field(None, description="Account number")
    account_type: Optional[str] = Field(None, description="Type of account")
    bank_code: Optional[str] = Field(None, description="Bank or institution code")
    country: str = Field(..., description="ISO 3166-1 alpha-2 country code")
    is_pep: bool = Field(False, description="Is a politically exposed person")
    is_sanctioned: bool = Field(False, description="Is on any sanctions list")
    risk_score: Optional[int] = Field(None, ge=0, le=100, description="Risk score (0-100)")
    additional_info: Optional[Dict[str, Any]] = Field(None, description="Additional KYC/AML data")


class TransactionAnalysisRequest(BaseModel):
    """Request model for transaction analysis endpoint.
    
    This model wraps a transaction input with additional metadata for the analysis request.
    """
    transaction: 'TransactionInput' = Field(..., description="Transaction to analyze")
    request_id: Optional[str] = Field(
        None,
        description="Client-provided request ID for correlation"
    )
    priority: str = Field(
        "NORMAL",
        description="Processing priority (LOW, NORMAL, HIGH, CRITICAL)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction": {
                    "transaction_id": "txn_1234567890abcdef",
                    "reference_id": "INV-2025-1001",
                    "timestamp": "2025-01-15T14:30:00Z",
                    "type": "FUNDS_TRANSFER",
                    "status": "PENDING",
                    "amount": "1500.75",
                    "currency": "USD",
                    "description": "Invoice payment #INV-2025-1001",
                    "originator": {
                        "id": "cust_9876543210",
                        "name": "John Doe",
                        "type": "INDIVIDUAL",
                        "account_number": "1234567890",
                        "account_type": "CHECKING",
                        "bank_code": "CHASUS33",
                        "country": "US",
                        "is_pep": False,
                        "is_sanctioned": False,
                        "risk_score": 25
                    },
                    "beneficiary": {
                        "id": "cust_1234567890",
                        "name": "Acme Corp",
                        "type": "BUSINESS",
                        "account_number": "0987654321",
                        "account_type": "CHECKING",
                        "bank_code": "CITIUS33",
                        "country": "US",
                        "is_pep": False,
                        "is_sanctioned": False,
                        "risk_score": 10
                    },
                    "channel": "ONLINE",
                    "device_id": "dev_xyz123",
                    "ip_address": "192.168.1.100"
                },
                "request_id": "req_1234567890",
                "priority": "NORMAL"
            }
        }
    }


class TransactionInput(BaseModel):
    """Input model for transaction analysis requests.
    
    This model represents a transaction that needs to be analyzed for potential risks.
    It includes all relevant details about the transaction and involved parties.
    """
    transaction_id: str = Field(..., description="Unique transaction identifier")
    reference_id: Optional[str] = Field(None, description="External reference ID")
    timestamp: datetime = Field(..., description="Transaction timestamp")
    type: TransactionType = Field(..., description="Type of transaction")
    status: TransactionStatus = Field(..., description="Current status")
    amount: Decimal = Field(..., gt=0, description="Transaction amount")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO 4217 currency code")
    description: Optional[str] = Field(None, description="Transaction description")
    
    # Parties involved
    originator: TransactionParty = Field(..., description="Originating party")
    beneficiary: TransactionParty = Field(..., description="Receiving party")
    
    # Additional context
    channel: str = Field(..., description="Transaction channel (e.g., ONLINE, BRANCH, ATM)")
    device_id: Optional[str] = Field(None, description="Device identifier")
    ip_address: Optional[str] = Field(None, description="IP address")
    location: Optional[Dict[str, float]] = Field(
        None,
        description="Geolocation coordinates: {lat: float, lon: float}"
    )
    
    # Metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata or custom fields"
    )
    
    # Relationships
    related_transactions: List[str] = Field(
        default_factory=list,
        description="List of related transaction IDs"
    )
    
    # Validation
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError('Amount must be greater than 0')
        return v.quantize(Decimal('0.01'))
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "txn_1234567890abcdef",
                "reference_id": "INV-2025-1001",
                "timestamp": "2025-01-15T14:30:00Z",
                "type": "FUNDS_TRANSFER",
                "status": "PENDING",
                "amount": "1500.75",
                "currency": "USD",
                "description": "Invoice payment #INV-2025-1001",
                "originator": {
                    "id": "cust_9876543210",
                    "name": "John Doe",
                    "type": "INDIVIDUAL",
                    "account_number": "1234567890",
                    "account_type": "CHECKING",
                    "bank_code": "CHASUS33",
                    "country": "US",
                    "is_pep": False,
                    "is_sanctioned": False,
                    "risk_score": 25
                },
                "beneficiary": {
                    "id": "cust_1234567890",
                    "name": "Acme Corp",
                    "type": "BUSINESS",
                    "account_number": "0987654321",
                    "account_type": "CHECKING",
                    "bank_code": "CITIUS33",
                    "country": "US",
                    "is_pep": False,
                    "is_sanctioned": False,
                    "risk_score": 10
                },
                "channel": "ONLINE",
                "device_id": "dev_xyz123",
                "ip_address": "192.168.1.100",
                "location": {"lat": 40.7128, "lon": -74.0060},
                "metadata": {
                    "invoice_number": "INV-2025-1001",
                    "category": "SERVICES"
                },
                "related_transactions": ["txn_a1b2c3d4e5f6"]
            }
        }
    }


class TransactionAnalysisResponse(BaseModel):
    """Response model for transaction analysis"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    risk_score: int = Field(..., ge=0, le=100, description="Overall risk score (0-100)")
    alert_level: AlertLevel = Field(..., description="Recommended alert level")
    decision: str = Field(..., description="Recommended decision (APPROVE, REVIEW, DECLINE)")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    
    # Analysis results
    violations: List[RuleViolation] = Field(
        default_factory=list,
        description="List of rule violations"
    )
    behavioral_flags: List[BehavioralFlag] = Field(
        default_factory=list,
        description="Behavioral pattern detections"
    )
    
    # Metadata
    analysis_id: str = Field(..., description="Unique analysis identifier")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")
    
    # Explanation
    explanation_summary: str = Field(..., description="Human-readable summary")
    recommended_action: str = Field(..., description="Recommended action")
    
    # Model configuration
    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "txn_1234567890abcdef",
                "risk_score": 75,
                "alert_level": "HIGH",
                "decision": "REVIEW",
                "timestamp": "2025-01-15T14:30:05.123456Z",
                "violations": [
                    {
                        "rule_id": "HKMA-CASH-001",
                        "rule_type": "cash_limit",
                        "severity": "HIGH",
                        "score": 70,
                        "description": "Cash transaction exceeds HKD 8,000 threshold",
                        "jurisdiction": "HK",
                        "parameters": {"limit": 8000, "currency": "HKD"}
                    }
                ],
                "behavioral_flags": [
                    {
                        "flag_type": "VELOCITY_ANOMALY",
                        "severity": "MEDIUM",
                        "score": 45,
                        "description": "Transaction frequency 4x normal (12 transactions in 24h)",
                        "detection_details": {
                            "transactions_24h": 12,
                            "normal_rate": 3,
                            "multiplier": 4.0
                        }
                    }
                ],
                "analysis_id": "ana_9876543210fedcba",
                "processing_time_ms": 245,
                "explanation_summary": "Transaction flagged due to cash limit violation and unusual activity pattern.",
                "recommended_action": "Review transaction and customer history for potential structuring."
            }
        }
    }


class RiskDetailResponse(BaseModel):
    """Detailed risk assessment for a transaction"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    risk_score: int = Field(..., ge=0, le=100, description="Overall risk score (0-100)")
    alert_level: AlertLevel = Field(..., description="Alert level")
    decision: str = Field(..., description="Recommended decision")
    timestamp: datetime = Field(..., description="Analysis timestamp")
    
    # Detailed breakdown
    rule_violations: List[RuleViolation] = Field(
        default_factory=list,
        description="All rule violations"
    )
    behavioral_flags: List[BehavioralFlag] = Field(
        default_factory=list,
        description="Behavioral pattern detections"
    )
    
    # Risk factors
    risk_factors: Dict[str, int] = Field(
        default_factory=dict,
        description="Contribution of each risk factor to the overall score"
    )
    
    # Execution timeline
    execution_timeline: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Detailed execution timeline of the analysis"
    )
    
    # Model configuration
    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "txn_1234567890abcdef",
                "risk_score": 75,
                "alert_level": "HIGH",
                "decision": "REVIEW",
                "timestamp": "2025-01-15T14:30:05.123456Z",
                "rule_violations": [
                    {
                        "rule_id": "HKMA-CASH-001",
                        "rule_type": "cash_limit",
                        "severity": "HIGH",
                        "score": 70,
                        "description": "Cash transaction exceeds HKD 8,000 threshold",
                        "jurisdiction": "HK"
                    }
                ],
                "behavioral_flags": [
                    {
                        "flag_type": "VELOCITY_ANOMALY",
                        "severity": "MEDIUM",
                        "score": 45,
                        "description": "Transaction frequency 4x normal"
                    }
                ],
                "risk_factors": {
                    "cash_limit_violation": 70,
                    "velocity_anomaly": 45,
                    "pep_risk": 0,
                    "sanctions_risk": 0
                },
                "execution_timeline": [
                    {
                        "step": "rule_engine",
                        "start_time": "2025-01-15T14:30:01.123456Z",
                        "end_time": "2025-01-15T14:30:01.523456Z",
                        "duration_ms": 400,
                        "status": "COMPLETED"
                    },
                    {
                        "step": "behavior_analysis",
                        "start_time": "2025-01-15T14:30:01.523456Z",
                        "end_time": "2025-01-15T14:30:02.023456Z",
                        "duration_ms": 500,
                        "status": "COMPLETED"
                    }
                ]
            }
        }
    }


class ExplanationResponse(BaseModel):
    """Natural language explanation of a transaction's risk"""
    transaction_id: str = Field(..., description="Unique transaction identifier")
    explanation: str = Field(..., description="Human-readable explanation")
    risk_summary: str = Field(..., description="Summary of identified risks")
    
    # Citations and evidence
    citations: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Sources and evidence supporting the explanation"
    )
    
    # Recommended actions
    recommended_actions: List[str] = Field(
        default_factory=list,
        description="List of recommended actions"
    )
    
    # Model configuration
    model_config = {
        "json_schema_extra": {
            "example": {
                "transaction_id": "txn_1234567890abcdef",
                "explanation": "This transaction was flagged due to multiple risk factors. The customer, identified as a Politically Exposed Person (PEP), is conducting a high-value transaction that significantly exceeds their normal transaction patterns.",
                "risk_summary": "High-risk transaction: PEP status + unusual transaction amount + velocity anomaly",
                "citations": [
                    {
                        "source": "PEP database",
                        "reference": "PEP-2023-0456",
                        "description": "Customer listed as PEP with high-risk classification"
                    },
                    {
                        "source": "Transaction history",
                        "reference": "TXN-HIST-001",
                        "description": "Transaction amount 5x higher than 90-day average"
                    }
                ],
                "recommended_actions": [
                    "Enhanced Due Diligence (EDD) required",
                    "Obtain senior management approval",
                    "Document the business purpose of the transaction",
                    "Monitor account for similar transactions"
                ]
            }
        }
    }
