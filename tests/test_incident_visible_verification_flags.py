from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from sqlalchemy.dialects import postgresql

from app.news.dtos.incident_dto import IncidentListParams
from app.news.repositories.incident_repository import IncidentRepository


def _sql(expression) -> str:
    return str(expression.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))


def test_visible_needs_verification_uses_duplicate_or_visible_open_flag() -> None:
    sql = _sql(IncidentRepository._needs_verification_column())
    assert "duplicate_flag IS true" in sql
    assert "EXISTS" in sql
    assert "incident_verification_flags.status = 'open'" in sql
    assert "visible_after IS NULL" in sql and "visible_after <= now()" in sql


def test_verification_type_filters_map_to_reason_codes() -> None:
    missing = " ".join(_sql(item) for item in IncidentRepository._list_filters(
        IncidentListParams(verification_type="casualty_missing_number")
    ))
    aggregate = " ".join(_sql(item) for item in IncidentRepository._list_filters(
        IncidentListParams(verification_type="casualty_aggregate_toll")
    ))
    duplicate = " ".join(_sql(item) for item in IncidentRepository._list_filters(
        IncidentListParams(verification_type="duplicate")
    ))
    assert "count_missing" in missing
    assert "aggregate_no_breakdown" in aggregate
    assert "duplicate_flag IS true" in duplicate


def test_verified_excludes_open_visible_flags() -> None:
    sql = " ".join(_sql(item) for item in IncidentRepository._list_filters(
        IncidentListParams(verification_status="verified")
    ))
    assert "NOT" in sql and "EXISTS" in sql


def test_payload_has_unique_incident_and_multiple_open_flags() -> None:
    incident_id = uuid4()
    flags = [
        SimpleNamespace(id=uuid4(), reason_code="count_missing", severity="review", detail={"summary": "A", "evidence_sentence": "one"}),
        SimpleNamespace(id=uuid4(), reason_code="aggregate_no_breakdown", severity="review", detail={"summary": "B", "evidence_sentence": "two"}),
    ]
    payload = IncidentRepository._verification_payload(incident_id, False, None, {incident_id: flags})
    assert payload["verification_status"] == "needs_verification"
    assert payload["verification_types"] == ["casualty_missing_number", "casualty_aggregate_toll"]
    assert len(payload["open_flags"]) == 2
