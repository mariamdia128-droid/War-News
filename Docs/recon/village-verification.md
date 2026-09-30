# Village-driven verification flags: recon (Phase 1)

Date range: 2026-08-20 to 2026-09-30. Read-only. No app code changed.
Tooling: `scripts/recon/village_flag_profile.py` (re-runs today's matcher on each flagged incident's own raw village string).

## Headline

| Number | What it is |
|---|---|
| 1,084 | `needs_verification` incidents in range, **including 412 soft-deleted** |
| 672 | same, not deleted |
| 666 | plus raw message `materialized`, no OCR payload (6 have raw status `error`) |
| 661 | what the UI shows; the last ~5 are removed by `_visible_incident_scope_filter` (war-context / Palestine-only text filter) and by time drift since the count |
| 357 | village-reason count you quoted; **354 once soft-deleted rows are excluded** |

1. **170 of the 354 (48%) are stale.** Today's matcher already resolves them as a confident match. All 51 rows in `village_location_aliases` were created between 2026-09-21 and 2026-09-28, after most of these incidents were matched. 123 are cleared by those aliases, 47 by the compact-key (spacing) scoring. Nothing re-evaluates a stored flag.
2. **63 of those 170 are attached to the wrong village** in `incidents.village_id`, so clearing the flag alone would keep a wrong village (see 1.3). Example: وادي السلوقي is stored as وادي الست and now resolves to تولين (33 incidents).
3. **184 are still low-confidence today.** Root causes are in 1.3.

## 1.1 Where the flag is produced

- **Reason text**: `LOW_CONFIDENCE_VILLAGE_REVIEW_REASON`, `verification_signals.py:4`. Set as the stored reason by `_verification_reason` (`verification_signals.py:88-89`) at materialization (`incident_materialization_service.py:1387-1420`).
- **Status decision**: `active_non_duplicate_verification_reasons` (`verification_signals.py:31-39`) adds `low_confidence_village` if any of these hold:
  - `match_result.any_village_low_confidence`;
  - any `village_matches[]` item has `village_review_required` or `village_match_status == "matched_low_confidence"`;
  - the incident's own `village_status == "matched_low_confidence"` (`incident_materialization_service.py:1390`).
- **Where the field is computed**: `MatchingService._classify_candidates` (`matching_service.py:1015-1063`) and `_resolve_village_candidates` (`:468-573`).
- **Thresholds** (module constants, `matching_service.py:44-51`, not settings or DB): `MATCH_THRESHOLD = 0.6`, `LOW_CONFIDENCE_THRESHOLD = 0.35`, `MATCH_TIE_MARGIN = 0.05`.
- **Score**: `VillageRepository.find_similar` (`village_repository.py:132-164`) is the max of four pg_trgm `similarity()` values: `acs_name` and `ref_name_ar`, each plain and space-stripped ("compact").
- **`MATCH_TIE_MARGIN`**: only applied when top score >= 0.6 (`:1042-1051`). A tie at 0.53 vs 0.53 is flagged simply for being below 0.6; the margin plays no part.
- **Other things that mark a village `matched_low_confidence`**, each a separate producer:
  - Bare score in [0.35, 0.6) (`:1057`).
  - No lexical overlap between mention and top candidate (`:540-551`).
  - Collision-like alternative: any 2+ candidates containing the mention as a token sequence (`:552-565`, `_has_collision_like_alternative`).
  - Terminology exception list (`:482-490`).
  - `location_ambiguity` from extraction forces **every** village in the bulletin low (`:318-329`).
  - "بين/محيط/قرب" collapse (`incident_materialization_service.py:2028-2033`).
  - Air-violation import (`air_violation_khabar_import.py:198`).
- **Per incident or per village?** Matching is per village mention. The status check reads the whole `match_result` (any village), so by code **one weak village flags every incident from that bulletin**. Observed bleed is small: 6 of 367 flagged incidents have their own village as a confident match. 233 of the 354 come from multi-village bulletins.

## 1.2 Profile of the flagged incidents

**Stored score of the incident's own village** (361 with a low-confidence own village):

| Bucket | Incidents |
|---|---|
| 0.35-0.39 | 68 |
| 0.40-0.49 | 101 |
| 0.50-0.59 | 177 |
| 0.60-0.73 | 6 |
| 1.00 (collision / overlap / exception, not fuzzy) | 9 |

About 75 sit within 0.05 of the 0.6 threshold.

**Match method**: not stored. The only method-like fields are `alias_matched` and `resolved_by_geo_context`. Of the village matches in flagged bulletins, 6 were alias hits, 0 geo-context resolutions, and the rest are trigram.

**Single vs multi**: 121 single-village bulletins, 233 multi-village bulletins. 8 carry `location_ambiguity`.

**Top raw strings** (stored score -> today; matched-to, then runner-ups):

| # | Raw string | Stored | Today | Top candidates today |
|---|---|---|---|---|
| 43 | دوحة كفررمان | 0.37 / 0.43 | matched 1.0 (alias) | كفر رمان |
| 33 | وادي السلوقي | 0.53 | matched 1.0 (alias) | تولين. Was stored as وادي الست (wrong) |
| 23 | وادي الحجير | 0.53 | low 0.53 | وادي الدير 0.53, وادي الحور 0.53, وادي الست 0.47 (all wrong, no gazetteer entry) |
| 17 | الفوقا | 0.53 | low 0.54 | حومين الفوقا, نبطية الفوقا, تمنين الفوقا (three-way tie) |
| 17 | وادي زبقين | 0.54 | matched 1.0 | زبقين |
| 16 | كفررمان | 0.54 | matched 1.0 | كفر رمان |
| 14 | الرمادية | 0.45 | low 0.45 | رمادية 0.45, الرمانة 0.42 (correct is #1; `ال` not folded) |
| 12 | كفرشوبا | 0.54 | matched 1.0 | كفر شوبا |
| 9 | بيوت السياد | 0.43 | matched 1.0 (alias) | المنصوري. Was حرف السياد (wrong) |
| 8 | كفرتبنيت | 0.58 | matched 1.0 | كفر تبنيت |
| 8 | زوطر | 0.38 | low 0.38 | زوطر الشرقية 0.38, زوطر الغربية 0.38 |
| 6 | البياضة / 6 عيناثا | 0.46 / 0.44 | matched 1.0 (alias) | changed village vs stored |
| 5+2 | الطيبة / الطيبه | 0.36 | low 0.36 | الخريبة 0.36, القبة 0.30 (wrong; no real candidate) |
| 5 | الحنية | 0.40 | low 0.40 | المنيه 0.40, حنية 0.33 (correct is #2; `ال` not folded) |

The ten most frequent strings account for about 55% of the flags (192 of 354).

## 1.3 Root causes (all 354 classified, grouped by raw string)

No human ground truth exists for "the correct village". The classes below are my reading of the candidate lists, so treat borderline strings as judgement calls.

| Cause | Incidents | Notes |
|---|---|---|
| **Stale**: already resolved by aliases / compact scoring added since | **170** | 63 also have the wrong `village_id` stored |
| (b) Normalization: `ال` prefix and spelling variants not folded | 33 | الرمادية 14, الحنية 5, الهبارية 4, عرب الصاليم variants 7, قناطرة 2, القنترة 1 |
| (c) Threshold: clear best match under 0.6 | 39 | ميفدون variants, `أطراف X`, `مرتفعات X`, يحمر الشقيف, Hardinga, typos of كفر تبنيت |
| (d) Real tie between distinct places | 35 | الفوقا 17, زوطر 8, عدشيت 2, مشاع 2, الريحان 2, `أطراف/حي … النبطية` 3, `قضاء بنت جبيل` 1 |
| (d) Parent/child or exact name wrongly seen as a collision | 5 | صور, بعلبك, جنين, عرمون x2: score is 1.00 but a longer name containing the mention trips `_has_collision_like_alternative` |
| (a) Alias gap / no real candidate | 57 | وادي الحجير 23 (no gazetteer row), الطيبة x8, Benton Jbeil x3, الشقيف/قلعة الشقيف, وادي الخنازير, and about 20 singletons |
| (e) Multi-place or generic string | 13 | `بين X و Y`, `X-Y`, `قرى عدة`, `الأودية`, `التلال`, `حي الدير` |
| (f) Out-of-country place matched to a Lebanese village | 2 | الناصرة -> الناقورة, خان يونس -> بيت يونس |

The sample for this table is all 354 incidents, not 40, so no extrapolation is needed.

Findings that go beyond the score:
- Normalization (`text_normalization.py:15-31`) folds hamza, ة->ه, ى->ي, diacritics, tatweel, and whitespace. It does **not** strip the `ال` prefix. The compact key only removes spaces. (Correction, Phase 2: an earlier version of this line said ة was not folded; it is, via `ARABIC_ALEF_VARIANTS`.)
- The extraction model returns Latin or garbled names (`Benton Jbeil`, `Hardinga`, `Harir`) that no Arabic reference can match. This is a rule-file fix (Phase 3).
- Two sibling villages (زوطر الشرقية / الغربية, عدشيت الشقيف / القصير, five `النبطية` villages) are real ties. Without a qualifier or geo anchor they should stay flagged.

**Projection.** Rule (best score >= floor, margin >= 0.05 over #2), applied to today's raw scores with no other fixes:

| Floor | Still flagged (of 184) |
|---|---|
| 0.35 | 89 |
| 0.40 | 104 |
| 0.50 | 137 (55 distinct strings) |

Normalization, aliases, and the parent/child rule should lower these. Even so, **a 0.5 floor keeps roughly 60-90 incidents flagged, so "under 10" needs alias or geo decisions from you.** Five strings (وادي الحجير, الفوقا, زوطر, الطيبة, Benton Jbeil) are about 55 incidents. I will not invent aliases for these, because a wrong alias silently attributes casualties to the wrong village.

## 1.4 Two data questions

**NULL reasons.** 439 `needs_verification` rows have NULL `verification_reason`, but 406 of them are soft-deleted. Only 33 are live. Their signals live in other places:
- 25 have a row in `duplicate_matches` (reason is the duplicate decision, not the text column).
- 4 have `match_result.any_village_low_confidence = true` (village flag; text was overwritten or never set).
- 2 have `match_result.condition_review_required = true`.
- 2 have `duplicate_flag = true` and no `duplicate_matches` row.

`active_non_duplicate_verification_reasons` derives reasons from `match_result` / `extraction_result`, which is why they still count. The 5-example listing for the 33 was not completed because the example query failed on a `match_type` enum cast; I will re-run it if you want examples.

**1,084 vs 661.** Explained in the headline table. The UI query is `IncidentRepository.list_all` (`incident_repository.py:239`) with filters from `_list_filters` (`:2691-2806`), non-`include_filtered_news` branch: `is_deleted = false`, condition not an air-violation condition, `_visible_incident_scope_filter()`, raw status `materialized`, no `ocr_text`, `verification_status != rejected`, and `_needs_verification_column()` (`verification_status = 'needs_verification'` OR an open visible `casualty_check` flag; none open in range). The date field is `coalesce(incident.event_date, date(raw.message_datetime or received_at))`, not `created_at`.

## Proposed order for Phase 2 (for your approval)

1. **Reprocess the stale 170.** Read-only dry-run script, then a `.sql` or apply-flag backfill for you to run. It must also correct the 63 wrong `village_id` values, so it is a re-match, not a flag clear.
2. **Normalization** (`ال` prefix, ة/ه, one shared function used on both sides): 33.
3. **Flag logic + tie handling**: parent/child exact-name (5), clear best over floor (part of 39), real ties stay flagged.
4. **Multi-village**: evaluate per village; stop `any_village_low_confidence` from flagging every sibling incident.
5. **Aliases**: only ones you approve (list to be produced from the 55 residual strings).

## Decisions needed from you

1. Floor value: start at 0.5 as you asked, or 0.4? At 0.5 the residual is higher (137 vs 104 on raw scores).
2. Are the 5 unresolved strings above to be resolved by alias (you tell me the correct village), by geo context, or left flagged?
3. Reprocessing existing incidents changes `village_id` on 63 rows: OK to include in the dry-run/backfill?
