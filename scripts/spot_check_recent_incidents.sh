#!/usr/bin/env bash
# Pulls every incident materialized in the last N hours (default 72),
# alongside the raw source text that produced it, so you can manually
# spot-check for false positives (like Burning Properties / محيط) before
# they pile up.
#
# Run this after any pipeline/prompt change, or just periodically as a
# gut-check on accuracy.
#
# Usage: scripts/spot_check_recent_incidents.sh [hours]

set -euo pipefail

HOURS="${1:-72}"

docker compose exec -T db psql -U postgres -d war_news_dev -c "
SELECT
    i.id,
    v.ref_name_ar AS village,
    c.action_en AS condition,
    i.event_date,
    i.verification_status,
    LEFT(rm.raw_text, 200) AS source_excerpt,
    rm.source_platform,
    rm.match_result->>'condition_confidence' AS match_confidence,
    rm.match_result->>'location_ambiguity' AS location_ambiguity
FROM incidents i
JOIN villages v ON i.village_id = v.id
JOIN conditions c ON i.condition_id = c.id
JOIN raw_messages rm ON i.raw_message_id = rm.id
WHERE i.created_at > now() - interval '${HOURS} hours'
  AND i.is_deleted = false
ORDER BY i.created_at DESC;
"
