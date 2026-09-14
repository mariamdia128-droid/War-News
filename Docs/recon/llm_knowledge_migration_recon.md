# LLM Knowledge Migration — Phase 1 Recon Report

**Date:** 2026-09-14  
**Scope:** Backend domain knowledge scattered outside a central `llm_knowledge/` location  
**Target architecture path (spec):** `backend/src/core/llm_knowledge/`  
**Actual repo layout:** `app/core/` (no `backend/src/` prefix) — implement under `app/core/llm_knowledge/`

---

## Test suite baseline (pre-Phase 1)

Command: `python -m pytest tests/ -q --tb=no`

| Result | Count |
|--------|------:|
| Passed | 655 |
| Failed | 15 |
| Skipped | 11 |
| Errors | 3 |

**Baseline is broken before any migration work.** Failures appear environment-related (DB/SQLAlchemy connectivity for webhook, pipeline, seed tests) rather than from uncommitted changes in this branch. Proceed with caution; migration commits must not increase failure count without explanation.

Representative failures:
- `tests/news/test_cnrs_webhook.py` (7 tests)
- `tests/test_pipeline_jobs.py` (2 tests)
- `tests/test_seed_villages.py`, `tests/test_village_location_aliases.py` (3 errors)
- `tests/test_air_violation_concurrency.py`, `tests/test_extraction_transient_retry.py`, others (singleton failures)

---

## Summary counts

| Category | Fragment count |
|----------|---------------:|
| `terminology` | 47 |
| `rules` | 12 |
| `fewshot` | 18 |
| `needs clarification` | 8 |
| **Total catalogued** | **85** |

Prompt-building functions: **8** (see dedicated section).

---

## 1. Arabic term mappings (terminology)

### 1.1 Casualty gender / status — explicit forms

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/news/services/incident_details/casualty_gender_evidence.py` | 24–52 | `_EXPLICIT_FORMS`: `شهيد`→male_deaths, `شهيدة`→female_deaths, `جريح`/`مصاب`→injuries | terminology |
| `app/news/services/incident_details/casualty_gender_evidence.py` | 47–52 | `_COUNTED_PLURALS`: `شهداء`, `شهيدات`, `جرحى`, `جريحات`, … | terminology |
| `app/news/services/incident_details/casualty_gender_evidence.py` | 118–138 | `_MALE_ROLE_NOUNS` / `_FEMALE_ROLE_NOUNS`: `مسعف`, `جندي`, `موظف`, … | terminology |
| `app/news/services/incident_details/casualty_gender_evidence.py` | 145–152 | Regex: `(?:شهيد\|استشهاد)\s+(?:ال)?(?:مسعف\|…)` occupation→gender | terminology |
| `app/news/services/incident_details/casualty_count_backstop.py` | 25–34 | `_EXPLICIT_COUNT_WORDS`: `شهيد`, `قتيل`, `جريح`, `مصاب` (+ dual forms) for counts 1–2 | terminology |

### 1.2 Organization / emergency-response terms

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/llm/services/ollama_presence_gate_service.py` | 75–86 | `CIVIL_DEFENSE_ORG_TERMS`: `الدفاع المدني`, `الصليب الأحمر`, `مسعف`, … | terminology |
| `scripts/phase2-extraction-testing/presence_gate_instruction.txt` | 47 | Rule: `الدفاع المدني` in rescue statement = positive emergency_civil_defense | rules |
| `app/llm/services/ollama_presence_gate_service.py` | 18–30 | `MUNICIPAL_INFRASTRUCTURE_TERMS`: `بلدية`, `مبنى البلدية`, … | terminology |
| `app/llm/services/ollama_presence_gate_service.py` | 31–42 | `VILLAGE_LOCATION_MARKERS`: `بلدة`, `دوحة`, `حرش`, `وادي`, … | terminology |
| `app/llm/services/ollama_presence_gate_service.py` | 43–50 | `TARGETING_VERBS`: `استهدف`, `قصف`, `غارة`, … | terminology |
| `app/llm/services/ollama_presence_gate_service.py` | 51–74 | `VEHICLE_TERMS`: `سيارة`, `دراج`, `دبابة`, … | terminology |
| `app/llm/services/ollama_category_detail_service.py` | 26 | `_MOTORCYCLE_TEXT_MARKERS = ("دراج", "موتور")` | terminology |

### 1.3 Category / infrastructure keyword sets (Tier 2 mapper)

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/news/services/incident_details/category_mapper.py` | 103–129 | `_SCHOOL_KEYWORDS`, `_MOSQUE_KEYWORDS`, `_BRIDGE_KEYWORDS`, `_DRONE_KEYWORDS`, … | terminology |
| `app/news/services/incident_details/category_mapper.py` | 131–136 | `_EMERGENCY_VEHICLE_KEYWORDS`: ambulance vehicle phrases | terminology |

### 1.4 Revision-language markers

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/news/services/incident_details/story_revision_backstop.py` | 17–25 | `_REVISION_PATTERNS`: `حصيلة أولية`, `ارتفاع عدد`, `معلومات أولية`, … | terminology |
| `app/news/services/incident_details/story_revision_backstop.py` | 27–32 | `_NAMED_VICTIM_PATTERNS`: `تنعي`, `الشهيده <name>`, full-name martyrdom | terminology |

### 1.5 Casualty transition trigger phrases

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/news/services/incident_details/casualty_transition_backstop.py` | 15–55 | `_KEYWORD_PATTERNS`: `استشهاد احد الجرحى`, `فارق احد الجرحى الحياه`, … | terminology |

### 1.6 Condition-type / air-violation keywords (hardcoded condition IDs)

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/sources/services/red_alert_collector.py` | 29 | `UNCLASSIFIED_AIR_CONDITION_ID = 45` | needs clarification |
| `app/sources/services/red_alert_collector.py` | 47–73 | `AIR_KEYWORDS`: condition 35/36/38 → Arabic phrases (`طيران حربي`, `مسيره`, `مروحيه`, …) | terminology |
| `app/news/services/dedup/fast_path_eligibility.py` | 10, 26 | `AIR_VIOLATION_CONDITION_IDS = {35, 36, 38}` in Python + inline SQL | needs clarification |
| `app/news/services/air_violations/air_violation_workbook_service.py` | 17 | `AIR_CONDITION_IDS = {35, 36, 38}` | needs clarification |
| `app/news/services/matching/matching_service.py` | 44–47 | `CONDITION_DISTINGUISHING_TOKENS`: id 2→`تحذيريه`, id 39→`وهميه` | terminology |
| `app/news/services/matching/condition_evidence_override.py` | 6–12 | Regex→English condition names: Tank Fire, Warning Raid, Feigned Attacks, Bombs | terminology |
| `app/news/services/matching/condition_aliases.py` | 12–30 | `CONDITION_ALIASES`: Arabic phrase variants per canonical `action_ar` | terminology |

### 1.7 Story-relationship action buckets

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/news/services/dedup/story_relationship_service.py` | 23–26 | `_HOUSE_RE`, `_CAR_RE`, `_SPARSE_RE` Arabic stems | terminology |

### 1.8 Vague-quantifier / negative-evidence terms (in prompts)

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/llm/services/ollama_extraction_service.py` | 106–107 | `عشرات`, `مئات`, `عدد من`, `بضعة`, … → null counts | rules |
| `app/llm/services/ollama_presence_gate_service.py` | 406–443 | `proximity_terms`, `negative_impact_terms`, `direct_impact_terms` | terminology |

### 1.9 Red Alert / import-only aliases

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/sources/services/red_alert_collector.py` | 34–46 | `RED_ALERT_VILLAGE_ALIASES`: map labels → ACS codes | terminology |
| `app/news/services/air_violations/import_source_enrichment.py` | 136 | `aliases = {'كفره': 72257, 'شعث': 53274, 'النبطيه': 71111}` | terminology |

---

## 2. Village alias / collision-handling logic

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/news/services/matching/village_aliases.py` | 30–157 | `PROPOSED_VILLAGE_LOCATION_ALIASES`: 18 evidence-backed alias→ACS rows | terminology |
| `app/news/services/matching/village_aliases.py` | 160–169 | `UNCERTAIN_VILLAGE_LOCATION_ALIAS_NOTES`: ambiguous cases not seeded | needs clarification |
| `app/news/services/matching/matching_service.py` | 36–42 | `MATCH_THRESHOLD=0.6`, `MATCH_TIE_MARGIN=0.05` collision demotion | rules |
| `app/news/services/matching/matching_service.py` | 251–268 | `_has_collision_like_alternative`: multiple `ref_name_ar` prefix matches | rules |
| `app/news/services/matching/matching_service.py` | 280–345 | Geo-context disambiguation when fuzzy ties persist | rules |
| `app/llm/services/ollama_extraction_service.py` | 43–50 | `_DASH_ROUTE_RE`: split `طريق … X - Y` into two villages | rules |
| `app/llm/services/ollama_extraction_service.py` | 50 | `_ROUTE_AREA_PREFIXES = ("مرج ",)` | terminology |
| `app/news/repositories/village_repository.py` | 49–72 | `casualty_scope_aliases()` from DB `village_location_aliases` | rules (data-driven; not migrate body) |
| `Data/VillageLocationAliases.json` | — | Seed data mirror of alias proposals | terminology (data file) |

---

## 3. Prompt template strings & prompt-building functions

### 3.1 Prompt-building functions

| Function / constant loader | File | Pipeline stage |
|----------------------------|------|----------------|
| `RELEVANCE_CLASSIFICATION_PROMPT` | `app/llm/services/local_llm_relevance_classifier.py:26–61` | Relevance filter |
| `PRESENCE_GATE_PROMPT` ← `presence_gate_instruction.txt` | `app/llm/services/ollama_presence_gate_service.py:87–93, ~172` | Tier 1 presence gate |
| `GENERAL_EXTRACTION_PROMPT` (inline) | `app/llm/services/ollama_extraction_service.py:56–141, ~818` | Tier 1 general extraction |
| `COMBINED_TIER1_PROMPT` ← `combined_tier1_presence_extraction_instruction.txt` | `app/llm/services/ollama_extraction_service.py:318–324, ~433` | Tier 1 combined (production path) |
| `CATEGORY_DETAIL_PROMPT` ← `category_detail_instruction.txt` | `app/llm/services/ollama_category_detail_service.py:43–49, ~181` | Tier 2 per-category detail |
| `BATCHED_CATEGORY_DETAIL_PROMPT` ← `batched_category_detail_instruction.txt` | `app/llm/services/ollama_category_detail_service.py:50–56, ~212` | Tier 2 batched detail |
| Legacy `extraction_instruction.txt` | `scripts/phase2-extraction-testing/extraction_instruction.txt` | Manual test harness only |
| Ollama relevance re-export | `app/llm/services/ollama_relevance_classifier_service.py` | Relevance (Ollama backend) |

**Note:** General extraction and relevance prompts mix extensive inline rules with Python schema/validation in the same module. Presence gate and category detail split prose (file) from post-processing heuristics (Python in `ollama_presence_gate_service.py`).

### 3.2 External prompt files (rules content)

| File | Stage | Category |
|------|-------|----------|
| `scripts/phase2-extraction-testing/presence_gate_instruction.txt` | Presence gate | rules |
| `scripts/phase2-extraction-testing/combined_tier1_presence_extraction_instruction.txt` | Combined Tier 1 | rules |
| `scripts/phase2-extraction-testing/category_detail_instruction.txt` | Tier 2 | rules |
| `scripts/phase2-extraction-testing/batched_category_detail_instruction.txt` | Tier 2 batched | rules |
| `scripts/phase2-extraction-testing/extraction_instruction.txt` | Legacy test | rules |

### 3.3 Inline prompt rule blocks (within Python)

| File | Lines | Content summary | Category |
|------|-------|-----------------|----------|
| `app/llm/services/ollama_extraction_service.py` | 56–141 | Full Tier 1 Arabic rules: multi-village, casualty_scope, transitions, sub_events, vague quantifiers | rules |
| `app/llm/services/local_llm_relevance_classifier.py` | 26–61 | Inclusion/exclusion criteria for relevance | rules |

---

## 4. Few-shot examples (embedded in prompts)

| File | Lines | Example topic | Category |
|------|-------|---------------|----------|
| `app/llm/services/ollama_extraction_service.py` | 79 | Two-action sub_events (Kfar Roummane house + car) | fewshot |
| `app/llm/services/ollama_extraction_service.py` | 86–91 | 5× `casualty_transitions` numbered examples | fewshot |
| `app/llm/services/ollama_extraction_service.py` | 93–96 | 3× `village_roles` examples (tank origin, single target, multi-village toll) | fewshot |
| `app/llm/services/ollama_extraction_service.py` | 73 | Dash-route example: `مرج حاروف - زبدين` | fewshot |
| `app/llm/services/ollama_extraction_service.py` | 107, 139 | Vague quantifier + demographic split examples | fewshot |
| `scripts/.../presence_gate_instruction.txt` | 35–43 | 8 English proximity/subject-target examples | fewshot |
| `scripts/.../combined_tier1_presence_extraction_instruction.txt` | 45–50+ | English transition + village_roles examples | fewshot |
| `scripts/.../category_detail_instruction.txt` | 21–24 | 3 category-specific null-detail examples | fewshot |

---

## 5. Casualty merge / scope logic

| File | Lines | Excerpt | Category |
|------|-------|---------|----------|
| `app/llm/services/ollama_extraction_service.py` | 110–112 | `casualty_scope` enum rules in prompt | rules |
| `app/news/services/incident_details/casualty_scope_backstop.py` | 77–113 | Validates `per_village_exact` vs `bulletin_aggregate` against evidence | rules |
| `app/news/services/incident_details/casualty_transition_merge.py` | 7–81 | `injured→deceased` merge arithmetic for `merge_existing` | rules |
| `app/news/repositories/incident_repository.py` | 1128–1210 | `merge_existing`: backstop gating, idempotent transitions, review flags | rules |
| `app/news/services/extraction/tier2_detail_fill_service.py` | 158–277 | Multi-village suppresses category/root demographics; aggregate bulletin groups | rules |
| `app/news/services/materialization/incident_materialization_service.py` | 1357–1438 | Multi-village casualty scope downgrade / bulletin aggregate handling | rules |
| `app/news/services/reconciliation/bulletin_reconciliation_service.py` | 120–139 | Re-validates `per_village_exact` scope on reconciliation | rules |

---

## 6. Conditions reference table vs hardcoded IDs

| Location | Pattern | Reads DB? |
|----------|---------|-----------|
| `ConditionRepository` + `CONDITION_ALIASES` | Similarity match on `action_ar` + alias phrases | Yes (conditions table) + hardcoded aliases |
| `matching_service.CONDITION_DISTINGUISHING_TOKENS` | IDs 2, 39 require disambiguating substrings | Hardcoded IDs |
| `fast_path_eligibility.AIR_VIOLATION_CONDITION_IDS` | Exclude 35/36/38 from incident fast path | Hardcoded IDs |
| `red_alert_collector.AIR_KEYWORDS` | Map keywords → condition IDs 35/36/38 | Hardcoded IDs |
| `red_alert_collector.UNCLASSIFIED_AIR_CONDITION_ID` | Fallback condition 45 | Hardcoded ID |
| `air_violation_workbook_service.AIR_CONDITION_IDS` | Workbook import filter | Hardcoded IDs |
| `condition_evidence_override.py` | Regex → English action names, resolved via repository | Hybrid |

**Assessment:** Air-violation IDs (35/36/38/45) and warning/feigned IDs (2/39) are intentionally hardcoded operational constants tied to seed data. Arabic *phrases* should migrate to `terminology/`; numeric IDs may remain as config or `needs clarification`.

---

## 7. Other “if Arabic phrase → do X” patterns

| File | Lines | Pattern | Category |
|------|-------|---------|----------|
| `app/llm/services/ollama_presence_gate_service.py` | 399–503 | `_is_context_only_evidence`: category-specific proximity/escort/hospital transport rules | rules |
| `app/news/services/matching/condition_evidence_override.py` | 15–26 | Weapon/evidence regex → override matched condition | rules |
| `app/news/services/dedup/story_relationship_service.py` | 165–224 | Embedding thresholds + action-bucket heuristics for story relationship | rules |
| `app/news/services/clustering/raw_message_embedding_service.py` | 12–62 | Boilerplate strip regexes (Telegram headers, etc.) | needs clarification |
| `app/sources/services/red_alert_collector.py` | 74–107 | `_NON_LOCATION_TERMS`, `NON_EVENT_NOTICE_PARTS` | terminology |
| `app/sources/services/red_alert_collector.py` | 218–223 | `حيطة`/`خبطة` + `حذر` heuristic | needs clarification |

---

## Needs clarification

1. **`CONDITION_DISTINGUISHING_TOKENS` IDs 2 and 39** — Confirm these always match seeded `conditions.id` across environments; migrate tokens only or also document ID→condition mapping in `index.yaml`?

2. **Air violation IDs 35/36/38/45** — Spec mentions these explicitly. Keep as Python/ SQL constants (operational routing) while migrating Arabic keyword lists to YAML, or move full ID maps to config?

3. **`category_mapper.py` English+Arabic keyword sets** — Tier 2 post-processing, not LLM prompts. Include in `llm_knowledge/terminology` or leave as materialization logic?

4. **`raw_message_embedding_service.py` boilerplate patterns** — Text normalization for embeddings, not extraction prompts. Out of scope?

5. **`RED_ALERT_VILLAGE_ALIASES` / OCR-specific typos** (`معم سر`, `كوترية`) — Red Alert ingestion only; separate namespace from war-news bulletin pipeline?

6. **`UNCERTAIN_VILLAGE_LOCATION_ALIAS_NOTES`** — Document as eval corpus negative cases or hold until human review?

7. **`condition_evidence_override` English condition names** (`Tank Fire`, `Bombs`) — Maps to DB `action_en`; terminology file should use Arabic, English, or condition key?

8. **Legacy `extraction_instruction.txt`** — Still used by `scripts/phase2-extraction-testing/run_extraction_test.ps1`; migrate or deprecate with test harness?

---

## Recommended `index.yaml` stage mapping (preview for Phase 2)

| Stage | Core rules | Situational triggers | Terminology | Few-shot |
|-------|------------|---------------------|-------------|----------|
| `relevance_filter` | relevance criteria | — | — | — |
| `tier1_extraction` | tier1_core.md | `is_multi_village_candidate` → tier1_multi_village.md | role_terms, revision_language_markers, vague_quantifiers | village_collision, scope, transitions |
| `presence_gate` | presence_gate rules (from txt) | — | org_types, vehicle_terms, municipal_terms | presence_gate examples |
| `casualty_scope` | casualty_merge.md | — | casualty_gender.yaml | scope_examples.jsonl |
| `casualty_transitions` | transition rules (subset of tier1) | — | transition_markers.yaml | transition examples |
| `village_matching` | village_matching.md | collision / geo-context | village alias glossary (reference only) | village_collision_examples |
| `story_revision` | revision detection rules | — | revision_language_markers | — |
| `tier2_detail` | category_detail rules | per category_key | category keywords | category null examples |
| `condition_matching` | — | distinguishing tokens | condition_aliases + air_keywords | — |

---

## Embedding infrastructure for few-shot retrieval (Phase 2)

Reuse existing path:
- `app/news/services/clustering/embedding_service.py` — `SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")`
- `EmbeddingServiceInterface.generate(text)` — no second embedding stack needed

---

## Files with NO migration needed (reference only)

- `Data/Conditions.json`, `Data/Villages.json` — canonical DB seeds
- `app/news/models/*` — schema enums (`CasualtyScope`, etc.)
- `app/llm/dtos/extraction_dto.py` — Pydantic shapes (not domain prose)
- `KeywordPrefilterService` — loads keywords from DB at runtime (not hardcoded domain list)

---

## Phase 1 complete

No code changes in this phase except this document. Next: Phase 2 additive architecture under `app/core/llm_knowledge/`, then batched migration per pipeline stage.
