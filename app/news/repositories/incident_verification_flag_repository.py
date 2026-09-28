from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.news.models import IncidentUpdate, UpdateAction
from app.news.models.incident_verification_flag import IncidentVerificationFlag


class IncidentVerificationFlagRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def open_flag(
        self,
        *,
        incident_id: UUID,
        flag_type: str,
        reason_code: str,
        severity: str,
        detail: dict[str, Any],
        source_message_id: int | None,
        visible_after: datetime | None = None,
    ) -> IncidentVerificationFlag:
        existing = self.db.scalar(
            select(IncidentVerificationFlag)
            .where(
                IncidentVerificationFlag.incident_id == incident_id,
                IncidentVerificationFlag.flag_type == flag_type,
                IncidentVerificationFlag.reason_code == reason_code,
                IncidentVerificationFlag.status == "open",
            )
            .with_for_update()
        )
        now = datetime.now(timezone.utc)
        if existing is None:
            flag = IncidentVerificationFlag(
                incident_id=incident_id,
                flag_type=flag_type,
                reason_code=reason_code,
                status="open",
                severity=severity,
                detail=detail,
                source_message_id=source_message_id,
                visible_after=visible_after,
                created_at=now,
                updated_at=now,
            )
            self.db.add(flag)
            self.db.flush()
            self._audit(flag, old_values=None)
            return flag

        old_values = self._flag_snapshot(existing)
        existing.detail = detail
        existing.severity = severity
        existing.source_message_id = source_message_id
        existing.visible_after = visible_after
        existing.updated_at = now
        self.db.add(existing)
        self._audit(existing, old_values=old_values)
        return existing

    def resolve_flag(
        self, flag_id: UUID, user_id: UUID, resolution: dict[str, Any]
    ) -> IncidentVerificationFlag:
        flag = self._get_open(flag_id)
        old_values = self._flag_snapshot(flag)
        flag.status = "resolved"
        flag.resolved_at = datetime.now(timezone.utc)
        flag.resolved_by = user_id
        flag.resolution = resolution
        flag.updated_at = flag.resolved_at
        return self._save_state(flag, old_values)

    def update_open_resolution(
        self, flag_id: UUID, resolution: dict[str, Any], detail: dict[str, Any]
    ) -> IncidentVerificationFlag:
        flag = self._get_open(flag_id)
        old_values = self._flag_snapshot(flag)
        flag.detail = detail
        flag.resolution = resolution
        flag.updated_at = datetime.now(timezone.utc)
        return self._save_state(flag, old_values)

    def dismiss_flag(
        self, flag_id: UUID, user_id: UUID, reason: str
    ) -> IncidentVerificationFlag:
        flag = self._get_open(flag_id)
        old_values = self._flag_snapshot(flag)
        flag.status = "dismissed"
        flag.resolved_at = datetime.now(timezone.utc)
        flag.resolved_by = user_id
        flag.resolution = {"dismiss_reason": reason}
        flag.updated_at = flag.resolved_at
        return self._save_state(flag, old_values)

    def auto_clear(self, flag_id: UUID, reason: str) -> IncidentVerificationFlag:
        flag = self._get_open(flag_id)
        old_values = self._flag_snapshot(flag)
        flag.status = "auto_cleared"
        flag.resolved_at = datetime.now(timezone.utc)
        flag.auto_clear_reason = reason
        flag.updated_at = flag.resolved_at
        return self._save_state(flag, old_values)

    def get_by_id(self, flag_id: UUID) -> IncidentVerificationFlag | None:
        return self.db.scalar(
            select(IncidentVerificationFlag).where(
                IncidentVerificationFlag.id == flag_id
            )
        )

    def list_open_for_incident(
        self, incident_id: UUID
    ) -> list[IncidentVerificationFlag]:
        return list(
            self.db.scalars(
                select(IncidentVerificationFlag)
                .where(
                    IncidentVerificationFlag.incident_id == incident_id,
                    IncidentVerificationFlag.status == "open",
                )
                .order_by(IncidentVerificationFlag.created_at, IncidentVerificationFlag.id)
            ).all()
        )

    def has_previously_reviewed(self, incident_id: UUID, reason_code: str) -> bool:
        return self.db.scalar(
            select(IncidentVerificationFlag.id).where(
                IncidentVerificationFlag.incident_id == incident_id,
                IncidentVerificationFlag.flag_type == "casualty_check",
                IncidentVerificationFlag.reason_code == reason_code,
                IncidentVerificationFlag.status.in_(("resolved", "dismissed")),
            ).limit(1)
        ) is not None

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
        query = select(IncidentVerificationFlag)
        filters = (
            (IncidentVerificationFlag.flag_type, flag_type),
            (IncidentVerificationFlag.reason_code, reason_code),
            (IncidentVerificationFlag.status, status),
            (IncidentVerificationFlag.severity, severity),
        )
        for column, value in filters:
            if value is not None:
                query = query.where(column == value)
        if created_after is not None:
            query = query.where(IncidentVerificationFlag.created_at >= created_after)
        if created_before is not None:
            query = query.where(IncidentVerificationFlag.created_at <= created_before)
        total = self.db.scalar(
            select(func.count()).select_from(query.subquery())
        ) or 0
        rows = self.db.scalars(
            query.order_by(
                IncidentVerificationFlag.created_at.desc(), IncidentVerificationFlag.id
            ).limit(limit).offset(offset)
        ).all()
        return list(rows), int(total)

    def _get_open(self, flag_id: UUID) -> IncidentVerificationFlag:
        flag = self.db.scalar(
            select(IncidentVerificationFlag)
            .where(
                IncidentVerificationFlag.id == flag_id,
                IncidentVerificationFlag.status == "open",
            )
            .with_for_update()
        )
        if flag is None:
            raise LookupError(f"Open verification flag {flag_id} was not found.")
        return flag

    def _save_state(
        self, flag: IncidentVerificationFlag, old_values: dict[str, Any]
    ) -> IncidentVerificationFlag:
        self.db.add(flag)
        self._audit(flag, old_values=old_values)
        return flag

    def _audit(
        self,
        flag: IncidentVerificationFlag,
        *,
        old_values: dict[str, Any] | None,
    ) -> None:
        self.db.add(
            IncidentUpdate(
                incident_id=flag.incident_id,
                action=UpdateAction.status_change,
                old_values={"verification_flag": old_values} if old_values else None,
                new_values={"verification_flag": self._flag_snapshot(flag)},
                performed_by=flag.resolved_by,
            )
        )

    @staticmethod
    def _flag_snapshot(flag: IncidentVerificationFlag) -> dict[str, Any]:
        return {
            "id": str(flag.id) if flag.id else None,
            "flag_type": flag.flag_type,
            "reason_code": flag.reason_code,
            "status": flag.status,
            "severity": flag.severity,
            "detail": flag.detail,
            "source_message_id": flag.source_message_id,
            "resolved_by": str(flag.resolved_by) if flag.resolved_by else None,
            "resolution": flag.resolution,
            "auto_clear_reason": flag.auto_clear_reason,
        }
