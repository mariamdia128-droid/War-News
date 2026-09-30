import pytest

from app.api.factories import action_factory
from app.core.config import settings


def test_removed_codecraft_backend_fails_clearly(monkeypatch):
    monkeypatch.setattr(settings, "relevance_classifier_backend", "codecraft")
    with pytest.raises(RuntimeError, match="codecraft backend was removed"):
        action_factory.build_relevance_classifier()
