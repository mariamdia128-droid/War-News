from datetime import date
from io import BytesIO
from types import SimpleNamespace

import pytest
from openpyxl import load_workbook

from app.news.services.air_violations.air_violation_workbook_service import (
    AirViolationWorkbookService,
)
from app.news.services.air_violations.war_month import war_month


@pytest.mark.parametrize(
    ("calendar_month", "expected"),
    [(month, ((month - 4) % 12) + 1) for month in range(1, 13)],
)
def test_war_month_for_all_calendar_months(
    calendar_month: int, expected: int
) -> None:
    assert war_month(date(2026, calendar_month, 1)) == expected


def test_war_month_december_january_boundary() -> None:
    assert war_month(date(2026, 12, 31)) == 9
    assert war_month(date(2027, 1, 1)) == 10


class _WorkbookDB:
    def execute(self, _statement):
        violation = SimpleNamespace(
            caza_en="Nabatiye",
            caza_ar=None,
            event_date=date(2026, 10, 2),
            event_time=None,
            event_month="October",
            war_month=None,
            khabar="طيران مسير فوق النبطية",
            note_1=None,
            note_2=None,
            source_link=None,
        )
        condition = SimpleNamespace(
            action_en="Surveillance Aircraft", action_ar="طيران استطلاعي"
        )
        source = SimpleNamespace(name="Test")
        return SimpleNamespace(all=lambda: [(violation, condition, source)])


def test_export_month_is_numeric_war_month() -> None:
    output: BytesIO = AirViolationWorkbookService(  # type: ignore[arg-type]
        _WorkbookDB()
    ).export_workbook()
    sheet = load_workbook(output, data_only=True).active

    assert sheet["B2"].value == 7
    assert isinstance(sheet["B2"].value, int)
