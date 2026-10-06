"""Behavior tests for deterministic temporal report analysis."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.models.entities import Hotspot, HotspotReport, HotspotTrend, Report, RiskLevel
from tests.test_reports import create_report


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def analyze(client: TestClient, **params: str) -> dict:
    authority(client)
    response = client.get("/api/v1/analytics/temporal", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def add_report(client: TestClient, timestamp: str, category: str = "Road Damage") -> dict:
    return create_report(client, issue_category=category, reported_at=timestamp)


def add_hotspot(client: TestClient, report_ids: list[str]) -> str:
    hotspot_id = uuid4()
    with client.testing_session_factory() as session:
        session.add(
            Hotspot(
                id=hotspot_id,
                name="Temporal test hotspot",
                center_latitude=28.6139,
                center_longitude=77.2090,
                report_count=len(report_ids),
                risk_score=Decimal("0"),
                risk_level=RiskLevel.LOW,
                trend=HotspotTrend.STABLE,
            )
        )
        for report_id in report_ids:
            session.add(
                HotspotReport(hotspot_id=hotspot_id, report_id=UUID(report_id))
            )
        session.commit()
    return str(hotspot_id)


def test_hour_day_date_and_time_of_day_aggregation(client: TestClient) -> None:
    add_report(client, "2026-09-08T06:00:00+00:00")
    add_report(client, "2026-09-08T12:00:00+00:00")
    add_report(client, "2026-09-08T17:00:00+00:00")
    add_report(client, "2026-09-08T22:00:00+00:00")

    body = analyze(
        client,
        **{
            "from": "2026-09-08T00:00:00+00:00",
            "to": "2026-09-14T23:59:59+00:00",
        },
    )

    assert body["total_reports"] == 4
    assert body["reports_by_hour"]["6"] == 1
    assert body["reports_by_hour"]["12"] == 1
    assert body["reports_by_hour"]["17"] == 1
    assert body["reports_by_hour"]["22"] == 1
    assert body["reports_by_day_of_week"]["Tuesday"] == 4
    assert body["reports_by_date"] == {"2026-09-08": 4}
    assert body["time_of_day"] == {
        "morning": 1,
        "afternoon": 1,
        "evening": 1,
        "night": 1,
    }


def test_peak_hour_and_weekday_are_reported(client: TestClient) -> None:
    for hour in (10, 10, 18):
        add_report(client, f"2026-09-09T{hour:02d}:00:00+00:00")

    body = analyze(
        client,
        **{
            "from": "2026-09-09T00:00:00+00:00",
            "to": "2026-09-15T23:59:59+00:00",
        },
    )

    assert body["peak_hour"] == 10
    assert body["peak_day_of_week"] == "Wednesday"


def test_current_previous_frequency_and_positive_change(client: TestClient) -> None:
    add_report(client, "2026-09-02T10:00:00+00:00")
    add_report(client, "2026-09-09T10:00:00+00:00")
    add_report(client, "2026-09-10T10:00:00+00:00")

    body = analyze(
        client,
        **{
            "from": "2026-09-09T00:00:00+00:00",
            "to": "2026-09-15T23:59:59+00:00",
            "window_days": "7",
        },
    )

    assert body["current_report_frequency"] == 2 / 7
    assert body["previous_report_frequency"] == 1 / 7
    assert body["frequency_change_percent"] == 100


def test_negative_change_and_zero_previous_baseline(client: TestClient) -> None:
    add_report(client, "2026-09-02T10:00:00+00:00")

    body = analyze(
        client,
        **{
            "from": "2026-09-09T00:00:00+00:00",
            "to": "2026-09-15T23:59:59+00:00",
        },
    )
    assert body["frequency_change_percent"] == -100

    empty_previous = analyze(
        client,
        **{
            "from": "2026-09-01T00:00:00+00:00",
            "to": "2026-09-07T23:59:59+00:00",
        },
    )
    assert empty_previous["previous_report_frequency"] == 0
    assert empty_previous["frequency_change_percent"] == 0


def test_category_and_hotspot_filters(client: TestClient) -> None:
    road = add_report(client, "2026-09-10T10:00:00+00:00")
    add_report(client, "2026-09-10T11:00:00+00:00", "Water Leakage")
    hotspot_id = add_hotspot(client, [road["id"]])

    category_body = analyze(
        client,
        category="Road Damage",
        **{
            "from": "2026-09-10T00:00:00+00:00",
            "to": "2026-09-10T23:59:59+00:00",
        },
    )
    hotspot_body = analyze(
        client,
        hotspot_id=hotspot_id,
        **{
            "from": "2026-09-10T00:00:00+00:00",
            "to": "2026-09-10T23:59:59+00:00",
        },
    )
    assert category_body["total_reports"] == 1
    assert hotspot_body["total_reports"] == 1


def test_empty_dataset_boundaries_and_timezone_are_safe(client: TestClient) -> None:
    body = analyze(
        client,
        **{
            "from": "2026-09-10T00:00:00+05:30",
            "to": "2026-09-16T23:59:59+05:30",
        },
    )
    assert body["total_reports"] == 0
    assert body["peak_hour"] is None
    assert body["peak_day_of_week"] is None

    boundary = add_report(client, "2026-09-10T00:00:00+00:00")
    boundary_body = analyze(
        client,
        **{
            "from": "2026-09-10T00:00:00+00:00",
            "to": "2026-09-10T00:00:00+00:00",
        },
    )
    assert boundary_body["total_reports"] == 1
    assert boundary["id"]


def test_invalid_ranges_missing_hotspot_and_citizen_rejection(client: TestClient) -> None:
    authority(client)
    invalid = client.get(
        "/api/v1/analytics/temporal",
        params={
            "from": "2026-09-11T00:00:00+00:00",
            "to": "2026-09-10T00:00:00+00:00",
        },
    )
    assert invalid.status_code == 422

    missing = client.get(
        "/api/v1/analytics/temporal",
        params={"hotspot_id": str(uuid4())},
    )
    assert missing.status_code == 404

    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )
    citizen = client.get("/api/v1/analytics/temporal")
    assert citizen.status_code == 403
