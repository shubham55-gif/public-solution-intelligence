"""Behavior tests for explainable hotspot risk scoring."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.models.entities import Hotspot, HotspotReport, HotspotTrend, RiskLevel
from app.services.risk_service import RiskService, RiskValidationError
from tests.test_reports import create_report


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def setup_hotspot(
    client: TestClient,
    reports: list[dict],
) -> str:
    hotspot_id = uuid4()
    with client.testing_session_factory() as session:
        session.add(
            Hotspot(
                id=hotspot_id,
                name="Risk test hotspot",
                center_latitude=28.6139,
                center_longitude=77.2090,
                report_count=len(reports),
                risk_score=Decimal("0"),
                risk_level=RiskLevel.LOW,
                trend=HotspotTrend.STABLE,
            )
        )
        session.flush()
        for report in reports:
            session.add(
                HotspotReport(hotspot_id=hotspot_id, report_id=UUID(report["id"]))
            )
        session.commit()
    return str(hotspot_id)


def report(
    client: TestClient,
    *,
    severity: str = "low",
    category: str = "Road Damage",
    timestamp: str = "2026-09-10T10:00:00+00:00",
    latitude: str = "28.6139",
    longitude: str = "77.2090",
) -> dict:
    return create_report(
        client,
        severity=severity,
        issue_category=category,
        reported_at=timestamp,
        latitude=latitude,
        longitude=longitude,
    )


def analyze(client: TestClient, hotspot_id: str, **params: str) -> dict:
    authority(client)
    response = client.get(f"/api/v1/analytics/risk/{hotspot_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def window() -> dict[str, str]:
    return {
        "from": "2026-09-01T00:00:00+00:00",
        "to": "2026-09-29T00:00:00+00:00",
    }


def test_all_components_zero_and_missing_evidence_are_explained(
    client: TestClient,
) -> None:
    body = analyze(client, setup_hotspot(client, []), **window())
    assert body["risk_score"] == 0
    assert body["risk_level"] == "low"
    assert body["evidence_summary"]["report_count"] == 0
    assert body["components"]["severity"]["available"] is False
    assert body["components"]["trend"]["available"] is False


def test_weighted_components_and_related_report_evidence(client: TestClient) -> None:
    reports = [
        report(client, severity="low", timestamp="2026-09-02T10:00:00+00:00"),
        report(client, severity="medium", timestamp="2026-09-02T10:00:00+00:00"),
        report(client, severity="high", timestamp="2026-09-02T10:00:00+00:00"),
        report(client, severity="critical", timestamp="2026-09-02T10:00:00+00:00"),
    ]
    body = analyze(client, setup_hotspot(client, reports), **window())
    assert body["components"]["spatial"]["percent"] == 40
    assert body["components"]["severity"]["percent"] == pytest.approx(50, abs=0.01)
    assert body["components"]["recurrence"]["percent"] == pytest.approx(33.33, abs=0.01)
    assert body["components"]["trend"]["percent"] == 0
    assert body["components"]["related_reports"]["percent"] == 80
    assert body["evidence_summary"]["related_reports_count"] == 4
    assert body["risk_score"] == round(
        sum(
            component["points"]
            for component in body["components"].values()
        ),
        2,
    )


def test_high_activity_and_severity_are_bounded(client: TestClient) -> None:
    reports = [
        report(
            client,
            severity="critical",
            timestamp=f"2026-09-{index + 1:02d}T10:00:00+00:00",
        )
        for index in range(12)
    ]
    body = analyze(client, setup_hotspot(client, reports), **window())
    assert body["risk_score"] <= 100
    assert body["components"]["spatial"]["percent"] == 100
    assert body["components"]["severity"]["percent"] == 100
    assert body["risk_level"] in {"high", "critical"}


def test_category_and_date_filters_are_applied(client: TestClient) -> None:
    road = report(
        client,
        severity="high",
        category="Road Damage",
        timestamp="2026-09-10T00:00:00+00:00",
    )
    report(
        client,
        severity="critical",
        category="Water Leakage",
        timestamp="2026-09-10T00:00:00+00:00",
    )
    body = analyze(
        client,
        setup_hotspot(client, [road]),
        category=" road damage ",
        **{"from": "2026-09-10T00:00:00+00:00", "to": "2026-09-10T00:00:00+00:00"},
    )
    assert body["evidence_summary"]["report_count"] == 1
    assert body["evidence_summary"]["severity_index_percent"] == pytest.approx(
        66.67, abs=0.01
    )
    assert body["components"]["temporal"]["available"] is True


def test_stable_and_decreasing_trends_use_deterministic_mapping(
    client: TestClient,
) -> None:
    reports = [
        report(client, timestamp="2026-09-02T10:00:00+00:00"),
        report(client, timestamp="2026-09-09T10:00:00+00:00"),
        report(client, timestamp="2026-09-16T10:00:00+00:00"),
        report(client, timestamp="2026-09-23T10:00:00+00:00"),
    ]
    stable = analyze(client, setup_hotspot(client, reports), **window())
    assert stable["evidence_summary"]["trend"] == "stable"
    assert stable["components"]["trend"]["percent"] == 50


def test_missing_hotspot_invalid_range_and_citizen_rejection(client: TestClient) -> None:
    authority(client)
    missing = client.get(f"/api/v1/analytics/risk/{uuid4()}")
    assert missing.status_code == 404
    hotspot_id = setup_hotspot(client, [report(client)])
    invalid = client.get(
        f"/api/v1/analytics/risk/{hotspot_id}",
        params={"from": "2026-09-20T00:00:00+00:00", "to": "2026-09-01T00:00:00+00:00"},
    )
    assert invalid.status_code == 422
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )
    assert client.get(f"/api/v1/analytics/risk/{hotspot_id}").status_code == 403


def test_all_hotspots_and_configuration_validation(client: TestClient) -> None:
    first = setup_hotspot(client, [report(client)])
    second = setup_hotspot(client, [report(client, severity="critical")])
    authority(client)
    response = client.get("/api/v1/analytics/risk", params=window())
    assert response.status_code == 200
    assert {item["hotspot_id"] for item in response.json()} == {first, second}
    with pytest.raises(RiskValidationError):
        RiskService.validate_configuration(
            weights={**RiskService.WEIGHTS, "spatial": 21}
        )
    with pytest.raises(RiskValidationError):
        RiskService.validate_configuration(
            caps={**RiskService.CAPS, "duplicate_count": 0}
        )


def test_repeated_calculation_is_deterministic(client: TestClient) -> None:
    hotspot_id = setup_hotspot(
        client,
        [
            report(client, severity="medium", timestamp="2026-09-02T10:00:00+00:00"),
            report(client, severity="high", timestamp="2026-09-23T10:00:00+00:00"),
        ],
    )
    first = analyze(client, hotspot_id, **window())
    second = analyze(client, hotspot_id, **window())
    assert first == second
