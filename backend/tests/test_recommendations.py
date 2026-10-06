"""Behavior tests for deterministic hotspot recommendations."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_development_user_id
from app.models.entities import Hotspot, HotspotReport, HotspotTrend, RiskLevel
from tests.test_reports import create_report


def authority(client: TestClient) -> None:
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.authority_user_id
    )


def make_report(
    client: TestClient,
    *,
    category: str,
    severity: str = "medium",
    timestamp: str = "2026-09-10T10:00:00+00:00",
) -> dict:
    return create_report(
        client,
        issue_category=category,
        severity=severity,
        reported_at=timestamp,
    )


def make_hotspot(client: TestClient, reports: list[dict]) -> str:
    hotspot_id = uuid4()
    with client.testing_session_factory() as session:
        session.add(
            Hotspot(
                id=hotspot_id,
                name="Recommendation hotspot",
                center_latitude=28.6139,
                center_longitude=77.2090,
                report_count=len(reports),
                risk_score=Decimal("0"),
                risk_level=RiskLevel.LOW,
                trend=HotspotTrend.STABLE,
            )
        )
        session.flush()
        for item in reports:
            session.add(
                HotspotReport(hotspot_id=hotspot_id, report_id=UUID(item["id"]))
            )
        session.commit()
    return str(hotspot_id)


def analyze(client: TestClient, hotspot_id: str, **params: str) -> dict:
    authority(client)
    response = client.get(f"/api/v1/recommendations/{hotspot_id}", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def window() -> dict[str, str]:
    return {
        "from": "2026-09-01T00:00:00+00:00",
        "to": "2026-09-29T00:00:00+00:00",
    }


@pytest.mark.parametrize(
    ("category", "action_type"),
    [
        ("Road Damage", "repair"),
        ("Garbage Overflow", "schedule_collection"),
        ("Water Leakage", "repair"),
        ("Street Light Issue", "replace"),
    ],
)
def test_known_categories_map_to_controlled_actions(
    client: TestClient, category: str, action_type: str
) -> None:
    body = analyze(
        client,
        make_hotspot(client, [make_report(client, category=category)]),
        **window(),
    )
    primary = body["recommendations"][0]
    assert primary["category"] == category
    assert primary["action_type"] == action_type
    assert primary["priority"] == "low"


def test_unknown_category_uses_generic_inspection(client: TestClient) -> None:
    body = analyze(
        client,
        make_hotspot(client, [make_report(client, category="Unlisted Issue")]),
        **window(),
    )
    primary = body["recommendations"][0]
    assert primary["action_type"] == "inspect"
    assert primary["action"] == "Perform a general public-space inspection"


def test_priority_uses_existing_risk_score(client: TestClient) -> None:
    timestamps = (
        ["2026-09-02T10:00:00+00:00"]
        + ["2026-09-09T10:00:00+00:00"] * 2
        + ["2026-09-16T10:00:00+00:00"] * 3
        + ["2026-09-23T10:00:00+00:00"] * 6
    )
    reports = [
        make_report(client, category="Road Damage", severity="critical", timestamp=timestamp)
        for timestamp in timestamps
    ]
    body = analyze(client, make_hotspot(client, reports), **window())
    assert body["risk_score"] >= 75
    assert body["risk_level"] == "critical"
    assert body["recommendations"][0]["priority"] == "critical"


def test_evidence_rules_add_traceable_supporting_recommendations(
    client: TestClient,
) -> None:
    timestamps = [
        "2026-09-02T10:00:00+00:00",
        "2026-09-09T10:00:00+00:00",
        "2026-09-16T10:00:00+00:00",
        "2026-09-16T11:00:00+00:00",
        "2026-09-23T10:00:00+00:00",
        "2026-09-23T11:00:00+00:00",
        "2026-09-23T12:00:00+00:00",
    ]
    reports = [
        make_report(
            client,
            category="Road Damage",
            severity="critical",
            timestamp=timestamp,
        )
        for timestamp in timestamps
    ]
    body = analyze(client, make_hotspot(client, reports), **window())
    reasons = " ".join(item["reason"] for item in body["recommendations"])
    actions = {item["action_type"] for item in body["recommendations"]}
    evidence = body["recommendations"][0]["evidence"]
    assert evidence["trend"] == "increasing"
    assert evidence["recurrence_level"] == "high"
    assert "increasing" in reasons
    assert "severity" in reasons
    assert "investigate" in actions
    assert "permanent_corrective_action" in actions


def test_related_report_evidence_adds_corroboration_explanation(
    client: TestClient,
) -> None:
    reports = [
        make_report(
            client,
            category="Road Damage",
            timestamp="2026-09-10T10:00:00+00:00",
        ),
        make_report(
            client,
            category="Road Damage",
            timestamp="2026-09-10T11:00:00+00:00",
        ),
    ]
    body = analyze(client, make_hotspot(client, reports), **window())
    reasons = " ".join(item["reason"] for item in body["recommendations"])
    assert body["recommendations"][0]["evidence"]["related_reports_count"] > 0
    assert "related reports" in reasons


def test_no_reports_returns_only_low_priority_monitoring(client: TestClient) -> None:
    body = analyze(client, make_hotspot(client, []), **window())
    assert len(body["recommendations"]) == 1
    assert body["recommendations"][0]["action_type"] == "monitor"
    assert body["recommendations"][0]["priority"] == "low"


def test_category_and_date_filters_are_inclusive(client: TestClient) -> None:
    road = make_report(
        client,
        category="Road Damage",
        timestamp="2026-09-10T00:00:00+00:00",
    )
    water = make_report(
        client,
        category="Water Leakage",
        timestamp="2026-09-11T00:00:00+00:00",
    )
    hotspot_id = make_hotspot(client, [road, water])
    body = analyze(
        client,
        hotspot_id,
        category=" road damage ",
        **{"from": "2026-09-10T00:00:00+00:00", "to": "2026-09-10T00:00:00+00:00"},
    )
    assert body["recommendations"][0]["category"] == "road damage"
    assert body["risk_score"] > 0


def test_missing_hotspot_invalid_range_and_citizen_rejection(
    client: TestClient,
) -> None:
    authority(client)
    assert client.get(f"/api/v1/recommendations/{uuid4()}").status_code == 404
    hotspot_id = make_hotspot(client, [make_report(client, category="Road Damage")])
    invalid = client.get(
        f"/api/v1/recommendations/{hotspot_id}",
        params={
            "from": "2026-09-20T00:00:00+00:00",
            "to": "2026-09-01T00:00:00+00:00",
        },
    )
    assert invalid.status_code == 422
    client.app.dependency_overrides[get_development_user_id] = (
        lambda: client.development_user_id
    )
    assert client.get(f"/api/v1/recommendations/{hotspot_id}").status_code == 403


def test_all_hotspots_and_repeated_output_are_deterministic(
    client: TestClient,
) -> None:
    first = make_hotspot(client, [make_report(client, category="Road Damage")])
    second = make_hotspot(client, [make_report(client, category="Water Leakage")])
    first_result = analyze(client, first, **window())
    second_result = analyze(client, first, **window())
    assert first_result == second_result
    authority(client)
    response = client.get("/api/v1/recommendations", params=window())
    assert response.status_code == 200
    assert {item["hotspot_id"] for item in response.json()} == {first, second}


def test_recommendations_do_not_create_interventions(client: TestClient) -> None:
    hotspot_id = make_hotspot(client, [make_report(client, category="Road Damage")])
    analyze(client, hotspot_id, **window())
    with client.testing_session_factory() as session:
        assert session.query(Hotspot).one().interventions == []
