from __future__ import annotations

import argparse
from dataclasses import dataclass

from sqlalchemy import bindparam, text

from app.core.database import SessionLocal
from app.news.services.matching.condition_evidence_override import (
    has_flare_language,
    has_strike_language,
)


RELABEL_REASON = "relabeled_by_flare_guard"
REVIEW_REASON = (
    "Flare wording appears together with strike language; verify whether this "
    "message contains both a strike and flare bombs."
)


@dataclass(frozen=True)
class Plan:
    incident_id: str
    old_condition: str
    new_condition: str
    operation: str
    snippet: str


def _snippet(value: str | None) -> str:
    return " ".join((value or "").split())[:220]


def _plans() -> list[Plan]:
    with SessionLocal() as db:
        rows = db.execute(
            text(
                """
                SELECT
                    i.id::text AS incident_id,
                    c.action_en AS old_condition,
                    COALESCE(rm.raw_text, i.khabar, '') AS source_text
                FROM incidents i
                JOIN conditions c ON c.id = i.condition_id
                LEFT JOIN raw_messages rm ON rm.id = i.raw_message_id
                WHERE c.action_en = 'Bombs'
                  AND (
                    COALESCE(rm.raw_text, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
                    OR COALESCE(i.khabar, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
                  )
                ORDER BY i.event_date DESC, i.id
                """
            )
        ).mappings()
        plans: list[Plan] = []
        for row in rows:
            source_text = str(row["source_text"] or "")
            if not has_flare_language(source_text):
                continue
            operation = "flag"
            new_condition = row["old_condition"]
            if not has_strike_language(source_text):
                operation = "relabel"
                new_condition = "Flare Bomb"
            plans.append(
                Plan(
                    incident_id=row["incident_id"],
                    old_condition=row["old_condition"],
                    new_condition=new_condition,
                    operation=operation,
                    snippet=_snippet(source_text),
                )
            )
        return plans


def _apply(plans: list[Plan]) -> None:
    relabel_ids = [plan.incident_id for plan in plans if plan.operation == "relabel"]
    flag_ids = [plan.incident_id for plan in plans if plan.operation == "flag"]
    with SessionLocal() as db:
        if relabel_ids:
            db.execute(
                text(
                    """
                    UPDATE incidents
                    SET condition_id = (SELECT id FROM conditions WHERE action_en = 'Flare Bomb'),
                        note = concat_ws('; ', NULLIF(note, ''), :reason),
                        updated_at = now()
                    WHERE id::text IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": relabel_ids, "reason": RELABEL_REASON},
            )
        if flag_ids:
            db.execute(
                text(
                    """
                    UPDATE incidents
                    SET verification_status = 'needs_verification',
                        verification_reason = concat_ws('; ', NULLIF(verification_reason, ''), :reason),
                        updated_at = now()
                    WHERE id::text IN :ids
                    """
                ).bindparams(bindparam("ids", expanding=True)),
                {"ids": flag_ids, "reason": REVIEW_REASON},
            )
        db.commit()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    plans = _plans()
    relabel_count = sum(1 for plan in plans if plan.operation == "relabel")
    flag_count = sum(1 for plan in plans if plan.operation == "flag")
    print(f"planned relabels={relabel_count} flags={flag_count}")
    for plan in plans:
        print(
            f"{plan.operation}: {plan.incident_id} "
            f"{plan.old_condition} -> {plan.new_condition} | {plan.snippet}"
        )
    if args.apply:
        _apply(plans)
        print("Applied changes.")
    else:
        print("Dry run only. Re-run with --apply to write updates.")


if __name__ == "__main__":
    main()
