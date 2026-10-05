from datetime import datetime, timezone
from types import SimpleNamespace

from app.news.dtos import BulletinCasualtyGroupDTO
from app.news.dtos.incident_dto import IncidentListItemDTO
from app.news.models.bulletin_casualty_group import (
    BulletinBreakdownStatus,
    CasualtyScope,
)
from app.news.repositories.incident_repository import IncidentRepository


def test_bulletin_group_dto_serializes_model_enums() -> None:
    now = datetime.now(timezone.utc)
    group = SimpleNamespace(
        raw_message_id=7,
        village_ids=[10, 20],
        casualty_scope=CasualtyScope.bulletin_aggregate,
        total_deaths=4,
        total_injuries=20,
        breakdown_status=BulletinBreakdownStatus.pending,
        window_expires_at=now,
        resolved_at=None,
        resolved_by_raw_message_id=None,
    )

    payload = BulletinCasualtyGroupDTO.model_validate(group)

    assert payload.casualty_scope == "bulletin_aggregate"
    assert payload.breakdown_status == "pending"
    assert (payload.total_deaths, payload.total_injuries) == (4, 20)


def test_incident_list_items_group_by_raw_message() -> None:
    now = datetime.now(timezone.utc)
    base = {
        "raw_status": "materialized",
        "condition_ar": None,
        "event_date": now.date(),
        "event_time": None,
        "khabar": "same bulletin text",
        "source": "Telegram",
        "source_reference": "telegram:1",
        "source_name": "Channel",
        "total_deaths": None,
        "total_injuries": None,
        "matched": False,
        "verification_status": "needs_verification",
        "verified_by_user_id": None,
        "verified_at": None,
        "duplicate_flag": "none",
        "details_pending": False,
        "created_at": now,
        "version": 1,
        "locked_by_user_id": None,
        "edit_lock_expires_at": None,
    }
    rows = [
        IncidentListItemDTO.model_validate(
            {
                **base,
                "id": None,
                "raw_message_id": 10,
                "village": "A",
                "condition": "Bombs",
                "verification_reason": "Reason one",
                "verification_types": ["duplicate"],
            }
        ),
        IncidentListItemDTO.model_validate(
            {
                **base,
                "id": None,
                "raw_message_id": 10,
                "village": "B",
                "condition": "Shelling",
                "verification_reason": "Reason two",
                "verification_types": ["casualty_missing_number"],
            }
        ),
    ]

    groups = IncidentRepository._group_list_items_by_raw_message(rows)

    assert len(groups) == 1
    assert groups[0].raw_message_id == 10
    assert groups[0].verification_reasons == ["Reason one", "Reason two"]
    assert groups[0].verification_types == ["duplicate", "casualty_missing_number"]
    assert [item.village for item in groups[0].incidents] == ["A", "B"]
