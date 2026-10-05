"""Guard: the removed CodeCraft backend must not creep back into app code."""

from pathlib import Path

import pytest

from app.api.factories import action_factory
from app.core.config import settings

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# The only place the string may appear in app code: the removal guard in
# build_relevance_classifier, which fails loudly instead of falling back.
ALLOWED = {
    ("api/factories/action_factory.py", 'if backend == "codecraft":'),
    (
        "api/factories/action_factory.py",
        '"codecraft backend was removed; use local_llm or cnrs_provided"',
    ),
}


def test_no_codecraft_references_in_app_code():
    offenders = []
    for path in sorted(APP_DIR.rglob("*.py")):
        rel = path.relative_to(APP_DIR).as_posix()
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if "codecraft" not in line.lower():
                continue
            if (rel, line.strip()) in ALLOWED:
                continue
            offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, "Unexpected CodeCraft references:\n" + "\n".join(offenders)


def test_codecraft_backend_fails_startup_without_fallback(monkeypatch):
    monkeypatch.setattr(settings, "relevance_classifier_backend", "codecraft")
    with pytest.raises(RuntimeError, match="codecraft backend was removed"):
        action_factory.build_relevance_classifier()


def test_codecraft_settings_are_gone():
    leaked = [name for name in type(settings).model_fields if "codecraft" in name.lower()]
    assert leaked == []
