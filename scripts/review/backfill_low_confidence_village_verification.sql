-- Manual review required. Do not execute automatically.
-- Backfill: flag active incidents whose own village came from a
-- matched_low_confidence village match so they leave the default Incidents
-- list and appear under Needs Verification (same reason string as current
-- materialization).
--
-- Driven only by match_result.village_matches[].village_match_status for the
-- incident's village_id — no village-name hardcoding.
-- Leaves verified / rejected human outcomes untouched.
-- Does not overwrite casualty-scope review reasons already stored on the row.

BEGIN;

-- Preview (run separately if desired):
-- SELECT
--   i.id,
--   i.village_id,
--   i.verification_status AS current_status,
--   i.verification_reason AS current_reason,
--   v->>'extracted_name' AS extracted_name,
--   v->>'village_confidence' AS village_confidence
-- FROM incidents i
-- JOIN raw_messages r ON r.id = i.raw_message_id
-- CROSS JOIN LATERAL jsonb_array_elements(
--   COALESCE(r.match_result->'village_matches', '[]'::jsonb)
-- ) AS v
-- WHERE i.is_deleted = false
--   AND i.verification_status NOT IN ('verified', 'rejected')
--   AND (v->>'matched_village_id') ~ '^[0-9]+$'
--   AND (v->>'matched_village_id')::int = i.village_id
--   AND v->>'village_match_status' = 'matched_low_confidence'
--   AND COALESCE(i.verification_reason, '')
--       IS DISTINCT FROM 'Low-confidence village match requires manual review.'
--   AND COALESCE(i.verification_reason, '') NOT LIKE 'Category casualties%'
--   AND COALESCE(i.verification_reason, '') NOT LIKE 'Unsupported casualty_scope%';

UPDATE incidents AS i
SET
  verification_status = 'needs_verification',
  verification_reason = 'Low-confidence village match requires manual review.'
FROM raw_messages AS r
WHERE r.id = i.raw_message_id
  AND i.is_deleted = false
  AND i.verification_status NOT IN ('verified', 'rejected')
  AND COALESCE(i.verification_reason, '')
      IS DISTINCT FROM 'Low-confidence village match requires manual review.'
  AND COALESCE(i.verification_reason, '') NOT LIKE 'Category casualties%'
  AND COALESCE(i.verification_reason, '') NOT LIKE 'Unsupported casualty_scope%'
  AND EXISTS (
    SELECT 1
    FROM jsonb_array_elements(
      COALESCE(r.match_result->'village_matches', '[]'::jsonb)
    ) AS v
    WHERE (v->>'matched_village_id') ~ '^[0-9]+$'
      AND (v->>'matched_village_id')::int = i.village_id
      AND v->>'village_match_status' = 'matched_low_confidence'
  );

-- Review affected count before COMMIT / ROLLBACK:
-- SELECT COUNT(*) FROM incidents
-- WHERE verification_reason = 'Low-confidence village match requires manual review.'
--   AND is_deleted = false;

COMMIT;
