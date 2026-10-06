"""Deterministic, read-only related-report analysis."""

from __future__ import annotations

from datetime import datetime, timezone
from math import asin, cos, radians, sin, sqrt
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import (
    DUPLICATE_SPATIAL_THRESHOLD_METERS,
    DUPLICATE_TEMPORAL_THRESHOLD_HOURS,
)
from app.models.entities import Report
from app.schemas.duplicates import DuplicateCheckResponse, RelatedReport


class DuplicatePersistenceError(Exception):
    """Raised when reports cannot be read for duplicate analysis."""


class DuplicateValidationError(Exception):
    """Raised when duplicate-analysis filters are invalid."""


class DuplicateService:
    EARTH_RADIUS_METERS = 6_371_000

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_report(self, report_id: UUID) -> Report | None:
        try:
            return self.session.get(Report, report_id)
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DuplicatePersistenceError("Could not retrieve report") from exc

    def check(self, report_id: UUID) -> DuplicateCheckResponse:
        report = self.get_report(report_id)
        if report is None:
            raise LookupError("Report not found")
        candidates = self._reports_for_comparison(report)
        return self._analyze(report, candidates)

    def list_detected(
        self,
        *,
        category: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
    ) -> list[DuplicateCheckResponse]:
        if from_ is not None and to is not None and to < from_:
            raise DuplicateValidationError("to must be greater than or equal to from")
        try:
            conditions = []
            if category:
                conditions.append(Report.issue_category == category)
            if from_ is not None:
                conditions.append(Report.reported_at >= from_)
            if to is not None:
                conditions.append(Report.reported_at <= to)
            reports = list(
                self.session.scalars(
                    select(Report).where(*conditions).order_by(Report.reported_at.desc())
                )
            )
            all_reports = list(self.session.scalars(select(Report)))
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DuplicatePersistenceError("Could not retrieve reports") from exc

        by_id = {report.id: report for report in all_reports}
        results = []
        for report in reports:
            candidates = [candidate for candidate in by_id.values() if candidate.id != report.id]
            analysis = self._analyze(report, candidates)
            if analysis.likely_duplicate:
                results.append(analysis)
        return results

    def _reports_for_comparison(self, report: Report) -> list[Report]:
        try:
            return list(
                self.session.scalars(
                    select(Report).where(Report.id != report.id)
                )
            )
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise DuplicatePersistenceError("Could not retrieve related reports") from exc

    def _analyze(
        self, report: Report, candidates: list[Report]
    ) -> DuplicateCheckResponse:
        related = []
        for candidate in candidates:
            same_category = self._same_category(report.issue_category, candidate.issue_category)
            distance = self._distance_meters(
                report.latitude,
                report.longitude,
                candidate.latitude,
                candidate.longitude,
            )
            time_difference = abs(
                self._aware(report.reported_at) - self._aware(candidate.reported_at)
            ).total_seconds() / 3600
            if (
                same_category
                and distance <= DUPLICATE_SPATIAL_THRESHOLD_METERS
                and time_difference <= DUPLICATE_TEMPORAL_THRESHOLD_HOURS
            ):
                related.append(
                    RelatedReport(
                        report_id=candidate.id,
                        distance_meters=round(distance, 2),
                        time_difference_hours=round(time_difference, 2),
                        same_category=True,
                        reasons=[
                            "issue categories match",
                            f"distance is within {DUPLICATE_SPATIAL_THRESHOLD_METERS:g} meters",
                            f"time difference is within {DUPLICATE_TEMPORAL_THRESHOLD_HOURS:g} hours",
                        ],
                    )
                )
        related.sort(key=lambda item: (item.distance_meters, item.time_difference_hours, str(item.report_id)))
        return DuplicateCheckResponse(
            report_id=report.id,
            related_reports=related,
            likely_duplicate=bool(related),
        )

    @staticmethod
    def _same_category(left: str, right: str) -> bool:
        return left.strip().casefold() == right.strip().casefold()

    @classmethod
    def _distance_meters(
        cls, latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float
    ) -> float:
        lat_a, lat_b = radians(latitude_a), radians(latitude_b)
        delta_lat = radians(latitude_b - latitude_a)
        delta_lon = radians(longitude_b - longitude_a)
        haversine = (
            sin(delta_lat / 2) ** 2
            + cos(lat_a) * cos(lat_b) * sin(delta_lon / 2) ** 2
        )
        return cls.EARTH_RADIUS_METERS * 2 * asin(sqrt(min(1.0, haversine)))

    @staticmethod
    def _aware(value: datetime) -> datetime:
        if value.tzinfo is not None and value.utcoffset() is not None:
            return value
        return value.replace(tzinfo=timezone.utc)
