from __future__ import annotations

import re

from app.core.text_normalization import normalize_arabic_text
from app.llm.dtos import ExtractionCasualties, ExtractionResult, ExtractionSubEvent


_ARABIC_LETTER = r"\u0600-\u06ff"


def _standalone(word: str) -> re.Pattern[str]:
    """Match *word* as a standalone token, allowing optional و / ال prefixes.

    The definite article ``ال`` is explicitly permitted so forms like
    ``الشهيدة`` match. Any other preceding Arabic letter still rejects the
    match, which avoids mid-word false positives.
    """
    return re.compile(
        rf"(?<![{_ARABIC_LETTER}])(?:و)?(?:ال)?(?:{word})(?![{_ARABIC_LETTER}])"
    )


_EXPLICIT_FORMS: dict[str, tuple[tuple[int, re.Pattern[str]], ...]] = {
    "male_deaths": (
        (1, _standalone("شهيد")),
        (2, _standalone("شهيدان|شهيدين")),
    ),
    "female_deaths": (
        (1, _standalone("شهيدة")),
        (2, _standalone("شهيدتان|شهيدتين")),
    ),
    "male_injuries": (
        (1, _standalone("جريح")),
        (1, _standalone("مصاب")),
        (2, _standalone("جريحان|جريحين")),
        (2, _standalone("مصابان|مصابين")),
    ),
    "female_injuries": (
        (1, _standalone("جريحة")),
        (1, _standalone("مصابة")),
        (2, _standalone("جريحتان|جريحتين")),
        (2, _standalone("مصابتان|مصابتين")),
    ),
}

_COUNTED_PLURALS: dict[str, tuple[str, ...]] = {
    "male_deaths": ("شهداء",),
    "female_deaths": ("شهيدات",),
    "male_injuries": ("جرحى", "مصابون", "مصابين"),
    "female_injuries": ("جريحات", "مصابات"),
}


def _arabic_indic_number(value: int) -> str:
    return str(value).translate(str.maketrans("0123456789", "٠١٢٣٤٥٦٧٨٩"))


def _has_counted_plural(text: str, *, count: int, words: tuple[str, ...]) -> bool:
    numbers = rf"(?:{count}|{_arabic_indic_number(count)})"
    for word in words:
        if re.search(rf"{numbers}\s*{re.escape(word)}", text) or re.search(
            rf"{re.escape(word)}\s*{numbers}",
            text,
        ):
            return True
    return False


def apply_explicit_arabic_gender_evidence(
    text: str,
    casualties: ExtractionCasualties,
) -> ExtractionCasualties:
    """Fill gender only when an unambiguous Arabic singular/dual form covers the total."""
    values = casualties.model_dump(mode="python")
    for outcome, reported_key, total_key in (
        ("deaths", "deaths", "total_deaths"),
        ("injuries", "injuries", "total_injuries"),
    ):
        total = values.get(total_key) or values.get(reported_key)
        if not isinstance(total, int) or total <= 0:
            continue
        male_key = f"male_{outcome}"
        female_key = f"female_{outcome}"
        if total <= 2:
            male_explicit = any(
                count == total and pattern.search(text)
                for count, pattern in _EXPLICIT_FORMS[male_key]
            )
            female_explicit = any(
                count == total and pattern.search(text)
                for count, pattern in _EXPLICIT_FORMS[female_key]
            )
        else:
            # Masculine Arabic plurals can represent a mixed-gender group, so
            # they do not prove that every casualty is male. Feminine plurals
            # are explicit and can safely cover the reported total.
            male_explicit = False
            female_explicit = _has_counted_plural(
                text,
                count=total,
                words=_COUNTED_PLURALS[female_key],
            )
        if male_explicit == female_explicit:
            continue
        child_count = values.get(f"children_{outcome}")
        adult_count = total - child_count if isinstance(child_count, int) else total
        confirmed_count = adult_count if adult_count > 0 else None
        if male_explicit:
            values[male_key] = confirmed_count
            values[female_key] = None
        else:
            values[female_key] = confirmed_count
            values[male_key] = None
    return ExtractionCasualties.model_validate(values)


_MALE_ROLE_NOUNS = (
    "مسعف",
    "جندي",
    "عنصر",
    "موظف",
    "شرطي",
    "اطفائي",
    "ممرض",
    "صحافي",
    "صحفي",
    "اعلامي",
)
_FEMALE_ROLE_NOUNS = (
    "مسعفه",
    "موظفه",
    "ممرضه",
    "شرطيه",
    "صحافيه",
    "صحفيه",
    "اعلاميه",
)


def _role_alternation(roles: tuple[str, ...]) -> str:
    return "|".join(re.escape(role) for role in roles)


_MALE_OCCUPATION_DEATH = re.compile(
    rf"(?:شهيد|استشهاد)\s+(?:ال)?(?:{_role_alternation(_MALE_ROLE_NOUNS)})"
    rf"(?![{_ARABIC_LETTER}])"
)
_FEMALE_OCCUPATION_DEATH = re.compile(
    rf"(?:شهيده|استشهاد)\s+(?:ال)?(?:{_role_alternation(_FEMALE_ROLE_NOUNS)})"
    rf"(?![{_ARABIC_LETTER}])"
)


def apply_gendered_occupation_casualty_evidence(
    text: str,
    casualties: ExtractionCasualties,
) -> ExtractionCasualties:
    """Fill gender from unambiguous occupation grammar, without covering the total.

    ``شهيد مسعف`` / ``استشهاد مسعف`` increment ``male_deaths`` even when the
    bulletin also reports a larger mixed toll. Existing gender fields are left
    unchanged.
    """
    normalized = normalize_arabic_text(text or "")
    if not normalized:
        return casualties
    values = casualties.model_dump(mode="python")
    female_hits = len(_FEMALE_OCCUPATION_DEATH.findall(normalized))
    male_hits = len(_MALE_OCCUPATION_DEATH.findall(normalized))
    if female_hits and values.get("female_deaths") is None:
        values["female_deaths"] = female_hits
    if male_hits and values.get("male_deaths") is None:
        values["male_deaths"] = male_hits
    return ExtractionCasualties.model_validate(values)


def apply_casualty_gender_backstops(
    text: str,
    result: ExtractionResult,
) -> ExtractionResult:
    """Apply explicit-form and occupation gender backstops to root and sub-events."""
    root = apply_gendered_occupation_casualty_evidence(
        text,
        apply_explicit_arabic_gender_evidence(text, result.casualties),
    )
    sub_events: list[ExtractionSubEvent] = []
    for sub_event in result.sub_events:
        span = sub_event.evidence_span or text
        sub_events.append(
            sub_event.model_copy(
                update={
                    "casualties": apply_gendered_occupation_casualty_evidence(
                        span,
                        apply_explicit_arabic_gender_evidence(
                            span,
                            sub_event.casualties,
                        ),
                    )
                }
            )
        )
    return result.model_copy(update={"casualties": root, "sub_events": sub_events})
