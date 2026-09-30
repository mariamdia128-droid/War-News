"""Fake Ollama client for split-phase extraction tests.

Routes each chat call by its response schema (which stage is asking) and hands
the user message to a per-stage responder that returns canned JSON.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from app.llm.services.ollama_category_detail_service import CATEGORY_DETAIL_RESPONSE_SCHEMA
from app.llm.services.ollama_extraction_service import GENERAL_EXTRACTION_RESPONSE_SCHEMA
from app.llm.services.ollama_presence_gate_service import PRESENCE_GATE_RESPONSE_SCHEMA
from app.llm.services import split_phase_extraction as split

Responder = Callable[[str], Any]


def _stage_for(schema: object) -> str:
    known = {
        id(split.SEGMENT_EVENT_RESPONSE_SCHEMA): "event",
        id(PRESENCE_GATE_RESPONSE_SCHEMA): "presence",
        id(GENERAL_EXTRACTION_RESPONSE_SCHEMA): "general",
        id(CATEGORY_DETAIL_RESPONSE_SCHEMA): "category",
    }
    casualty = getattr(split, "SEGMENT_CASUALTY_RESPONSE_SCHEMA", None)
    if casualty is not None:
        known[id(casualty)] = "casualty"
    segment_category = getattr(split, "SEGMENT_CATEGORY_DETAIL_RESPONSE_SCHEMA", None)
    if segment_category is not None:
        known[id(segment_category)] = "segment_category"
    return known.get(id(schema), "unknown")


@dataclass
class FakeCall:
    stage: str
    system: str
    user: str


@dataclass
class FakeSplitClient:
    """Stand-in for OllamaChatClient: ``responders[stage](user_text) -> dict``."""

    responders: dict[str, Responder]
    model: str = "fake-7b"
    calls: list[FakeCall] = field(default_factory=list)

    def chat(self, messages, response_format=None, temperature=None, **_: object) -> str:
        stage = _stage_for(response_format)
        system = next((m.content for m in messages if m.role == "system"), "")
        user = next((m.content for m in messages if m.role == "user"), "")
        self.calls.append(FakeCall(stage=stage, system=system, user=user))
        responder = self.responders.get(stage)
        if responder is None:
            raise AssertionError(f"unexpected LLM call for stage={stage}")
        payload = responder(user)
        if isinstance(payload, BaseException):
            raise payload
        return payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    def stages(self) -> list[str]:
        return [call.stage for call in self.calls]
