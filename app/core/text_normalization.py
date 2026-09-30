import re
import string

from sqlalchemy import func
from sqlalchemy.sql.elements import ColumnElement

ARABIC_DIACRITICS_RE = re.compile(r"[\u064b-\u0652\u0640]")
MULTIPLE_SPACES_RE = re.compile(r"\s+")
ARABIC_EDGE_PUNCTUATION = "،.؛!؟\"'"
ENGLISH_EDGE_PUNCTUATION = string.punctuation + "،؛؟"
ARABIC_ALEF_VARIANTS = "أإآٱة"
ARABIC_NORMALIZED_VARIANTS = "ااااه"


def normalize_arabic_text(text: str, *, compact: bool = False) -> str:
    """Normalize Arabic spelling for matching without changing stored text.

    ``compact`` is intended for village-name comparison keys, where spaces in
    names are not semantically meaningful. Condition matching keeps word
    boundaries for pg_trgm word similarity.
    """
    normalized = ARABIC_DIACRITICS_RE.sub("", text)
    normalized = normalized.translate(
        str.maketrans(ARABIC_ALEF_VARIANTS, ARABIC_NORMALIZED_VARIANTS)
    )
    normalized = normalized.replace("ى", "ي")
    normalized = normalized.strip().strip(ARABIC_EDGE_PUNCTUATION)
    normalized = MULTIPLE_SPACES_RE.sub(" ", normalized).strip()
    if compact:
        return normalized.replace(" ", "")
    return normalized


# Definite article "ال" at the start of a word, only when 3+ letters follow so a
# short stem is never reduced to nothing. Applied to every word because village
# names carry it mid-name too ("عرب الصاليم" vs the reference "عرب صاليم").
_DEFINITE_ARTICLE_RE = re.compile(r"(^| )ال(?=\S{3,})")
_DEFINITE_ARTICLE_SQL = r"(^| )ال(?=[^ ]{3,})"


def village_match_key(text: str, *, compact: bool = False) -> str:
    """Return the village-name comparison key.

    The existing Arabic folds plus removal of the definite article, so
    ``الرمادية`` and ``رمادية`` produce the same key. It must be applied to BOTH
    the incoming mention and every reference name (ACS, reference, alias) so the
    two sides go through identical steps. Reference names that collide after
    this fold are reported by ``scripts/report_village_key_collisions.py``
    rather than merged.
    """
    key = _DEFINITE_ARTICLE_RE.sub(r"\1", normalize_arabic_text(text or ""))
    return key.replace(" ", "") if compact else key


def village_match_key_sql(
    column: ColumnElement[str],
    *,
    compact: bool = False,
) -> ColumnElement[str]:
    """PostgreSQL equivalent of :func:`village_match_key`."""
    key = func.regexp_replace(
        normalize_arabic_sql(column), _DEFINITE_ARTICLE_SQL, r"\1", "g"
    )
    return func.replace(key, " ", "") if compact else key


def normalize_english_text(text: str) -> str:
    normalized = text.lower().strip().strip(ENGLISH_EDGE_PUNCTUATION)
    return MULTIPLE_SPACES_RE.sub(" ", normalized).strip()


def normalize_arabic_sql(
    column: ColumnElement[str],
    *,
    compact: bool = False,
) -> ColumnElement[str]:
    """Build the PostgreSQL equivalent of :func:`normalize_arabic_text`."""
    without_diacritics = func.regexp_replace(
        column,
        "[\u064b-\u0652\u0640]",
        "",
        "g",
    )
    normalized_letters = func.translate(
        without_diacritics,
        ARABIC_ALEF_VARIANTS,
        ARABIC_NORMALIZED_VARIANTS,
    )
    normalized_letters = func.replace(normalized_letters, "ى", "ي")
    without_edge_punctuation = func.btrim(
        func.btrim(normalized_letters),
        ARABIC_EDGE_PUNCTUATION,
    )
    normalized = func.btrim(
        func.regexp_replace(without_edge_punctuation, r"\s+", " ", "g")
    )
    if compact:
        return func.replace(normalized, " ", "")
    return normalized
