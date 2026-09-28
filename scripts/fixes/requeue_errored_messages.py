"""Preview or re-queue parked raw messages (status error / held_for_review).

Dry-run by default: prints counts per reason and plan, 10 examples and writes
scripts/fixes/out/requeue_errored_messages_dryrun.csv inside a READ ONLY
transaction. With --apply, eligible messages are reset to the state the
existing stage claims pick up (claim_pending_match / claim_pending_extraction);
the running pipeline does the rest. Each requeue appends an audit entry to
raw_messages.filter_result["requeue_history"].

Rematch messages first re-run the existing extraction finalizer
(finalize_extraction_action) so pre-override actions such as «غارة» become
"Bombs" before matching. No LLM call is made by this script.

Never requeued: exact-hash duplicates, air-violation routes, irrelevant posts,
messages that already have a live incident, and non-transient LLM failures.

Usage:
  python -m scripts.fixes.requeue_errored_messages [--since 2026-08-17] [--reason "unmatched or missing condition"]
  python -m scripts.fixes.requeue_errored_messages --include-no-place-reextract   # adds ~150 s of LLM per message
  python -m scripts.fixes.requeue_errored_messages --apply
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy import or_, select, text
from sqlalchemy.orm import defer

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.core.database import SessionLocal
from app.llm.dtos import ExtractionResult
from app.llm.services.action_finalization import finalize_extraction_action
from app.news.models import Incident, MessageStatus, RawMessage
from app.news.repositories.raw_message_repository import RawMessageRepository
from app.news.services.pipeline.errored_message_requeue import (
    PLAN_REEXTRACT,
    PLAN_REMATCH,
    PLAN_SKIP,
    classify_errored_message,
)

OUT = Path(__file__).resolve().parent / "out" / "requeue_errored_messages_dryrun.csv"
AUDIT_SOURCE = "scripts.fixes.requeue_errored_messages"


def _refinalized(message: RawMessage) -> tuple[dict, str | None, str | None]:
    """Return (extraction_json, old_action, new_action) via the pipeline finalizer."""
    stored = dict(message.extraction_result or {})
    old_action = stored.get("action_description")
    try:
        result = finalize_extraction_action(
            ExtractionResult.model_validate(stored),
            post_text=message.raw_text or "",
            cnrs_classification=message.cnrs_classification,
        )
    except Exception:
        return stored, old_action, old_action
    return result.model_dump(mode="json"), old_action, result.action_description


def _live_incident_ids(db, message_ids: list[int]) -> set[int]:
    if not message_ids:
        return set()
    return set(
        db.scalars(
            select(Incident.raw_message_id).where(
                Incident.raw_message_id.in_(message_ids),
                Incident.is_deleted.is_(False),
            )
        ).all()
    )


def _enum_has_value(db, value: str) -> bool:
    return bool(
        db.scalar(
            text(
                "SELECT EXISTS (SELECT 1 FROM pg_enum e JOIN pg_type t ON t.oid = e.enumtypid "
                "WHERE t.typname = 'message_status' AND e.enumlabel = :value)"
            ),
            {"value": value},
        )
    )


def _candidates(db, since: date | None, reason: str | None) -> list[RawMessage]:
    # held_for_review / failed_stage only exist after migrations 0064/0065;
    # the dry-run must also work on a database that is not upgraded yet.
    statuses = [MessageStatus.error.value]
    if _enum_has_value(db, "held_for_review"):
        statuses.append(MessageStatus.held_for_review.value)
    query = (
        select(RawMessage)
        .options(defer(RawMessage.failed_stage))
        .where(RawMessage.status.in_(statuses))
    )
    if since is not None:
        cutoff = datetime.combine(since, datetime.min.time(), tzinfo=timezone.utc)
        query = query.where(
            or_(RawMessage.message_datetime >= cutoff, RawMessage.received_at >= cutoff)
        )
    if reason:
        query = query.where(RawMessage.error_message.ilike(f"%{reason}%"))
    return list(db.scalars(query.order_by(RawMessage.id)).all())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--since", type=date.fromisoformat, default=None)
    parser.add_argument("--reason", default=None, help="case-insensitive substring of error_message")
    parser.add_argument("--include-no-place-reextract", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        if not args.apply:
            db.execute(text("SET TRANSACTION READ ONLY"))
        messages = _candidates(db, args.since, args.reason)
        live = _live_incident_ids(db, [message.id for message in messages])

        rows: list[dict] = []
        plans: list[tuple[RawMessage, str, dict | None]] = []
        by_reason_plan: Counter = Counter()
        action_changes: Counter = Counter()
        for message in messages:
            decision = classify_errored_message(
                message,
                has_live_incident=message.id in live,
                include_no_place_reextract=args.include_no_place_reextract,
            )
            by_reason_plan[(decision.reason_group, decision.plan, decision.skip_reason or "")] += 1
            extraction, old_action, new_action = (None, None, None)
            if decision.plan == PLAN_REMATCH:
                extraction, old_action, new_action = _refinalized(message)
                if new_action != old_action:
                    action_changes[f"{old_action!r} -> {new_action!r}"] += 1
            plans.append((message, decision.plan, extraction))
            rows.append(
                {
                    "raw_message_id": message.id,
                    "source": message.source_name,
                    "message_day": message.message_datetime.date() if message.message_datetime else None,
                    "status": getattr(message.status, "value", message.status),
                    "reason_group": decision.reason_group,
                    "plan": decision.plan,
                    "skip_reason": decision.skip_reason,
                    "old_action": old_action,
                    "new_action": new_action,
                    "text": " ".join((message.raw_text or "").split())[:200],
                }
            )

        OUT.parent.mkdir(parents=True, exist_ok=True)
        with OUT.open("w", encoding="utf-8-sig", newline="") as handle:
            fields = ("raw_message_id", "source", "message_day", "status", "reason_group", "plan",
                      "skip_reason", "old_action", "new_action", "text")
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

        plan_counts = Counter(row["plan"] for row in rows)
        print(f"candidates: {len(rows)}  plans: {dict(plan_counts)}")
        print("per reason / plan / skip_reason:")
        for (group, plan, why), count in sorted(by_reason_plan.items(), key=lambda item: -item[1]):
            print(f"  {count:5d}  {plan:9s} {why:32s} {group}")
        print("re-finalized action changes (top 15):")
        for change, count in action_changes.most_common(15):
            print(f"  {count:5d}  {change}")
        print("examples:")
        for row in [r for r in rows if r["plan"] != PLAN_SKIP][:10]:
            print(f"  #{row['raw_message_id']} {row['plan']} [{row['reason_group'][:45]}] "
                  f"{row['old_action']!r}->{row['new_action']!r} :: {row['text'][:110]}")
        print(f"csv: {OUT}")

        if not args.apply:
            db.rollback()
            print("dry-run: nothing written (pass --apply to requeue)")
            return

        repository = RawMessageRepository(db)
        stats = {"processed": 0, "succeeded": 0, "failed": 0}
        for message, plan, extraction in plans:
            if plan == PLAN_SKIP:
                continue
            stats["processed"] += 1
            audit = {"source": AUDIT_SOURCE, "plan": plan}
            try:
                with db.begin_nested():
                    if plan == PLAN_REMATCH:
                        repository.requeue_for_matching(message, extraction_result=extraction or {}, audit=audit)
                    elif plan == PLAN_REEXTRACT:
                        repository.requeue_for_extraction(message, audit=audit)
                stats["succeeded"] += 1
            except Exception as exc:  # keep going; report at the end
                stats["failed"] += 1
                print(f"  failed #{message.id}: {type(exc).__name__}: {exc}")
        db.commit()
        print(f"apply: {stats}")


if __name__ == "__main__":
    main()
