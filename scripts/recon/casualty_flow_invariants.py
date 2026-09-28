"""Check casualty status and verification-flag invariants on every live incident.

Read-only for I1-I7 and I10. I8 and I9 evaluate and simulate merges inside a
transaction that is always rolled back, and run only on the scratch database
``war_news_casualty_test`` (skipped elsewhere).

    python -m scripts.recon.casualty_flow_invariants --since 2026-08-17
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import select, text

from app.core.database import SessionLocal
from app.news.dtos.incident_dto import IncidentListParams
from app.news.models import Incident, IncidentUpdate, IncidentVerificationFlag, RawMessage, UpdateAction
from app.news.repositories.incident_repository import IncidentRepository
from app.news.services.casualty_flag_evaluator import CasualtyFlagEvaluator
from app.news.services.incident_details.casualty_status import target_location_count_from_extraction
from app.news.services.incident_details.casualty_text import find_count_mentions, has_explicit_none

SCRATCH_DB = "war_news_casualty_test"
KINDS = ("deaths", "injuries")
FLAG_KEYS = {"count_missing": "casualty_missing_number", "aggregate_no_breakdown": "casualty_aggregate_toll"}


class Report:
    def __init__(self) -> None:
        self.results: dict[str, dict[str, Any]] = {}

    def add(self, name: str, checked: int, failures: list[tuple[Any, str]], note: str = "") -> None:
        self.results[name] = {"checked": checked, "violations": len(failures), "failures": failures, "note": note}
        print(f"{name}: checked={checked} violations={len(failures)}{' (' + note + ')' if note else ''}")
        for incident_id, reason in failures[:10]:
            print(f"    {incident_id}: {reason}")


def _target_count(extraction: dict | None) -> int:
    extraction = extraction or {}
    return target_location_count_from_extraction(
        extraction.get("village"), extraction.get("village_roles"), extraction.get("sub_events")
    )


def _extracted(extraction: dict | None, kind: str) -> int | None:
    value = ((extraction or {}).get("casualties") or {}).get(kind)
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def load(db) -> dict[str, Any]:
    incidents = db.scalars(select(Incident)).all()
    messages = {
        row.id: row for row in db.execute(
            select(RawMessage.id, RawMessage.raw_text, RawMessage.extraction_result)
        ).all()
    }
    merged: dict[Any, list[int]] = defaultdict(list)
    admin_edited: dict[Any, set[str]] = defaultdict(set)
    for incident_id, action, values, performed_by in db.execute(
        select(IncidentUpdate.incident_id, IncidentUpdate.action, IncidentUpdate.new_values, IncidentUpdate.performed_by)
    ):
        values = values or {}
        raw_id = (values.get("merged_from") or {}).get("raw_message_id")
        if action == UpdateAction.pipeline_merge and isinstance(raw_id, int):
            merged[incident_id].append(raw_id)
        if performed_by is not None:
            admin_edited[incident_id].update(set(values) & {"deaths", "injuries", "total_deaths", "total_injuries"})
    flags = db.scalars(select(IncidentVerificationFlag)).all()
    return {"incidents": incidents, "messages": messages, "merged": merged, "admin_edited": admin_edited, "flags": flags}


def check_static(data: dict[str, Any], since: date, report: Report) -> None:
    incidents = {item.id: item for item in data["incidents"]}
    live = [item for item in incidents.values() if not item.is_deleted and item.verification_status != "rejected"]
    messages, merged, flags = data["messages"], data["merged"], data["flags"]
    open_flags = [flag for flag in flags if flag.status == "open" and flag.flag_type == "casualty_check"]
    open_by_incident: dict[Any, list] = defaultdict(list)
    for flag in open_flags:
        open_by_incident[flag.incident_id].append(flag)
    reviewed = {(flag.incident_id, flag.reason_code) for flag in flags if flag.status in ("resolved", "dismissed")}

    def text_of(raw_id):
        message = messages.get(raw_id)
        return (message.raw_text or "") if message else ""

    # I1 -- no open flag where nothing to check.
    failures = []
    for flag in open_flags:
        item = incidents.get(flag.incident_id)
        if item is None:
            failures.append((flag.incident_id, "flag on missing incident"))
        elif item.is_deleted:
            failures.append((item.id, f"open flag on deleted incident ({item.deleted_reason})"))
        elif item.verification_status == "rejected":
            failures.append((item.id, "open flag on rejected incident"))
        elif item.casualty_status in ("none_mentioned", "explicit_none"):
            failures.append((item.id, f"open {flag.reason_code} flag but casualty_status={item.casualty_status}"))
    report.add("I1", len(open_flags), failures)

    # I2 -- every flaggable incident in the window has exactly one open flag per reason.
    failures, checked, skips = [], 0, Counter()
    for item in live:
        wanted = []
        if "count_missing" in (item.casualty_deaths_status, item.casualty_injuries_status):
            wanted.append("count_missing")
        remaining = item.casualty_status_remaining_total or {}
        if item.casualty_status == "aggregate_only" and any(isinstance(v, int) and v > 0 for v in remaining.values()):
            wanted.append("aggregate_no_breakdown")
        if not wanted or item.created_at.date() < since:
            continue
        for reason in wanted:
            checked += 1
            count = sum(1 for flag in open_by_incident[item.id] if flag.reason_code == reason)
            if (item.id, reason) in reviewed:
                skips["previously_reviewed"] += 1
                if count:
                    failures.append((item.id, f"{reason}: reviewed but reopened"))
            elif item.verification_status == "verified" and data["admin_edited"].get(item.id):
                skips["verified_admin_edited"] += 1
            elif count != 1:
                failures.append((item.id, f"{reason}: {count} open flags, expected 1"))
    report.add("I2", checked, failures, f"logged skips {dict(skips)}")

    # I3 -- no open flag when both counts are exact.
    failures = [
        (flag.incident_id, f"open {flag.reason_code} but deaths/injuries both exact")
        for flag in open_flags
        if (item := incidents.get(flag.incident_id)) is not None
        and item.casualty_deaths_status == "exact" and item.casualty_injuries_status == "exact"
    ]
    report.add("I3", len(open_flags), failures)

    # I4 -- single-location counts are backed by a non-aggregate source extraction.
    failures, checked, unverifiable = [], 0, []
    for item in live:
        primary = messages.get(item.raw_message_id)
        if primary is None or _target_count(primary.extraction_result) > 1:
            continue
        for kind in KINDS:
            value = getattr(item, kind)
            if not isinstance(value, int) or value == 0 or kind in data["admin_edited"].get(item.id, set()):
                continue
            checked += 1
            sources = [primary] + [messages[r] for r in merged.get(item.id, []) if r in messages]
            backing = [m for m in sources if _extracted(m.extraction_result, kind) == value]
            if not backing:
                missing = sum(1 for r in merged.get(item.id, []) if r not in messages)
                reason = (f"{kind}={value} not in any available source extraction"
                          f" (msg {item.raw_message_id}; {missing} merged sources missing)")
                # A purged merged source may be the only backing: unverifiable, not a proven leak.
                (unverifiable if missing else failures).append((item.id, reason))
            elif all(_target_count(m.extraction_result) > 1 for m in backing):
                failures.append((item.id, f"{kind}={value} only from aggregate message {backing[0].id}"))
    report.add("I4", checked, failures, f"unverifiable (merged source purged): {len(unverifiable)} fields on "
               f"{len({i for i, _ in unverifiable})} incidents")
    for incident_id, reason in unverifiable:
        print(f"    unverifiable {incident_id}: {reason}")

    # I5 -- Bug A: the same non-zero count stamped on 2+ sibling rows without per-location evidence.
    failures, checked = [], 0
    siblings: dict[int, list] = defaultdict(list)
    for item in live:
        if item.raw_message_id is not None:
            siblings[item.raw_message_id].append(item)
    for raw_id, rows in siblings.items():
        if len(rows) < 2:
            continue
        checked += 1
        mentions = find_count_mentions(text_of(raw_id))
        for kind in KINDS:
            for value, count in Counter(getattr(r, kind) for r in rows if isinstance(getattr(r, kind), int)).items():
                if value == 0 or count < 2:
                    continue
                stated = sum(1 for m in mentions if m.kind == kind and m.value == value and m.counts_total)
                if stated < count:
                    ids = ",".join(str(r.id)[:8] for r in rows if getattr(r, kind) == value)
                    failures.append((raw_id, f"{kind}={value} on {count} rows ({ids}), stated {stated}x in text"))
    report.add("I5", checked, failures, "id column is the bulletin message id")

    # I6 -- count_missing must not fire when a singular/dual count word exists for that kind.
    failures, checked = [], 0
    for flag in open_flags:
        if flag.reason_code != "count_missing":
            continue
        checked += 1
        item = incidents.get(flag.incident_id)
        affected = set((flag.detail or {}).get("affected_types") or [])
        words = [m for m in find_count_mentions(text_of(item.raw_message_id) if item else "")
                 if m.rule in ("singular", "dual") and m.kind in affected]
        if words:
            failures.append((flag.incident_id, f"{words[0].kind} count word «{words[0].text}» (value {words[0].value})"))
    report.add("I6", checked, failures)

    # I7 -- a stored zero needs an explicit-none phrase in a source.
    failures, checked = [], 0
    for item in live:
        for kind in KINDS:
            if getattr(item, kind) != 0 or kind in data["admin_edited"].get(item.id, set()):
                continue
            checked += 1
            texts = [text_of(item.raw_message_id)] + [text_of(r) for r in merged.get(item.id, [])]
            if not any(has_explicit_none(t, kind) for t in texts if t):
                failures.append((item.id, f"{kind}=0 without explicit-none phrase"))
    report.add("I7", checked, failures)


def check_evaluator(db, data: dict[str, Any], since: date, report: Report) -> None:
    # I8 -- re-evaluating every live incident changes nothing (rolled back).
    evaluator = CasualtyFlagEvaluator(db, enabled=True)
    totals, failures, checked = Counter(), [], 0
    for item in data["incidents"]:
        if item.created_at.date() < since and item.id not in {f.incident_id for f in data["flags"]}:
            continue
        checked += 1
        result = evaluator.evaluate_incident(item.id)
        totals.update(result)
        if result["opened"] or result["updated"] or result["auto_cleared"]:
            failures.append((item.id, str(result)))
    db.rollback()
    report.add("I8", checked, failures, f"totals {dict(totals)}")


def check_merge(db, report: Report) -> None:
    # I9 -- aggregate merge leaves counts alone; flags survive a status reset; admin numbers survive.
    repo, failures, checked = IncidentRepository(db), [], 0
    target = db.scalar(select(Incident).join(IncidentVerificationFlag, IncidentVerificationFlag.incident_id == Incident.id).where(
        IncidentVerificationFlag.status == "open", IncidentVerificationFlag.reason_code == "count_missing",
        Incident.is_deleted.is_(False)).limit(1))
    aggregate = db.scalar(select(RawMessage).join(Incident, Incident.raw_message_id == RawMessage.id).where(
        Incident.casualty_status == "aggregate_only", Incident.is_deleted.is_(False)).limit(1))
    if target is None or aggregate is None:
        report.add("I9", 0, [], "no flagged single-location incident or aggregate message found")
        return
    casualties = (aggregate.extraction_result or {}).get("casualties") or {}
    agg_payload = {"deaths": casualties.get("deaths"), "injuries": casualties.get("injuries"),
                   "total_deaths": casualties.get("deaths"), "total_injuries": casualties.get("injuries"),
                   "khabar": aggregate.raw_text or "", "origin_villages": [], "mapped_fields": {},
                   "casualty_transitions": [], "casualty_status": "aggregate_only",
                   "casualty_deaths_status": "aggregate_only", "casualty_injuries_status": "aggregate_only",
                   "casualty_status_remaining_total": {"deaths": casualties.get("deaths") or 0}}
    before = (target.deaths, target.injuries, target.total_deaths, target.total_injuries)
    checked += 1
    repo.merge_existing(target, dict(agg_payload), aggregate.id)
    db.flush()
    after = (target.deaths, target.injuries, target.total_deaths, target.total_injuries)
    if after != before:
        failures.append((target.id, f"aggregate merge changed counts {before} -> {after}"))

    checked += 1
    target.verification_status = "auto_processed"
    db.flush()
    CasualtyFlagEvaluator(db, enabled=True).evaluate_incident(target.id)
    open_count = db.scalar(text("select count(*) from incident_verification_flags where incident_id=:i and status='open'"),
                           {"i": target.id})
    if not open_count:
        failures.append((target.id, "open flag lost after verification_status reset"))

    checked += 1
    db.add(IncidentUpdate(incident_id=target.id, action=UpdateAction.edit, old_values={"deaths": target.deaths},
                          new_values={"deaths": 7}, performed_by=db.scalar(text("select id from users limit 1"))))
    target.deaths = 7
    db.flush()
    single = {**agg_payload, "deaths": 2, "total_deaths": 2, "casualty_status": "exact",
              "casualty_deaths_status": "exact", "casualty_injuries_status": "none_mentioned",
              "casualty_status_remaining_total": {}}
    repo.merge_existing(target, single, target.raw_message_id)
    db.flush()
    if target.deaths != 7:
        failures.append((target.id, f"admin-entered deaths=7 overwritten by later merge -> {target.deaths}"))
    db.rollback()
    report.add("I9", checked, failures, f"target {target.id}, aggregate message {aggregate.id}; rolled back")


def check_list(db, report: Report) -> None:
    # I10 -- list counts and verification_type filters agree with the flag table.
    repo = IncidentRepository(db)

    def ids(**kwargs) -> tuple[set, int]:
        found, cursor, total = set(), None, 0
        while True:
            page = repo.list_all(IncidentListParams(limit=150, cursor=cursor, event_date_from=None, **kwargs))
            total = page.total
            found.update(item.id for item in page.items)
            cursor = page.next_cursor
            if not cursor:
                return found, total

    visible = """select distinct f.incident_id from incident_verification_flags f join incidents i on i.id=f.incident_id
                 where f.status='open' and f.flag_type='casualty_check' and (f.visible_after is null or f.visible_after<=now())
                 and not i.is_deleted {extra}"""
    flagged = {r[0] for r in db.execute(text(visible.format(extra="")))}
    duplicates = {r[0] for r in db.execute(text(
        "select id from incidents where not is_deleted and verification_status='needs_verification' and duplicate_flag"))}
    failures = []
    needs, needs_total = ids(verification_status="needs_verification")
    expected = flagged | duplicates
    if needs != expected or needs_total != len(expected):
        failures.append(("needs_verification", f"list={len(needs)} total={needs_total} expected={len(expected)} "
                         f"missing={len(expected - needs)} extra={len(needs - expected)}"))
    verified, _ = ids(verification_status="verified")
    if verified & flagged:
        failures.append(("verified", f"{len(verified & flagged)} flagged incidents listed as verified"))
    for reason, key in FLAG_KEYS.items():
        want = {r[0] for r in db.execute(text(visible.format(extra=f"and f.reason_code='{reason}'")))}
        got, _ = ids(verification_type=key)
        if got != want:
            failures.append((key, f"list={len(got)} expected={len(want)}"))
    got, _ = ids(verification_type="duplicate")
    if got != duplicates:
        failures.append(("duplicate", f"list={len(got)} expected={len(duplicates)}"))
    report.add("I10", 5, failures, f"needs_verification={len(expected)} (flagged {len(flagged)}, duplicates "
               f"{len(duplicates)}, overlap {len(flagged & duplicates)})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--since", type=date.fromisoformat, default=date(2026, 8, 17))
    args = parser.parse_args()
    report = Report()
    with SessionLocal() as db:
        database = db.execute(text("select current_database()")).scalar()
        print(f"database={database} since={args.since} at={datetime.now(timezone.utc).isoformat()}")
        db.execute(text("set transaction read only"))
        data = load(db)
        print(f"live incidents={sum(1 for i in data['incidents'] if not i.is_deleted)} flags={len(data['flags'])}")
        check_static(data, args.since, report)
        check_list(db, report)
        db.rollback()
        if database == SCRATCH_DB:
            check_evaluator(db, load(db), args.since, report)
            check_merge(db, report)
        else:
            print("I8/I9 skipped: they write inside a rolled-back transaction and run only on the scratch DB")
    print("summary: " + ", ".join(f"{k}={v['violations']}" for k, v in report.results.items()))


if __name__ == "__main__":
    main()
