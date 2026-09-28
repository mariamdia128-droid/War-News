# Casualty verification recon

**Date:** 2026-09-28 · **Branch:** `main` @ `bad8a73` · **DB:** `war_news_dev` (docker `db`, alembic head `20260924_0062`)
**Scope:** read-only investigation for a new casualty-verification type (missing number / aggregate toll / preliminary toll). Findings only, with no design proposal.

## Headline findings

1. **Admins cannot see any non-duplicate verification flag today.** 419 live incidents are stored as `verification_status='needs_verification'`, but only 3 appear in the UI, because the API treats NV as "visible" only when `duplicate_flag` is true (`incident_repository.py:2400-2405`, `:2415-2420`). Every existing casualty-related reason is stored but hidden.
2. **Casualty messages are rare in this DB.** Of 887 materialized messages, 4.4% (39) fall in C∪D∪E. They cluster in one escalation week (2026-09-03 to 09-09), with a peak of 12 messages / 18 incidents per day.
3. **"No number", "explicitly zero" and "no casualty mention" are all stored as NULL.** 0 is never used for a stated zero. The 3 zeros in the DB are all extraction errors.
4. **About half of bucket C ("casualties, no number") is really an extraction miss.** The text has an exact count as a singular or dual word (شهيدان، شهيد) and the LLM returned null.
5. **Bug A: the aggregate leak exists in 4 historical messages (14 rows).** All were created 2026-09-07, before the 2026-09-09 guard. There is also one post-guard (2026-09-14) row where a bulletin total sits on a single village (mechanism unverified).
6. **The existing bulletin machinery has never fired usefully.** `casualty_scope` is `bulletin_aggregate` on only 7 of 1,799 messages that carry the field. All 7 `bulletin_casualty_groups` rows have null totals and are `expired`. The 34 existing "Unsupported casualty_scope=bulletin_aggregate" flags come from 3 messages with no casualty words at all.
7. **Nothing clears a flag when a number arrives later.** The only automatic clear is an unconditional reset on any successful merge, and it wipes every reason, not just duplicate ones.

---

## 1. Code map

### 1.1 Where casualties are extracted

| Piece | Location | Notes |
|---|---|---|
| Tier 1 prompt (general) | `app/core/llm_knowledge/rules/tier1_general_prompt.md:23,29,48,64-74` | Per-village `deaths/injuries` in `village_roles` (`:23`); "a target village with no explicit count → null, not 0 and not the bulletin toll" (`:29`); no inference from plurals (`:65-66`); vague quantifiers → null (`:68-69`); `casualty_evidence` required per non-null field (`:71`); `casualty_scope` definitions (`:72-74`). |
| Tier 1 combined prompt | `app/core/llm_knowledge/rules/combined_tier1_prompt.md:53-61` | Same rules in English (vague quantifiers, `casualty_scope`, `casualty_scope_evidence`). |
| Multi-village rules | `app/core/llm_knowledge/rules/tier1_multi_village.md:11,22,24,58` | `per_village_exact` via sub_events (`:11`); shared toll → `bulletin_aggregate` (`:22`); worked example with totals only at root (`:58`). |
| Tier 2 prompts | `rules/tier2_category_detail_prompt.md:47`, `rules/tier2_batched_category_detail_prompt.md:19` | Only the vague-quantifier rule is casualty-specific. |
| Tier 2 service | `app/news/services/extraction/tier2_detail_fill_service.py:247-258` | Multi-village rows keep fast-path per-village counts. Root toll is copied only when `not is_multi_village` and the current value is `None` **or 0**. |
| DTOs | `app/llm/dtos/extraction_dto.py` | `CasualtyScope` enum `:36`; `VillageRoleEntry` (per-village `deaths/injuries/evidence_span`) `:74`; `ExtractionCasualties` (10 nullable ints) `:93`; `CasualtyCountEvidence` `:108`; `ExtractionResult.casualty_scope*` `:194-197`. |
| Tier 1 assembly | `app/llm/services/ollama_extraction_service.py:529-640` | Count backstop `:537`; scope validation `:602-608`; result assembly `:620-640`. |
| Count backstop | `app/news/services/incident_details/casualty_count_backstop.py:80-151` | Keeps a count only if its evidence span holds the digit, **or** an Arabic word for **1 or 2 only** (`:36-50`). Fallback `:132-140`: if the span is missing or ungrounded, any occurrence of that digit anywhere in the text keeps the value. |
| Scope backstop | `app/news/services/incident_details/casualty_scope_backstop.py:77-113`, called at `ollama_extraction_service.py:1691-1718` | `bulletin_aggregate` is plausible only if the evidence names ≥2 target villages. `per_village_exact` is plausible if any named village has a count. Otherwise it is downgraded to `unspecified` with `casualty_scope_needs_review=True` and reason `"Unsupported casualty_scope=…"`. |
| Per-village assignment at materialization | `incident_materialization_service.py:1806-1860` | For multi-village messages, root totals are **not** copied onto village rows (`:1850-1855`, guard added in `470f5e9`, 2026-09-09). `is_multi_village` counts only villages with a `matched_village_id` (`_distinct_target_village_count`, `:339`, `:1144`). Sub-event path is `_event_casualties_for_match` `:1775`. |
| Bulletin group write | `incident_materialization_service.py:1862-1891` | Creates a `bulletin_casualty_groups` row only when `casualty_scope == bulletin_aggregate` and ≥2 distinct matched village ids. |

### 1.2 NULL vs 0 vs "no data", end to end

| Layer | Representation |
|---|---|
| Extraction DTO | All counts are `int \| None` (`extraction_dto.py:78-79, 96-105`). The prompt default is null for everything (`tier1_general_prompt.md:83-94`). There is no field for "text says casualties but gives no number" and none for "text explicitly says none". |
| DB | `incidents.deaths / injuries / total_deaths / total_injuries` are nullable `Integer` (`app/news/models/incident.py:98-101`). `bulletin_casualty_groups.total_*` are nullable (`bulletin_casualty_group.py:41-42`). |
| Merge | `_max_preserving_empty` (`incident_repository.py:2660-2664`) keeps NULL only if both sides are NULL, otherwise `max(current or 0, incoming or 0)`. So NULL+0 → 0 and NULL+N → N. |
| Tier 2 | Treats `0` as "empty" and overwrites it with the root toll on single-village rows (`tier2_detail_fill_service.py:252-258`), despite the comment at `:247-249` saying 0 means "stated as zero". |
| API list filter | `has_casualties` uses `coalesce(total_*, 0) > 0` (`incident_repository.py:2482+`), so NULL and 0 are both "no casualties". |
| Frontend | `IncidentDetailPage.tsx:548-559` renders `value ?? "No data"`, so NULL shows "No data" and 0 shows "0". The list page does not show counts. |

### 1.3 Where `needs_verification` / `verification_reason` are set

**Storage and model.** There is no `needs_verification` column. The model has `verification_status String(24)` (`auto_processed | needs_verification | verified | rejected`; `incident.py:136-139`, `Literal` in `incident_dto.py:29,57,178`) plus one free-text `verification_reason` (Text). **There is no enum of reasons, and an incident carries at most one reason.** Later writers overwrite earlier ones; for example, fast-path precedence is scope-review reason, then extraction review, then category suppression, then `_verification_reason()`.

**Fast path.** `_insert_fast_incident` (`incident_materialization_service.py:941-1030`) calls `_initial_verification_status` (`:76-98`: duplicate, insufficient score, low-confidence village, condition review) and then `_verification_reason()` (`app/news/services/materialization/verification_signals.py:9-39`). A `scope_review_reason` forces NV (`:989-1001`).

**Full path.** `incident_materialization_service.py:1325-1360`. `_extraction_review_reason` (`:139-144`, which returns `casualty_scope_review_reason` or `review_reason`) and `category_casualties_suppressed` force NV with reason "Category casualties require manual per-village confirmation for a multi-target bulletin".

**Merge paths.**
- High-score dedup merge at materialization (`:1258-1271`): sets NV for category suppression or scope review.
- `incident_repository.py:1491-1513`: a casualty-transition conflict sets NV with `duplicate_flag=True`. Otherwise it **resets NV → `auto_processed` whatever the reason**.
- Heuristic story revision that would lower counts (`:1617-1621`).
- Demotion of `verified` after a pipeline write (`:1780-1786`).

**Tier 2.**
- `tier2_detail_fill_service.py:268-282`: category suppression / scope review.
- `:353-356`: retry cap reached.
- `:528-531`: possible duplicate.

**Other writers.**
- `segment_review_dedup.py:103-104`
- `rejected_news_router.py:354-360` (restore)

**Existing casualty-related signals.** All are free strings:
- `"Unsupported casualty_scope=<scope>: evidence matched N target village(s)"`
- `"Category casualties require manual per-village confirmation for a multi-target bulletin"`
- `"Possible duplicate — casualty count conflict detected during merge…"`
- `"Unconfirmed story revision … would lower …"`

**Visibility gate.** `_needs_verification_column()` = NV **and** `duplicate_flag` (`incident_repository.py:2400-2405`, commit `06beb93` "fix: limit incident verification to duplicates", 2026-09-14). The list and detail payloads rewrite non-duplicate NV to `auto_processed` and a null reason (`:274-290`, `:552-563`). `_is_casualty_review_reason` (`:2408-2412`) is defined but never called. `_should_keep_needs_verification_after_duplicate_clear` always returns `False` (`:2423-2427`).

### 1.4 `bulletin_casualty_groups` / Bug A state

- **Model and migration exist:** `app/news/models/bulletin_casualty_group.py` and `alembic/migration/20260909_0055_add_bulletin_casualty_groups.py` (commit `15f3c70`, 2026-09-09). The table is present in the DB.
- **Reconciliation is wired:** `BulletinReconciliationService` (`app/news/services/reconciliation/bulletin_reconciliation_service.py`) runs in the `bulletin-reconciliation-worker` compose service (`docker-compose.yml:119-132`, every 1800 s, 60 h window, `app/core/config.py:140-142`). `_apply_candidate` (`:137-188`) writes only `deaths`/`injuries`. It does **not** update `total_*` and does **not** touch `verification_status`.
- **Data state:** 7 groups, all `expired`, 0 with a non-null total, 0 resolved.
- **Git:** on `main`, up to date with origin. At session start the working tree had uncommitted flare-bomb and condition-reconciliation work, which was committed during the session as `abe1219`, `2011e11` and `bad8a73`. None of it touches casualty logic. `git log -15` shows no casualty or Bug A commits after 2026-09-16.

### 1.5 Arabic singular / dual forms

- **Terminology** `app/core/llm_knowledge/terminology/casualty_gender.yaml`:
  - singular, e.g. شهيد `:9`, جريح `:52`
  - dual, e.g. شهيدان `:23`, جريحان `:68`
  - plural, e.g. شهداء `:118`
  - `death_count_word` قتيل/قتيلان `:151-169`
- **مصابين appears twice**, as `male_injury_dual` (`:83`) and as `male_injury_plural` (`:136`).
- **Code:** `casualty_count_backstop.py:28-50` maps these words to the values 1 and 2 only. There is **no mapping for spelled-out numbers ≥3** (ثلاثة شهداء). Such a count survives only if a digit also appears in the evidence or text. `casualty_gender_evidence.py:34-63` uses the same forms for gender inference.
- **Prompts:** there is no explicit dual rule. The only examples are «شهيد و3 جرحى» → deaths=1 (`tier1_general_prompt.md:55`) and «شهيدين و6 جرحى» → total_deaths=2 (`tier1_multi_village.md:58`). The prompts forbid converting plurals (`tier1_general_prompt.md:66`).

### 1.6 Admin UI

- **List** (`frontend/src/features/news/pages/IncidentsPage.tsx`): the verification badge appears only when NV **and** `duplicate_flag==="possible"` (`:192-197`). The reason is shown under the badge (`:313-315`). There is a "Needs verification" counter (`:186`, `:370-373`) and a review dialog (`:741`).
- **List filters:** village, condition, source name, verification status (`:445-452`), date range, duplicate only, has casualties (`:527-533`). API parameters are in `app/api/incidents_router.py:50-64`. There is no filter by reason.
- **Detail** (`IncidentDetailPage.tsx`): NV badge `:231-232`; casualty grid `:548-559`; bulletin group card with a pending countdown `:585-625`; toll revision history `:512-514`.

### 1.7 A later message supplies the missing number

- **Counts.** A merge into the same incident takes `max()`, so a later number fills a NULL (`incident_repository.py:1520-1541`). Bulletin reconciliation fills per-village `deaths/injuries` from a later breakdown message (`bulletin_reconciliation_service.py:137-188`).
- **Flags.** Nothing checks whether a number arrived. NV is cleared only as a side effect of a successful merge (`:1503-1513`) or a duplicate marked false-positive (`:1134-1145`), and both clear **every** reason. Bulletin reconciliation does not clear NV.
- **Preliminary-toll markers** (`revision_language_markers.yaml:9-72`) are used only for story routing and relationship classification (`story_revision_backstop.py:56-117`, `story_candidate_search.py:32`, `story_relationship_service.py:20`). They never set a flag. `rules/story_revision_prompt.md` exists but is not wired (per `Docs/audit-reports/extraction-to-action-flow-audit-2026-09-24.md:164`).

---

## 2. Bucket counts

**Window:** incident `event_date` 2026-08-17 → 2026-09-28 (all data in the DB).

**Primary universe:** relevant extracted messages with ≥1 live incident, i.e. **887 messages → 1,445 live incidents**.

**Secondary universe:** all 4,648 relevant extracted messages. This includes 1,582 `duplicate`, 1,489 `error` and 292 `routed_air_violation` messages.

**Script:** `scripts/recon/casualty_verification_recon.py` (SELECT-only, `readonly=True` session plus `SET TRANSACTION READ ONLY`, rolled back).

### Classification (per message; A–D, F mutually exclusive; E is an overlay)

- **has_num** = the extraction kept any root count, any per-target `village_roles` count, or any sub-event count.
- **multi** = ≥2 target locations (extraction targets, or distinct incident villages).
- **Keywords** are matched on normalized text (hamza unified, tashkeel and tatweel stripped, and the page header «صفحة الإعلامي الشهيد علي شعيب» removed).
- **Bucket rules:**
  - B = multi and a per-location count present
  - D = multi and (root count or a digit+casualty noun in text) and no per-location count
  - A = has_num and single location
  - C = casualty keyword and no number extracted
  - F0 = explicit «دون إصابات» type text
  - F = the rest
  - X = single location, digit in text, not extracted
- **E** = «حصيلة أولية/مؤقتة/غير نهائية/نهائية، المعلومات الأولية، ارتفاع/ارتفع عدد، تحديث/مراجعة/تصحيح الحصيلة».

| Bucket | Definition | Materialized msgs | % of 887 | Incidents | All relevant msgs | % of 4,648 |
|---|---|---:|---:|---:|---:|---:|
| A | exact number, single location | 31 | 3.5% | 31 | 119 | 2.6% |
| B | multi-location, per-location breakdown | 6 | 0.7% | 32 | 14 | 0.3% |
| C | casualty keyword, no number extracted | 21 | 2.4% | 29 | 85 | 1.8% |
| D | multi-location aggregate, no breakdown | 8 | 0.9% | 23 | 12 | 0.3% |
| E | preliminary / revision language (overlay) | 15 | 1.7% | 24 | 36 | 0.8% |
| X | number in text but not extracted | 0 | 0% | 0 | 7 | 0.2% |
| F0 | explicit "no casualties" | 8 | 0.9% | 14 | 33 | 0.7% |
| F | no casualty mention | 813 | 91.7% | 1,316 | 4,378 | 94.2% |

E overlaps the other buckets: A 9, D 3, C 2, F 1 (materialized).

### Accuracy of the keyword/regex pass (from manual review of every materialized C, D, E and B row and 10 A rows)

- **Header false positive, fixed.** The first pass put 151 messages in C because the page name «الإعلامي الشهيد علي شعيب» appears in 464 messages (166 materialized). The script now strips it. Any production detector needs the same exclusion.
- **C (21 materialized):**
  - about 8 are "C1" (singular or dual word, so the count is implicit in the text and the extraction missed it)
  - about 2 more are singular nouns («استشهاد مواطن») that imply 1
  - 1 false positive (28455 «والد احد الشهداء», an unrelated martyr)
  - about 10 are genuine "casualties, no number" («وقوع إصابات»، «شهداء وجرحى»، «سقوط ضحايا»، «استشهاد وإصابة مواطنين»)
  - Sub-type counts across all relevant messages: C1 27, C2 vague quantifier 8, C4 bare plural or verb 47, other 3.
- **D (8):** 5 true aggregates and 3 false positives:
  - 32412: «طريق مرج حاروف - زبدين» is one event on a road between two villages
  - 28917: one village's toll inside a multi-item digest
  - 31308: the text *has* a per-location breakdown that the extraction collapsed to root
- **D misses:**
  - 29321 («4 شهداء و20 جريحا … على عربصاليم والنبطية والنبطية الفوقا وكفررمان») landed in A because only one incident row survived
  - 32735 landed in B (see §4.4)
- **E (15):** 13 are real toll-status language. 32045 «معلومات أولية عن غارة» is preliminary *strike* information, not a toll. 2 hits are «حصيلة نهائية», which is final rather than preliminary.
- **A (31):** at least 4 are wrong values:
  - 30496 «وقوع إصابات» → injuries=1
  - 31816 «عشرات الجرحى» → injuries=10
  - 31315 «ووقوع إصابات» → injuries=0
  - 29321, an aggregate
  - The first three were extracted 2026-09-07 with empty `casualty_evidence`, the same day the count backstop landed (`1397250`). The current backstop would null them.
- **B (6):**
  - 32708: strike counts «النبطية الفوقا (١١)، حولا (٢)» were read as deaths=11 and deaths=2. The digit is in the span, so the backstop accepts it. Incident `8fc74304` (Houla) shows d=2.
  - 32735/32756/32767 are copies of one MoH bulletin. The short copy (32735) is an aggregate; the long copies have a real breakdown, but rows are misattributed (§4.4).
- **Recall:** only 4 materialized messages carry a casualty cue the keyword list misses (obfuscated «الشهـ..»، «ارتقى»), and all 4 have extracted numbers (bucket A). F contains no known casualty messages without a number, but F was not exhaustively sampled.
- **Overall:** the regex works as a first-pass *recall* net. As a flag trigger it would be about 50% precise for C, about 60% for D and about 85% for E.

---

## 3. Examples per bucket (5 each, trimmed)

Incident values are `d / i / td / ti` = deaths / injuries / total_deaths / total_injuries. No example has a `casualty_scope` value except where shown, because pre-2026-09-14 extractions have no scope field. `evidence_span` is shown where one exists.

### A — exact number, single location
| msg | incident | text | extracted | scope |
|---|---|---|---|---|
| 32036 | e15b8ee6-5705-4a77-89c4-7808f778b8b4 (ميفدون) | «4 جرحى في حصيلة أولية للغارة التي إستهدفت ميفدون» | root ti=4 → row ti=4, i=NULL | — |
| 31492 | 2c255b6b-875c-4f3e-bb2f-43c12918521e (كفر رمان) | «استشهاد مسعف في كشافة الرسالة وإصابة 2 آخرين في غارة العدو على سيارة في كفررمان» | 1 / 2 / 1 / 2 | — |
| 31946 | 4b0a525e-070e-44c1-8fc9-dc64a5b3a3e3 (كفر رمان) | «والمعلومات الأولية تشير إلى وقوع إصابتين» | – / 2 / – / 2 | — |
| 30140 | 9f5855d0-e7ff-4a68-b706-4d6b79a137b4 (كفر رمان) | «ما أدى إلى استشهاد مسعف وإصابة اثنين آخرين» | 1 / 2 / 1 / 2 | — |
| 28686 | 8bf5fa89-00a6-4e87-923c-388c4b707443 (كفر رمان) | «الحصيلة النهائية… النبطية: ضحية و3 جرحى… كفررمان…» | – / 3 / – / 3 (the 3 belongs to النبطية, not كفررمان) | — |

### B — multi-location with a per-location breakdown
| msg | incident | text | extracted (village_roles) | scope |
|---|---|---|---|---|
| 32767 | 5cc96ca9-845b-43e8-a1e4-563d6fbd1c32 (ريحانة جزين) | «الريحان قضاء جزين: شهيد / النبطية حي المسلخ: 9 جرحى… / النبطية الفوقا: جريح» | الريحان d=1; النبطية حي المسلخ i=9; النبطية الفوقا i=1 → row 1 / – / 1 / – | unspecified (downgraded, needs_review) |
| 32756 | a876b81c-b70e-4b20-a14a-84c7557d3c78 (الدوير النبطية) | same bulletin | same roles → row **1 / 9** / 1 / 9 (the death belongs to الريحان) | unspecified (downgraded) |
| 32708 | 8fc74304-a55d-4e3d-9d24-e1cf4b9c1730 (حولا) | «الغارات من الطيران الحـربي: • النبطية الفوقا (١١) • كفررمان (٢)… حولا (٢)» | evidence_span «حولا (٢)» → d=2 (**strike count read as deaths**) | unspecified |
| 32249 | 7b1e1589-520b-4ec3-abf7-1e3a4bf61503 (القنطرة) + 15 rows | «…استشهاد مواطن من بلدة برعشيت بعد اصابته برصاص العدو…» | one sub-event d=1; all 16 rows NULL (برعشيت not materialized) | unspecified |
| 33187 | 12e50bad-… (حولا) + 6 rows | «ملخص الإعتداءات الإسرائيلية… بتاريخ ١٣/٩/٢٠٢٦» | sub-events 8/11 and 1/2; all 7 rows NULL | unspecified |

### C — casualty keyword, no number
| msg | incident | text | extracted | sub-type |
|---|---|---|---|---|
| 31539 | b05c0b8b-b626-4fe8-8709-900c9f60a043 (كفر رمان) | «شهيدان في غارة إسرائيلية استهدفت دراجة نارية في بلدة كفررمان» | all NULL (**dual missed**) | C1 |
| 30335 | b2e88fe2-0407-4b48-87be-f2ad13535e73 (كفر رمان) | «شهيدان جراء غارة معادية على دراجة نارية في كفررمان» | all NULL (dual missed) | C1 |
| 31438 | 87cf6aaa-fc00-4ba0-8b23-febba4b02124 (نبطية الفوقا) | «غارة… تستهدف دراجة نارية في بلدة النبطية الفوقا وأنباء عن وقوع إصابات» | all NULL | C4 |
| 31245 | e6a1bf5a-a293-436f-aa7b-764eefdf7cc0 (ميفدون) | «غارة إسرائيلية أدت لتدمير منازل واستشهاد وإصابة مواطنين» | all NULL | C4 |
| 32074 | e1106287-8e01-4e42-a203-0fbc987e85b1 (عين التينه المنيه) + 932d6033 | «شهداء وجرحى جنوبًا وبقاعًا..» | all NULL | C4 (multi-location, no number) |

### D — multi-location aggregate, no breakdown
| msg | incidents | text | extracted | scope |
|---|---|---|---|---|
| 32072 | 81a5822c-f5fa-4c6c-bec6-7a8b0119ee0e (نبطية التحتا), c238e070 (الوقف), cd0dac06 (صور) | «5 شهداء و24 جريحًا حصيلة سلسلة غارات… بينها النبطية وصور والبقاع الغربي» | root td=5 ti=24; all 3 rows NULL (correct, unflagged) | absent |
| 31884 | d34027f5-7a42-42b1-862f-b15c1fe7e19c (الدوير النبطية) + 2 | same MoH text, second source | root 5/24; rows NULL | absent |
| 32095 | b1097a42-47f4-43e1-9ff5-1cf89cd01cf9 (رمادية) + 4 | «3 شهداء و23 جريحا في حصيلة أولية لغارات العدو هذا المساء» | root d=3 i=23 → **3/23 stamped on all 5 rows** | absent |
| 31863 | 96e09f61-3155-41d9-81a2-9373bc74f4a1 (عين التينة) + 4 | «4 شهداء و32 جريحا في حصيلة نهائية لغارات العدو أمس» | root 4/32 → **stamped on all 5 rows** | absent |
| 31425 | 970268f1-baa7-46e4-85d1-ee6c357588ab, a1ec7059-beeb-4c8a-8c8a-ba2045082e2f | «3 شهداء و23 جريحا في حصيلة أولية…» | root td=3 ti=23 → i=23 on both rows | absent |

### E — preliminary / revision language
| msg | incident | text | extracted |
|---|---|---|---|
| 32000 | 89a5b113-4140-4974-b0f9-2903a9bedc69 (رمادية) | «4 جرحى في حصيلة اولية للغارة على الرمادية» | root ti=4 → row all NULL (row is NV: low-confidence village) |
| 31495 | 78145585-421c-4c24-8c04-dbf701cb7bcb (رمادية) | «شهيد وعدد من الجرحى في حصيلة غير نهائية للغارة على منزل في الرمادية» | all NULL (singular شهيد missed) |
| 30149 | 512c900e-e5c3-45b6-b526-89c304d75277 (رمادية) | «شهيدان وجرحى في حصيلة أولية للغارة على الرمادية - صور» | all NULL (dual missed) |
| 31415 | 636e9cec-4223-467a-a7bd-d3c52721a299 (نبطية الفوقا) | «ومعلومات أولية عن سقوط شهيدين» | d=2 (correct) |
| 32095 | b1097a42-… (see D) | «…في حصيلة أولية لغارات العدو هذا المساء» | aggregate stamped on 5 rows |

---

## 4. Gap analysis

### 4.1 What is flagged today (materialized, stored vs visible)

| Bucket | Incidents | Stored NV | Visible NV | Not flagged | Stored reasons |
|---|---:|---:|---:|---:|---|
| C | 29 | 9 (31%) | 0 | 20 | 7 low-confidence village, 1 null, 1 "Unsupported casualty_scope=per_village_exact" |
| D | 23 | 6 (26%) | 0 | 17 | 4 low-confidence village, 1 null, 1 "Category casualties require manual per-village confirmation" |
| E | 24 | 8 (33%) | 0 | 16 | 7 low-confidence village, 1 null |

- **No C, D or E row is flagged *because of* casualties.** Where a row is flagged, the reason is almost always the village match, and it is hidden anyway.
- **The real gap is 100%:** 29 C rows, 23 D rows and 24 E rows have no visible casualty review signal.
- **All live NV incidents, by reason:**
  - 346 low-confidence village
  - 34 "Unsupported casualty_scope=bulletin_aggregate"
  - 31 null reason
  - 4 "Unsupported casualty_scope=per_village_exact"
  - 2 "Category casualties…"
  - 2 duplicate-flagged
- **The 34 bulletin_aggregate flags are all false.** They come from 3 multi-village messages with no casualty words; the model tagged a shelling list as `bulletin_aggregate`.

### 4.2 Bucket C: did a later message or merge supply the number?

- **Filled in place:** 2 of 29 C incidents now carry a number. One came through a logged `pipeline_merge`.
- **Number landed elsewhere:** 10 of 29 are still NULL while a **separate later incident** in the same village or story group within ±1 day has counts. The number exists in the DB but on a different, unlinked row. Examples:
  - 30335 كفر رمان → later 32095 row `baf456b2` (3/23)
  - 31438 نبطية الفوقا → later 31863 row `6ff50399` (4/32)
  - 29118 عرب صاليم → later 31007 row `fdd35f95` (d=2)
- **Merged C messages:** 20 C messages have status `duplicate` (merged into a canonical); 8 of those canonicals carry a number.
- **Auto-clear estimate:** a flag cleared "when the incident later gets a number" would have cleared **2/29** on its own. A clear that looks across village + story group ±1 day would reach **12/29**. Both counts are unverified as to whether the later number refers to the same event (several later rows are the leaked D aggregates).

### 4.3 Bucket D: Bug A leak (aggregate stamped on individual rows)

- **Scale:** 4 messages / 14 rows. Each has the same non-zero count on ≥2 village rows equal to the root aggregate: 32095 (3/23 ×5), 31863 (4/32 ×5), 31425 (i=23 ×2), 28917 (9/13 ×2).
- **Timing:** all rows were created **2026-09-07**, before the multi-village guard (`470f5e9`, 2026-09-09). Later `pipeline_merge` entries re-write the same values; for example, b1097a42 was re-written on 09-07 and 09-09. No backfill has cleaned them up.
- **Not leaked:** 7 of 23 D rows correctly hold NULL (32072, 31884), but they carry no flag.
- **Post-guard single-row variant (unverified mechanism):** incident `b5a71798-d190-427a-82c9-85a950eeb0e2` (عين الريحان, msg 32735, 2026-09-14) holds d=1 **i=10**, the bulletin total. Rihan's own extracted role has i=NULL; the 10 injuries belong to النبطية (9) and النبطية الفوقا (1). The row was created at 08:22:17, before msg 32735's own `extracted_at` (08:22:19), so it originated from another copy of the bulletin and was re-pointed.
- **Related sub-event path:** `_event_casualties_for_match` (`incident_materialization_service.py:1775-1804`) falls back to sub-event totals when `event_location_count` is missing or ≤1.

### 4.4 NULL vs 0

| Column (1,445 live incidents) | NULL | 0 | >0 |
|---|---:|---:|---:|
| deaths | 1,396 | 0 | 49 |
| injuries | 1,398 | 3 | 44 |
| total_deaths | 1,395 | 0 | 50 |
| total_injuries | 1,396 | 3 | 46 |

- **Every 0 is wrong:**
  - 28793 «حزام ناري ٤ غارات» → i=0
  - 31315 «ووقوع إصابات» → i=0; the text *affirms* injuries
  - 32064, where the text has no casualty mention → i=0
- **Explicit-zero text is stored as NULL:** all 14 rows from F0 messages («دون تسجيل إصابات») hold NULL, not 0.
- **Extraction roots** (4,648 relevant messages): `injuries=0` on 2 messages, other fields never 0.
- **Consequence:** the data cannot distinguish "no casualties mentioned", "explicitly none" and "mentioned but no number". Only a text re-scan or a new field can. `deaths` and `total_deaths` agree in 1,444 of 1,445 rows.

### 4.5 Arabic singular / dual without an adjacent digit (all 4,648 relevant messages)

| Form | Messages | Correct | NULL (missed) | Other value |
|---|---:|---:|---:|---:|
| Dual deaths (شهيدان/شهيدين/شهيدتان/شهيدتين/قتيلان/قتيلين) → 2 | 32 | 16 | 12 | 4 (3 or 4, from merges or aggregates) |
| Dual injuries (جريحان/جريحين/جريحتان/جريحتين/مصابان) → 2 | 16 | 4 | 8 | 4 (12–32, merged or aggregate) |
| Singular death (شهيد/شهيدة/قتيل, no ال) → ≥1 | 38 | 22 | 16 | 0 |
| Singular injury (جريح/جريحة, no ال) → ≥1 | 15 | 10 | 5 | 0 |
| Spelled-out ≥3 (ثلاثة شهداء…) | 1 | 1 | 0 | 0 |

- The misses are LLM omissions. The backstop does accept 1 and 2 words (`casualty_count_backstop.py:36-50`).
- Examples:
  - 31539 «شهيدان…» → NULL
  - 29191 «النبطية الفوقا: شهيدان وجريحان» → neither extracted
  - 31871/31938/31954 «شهيدان وجريح… جريح إثر الغارة…» → NULL (status `error`)
- Spelled-out numbers ≥3 are rare in this data (1 message), but the backstop would null them unless a digit is present.

---

## 5. Flag volume estimate

These are the counts if C + D + E were flagged exactly as classified today, on materialized messages and by incident `event_date`, over 40 days with data:

| Series | Mean/day | Median | p90 | Max | Total |
|---|---:|---:|---:|---:|---:|
| All materialized messages | 22.2 | 17 | 57 | 119 | 887 |
| All incidents | 36.1 | 25 | 84 | 159 | 1,445 |
| C msgs | 0.5 | 0 | 1 | 7 | 21 |
| D msgs | 0.2 | 0 | 1 | 3 | 8 |
| E msgs | 0.4 | 0 | 0 | 7 | 15 |
| **C∪D∪E messages** | **1.0** | **0** | **3** | **12** | 39 |
| **C∪D∪E incidents** | **1.6** | **0** | **4** | **18** | 62 |

- **Concentration:** almost all volume falls on 2026-09-04 to 09-07 (12, 6, 7 and 9 messages/day; 18, 14, 13 and 11 incidents/day). August has none. Casualty flags track escalation days, not a steady rate.
- **Ratio for scaling:** about 4.4% of materialized messages and 4.3% of incidents.
- **Manageability:** with the regex precision in §2, about half of the C flags and about 40% of the D flags on a peak day would be noise or extraction misses. The peak is about 18 incident rows (≈12 messages).
- **Hidden-flag context:** 416 NV incidents already sit hidden, 346 of them low-confidence village. If the visibility gate is lifted for casualty reasons only, the load stays small.
- **Caveats** (this DB is not a steady-state sample):
  - materialization nearly stopped after 2026-09-17 (1–26 messages/day)
  - 1,875 messages are in `error`, 1,305 of them "fast_path: unmatched or missing condition"
  - C messages that are merged duplicates (20) would add flags onto existing canonicals, not new rows

---

## 6. Risks / open questions

### 6.1 Where "no number" is indistinguishable from "zero"
- NULL covers "not mentioned", "explicitly none" (F0) and "mentioned without a number" (C). 0 is used only by mistake (§4.4).
- A C/D flag cannot be derived from DB columns alone; it needs text or an extraction signal. `ExtractionResult` has no "casualties mentioned but uncounted" field.
- Tier 2 treats 0 as empty and overwrites it (`tier2_detail_fill_service.py:252-258`). The merge turns NULL+0 into 0 (`incident_repository.py:2660-2664`). A future "stated zero" would be overwritten or promoted inconsistently.
- `has_casualties` and the frontend "No data" rendering both conflate NULL with 0 or unknown.

### 6.2 Where the current pipeline would produce a wrong flag or miss a real one
- **Visibility.** Any new reason stays invisible unless the duplicate-only gate changes (`incident_repository.py:2400-2420`, `IncidentsPage.tsx:195`).
- **Overwrites.** One free-text reason per incident: a casualty reason overwrites, or is overwritten by, low-confidence village and duplicate reasons. Precedence differs between the fast path (`:989-1001`) and the full path (`:1336-1360`).
- **Accidental clears.** Any successful merge resets NV and reason, whatever the reason (`incident_repository.py:1503-1513`). The false-positive duplicate decision does the same (`:1134-1145`). A casualty flag would be silently cleared by an unrelated merge.
- **Source header.** «صفحة الإعلامي الشهيد علي شعيب» (464 messages) triggers naive casualty-keyword detection. Named-victim obituaries («تنعى الشهيد…») are casualty mentions with an implicit count of 1.
- **False aggregate flags.** `casualty_scope=bulletin_aggregate` is emitted with all-null totals. All 7 bulletin groups have null totals, and the 34 existing downgrade flags come from non-casualty messages. The scope field cannot be trusted as a D trigger.
- **Blind spots in the scope backstop.**
  - `per_village_exact` passes when evidence lists several villages but only one has a count; see 32735, where the "per-village" evidence is «شهيد و10 جرحى… على الريحان والنبطية والنبطية الفوقا».
  - Strike counts in parentheses «(١١)» pass the digit backstop as deaths (32708).
- **Full-text digit fallback.** When the evidence span is missing, any matching digit anywhere in the text (dates, times, URLs) validates a count (`casualty_count_backstop.py:132-140`).
- **Ambiguous مصابين.** It is listed as both dual and plural (`casualty_gender.yaml:83,136`), so a hallucinated injuries=2 for plural «مصابين» would pass the backstop. This did not show up in sampled data (unverified).
- **Unmatched villages.** `is_multi_village` counts only villages with a `matched_village_id` (`incident_materialization_service.py:339,1144`). If only one village of a multi-village aggregate matches, the root fallback applies and the aggregate lands on that one row. Not observed directly in this data; 29321 is consistent with it but predates the guard.
- **Revision markers.** «حصيلة نهائية» and «معلومات أولية عن غارة» match the markers but are not preliminary tolls. The markers drive routing, not flags.

### 6.3 Conflicts with in-flight work
- **Bug A / bulletin groups.** Infrastructure is live but inert (7 expired groups, null totals). Reconciliation updates `deaths/injuries` but not `total_*` or NV. A D-flag would need to coordinate with `breakdown_status` (pending → resolved/expired) and the worker's 60 h window. The 14 pre-guard leaked rows (§4.3) remain in data.
- **Toll revision.** `apply_story_revision` flags only heuristic lowering (`incident_repository.py:1617-1621`). The audit reports sparse late preliminary bulletins lowering counts, with no monotonicity guard (`Docs/audit-reports/extraction-to-action-flow-audit-2026-09-24.md:164`). `story_revision_prompt.md` is not wired. An E flag and the revision path would both touch the same incidents.
- **Merge logic.** `max()` merging (`:1520-1541`) makes a preliminary low count be superseded, but it also makes a stamped aggregate "win" over a later correct per-village count. The unconditional NV reset on merge conflicts with any persistent casualty flag.
- **`casualty_updated_at` migration.** It **does not exist**: no file, no model field and no reference in any commit (`git log --all -S casualty_updated_at` is empty). Separately, the DB is behind the code:
  - DB head `20260924_0062`; on disk `20260924_0063…0067` are unapplied, e.g. `incidents.deleted_reason` is in the ORM model but missing in the DB
  - `20260923_0062/0063` form a **second alembic head** (`20260923_0063` → `20260923_0062` → `20260923_0061`, parallel to `20260924_0062`), so `alembic upgrade head` will report multiple heads
  - Any new column for this feature lands on top of that.
- **Extraction eras.** 3,208 of 5,007 extractions (2026-08-24 → 09-09, plus 19 `cnrs_provided`) predate `casualty_scope`, `sub_events` and the count backstop. Any backfill or flag based on extraction fields will behave differently for those rows.

### 6.4 Unverified
- The exact code path that produced `b5a71798`'s i=10 after the guard (§4.3).
- Whether the 10 "later sibling" rows in §4.2 describe the same event as the C row.
- F-bucket recall beyond the obfuscation and «ارتقى» check (4 misses found, all already in A).
- Production volumes: this is `war_news_dev` with partial, bursty ingestion.

---

## Files touched

- `scripts/recon/casualty_verification_recon.py`: new, read-only recon script (SELECT only, read-only transaction, rolled back)
- `Docs/recon/casualty_verification_recon.md`: this report (the repo's existing `Docs/` folder; `docs/` resolves to it on Windows)

All other SQL was ad-hoc `BEGIN READ ONLY; SELECT …; ROLLBACK;` via `docker compose exec db psql`. No source, migration, LLM rule file or data was changed.
