from __future__ import annotations

from uuid import uuid4

from app.news.models import Incident, IncidentUpdate
from app.news.models.incident_verification_flag import IncidentVerificationFlag
from app.news.repositories.incident_repository import IncidentRepository
from app.news.repositories.incident_verification_flag_repository import (
    IncidentVerificationFlagRepository,
)
from app.news.services.verification_flag_service import VerificationFlagService


class _FlagSessionStub:
    def __init__(self, flag: IncidentVerificationFlag | None = None, flags=None) -> None:
        self.flag = flag
        self.flags = flags if flags is not None else []
        self.added: list[object] = []

    def scalar(self, _statement):
        return self.flag

    def get(self, _model, _pk):
        return self.flag if _model is IncidentVerificationFlag else None

    def add(self, value: object) -> None:
        self.added.append(value)

    def flush(self) -> None:
        return None


def test_open_flag_is_idempotent_and_refreshes_existing_open_detail() -> None:
    incident_id = uuid4()
    flag = IncidentVerificationFlag(
        id=uuid4(), incident_id=incident_id, flag_type="casualty_check",
        reason_code="count_missing", status="open", severity="review", detail={"old": True},
    )
    db = _FlagSessionStub(flag)
    service = VerificationFlagService(IncidentVerificationFlagRepository(db))  # type: ignore[arg-type]

    opened = service.open_flag(
        incident_id, "casualty_check", "count_missing", "review", {"evidence": "updated"}, 17
    )

    assert opened is flag
    assert flag.detail == {"evidence": "updated"}
    assert flag.source_message_id == 17
    assert len([item for item in db.added if isinstance(item, IncidentVerificationFlag)]) == 1
    audit = next(item for item in db.added if isinstance(item, IncidentUpdate))
    assert audit.new_values["verification_flag"]["detail"] == {"evidence": "updated"}


def test_resolving_flag_changes_state_and_writes_incident_audit() -> None:
    user_id = uuid4()
    flag = IncidentVerificationFlag(
        id=uuid4(), incident_id=uuid4(), flag_type="casualty_check",
        reason_code="preliminary_toll", status="open", severity="info", detail={},
    )
    db = _FlagSessionStub(flag)
    service = VerificationFlagService(IncidentVerificationFlagRepository(db))  # type: ignore[arg-type]

    resolved = service.resolve_flag(flag.id, user_id, {"confirmed_unknown": True})

    assert resolved.status == "resolved"
    assert resolved.resolved_by == user_id
    assert resolved.resolution == {"confirmed_unknown": True}
    audit = next(item for item in db.added if isinstance(item, IncidentUpdate))
    assert audit.performed_by == user_id
    assert audit.new_values["verification_flag"]["status"] == "resolved"


def test_incident_merge_leaves_open_verification_flags_untouched() -> None:
    existing = Incident(
        id=uuid4(), deaths=2, total_deaths=2, verification_status="needs_verification",
        verification_reason="review casualty report",
    )
    open_flags = [
        {"id": uuid4(), "status": "open", "reason_code": "count_missing"}
    ]
    db = _FlagSessionStub(flags=open_flags)
    before = list(db.flags)
    IncidentRepository(db).merge_existing(  # type: ignore[arg-type]
        existing,
        {"deaths": 3, "total_deaths": 3, "khabar": "later report"},
        raw_message_id=91,
    )

    assert db.flags == before
    assert existing.verification_status == "needs_verification"
    assert existing.verification_reason == "review casualty report"
