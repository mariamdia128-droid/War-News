from datetime import date

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from sqlalchemy import select, func, or_
from app.core.database import SessionLocal
from app.news.models import Incident, Village, Condition, DuplicateMatch, IncidentUpdate

db = SessionLocal()
try:
    villages = db.execute(
        select(Village.id, Village.ref_name_en, Village.ref_name_ar, Village.cad_name).where(
            or_(
                func.coalesce(Village.ref_name_en, "").ilike("%kfar%roum%"),
                func.coalesce(Village.ref_name_en, "").ilike("%kfarremane%"),
                func.coalesce(Village.ref_name_ar, "").ilike("%كفررمان%"),
                func.coalesce(Village.ref_name_ar, "").ilike("%كفر رمان%"),
                func.coalesce(Village.cad_name, "").ilike("%kfar%roum%"),
            )
        )
    ).all()
    print("VILLAGES", villages)
    village_ids = [v[0] for v in villages]
    if not village_ids:
        raise SystemExit("no villages")
    rows = db.execute(
        select(
            Incident.id,
            Incident.event_date,
            Incident.event_time,
            Incident.total_deaths,
            Incident.total_injuries,
            Incident.deaths,
            Incident.injuries,
            Incident.duplicate_level,
            Incident.duplicate_similarity_score,
            Incident.verification_status,
            Incident.raw_message_id,
            Incident.condition_id,
            Condition.action_en,
            Incident.khabar,
        )
        .outerjoin(Condition, Condition.id == Incident.condition_id)
        .where(
            Incident.village_id.in_(village_ids),
            Incident.event_date == date(2026, 9, 7),
            Incident.is_deleted.is_(False),
        )
        .order_by(Incident.event_time.asc().nulls_last(), Incident.created_at.asc())
    ).all()
    print("INCIDENT_COUNT", len(rows))
    for r in rows:
        khabar = (r.khabar or "").replace("\n", " ")[:220]
        print("---")
        print(
            "id=", r.id,
            "time=", r.event_time,
            "cond=", r.action_en, r.condition_id,
            "deaths=", r.total_deaths, r.deaths,
            "inj=", r.total_injuries, r.injuries,
            "dup=", r.duplicate_level,
            "score=", r.duplicate_similarity_score,
            "ver=", r.verification_status,
            "raw=", r.raw_message_id,
        )
        print(khabar)
    ids = [r.id for r in rows]
    if ids:
        matches = db.execute(
            select(
                DuplicateMatch.incident_id,
                DuplicateMatch.matched_incident_id,
                DuplicateMatch.raw_message_id,
                DuplicateMatch.match_type,
                DuplicateMatch.similarity_score,
                DuplicateMatch.status,
            ).where(
                DuplicateMatch.incident_id.in_(ids)
                | DuplicateMatch.matched_incident_id.in_(ids)
            )
        ).all()
        print("MATCHES", len(matches))
        for m in matches:
            print(m)
        updates = db.execute(
            select(
                IncidentUpdate.incident_id,
                IncidentUpdate.action,
                IncidentUpdate.new_values,
                IncidentUpdate.created_at,
            )
            .where(IncidentUpdate.incident_id.in_(ids))
            .order_by(IncidentUpdate.created_at.asc())
        ).all()
        print("UPDATES", len(updates))
        for u in updates:
            nv = u.new_values or {}
            keys = list(nv.keys())[:12]
            merged = nv.get("merged_from") or {}
            print(
                "update",
                u.incident_id,
                u.action,
                keys,
                merged.get("raw_message_id"),
                u.created_at,
            )
finally:
    db.close()
