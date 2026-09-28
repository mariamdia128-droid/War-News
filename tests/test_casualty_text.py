"""Shared Arabic casualty wording helpers (casualty_text)."""

from __future__ import annotations

from app.core.llm_knowledge.loader import terms_by_category
from app.news.services.incident_details.casualty_text import (
    DEATHS,
    INJURIES,
    find_count_mentions,
    find_count_words,
    find_explicit_none,
    find_supporting_mention,
    has_explicit_none,
    has_vague_quantifier,
    is_obituary,
    mentions_named_victim,
    normalize_casualty_text,
    normalize_with_offsets,
    sentences,
    strike_list_number_spans,
    strip_page_header,
)

SHOAIB_HEADER = "صفحة الإعلامي الشهيد علي شعيب :  قصف مدفعي معادٍ استهدف بلدة حولا"


def _words(text: str) -> set[tuple[str, int, str]]:
    return {(m.kind, m.value, m.rule) for m in find_count_words(text)}


# --- normalization ---------------------------------------------------------


def test_normalization_unifies_hamza_and_drops_tashkeel_and_tatweel() -> None:
    assert normalize_casualty_text("إصابةٌ أُولى شهـيدًا") == "اصابه اولي شهيدا"


def test_normalized_offsets_return_verbatim_source_slices() -> None:
    source = "سقوط شهيـدٍ في الغارة"
    normalized = normalize_with_offsets(source)
    start = normalized.text.index("شهيد")
    assert normalized.source_slice(start, start + len("شهيد")) == "شهيـدٍ"[:-1]


# --- page header -----------------------------------------------------------


def test_strip_page_header_removes_shoaib_header() -> None:
    stripped = strip_page_header(SHOAIB_HEADER)
    assert "شعيب" not in stripped
    assert "قصف مدفعي" in stripped


def test_strip_page_header_tolerates_spelling_variants() -> None:
    for variant in (
        "صفحة اللإعلامي الشهيد علي شعيب: غارة",
        "صفحةالإعلامي الشهيدعلي شعيب : غارة",
        "صفحة الإعلاميالشهيد علي شعيب غارة",
        "صفحة الإعلامي الشهـيد علي شعيب: غارة",
    ):
        assert "شعيب" not in strip_page_header(variant), variant


def test_page_header_is_not_a_casualty_mention() -> None:
    assert find_count_mentions(SHOAIB_HEADER) == ()
    assert not mentions_named_victim(SHOAIB_HEADER)


# --- singular / dual / spelled counts --------------------------------------


def test_dual_death_word_counts_two() -> None:
    """31539: «شهيدان في غارة… كفررمان»."""
    text = "وزارة الصحة اللبنانية: شهيدان في غارة إسرائيلية استهدفت دراجة نارية في بلدة كفررمان"
    assert _words(text) == {(DEATHS, 2, "dual")}


def test_dual_and_singular_of_both_types_count_independently() -> None:
    """29191: «النبطية الفوقا: شهيدان وجريحان»; «شهيد وجريحان»."""
    assert _words("النبطية الفوقا: شهيدان وجريحان") == {
        (DEATHS, 2, "dual"),
        (INJURIES, 2, "dual"),
    }
    assert _words("شهيد وجريحان في الغارة") == {
        (DEATHS, 1, "singular"),
        (INJURIES, 2, "dual"),
    }


def test_feminine_and_accusative_forms() -> None:
    assert _words("ارتقاء شهيدتين") == {(DEATHS, 2, "dual")}
    assert _words("سجلت البلدة شهيدا وجريحة") == {
        (DEATHS, 1, "singular"),
        (INJURIES, 1, "singular"),
    }


def test_definite_singular_is_a_named_victim_not_a_count() -> None:
    text = "منزل الشهيد علي معلم"
    assert _words(text) == set()
    assert mentions_named_victim(text)


def test_singular_after_between_or_number_is_not_a_count() -> None:
    """30616: «أكثر من 10 اصابات بين شهيد وجريح» is a mixed total, not 1+1."""
    text = "حصيلة أولية تفيد بوقوع أكثر من 10 اصابات بين شهيد وجريح"
    assert (DEATHS, 1, "singular") not in _words(text)


def test_spelled_out_numbers_next_to_casualty_noun() -> None:
    assert _words("سقوط ثلاثة شهداء وأربع إصابات") == {
        (DEATHS, 3, "spelled_number"),
        (INJURIES, 4, "spelled_number"),
    }
    # 30140: «استشهاد مسعف وإصابة اثنين آخرين» — the verbal noun precedes the number.
    assert _words("استشهاد مسعف وإصابة اثنين آخرين") == {
        (DEATHS, 1, "singular"),
        (INJURIES, 2, "spelled_number"),
    }


def test_spelled_number_not_next_to_casualty_noun_is_ignored() -> None:
    assert _words("ثلاثة غارات على البلدة") == set()


def test_masab_plural_is_not_dual() -> None:
    """«مصابين» is plural only; the yaml no longer lists it as dual."""
    assert "مصابين" not in terms_by_category(
        "terminology/casualty_gender.yaml", "male_injury_dual"
    )
    assert _words("نقل مصابين إلى المستشفى") == set()
    assert _words("مصابان في الغارة") == {(INJURIES, 2, "dual")}


# --- digits bound to casualty nouns ----------------------------------------


def test_digit_binds_to_nearest_casualty_noun() -> None:
    mentions = {(m.kind, m.value) for m in find_count_mentions("شهيد و10 جرحى في الغارة")}
    assert (INJURIES, 10) in mentions
    assert (DEATHS, 10) not in mentions


def test_dates_times_urls_and_parenthesized_numbers_are_not_counts() -> None:
    text = (
        "ملخص بتاريخ ١٣/٩/٢٠٢٦ حتى الساعة ١٢:٠٠ شهداء "
        "https://t.me/x/2 حولا (٢) جرحى"
    )
    assert find_count_mentions(text) == ()


def test_strike_count_list_entries_are_detected_and_not_counts() -> None:
    """32708: per-place strike counts under a raid/demolition heading."""
    text = (
        "الغارات من الطيران الحـربي :\n\n• النبطية الفوقا (١١)\n• كفررمان (٢)\n\n"
        "عمليات التفجير :\n\n• زوطر الشرقية (٢)\n• حولا (٢)\n"
    )
    spans = strike_list_number_spans(text)
    assert any("النبطية الفوقا (١١)" in span for span in spans)
    assert any("حولا (٢)" in span for span in spans)
    assert find_supporting_mention(text, "deaths", 2) is None


def test_supporting_mention_for_demographic_field() -> None:
    text = "4 شهداء و33 جريحا من بينهم 6 أطفال و4 سيدات"
    assert find_supporting_mention(text, "children_injuries", 6) is not None
    assert find_supporting_mention(text, "female_injuries", 4) is not None
    assert find_supporting_mention(text, "injuries", 33) is not None
    assert find_supporting_mention(text, "deaths", 4) is not None
    assert find_supporting_mention(text, "injuries", 6) is None


def test_obfuscated_martyr_word_still_binds_digit() -> None:
    """29321: «4 شهـ.. و20 جريحا» dodges moderation but is still a death count."""
    assert find_supporting_mention("4 شهـ.. و20 جريحا في حصيلة أولية", "deaths", 4)


# --- explicit none / vague / obituary --------------------------------------


def test_explicit_none_phrases() -> None:
    assert has_explicit_none("غارة على منزل دون تسجيل إصابات", INJURIES)
    assert has_explicit_none("من دون تسجيل أي إصابات", INJURIES)
    assert has_explicit_none("لم تسجل إصابات في صفوف المدنيين", INJURIES)
    assert has_explicit_none("دون وقوع ضحايا", DEATHS)
    assert not has_explicit_none("دون تسجيل إصابات", DEATHS)
    assert not has_explicit_none("ووقوع إصابات", INJURIES)
    assert find_explicit_none("استهدفت منزل الشهيد علي معلم دون تسجيل اصابات،", INJURIES) == (
        "دون تسجيل اصابات"
    )


def test_vague_quantifiers() -> None:
    """30496 «وقوع إصابات», 31816 «عشرات الجرحى», «سقوط ضحايا»."""
    assert has_vague_quantifier("وقوع  إصابات في غارة كفررمان", INJURIES)
    assert has_vague_quantifier("عشرات الجرحى، بينهم أطفال ونساء", INJURIES)
    assert has_vague_quantifier("سقوط ضحايا في كفررمان", DEATHS)
    assert has_vague_quantifier("شهيد وعدد من الجرحى", INJURIES)
    assert not has_vague_quantifier("شهيد وعدد من الجرحى", DEATHS)
    assert not has_vague_quantifier("سقوط شهيد", DEATHS)
    assert not has_vague_quantifier("وقوع إصابتين", INJURIES)


def test_obituary_markers() -> None:
    """31831: «النبطية الفوقا تنعى الشهـ.. الشاب حيدر كلاس»."""
    assert is_obituary("النبطية الفوقا تنعى الشهـ..  الشاب حيدر كلاس")
    assert is_obituary("وزير العمل ينعى الشهيدة هبة علي صباح")
    assert not is_obituary("شهيدان في غارة على كفررمان")


def test_sentences_split_on_bullets_and_newlines_not_on_comma() -> None:
    text = "📌 شهيدان وجريح في حي الرويس - النبطية 📌 جريح إثر الغارة، في البقاع"
    parts = sentences(text)
    assert parts[0].startswith("شهيدان")
    assert parts[1] == "جريح إثر الغارة، في البقاع"
    assert sentences("4 شهـ.. و20 جريحا. غارة ثانية") == ["4 شهـ.. و20 جريحا", "غارة ثانية"]


def test_waqu_or_suqut_before_a_count_word_is_still_a_count() -> None:
    """31946: «وقوع إصابتين» is 2 injuries; «سقوط شهيد» is 1 death."""
    assert find_supporting_mention(
        "والمعلومات الأولية تشير إلى وقوع إصابتين", "injuries", 2
    )
    assert find_supporting_mention("سُجل سقوط شهيد في حصيلة غير نهائية", "deaths", 1)


def test_verbal_noun_with_singular_person_is_one() -> None:
    """31492: «استشهاد مسعف في كشافة الرسالة وإصابة 2 آخرين»."""
    text = "استشهاد مسعف في كشافة الرسالة وإصابة 2 آخرين في غارة العدو على سيارة"
    assert find_supporting_mention(text, "deaths", 1).text == "استشهاد مسعف"
    assert find_supporting_mention(text, "male_deaths", 1)
    assert find_supporting_mention(text, "injuries", 2)
    assert find_supporting_mention("إصابة مواطنة بجروح", "female_injuries", 1)
    assert find_supporting_mention("استشهاد المسعف", "deaths", 1) is None


def test_named_victim_with_death_verb_supports_one_but_is_not_a_fill_word() -> None:
    """31703: «الشهيدة إسراء بهجة… إرتقت في غارة عربصاليم»."""
    text = "الشهيدة إسراء بهجة من بلدة جبشيت إرتقت في غارة عربصاليم الأولى"
    assert find_supporting_mention(text, "deaths", 1)
    assert find_supporting_mention(text, "female_deaths", 1)
    assert _words(text) == set()
    # No death verb: a house of a known martyr is not a casualty count.
    assert find_supporting_mention("غارة استهدفت منزل الشهيد علي معلم", "deaths", 1) is None


def test_emoji_glued_to_the_word_does_not_hide_the_count() -> None:
    """31537: «⭕شهيدان على الأقل في اعتداء إسرائيلي… في عربصاليم»."""
    assert find_supporting_mention("⭕شهيدان على الأقل في اعتداء إسرائيلي", "deaths", 2)


def test_event_verb_with_singular_injury_is_one_but_direct_hit_is_not() -> None:
    """28394 «وقوع إصابة بعدما ألقت محلقة قنبلة صوتية», 31203 «و وقوع اصابة»."""
    assert find_supporting_mention("وقوع إصابة بعدما ألقت محلقة قنبلة صوتية", "injuries", 1)
    assert find_supporting_mention("مستهدفاً حي الراهبات في النبطية و وقوع اصابة", "injuries", 1)
    assert find_supporting_mention("وقوع إصابة مباشرة في المبنى", "injuries", 1) is None


def test_recovered_bodies_count_as_deaths() -> None:
    """28576: «إنتشال جثمانَي حسين شكر واحمد روماني»."""
    assert find_supporting_mention(
        "🥀 إنتشال جثمانَي حسين شكر واحمد روماني من منطقة دوحة كفررمان", "deaths", 2
    )


def test_obfuscated_named_victim_with_death_verb_supports_one() -> None:
    """31955: «تزفّ ابنها الشهـ,,, محمد دايخ، الذي ارتقى صباح اليوم»."""
    text = "بلدة جويا تزفّ ابنها الشهـ,,,  محمد دايخ، الذي ارتقى صباح اليوم جراء غارة"
    assert find_supporting_mention(text, "deaths", 1)
