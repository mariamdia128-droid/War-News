from app.news.services.incident_details.casualty_merge_guard import guard_casualty_merge


def test_multi_location_aggregate_is_suppressed() -> None:
    result = guard_casualty_merge(
        incident_village_id=10, target_location_count=3,
        casualty_scope="bulletin_aggregate", incoming_status="aggregate_only",
        village_matches=[],
    )
    assert result.suppress
    assert result.reason == "aggregate_casualties_suppressed"


def test_trusted_count_for_this_incident_is_applied() -> None:
    result = guard_casualty_merge(
        incident_village_id=10, target_location_count=3,
        casualty_scope="bulletin_aggregate", incoming_status="aggregate_only",
        village_matches=[{"matched_village_id": 10, "village_role": "target", "deaths": 2}],
    )
    assert not result.suppress


def test_single_location_revision_is_applied() -> None:
    result = guard_casualty_merge(
        incident_village_id=10, target_location_count=1,
        casualty_scope="per_village_exact", incoming_status="exact",
        village_matches=[{"matched_village_id": 10, "village_role": "target"}],
    )
    assert not result.suppress
