# Dedup Follow-up: Ollama Connectivity and Materialized Orphans

## Connectivity Summary

The `ConnectError: [Errno 111] Connection refused` failures are a recurring live condition in this database snapshot, not an isolated one-off. `raw_messages` currently contains 180 rows with `status = 'error'` and `error_message ILIKE '%connection refused%'` / `'%ConnectError%'`. The raw data spans `received_at` 2026-08-24 11:30:44+03 through 2026-09-10 10:02:03+03; within the last 14 days of available data, connection-refused errors cluster heavily around two ingestion/processing periods: 61 rows received around 2026-09-07 09:00+03, and 108 rows received between 2026-09-10 09:00 and 10:00+03. The event-day view spreads those rows across Sep 4, Sep 7, Sep 8, Sep 9, and Sep 10 because many messages were backlogged and processed later than their source `message_datetime`.

Read-only SQL used:

```sql
SELECT date_trunc('day', coalesce(message_datetime, received_at))::date AS event_day,
       count(*) AS connection_refused_errors,
       min(id) AS min_id,
       max(id) AS max_id,
       min(received_at) AS first_received,
       max(received_at) AS last_received
FROM raw_messages
WHERE status='error'
  AND error_message ILIKE '%connection refused%'
  AND coalesce(message_datetime, received_at) >= (
      SELECT max(coalesce(message_datetime, received_at)) - interval '14 days'
      FROM raw_messages
  )
GROUP BY event_day
ORDER BY event_day;
```

Result:

| event_day | connection_refused_errors | min_id | max_id | first_received | last_received |
| --- | ---: | ---: | ---: | --- | --- |
| 2026-09-04 | 61 | 3458 | 3549 | 2026-09-07 09:12:59+03 | 2026-09-07 09:12:59+03 |
| 2026-09-07 | 12 | 8863 | 8970 | 2026-09-10 09:16:45+03 | 2026-09-10 09:16:46+03 |
| 2026-09-08 | 4 | 9067 | 9070 | 2026-09-10 09:16:47+03 | 2026-09-10 09:16:47+03 |
| 2026-09-09 | 56 | 8800 | 9508 | 2026-09-09 14:55:54+03 | 2026-09-10 09:16:50+03 |
| 2026-09-10 | 38 | 9469 | 9568 | 2026-09-10 09:16:50+03 | 2026-09-10 10:02:03+03 |

Hourly by `received_at`:

| received_hour | connection_refused_errors | min_id | max_id |
| --- | ---: | ---: | ---: |
| 2026-09-07 09:00+03 | 61 | 3458 | 3549 |
| 2026-09-09 14:00+03 | 1 | 8800 | 8800 |
| 2026-09-09 15:00+03 | 1 | 8805 | 8805 |
| 2026-09-10 09:00+03 | 106 | 8863 | 9547 |
| 2026-09-10 10:00+03 | 2 | 9566 | 9568 |

Retry state: 178 connection-refused rows have `extraction_retry_count = 1`; 2 have `extraction_retry_count = 2`; none have reached the configured extraction cap of 5.

The failure is triggered by the extraction stack calling the Ollama chat endpoint. `app/api/factories/action_factory.py:110-119` constructs `OllamaExtractionService` with `OllamaChatClient(base_url=settings.ollama_base_url, model=settings.extraction_ollama_model, timeout_seconds=settings.extraction_llm_timeout_seconds, max_request_retries=settings.extraction_llm_request_retries, retry_backoff_seconds=settings.extraction_llm_retry_backoff_seconds)`. Defaults in `app/core/config.py` are `ollama_base_url = "http://192.168.40.25:11435/ollama"`, `extraction_ollama_model = "qwen2.5:7b"`, timeout `240`, request retries `2`, and backoff `2.0` seconds. `app/core/ollama_client.py:72` sends to `"api/chat"`, so the effective request path is `http://192.168.40.25:11435/ollama/api/chat`; `app/core/ollama_client.py:104-116` retries `httpx.TimeoutException`, `httpx.NetworkError`, and retryable 502/503/504 responses.

The error gets stored by the tier1 extraction failure handlers. `app/llm/actions/extract_incidents_action.py:56-81` catches extraction exceptions and calls `RawMessageRepository.record_transient_extraction_failure` for transient LLM failures. The concurrent worker path does the same at `app/news/services/pipeline/pipeline_llm_workers.py:74-115`. `app/llm/services/transient_llm_errors.py:20-36` classifies messages containing `"connection refused"` as transient. `app/news/repositories/raw_message_repository.py:158-193` then sets `status = MessageStatus.error`, increments `extraction_retry_count`, clears the processing claim, and stores `ConnectError: [Errno 111] Connection refused` until the retry cap is reached.

Errored rows do have an automatic retry path in principle, but this specific error string is not currently picked up by that reset query. `RawMessageRepository.reset_retryable_extraction_errors` at `app/news/repositories/raw_message_repository.py:200-251` requeues `status = error` rows only when `error_message` matches `ReadTimeout`, `ConnectTimeout`, `TimeoutException`, or `timed out`. It does not match `ConnectError` or `connection refused`. The sweep entrypoints call that reset before tier1 extraction at `app/news/services/pipeline/pipeline_concurrent_sweeps.py:341-356` and `app/news/services/pipeline/pipeline_sweep_stages.py:235-260`, but the current connection-refused rows are effectively stuck unless some other manual/admin path resets them.

Recent bounded container logs support the same conclusion. `docker compose logs --tail 1500 pipeline-worker live-sweep-worker | Select-String -Pattern "ConnectError|Connection refused|Concurrent tier1 extraction|Pipeline stage=tier1_extraction|pre_extraction_dedup"` showed repeated `httpx.ConnectError: [Errno 111] Connection refused` and `httpcore.ConnectError: [Errno 111] Connection refused` from both `pipeline-worker-1` and `live-sweep-worker-1`. The visible stack trace runs through `app/core/ollama_client.py:72` and `:106`, `app/llm/services/ollama_presence_gate_service.py:179`, `app/llm/services/ollama_extraction_service.py:411`, and `app/news/services/pipeline/pipeline_llm_workers.py:60`. The same log slice shows tier1 passes such as `processed=4 succeeded=0 failed=4 capped=0`, while pre-extraction dedup continued to process 100 rows at a time.

## Orphan Materialized-row Summary

The original active-incident join was correct for Incidents page visibility. The relationship is direct: `app/news/models/incident.py` defines `Incident.raw_message_id` as a foreign key to `raw_messages.id`, and `app/news/models/raw_message.py` has no alternate materialized incident id. `app/news/repositories/incident_repository.py:127-200` lists incidents from `Incident` joined to `RawMessage` on `RawMessage.id == Incident.raw_message_id`; `app/news/repositories/pipeline_claim_repository.py:127-155` checks active incident existence with the same `Incident.raw_message_id == RawMessage.id` and `Incident.is_deleted IS false` condition.

The 214 duplicate rows whose target raw message is `status = 'materialized'` but has no active incident break down as:

| bucket | duplicate_rows | distinct_originals |
| --- | ---: | ---: |
| target has only soft-deleted incident rows | 189 | 61 |
| target has zero incident rows anywhere | 25 | 12 |

No wrong-join artifact was found. The sample requested was expanded to the first 50 rows by `original_id`; every sampled row had only deleted incident rows, with `active_incident_count = 0`. The full-count query then found the smaller zero-incident anomaly. Examples from that zero-incident materialized-original group include:

| duplicate_id | original_id | original_source | original_time | original_materialized_at | original_has_extraction | original_has_match | preview |
| ---: | ---: | --- | --- | --- | --- | --- | --- |
| 3139 | 3137 | sameralhajali | 2026-09-02 16:20:09+03 | 2026-09-03 11:23:54+03 | true | true | قصف مدفعي يستهدف بلدة المنصوري |
| 3145 | 3137 | sameralhajali | 2026-09-02 16:20:09+03 | 2026-09-03 11:23:54+03 | true | true | قصف مدفعي يستهدف بلدة المنصوري |
| 3150 | 3137 | sameralhajali | 2026-09-02 16:20:09+03 | 2026-09-03 11:23:54+03 | true | true | قصف مدفعي يستهدف بلدة المنصوري |
| 3603 | 3575 | bintjbeilnews | 2026-09-04 22:01:49+03 | 2026-09-07 15:09:09+03 | true | true | غارة على النبطية الفوقا |
| 3597 | 3593 | manarbreaking | 2026-09-04 22:17:22+03 | 2026-09-07 15:05:39+03 | true | true | غارة اسرائيلية معادية استهدفت خراج بلدة عين التينة |

These 25 rows are genuinely anomalous under the current schema: the target raw messages say `materialized`, have extraction and match results, and have `materialized_at`, but there is no `incidents` row with that `raw_message_id`, deleted or active.

## Updated Blast Radius

The live snapshot changed while recon was running. The prior pass saw 906 duplicate rows and 461 duplicates with no active incident on self or target. This pass sees 934 duplicate rows total and 489 duplicates with no active incident on either the duplicate raw id or its `duplicate_of_id` target. If soft-deleted incidents count as expected non-visible historical rows, the stricter "zero incident anywhere on self or target" count is 274 duplicate rows.

Corrected full duplicate buckets:

| corrected_bucket | original_status | duplicate_rows | distinct_originals |
| --- | --- | ---: | ---: |
| target_has_active | materialized | 438 | 190 |
| target_has_active | error | 7 | 5 |
| target_soft_deleted_only | materialized | 189 | 61 |
| target_soft_deleted_only | duplicate | 16 | 11 |
| target_soft_deleted_only | error | 10 | 2 |
| zero_incident_on_self_or_target | parsed | 135 | 73 |
| zero_incident_on_self_or_target | error | 105 | 63 |
| zero_incident_on_self_or_target | materialized | 25 | 12 |
| zero_incident_on_self_or_target | duplicate | 7 | 5 |
| zero_incident_on_self_or_target | routed_air_violation | 2 | 2 |

The biggest live risk remains pre-extraction duplicates that point to targets without active canonical incidents, especially `parsed` and `error` targets. Connection-refused errors are actively feeding that risk because they strand candidate originals in `status = error`, and the current retry reset does not requeue that exact error pattern.

## Open Questions

- Are soft-deleted target incidents expected to remain valid duplicate targets for Rejected News, or should duplicate rows linked to soft-deleted canonicals be surfaced differently?
- What process produced `status = materialized` raw rows with `materialized_at` but zero incident rows anywhere for the same `raw_message_id`?
- Should `ConnectError` / `connection refused` be part of the automatic retry reset criteria, or was it intentionally excluded because it can indicate a long-lived infrastructure outage?
- The logs show both `pipeline-worker` and `live-sweep-worker` running pre-dedup/tier1 work. Is that concurrent overlap intentional for this environment?
