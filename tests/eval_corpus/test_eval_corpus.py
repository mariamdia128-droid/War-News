"""Regression corpus: every confirmed extraction/classification/matching
accuracy bug fixed in this project, replayed against the real deterministic
code (no live Ollama) so a future prompt/matching change is checked against
ALL of them at once — not just the newest bulletin that triggered a fix.

Per app/core/llm_knowledge/CHANGELOG.md policy: every future accuracy fix
must add its confirmed example here, in addition to its own unit test and
changelog entry. Each case is its own parametrized test id, so a failure
names the exact historical bulletin that broke — not just "some case failed".
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.text_normalization import normalize_arabic_text
from app.llm.dtos import ExtractionResult, VillageRoleEntry
from app.llm.services.cnrs_extraction_fallback import trusted_cnrs_action
from app.llm.services.lebanon_scope_filter import is_non_lebanon_location
from app.llm.services.ollama_extraction_service import OllamaExtractionService
from app.news.dtos import MatchResultStatus
from app.news.services.matching.matching_service import MatchingService

CASES_DIR = Path(__file__).resolve().parent / "cases"


def _load_cases() -> list[dict[str, Any]]:
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        cases.append(json.loads(path.read_text(encoding="utf-8")))
    return cases


class _ConditionRepositoryStub:
    """Always returns a single fixed (condition_id, score=1.0) candidate."""

    def __init__(self, condition_id: int) -> None:
        self.condition_id = condition_id

    def find_similar(self, text: str, limit: int = 5):
        return [(SimpleNamespace(id=self.condition_id), 1.0)]


class _EmptyRepositoryStub:
    def find_similar(self, text: str, limit: int = 5):
        return []


class _AliasRepositoryStub(_EmptyRepositoryStub):
    def __init__(self, aliases: dict[str, int]) -> None:
        self.aliases = aliases

    def resolve_alias(self, normalized_text: str):
        village_id = self.aliases.get(normalized_text)
        if village_id is None:
            return None
        return SimpleNamespace(id=village_id), 1.0


def _extraction(action: str) -> ExtractionResult:
    from datetime import datetime, timezone

    return ExtractionResult(
        is_relevant=True,
        village=[],
        village_roles=[],
        action_description=action,
        model="test",
        extracted_at=datetime.now(timezone.utc),
    )


def _check_cnrs_fire_attribution(input_: dict, expected: dict) -> None:
    actual = trusted_cnrs_action(input_["classification"], input_["post_text"])
    assert actual == expected["trusted_action"]


def _check_fuzzy_area_collapse(input_: dict, expected: dict) -> None:
    villages, _roles, alternatives, _evidence = (
        OllamaExtractionService._collapse_fuzzy_area_locations(
            input_["post_text"],
            input_["villages"],
            [],
        )
    )
    assert villages == expected["villages"]
    assert alternatives == expected["alternatives"]


def _check_dash_route_recovery(input_: dict, expected: dict) -> None:
    roles = [VillageRoleEntry(village=name) for name in input_["villages"]]
    villages, _roles = OllamaExtractionService._apply_dash_compound_location_rules(
        input_["post_text"],
        input_["villages"],
        roles,
    )
    assert set(villages or []) == set(expected["villages"])


def _check_secondary_strike_recovery(input_: dict, expected: dict) -> None:
    roles = [VillageRoleEntry(village=name) for name in input_["villages"]]
    villages, _roles = OllamaExtractionService._apply_dash_compound_location_rules(
        input_["post_text"],
        input_["villages"],
        roles,
    )
    assert villages == expected["villages"]


def _check_fuzzy_then_secondary_coexist(input_: dict, expected: dict) -> None:
    roles = [VillageRoleEntry(village=name) for name in input_["villages"]]
    villages, roles = OllamaExtractionService._apply_dash_compound_location_rules(
        input_["post_text"],
        input_["villages"],
        roles,
    )
    villages, _roles, alternatives, _evidence = (
        OllamaExtractionService._collapse_fuzzy_area_locations(
            input_["post_text"],
            villages,
            roles,
        )
    )
    assert set(villages or []) == set(expected["villages"])
    assert alternatives == expected["alternatives"]


def _check_lebanon_scope(input_: dict, expected: dict) -> None:
    marker = is_non_lebanon_location(input_["post_text"])
    assert (marker is not None) == expected["is_non_lebanon"]


def _check_condition_attribution(input_: dict, expected: dict) -> None:
    condition_id = input_["condition_id"]
    service = MatchingService(_EmptyRepositoryStub(), _ConditionRepositoryStub(condition_id))
    result = service.match(_extraction(input_["action_description"]))
    assert result.matched_condition_id == expected["matched_condition_id"]
    assert result.condition_match_status == MatchResultStatus(
        expected["condition_match_status"]
    )


def _check_village_lexical_overlap(input_: dict, expected: dict) -> None:
    candidate = SimpleNamespace(
        id=1,
        ref_name_ar=input_["candidate_ref_name_ar"],
        acs_name=None,
        cad_name=None,
    )
    actual = MatchingService._has_lexical_overlap(input_["mention"], candidate)
    assert actual == expected["has_overlap"]


def _check_village_alias(input_: dict, expected: dict) -> None:
    from datetime import datetime, timezone

    service = MatchingService(
        _AliasRepositoryStub(
            {
                normalize_arabic_text(alias): village_id
                for alias, village_id in input_["aliases"].items()
            }
        ),
        _EmptyRepositoryStub(),
    )
    extraction = ExtractionResult(
        is_relevant=True,
        village=[input_["mention"]],
        village_roles=[],
        action_description=None,
        model="test",
        extracted_at=datetime.now(timezone.utc),
    )
    result = service.match(extraction)
    village = result.village_matches[0]
    assert village.matched_village_id == expected["matched_village_id"]
    assert village.village_match_status == MatchResultStatus(expected["status"])
    if expected.get("alias_matched") is not None:
        assert village.alias_matched is expected["alias_matched"]


def _check_village_alias_display(input_: dict, expected: dict) -> None:
    for mention in input_["mentions"]:
        _check_village_alias(
            {"mention": mention, "aliases": input_["aliases"]},
            {
                "matched_village_id": expected["matched_village_id"],
                "status": expected["status"],
                "alias_matched": True,
            },
        )
    assert input_["mentions"] == expected["display_names"]


_CHECKS = {
    "cnrs_fire_attribution": _check_cnrs_fire_attribution,
    "fuzzy_area_collapse": _check_fuzzy_area_collapse,
    "dash_route_recovery": _check_dash_route_recovery,
    "secondary_strike_recovery": _check_secondary_strike_recovery,
    "fuzzy_then_secondary_coexist": _check_fuzzy_then_secondary_coexist,
    "lebanon_scope": _check_lebanon_scope,
    "condition_attribution": _check_condition_attribution,
    "village_lexical_overlap": _check_village_lexical_overlap,
    "village_alias": _check_village_alias,
    "village_alias_display": _check_village_alias_display,
}

_CASES = _load_cases()


@pytest.mark.parametrize(
    "case",
    _CASES,
    ids=[case["bug_ref"] for case in _CASES],
)
def test_eval_corpus_case(case: dict[str, Any]) -> None:
    checker = _CHECKS.get(case["check"])
    assert checker is not None, f"Unknown check type: {case['check']!r}"
    checker(case["input"], case["expected"])


def test_eval_corpus_is_not_empty() -> None:
    assert len(_CASES) >= 10, (
        "The eval corpus should keep growing with every confirmed accuracy "
        "fix — see app/core/llm_knowledge/CHANGELOG.md policy."
    )
