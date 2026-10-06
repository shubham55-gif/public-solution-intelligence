"""Behavior tests for authority intervention management."""

from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.models.entities import Hotspot


def create_hotspot(client: TestClient):
    with client.testing_session_factory() as session:
        hotspot = Hotspot(
            name="Test hotspot",
            center_latitude=28.6139,
            center_longitude=77.2090,
        )
        session.add(hotspot)
        session.commit()
        session.refresh(hotspot)
        return hotspot.id


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def create_intervention(client: TestClient, hotspot_id, **overrides: object) -> dict:
    authority(client)
    payload = {
        "hotspot_id": str(hotspot_id),
        "action_type": "Street lighting repair",
        "description": "Replace damaged lamps.",
        "assigned_unit": "Electrical Unit",
        "status": "planned",
        "started_at": "2026-09-14T10:00:00+05:30",
    }
    payload.update(overrides)
    response = client.post("/api/v1/interventions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_authority_can_create_intervention(client: TestClient) -> None:
    hotspot_id = create_hotspot(client)
    created = create_intervention(client, hotspot_id)

    assert created["hotspot_id"] == str(hotspot_id)
    assert created["status"] == "planned"
    assert created["assigned_unit"] == "Electrical Unit"


def test_citizen_cannot_create_intervention(client: TestClient) -> None:
    hotspot_id = create_hotspot(client)

    response = client.post(
        "/api/v1/interventions",
        json={
            "hotspot_id": str(hotspot_id),
            "action_type": "Cleanup",
            "description": "Clean area",
        },
    )

    assert response.status_code == 403


def test_missing_hotspot_returns_404(client: TestClient) -> None:
    authority(client)
    response = client.post(
        "/api/v1/interventions",
        json={
            "hotspot_id": str(uuid4()),
            "action_type": "Cleanup",
            "description": "Clean area",
        },
    )

    assert response.status_code == 404
    assert response.json() == {"detail": "Hotspot not found"}


def test_invalid_status_is_rejected(client: TestClient) -> None:
    hotspot_id = create_hotspot(client)
    authority(client)
    response = client.post(
        "/api/v1/interventions",
        json={
            "hotspot_id": str(hotspot_id),
            "action_type": "Cleanup",
            "description": "Clean area",
            "status": "cancelled",
        },
    )

    assert response.status_code == 422


def test_retrieve_and_update_intervention(client: TestClient) -> None:
    hotspot_id = create_hotspot(client)
    created = create_intervention(client, hotspot_id)

    retrieved = client.get(f"/api/v1/interventions/{created['id']}")
    assert retrieved.status_code == 200
    assert retrieved.json()["id"] == created["id"]

    updated = client.patch(
        f"/api/v1/interventions/{created['id']}",
        json={
            "status": "completed",
            "description": "Replacement completed.",
            "completed_at": "2026-09-14T12:00:00+05:30",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "completed"
    assert updated.json()["description"] == "Replacement completed."


def test_list_and_filter_interventions(client: TestClient) -> None:
    first_hotspot = create_hotspot(client)
    second_hotspot = create_hotspot(client)
    create_intervention(client, first_hotspot, status="in_progress")
    create_intervention(client, second_hotspot, status="completed")

    response = client.get(
        f"/api/v1/interventions?hotspot_id={first_hotspot}&status=in_progress"
    )

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert page["items"][0]["hotspot_id"] == str(first_hotspot)
    assert page["items"][0]["status"] == "in_progress"
