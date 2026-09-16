-- Manual reference-data change for review/execution.
-- Adds Vehicle Movement while allowing PostgreSQL to allocate the next id.

INSERT INTO conditions (action_en, action_ar, note, is_active)
VALUES (
    'Vehicle Movement',
    'تحرك آليات',
    'Movement or maneuvering of enemy vehicles/equipment without direct fire.',
    TRUE
)
ON CONFLICT (action_ar) DO NOTHING;

