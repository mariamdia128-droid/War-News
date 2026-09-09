from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.news.repositories.incident_repository import (
    IncidentRepository,
    StoryCandidate,
)
from app.news.services.dedup.story_candidate_search import StoryCandidateSearch


_MSG_DT = datetime(2026, 9, 7, 11, 33, tzinfo=timezone.utc)
_EMBEDDING = [0.1, 0.2, 0.3]


class _RepoStub:
    def __init__(self, candidates: list[StoryCandidate] | None = None) -> None:
        self.candidates = candidates or []
        self.last_query: dict | None = None
        self.queries: list[dict] = []

    def find_story_candidates(self, **kwargs):
        self.last_query = kwargs
        self.queries.append(kwargs)
        return list(self.candidates)


def test_story_search_uses_match_result_villages_not_condition() -> None:
    repo = _RepoStub()
    search = StoryCandidateSearch(repo)  # type: ignore[arg-type]
    match_result = {
        "matched_condition_id": 1,
        "village_matches": [
            {"matched_village_id": 851, "village_role": "target"},
            {"matched_village_id": 900, "village_role": "origin"},
        ],
    }

    search.find_for_message(
        match_result=match_result,
        message_datetime=_MSG_DT,
        candidate_text="غارة على سيارة",
        candidate_embedding=_EMBEDDING,
        exclude_raw_message_id=5311,
        window_hours=72,
        embedding_threshold=0.55,
        max_results=10,
    )

    assert repo.last_query is not None
    assert repo.last_query["village_ids"] == {851, 900}
    assert "condition_id" not in repo.last_query
    assert repo.last_query["window_hours"] == 72
    assert repo.last_query["embedding_threshold"] == 0.55
    assert repo.last_query["max_results"] == 10
    assert repo.last_query["exclude_raw_message_id"] == 5311
    assert repo.last_query["candidate_embedding"] == _EMBEDDING


def test_story_search_returns_empty_when_no_villages() -> None:
    repo = _RepoStub(
        [
            StoryCandidate(
                incident=SimpleNamespace(id=uuid4(), condition_id=3),
                time_gap_seconds=60,
                embedding_similarity=0.9,
            )
        ]
    )
    search = StoryCandidateSearch(repo)  # type: ignore[arg-type]

    result = search.find_for_message(
        match_result={"village_matches": []},
        message_datetime=_MSG_DT,
        candidate_text="x",
        candidate_embedding=_EMBEDDING,
        exclude_raw_message_id=1,
    )

    assert result == []
    assert repo.last_query is None


def test_find_story_candidates_sql_omits_condition_and_caps_by_embedding() -> None:
    class _CompileSession:
        def __init__(self) -> None:
            self.statements: list[object] = []

        def execute(self, statement: object):
            self.statements.append(statement)
            return SimpleNamespace(all=lambda: [])

    db = _CompileSession()
    IncidentRepository(db).find_story_candidates(  # type: ignore[arg-type]
        village_ids={851},
        message_datetime=_MSG_DT,
        window_hours=72,
        embedding_threshold=0.78,
        max_results=10,
        candidate_text="استشهاد مسعف في كفررمان",
        candidate_embedding=_EMBEDDING,
        exclude_raw_message_id=5311,
    )

    compiled = str(
        db.statements[0].compile(compile_kwargs={"literal_binds": True})
    ).lower()
    where_sql = compiled.split("where", 1)[-1]
    assert "incidents.village_id in (851)" in where_sql
    assert "incidents.condition_id =" not in where_sql
    assert "incidents.condition_id in" not in where_sql
    assert "khabar_embedding" in compiled
    assert "<=>" in compiled or "cosine" in compiled
    assert "incidents.raw_message_id != 5311" in where_sql
    assert "khabar_embedding is not null" in where_sql


def test_find_story_candidates_returns_empty_without_embedding() -> None:
    class _CompileSession:
        def execute(self, _statement: object):
            raise AssertionError("should not query without an embedding")

    result = IncidentRepository(_CompileSession()).find_story_candidates(  # type: ignore[arg-type]
        village_ids={851},
        message_datetime=_MSG_DT,
        window_hours=72,
        embedding_threshold=0.78,
        max_results=10,
        candidate_embedding=None,
    )
    assert result == []


def test_find_story_candidates_ranks_and_caps_cross_condition_hits() -> None:
    bombs = SimpleNamespace(
        id=uuid4(),
        condition_id=1,
        village_id=851,
        event_date=_MSG_DT.date(),
        event_time=_MSG_DT.time().replace(hour=11, minute=0),
        khabar="وزارة الصحة: استشهاد مسعف",
        raw_message_id=5306,
    )
    drone = SimpleNamespace(
        id=uuid4(),
        condition_id=3,
        village_id=851,
        event_date=_MSG_DT.date(),
        event_time=_MSG_DT.time().replace(hour=7, minute=4),
        khabar="مسيرة استهدفت سيارة",
        raw_message_id=4389,
    )
    low = SimpleNamespace(
        id=uuid4(),
        condition_id=1,
        village_id=851,
        event_date=_MSG_DT.date(),
        event_time=_MSG_DT.time().replace(hour=2, minute=12),
        khabar="غارة على البلدة",
        raw_message_id=4329,
    )

    class _RankSession:
        def execute(self, _statement: object):
            return SimpleNamespace(
                all=lambda: [
                    (low, 0.50, 0.1),
                    (drone, 0.74, 0.2),
                    (bombs, 0.90, 0.3),
                ]
            )

    result = IncidentRepository(_RankSession()).find_story_candidates(  # type: ignore[arg-type]
        village_ids={851},
        message_datetime=_MSG_DT,
        window_hours=72,
        embedding_threshold=0.55,
        max_results=2,
        candidate_text="تقرير لاحق",
        candidate_embedding=_EMBEDDING,
        exclude_raw_message_id=5311,
    )

    assert [c.incident.condition_id for c in result] == [1, 3]
    assert result[0].incident is bombs
    assert result[1].incident is drone
    assert all(c.embedding_similarity is not None and c.embedding_similarity >= 0.55 for c in result)


def test_default_story_threshold_matches_kfar_roummane_diagnosis() -> None:
    repo = _RepoStub()
    StoryCandidateSearch(repo).find_for_message(  # type: ignore[arg-type]
        match_result={"village_matches": [{"matched_village_id": 851}]},
        message_datetime=_MSG_DT,
        candidate_text="غارة على سيارة في كفررمان",
        candidate_embedding=_EMBEDDING,
        exclude_raw_message_id=1,
    )

    assert repo.last_query is not None
    assert repo.last_query["embedding_threshold"] == 0.40
    assert len(repo.queries) == 1


def test_preliminary_text_adds_zero_threshold_recall_pass() -> None:
    repo = _RepoStub()
    StoryCandidateSearch(repo).find_for_message(  # type: ignore[arg-type]
        match_result={"village_matches": [{"matched_village_id": 851}]},
        message_datetime=_MSG_DT,
        candidate_text="المعلومات الأولية تشير إلى وقوع إصابتين",
        candidate_embedding=_EMBEDDING,
        exclude_raw_message_id=1,
    )

    assert [query["embedding_threshold"] for query in repo.queries] == [0.40, 0.0]
