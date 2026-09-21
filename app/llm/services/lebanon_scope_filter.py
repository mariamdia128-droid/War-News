"""Reject bulletins whose stated location is explicitly outside Lebanon.

Recon: a bulletin about "منطقة العين، غربي رام الله" (Ramallah, West Bank)
was materialized as a Lebanon incident because the extracted place name
"العين" happens to also be a real Lebanese village, so trigram similarity
matched it with high confidence. Text similarity alone cannot see that the
bulletin itself names a non-Lebanon place; this must be caught before
extraction ever runs.
"""

NON_LEBANON_LOCATION_MARKERS: tuple[str, ...] = (
    # West Bank / Palestine
    "الضفة الغربية",
    "رام الله",
    "رامالله",
    "الأراضي الفلسطينية",
    "فلسطين المحتلة",
    "نابلس",
    "الخليل",
    "بيت لحم",
    "جنين",
    "طولكرم",
    "قلقيلية",
    "أريحا",
    "سلفيت",
    "طوباس",
    # Gaza
    "قطاع غزة",
    "غزة",
    # Jerusalem (routinely used as a Palestine/West Bank dateline)
    "القدس المحتلة",
    "الضفة المحتلة",
)

# Deliberately scoped to Palestine/West Bank/Gaza — the confirmed bug — and
# not to every non-Lebanon country name. A bare country mention ("مصر",
# "الأردن", "اليمن") is common in real Lebanon bulletins covering regional
# diplomacy or comparisons without the incident itself happening there;
# rejecting on those would risk false negatives with no matching confirmed
# case yet. Broaden this list only against a real recurring example, per
# the corpus-first policy in app/core/llm_knowledge/CHANGELOG.md.


def is_non_lebanon_location(text: str | None) -> str | None:
    """Return the matched marker if the text names a clearly non-Lebanon
    location, else None. A plain substring check is deliberately used
    (matching this codebase's other marker-token guards, e.g.
    CONFLICT_ATTRIBUTION_TOKENS) rather than full geocoding, since these
    place names have no legitimate Lebanese homonym worth risking a false
    reject over.
    """
    if not text:
        return None
    for marker in NON_LEBANON_LOCATION_MARKERS:
        if marker in text:
            return marker
    return None
