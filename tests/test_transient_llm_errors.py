import httpx
import pytest

from app.llm.services.transient_llm_errors import is_transient_llm_error


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (httpx.ReadTimeout("timed out"), True),
        (httpx.ConnectTimeout("timed out"), True),
        (RuntimeError("Malformed extraction response."), False),
        (RuntimeError("ReadTimeout: something"), True),
        (httpx.RemoteProtocolError("Server disconnected without sending a response."), True),
        # Stored form in raw_messages.error_message (no class name prefix).
        (RuntimeError("Server disconnected without sending a response."), True),
    ],
)
def test_is_transient_llm_error(exc: BaseException, expected: bool) -> None:
    assert is_transient_llm_error(exc) is expected


def test_server_disconnected_rows_match_the_retry_sql_markers() -> None:
    from app.llm.services.transient_llm_errors import TRANSIENT_LLM_ERROR_MARKERS

    stored = "Server disconnected without sending a response.".lower()
    assert any(marker in stored for marker in TRANSIENT_LLM_ERROR_MARKERS)
