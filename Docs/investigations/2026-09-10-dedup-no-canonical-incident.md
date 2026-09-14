# Same-Event Duplicate Rows With No Canonical Incident

## Summary

The original hypothesis is partially confirmed, but the evidence points to the pre-extraction raw-message dedup stage rather than the fast-path incident-level dedup branch. Raw messages 9540, 9541, 9542, and 9543 were all marked `status = 'duplicate'` with `duplicate_of_id = 9539` before extraction or matching, so none of those four could be materialized. The chosen original raw message, 9539, was not materialized either: it is currently `status = 'error'` with `error_message = 'ConnectError: [Errno 111] Connection refused'`, no `extraction_result`, no `match_result`, no `materialized_at`, and no incident row. This produces the observed zero-canonical outcome, but not because fast-path dedup compared extracted messages against each other and failed to promote a winner.

## Evidence

Read-only SQL was run through the containerized database with `docker compose exec -T db psql -U postgres -d war_news_dev -c "...SELECT..."`. The relevant tables and columns used were `raw_messages.id`, `status`, `source_name`, `source_platform`, `external_message_id`, `message_datetime`, `received_at`, `dedup_checked_at`, `extracted_at`, `matched_at`, `fast_path_completed_at`, `tier2_completed_at`, `embedded_at`, `materialized_at`, `duplicate_of_id`, `filter_result`, `extraction_result`, `match_result`, `raw_text`; `incidents.id`, `raw_message_id`, `village_id`, `condition_id`, `event_date`, `event_time`, `is_deleted`, `verification_status`, `duplicate_flag`; and `duplicate_matches.incident_id`, `matched_incident_id`, `raw_message_id`, `match_type`, `similarity_score`, `status`.

For the four requested rows:

| raw_message_id | source_name | message_datetime | status | duplicate_of_id | extraction_result | match_result | materialized_at |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 9540 | bintjbeilnews | 2026-09-10 08:31:16+03 | duplicate | 9539 | null | null | null |
| 9541 | nabatiehchannel | 2026-09-10 08:30:42+03 | duplicate | 9539 | null | null | null |
| 9542 | Janoubana | 2026-09-10 08:32:23+03 | duplicate | 9539 | null | null | null |
| 9543 | mehwaralmokawma | 2026-09-10 08:45:25+03 | duplicate | 9539 | null | null | null |

All four had `filter_result->>'verdict' = 'relevant'`, `filter_result->'raw_response'->>'location' = 'كفرشوبا'`, and `filter_result->'raw_response'->>'event_subtype' = 'artillery'`. None had a materialized incident id or any incident reference. The query for `incidents` where `raw_message_id IN (9539,9540,9541,9542,9543)` or where an incident's `raw_message_id` matched their `duplicate_of_id` returned 0 rows. The query for `duplicate_matches` involving those raw ids or any incidents for those raw ids also returned 0 rows.

The actual target/original row is:

| raw_message_id | source_name | message_datetime | status | duplicate_of_id | extraction_result | match_result | materialized_at | error_message |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 9539 | sameralhajali | 2026-09-10 08:30:10+03 | error | null | null | null | null | ConnectError: [Errno 111] Connection refused |

The code path that matches the observed row state is pre-extraction dedup:

- `app/news/services/pipeline/pipeline_sweep_stages.py:153` defines `sweep_pre_extraction_dedup`; lines 183-191 select `status == parsed`, `extraction_result IS NULL`, and `duplicate_of_id IS NULL`; lines 201-210 process each raw id.
- `app/news/services/dedup/pre_extraction_dedup.py:89` builds the raw-message similarity query. Lines 106-116 exclude only `rejected`, `duplicate`, and `materialized` rows, meaning `error` rows remain eligible as duplicate originals. Lines 121-125 apply the configured narrowing mode. The defaults in `app/core/config.py:76-83` are threshold `0.92`, window `48` hours, narrowing `same_source`, and bucket `6` hours.
- `app/news/services/dedup/pre_extraction_dedup.py:19-32` picks the lower raw message id as the original. Lines 35-55 validate only that the original exists, is not itself `duplicate`, and does not point back to the candidate; they do not require the original to be extracted, matched, materialized, or even non-error. Lines 191-193 set `msg.status = MessageStatus.duplicate`, `msg.duplicate_of_id = original_id`, and commit.
- `app/news/services/pipeline/pipeline_sweep_stages.py:159-165` documents that a row marked duplicate here is skipped by extraction. `_count_pending_extraction_rows` also counts only parsed rows with `duplicate_of_id IS NULL` at lines 72-80, and the materialization sweep selects only parsed rows with `duplicate_of_id IS NULL` and `match_result IS NOT NULL` at lines 614-622.

The fast-path incident-level dedup code does not match the row state:

- `app/news/services/dedup/fast_path_dedup.py:90-100` checks existing active incidents via `find_fast_dedup_candidates`; if none exist it returns `materialize`.
- `app/news/repositories/incident_repository.py:1424-1510` implements that candidate search against the `incidents` table with `Incident.is_deleted IS false`, same village, same condition, and date window filters. It does not compare only raw messages.
- `app/news/services/materialization/incident_materialization_service.py:428-454` materializes possible duplicates as incidents and records a `duplicate_matches` row. Lines 469-519 merge confident duplicates into an existing canonical incident when a merge service is present, and lines 590-608 mark the raw message duplicate only after a canonical raw message id has been found. Lines 562-588 insert a new incident when the decision is materialize.
- `app/news/services/materialization/incident_materialization_service.py:332-339` acquires a same-village/condition advisory lock before fast-path dedup. `tests/test_fast_path_concurrent_dedup.py` asserts that two concurrent fast-path workers produce one incident and one duplicate match, which supports the intended first-wins behavior for this later stage.

The Rejected News UI maps the displayed "Duplicate" label to the raw message status:

- `app/api/rejected_news_router.py:126-131` returns rejection type `duplicate` when `message.status == MessageStatus.duplicate`, including `duplicate_of_id` in the reason.
- `app/api/rejected_news_router.py:211-216` includes raw messages whose status is `rejected` or `duplicate`.

## Root Cause Candidates

1. Pre-extraction dedup can choose an errored raw message as the original. This is strongly supported: ids 9540-9543 all point to 9539, and 9539 is `error` with no extraction, match, materialization, or incident.
2. Pre-extraction dedup treats a raw-message original as canonical before any incident exists. This is strongly supported by `pre_extraction_dedup.py:19-32` and `191-193`; the canonical target is a lower raw id, not a materialized incident id.
3. The original message failed extraction because the LLM/backend dependency was unavailable. This is supported by 9539's `ConnectError: [Errno 111] Connection refused`, and nearby rows 9535-9538 and 9544-9545 also show the same error.
4. Same-batch/concurrency race in fast-path materialization. This is not supported for this incident: the four duplicate rows never reached extraction, matching, or fast-path materialization, and fast-path code/tests use incident-backed candidates plus a village/condition advisory lock.
5. Recently touched casualty fields (`bulletin_casualty_groups`, `is_multi_village`, casualty scope handling). This is not supported for these rows because they never had `extraction_result` or `match_result`, so materialization code that creates bulletin groups or handles multi-village casualties never ran.

## Blast Radius

This is not specific to the four Kafarchouba rows or necessarily to same-minute multi-channel bursts. Any near-identical raw message can be suppressed before extraction if it is assigned to a lower-id original that later errors or otherwise never materializes. The current pre-dedup query narrows by `source_id`, and these Telegram messages all had `source_id = 3`, so the behavior can affect cross-channel bursts that share the same aggregate source id.

Rough live counts from read-only SQL:

| metric | count |
| --- | ---: |
| all `raw_messages.status = 'duplicate'` rows | 906 |
| duplicate rows with no active incident on either the duplicate raw id or its `duplicate_of_id` target | 461 |

Among duplicate rows whose `duplicate_of_id` target has no active incident, the target/original statuses were:

| original_status | duplicate_rows | distinct_originals |
| --- | ---: | ---: |
| materialized | 214 | 73 |
| parsed | 116 | 65 |
| error | 112 | 62 |
| duplicate | 23 | 16 |
| routed_air_violation | 2 | 2 |

The `materialized` bucket needs interpretation: those originals may have only soft-deleted incidents, missing incidents, or incident rows not counted by `is_deleted = false`. The `error`, `parsed`, `duplicate`, and `routed_air_violation` buckets clearly show that raw duplicate rows can point to targets that are not visible active canonical incidents.

Single-source events are less exposed if there is literally only one raw message, because pre-extraction dedup needs a similarity match. But a single-source event can still disappear if that source posts a correction/repost or nearly identical repeat and the lower-id original fails before materialization.

## Open Questions

- Should a pre-extraction duplicate target be allowed to be anything other than an already materialized raw message, or should this stage only suppress exact reposts after a durable canonical incident exists?
- Should errored originals automatically release or transfer their dependent duplicate rows for extraction/materialization retry?
- Are the 214 duplicate rows whose target raw message is `materialized` but has no active incident expected because of soft-deletes/manual rejection, or are they additional orphaned canonical cases?
- The current data shows two requested rows, 9542 and 9543, still have `processing_claim_stage = 'tier1_extraction'` even though they are `duplicate`. Is that stale claim metadata harmless, or does it affect retry visibility elsewhere?
