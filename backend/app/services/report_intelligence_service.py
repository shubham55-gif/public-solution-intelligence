"""Deterministic orchestration of validated LLM and VLM report evidence and public safety intelligence."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import (
    HOTSPOT_DBSCAN_RADIUS_METERS,
    RISK_DUPLICATE_COUNT_CAP,
    RISK_DUPLICATE_WEIGHT,
    RISK_RECURRENCE_WEIGHT,
    RISK_SEVERITY_WEIGHT,
    RISK_SPATIAL_REPORT_COUNT_CAP,
    RISK_SPATIAL_WEIGHT,
    RISK_TEMPORAL_FREQUENCY_CAP,
    RISK_TEMPORAL_WEIGHT,
    RISK_TREND_WEIGHT,
    UPLOADS_DIR,
)
from app.models.entities import AIAnalysis, Hotspot, HotspotReport, Report, VlmValidationStatus
from app.schemas.orchestration import (
    DuplicateIntelligence,
    EvidenceConsistency,
    PriorityIntelligence,
    RecommendationIntelligence,
    RecurrenceIntelligence,
    RiskIntelligence,
    SpatialClusterIntelligence,
    TemporalIntelligence,
    TrendIntelligence,
    UnifiedImageAnalysis,
    UnifiedReportIntelligenceResponse,
    UnifiedTextAnalysis,
)
from app.services.duplicate_service import DuplicateService
from app.services.llm_service import LLMService
from app.services.recommendation_service import RecommendationService
from app.services.recurrence_service import RecurrenceService
from app.services.temporal_service import TemporalService
from app.services.trend_service import TrendService
from app.services.vlm_service import VLMService


class ReportNotFoundError(LookupError):
    """Raised when the requested report does not exist."""


class ReportIntelligenceService:
    """Coordinate existing model adapters and persist one result per report."""

    def __init__(
        self,
        session: Session,
        llm: LLMService,
        vlm: VLMService,
    ) -> None:
        self.session = session
        self.llm = llm
        self.vlm = vlm

    def get_analysis(self, report_id: UUID) -> UnifiedReportIntelligenceResponse | None:
        report = self.session.get(Report, report_id)
        if report is None:
            raise ReportNotFoundError
        if report.ai_analysis is None or not report.ai_analysis.llm_output:
            return None
        try:
            analysis = report.ai_analysis
            llm_data = json.loads(analysis.llm_output) if analysis.llm_output else {}
            vlm_data = json.loads(analysis.vlm_result) if analysis.vlm_result else {}
            text_analysis = UnifiedTextAnalysis(**llm_data.get("text_analysis", {}))
            image_analysis = UnifiedImageAnalysis(**vlm_data)
            consistency_dict = llm_data.get("evidence_consistency", {})
            if "consistency_status" not in consistency_dict:
                if consistency_dict.get("agreement") is True:
                    consistency_dict["consistency_status"] = "CONSISTENT"
                elif consistency_dict.get("agreement") is False:
                    consistency_dict["consistency_status"] = "INCONSISTENT"
                else:
                    consistency_dict["consistency_status"] = (
                        "UNCERTAIN" if image_analysis.available and image_analysis.validation_result == "UNCERTAIN" else "CONSISTENT"
                    )
            consistency = EvidenceConsistency(**consistency_dict)
            base_result = UnifiedReportIntelligenceResponse(
                report_id=report.id,
                issue_category=report.issue_category,
                analysis_available=text_analysis.available or image_analysis.available,
                text_analysis=text_analysis,
                image_analysis=image_analysis,
                overall_needs_review=llm_data.get("overall_needs_review", False),
                evidence_consistency=consistency,
                explanation=llm_data.get("explanation", ""),
            )
            return self._enrich_intelligence(report, base_result)
        except Exception:
            return None

    def analyze(self, report_id: UUID) -> UnifiedReportIntelligenceResponse:
        report = self.session.get(Report, report_id)
        if report is None:
            raise ReportNotFoundError

        try:
            text_result = self.llm.analyze_text(report.issue_category, report.description)
        except Exception as exc:
            text_result = self.llm._fallback(report.issue_category, f"LLM analysis unavailable: {exc}")

        text_analysis = UnifiedTextAnalysis(
            available=text_result.analysis_available,
            summary=text_result.summary,
            keywords=text_result.keywords,
            category_consistent=text_result.category_consistent,
            urgency_indicators=text_result.urgency_indicators,
            hazard_indicators=text_result.hazard_indicators,
            confidence=text_result.confidence,
            needs_review=text_result.needs_review,
            explanation=text_result.explanation,
        )

        image_bytes = self._load_image(report.image_path)
        if image_bytes is None:
            image_analysis = UnifiedImageAnalysis(
                available=False,
                validation_result="UNCERTAIN",
                image_consistent=False,
                confidence=0.0,
                needs_review=False,
                explanation="Visual evidence was unavailable because no usable image was supplied.",
            )
            image_category_consistent = None
            agreement = None
            consistency_status = "CONSISTENT" if text_analysis.category_consistent and text_analysis.available else "UNCERTAIN"
            image_reason = "No image was supplied, so visual evidence was unavailable."
            vlm_status = VlmValidationStatus.PENDING
        else:
            try:
                media_type = mimetypes.guess_type(report.image_path or "")[0] or "application/octet-stream"
                vlm_result = self.vlm.validate_image(
                    report.issue_category,
                    image_bytes,
                    media_type,
                )
            except Exception as exc:
                vlm_result = self.vlm._fallback(report.issue_category, f"VLM analysis unavailable: {exc}")

            image_analysis = UnifiedImageAnalysis(
                available=vlm_result.analysis_available,
                validation_result=vlm_result.validation_result,
                image_consistent=vlm_result.image_consistent,
                confidence=vlm_result.confidence,
                needs_review=vlm_result.needs_review,
                explanation=vlm_result.explanation,
            )
            image_category_consistent = (
                vlm_result.image_consistent if vlm_result.analysis_available else None
            )

            if not vlm_result.analysis_available:
                agreement = False
                consistency_status = "UNCERTAIN"
                image_reason = "Visual evidence requires human review because it is unavailable or failed validation."
                vlm_status = VlmValidationStatus.NEEDS_REVIEW
            elif text_analysis.category_consistent and vlm_result.validation_result == "YES":
                agreement = True
                consistency_status = "CONSISTENT"
                image_reason = "Visual evidence agrees with the selected category."
                vlm_status = (
                    VlmValidationStatus.VALIDATED
                    if not vlm_result.needs_review
                    else VlmValidationStatus.NEEDS_REVIEW
                )
            elif vlm_result.validation_result == "NO" or not text_analysis.category_consistent:
                agreement = False
                consistency_status = "INCONSISTENT"
                image_reason = "Visual evidence is inconsistent with the reported category."
                vlm_status = VlmValidationStatus.NEEDS_REVIEW
            else:  # UNCERTAIN
                agreement = False
                consistency_status = "UNCERTAIN"
                image_reason = "Visual evidence is uncertain or ambiguous and requires human review."
                vlm_status = VlmValidationStatus.NEEDS_REVIEW

        if image_bytes is None:
            overall_needs_review = (
                text_analysis.needs_review
                or not text_analysis.available
                or not text_analysis.category_consistent
            )
        else:
            overall_needs_review = (
                text_analysis.needs_review
                or not text_analysis.available
                or not text_analysis.category_consistent
                or not image_analysis.available
                or image_analysis.needs_review
                or image_analysis.validation_result != "YES"
                or consistency_status in ("INCONSISTENT", "UNCERTAIN")
            )

        analysis_available = text_analysis.available or image_analysis.available
        explanation = (
            f"Text analysis is {'available' if text_analysis.available else 'unavailable'}. "
            f"{image_reason} "
            f"{'Human review is required.' if overall_needs_review else 'The validated evidence is internally consistent.'}"
        )
        result = UnifiedReportIntelligenceResponse(
            report_id=report.id,
            issue_category=report.issue_category,
            analysis_available=analysis_available,
            text_analysis=text_analysis,
            image_analysis=image_analysis,
            overall_needs_review=overall_needs_review,
            evidence_consistency=EvidenceConsistency(
                text_category_consistent=text_analysis.category_consistent,
                image_category_consistent=image_category_consistent,
                agreement=agreement,
                consistency_status=consistency_status,
            ),
            explanation=explanation,
        )
        result = self._enrich_intelligence(report, result)
        self._persist(report, result, vlm_status)
        return result

    def _enrich_intelligence(
        self, report: Report, result: UnifiedReportIntelligenceResponse
    ) -> UnifiedReportIntelligenceResponse:
        # 1. Duplicate detection
        dup_service = DuplicateService(self.session)
        candidates = list(
            self.session.scalars(select(Report).where(Report.id != report.id))
        )
        dup_analysis = dup_service._analyze(report, candidates)
        if dup_analysis.likely_duplicate and dup_analysis.related_reports:
            first_rel = dup_analysis.related_reports[0]
            dup_info = DuplicateIntelligence(
                is_duplicate=True,
                duplicate_report_id=first_rel.report_id,
                duplicate_reason="; ".join(first_rel.reasons),
                duplicate_distance=first_rel.distance_meters,
                duplicate_time_difference=first_rel.time_difference_hours,
            )
            related_count = len(dup_analysis.related_reports)
        else:
            dup_info = DuplicateIntelligence(
                is_duplicate=False,
                duplicate_report_id=None,
                duplicate_reason=None,
                duplicate_distance=None,
                duplicate_time_difference=None,
            )
            related_count = 0

        # 2. Spatial / DBSCAN cluster
        hotspot_link = self.session.scalar(
            select(HotspotReport).where(HotspotReport.report_id == report.id)
        )
        if hotspot_link is not None:
            hotspot = self.session.get(Hotspot, hotspot_link.hotspot_id)
            if hotspot is not None:
                spatial_info = SpatialClusterIntelligence(
                    cluster_id=hotspot.id,
                    cluster_size=hotspot.report_count,
                    cluster_center_latitude=hotspot.center_latitude,
                    cluster_center_longitude=hotspot.center_longitude,
                    cluster_radius_meters=HOTSPOT_DBSCAN_RADIUS_METERS,
                    is_hotspot=True,
                )
            else:
                spatial_info = SpatialClusterIntelligence(is_hotspot=False)
        else:
            spatial_info = SpatialClusterIntelligence(is_hotspot=False)

        # 3. Temporal analysis
        temp_service = TemporalService(self.session)
        temp_resp = temp_service.analyze(
            hotspot_id=spatial_info.cluster_id if spatial_info.is_hotspot else None,
            category=report.issue_category if not spatial_info.is_hotspot else None,
            window_days=30,
        )
        if temp_resp.frequency_change_percent >= 50.0 or temp_resp.current_report_frequency >= 3.0:
            activity_level = "HIGH"
        elif temp_resp.frequency_change_percent >= 20.0 or temp_resp.current_report_frequency >= 1.0:
            activity_level = "MODERATE"
        elif temp_resp.current_report_frequency > 0:
            activity_level = "NORMAL"
        else:
            activity_level = "LOW"

        tod = temp_resp.time_of_day
        periods_list = [
            ("morning", tod.morning),
            ("afternoon", tod.afternoon),
            ("evening", tod.evening),
            ("night", tod.night),
        ]
        peak_part = max(periods_list, key=lambda x: x[1])[0]
        concentration = f"{temp_resp.peak_day_of_week or 'All week'} ({peak_part})"

        temporal_info = TemporalIntelligence(
            recent_report_count=temp_resp.total_reports,
            time_window="30d",
            recent_activity=activity_level,
            temporal_concentration=concentration,
        )

        # 4. Recurrence
        rec_service = RecurrenceService(self.session)
        rec_resp = (
            rec_service.analyze(
                spatial_info.cluster_id,
                category=report.issue_category,
            )
            if spatial_info.is_hotspot and spatial_info.cluster_id
            else None
        )

        if rec_resp is not None:
            is_rec = rec_resp.active_periods >= 2
            rec_count = rec_resp.active_periods
            rec_window = f"{rec_resp.analysis_window.days}d"
            rec_level_str = rec_resp.recurrence_level
            rec_reason = (
                f"Active across {rec_resp.active_periods} observation periods ({rec_resp.recurrence_level.upper()})."
                if is_rec
                else "No recurring pattern detected across analysis window."
            )
        else:
            is_rec = False
            rec_count = 1 if temporal_info.recent_report_count > 1 else 0
            rec_window = "30d"
            rec_level_str = "none"
            rec_reason = "No recurring pattern detected across analysis window."

        recurrence_info = RecurrenceIntelligence(
            is_recurring=is_rec,
            recurrence_count=rec_count,
            recurrence_window=rec_window,
            recurrence_reason=rec_reason,
        )

        # 5. Trend
        trend_service = TrendService(self.session)
        trend_resp = (
            trend_service.analyze(
                spatial_info.cluster_id, category=report.issue_category
            )
            if spatial_info.is_hotspot and spatial_info.cluster_id
            else None
        )
        if trend_resp is not None:
            raw_trend = trend_resp.trend
            if raw_trend == "increasing":
                trend_type = "INCREASING"
            elif raw_trend == "decreasing":
                trend_type = "DECREASING"
            elif raw_trend == "stable":
                trend_type = "STABLE"
            else:
                trend_type = "UNKNOWN"
            cur_cnt = round(
                trend_resp.second_half_average
                * max(1, trend_resp.observed_periods // 2)
            )
            base_cnt = round(
                trend_resp.first_half_average
                * max(1, trend_resp.observed_periods // 2)
            )
        else:
            trend_type = "UNKNOWN"
            cur_cnt = temporal_info.recent_report_count
            base_cnt = 0

        trend_info = TrendIntelligence(
            trend=trend_type,
            current_count=cur_cnt,
            baseline_count=base_cnt,
        )

        # 6. Severity (deterministic)
        raw_sev = (report.severity or "low").strip().casefold()
        if result.text_analysis.hazard_indicators or (
            result.text_analysis.urgency_indicators and raw_sev in ("low", "medium")
        ):
            sev_level = (
                "HIGH"
                if raw_sev == "medium"
                else ("MEDIUM" if raw_sev == "low" else raw_sev.upper())
            )
        else:
            sev_level = raw_sev.upper()
        if sev_level not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            sev_level = "LOW"

        # 7. Explainable Risk Score (0-100) & Risk Factors
        risk_factors: list[str] = []

        # Spatial points
        if spatial_info.is_hotspot and spatial_info.cluster_size:
            sp_ratio = min(
                spatial_info.cluster_size / RISK_SPATIAL_REPORT_COUNT_CAP, 1.0
            )
            sp_points = round(sp_ratio * RISK_SPATIAL_WEIGHT, 1)
            risk_factors.append(
                f"Clustered in hotspot with {spatial_info.cluster_size} reports (+{sp_points} pts)"
            )
        else:
            sp_points = 0.0

        # Temporal points
        t_freq = temporal_info.recent_report_count / 30.0
        t_ratio = min(t_freq / RISK_TEMPORAL_FREQUENCY_CAP, 1.0)
        t_points = round(t_ratio * RISK_TEMPORAL_WEIGHT, 1)
        if temporal_info.recent_report_count > 0:
            risk_factors.append(
                f"Recent reporting volume of {temporal_info.recent_report_count} reports in {temporal_info.time_window} (+{t_points} pts)"
            )

        # Recurrence points
        rec_ratio = {
            "none": 0.0,
            "low": 0.3333,
            "moderate": 0.6667,
            "high": 1.0,
        }.get(rec_level_str, 0.0)
        rec_points = round(rec_ratio * RISK_RECURRENCE_WEIGHT, 1)
        if rec_points > 0:
            risk_factors.append(
                f"Recurring issue active across {recurrence_info.recurrence_count} observation periods (+{rec_points} pts)"
            )

        # Trend points
        tr_ratio = {
            "INCREASING": 1.0,
            "STABLE": 0.5,
            "DECREASING": 0.0,
            "UNKNOWN": 0.0,
        }.get(trend_info.trend, 0.0)
        tr_points = round(tr_ratio * RISK_TREND_WEIGHT, 1)
        if tr_points > 0:
            risk_factors.append(
                f"Reporting activity trend is {trend_info.trend} (+{tr_points} pts)"
            )

        # Severity points
        sv_ratio = {
            "LOW": 0.0,
            "MEDIUM": 0.3333,
            "HIGH": 0.6667,
            "CRITICAL": 1.0,
        }.get(sev_level, 0.0)
        sv_points = round(sv_ratio * RISK_SEVERITY_WEIGHT, 1)
        risk_factors.append(f"{sev_level} severity classification (+{sv_points} pts)")

        # Related reports points
        if dup_info.is_duplicate or related_count > 0:
            rel_ratio = min(related_count / RISK_DUPLICATE_COUNT_CAP, 1.0)
            rel_points = round(
                max(rel_ratio, 0.5 if dup_info.is_duplicate else 0.0)
                * RISK_DUPLICATE_WEIGHT,
                1,
            )
            risk_factors.append(
                f"Corroborated by duplicate/nearby reports (+{rel_points} pts)"
            )
        else:
            rel_points = 0.0

        total_risk = round(
            min(
                100.0,
                max(
                    0.0,
                    sp_points
                    + t_points
                    + rec_points
                    + tr_points
                    + sv_points
                    + rel_points,
                ),
            ),
            1,
        )
        if total_risk >= 75.0:
            risk_lvl = "CRITICAL"
        elif total_risk >= 50.0:
            risk_lvl = "HIGH"
        elif total_risk >= 25.0:
            risk_lvl = "MEDIUM"
        else:
            risk_lvl = "LOW"

        risk_info = RiskIntelligence(
            risk_score=total_risk,
            risk_level=risk_lvl,
            risk_factors=risk_factors,
        )

        # 8. Deterministic Priority & Priority Reasons
        if total_risk >= 75.0 or sev_level == "CRITICAL":
            prio = "CRITICAL"
        elif (
            total_risk >= 50.0
            or sev_level == "HIGH"
            or (recurrence_info.is_recurring and spatial_info.is_hotspot)
        ):
            prio = "HIGH"
        elif (
            total_risk >= 25.0
            or sev_level == "MEDIUM"
            or recurrence_info.is_recurring
            or spatial_info.is_hotspot
        ):
            prio = "MEDIUM"
        else:
            prio = "LOW"

        prio_reasons = [
            f"Risk score is {total_risk} ({risk_lvl} level)",
            f"Severity evaluated as {sev_level}",
        ]
        if spatial_info.is_hotspot:
            prio_reasons.append(
                f"Part of active hotspot cluster (size: {spatial_info.cluster_size})"
            )
        if recurrence_info.is_recurring:
            prio_reasons.append(
                f"Recurring issue across {recurrence_info.recurrence_count} observation windows"
            )
        if trend_info.trend == "INCREASING":
            prio_reasons.append("Reporting activity trend is increasing")
        if dup_info.is_duplicate:
            prio_reasons.append("Duplicate report detected nearby")

        # 9. Authority Recommendation
        action_tuple = RecommendationService.CATEGORY_RULES.get(
            (report.issue_category or "").strip().casefold(),
            RecommendationService.GENERIC_ACTION,
        )
        rec_action = f"{action_tuple[0]} (Priority: {prio})"
        rec_type = action_tuple[1]

        reason_parts = []
        if total_risk >= 50.0:
            reason_parts.append(f"{risk_lvl} risk ({total_risk})")
        if sev_level in ("HIGH", "CRITICAL"):
            reason_parts.append(f"{sev_level} severity")
        if recurrence_info.is_recurring:
            reason_parts.append("recurring pattern")
        if spatial_info.is_hotspot:
            reason_parts.append(f"active cluster of {spatial_info.cluster_size} reports")
        if trend_info.trend == "INCREASING":
            reason_parts.append("increasing reporting trend")
        if dup_info.is_duplicate:
            reason_parts.append("corroborated by duplicate reports")
        if not reason_parts:
            reason_parts.append(f"standard protocol for {report.issue_category}")

        rec_reason = " + ".join(reason_parts) + "."

        recommendation_info = RecommendationIntelligence(
            recommended_action=rec_action,
            action_type=rec_type,
            reason=rec_reason,
            is_available=True,
        )

        result.duplicate = dup_info
        result.spatial = spatial_info
        result.temporal = temporal_info
        result.recurrence = recurrence_info
        result.trend = trend_info
        result.severity = sev_level
        result.risk = risk_info
        result.priority = prio
        result.priority_reasons = prio_reasons
        result.recommendation = recommendation_info

        return result

    @staticmethod
    def _load_image(image_path: str | None) -> bytes | None:
        if not image_path:
            return None
        raw_path = Path(image_path)
        uploads_root = UPLOADS_DIR.resolve()
        if raw_path.is_absolute():
            candidate = raw_path.resolve()
        else:
            parts = raw_path.parts
            if parts and parts[0].casefold() == "uploads":
                parts = parts[1:]
            candidate = UPLOADS_DIR.joinpath(*parts).resolve()
        if not candidate.is_relative_to(uploads_root) or not candidate.is_file():
            return None
        return candidate.read_bytes()

    def _persist(
        self,
        report: Report,
        result: UnifiedReportIntelligenceResponse,
        vlm_status: VlmValidationStatus,
    ) -> None:
        analysis = report.ai_analysis
        if analysis is None:
            analysis = AIAnalysis(report_id=report.id)
            self.session.add(analysis)
        analysis.llm_output = json.dumps(
            {
                "text_analysis": result.text_analysis.model_dump(mode="json"),
                "overall_needs_review": result.overall_needs_review,
                "evidence_consistency": result.evidence_consistency.model_dump(mode="json"),
                "explanation": result.explanation,
            }
        )
        analysis.extracted_category = report.issue_category
        analysis.time_context = report.reported_at.isoformat()
        analysis.severity_indicator = report.severity
        analysis.vlm_result = json.dumps(result.image_analysis.model_dump(mode="json"))
        analysis.vlm_validation_status = vlm_status
        self.session.commit()
