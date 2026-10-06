"""Deterministic, read-only candidate interventions for hotspots."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.entities import Hotspot, HotspotReport, Report
from app.schemas.recommendations import (
    RecommendationEvidence,
    RecommendationItem,
    RecommendationResponse,
)
from app.services.risk_service import RiskService


class RecommendationPersistenceError(Exception):
    """Raised when recommendation source data cannot be read."""


class RecommendationValidationError(Exception):
    """Raised when recommendation filters are invalid."""


class RecommendationService:
    CATEGORY_RULES = {
        "road damage": (
            "Inspect and repair damaged road surface",
            "repair",
        ),
        "garbage overflow": (
            "Schedule garbage collection and inspect overflow point",
            "schedule_collection",
        ),
        "water leakage": (
            "Inspect water line/leak source and arrange repair",
            "repair",
        ),
        "street light issue": (
            "Inspect street-light equipment and arrange repair/replacement",
            "replace",
        ),
    }
    GENERIC_ACTION = ("Perform a general public-space inspection", "inspect")

    def __init__(self, session: Session) -> None:
        self.session = session
        self.risk_service = RiskService(session)

    def analyze(
        self,
        hotspot_id: UUID,
        *,
        category: str | None = None,
        from_: datetime | None = None,
        to: datetime | None = None,
    ) -> RecommendationResponse:
        self._validate_range(from_, to)
        reports = self._load_reports(hotspot_id, category, from_, to)
        risk = self.risk_service.analyze(
            hotspot_id, category=category, from_=from_, to=to
        )
        evidence = RecommendationEvidence(
            risk_score=risk.risk_score,
            trend=risk.evidence_summary.trend,
            recurrence_level=risk.evidence_summary.recurrence_level,
            severity_index_percent=risk.evidence_summary.severity_index_percent,
            related_reports_count=risk.evidence_summary.related_reports_count,
        )
        if not reports:
            return RecommendationResponse(
                hotspot_id=hotspot_id,
                risk_score=risk.risk_score,
                risk_level=risk.risk_level,
                recommendations=[
                    RecommendationItem(
                        action="Monitor hotspot through routine public-space checks",
                        action_type="monitor",
                        priority="low",
                        category=category.strip() if category else None,
                        reason="No reports matched the selected filters, so only routine monitoring is suggested.",
                        evidence=evidence,
                    )
                ],
            )

        selected_category = self._selected_category(reports, category)
        action, action_type = self.CATEGORY_RULES.get(
            selected_category.casefold(), self.GENERIC_ACTION
        )
        recommendations = [
            RecommendationItem(
                action=action,
                action_type=action_type,
                priority=self._priority(risk.risk_score),
                category=selected_category,
                reason=self._primary_reason(
                    selected_category, risk.risk_score, risk.evidence_summary.trend
                ),
                evidence=evidence,
            )
        ]
        self._add_supporting_recommendations(recommendations, risk, evidence, selected_category)
        return RecommendationResponse(
            hotspot_id=hotspot_id,
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            recommendations=recommendations[:4],
        )

    def _load_reports(
        self,
        hotspot_id: UUID,
        category: str | None,
        from_: datetime | None,
        to: datetime | None,
    ) -> list[Report]:
        try:
            if self.session.get(Hotspot, hotspot_id) is None:
                raise LookupError("Hotspot not found")
            reports = list(
                self.session.scalars(
                    select(Report)
                    .join(HotspotReport, HotspotReport.report_id == Report.id)
                    .where(HotspotReport.hotspot_id == hotspot_id)
                )
            )
            normalized = category.strip().casefold() if category else None
            start = self._to_utc(from_) if from_ else None
            end = self._to_utc(to) if to else None
            return [
                report
                for report in reports
                if (normalized is None
                    or report.issue_category.strip().casefold() == normalized)
                and (start is None or start <= self._to_utc(report.reported_at))
                and (end is None or self._to_utc(report.reported_at) <= end)
            ]
        except LookupError:
            raise
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise RecommendationPersistenceError(
                "Could not retrieve recommendation reports"
            ) from exc

    @staticmethod
    def _selected_category(reports: list[Report], category: str | None) -> str:
        if category:
            return category.strip()
        counts = Counter(report.issue_category.strip() for report in reports)
        return sorted(counts, key=lambda value: (-counts[value], value.casefold(), value))[0]

    @staticmethod
    def _priority(score: float) -> str:
        if score >= 75:
            return "critical"
        if score >= 50:
            return "high"
        if score >= 25:
            return "moderate"
        return "low"

    @staticmethod
    def _primary_reason(category: str, score: float, trend: str) -> str:
        category_reason = f"{category} reports are linked to this hotspot"
        if trend == "increasing":
            return f"{category_reason}, and reporting activity is increasing (risk score {score:g})."
        return f"{category_reason}; the current explainable risk score is {score:g}."

    @classmethod
    def _add_supporting_recommendations(
        cls,
        recommendations: list[RecommendationItem],
        risk,
        evidence: RecommendationEvidence,
        category: str,
    ) -> None:
        component = risk.components.severity
        if component.available and component.percent >= 66.67:
            recommendations.append(
                RecommendationItem(
                    action="Prioritize field inspection",
                    action_type="inspect",
                    priority=cls._priority(risk.risk_score),
                    category=category,
                    reason=(
                        f"Recorded severity evidence is high "
                        f"(severity index {component.percent:g}%)."
                    ),
                    evidence=evidence,
                )
            )
        if risk.evidence_summary.trend == "increasing":
            recommendations.append(
                RecommendationItem(
                    action="Schedule prompt investigation and monitoring",
                    action_type="investigate",
                    priority=cls._priority(risk.risk_score),
                    category=category,
                    reason="Reporting activity is increasing across the selected analysis window.",
                    evidence=evidence,
                )
            )
        if risk.evidence_summary.recurrence_level == "high":
            recommendations.append(
                RecommendationItem(
                    action="Consider recurring inspection or permanent corrective action",
                    action_type="permanent_corrective_action",
                    priority=cls._priority(risk.risk_score),
                    category=category,
                    reason="Reports are active across multiple recurring analysis periods.",
                    evidence=evidence,
                )
            )
        if risk.evidence_summary.related_reports_count > 0:
            recommendations.append(
                RecommendationItem(
                    action="Check whether related reports describe the same underlying issue",
                    action_type="investigate",
                    priority=cls._priority(risk.risk_score),
                    category=category,
                    reason=(
                        f"{risk.evidence_summary.related_reports_count} related reports "
                        "provide corroborating reporting activity."
                    ),
                    evidence=evidence,
                )
            )

    @staticmethod
    def _validate_range(from_: datetime | None, to: datetime | None) -> None:
        for name, value in (("from", from_), ("to", to)):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise RecommendationValidationError(
                    f"{name} must include a timezone offset"
                )
        if from_ and to and RecommendationService._to_utc(to) < RecommendationService._to_utc(from_):
            raise RecommendationValidationError("to must be greater than or equal to from")

    @staticmethod
    def _to_utc(value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
