from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.llm.services.tier1_segmenter import split_segments

_STUDY_DIR = Path(__file__).resolve().parents[1] / "outputs" / "accuracy_study_import"


def _load_study() -> list[tuple[dict, dict]]:
    raw = json.loads((_STUDY_DIR / "synthetic_raw.json").read_text(encoding="utf-8"))
    truth = {
        row["row_id"]: row
        for row in json.loads((_STUDY_DIR / "ground_truth.json").read_text(encoding="utf-8"))
    }
    return [(row, truth[row["row_id"]]) for row in raw]


_STUDY = _load_study()


def _assert_covers(text: str) -> list:
    segments = split_segments(text)
    assert segments, "at least one segment"
    assert "".join(segment.raw for segment in segments) == text
    assert segments[0].start == 0
    assert segments[-1].end == len(text)
    for left, right in zip(segments, segments[1:]):
        assert left.end == right.start
    assert [segment.index for segment in segments] == list(range(len(segments)))
    return segments


@pytest.mark.parametrize(
    ("row", "truth"),
    _STUDY,
    ids=[f"{truth['row_id']}-{truth['category']}" for _, truth in _STUDY],
)
def test_synthetic_study_segment_counts(row: dict, truth: dict) -> None:
    segments = _assert_covers(row["raw_text"])
    category = truth["category"]
    if category == "multi_village_exact":
        # One item per village, each with its own toll.
        assert len(segments) == truth["village_count"]
        for segment in segments:
            assert segment.text
    else:
        # single_village(_revision), irrelevant and bulletin_aggregate_* stay
        # one segment: a one-line list of villages with one total is one item.
        assert len(segments) == 1


def test_synthetic_multi_village_segments_carry_their_own_village() -> None:
    for row, truth in _STUDY:
        if truth["category"] != "multi_village_exact":
            continue
        villages = [name.strip() for name in truth["villages_mentioned"].split(";")]
        segments = split_segments(row["raw_text"])
        for village, segment in zip(villages, segments, strict=True):
            assert village in segment.text
            others = [other for other in villages if other != village]
            assert not any(f"بلدة {other}" in segment.text for other in others)


# Real-style bulletins (written for these tests, shapes seen in Telegram feeds).
REAL_STYLE_CASES: list[tuple[str, str, int]] = [
    (
        "numbered_list",
        "حصيلة اعتداءات اليوم:\n"
        "1- غارة من مسيرة استهدفت سيارة في بلدة كفرا أدت إلى استشهاد مواطن.\n"
        "2- قصف مدفعي على أطراف بلدة شبعا دون إصابات.\n"
        "3- غارة جوية على منزل في بلدة عيترون أسفرت عن جريحين.",
        3,
    ),
    (
        "arabic_indic_numbered",
        "٧. غارة على بلدة الخيام أدت إلى سقوط شهيد\n"
        "٨. قصف مدفعي استهدف وادي السلوقي",
        2,
    ),
    (
        "bullet_strike_count_list",
        "الغارات من الطيران الحربي:\n• النبطية الفوقا (١١)\n• حولا (٢)\n• ميس الجبل (٣)",
        3,
    ),
    (
        "repeated_emoji_headlines",
        "🔴 غارة من مسيرة معادية على دراجة نارية في بلدة الناقورة\n"
        "🔴 قصف مدفعي يستهدف أطراف بلدة الضهيرة\n"
        "🔴 استشهاد مواطن متأثراً بجروحه في بلدة بنت جبيل",
        3,
    ),
    (
        "repeated_breaking_word",
        "عاجل: غارة إسرائيلية على بلدة طيردبا\nعاجل: مسيرة تستهدف سيارة في بلدة المنصوري",
        2,
    ),
    (
        "blank_line_blocks_with_footer",
        "غارة من مسيرة على سيارة في بلدة عيتا الشعب أدت إلى استشهاد شخصين.\n\n"
        "قصف مدفعي على بلدة رامية أسفر عن إصابة مواطن بجروح.\n\n"
        "المصدر: الوكالة الوطنية للإعلام",
        2,
    ),
    (
        "single_news_hashtag_footer",
        "استهدفت غارة إسرائيلية منزلاً في بلدة ياطر ما أدى إلى استشهاد 3 أشخاص.\n\n#لبنان #الجنوب",
        1,
    ),
    (
        "one_line_six_villages_one_total",
        "شن الطيران الحربي غارات على بلدات الخيام، كفركلا، حولا، مركبا، عديسة والطيبة "
        "ما أدى إلى سقوط 4 شهداء و9 جرحى في حصيلة إجمالية.",
        1,
    ),
    (
        "connector_continues_same_item",
        "غارة من مسيرة على سيارة في بلدة برج قلاويه أدت إلى استشهاد شخص. "
        "كما أصيب 3 آخرون بجروح نقلوا إلى المستشفى.",
        1,
    ),
    (
        "connector_same_village_no_new_event",
        "قصف مدفعي على أطراف بلدة الخيام. كما طال القصف حي المسلخ في بلدة الخيام.",
        1,
    ),
    (
        "connector_another_strike",
        "غارة على منزل في بلدة كفررمان أدت إلى 8 شهداء. "
        "كما غارة أخرى على البلدة نفسها أسفرت عن جريح.",
        2,
    ),
    (
        "connector_new_village_context_phrase",
        "استهدفت مسيرة دراجة نارية في بلدة القليلة. "
        "وفي سياق متصل، استهدف قصف مدفعي بلدة زبقين وأطرافها.",
        2,
    ),
    (
        "fima_connector_new_village",
        "قصف مدفعي على بلدة شبعا أدى إلى إصابة 3 أشخاص. "
        "فيما غارة أخرى في بلدة الخردلي لم تسفر عن إصابات.",
        2,
    ),
    (
        "connector_after_comma_does_not_split",
        "استهدفت غارة بلدة الخيام، كما طالت بلدة كفركلا، ما أدى إلى سقوط 3 شهداء.",
        1,
    ),
]


@pytest.mark.parametrize(
    ("text", "expected"),
    [(text, expected) for _, text, expected in REAL_STYLE_CASES],
    ids=[name for name, _, _ in REAL_STYLE_CASES],
)
def test_real_style_bulletins(text: str, expected: int) -> None:
    segments = _assert_covers(text)
    assert len(segments) == expected, [segment.text for segment in segments]


def test_list_header_is_context_for_every_item() -> None:
    text = "الغارات من الطيران الحربي:\n• النبطية الفوقا (١١)\n• حولا (٢)"
    segments = split_segments(text)
    assert [segment.header for segment in segments] == ["الغارات من الطيران الحربي:"] * 2
    assert segments[1].text == "• حولا (٢)"


def test_footer_is_merged_into_previous_item() -> None:
    text = (
        "غارة على بلدة رامية أدت إلى استشهاد مواطن.\n\n"
        "قصف على بلدة عيتا الشعب أسفر عن جريح.\n\n"
        "المصدر: الوكالة الوطنية للإعلام"
    )
    segments = split_segments(text)
    assert segments[-1].text.endswith("المصدر: الوكالة الوطنية للإعلام")
    assert segments[-1].text.startswith("قصف على بلدة عيتا الشعب")


@pytest.mark.parametrize("text", ["", "   ", "\n\n", "نص بلا حدث"])
def test_empty_or_eventless_text_is_one_segment(text: str) -> None:
    segments = _assert_covers(text)
    assert len(segments) == 1
