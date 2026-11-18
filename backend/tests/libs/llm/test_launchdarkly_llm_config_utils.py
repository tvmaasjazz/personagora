from typing import Any

import pytest
import structlog

from libs.llm.results import GetLlmConfigResult, LlmConfigMessageResult
from libs.llm.types import LlmProviderType, LlmReasoningEffortType
from libs.llm.utils import LaunchDarklyLlmConfigUtils
from tests.payloads.launchdarkly import build_launchdarkly_inspect_config_payload


def test_parse_config_well_formed_payload_returns_config_in_our_types() -> None:
    inspect_config_payload = build_launchdarkly_inspect_config_payload(
        model_name="gpt-5.4-nano",
        model_parameters={"reasoning_effort": "low", "max_output_tokens": 500},
        provider_name="OpenAI",
        messages=[{"role": "system", "content": "Served."}],
        variation_key="variation-a",
        variation_version=3,
    )

    parse_config_result = LaunchDarklyLlmConfigUtils.parse_config(
        "blog-post-draft-standard", inspect_config_payload
    )

    assert parse_config_result == GetLlmConfigResult(
        config_key="blog-post-draft-standard",
        provider=LlmProviderType.OPENAI,
        model_name="gpt-5.4-nano",
        reasoning_effort=LlmReasoningEffortType.LOW,
        max_output_tokens=500,
        messages=[LlmConfigMessageResult(role="system", content="Served.")],
        variation_key="variation-a",
        variation_version=3,
        source_payload={
            "config": {
                "model": {
                    "name": "gpt-5.4-nano",
                    "parameters": {"reasoning_effort": "low", "max_output_tokens": 500},
                },
                "provider": {"name": "OpenAI"},
                "messages": [{"role": "system", "content": "Served."}],
            },
            "meta": {"variationKey": "variation-a", "version": 3},
            "provider_name": "OpenAI",
        },
    )


def test_parse_config_no_parameters_returns_none_for_both() -> None:
    inspect_config_payload = build_launchdarkly_inspect_config_payload(model_parameters={})

    parse_config_result = LaunchDarklyLlmConfigUtils.parse_config(
        "blog-post-draft-standard", inspect_config_payload
    )

    assert parse_config_result is not None
    assert parse_config_result.reasoning_effort is None
    assert parse_config_result.max_output_tokens is None


@pytest.mark.parametrize(
    ("served_reasoning_effort", "expected_reasoning_effort"),
    [
        pytest.param("high", LlmReasoningEffortType.HIGH, id="lower_case"),
        pytest.param("HIGH", LlmReasoningEffortType.HIGH, id="upper_case"),
        pytest.param("Medium", LlmReasoningEffortType.MEDIUM, id="mixed_case"),
    ],
)
def test_parse_config_reasoning_effort_in_any_case_is_parsed(
    served_reasoning_effort: str, expected_reasoning_effort: LlmReasoningEffortType
) -> None:
    inspect_config_payload = build_launchdarkly_inspect_config_payload(
        model_parameters={"reasoning_effort": served_reasoning_effort}
    )

    parse_config_result = LaunchDarklyLlmConfigUtils.parse_config(
        "blog-post-draft-standard", inspect_config_payload
    )

    assert parse_config_result is not None
    assert parse_config_result.reasoning_effort == expected_reasoning_effort


@pytest.mark.parametrize(
    ("payload_fields", "expected_reason"),
    [
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
        pytest.param({"provider_name": "Anthropic"}, "provider_not_allowed", id="unknown_provider"),
        pytest.param(
            {"model_parameters": {"temperature": 0.5}},
            "parameter_not_allowed",
            id="unknown_parameter_key",
        ),
        pytest.param(
            {"model_parameters": {"reasoning_effort": 5}},
            "parameter_invalid",
            id="reasoning_effort_not_a_string",
        ),
        pytest.param(
            {"model_parameters": {"reasoning_effort": "extreme"}},
            "parameter_invalid",
            id="reasoning_effort_not_a_member",
        ),
        pytest.param(
            {"model_parameters": {"max_output_tokens": "500"}},
            "parameter_invalid",
            id="max_output_tokens_not_an_int",
        ),
        pytest.param(
            {"model_parameters": {"max_output_tokens": True}},
            "parameter_invalid",
            id="max_output_tokens_a_bool",
        ),
    ],
)
def test_parse_config_unusable_payload_returns_none_and_logs_reason_as_warning(
    payload_fields: dict[str, Any], expected_reason: str
) -> None:
    inspect_config_payload = build_launchdarkly_inspect_config_payload(**payload_fields)

    with structlog.testing.capture_logs() as captured_log_events:
        parse_config_result = LaunchDarklyLlmConfigUtils.parse_config(
            "blog-post-draft-standard", inspect_config_payload
        )

    assert parse_config_result is None
    assert captured_log_events == [
        {
            "event": "launchdarkly_llm_config_not_served",
            "log_level": "warning",
            "config_key": "blog-post-draft-standard",
            "reason": expected_reason,
        }
    ]


def test_parse_config_not_enabled_returns_none_and_logs_reason_as_info() -> None:
    inspect_config_payload = build_launchdarkly_inspect_config_payload(is_enabled=False)

    with structlog.testing.capture_logs() as captured_log_events:
        parse_config_result = LaunchDarklyLlmConfigUtils.parse_config(
            "blog-post-draft-standard", inspect_config_payload
        )

    assert parse_config_result is None
    assert captured_log_events == [
        {
            "event": "launchdarkly_llm_config_not_served",
            "log_level": "info",
            "config_key": "blog-post-draft-standard",
            "reason": "not_enabled",
        }
    ]
