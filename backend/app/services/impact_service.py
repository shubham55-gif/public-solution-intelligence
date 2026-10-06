"""Transparent, window-based hotspot intervention impact measurements."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import (
    Hotspot,
    HotspotReport,
    ImpactMetric,
    Intervention,
    InterventionStatus,
    Report,
)
from app.schemas.impact import ImpactMeasureRequest


class ImpactPersistenceError(Exception):
    """Raised after an impact transaction has been rolled back."""


class ImpactValidationError(Exception):
    """Raised when an impact request does not describe a valid relationship/window."""


class ImpactService:
    WINDOW_DAYS = 7
    RECURRENCE_UNAVAILABLE = "not_available"

    def __init__(self, session: Session) -> None:
        self.session = session

    def hotspot_exists(self, hotspot_id: UUID) -> bool:
        return self.session.get(Hotspot, hotspot_id) is not None

    def snapshot(self, hotspot_id: UUID, measured_at: datetime | None):
        hotspot = self.session.get(Hotspot, hotspot_id)
        if hotspot is None:
            raise LookupError("Hotspot not found")
        measured_at = measured_at or datetime.now(timezone.utc)
        count = self._report_count(hotspot_id, measured_at)
        return {
            "hotspot_id": hotspot_id,
            "measured_at": measured_at,
            "window_days": self.WINDOW_DAYS,
            "risk_score": float(hotspot.risk_score),
            "report_frequency": count / self.WINDOW_DAYS,
            "recurrence_level": self.RECURRENCE_UNAVAILABLE,
            "report_count": count,
        }

    def measure(self, hotspot_id: UUID, data: ImpactMeasureRequest) -> ImpactMetric:
        hotspot = self.session.get(Hotspot, hotspot_id)
        if hotspot is None:
            raise LookupError("Hotspot not found")
        intervention = self.session.get(Intervention, data.intervention_id)
        if intervention is None:
            raise LookupError("Intervention not found")
        if intervention.hotspot_id != hotspot_id:
            raise ImpactValidationError("Intervention does not belong to hotspot")

        before_at = data.before_measured_at or intervention.started_at
        after_at = data.after_measured_at or intervention.completed_at
        if before_at is None or after_at is None:
            raise ImpactValidationError(
                "before_measured_at and after_measured_at are required when intervention timestamps are missing"
            )
        if after_at <= before_at:
            raise ImpactValidationError("after_measured_at must be after before_measured_at")
        if (
            intervention.status != InterventionStatus.COMPLETED
            and data.after_measured_at is None
        ):
            raise ImpactValidationError(
                "An active intervention requires an explicit after_measured_at"
            )

        before_frequency = self._report_count(hotspot_id, before_at) / self.WINDOW_DAYS
        after_frequency = self._report_count(hotspot_id, after_at) / self.WINDOW_DAYS
        before_risk = float(hotspot.risk_score)
        after_risk = float(hotspot.risk_score)

        metric = ImpactMetric(
            hotspot_id=hotspot_id,
            intervention_id=intervention.id,
            before_risk_score=before_risk,
            after_risk_score=after_risk,
            before_report_frequency=before_frequency,
            after_report_frequency=after_frequency,
            before_recurrence_level=self.RECURRENCE_UNAVAILABLE,
            after_recurrence_level=self.RECURRENCE_UNAVAILABLE,
            risk_reduction_percent=self._reduction_percent(before_risk, after_risk),
            report_reduction_percent=self._reduction_percent(
                before_frequency, after_frequency
            ),
            measured_at=after_at,
        )
        self.session.add(metric)
        try:
            self.session.commit()
            self.session.refresh(metric)
            return metric
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ImpactPersistenceError("Could not persist impact measurement") from exc

    def latest(self, hotspot_id: UUID) -> ImpactMetric | None:
        statement = (
            select(ImpactMetric)
            .where(ImpactMetric.hotspot_id == hotspot_id)
            .order_by(ImpactMetric.measured_at.desc())
            .limit(1)
        )
        try:
            return self.session.scalar(statement)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ImpactPersistenceError("Could not retrieve impact measurement") from exc

    def for_intervention(self, intervention_id: UUID) -> list[ImpactMetric]:
        statement = (
            select(ImpactMetric)
            .where(ImpactMetric.intervention_id == intervention_id)
            .order_by(ImpactMetric.measured_at.desc())
        )
        try:
            return list(self.session.scalars(statement))
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise ImpactPersistenceError("Could not retrieve intervention impact") from exc

    def _report_count(self, hotspot_id: UUID, measured_at: datetime) -> int:
        window_start = measured_at - timedelta(days=self.WINDOW_DAYS)
        statement = (
            select(func.count(Report.id))
            .join(HotspotReport, HotspotReport.report_id == Report.id)
            .where(
                HotspotReport.hotspot_id == hotspot_id,
                Report.reported_at >= window_start,
                Report.reported_at <= measured_at,
            )
        )
        return int(self.session.scalar(statement) or 0)

    @staticmethod
    def _reduction_percent(before: float, after: float) -> float:
        if before <= 0:
            return 0.0
        value = (before - after) / before * 100
        return round(max(0.0, min(100.0, value)), 2)
