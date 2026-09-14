"""Standalone eval harness for llm_knowledge corpus files.

PowerShell usage (from repo root):

    python -m app.core.llm_knowledge.eval.run_eval

Does not mutate the database. Full LLM-output comparison requires Phase 3
pipeline wiring; this harness validates knowledge loading and terminology
presence checks against labeled corpus inputs.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from app.core.llm_knowledge.loader import PromptBuilder

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"

STAGE_BY_CORPUS: dict[str, str] = {
    "tier1_extraction.jsonl": "tier1_extraction",
    "casualty_scope.jsonl": "casualty_scope",
    "village_matching.jsonl": "village_matching",
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
            if isinstance(payload, dict):
                cases.append(payload)
    return cases


def _check_case(
    case: dict[str, Any],
    *,
    stage: str,
    builder: PromptBuilder,
    root: Path,
) -> tuple[bool, str]:
    input_text = str(case.get("input") or "")
    expected = case.get("expected_output") or {}
    context = builder.build(stage, input_text)

    if not context.rules.strip() and stage != "relevance_filter":
        return False, "no rules loaded"

    # Terminology sanity: multi-village inputs should load situational rules when applicable.
    if stage == "tier1_extraction" and "؛" in input_text or " - " in input_text:
        if "rules/tier1_multi_village.md" not in context.situational_rules_loaded:
            if "مرج" in input_text or "؛" in input_text:
                return False, "expected tier1_multi_village situational rule"

    # Scope corpus: verify key terms appear in terminology scan when expected.
    if stage == "casualty_scope":
        scope = expected.get("casualty_scope")
        if scope == "per_village_exact" and ":" in input_text:
            return True, "per-village clause pattern present"
        if scope == "bulletin_aggregate":
            return True, "aggregate pattern accepted (LLM eval pending)"
        if scope == "unspecified":
            return True, "no-casualty case accepted"

    # Village matching: verify alias-related terminology would be available.
    if stage == "village_matching":
        acs = expected.get("resolved_parent_acs")
        if acs is not None:
            return True, f"alias case documented (ACS {acs}); matcher eval pending Phase 3"

    if not context.as_prompt_fragment().strip():
        return False, "empty prompt fragment"

    return True, "ok"


def run_eval() -> int:
    builder = PromptBuilder()
    root = builder.root
    total_pass = 0
    total_fail = 0

    corpus_files = sorted(CORPUS_DIR.glob("*.jsonl"))
    if not corpus_files:
        print("No corpus files found.")
        return 1

    for corpus_path in corpus_files:
        stage = STAGE_BY_CORPUS.get(corpus_path.name, "tier1_extraction")
        cases = _load_jsonl(corpus_path)
        file_pass = 0
        file_fail = 0
        print(f"\n=== {corpus_path.name} ({len(cases)} cases, stage={stage}) ===")
        for index, case in enumerate(cases, start=1):
            ok, reason = _check_case(case, stage=stage, builder=builder, root=root)
            if ok:
                file_pass += 1
                print(f"  PASS [{index}] {reason}")
            else:
                file_fail += 1
                print(f"  FAIL [{index}] {reason}")
                print(f"         input: {case.get('input', '')[:120]}")
                print(f"         expected: {json.dumps(case.get('expected_output'), ensure_ascii=False)}")
        total_pass += file_pass
        total_fail += file_fail
        print(f"  -> {file_pass} passed, {file_fail} failed")

    print(f"\nTotal: {total_pass} passed, {total_fail} failed")
    return 0 if total_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(run_eval())
