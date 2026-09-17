from app.news.dtos import MatchResultDTO, MatchResultStatus, VillageMatchResult
from app.news.repositories.air_violation_repository import AirViolationRepository


def test_extracts_all_air_violation_location_entries_from_match_result() -> None:
    result = MatchResultDTO(
        village_matches=[
            VillageMatchResult(
                matched_village_id=7,
                village_match_status=MatchResultStatus.matched,
                village_confidence=1.0,
                village_review_required=False,
                raw_village_text="الناقورة",
                evidence_span="فوق الناقورة",
            ),
            VillageMatchResult(
                matched_village_id=8,
                village_match_status=MatchResultStatus.matched,
                village_confidence=1.0,
                village_review_required=False,
                raw_village_text="علما الشعب",
                evidence_span="فوق علما الشعب",
            ),
        ],
        any_village_low_confidence=False,
        matched_condition_id=35,
        condition_confidence=1.0,
        condition_match_status=MatchResultStatus.matched,
        condition_review_required=False,
        raw_condition_text="طيران حربي",
    )

    entries = AirViolationRepository._location_entries_from_match(result)

    assert [entry["village_id"] for entry in entries] == [7, 8]
