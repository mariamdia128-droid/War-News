from __future__ import annotations

from app.core.text_normalization import normalize_arabic_text


_RAW_CONFLICT_ATTRIBUTION_TOKENS = (
    "غار",
    "قصف",
    "قذيف",
    "صاروخ",
    "صواريخ",
    "مسير",
    "مسيّر",
    "طيران",
    "حربي",
    "مروحي",
    "مدفع",
    "دباب",
    "ميركافا",
    "عدو",
    "إسرائيل",
    "اسرائيل",
    "إسرائيلي",
    "اسرائيلي",
    "احتلال",
    "جيش العدو",
    "استهدف",
    "استهداف",
    "اعتداء",
    "حزام ناري",
    "فوسفور",
    "فوسفوري",
    "حارق",
    "حارقة",
    "تفجير",
    "تفجيرات",
    "مفخخ",
    "عبوه",
    "عبوة",
    "اشتباك",
    "توغل",
    "تمشيط",
    "رشاش",
    "رصاص",
    "معادي",
)

CONFLICT_ATTRIBUTION_TOKENS = tuple(
    dict.fromkeys(normalize_arabic_text(token) for token in _RAW_CONFLICT_ATTRIBUTION_TOKENS)
)


def has_conflict_attribution_text(text: str) -> bool:
    normalized = normalize_arabic_text(text or "")
    return any(token in normalized for token in CONFLICT_ATTRIBUTION_TOKENS)
