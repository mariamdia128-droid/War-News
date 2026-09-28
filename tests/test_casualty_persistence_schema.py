from app.news.models.incident import Incident
from app.news.models.incident_verification_flag import IncidentVerificationFlag


def test_incidents_persist_casualty_type_statuses_and_remaining_total() -> None:
    columns = Incident.__table__.columns

    assert "casualty_deaths_status" in columns
    assert "casualty_injuries_status" in columns
    assert "casualty_status_remaining_total" in columns


def test_verification_flags_have_delayed_visibility_index() -> None:
    columns = IncidentVerificationFlag.__table__.columns
    indexes = {index.name: tuple(column.name for column in index.columns) for index in IncidentVerificationFlag.__table__.indexes}

    assert "visible_after" in columns
    assert indexes["ix_incident_verification_flags_type_status_visible_after"] == (
        "flag_type",
        "status",
        "visible_after",
    )
