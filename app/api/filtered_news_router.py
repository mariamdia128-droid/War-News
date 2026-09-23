from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.orm import Session

from app.accounts.models import User
from app.api.deps import require_admin
from app.core.database import get_db
from app.news.constants.air_violation_conditions import AIR_VIOLATION_CONDITION_ID_TUPLE
from app.news.models import AirViolation, Condition, Incident, RawMessage, Village


router = APIRouter(prefix="/api/filtered-news", tags=["filtered-news"])
RED_ALERT_SOURCE_NAME = "Red Alert Lebanon"


def _war_context_text_filter(text_expr) -> object:
    patterns = (
        "%israel%",
        "%israeli%",
        "%idf%",
        "%enemy%",
        "%war%",
        "%military%",
        "%security%",
        "%strike%",
        "%airstrike%",
        "%shelling%",
        "%bombardment%",
        "%missile%",
        "%rocket%",
        "%drone%",
        "%raid%",
        "%targeted%",
        "%إسرائيل%",
        "%اسرائيل%",
        "%إسرائيلي%",
        "%اسرائيلي%",
        "%العدو%",
        "%حرب%",
        "%حربي%",
        "%أمني%",
        "%امني%",
        "%عسكري%",
        "%غارة%",
        "%غارات%",
        "%قصف%",
        "%استهداف%",
        "%استهدف%",
        "%صاروخ%",
        "%صواريخ%",
        "%مسيرة%",
    )
    return or_(*(text_expr.ilike(pattern) for pattern in patterns))


def _palestine_scope_text_filter(text_expr) -> object:
    patterns = (
        "%palestine%",
        "%gaza%",
        "%ramallah%",
        "%west bank%",
        "%nablus%",
        "%jenin%",
        "%khan younis%",
        "%rafah%",
        "%فلسطين%",
        "%غزة%",
        "%رام الله%",
        "%رامالله%",
        "%الضفة الغربية%",
        "%نابلس%",
        "%جنين%",
        "%خان يونس%",
        "%رفح%",
    )
    return or_(*(text_expr.ilike(pattern) for pattern in patterns))


def _lebanon_scope_text_filter(text_expr) -> object:
    patterns = (
        "%lebanon%",
        "%lebanese%",
        "%لبنان%",
        "%لبناني%",
    )
    return or_(*(text_expr.ilike(pattern) for pattern in patterns))


def _visible_incident_scope_filter() -> object:
    text_expr = func.coalesce(Incident.khabar, RawMessage.raw_text, "")
    ordinary_burning_properties = and_(
        Condition.action_en == "Burning Properties",
        ~_war_context_text_filter(text_expr),
    )
    palestine_only = and_(
        _palestine_scope_text_filter(text_expr),
        ~_lebanon_scope_text_filter(text_expr),
    )
    return ~or_(ordinary_burning_properties, palestine_only)


class FilteredNewsItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    incident_id: str | None
    air_violation_id: int | None
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
        air_violation_id=row.air_violation_id,
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
    include_rejected_red_alert: bool = Query(False),
    last_hours: int | None = Query(None, ge=1, le=8760),
    search: str | None = Query(None),
    _current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> FilteredNewsList:
    raw_event_at = func.timezone(
        "Asia/Beirut",
        func.coalesce(RawMessage.message_datetime, RawMessage.received_at),
    )
    incident_event_at = Incident.event_date + func.coalesce(Incident.event_time, time.min)
    air_violation_event_at = AirViolation.event_date + func.coalesce(
        AirViolation.event_time,
        time.min,
    )
    event_at = func.coalesce(incident_event_at, air_violation_event_at, raw_event_at)
    visible_news_filter = or_(
        RawMessage.filter_result["verdict"].as_string() == "relevant",
        Incident.id.is_not(None),
        AirViolation.id.is_not(None),
    )
    red_alert_scope = RawMessage.source_name == RED_ALERT_SOURCE_NAME
    if include_rejected_red_alert and source_name == RED_ALERT_SOURCE_NAME and not related_only:
        filters = [or_(visible_news_filter, red_alert_scope)]
    else:
        filters = [visible_news_filter]
    if related_only:
        filters.append(or_(Incident.id.is_not(None), AirViolation.id.is_not(None)))
        filters.append(
            or_(
                AirViolation.id.is_not(None),
                _visible_incident_scope_filter(),
            )
        )
    if event_date_from is not None:
        filters.append(func.date(event_at) >= event_date_from)
    if event_date_to is not None:
        filters.append(func.date(event_at) <= event_date_to)
    if last_hours is not None:
        cutoff = datetime.now(ZoneInfo("Asia/Beirut")).replace(tzinfo=None) - timedelta(
            hours=last_hours,
        )
        filters.append(event_at >= cutoff)
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
                AirViolation.caza_ar.ilike(pattern),
                AirViolation.caza_en.ilike(pattern),
            )
        )

    village_label = func.coalesce(
        Village.ref_name_ar,
        Village.ref_name_en,
        Village.acs_name,
        Village.cad_name,
        AirViolation.caza_ar,
        AirViolation.caza_en,
    )
    condition_label = func.coalesce(
        Condition.action_ar,
        Condition.action_en,
        case((AirViolation.id.is_not(None), "خرق جوي"), else_=None),
    )
    resolved_condition_id = func.coalesce(Incident.condition_id, AirViolation.condition_id)
    resolved_village_id = func.coalesce(Incident.village_id, AirViolation.village_id)

    base = (
        select(
            RawMessage,
            event_at.label("event_at"),
            Incident.id.label("incident_id"),
            AirViolation.id.label("air_violation_id"),
            resolved_condition_id.label("condition_id"),
            resolved_village_id.label("village_id"),
            village_label.label("village_name"),
            condition_label.label("condition_name"),
        )
        .outerjoin(
            Incident,
            (Incident.raw_message_id == RawMessage.id)
            & (Incident.is_deleted.is_(False))
            & (Incident.condition_id.not_in(AIR_VIOLATION_CONDITION_ID_TUPLE)),
        )
        .outerjoin(AirViolation, AirViolation.raw_message_id == RawMessage.id)
        .outerjoin(Village, Village.id == resolved_village_id)
        .outerjoin(Condition, Condition.id == resolved_condition_id)
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
            & (Incident.is_deleted.is_(False))
            & (Incident.condition_id.not_in(AIR_VIOLATION_CONDITION_ID_TUPLE)),
        )
        .outerjoin(AirViolation, AirViolation.raw_message_id == RawMessage.id)
        .outerjoin(Village, Village.id == resolved_village_id)
        .outerjoin(Condition, Condition.id == resolved_condition_id)
        .where(*filters)
    )
    return FilteredNewsList(
        items=[_item(row) for row in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )
