"""Behavior tests for deterministic hotspot severity aggregation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.models.entities import Hotspot, HotspotReport, HotspotTrend, Report
from app.models.entities import RiskLevel
from tests.test_reports import create_report


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def create_hotspot(client: TestClient, reports: list[dict]) -> str:
    hotspot_id = uuid4()
    with client.testing_session_factory() as session:
        session.add(
            Hotspot(
                id=hotspot_id,
                name="Severity test hotspot",
                center_latitude=28.6139,
                center_longitude=77.2090,
                report_count=len(reports),
                risk_score=Decimal("0"),
                risk_level=RiskLevel.LOW,
                trend=HotspotTrend.STABLE,
            )
        )
        for report in reports:
            session.add(
                HotspotReport(hotspot_id=hotspot_id, report_id=UUID(report["id"]))
            )
        session.commit()
    return str(hotspot_id)


def setup(client: TestClient, severities: list[str], category: str = "Road Damage") -> str:
    reports = [
        create_report(
            client,
            issue_category=category,
            severity=severity,
            reported_at=f"2026-09-{index + 1:02d}T10:00:00+00:00",
        )
        for index, severity in enumerate(severities)
    ]
    return create_hotspot(client, reports)


def analyze(client: TestClient, hotspot_id: str, **params: str) -> dict:
    authority(client)
    response = client.get(f"/api/v1/analytics/severity/{hotspot_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_no_reports_returns_zero_baselines(client: TestClient) -> None:
    hotspot_id = setup(client, [])
    body = analyze(client, hotspot_id)
    assert body["total_reports"] == 0
    assert body["valid_severity_reports"] == 0
    assert body["invalid_severity_reports"] == 0
    assert body["weighted_severity_average"] == 0
    assert body["severity_index_percent"] == 0


@pytest.mark.parametrize(
    ("severity", "score", "index"),
    [("low", 1, 0), ("medium", 2, pytest.approx(33.3333, abs=0.01)),
     ("high", 3, pytest.approx(66.6667, abs=0.01)),
     ("critical", 4, 100)],
)
def test_single_severity_values(client: TestClient, severity: str, score: int, index) -> None:
    body = analyze(client, setup(client, [severity]))
    assert body["severity_counts"][severity] == 1
    assert body["weighted_severity_average"] == score
    assert body["severity_index_percent"] == index


def test_mixed_counts_percentages_and_weighted_average(client: TestClient) -> None:
    body = analyze(client, setup(client, ["low", "medium", "medium", "high", "critical"]))
    assert body["valid_severity_reports"] == 5
    assert body["severity_counts"] == {"low": 1, "medium": 2, "high": 1, "critical": 1}
    assert body["severity_percentages"]["medium"] == 40
    assert body["weighted_severity_average"] == 2.4
    assert body["severity_index_percent"] == pytest.approx(46.6667, abs=0.01)


def test_unknown_severity_is_counted_invalid_without_mapping(client: TestClient) -> None:
    hotspot_id = setup(client, ["low"])
    with client.testing_session_factory() as session:
        report = session.query(Report).one()
        report.severity = "urgent"
        session.commit()
    body = analyze(client, hotspot_id)
    assert body["total_reports"] == 1
    assert body["valid_severity_reports"] == 0
    assert body["invalid_severity_reports"] == 1
    assert sum(body["severity_counts"].values()) == 0


def test_category_and_time_filters_are_inclusive(client: TestClient) -> None:
    road = create_report(
        client, issue_category="Road Damage", severity="high",
        reported_at="2026-09-10T00:00:00+00:00",
    )
    water = create_report(
        client, issue_category="Water Leakage", severity="low",
        reported_at="2026-09-11T00:00:00+00:00",
    )
    hotspot_id = create_hotspot(client, [road, water])
    body = analyze(
        client,
        hotspot_id,
        category=" road damage ",
        **{"from": "2026-09-10T00:00:00+00:00", "to": "2026-09-10T00:00:00+00:00"},
    )
    assert body["total_reports"] == 1
    assert body["severity_counts"]["high"] == 1


def test_empty_category_multiple_hotspots_and_authorization(client: TestClient) -> None:
    first = setup(client, ["low"])
    second = setup(client, ["critical"], category="Water Leakage")
    empty = analyze(client, first, category="Garbage Overflow")
    assert empty["total_reports"] == 0
    assert empty["invalid_severity_reports"] == 0

    authority(client)
    listing = client.get("/api/v1/analytics/severity")
    assert listing.status_code == 200
    assert {item["hotspot_id"] for item in listing.json()} == {first, second}

    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )
    assert client.get("/api/v1/analytics/severity").status_code == 403


def test_missing_hotspot_invalid_range_and_timezone(client: TestClient) -> None:
    authority(client)
    missing = client.get(f"/api/v1/analytics/severity/{uuid4()}")
    assert missing.status_code == 404
    hotspot_id = setup(client, ["low"])
    reversed_range = client.get(
        f"/api/v1/analytics/severity/{hotspot_id}",
        params={"from": "2026-09-12T00:00:00+00:00", "to": "2026-09-01T00:00:00+00:00"},
    )
    assert reversed_range.status_code == 422
    naive = client.get(
        f"/api/v1/analytics/severity/{hotspot_id}",
        params={"from": "2026-09-01T00:00:00", "to": "2026-09-02T00:00:00+00:00"},
    )
    assert naive.status_code == 422
