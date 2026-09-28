from __future__ import annotations

from types import SimpleNamespace

from app.news.models import MessageStatus, RawMessage
from app.news.repositories.raw_message_repository import RawMessageRepository
from app.news.services.dedup.fast_path_eligibility import (
    ERROR_EXACT_HASH,
    ERROR_NO_VILLAGE,
    ERROR_UNMATCHED_CONDITION,
    HELD_UNMATCHED_PLACE,
)
from app.news.services.pipeline.errored_message_requeue import (
    PLAN_REEXTRACT,
    PLAN_REMATCH,
    PLAN_SKIP,
    classify_errored_message,
    reason_group,
)


def _message(**overrides):
    values = {
        "status": MessageStatus.error,
        "error_message": ERROR_UNMATCHED_CONDITION,
        "duplicate_of_id": None,
        "filter_result": {"verdict": "relevant"},
        # raw_message 30871
        "raw_text": "🔴 عاجل | مراسل المنار: غارة إسرائيلية استهدفت اطراف بلدة النبطية الفوقا",
        "extraction_result": {"is_relevant": True, "village": ["النبطية الفوقا"], "action_description": "غارة إسرائيلية"},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_condition_error_with_place_and_conflict_text_is_rematched() -> None:
    decision = classify_errored_message(_message(), has_live_incident=False)

    assert decision.plan == PLAN_REMATCH
    assert decision.reason_group == ERROR_UNMATCHED_CONDITION


def test_held_unmatched_place_is_rematched_after_alias_fix() -> None:
    decision = classify_errored_message(
        _message(status=MessageStatus.held_for_review, error_message=HELD_UNMATCHED_PLACE),
        has_live_incident=False,
    )

    assert decision.plan == PLAN_REMATCH


def test_civilian_fire_without_conflict_evidence_is_never_requeued() -> None:
    # raw_message 285: condition withheld on purpose (no military attribution).
    decision = classify_errored_message(
        _message(
            raw_text="حريق داخل منزل في البحصة – طرابلس Video",
            extraction_result={"is_relevant": True, "village": ["البحصة"], "action_description": None},
        ),
        has_live_incident=False,
    )

    assert (decision.plan, decision.skip_reason) == (PLAN_SKIP, "no_conflict_evidence")


def test_permanent_rejections_are_skipped() -> None:
    exact = classify_errored_message(_message(error_message=ERROR_EXACT_HASH), has_live_incident=False)
    air = classify_errored_message(
        _message(error_message="red_alert: routed to air_violations; not an incident"),
        has_live_incident=False,
    )
    irrelevant = classify_errored_message(
        _message(filter_result={"verdict": "not_relevant"}), has_live_incident=False
    )
    marked = classify_errored_message(
        _message(extraction_result={"is_relevant": False, "village": ["حولا"]}), has_live_incident=False
    )

    assert exact.skip_reason == "exact_hash_duplicate"
    assert air.skip_reason == "air_violation"
    assert irrelevant.skip_reason == "not_relevant"
    assert marked.skip_reason == "extraction_marked_irrelevant"


def test_message_with_live_incident_or_duplicate_link_is_skipped() -> None:
    assert classify_errored_message(_message(), has_live_incident=True).skip_reason == "has_live_incident"
    assert (
        classify_errored_message(_message(duplicate_of_id=7), has_live_incident=False).skip_reason
        == "duplicate_of_other_message"
    )


def test_no_place_extracted_needs_explicit_reextract_opt_in() -> None:
    # raw_message 31548: «رئيس بلدية كفررمان … ارتقاء 11 شهيداً» with village=null.
    message = _message(
        error_message=ERROR_NO_VILLAGE,
        raw_text="لبنان: رئيس بلدية كفررمان للميادين: ارتقاء 11 شهيداً وجرح 3 آخرين",
        extraction_result={"is_relevant": True, "village": None},
    )

    default = classify_errored_message(message, has_live_incident=False)
    opted_in = classify_errored_message(message, has_live_incident=False, include_no_place_reextract=True)

    assert (default.plan, default.skip_reason) == (PLAN_SKIP, "no_place_extracted")
    assert opted_in.plan == PLAN_REEXTRACT


def test_transient_extraction_failures_are_reextracted_others_are_not() -> None:
    disconnected = classify_errored_message(
        _message(error_message="Server disconnected without sending a response.", extraction_result=None),
        has_live_incident=False,
    )
    capped = classify_errored_message(
        _message(
            error_message="extraction: exceeded max retries (5) — last error: ReadTimeout: timed out",
            extraction_result=None,
        ),
        has_live_incident=False,
    )
    malformed = classify_errored_message(
        _message(error_message="Malformed extraction response.", extraction_result=None),
        has_live_incident=False,
    )

    assert disconnected.plan == PLAN_REEXTRACT
    assert capped.plan == PLAN_REEXTRACT
    assert malformed.skip_reason == "extraction_failed_non_transient"


def test_rejected_status_is_never_touched() -> None:
    decision = classify_errored_message(_message(status=MessageStatus.rejected), has_live_incident=False)

    assert decision.skip_reason == "not_errored_or_held"


def test_reason_group_collapses_numbers() -> None:
    assert reason_group("extraction: exceeded max retries (5) — last error: X") == (
        "extraction: exceeded max retries (#) — last error: X"
    )


class _DbStub:
    def __init__(self) -> None:
        self.added: list[object] = []

    def add(self, value: object) -> None:
        self.added.append(value)


def test_requeue_for_matching_resets_to_match_claim_state_with_audit() -> None:
    message = RawMessage(
        id=1,
        status=MessageStatus.error,
        error_message=ERROR_UNMATCHED_CONDITION,
        filter_result={"verdict": "relevant"},
        match_result={"condition_match_status": "unmatched"},
        match_retry_count=2,
        processing_claim_stage="fast_path",
    )
    repository = RawMessageRepository(_DbStub())  # type: ignore[arg-type]

    repository.requeue_for_matching(
        message, extraction_result={"action_description": "Bombs"}, audit={"plan": "rematch"}
    )

    assert message.status == MessageStatus.parsed
    assert message.match_result is None and message.matched_at is None
    assert message.match_retry_count == 0
    assert message.error_message is None and message.processing_claim_stage is None
    assert message.extraction_result == {"action_description": "Bombs"}
    history = message.filter_result["requeue_history"]
    assert history[-1]["plan"] == "rematch"
    assert history[-1]["from_error"] == ERROR_UNMATCHED_CONDITION
    assert message.filter_result["verdict"] == "relevant"


def test_requeue_for_extraction_clears_extraction_and_retry_count() -> None:
    message = RawMessage(
        id=2,
        status=MessageStatus.error,
        error_message="Server disconnected without sending a response.",
        extraction_result=None,
        extraction_retry_count=5,
        filter_result={"verdict": "relevant"},
    )
    repository = RawMessageRepository(_DbStub())  # type: ignore[arg-type]

    repository.requeue_for_extraction(message, audit={"plan": "reextract"})

    assert message.status == MessageStatus.parsed
    assert message.extraction_result is None
    assert message.extraction_retry_count == 0
    assert message.filter_result["requeue_history"][-1]["from_status"] == "error"
