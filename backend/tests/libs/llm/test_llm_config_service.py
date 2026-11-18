from typing import Any

import pytest
import structlog

from libs.llm.results import (
    LlmConfigMessageResult,
    LlmProviderCompletionResult,
    ResolveLlmConfigResult,
)
from libs.llm.services.llm_config_service import LlmConfigService
from libs.llm.settings import (
    Gpt54NanoLlmModelSettings,
    Gpt62SolLlmModelSettings,
    LlmSettings,
)
from libs.llm.types import LlmReasoningEffortType, LlmType
from tests.factories.auth import build_auth_user
from tests.factories.llm import (
    build_get_llm_config_result,
    build_llm_completion_input,
    build_llm_provider_completion_result,
    build_llm_system_prompt_input,
    build_resolve_llm_config_result,
)
from tests.stubs.llm import LlmConfigSourceServiceStub


def _build_llm_config_service(
    llm_config_source_service_stub: LlmConfigSourceServiceStub,
) -> LlmConfigService:
    llm_settings = LlmSettings(gpt_5_4_nano=Gpt54NanoLlmModelSettings(max_output_tokens=1234))
    return LlmConfigService(
        llm_config_source_service=llm_config_source_service_stub, llm_settings=llm_settings
    )


def _build_default_resolve_llm_config_result(system_prompt: str) -> ResolveLlmConfigResult:
    return build_resolve_llm_config_result(
        config_key="test-config-key",
        model_settings=Gpt54NanoLlmModelSettings(max_output_tokens=1234),
        system_prompt=system_prompt,
    )


async def test_resolve_config_nothing_served_returns_code_default() -> None:
    llm_config_source_service_stub = LlmConfigSourceServiceStub()
    llm_config_service = _build_llm_config_service(llm_config_source_service_stub)
    auth_user = build_auth_user()
    llm_completion_input = build_llm_completion_input(
        config_key="test-config-key",
        default_llm_type=LlmType.GPT_5_4_NANO,
        system_prompt=build_llm_system_prompt_input(
            default_template="Hello {{name}} and {{other}}.", variables={"name": "Ada"}
        ),
    )

    resolve_config_result = await llm_config_service.resolve_config(llm_completion_input, auth_user)

    assert resolve_config_result == _build_default_resolve_llm_config_result(
        "Hello Ada and {{other}}."
    )
    assert llm_config_source_service_stub.get_config_inputs == [("test-config-key", auth_user)]


async def test_resolve_config_served_config_returns_served_model_and_prompt() -> None:
    llm_config_source_service_stub = LlmConfigSourceServiceStub()
    llm_config_source_result = build_get_llm_config_result(
        config_key="test-config-key",
        model_name="gpt-6.2-sol",
        messages=[LlmConfigMessageResult(role="system", content="Served for {{name}}.")],
    )
    llm_config_source_service_stub.get_config_result = llm_config_source_result
    llm_config_service = _build_llm_config_service(llm_config_source_service_stub)
    llm_completion_input = build_llm_completion_input(
        config_key="test-config-key",
        system_prompt=build_llm_system_prompt_input(
            default_template="Default.", variables={"name": "Ada"}
        ),
    )

    resolve_config_result = await llm_config_service.resolve_config(
        llm_completion_input, build_auth_user()
    )

    assert resolve_config_result == ResolveLlmConfigResult(
        config_key="test-config-key",
        model_settings=Gpt62SolLlmModelSettings(),
        system_prompt="Served for Ada.",
        llm_config_source_result=llm_config_source_result,
    )


async def test_resolve_config_reasoning_effort_overrides_model_default() -> None:
    llm_config_source_service_stub = LlmConfigSourceServiceStub()
    llm_config_source_service_stub.get_config_result = build_get_llm_config_result(
        model_name="gpt-5.4-nano", reasoning_effort=LlmReasoningEffortType.HIGH
    )
    llm_config_service = _build_llm_config_service(llm_config_source_service_stub)

    resolve_config_result = await llm_config_service.resolve_config(
        build_llm_completion_input(), build_auth_user()
    )

    assert resolve_config_result.model_settings == Gpt54NanoLlmModelSettings(
        max_output_tokens=1234, reasoning_effort=LlmReasoningEffortType.HIGH
    )


async def test_resolve_config_max_output_tokens_overrides_model_default() -> None:
    llm_config_source_service_stub = LlmConfigSourceServiceStub()
    llm_config_source_service_stub.get_config_result = build_get_llm_config_result(
        model_name="gpt-5.4-nano", max_output_tokens=999
    )
    llm_config_service = _build_llm_config_service(llm_config_source_service_stub)

    resolve_config_result = await llm_config_service.resolve_config(
        build_llm_completion_input(), build_auth_user()
    )

    assert resolve_config_result.model_settings == Gpt54NanoLlmModelSettings(max_output_tokens=999)


@pytest.mark.parametrize(
    ("source_result_fields", "default_template", "variables", "required_names", "expected_reason"),
    [
        pytest.param(
            {"model_name": "gpt-4"},
            "Hi.",
            {},
            frozenset[str](),
            "model_not_allowed",
            id="model_not_ours",
        ),
        pytest.param(
            {"model_name": "gpt-6.2-sol", "reasoning_effort": LlmReasoningEffortType.NONE},
            "Hi.",
            {},
            frozenset[str](),
            "parameter_invalid",
            id="reasoning_effort_none_not_accepted",
        ),
        pytest.param(
            {"model_name": "gpt-5.4-nano", "reasoning_effort": LlmReasoningEffortType.MAX},
            "Hi.",
            {},
            frozenset[str](),
            "parameter_invalid",
            id="reasoning_effort_max_not_accepted",
        ),
        pytest.param(
            {"max_output_tokens": 0},
            "Hi.",
            {},
            frozenset[str](),
            "parameter_invalid",
            id="max_output_tokens_not_positive",
        ),
        pytest.param(
            {
                "messages": [
                    LlmConfigMessageResult(role="system", content="One."),
                    LlmConfigMessageResult(role="system", content="Two."),
                ]
            },
            "Hi.",
            {},
            frozenset[str](),
            "messages_not_one_system_message",
            id="more_than_one_message",
        ),
        pytest.param(
            {"messages": [LlmConfigMessageResult(role="user", content="One.")]},
            "Hi.",
            {},
            frozenset[str](),
            "messages_not_one_system_message",
            id="non_system_message",
        ),
        pytest.param(
            {"messages": [LlmConfigMessageResult(role="system", content="Hi {{name}}.")]},
            "Hi.",
            {},
            frozenset[str](),
            "placeholder_without_variable",
            id="placeholder_without_variable",
        ),
        pytest.param(
            {"messages": [LlmConfigMessageResult(role="system", content="Hi {{ name }}.")]},
            "Hi.",
            {},
            frozenset[str](),
            "placeholder_malformed",
            id="placeholder_malformed",
        ),
        pytest.param(
            {"messages": [LlmConfigMessageResult(role="system", content="Hi.")]},
            "Hi {{name}}.",
            {"name": "Ada"},
            frozenset({"name"}),
            "required_placeholder_missing",
            id="required_placeholder_missing",
        ),
    ],
)
async def test_resolve_config_rejected_config_falls_back_to_code_default(
    source_result_fields: dict[str, Any],
    default_template: str,
    variables: dict[str, str],
    required_names: frozenset[str],
    expected_reason: str,
) -> None:
    llm_config_source_service_stub = LlmConfigSourceServiceStub()
    llm_config_source_service_stub.get_config_result = build_get_llm_config_result(
        config_key="test-config-key", variation_key="variation-a", **source_result_fields
    )
    llm_config_service = _build_llm_config_service(llm_config_source_service_stub)
    llm_completion_input = build_llm_completion_input(
        config_key="test-config-key",
        system_prompt=build_llm_system_prompt_input(
            default_template=default_template,
            variables=variables,
            required_variable_names=required_names,
        ),
    )

    with structlog.testing.capture_logs() as captured_log_events:
        resolve_config_result = await llm_config_service.resolve_config(
            llm_completion_input, build_auth_user()
        )

    expected_system_prompt = "Hi Ada." if "name" in variables else "Hi."
    assert resolve_config_result == _build_default_resolve_llm_config_result(expected_system_prompt)
    fallback_log_events = [
        log_event
        for log_event in captured_log_events
        if log_event["event"] == "llm_config_fallback"
    ]
    assert len(fallback_log_events) == 1
    assert fallback_log_events[0]["config_key"] == "test-config-key"
    assert fallback_log_events[0]["variation_key"] == "variation-a"
    assert fallback_log_events[0]["reason"] == expected_reason


async def test_track_call_without_source_result_awaits_call_and_skips_source() -> None:
    llm_config_source_service_stub = LlmConfigSourceServiceStub()
    llm_config_service = _build_llm_config_service(llm_config_source_service_stub)
    expected_result = build_llm_provider_completion_result(content="From the call")

    async def call() -> LlmProviderCompletionResult:
        return expected_result

    track_call_result = await llm_config_service.track_call(
        build_resolve_llm_config_result(llm_config_source_result=None), build_auth_user(), call
    )

    assert track_call_result == expected_result
    assert llm_config_source_service_stub.track_call_inputs == []


async def test_track_call_with_source_result_delegates_to_source() -> None:
    llm_config_source_service_stub = LlmConfigSourceServiceStub()
    llm_config_service = _build_llm_config_service(llm_config_source_service_stub)
    llm_config_source_result = build_get_llm_config_result()
    auth_user = build_auth_user()
    expected_result = build_llm_provider_completion_result(content="From the call")

    async def call() -> LlmProviderCompletionResult:
        return expected_result

    track_call_result = await llm_config_service.track_call(
        build_resolve_llm_config_result(llm_config_source_result=llm_config_source_result),
        auth_user,
        call,
    )

    assert track_call_result == expected_result
    assert llm_config_source_service_stub.track_call_inputs == [
        (llm_config_source_result, auth_user)
    ]
