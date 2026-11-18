from collections.abc import Awaitable, Callable

import structlog
from pydantic import ValidationError

from libs.auth.results import AuthUser
from libs.llm.constants import SYSTEM_MESSAGE_ROLE
from libs.llm.exceptions import LlmConfigRejectedException
from libs.llm.inputs import LlmCompletionInput
from libs.llm.results import (
    GetLlmConfigResult,
    LlmProviderCompletionResult,
    ResolveLlmConfigResult,
)
from libs.llm.services.base_llm_config_source_service import BaseLlmConfigSourceService
from libs.llm.settings import LlmModelSettings, LlmSettings
from libs.llm.types import LlmReasoningEffortType
from libs.llm.utils import PromptTemplateUtils

logger = structlog.get_logger(__name__)


class LlmConfigService:
    """Picks each call's model and system prompt from the config source, else the code default."""

    def __init__(
        self, llm_config_source_service: BaseLlmConfigSourceService, llm_settings: LlmSettings
    ) -> None:
        self._llm_config_source_service = llm_config_source_service
        self._llm_settings = llm_settings

    async def resolve_config(
        self, llm_completion_input: LlmCompletionInput, auth_user: AuthUser
    ) -> ResolveLlmConfigResult:
        """Returns the served config when every check passes, else the call's code default."""
        llm_config_source_result = await self._llm_config_source_service.get_config(
            llm_completion_input.config_key, auth_user
        )
        if llm_config_source_result is None:
            return self._build_default_result(llm_completion_input)

        try:
            return self._build_served_result(llm_completion_input, llm_config_source_result)
        except LlmConfigRejectedException as llm_config_rejected_exception:
            logger.warning(
                "llm_config_fallback",
                config_key=llm_completion_input.config_key,
                variation_key=llm_config_source_result.variation_key,
                reason=str(llm_config_rejected_exception),
            )
            return self._build_default_result(llm_completion_input)

    async def track_call(
        self,
        resolve_llm_config_result: ResolveLlmConfigResult,
        auth_user: AuthUser,
        call: Callable[[], Awaitable[LlmProviderCompletionResult]],
    ) -> LlmProviderCompletionResult:
        """Runs call, reporting it to the source only when a served config produced it."""
        # A fallback is never reported against a variation it didn't run
        llm_config_source_result = resolve_llm_config_result.llm_config_source_result
        if llm_config_source_result is None:
            return await call()
        return await self._llm_config_source_service.track_call(
            llm_config_source_result, auth_user, call
        )

    def _build_default_result(
        self, llm_completion_input: LlmCompletionInput
    ) -> ResolveLlmConfigResult:
        system_prompt_input = llm_completion_input.system_prompt
        return ResolveLlmConfigResult(
            config_key=llm_completion_input.config_key,
            model_settings=self._llm_settings.get_model_settings(
                llm_completion_input.default_llm_type
            ),
            system_prompt=PromptTemplateUtils.render(
                system_prompt_input.default_template, system_prompt_input.variables
            ),
            llm_config_source_result=None,
        )

    def _build_served_result(
        self,
        llm_completion_input: LlmCompletionInput,
        llm_config_source_result: GetLlmConfigResult,
    ) -> ResolveLlmConfigResult:
        """Returns the served config as a result; LlmConfigRejectedException if a check fails."""
        system_prompt_input = llm_completion_input.system_prompt

        # The model must be exactly one we price
        matching_model_settings = self._llm_settings.get_model_settings_by_model_name(
            llm_config_source_result.provider, llm_config_source_result.model_name
        )
        if matching_model_settings is None:
            raise LlmConfigRejectedException("model_not_allowed")
        model_settings = self._overlay_parameters(
            matching_model_settings,
            llm_config_source_result.reasoning_effort,
            llm_config_source_result.max_output_tokens,
        )

        # The prompt must be one system message
        messages = llm_config_source_result.messages
        if len(messages) != 1 or messages[0].role != SYSTEM_MESSAGE_ROLE:
            raise LlmConfigRejectedException("messages_not_one_system_message")
        template = messages[0].content

        # The template must have a value for every placeholder and keep the required ones
        if PromptTemplateUtils.find_malformed_placeholders(template):
            raise LlmConfigRejectedException("placeholder_malformed")
        placeholder_names = PromptTemplateUtils.find_placeholder_names(template)
        if not placeholder_names <= system_prompt_input.variables.keys():
            raise LlmConfigRejectedException("placeholder_without_variable")
        if not system_prompt_input.required_variable_names <= placeholder_names:
            raise LlmConfigRejectedException("required_placeholder_missing")

        return ResolveLlmConfigResult(
            config_key=llm_completion_input.config_key,
            model_settings=model_settings,
            system_prompt=PromptTemplateUtils.render(template, system_prompt_input.variables),
            llm_config_source_result=llm_config_source_result,
        )

    def _overlay_parameters(
        self,
        model_settings: LlmModelSettings,
        reasoning_effort: LlmReasoningEffortType | None,
        max_output_tokens: int | None,
    ) -> LlmModelSettings:
        """Returns the model's settings with the served parameters laid over them."""
        updates: dict[str, object] = {}
        if reasoning_effort is not None:
            updates["reasoning_effort"] = reasoning_effort
        if max_output_tokens is not None:
            updates["max_output_tokens"] = max_output_tokens
        if not updates:
            return model_settings

        # Revalidate, since model_copy(update=) would skip the model's own checks
        try:
            return type(model_settings).model_validate({**model_settings.model_dump(), **updates})
        except (ValidationError, ValueError) as validation_error:
            raise LlmConfigRejectedException("parameter_invalid") from validation_error
