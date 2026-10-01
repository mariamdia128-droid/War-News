from datetime import date, datetime, time
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlalchemy.dialects import postgresql

from app.news.dtos import AirViolationListParams
from app.news.repositories.air_violation_repository import AirViolationRepository


def test_import_filter_does_not_require_join_in_summary_or_count():
    filters = AirViolationRepository._filters(AirViolationListParams(imported_only=True))
    assert len(filters) == 2
    sql = str(filters[1].compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
    assert 'raw_message_id IN (SELECT raw_messages.id' in sql
    assert 'khabar' in sql
    default_filters = AirViolationRepository._filters(AirViolationListParams())
    sql = str(default_filters[0].compile(compile_kwargs={'literal_binds': True}))
    assert 'condition_id IN (35, 36, 38)' in sql


def test_import_details_preserve_file_fields():
    row = SimpleNamespace(_mapping={
        'import_payload': {'import': 'khabar', 'filename': 'news.xlsx', 'row': {'khabar': 'news', 'custom column': 'original'}},
        'raw_match_result': {}, 'caza_en': None, 'caza_ar': None,
    })
    result = AirViolationRepository(MagicMock())._with_village_labels([row])[0]
    assert result['is_imported'] is True
    assert result['import_filename'] == 'news.xlsx'
    assert result['import_row']['custom column'] == 'original'
    assert 'import_payload' not in result


def test_village_labels_do_not_override_stored_multi_region_caza():
    row = SimpleNamespace(_mapping={
        'id': 42,
        'village_id': 7,
        'import_payload': {},
        'raw_match_result': {},
        'caza_en': 'Multiple regions',
        'caza_ar': 'مناطق متعددة',
    })
    village = SimpleNamespace(
        id=7,
        ref_name_en='Aadloun',
        ref_name_ar='عدلون',
        acs_name=None,
        cad_name=None,
        caza_en='Saida',
        caza_ar='صيدا',
    )
    db = MagicMock()
    db.execute.return_value.all.return_value = []
    db.scalars.return_value = [village]

    result = AirViolationRepository(db)._with_village_labels([row])[0]

    assert result['caza_en'] == 'Multiple regions'
    assert result['caza_ar'] == 'مناطق متعددة'
    assert result['village_en'] == 'Aadloun'


def test_list_response_collapses_air_violation_window_rows():
    rows = [
        {"id": 2, "condition_id": 36, "window_id": "36:South Lebanon:2026-09-28T10:17:59"},
        {"id": 1, "condition_id": 36, "window_id": "36:South Lebanon:2026-09-28T10:17:59"},
        {"id": 3, "condition_id": 35, "window_id": None},
    ]

    result = AirViolationRepository._collapse_windowed_items(rows)

    assert [item["id"] for item in result] == [2, 3]


def test_list_response_does_not_collapse_warplane_rows():
    rows = [
        {"id": 2, "condition_id": 35, "window_id": "35:Sour:2026-09-28T10:00:00"},
        {"id": 1, "condition_id": 35, "window_id": "35:Sour:2026-09-28T10:00:00"},
    ]

    result = AirViolationRepository._collapse_windowed_items(rows)

    assert [item["id"] for item in result] == [2, 1]


def test_window_metadata_aggregates_villages_and_reports():
    items = [
        {
            "id": 2, "condition_id": 36, "caza_en": "Sour", "caza_ar": None,
            "event_date": date(2026, 9, 22), "event_time": time(10, 30),
            "villages": [{"village_id": 2, "name": "Maarakeh"}], "khabar": "Second report",
            "source_name": "Source B", "source_link": "https://example.test/b", "window_id": None,
        },
        {
            "id": 1, "condition_id": 36, "caza_en": "Tyre", "caza_ar": None,
            "event_date": date(2026, 9, 22), "event_time": time(10, 0),
            "villages": [{"village_id": 1, "name": "Aadloun"}], "khabar": "First report",
            "source_name": "Source A", "source_link": None, "window_id": None,
        },
    ]

    result = AirViolationRepository._attach_window_metadata(items, items)

    assert result[0]["villages"] == [
        {"village_id": 1, "name": "Aadloun"},
        {"village_id": 2, "name": "Maarakeh"},
    ]
    assert result[0]["window_violation_count"] == 2
    assert result[0]["window_duration_minutes"] == 60
    assert [report["id"] for report in result[0]["window_reports"]] == [1, 2]


def test_window_metadata_includes_reports_outside_the_visible_filter():
    visible = {
        "id": 2, "condition_id": 36, "caza_en": "Koura", "caza_ar": None,
        "event_date": date(2026, 9, 22), "event_time": time(13, 30),
        "villages": [{"village_id": 2, "name": "Amioun"}], "khabar": "Visible report",
        "source_name": "Source B", "source_link": None, "window_id": None,
    }
    earlier = {
        "id": 1, "condition_id": 36, "caza_en": "Koura", "caza_ar": None,
        "event_date": date(2026, 9, 22), "event_time": time(10, 0),
        "villages": [{"village_id": 1, "name": "Kfar Hazir"}], "khabar": "Earlier report",
        "source_name": "Source A", "source_link": None, "window_id": None,
    }

    result = AirViolationRepository._attach_window_metadata([visible], [visible, earlier])

    assert result[0]["villages"] == [
        {"village_id": 1, "name": "Kfar Hazir"},
        {"village_id": 2, "name": "Amioun"},
    ]
    assert result[0]["window_violation_count"] == 2
    assert result[0]["window_duration_minutes"] == 240


def test_window_metadata_dedupes_village_by_id_not_spelling():
    items = [
        {
            "id": 2, "condition_id": 36, "caza_en": "Sour", "caza_ar": None,
            "event_date": date(2026, 9, 22), "event_time": time(10, 30),
            "villages": [{"village_id": 44, "name": "صور"}],
            "khabar": "Second", "source_name": "B", "source_link": None,
            "window_id": None,
        },
        {
            "id": 1, "condition_id": 36, "caza_en": "Sour", "caza_ar": None,
            "event_date": date(2026, 9, 22), "event_time": time(10, 0),
            "villages": [{"village_id": 44, "name": "Tyre"}],
            "khabar": "First", "source_name": "A", "source_link": None,
            "window_id": None,
        },
    ]

    result = AirViolationRepository._attach_window_metadata(items, items)

    assert result[0]["villages"] == [{"village_id": 44, "name": "Tyre"}]
    assert result[0]["window_violation_count"] == 2


def test_unconfirmed_surveillance_region_stays_as_individual_reports():
    items = [
        {
            "id": 2, "condition_id": 36, "caza_en": "South Lebanon", "caza_ar": None,
            "event_date": date(2026, 9, 22), "event_time": time(10, 30),
            "villages": [], "khabar": "Second report", "source_name": "Source B",
            "source_link": None, "window_id": None,
        },
        {
            "id": 1, "condition_id": 36, "caza_en": "South Lebanon", "caza_ar": None,
            "event_date": date(2026, 9, 22), "event_time": time(10, 0),
            "villages": [], "khabar": "First report", "source_name": "Source A",
            "source_link": None, "window_id": None,
        },
    ]

    result = AirViolationRepository._attach_window_metadata(items, items)

    assert all(item["window_id"] is None for item in result)
    assert [item["id"] for item in AirViolationRepository._collapse_windowed_items(result)] == [2, 1]


def test_condition_45_is_not_routed_to_air_violations():
    db = MagicMock()
    result = AirViolationRepository(db).route_from_match(
        SimpleNamespace(), SimpleNamespace(matched_condition_id=45)
    )
    assert result is False
    assert db.mock_calls == []


def test_recent_drone_air_violation_duplicate_check_requires_same_news_text():
    existing = SimpleNamespace(
        condition_id=36,
        caza_en="Koura",
        caza_ar=None,
        event_date=date(2026, 9, 22),
        event_time=time(12, 45),
        khabar="Surveillance aircraft over Aaba",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [existing]
    repository = AirViolationRepository(db)

    assert repository._has_recent_air_violation(
        "Koura",
        None,
        datetime(2026, 9, 22, 13, 5),
        condition_id=36,
        khabar="Surveillance aircraft over Aaba",
    )
    assert not repository._has_recent_air_violation(
        "Koura",
        None,
        datetime(2026, 9, 22, 13, 5),
        condition_id=36,
        khabar="Surveillance aircraft over Kfar Hazir",
    )


def test_recent_warplane_air_violation_duplicate_check_suppresses_exact_duplicate():
    existing = SimpleNamespace(
        condition_id=35,
        caza_en="Sour",
        caza_ar=None,
        event_date=date(2026, 9, 22),
        event_time=time(12, 45),
        khabar="Warplanes over Sour",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [existing]
    repository = AirViolationRepository(db)

    assert repository._has_recent_air_violation(
        "Sour",
        None,
        datetime(2026, 9, 22, 13, 5),
        condition_id=35,
        khabar="Warplanes over Sour",
    )


def test_recent_caza_only_air_violation_duplicate_check_ignores_text_variation():
    existing = SimpleNamespace(
        condition_id=35,
        caza_en="South Lebanon",
        caza_ar="جنوب لبنان",
        event_date=date(2026, 9, 28),
        event_time=time(10, 17),
        khabar="#مقاتلات_حربية #الجنوب <A>",
    )
    db = MagicMock()
    db.scalars.return_value.all.return_value = [existing]
    repository = AirViolationRepository(db)

    assert repository._has_recent_air_violation(
        "South Lebanon",
        "جنوب لبنان",
        datetime(2026, 9, 28, 10, 58),
        condition_id=35,
        khabar=None,
    )
