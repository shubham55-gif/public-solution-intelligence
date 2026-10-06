"""Behavior tests for deterministic hotspot trend analysis."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.models.entities import Hotspot, HotspotReport, HotspotTrend, RiskLevel
from tests.test_reports import create_report


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def setup_hotspot(
    client: TestClient, timestamps: list[str], category: str = "Road Damage"
) -> str:
    hotspot_id = uuid4()
    with client.testing_session_factory() as session:
        session.add(
            Hotspot(
                id=hotspot_id,
                name="Trend test hotspot",
                center_latitude=28.6139,
                center_longitude=77.2090,
                report_count=len(timestamps),
                risk_score=Decimal("0"),
                risk_level=RiskLevel.LOW,
                trend=HotspotTrend.STABLE,
            )
        )
        session.flush()
        for timestamp in timestamps:
            report = create_report(client, issue_category=category, reported_at=timestamp)
            session.add(
                HotspotReport(hotspot_id=hotspot_id, report_id=UUID(report["id"]))
            )
        session.commit()
    return str(hotspot_id)


def analyze(client: TestClient, hotspot_id: str, **params: str) -> dict:
    authority(client)
    response = client.get(f"/api/v1/analytics/trend/{hotspot_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def window() -> dict[str, str]:
    return {
        "from": "2026-09-01T00:00:00+00:00",
        "to": "2026-09-29T00:00:00+00:00",
        "period_days": "7",
        "analysis_window_days": "28",
    }


def test_no_reports_and_insufficient_data(client: TestClient) -> None:
    hotspot = setup_hotspot(client, [])
    body = analyze(client, hotspot, **window())
    assert body["total_reports"] == 0
    assert body["trend"] == "insufficient_data"
    assert body["period_counts"] == [
        {"start": "2026-09-01T00:00:00Z", "end": "2026-09-08T00:00:00Z", "report_count": 0},
        {"start": "2026-09-08T00:00:00Z", "end": "2026-09-15T00:00:00Z", "report_count": 0},
        {"start": "2026-09-15T00:00:00Z", "end": "2026-09-22T00:00:00Z", "report_count": 0},
        {"start": "2026-09-22T00:00:00Z", "end": "2026-09-29T00:00:00Z", "report_count": 0},
    ]


def test_stable_counts(client: TestClient) -> None:
    timestamps = [
        "2026-09-02T10:00:00+00:00",
        "2026-09-09T10:00:00+00:00",
        "2026-09-16T10:00:00+00:00",
        "2026-09-23T10:00:00+00:00",
    ]
    body = analyze(client, setup_hotspot(client, timestamps), **window())
    assert body["period_counts"][0]["report_count"] == 1
    assert body["period_counts"][3]["report_count"] == 1
    assert body["first_half_average"] == 1
    assert body["second_half_average"] == 1
    assert body["trend_change_percent"] == 0
    assert body["trend"] == "stable"


def test_increasing_and_strong_increase(client: TestClient) -> None:
    timestamps = [
        "2026-09-02T10:00:00+00:00",
        "2026-09-09T10:00:00+00:00",
        "2026-09-16T10:00:00+00:00",
        "2026-09-16T11:00:00+00:00",
        "2026-09-23T10:00:00+00:00",
        "2026-09-23T11:00:00+00:00",
        "2026-09-23T12:00:00+00:00",
    ]
    body = analyze(client, setup_hotspot(client, timestamps), **window())
    assert body["trend"] == "increasing"
    assert body["trend_change_percent"] == 150


def test_decreasing_and_strong_decrease(client: TestClient) -> None:
    timestamps = [
        "2026-09-02T10:00:00+00:00",
        "2026-09-02T11:00:00+00:00",
        "2026-09-02T12:00:00+00:00",
        "2026-09-09T10:00:00+00:00",
        "2026-09-16T10:00:00+00:00",
        "2026-09-23T10:00:00+00:00",
    ]
    body = analyze(client, setup_hotspot(client, timestamps), **window())
    assert body["trend"] == "decreasing"
    assert body["trend_change_percent"] == -50


def test_zero_first_half_baseline_is_safe(client: TestClient) -> None:
    timestamps = [
        "2026-09-16T10:00:00+00:00",
        "2026-09-23T10:00:00+00:00",
    ]
    body = analyze(client, setup_hotspot(client, timestamps), **window())
    assert body["first_half_average"] == 0
    assert body["trend_change_percent"] == 0
    assert body["trend"] == "insufficient_data"


def test_category_filter_empty_category_and_boundary(client: TestClient) -> None:
    hotspot = setup_hotspot(
        client,
        ["2026-09-01T00:00:00+00:00"],
        category="Road Damage",
    )
    with client.testing_session_factory() as session:
        report = create_report(
            client,
            issue_category="Water Leakage",
            reported_at="2026-09-08T00:00:00+00:00",
        )
        session.add(HotspotReport(hotspot_id=UUID(hotspot), report_id=UUID(report["id"])))
        session.commit()

    road = analyze(client, hotspot, category=" road damage ", **window())
    empty = analyze(client, hotspot, category="Garbage Overflow", **window())
    assert road["total_reports"] == 1
    assert road["period_counts"][0]["report_count"] == 1
    assert empty["total_reports"] == 0


def test_all_hotspots_timezone_validation_and_citizen_rejection(client: TestClient) -> None:
    first = setup_hotspot(client, ["2026-09-02T10:00:00+05:30"])
    second = setup_hotspot(client, ["2026-09-23T10:00:00+05:30"])
    authority(client)
    response = client.get(
        "/api/v1/analytics/trend",
        params={"from": "2026-09-01T00:00:00+05:30", "to": "2026-09-29T00:00:00+05:30"},
    )
    assert response.status_code == 200
    assert {item["hotspot_id"] for item in response.json()} == {first, second}

    invalid = client.get(
        "/api/v1/analytics/trend",
        params={"period_days": "0"},
    )
    assert invalid.status_code == 422

    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )
    citizen = client.get("/api/v1/analytics/trend")
    assert citizen.status_code == 403


def test_missing_hotspot_and_reversed_range(client: TestClient) -> None:
    authority(client)
    missing = client.get(f"/api/v1/analytics/trend/{uuid4()}")
    assert missing.status_code == 404
    hotspot = setup_hotspot(client, [])
    reversed_range = client.get(
        f"/api/v1/analytics/trend/{hotspot}",
        params={
            "from": "2026-09-20T00:00:00+00:00",
            "to": "2026-09-01T00:00:00+00:00",
        },
    )
    assert reversed_range.status_code == 422
