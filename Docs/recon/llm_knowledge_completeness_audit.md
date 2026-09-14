# llm_knowledge Completeness Audit (Part A.1)

**Date:** 2026-09-14  
**Scope:** All `app/**/*.py` outside `app/core/llm_knowledge/`  
**Method:** Full Arabic Unicode scan (205 hits / 23 files) + LLM call-site inventory + `index.yaml` coverage check

Raw scan dump (auto): `Docs/recon/_arabic_scan_raw.md`

---

## Test baseline for this audit

Current suite reference (post prior migration): **665 passed / 15 failed / 3 errors / 11 skipped**.

---

## LLM call sites vs `index.yaml`

| Call site | Stage | Uses `PromptBuilder`? | `index.yaml` entry? | Verdict |
|-----------|-------|----------------------|---------------------|---------|
| `ollama_extraction_service._extract_general_fields` | Tier 1 general | Yes | `tier1_extraction` | OK |
| `ollama_extraction_service._extract_tier1_combined` | Combined Tier 1 | Yes | `combined_tier1` | OK |
| `ollama_presence_gate_service` chat | Presence gate | Yes | `presence_gate` | OK |
| `ollama_category_detail_service` (single) | Tier 2 detail | **No** — loads `scripts/.../category_detail_instruction.txt` | **Missing** | **MIGRATE** |
| `ollama_category_detail_service` (batched) | Tier 2 batched | **No** — loads `batched_category_detail_instruction.txt` | **Missing** | **MIGRATE** |
| `local_llm_relevance_classifier` | Relevance | **No** — inline `RELEVANCE_CLASSIFICATION_PROMPT` | `relevance_filter` exists but `core: []` | **MIGRATE** |

No other Ollama chat call sites found under `app/`.

---

## Hit catalog (migrate vs code-only)

### MIGRATE — LLM prompt / knowledge still outside `llm_knowledge/`

| ID | File | Lines | Excerpt / summary | Reasoning |
|----|------|-------|-------------------|-----------|
| M1 | `app/llm/services/ollama_category_detail_service.py` | 48–61, 186, 217 | Loads Tier 2 prompts from `scripts/phase2-extraction-testing/*.txt`; system message bypasses PromptBuilder | LLM-facing prompt text; must live under `rules/` and assemble via PromptBuilder + new `index.yaml` stages `tier2_detail` / `tier2_detail_batched` |
| M2 | `app/llm/services/local_llm_relevance_classifier.py` | 26–61, 134 | Inline English relevance inclusion/exclusion criteria | LLM-facing prompt; move to `rules/relevance_filter.md` and wire `relevance_filter` stage |
| M3 | `app/llm/services/ollama_presence_gate_service.py` | 401–434 | Remaining inline heuristic terms: `الطريق`/`الجسر`/`الأوتوستراد`, `مواكبة`, `قسم الطوارئ`, `إلى المستشفى`, army impact phrases | Term *lists* still hardcoded after prior migration; logic stays code-only but terms belong in `terminology/role_terms.yaml` |
| M4 | `app/llm/services/cnrs_extraction_fallback.py` | 26, 38 | `_MOTORCYCLE_TEXT_MARKERS = ("دراج","موتور")`; `"دبابة" in post_text` | Duplicate of role_terms / vehicle terminology; should load from YAML (deterministic code stays) |
| M5 | `app/llm/services/ollama_extraction_service.py` | 43–51 | `_DASH_ROUTE_RE`, `_ROUTE_AREA_PREFIXES = ("مرج ",)` | Prefix already in `role_terms.yaml`; wire load from terminology; regex remains code-logic |
| M6 | `app/news/services/air_violations/import_source_enrichment.py` | 136 | `aliases = {'كفره': 72257, 'شعث': 53274, 'النبطيه': 71111}` | Same class as village location aliases; migrate into `terminology/village_aliases.yaml` (or import-specific section) |

### CODE-ONLY — intentional (documented)

| ID | File | Lines | Reasoning |
|----|------|-------|-----------|
| C1 | `category_mapper.py` L103–485 | Keyword frozensets + warning/building name heuristics | Phase 2.5: post-LLM deterministic field routing; never enters a prompt |
| C2 | `casualty_transition_backstop.py` / `story_revision_backstop.py` | Regex detector tables | Phase 3.5: labels mirrored in YAML; compiled regex patterns are deterministic detectors |
| C3 | `casualty_gender_evidence.py` | Occupation regex wrappers `شهيد\|استشهاد` | Grammar pattern around YAML-loaded role nouns; code-logic |
| C4 | `casualty_count_backstop.py` | Digit boundary / Indic digits | Normalization helpers, not domain vocabulary |
| C5 | `condition_evidence_override.py` | Weapon/evidence regexes | Deterministic remapping; Arabic stems already catalogued in `condition_labels.yaml` |
| C6 | `story_relationship_service.py` | `_HOUSE_RE` / `_CAR_RE` / `_SPARSE_RE` | Deterministic embedding-heuristic story routing (not LLM prompt) |
| C7 | `raw_message_embedding_service.py` | Boilerplate strip patterns | Phase 2.5: embedding hygiene |
| C8 | `text_normalization.py` | Alef/ya punctuation maps | Shared normalizer infrastructure |
| C9 | `red_alert_collector.py` | `RED_ALERT_VILLAGE_ALIASES`, OCR typos, non-event notices | Phase 2.5: ingestion-only; OCR typos stay local |
| C10 | `rejected_news_router.py` | Arabic UI rejection reasons + khabar summary templates | API presentation / i18n, not LLM knowledge |
| C11 | `air_violation_repository.py` | Khabar format strings `فوق`/`في قضاء` | Deterministic string templates for air-violation rows |
| C12 | `matching_service.py` L57–58 | Fallback `("تحذيريه",)` / `("وهميه",)` | Defensive fallback if YAML empty; primary load from terminology |
| C13 | `village_aliases.py` uncertain notes | Documentation tuples | Already mirrored as eval negatives |
| C14 | Model docstrings (`emergency_organization.py`, `village_location_alias.py`) | Comments only | No runtime knowledge |
| C15 | `casualty_scope_backstop.py` | Generic word-boundary regex | Infrastructure, phrase comes from caller |
| C16 | `red_alert_air_violation_service.py` L63 | `آخر تحديث` + `لبنان` gate | Ingestion heuristic (same family as C9) |
| C17 | Numeric condition IDs 2/35/36/38/39/45 | Various | Phase 2.5: deterministic routing |

### AMBIGUOUS / NEEDS CLARIFICATION (not auto-migrated as LLM knowledge)

| ID | File | Issue | Tentative call |
|----|------|-------|----------------|
| A1 | `rejected_news_router.py` L95–114 | Air-type keyword detection for *UI summaries* overlaps air terminology | **Code-only** for now (UI); optionally share keywords with `condition_labels.yaml` later without PromptBuilder |
| A2 | `category_mapper.py` L477–485 | `لا تحذير` / `إبادة` / `شقة` in *name* classification | **Code-only** (same as C1); optional doc-only mirror in terminology |
| A3 | `import_source_enrichment.py` L104 | Regex stripping air prefixes from import text | Ingestion code-logic; phrases already in condition_labels — keep regex, no PromptBuilder |
| A4 | Scripts under `scripts/phase2-extraction-testing/*.txt` | Still on disk after prompt migration | **Keep** until harness updated (prior Phase 2.5 #8); not production path once M1–M2 done |

---

## Coverage gap summary

**Must migrate in A.2 (production LLM paths):**
1. Tier 2 category-detail prompts (single + batched) → `llm_knowledge` + PromptBuilder  
2. Relevance classification prompt → `llm_knowledge` + PromptBuilder  
3. Remaining presence-gate heuristic term literals → `role_terms.yaml`  
4. CNRS motorcycle / tank markers → load from terminology  
5. Dash-route prefix → load from terminology  
6. Import village ACS aliases → `village_aliases.yaml`

**Confirmed complete from prior migration (no further prompt work):**
- Tier 1 general + combined prompts  
- Presence gate prompt file  
- Condition/village alias catalogues (loaders)  
- Backstop *labels* catalogue  

---

## A.1 complete

This report is reviewable independently of A.2. Next: migrate M1–M6 in per-module batches.

---

## A.2 migration status

Committed in `f62eda7` (`refactor(llm_knowledge): wire PromptBuilder and migrate completeness stragglers`):

| ID | Action taken |
|----|--------------|
| M1 | Tier 2 prompts → `rules/tier2_*_prompt.md`; wired via `build_stage_system_prompt` + `tier2_detail` / `tier2_detail_batched` in `index.yaml` |
| M2 | Relevance prompt → `rules/relevance_filter_prompt.md`; wired via PromptBuilder |
| M3 | Remaining presence heuristic terms → `role_terms.yaml`; `_is_context_only_evidence` loads categories |
| M4 | CNRS motorcycle/tank markers load from `role_terms.yaml` |
| M5 | `_ROUTE_AREA_PREFIXES` loads from `route_area_prefix` terminology |
| M6 | Import ACS aliases → `village_aliases.yaml`; `import_source_enrichment` loads them |

---

## A.3 confirmation re-scan (2026-09-14)

Re-ran the same Arabic Unicode scan after A.2:

| Metric | A.1 | A.3 |
|--------|----:|----:|
| Files with hits | 23 | 23 |
| Total hits | 205 | 201 |
| Presence-gate hardcoded heuristic literals | 6 | **1** (only residual punctuation/comment-free load path) |

**LLM PromptBuilder coverage (re-checked):**

| Stage | PromptBuilder? |
|-------|----------------|
| `tier1_extraction` | Yes |
| `combined_tier1` | Yes |
| `presence_gate` | Yes |
| `relevance_filter` | Yes |
| `tier2_detail` | Yes |
| `tier2_detail_batched` | Yes |

**Remaining Arabic hits are exclusively code-only** (C1–C17 from A.1 catalog):
- Red Alert ingestion / OCR / UI rejection strings
- `category_mapper` deterministic routing keywords
- Backstop **regex** detectors (labels already in YAML)
- Boilerplate strip, text normalization, story-relationship heuristics
- Defensive fallbacks (`or ("دراج", "موتور")`) when YAML empty
- Dash-route regex character classes
- Model/docstring comments

**No remaining migrate-class LLM prompt text outside `llm_knowledge/`.**

Test suite after A.2/A.3: **665 passed / 15 failed / 3 errors / 11 skipped** — identical failure names to baseline; no new regressions.
