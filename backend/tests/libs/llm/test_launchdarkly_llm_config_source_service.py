from uuid import UUID

import pytest
import structlog

from libs.llm.results import (
    GetLlmConfigResult,
    LlmConfigMessageResult,
    LlmProviderCompletionResult,
)
from libs.llm.services.launchdarkly_llm_config_source_service import (
    LaunchDarklyLlmConfigSourceService,
)
from libs.llm.types import LlmCallReasonType, LlmProviderType, LlmReasoningEffortType
from libs.permissions.types import RoleType
from tests.factories.auth import build_auth_user
from tests.factories.llm import build_get_llm_config_result, build_llm_provider_completion_result
from tests.payloads.launchdarkly import build_launchdarkly_inspect_config_payload
from tests.stubs.launchdarkly import LaunchDarklyAiSdkStub

USER_IDENTITY = UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def launchdarkly_ai_sdk_stub() -> LaunchDarklyAiSdkStub:
    return LaunchDarklyAiSdkStub()


def _build_get_llm_config_result_with_payload() -> GetLlmConfigResult:
    return build_get_llm_config_result(
        config_key="blog-post-draft-standard",
        source_payload={
            "config": {"model": "served"},
            "meta": {"version": 3},
            "provider_name": "OpenAI",
        },
    )


async def test_get_config_sends_identity_and_role_as_context(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    launchdarkly_ai_sdk_stub.inspect_config_result = build_launchdarkly_inspect_config_payload()
    auth_user = build_auth_user(user_identity=USER_IDENTITY, role=RoleType.CREATOR)

    launchdarkly_llm_config_source_service = LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    )
    await launchdarkly_llm_config_source_service.get_config("blog-post-draft-standard", auth_user)

    assert launchdarkly_ai_sdk_stub.inspect_config_inputs == [
        (
            "blog-post-draft-standard",
            {"kind": "user", "key": "11111111-2222-3333-4444-555555555555", "role": "CREATOR"},
        )
    ]


async def test_get_config_well_formed_payload_returns_source_result(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    inspect_config_payload = build_launchdarkly_inspect_config_payload(
        model_name="gpt-5.4-nano",
        model_parameters={"reasoning_effort": "low"},
        provider_name="OpenAI",
        messages=[{"role": "system", "content": "Served."}],
        variation_key="variation-a",
        variation_version=3,
    )
    launchdarkly_ai_sdk_stub.inspect_config_result = inspect_config_payload

    get_config_result = await LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    ).get_config("blog-post-draft-standard", build_auth_user())

    assert get_config_result == GetLlmConfigResult(
        config_key="blog-post-draft-standard",
        provider=LlmProviderType.OPENAI,
        model_name="gpt-5.4-nano",
        reasoning_effort=LlmReasoningEffortType.LOW,
        max_output_tokens=None,
        messages=[LlmConfigMessageResult(role="system", content="Served.")],
        variation_key="variation-a",
        variation_version=3,
        source_payload={
            "config": {
                "model": {"name": "gpt-5.4-nano", "parameters": {"reasoning_effort": "low"}},
                "provider": {"name": "OpenAI"},
                "messages": [{"role": "system", "content": "Served."}],
            },
            "meta": {"variationKey": "variation-a", "version": 3},
            "provider_name": "OpenAI",
        },
    )


async def test_track_call_returns_the_calls_result_and_reports_token_usage(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    llm_config_source_result = _build_get_llm_config_result_with_payload()
    auth_user = build_auth_user(user_identity=USER_IDENTITY, role=RoleType.CREATOR)
    expected_result = build_llm_provider_completion_result(input_tokens=123, output_tokens=45)

    async def call() -> LlmProviderCompletionResult:
        return expected_result

    track_call_result = await LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    ).track_call(llm_config_source_result, auth_user, call)

    assert track_call_result == expected_result
    assert launchdarkly_ai_sdk_stub.execute_and_track_handler_outputs == [
        {"output": "", "usage": {"input_tokens": 123, "output_tokens": 45}}
    ]
    assert launchdarkly_ai_sdk_stub.create_handler_inputs == [(("OpenAI", "messages"), False)]
    assert launchdarkly_ai_sdk_stub.execute_and_track_inputs == [
        {
            "config_key": "blog-post-draft-standard",
            "config": {"model": "served"},
            "meta": {"version": 3},
            "user_context": {
                "kind": "user",
                "key": "11111111-2222-3333-4444-555555555555",
                "role": "CREATOR",
            },
        }
    ]


async def test_track_call_other_provider_creates_handler_for_that_provider(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    llm_config_source_result = build_get_llm_config_result(
        source_payload={"config": {}, "meta": {}, "provider_name": "Anthropic"}
    )

    async def call() -> LlmProviderCompletionResult:
        return build_llm_provider_completion_result()

    launchdarkly_llm_config_source_service = LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    )
    await launchdarkly_llm_config_source_service.track_call(
        llm_config_source_result, build_auth_user(), call
    )

    assert launchdarkly_ai_sdk_stub.create_handler_inputs == [(("Anthropic", "messages"), False)]


async def test_track_call_call_raises_and_sdk_reraises_it_propagates_without_warning(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    call_exception = TimeoutError("provider timed out")

    async def call() -> LlmProviderCompletionResult:
        raise call_exception

    launchdarkly_llm_config_source_service = LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    )
    with (
        structlog.testing.capture_logs() as captured_log_events,
        pytest.raises(TimeoutError) as raised_exception_info,
    ):
        await launchdarkly_llm_config_source_service.track_call(
            _build_get_llm_config_result_with_payload(), build_auth_user(), call
        )

    assert raised_exception_info.value is call_exception
    assert captured_log_events == []


async def test_track_call_call_raises_and_sdk_raises_another_error_propagates_calls_error(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    launchdarkly_ai_sdk_stub.execute_and_track_replacement_error = RuntimeError("sdk broke")
    call_exception = TimeoutError("provider timed out")
    call_count = 0

    async def call() -> LlmProviderCompletionResult:
        nonlocal call_count
        call_count += 1
        raise call_exception

    launchdarkly_llm_config_source_service = LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    )
    with (
        structlog.testing.capture_logs() as captured_log_events,
        pytest.raises(TimeoutError) as raised_exception_info,
    ):
        await launchdarkly_llm_config_source_service.track_call(
            _build_get_llm_config_result_with_payload(), build_auth_user(), call
        )

    assert raised_exception_info.value is call_exception
    assert call_count == 1
    assert [log_event["event"] for log_event in captured_log_events] == [
        "launchdarkly_llm_call_tracking_failed"
    ]


async def test_track_call_tracking_fails_after_call_returns_the_result(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    launchdarkly_ai_sdk_stub.execute_and_track_error = RuntimeError("tracking down")
    launchdarkly_ai_sdk_stub.execute_and_track_is_error_after_handler = True
    expected_result = build_llm_provider_completion_result(content="From the call")
    call_count = 0

    async def call() -> LlmProviderCompletionResult:
        nonlocal call_count
        call_count += 1
        return expected_result

    with structlog.testing.capture_logs() as captured_log_events:
        track_call_result = await LaunchDarklyLlmConfigSourceService(
            launchdarkly_ai_sdk_stub
        ).track_call(_build_get_llm_config_result_with_payload(), build_auth_user(), call)

    assert track_call_result == expected_result
    assert call_count == 1
    assert [log_event["event"] for log_event in captured_log_events] == [
        "launchdarkly_llm_call_tracking_failed"
    ]


async def test_track_call_tracking_fails_before_call_runs_call_untracked(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    launchdarkly_ai_sdk_stub.execute_and_track_error = RuntimeError("tracking down")
    expected_result = build_llm_provider_completion_result(content="From the call")
    call_count = 0

    async def call() -> LlmProviderCompletionResult:
        nonlocal call_count
        call_count += 1
        return expected_result

    with structlog.testing.capture_logs() as captured_log_events:
        track_call_result = await LaunchDarklyLlmConfigSourceService(
            launchdarkly_ai_sdk_stub
        ).track_call(_build_get_llm_config_result_with_payload(), build_auth_user(), call)

    assert track_call_result == expected_result
    assert call_count == 1
    assert [log_event["event"] for log_event in captured_log_events] == [
        "launchdarkly_llm_call_tracking_failed"
    ]


async def test_track_call_sdk_returns_without_running_handler_runs_call_untracked(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    launchdarkly_ai_sdk_stub.execute_and_track_is_handler_skipped = True
    expected_result = build_llm_provider_completion_result(content="From the call")
    call_count = 0

    async def call() -> LlmProviderCompletionResult:
        nonlocal call_count
        call_count += 1
        return expected_result

    track_call_result = await LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    ).track_call(_build_get_llm_config_result_with_payload(), build_auth_user(), call)

    assert track_call_result == expected_result
    assert call_count == 1


async def test_track_call_result_with_reason_returns_result_and_reports_error_without_warning(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    expected_result = build_llm_provider_completion_result(reason=LlmCallReasonType.MAX_TOKENS)
    call_count = 0

    async def call() -> LlmProviderCompletionResult:
        nonlocal call_count
        call_count += 1
        return expected_result

    with structlog.testing.capture_logs() as captured_log_events:
        track_call_result = await LaunchDarklyLlmConfigSourceService(
            launchdarkly_ai_sdk_stub
        ).track_call(_build_get_llm_config_result_with_payload(), build_auth_user(), call)

    assert track_call_result == expected_result
    assert call_count == 1
    assert len(launchdarkly_ai_sdk_stub.execute_and_track_handler_errors) == 1
    assert captured_log_events == []
