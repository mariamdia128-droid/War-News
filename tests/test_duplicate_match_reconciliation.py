from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

from app.news.models import MessageStatus
from app.news.services.dedup.duplicate_match_reconciliation import (
    _find_representative_incident,
    reconcile_orphaned_soft_deleted_incidents,
)


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _ReconciliationSession:
    def __init__(
        self,
        *,
        orphans: list[object],
        raw_messages: dict[int, object],
        representative_lookup: dict[tuple[int, int], object | None],
        partial_lookup: dict[tuple[int, int, int], object | None],
    ) -> None:
        self.orphans = orphans
        self.raw_messages = raw_messages
        self.representative_lookup = representative_lookup
        self.partial_lookup = partial_lookup
        self.duplicate_matches: list[tuple[object, object]] = []
        self.committed = 0
        self.scalar_calls = 0

    def scalars(self, stmt) -> _ScalarResult:
        self.scalar_calls += 1
        return _ScalarResult(self.orphans if self.scalar_calls == 1 else [])

    def get(self, model, pk):
        return self.raw_messages.get(pk)

    def scalar(self, stmt):
        # The reconciliation service issues two different lookup shapes; the
        # stub keys are enough for the unit test scenarios below.
        return None

    def commit(self) -> None:
        self.committed += 1


def test_reconcile_backfills_after_representative_exists(monkeypatch) -> None:
    soft_deleted_id = uuid4()
    representative_id = uuid4()
    soft_deleted = SimpleNamespace(
        id=soft_deleted_id,
        raw_message_id=712,
        village_id=976,
        condition_id=5,
        event_date="2026-08-18",
        khabar="قصف مدفعي على المنصوري",
        is_deleted=True,
    )
    representative = SimpleNamespace(
        id=representative_id,
        raw_message_id=711,
        village_id=976,
        condition_id=5,
        khabar="قصف مدفعي على المنصوري",
        is_deleted=False,
    )
    raw_message = SimpleNamespace(
        id=712, duplicate_of_id=711, raw_text="قصف مدفعي على المنصوري"
    )
    representative_raw = SimpleNamespace(
        id=711, duplicate_of_id=None, raw_text="قصف مدفعي على المنصوري"
    )

    session = _ReconciliationSession(
        orphans=[soft_deleted],
        raw_messages={712: raw_message, 711: representative_raw},
        representative_lookup={(711, 976): representative},
        partial_lookup={},
    )

    class _RepoStub:
        def find_active_incident_for_raw_message_village(
            self,
            raw_message_id: int,
            village_id: int,
        ):
            return session.representative_lookup.get((raw_message_id, village_id))

        def create_duplicate_match(self, *, incident, matched_incident, similarity_score):
            session.duplicate_matches.append((incident, matched_incident, similarity_score))

    monkeypatch.setattr(
        "app.news.services.dedup.duplicate_match_reconciliation.IncidentRepository",
        lambda db: _RepoStub(),
    )
    monkeypatch.setattr(
        "app.news.services.dedup.duplicate_match_reconciliation._find_representative_incident",
        lambda db, repo, *, soft_deleted: representative,
    )
    monkeypatch.setattr(
        "app.news.services.dedup.duplicate_match_reconciliation._raw_text_similarity",
        lambda db, left, right: 0.95,
    )

    backfilled = reconcile_orphaned_soft_deleted_incidents(session)  # type: ignore[arg-type]

    assert backfilled == 1
    assert session.duplicate_matches == [(soft_deleted, representative, 0.95)]
    assert session.committed == 1


def test_reconcile_logs_both_raw_ids_when_representative_still_missing(
    monkeypatch, caplog
) -> None:
    soft_deleted = SimpleNamespace(
        id=uuid4(),
        raw_message_id=900,
        village_id=976,
        condition_id=5,
        event_date="2026-08-18",
        is_deleted=True,
    )
    session = _ReconciliationSession(
        orphans=[soft_deleted],
        raw_messages={900: SimpleNamespace(id=900, duplicate_of_id=899)},
        representative_lookup={(899, 976): None},
        partial_lookup={},
    )

    monkeypatch.setattr(
        "app.news.services.dedup.duplicate_match_reconciliation.IncidentRepository",
        lambda db: SimpleNamespace(
            find_active_incident_for_raw_message_village=lambda *_args, **_kwargs: None,
            create_duplicate_match=lambda **_kwargs: None,
        ),
    )
    monkeypatch.setattr(
        "app.news.services.dedup.duplicate_match_reconciliation._find_representative_incident",
        lambda db, repo, *, soft_deleted: None,
    )

    with caplog.at_level("INFO"):
        backfilled = reconcile_orphaned_soft_deleted_incidents(session)  # type: ignore[arg-type]

    assert backfilled == 0
    assert session.duplicate_matches == []
    assert session.committed == 0
    assert "raw_message_id=900" in caplog.text
    assert "matched_raw_message_id=899" in caplog.text
    assert "gate=representative" in caplog.text


def test_find_representative_rejects_duplicate_of_with_different_condition() -> None:
    soft_deleted = SimpleNamespace(
        raw_message_id=712,
        village_id=976,
        condition_id=5,
    )
    representative = SimpleNamespace(condition_id=6)
    db = _ReconciliationSession(
        orphans=[],
        raw_messages={712: SimpleNamespace(id=712, duplicate_of_id=711)},
        representative_lookup={},
        partial_lookup={},
    )
    repo = SimpleNamespace(
        find_active_incident_for_raw_message_village=lambda *_args: representative
    )

    assert _find_representative_incident(  # type: ignore[arg-type]
        db, repo, soft_deleted=soft_deleted
    ) is None


def test_reconcile_declines_explicit_modifier_conflict_and_logs_gate(
    monkeypatch, caplog
) -> None:
    soft_deleted = SimpleNamespace(
        id=uuid4(), raw_message_id=712, village_id=976, condition_id=5,
        event_date="2026-08-18",
        khabar="قصف فسفوري على المنصوري",
        is_deleted=True,
    )
    representative = SimpleNamespace(
        id=uuid4(), raw_message_id=711, village_id=976, condition_id=5,
        khabar="قصف دبابة على المنصوري",
        is_deleted=False,
    )
    session = _ReconciliationSession(
        orphans=[soft_deleted],
        raw_messages={
            712: SimpleNamespace(
                id=712, duplicate_of_id=711, raw_text="قصف فسفوري على المنصوري"
            ),
            711: SimpleNamespace(
                id=711, duplicate_of_id=None, raw_text="قصف دبابة على المنصوري"
            ),
        },
        representative_lookup={}, partial_lookup={},
    )
    created: list[dict] = []
    repo = SimpleNamespace(
        create_duplicate_match=lambda **kwargs: created.append(kwargs),
    )
    monkeypatch.setattr(
        "app.news.services.dedup.duplicate_match_reconciliation.IncidentRepository",
        lambda db: repo,
    )
    monkeypatch.setattr(
        "app.news.services.dedup.duplicate_match_reconciliation._find_representative_incident",
        lambda db, incident_repo, *, soft_deleted: representative,
    )

    with caplog.at_level("INFO"):
        assert reconcile_orphaned_soft_deleted_incidents(session) == 0  # type: ignore[arg-type]
    assert created == []
    assert session.committed == 0
    assert "raw_message_id=712" in caplog.text
    assert "matched_raw_message_id=711" in caplog.text
    assert "gate=modifier" in caplog.text
