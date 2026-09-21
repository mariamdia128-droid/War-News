from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.api.deps import require_admin
from app.core.database import get_db
from app.news.models import Condition, Incident, RawMessage, Village


router = APIRouter(prefix="/api/filtered-news", tags=["filtered-news"])


class FilteredNewsItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    incident_id: str | None
    status: str
    khabar: str
    message_datetime: datetime | None
    received_at: datetime
    event_at: datetime
    source_name: str | None
    source_platform: str | None
    external_message_id: str | None
    verdict: str | None
    confidence: float | None
    reasoning: str | None
    condition_id: int | None
    condition_name: str | None
    village_id: int | None
    village_name: str | None


class FilteredNewsList(BaseModel):
    items: list[FilteredNewsItem]
    total: int
    limit: int
    offset: int


def _item(row) -> FilteredNewsItem:
    message = row.RawMessage
    result = message.filter_result or {}
    confidence = result.get("confidence")
    return FilteredNewsItem(
        id=message.id,
        incident_id=str(row.incident_id) if row.incident_id is not None else None,
        status=message.status.value,
        khabar=message.raw_text or "",
        message_datetime=message.message_datetime,
        received_at=message.received_at,
        event_at=row.event_at,
        source_name=message.source_name,
        source_platform=message.source_platform,
        external_message_id=message.external_message_id,
        verdict=result.get("verdict"),
        confidence=(
            float(confidence)
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool)
            else None
        ),
        reasoning=result.get("reasoning") or result.get("reason"),
        condition_id=row.condition_id,
        condition_name=row.condition_name,
        village_id=row.village_id,
        village_name=row.village_name,
    )


@router.get("", response_model=FilteredNewsList)
def list_filtered_news(
    limit: int = Query(150, ge=1, le=150),
    offset: int = Query(0, ge=0),
    event_date_from: date | None = Query(None),
    event_date_to: date | None = Query(None),
    source_name: str | None = Query(None),
    status: str | None = Query(None),
    related_only: bool = Query(False),
    search: str | None = Query(None),
    _current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FilteredNewsList:
    event_at = func.coalesce(RawMessage.message_datetime, RawMessage.received_at)
    filters = [
        or_(
            RawMessage.filter_result["verdict"].as_string() == "relevant",
            Incident.id.is_not(None),
        ),
    ]
    if related_only:
        filters.append(Incident.id.is_not(None))
    if event_date_from is not None:
        filters.append(func.date(event_at) >= event_date_from)
    if event_date_to is not None:
        filters.append(func.date(event_at) <= event_date_to)
    if source_name and source_name.strip():
        filters.append(RawMessage.source_name == source_name.strip())
    if status and status.strip():
        filters.append(RawMessage.status == status.strip())
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(
            or_(
                RawMessage.raw_text.ilike(pattern),
                RawMessage.source_name.ilike(pattern),
                RawMessage.external_message_id.ilike(pattern),
                Village.ref_name_ar.ilike(pattern),
                Village.ref_name_en.ilike(pattern),
                Condition.action_ar.ilike(pattern),
                Condition.action_en.ilike(pattern),
            )
        )

    village_label = func.coalesce(
        Village.ref_name_ar,
        Village.ref_name_en,
        Village.acs_name,
        Village.cad_name,
    )
    condition_label = func.coalesce(
        Condition.action_ar,
        Condition.action_en,
    )

    base = (
        select(
            RawMessage,
            event_at.label("event_at"),
            Incident.id.label("incident_id"),
            Incident.condition_id.label("condition_id"),
            Incident.village_id.label("village_id"),
            village_label.label("village_name"),
            condition_label.label("condition_name"),
        )
        .outerjoin(
            Incident,
            (Incident.raw_message_id == RawMessage.id)
            & (Incident.is_deleted.is_(False)),
        )
        .outerjoin(Village, Village.id == Incident.village_id)
        .outerjoin(Condition, Condition.id == Incident.condition_id)
        .where(*filters)
    )
    rows = db.execute(
        base.order_by(event_at.desc(), RawMessage.id.desc()).limit(limit).offset(offset)
    ).all()
    total = db.scalar(
        select(func.count(RawMessage.id.distinct()))
        .select_from(RawMessage)
        .outerjoin(
            Incident,
            (Incident.raw_message_id == RawMessage.id)
            & (Incident.is_deleted.is_(False)),
        )
        .outerjoin(Village, Village.id == Incident.village_id)
        .outerjoin(Condition, Condition.id == Incident.condition_id)
        .where(*filters)
    )
    return FilteredNewsList(
        items=[_item(row) for row in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )
