import os
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, delete as sa_delete, func, select
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session

import app.accounts.models  # noqa: F401
import app.logs.models  # noqa: F401
from app.news.dtos import AirViolationListParams, MatchResultDTO, MatchResultStatus, VillageMatchResult
from app.news.models import AirViolation, Condition, MessageStatus, RawMessage, Village
from app.news.repositories.air_violation_repository import (
    AirViolationRepository,
    air_violation_caza_labels,
    air_violation_caza_window_hours,
    air_violation_news_text,
    as_beirut_datetime,
    clean_air_violation_news,
)
from app.sources.models import Source, SourceType


def test_air_violation_converts_telegram_utc_time_to_beirut() -> None:
    occurred_at = datetime(2026, 8, 20, 8, 55, tzinfo=timezone.utc)

    local = as_beirut_datetime(occurred_at)

    assert local.date() == date(2026, 8, 20)
    assert local.time().replace(tzinfo=None) == datetime(2026, 8, 20, 11, 55).time()


def test_image_ocr_news_is_replaced_with_clean_summary() -> None:
    message = type("Message", (), {
        "raw_payload": {"ocr_text": "garbled"},
        "raw_text": "Nabatieh مسيرة حيطة وحذر OCR garbage",
    })()
    village = type("Village", (), {"caza_ar": "النبطية", "caza_en": "Nabatiye"})()
    condition = type("Condition", (), {"action_ar": "طيران استطلاعي"})()

    assert air_violation_news_text(message, village, condition) == (
        "طيران استطلاعي في قضاء النبطية - حيطة وحذر"
    )


def test_written_news_removes_decorative_symbol_lines_but_keeps_text() -> None:
    value = "🚫\nإطباق جوي واسع\n⛔️\nأقصى درجات الحيطة والحذر\n⛔️"

    assert clean_air_violation_news(value) == (
        "إطباق جوي واسع\nأقصى درجات الحيطة والحذر"
    )


def test_air_violation_news_text_strips_inline_emoji_from_raw_text() -> None:
    message = type("Message", (), {
        "raw_payload": {},
        "raw_text": "🚨 Ø·ÙŠØ±Ø§Ù† Ø­Ø±Ø¨ÙŠ ÙÙˆÙ‚ Ø§Ù„Ø¬Ù†ÙˆØ¨ 🔴",
    })()

    assert air_violation_news_text(message, None, None) == "Ø·ÙŠØ±Ø§Ù† Ø­Ø±Ø¨ÙŠ ÙÙˆÙ‚ Ø§Ù„Ø¬Ù†ÙˆØ¨"


def test_multi_region_bulletin_does_not_get_a_false_single_caza() -> None:
    labels = air_violation_caza_labels(
        "الجنوب: النبطية والجوار\nخط الساحل / بيروت\nالهرمل",
        "Akkar",
        "عكار",
        [("Nabatiye", "النبطية"), ("Beirut", "بيروت"), ("Hermel", "الهرمل")],
    )

    assert labels == ("Multiple regions", "مناطق متعددة")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("drone activity over hermel", ("Hermel", "الهرمل")),
        ("warplanes over baalbeck", ("Baalbek", "بعلبك")),
        ("surveillance aircraft over saida", ("Saida", "صيدا")),
        ("drone patrol over west beqaa", ("West Bekaa", "البقاع الغربي")),
    ],
)
def test_air_violation_caza_aliases_include_requested_kadaa(text, expected) -> None:
    labels = air_violation_caza_labels(
        text,
        None,
        None,
        [
            ("Hermel", "الهرمل"),
            ("Baalbek", "بعلبك"),
            ("Saida", "صيدا"),
            ("West Bekaa", "البقاع الغربي"),
        ],
    )

    assert labels == expected


@pytest.mark.parametrize(
    ("caza_en", "condition_id", "expected_hours"),
    [
        ("Nabatiye", 35, 4),
        ("Marjaayoun", 35, 4),
        ("Bint Jbeil", 35, 4),
        ("Tyre", 35, 4),
        ("Sour", 35, 4),
        ("Baabda", 35, 4),
        ("Hermel", 35, 4),
        ("Baalbeck", 35, 4),
        ("Saida", 35, 4),
        ("West Beqaa", 35, 4),
        ("Akkar", 35, 4),
        (None, 35, 4),
        ("Nabatiye", 36, 1),
        ("Akkar", 36, 1),
        ("Nabatiye", 38, 1),
        ("Akkar", 38, 1),
    ],
)
def test_air_violation_caza_window_hours(caza_en, condition_id, expected_hours) -> None:
    assert air_violation_caza_window_hours(caza_en, condition_id) == expected_hours


def test_priority_caza_air_violations_are_limited_to_one_per_hour() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for repository integration coverage.")

    engine = create_engine(database_url)
    try:
        connection = engine.connect()
    except OperationalError as exc:
        pytest.skip(f"Database is unavailable: {exc}")

    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    marker = uuid4().hex
    try:
        condition = db.get(Condition, 36)
        if condition is None:
            pytest.skip("Air-violation condition 36 is unavailable.")

        source = Source(
            type=SourceType.api,
            name="Red Alert Lebanon",
            external_id=f"air-window-source-{marker}",
            config={},
        )
        village = Village(
            acs_code=int(marker[:6], 16),
            ref_name_en=f"Arnoun Test {marker}",
            ref_name_ar=f"Arnoun Test {marker}",
            caza_en="Nabatiye",
            caza_ar="Nabatiye",
        )
        db.add_all([source, village])
        db.flush()

        def result() -> MatchResultDTO:
            return MatchResultDTO(
                village_matches=[
                    VillageMatchResult(
                        matched_village_id=village.id,
                        village_confidence=1.0,
                        village_match_status=MatchResultStatus.matched,
                        village_review_required=False,
                        raw_village_text=village.ref_name_en,
                    )
                ],
                any_village_low_confidence=False,
                matched_condition_id=condition.id,
                condition_confidence=1.0,
                condition_match_status=MatchResultStatus.matched,
                condition_review_required=False,
                raw_condition_text="drone over Nabatiye",
            )

        def message(suffix: str, occurred_at: datetime) -> RawMessage:
            item = RawMessage(
                source_id=source.id,
                external_message_id=f"air-window-message-{marker}-{suffix}",
                source_platform="telegram",
                source_name="red-alert",
                raw_text=f"drone over {village.ref_name_en}",
                raw_payload={},
                status=MessageStatus.parsed,
                message_datetime=occurred_at,
            )
            db.add(item)
            db.flush()
            return item

        repository = AirViolationRepository(db)
        first_at = datetime(2026, 9, 21, 8, 0, tzinfo=timezone.utc)
        db.execute(
            sa_delete(AirViolation).where(
                AirViolation.caza_en == "Nabatiye",
                AirViolation.event_date == first_at.astimezone().date(),
            )
        )
        db.flush()

        assert repository.route_from_match(message("first", first_at), result()) is True
        assert repository.route_from_match(
            message("inside-window", first_at + timedelta(minutes=59)),
            result(),
        ) is False
        assert repository.route_from_match(
            message("after-window", first_at + timedelta(hours=1, minutes=1)),
            result(),
        ) is True

        total = db.scalar(
            select(func.count(AirViolation.id)).where(
                AirViolation.caza_en == "Nabatiye",
                AirViolation.source_id == source.id,
            )
        )
        assert total == 2
    except (OperationalError, ProgrammingError) as exc:
        pytest.skip(f"Air-violation schema is unavailable: {exc}")
    finally:
        db.close()
        transaction.rollback()
        connection.close()


def test_air_violation_uses_original_message_source_name() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        pytest.skip("DATABASE_URL is required for repository integration coverage.")

    engine = create_engine(database_url)
    try:
        connection = engine.connect()
    except OperationalError as exc:
        pytest.skip(f"Database is unavailable: {exc}")

    transaction = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint")
    marker = uuid4().hex
    try:
        condition = db.get(Condition, 35)
        if condition is None:
            pytest.skip("Air-violation condition 35 is unavailable.")

        source = Source(
            type=SourceType.api,
            name="CNRS Webhook",
            external_id=f"source-test-{marker}",
            config={},
        )
        db.add(source)
        db.flush()
        message = RawMessage(
            source_id=source.id,
            external_message_id=f"message-test-{marker}",
            source_platform="telegram",
            source_name="original-channel",
            origin_account="original-account",
            raw_payload={},
            status=MessageStatus.parsed,
        )
        db.add(message)
        db.flush()
        db.add(
            AirViolation(
                raw_message_id=message.id,
                condition_id=condition.id,
                source_id=source.id,
                caza_en=marker,
                event_date=date(2026, 8, 18),
                khabar="Source mapping test",
            )
        )
        db.flush()

        result = AirViolationRepository(db).list_all(
            AirViolationListParams(caza_en=marker)
        )

        assert result.total == 1
        assert result.items[0].source_name == "original-account"
    except (OperationalError, ProgrammingError) as exc:
        pytest.skip(f"Air-violation schema is unavailable: {exc}")
    finally:
        db.close()
        transaction.rollback()
        connection.close()
