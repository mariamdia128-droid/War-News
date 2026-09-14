# llm_knowledge CHANGELOG

## 2026-09-14 — B.3 confirm air-violation / special condition IDs

**Decision (reconfirmed):** condition IDs `2`, `35`, `36`, `38`, `39`, `45` remain Python/SQL constants for deterministic routing, distinguishing-token gates, fast-path exclusion, and unclassified fallback. They must not move into PromptBuilder as authoritative IDs.

**Prompt gap closed:** added `condition_id_label` rows in `terminology/condition_labels.yaml` with Arabic surface forms + documented `condition_id=N` notes for LLM explanation only. Wired `condition_labels.yaml` into `tier1_extraction` index terminology.

## 2026-09-14 — B.2 expand terminology coverage

| Change | Reason |
|--------|--------|
| `casualty_gender.yaml`: occupation×status compounds + جندية/اطفائية/مسعفة | Document unambiguous role×death patterns for prompts; flag مدني/طفل as ambiguous |
| `org_types.yaml`: sharpen الرسالة vs الهيئة الصحية notes | Confirm two distinct orgs (scout_paramedic vs health_organization), not merged |
| `revision_language_markers.yaml`: تنعي/الشهيده + مراجعة/تصحيح الحصيلة | Orthography used by backstop regex + common revision phrasing from audits |
| `role_terms.yaml`: مسيرة/مسيّرة/طيران حربي/مروحية | Air-platform nouns from real bulletin text for prompt glossary |

## 2026-09-14 — B.1 eval corpus from historical bugs

| Corpus file | Entries (approx) | Coverage |
|-------------|------------------|----------|
| `tier1_extraction.jsonl` | 11 | vague quantifiers, gender/occupation, transitions |
| `casualty_scope.jsonl` | 6 | multi-village misattribution, null-not-shared, merge-before-max-wins |
| `village_matching.jsonl` | 9 | maslakh/nabatieh/qantara/aynata/kafra + ambiguous negatives |
| `revision_detection.jsonl` | 5 (new) | preliminary toll, named victim, rising toll markers |

Tagged `source: real_bug` with `bug_ref` for each historical accuracy class named in the enrichment prompt.

## 2026-09-14 — Completeness audit A.2 stragglers

| Fragment | Destination | Status |
|----------|-------------|--------|
| Tier 2 category detail prompts | `rules/tier2_*_prompt.md` + PromptBuilder | migrated |
| Relevance classification prompt | `rules/relevance_filter_prompt.md` + PromptBuilder | migrated |
| Presence heuristic literals (road/escort/hospital) | `terminology/role_terms.yaml` | migrated |
| CNRS motorcycle/tank markers | load from `role_terms.yaml` | migrated |
| Dash-route `_ROUTE_AREA_PREFIXES` | load from `role_terms.yaml` | migrated |
| Import ACS aliases كفره/شعث/النبطيه | `terminology/village_aliases.yaml` | migrated |


Resolved all 8 recon "needs clarification" items in
`Docs/recon/llm_knowledge_migration_recon.md`. Summary: category_mapper
keywords, numeric condition IDs, boilerplate strip, Red Alert OCR aliases,
and evidence-override control flow stay **code-only**; Arabic labels/phrases
migrate; uncertain aliases → eval negatives; legacy extraction_instruction.txt
stays scripts-only until harness update.

## 2026-09-14 — Batch 3.1 pure terminology

| Fragment source | New location | Status |
|-----------------|--------------|--------|
| Full `_EXPLICIT_FORMS` + duals + plurals + count words | `terminology/casualty_gender.yaml` | completed |
| Full `_MALE_ROLE_NOUNS` / `_FEMALE_ROLE_NOUNS` | `terminology/casualty_gender.yaml` | completed |
| All revision + transition labels | `terminology/revision_language_markers.yaml` | completed |
| Named orgs from EmergencyOrganizations.json | `terminology/org_types.yaml` | completed (prior expand) |
| `load_terminology` / `terms_by_category` / `terms_by_meaning` API | `loader.py` | added for 3.4/3.5 wiring |

## 2026-09-14 — Batch 3.2 Tier 1 prompt + fewshot

| Fragment source | New location | Status |
|-----------------|--------------|--------|
| Inline `GENERAL_EXTRACTION_PROMPT` | `rules/tier1_general_prompt.md` | migrated verbatim |
| `combined_tier1_presence_extraction_instruction.txt` | `rules/combined_tier1_prompt.md` | migrated verbatim |
| `build_stage_system_prompt()` | `prompt_assembly.py` | wired |
| `ollama_extraction_service` Tier 1 + combined calls | uses `PromptBuilder` via prompt_assembly | wired |
| Prompt few-shot examples | `fewshot/scope_examples.jsonl` | expanded |

## 2026-09-14 — Batch 3.3 matching aliases

| Fragment source | New location | Status |
|-----------------|--------------|--------|
| `CONDITION_ALIASES` phrases | `terminology/condition_labels.yaml` | migrated; `condition_aliases.py` loads YAML |
| Distinguishing tokens `تحذيريه`/`وهميه` | `terminology/condition_labels.yaml` | migrated; IDs stay in `matching_service` |
| Air keyword Arabic phrases | `terminology/condition_labels.yaml` | migrated; IDs + OCR typos stay in Red Alert |
| `PROPOSED_VILLAGE_LOCATION_ALIASES` | `terminology/village_aliases.yaml` | migrated; `village_aliases.py` loads YAML |
| Uncertain alias notes | `eval/corpus/village_matching.jsonl` negatives | documented |

## 2026-09-14 — Batch 3.4 presence gate

| Fragment source | New location | Status |
|-----------------|--------------|--------|
| `MUNICIPAL_*` / `VILLAGE_*` / `TARGETING_*` / `VEHICLE_*` | `terminology/role_terms.yaml` | migrated |
| `CIVIL_DEFENSE_ORG_TERMS` | `terminology/org_types.yaml` | migrated |
| Proximity / negative / direct impact term lists | `terminology/role_terms.yaml` | migrated |
| `presence_gate_instruction.txt` | `rules/presence_gate_prompt.md` | migrated |
| `_is_context_only_evidence` branching | stays in Python | code-logic (Phase 2.5) |
| Presence chat system prompt | `build_stage_system_prompt("presence_gate")` | wired |

## 2026-09-14 — Batch 3.5 backstop terminology

| Fragment | Classification | Action |
|----------|----------------|--------|
| Explicit gender term lists | knowledge | load from `casualty_gender.yaml` |
| Role noun lists | knowledge | load from YAML |
| `_standalone` / cover-total / apply_* | code-logic | unchanged behavior, uses loaded terms |
| Transition regex patterns | code-logic | kept in Python |
| Transition labels | knowledge | mirrored in YAML; `keyword_labels()` prefers YAML |
| Revision regex patterns | code-logic | kept in Python |
| Revision labels | knowledge | mirrored in YAML |
| `casualty_count_backstop` count words | knowledge | load from YAML |

## 2026-09-14 — Phase 2 architecture (additive seed)

Initial structure under `app/core/llm_knowledge/`. See earlier commits.
