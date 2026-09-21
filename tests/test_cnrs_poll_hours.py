from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.sources.actions.ingest_source_action import IngestSourceAction
from scripts.cnrs_poll_worker import (
    CnrsPollBootstrapRequired,
    build_parser,
    main,
    min_datetime_from_hours,
    run_poll_pass,
    _resolve_resume_cursor,
    _resolve_source,
)


def test_hours_without_after_id_parses() -> None:
    args = build_parser().parse_args(["--hours", "6"])
    assert args.after_id is None
    assert args.hours == 6


def test_hours_and_after_id_parse() -> None:
    args = build_parser().parse_args(["--after-id", "731000", "--hours", "6"])
    assert args.after_id == "731000"
    assert args.hours == 6


def test_omitted_hours_keeps_after_id_optional() -> None:
    args = build_parser().parse_args([])
    assert args.after_id is None
    assert args.hours is None


def test_hours_cutoff_excludes_older_posts() -> None:
    now = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
    cutoff = min_datetime_from_hours(6, now=now)
    assert cutoff == datetime(2026, 8, 24, 6, 0, tzinfo=timezone.utc)
    assert IngestSourceAction._is_before_cutoff(
        datetime(2026, 8, 24, 5, 59, tzinfo=timezone.utc),
        cutoff,
    )
    assert not IngestSourceAction._is_before_cutoff(
        datetime(2026, 8, 24, 6, 0, tzinfo=timezone.utc),
        cutoff,
    )


def test_omitted_hours_does_not_apply_cutoff() -> None:
    assert min_datetime_from_hours(None) is None
    assert IngestSourceAction._is_before_cutoff(
        datetime(2020, 1, 1, tzinfo=timezone.utc),
        None,
    ) is False


class _FakeRepo:
    def __init__(self) -> None:
        self.by_id = {}
        self.active_by_external_id = {}

    def get_by_id(self, source_id: int):
        return self.by_id.get(source_id)

    def get_active_by_external_id(self, external_id: str):
        return self.active_by_external_id.get(external_id)


class _FakeSource:
    def __init__(self, source_id: int, last_cursor: str | None = None) -> None:
        self.id = source_id
        self.last_cursor = last_cursor


def test_resolve_resume_cursor_uses_source_last_cursor_before_db_max(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.cnrs_poll_worker._last_ingested_cursor",
        lambda repo, source_id: "730500",
    )
    assert (
        _resolve_resume_cursor(_FakeRepo(), _FakeSource(3, "730400"), None)
        == "730400"
    )


def test_resolve_resume_cursor_uses_db_max_when_source_cursor_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.cnrs_poll_worker._last_ingested_cursor",
        lambda repo, source_id: "730500",
    )
    assert _resolve_resume_cursor(_FakeRepo(), _FakeSource(3), None) == "730500"


def test_resolve_resume_cursor_honors_explicit_override(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.cnrs_poll_worker._last_ingested_cursor",
        lambda repo, source_id: "730500",
    )
    assert (
        _resolve_resume_cursor(_FakeRepo(), _FakeSource(3, "730400"), "731000")
        == "731000"
    )


def test_resolve_resume_cursor_raises_when_no_numeric_rows(monkeypatch) -> None:
    monkeypatch.setattr(
        "scripts.cnrs_poll_worker._last_ingested_cursor",
        lambda repo, source_id: None,
    )
    with pytest.raises(CnrsPollBootstrapRequired, match="--after-id"):
        _resolve_resume_cursor(_FakeRepo(), _FakeSource(3), None)


def test_resolve_source_uses_active_cnrs_external_id_by_default() -> None:
    repo = _FakeRepo()
    repo.active_by_external_id["cnrs_webhook"] = _FakeSource(2)

    assert _resolve_source(repo, None).id == 2


def test_resolve_source_keeps_explicit_source_id_override() -> None:
    repo = _FakeRepo()
    repo.by_id[7] = _FakeSource(7)
    repo.active_by_external_id["cnrs_webhook"] = _FakeSource(2)

    assert _resolve_source(repo, 7).id == 7


def test_main_exits_quietly_when_bootstrap_required(monkeypatch) -> None:
    def _raise_bootstrap(**kwargs):
        raise CnrsPollBootstrapRequired("bootstrap once with --after-id")

    monkeypatch.setattr("scripts.cnrs_poll_worker.run_poll_pass", _raise_bootstrap)
    main([])


def test_run_poll_pass_resolves_cnrs_source_by_external_id(monkeypatch) -> None:
    source = SimpleNamespace(
        id=44,
        name="CNRS Webhook",
        external_id="cnrs_webhook",
        config={"delivery_method": "webhook"},
    )
    added_messages = []
    logs = []

    class _FakeDb:
        def close(self) -> None:
            return

    class _FakeRepo:
        def __init__(self, db):
            self.db = db

        def get_active_by_external_id(self, external_id: str):
            assert external_id == "cnrs_webhook"
            return source

        def is_content_source_blocked(self, source_platform, origin_account) -> bool:
            return False

        def get_or_create_source_platform_id(self, source_platform, source_name):
            return 99

        def add_raw_message(self, raw_message) -> None:
            added_messages.append(raw_message)

        def is_duplicate_raw_message_error(self, exc) -> bool:
            return False

        def rollback(self) -> None:
            return

        def update_last_cursor(self, resolved_source, cursor) -> None:
            assert resolved_source is source
            source.last_cursor = cursor

        def write_ingestion_log(self, **kwargs) -> None:
            logs.append(kwargs)

    class _FakeProvider:
        def __init__(self, config, api_key):
            assert config == source.config
            assert api_key == "cnrs-api-key"

        def fetch_batch(self, cursor, limit):
            assert cursor == "731000"
            return (
                [
                    {
                        "external_message_id": "731001",
                        "source_platform": "telegram",
                        "source_name": "field-channel",
                        "raw_text": "message",
                        "raw_payload": {"id": 731001},
                        "message_datetime": "2026-08-24T10:00:00+00:00",
                        "cnrs_classification": {"include": True},
                    }
                ],
                "731001",
                False,
            )

    monkeypatch.setattr("scripts.cnrs_poll_worker.SessionLocal", _FakeDb)
    monkeypatch.setattr("scripts.cnrs_poll_worker.SourceRepository", _FakeRepo)
    monkeypatch.setattr("scripts.cnrs_poll_worker.CNRSSourceProvider", _FakeProvider)
    monkeypatch.setattr(
        "scripts.cnrs_poll_worker._resolve_cnrs_api_key",
        lambda: "cnrs-api-key",
    )

    summary = run_poll_pass(after_id="731000")

    assert summary["source_id"] == 44
    assert summary["inserted"] == 1
    assert summary["resume_cursor"] == "731001"
    assert added_messages[0].source_id == 44
    assert added_messages[0].source_platform_id == 99
    assert logs[0]["source_id"] == 44
