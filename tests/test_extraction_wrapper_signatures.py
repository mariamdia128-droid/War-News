import inspect

from app.llm.services.cnrs_extraction_fallback import CnrsExtractionFallback
from app.llm.services.ollama_extraction_service import OllamaExtractionService


def _params(func) -> set[str]:
    return {name for name in inspect.signature(func).parameters if name != "self"}


def test_cnrs_fallback_tier2_accepts_every_ollama_tier2_parameter():
    """The wrapper must forward everything the delegate accepts.

    A missing keyword (villages, casualty_scope) once made every Tier 2 call
    raise TypeError, so no Tier 2 detail fill ever succeeded.
    """
    delegate = _params(OllamaExtractionService.extract_tier2_details)
    wrapper = _params(CnrsExtractionFallback.extract_tier2_details)
    assert delegate - wrapper == set()
