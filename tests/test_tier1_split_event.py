from __future__ import annotations

from pathlib import Path

import pytest

from app.core.llm_knowledge.prompt_assembly import build_stage_system_prompt
from app.llm.dtos import VillageRole
from app.llm.services.ollama_extraction_service import OllamaExtractionService
from app.llm.services.split_phase_extraction import (
    parse_segment_event,
    segment_user_content,
)
from app.llm.services.tier1_segmenter import split_segments
from tests.split_phase_fakes import FakeSplitClient

_EVENT_PROMPT = (
    Path(__file__).resolve().parents[1]
    / "app"
    / "core"
    / "llm_knowledge"
    / "rules"
    / "tier1_event_prompt.md"
)


def test_event_prompt_is_small_and_numbers_free() -> None:
    text = _EVENT_PROMPT.read_text(encoding="utf-8")
    # Rough Qwen budget for Arabic: >= 2 characters per token.
    assert len(text) / 2 < 1500
    prompt = build_stage_system_prompt("tier1_event", "غارة على بلدة الخيام")
    assert "villages" in prompt
    assert "casualties" not in prompt
    assert "categories_present" not in prompt


def test_parse_segment_event_normalizes_villages() -> None:
    event = parse_segment_event(
        '{"is_relevant": true, "villages": ['
        '{"name": " البياض ", "role": "origin", "qualifier_text": null},'
        '{"name": "المنصوري", "role": "target", "qualifier_text": " "},'
        '{"name": "المنصوري", "role": "target", "qualifier_text": null},'
        '{"name": "", "role": "target", "qualifier_text": null}],'
        '"action_description": " قصف مدفعي "}',
        model="fake",
        segment_index=0,
        raw_message_id=1,
    )
    assert event.is_relevant is True
    assert [(entry.village, entry.role) for entry in event.village_roles] == [
        ("البياض", VillageRole.origin),
        ("المنصوري", VillageRole.target),
    ]
    assert event.village_roles[1].qualifier_text is None
    assert event.target_names == ["المنصوري"]
    assert event.action_description == "قصف مدفعي"


def test_parse_segment_event_accepts_null_villages() -> None:
    event = parse_segment_event(
        '{"is_relevant": false, "villages": null, "action_description": null}',
        model="fake",
        segment_index=0,
        raw_message_id=None,
    )
    assert event.is_relevant is False
    assert event.village_roles == []


def test_parse_segment_event_rejects_malformed_json() -> None:
    with pytest.raises(RuntimeError, match="Malformed segment event"):
        parse_segment_event("not json", model="fake", segment_index=0, raw_message_id=1)


def test_segment_event_call_sends_only_the_segment() -> None:
    text = (
        "قصف مدفعي على بلدة شبعا أدى إلى إصابة 3 أشخاص. "
        "كما غارة أخرى في بلدة عيناتا أدت إلى استشهاد شخص."
    )
    segments = split_segments(text)
    assert len(segments) == 2
    client = FakeSplitClient(
        responders={
            "event": lambda user: {
                "is_relevant": True,
                "villages": [{"name": "عيناتا", "role": "target", "qualifier_text": None}],
                "action_description": "غارة",
            }
        }
    )
    service = OllamaExtractionService(client)  # type: ignore[arg-type]
    event = service._extract_segment_event(segments[1], raw_message_id=7)
    assert event.target_names == ["عيناتا"]
    assert client.stages() == ["event"]
    assert "عيناتا" in client.calls[0].user
    assert "شبعا" not in client.calls[0].user


def test_list_header_is_sent_as_context() -> None:
    segments = split_segments("الغارات من الطيران الحربي:\n• النبطية الفوقا (١١)\n• حولا (٢)")
    content = segment_user_content(segments[1])
    assert content.startswith("سياق: الغارات من الطيران الحربي:")
    assert content.endswith("• حولا (٢)")
    # The first item already contains its header text.
    assert not segment_user_content(segments[0]).startswith("سياق")
