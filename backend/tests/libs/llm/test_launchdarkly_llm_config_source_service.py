from typing import Any
from uuid import UUID

import pytest
import structlog

from libs.llm.results import (
    LlmConfigMessageResult,
    LlmConfigSourceResult,
    LlmProviderCompletionResult,
)
from libs.llm.services.launchdarkly_llm_config_source_service import (
    LaunchDarklyLlmConfigSourceService,
)
from libs.permissions.types import RoleType
from tests.factories.auth import build_auth_user
from tests.factories.llm import build_llm_config_source_result, build_llm_provider_completion_result
from tests.payloads.launchdarkly import build_launchdarkly_inspect_config_payload
from tests.stubs.launchdarkly import LaunchDarklyAiSdkStub

USER_IDENTITY = UUID("11111111-2222-3333-4444-555555555555")


@pytest.fixture
def launchdarkly_ai_sdk_stub() -> LaunchDarklyAiSdkStub:
    return LaunchDarklyAiSdkStub()


def _build_source_result_with_data() -> LlmConfigSourceResult:
    return build_llm_config_source_result(
        config_key="blog-post-draft-standard",
        provider_name="OpenAI",
        source_data={"config": {"model": "served"}, "meta": {"version": 3}},
    )


async def test_find_config_sends_identity_and_role_as_context(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    launchdarkly_ai_sdk_stub.inspect_config_result = build_launchdarkly_inspect_config_payload()
    auth_user = build_auth_user(user_identity=USER_IDENTITY, role=RoleType.CREATOR)

    launchdarkly_llm_config_source_service = LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    )
    await launchdarkly_llm_config_source_service.find_config("blog-post-draft-standard", auth_user)

    assert launchdarkly_ai_sdk_stub.inspect_config_inputs == [
        (
            "blog-post-draft-standard",
            {"kind": "user", "key": "11111111-2222-3333-4444-555555555555", "role": "CREATOR"},
        )
    ]


async def test_find_config_well_formed_payload_returns_source_result(
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

    find_config_result = await LaunchDarklyLlmConfigSourceService(
        launchdarkly_ai_sdk_stub
    ).find_config("blog-post-draft-standard", build_auth_user())

    assert find_config_result == LlmConfigSourceResult(
        config_key="blog-post-draft-standard",
        provider_name="OpenAI",
        model_name="gpt-5.4-nano",
        model_parameters={"reasoning_effort": "low"},
        messages=[LlmConfigMessageResult(role="system", content="Served.")],
        variation_key="variation-a",
        variation_version=3,
        source_data={
            "config": {
                "model": {"name": "gpt-5.4-nano", "parameters": {"reasoning_effort": "low"}},
                "provider": {"name": "OpenAI"},
                "messages": [{"role": "system", "content": "Served."}],
            },
            "meta": {"variationKey": "variation-a", "version": 3},
        },
    )


@pytest.mark.parametrize(
    ("payload_fields", "expected_reason"),
    [
        pytest.param({"is_enabled": False}, "not_enabled", id="not_enabled"),
        pytest.param({"has_config": False}, "config_or_meta_missing", id="config_missing"),
        pytest.param({"has_meta": False}, "config_or_meta_missing", id="meta_missing"),
        pytest.param(
            {"model_name": 5}, "field_missing_or_wrong_type", id="model_name_not_a_string"
        ),
        pytest.param(
            {"model_parameters": ["x"]}, "field_missing_or_wrong_type", id="parameters_not_a_dict"
        ),
        pytest.param(
            {"provider_name": None}, "field_missing_or_wrong_type", id="provider_name_missing"
        ),
        pytest.param({"messages": "text"}, "field_missing_or_wrong_type", id="messages_not_a_list"),
        pytest.param(
            {"variation_key": None}, "field_missing_or_wrong_type", id="variation_key_missing"
        ),
        pytest.param(
            {"variation_version": "3"},
            "field_missing_or_wrong_type",
            id="variation_version_not_an_int",
        ),
        pytest.param(
            {"variation_version": True},
            "field_missing_or_wrong_type",
            id="variation_version_a_bool",
        ),
        pytest.param(
            {"messages": [{"role": "system"}]}, "message_wrong_type", id="message_without_content"
        ),
        pytest.param({"messages": ["text"]}, "message_wrong_type", id="message_not_a_dict"),
    ],
)
async def test_find_config_unusable_payload_returns_none(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
    payload_fields: dict[str, Any],
    expected_reason: str,
) -> None:
    launchdarkly_ai_sdk_stub.inspect_config_result = build_launchdarkly_inspect_config_payload(
        **payload_fields
    )

    with structlog.testing.capture_logs() as captured_log_events:
        find_config_result = await LaunchDarklyLlmConfigSourceService(
            launchdarkly_ai_sdk_stub
        ).find_config("blog-post-draft-standard", build_auth_user())

    assert find_config_result is None
    assert captured_log_events == [
        {
            "event": "launchdarkly_llm_config_not_served",
            "log_level": "info",
            "config_key": "blog-post-draft-standard",
            "reason": expected_reason,
        }
    ]


async def test_track_call_returns_the_calls_result_and_reports_token_usage(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    llm_config_source_result = _build_source_result_with_data()
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
    llm_config_source_result = build_llm_config_source_result(
        provider_name="Anthropic", source_data={"config": {}, "meta": {}}
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


async def test_track_call_call_raises_propagates_unchanged(
    launchdarkly_ai_sdk_stub: LaunchDarklyAiSdkStub,
) -> None:
    async def call() -> LlmProviderCompletionResult:
        raise TimeoutError

    with pytest.raises(TimeoutError):
        launchdarkly_llm_config_source_service = LaunchDarklyLlmConfigSourceService(
            launchdarkly_ai_sdk_stub
        )
        await launchdarkly_llm_config_source_service.track_call(
            _build_source_result_with_data(), build_auth_user(), call
        )


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
        ).track_call(_build_source_result_with_data(), build_auth_user(), call)

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
        ).track_call(_build_source_result_with_data(), build_auth_user(), call)

    assert track_call_result == expected_result
    assert call_count == 1
    assert [log_event["event"] for log_event in captured_log_events] == [
        "launchdarkly_llm_call_tracking_failed"
    ]
