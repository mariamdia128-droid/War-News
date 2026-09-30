"""Re-run village matching for village-flagged incidents (dry run by default).

For every live incident in the date range whose stored review reason is the
low-confidence village one, this re-matches the village with the CURRENT matcher
and reports what would change: village, flag, and match method. It writes the
UPDATE statements to ``scripts/sql/village_reprocess.sql`` and a per-incident CSV
instead of executing anything. ``--apply`` runs the same updates in one
transaction per incident; it is meant to be used by hand after reviewing the
report.

    docker compose exec -T backend python scripts/reprocess_village_flags.py
    docker compose exec -T backend python scripts/reprocess_village_flags.py --apply

Categories
  cleared_same_village       flag cleared, village unchanged
  cleared_village_changed    flag cleared and village_id would change
  still_flagged              village still unresolved (reason recorded)
  other_reason_remains       village resolved but another review signal remains
  no_replacement_village     new matcher finds no Lebanese village; the incident
                             is left exactly as it is (never removed)
  failed                     could not be re-matched

Every batch returns a processed / succeeded / failed summary.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import text

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.core.config import settings
from app.core.database import SessionLocal
from app.llm.dtos import ExtractionResult
from app.news.dtos import MatchResultStatus
from app.news.repositories.condition_repository import ConditionRepository
from app.news.repositories.village_repository import VillageRepository
try:
    from app.news.services.materialization.verification_signals import (
        LOW_CONFIDENCE_VILLAGE_REVIEW_REASON,
        active_non_duplicate_verification_reasons,
    )
except ImportError as exc:  # pragma: no cover - depends on the review-signal work
    raise SystemExit(
        "verification_signals.active_non_duplicate_verification_reasons is required "
        f"(commit the review-signal changes first): {exc}"
    )
from app.news.services.matching.matching_service import (
    MATCH_TIE_MARGIN,
    VILLAGE_CONFIDENT_FLOOR,
    MatchingService,
)

DEFAULT_SQL_OUT = Path("scripts/sql/village_reprocess.sql")
DEFAULT_CSV_OUT = Path("scripts/output/village_reprocess.csv")

QUERY = text(
    """
    select i.id::text as incident_id, i.village_id, i.village_display_name,
           i.duplicate_flag, i.verification_status, i.verification_reason,
           r.id as raw_id, r.extraction_result, r.match_result,
           r.cnrs_classification, coalesce(r.tier2_retry_count, 0) as tier2_retries
    from incidents i join raw_messages r on r.id = i.raw_message_id
    where not i.is_deleted
      and i.verification_status = 'needs_verification'
      and i.verification_reason = :reason
      and i.event_date between :d0 and :d1
    order by i.event_date, i.id
    """
)


@dataclass
class Plan:
    incident_id: str
    raw_id: int
    raw_text: str
    category: str
    old_village_id: int | None
    old_village: str
    new_village_id: int | None
    new_village: str
    method: str | None
    detail: str
    old_display_name: str | None = None
    new_display_name: str | None = None
    top_candidates: list[str] = field(default_factory=list)

    @property
    def clears_flag(self) -> bool:
        return self.category in {"cleared_same_village", "cleared_village_changed"}

    @property
    def changes_village(self) -> bool:
        return self.category == "cleared_village_changed"


def _sql_literal(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def _statement(plan: Plan) -> tuple[str, dict]:
    sets = [
        "verification_status = 'auto_processed'",
        "verification_reason = NULL",
        "version = version + 1",
        "updated_at = now()",
    ]
    params: dict = {"id": plan.incident_id, "reason": LOW_CONFIDENCE_VILLAGE_REVIEW_REASON}
    if plan.changes_village:
        sets += ["village_id = :village_id", "village_display_name = :display"]
        params.update(village_id=plan.new_village_id, display=plan.new_display_name)
    sql = (
        "UPDATE incidents SET " + ", ".join(sets) + " WHERE id = :id "
        "AND verification_status = 'needs_verification' "
        "AND verification_reason = :reason"
    )
    return sql, params


def _render(sql: str, params: dict) -> str:
    rendered = sql
    # Longest names first so ":village_id" is never clobbered by ":id".
    for key in sorted(params, key=len, reverse=True):
        rendered = rendered.replace(f":{key}", _sql_literal(params[key]))
    return rendered + ";"


def _own_entry(match_result: dict, village_id: int | None) -> dict | None:
    for entry in (match_result or {}).get("village_matches") or []:
        if entry.get("matched_village_id") == village_id:
            return entry
    return None


def _new_entry(new_matches: list[dict], old_entry: dict) -> dict | None:
    raw = (old_entry.get("raw_village_text") or "").strip()
    role = old_entry.get("village_role")
    same_text = [m for m in new_matches if (m.get("raw_village_text") or "").strip() == raw]
    for entry in same_text:
        if entry.get("village_role") == role:
            return entry
    return same_text[0] if same_text else None


def _still_flagged_reason(service: MatchingService, entry: dict, ambiguity: bool) -> tuple[str, list[str]]:
    resolution = service._resolve_village_candidates(
        entry.get("raw_village_text"), qualifier_text=entry.get("qualifier_text")
    )
    tops = [
        f"{(c.ref_name_ar or c.acs_name)}#{c.id}:{s:.2f}"
        for c, s in resolution.candidates[:2]
    ]
    if not resolution.candidates or entry.get("village_match_status") == "unmatched":
        return "no_candidate", tops
    if (
        ambiguity
        and entry.get("village_review_required")
        and resolution.classified.status == MatchResultStatus.matched
    ):
        # The name alone resolves; only the bulletin's ambiguity flags it.
        return "location_ambiguity", tops
    confidence = float(entry.get("village_confidence") or 0.0)
    second = resolution.candidates[1][1] if len(resolution.candidates) > 1 else 0.0
    if confidence < VILLAGE_CONFIDENT_FLOOR:
        return "below_floor", tops
    if resolution.collision_like:
        return "same_name_collision", tops
    if confidence - second < MATCH_TIE_MARGIN:
        return "tie_between_distinct_places", tops
    # Clear score margin, but the name shares no whole word with the candidate
    # (Latin script, typos) or covers only part of the mention.
    return "name_not_covered_by_candidate", tops


def build_plans(db, service: MatchingService, names: dict[int, str], args) -> tuple[list[Plan], Counter]:
    summary: Counter = Counter()
    plans: list[Plan] = []
    match_cache: dict[int, tuple[list[dict], dict]] = {}
    rows = db.execute(
        QUERY,
        {"reason": LOW_CONFIDENCE_VILLAGE_REVIEW_REASON, "d0": args.d0, "d1": args.d1},
    ).mappings()
    for row in rows:
        summary["processed"] += 1
        try:
            old_entry = _own_entry(row["match_result"], row["village_id"]) or {}
            raw_text = old_entry.get("raw_village_text") or ""
            old_name = names.get(row["village_id"], "")
            if row["raw_id"] not in match_cache:
                extraction = ExtractionResult(**row["extraction_result"])
                result = service.match(
                    extraction, cnrs_classification=row["cnrs_classification"]
                )
                match_cache[row["raw_id"]] = (
                    [m.model_dump(mode="json") for m in result.village_matches],
                    result.model_dump(mode="json"),
                )
            new_matches, new_dto = match_cache[row["raw_id"]]
            entry = _new_entry(new_matches, old_entry) if old_entry else None
            if entry is None:
                raise ValueError("no matching village entry after re-match")
            new_id = entry.get("matched_village_id")
            base = dict(
                incident_id=row["incident_id"],
                raw_id=row["raw_id"],
                raw_text=raw_text,
                old_village_id=row["village_id"],
                old_village=old_name,
                new_village_id=new_id,
                new_village=names.get(new_id, "") if new_id else "",
                method=entry.get("village_match_method"),
                old_display_name=row["village_display_name"],
                new_display_name=(raw_text.strip() or None)
                if entry.get("alias_matched")
                else None,
            )
            confident = entry.get("village_match_status") == "matched" and new_id is not None
            if not confident:
                reason, tops = _still_flagged_reason(
                    service, entry, bool(new_dto.get("location_ambiguity"))
                )
                category = "no_replacement_village" if new_id is None else "still_flagged"
                plans.append(Plan(category=category, detail=reason, top_candidates=tops, **base))
                summary[category] += 1
                summary["succeeded"] += 1
                continue
            # Only the village evidence is re-evaluated: keep the stored
            # condition/casualty signals so "other reasons" means reasons that
            # already applied to this incident, not artefacts of a re-match.
            village_fields = (
                "matched_village_id", "village_confidence", "village_match_status",
                "village_review_required", "village_match_method",
            )
            combined = {**(row["match_result"] or {})}
            combined["village_matches"] = [
                {**stored, **{k: entry.get(k) for k in village_fields}}
                if stored is old_entry
                else stored
                for stored in (row["match_result"] or {}).get("village_matches") or []
            ]
            combined["any_village_low_confidence"] = entry.get("village_match_status") != "matched"
            remaining = active_non_duplicate_verification_reasons(
                match_result=combined,
                extraction_result=row["extraction_result"],
                tier2_retry_count=int(row["tier2_retries"] or 0),
                tier2_retry_limit=settings.extraction_max_retries,
                verification_reason=None,
                village_id=new_id,
            )
            if remaining or row["duplicate_flag"]:
                detail = ",".join(sorted(remaining)) or "duplicate_flag"
                plans.append(Plan(category="other_reason_remains", detail=detail, **base))
                summary["other_reason_remains"] += 1
            else:
                category = (
                    "cleared_same_village" if new_id == row["village_id"] else "cleared_village_changed"
                )
                plans.append(Plan(category=category, detail=entry.get("village_match_note") or "", **base))
                summary[category] += 1
            summary["succeeded"] += 1
        except Exception as exc:  # noqa: BLE001 - one bad incident must not stop the batch
            summary["failed"] += 1
            plans.append(
                Plan(
                    incident_id=row["incident_id"], raw_id=row["raw_id"], raw_text="",
                    category="failed", old_village_id=row["village_id"],
                    old_village=names.get(row["village_id"], ""), new_village_id=None,
                    new_village="", method=None, detail=str(exc)[:200],
                )
            )
    return plans, summary


def write_outputs(plans: list[Plan], sql_out: Path, csv_out: Path) -> None:
    sql_out.parent.mkdir(parents=True, exist_ok=True)
    csv_out.parent.mkdir(parents=True, exist_ok=True)
    with csv_out.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh)
        writer.writerow(
            ["incident_id", "category", "detail", "raw_village", "old_village_id", "old_village",
             "new_village_id", "new_village", "method", "old_flag", "new_flag", "top_candidates"]
        )
        for p in plans:
            writer.writerow(
                [p.incident_id, p.category, p.detail, p.raw_text, p.old_village_id, p.old_village,
                 p.new_village_id, p.new_village, p.method, "needs_verification",
                 "auto_processed" if p.clears_flag else "needs_verification",
                 " ; ".join(p.top_candidates)]
            )
    same = [p for p in plans if p.category == "cleared_same_village"]
    changed = [p for p in plans if p.changes_village]
    lines = [
        "-- Generated by scripts/reprocess_village_flags.py. NOT executed by the script.",
        "-- Review scripts/output/village_reprocess.csv first. Run section A and B separately.",
        "-- exact_hash is NOT recomputed for section B (it depends on the event hash suffix).",
        "-- Each UPDATE only fires while the incident still carries the village reason.",
        "",
        f"-- Section A: flag cleared, village unchanged ({len(same)} incidents)",
        "BEGIN;",
    ]
    for p in same:
        lines.append(_render(*_statement(p)))
    lines += ["COMMIT;", "", f"-- Section B: flag cleared AND village_id changed ({len(changed)} incidents)", "BEGIN;"]
    for p in changed:
        lines.append(f"-- {p.raw_text!r}: {p.old_village} ({p.old_village_id}) -> {p.new_village} ({p.new_village_id}), method={p.method}")
        lines.append(_render(*_statement(p)))
    lines += ["COMMIT;", ""]
    sql_out.write_text("\n".join(lines), encoding="utf-8")


def apply_plans(db, plans: list[Plan]) -> Counter:
    result: Counter = Counter()
    for plan in plans:
        if not plan.clears_flag:
            continue
        result["processed"] += 1
        try:
            sql, params = _statement(plan)
            outcome = db.execute(text(sql), params)
            db.commit()
            result["succeeded" if outcome.rowcount else "skipped_not_matching_anymore"] += 1
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            result["failed"] += 1
            print(f"APPLY FAILED {plan.incident_id}: {exc}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--from", dest="d0", default="2026-08-20")
    parser.add_argument("--to", dest="d1", default="2026-09-30")
    parser.add_argument("--sql-out", type=Path, default=DEFAULT_SQL_OUT)
    parser.add_argument("--csv-out", type=Path, default=DEFAULT_CSV_OUT)
    parser.add_argument("--apply", action="store_true", help="execute the UPDATEs (default: dry run)")
    args = parser.parse_args()

    with SessionLocal() as db:
        names = {
            row[0]: row[1] or ""
            for row in db.execute(text("select id, coalesce(ref_name_ar, acs_name) from villages"))
        }
        service = MatchingService(VillageRepository(db), ConditionRepository(db))
        plans, summary = build_plans(db, service, names, args)
        write_outputs(plans, args.sql_out, args.csv_out)
        print(json.dumps({k: summary[k] for k in ("processed", "succeeded", "failed")}))
        for category in ("cleared_same_village", "cleared_village_changed", "still_flagged",
                         "other_reason_remains", "no_replacement_village", "failed"):
            print(f"{category}: {sum(1 for p in plans if p.category == category)}")
        print("\nstill flagged by reason:",
              dict(Counter(p.detail for p in plans if p.category == "still_flagged")))
        print("\nVillage would CHANGE (raw | old -> new | method):")
        for p in plans:
            if p.changes_village:
                print(f"  {p.raw_text} | {p.old_village}#{p.old_village_id} -> {p.new_village}#{p.new_village_id} | {p.method} | {p.incident_id}")
        print("\nWrong village stays, no Lebanese replacement (left untouched):")
        for p in plans:
            if p.category == "no_replacement_village":
                print(f"  {p.raw_text} | {p.old_village}#{p.old_village_id} | {p.incident_id}")
        print(
            "\nCNRS export check: no outbound webhook/export log exists in the database "
            "or code ('CNRS Webhook' is an inbound source), so already-sent incidents "
            "cannot be listed. Nothing is resent by this script."
        )
        print(f"SQL written to {args.sql_out}; report to {args.csv_out}")
        if args.apply:
            print("APPLY:", json.dumps(dict(apply_plans(db, plans))))
        else:
            print("Dry run: nothing was executed.")


if __name__ == "__main__":
    main()
