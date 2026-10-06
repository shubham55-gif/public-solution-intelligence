"""DBSCAN-based geographic hotspot detection and persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from math import isfinite, radians
from uuid import UUID, uuid4

import numpy as np
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from sklearn.cluster import DBSCAN

from app.core.config import HOTSPOT_DBSCAN_MIN_SAMPLES, HOTSPOT_DBSCAN_RADIUS_METERS
from app.models.entities import (
    Hotspot,
    HotspotReport,
    HotspotTrend,
    Report,
    RiskLevel,
)
from app.schemas.hotspots import HotspotDetectionResponse, HotspotSummary


class HotspotPersistenceError(Exception):
    """Raised when hotspot detection cannot be persisted."""


class HotspotService:
    EARTH_RADIUS_METERS = 6_371_000

    def __init__(
        self,
        session: Session,
        *,
        radius_meters: float = HOTSPOT_DBSCAN_RADIUS_METERS,
        min_samples: int = HOTSPOT_DBSCAN_MIN_SAMPLES,
    ) -> None:
        if radius_meters <= 0 or not isfinite(radius_meters):
            raise ValueError("radius_meters must be a positive finite value")
        if min_samples < 1:
            raise ValueError("min_samples must be positive")
        self.session = session
        self.radius_meters = radius_meters
        self.min_samples = min_samples

    def detect(self) -> HotspotDetectionResponse:
        try:
            reports = list(self.session.scalars(select(Report)))
            valid_reports = [report for report in reports if self._valid_coordinates(report)]
            if not valid_reports:
                return HotspotDetectionResponse(
                    clusters_detected=0,
                    reports_analyzed=0,
                    reports_clustered=0,
                    noise_reports=0,
                    hotspots=[],
                )

            coordinates = np.radians(
                [[report.latitude, report.longitude] for report in valid_reports]
            )
            labels = DBSCAN(
                eps=self.radius_meters / self.EARTH_RADIUS_METERS,
                min_samples=self.min_samples,
                metric="haversine",
                algorithm="ball_tree",
            ).fit_predict(coordinates)

            clusters: dict[int, list[Report]] = {}
            noise_reports = 0
            for report, label in zip(valid_reports, labels):
                if label == -1:
                    noise_reports += 1
                else:
                    clusters.setdefault(int(label), []).append(report)

            summaries = [
                self._persist_cluster(cluster_reports)
                for _, cluster_reports in sorted(clusters.items())
            ]
            self.session.commit()
            return HotspotDetectionResponse(
                clusters_detected=len(summaries),
                reports_analyzed=len(valid_reports),
                reports_clustered=sum(item.report_count for item in summaries),
                noise_reports=noise_reports,
                hotspots=summaries,
            )
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise HotspotPersistenceError("Could not persist hotspot detection") from exc
        except Exception:
            self.session.rollback()
            raise

    def list_hotspots(self) -> list[HotspotSummary]:
        try:
            hotspots = list(self.session.scalars(select(Hotspot).order_by(Hotspot.created_at)))
            return [
                HotspotSummary(
                    hotspot_id=hotspot.id,
                    latitude=hotspot.center_latitude,
                    longitude=hotspot.center_longitude,
                    report_count=hotspot.report_count,
                )
                for hotspot in hotspots
            ]
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise HotspotPersistenceError("Could not retrieve hotspots") from exc

    def _persist_cluster(self, reports: list[Report]) -> HotspotSummary:
        report_ids = {report.id for report in reports}
        hotspot = self._find_matching_hotspot(report_ids)
        latitude = sum(report.latitude for report in reports) / len(reports)
        longitude = sum(report.longitude for report in reports) / len(reports)
        if hotspot is None:
            hotspot = Hotspot(
                id=uuid4(),
                name=f"Detected hotspot {uuid4()}",
                center_latitude=latitude,
                center_longitude=longitude,
                report_count=len(reports),
                risk_score=Decimal("0"),
                risk_level=RiskLevel.LOW,
                trend=HotspotTrend.STABLE,
            )
            self.session.add(hotspot)
            self.session.flush()
        else:
            hotspot.center_latitude = latitude
            hotspot.center_longitude = longitude
            hotspot.report_count = len(reports)
            hotspot.updated_at = datetime.now(timezone.utc)

        existing_ids = {link.report_id for link in hotspot.report_links}
        for report in reports:
            if report.id not in existing_ids:
                self.session.add(HotspotReport(hotspot_id=hotspot.id, report_id=report.id))
        return HotspotSummary(
            hotspot_id=hotspot.id,
            latitude=latitude,
            longitude=longitude,
            report_count=len(reports),
        )

    def _find_matching_hotspot(self, report_ids: set[UUID]) -> Hotspot | None:
        for hotspot in self.session.scalars(select(Hotspot)):
            if {link.report_id for link in hotspot.report_links} == report_ids:
                return hotspot
        return None

    @staticmethod
    def _valid_coordinates(report: Report) -> bool:
        return (
            report.latitude is not None
            and report.longitude is not None
            and isfinite(report.latitude)
            and isfinite(report.longitude)
            and -90 <= report.latitude <= 90
            and -180 <= report.longitude <= 180
        )
