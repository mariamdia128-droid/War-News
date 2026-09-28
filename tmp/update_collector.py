import re

with open("app/sources/services/red_alert_collector.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update village aliases
old_aliases = """    "zibqine": 71122,
    "zebqine": 71122,
}"""
new_aliases = """    "zibqine": 71122,
    "zebqine": 71122,
    "المنصور": 62296,
    "منصور": 62296,
    "كفرتبنيت": 71120,
    "كفر تبنيت": 71120,
    "المنزلة": 71131,
    "منزلة": 71131,
    "القليلة": 62241,
    "قليلة": 62241,
    "بعلول": 52115,
    "baaloul": 52115,
}"""
assert old_aliases in content, "old_aliases not found"
content = content.replace(old_aliases, new_aliases)

# 2. Empty broken map fallbacks
old_fallbacks = """BROKEN_RED_ALERT_MAP_FALLBACKS: dict[tuple[int, int], str] = {
    (7, 26): "Zibdine En-Nabatiyeh زبدين النبطية مسيرة حيطة وحذر",
    (8, 11): "Zibdine En-Nabatiyeh زبدين النبطية مسيرة حيطة وحذر",
    (9, 23): "Borj qalaouiye برج قلويه مسيرة حيطة وحذر",
}

BROKEN_RED_ALERT_MESSAGE_FALLBACKS: dict[int, str] = {
    45675: "فرون صربين الغندورية مسيرة حيطة وحذر",
}"""
new_fallbacks = """BROKEN_RED_ALERT_MAP_FALLBACKS: dict[tuple[int, int], str] = {}
BROKEN_RED_ALERT_MESSAGE_FALLBACKS: dict[int, str] = {}"""
assert old_fallbacks in content, "old_fallbacks not found"
content = content.replace(old_fallbacks, new_fallbacks)

# 3. Add kinetic exclusion keywords and wording variations
old_keywords = """AIR_KEYWORDS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (35, _air_keyword_phrases("Warplane")),
    (
        36,
        _air_keyword_phrases("Drone / recon")
        + (
            # Common Tesseract output from Red Alert drone-map headers.
            "معم سر",
            "معمر سر",
        ),
    ),
    (
        38,
        _air_keyword_phrases("Helicopter")
        + (
            "apache",
            "ah-64",
            # Common Tesseract substitution in Red Alert helicopter headers.
            "كوترية",
        ),
    ),
)"""

new_keywords = """KINETIC_EXCLUSION_KEYWORDS = (
    "قصف جوي",
    "قصف مدفعي",
    "مدفعية",
    "قذائف",
    "قذيفة",
    "صاروخ",
    "صواريخ",
    "انفجار",
    "انفجارات",
    "رشقات نارية",
    "رشقات",
    "تمشيط",
    "اشتباكات",
    "اشتباك",
    "شهداء",
    "شهيد",
    "جرحى",
    "جريح",
    "إصابات",
    "اصابات",
    "حزام ناري",
)

AIR_KEYWORDS: tuple[tuple[int, tuple[str, ...]], ...] = (
    (
        35,
        _air_keyword_phrases("Warplane")
        + (
            "طيران حربي",
            "الطيران الحربي",
            "طائرات حربية",
            "طائرات حربيه",
            "طائرة حربية",
            "طائره حربيه",
            "مقاتلات حربية",
            "مقاتلات حربيه",
            "مقاتلة حربية",
            "مقاتله حربيه",
            "طيران العدو الحربي",
        ),
    ),
    (
        36,
        _air_keyword_phrases("Drone / recon")
        + (
            "طيران استطلاعي",
            "طيران استطلاع",
            "طائرات استطلاع",
            "طائرة استطلاع",
            "طائره استطلاع",
            "طيران مسير",
            "الطيران المسير",
            "طائرات مسيرة",
            "طائرات مسيره",
            "طائرة مسيرة",
            "طائره مسيره",
            "المسير المعادي",
            "مسيرات",
            "درون",
            "drones",
            "drone",
            # Common Tesseract output from Red Alert drone-map headers.
            "معم سر",
            "معمر سر",
        ),
    ),
    (
        38,
        _air_keyword_phrases("Helicopter")
        + (
            "طيران مروحي",
            "الطيران المروحي",
            "طائرات مروحية",
            "طائرة مروحية",
            "طائره مروحيه",
            "مروحية",
            "مروحيات",
            "apache",
            "ah-64",
            "اباتشي",
            "أباتشي",
            # Common Tesseract substitution in Red Alert helicopter headers.
            "كوترية",
        ),
    ),
)"""
assert old_keywords in content, "old_keywords not found"
content = content.replace(old_keywords, new_keywords)

# 4. Update classify_condition
old_classify = """def classify_condition(text: str) -> int | None:
    normalized = normalize_arabic(text)
    if any(normalize_arabic(part) in normalized for part in NON_EVENT_NOTICE_PARTS):
        return None
    if any(normalize_arabic(part) in normalized for part in NON_AIR_DRONE_WORD_PATTERNS):
        return None
    for condition_id, keywords in AIR_KEYWORDS:
        for keyword in keywords:
            normalized_keyword = normalize_arabic(keyword)
            if normalized_keyword not in normalized:
                continue
            if (
                condition_id == 36
                and normalized_keyword in {normalize_arabic(part) for part in BARE_DRONE_KEYWORDS}
                and not any(normalize_arabic(context) in normalized for context in DRONE_CONTEXT_KEYWORDS)
            ):
                continue
            return condition_id
    if (
        "redalert com lb" in normalized
        and (
            normalize_arabic("حيطة") in normalized
            or normalize_arabic("خبطة") in normalized
        )
        and normalize_arabic("حذر") in normalized
    ):
        # Red Alert's map card is a drone/surveillance alert. Explicit
        # warplane/helicopter keywords have already been checked above.
        return 36
    return None"""

new_classify = """def classify_condition(text: str) -> int | None:
    normalized = normalize_arabic(text)
    if any(normalize_arabic(part) in normalized for part in NON_EVENT_NOTICE_PARTS):
        return None
    if any(normalize_arabic(part) in normalized for part in NON_AIR_DRONE_WORD_PATTERNS):
        return None
    if any(normalize_arabic(part) in normalized for part in KINETIC_EXCLUSION_KEYWORDS):
        return None
    if (
        (normalize_arabic("غارة") in normalized or normalize_arabic("غارات") in normalized or normalize_arabic("اغار") in normalized)
        and not (normalize_arabic("غارة وهمية") in normalized or normalize_arabic("غارات وهمية") in normalized or normalize_arabic("وهمية") in normalized)
    ):
        return None
    if (
        normalize_arabic("استهداف") in normalized
        or normalize_arabic("استهدفت") in normalized
        or normalize_arabic("استهدف") in normalized
    ):
        return None

    for condition_id, keywords in AIR_KEYWORDS:
        for keyword in keywords:
            normalized_keyword = normalize_arabic(keyword)
            if normalized_keyword not in normalized:
                continue
            if (
                condition_id == 36
                and normalized_keyword in {normalize_arabic(part) for part in BARE_DRONE_KEYWORDS}
                and not any(normalize_arabic(context) in normalized for context in DRONE_CONTEXT_KEYWORDS)
                and len(normalized.split()) > 4
            ):
                continue
            return condition_id
    if (
        "redalert com lb" in normalized
        and (
            normalize_arabic("حيطة") in normalized
            or normalize_arabic("خبطة") in normalized
        )
        and normalize_arabic("حذر") in normalized
    ):
        # Red Alert's map card is a drone/surveillance alert. Explicit
        # warplane/helicopter keywords have already been checked above.
        return 36
    return None"""
assert old_classify in content, "old_classify not found"
content = content.replace(old_classify, new_classify)

# 5. Allow multiple village matches in match_village without returning None
old_multimatch1 = """    if RED_ZONE_OCR_MARKER in text and len({village.id for village, _alias in alias_matches}) > 1:
        return None"""
new_multimatch1 = """    # If multiple alias matches exist, keep the longest match as primary for match_village
    pass"""
if old_multimatch1 in content:
    content = content.replace(old_multimatch1, new_multimatch1)

old_multimatch2 = """    if RED_ZONE_OCR_MARKER in text and len({village.id for _length, _name, village in matches}) > 1:
        return None"""
new_multimatch2 = """    # Keep the longest match as primary for match_village
    pass"""
if old_multimatch2 in content:
    content = content.replace(old_multimatch2, new_multimatch2)

with open("app/sources/services/red_alert_collector.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Batch 1 updates applied successfully!")
