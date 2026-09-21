from __future__ import annotations

import re

from app.core.text_normalization import normalize_arabic_text, normalize_english_text
from app.llm.dtos import ClassificationResultDTO, ClassificationVerdict

GUARDRAIL_BACKEND = "rule_guardrail"

PALESTINE_ONLY_REASON = "Rejected: event is scoped to Palestine/Gaza/Ramallah, not Lebanon."
ORDINARY_FIRE_REASON = (
    "Rejected: ordinary fire/property damage without Israeli, war, military, or security context."
)

_PALESTINE_TERMS_EN = (
    "palestine",
    "gaza",
    "ramallah",
    "west bank",
    "nablus",
    "jenin",
    "khan younis",
    "rafah",
)
_PALESTINE_TERMS_AR = (
    "\u0641\u0644\u0633\u0637\u064a\u0646",
    "\u063a\u0632\u0629",
    "\u0631\u0627\u0645 \u0627\u0644\u0644\u0647",
    "\u0631\u0627\u0645\u0627\u0644\u0644\u0647",
    "\u0627\u0644\u0636\u0641\u0629 \u0627\u0644\u063a\u0631\u0628\u064a\u0629",
    "\u0646\u0627\u0628\u0644\u0633",
    "\u062c\u0646\u064a\u0646",
    "\u062e\u0627\u0646 \u064a\u0648\u0646\u0633",
    "\u0631\u0641\u062d",
)
_LEBANON_TERMS_EN = ("lebanon", "lebanese")
_LEBANON_TERMS_AR = ("\u0644\u0628\u0646\u0627\u0646", "\u0644\u0628\u0646\u0627\u0646\u064a")

_FIRE_TERMS_EN = (
    "fire",
    "burn",
    "burned",
    "burning",
    "blaze",
    "property damage",
    "properties",
    "house fire",
    "car fire",
    "electrical fault",
    "short circuit",
)
_FIRE_TERMS_AR = (
    "\u062d\u0631\u064a\u0642",
    "\u0627\u062d\u062a\u0631\u0627\u0642",
    "\u0627\u062d\u062a\u0631\u0642",
    "\u062d\u0631\u0627\u0626\u0642",
    "\u0645\u0645\u062a\u0644\u0643\u0627\u062a",
    "\u0645\u0646\u0632\u0644",
    "\u0633\u064a\u0627\u0631\u0629",
    "\u0645\u0627\u0633 \u0643\u0647\u0631\u0628\u0627\u0626\u064a",
)

_WAR_CONTEXT_EN = (
    "israel",
    "israeli",
    "idf",
    "enemy",
    "hostile",
    "war",
    "military",
    "security",
    "strike",
    "airstrike",
    "shelling",
    "bombardment",
    "missile",
    "rocket",
    "drone",
    "raid",
    "targeted",
)
_WAR_CONTEXT_AR = (
    "\u0627\u0633\u0631\u0627\u0626\u064a\u0644",
    "\u0627\u0633\u0631\u0627\u0626\u064a\u0644\u064a",
    "\u0627\u0644\u0639\u062f\u0648",
    "\u062d\u0631\u0628",
    "\u062d\u0631\u0628\u064a",
    "\u0627\u0645\u0646\u064a",
    "\u0627\u0645\u0646\u064a\u0629",
    "\u0639\u0633\u0643\u0631\u064a",
    "\u063a\u0627\u0631\u0629",
    "\u063a\u0627\u0631\u0627\u062a",
    "\u0642\u0635\u0641",
    "\u0627\u0633\u062a\u0647\u062f\u0627\u0641",
    "\u0627\u0633\u062a\u0647\u062f\u0641",
    "\u0635\u0627\u0631\u0648\u062e",
    "\u0635\u0648\u0627\u0631\u064a\u062e",
    "\u0645\u0633\u064a\u0631\u0629",
)


def _contains_any(value: str, terms: tuple[str, ...]) -> bool:
    return any(term in value for term in terms)


def _contains_english_term(value: str, terms: tuple[str, ...]) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", value) for term in terms)


def _normalized(text: str | None) -> tuple[str, str]:
    value = text or ""
    return normalize_english_text(value), normalize_arabic_text(value)


def relevance_guardrail_result(
    raw_message_id: int,
    text: str | None,
) -> ClassificationResultDTO | None:
    english, arabic = _normalized(text)

    mentions_palestine = _contains_english_term(
        english, _PALESTINE_TERMS_EN
    ) or _contains_any(arabic, _PALESTINE_TERMS_AR)
    mentions_lebanon = _contains_english_term(
        english, _LEBANON_TERMS_EN
    ) or _contains_any(arabic, _LEBANON_TERMS_AR)
    if mentions_palestine and not mentions_lebanon:
        return _not_relevant(raw_message_id, PALESTINE_ONLY_REASON)

    mentions_fire = _contains_english_term(
        english, _FIRE_TERMS_EN
    ) or _contains_any(arabic, _FIRE_TERMS_AR)
    mentions_war_context = _contains_english_term(
        english, _WAR_CONTEXT_EN
    ) or _contains_any(arabic, _WAR_CONTEXT_AR)
    if mentions_fire and not mentions_war_context:
        return _not_relevant(raw_message_id, ORDINARY_FIRE_REASON)

    return None


def apply_relevance_guardrails(
    message,
    result: ClassificationResultDTO,
) -> ClassificationResultDTO:
    guardrail = relevance_guardrail_result(
        raw_message_id=result.raw_message_id,
        text=getattr(message, "raw_text", None),
    )
    return guardrail or result


def _not_relevant(raw_message_id: int, reason: str) -> ClassificationResultDTO:
    return ClassificationResultDTO(
        raw_message_id=raw_message_id,
        verdict=ClassificationVerdict.not_relevant,
        confidence=1.0,
        reasoning=reason,
        backend=GUARDRAIL_BACKEND,
    )
