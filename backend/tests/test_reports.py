"""Behavior tests for the initial report API, independent of PostgreSQL access."""

from __future__ import annotations

from fastapi.testclient import TestClient
from app.api.dependencies import get_development_user_id
from app.models.entities import ReportStatusHistory


VALID_REPORT = {
    "issue_category": "Road Damage",
    "description": "A large pothole blocks part of the lane.",
    "latitude": "28.6139",
    "longitude": "77.2090",
    "reported_at": "2026-09-12T10:30:00+05:30",
    "severity": "high",
}


def create_report(client: TestClient, **overrides: str) -> dict:
    payload = {**VALID_REPORT, **overrides}
    response = client.post("/api/v1/reports", data=payload)
    assert response.status_code == 201, response.text
    return response.json()


def use_authority(client: TestClient) -> None:
    client.headers["X-Development-User-Id"] = str(client.authority_user_id)
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def use_citizen(client: TestClient) -> None:
    client.headers["X-Development-User-Id"] = str(client.development_user_id)
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )


def test_create_report_and_retrieve_it(client: TestClient) -> None:
    created = create_report(client)

    assert created["issue_category"] == "Road Damage"
    assert created["severity"] == "high"
    assert created["status"] == "pending"
    assert created["image_path"] is None

    response = client.get(f"/api/v1/reports/{created['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_missing_report_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/reports/11111111-1111-1111-1111-111111111111")
    assert response.status_code == 404
    assert response.json() == {"detail": "Report not found"}


def test_list_pagination_and_my_reports(client: TestClient) -> None:
    create_report(client, issue_category="Water Leakage")
    create_report(client, issue_category="Street Light Issue")

    response = client.get("/api/v1/reports?page=1&page_size=1")
    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 2
    assert page["page"] == 1
    assert page["page_size"] == 1
    assert page["total_pages"] == 2
    assert len(page["items"]) == 1

    my_response = client.get("/api/v1/reports/my")
    assert my_response.status_code == 200
    assert my_response.json()["total"] == 2


def test_invalid_latitude_and_longitude_are_rejected(client: TestClient) -> None:
    invalid_latitude = client.post("/api/v1/reports", data={**VALID_REPORT, "latitude": "91"})
    invalid_longitude = client.post("/api/v1/reports", data={**VALID_REPORT, "longitude": "181"})

    assert invalid_latitude.status_code == 422
    assert invalid_longitude.status_code == 422


def test_invalid_severity_and_status_filters_are_rejected(client: TestClient) -> None:
    invalid_severity = client.post("/api/v1/reports", data={**VALID_REPORT, "severity": "extreme"})
    invalid_status = client.get("/api/v1/reports?status=unknown")
    invalid_filter_severity = client.get("/api/v1/reports?severity=extreme")

    assert invalid_severity.status_code == 422
    assert invalid_status.status_code == 422
    assert invalid_filter_severity.status_code == 422


def test_authority_can_update_status_and_history_is_created(client: TestClient) -> None:
    created = create_report(client)
    authority_id = client.authority_user_id
    use_authority(client)

    response = client.patch(
        f"/api/v1/admin/reports/{created['id']}/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "resolved"
    with client.testing_session_factory() as session:
        history = session.query(ReportStatusHistory).one()
        assert history.report_id.hex == created["id"].replace("-", "")
        assert history.old_status.value == "pending"
        assert history.new_status.value == "resolved"
        assert history.changed_by == authority_id


def test_citizen_cannot_update_status(client: TestClient) -> None:
    created = create_report(client)
    use_citizen(client)

    response = client.patch(
        f"/api/v1/admin/reports/{created['id']}/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 403


def test_invalid_status_is_rejected(client: TestClient) -> None:
    created = create_report(client)
    use_authority(client)

    response = client.patch(
        f"/api/v1/admin/reports/{created['id']}/status",
        json={"status": "closed"},
    )

    assert response.status_code == 422


def test_status_update_missing_report_returns_404(client: TestClient) -> None:
    use_authority(client)

    response = client.patch(
        "/api/v1/admin/reports/11111111-1111-1111-1111-111111111111/status",
        json={"status": "resolved"},
    )

    assert response.status_code == 404


def test_authorization_matrix_citizen_and_admin(client: TestClient) -> None:
    """Verify authorization paths for Citizen A, Citizen B, and Admin."""
    from uuid import uuid4
    from app.core.security import create_access_token
    from app.models.entities import User, UserRole

    citizen_b_id = uuid4()
    with client.testing_session_factory() as session:
        session.add(
            User(
                id=citizen_b_id,
                name="Citizen B",
                email="citizen-b@example.test",
                password_hash="fake-hash",
                role=UserRole.CITIZEN,
            )
        )
        session.commit()

    # Citizen A creates Report A
    use_citizen(client)
    report_a = create_report(client, description="Report A by Citizen A")
    report_a_id = report_a["id"]

    # Citizen B creates Report B
    token_b = create_access_token(citizen_b_id, "citizen")
    res_b = client.post(
        "/api/v1/reports",
        data={**VALID_REPORT, "description": "Report B by Citizen B"},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 201
    report_b_id = res_b.json()["id"]

    # Tokens
    token_a = create_access_token(client.development_user_id, "citizen")
    token_admin = create_access_token(client.authority_user_id, "authority")

    # A. Citizen A -> own report (Expected: 200)
    res_a_own = client.get(
        f"/api/v1/reports/{report_a_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_own.status_code == 200
    assert res_a_own.json()["id"] == report_a_id

    # B. Citizen A -> Citizen B report (Expected: 403)
    res_a_other = client.get(
        f"/api/v1/reports/{report_b_id}",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert res_a_other.status_code == 403
    assert "Forbidden" in res_a_other.json()["detail"]

    # C. Admin -> Citizen A report (Expected: 200)
    res_admin_a = client.get(
        f"/api/v1/reports/{report_a_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res_admin_a.status_code == 200
    assert res_admin_a.json()["id"] == report_a_id

    # D. Admin -> Citizen B report (Expected: 200)
    res_admin_b = client.get(
        f"/api/v1/reports/{report_b_id}",
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert res_admin_b.status_code == 200
    assert res_admin_b.json()["id"] == report_b_id


def test_resolve_report_with_image_and_static_serving(client: TestClient) -> None:
    """Verify after-resolution image upload, persistence, and static image serving."""
    from io import BytesIO
    from app.core.security import create_access_token

    # 1. Citizen creates a report
    use_citizen(client)
    report = create_report(client, description="Pothole needs repair")
    report_id = report["id"]

    token_citizen = create_access_token(client.development_user_id, "citizen")
    token_admin = create_access_token(client.authority_user_id, "authority")

    # 2. Admin resolves the report with an after-resolution image and note
    fake_image = BytesIO(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb\x00C\x00")
    files = {"resolution_image": ("after_repair.jpg", fake_image, "image/jpeg")}
    data = {"resolution_note": "Pothole filled with asphalt and compacted."}

    resolve_res = client.post(
        f"/api/v1/admin/reports/{report_id}/resolve",
        headers={"Authorization": f"Bearer {token_admin}"},
        data=data,
        files=files,
    )
    assert resolve_res.status_code == 200, resolve_res.text
    resolved_body = resolve_res.json()
    assert resolved_body["status"] == "resolved"
    assert resolved_body["resolution_note"] == "Pothole filled with asphalt and compacted."
    assert resolved_body["resolution_image_path"] is not None
    assert resolved_body["resolution_image_path"].startswith("uploads/reports/")
    assert resolved_body["resolved_by_admin_name"] is not None
    assert resolved_body["resolved_at"] is not None

    image_path = resolved_body["resolution_image_path"]

    # 3. Verify static image serving (HTTP 200 + image content type)
    static_url = f"/{image_path}"
    static_res = client.get(static_url)
    assert static_res.status_code == 200, f"Static image not served at {static_url}"
    assert "image/" in static_res.headers.get("content-type", "")

    # 4. Verify Citizen retrieves the report with the resolution image path and note
    citizen_get_res = client.get(
        f"/api/v1/reports/{report_id}",
        headers={"Authorization": f"Bearer {token_citizen}"},
    )
    assert citizen_get_res.status_code == 200
    citizen_report = citizen_get_res.json()
    assert citizen_report["status"] == "resolved"
    assert citizen_report["resolution_image_path"] == image_path
    assert citizen_report["resolution_note"] == "Pothole filled with asphalt and compacted."
    assert citizen_report["resolved_by_admin_name"] is not None
    assert citizen_report["resolved_at"] is not None

