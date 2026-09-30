from __future__ import annotations

import re

import pytest

from app.core.config import settings
from app.llm.dtos import CasualtyScope, ExtractionCategoryKey as K
from app.llm.services.ollama_extraction_service import (
    EXTRACTION_FLOW_SPLIT,
    OllamaExtractionService,
)
from app.llm.services.ollama_presence_gate_service import OllamaPresenceGateService
from app.llm.services.split_phase_extraction import SPLIT_MIXED_SCOPE_REVIEW_REASON
from tests.split_phase_fakes import FakeSplitClient

MULTI = (
    "قصف بالقذائف المدفعية على محيط البلدة في بلدة شبعا، أدى الاستهداف إلى إصابة 3 أشخاص "
    "دون تسجيل حالات وفاة. كما غارة أخرى في بلدة عيناتا، أدى الاستهداف إلى إصابة 3 أشخاص "
    "دون تسجيل حالات وفاة. كما غارة أخرى في بلدة طيرحرفا، أسفر الاستهداف عن استشهاد 2 "
    "أشخاص وإصابة 1 آخرين بجروح متفاوتة."
)
AGGREGATE = (
    "شنت طائرات العدو الإسرائيلي سلسلة غارات متزامنة طالت بلدات كفركلا، عيتا الشعب، شبعا، "
    "طيرحرفا، ميس الجبل وجويا، ما أسفر عن سقوط 3 شهداء و10 جرحى في حصيلة إجمالية للغارات."
)
NO_CASUALTIES = "قصف مدفعي إسرائيلي على أطراف بلدة كفرشوبا."
_VILLAGE_RE = re.compile(r"(?<![ء-ي])بلدة ([ء-ي]+)")

_NULL_CASUALTIES = dict.fromkeys(
    [
        "deaths",
        "injuries",
        "male_deaths",
        "male_injuries",
        "female_deaths",
        "female_injuries",
        "children_deaths",
        "children_injuries",
    ]
)


def _event_from_text(user: str) -> dict:
    item = user.split("البند:\n")[-1]
    names = _VILLAGE_RE.findall(item)
    if "بلدات" in item:
        names = ["كفركلا", "عيتا الشعب", "شبعا", "طيرحرفا", "ميس الجبل", "جويا"]
    return {
        "is_relevant": True,
        "villages": [{"name": name, "role": "target", "qualifier_text": None} for name in names],
        "action_description": "غارة",
    }


def _casualties_from_text(user: str) -> dict:
    """Reads «استشهاد N» / «إصابة N» / «N شهداء و M جرحى» from the item only."""
    item = user.split("البند:\n")[-1]
    values = dict(_NULL_CASUALTIES)
    evidence = []
    for pattern, field_name in (
        (r"استشهاد (\d+) أشخاص", "deaths"),
        (r"إصابة (\d+) أشخاص", "injuries"),
        (r"إصابة (\d+) آخرين", "injuries"),
        (r"(\d+) شهداء", "deaths"),
        (r"(\d+) جرحى", "injuries"),
    ):
        match = re.search(pattern, item)
        if match and values[field_name] is None:
            values[field_name] = int(match.group(1))
            evidence.append({"field": field_name, "evidence_span": match.group(0)})
    if values["deaths"] is None and "دون تسجيل حالات وفاة" in item:
        values["deaths"] = 0
        evidence.append({"field": "deaths", "evidence_span": "دون تسجيل حالات وفاة"})
    return {
        "casualties": values,
        "casualty_evidence": evidence,
        "village_casualties": [],
        "casualty_transitions": [],
    }


def _no_presence(user: str) -> dict:
    return {"categories_present": [], "category_evidence": []}


def _service(responders: dict) -> tuple[OllamaExtractionService, FakeSplitClient]:
    client = FakeSplitClient(responders=responders)
    service = OllamaExtractionService(
        client,  # type: ignore[arg-type]
        presence_gate=OllamaPresenceGateService(client),  # type: ignore[arg-type]
    )
    return service, client


@pytest.fixture
def split_on(monkeypatch):
    monkeypatch.setattr(settings, "tier1_split_phases_enabled", True)
    monkeypatch.setattr(settings, "tier1_split_max_segments", 10)


_DEFAULT_RESPONDERS = {
    "event": _event_from_text,
    "presence": _no_presence,
    "casualty": _casualties_from_text,
}


def test_multi_item_bulletin_gives_one_sub_event_per_item(split_on) -> None:
    service, client = _service(dict(_DEFAULT_RESPONDERS))
    result = service.extract_tier1(MULTI, raw_message_id=2)

    assert result.extraction_flow == EXTRACTION_FLOW_SPLIT
    assert result.extraction_tier == 1
    assert client.stages() == ["event"] * 3 + ["presence"] + ["casualty"] * 3
    assert [
        [location.village for location in sub_event.locations]
        for sub_event in result.sub_events
    ] == [["شبعا"], ["عيناتا"], ["طيرحرفا"]]
    assert [
        (sub_event.casualties.deaths, sub_event.casualties.injuries)
        for sub_event in result.sub_events
    ] == [(None, 3), (None, 3), (2, 1)]
    assert [sub_event.segment_index for sub_event in result.sub_events] == [0, 1, 2]
    for sub_event in result.sub_events:
        start, end = sub_event.segment_span
        assert sub_event.evidence_span == MULTI[start:end].strip()
        assert K.casualty_demographics in sub_event.presence_category_keys
    assert result.casualty_scope == CasualtyScope.per_village_exact
    assert not result.casualty_scope_needs_review
    assert {
        role.village: (role.deaths, role.injuries) for role in result.village_roles
    } == {"شبعا": (None, 3), "عيناتا": (None, 3), "طيرحرفا": (2, 1)}


def test_root_totals_are_the_sum_of_items_not_double_counted(split_on) -> None:
    service, _client = _service(dict(_DEFAULT_RESPONDERS))
    result = service.extract_tier1(MULTI, raw_message_id=2)

    assert (result.casualties.deaths, result.casualties.injuries) == (2, 7)
    assert (result.casualties.total_deaths, result.casualties.total_injuries) == (2, 7)
    assert result.casualties.deaths == sum(
        sub_event.casualties.deaths or 0 for sub_event in result.sub_events
    )
    # Tier 1 has no entity categories yet; the casualty category mirrors root.
    demographics = result.categories[K.casualty_demographics].casualties
    assert (demographics.deaths, demographics.injuries) == (2, 7)


def test_one_line_bulletin_with_shared_total_is_aggregate(split_on) -> None:
    service, client = _service(dict(_DEFAULT_RESPONDERS))
    result = service.extract_tier1(AGGREGATE, raw_message_id=3)

    assert client.stages() == ["event", "presence", "casualty"]
    assert result.sub_events == []
    assert result.casualty_scope == CasualtyScope.bulletin_aggregate
    assert (result.casualties.total_deaths, result.casualties.total_injuries) == (3, 10)
    assert result.casualties.deaths is None
    assert result.casualties.injuries is None
    assert len(result.village_roles) == 6
    assert all(role.deaths is None and role.injuries is None for role in result.village_roles)


def test_casualty_call_skipped_without_casualty_language(split_on) -> None:
    service, client = _service(dict(_DEFAULT_RESPONDERS))
    result = service.extract_tier1(NO_CASUALTIES, raw_message_id=4)

    assert client.stages() == ["event", "presence"]
    assert result.is_relevant
    assert result.casualty_scope == CasualtyScope.unspecified
    assert K.casualty_demographics not in result.presence_category_keys


def test_presence_keys_are_merged_on_root_and_scoped_on_items(split_on) -> None:
    text = (
        "غارة من مسيرة على منزل في بلدة شبعا أدت إلى استشهاد 2 أشخاص. "
        "كما غارة أخرى استهدفت سيارة في بلدة الخيام."
    )

    def presence(user: str) -> dict:
        return {
            "categories_present": ["vehicles"],
            "category_evidence": [{"category_key": "vehicles", "evidence_span": "استهدفت سيارة"}],
        }

    service, _client = _service({**_DEFAULT_RESPONDERS, "presence": presence})
    result = service.extract_tier1(text, raw_message_id=5)

    assert result.sub_events[0].presence_category_keys == [K.casualty_demographics]
    assert result.sub_events[1].presence_category_keys == [K.vehicles]
    assert result.presence_category_keys == [K.casualty_demographics, K.vehicles]


def test_mixed_scope_is_flagged_for_review(split_on) -> None:
    text = (
        "غارات على بلدات كفركلا وحولا أسفرت عن 3 شهداء. "
        "كما غارة أخرى في بلدة عيناتا أدت إلى استشهاد 1 أشخاص."
    )

    def event(user: str) -> dict:
        item = user.split("البند:\n")[-1]
        names = ["كفركلا", "حولا"] if "بلدات" in item else ["عيناتا"]
        return {
            "is_relevant": True,
            "villages": [{"name": n, "role": "target", "qualifier_text": None} for n in names],
            "action_description": "غارة",
        }

    service, _client = _service({**_DEFAULT_RESPONDERS, "event": event})
    result = service.extract_tier1(text, raw_message_id=6)

    assert len(result.sub_events) == 2
    assert result.casualty_scope == CasualtyScope.unspecified
    assert result.casualty_scope_needs_review
    assert result.casualty_scope_review_reason == SPLIT_MIXED_SCOPE_REVIEW_REASON
    assert result.casualties.total_deaths == 4
    assert result.casualties.deaths == 1


def test_irrelevant_message_skips_presence_and_casualty_calls(split_on) -> None:
    def event(user: str) -> dict:
        return {"is_relevant": False, "villages": [], "action_description": None}

    service, client = _service({**_DEFAULT_RESPONDERS, "event": event})
    result = service.extract_tier1("صدر تقرير اقتصادي جديد.", raw_message_id=7)

    assert client.stages() == ["event"]
    assert result.is_relevant is False
    assert result.presence_category_keys == []


def _general_response(user: str) -> dict:
    return {
        "is_relevant": True,
        "village": ["شبعا"],
        "village_roles": [],
        "action_description": "قصف",
        "sub_events": [],
        "casualties": {},
        "casualty_transitions": [],
        "casualty_evidence": [],
        "casualty_scope": "unspecified",
        "casualty_scope_evidence": None,
    }


def test_item_call_failure_falls_back_to_single_call_path(split_on) -> None:
    def event(user: str):
        if "عيناتا" in user:
            return RuntimeError("model timeout")
        return _event_from_text(user)

    service, client = _service(
        {**_DEFAULT_RESPONDERS, "event": event, "general": _general_response}
    )
    result = service.extract_tier1(MULTI, raw_message_id=8)

    assert result.extraction_flow is None
    assert result.is_relevant
    assert client.stages()[-2:] == ["presence", "general"]


def test_too_many_items_use_single_call_path(split_on, monkeypatch) -> None:
    monkeypatch.setattr(settings, "tier1_split_max_segments", 2)
    service, client = _service({**_DEFAULT_RESPONDERS, "general": _general_response})
    result = service.extract_tier1(MULTI, raw_message_id=9)

    assert result.extraction_flow is None
    assert client.stages() == ["presence", "general"]


def test_flag_off_uses_the_current_path_unchanged() -> None:
    assert settings.tier1_split_phases_enabled is False
    service, client = _service({"presence": _no_presence, "general": _general_response})
    result = service.extract_tier1(MULTI, raw_message_id=10)

    assert client.stages() == ["presence", "general"]
    assert result.extraction_flow is None
    dumped = result.model_dump(mode="json")
    assert "extraction_flow" not in dumped

    expected_service, _ = _service({"presence": _no_presence, "general": _general_response})
    expected = expected_service._extract_tier1_current(MULTI, raw_message_id=10)
    expected_dump = expected.model_dump(mode="json")
    dumped.pop("extracted_at")
    expected_dump.pop("extracted_at")
    assert dumped == expected_dump
