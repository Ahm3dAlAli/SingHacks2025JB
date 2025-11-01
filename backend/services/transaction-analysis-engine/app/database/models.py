"""
SQLAlchemy ORM models for TAE database schema.
Maps to 5 tables: transactions, risk_assessments, agent_execution_logs, audit_trail, regulatory_rules
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from sqlalchemy import (
    String,
    Integer,
    Boolean,
    TIMESTAMP,
    DATE,
    DECIMAL,
    TEXT,
    CheckConstraint,
    ForeignKey,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB, INET
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all ORM models"""

    pass


class Transaction(Base):
    """Transaction model - stores all transaction data from CSV"""

    __tablename__ = "transactions"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), unique=True, nullable=False, index=True
    )

    # Basic Transaction Info
    booking_jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    regulator: Mapped[str] = mapped_column(String(50), nullable=False)
    booking_datetime: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, index=True)
    value_date: Mapped[Optional[date]] = mapped_column(DATE)
    amount: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    channel: Mapped[Optional[str]] = mapped_column(String(50))
    product_type: Mapped[Optional[str]] = mapped_column(String(50))

    # Originator Info
    originator_name: Mapped[Optional[str]] = mapped_column(String(255))
    originator_account: Mapped[Optional[str]] = mapped_column(String(100))
    originator_country: Mapped[Optional[str]] = mapped_column(String(2))

    # Beneficiary Info
    beneficiary_name: Mapped[Optional[str]] = mapped_column(String(255))
    beneficiary_account: Mapped[Optional[str]] = mapped_column(String(100))
    beneficiary_country: Mapped[Optional[str]] = mapped_column(String(2))

    # SWIFT Fields
    swift_mt: Mapped[Optional[str]] = mapped_column(String(20))
    ordering_institution_bic: Mapped[Optional[str]] = mapped_column(String(11))
    beneficiary_institution_bic: Mapped[Optional[str]] = mapped_column(String(11))
    swift_f50_present: Mapped[bool] = mapped_column(Boolean, default=False)
    swift_f59_present: Mapped[bool] = mapped_column(Boolean, default=False)
    swift_f70_purpose: Mapped[Optional[str]] = mapped_column(TEXT)
    swift_f71_charges: Mapped[Optional[str]] = mapped_column(String(10))
    travel_rule_complete: Mapped[bool] = mapped_column(Boolean, default=False)

    # FX Info
    fx_indicator: Mapped[bool] = mapped_column(Boolean, default=False)
    fx_base_ccy: Mapped[Optional[str]] = mapped_column(String(3))
    fx_quote_ccy: Mapped[Optional[str]] = mapped_column(String(3))
    fx_applied_rate: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 6))
    fx_market_rate: Mapped[Optional[Decimal]] = mapped_column(DECIMAL(10, 6))
    fx_spread_bps: Mapped[Optional[int]] = mapped_column(Integer)
    fx_counterparty: Mapped[Optional[str]] = mapped_column(String(255))

    # Customer Info
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    customer_type: Mapped[Optional[str]] = mapped_column(String(50))
    customer_risk_rating: Mapped[Optional[str]] = mapped_column(String(20))
    customer_is_pep: Mapped[bool] = mapped_column(Boolean, default=False)
    kyc_last_completed: Mapped[Optional[date]] = mapped_column(DATE)
    kyc_due_date: Mapped[Optional[date]] = mapped_column(DATE)
    edd_required: Mapped[bool] = mapped_column(Boolean, default=False)
    edd_performed: Mapped[bool] = mapped_column(Boolean, default=False)
    sow_documented: Mapped[bool] = mapped_column(Boolean, default=False)

    # Transaction Details
    purpose_code: Mapped[Optional[str]] = mapped_column(String(10))
    narrative: Mapped[Optional[str]] = mapped_column(TEXT)
    is_advised: Mapped[bool] = mapped_column(Boolean, default=False)
    product_complex: Mapped[bool] = mapped_column(Boolean, default=False)
    client_risk_profile: Mapped[Optional[str]] = mapped_column(String(20))
    suitability_assessed: Mapped[bool] = mapped_column(Boolean, default=False)
    suitability_result: Mapped[Optional[str]] = mapped_column(String(50))
    product_has_va_exposure: Mapped[bool] = mapped_column(Boolean, default=False)
    va_disclosure_provided: Mapped[bool] = mapped_column(Boolean, default=False)

    # Cash Transaction Fields
    cash_id_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    daily_cash_total_customer: Mapped[Decimal] = mapped_column(DECIMAL(15, 2), default=0)
    daily_cash_txn_count: Mapped[int] = mapped_column(Integer, default=0)

    # Screening & Compliance
    sanctions_screening: Mapped[Optional[str]] = mapped_column(String(20), index=True)
    suspicion_determined_datetime: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    str_filed_datetime: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    # Flexible Storage
    raw_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Batch Processing
    batch_id: Mapped[Optional[str]] = mapped_column(String(100), index=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # Relationships
    risk_assessment: Mapped[Optional["RiskAssessment"]] = relationship(
        "RiskAssessment", back_populates="transaction", uselist=False
    )


class RiskAssessment(Base):
    """Risk assessment results per transaction"""

    __tablename__ = "risk_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("transactions.transaction_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Risk Scoring
    risk_score: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("risk_score >= 0 AND risk_score <= 100"),
        nullable=False,
        index=True,
    )
    alert_level: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("alert_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')"),
        nullable=False,
        index=True,
    )

    # Analysis Results
    rules_triggered: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="[]")
    patterns_detected: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="[]")
    explanation: Mapped[Optional[str]] = mapped_column(TEXT)

    # Agent Contributions
    static_rules_score: Mapped[Optional[int]] = mapped_column(Integer)
    behavioral_score: Mapped[Optional[int]] = mapped_column(Integer)

    # Timestamps
    analyzed_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp()
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # Relationships
    transaction: Mapped["Transaction"] = relationship(
        "Transaction", back_populates="risk_assessment"
    )


class AgentExecutionLog(Base):
    """Audit trail of agent executions"""

    __tablename__ = "agent_execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, index=True)
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # Execution Data
    input_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    output_data: Mapped[Optional[dict]] = mapped_column(JSONB)
    execution_time_ms: Mapped[Optional[int]] = mapped_column(Integer)

    # Status Tracking
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('success', 'error', 'timeout', 'skipped')"),
        nullable=False,
        index=True,
    )
    error_message: Mapped[Optional[str]] = mapped_column(TEXT)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), index=True
    )


class AuditTrail(Base):
    """System-wide audit log for regulatory compliance"""

    __tablename__ = "audit_trail"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Service & Action
    service_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)

    # User Info
    user_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Resource Info
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))

    # Details
    details: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Network Info
    ip_address: Mapped[Optional[str]] = mapped_column(INET)

    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), index=True
    )


class RegulatoryRule(Base):
    """Regulatory rules (read-only, written by Service 1)"""

    __tablename__ = "regulatory_rules"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Rule Identification
    rule_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    jurisdiction: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    regulator: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)

    # Rule Content
    rule_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    rule_parameters: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Severity & Priority
    severity: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')"),
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(Integer, default=100)

    # Versioning
    effective_date: Mapped[date] = mapped_column(DATE, nullable=False, index=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(DATE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Metadata
    source_url: Mapped[Optional[str]] = mapped_column(TEXT)
    tags: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String(255)))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )


class BatchMetadata(Base):
    """Batch processing metadata for CSV uploads"""

    __tablename__ = "batch_metadata"

    # Primary Key
    batch_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, server_default=func.uuid_generate_v4()
    )

    # Batch Info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    total_transactions: Mapped[int] = mapped_column(Integer, nullable=False)
    processed_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)

    # Status Tracking
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED')"),
        nullable=False,
        index=True,
    )

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    completed_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)

    # Error Handling
    error_message: Mapped[Optional[str]] = mapped_column(TEXT)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
