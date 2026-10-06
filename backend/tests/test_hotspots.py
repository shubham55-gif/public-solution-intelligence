"""Behavior tests for DBSCAN geographic hotspot detection."""

from __future__ import annotations

from datetime import datetime
from math import degrees
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.core.config import HOTSPOT_DBSCAN_RADIUS_METERS
from app.models.entities import Hotspot, HotspotReport, Report
from app.services.hotspot_service import HotspotService
from tests.test_reports import create_report


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def reports_at(client: TestClient, latitude: str, longitude: str, count: int) -> list[dict]:
    return [
        create_report(
            client,
            latitude=latitude,
            longitude=longitude,
            reported_at=f"2026-09-12T{10 + index:02d}:00:00+05:30",
        )
        for index in range(count)
    ]


def detect(client: TestClient):
    authority(client)
    response = client.post("/api/v1/analytics/hotspots/detect")
    assert response.status_code == 200, response.text
    return response.json()


def test_small_nearby_cluster_creates_one_hotspot(client: TestClient) -> None:
    reports_at(client, "28.6139", "77.2090", 3)

    result = detect(client)

    assert result["clusters_detected"] == 1
    assert result["reports_analyzed"] == 3
    assert result["reports_clustered"] == 3
    assert result["noise_reports"] == 0
    assert result["hotspots"][0]["report_count"] == 3


def test_distant_groups_create_separate_hotspots(client: TestClient) -> None:
    reports_at(client, "28.6139", "77.2090", 3)
    reports_at(client, "19.0760", "72.8777", 3)

    result = detect(client)

    assert result["clusters_detected"] == 2
    assert sorted(item["report_count"] for item in result["hotspots"]) == [3, 3]


def test_noise_points_do_not_create_hotspots(client: TestClient) -> None:
    reports_at(client, "28.6139", "77.2090", 2)
    create_report(client, latitude="19.0760", longitude="72.8777")

    result = detect(client)

    assert result["clusters_detected"] == 0
    assert result["reports_clustered"] == 0
    assert result["noise_reports"] == 3


def test_fewer_than_min_samples_produces_no_cluster(client: TestClient) -> None:
    reports_at(client, "28.6139", "77.2090", 2)

    result = detect(client)

    assert result["clusters_detected"] == 0
    assert result["hotspots"] == []


def test_duplicate_coordinates_are_handled(client: TestClient) -> None:
    reports_at(client, "28.6139", "77.2090", 3)

    result = detect(client)

    assert result["clusters_detected"] == 1
    assert result["hotspots"][0]["report_count"] == 3


def test_radius_boundary_is_inclusive(client: TestClient) -> None:
    longitude_delta = degrees(
        (HOTSPOT_DBSCAN_RADIUS_METERS - 0.01) / HotspotService.EARTH_RADIUS_METERS
    )
    reports_at(client, "0", "0", 2)
    create_report(
        client,
        latitude="0",
        longitude=str(longitude_delta),
        reported_at=datetime.fromisoformat("2026-09-12T12:00:00+05:30"),
    )

    result = detect(client)

    assert result["clusters_detected"] == 1
    assert result["hotspots"][0]["report_count"] == 3


def test_invalid_coordinates_are_skipped_safely(client: TestClient) -> None:
    reports_at(client, "28.6139", "77.2090", 3)
    assert not HotspotService._valid_coordinates(
        SimpleNamespace(latitude=float("nan"), longitude=77.2090)
    )
    assert not HotspotService._valid_coordinates(
        SimpleNamespace(latitude=91.0, longitude=77.2090)
    )

    result = detect(client)

    assert result["reports_analyzed"] == 3
    assert result["clusters_detected"] == 1


def test_relationships_are_not_duplicated_and_rerun_reuses_hotspot(
    client: TestClient,
) -> None:
    reports = reports_at(client, "28.6139", "77.2090", 3)

    first = detect(client)
    second = detect(client)

    assert first["hotspots"][0]["hotspot_id"] == second["hotspots"][0]["hotspot_id"]
    with client.testing_session_factory() as session:
        assert session.query(Hotspot).count() == 1
        assert session.query(HotspotReport).count() == len(reports)


def test_empty_dataset_returns_empty_summary(client: TestClient) -> None:
    result = detect(client)

    assert result == {
        "clusters_detected": 0,
        "reports_analyzed": 0,
        "reports_clustered": 0,
        "noise_reports": 0,
        "hotspots": [],
    }


def test_citizen_cannot_trigger_detection(client: TestClient) -> None:
    response = client.post("/api/v1/analytics/hotspots/detect")

    assert response.status_code == 403


def test_hotspot_list_returns_detected_hotspots(client: TestClient) -> None:
    reports_at(client, "28.6139", "77.2090", 3)
    detect(client)

    response = client.get("/api/v1/analytics/hotspots")

    assert response.status_code == 200
    assert len(response.json()) == 1
