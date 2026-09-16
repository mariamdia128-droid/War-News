from uuid import UUID

from scripts.backfill.historical_incident_reconcile.phase2_village import (
    VillageCorrection,
    correction_plan,
)


def test_correction_plan_contains_old_new_diff_and_audit_tag() -> None:
    run_id = UUID("00000000-0000-0000-0000-000000000001")
    plan = correction_plan(
        VillageCorrection(
            incident_id="incident",
            raw_message_id=5,
            is_deleted=False,
            old_village_id=543,
            new_village_id=1152,
            raw_village_text="النبطية",
            qualifier_text="قضاء النبطية",
            old_status="matched",
            new_status="matched",
            old_confidence=0.8,
            new_confidence=0.9,
        ),
        run_id,
    )

    assert plan["operation"] == "update_village"
    assert plan["changes"]["village_id"] == {"old": 543, "new": 1152}
    assert plan["planned_incident_update_new_values"] == {
        "village_id": 1152,
        "backfill_operation": "village_correction",
        "raw_message_id": 5,
        "backfill_run_id": str(run_id),
    }
