from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.news.models.incident_verification_flag import IncidentVerificationFlag
from app.news.repositories.incident_verification_flag_repository import (
    IncidentVerificationFlagRepository,
)


class VerificationFlagService:
    def __init__(self, repository: IncidentVerificationFlagRepository) -> None:
        self.repository = repository

    def open_flag(
        self,
        incident_id: UUID,
        flag_type: str,
        reason_code: str,
        severity: str,
        detail: dict[str, Any],
        source_message_id: int | None,
        visible_after: datetime | None = None,
    ) -> IncidentVerificationFlag:
        return self.repository.open_flag(
            incident_id=incident_id,
            flag_type=flag_type,
            reason_code=reason_code,
            severity=severity,
            detail=detail,
            source_message_id=source_message_id,
            visible_after=visible_after,
        )

    def resolve_flag(
        self, flag_id: UUID, user_id: UUID, resolution: dict[str, Any]
    ) -> IncidentVerificationFlag:
        return self.repository.resolve_flag(flag_id, user_id, resolution)

    def dismiss_flag(
        self, flag_id: UUID, user_id: UUID, reason: str
    ) -> IncidentVerificationFlag:
        return self.repository.dismiss_flag(flag_id, user_id, reason)

    def auto_clear(self, flag_id: UUID, reason: str) -> IncidentVerificationFlag:
        return self.repository.auto_clear(flag_id, reason)

    def list_open_for_incident(
        self, incident_id: UUID
    ) -> list[IncidentVerificationFlag]:
        return self.repository.list_open_for_incident(incident_id)

    def list_flags(
        self,
        *,
        flag_type: str | None = None,
        reason_code: str | None = None,
        status: str | None = None,
        severity: str | None = None,
        created_after: datetime | None = None,
        created_before: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[IncidentVerificationFlag], int]:
        return self.repository.list_flags(
            flag_type=flag_type,
            reason_code=reason_code,
            status=status,
            severity=severity,
            created_after=created_after,
            created_before=created_before,
            limit=limit,
            offset=offset,
        )
