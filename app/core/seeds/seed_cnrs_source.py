from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.sources.models.source import Source, SourceType

CNRS_WEBHOOK_SECRET_REF = "CNRS_WEBHOOK_SECRET"

CNRS_SOURCES: tuple[dict[str, Any], ...] = (
    {
        "type": SourceType.api,
        "name": "CNRS Webhook",
        "external_id": "cnrs_webhook",
        "config": {"delivery_method": "webhook"},
        "last_cursor": None,
        "auth_secret_ref": CNRS_WEBHOOK_SECRET_REF,
        "is_active": True,
    },
)


def ensure_cnrs_source(db: Session) -> tuple[Source, bool]:
    source_data = CNRS_SOURCES[0]
    existing_source = db.scalar(
        select(Source).where(Source.external_id == source_data["external_id"])
    )
    if existing_source is None:
        source = Source(**source_data)
        db.add(source)
        db.flush()
        db.commit()
        return source, True

    changed = False
    desired_config = {
        **(existing_source.config or {}),
        "delivery_method": source_data["config"]["delivery_method"],
    }
    updates = {
        "type": source_data["type"],
        "name": source_data["name"],
        "config": desired_config,
        "auth_secret_ref": source_data["auth_secret_ref"],
        "is_active": True,
    }
    for field, value in updates.items():
        if getattr(existing_source, field) != value:
            setattr(existing_source, field, value)
            changed = True

    if changed:
        db.add(existing_source)
        db.commit()
    return existing_source, False


def seed_cnrs_sources(db: Session) -> list[tuple[Source, bool]]:
    results: list[tuple[Source, bool]] = []

    source, inserted = ensure_cnrs_source(db)
    results.append((source, inserted))
    return results


def main() -> None:
    db = SessionLocal()
    try:
        for source, inserted in seed_cnrs_sources(db):
            action = "inserted" if inserted else "skipped"
            print(
                f"{action}: id={source.id}, "
                f"external_id={source.external_id}, "
                f"config={source.config}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
