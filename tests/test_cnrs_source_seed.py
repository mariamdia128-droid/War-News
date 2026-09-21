from app.core.seeds.seed_cnrs_source import ensure_cnrs_source
from app.sources.models.source import Source, SourceType


class _FakeSession:
    def __init__(self, existing_source: Source | None = None) -> None:
        self.existing_source = existing_source
        self.added: list[Source] = []
        self.flushed = False
        self.commits = 0

    def scalar(self, _statement):
        return self.existing_source

    def add(self, source: Source) -> None:
        self.added.append(source)
        if self.existing_source is None:
            self.existing_source = source

    def flush(self) -> None:
        self.flushed = True

    def commit(self) -> None:
        self.commits += 1


def test_ensure_cnrs_source_inserts_missing_source() -> None:
    session = _FakeSession()

    source, inserted = ensure_cnrs_source(session)  # type: ignore[arg-type]

    assert inserted is True
    assert source.name == "CNRS Webhook"
    assert source.external_id == "cnrs_webhook"
    assert source.config == {"delivery_method": "webhook"}
    assert source.auth_secret_ref == "CNRS_WEBHOOK_SECRET"
    assert source.is_active is True
    assert session.flushed is True
    assert session.commits == 1


def test_ensure_cnrs_source_repairs_existing_source_and_preserves_cursor() -> None:
    existing = Source(
        type=SourceType.other,
        name="Old CNRS",
        external_id="cnrs_webhook",
        config={"foo": "bar", "delivery_method": "polling"},
        last_cursor="800934",
        auth_secret_ref="OLD_SECRET",
        is_active=False,
    )
    session = _FakeSession(existing)

    source, inserted = ensure_cnrs_source(session)  # type: ignore[arg-type]

    assert inserted is False
    assert source is existing
    assert source.type == SourceType.api
    assert source.name == "CNRS Webhook"
    assert source.config == {"foo": "bar", "delivery_method": "webhook"}
    assert source.last_cursor == "800934"
    assert source.auth_secret_ref == "CNRS_WEBHOOK_SECRET"
    assert source.is_active is True
    assert session.commits == 1
