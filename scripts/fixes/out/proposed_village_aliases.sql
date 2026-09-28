-- Proposed village alias fixes from the lost-incident recon (2026-09-28).
-- REVIEW ONLY. Nothing here has been executed. Run approved sections manually,
-- after `alembic upgrade head`, inside a transaction:
--   psql -d war_news_dev -v ON_ERROR_STOP=1 -f scripts/fixes/out/proposed_village_aliases.sql
-- Afterwards re-run matching for the affected messages with
--   python -m scripts.fixes.requeue_errored_messages --since 2026-08-17   (dry-run first)
--
-- alias_normalized values below equal app.core.text_normalization.normalize_arabic_text(alias_text).
-- Villages are resolved by ACS code, never by internal id.

BEGIN;

-- ============================================================================
-- Section A: repair 13 dead alias keys (confidence: high, mechanical)
-- Migration 20260923_0061 stored alias_normalized = alias_text, so ta marbuta /
-- hamza forms never matched the normalized mention. The code fix in
-- village_repository._alias_key_matches already works around this at read time;
-- this section makes the stored key consistent (and the unique index meaningful).
-- Each UPDATE is guarded by alias_text so it is a no-op if the row changed.
-- ============================================================================
UPDATE village_location_aliases SET alias_normalized = 'لبونه'           WHERE alias_text = 'لبونة'           AND alias_normalized = 'لبونة';
UPDATE village_location_aliases SET alias_normalized = 'الناقوره'        WHERE alias_text = 'الناقورة'        AND alias_normalized = 'الناقورة';
UPDATE village_location_aliases SET alias_normalized = 'المالكيه'        WHERE alias_text = 'المالكية'        AND alias_normalized = 'المالكية';
UPDATE village_location_aliases SET alias_normalized = 'خله الدواوير'    WHERE alias_text = 'خلة الدواوير'    AND alias_normalized = 'خلة الدواوير';
UPDATE village_location_aliases SET alias_normalized = 'المعليه'         WHERE alias_text = 'المعلية'         AND alias_normalized = 'المعلية';
UPDATE village_location_aliases SET alias_normalized = 'السماعيه'        WHERE alias_text = 'السماعية'        AND alias_normalized = 'السماعية';
UPDATE village_location_aliases SET alias_normalized = 'خله الساقيه'     WHERE alias_text = 'خلة الساقية'     AND alias_normalized = 'خلة الساقية';
UPDATE village_location_aliases SET alias_normalized = 'وادي اسطبل'      WHERE alias_text = 'وادي إسطبل'      AND alias_normalized = 'وادي إسطبل';
UPDATE village_location_aliases SET alias_normalized = 'البياضه'         WHERE alias_text = 'البياضة'         AND alias_normalized = 'البياضة';
-- الدبشة -> Kfar Roummane; blocks 29 errored messages (28838, 28898, 29109, 29209, ...)
UPDATE village_location_aliases SET alias_normalized = 'الدبشه'          WHERE alias_text = 'الدبشة'          AND alias_normalized = 'الدبشة';
UPDATE village_location_aliases SET alias_normalized = 'جبل الورده'      WHERE alias_text = 'جبل الوردة'      AND alias_normalized = 'جبل الوردة';
UPDATE village_location_aliases SET alias_normalized = 'محرونه'          WHERE alias_text = 'محرونة'          AND alias_normalized = 'محرونة';
UPDATE village_location_aliases SET alias_normalized = 'محميه وادي الحجير' WHERE alias_text = 'محمية وادي الحجير' AND alias_normalized = 'محمية وادي الحجير';

-- ============================================================================
-- Section B: new unambiguous aliases (9 rows)
-- Only rows where the message text itself names the place unambiguously and the
-- gazetteer has exactly one plausible parent.
-- ============================================================================
INSERT INTO village_location_aliases (alias_text, alias_normalized, village_id, note, requires_geo_context, is_active)
SELECT a.alias_text, a.alias_normalized, v.id, a.note, false, true
FROM (VALUES
    -- alias «الطيري» -> Tiri (Bint Jubail, acs 72254). msgs 29236, 32582, 32695:
    -- «تفجيرًا ضخمًا في بلدة الطيري بقضاء بنت جبيل». confidence: high
    ('الطيري', 'الطيري', 72254, 'recon 2026-09-28 lost incidents: definite-article form of Tiri; msgs 29236,32582,32695'),
    -- alias «الغندورية» -> Ghandouriyet Bent Jbayl (acs 72274). msgs 29077, 29101:
    -- «قصف مدفعي يستهدف وادي الحجير لجهة بلدة الغندورية». confidence: high
    ('الغندورية', 'الغندوريه', 72274, 'recon 2026-09-28 lost incidents: definite-article form; msgs 29077,29101'),
    -- alias «الرشاف» -> Rachaf (Bint Jubail, acs 72271). msg 30813. confidence: high
    ('الرشاف', 'الرشاف', 72271, 'recon 2026-09-28 lost incidents: definite-article form; msg 30813'),
    -- alias «اللبوة» -> Laboue (Baalbek, acs 53234). msg 31613 (drone overflight list). confidence: high
    ('اللبوة', 'اللبوه', 53234, 'recon 2026-09-28 lost incidents: definite-article form; msg 31613'),
    -- alias «ماركابا» -> Markaba (Marjaayoun, acs 73245). msg 30878, English line in the same
    -- message says "the town of Markaba". confidence: high
    ('ماركابا', 'ماركابا', 73245, 'recon 2026-09-28 lost incidents: misspelling, same message says Markaba; msg 30878'),
    -- LLM English transliterations of تبنين (Tibnine, acs 72211). Arabic text of 28760/31175:
    -- «تستهدف اطراف بلدة تبنين». confidence: high (also report as a Tier 1 prompt gap)
    ('Tbaineen', 'Tbaineen', 72211, 'recon 2026-09-28: LLM transliteration of تبنين; msgs 28760,29048,29837,31175'),
    ('Tabbin', 'Tabbin', 72211, 'recon 2026-09-28: LLM transliteration of تبنين; msgs 28610,29040'),
    -- LLM transliteration of بيت ياحون (Beit Yahoun, acs 72237). msgs 30812, 30813. confidence: medium-high
    ('Bite Yahanun', 'Bite Yahanun', 72237, 'recon 2026-09-28: LLM transliteration of بيت ياحون; msgs 30812,30813'),
    -- LLM transliteration of ميس الجبل (Meiss Ej-Jabal, acs 73250). msg 30742. confidence: high
    ('Mais al Jabal', 'Mais al Jabal', 73250, 'recon 2026-09-28: LLM transliteration of ميس الجبل; msg 30742')
) AS a(alias_text, alias_normalized, acs_code, note)
JOIN villages v ON v.acs_code = a.acs_code AND v.is_active
ON CONFLICT (alias_normalized) DO NOTHING;

-- Sanity check before COMMIT: expect 13 repaired keys and up to 9 new rows.
SELECT alias_text, alias_normalized, village_id FROM village_location_aliases
WHERE note LIKE 'recon 2026-09-28%' OR alias_text IN ('الدبشة', 'الناقورة', 'المالكية')
ORDER BY alias_text;

COMMIT;  -- change to ROLLBACK for a dry run

-- ============================================================================
-- Section C: AMBIGUOUS - do NOT insert without a human decision
-- raw text | msgs | candidates / why ambiguous
-- ============================================================================
-- «الرويس»      | 30113, 30771, 30779, 32005 | 30113 says «حي الرويس في النبطية» -> Nabatieh Et-Tahta (acs 71111),
--                 but «الرويس» is also a Dahiyeh (Beirut southern suburbs) neighbourhood. Needs geo-conditional alias.
-- «دوحة»        | 29127, 29863, 30810, 30941 | bare «دوحة»: Doha Kfar Roummane (acs 71133) vs Doha Aramoun (Aley).
-- «شقا»         | 30489, 30505, 30913, 31629 | LLM truncation of «شقرا» (Chaqra, acs 72229) but «شكا» (Chekka, Batroun) is close;
--                 fix belongs in extraction, not an alias.
-- «الجبور»      | 31355, 31752, 32183 | «محيط الجبور – البقاع الغربي»: a site in West Bekaa, no gazetteer village.
-- «سدانا» / «سدانا عند أطراف الهبارية» | 28385, 28444, 28475, 31414, 29812 | Jabal Sadana: Habbariyeh (acs 74122) vs Kfarchouba (not in gazetteer by that spelling).
-- «حدادا», «حدانا» | 31356, 29746 | probably «حداثا» (Haddatha) misspellings; extraction issue.
-- «بركة النقار» | 33946 | «عند أطراف شبعا»: Chebaa (acs 74130) vs Chebaa Farms (acs 74183).
-- «قلعة دوبيه» / «doubiyeh» | 31785, 30742 | Doubiyeh castle lies between Chaqra and Meiss Ej-Jabal.
-- «فلاوي»       | 28607, 29819 | Flaoui (Baalbek) is missing from the gazetteer; gazetteer addition needs an ACS code.
-- «رسم الحدث», «نبي رشاد», «حرفوش», «شبق», «حمامص» | 31613, 32183, 29668 | Baalbek-Hermel localities not in the
--                 gazetteer (31613 is a drone-overflight list, i.e. air violation).
-- «المفيلحة», «العراقيب», «المعشوق», «الرفيع», «ام التوت» | 28418, 32660, 31692, 31815 | unknown / no candidate.
-- «جبل عامل», «الجنوب», «سهل البقاع», «سلسلة غربية» | regions, not villages - never alias.
-- «الصمدانية»   | 29562, 29942, 29962, 30000 | Syrian Quneitra countryside - correctly unmatched (not Lebanon).
-- «البحصة»      | 285, 342 | Tripoli neighbourhood (house fire, not conflict) - correctly unmatched.
-- «المطلة»      | 32183 | Metula (Israel) - correctly unmatched.
--
-- Conditions: no condition-table rows are proposed. The recurring unmapped texts
-- («غارة» 48, «غارة إسرائيلية» 34, «استهداف» 27, «غارتان» 23, «دبابة ميركافا معادية تستهدف» 12, ...)
-- were stored before extraction-time finalization (condition_evidence_override:
-- «غارة» -> Bombs, «دبابة/ميركافا» -> Tank Fire) and the Unclassified fallback
-- (commit 94ed1b2) existed. requeue_errored_messages.py re-runs that finalization
-- through the existing finalize_extraction_action before re-matching.
