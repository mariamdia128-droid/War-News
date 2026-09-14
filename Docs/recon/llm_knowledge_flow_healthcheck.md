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

### 2.1 Ollama call-site inventory

The runtime Ollama call sites are:

| Stage | Owner | PromptBuilder stage | Result |
|---|---|---|---|
| Relevance filter | `app/llm/services/local_llm_relevance_classifier.py` | `relevance_filter` | **clean** |
| Presence gate | `app/llm/services/ollama_presence_gate_service.py` | `presence_gate` | **clean** |
| Tier 1 general extraction | `app/llm/services/ollama_extraction_service.py` | `tier1_extraction` | **clean** |
| Combined Tier 1 extraction | `app/llm/services/ollama_extraction_service.py` | `combined_tier1` | **clean** |
| Tier 2 detail | `app/llm/services/ollama_category_detail_service.py` | `tier2_detail` | **clean** |
| Batched Tier 2 detail | `app/llm/services/ollama_category_detail_service.py` | `tier2_detail_batched` | **clean** |

The legacy module-level prompt constants remain as compatibility aliases, but
the runtime calls use `build_stage_system_prompt`; no leftover runtime local
prompt-construction path was found.

The evaluation harness also calls `build_stage_system_prompt` for all corpus
stages, including `story_revision`. That stage has no production Ollama
service of its own; its prompt is assembled by `eval/run_eval.py`.

### 2.2 Prompt assembly spot checks

Offline `PromptBuilder` assembly was exercised for representative inputs from
the extraction, scope, village, presence, detail, relevance, and revision
stages. Core rule text was present for every configured stage. The situational
`tier1_multi_village.md` rule loaded for multi-village candidates and did not
load for a single-village input. Matched terminology included the expected
Arabic terms for `مسعف`, revision markers, village aliases, and organization
terms when present in the source text.

No prompt-assembly omission was found in the runtime stages. The exception is
the `story_revision` configuration itself, documented in Phase 3: it assembles
the wrong core rule file for the revision task.

### 2.3 Few-shot retrieval

The configured few-shot pools returned non-empty results in the loader test
and offline spot checks. With no embedding service, retrieval intentionally
falls back to file order. With an embedding service, the loader scores every
non-empty example input and returns the top `k` results; no empty-pool or
dimension-mismatch behavior was observed in the checked path.

The mixed-village/mixed-victim example is present in
`village_collision_examples.jsonl`, but the failing `gendered-occupation`
case runs through the combined Tier-1 stage, whose configured pool is
`scope_examples.jsonl`. That pool has no example showing independent
occupation-linked attribution inside a mixed toll. This is a Phase 3 finding,
not a retrieval implementation bug.

### 2.4 Arabic normalization

`scan_terminology` applies `normalize_arabic_text` to both source text and
terminology probes. The normalizer removes tashkeel and tatweel, maps alef
variants, and maps `ى` to `ي`. Existing tests verify equivalent normalized
spellings such as `حصيلة أولية` / `حصيله اوليه`, and the direct `مسعف` lookup
matches the failing input path.

**Status:** **clean**. No Phase 2 normalization bug was found.

### 2.5 Phase 2 finding summary

- **clean:** all six runtime Ollama stage families use `PromptBuilder`.
- **clean:** configured core and situational rule assembly works offline.
- **clean:** few-shot retrieval returns configured examples and has a tested
  file-order fallback.
- **clean:** Arabic diacritic and alef/yaa normalization covers the checked
  variants.
- **minor:** the mixed-toll occupation example is in a different pool from
  the combined Tier-1 stage and is therefore not available to that prompt.

## Phase 3: Root-Cause Investigation

### 3.1 Revision detection under-specification

The three failing revision cases use the `story_revision` stage in the
evaluation harness. Its `index.yaml` entry loads only `rules/casualty_merge.md`
and `revision_language_markers.yaml`. The assembled rule text describes
casualty scope and injured-to-deceased transitions, but it does not instruct
the model to classify preliminary tolls, rising tolls, obituary/named-victim
follow-ups, or `relationship_hint="revision"`.

The terminology file is present and the deterministic
`story_revision_backstop.py` recognizes these patterns, but the eval call
tests the LLM stage output directly. This explains the failures for
`المعلومات الأولية`, `تنعى`, and `حصيلة أولية`; the passing `ارتفاع عدد` case
is model behavior rather than evidence that the prompt is complete.

**Finding:** **bug**, confirmed knowledge/prompt gap.

**Proposed fix:** add `rules/story_revision_prompt.md` with the backstop's
preliminary-toll, rising-toll, toll-correction, and named-victim follow-up
patterns, then wire it to the `story_revision` entry in `index.yaml`. Keep the
existing Python backstop unchanged and additive.

**Risk:** low; pure knowledge addition plus one index reference, with no
backstop behavior change.

### 3.2 Gendered occupation in a mixed toll

For the exact failing mixed-toll input, the combined Tier-1 prompt contains
the matched `مسعف` terminology entry and the existing mandatory two-action
example in `combined_tier1_prompt.md`. The `scope_examples.jsonl` pool still
returns transition/scope examples and contains no example whose expected
output attributes an occupation-linked casualty independently inside a
separate mixed-victim toll.

The standalone `مسعف` cases pass, and the exact terminology match succeeds
offline. Therefore this is not a missing term or Arabic-normalization defect.

**Finding:** **minor**, suspected few-shot coverage gap confirmed by pool
inspection; the live partial result is model behavior.

**Proposed fix:** add a `scope_examples.jsonl` example based on the failing
house-plus-car bulletin, with the separate car sub-event assigning
`male_deaths=1` for `مسعف` while preserving the unrelated house toll.

**Risk:** low; pure few-shot knowledge addition.

### 3.3 Intentionally unmapped context-dependent terms

`مدني شهيد` and `طفل شهيد` remain intentionally unmapped. The current
terminology design avoids turning context-dependent adjectives into automatic
demographic counts. No live failure in the supplied 16-case validation run
requires changing that decision.

**Finding:** **clean by design**; retain as a review candidate only if a
future corpus case establishes a reliable disambiguation rule.

### 3.4 Phase 3 disposition

Both authorized Phase 4 changes are appropriately narrow: one revision rule
file/index wiring change and one mixed-toll few-shot example. No backstop code,
schema, or expected output requires modification.

---

## Phase 3: Root Cause Analysis — Live Validation Failures

*(To be completed)*

---

## Phase 4: Targeted Fixes

*(To be completed)*

---

## Final Summary

*(To be completed after Phase 4)*
