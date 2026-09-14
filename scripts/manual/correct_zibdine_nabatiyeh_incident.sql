-- Manual review required. Do not execute automatically.
-- Corrects raw messages 8788/8791 and their materialized incident from
-- Zibdine Jbayl (ACS 26246) to Zibdine En-Nabatiyeh (ACS 71122).

BEGIN;

DO $$
DECLARE
    target_village_id integer;
    original_village_id integer;
    anchor_village_id integer;
    affected_incident_id uuid := 'adaf82c3-ee63-45c8-af89-44049dc609f5';
    previous_exact_hash char(64);
BEGIN
    SELECT id INTO STRICT target_village_id
    FROM villages
    WHERE acs_code = 71122;

    SELECT id INTO STRICT original_village_id
    FROM villages
    WHERE acs_code = 26246;

    SELECT id INTO STRICT anchor_village_id
    FROM villages
    WHERE acs_code = 71331;

    SELECT exact_hash INTO previous_exact_hash
    FROM incidents
    WHERE id = affected_incident_id
      AND village_id = original_village_id
      AND is_deleted = false
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION
            'Expected active incident % matched to ACS 26246 was not found',
            affected_incident_id;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM incident_updates AS updates
        JOIN users
          ON users.id = updates.performed_by
        JOIN roles
          ON roles.id = users.role_id
        WHERE updates.incident_id = affected_incident_id
          AND roles.name::text IN ('admin', 'super_admin')
          AND (
            updates.old_values ? 'village_id'
            OR updates.new_values ? 'village_id'
            OR updates.old_values ? 'village'
            OR updates.new_values ? 'village'
          )
          AND COALESCE(
                updates.old_values->>'village_id',
                updates.old_values->>'village'
              )
              IS DISTINCT FROM
              COALESCE(
                updates.new_values->>'village_id',
                updates.new_values->>'village'
              )
    ) THEN
        RAISE EXCEPTION
            'Incident % has a recorded human village correction',
            affected_incident_id;
    END IF;

    UPDATE incidents
    SET
        village_id = target_village_id,
        -- District/governorate displayed by the API are joined from villages;
        -- there are no persisted Caza/Mohafaza copies to update.
        exact_hash = encode(
            digest(
                concat(
                    regexp_replace(btrim(khabar), '\s+', ' ', 'g'),
                    '|',
                    target_village_id,
                    '|',
                    condition_id,
                    '|',
                    event_date::text
                ),
                'sha256'
            ),
            'hex'
        ),
        version = version + 1,
        updated_at = now()
    WHERE id = affected_incident_id;

    INSERT INTO incident_updates (
        incident_id,
        action,
        old_values,
        new_values,
        performed_by
    )
    VALUES (
        affected_incident_id,
        'edit',
        jsonb_build_object(
            'village_id', original_village_id,
            'exact_hash', previous_exact_hash
        ),
        jsonb_build_object(
            'village_id', target_village_id,
            'correction_reason', 'Harouf/Zibdine Nabatiyeh geo-context'
        ),
        NULL
    );

    UPDATE raw_messages AS raw
    SET match_result = jsonb_set(
        raw.match_result,
        '{village_matches}',
        (
            SELECT jsonb_agg(
                CASE
                    WHEN (entry->>'matched_village_id')::integer
                         = original_village_id
                    THEN jsonb_set(
                        jsonb_set(
                            jsonb_set(
                                jsonb_set(
                                    jsonb_set(
                                        jsonb_set(
                                            jsonb_set(
                                                entry,
                                                '{matched_village_id}',
                                                to_jsonb(target_village_id),
                                                true
                                            ),
                                            '{village_match_status}',
                                            '"matched"'::jsonb,
                                            true
                                        ),
                                        '{village_review_required}',
                                        'false'::jsonb,
                                        true
                                    ),
                                    '{resolved_by_geo_context}',
                                    'true'::jsonb,
                                    true
                                ),
                                '{geo_context_anchor_village_id}',
                                to_jsonb(anchor_village_id),
                                true
                            ),
                            '{original_top_candidate_id}',
                            to_jsonb(original_village_id),
                            true
                        ),
                        '{alternate_candidate_village_id}',
                        to_jsonb(original_village_id),
                        true
                    )
                    ELSE entry
                END
                ORDER BY ordinal
            )
            FROM jsonb_array_elements(
                raw.match_result->'village_matches'
            ) WITH ORDINALITY AS matches(entry, ordinal)
        ),
        false
    ) || jsonb_build_object('any_village_low_confidence', false)
    WHERE raw.id IN (8788, 8791)
      AND jsonb_typeof(raw.match_result->'village_matches') = 'array'
      AND EXISTS (
          SELECT 1
          FROM jsonb_array_elements(
              raw.match_result->'village_matches'
          ) AS matches(entry)
          WHERE (entry->>'matched_village_id')::integer
                = original_village_id
      );

    IF (
        SELECT count(*)
        FROM raw_messages
        WHERE id IN (8788, 8791)
          AND EXISTS (
              SELECT 1
              FROM jsonb_array_elements(
                  match_result->'village_matches'
              ) AS matches(entry)
              WHERE (entry->>'matched_village_id')::integer
                    = target_village_id
          )
    ) <> 2 THEN
        RAISE EXCEPTION
            'Both raw messages were not corrected; transaction will roll back';
    END IF;
END
$$;

-- Review these rows before replacing COMMIT with an approved execution.
SELECT
    i.id,
    i.raw_message_id,
    i.village_id,
    v.acs_code,
    v.ref_name_en,
    v.caza_en,
    v.mohafaza_en,
    i.exact_hash
FROM incidents AS i
JOIN villages AS v ON v.id = i.village_id
WHERE i.id = 'adaf82c3-ee63-45c8-af89-44049dc609f5';

SELECT id, match_result
FROM raw_messages
WHERE id IN (8788, 8791)
ORDER BY id;

ROLLBACK;
-- After Najdi reviews the SELECT output, change the final ROLLBACK to COMMIT
-- in a separately approved execution.
