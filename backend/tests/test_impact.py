"""Behavior tests for transparent hotspot impact measurement."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.models.entities import Hotspot, HotspotReport, Report


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def create_hotspot(client: TestClient, risk_score: float = 40) -> object:
    with client.testing_session_factory() as session:
        hotspot = Hotspot(
            name="Impact hotspot",
            center_latitude=28.6139,
            center_longitude=77.2090,
            risk_score=risk_score,
        )
        session.add(hotspot)
        session.commit()
        session.refresh(hotspot)
        return hotspot.id


def create_intervention(client: TestClient, hotspot_id, **overrides: object) -> dict:
    authority(client)
    payload = {
        "hotspot_id": str(hotspot_id),
        "action_type": "Lighting repair",
        "description": "Repair lighting.",
        "status": "completed",
        "started_at": "2026-09-01T10:00:00+00:00",
        "completed_at": "2026-09-10T10:00:00+00:00",
    }
    payload.update(overrides)
    response = client.post("/api/v1/interventions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def add_report(client: TestClient, hotspot_id, reported_at: str) -> None:
    with client.testing_session_factory() as session:
        report = Report(
            user_id=client.development_user_id,
            issue_category="Road Damage",
            description="Test report",
            latitude=28.6139,
            longitude=77.2090,
            reported_at=datetime.fromisoformat(reported_at),
            severity="high",
        )
        session.add(report)
        session.flush()
        session.add(HotspotReport(hotspot_id=hotspot_id, report_id=report.id))
        session.commit()


def test_authority_can_create_snapshot(client: TestClient) -> None:
    hotspot_id = create_hotspot(client, risk_score=55)
    add_report(client, hotspot_id, "2026-09-14T10:00:00+00:00")
    authority(client)

    response = client.post(
        f"/api/v1/impact/{hotspot_id}/snapshot",
        json={"measured_at": "2026-09-14T12:00:00+00:00"},
    )

    assert response.status_code == 200
    assert response.json()["risk_score"] == 55
    assert response.json()["report_count"] == 1
    assert response.json()["report_frequency"] == 1 / 7


def test_citizen_cannot_create_snapshot(client: TestClient) -> None:
    hotspot_id = create_hotspot(client)
    response = client.post(f"/api/v1/impact/{hotspot_id}/snapshot", json={})
    assert response.status_code == 403


def test_missing_hotspot_snapshot_returns_404(client: TestClient) -> None:
    authority(client)
    response = client.post(f"/api/v1/impact/{uuid4()}/snapshot", json={})
    assert response.status_code == 404


def test_measurement_calculates_frequency_and_reduction(client: TestClient) -> None:
    hotspot_id = create_hotspot(client, risk_score=20)
    add_report(client, hotspot_id, "2026-08-31T12:00:00+00:00")
    add_report(client, hotspot_id, "2026-09-09T12:00:00+00:00")
    intervention = create_intervention(client, hotspot_id)

    response = client.post(
        f"/api/v1/impact/{hotspot_id}/measure",
        json={
            "intervention_id": intervention["id"],
            "before_measured_at": "2026-09-01T12:00:00+00:00",
            "after_measured_at": "2026-09-10T12:00:00+00:00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["before_report_frequency"] == pytest.approx(1 / 7, abs=0.0001)
    assert body["after_report_frequency"] == pytest.approx(1 / 7, abs=0.0001)
    assert body["report_reduction_percent"] == 0
    assert body["risk_reduction_percent"] == 0


def test_zero_baseline_does_not_divide_by_zero(client: TestClient) -> None:
    hotspot_id = create_hotspot(client, risk_score=0)
    intervention = create_intervention(client, hotspot_id)

    response = client.post(
        f"/api/v1/impact/{hotspot_id}/measure",
        json={
            "intervention_id": intervention["id"],
            "before_measured_at": "2026-09-01T12:00:00+00:00",
            "after_measured_at": "2026-09-10T12:00:00+00:00",
        },
    )

    assert response.status_code == 200
    assert response.json()["risk_reduction_percent"] == 0


def test_missing_intervention_and_mismatch_are_rejected(client: TestClient) -> None:
    first_hotspot = create_hotspot(client)
    second_hotspot = create_hotspot(client)
    intervention = create_intervention(client, first_hotspot)

    missing = client.post(
        f"/api/v1/impact/{first_hotspot}/measure",
        json={"intervention_id": str(uuid4())},
    )
    assert missing.status_code == 404

    mismatch = client.post(
        f"/api/v1/impact/{second_hotspot}/measure",
        json={
            "intervention_id": intervention["id"],
            "before_measured_at": "2026-09-01T00:00:00+00:00",
            "after_measured_at": "2026-09-10T00:00:00+00:00",
        },
    )
    assert mismatch.status_code == 422


def test_retrieve_latest_and_intervention_impact(client: TestClient) -> None:
    hotspot_id = create_hotspot(client)
    intervention = create_intervention(client, hotspot_id)
    measure = client.post(
        f"/api/v1/impact/{hotspot_id}/measure",
        json={
            "intervention_id": intervention["id"],
            "before_measured_at": "2026-09-01T00:00:00+00:00",
            "after_measured_at": "2026-09-10T00:00:00+00:00",
        },
    )
    assert measure.status_code == 200

    latest = client.get(f"/api/v1/impact/{hotspot_id}")
    by_intervention = client.get(
        f"/api/v1/impact/interventions/{intervention['id']}/impact"
    )
    assert latest.status_code == 200
    assert by_intervention.status_code == 200
    assert len(by_intervention.json()) == 1


def test_invalid_timestamps_are_rejected(client: TestClient) -> None:
    hotspot_id = create_hotspot(client)
    intervention = create_intervention(client, hotspot_id)
    response = client.post(
        f"/api/v1/impact/{hotspot_id}/measure",
        json={
            "intervention_id": intervention["id"],
            "before_measured_at": "2026-09-10T00:00:00+00:00",
            "after_measured_at": "2026-09-01T00:00:00+00:00",
        },
    )
    assert response.status_code == 422
