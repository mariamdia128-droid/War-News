"""Reject bulletins whose stated location is explicitly outside Lebanon.

Text similarity alone cannot tell that a non-Lebanon place name is outside the
incident domain when extraction produces a token that also resembles a Lebanese
village. This guard runs before extraction and again before matching.
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
    "قطاع غز.ة",
    "غزة",
    "غز.ة",
    "بيت لاهيا",
    "بيت لا.هيا",
    "مشروع بيت لاهيا",
    "مشروع بيت لا.هيا",
    "رفح",
    "خان يونس",
    # Other explicit non-Lebanon country/location markers requested after the
    # Gaza/Beit Lahia production miss. Keep these concrete, not inferential.
    "سوريا",
    "العراق",
    "اليمن",
    # Jerusalem (routinely used as a Palestine/West Bank dateline)
    "القدس المحتلة",
    "الضفة المحتلة",
)

# Deliberately scoped to explicit location markers from confirmed/reviewed
# misses. Do not turn this into a broad country-name geocoder; regional names
# can appear in Lebanon bulletins as context, and every expansion should be
# tied to a real corpus example per app/core/llm_knowledge/CHANGELOG.md.


def is_non_lebanon_location(text: str | None) -> str | None:
    """Return the matched marker if the text names a clearly non-Lebanon location."""
    if not text:
        return None
    for marker in NON_LEBANON_LOCATION_MARKERS:
        if marker in text:
            return marker
    return None
