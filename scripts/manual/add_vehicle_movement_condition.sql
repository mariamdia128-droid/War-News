-- Manual reference-data change for review/execution.
-- Adds Vehicle Movement without shifting existing condition ids; id 45 remains
-- reserved for Unclassified air violation in application code.

INSERT INTO conditions (id, action_en, action_ar, note, is_active)
VALUES (
    46,
    'Vehicle Movement',
    'تحرك آليات',
    'Movement or maneuvering of enemy vehicles/equipment without direct fire.',
    TRUE
)
ON CONFLICT (id) DO NOTHING;

