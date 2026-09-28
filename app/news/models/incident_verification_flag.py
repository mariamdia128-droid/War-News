from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IncidentVerificationFlag(Base):
    __tablename__ = "incident_verification_flags"
    __table_args__ = (
        CheckConstraint(
            "status IN ('open', 'resolved', 'dismissed', 'auto_cleared')",
            name="ck_incident_verification_flags_status",
        ),
        CheckConstraint(
            "severity IN ('review', 'info')",
            name="ck_incident_verification_flags_severity",
        ),
        Index(
            "uq_incident_verification_flags_open_key",
            "incident_id",
            "flag_type",
            "reason_code",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index(
            "ix_incident_verification_flags_type_status_visible_after",
            "flag_type",
            "status",
            "visible_after",
        ),
        Index(
            "ix_incident_verification_flags_incident_status_visible_after",
            "incident_id", "status", "visible_after",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    incident_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False
    )
    flag_type: Mapped[str] = mapped_column(String(48), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open", server_default="open"
    )
    visible_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    source_message_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("raw_messages.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    resolution: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    auto_clear_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
