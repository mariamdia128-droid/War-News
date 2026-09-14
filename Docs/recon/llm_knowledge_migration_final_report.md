# llm_knowledge Migration — Final Report (Phases 2.5 → 5)

**Date:** 2026-09-14  
**Commits:** none in this session (user will commit manually)

---

## Test suite

| | Passed | Failed | Errors | Skipped |
|--|--:|--:|--:|--:|
| Baseline (Phase 1) | 655 | 15 | 3 | 11 |
| After Phases 2.5–5 | **665** | **15** | **3** | **11** |

**Delta:** +10 passed (new `test_llm_knowledge_loader` cases). Failures/errors are the **same names** as baseline — no new regression.

Baseline failure names (unchanged):
- 7× `tests/news/test_cnrs_webhook.py`
- `test_air_violation_concurrency`, `test_extraction_transient_retry`, `test_incident_event_stream`, `test_pipeline_health_route`, 2× `test_pipeline_jobs`, `test_rescan_existing_duplicates`, `test_village_role_materialization`
- Errors: `test_seed_villages`, 2× `test_village_location_aliases` (tmp_path PermissionError)

Eval harness: `python -m app.core.llm_knowledge.eval.run_eval` → **17 passed, 0 failed** (knowledge-load + assembly checks; not live Ollama).

---

## Phase 2.5 decisions (restated)

| Item | Decision |
|------|----------|
| `category_mapper.py` keywords | **Code-only** — post-LLM deterministic field routing |
| Air/condition IDs 2,35,36,38,39,45 | **Code-only IDs**; Arabic phrases → terminology |
| Boilerplate strip regexes | **Out of scope / code-only** |
| Red Alert OCR / village aliases | **Ingestion-only**; stay in Red Alert code |
| Uncertain village notes | **Eval negatives** (not seeded) |
| `condition_evidence_override` | **Logic stays**; Arabic stems in terminology |
| Legacy `extraction_instruction.txt` | **Scripts-only**; keep until harness update |

Full text: `Docs/recon/llm_knowledge_migration_recon.md` §Needs clarification → Resolved.

---

## Fragment tally (reconcile to 85)

| Bucket | Count | Notes |
|--------|------:|-------|
| Migrated into `llm_knowledge/` + wired | ~62 | terminology, rules, fewshot, prompt paths |
| Intentionally code-only (Phase 2.5) | ~18 | IDs, category_mapper, boilerplate, Red Alert OCR, override control flow, scripts legacy prompt |
| Code-logic kept with terms loaded from YAML | ~5 | backstop regexes, presence `_is_context_only_evidence`, count/gender apply_* |

No original recon fragment left unclassified.

---

## Files deleted

**None.** Production prompt constants were rewritten to load from `app/core/llm_knowledge/`; script copies under `scripts/phase2-extraction-testing/` retained on purpose (Phase 2.5 #8).

Stale-import check: `scripts/check_stale_service_imports.py` — run after local commit.

---

## Wiring confirmation

| `index.yaml` stage | Call site |
|--------------------|-----------|
| `tier1_extraction` | `ollama_extraction_service._extract_general_fields` via `build_stage_system_prompt` |
| `combined_tier1` | `ollama_extraction_service._extract_tier1_combined` |
| `presence_gate` | `ollama_presence_gate_service` chat system message |
| `casualty_scope` / `story_revision` / etc. | PromptBuilder available; backstops load terminology via `terms_by_category` |

Modules now sourcing terminology YAML:
- `condition_aliases.py`, `village_aliases.py`
- `matching_service.CONDITION_DISTINGUISHING_TOKENS` (tokens only)
- `red_alert_collector.AIR_KEYWORDS` (phrases only)
- `ollama_presence_gate_service` term tuples
- `casualty_gender_evidence`, `casualty_count_backstop`
- label helpers in transition/revision backstops

---

## Knowledge inventory (entry counts)

| File | Entries / size |
|------|----------------|
| `terminology/casualty_gender.yaml` | 50 |
| `terminology/condition_labels.yaml` | 25 |
| `terminology/org_types.yaml` | 24 |
| `terminology/revision_language_markers.yaml` | 23 |
| `terminology/role_terms.yaml` | 79 |
| `terminology/village_aliases.yaml` | 18 |
| `fewshot/scope_examples.jsonl` | 9 |
| `fewshot/village_collision_examples.jsonl` | 4 |
| `eval/corpus/tier1_extraction.jsonl` | 5 |
| `eval/corpus/casualty_scope.jsonl` | 3 |
| `eval/corpus/village_matching.jsonl` | 9 |
| `rules/*.md` | 7 files (incl. full Tier1 + presence + combined prompts) |

---

## Follow-up TODOs

1. Point `run_extraction_test.ps1` / `quick_test.ps1` at `rules/tier1_general_prompt.md`, then delete legacy `extraction_instruction.txt`.
2. Optionally sync/remove duplicate script prompt files once harness updated.
3. Grow `run_eval.py` to exercise real extraction path (currently assembly-only — **do not** run live Ollama without explicit approval; ~150s/call).
4. Consider mirroring `category_mapper` keywords into terminology for documentation only (not required).

---

## Suggested commit sequence (manual)

1. `docs(recon): resolve Phase 2.5 clarifications`
2. `refactor(llm_knowledge): migrate pure terminology (batch 3.1)`
3. `refactor(llm_knowledge): migrate Tier 1 prompt + fewshot (batch 3.2)`
4. `refactor(llm_knowledge): migrate matching aliases (batch 3.3)`
5. `refactor(llm_knowledge): migrate presence gate terms (batch 3.4)`
6. `refactor(llm_knowledge): migrate backstop terminology, preserve backstop logic (batch 3.5)`
7. (optional) `docs: llm_knowledge migration final report`
