"""Read-only recon: why village ties are not resolved by bulletin geo context.

For every raw message behind a village-flagged incident, re-resolve each village
mention with the current matcher and report, for the still-low mentions, whether
the bulletin has anchors, whether the tied candidates have coordinates, and how
far each candidate is from the nearest anchor. SELECTs only.

    docker compose exec -T backend python - < scripts/recon/tie_geo_probe.py
"""

from __future__ import annotations

import json
from collections import Counter

from sqlalchemy import text

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.core.config import settings
from app.core.database import SessionLocal
from app.llm.dtos import ExtractionResult
from app.news.repositories.condition_repository import ConditionRepository
from app.news.repositories.village_repository import VillageRepository
from app.news.services.matching.matching_service import MatchingService

QUERY = text(
    """
    select distinct r.id, r.extraction_result
    from incidents i join raw_messages r on r.id = i.raw_message_id
    where not i.is_deleted and i.verification_status = 'needs_verification'
      and i.verification_reason = 'Low-confidence village match requires manual review.'
      and i.event_date between '2026-08-20' and '2026-09-30'
    """
)


def main() -> None:
    processed = succeeded = failed = 0
    outcome = Counter()
    examples: list[dict] = []
    with SessionLocal() as db:
        service = MatchingService(VillageRepository(db), ConditionRepository(db))
        for row in db.execute(QUERY).mappings():
            processed += 1
            try:
                extraction = ExtractionResult(**row["extraction_result"])
                mentions = MatchingService._village_mentions(extraction)
                resolutions = [
                    service._resolve_village_candidates(
                        m.village, qualifier_text=m.qualifier_text
                    )
                    for m in mentions
                ]
                anchors = [
                    r.candidates[0][0] for r in resolutions if service._is_anchor(r)
                ]
                for mention, res in zip(mentions, resolutions, strict=True):
                    if service._is_anchor(res):
                        outcome["confident_anchor"] += 1
                        continue
                    geo = service._resolve_with_geo_context(res, anchors)
                    if geo.resolved_by_geo_context:
                        outcome["resolved_by_geo"] += 1
                        continue
                    top = res.candidates[:3]
                    with_coords = [
                        c
                        for c, _s in top
                        if getattr(c, "coord_x", None) is not None
                    ]
                    reason = (
                        "no_anchor_in_bulletin"
                        if not anchors
                        else "candidates_without_coords"
                        if len(with_coords) < 2
                        else "no_distance_advantage_or_too_far"
                    )
                    outcome[f"unresolved:{reason}"] += 1
                    if len(examples) < 12 and anchors and len(with_coords) >= 2:
                        examples.append(
                            {
                                "raw": mention.village,
                                "anchors": [a.ref_name_ar for a in anchors][:3],
                                "candidates": [
                                    (
                                        c.ref_name_ar,
                                        round(
                                            service._nearest_anchor(c, anchors)[0]
                                        ),
                                    )
                                    for c in with_coords
                                ],
                            }
                        )
                succeeded += 1
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"FAILED raw {row['id']}: {exc}")
    print(json.dumps({"processed": processed, "succeeded": succeeded, "failed": failed}))
    print(
        "geo max distance m:",
        settings.village_geo_context_max_distance_meters,
        "min advantage m:",
        settings.village_geo_context_min_distance_advantage_meters,
    )
    for key, value in outcome.most_common():
        print(key, value)
    for example in examples:
        print(json.dumps(example, ensure_ascii=False))


if __name__ == "__main__":
    main()
