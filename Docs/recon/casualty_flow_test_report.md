# Casualty verification flow: scratch-database test report

Date: 2026-09-28. Branch `dev` at `5ebd172` plus the uncommitted fixes listed in section 8.
Scratch database: `war_news_casualty_test` on a separate Postgres container
(`war_news_casualty_test-db-1`, host port 5435). The real database `war_news_dev` was only read
(`pg_dump`, `default_transaction_read_only`). Evidence files are in `Docs/recon/casualty_flow_test/`.

## Verdict

**Ready after these fixes.**

1. **Blocker outside the casualty code.** One live incident has `duplicate_level='segment'`
   (written by `app/news/services/dedup/segment_review_dedup.py`), but
   `IncidentListItemDTO.duplicate_level` only allows `low|medium|high`. Any Incidents-list page
   containing that row returns 500. The row is a needs-verification duplicate, so the
   **Needs verification** view fails on the real data. The fix is one word
   (`Literal["low", "medium", "high", "segment"]`, two places in `app/news/dtos/incident_dto.py`).
   It was applied only inside the scratch image, not in the working tree, because it is not our code.
2. **Five defects in our code were found and fixed** (section 8). Two of them would have broken the
   rollout: the status backfill did not store the per-type statuses, so the flag backfill created
   **zero** flags; and resolving an aggregate toll could not enforce the bulletin total, then used
   the admin's own entries as the total.
3. **Known false negatives remain (design decision needed):** 14 incidents have status `exact`, but
   the number was never stored (legacy rows where the text says «شهيدان», «4 جرحى» and so on), and
   they get no flag. See section 4.

## T0 Safety and setup

| | Value |
|---|---|
| Real DB | `war_news_dev`, host `db` (container `war-news-db-1`, host port 5433), user `postgres`, URL `postgresql+psycopg2://postgres:***@db:5432/war_news_dev` |
| Scratch DB | `war_news_casualty_test`, URL `postgresql+psycopg2://postgres:***@db:5432/war_news_casualty_test` (own container) |
| Real revision | `20260928_0071` (not `0062` as expected: 0063 to 0071 are already applied on the real DB) |
| Code heads | exactly one: `20260928_0072` |

Row counts after restore, real = scratch: raw_messages 7,401; incidents 2,148 (1,445 live);
incident_updates 4,909; incident_details 2,148; villages 1,544; village_location_aliases 51;
conditions 46; bulletin_casualty_groups 7; incident_verification_flags 0.

**Image method.** Docker cannot bind-mount the `Z:` network drive, so the test image
`war-news-casualty-test:latest` is `FROM war-news-backend:latest` with the working tree copied in
(tracked and untracked files only). The frontend image `war-news-casualty-test-frontend:latest` is
built the same way from `frontend/`. Every write command runs through a guard that aborts unless
`SELECT current_database()` returns `war_news_casualty_test`.

## T1 Migrations

`alembic upgrade head` applied `20260928_0071 -> 20260928_0072` (incident-first flag visibility index).
All six `incidents.casualty_*` columns exist. `incident_verification_flags` has `visible_after` and the
indexes `uq_..._open_key` (partial, open), `ix_..._type_status_visible_after` and the new
`ix_..._incident_status_visible_after`. Running `downgrade -1` and then `upgrade head` works.

## T2 Data scripts (final run on a fresh restore, with the fixed code)

| Script | Dry-run | `--apply` | Second `--apply` |
|---|---|---|---|
| casualty_cleanup | 64 field changes on 21 incidents (A 48 bulletin total on 5 rows, B 6 zero without explicit none, C 10 village-role value), 16 review-only, 1 skipped (verified/admin-edited) | processed 21 / succeeded 21 / failed 0 | 0 / 0 / 0 |
| casualty_merge_leak_cleanup | 0 leaked fields; 28 unverifiable (merged raw message purged) | 0 / 0 / 0 | 0 / 0 / 0 |
| casualty_status_backfill | 1,445: none_mentioned 1,348, explicit_none 20, exact 32, count_missing 18, aggregate_only 27; 15 preliminary; 26 disagreements; 2,249 merged-source references missing | 1,445 / 1,445 / 0 (1,445 audit rows) | no new audit rows |
| casualty_flags_backfill `--since 2026-08-17` | would open 19 count_missing + 27 aggregate | opened 46, updated 0, cleared 0 | opened 0, updated 0, cleared 0 |

Before and after (live incidents): stored deaths 49 → 37 rows (sum 199 → 153), injuries 47 → 27
rows (sum 624 → 257). All flags are visible immediately (grace 0).

**Grace on backfilled flags.** The backfill uses `settings.casualty_flag_grace_minutes` for every
incident, old ones included. With the default of 120, historical flags stay hidden for 2 hours
after the backfill. That is not the right behaviour: the grace exists to let the pipeline settle
new messages. Run the rollout backfill with `CASUALTY_FLAG_GRACE_MINUTES=0`, or change the backfill
to use `visible_after = now` for incidents older than the grace period. The code was not changed.

## T3 Invariants (`scripts/recon/casualty_flow_invariants.py`, final state)

| Invariant | Checked | Violations | Note |
|---|---|---|---|
| I1 no open flag on none/explicit-none/deleted/rejected/merged | 46 flags | 0 | |
| I2 each flaggable incident in window has exactly one open flag per reason | 46 | 0 | no skips needed |
| I3 no open flag when both statuses exact | 46 | 0 | |
| I4 single-location counts backed by a non-aggregate source | 31 fields | 0 | 13 fields on 9 incidents are unverifiable because their merged source was purged |
| I5 same count stamped on 2+ siblings without evidence (Bug A) | 181 bulletins | 0 | |
| I6 no count_missing flag where a singular/dual word gives that count | 19 | 0 | was 1 (30335 «شهيدان»), fixed |
| I7 stored 0 needs an explicit-none phrase | 0 zeros | 0 | cleanup removed all 6 zeros |
| I8 re-evaluating everything changes nothing | 2,148 | 0 | was 47 "updated" plus audit rows per run, fixed |
| I9 merge safety (aggregate merge, status reset, admin numbers) | 3 | 0 | rolled back |
| I10 list counts and verification_type filters | 5 | 0 | needs verification 48 = 45 flagged + 3 duplicates |

The first run found I6 = 1 and I8 = 47. Both are fixed (section 8).

## T4 Manual review (Arabic read)

The 50-row stratified sample is in `t4_review_sample.csv`. Because only 46 flags exist, **all 46
were graded**; the table gives the full population and the sample figure.

| Reason | Flags | Correct | False positive | Precision (all / sample) | Recall estimate |
|---|---|---|---|---|---|
| count_missing | 19 | 15 | 4 | 79% / 60% (6/10) | 83% for vague wording (3 misses); 52% if "exact number never stored" counts as a miss (14 misses) |
| aggregate_no_breakdown | 27 | 23 | 4 | 85% / 90% (9/10) | about 96% (1 miss) |

Other strata: `exact` 5/10 correct. `none_mentioned` rows with casualty keywords: 10/10 correct
(all were the «صفحة الإعلامي الشهيد علي شعيب» page header, or a toll for another place).
Cleanup-changed rows: 10/10 correct removals, but 2 of them were left `exact` with no number.

**Every wrong row**

| Incident | Msg | Problem | Arabic evidence |
|---|---|---|---|
| f21f3099 | 32134 | FP count_missing: named single victim is 1 death | «استشهاد المواطن المدني خضر صباح ابو حنان» |
| 1cb68d36 | 28455 | FP count_missing: past martyr mentioned in passing | «وهو والد احد الشهداء» |
| bc6bcd39, a8ee0219 | 31204 | FP count_missing: digest; the injured are in Kfar Remmane, but the rows are Zaoutar and Jebla | «غارة ... في كفررمان ... نقل المصابين» |
| c038337e, 3b319f82 | 28917 | FP aggregate: toll tied to one named town; Kfar Remmane already holds 9/13, Deir ez-Zahrani should be none | «في بلدة كفررمان حيث ارتقى 9 شهـداء» |
| f88a14c9, cbb16d56 | 31308 | FP aggregate: the sentence gives each town's count | «إصابة 5 ... في بلدة كفررمان ... وشهيدان ... عربصاليم» |
| 0a10e831 | 31336 | wrong count 4/20 (text: 2 deaths); likely an old merge leak, merged source purged | «شهيدان في غارة استهدفت دراجة نارية» |
| 1a5b73de | 28698 | wrong count: deaths 2, injuries null (text: 9 deaths, 6 or 13 injured) | «9 شهداء و6 جرحى في كفررمان» |
| 3c1db7e5 | 31925 | deaths 40 stored; text is vague (flag is correct) | «ضحايا وإصابات متعددة» |
| 0b0e4a71 | 31240 | 1/1 stored, primary text has no casualties (merged source purged) | «شن غارات استهدفت مدينة النبطية» |
| 2d36a140 | 31827 | FN: multi-area article toll marked `exact` on one row | «3 شهداء و23 جريحاً» |
| 8fc74304 | 32708 | status `exact` from strike counts in a digest (harmless, no numbers) | «كفررمان (٢)» |
| 14 incidents | see below | FN: status `exact`, number not stored, no flag | e.g. «شهيدان»، «4 جرحى»، «وقوع إصابات»، «عشرات الجرحى» |

The 14 "exact, number not stored" incidents: 03f8432a, 1a5b73de, 2d36a140, 512c900e, 78145585,
7f509439, 86bc5b05, 89a5b113, 8fc74304, 4d8f7159, a7d8a296, b05c0b8b, b2e88fe2, e15b8ee6.
Their `extraction_result.casualties` is empty (legacy rows from before count filling at extraction
time). The status rule recognises the number, but no script writes it. Options: (a) the status
backfill writes the count it infers (same `infer_count_from_count_words` rule used at extraction),
with an audit row; or (b) the evaluator opens a flag when a type is `exact` but its count is null.
Three of them (03f8432a/86bc5b05 «عشرات», a7d8a296 «إصابات») are vague and should be
`count_missing`.

Wording issue: 13 aggregate flags (bulletins 28686, 31425, 31863, 32095) come from Health Ministry
bulletins whose text **does** list per-location numbers; the extraction did not capture them. The
flag is still useful (the admin types the numbers from the bulletin shown in the panel), but
"no per-location breakdown" is inaccurate. Bulletins 31884 and 32072 are the same toll from two
channels (6 flags for one toll).

## T5 Tests and API flow

**Backend suite on the scratch DB:** 1,168 tests; 17 failed, 1,151 passed. The same suite built from
`git archive main` and `git archive HEAD` on the same DB also fails **the same 17 tests**
(`t5_suite_failures_main.txt`). So there are **0 new failures**, and no baseline failure now
passes. The 4 above the 13-failure baseline are DB/environment dependent and fail on `main` too.
The +2 passes are the new regression tests. The manifest has no "D3" list, so its focused command
was used instead: 42 passed, and all casualty test files pass (63). **Frontend:** `tsc --noEmit`
exit 0; vitest 15 files / 67 tests passed.

**API flow** (running scratch backend, `t5_api_flow.txt`; the pre-fix run is kept as
`t5_api_flow_before_fixes.txt`):
- Lists: needs_verification 42, duplicate 3, casualty_missing_number 18, casualty_aggregate_toll 22,
  verified 0. The list item carries `verification_types` and `open_flags`; detail
  `open_casualty_flags_count` = 1.
- Bulletin 31863 (4 deaths, 32 injuries, 5 locations), partial save of 2 locations
  (النبطية 1/3, النبطية الفوقا injuries 2 + unknown deaths): 200, `totals` deaths 1/4 and
  injuries 5/32, `remaining_total` {deaths 3, injuries 27}. Rows became `exact`; both flags
  `resolved` with admin `edit` audit rows. Three siblings stayed open. The rest were resolved with
  `unknown_*`, and all 5 ended `resolved`.
- 422 `errors[]`: over_total (deaths 10 > 4), negative, conflicting_unknown, not_a_sibling, required.
- Dismiss with a reason: 200 `dismissed`. Without a reason, or with a short one: 422 in FastAPI's
  `detail` format (not `errors[]`). Dismissing again: 404.
- T5.3: re-running the evaluator over every flagged incident and the flags backfill changed nothing
  (resolved 5, dismissed 1 stay closed). An aggregate merge (msg 32095) and then a single-location
  merge onto the admin-resolved Nabatieh row left 1/3 unchanged and reopened nothing (rolled back).

## T6 Flag volume

- Per reason: count_missing 19 (17 messages); aggregate_no_breakdown 27 (12 bulletins).
  Total 46 flags on 45 incidents from **28 distinct messages**.
- Per message day: 09-03: 1; 09-04: 13 (7 msgs); 09-05: 14 flags / 13 incidents (5 msgs);
  09-06: 8 (7); 09-07: 9 (7); 09-09: 1. **Peak: 13 incidents, 7 messages in one day.**
  (The backfill's own per-day figure uses `created_at`, so it shows 43 on 09-07, an import date.)
- Largest bulletins: 31863 = 5, 32095 = 5, 32072 = 3, 31884 = 3, then 2 each for 32074, 31204,
  31308, 28917 and 31425, and 30149 = 1. No bulletin has more than 8 flagged rows, so no
  false-positive rule change was required under T6.
- Workload: over the 42 days of data, the average is 0.7 messages/day and the peak is 13 incidents,
  so the expected ~1 message/day and ~18-incident peak is **met on average and at the incident
  peak**. During the 4-7 September escalation it reached 5-7 messages/day.

## T7 Scratch stack

`docker-compose.casualty-test.yml` (untracked). Project `war_news_casualty_test`: db, redis,
backend and frontend only. No pipeline, CNRS, red-alert or sweep workers. Ollama/CNRS URLs point to
`127.0.0.1:9`, `RED_ALERT_ENABLED=false`, `CASUALTY_FLAGS_ENABLED=true`,
`CASUALTY_FLAG_GRACE_MINUTES=0`.

- Frontend http://localhost:5175, backend http://localhost:8002 (`/health` ok, `/docs`),
  Postgres localhost:5435.
- Login: `casualty_test_admin` / `CasualtyTest!2026` (super_admin, exists only in the scratch DB).
- State: 40 open flags. Bulletin 31863 is resolved and 1cb68d36 is dismissed from the API test.
- Code check: the Incidents page has the **Check type** filter (`IncidentsPage.tsx:472`), the type
  chips (`verificationBadge`), the **Review** button (`:626`); the detail page renders the inline
  **Casualty check** panel (`IncidentDetailPage.tsx:284`). No browser tool was available, so no
  screenshots were taken.

Stop: `docker compose -f docker-compose.casualty-test.yml stop`
Drop the stack and scratch DB: `docker compose -f docker-compose.casualty-test.yml down -v`
Remove images: `docker image rm war-news-casualty-test war-news-casualty-test-frontend war-news-casualty-test-main war-news-casualty-test-head`

## 8 Fixes made (all our code, regression tests included)

| File | Fix | Test |
|---|---|---|
| `scripts/fixes/casualty_status_backfill.py` | `--apply` now stores all six status fields (`casualty_deaths_status`, `casualty_injuries_status`, `casualty_status_remaining_total` were never written, so the flag backfill opened 0 flags); the concurrency guard is the version check | scratch run: I2 = 0, second run writes nothing |
| `app/news/repositories/incident_verification_flag_repository.py`, `app/news/services/casualty_flag_evaluator.py` | re-opening an unchanged flag no longer rewrites it and no longer adds an audit row on every evaluation (every hook call did) | `test_unchanged_open_flag_is_not_rewritten` |
| `app/news/services/incident_details/casualty_status.py` | a single-target count word uses the role target, not the plain `village` list, which also names merely mentioned places (msg 30335 «شهيدان») | `test_30335_dual_with_mentioned_non_target_villages_is_exact` |
| `app/news/repositories/incident_verification_flag_repository.py` | `list_open_for_incident` ignores flags already resolved/dismissed in the same session (no autoflush), so the resolve endpoint no longer turns them into `auto_cleared` | `test_list_open_for_incident_skips_flag_resolved_earlier_in_session` |
| `app/news/services/casualty_flag_evaluator.py` | aggregate `bulletin_totals` come from the stored status (remainder plus located exact counts) and are kept once set, so admin entries cannot become the total and over-total works after the cleanup nulls `total_*` | `test_aggregate_totals_come_from_status_when_row_totals_were_cleared`, `test_admin_entries_on_siblings_do_not_become_the_bulletin_total` |
| evaluator and `app/api/verification_flags_router.py` | location names fall back to the village's `ref_name_en` (summaries said "across Unknown, Unknown …") | covered by the scratch API run |
| `scripts/fixes/casualty_flags_backfill.py` | `--apply` also re-evaluates incidents with open flags, so stale ones are auto-cleared, and prints opened/updated/cleared totals | scratch run: 1 cleared, then 0 |

All 5 new unit tests fail on `HEAD` and pass with the fixes.

## Not fixed (reported)

- `duplicate_level='segment'` list crash (not our code; blocker; see Verdict).
- 14 `exact` incidents without a stored number (design choice; section 4).
- False-positive rules: named single victim «استشهاد المواطن …», past-martyr references
  «والد احد الشهداء», digest rows inheriting another town's casualty wording, and a toll tied to a
  named town «في بلدة X حيث ارتقى». Together these are 8 of the 46 flags.
- The dismiss-without-reason 422 uses FastAPI's `detail` shape, not `errors[]`.
- `casualty_flags_backfill` dry-run `per_day` uses `created_at`; `processed` counts an incident
  with two reasons twice.
