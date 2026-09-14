# llm_knowledge Full Flow Health Check

**Date:** 2026-09-14  
**Scope:** Static integrity → stage wiring → root-cause analysis → targeted fixes

---

## Phase 1: Static Integrity Check

### 1.1 Schema Validation

All YAML and JSONL files parsed successfully:

- **Terminology files (6):** All valid YAML; all entries have required `term`, `category`, `meaning` fields
- **Fewshot files (2):** All valid JSONL; `fewshot/scope_examples.jsonl` (9 entries), `fewshot/village_collision_examples.jsonl` (4 entries)
- **Eval corpus files (4):** All valid JSONL; total 31 test cases across `tier1_extraction.jsonl`, `casualty_scope.jsonl`, `village_matching.jsonl`, `revision_detection.jsonl`
- **index.yaml:** Valid; defines 10 pipeline stages

**Status:** ✅ CLEAN

### 1.2 Duplicate/Conflicting Terminology

#### Intra-file conflicts

**condition_labels.yaml:**
- `طيران حربي` appears twice:
  - Line 58: `air_violation_keyword` (individual entry)
  - Line 136: Part of compound `طيران حربي / مقاتلات حربية` under `condition_id_label`
- **Severity:** MINOR — Different categories, different semantic roles (keyword vs glossary label)

#### Cross-file conflicts

**بلدية / مبنى البلدية / موظفي البلدية:**
- `role_terms.yaml` → `municipal_infrastructure` category
- `org_types.yaml` → `municipality` category
- **Severity:** MINOR — Same meaning, different category strings; `scan_terminology` first-match-wins behavior is deterministic

**موظف:**
- `role_terms.yaml` line 27 → `municipal_infrastructure/employee`
- `casualty_gender.yaml` → `male_role_noun` (in compounds like `استشهاد موظف`)
- **Severity:** MINOR — The raw term `موظف` exists in role_terms only; casualty_gender has compound forms. `scan_terminology` will find the role_terms entry first for the standalone term.

**Orthography pairs (expected, not conflicts):**
- `revision_language_markers.yaml`: `تنعى` (line 48) and `تنعي` (line 53) — both normalize to `تنعي`; second entry documents the post-normalization form
- `village_aliases.yaml`: `النبطية` and `النبطيه` — both map to `acs:71111` (taa-marbuta variant)

**Status:** ✅ CLEAN (no blocking conflicts; minor duplicates documented)

### 1.3 Orphan Files and References

**Orphan rule file (on disk, not in index.yaml):**
- `rules/tier1_core.md` — 43-line rule file covering output discipline, relevance, villages/roles, casualty counts, demographics, sub-events, categories
- **Severity:** 🔴 BUG — Legitimate rule content exists but is never loaded by any stage

**Orphan index.yaml references (in index.yaml, not on disk):**
- None — all 9 rule files referenced in index.yaml exist on disk

**Status:** 🔴 BUG FOUND — `tier1_core.md` orphaned

### 1.4 Situational Trigger Coverage

**Registered triggers:**
- `is_multi_village_candidate` → loads `rules/tier1_multi_village.md`

**Function implementation:**
- Location: `app/core/llm_knowledge/loader.py:182-195`
- Logic: Dash-route regex + separator count ≥2 + Arabic "and" clause heuristics

**Test coverage:**
- File: `tests/test_llm_knowledge_loader.py`
- `test_is_multi_village_candidate_dash_route()` (line 46) — TRUE branch ✅
- `test_is_multi_village_candidate_single_village_false()` (line 51) — FALSE branch ✅

**Status:** ✅ CLEAN (both branches tested)

### 1.5 Eval Corpus Balance

| Corpus File | Total | real_bug | synthetic | Balance |
|-------------|------:|--------:|----------:|---------|
| `tier1_extraction.jsonl` | 11 | 7 | 4 | ✅ CLEAN |
| `casualty_scope.jsonl` | 6 | 2 | 4 | ⚠️ MINOR (majority synthetic) |
| `village_matching.jsonl` | 9 | 9 | 0 | ⚠️ MINOR (no adversarial test cases) |
| `revision_detection.jsonl` | 5 | 4 | 1 | ✅ CLEAN |

**Status:** ⚠️ MINOR — `village_matching` lacks synthetic adversarial cases; `casualty_scope` is majority synthetic

### 1.6 Stage Wiring Integrity

**Critical bug identified:**

**`story_revision` stage (index.yaml lines 73-78):**
- **Rule file:** `rules/casualty_merge.md` — contains casualty_scope, casualty_transitions, and merge_existing logic; **ZERO revision-detection content**
- **Fewshot:** None configured
- **Terminology:** `revision_language_markers.yaml` (correct)

**What `casualty_merge.md` actually contains:**
- `casualty_scope` values and evidence rules
- `casualty_transitions` injured→deceased transition patterns
- `merge_existing` logic for combining incident extractions
- Backstop validation rules

**What it does NOT contain:**
- Any instruction to detect preliminary toll language
- Any instruction to detect named-victim follow-ups
- Any instruction to set `relationship_hint="revision"`

**Backstop relationship:**
- `app/news/services/incident_details/story_revision_backstop.py` implements deterministic regex-based revision detection via `_REVISION_PATTERNS` and `_NAMED_VICTIM_PATTERNS`
- The backstop runs AFTER (or alongside) the LLM stage and can rescue cases the LLM misses
- **However:** The LLM stage itself receives no meaningful revision-detection instruction

**Live validation impact:**
- 3 of 4 real_bug revision cases fail in live validation (see `Docs/recon/llm_knowledge_live_validation.md`)
- Backstop cannot rescue all cases if eval tests the LLM output directly before backstop runs

**Severity:** 🔴 BUG — Wrong rule file wired to `story_revision` stage

### 1.7 Phase 1 Summary

| Finding | Severity | Description |
|---------|----------|-------------|
| Schema validation | ✅ CLEAN | All YAML/JSONL files valid |
| Terminology conflicts | ⚠️ MINOR | Cross-file duplicates exist; first-match-wins behavior is deterministic |
| Orphan rule file | 🔴 BUG | `tier1_core.md` exists on disk but not referenced in index.yaml |
| Trigger test coverage | ✅ CLEAN | `is_multi_village_candidate` has true/false branch tests |
| Corpus balance | ⚠️ MINOR | `village_matching` has no synthetic cases; `casualty_scope` is majority synthetic |
| **story_revision wiring** | 🔴 BUG | Stage receives `casualty_merge.md` (wrong rule) + no fewshot; LLM has zero revision-detection instruction |

**Blocking bugs before Phase 2:** 2
- Orphan `tier1_core.md` file
- `story_revision` stage wired to wrong rule file

---

## Phase 2: Stage Wiring and Prompt Assembly

*(To be completed)*

---

## Phase 3: Root Cause Analysis — Live Validation Failures

*(To be completed)*

---

## Phase 4: Targeted Fixes

*(To be completed)*

---

## Final Summary

*(To be completed after Phase 4)*
