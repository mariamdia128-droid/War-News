"""Assemble LLM system prompts from llm_knowledge via PromptBuilder."""

from __future__ import annotations

from app.core.llm_knowledge.loader import PromptBuilder, get_prompt_builder


def build_stage_system_prompt(
    stage: str,
    message_text: str,
    *,
    builder: PromptBuilder | None = None,
) -> str:
    """Build a system prompt for *stage* using rules/terminology/fewshot.

    The core rule files for ``tier1_extraction`` and ``combined_tier1`` contain
    the full production prompt text (migrated verbatim from the former inline
    constants / external instruction files). Matched terminology and
    situational multi-village rules are appended when applicable.
    """
    prompt_builder = builder or get_prompt_builder()
    context = prompt_builder.build(stage, message_text)
    fragment = context.as_prompt_fragment().strip()
    if not fragment:
        raise RuntimeError(f"llm_knowledge produced empty prompt for stage={stage}")
    return fragment
