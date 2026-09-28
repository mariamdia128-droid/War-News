# Casualty flow manifest

Commit manually. Do not include the pre-existing staged CSVs or the
`latest_red_alert.jpg` deletion.

## Commit 1 — status rule and backfill

- `app/news/services/incident_details/casualty_count_fill.py`: shared count-word helper.
- `app/news/services/incident_details/casualty_status.py`: row ownership and aggregate rules.
- `scripts/fixes/casualty_status_backfill.py`: primary plus merged-source derivation,
  aggregate suppression, missing-source reporting, classified remainder and CSV.
- `tests/test_casualty_status_row_rules.py`.

## Commit 2 — merge guard and leak cleanup

- `app/news/services/incident_details/casualty_merge_guard.py`.
- `app/news/repositories/incident_repository.py`: guard in `merge_existing` and
  `apply_story_revision`, `_casualty_merge_guard`, admin-edited count protection.
- `scripts/fixes/casualty_merge_leak_cleanup.py`.
- `tests/test_casualty_merge_guard.py`.

## Commit 3 — evaluator, hooks, config and flags backfill

- `app/news/services/casualty_flag_evaluator.py`.
- `app/news/services/verification_flag_service.py`.
- `app/news/repositories/incident_verification_flag_repository.py`.
- `app/news/repositories/incident_repository.py`: hooks in admin edits, rejection,
  duplicate resolution, merge/story revision and `_record_soft_delete`.
- `app/news/services/materialization/incident_materialization_service.py`: fast/full hooks.
- `app/news/services/extraction/tier2_detail_fill_service.py`: Tier 2 hook.
- `app/news/services/reconciliation/bulletin_reconciliation_service.py`: reconciliation hook.
- `scripts/fixes/casualty_flags_backfill.py`.
- `tests/test_casualty_flag_evaluator.py`.
- `app/core/config.py`: only the two `casualty_flag_*` fields are ours.
- `.env.example`: only the casualty flag comment and two variables are ours.

## Commit 4 — API

- `app/api/verification_flags_router.py`.
- `app/api/router.py`: verification-flags import/include only.
- `app/api/incidents_router.py`: `get_incident_verification_flags` only.
- `app/news/dtos/incident_dto.py`: `open_casualty_flags_count` only.
- `app/news/repositories/incident_repository.py`: open visible flag count in detail.

## Flags in Incidents page

- `app/news/repositories/incident_repository.py`: visible-needs-verification
  `EXISTS`, status/type filters, summary count reuse, bulk page flag payloads,
  and detail payloads. Stored incident verification fields remain unchanged.
- `app/news/dtos/incident_dto.py` and `app/api/incidents_router.py`:
  `verification_type`, `verification_types`, and `open_flags` contracts.
- `frontend/src/features/news/pages/IncidentsPage.tsx`: URL-persisted Check type
  filter, chips/reasons, and sequential casualty-review dialog.
- `frontend/src/features/news/pages/IncidentDetailPage.tsx`: inline casualty
  check cards replacing the route link badge.
- `frontend/src/features/casualtyChecks/components/CasualtyCheckPanel.tsx` and
  `hooks.ts`: reusable inline rendering and incident/list/flag invalidation.
- Removed only the casualty-check import and two route rows from
  `frontend/src/app/routes.tsx`; removed only its nav item, page metadata,
  summary hook and badge render from `frontend/src/app/AppShell.tsx`; deleted
  the standalone `CasualtyChecksPage.tsx` and unused list/summary frontend calls.

The earlier queue plan to group flags by bulletin is cancelled: Incidents is
already per-incident. Aggregate-toll review still shows all sibling locations
inside the panel.

### Finish B2 resolve-contract follow-up

- `app/api/verification_flags_router.py`: per-incident partial resolution,
  per-type unknown markers, backward-compatible `confirmed_unknown`, structured
  field errors, per-incident results, and assigned/remaining totals.
- `app/news/repositories/incident_verification_flag_repository.py`:
  `update_open_resolution` is the exact C1 hunk; it audits partial open-flag
  detail/resolution changes. Other dirty hunks in this shared file predate C1.
- `tests/test_verification_flags_api.py`: contract, partial save,
  per-location unknown, field errors, non-sibling, over-total, and legacy tests.
- `tests/test_casualty_flag_evaluator.py`: only
  `test_previously_resolved_is_not_reopened` is the C1 hunk.
- `frontend/src/features/casualtyChecks/types.ts`: new entry/error/result types.
- `frontend/src/features/casualtyChecks/api.ts`: typed resolve response.
- `frontend/src/features/casualtyChecks/logic.ts` and `logic.test.ts`: payload
  builder and incident/field error mapping.
- `frontend/src/features/casualtyChecks/components/CasualtyCheckPanel.tsx`:
  per-type unknown controls, partial-save result handling, server remaining
  totals, and field-level errors.

## Migration chain

### Finish A-FIX â€” source snapshots, flag noise and grouping

- `app/news/services/casualty_flag_evaluator.py`: saves a trimmed 4,000-character
  source text, message datetime and source name; updates preserve the snapshot
  when the raw row is unavailable.
- `app/api/verification_flags_router.py`: snapshot fallback, aggregate grouping
  by source/reason, group-level paging and summary counts, location previews and
  partial-resolution group size.
- `app/news/services/incident_details/casualty_status.py`: a casualty sub-event
  naming another town but lacking structured locations no longer creates an
  aggregate toll on every unrelated bulletin location.
- The casualty-check frontend types and panel render grouped rows and the
  saved-snapshot fallback note. The standalone list page was removed.
- Focused tests cover source deletion, 5-to-1 grouping, partial open groups,
  individual missing-number checks and bulletin 32249.

Verified read-only DB facts on 2026-09-28: 7,393 raw messages remain (IDs 1 to
34,339), and all 1,445 live incidents retain valid primary source references.
The 1,678 missing distinct raw IDs occur only in historical `pipeline_merge`
audit JSON (3,269 references, IDs 364 to 11,877, audit dates 2026-08-26 through
2026-09-17). No automatic retention/purge job or setting was found. The only
repository `DELETE FROM raw_messages` is an explicitly run, tag-scoped
accuracy-study cleanup script. Selective historical cleanup/restore/reseed is
therefore the leading explanation, but the exact external operation is not
provable from repository or database evidence.

The 18 recent aggregate rows came from three bulletins: message 32249 (16 rows,
false positive), 32412 (one genuine two-location motorcycle-strike toll), and
32735 (one genuine multi-location injury total). Message 32249's single death
belongs to Brashit in an unlocated sub-event and is now suppressed for the
other 16 bulletin locations.

The incident-correlated visibility query gets an incident-first index in
`20260928_0072_add_incident_flag_visibility_index.py`. Chain:
`0068 -> 0069 -> 0070 -> 0071 -> 0072`; code head is `20260928_0072`.

After migrations are applied, run exactly:

```powershell
docker compose run --rm backend pytest -q tests/test_casualty_flag_evaluator.py tests/test_verification_flags_api.py tests/test_casualty_status_row_rules.py tests/test_casualty_persistence_schema.py
docker compose run --rm backend python -m scripts.fixes.casualty_flags_backfill --since 2026-09-14
docker compose run --rm frontend npm run typecheck
```

## Shared dirty files — our exact hunks

- `.env.example`: `CASUALTY_FLAGS_ENABLED`, `CASUALTY_FLAG_GRACE_MINUTES`, comment.
- `app/core/config.py`: the two `casualty_flag_*` fields.
- `app/news/repositories/incident_repository.py`: casualty imports, detail count,
  hook calls, guarded casualty loops, `_casualty_merge_guard`,
  `_admin_edited_casualty_fields`.
- `app/news/services/materialization/incident_materialization_service.py`:
  evaluator import and two calls immediately before insert commits.
- `app/news/services/extraction/tier2_detail_fill_service.py`: evaluator import
  and loop immediately before Tier 2 commit.
- `app/news/services/reconciliation/bulletin_reconciliation_service.py`:
  evaluator import and loop before reconciliation commit.
- Removed standalone casualty-check page lines:
  `frontend/src/app/routes.tsx` casualty page import and `/admin` plus
  `/superadmin` child routes; `frontend/src/app/AppShell.tsx` casualty nav item,
  page metadata, summary hook and count badge; `frontend/src/features/casualtyChecks/pages/CasualtyChecksPage.tsx`;
  unused list/summary frontend API and hooks.

## Housekeeping

The staged `scripts/fixes/out/casualty_cleanup_dryrun.csv`,
`scripts/fixes/out/casualty_status_backfill_dryrun.csv`, and staged
`latest_red_alert.jpg` deletion are not ours. This session did not alter their
staged state.

## Lost incidents

### Suggested commit 1 — visible holds and matching repairs

- `app/news/services/dedup/fast_path_eligibility.py`: only the
  `HELD_UNMATCHED_PLACE`, unmatched-target detection, terminal-status mapping,
  and equivalent bulk SQL hunks are from this work.
- `app/news/repositories/village_repository.py`: only `_alias_key_matches` and
  its two call-site replacements are from this work.
- `app/llm/services/transient_llm_errors.py`: only the server-disconnect and
  `RemoteProtocolError` transient markers are from this work.
- `app/core/llm_knowledge/CHANGELOG.md`: the 2026-09-28 lost-incidents entry.
- `tests/test_fast_path_eligibility.py`, `tests/test_village_location_aliases.py`,
  and `tests/test_transient_llm_errors.py`: lost-incident regression hunks only.

### Suggested commit 2 — safe requeue tooling

- `app/news/services/pipeline/errored_message_requeue.py`.
- `app/news/repositories/raw_message_repository.py`: only
  `requeue_for_matching`, `requeue_for_extraction`, `_reset_to_parsed`, and
  `_append_requeue_audit` are from this work.
- `scripts/fixes/requeue_errored_messages.py`.
- `tests/test_errored_message_requeue.py`.

### Suggested commit 3 — reviewable reference-data proposal

- `scripts/fixes/out/proposed_village_aliases.sql`: review Section C first,
  review Sections A/B, replace the final `COMMIT` with `ROLLBACK` for a manual
  preview, and execute only after explicit approval. This session did not run it.
- After approved alias SQL, run `scripts/fixes/requeue_errored_messages.py`
  without `--apply`, review the CSV/examples, then separately authorize an
  `--apply` run. This session ran dry-run only.
- `scripts/fixes/out/requeue_errored_messages_dryrun.csv` is generated review
  output and should not be mixed with the pre-existing casualty CSVs.

No migration, schema change, extraction-prompt change, or condition-table
addition is part of Lost incidents. The changelog documents why the behavior
changes are lookup, pipeline-status, and transport-retry policy rather than LLM
knowledge changes.

## Scratch-DB verification run (2026-09-28)

Report: `Docs/recon/casualty_flow_test_report.md`. Suggested single commit
"Fix casualty backfill and flag resolution defects found on scratch DB":

- `scripts/fixes/casualty_status_backfill.py`: `--apply` stores all six status fields.
- `scripts/fixes/casualty_flags_backfill.py`: re-evaluates open flags; prints flag changes.
- `app/news/services/casualty_flag_evaluator.py`: unchanged flags are not rewritten;
  bulletin totals from stored status and kept once set; village-name fallback.
- `app/news/repositories/incident_verification_flag_repository.py`: `is_unchanged`,
  no-op `open_flag`, `list_open_for_incident` in-memory status check.
- `app/news/services/incident_details/casualty_status.py`: single-target count words use
  role targets first.
- `app/api/verification_flags_router.py`: location-name fallback (5 lines).
- Tests: `tests/test_casualty_flag_evaluator.py` (3 tests),
  `tests/test_casualty_status_row_rules.py` (1), `tests/test_verification_flags_api.py` (1).

New files: `scripts/recon/casualty_flow_invariants.py`, `Docs/recon/casualty_flow_test_report.md`,
`Docs/recon/casualty_flow_test/` (CSVs and run logs). Do not commit
`docker-compose.casualty-test.yml` (scratch stack only).

Not ours, required before rollout: `app/news/dtos/incident_dto.py` `duplicate_level` must allow
`"segment"` (two places), otherwise the Incidents list returns 500 on the real data.

## Manual-test setup and Verification filter fixes (2026-09-28, second run)

Suggested commit "Fix Incidents verification view: outside-range notice, partial-save panel,
duplicate reason, live-stream filter". All hunks below are ours; the shared files had no other
dirty hunks from this run.

- `app/news/repositories/incident_repository.py` (shared file; ours only):
  `outside_range_filters` / `outside_range_count` block in `list_all` right after the summary query,
  `needs_verification_outside_range_count=` in the `IncidentListResponse(...)` call, new classmethod
  `_outside_range_needs_verification_filters` just above `_list_ordering`, and in
  `_verification_payload` the duplicate branch `verification_reason=duplicate_reason or
  "Possible duplicate of another incident"`. HEAD has mixed CRLF/LF in this file; the working copy
  keeps HEAD's line endings (diff is +36/-1).
- `app/news/dtos/incident_dto.py`: `IncidentListResponse.needs_verification_outside_range_count`
  (1 line). The `duplicate_level` "segment" fix is still NOT in the working tree (not ours; see above).
- `app/api/verification_flags_router.py`: `_live_remaining_total` helper and its use in `get_flag`
  for aggregate flags (sibling flags now show the remainder after a partial save on another location).
- `frontend/src/features/news/verificationLogic.ts`: `ALL_DATES_RANGE`, `isVerificationView`,
  `outsideRangeNotice`, `hasNonDefaultFilters`.
- `frontend/src/features/news/pages/IncidentsPage.tsx`: imports, `hasFilters` via
  `hasNonDefaultFilters` (default dates no longer count as filters), `verificationView`,
  `outsideRangeText`, sort note after the result count, outside-range notice with "Show all dates".
- `frontend/src/features/news/types.ts`: optional `needs_verification_outside_range_count`.
- `frontend/src/features/news/hooks.ts`: `matchesFilters` exported; it rejects stream events while a
  check type or channel filter is active; non-matching events no longer bump `total`.
- `frontend/src/features/casualtyChecks/logic.ts`: `unresolvedSiblingIds`.
- `frontend/src/features/casualtyChecks/components/CasualtyCheckPanel.tsx`: internal active flag id;
  after a partial aggregate save the panel moves to the next open sibling flag instead of closing.
- Tests: `tests/test_incident_visible_verification_flags.py` (4 new),
  `tests/test_verification_flags_api.py` (1 new + import), `frontend/src/features/news/verificationLogic.test.ts`
  (3 new), new `frontend/src/features/news/incidentStreamFilters.test.ts` (3),
  `frontend/src/features/casualtyChecks/logic.test.ts` (1 new + import).

Optional (docs, commit if wanted): `Docs/recon/manual_test_checklist.md`,
`Docs/recon/casualty_flow_rollout_runbook.md`, `scripts/rollout/casualty_flow_rollout.ps1`,
`scripts/rollout/reset_scratch.ps1`, `Docs/recon/casualty_flow_test/u2_api_read_checks.txt`,
`Docs/recon/casualty_flow_test/u2_api_write_flow.txt`.

Do not commit: `docker-compose.casualty-test.yml`, `backups/` (contains
`backups/scratch/war_news_casualty_test_baseline.dump`, 23.6 MB, used by `reset_scratch.ps1`;
suggest adding `backups/` to `.gitignore`), the CSVs under `Docs/recon/casualty_flow_test/`.
No screenshots were produced (no browser automation available).

No new migration. `alembic heads` from code: exactly one, `20260928_0072`.

## Incident DTO "segment" fix and rollout preflight (2026-09-28, third run)

Suggested commit "Accept segment duplicate level in incident read models". Required before the
rollout: without it the Incidents list returns 500 on the real data.

- `app/news/dtos/incident_dto.py` (ours in this run, on top of the earlier
  `needs_verification_outside_range_count` line): `import logging`, `get_args` import,
  module-level `logger`, `DuplicateLevel = Literal["low", "medium", "high", "segment"]`,
  `_DUPLICATE_LEVELS`, `_display_duplicate_level`; `duplicate_level: DuplicateLevel | None` in
  `IncidentListItemDTO` and `IncidentDetailDTO`; a `_tolerant_duplicate_level` before-validator in
  both (unknown value -> `None` + warning). Read models only; write DTOs unchanged.
  `"segment"` is written by `app/news/services/dedup/segment_review_dedup.py:101`, committed in
  `3480afb` (2026-09-16); the DTO was never updated. No uncommitted work of others involved.
  No DB check constraint exists on `incidents.duplicate_level`.
- `frontend/src/features/news/types.ts`: `"segment"` added to `duplicate_level` (1 line).
- New test: `tests/test_incident_dto_enum_values.py` (12 tests).
- `scripts/rollout/casualty_flow_rollout.ps1`: preflight works out the pending revisions from the
  DB's own `alembic_version` (graph from the migration files), prints them next to the code head,
  skips step 4 at head, reports existing `incident_verification_flags` rows/indexes and stops if the
  0072 index exists while 0072 is pending; rollback B defaults to the pre-rollout revision.
- `Docs/recon/casualty_flow_rollout_runbook.md`: step 4 row, migration section and rollback B no
  longer assume `20260924_0062`.
- Optional: `Docs/recon/casualty_flow_test/f3_real_rows_validation.txt` (read-only validation log).

**`backups/` must not be committed** (scratch baseline dump; rollout backups land there too).
The scratch-only DTO patch is no longer used; the scratch image is now built from the working tree
as is. No new migration; `alembic heads` from code: exactly one, `20260928_0072`.
