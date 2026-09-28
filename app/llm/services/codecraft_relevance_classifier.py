from __future__ import annotations

import asyncio
import logging

from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI

from app.core.llm_knowledge.prompt_assembly import build_stage_system_prompt
from app.llm.dtos import ClassificationResultDTO
from app.llm.interfaces import RelevanceClassifierInterface
from app.llm.services.local_llm_relevance_classifier import (
    LOW_TEMPERATURE,
    LocalLLMRelevanceClassifier,
)
from app.news.models import RawMessage

logger = logging.getLogger(__name__)

CODECRAFT_RELEVANCE_BACKEND = "codecraft"


class CodeCraftRelevanceClassifier(RelevanceClassifierInterface):
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        model: str,
        timeout_seconds: int,
        max_retries: int = 3,
        retry_backoff_seconds: float = 1.0,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout_seconds,
            max_retries=0,
        )
        self.model = model
        self.max_retries = max(1, max_retries)
        self.retry_backoff_seconds = retry_backoff_seconds
        self._parser = LocalLLMRelevanceClassifier(
            client=_CodeCraftParserClient(model=model),
            backend=CODECRAFT_RELEVANCE_BACKEND,
        )

    async def classify_batch(
        self,
        messages: list[RawMessage],
    ) -> list[ClassificationResultDTO]:
        if not messages:
            return []

        try:
            content = await self._chat_with_retries(messages)
        except Exception as exc:
            logger.warning(
                "CodeCraft relevance classifier failed for model=%s: %s",
                self.model,
                exc.__class__.__name__,
            )
            return [
                self._parser._uncertain_result(
                    message.id,
                    reasoning="CodeCraft relevance classification failed.",
                    raw_response={"error": exc.__class__.__name__},
                )
                for message in messages
            ]

        return self._parser._parse_batch_response(content, messages)

    async def _chat_with_retries(self, messages: list[RawMessage]) -> str:
        batch = LocalLLMRelevanceClassifier._format_batch(messages)
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": build_stage_system_prompt(
                                "relevance_filter",
                                batch,
                            ),
                        },
                        {"role": "user", "content": batch},
                    ],
                    temperature=LOW_TEMPERATURE,
                    response_format={"type": "json_object"},
                )
                return response.choices[0].message.content or ""
            except (APIConnectionError, APITimeoutError, APIError) as exc:
                last_error = exc
                if attempt == self.max_retries:
                    break
                await asyncio.sleep(self.retry_backoff_seconds * (2 ** (attempt - 1)))

        if last_error is None:
            raise RuntimeError("CodeCraft relevance classifier failed without an error.")
        raise last_error


class _CodeCraftParserClient:
    def __init__(self, *, model: str) -> None:
        self.model = model
