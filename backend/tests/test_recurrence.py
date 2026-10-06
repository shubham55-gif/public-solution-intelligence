"""Behavior tests for deterministic hotspot recurrence analysis."""

from __future__ import annotations

from datetime import datetime
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


def add_hotspot(client: TestClient, report_ids: list[str]) -> str:
    hotspot_id = uuid4()
    with client.testing_session_factory() as session:
        session.add(
            Hotspot(
                id=hotspot_id,
                name="Recurrence test hotspot",
                center_latitude=28.6139,
                center_longitude=77.2090,
                report_count=len(report_ids),
                risk_score=Decimal("0"),
                risk_level=RiskLevel.LOW,
                trend=HotspotTrend.STABLE,
            )
        )
        for report_id in report_ids:
            session.add(HotspotReport(hotspot_id=hotspot_id, report_id=UUID(report_id)))
        session.commit()
    return str(hotspot_id)


def setup_hotspot(client: TestClient, timestamps: list[str], category: str = "Road Damage") -> str:
    reports = [
        create_report(client, issue_category=category, reported_at=timestamp)
        for timestamp in timestamps
    ]
    return add_hotspot(client, [report["id"] for report in reports])


def analyze(client: TestClient, hotspot_id: str, **params: str) -> dict:
    authority(client)
    response = client.get(f"/api/v1/analytics/recurrence/{hotspot_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def window_params() -> dict[str, str]:
    return {
        "from": "2026-09-01T00:00:00+00:00",
        "to": "2026-09-28T00:00:00+00:00",
        "period_days": "7",
        "analysis_window_days": "28",
    }


def test_no_reports_is_none(client: TestClient) -> None:
    hotspot_id = setup_hotspot(client, [])

    body = analyze(client, hotspot_id, **window_params())

    assert body["total_reports"] == 0
    assert body["active_periods"] == 0
    assert body["recurrence_level"] == "none"
    assert body["recurrence_ratio"] == 0


def test_one_two_and_three_active_periods_levels(client: TestClient) -> None:
    one = setup_hotspot(client, ["2026-09-02T10:00:00+00:00"])
    two = setup_hotspot(
        client,
        ["2026-09-02T10:00:00+00:00", "2026-09-10T10:00:00+00:00"],
    )
    three = setup_hotspot(
        client,
        [
            "2026-09-02T10:00:00+00:00",
            "2026-09-10T10:00:00+00:00",
            "2026-09-20T10:00:00+00:00",
        ],
    )

    assert analyze(client, one, **window_params())["recurrence_level"] == "low"
    assert analyze(client, two, **window_params())["recurrence_level"] == "moderate"
    assert analyze(client, three, **window_params())["recurrence_level"] == "high"


def test_streak_ratio_and_current_period(client: TestClient) -> None:
    hotspot_id = setup_hotspot(
        client,
        [
            "2026-09-02T10:00:00+00:00",
            "2026-09-03T10:00:00+00:00",
            "2026-09-10T10:00:00+00:00",
        ],
    )

    body = analyze(client, hotspot_id, **window_params())

    assert body["observed_periods"] == 4
    assert body["active_periods"] == 2
    assert body["recurrence_ratio"] == 0.5
    assert body["longest_consecutive_periods"] == 2
    assert body["current_period_active"] is False
    assert [period["report_count"] for period in body["periods"]] == [2, 1, 0, 0]


def test_non_consecutive_periods_and_exact_boundary(client: TestClient) -> None:
    hotspot_id = setup_hotspot(
        client,
        [
            "2026-09-01T00:00:00+00:00",
            "2026-09-15T00:00:00+00:00",
            "2026-09-28T00:00:00+00:00",
        ],
    )

    body = analyze(client, hotspot_id, **window_params())

    assert body["active_periods"] == 3
    assert body["longest_consecutive_periods"] == 2
    assert body["current_period_active"] is True


def test_category_filter_and_empty_category(client: TestClient) -> None:
    road = create_report(
        client, issue_category="Road Damage", reported_at="2026-09-02T10:00:00+00:00"
    )
    water = create_report(
        client, issue_category="Water Leakage", reported_at="2026-09-10T10:00:00+00:00"
    )
    hotspot_id = add_hotspot(client, [road["id"], water["id"]])

    road_body = analyze(client, hotspot_id, category=" road damage ", **window_params())
    empty_body = analyze(client, hotspot_id, category="Garbage Overflow", **window_params())

    assert road_body["total_reports"] == 1
    assert empty_body["total_reports"] == 0
    assert empty_body["recurrence_level"] == "none"


def test_collection_endpoint_timezone_and_validation(client: TestClient) -> None:
    setup_hotspot(client, ["2026-09-02T10:00:00+05:30"])
    authority(client)
    response = client.get(
        "/api/v1/analytics/recurrence",
        params={"from": "2026-09-01T00:00:00+05:30", "to": "2026-09-28T00:00:00+05:30"},
    )
    assert response.status_code == 200
    assert response.json()[0]["total_reports"] == 1

    invalid = client.get(
        "/api/v1/analytics/recurrence",
        params={**window_params(), "period_days": "0"},
    )
    assert invalid.status_code == 422

    reversed_range = client.get(
        "/api/v1/analytics/recurrence",
        params={"from": "2026-09-28T00:00:00+00:00", "to": "2026-09-01T00:00:00+00:00"},
    )
    assert reversed_range.status_code == 422


def test_missing_hotspot_and_citizen_rejection(client: TestClient) -> None:
    authority(client)
    missing = client.get(
        f"/api/v1/analytics/recurrence/{uuid4()}",
        params=window_params(),
    )
    assert missing.status_code == 404

    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )
    citizen = client.get("/api/v1/analytics/recurrence")
    assert citizen.status_code == 403
