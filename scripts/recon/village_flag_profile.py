"""Read-only recon: profile incidents flagged for low-confidence village matches.

Re-runs the *current* village candidate resolution on each flagged incident's
own raw village string and reports stored vs current score/status plus the top
candidates. Performs SELECTs only.

    docker compose exec -T backend python -m scripts.recon.village_flag_profile
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

from sqlalchemy import text

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.core.database import SessionLocal
from app.news.repositories.condition_repository import ConditionRepository
from app.news.repositories.village_repository import VillageRepository
from app.news.services.matching.matching_service import (
    LOW_CONFIDENCE_THRESHOLD,
    MATCH_THRESHOLD,
    MatchingService,
)

REASON = "Low-confidence village match requires manual review."
QUERY = text(
    """
    select i.id::text as incident_id, i.raw_message_id, i.village_id,
           r.match_result as mr
    from incidents i join raw_messages r on r.id = i.raw_message_id
    where not i.is_deleted
      and i.verification_status = 'needs_verification'
      and i.verification_reason = :reason
      and i.event_date between :d0 and :d1
    order by i.event_date
    """
)


def _own_match(mr: dict, village_id: int | None) -> dict | None:
    for vm in (mr or {}).get("village_matches") or []:
        if vm.get("matched_village_id") == village_id:
            return vm
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from", dest="d0", default="2026-08-20")
    parser.add_argument("--to", dest="d1", default="2026-09-30")
    parser.add_argument(
        "--output", default="scripts/output/village_flag_profile.csv"
    )
    args = parser.parse_args()

    processed = succeeded = failed = 0
    rows: list[dict] = []
    with SessionLocal() as db:
        service = MatchingService(VillageRepository(db), ConditionRepository(db))
        for rec in db.execute(
            QUERY, {"reason": REASON, "d0": args.d0, "d1": args.d1}
        ).mappings():
            processed += 1
            try:
                mr = rec["mr"] or {}
                vm = _own_match(mr, rec["village_id"]) or {}
                raw = vm.get("raw_village_text") or ""
                res = service._resolve_village_candidates(
                    raw, qualifier_text=vm.get("qualifier_text")
                )
                cands = [
                    f"{c.ref_name_ar or c.acs_name}#{c.id}:{s:.2f}"
                    for c, s in res.candidates[:3]
                ]
                rows.append(
                    {
                        "incident_id": rec["incident_id"],
                        "raw": raw,
                        "n_villages": len(mr.get("village_matches") or []),
                        "location_ambiguity": bool(mr.get("location_ambiguity")),
                        "stored_status": vm.get("village_match_status"),
                        "stored_conf": vm.get("village_confidence"),
                        "stored_alias": vm.get("alias_matched"),
                        "cur_status": res.classified.status.value
                        if hasattr(res.classified.status, "value")
                        else str(res.classified.status),
                        "cur_conf": res.classified.confidence,
                        "cur_matched_id": res.classified.matched_id,
                        "stored_matched_id": rec["village_id"],
                        "collision_like": res.collision_like,
                        "alias_hit": res.alias_hit,
                        "top1": cands[0] if len(cands) > 0 else "",
                        "top2": cands[1] if len(cands) > 1 else "",
                        "top3": cands[2] if len(cands) > 2 else "",
                    }
                )
                succeeded += 1
            except Exception as exc:  # noqa: BLE001 - recon script keeps going
                failed += 1
                print(f"FAILED {rec['incident_id']}: {exc}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if rows:
        with out.open("w", newline="", encoding="utf-8-sig") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    print(json.dumps({"processed": processed, "succeeded": succeeded, "failed": failed}))
    print("thresholds:", {"MATCH": MATCH_THRESHOLD, "LOW": LOW_CONFIDENCE_THRESHOLD})
    print("stored->current status:", Counter((r["stored_status"], r["cur_status"]) for r in rows))
    print("collision_like:", Counter(r["collision_like"] for r in rows))
    print("same matched id:", Counter(r["cur_matched_id"] == r["stored_matched_id"] for r in rows))


if __name__ == "__main__":
    main()
