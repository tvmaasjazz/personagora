from typing import Any

import structlog

from libs.llm.constants import (
    LLM_CONFIG_PARAMETER_NAMES,
    LLM_PROVIDER_TYPE_BY_LAUNCHDARKLY_PROVIDER_NAME,
    MAX_OUTPUT_TOKENS_PARAMETER_NAME,
    REASONING_EFFORT_PARAMETER_NAME,
)
from libs.llm.results import GetLlmConfigResult, LlmConfigMessageResult
from libs.llm.types import LlmReasoningEffortType

logger = structlog.get_logger(__name__)


class LaunchDarklyLlmConfigUtils:
    """Translates a config LaunchDarkly served into our types."""

    @staticmethod
    def parse_config(
        config_key: str, inspect_config_result: dict[str, Any]
    ) -> GetLlmConfigResult | None:
        """Returns the served config in our types, or None (logged with why) when it can't be."""
        if not inspect_config_result.get("enabled"):
            logger.info(
                "launchdarkly_llm_config_not_served", config_key=config_key, reason="not_enabled"
            )
            return None
        config = inspect_config_result.get("config")
        meta = inspect_config_result.get("meta")
        if not isinstance(config, dict) or not isinstance(meta, dict):
            return LaunchDarklyLlmConfigUtils._not_served(config_key, "config_or_meta_missing")

        # Read the fields, refusing a config with one missing or of the wrong type
        model = config.get("model")
        provider = config.get("provider")
        messages = config.get("messages")
        variation_key = meta.get("variationKey")
        variation_version = meta.get("version")
        if (
            not isinstance(model, dict)
            or not isinstance(provider, dict)
            or not isinstance(messages, list)
            or not isinstance(variation_key, str)
            or not isinstance(variation_version, int)
            or isinstance(variation_version, bool)
        ):
            return LaunchDarklyLlmConfigUtils._not_served(config_key, "field_missing_or_wrong_type")
        model_name = model.get("name")
        model_parameters = model.get("parameters") or {}
        provider_name = provider.get("name")
        if (
            not isinstance(model_name, str)
            or not isinstance(model_parameters, dict)
            or not isinstance(provider_name, str)
        ):
            return LaunchDarklyLlmConfigUtils._not_served(config_key, "field_missing_or_wrong_type")
        message_results: list[LlmConfigMessageResult] = []
        for message in messages:
            if (
                not isinstance(message, dict)
                or not isinstance(message.get("role"), str)
                or not isinstance(message.get("content"), str)
            ):
                return LaunchDarklyLlmConfigUtils._not_served(config_key, "message_wrong_type")
            message_results.append(
                LlmConfigMessageResult(role=message["role"], content=message["content"])
            )

        # Translate LaunchDarkly's spellings into ours
        llm_provider = LLM_PROVIDER_TYPE_BY_LAUNCHDARKLY_PROVIDER_NAME.get(provider_name)
        if llm_provider is None:
            return LaunchDarklyLlmConfigUtils._not_served(config_key, "provider_not_allowed")
        if not model_parameters.keys() <= LLM_CONFIG_PARAMETER_NAMES:
            return LaunchDarklyLlmConfigUtils._not_served(config_key, "parameter_not_allowed")
        reasoning_effort: LlmReasoningEffortType | None = None
        reasoning_effort_value = model_parameters.get(REASONING_EFFORT_PARAMETER_NAME)
        if REASONING_EFFORT_PARAMETER_NAME in model_parameters:
            if not isinstance(reasoning_effort_value, str):
                return LaunchDarklyLlmConfigUtils._not_served(config_key, "parameter_invalid")
            try:
                reasoning_effort = LlmReasoningEffortType(reasoning_effort_value.upper())
            except ValueError:
                return LaunchDarklyLlmConfigUtils._not_served(config_key, "parameter_invalid")
        max_output_tokens = model_parameters.get(MAX_OUTPUT_TOKENS_PARAMETER_NAME)
        if MAX_OUTPUT_TOKENS_PARAMETER_NAME in model_parameters and (
            not isinstance(max_output_tokens, int) or isinstance(max_output_tokens, bool)
        ):
            return LaunchDarklyLlmConfigUtils._not_served(config_key, "parameter_invalid")

        return GetLlmConfigResult(
            config_key=config_key,
            provider=llm_provider,
            model_name=model_name,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
            messages=message_results,
            variation_key=variation_key,
            variation_version=variation_version,
            source_payload={"config": config, "meta": meta, "provider_name": provider_name},
        )

    @staticmethod
    def _not_served(config_key: str, reason: str) -> None:
        logger.warning("launchdarkly_llm_config_not_served", config_key=config_key, reason=reason)
