from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from libs.llm.constants import (
    LLM_CONFIG_PARAMETER_NAMES,
    LLM_PROVIDER_TYPE_BY_LAUNCHDARKLY_PROVIDER_NAME,
    MAX_OUTPUT_TOKENS_PARAMETER_NAME,
    REASONING_EFFORT_PARAMETER_NAME,
)
from libs.llm.results import GetLlmConfigResult, LlmConfigMessageResult
from libs.llm.types import LlmReasoningEffortType

logger = structlog.get_logger(__name__)


# Strict, so a field of the wrong type is refused rather than coerced (a bool is not an int)
_STRICT_MODEL_CONFIG = ConfigDict(strict=True)

MESSAGES_FIELD_NAME = "messages"


# The pieces of the AI SDK's inspect_config payload that parse_config reads
class _LaunchDarklyMessageDto(BaseModel):
    model_config = _STRICT_MODEL_CONFIG

    role: str
    content: str


class _LaunchDarklyModelDto(BaseModel):
    model_config = _STRICT_MODEL_CONFIG

    name: str
    parameters: dict[str, Any] | None = None


class _LaunchDarklyProviderDto(BaseModel):
    model_config = _STRICT_MODEL_CONFIG

    name: str


class _LaunchDarklyConfigDto(BaseModel):
    model_config = _STRICT_MODEL_CONFIG

    model: _LaunchDarklyModelDto
    provider: _LaunchDarklyProviderDto
    messages: list[_LaunchDarklyMessageDto]


class _LaunchDarklyMetaDto(BaseModel):
    model_config = _STRICT_MODEL_CONFIG

    variation_key: str = Field(alias="variationKey")
    version: int


class _LaunchDarklyInspectConfigDto(BaseModel):
    model_config = _STRICT_MODEL_CONFIG

    config: _LaunchDarklyConfigDto
    meta: _LaunchDarklyMetaDto


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

        # Refuse a config with a field missing or of the wrong type
        try:
            inspect_config_dto = _LaunchDarklyInspectConfigDto.model_validate(inspect_config_result)
        except ValidationError as validation_error:
            # An error inside a message, not in the list itself or elsewhere
            is_message_error = all(
                len(error["loc"]) > 2 and error["loc"][:2] == ("config", MESSAGES_FIELD_NAME)
                for error in validation_error.errors()
            )
            reason = "message_wrong_type" if is_message_error else "field_missing_or_wrong_type"
            return LaunchDarklyLlmConfigUtils._not_served(config_key, reason)
        config_dto = inspect_config_dto.config
        meta_dto = inspect_config_dto.meta

        # Translate LaunchDarkly's spellings into ours
        llm_provider = LLM_PROVIDER_TYPE_BY_LAUNCHDARKLY_PROVIDER_NAME.get(config_dto.provider.name)
        if llm_provider is None:
            return LaunchDarklyLlmConfigUtils._not_served(config_key, "provider_not_allowed")
        model_parameters = config_dto.model.parameters or {}
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

        message_results = [
            LlmConfigMessageResult(role=message_dto.role, content=message_dto.content)
            for message_dto in config_dto.messages
        ]
        return GetLlmConfigResult(
            config_key=config_key,
            provider=llm_provider,
            model_name=config_dto.model.name,
            reasoning_effort=reasoning_effort,
            max_output_tokens=max_output_tokens,
            messages=message_results,
            variation_key=meta_dto.variation_key,
            variation_version=meta_dto.version,
            source_payload={
                "config": inspect_config_result["config"],
                "meta": inspect_config_result["meta"],
            },
        )

    @staticmethod
    def _not_served(config_key: str, reason: str) -> None:
        logger.warning("launchdarkly_llm_config_not_served", config_key=config_key, reason=reason)
