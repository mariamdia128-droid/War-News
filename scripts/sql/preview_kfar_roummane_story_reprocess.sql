-- Preview only. Do not execute as a data correction.
-- After deploying story-continuation, sub-event splitting, and gendered
-- occupation backstops, reprocess Kfar Roummane messages from 2026-09-07
-- through the pipeline (reset extraction/match/materialization for the
-- selected raw_messages). Review this result set before any write.

SELECT
    i.id,
    i.raw_message_id,
    i.event_date,
    i.event_time,
    i.condition_id,
    c.action_en AS condition_en,
    i.total_deaths,
    i.total_injuries,
    i.deaths,
    i.injuries,
    i.story_group_id,
    i.duplicate_level,
    i.duplicate_similarity_score,
    i.verification_status,
    left(i.khabar, 180) AS khabar_preview
FROM incidents AS i
JOIN villages AS v ON v.id = i.village_id
LEFT JOIN conditions AS c ON c.id = i.condition_id
WHERE i.is_deleted IS FALSE
  AND i.event_date = DATE '2026-09-07'
  AND (
        v.ref_name_en ILIKE '%kfar roummane%'
     OR v.ref_name_ar LIKE '%كفر رمان%'
     OR v.cad_name ILIKE '%kfar%'
     OR v.cad_name LIKE '%كفر رمان%'
     OR v.cad_name LIKE '%كفررمان%'
  )
ORDER BY i.event_time NULLS LAST, i.created_at;
