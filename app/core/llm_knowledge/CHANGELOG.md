# llm_knowledge CHANGELOG

## 2026-09-14 — Phase 2 architecture (additive seed)

Initial structure under `app/core/llm_knowledge/`. Content seeded from Phase 1 recon; call sites not yet wired (Phase 3).

| Fragment source | New location | Status |
|-----------------|--------------|--------|
| `casualty_gender_evidence.py` explicit forms + role nouns | `terminology/casualty_gender.yaml` | seeded |
| `ollama_presence_gate_service.py` org terms | `terminology/org_types.yaml` | seeded |
| `ollama_presence_gate_service.py` location/vehicle/verb terms | `terminology/role_terms.yaml` | seeded |
| `story_revision_backstop.py` + `casualty_transition_backstop.py` markers | `terminology/revision_language_markers.yaml` | seeded |
| `GENERAL_EXTRACTION_PROMPT` core rules | `rules/tier1_core.md` | seeded |
| Multi-village prompt sections | `rules/tier1_multi_village.md` | seeded |
| casualty_scope / merge / transitions | `rules/casualty_merge.md` | seeded |
| `matching_service.py` thresholds + alias notes | `rules/village_matching.md` | seeded |
| Inline prompt examples | `fewshot/*.jsonl` | seeded |
| Recon bug cases | `eval/corpus/*.jsonl` | seeded |
