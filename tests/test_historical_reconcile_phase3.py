from uuid import UUID

from scripts.backfill.historical_incident_reconcile.phase3_toll import (
    TollIncident,
    effective_casualties,
    toll_plan,
)


def test_effective_casualties_matches_toll_projection_fallback() -> None:
    assert effective_casualties(
        {"total_deaths": 3, "deaths": 2, "injuries": 4}
    ) == (3, 4)
    assert effective_casualties(
        {"total_deaths": None, "deaths": 2, "total_injuries": None}
    ) == (2, None)


def test_toll_plan_preserves_rows_and_reports_surface_removal() -> None:
    run_id = UUID("00000000-0000-0000-0000-000000000001")
    plan = toll_plan(
        TollIncident(
            incident_id="incident",
            is_deleted=False,
            rows=(
                {"update_id": 10, "old_effective": {}, "new_effective": {}},
                {"update_id": 11, "old_effective": {}, "new_effective": {}},
            ),
        ),
        run_id,
    )

    assert plan["operation"] == "suppress_noop_toll_revisions"
    assert plan["surface_diff"] == {"old": [10, 11], "new": []}
    assert plan["database_row_action"] == "none"
    assert (
        plan["future_audit_payload_if_state_changes"]["backfill_run_id"]
        == str(run_id)
    )
