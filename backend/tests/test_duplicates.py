"""Behavior tests for deterministic duplicate/related-report analysis."""

from __future__ import annotations

from math import degrees

from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.core.config import (
    DUPLICATE_SPATIAL_THRESHOLD_METERS,
    DUPLICATE_TEMPORAL_THRESHOLD_HOURS,
)
from app.services.duplicate_service import DuplicateService
from tests.test_reports import create_report


def use_authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def test_same_category_nearby_report_is_related(client: TestClient) -> None:
    first = create_report(client, latitude="28.6139", longitude="77.2090")
    create_report(
        client,
        latitude="28.6140",
        longitude="77.2090",
        reported_at="2026-09-12T11:00:00+05:30",
    )
    use_authority(client)

    response = client.post(f"/api/v1/analytics/duplicates/check/{first['id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["likely_duplicate"] is True
    assert len(body["related_reports"]) == 1
    assert body["related_reports"][0]["same_category"] is True
    assert body["related_reports"][0]["reasons"]


def test_different_category_nearby_report_is_not_related(client: TestClient) -> None:
    first = create_report(client)
    create_report(client, issue_category="Garbage Overflow")
    use_authority(client)

    response = client.post(f"/api/v1/analytics/duplicates/check/{first['id']}")

    assert response.status_code == 200
    assert response.json()["likely_duplicate"] is False
    assert response.json()["related_reports"] == []


def test_same_category_distant_report_is_not_related(client: TestClient) -> None:
    first = create_report(client)
    create_report(client, latitude="28.7000", longitude="77.3000")
    use_authority(client)

    response = client.post(f"/api/v1/analytics/duplicates/check/{first['id']}")

    assert response.json()["likely_duplicate"] is False


def test_same_category_old_report_is_not_related(client: TestClient) -> None:
    first = create_report(client)
    create_report(client, reported_at="2026-09-13T12:00:00+05:30")
    use_authority(client)

    response = client.post(f"/api/v1/analytics/duplicates/check/{first['id']}")

    assert response.json()["likely_duplicate"] is False


def test_boundary_distance_and_time_are_inclusive(client: TestClient) -> None:
    first = create_report(client, latitude="0", longitude="0")
    longitude_delta = degrees(
        DUPLICATE_SPATIAL_THRESHOLD_METERS / DuplicateService.EARTH_RADIUS_METERS
    )
    create_report(
        client,
        latitude="0",
        longitude=str(longitude_delta),
        reported_at="2026-09-13T10:30:00+05:30",
    )
    use_authority(client)

    response = client.post(f"/api/v1/analytics/duplicates/check/{first['id']}")

    assert response.status_code == 200
    assert response.json()["likely_duplicate"] is True
    assert response.json()["related_reports"][0]["time_difference_hours"] <= (
        DUPLICATE_TEMPORAL_THRESHOLD_HOURS
    )


def test_no_related_reports_returns_empty_result(client: TestClient) -> None:
    first = create_report(client)
    use_authority(client)

    response = client.post(f"/api/v1/analytics/duplicates/check/{first['id']}")

    assert response.status_code == 200
    assert response.json() == {
        "report_id": first["id"],
        "related_reports": [],
        "likely_duplicate": False,
    }


def test_multiple_related_reports_and_admin_filters(client: TestClient) -> None:
    first = create_report(client)
    related_a = create_report(client, reported_at="2026-09-12T11:00:00+05:30")
    related_b = create_report(client, reported_at="2026-09-12T12:00:00+05:30")
    create_report(client, issue_category="Water Leakage")
    use_authority(client)

    check = client.post(f"/api/v1/analytics/duplicates/check/{first['id']}")
    assert {item["report_id"] for item in check.json()["related_reports"]} == {
        related_a["id"],
        related_b["id"],
    }

    listing = client.get(
        "/api/v1/analytics/duplicates"
        "?category=Road%20Damage"
        "&from=2026-09-12T00:00:00%2B05:30"
        "&to=2026-09-12T23:59:59%2B05:30"
    )
    assert listing.status_code == 200
    assert listing.json()


def test_missing_report_and_citizen_access_are_rejected(client: TestClient) -> None:
    use_authority(client)
    missing = client.post(
        "/api/v1/analytics/duplicates/check/11111111-1111-1111-1111-111111111111"
    )
    assert missing.status_code == 404

    report = create_report(client)
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )
    citizen = client.post(f"/api/v1/analytics/duplicates/check/{report['id']}")
    assert citizen.status_code == 403
