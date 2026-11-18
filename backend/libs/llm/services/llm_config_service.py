from collections.abc import Awaitable, Callable

import structlog
from pydantic import ValidationError

from libs.auth.results import AuthUser
from libs.llm.constants import (
    LLM_CONFIG_PARAMETER_NAMES,
    LLM_PROVIDER_TYPE_BY_LAUNCHDARKLY_PROVIDER_NAME,
    SYSTEM_MESSAGE_ROLE,
)
from libs.llm.exceptions import LlmConfigRejectedException
from libs.llm.inputs import LlmCompletionInput
from libs.llm.results import (
    LlmConfigSourceResult,
    LlmProviderCompletionResult,
    ResolveLlmConfigResult,
)
from libs.llm.services.base_llm_config_source_service import BaseLlmConfigSourceService
from libs.llm.settings import LlmModelSettings, LlmSettings
from libs.llm.types import LlmReasoningEffortType, LlmType
from libs.llm.utils import PromptTemplateUtils

logger = structlog.get_logger(__name__)


class LlmConfigService:
    """Picks each call's model and system prompt from the config source, else the code default."""

    def __init__(
        self, llm_config_source_service: BaseLlmConfigSourceService, llm_settings: LlmSettings
    ) -> None:
        self._llm_config_source_service = llm_config_source_service
        self._model_settings_by_llm_type: dict[LlmType, LlmModelSettings] = {
            LlmType.GPT_5_4_NANO: llm_settings.gpt_5_4_nano,
            LlmType.GPT_5_6_LUNA: llm_settings.gpt_5_6_luna,
            LlmType.GPT_5_6_TERRA: llm_settings.gpt_5_6_terra,
            LlmType.GPT_5_6_SOL: llm_settings.gpt_5_6_sol,
            LlmType.GPT_6_LUNA: llm_settings.gpt_6_luna,
            LlmType.GPT_6_1_TERRA: llm_settings.gpt_6_1_terra,
            LlmType.GPT_6_2_SOL: llm_settings.gpt_6_2_sol,
            LlmType.GPT_6_2_ASTRA: llm_settings.gpt_6_2_astra,
        }

    async def resolve_config(
        self, llm_completion_input: LlmCompletionInput, auth_user: AuthUser
    ) -> ResolveLlmConfigResult:
        """Returns the served config when every check passes, else the call's code default."""
        llm_config_source_result = await self._llm_config_source_service.find_config(
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

    def find_model_settings(self, llm_type: LlmType) -> LlmModelSettings:
        """Returns the model's settings; NotImplementedError if the type has none."""
        model_settings = self._model_settings_by_llm_type.get(llm_type)
        if model_settings is None:
            raise NotImplementedError(f"No model configured for {llm_type}")
        return model_settings

    def _build_default_result(
        self, llm_completion_input: LlmCompletionInput
    ) -> ResolveLlmConfigResult:
        system_prompt_input = llm_completion_input.system_prompt
        return ResolveLlmConfigResult(
            config_key=llm_completion_input.config_key,
            model_settings=self.find_model_settings(llm_completion_input.default_llm_type),
            system_prompt=PromptTemplateUtils.render(
                system_prompt_input.default_template, system_prompt_input.variables
            ),
            variation_key=None,
            variation_version=None,
            llm_config_source_result=None,
        )

    def _build_served_result(
        self,
        llm_completion_input: LlmCompletionInput,
        llm_config_source_result: LlmConfigSourceResult,
    ) -> ResolveLlmConfigResult:
        """Returns the served config as a result; LlmConfigRejectedException if a check fails."""
        system_prompt_input = llm_completion_input.system_prompt

        # The provider must be one we have a service for
        provider = LLM_PROVIDER_TYPE_BY_LAUNCHDARKLY_PROVIDER_NAME.get(
            llm_config_source_result.provider_name
        )
        if provider is None:
            raise LlmConfigRejectedException("provider_not_allowed")

        # The model must be exactly one we price
        matching_model_settings = [
            model_settings
            for model_settings in self._model_settings_by_llm_type.values()
            if model_settings.provider == provider
            and model_settings.model_name == llm_config_source_result.model_name
        ]
        if len(matching_model_settings) != 1:
            raise LlmConfigRejectedException("model_not_allowed")
        model_settings = self._merge_parameters(
            matching_model_settings[0], llm_config_source_result.model_parameters
        )

        # The prompt must be one system message
        messages = llm_config_source_result.messages
        if len(messages) != 1 or messages[0].role != SYSTEM_MESSAGE_ROLE:
            raise LlmConfigRejectedException("messages_not_one_system_message")
        template = messages[0].content

        # The template must have a value for every placeholder and keep the required ones
        placeholder_names = PromptTemplateUtils.find_placeholder_names(template)
        if not placeholder_names <= system_prompt_input.variables.keys():
            raise LlmConfigRejectedException("placeholder_without_variable")
        if not system_prompt_input.required_variable_names <= placeholder_names:
            raise LlmConfigRejectedException("required_placeholder_missing")

        return ResolveLlmConfigResult(
            config_key=llm_completion_input.config_key,
            model_settings=model_settings,
            system_prompt=PromptTemplateUtils.render(template, system_prompt_input.variables),
            variation_key=llm_config_source_result.variation_key,
            variation_version=llm_config_source_result.variation_version,
            llm_config_source_result=llm_config_source_result,
        )

    def _merge_parameters(
        self, model_settings: LlmModelSettings, model_parameters: dict[str, object]
    ) -> LlmModelSettings:
        """Returns the model's settings with the served parameters laid over them."""
        if not model_parameters.keys() <= LLM_CONFIG_PARAMETER_NAMES:
            raise LlmConfigRejectedException("parameter_not_allowed")

        updates: dict[str, object] = {}
        for parameter_name, parameter_value in model_parameters.items():
            if parameter_name == "reasoning_effort":
                if not isinstance(parameter_value, str):
                    raise LlmConfigRejectedException("parameter_invalid")
                try:
                    updates[parameter_name] = LlmReasoningEffortType(parameter_value.upper())
                except ValueError as value_error:
                    raise LlmConfigRejectedException("parameter_invalid") from value_error
            else:
                updates[parameter_name] = parameter_value

        # Revalidate, since model_copy(update=) would skip the model's own checks
        try:
            return type(model_settings).model_validate({**model_settings.model_dump(), **updates})
        except (ValidationError, ValueError) as validation_error:
            raise LlmConfigRejectedException("parameter_invalid") from validation_error
