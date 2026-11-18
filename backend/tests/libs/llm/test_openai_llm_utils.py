import httpx
import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAIError,
    PermissionDeniedError,
    RateLimitError,
    omit,
)

from libs.llm.exceptions import (
    LlmException,
    LlmFailedException,
    LlmRateLimitedException,
    LlmUnavailableException,
)
from libs.llm.types import LlmReasoningEffortType
from libs.llm.utils import OpenAiLlmUtils
from tests.factories.llm import build_llm_provider_completion_input

_OPENAI_REQUEST = httpx.Request("POST", "https://api.openai.com/v1/responses")


def _build_status_error(
    error_class: type[APIStatusError], status_code: int, message: str = "provider said no"
) -> APIStatusError:
    openai_response = httpx.Response(status_code, request=_OPENAI_REQUEST)
    return error_class(message, response=openai_response, body=None)  # ty: ignore[invalid-argument-type]


def test_build_reasoning_no_effort_returns_omit() -> None:
    provider_input = build_llm_provider_completion_input(reasoning_effort=None)

    reasoning = OpenAiLlmUtils.build_reasoning(provider_input)

    assert reasoning is omit


@pytest.mark.parametrize(
    ("reasoning_effort", "expected_effort"),
    [
        pytest.param(LlmReasoningEffortType.NONE, "none", id="none"),
        pytest.param(LlmReasoningEffortType.LOW, "low", id="low"),
        pytest.param(LlmReasoningEffortType.MEDIUM, "medium", id="medium"),
        pytest.param(LlmReasoningEffortType.HIGH, "high", id="high"),
        pytest.param(LlmReasoningEffortType.XHIGH, "xhigh", id="xhigh"),
        pytest.param(LlmReasoningEffortType.MAX, "max", id="max"),
    ],
)
def test_build_reasoning_effort_returns_openai_effort(
    reasoning_effort: LlmReasoningEffortType, expected_effort: str
) -> None:
    provider_input = build_llm_provider_completion_input(reasoning_effort=reasoning_effort)

    reasoning = OpenAiLlmUtils.build_reasoning(provider_input)

    assert reasoning == {"effort": expected_effort}


@pytest.mark.parametrize("reasoning_effort", list(LlmReasoningEffortType))
def test_build_reasoning_every_effort_has_an_openai_value(
    reasoning_effort: LlmReasoningEffortType,
) -> None:
    provider_input = build_llm_provider_completion_input(reasoning_effort=reasoning_effort)

    reasoning = OpenAiLlmUtils.build_reasoning(provider_input)

    assert isinstance(reasoning, dict)
    assert reasoning["effort"] in {"none", "low", "medium", "high", "xhigh", "max"}


@pytest.mark.parametrize(
    ("openai_error", "expected_is_retryable"),
    [
        pytest.param(_build_status_error(RateLimitError, 429), True, id="rate_limit"),
        pytest.param(_build_status_error(InternalServerError, 500), True, id="internal_server"),
        pytest.param(APIConnectionError(request=_OPENAI_REQUEST), True, id="connection"),  # ty: ignore[invalid-argument-type]
        pytest.param(APITimeoutError(request=_OPENAI_REQUEST), False, id="timeout"),  # ty: ignore[invalid-argument-type]
        pytest.param(_build_status_error(BadRequestError, 400), False, id="bad_request"),
        pytest.param(_build_status_error(AuthenticationError, 401), False, id="authentication"),
        pytest.param(_build_status_error(PermissionDeniedError, 403), False, id="permission"),
        pytest.param(OpenAIError("generic"), False, id="generic_openai_error"),
    ],
)
def test_is_retryable_error_classifies_error(
    openai_error: OpenAIError, expected_is_retryable: bool
) -> None:
    is_retryable = OpenAiLlmUtils.is_retryable_error(openai_error)

    assert is_retryable is expected_is_retryable


@pytest.mark.parametrize(
    ("attempt", "base_delay_seconds", "max_delay_seconds", "expected_upper_bound"),
    [
        pytest.param(0, 1.0, 20.0, 1.0, id="first_attempt"),
        pytest.param(3, 1.0, 20.0, 8.0, id="doubles_per_attempt"),
        pytest.param(6, 1.0, 20.0, 20.0, id="capped_at_max"),
        pytest.param(2, 0.0, 0.0, 0.0, id="zero_delay"),
    ],
)
def test_compute_retry_delay_seconds_stays_within_bounds(
    attempt: int,
    base_delay_seconds: float,
    max_delay_seconds: float,
    expected_upper_bound: float,
) -> None:
    sampled_delays = [
        OpenAiLlmUtils.compute_retry_delay_seconds(attempt, base_delay_seconds, max_delay_seconds)
        for _ in range(200)
    ]

    assert min(sampled_delays) >= 0
    assert max(sampled_delays) <= expected_upper_bound


def test_compute_retry_delay_seconds_uses_the_range_below_the_bound() -> None:
    sampled_delays = [OpenAiLlmUtils.compute_retry_delay_seconds(3, 1.0, 20.0) for _ in range(200)]

    assert max(sampled_delays) > 4.0
    assert min(sampled_delays) < 4.0


@pytest.mark.parametrize(
    ("openai_error", "expected_exception"),
    [
        pytest.param(
            _build_status_error(RateLimitError, 429), LlmRateLimitedException, id="rate_limit"
        ),
        pytest.param(
            APIConnectionError(request=_OPENAI_REQUEST),  # ty: ignore[invalid-argument-type]
            LlmUnavailableException,
            id="connection",
        ),
        pytest.param(
            APITimeoutError(request=_OPENAI_REQUEST),  # ty: ignore[invalid-argument-type]
            LlmUnavailableException,
            id="timeout",
        ),
        pytest.param(
            _build_status_error(AuthenticationError, 401),
            LlmUnavailableException,
            id="authentication",
        ),
        pytest.param(
            _build_status_error(PermissionDeniedError, 403),
            LlmUnavailableException,
            id="permission_denied",
        ),
        pytest.param(
            _build_status_error(InternalServerError, 500), LlmFailedException, id="internal_server"
        ),
        pytest.param(
            _build_status_error(BadRequestError, 400), LlmFailedException, id="bad_request"
        ),
        pytest.param(OpenAIError("generic"), LlmFailedException, id="generic"),
    ],
)
def test_map_openai_error_returns_mapped_exception_carrying_provider_message(
    openai_error: OpenAIError, expected_exception: type[LlmException]
) -> None:
    mapped_exception = OpenAiLlmUtils.map_openai_error(openai_error)

    assert type(mapped_exception) is expected_exception
    assert mapped_exception.provider_message == str(openai_error)
