# Village verification flags: Phase 2 result

Range 2026-08-20 to 2026-09-30, soft-deleted incidents excluded, incidents whose stored reason is "Low-confidence village match requires manual review." (354). Numbers come from `scripts/reprocess_village_flags.py` in dry-run mode against the live data (SELECTs only). Nothing was applied.

## Result

| | Incidents |
|---|---|
| Village-flagged before | **354** |
| Village-flagged after (dry run) | **133** |
| Village resolved | 221 |

The target of "under 10" is **not** reached and I did not tune to reach it. What is left is real: 133 incidents across 69 raw strings that the general rules cannot honestly resolve (list below).

Of the 221 that resolve:

| Outcome | Incidents | What happens |
|---|---|---|
| Flag cleared, same village | 102 | leave the queue |
| Flag cleared, village changes | 63 | leave the queue; `village_id` is corrected |
| Village resolved, but a condition review already applied | 56 | stay in the queue for the condition, not the village |

So the review queue shrinks by **165** (672 to about 507), not 221. The other 56 carry a condition-review signal that predates this work (`condition_review_required` at bulletin level; 72 of the 354 have it). That signal is also bulletin-wide, so it has the same sibling-bleed problem the village flag had. I did not touch it.

The 63 changed villages: 53 by curated alias (وادي السلوقي to تولين 33, بيوت السياد to المنصوري, عيناثا, البياضة, جبل الرفيع, ...), 4 by the new `ال` fold (الحنية to حنية), 5 by geo context (الطيبة to طيبة مرجعيون x4, الفوقا to نبطية الفوقا), 1 by fuzzy score (عرقوب to مزرعة العرقوب).

## Stale vs new

| Source of the clearing | Incidents |
|---|---|
| Already resolved by the matcher before this work (aliases and compact scoring added 2026-09-21..28; flags were never recomputed) | 167 |
| Cleared by the Phase 2 rules | 54 |
| Previously resolved, now flagged again because the bulletin's `location_ambiguity` names that village (الخيام, طلوسة, تلة علي الطاهر) | 3 |

The 54 by rule (attributed by the winning match method and string pattern, not by ablation, so read them as approximate):

| Step | Incidents | Examples |
|---|---|---|
| 1. `ال` fold | 27 | الرمادية 14, الحنية 5, الهبارية 4, عرب الصاليم 3 |
| 2. Descriptor stripping | 11 | أطراف ميفدون / شقرا / برعشيت / طلوسة, مرتفعات حلتا, المدينة الخيام |
| 3. Exact-name rule | 3 | صور, بعلبك, جنين |
| 3. Floor + margin (clear best match under 0.6) | 6 | الشقيف, العرقوب, عربي الصاليم, قضاء بنت جبيل |
| 5. Geo context (existing path) | 6 | الطيبة to طيبة مرجعيون, الفوقا to نبطية الفوقا |
| 4. Multi-village scoping | included above | siblings whose own village was confident |
| 6. Foreign places | 0 cleared | stops 2 wrong matches (below) |
| Other | 1 | جبل الرفيع (existing alias) |

## Values chosen

- `VILLAGE_CONFIDENT_FLOOR = 0.5`. Below it the recon's wrong best matches lived (الطيبة to الخريبة 0.36, الناصرة to الناقورة 0.42).
- `MATCH_TIE_MARGIN = 0.05`, now applied at every score, so 0.53 vs 0.53 is flagged as a tie.
- `MATCH_THRESHOLD = 0.6` and `LOW_CONFIDENCE_THRESHOLD = 0.35` are unchanged. 0.6 is now only the point below which an accepted match gets a soft `village_match_note` and must cover every word of the mention.

## What changed, by commit

| Step | Commit | Change |
|---|---|---|
| 1 | `eeff636` | `village_match_key` (drops leading `ال` on every word, both sides); scored in `find_similar` with a plain-exact tie-break |
| 2 | `e3ba048` | descriptor list in `terminology/village_descriptors.yaml`; stripped only when the rest resolves better |
| 3 | `eee5c77` | floor + margin + exact-name rule; `village_match_method` and `village_match_note` stored in `match_result` |
| 4 | `c099db9` | `location_ambiguity` downgrades only the named villages |
| 5 | `903d195` | no new rule; method `geo_context` recorded; probe script |
| 6 | `e8be792` | foreign-place list; whole-word overlap guard |
| 7 | `c1ae87f` | verbatim-name rule in the three Tier 1 rule files; changelog |
| 8 | `9315089` | remaining regression tests |
| 9 | `de799cc` | partial-word and geo-context guards found by the dry run; `scripts/reprocess_village_flags.py` |

## Where I departed from your spec, and why

1. **Exact-name rule (صور, بعلبك, جنين, عرمون).** صور, بعلبك and جنين now win as specified. عرمون does not: the reference data has عرمون كسروان, a region-suffixed twin, and two existing tests (`test_region_suffixed_collision_without_anchor_is_reviewable`, raw 9298/10395) encode that a bare name next to `<name> <region>` is ambiguous. An exact winner that a longer name also contains can still be overridden by a nearby geo anchor (raw 10395 القصير). عرمون x2 stays flagged.
2. **Step 4 is only half committed.** The matching side (per-village `location_ambiguity`) is in `c099db9`. The per-incident review signal is not: `active_non_duplicate_verification_reasons` exists only in your uncommitted working tree (HEAD has none of it), so I could not commit my change to it without committing your work. It is in your working tree on top of yours: `verification_signals.py` (`village_id` parameter and `_village_signal`), `incident_materialization_service.py` (passes `village_id` at the two `_initial_verification_status` call sites), `incident_repository.py` (`village_id=getattr(incident, "village_id", None)`), and the new untracked `tests/test_village_verification_scoping.py` (6 tests, passing). Commit them with your review-signal work. Until then, `scripts/reprocess_village_flags.py` will exit with a clear message on a clean checkout.
3. **Step 5 adds no district rule.** The existing distance-based geo-context path works (6 more resolutions above). The remaining ties fail for real reasons: no anchor in the bulletin (46 mentions), or no candidate clearly closer. الفوقا has an anchor, but both tied candidates are in the same district (Nabatieh), so a district rule would not pick one either.
4. **"Village evidence conflicts with the source metadata" is not implemented.** No village-level source metadata exists in the data.
5. **Foreign places become "no candidate", not a match.** For new bulletins this means a foreign-only mention produces no incident (the village is skipped as unmatched). Existing incidents are left alone: الناصرة and خان يونس keep their wrong village until you decide (listed below).
6. **Verbatim-name rule is "in the source's script", not "in Arabic".** For an English source, Arabic output would require transliteration, which is what the rule forbids. The real failure was Arabic source, Latin output: raw 37597 and 37706 «أطراف بلدتي حداثا وحاريص» returned `["Harir"]`.
7. **No list of "already sent to the CNRS webhook".** There is no outbound webhook or export log in the database or the code. "CNRS Webhook" is an inbound source; `incident_excel_view` is a live view. I cannot say which changed-village incidents were exported. Nothing is resent.

## Tests

`docker compose exec backend` runs the image copy of the code, not the working tree (bind mounts from Z: do not work in Docker Desktop here), and its `DATABASE_URL` points at the live dev database. To avoid touching live data I ran pytest in a throwaway container with the working tree copied in and a dummy database URL.

Final run: **1390 passed, 23 failed, 14 skipped**. The 23 failures are identical to the baseline I recorded before changing anything (1343 passed, 23 failed, 14 skipped): database-integration tests that cannot connect, plus tests around your uncommitted review-signal work. No test that passed at baseline fails now. I added 47 tests in `tests/test_village_match_key.py`, `tests/test_matching_service.py` and `tests/test_village_verification_scoping.py`. `scripts/check_stale_service_imports.py`: OK. The database-integration tests have not been run against a real database.

## Reference villages that collide after normalization

Seven pairs share a key once `ال` is dropped. They are not merged: a plain-exact mention wins the ordering, and a fuzzy tie between them stays a tie.

| Key | Village ids | Names |
|---|---|---|
| بقيعه | 357, 358 | البقيعة / بقيعة |
| خريبه | 903, 905 | الخريبة / خريبة |
| رمانه | 1335, 1473 | الرمانة / رمانة |
| قنطره | 1228, 1229 | القنطرة / قنطرة |
| كنيسه | 909, 911, 915 | الكنيسة / كنيسة |
| مزرعه | 1009, 1026 | المزرعة / مزرعة |
| معيصره | 946, 947 | المعيصرة / معيصرة |

Three pairs already had identical names before this work and stay real collisions: برباره (283, 284), شويا (445, 446), مغيره (1092, 1120).

## Ongoing rate (most recent week)

Incidents with an event date 2026-09-24 to 2026-09-28 (the data ends on the 28th): 202 incidents.

| Date | Village flags today | Still flagged under the new rules |
|---|---|---|
| 09-24 | 1 | 1 |
| 09-25 | 0 | 0 |
| 09-26 | 2 | 0 |
| 09-27 | 2 | 1 |
| 09-28 | 0 | 0 |

That is about one new village flag a day now (about 0.4 a day under the new rules). The 354 is a backlog: most of it comes from strings that the aliases added 2026-09-21..28 already fixed for new incidents.

## Spot-check before you apply

Cleared by a rule rather than an alias, and worth a look:

- `قضاء بنت جبيل` to بنت جبيل (a district name resolving to the town of the same name; village unchanged, flag cleared).
- `عرقوب` to مزرعة العرقوب (village changes from عرقا, which was wrong).
- `الشقيف` to عدشيت الشقيف (village unchanged).
- `الطيبة` to طيبة مرجعيون x4 and `الفوقا` to نبطية الفوقا (geo context).

## What still flags (133 incidents, 69 strings): your decisions

Reasons: below the 0.5 floor 43, name not covered by the best candidate 34, tie between distinct places 28, same name in several places 23, bulletin-level ambiguity 3, foreign place 2.

The five largest are 54 incidents: وادي الحجير 23 (no gazetteer row; the three candidates are all wrong), الفوقا 16, زوطر 8, يحمر الشقيف 4, Benton Jbeil 3. One alias or one decision each would clear them, which is why I did not add any.

| Raw village string | Incidents | Why it still flags | Top candidates (score) |
|---|---|---|---|
| وادي الحجير | 23 | tie between distinct places | وادي الدير 0.53 / وادي الحور 0.53 |
| الفوقا | 16 | same name in several places | حومين الفوقا 0.54 / نبطية الفوقا 0.54 |
| زوطر | 8 | below floor (sibling tie) | زوطر الشرقية 0.45 / زوطر الغربية 0.45 |
| يحمر الشقيف | 4 | name not covered | يحمر 0.50 / عدشيت الشقيف 0.39 |
| ميوفدون | 3 | name not covered (typo) | ميفدون 0.50 / ميدون 0.40 |
| العريش | 3 | name not covered | العريضة 0.50 / وادي العرايش 0.33 |
| معرية | 3 | below floor | معمارية 0.40 / معنيه 0.33 |
| Benton Jbeil | 3 | below floor (Latin script) | بلاط 0.41 / بنت جبيل 0.33 |
| الطيبة | 2 | below floor (same name in several places) | طيبة بعلبك 0.45 / طيبة مرجعيون 0.38 |
| عدشيت | 2 | same name in several places | عدشيت الشقيف 0.55 / عدشيت القصير 0.55 |
| دوبيه | 2 | below floor | دبية 0.38 / لوبية 0.33 |
| مشاع | 2 | same name in several places | مشاع الجبه 0.56 / مشاع الفتوح 0.50 |
| Hardinga | 2 | name not covered (Latin script) | حردين 0.55 / حاريص 0.25 |
| عرابصاليم | 2 | name not covered (typo) | عرب صاليم 0.58 / بصاليم 0.42 |
| الريحان | 2 | tie between distinct places | عين الريحان 0.67 / الريحانية 0.64 |
| عرمون | 2 | region-suffixed twin | عرمون 1.00 / عرمون كسروان 0.46 |
| قناطرة | 2 | below floor | قنطرة 0.44 / القنطرة 0.44 |
| أودية قبريخا | 1 | name not covered | قبريخا 0.54 |
| ظوحة كفررمان | 1 | below floor | كفر رمان 0.43 |
| التلال | 1 | name not covered (generic) | التل 0.50 |
| بين برعشيت وبيت ياحون | 1 | name not covered (two places in one string) | بيت ياحون 0.50 |
| المياد | 1 | below floor | المينا 0.40 |
| وادي صربين | 1 | name not covered | صربين 0.55 |
| النبطية الفوفا | 1 | name not covered (typo) | نبطية الفوقا 0.57 |
| Hardinga (Hadatha) | 1 | below floor (Latin script) | حداثا 0.41 |
| الناصرة | 1 | foreign place, no Lebanese village (kept الناقورة, wrong) | none |
| خان يونس | 1 | foreign place, no Lebanese village (kept بيت يونس, wrong) | none |
| عين السماحية | 1 | below floor | عين البنية 0.41 |
| ميفردون | 1 | name not covered (typo) | ميفدون 0.50 |
| وادي العزية | 1 | tie between distinct places | عزّيه 0.50 / وادي العرايش 0.47 |
| Harir | 1 | name not covered (Latin script) | حاريص 0.50 |
| عين العروس | 1 | tie between distinct places | العين 0.50 / عين عرب 0.50 |
| شقرة | 1 | below floor | شقرا 0.43 |
| مزرعة بسطرة | 1 | tie between distinct places | مزرعة 0.50 / المزرعة 0.50 |
| شُمران | 1 | below floor | دير شمرا 0.36 |
| حالتا | 1 | below floor | حلتا 0.38 |
| قلعة الشقيف | 1 | name not covered | القلعة 0.50 |
| حي المسلخ- النبطية | 1 | below floor | الدوير النبطية 0.44 |
| رعشيت | 1 | name not covered | رعشين 0.50 |
| القنترة | 1 | below floor | القنطرة 0.45 |
| الميتم | 1 | below floor | المينا 0.40 |
| الخيام | 1 | bulletin-level ambiguity | الخيام 1.00 |
| المصنوري | 1 | below floor | النوري 0.45 |
| نبطية-كفررمان | 1 | name not covered (two places in one string) | كفر رمان 0.57 |
| طلوسة-وادي السلوقي | 1 | below floor (two places in one string) | وادي الست 0.38 |
| بين ميفدون و زوطر الشرقية | 1 | name not covered (two places in one string) | زوطر الشرقية 0.50 |
| حي الدير-النبطية الفوقا | 1 | name not covered | نبطية الفوقا 0.58 |
| كفرمان قضاء النبطية | 1 | name not covered | كفر رمان 0.67 |
| بين ارنون و كفرتبنيت | 1 | below floor (two places in one string) | كفر تبنيت 0.35 |
| حي الدير | 1 | same name in several places | ضهر الدير 0.60 / وادي الدير 0.55 |
| وادي زيفين | 1 | below floor | وادي جزين 0.40 |
| الراهبات | 1 | below floor | الرام 0.36 |
| عربيصاليم | 1 | name not covered (typo) | عرب صاليم 0.58 |
| كفرربينيت | 1 | below floor (typo) | كفربيت 0.42 |
| كفرربنيت | 1 | name not covered (typo) | كفر تبنيت 0.50 |
| شقراء | 1 | name not covered | شقرا 0.57 |
| بين حداثا و حاريص | 1 | below floor (two places in one string) | حداثا 0.35 / حاريص 0.35 |
| الطيبة الجنوبية | 1 | below floor | راس مسقا الجنوبية 0.39 |
| حانين | 1 | below floor | حنين 0.38 |
| بين القنطرة-الطيبة | 1 | below floor (two places in one string) | القنطرة 0.47 |
| وادي الخنازير | 1 | name not covered | قاع وادي الخنزير 0.55 |
| السدانة-كفرشوبا | 1 | name not covered (two places in one string) | كفر شوبا 0.57 |
| تلة علي الطاهر | 1 | bulletin-level ambiguity | علي الطاهر 0.73 |
| الأودية | 1 | name not covered (generic) | الداودية 0.55 |
| قرى عدة | 1 | below floor (generic) | قريعة 0.44 |
| المجدية | 1 | name not covered | المجدل 0.50 |
| طلوسة | 1 | bulletin-level ambiguity | طلوسة 1.00 |
| حلاوة | 1 | below floor | حلوة 0.38 |
| حداثا_الطيري | 1 | below floor | حداثا 0.46 |

Two groups are not village decisions and will keep recurring: the "two places in one string" rows (`بين X و Y`, `X-Y`) are an extraction problem (one target on the left, the rest as `qualifier_text`, per the existing rule), and the Latin-script rows (`Hardinga`, `Harir`, `Benton Jbeil`) should stop once the verbatim-name rule takes effect. The extraction prompt change has no automated test; check it on the next live sample.

## Files to review before applying

- `scripts/sql/village_reprocess.sql`: section A (flag clear, 102) and section B (flag clear plus `village_id` and `village_display_name`, 63) in separate transactions. Each `UPDATE` only fires while the incident still has the village reason. `exact_hash` is not recomputed for section B because it depends on the event hash suffix.
- `scripts/output/village_reprocess.csv`: one row per incident with old and new village, method, category, and top candidates.
- The 56 "condition review remains" incidents get no SQL: their stored reason text still says village. If you want that text corrected, that is a separate small update.
