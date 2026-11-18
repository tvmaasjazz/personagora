import structlog
from pydantic import BaseModel

from libs.auth.results import AuthUser
from libs.core.utils.date_time_utils import DateTimeUtils
from libs.llm.exceptions import LlmUnavailableException
from libs.llm.inputs import LlmCompletionInput, LlmProviderCompletionInput
from libs.llm.results import (
    CompleteLlmCallResult,
    LlmCompletionResult,
    LlmProviderCompletionResult,
    LlmStructuredCompletionResult,
)
from libs.llm.services.base_llm_provider_service import BaseLlmProviderService
from libs.llm.services.llm_call_service import LlmCallService
from libs.llm.services.llm_config_service import LlmConfigService
from libs.llm.types import LlmProviderType
from libs.llm.utils import LlmUtils

logger = structlog.get_logger(__name__)


class LlmService:
    """Runs completions on the provider each model is configured for and logs every call."""

    def __init__(
        self,
        llm_provider_services: dict[LlmProviderType, BaseLlmProviderService],
        llm_call_service: LlmCallService,
        llm_config_service: LlmConfigService,
    ) -> None:
        self._llm_provider_services = llm_provider_services
        self._llm_call_service = llm_call_service
        self._llm_config_service = llm_config_service

    async def complete(
        self, llm_completion_input: LlmCompletionInput, auth_user: AuthUser
    ) -> LlmCompletionResult:
        """Runs a free-text completion; an LlmException if the provider fails or stops early."""
        complete_llm_call_result = await self._complete(
            llm_completion_input, auth_user, output_type=None
        )
        provider_completion_result = complete_llm_call_result.provider_completion_result
        return LlmCompletionResult(
            llm_call_identity=complete_llm_call_result.llm_call_identity,
            content=provider_completion_result.content,
            input_tokens=provider_completion_result.input_tokens,
            output_tokens=provider_completion_result.output_tokens,
        )

    async def complete_structured[T: BaseModel](
        self,
        llm_completion_input: LlmCompletionInput,
        output_type: type[T],
        auth_user: AuthUser,
    ) -> LlmStructuredCompletionResult[T]:
        """Runs a completion parsed into output_type; LlmUnavailableException if none comes back."""
        complete_llm_call_result = await self._complete(
            llm_completion_input, auth_user, output_type=output_type
        )
        provider_completion_result = complete_llm_call_result.provider_completion_result
        if provider_completion_result.parsed_output is None:
            raise LlmUnavailableException("The model returned no structured output")

        return LlmStructuredCompletionResult[T](
            llm_call_identity=complete_llm_call_result.llm_call_identity,
            output=provider_completion_result.parsed_output,
            input_tokens=provider_completion_result.input_tokens,
            output_tokens=provider_completion_result.output_tokens,
        )

    async def _complete(
        self,
        llm_completion_input: LlmCompletionInput,
        auth_user: AuthUser,
        output_type: type[BaseModel] | None,
    ) -> CompleteLlmCallResult:
        # Resolve the model and system prompt, from the config source or the code default
        resolve_llm_config_result = await self._llm_config_service.resolve_config(
            llm_completion_input, auth_user
        )
        model_settings = resolve_llm_config_result.model_settings
        llm_provider_service = self._resolve_provider_service(model_settings.provider)

        create_pending_llm_call_result = await self._llm_call_service.create_pending_llm_call(
            llm_completion_input, resolve_llm_config_result, auth_user
        )
        llm_call_id = create_pending_llm_call_result.llm_call_id
        llm_call_identity = create_pending_llm_call_result.llm_call_identity

        provider_input = LlmProviderCompletionInput(
            model_name=model_settings.model_name,
            system_prompt=resolve_llm_config_result.system_prompt,
            user_prompt=llm_completion_input.user_prompt,
            max_output_tokens=model_settings.max_output_tokens,
            request_timeout_seconds=model_settings.request_timeout_seconds,
            reasoning_effort=model_settings.reasoning_effort,
        )

        start_time = DateTimeUtils.now_monotonic()
        try:
            provider_completion_result = await self._llm_config_service.track_call(
                resolve_llm_config_result,
                auth_user,
                lambda: self._complete_with_provider(
                    llm_provider_service, provider_input, output_type
                ),
            )
        except Exception as llm_provider_exception:
            duration_ms = DateTimeUtils.elapsed_ms(start_time)
            await self._llm_call_service.fail_llm_call(
                llm_call_id, llm_provider_exception, duration_ms, auth_user
            )
            raise
        duration_ms = DateTimeUtils.elapsed_ms(start_time)

        cost_usd = LlmUtils.compute_cost(
            model_settings,
            provider_completion_result.input_tokens,
            provider_completion_result.output_tokens,
            provider_completion_result.cached_input_tokens,
        )

        # Record the call before any exception leaves, so a call with no usable output is logged
        await self._llm_call_service.complete_llm_call(
            llm_call_id, provider_completion_result, cost_usd, duration_ms, auth_user
        )

        logger.info(
            "llm_call_completed",
            config_key=resolve_llm_config_result.config_key,
            config_variation_key=resolve_llm_config_result.variation_key,
            model_name=model_settings.model_name,
            purpose=llm_completion_input.purpose,
            input_tokens=provider_completion_result.input_tokens,
            output_tokens=provider_completion_result.output_tokens,
            cached_input_tokens=provider_completion_result.cached_input_tokens,
            reasoning_tokens=provider_completion_result.reasoning_tokens,
            cost_usd=cost_usd,
            duration_ms=duration_ms,
        )

        if provider_completion_result.reason is not None:
            raise LlmUtils.build_reason_exception(provider_completion_result.reason)

        return CompleteLlmCallResult(
            llm_call_identity=llm_call_identity,
            provider_completion_result=provider_completion_result,
        )

    async def _complete_with_provider(
        self,
        llm_provider_service: BaseLlmProviderService,
        provider_input: LlmProviderCompletionInput,
        output_type: type[BaseModel] | None,
    ) -> LlmProviderCompletionResult:
        if output_type is None:
            return await llm_provider_service.complete(provider_input)
        return await llm_provider_service.complete_structured(provider_input, output_type)

    def _resolve_provider_service(self, provider: LlmProviderType) -> BaseLlmProviderService:
        llm_provider_service = self._llm_provider_services.get(provider)
        if llm_provider_service is None:
            raise NotImplementedError(f"No provider service registered for {provider}")
        return llm_provider_service
