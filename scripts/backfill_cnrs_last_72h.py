"""One-off backfill: pull the last N hours of real CNRS posts for manual testing.

Inserts into raw_messages under a dedicated "CNRS Webhook (backfill)" source
row so this never touches the live cnrs-poll-worker's resume cursor (which is
derived from MAX(external_message_id) scoped to the live source_id only).
Safe to re-run: duplicate (source_id, external_message_id) rows are skipped.

Usage: docker compose exec backend python scripts/backfill_cnrs_last_72h.py [hours]
"""

import argparse
import logging
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.database import SessionLocal
from app.news.models import MessageStatus, RawMessage
from app.sources.actions.ingest_source_action import _derive_platform_from_external_id
from app.sources.models import Source
from app.sources.repositories.source_repository import SourceRepository
from app.sources.services.cnrs_source import CNRSSourceProvider
from scripts.cnrs_poll_worker import _parse_message_datetime, min_datetime_from_hours

logger = logging.getLogger(__name__)

BACKFILL_SOURCE_EXTERNAL_ID = "cnrs_webhook_backfill"
LIVE_SOURCE_EXTERNAL_ID = "cnrs_webhook"
PAGE_LIMIT = 2000


def _get_or_create_backfill_source(repo: SourceRepository) -> Source:
    existing = repo.get_active_by_external_id(BACKFILL_SOURCE_EXTERNAL_ID)
    if existing is not None:
        return existing

    live_source = repo.get_active_by_external_id(LIVE_SOURCE_EXTERNAL_ID)
    if live_source is None:
        raise RuntimeError(f"Live source {LIVE_SOURCE_EXTERNAL_ID!r} not found.")

    source = Source(
        type=live_source.type,
        name="CNRS Webhook (backfill)",
        external_id=BACKFILL_SOURCE_EXTERNAL_ID,
        config=dict(live_source.config or {}),
        auth_secret_ref=live_source.auth_secret_ref,
        is_active=True,
    )
    repo.db.add(source)
    repo.db.commit()
    repo.db.refresh(source)
    return source


def _find_after_id_for_cutoff(
    provider: CNRSSourceProvider,
    cutoff: datetime,
    *,
    lo: int = 0,
    hi: int = 1_000_000,
) -> int:
    """Binary-search the CNRS post id space for the id just before cutoff."""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        items, _next_cursor, _has_more = provider.fetch_batch(cursor=str(mid), limit=1)
        if not items:
            hi = mid - 1
            continue
        message_datetime = _parse_message_datetime(items[0].get("message_datetime"))
        if message_datetime is not None and message_datetime < cutoff:
            lo = mid
        else:
            hi = mid - 1
    return lo


def run_backfill(hours: int) -> dict[str, int]:
    db = SessionLocal()
    try:
        repo = SourceRepository(db)
        source = _get_or_create_backfill_source(repo)
        source_id = source.id

        provider = CNRSSourceProvider(config=source.config, api_key=settings.cnrs_api_key)
        started_at = datetime.now(timezone.utc)
        cutoff = min_datetime_from_hours(hours, now=started_at)
        assert cutoff is not None

        current_cursor = str(_find_after_id_for_cutoff(provider, cutoff))
        logger.info("Backfilling CNRS posts after_id=%s (cutoff=%s)", current_cursor, cutoff)

        fetched = 0
        inserted = 0
        duplicates = 0
        failed = 0

        while True:
            items, next_cursor, has_more = provider.fetch_batch(
                cursor=current_cursor, limit=PAGE_LIMIT
            )
            fetched += len(items)

            for item in items:
                try:
                    message_datetime = _parse_message_datetime(item.get("message_datetime"))
                    if message_datetime is not None and message_datetime < cutoff:
                        continue

                    source_platform = item.get(
                        "source_platform"
                    ) or _derive_platform_from_external_id(item.get("external_message_id"))
                    source_name = item.get("source_name") or source.name

                    repo.add_raw_message(
                        RawMessage(
                            source_id=source_id,
                            external_message_id=item.get("external_message_id"),
                            source_platform=source_platform,
                            source_name=source_name,
                            origin_platform=item.get("origin_platform") or source_platform,
                            origin_account=item.get("origin_account") or source_name,
                            cnrs_classification=item.get("cnrs_classification") or None,
                            raw_text=item.get("raw_text"),
                            raw_payload=item.get("raw_payload") or item,
                            message_datetime=message_datetime,
                            status=MessageStatus.pending,
                        )
                    )
                    inserted += 1
                except IntegrityError as exc:
                    if not repo.is_duplicate_raw_message_error(exc):
                        failed += 1
                        repo.rollback()
                        raise
                    duplicates += 1
                except Exception:
                    failed += 1
                    logger.exception(
                        "Failed to backfill CNRS post external_message_id=%s",
                        item.get("external_message_id"),
                    )

            repo.commit()
            current_cursor = str(next_cursor) if next_cursor else current_cursor
            if not has_more or not items:
                break

        summary = {"fetched": fetched, "inserted": inserted, "duplicates": duplicates, "failed": failed}
        logger.info("CNRS backfill complete: %s", summary)
        return summary
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hours", nargs="?", type=int, default=72)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    summary = run_backfill(args.hours)
    logger.info("Backfill summary: %s", summary)


if __name__ == "__main__":
    main()
