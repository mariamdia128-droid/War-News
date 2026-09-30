from __future__ import annotations

import json

import pytest

from app.llm.dtos import CasualtyTransitionStatus, ExtractionCategoryKey as K
from app.llm.services.ollama_extraction_service import OllamaExtractionService
from app.llm.services.ollama_presence_gate_service import (
    OllamaPresenceGateService,
    PresenceGateEvidence,
    PresenceGateResult,
)
from app.llm.services.split_phase_extraction import (
    assign_presence,
    parse_segment_casualties,
    segment_has_casualty_language,
)
from app.llm.services.tier1_segmenter import split_segments
from tests.split_phase_fakes import FakeSplitClient

SEG1 = "غارة من مسيرة على منزل في بلدة شبعا أدت إلى استشهاد 2 وإصابة 3 بجروح."
SEG2 = "كما غارة أخرى استهدفت سيارة في بلدة الخيام دون تسجيل إصابات."
TWO_ITEMS = f"{SEG1} {SEG2}"


def _parse(payload: dict, segment_text: str, villages: list[str]):
    return parse_segment_casualties(
        json.dumps(payload, ensure_ascii=False),
        segment_text=segment_text,
        villages=villages,
        model="fake",
        segment_index=0,
        raw_message_id=1,
    )


def _casualties(**values):
    base = dict.fromkeys(
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
    base.update(values)
    return base


def test_grounded_counts_are_kept() -> None:
    result = _parse(
        {
            "casualties": _casualties(deaths=2, injuries=3),
            "casualty_evidence": [
                {"field": "deaths", "evidence_span": "استشهاد 2"},
                {"field": "injuries", "evidence_span": "إصابة 3 بجروح"},
            ],
            "village_casualties": [],
            "casualty_transitions": [],
        },
        SEG1,
        ["شبعا"],
    )
    assert (result.casualties.deaths, result.casualties.injuries) == (2, 3)
    assert {item.field for item in result.casualty_evidence} == {"deaths", "injuries"}
    assert result.has_counts()


def test_number_from_another_item_is_nulled() -> None:
    # The model copies a toll that is not in this segment.
    result = _parse(
        {
            "casualties": _casualties(deaths=2, injuries=3),
            "casualty_evidence": [{"field": "deaths", "evidence_span": "استشهاد 2"}],
            "village_casualties": [],
            "casualty_transitions": [],
        },
        SEG2,
        ["الخيام"],
    )
    assert result.casualties.deaths is None
    assert result.casualties.injuries is None


def test_explicit_zero_is_kept_and_null_stays_null() -> None:
    result = _parse(
        {
            "casualties": _casualties(injuries=0),
            "casualty_evidence": [
                {"field": "injuries", "evidence_span": "دون تسجيل إصابات"}
            ],
            "village_casualties": [],
            "casualty_transitions": [],
        },
        SEG2,
        ["الخيام"],
    )
    assert result.casualties.injuries == 0
    assert result.casualties.deaths is None


def test_village_casualties_need_a_listed_village_and_a_span() -> None:
    text = "غارات على بلدتي المنصوري ومجدل زون: المنصوري: شهيد و3 جرحى؛ مجدل زون: 4 جرحى"
    result = _parse(
        {
            "casualties": _casualties(),
            "casualty_evidence": [],
            "village_casualties": [
                {"village": "المنصوري", "deaths": 1, "injuries": 3,
                 "evidence_span": "المنصوري: شهيد و3 جرحى"},
                {"village": "مجدل زون", "deaths": None, "injuries": 4,
                 "evidence_span": "مجدل زون: 5 جرحى"},
                {"village": "صور", "deaths": 1, "injuries": None,
                 "evidence_span": "المنصوري: شهيد"},
            ],
            "casualty_transitions": [],
        },
        text,
        ["المنصوري", "مجدل زون"],
    )
    assert [(v.village, v.deaths, v.injuries) for v in result.village_casualties] == [
        ("المنصوري", 1, 3)
    ]


def test_transition_without_literal_span_is_dropped() -> None:
    text = "استشهاد أحد جرحى الغارة على بلدة عيترون متأثراً بجروحه."
    result = _parse(
        {
            "casualties": _casualties(),
            "casualty_evidence": [],
            "village_casualties": [],
            "casualty_transitions": [
                {"from_status": "injured", "to_status": "deceased", "count": 1,
                 "evidence_span": "استشهاد أحد جرحى الغارة"},
                {"from_status": "injured", "to_status": "deceased", "count": 2,
                 "evidence_span": "توفي اثنان"},
            ],
        },
        text,
        ["عيترون"],
    )
    assert [(t.from_status, t.count) for t in result.transitions] == [
        (CasualtyTransitionStatus.injured, 1)
    ]


def test_malformed_casualty_response_raises() -> None:
    with pytest.raises(RuntimeError, match="Malformed segment casualty"):
        parse_segment_casualties(
            "{", segment_text=SEG1, villages=[], model="f", segment_index=0, raw_message_id=1
        )


def test_casualty_keyword_precheck() -> None:
    assert segment_has_casualty_language(SEG1)
    assert segment_has_casualty_language(SEG2)  # explicit none
    assert not segment_has_casualty_language("قصف مدفعي على أطراف بلدة كفرشوبا.")


def test_segment_casualty_call_uses_segment_and_villages() -> None:
    segments = split_segments(TWO_ITEMS)
    client = FakeSplitClient(
        responders={
            "casualty": lambda user: {
                "casualties": _casualties(injuries=0),
                "casualty_evidence": [
                    {"field": "injuries", "evidence_span": "دون تسجيل إصابات"}
                ],
                "village_casualties": [],
                "casualty_transitions": [],
            }
        }
    )
    service = OllamaExtractionService(client)  # type: ignore[arg-type]
    result = service._extract_segment_casualties(segments[1], ["الخيام"], raw_message_id=3)
    assert result.casualties.injuries == 0
    user = client.calls[0].user
    assert "البلدات المستهدفة: الخيام" in user
    assert "شبعا" not in user


# --- presence assignment ------------------------------------------------------


def _gate(responder=None) -> tuple[OllamaPresenceGateService, FakeSplitClient]:
    client = FakeSplitClient(responders={"presence": responder} if responder else {})
    return OllamaPresenceGateService(client), client  # type: ignore[arg-type]


def _result(*pairs: tuple[K, str]) -> PresenceGateResult:
    return PresenceGateResult(
        categories_present=[key for key, _ in pairs],
        category_evidence=[
            PresenceGateEvidence(category_key=key, evidence_span=span) for key, span in pairs
        ],
    )


def test_categories_follow_their_evidence_span() -> None:
    text = (
        "غارة على مدرسة في بلدة شبعا أدت إلى أضرار. "
        "كما غارة أخرى استهدفت مستشفى في بلدة الخيام."
    )
    segments = split_segments(text)
    gate, client = _gate()
    presence = assign_presence(
        gate,
        _result((K.school_university, "غارة على مدرسة"), (K.hospital, "استهدفت مستشفى")),
        segments,
        eligible=[0, 1],
        raw_message_id=1,
    )
    assert presence.per_segment == [[K.school_university], [K.hospital]]
    assert presence.unplaced == []
    assert client.calls == []


def test_vehicle_in_second_item_does_not_attach_to_first() -> None:
    segments = split_segments(TWO_ITEMS)
    gate, client = _gate()
    presence = assign_presence(
        gate,
        _result((K.vehicles, "سيارة")),
        segments,
        eligible=[0, 1],
        raw_message_id=1,
    )
    assert K.vehicles not in presence.per_segment[0]
    assert K.vehicles in presence.per_segment[1]
    # Casualty wording in both items: shaba has counts, khiam an explicit none.
    assert K.casualty_demographics in presence.per_segment[0]
    assert K.casualty_demographics in presence.per_segment[1]
    assert client.calls == []


def test_unplaceable_span_asks_the_gate_per_segment() -> None:
    text = (
        "غارة على بلدة شبعا طالت مركزاً للجيش اللبناني. "
        "كما غارة أخرى على بلدة الخيام."
    )
    segments = split_segments(text)

    def responder(user: str):
        if "للجيش" in user:
            return {
                "categories_present": ["lebanese_army"],
                "category_evidence": [
                    {"category_key": "lebanese_army", "evidence_span": "مركزاً للجيش اللبناني"}
                ],
            }
        return {"categories_present": [], "category_evidence": []}

    gate, client = _gate(responder)
    presence = assign_presence(
        gate,
        _result((K.lebanese_army, "الجيش استُهدف")),  # paraphrase, not in any segment
        segments,
        eligible=[0, 1],
        raw_message_id=1,
    )
    assert presence.per_segment == [[K.lebanese_army], []]
    assert presence.segment_gate_calls == 2
    assert client.stages() == ["presence", "presence"]


def test_category_nobody_confirms_stays_unplaced() -> None:
    segments = split_segments(TWO_ITEMS)
    gate, _client = _gate(lambda user: {"categories_present": [], "category_evidence": []})
    presence = assign_presence(
        gate,
        _result((K.press, "طاقم صحفي")),
        segments,
        eligible=[0, 1],
        raw_message_id=1,
    )
    assert presence.unplaced == [K.press]
    assert all(K.press not in keys for keys in presence.per_segment)


def test_single_segment_takes_every_key_without_calls() -> None:
    segments = split_segments(SEG1)
    gate, client = _gate()
    presence = assign_presence(
        gate,
        _result((K.municipality, "مبنى البلدية")),
        segments,
        eligible=[0],
        raw_message_id=1,
    )
    assert presence.per_segment == [[K.casualty_demographics, K.municipality]]
    assert client.calls == []


def test_irrelevant_segments_get_nothing() -> None:
    segments = split_segments(TWO_ITEMS)
    gate, _client = _gate()
    presence = assign_presence(
        gate,
        _result((K.vehicles, "سيارة")),
        segments,
        eligible=[0],
        raw_message_id=1,
    )
    # The car is in the irrelevant item: not moved onto item 0, not unplaced.
    assert presence.per_segment[1] == []
    assert K.vehicles not in presence.per_segment[0]
    assert presence.unplaced == []
