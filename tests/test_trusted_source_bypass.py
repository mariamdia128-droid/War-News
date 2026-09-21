from __future__ import annotations

from types import SimpleNamespace

import pytest

import app.sources.models  # noqa: F401
from app.llm.actions.filter_relevance_action import (
    NON_LEBANON_LOCATION_BACKEND,
    TRUSTED_SOURCE_BACKEND,
    TRUSTED_SOURCE_REASONING,
    FilterRelevanceAction,
)
from app.llm.dtos import (
    ClassificationResultDTO,
    ClassificationVerdict,
    FilterPendingMessagesData,
)
from app.news.models import MessageStatus


class _RepoStub:
    def __init__(self, messages: list) -> None:
        self.messages = messages
        self.saved: list[dict] = []
        self.rollbacks = 0

    def get_pending_unfiltered_batch(self, limit: int):
        return self.messages[:limit]

    def save_filter_result(self, **kwargs) -> None:
        self.saved.append(kwargs)

    def rollback(self) -> None:
        self.rollbacks += 1


class _KeywordStub:
    def __init__(self, *, has_keywords: bool = True) -> None:
        self.has_keywords = has_keywords
        self.calls: list[str] = []

    def has_candidate_keywords(self, text: str) -> bool:
        self.calls.append(text)
        return self.has_keywords


class _ClassifierStub:
    def __init__(self) -> None:
        self.calls: list[list] = []

    async def classify_batch(self, messages):
        self.calls.append(list(messages))
        return [
            ClassificationResultDTO(
                raw_message_id=message.id,
                verdict=ClassificationVerdict.relevant,
                confidence=0.9,
                reasoning="llm",
                backend="local_llm",
            )
            for message in messages
        ]


def _message(
    message_id: int,
    *,
    trusted: bool | None = None,
    source_id: int = 3,
    source_name: str = "CNRS Webhook",
    cnrs_classification: dict | None = None,
    text: str = "غارة إسرائيلية على أطراف بلدة.",
):
    config: dict = {}
    if trusted is True:
        config = {"trusted": True}
    elif trusted is False:
        config = {"trusted": False}
    source = SimpleNamespace(id=source_id, name=source_name, config=config)
    return SimpleNamespace(
        id=message_id,
        raw_text=text,
        cnrs_classification=cnrs_classification,
        source=source,
        status=MessageStatus.pending,
        filter_result=None,
    )


@pytest.mark.asyncio
async def test_trusted_source_skips_classifier_and_marks_parsed() -> None:
    message = _message(11, trusted=True, cnrs_classification={"include": False})
    repo = _RepoStub([message])
    keyword = _KeywordStub(has_keywords=True)
    classifier = _ClassifierStub()
    action = FilterRelevanceAction(repo, classifier, keyword)

    summary = await action.execute_async(FilterPendingMessagesData(batch_size=10))

    assert summary.processed == 1
    assert summary.relevant == 1
    assert summary.classifier_calls_made == 0
    assert classifier.calls == []
    assert keyword.calls == []
    saved = repo.saved[0]
    assert saved["new_status"] == MessageStatus.parsed
    assert saved["result"].backend == TRUSTED_SOURCE_BACKEND
    assert saved["result"].reasoning == TRUSTED_SOURCE_REASONING
    assert saved["result"].verdict == ClassificationVerdict.relevant


@pytest.mark.asyncio
async def test_untrusted_source_still_uses_cnrs_payload() -> None:
    message = _message(12, trusted=False, cnrs_classification={"include": True})
    repo = _RepoStub([message])
    keyword = _KeywordStub()
    classifier = _ClassifierStub()
    action = FilterRelevanceAction(repo, classifier, keyword)

    summary = await action.execute_async(FilterPendingMessagesData(batch_size=10))

    assert summary.processed == 1
    assert summary.relevant == 1
    assert summary.classifier_calls_made == 0
    assert classifier.calls == []
    assert keyword.calls == []
    assert repo.saved[0]["result"].backend == "cnrs_provided"


@pytest.mark.asyncio
async def test_untrusted_source_without_keywords_is_rejected() -> None:
    message = _message(13, text="بيان سياسي لا علاقة له.")
    repo = _RepoStub([message])
    keyword = _KeywordStub(has_keywords=False)
    classifier = _ClassifierStub()
    action = FilterRelevanceAction(repo, classifier, keyword)

    summary = await action.execute_async(FilterPendingMessagesData(batch_size=10))

    assert summary.rejected == 1
    assert summary.auto_rejected_by_keyword == 1
    assert classifier.calls == []
    assert repo.saved[0]["new_status"] == MessageStatus.rejected


@pytest.mark.asyncio
async def test_west_bank_bulletin_is_rejected_even_with_matching_village_name() -> None:
    """Recon: "منطقة العين، غربي رام الله" (Ramallah, West Bank) was
    materialized as a Lebanon incident because "العين" also happens to be a
    real Lebanese village name. The stated location must reject it before
    extraction ever sees the text, regardless of what village name matches.
    """
    message = _message(
        15,
        text=(
            "شاهد | لحظة فرار المستوطنين واختبائهم عقب إطلاق نار في منطقة "
            "العين، غربي رام الله. #الميادين"
        ),
    )
    repo = _RepoStub([message])
    keyword = _KeywordStub(has_keywords=True)
    classifier = _ClassifierStub()
    action = FilterRelevanceAction(repo, classifier, keyword)

    summary = await action.execute_async(FilterPendingMessagesData(batch_size=10))

    assert summary.rejected == 1
    assert classifier.calls == []
    assert keyword.calls == []
    assert repo.saved[0]["result"].backend == NON_LEBANON_LOCATION_BACKEND
    assert repo.saved[0]["result"].verdict == ClassificationVerdict.not_relevant


@pytest.mark.asyncio
async def test_west_bank_bulletin_overrides_trusted_source() -> None:
    message = _message(
        16,
        trusted=True,
        text="اشتباكات في الضفة الغربية عقب مداهمة قوات الاحتلال لمخيم جنين.",
    )
    repo = _RepoStub([message])
    action = FilterRelevanceAction(repo, _ClassifierStub(), _KeywordStub())

    summary = await action.execute_async(FilterPendingMessagesData(batch_size=10))

    assert summary.rejected == 1
    assert summary.relevant == 0
    assert repo.saved[0]["result"].backend == NON_LEBANON_LOCATION_BACKEND


@pytest.mark.asyncio
async def test_west_bank_bulletin_overrides_cnrs_include_true() -> None:
    message = _message(
        17,
        cnrs_classification={"include": True},
        text="قوات الاحتلال تعتقل شابا من مدينة نابلس خلال مداهمة فجرية.",
    )
    repo = _RepoStub([message])
    action = FilterRelevanceAction(repo, _ClassifierStub(), _KeywordStub())

    summary = await action.execute_async(FilterPendingMessagesData(batch_size=10))

    assert summary.rejected == 1
    assert repo.saved[0]["result"].backend == NON_LEBANON_LOCATION_BACKEND


@pytest.mark.asyncio
async def test_untrusted_source_with_keywords_calls_classifier() -> None:
    message = _message(14)
    repo = _RepoStub([message])
    keyword = _KeywordStub(has_keywords=True)
    classifier = _ClassifierStub()
    action = FilterRelevanceAction(repo, classifier, keyword)

    summary = await action.execute_async(FilterPendingMessagesData(batch_size=10))

    assert summary.relevant == 1
    assert summary.classifier_calls_made == 1
    assert len(classifier.calls) == 1
    assert classifier.calls[0][0].id == 14
    assert repo.saved[0]["result"].backend == "local_llm"
