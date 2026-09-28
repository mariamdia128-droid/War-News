from app.news.services.pipeline.pipeline_llm_workers import (
    _final_action_description,
)
from app.llm.dtos import ExtractionResult, ExtractionBatchSummary
from app.llm.actions.extract_incidents_action import ExtractIncidentsAction
from app.news.models import MessageStatus
from datetime import datetime, timezone
from types import SimpleNamespace


def _result(action: str | None) -> ExtractionResult:
    return ExtractionResult(
        is_relevant=True,
        village=["المنصوري"],
        action_description=action,
        model="test",
        extracted_at=datetime.now(timezone.utc),
    )


class _Classifier:
    def __init__(self, action: str | None = "Bombs") -> None:
        self.action = action

    def extract_tier1(self, *, post_text: str, raw_message_id: int) -> ExtractionResult:
        return _result(self.action)


class _RawMessages:
    def __init__(self, text: str, cnrs_classification: dict | None = None) -> None:
        self.message = SimpleNamespace(
            id=1,
            raw_text=text,
            status=MessageStatus.parsed,
            extraction_result=None,
            cnrs_classification=cnrs_classification,
        )
        self.saved: ExtractionResult | None = None

    def get_pending_extraction_batch(self, limit: int):
        return [self.message]

    def save_extraction_result(self, *, message, result, audited_candidates):
        self.saved = result
        message.extraction_result = result.model_dump(mode="json")

    def rollback(self):
        raise AssertionError("rollback should not be called")


def test_supported_cnrs_action_wins_over_condition_evidence_heuristic() -> None:
    result = _final_action_description(
        "غارة جوية قرب موقع القصف المدفعي",
        "Artillery Shelling",
        {
            "include": True,
            "location": "النبطية",
            "event_subtype": "artillery",
        },
    )

    assert result == "Artillery Shelling"


def test_non_cnrs_action_still_uses_condition_evidence_heuristic() -> None:
    result = _final_action_description(
        "غارة جوية على البلدة",
        "Unknown",
        None,
    )

    assert result == "Bombs"


def test_sweep_extraction_path_relabels_mansouri_flare_bombs() -> None:
    text = "الطائرات الإسرائيلية تلقي قنابل مضيئة على بلدة المنصوري في قضاء صور"
    repo = _RawMessages(
        text,
        {"include": True, "event_subtype": "airstrike", "location": "المنصوري"},
    )

    summary = ExtractIncidentsAction(repo, _Classifier("Bombs")).execute(
        SimpleNamespace(batch_size=1)
    )

    assert isinstance(summary, ExtractionBatchSummary)
    assert repo.saved is not None
    assert repo.saved.action_description == "Flare Bomb"
    assert repo.saved.review_reason == "relabeled_by_flare_guard"


def test_sweep_extraction_path_relabels_haddatha_flare_bombs() -> None:
    text = "الاحتلال يلقي قنابل مضيئة في محيط حداثا."
    repo = _RawMessages(
        text,
        {"include": True, "event_subtype": "airstrike", "location": "حداثا"},
    )

    ExtractIncidentsAction(repo, _Classifier("Bombs")).execute(
        SimpleNamespace(batch_size=1)
    )

    assert repo.saved is not None
    assert repo.saved.action_description == "Flare Bomb"


def test_mixed_strike_and_flares_stays_bombs_but_needs_review() -> None:
    text = "غارة إسرائيلية استهدفت منزلا في المنصوري مع إلقاء قنابل مضيئة فوق البلدة"
    repo = _RawMessages(text, {"include": True, "event_subtype": "airstrike"})

    ExtractIncidentsAction(repo, _Classifier("Bombs")).execute(
        SimpleNamespace(batch_size=1)
    )

    assert repo.saved is not None
    assert repo.saved.action_description == "Bombs"
    assert repo.saved.needs_review is True
    assert "Flare wording appears together with strike language" in (
        repo.saved.review_reason or ""
    )


def test_plain_drops_bombs_without_qualifier_stays_bombs() -> None:
    result = _final_action_description(
        "الطيران الحربي يلقي قنابل على أطراف بلدة عيتا الشعب",
        "Bombs",
        None,
    )

    assert result == "Bombs"


def test_sound_and_smoke_bombs_do_not_resolve_to_plain_bombs() -> None:
    assert (
        _final_action_description("قنابل صوتية فوق مدينة صور", "Bombs", None)
        == "Sound Bombs"
    )
    assert (
        _final_action_description("إلقاء قنابل دخانية في محيط تلة علي الطاهر", "Bombs", None)
        == "Smoke Grenades"
    )


def test_incendiary_strike_with_damage_is_not_flare_bomb() -> None:
    result = _final_action_description(
        "قصف بقنابل حارقة تسبب بحريق في أطراف البلدة",
        "Bombs",
        None,
    )

    assert result == "Bombs"
