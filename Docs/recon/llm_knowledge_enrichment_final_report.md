# llm_knowledge Full-Repo Audit + Enrichment — Final Report

**Date:** 2026-09-14  
**Scope:** Part A completeness audit/migration confirm + Part B accuracy enrichment

---

## Part A — Completeness

| Item | Result |
|------|--------|
| Audit report | [`Docs/recon/llm_knowledge_completeness_audit.md`](llm_knowledge_completeness_audit.md) |
| Stragglers classified migrate | M1–M6 (Tier2/relevance prompts, presence heuristics, CNRS markers, route prefixes, import ACS aliases) — wired in prior A.2 commit |
| Confirmed code-only | category_mapper keywords; numeric condition IDs; backstop regex control flow; Red Alert OCR aliases; boilerplate strip; UI/rejected-news strings; air-violation format templates |
| A.3 re-scan | Remaining Arabic hits are code-only only; all LLM call stages go through `PromptBuilder` + `index.yaml` |

Commits: `docs(recon): llm_knowledge completeness audit`, A.2 migration batch(es), `docs(recon): confirm llm_knowledge completeness`.

---

## Part B — Accuracy enrichment

### B.1 Eval corpus growth

| Corpus | Approx entries | Notable `bug_ref`s |
|--------|---------------:|--------------------|
| `tier1_extraction.jsonl` | 11 | gendered occupation, transitions, vague quantifiers |
| `casualty_scope.jsonl` | 6 | multi-village misattribution, null-not-shared, merge-before-max-wins |
| `village_matching.jsonl` | 9 | maslakh/nabatieh/qantara/aynata/kafra + ambiguous negatives |
| `revision_detection.jsonl` | 5 (new) | preliminary / named-victim / rising toll |

Knowledge-load eval: **31 passed / 0 failed** (was 17).

### B.2 Terminology expansion

- Occupation×status compounds + female role spellings in `casualty_gender.yaml` (ambiguous: مدني/طفل flagged, not auto-mapped).
- Confirmed **الرسالة** (`scout_paramedic`) ≠ **الهيئة الصحية** (`health_organization`).
- Revision orthography (`تنعي`/`الشهيده`) + مراجعة/تصحيح الحصيلة.
- Air-platform nouns on `role_terms.yaml`.

### B.3 Condition IDs 2 / 35 / 36 / 38 / 39 / 45

**Reconfirmed code-only** for routing/SQL/fast-path. Arabic `condition_id_label` glossary rows added for prompts; wired into `tier1_extraction` terminology.

### B.4 Live validation

Report: [`Docs/recon/llm_knowledge_live_validation.md`](llm_knowledge_live_validation.md)

- Model: `qwen2.5:7b`
- Subset: **16** cases (one+ per corpus file; all named B.1 historical-bug refs in `LIVE_BUG_REFS`)
- Result: **11 pass / 1 partial / 4 fail**
- `expected_output` **not** edited to match the model

Open mismatches (see live report for detail):
1. `multi-village-null-not-zero-or-shared` — scope mislabel (roles mostly right)
2. `preliminary-toll-revision`, `named-victim-zahraa-revision`, `preliminary-tally-marker` — revision LLM stage under-specified vs keyword backstop
3. `gendered-occupation-paramedic-in-mixed-toll` — partial (totals OK, male_deaths from مسعف missing)

---

## Test suite

| | Passed | Failed | Errors | Skipped |
|--|-------:|-------:|-------:|--------:|
| Baseline (this prompt start / prior migration) | 665 | 15 | 3 | 11 |
| After Part A+B (knowledge-load + focused gender/revision tests green) | 665 | 15 | 3 | 11 |

**New failures vs baseline:** none. Same 15 failed / 3 errors (env/DB).

---

## Open for manual review

1. Live-validation mismatches above (do not absorb into corpus without decision).
2. Whether to add a dedicated `rules/story_revision_prompt.md` for LLM revision classification (today: backstop-first).
3. Ambiguous gender compounds: مدني شهيد / طفل شهيد — intentionally not auto-mapped.
4. Unrelated WIP still unstaged: `incident_repository.py`, `test_incident_materialization_service.py` (left alone).
