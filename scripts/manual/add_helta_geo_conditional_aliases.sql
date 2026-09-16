-- MANUAL REVIEW REQUIRED: reference-data addition; do not run automatically.
-- Prerequisite: apply migration 70c5f2978984 first.
--
-- These aliases do not override the Batroun Helta row. They only add Kfar
-- Chouba (ACS 74160) as a candidate when same-message geo anchors support it.

BEGIN;

INSERT INTO village_location_aliases (
    alias_text,
    alias_normalized,
    village_id,
    note,
    requires_geo_context
)
SELECT
    alias.alias_text,
    alias.alias_normalized,
    villages.id,
    'Southern Mazraat Helta shares Kfar Chouba ACS 74160; geo context required.',
    TRUE
FROM villages
CROSS JOIN (
    VALUES
        ('حلتا', 'حلتا'),
        ('مزرعة حلتا', 'مزرعة حلتا')
) AS alias(alias_text, alias_normalized)
WHERE villages.acs_code = 74160
ON CONFLICT (alias_normalized) DO NOTHING;

DO $$
BEGIN
    IF (
        SELECT count(*)
        FROM village_location_aliases AS aliases
        JOIN villages ON villages.id = aliases.village_id
        WHERE aliases.alias_normalized IN ('حلتا', 'مزرعة حلتا')
          AND aliases.requires_geo_context IS TRUE
          AND villages.acs_code = 74160
    ) <> 2 THEN
        RAISE EXCEPTION
            'Helta aliases conflict with existing rows; expected two conditional aliases to ACS 74160';
    END IF;
END
$$;

COMMIT;

SELECT
    aliases.alias_text,
    aliases.alias_normalized,
    aliases.requires_geo_context,
    villages.id AS village_id,
    villages.acs_code,
    villages.ref_name_ar
FROM village_location_aliases AS aliases
JOIN villages ON villages.id = aliases.village_id
WHERE aliases.alias_normalized IN ('حلتا', 'مزرعة حلتا')
ORDER BY aliases.alias_normalized;
