"""Core PostgreSQL ORM entities for Public Solution Intelligence."""

from __future__ import annotations

import uuid
from datetime import datetime, time
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, DateTime, Enum as SqlEnum, Float, ForeignKey
from sqlalchemy import Integer, Numeric, String, Text, Time, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserRole(str, Enum):
    CITIZEN = "citizen"
    AUTHORITY = "authority"


class ReportStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"


class VlmValidationStatus(str, Enum):
    PENDING = "pending"
    VALIDATED = "validated"
    NEEDS_REVIEW = "needs_review"


class RiskLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class HotspotTrend(str, Enum):
    IMPROVING = "improving"
    STABLE = "stable"
    INCREASING = "increasing"


class InterventionStatus(str, Enum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


def enum_column_type(enum_class: type[Enum], name: str) -> SqlEnum:
    """Persist enum values (for example ``pending``), not Python member names."""
    return SqlEnum(
        enum_class,
        name=name,
        values_callable=lambda values: [member.value for member in values],
    )


class TimestampMixin:
    """Timezone-aware audit timestamps shared by mutable core records."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        enum_column_type(UserRole, "user_role"), nullable=False, server_default=UserRole.CITIZEN.value
    )

    reports: Mapped[list[Report]] = relationship(
        "Report", back_populates="user", foreign_keys="Report.user_id"
    )
    assigned_reports: Mapped[list[Report]] = relationship(
        "Report", back_populates="assigned_admin", foreign_keys="Report.assigned_admin_id"
    )
    resolved_reports: Mapped[list[Report]] = relationship(
        "Report", back_populates="resolved_by_admin", foreign_keys="Report.resolved_by_admin_id"
    )
    status_changes: Mapped[list[ReportStatusHistory]] = relationship(back_populates="changed_by_user")
    notifications: Mapped[list[Notification]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def is_admin(self) -> bool:
        """Return True if user has the authority/admin role."""
        role_val = self.role.value if hasattr(self.role, "value") else str(self.role)
        return role_val.lower() in ("authority", "admin")


class Report(TimestampMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        CheckConstraint("latitude BETWEEN -90 AND 90", name="ck_reports_latitude_range"),
        CheckConstraint("longitude BETWEEN -180 AND 180", name="ck_reports_longitude_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    issue_category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    longitude: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    severity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[ReportStatus] = mapped_column(
        enum_column_type(ReportStatus, "report_status"),
        nullable=False,
        server_default=ReportStatus.PENDING.value,
        index=True,
    )
    image_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    resolution_image_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    assigned_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    resolved_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    user: Mapped[User] = relationship(
        "User", back_populates="reports", foreign_keys=[user_id]
    )
    assigned_admin: Mapped[User | None] = relationship(
        "User", back_populates="assigned_reports", foreign_keys=[assigned_admin_id]
    )
    resolved_by_admin: Mapped[User | None] = relationship(
        "User", back_populates="resolved_reports", foreign_keys=[resolved_by_admin_id]
    )
    ai_analysis: Mapped[AIAnalysis | None] = relationship(
        back_populates="report", uselist=False, cascade="all, delete-orphan"
    )
    hotspot_links: Mapped[list[HotspotReport]] = relationship(
        back_populates="report", cascade="all, delete-orphan"
    )
    status_history: Mapped[list[ReportStatusHistory]] = relationship(
        back_populates="report", cascade="all, delete-orphan", order_by="ReportStatusHistory.changed_at.asc()"
    )

    @property
    def has_ai_analysis(self) -> bool:
        return self.ai_analysis is not None

    @property
    def citizen_name(self) -> str | None:
        return self.user.name if self.user else None

    @property
    def assigned_admin_name(self) -> str | None:
        return self.assigned_admin.name if self.assigned_admin else None

    @property
    def resolved_by_admin_name(self) -> str | None:
        return self.resolved_by_admin.name if self.resolved_by_admin else None


class AIAnalysis(TimestampMixin, Base):
    __tablename__ = "ai_analysis"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    llm_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    time_context: Mapped[str | None] = mapped_column(String(255), nullable=True)
    severity_indicator: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vlm_result: Mapped[str | None] = mapped_column(Text, nullable=True)
    vlm_validation_status: Mapped[VlmValidationStatus] = mapped_column(
        enum_column_type(VlmValidationStatus, "vlm_validation_status"),
        nullable=False,
        server_default=VlmValidationStatus.PENDING.value,
    )

    report: Mapped[Report] = relationship(back_populates="ai_analysis")


class Hotspot(TimestampMixin, Base):
    __tablename__ = "hotspots"
    __table_args__ = (
        CheckConstraint("center_latitude BETWEEN -90 AND 90", name="ck_hotspots_latitude_range"),
        CheckConstraint("center_longitude BETWEEN -180 AND 180", name="ck_hotspots_longitude_range"),
        CheckConstraint("risk_score BETWEEN 0 AND 100", name="ck_hotspots_risk_score_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    center_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    center_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    report_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    dominant_category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, server_default="0", index=True)
    risk_level: Mapped[RiskLevel] = mapped_column(
        enum_column_type(RiskLevel, "hotspot_risk_level"), nullable=False, server_default=RiskLevel.LOW.value
    )
    trend: Mapped[HotspotTrend] = mapped_column(
        enum_column_type(HotspotTrend, "hotspot_trend"),
        nullable=False,
        server_default=HotspotTrend.STABLE.value,
        index=True,
    )
    peak_time_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    peak_time_end: Mapped[time | None] = mapped_column(Time, nullable=True)
    recurrence_level: Mapped[str | None] = mapped_column(String(50), nullable=True)

    report_links: Mapped[list[HotspotReport]] = relationship(
        back_populates="hotspot", cascade="all, delete-orphan"
    )
    interventions: Mapped[list[Intervention]] = relationship(back_populates="hotspot")
    impact_metrics: Mapped[list[ImpactMetric]] = relationship(back_populates="hotspot")


class HotspotReport(Base):
    __tablename__ = "hotspot_reports"

    hotspot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hotspots.id", ondelete="CASCADE"), primary_key=True
    )
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), primary_key=True
    )

    hotspot: Mapped[Hotspot] = relationship(back_populates="report_links")
    report: Mapped[Report] = relationship(back_populates="hotspot_links")


class Intervention(TimestampMixin, Base):
    __tablename__ = "interventions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hotspot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hotspots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    action_type: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    assigned_unit: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[InterventionStatus] = mapped_column(
        enum_column_type(InterventionStatus, "intervention_status"),
        nullable=False,
        server_default=InterventionStatus.PLANNED.value,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    hotspot: Mapped[Hotspot] = relationship(back_populates="interventions")
    impact_metrics: Mapped[list[ImpactMetric]] = relationship(back_populates="intervention")


class ImpactMetric(Base):
    __tablename__ = "impact_metrics"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hotspot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("hotspots.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    intervention_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("interventions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    before_risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    after_risk_score: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    before_report_frequency: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    after_report_frequency: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    before_recurrence_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    after_recurrence_level: Mapped[str | None] = mapped_column(String(50), nullable=True)
    risk_reduction_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    report_reduction_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    measured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    hotspot: Mapped[Hotspot] = relationship(back_populates="impact_metrics")
    intervention: Mapped[Intervention] = relationship(back_populates="impact_metrics")


class ReportStatusHistory(Base):
    __tablename__ = "report_status_history"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    report_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True
    )
    old_status: Mapped[ReportStatus] = mapped_column(
        enum_column_type(ReportStatus, "report_status"), nullable=False
    )
    new_status: Mapped[ReportStatus] = mapped_column(
        enum_column_type(ReportStatus, "report_status"), nullable=False
    )
    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    report: Mapped[Report] = relationship(back_populates="status_history")
    changed_by_user: Mapped[User | None] = relationship(back_populates="status_changes")

    @property
    def changed_by_admin_name(self) -> str | None:
        return self.changed_by_user.name if self.changed_by_user else None


class Notification(Base):
    """In-app notification sent to a citizen when their report status changes."""
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="status_update")
    is_read: Mapped[bool] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="notifications")
