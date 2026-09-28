"""Casualty count backstop: vague quantifiers and missing evidence_span."""

from __future__ import annotations

import logging

from app.llm.dtos import CasualtyCountEvidence, ExtractionCasualties
from app.news.services.incident_details.casualty_count_backstop import (
    apply_casualty_count_backstop,
)


def test_dozens_injured_with_children_mention_is_nulled() -> None:
    """4105/4121-style: عشرات الجرحى بينهم أطفال ونساء must not fabricate counts."""
    text = (
        "عشرات الجرحى، بينهم أطفال ونساء، جراء غارة استهدفت منزلًا خاليًا "
        "في حي سكني ببلدة الرمادية، قضاء صور."
    )
    casualties = ExtractionCasualties(injuries=10, children_injuries=6)
    evidence = [
        CasualtyCountEvidence(field="injuries", evidence_span="عشرات الجرحى"),
        CasualtyCountEvidence(field="children_injuries", evidence_span="بينهم أطفال"),
    ]

    result, kept = apply_casualty_count_backstop(
        text,
        casualties,
        evidence,
        raw_message_id=4105,
    )

    assert result.injuries is None
    assert result.children_injuries is None
    assert kept == []


def test_number_of_martyrs_vague_phrase_is_nulled() -> None:
    """4396-style: عدد من الشهداء must not become a fabricated death count."""
    text = "سقوط عدد من الشهداء من عائلة واحدة في كفررمان"
    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(deaths=4),
        [CasualtyCountEvidence(field="deaths", evidence_span="عدد من الشهداء")],
        raw_message_id=4396,
    )

    assert result.deaths is None
    assert kept == []


def test_number_of_injuries_vague_phrase_stays_null() -> None:
    """4005-style: عدد من الإصابات already null — stays null."""
    text = "لبنان: مراسل الميادين: عدد من الإصابات في غارات إسرائيلية على حي الراهبات"
    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(),
        [],
        raw_message_id=4005,
    )

    assert result == ExtractionCasualties()
    assert kept == []


def test_explicit_digit_counts_are_preserved_with_evidence() -> None:
    text = "4 قتلى و10 جرحى في غارة على البلدة"
    evidence = [
        CasualtyCountEvidence(field="deaths", evidence_span="4 قتلى"),
        CasualtyCountEvidence(field="injuries", evidence_span="10 جرحى"),
    ]

    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(deaths=4, injuries=10),
        evidence,
        raw_message_id=99,
    )

    assert result.deaths == 4
    assert result.injuries == 10
    assert {item.field for item in kept} == {"deaths", "injuries"}


def test_arabic_indic_digit_counts_are_preserved() -> None:
    text = "٤ شهداء و١٠ جرحى"
    evidence = [
        CasualtyCountEvidence(field="deaths", evidence_span="٤ شهداء"),
        CasualtyCountEvidence(field="injuries", evidence_span="١٠ جرحى"),
    ]

    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(deaths=4, injuries=10),
        evidence,
        raw_message_id=100,
    )

    assert result.deaths == 4
    assert result.injuries == 10
    assert len(kept) == 2


def test_explicit_arabic_singular_and_dual_counts_are_preserved() -> None:
    text = "الرمادية: شهيد وجريح، كفرمان: شهيدان"
    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(deaths=2, injuries=1),
        [
            CasualtyCountEvidence(field="deaths", evidence_span="شهيدان"),
            CasualtyCountEvidence(field="injuries", evidence_span="جريح"),
        ],
    )

    assert result.deaths == 2
    assert result.injuries == 1
    assert {item.field for item in kept} == {"deaths", "injuries"}


def test_explicit_arabic_accusative_singular_is_preserved() -> None:
    text = "سجلت البلدة شهيدا وجريحا"
    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(deaths=1, injuries=1),
        [
            CasualtyCountEvidence(field="deaths", evidence_span="شهيدا"),
            CasualtyCountEvidence(field="injuries", evidence_span="جريحا"),
        ],
    )

    assert result.deaths == 1
    assert result.injuries == 1
    assert {item.field for item in kept} == {"deaths", "injuries"}


def test_casualty_digit_must_appear_inside_grounded_evidence_span() -> None:
    text = "البلدة الأولى: 4 جرحى، البلدة الثانية: عشرات الجرحى"
    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(injuries=4),
        [
            CasualtyCountEvidence(
                field="injuries",
                evidence_span="البلدة الثانية: عشرات الجرحى",
            )
        ],
    )

    assert result.injuries is None
    assert kept == []


def test_missing_evidence_span_keeps_count_when_digit_in_full_text() -> None:
    text = "4 قتلى و10 جرحى في غارة على البلدة"

    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(deaths=4, injuries=10),
        [
            CasualtyCountEvidence(field="deaths", evidence_span="4 قتلى"),
            # injuries intentionally missing evidence_span
        ],
        raw_message_id=777,
    )

    assert result.deaths == 4
    assert result.injuries == 10
    assert {item.field for item in kept} == {"deaths", "injuries"}


def test_missing_evidence_span_nulls_when_no_digit_in_source(caplog) -> None:
    text = "عشرات الجرحى في غارة على البلدة"

    with caplog.at_level(logging.WARNING):
        result, kept = apply_casualty_count_backstop(
            text,
            ExtractionCasualties(injuries=10),
            [],
            raw_message_id=778,
        )

    assert result.injuries is None
    assert kept == []
    assert any(
        "casualty_count_backstop nulled field=injuries" in record.message
        and "missing_evidence_span" in record.message
        and "raw_message_id=778" in record.message
        for record in caplog.records
    )


def test_evidence_present_but_digit_absent_is_nulled(caplog) -> None:
    text = "عشرات الجرحى في البلدة"

    with caplog.at_level(logging.WARNING):
        result, kept = apply_casualty_count_backstop(
            text,
            ExtractionCasualties(injuries=10),
            [CasualtyCountEvidence(field="injuries", evidence_span="عشرات الجرحى")],
            raw_message_id=4121,
        )

    assert result.injuries is None
    assert kept == []
    assert any(
        "digit_not_in_source" in record.message and "raw_message_id=4121" in record.message
        for record in caplog.records
    )


def test_dozens_of_injured_and_martyrs_never_becomes_ten() -> None:
    text = "عشرات الجرحى والشهداء جراء الغارة على البلدة"
    evidence = [
        CasualtyCountEvidence(
            field=field,
            evidence_span="عشرات الجرحى والشهداء",
        )
        for field in ("deaths", "injuries", "total_deaths", "total_injuries")
    ]

    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(
            deaths=10,
            injuries=10,
            total_deaths=10,
            total_injuries=10,
        ),
        evidence,
    )

    assert result == ExtractionCasualties()
    assert kept == []


# --- Prompt 1 / Step 4: no "digit anywhere" fallback, strike lists, vague, zero ---


def test_missing_evidence_uses_local_casualty_phrase_as_evidence() -> None:
    text = "4 قتلى و10 جرحى في غارة على البلدة"

    _, kept = apply_casualty_count_backstop(
        text, ExtractionCasualties(injuries=10), [], raw_message_id=1
    )

    assert [(item.field, item.evidence_span) for item in kept] == [("injuries", "10 جرحى")]


def test_date_time_or_url_digit_never_validates_a_count() -> None:
    """Digits in dates, clock times and links used to satisfy the full-text fallback."""
    text = (
        "ملخص الاعتداءات بتاريخ ١٣/٩/٢٠٢٦ حتى الساعة ١٢:٠٠ ووقوع إصابات "
        "https://t.me/channel/2"
    )
    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(injuries=2, deaths=12, total_injuries=13),
        [],
        raw_message_id=2,
    )

    assert result == ExtractionCasualties()
    assert kept == []


def test_strike_count_list_number_is_not_a_death_count(caplog) -> None:
    """32708: «حولا (٢)» under «عمليات التفجير» is a demolition count, not deaths=2."""
    text = (
        "ملخص الاعتداءات التي طالت بلدات و قرى جنوبية\n\n"
        "الغارات من الطيران الحـربي :\n\n• النبطية الفوقا (١١)\n• كفررمان (٢)\n\n"
        "عمليات التفجير :\n\n• زوطر الشرقية (٢)\n• المنصوري (٢٥)\n• حولا (٢)\n"
    )
    with caplog.at_level(logging.WARNING):
        result, kept = apply_casualty_count_backstop(
            text,
            ExtractionCasualties(deaths=2),
            [CasualtyCountEvidence(field="deaths", evidence_span="حولا (٢)")],
            raw_message_id=32708,
        )

    assert result.deaths is None
    assert kept == []
    assert any(
        "strike_count_list" in record.message and "raw_message_id=32708" in record.message
        for record in caplog.records
    )


def test_vague_waqu_isabat_never_becomes_one() -> None:
    """30496: «وقوع إصابات في غارة كفررمان» was stored as injuries=1."""
    result, kept = apply_casualty_count_backstop(
        "وقوع  إصابات في غارة كفررمان",
        ExtractionCasualties(injuries=1, total_injuries=1),
        [],
        raw_message_id=30496,
    )

    assert result == ExtractionCasualties()
    assert kept == []


def test_dozens_injured_without_evidence_never_becomes_ten() -> None:
    """31816: «عشرات الجرحى، بينهم أطفال ونساء» was stored as injuries=10, children=6."""
    text = (
        "◼️ عشرات الجرحى، بينهم أطفال ونساء، جراء غارة استهدفت منزلًا خاليًا "
        "في حي سكني ببلدة الرمادية، قضاء صور."
    )
    result, kept = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(injuries=10, children_injuries=6),
        [],
        raw_message_id=31816,
    )

    assert result == ExtractionCasualties()
    assert kept == []


def test_zero_without_explicit_none_is_nulled(caplog) -> None:
    """31315: «ووقوع إصابات» (injuries asserted!) was stored as injuries=0."""
    with caplog.at_level(logging.WARNING):
        result, kept = apply_casualty_count_backstop(
            "#عاجل | سلسلة غارات تتعرض لها النبطية والنبطية الفوقا ووقوع إصابات",
            ExtractionCasualties(injuries=0),
            [],
            raw_message_id=31315,
        )

    assert result.injuries is None
    assert kept == []
    assert any("zero_without_explicit_none" in r.message for r in caplog.records)


def test_zero_with_explicit_none_phrase_is_kept() -> None:
    text = "غارة على منزل غير مأهول في حي الراهبات دون تسجيل إصابات"
    result, kept = apply_casualty_count_backstop(
        text, ExtractionCasualties(injuries=0), [], raw_message_id=3
    )

    assert result.injuries == 0
    assert [(item.field, item.evidence_span) for item in kept] == [
        ("injuries", "دون تسجيل إصابات")
    ]


def test_explicit_none_for_injuries_does_not_allow_zero_deaths() -> None:
    result, _ = apply_casualty_count_backstop(
        "غارة دون تسجيل إصابات", ExtractionCasualties(deaths=0), []
    )

    assert result.deaths is None


def test_digit_bound_to_the_other_casualty_type_is_rejected() -> None:
    """«شهيد و10 جرحى»: 10 belongs to injuries, never to deaths."""
    result, _ = apply_casualty_count_backstop(
        "شهيد و10 جرحى",
        ExtractionCasualties(deaths=10),
        [CasualtyCountEvidence(field="deaths", evidence_span="شهيد و10 جرحى")],
    )

    assert result.deaths is None


def test_demographic_sub_count_supports_demographic_field_only() -> None:
    text = "4 شهداء و33 جريحا من بينهم 6 أطفال و4 سيدات"
    result, _ = apply_casualty_count_backstop(
        text,
        ExtractionCasualties(
            deaths=4, injuries=33, children_injuries=6, female_injuries=4
        ),
        [
            CasualtyCountEvidence(field="deaths", evidence_span="4 شهداء"),
            CasualtyCountEvidence(field="injuries", evidence_span="33 جريحا"),
            CasualtyCountEvidence(field="children_injuries", evidence_span="6 أطفال"),
            CasualtyCountEvidence(field="female_injuries", evidence_span="4 سيدات"),
        ],
    )

    assert (result.deaths, result.injuries) == (4, 33)
    assert (result.children_injuries, result.female_injuries) == (6, 4)
