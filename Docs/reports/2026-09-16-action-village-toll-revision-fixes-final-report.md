# Action/Village Binding, Collision, Sub-Location, and Toll-Revision Fixes

Date: 2026-09-16

## Outcome

All requested implementation phases were completed and verified. The pipeline now preserves the relationship between each extracted action and its locations, uses each location/event's own matched condition during materialization, handles explicit district context before geographic fallback, avoids treating parenthetical qualifiers as independent villages, suppresses no-op toll history entries, exposes toll source attribution, infers narrowly supported singular casualties, and treats two-endpoint route reports as one story context without copying casualties to both endpoints.

No migration was generated or run. No data-modifying SQL was executed. No commit or push was performed during this continuation.

The repository already had commit `954ac24` (`Phase 1 add vehicle movement condition data`) immediately before the no-commit instruction. All subsequent work remains uncommitted.

## Phase 0 — Assumption and drift confirmation

The recon assumptions were rechecked against the current extraction, matching, materialization, revision, casualty, and frontend paths. Previously noted line-ending drift was preserved while substantive work continued.

## Phase 1 — Condition reference data

- Added `Vehicle Movement` / `تحرك آليات` to `Data/Conditions.json` without a hardcoded numeric ID.
- Added a manual, idempotent insert script at `scripts/manual/add_vehicle_movement_condition.sql`.
- Added aliases for vehicle movement wording, including `تحرك لآليات`, `تحرك للآليات`, `تحركت آليات`, and related forms.
- Added detonation variants such as `تفجير`, `تفجيران`, and `تفجيرات`, mapped to the existing Mining & Detonation condition.
- Added direct singular sound-bomb wording for `إلقاء قنبلة صوتية` and `قنبلة صوتية`.

Manual action still required: review and execute `scripts/manual/add_vehicle_movement_condition.sql` if the database does not yet contain the new condition. The script was not run.

## Phases 2–4 — Event-scoped extraction, qualifiers, matching, and materialization

### Extraction contract

`ExtractionSubEvent` now uses the event shape:

- `locations`
- `action_text`
- `casualties`
- `evidence_span`
- `casualty_evidence`

Persisted legacy `action_description` values remain readable through a validation alias and compatibility accessor.

The Ollama JSON schema requires complete event locations, location roles, local casualty fields, evidence, and `qualifier_text`. Sub-events without locations are rejected rather than being multiplied across every village.

Sub-event location evidence, qualifier text, event evidence, casualty evidence, and casualty counts are validated against the source before persistence.

### Prompt behavior

Both Tier-1 prompts now require:

- One scoped sub-event per distinct action when a bulletin contains multiple actions.
- Only the locations belonging to that action inside each event.
- Parenthetical sub-areas and landmarks to remain qualifiers of the preceding village.
- Parenthetical district/qada labels to remain administrative context and never become independent targets.
- Route endpoints to remain grouped as locations of one event.

The rules are pattern-based and contain no one-off production mapping for Froun, Wadi el-Khanzir, Qsair, Zibdine, or any raw-message ID.

### Matching and materialization

- Conditions are matched for each sub-event and copied to each event location's `VillageMatchResult`.
- Fast-path eligibility accepts valid per-village event conditions even when the combined root action cannot be matched.
- Event-indexed locations do not fall back to the root condition when their own condition is missing.
- `_fast_path_units()` now creates only source-declared location/action pairs.
- The old village × locationless-sub-event Cartesian expansion was removed.
- Fast and non-fast materialization use event-local casualties and event-specific hash suffixes.
- Multi-location event casualties are retained only on the location entry carrying the explicit local count.
- Distinct-village checks now count unique village IDs rather than event rows.
- Event siblings and route endpoints receive a shared story group.
- `qualifier_text` is retained in match JSON and included in the incident note for display while the original report remains searchable.
- Tier 2 continues to fill only null conditions and does not overwrite a correctly materialized per-village condition.

## Phase 5 — Village collision resolution

- Collision detection now recognizes the mention as a complete token sequence anywhere in a longer reference name.
- Explicit `قضاء ...` context is read from both the location text and `qualifier_text`.
- Matching candidates in the stated district are filtered and promoted before lexical classification.
- Multi-token districts such as `بنت جبيل` are preserved.
- Alias matching is not allowed to bypass explicit district context.
- Existing geographic re-ranking remains the fallback when no usable district context exists.
- The existing single-anchor policy and configured 20 km / 5 km-advantage constraints remain unchanged.

Regression coverage confirms:

- Message 10395: bare Qsair resolves to Aadchit El-Qoussair in the South Lebanon context.
- Raw 9298: Zibdine with Nabatiyeh qada context resolves to Zibdine En-Nabatiyeh rather than Zibdine Jbayl.

## Phase 6 — Toll revision history

`IncidentRepository._toll_revisions_for()` now excludes a story-revision entry when the displayed old and new death/injury values are identical.

The underlying `IncidentUpdate` pipeline-merge record is still written, so deduplication, story-revision classification, and audit history are unchanged.

The DTO now carries existing `merged_from` attribution:

- `source_raw_message_id`
- `source_channel`
- `source_khabar`

Malformed or historical non-object `merged_from` payloads degrade safely to missing attribution.

## Phase 7 — Source attribution UI

- Each attributed toll revision displays a `View source` link.
- The link preserves the current admin/superadmin role base.
- The existing rejected/raw-message detail page supports a source-view mode and opens the requested `raw_message_id`.
- Source mode hides rejection-only and restore controls.
- The authenticated raw-message detail endpoint can display a materialized source message, not only rejected or duplicate messages.
- Historical revisions without a source ID render normally without a link.

No database column or foreign-key migration was added because attribution already exists in `IncidentUpdate.new_values`.

## Phase 8 — Singular casualty inference

A deterministic backstop runs before gender filling and infers one death only when:

- no death total or gendered death count already exists;
- exactly one gendered singular death form is present; and
- the wording has a current-event casualty context such as a death caused by a raid, strike, or shelling.

The terminology now includes singular martyr/killed forms for masculine and feminine Arabic. Normalization is applied consistently, fixing feminine forms such as `شهيدة`.

The backstop explicitly avoids:

- plural wording;
- mixed `شهيد وشهيدة` wording;
- reports that already contain a death total; and
- honorific/historical phrases such as a page name containing `الشهيد`.

Raw 9298's singular `شهيد في غارة` wording now yields one death and can subsequently fill the male demographic count.

## Phase 9 — Route casualty attribution

The existing `casualty_scope` and bulletin-group implementation was reused. No parallel route-only schema was introduced.

The route case fits `per_village_exact` when the explicit count is attached to one endpoint's location entry. Materialization preserves the count and demographics on that endpoint and leaves the other endpoint null rather than copying the toll.

For a single-action route without sub-events, a general route rule treats both dash-separated endpoints as story-equivalent candidate villages. This allows a Haroof-side follow-up to route to the canonical Zibdine incident while retaining normal story-relationship classification.

Regression coverage confirms that raw 9302 can route to the raw 8788 Zibdine incident and that its exact casualty is not duplicated across both route endpoints.

## Phase 10 — Regression verification

Backend:

- Named original-case regressions: 7 passed.
- Targeted extraction/matching/materialization/revision/casualty suite: 152 passed.
- Full backend suite: 712 passed.
- Warnings: 8 existing deprecation/SQLAlchemy warnings; no failures.

Frontend:

- TypeScript typecheck passed.
- Vitest: 50 passed across 10 files.
- Production build passed.
- Vite reported only the existing large-chunk advisory.

Static checks:

- IDE diagnostics reported no lint errors in changed implementation files.
- Python compilation passed.
- Git whitespace validation passes when CRLF is treated as an allowed line ending.

The originally failing CNRS webhook tests were time-dependent: their fixed timestamp had moved outside the configured webhook lookback window. The fixture now uses a current, stable test timestamp. The duplicate-rescan expectation was also updated to match the current comparison authority, where an embedding score above `embedding_possible` inside the 30-minute window is high-confidence rather than merely possible.

## Regression cases

- Message 10395:
  - event/location action binding;
  - no Cartesian multiplication;
  - South Lebanon Qsair collision resolution.
- Message 10387:
  - parenthetical Wadi el-Khanzir remains a qualifier;
  - only Froun is matchable/materializable.
- Raw 9298:
  - explicit Nabatiyeh qada resolves the correct Zibdine;
  - singular martyr wording infers one death.
- Raw 8788/9298/9302:
  - route endpoint story equivalence;
  - route follow-up can revise the canonical Zibdine incident;
  - exact casualty count is not copied to both endpoints.

## Operational notes

- Review and manually execute `scripts/manual/add_vehicle_movement_condition.sql` before relying on Vehicle Movement in a live database.
- Existing historical raw messages and incidents are not rewritten automatically. Reprocessing/backfill, if desired, should be designed and reviewed separately.
- A normalized `incident_updates.raw_message_id` foreign key remains a possible future optimization if attribution queries become frequent; it is not required for the current UI.
- No commit or push was performed.
