"""Deterministic fill of bare singular/dual casualty words the LLM left null."""

from __future__ import annotations

import logging

from app.llm.dtos import CasualtyCountEvidence, ExtractionCasualties
from app.news.services.incident_details.casualty_count_fill import (
    fill_counts_from_count_words,
)


def _fill(text: str, targets: list[str], casualties: ExtractionCasualties | None = None):
    return fill_counts_from_count_words(
        text,
        casualties or ExtractionCasualties(),
        [],
        target_villages=targets,
        raw_message_id=1,
    )


def test_dual_death_single_village_fills_two_with_evidence(caplog) -> None:
    """31539: «شهيدان في غارة إسرائيلية… في بلدة كفررمان» → deaths=2."""
    text = (
        "وزارة الصحة اللبنانية: شهيدان في غارة إسرائيلية استهدفت دراجة نارية "
        "في بلدة كفررمان جنوبي #لبنان.\nT.me/mehwaralmokawma"
    )
    with caplog.at_level(logging.INFO):
        result, evidence = _fill(text, ["كفررمان"])

    assert result.deaths == 2
    assert result.total_deaths == 2
    assert result.injuries is None
    assert {(item.field, item.evidence_span) for item in evidence} == {
        ("deaths", "شهيدان"),
        ("total_deaths", "شهيدان"),
    }
    assert all(item.evidence_span in text for item in evidence)
    assert any(
        "casualty_count_fill filled field=deaths value=2 rule=dual" in record.message
        and "raw_message_id=1" in record.message
        for record in caplog.records
    )


def test_dual_death_with_later_plural_mention_still_fills() -> None:
    """30335: «شهيدان جراء غارة… في كفررمان… سقوط شهداء»."""
    text = (
        "⚫ شهيدان جراء غارة معادية على دراجة نارية في كفررمان يستمر العدو في "
        "التصعيد العسكري جنوبي لبنان، حيث قام اليوم باستهداف دراجة نارية مما "
        "أسفر عن سقوط شهداء"
    )
    result, _ = _fill(text, ["كفررمان"])

    assert result.deaths == 2


def test_multi_village_bulletin_is_never_filled() -> None:
    """29191: «النبطية الفوقا: شهيدان وجريحان» inside a multi-village bulletin."""
    text = (
        "- النبطية الفوقا: شهيدان وجريحان\n"
        "- النبطية- حي الراهبات: 8 جرحى من بينهم سيدة وطفلة\n"
        "- عربصاليم: شهيدتان و6  جرحى من بينهم طفلتان"
    )
    result, evidence = _fill(text, ["النبطية الفوقا", "النبطية", "عربصاليم"])

    assert result == ExtractionCasualties()
    assert evidence == []


def test_singular_death_fills_and_vague_injuries_stay_null() -> None:
    """31495: «شهيد وعدد من الجرحى… في الرمادية» → deaths=1, injuries null."""
    text = (
        "شهيد وعدد من الجرحى في حصيلة غير نهائية للغارة على منزل في الرمادية "
        "nna-leb.gov.lb/ar/news/short… Link شهيد وعدد من الجرحى في حصيلة غير "
        "نهائية للغارة على منزل في الرمادية"
    )
    result, _ = _fill(text, ["الرمادية"])

    assert result.deaths == 1
    assert result.injuries is None
    assert result.total_injuries is None


def test_singular_and_dual_of_different_types_fill_independently() -> None:
    result, _ = _fill("شهيد وجريحان في غارة على بلدة ياطر", ["ياطر"])

    assert (result.deaths, result.injuries) == (1, 2)


def test_obituary_line_is_not_filled() -> None:
    """31831-style: mourning a named martyr is not a new casualty count."""
    text = "النبطية الفوقا تنعى شهيد الواجب الشاب حيدر كلاس الذي ارتقى إثر الغارة"
    result, _ = _fill(text, ["النبطية الفوقا"])

    assert result == ExtractionCasualties()


def test_named_victim_sentence_is_not_filled() -> None:
    text = "غارة معادية استهدفت منزل الشهيد علي معلم في كفررمان"
    result, _ = _fill(text, ["كفررمان"])

    assert result.deaths is None


def test_page_header_only_is_not_filled() -> None:
    text = "صفحة الإعلامي الشهيد علي شعيب :  قصف مدفعي معادٍ استهدف بلدة حولا"
    result, _ = _fill(text, ["حولا"])

    assert result == ExtractionCasualties()


def test_explicit_none_blocks_fill_for_that_type() -> None:
    text = "شهيد في غارة على منزل في بلدة ياطر دون تسجيل إصابات أخرى"
    result, _ = _fill(text, ["ياطر"])

    assert result.deaths == 1
    assert result.injuries is None


def test_word_outside_the_target_sentence_is_not_filled() -> None:
    text = "غارة على بلدة ياطر.\nوفي سياق آخر شهيدان في غزة"
    result, _ = _fill(text, ["ياطر"])

    assert result.deaths is None


def test_existing_llm_value_is_never_overwritten() -> None:
    evidence = [CasualtyCountEvidence(field="deaths", evidence_span="3 شهداء")]
    result, kept = fill_counts_from_count_words(
        "3 شهداء وشهيدان في ياطر",
        ExtractionCasualties(deaths=3),
        evidence,
        target_villages=["ياطر"],
    )

    assert result.deaths == 3
    assert kept == evidence


def test_dropped_digit_count_makes_the_type_ambiguous() -> None:
    """«10 اصابات بين شهيد وجريح» — the LLM dropped a digit count; don't guess."""
    text = "استهداف مبنى في كفررمان وحصيلة تفيد بوقوع 10 اصابات بين شهيد وجريح"
    result, _ = _fill(text, ["كفررمان"])

    assert result == ExtractionCasualties()


def test_conflicting_count_words_are_not_filled() -> None:
    text = "شهيد في غارة على ياطر. شهيدان في غارة ثانية على ياطر"
    result, _ = _fill(text, ["ياطر"])

    assert result.deaths is None


def test_spelled_out_number_fills() -> None:
    result, evidence = _fill("سقوط ثلاثة شهداء في غارة على بلدة ياطر", ["ياطر"])

    assert result.deaths == 3
    assert evidence[0].evidence_span == "ثلاثة شهداء"
