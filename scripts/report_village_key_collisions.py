"""Read-only report: reference villages that collide under the shared match key.

Two villages collide when their names produce the same ``village_match_key``.
Collisions that already exist without the definite-article fold (identical
normalized names such as several villages called الطيبة) are listed separately
from collisions the fold introduces, so a reviewer can see what Step 1 changed.
Nothing is merged or written.

    docker compose exec -T backend python - < scripts/report_village_key_collisions.py
"""

from __future__ import annotations

import json
from collections import defaultdict

from sqlalchemy import select

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
import app.sources.models  # noqa: F401
from app.core.database import SessionLocal
from app.core.text_normalization import normalize_arabic_text, village_match_key
from app.news.models import Village


def main() -> None:
    processed = succeeded = failed = 0
    by_key: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    with SessionLocal() as db:
        for village in db.scalars(select(Village).where(Village.is_active.is_(True))):
            processed += 1
            try:
                for name in (village.ref_name_ar, village.acs_name):
                    if name and name.strip():
                        by_key[village_match_key(name)][village.id].add(
                            normalize_arabic_text(name)
                        )
                succeeded += 1
            except Exception as exc:  # noqa: BLE001 - report and continue
                failed += 1
                print(f"FAILED village {village.id}: {exc}")

    introduced: list[dict] = []
    preexisting: list[dict] = []
    for key, villages in by_key.items():
        if len(villages) < 2:
            continue
        plain_forms = {form for forms in villages.values() for form in forms}
        entry = {
            "key": key,
            "village_ids": sorted(villages),
            "plain_forms": sorted(plain_forms),
        }
        # More than one plain form under one key means the fold merged names
        # that differed before it.
        (introduced if len(plain_forms) > 1 else preexisting).append(entry)

    print(json.dumps({"processed": processed, "succeeded": succeeded, "failed": failed}))
    print(f"introduced_by_fold={len(introduced)} preexisting_identical_names={len(preexisting)}")
    print("--- introduced by the definite-article fold:")
    for entry in sorted(introduced, key=lambda e: e["key"]):
        print(json.dumps(entry, ensure_ascii=False))
    print("--- identical normalized names (real collisions, unchanged; first 40):")
    for entry in sorted(preexisting, key=lambda e: -len(e["village_ids"]))[:40]:
        print(json.dumps(entry, ensure_ascii=False))


if __name__ == "__main__":
    main()
