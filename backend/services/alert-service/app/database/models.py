"""
SQLAlchemy ORM models for Alert Service database schema.
Maps to 4 tables: alerts, alert_notifications, alert_notes, alert_status_history
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import (
    String,
    Integer,
    TEXT,
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    """Base class for all ORM models"""

    pass


class Alert(Base):
    """Alert model - stores all risk alerts from TAE"""

    __tablename__ = "alerts"

    # Primary Key
    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    transaction_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    # Risk Assessment
    risk_score: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("risk_score >= 0 AND risk_score <= 100"),
        nullable=False,
    )
    alert_level: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("alert_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')"),
        nullable=False,
        index=True,
    )
    severity: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("severity IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')"),
        nullable=False,
    )

    # Content
    explanation: Mapped[Optional[str]] = mapped_column(TEXT)
    summary: Mapped[Optional[str]] = mapped_column(String(500))
    rules_violated: Mapped[Optional[dict]] = mapped_column(JSONB, default=dict, server_default="[]")
    behavioral_flags: Mapped[Optional[dict]] = mapped_column(
        JSONB, default=dict, server_default="[]"
    )
    recommended_action: Mapped[Optional[str]] = mapped_column(String(100))

    # Transaction Context
    transaction_data: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Routing & Assignment
    assigned_to: Mapped[Optional[str]] = mapped_column(String(100), index=True)
    priority: Mapped[int] = mapped_column(Integer, default=50, server_default="50")

    # Status Management
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "status IN ('NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED', 'FALSE_POSITIVE')"
        ),
        default="NEW",
        server_default="NEW",
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP, server_default=func.current_timestamp(), index=True
    )
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    acknowledged_by: Mapped[Optional[str]] = mapped_column(String(100))
    resolved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(100))

    # Audit
    created_by: Mapped[str] = mapped_column(
        String(100), default="TAE_SERVICE", server_default="TAE_SERVICE"
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
    )


class AlertNotification(Base):
    """Alert notification tracking model"""

    __tablename__ = "alert_notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("alerts.alert_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    channel: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient: Mapped[Optional[str]] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="PENDING", server_default="PENDING")
    sent_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP)
    error_message: Mapped[Optional[str]] = mapped_column(TEXT)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())


class AlertNote(Base):
    """Alert notes (user comments) model"""

    __tablename__ = "alert_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("alerts.alert_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    note_text: Mapped[str] = mapped_column(TEXT, nullable=False)
    created_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())


class AlertStatusHistory(Base):
    """Alert status history (audit trail) model"""

    __tablename__ = "alert_status_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    alert_id: Mapped[str] = mapped_column(
        String(50),
        ForeignKey("alerts.alert_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    old_status: Mapped[Optional[str]] = mapped_column(String(20))
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(100), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.current_timestamp())
    reason: Mapped[Optional[str]] = mapped_column(TEXT)
