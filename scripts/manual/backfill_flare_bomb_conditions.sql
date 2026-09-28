-- Manual review SQL for flare-bomb condition cleanup.
-- Expected preview from 2026-09-28 recon: 2 clean Bombs rows should relabel to
-- Flare Bomb; 7 mixed daily-summary rows should only be flagged for review.
-- Review the SELECTs before running either UPDATE.

WITH candidates AS (
    SELECT
        i.id,
        i.condition_id,
        c.action_en AS old_condition,
        COALESCE(rm.raw_text, i.khabar, '') AS source_text,
        (
            COALESCE(rm.raw_text, '') ~* '(غارة|غارات|قصف|استهداف|استهدف|استهدفت|انفجار|شهيد|جريح|دمار|حريق)'
            OR COALESCE(i.khabar, '') ~* '(غارة|غارات|قصف|استهداف|استهدف|استهدفت|انفجار|شهيد|جريح|دمار|حريق)'
        ) AS has_strike_language
    FROM incidents i
    JOIN conditions c ON c.id = i.condition_id
    LEFT JOIN raw_messages rm ON rm.id = i.raw_message_id
    WHERE c.action_en = 'Bombs'
      AND (
        COALESCE(rm.raw_text, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
        OR COALESCE(i.khabar, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
      )
)
SELECT
    id,
    old_condition,
    CASE WHEN has_strike_language THEN old_condition ELSE 'Flare Bomb' END AS new_condition,
    CASE WHEN has_strike_language THEN 'flag' ELSE 'relabel' END AS operation,
    left(regexp_replace(source_text, '\s+', ' ', 'g'), 220) AS snippet
FROM candidates
ORDER BY operation DESC, id;

-- Relabel clean flare-only rows.
UPDATE incidents
SET condition_id = (SELECT id FROM conditions WHERE action_en = 'Flare Bomb'),
    note = concat_ws('; ', NULLIF(note, ''), 'relabeled_by_flare_guard'),
    updated_at = now()
WHERE id IN (
    SELECT i.id
    FROM incidents i
    JOIN conditions c ON c.id = i.condition_id
    LEFT JOIN raw_messages rm ON rm.id = i.raw_message_id
    WHERE c.action_en = 'Bombs'
      AND (
        COALESCE(rm.raw_text, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
        OR COALESCE(i.khabar, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
      )
      AND NOT (
        COALESCE(rm.raw_text, '') ~* '(غارة|غارات|قصف|استهداف|استهدف|استهدفت|انفجار|شهيد|جريح|دمار|حريق)'
        OR COALESCE(i.khabar, '') ~* '(غارة|غارات|قصف|استهداف|استهدف|استهدفت|انفجار|شهيد|جريح|دمار|حريق)'
      )
);

-- Flag mixed strike + flare rows for manual verification; do not relabel them.
UPDATE incidents
SET verification_status = 'needs_verification',
    verification_reason = concat_ws(
        '; ',
        NULLIF(verification_reason, ''),
        'Flare wording appears together with strike language; verify whether this message contains both a strike and flare bombs.'
    ),
    updated_at = now()
WHERE id IN (
    SELECT i.id
    FROM incidents i
    JOIN conditions c ON c.id = i.condition_id
    LEFT JOIN raw_messages rm ON rm.id = i.raw_message_id
    WHERE c.action_en = 'Bombs'
      AND (
        COALESCE(rm.raw_text, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
        OR COALESCE(i.khabar, '') ~* '(مضيئة|مضيئه|إنارة|انارة|ضوئية|flare|illumination)'
      )
      AND (
        COALESCE(rm.raw_text, '') ~* '(غارة|غارات|قصف|استهداف|استهدف|استهدفت|انفجار|شهيد|جريح|دمار|حريق)'
        OR COALESCE(i.khabar, '') ~* '(غارة|غارات|قصف|استهداف|استهدف|استهدفت|انفجار|شهيد|جريح|دمار|حريق)'
      )
);
