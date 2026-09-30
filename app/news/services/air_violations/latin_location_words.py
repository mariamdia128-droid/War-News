from __future__ import annotations

import re
import unicodedata


def normalize_latin_location_token(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    value = re.sub(r"[^a-z]", "", value.casefold())
    return value.replace("ch", "sh")


def latin_location_words(value: str) -> list[str]:
    """Split Latin text into normalized words before any spaces are stripped."""
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return [
        word
        for word in (normalize_latin_location_token(part) for part in re.split(r"[^A-Za-z]+", value))
        if word
    ]


def latin_name_in_words(name_words: list[str], candidate_words: list[str]) -> bool:
    """Match a place name only on whole-word boundaries of the candidate.

    A run of consecutive candidate words matches when it spells the name,
    ignoring spacing ("Kfarkila" vs "kfar kila"), but a name never matches
    inside a longer word. Names shorter than 5 letters must match word for
    word, since a short compact form is too easy to assemble by accident.
    """
    compact_name = "".join(name_words)
    if not compact_name:
        return False
    if len(compact_name) < 5:
        size = len(name_words)
        return any(
            candidate_words[start : start + size] == name_words
            for start in range(len(candidate_words) - size + 1)
        )
    for start in range(len(candidate_words)):
        spelled = ""
        for word in candidate_words[start:]:
            spelled += word
            if len(spelled) >= len(compact_name):
                break
        if spelled == compact_name:
            return True
    return False
