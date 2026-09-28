from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.api.factories.action_factory import _build_local_llm_relevance_classifier
from app.core.config import settings
from app.llm.services.codecraft_relevance_classifier import CodeCraftRelevanceClassifier
from app.news.models import RawMessage


SAMPLES = [
    ("relevant", "غارة إسرائيلية تستهدف أطراف بلدة عيتا الشعب في جنوب لبنان."),
    ("relevant", "قصف مدفعي على محيط كفركلا ولا إصابات حتى الآن."),
    ("relevant", "تحليق مكثف للطيران الحربي الإسرائيلي فوق النبطية وإقليم التفاح."),
    ("relevant", "إصابة مدني جراء سقوط قذيفة في بلدة الخيام."),
    ("relevant", "استهداف سيارة بصاروخ مسير قرب بنت جبيل."),
    ("irrelevant", "افتتاح معرض للكتاب في بيروت بمشاركة دور نشر عربية."),
    ("irrelevant", "انخفاض أسعار النفط في الأسواق العالمية صباح اليوم."),
    ("irrelevant", "فريق رياضي يفوز في مباراة ودية أقيمت في طرابلس."),
    ("irrelevant", "تقرير عن فوائد النوم المنتظم للصحة النفسية والجسدية."),
    ("irrelevant", "عاصفة ثلجية تضرب شمال شرق الولايات المتحدة وتغلق المدارس."),
]


def _messages() -> list[RawMessage]:
    return [
        RawMessage(id=index, raw_text=text)
        for index, (_, text) in enumerate(SAMPLES, start=1)
    ]


async def _classify(label: str, classifier, messages: list[RawMessage]) -> dict[int, str]:
    try:
        results = await classifier.classify_batch(messages)
    except Exception as exc:
        return {message.id: f"error:{exc.__class__.__name__}" for message in messages}
    return {result.raw_message_id: result.verdict.value for result in results}


async def main() -> None:
    if not settings.codecraft_api_key:
        raise RuntimeError("CODECRAFT_API_KEY is required.")
    if not settings.codecraft_model:
        raise RuntimeError("CODECRAFT_MODEL is required.")

    messages = _messages()
    local_classifier = _build_local_llm_relevance_classifier()
    codecraft_classifier = CodeCraftRelevanceClassifier(
        api_key=settings.codecraft_api_key,
        base_url=settings.codecraft_base_url,
        model=settings.codecraft_model,
        timeout_seconds=settings.relevance_llm_timeout_seconds,
        max_retries=settings.relevance_classifier_max_retries,
        retry_backoff_seconds=settings.relevance_classifier_retry_backoff_seconds,
    )

    local_results, codecraft_results = await asyncio.gather(
        _classify("local_llm", local_classifier, messages),
        _classify("codecraft", codecraft_classifier, messages),
    )

    print("id\texpected\tlocal_llm\tcodecraft\ttext")
    for message, (expected, text) in zip(messages, SAMPLES, strict=True):
        print(
            f"{message.id}\t{expected}\t"
            f"{local_results.get(message.id, 'missing')}\t"
            f"{codecraft_results.get(message.id, 'missing')}\t{text}"
        )


if __name__ == "__main__":
    asyncio.run(main())
