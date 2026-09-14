# Recon: Village Match and Multi-Action Extraction

Date: 2026-09-10

Scope: read-only investigation of wrong village matches, dropped villages, and collapsed multi-action extraction. No code or data changes were made.

## Part 1: Wrong Village Match

### Confirmed Root Cause

Part 1 is primarily a village matching/materialization problem exposed by imperfect extraction. The current persisted rows show low-confidence village matches being materialized as incidents, even when the matched village is not textually present.

For suffix/name-collision cases, extraction sometimes emits a partial place string such as `الفوقا` or bare `النبطية`. The matcher then compares that fragment with village names using trigram similarity and stores a best candidate even when the result is ambiguous. These examples were not high-confidence village matches: the stored `village_match_status` values for the wrong village rows are `matched_low_confidence`.

Current code has since added some mitigations:

- Exact active alias resolution before trigram matching: `app/news/repositories/village_repository.py:23-43`, used by `app/news/services/matching/matching_service.py:210-228`.
- Collision-like demotion and tie-margin handling: `app/news/services/matching/matching_service.py:36-42`, `app/news/services/matching/matching_service.py:252-274`, `app/news/services/matching/matching_service.py:431-468`.
- Geo-context re-ranking is present in current code: `app/news/services/matching/matching_service.py:79-95`, `app/news/services/matching/matching_service.py:116-142`, `app/news/services/matching/matching_service.py:280-342`, with settings at `app/core/config.py:148-149`.

So these rows appear to be at least partly pre/current-data-backlog behavior rather than proof that the current matcher is still pure trigram. However, current materialization still permits low-confidence village matches to create incidents.

### Evidence

Case 1A incident `328d9ee4-bae6-4540-93c8-94c0efce2c6a`:

- `raw_message_id`: `4118`
- Stored incident village: `Houmine El-Faouqa`, village id `703`
- Raw text contains: `الحنية`, `المنصوري`, `النبطية الفوقا`; it does not contain `حومين الفوقا`.
- `extraction_result.village`: `["الحنية", "المنصوري", "الفوقا"]`
- `extraction_result.village_roles`: `المنصوري`, `الحنية`, `الفوقا`
- `match_result.village_matches`:
  - `المنصوري` -> `976`, confidence `1.0`, `matched`
  - `الحنية` -> `1109`, confidence `0.4`, `matched_low_confidence`
  - `الفوقا` -> `703`, confidence `0.53846157`, `matched_low_confidence`
- The related `Minie` incident from the same raw message is `24379763-2637-4079-ac57-f81327fed8e5`; it came from raw text `الحنية`, not from `مينية` or similar appearing in the source text.

Candidate scores from direct `similarity(...)` SELECTs:

- For `الفوقا`:
  - `1153 Nabatiyeh El-Faouka / نبطية الفوقا`: `0.53846157`
  - `703 Houmine El-Faouqa / حومين الفوقا`: `0.53846157`
  - `1449 Temnine El-Faouqa / تمنين الفوقا`: `0.53846157`
  - `1434 Tannourine El-Faouqa / تنورين الفوقا`: `0.5`
- For `الحنية`:
  - `678 Henniy? / حنية`: `0.33333334`
  - `1319 Rihaniyet Aakkar / الريحانية`: `0.30769232`
  - Stored match was `1109 Minie / المنيه` at `0.4`, indicating the current repository scoring path differs from that simple ad hoc SELECT because current `find_similar` also scores normalized/compact variants at `app/news/repositories/village_repository.py:95-118`.

Case 1B:

- I found several Sep 6 rows matching the described family of symptoms.
- Bare `النبطية` rows materialized as `Douair En-Nabatiyeh` because direct trigram scores tie at `0.61538464` for several `... النبطية` villages; lowest id `543` wins in persisted historical rows.
- Direct scores for `النبطية`:
  - `543 Douair En-Nabatiyeh / الدوير النبطية`: `0.61538464`
  - `614 Hamra En-Nabattiyeh / الحمرا النبطية`: `0.61538464`
  - `741 Jbaa En-Nabatiyeh / جباع النبطية`: `0.61538464`
  - `874 Kfour En-Nabatieh / الكفور النبطية`: `0.61538464`
  - `1366 Sarba En-Nabatieh / صربا النبطية`: `0.61538464`
- Direct scores for `النبطية الفوقا`:
  - `1153 Nabatiyeh El-Faouka / نبطية الفوقا`: `0.73333335`
  - `543 Douair En-Nabatiyeh / الدوير النبطية`: `0.44444445`
- Existing alias data now includes `النبطية` -> Nabatieh Et-Tahta and `محيط النبطية الفوقا` -> Nabatiyeh El-Faouka in `app/news/services/matching/village_aliases.py:25-65` and `Data/VillageLocationAliases.json:7-35`.

### Generality Check

A general fix likely needs materialization policy changes for low-confidence village matches, plus extraction improvements to avoid emitting partial suffixes as standalone villages. Current code does contain evidence-backed reference alias entries for some affected patterns, but I did not find code-level `if village == ...` special-casing. Existing alias rows are data-level remediations, not control-flow special cases.

## Part 2: Dropped Village in Multi-Village Extraction

### Confirmed Root Cause

Case 2A is extraction-stage loss. Bint Jbeil exists in the village reference table, but Tier 1 extraction never emitted it for raw message `8566`, so matching and materialization never had a Bint Jbeil candidate to process.

### Evidence

Incident `08be2b9d-d0fd-44c5-80f4-b3bd0f4e86eb`:

- `raw_message_id`: `8566`
- Raw text includes `وتفجير كبير في بنت جبيل`.
- `extraction_result.village`: `["المنصوري", "النبطية الفوقا"]`
- `extraction_result.village_roles`: `المنصوري`, `النبطية الفوقا`
- `match_result.village_matches`: only those two villages.
- Materialized incidents for raw message `8566`: `Mansouri Sour / Bombs` and `Nabatiyeh El-Faouka / Bombs`.
- Reference data contains `280 Bent Jbayl / بنت جبيل`, plus related Bint Jbeil district villages.

Prompt/schema observations:

- The prompt asks for all multiple places in `village`: `app/llm/services/ollama_extraction_service.py:71`.
- `village_roles` are one object per village, not action-scoped: `app/llm/services/ollama_extraction_service.py:72`.
- `sub_events` describe actions and casualties, but the schema has no village list per sub-event: `app/llm/dtos/extraction_dto.py:85-92`.
- There is no explicit max-village cap in the DTO. I did not find an extraction token/output cap in `app/core/config.py`; the Ollama call uses the response schema at `app/llm/services/ollama_extraction_service.py:811-824`.

### Generality Check

The fix surface is extraction schema/prompt, and possibly downstream pairing if sub-events become village-scoped. Matching is not the cause for 2A because no Bint Jbeil match was attempted. I found no hardcoded Bint Jbeil special-case in application code.

## Part 3: Multiple Action Types Collapsed Into One Condition

### Confirmed Root Cause

Part 3 is a schema/prompt plus materialization coupling problem. Current DTOs can store multiple `sub_events`, and matching can produce `sub_event_matches`, but `ExtractionSubEvent` has no village field. Materialization therefore creates either one unit per village using the root condition, or a Cartesian village x sub-event split when two or more sub-events exist. If extraction emits zero sub-events and puts all action types into one root `action_description`, one condition wins and is applied to every village.

### Evidence

Case 3A incident `895b9598-12ef-4eb4-8286-d121a94413e6`:

- `raw_message_id`: `4388`
- `extraction_result.village`: `["زوطر الشرقية", "وادي السلوقي", "الجبل الرفيع", "دوحة كفررمان", "بني حيان"]`
- `extraction_result.sub_events`: `0`
- `extraction_result.action_description`: `تفجيرات وقصف مدفعي وتمشيط بالأسلحة الرشاشة`
- `match_result.raw_condition_text`: same combined text
- Condition matched to id `18`, `Sweeping Operations`, confidence `0.9130435`, status `matched`.
- Materialized rows for raw message `4388`: 5 incidents, all `Sweeping Operations`, including Kfar Roummane.

Case 3B incident `c71fae20-5bd1-4ab6-a14a-779121f1906e`:

- `raw_message_id`: `3304`
- `extraction_result.village` count: `29`
- Distinct extracted village strings: `25`
- Duplicates retained only for `المنصوري`, `بيت ليف`, `حولا`, `وادي السلوقي`; other repeated source villages under multiple action headings were not all repeated.
- `extraction_result.sub_events`: `0`
- `match_result.sub_event_matches`: `0`
- `action_description`: `غارات، قصف مدفعي وفوسفوري، غارات طيران مسير، تفجيرات، إحراق المنازل، تمشيط بالأسلحة الرشاشة`
- Materialized incident count: `24`
- Materialized conditions: only `Artillery Shelling`.

Relevant code:

- `ExtractionSubEvent` has `action_description`, casualties, evidence, but no village list: `app/llm/dtos/extraction_dto.py:85-92`.
- `ExtractionResult` stores global `village`, global `village_roles`, global `action_description`, and global `sub_events`: `app/llm/dtos/extraction_dto.py:120-126`.
- Matching creates one global condition from `extraction_result.action_description`, then optional condition matches for sub-events: `app/news/services/matching/matching_service.py:147-168`.
- Materialization reads root `matched_condition_id` first: `app/news/services/materialization/incident_materialization_service.py:263-304` and `app/news/services/materialization/incident_materialization_service.py:904-905`.
- `_build_materialization_units` falls back to one unit per village using the root condition when `len(paired) < 2`; with sub-events, it creates village x sub-event units without village/action scoping: `app/news/services/materialization/incident_materialization_service.py:1269-1325`.

### Generality Check

A general fix must touch extraction schema/prompt and materialization. The current schema cannot accurately represent “village A has shelling and demolition, village B has sweeping only” because sub-events are not linked to villages. Condition matching is doing what it is asked to do: choose one condition for a combined root action string when no sub-event structure exists.

## Shared or Independent Root Causes

Parts 2 and 3 overlap at the extraction representation layer: the system asks for a global village list and a global or unscoped action list, so complex bulletins can lose villages and cannot preserve village/action pairs. Part 2 is a plain extraction omission in the observed row; Part 3 is a structural loss of action-to-village relationships.

Part 1 is mostly independent. It is about ambiguous/partial village strings and low-confidence matches materializing into incidents. Extraction contributes by emitting partial strings, but the concrete wrong-village incidents are caused downstream by accepting those low-confidence matches as materializable villages.

## Open Questions

- Should low-confidence village matches ever materialize automatically, or should they be review-only until confirmed?
- For extraction, should the primary unit become an explicit `(village, action_description, evidence_span, casualties)` event object rather than global `village` plus global `action_description`?
- Should historical rows be reprocessed after current alias/geo/tie-margin improvements, or should fixes only apply prospectively?
- Do we want to preserve repeated same-village mentions under multiple action categories as separate incident rows even when casualties are null?
