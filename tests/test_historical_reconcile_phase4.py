from scripts.backfill.historical_incident_reconcile.phase4_manual_review import (
    classify_no_direct,
)


def test_classify_no_direct_incident_provenance() -> None:
    assert (
        classify_no_direct(
            {"duplicate_links": [{"id": 1}], "merged_update_links": []}
        )
        == "confirmed_or_pending_duplicate_only"
    )
    assert (
        classify_no_direct(
            {
                "duplicate_links": [{"id": 1}],
                "merged_update_links": [{"id": 2}],
            }
        )
        == "duplicate_and_merge_update_only"
    )
    assert (
        classify_no_direct(
            {"duplicate_links": [], "merged_update_links": [{"id": 2}]}
        )
        == "merge_or_story_revision_only"
    )
