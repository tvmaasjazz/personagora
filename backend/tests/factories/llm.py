from decimal import Decimal
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from libs.database.orm.llm_call import LlmCallOrm
from libs.llm.inputs import (
    LlmCompletionInput,
    LlmProviderCompletionInput,
    LlmSystemPromptInput,
)
from libs.llm.results import (
    GetLlmConfigResult,
    LlmCompletionResult,
    LlmConfigMessageResult,
    LlmProviderCompletionResult,
    ResolveLlmConfigResult,
)
from libs.llm.settings import ALL_REASONING_EFFORTS, LlmModelSettings
from libs.llm.types import (
    LlmCallReasonType,
    LlmCallStatusType,
    LlmProviderType,
    LlmReasoningEffortType,
    LlmType,
)


def build_llm_system_prompt_input(
    *,
    default_template: str = "You are a helpful assistant.",
    variables: dict[str, str] | None = None,
    required_variable_names: frozenset[str] = frozenset(),
) -> LlmSystemPromptInput:
    return LlmSystemPromptInput(
        default_template=default_template,
        variables={} if variables is None else variables,
        required_variable_names=required_variable_names,
    )


def build_llm_completion_input(
    *,
    config_key: str = "test-config-key",
    default_llm_type: LlmType = LlmType.GPT_5_4_NANO,
    purpose: str = "test_purpose",
    system_prompt: LlmSystemPromptInput | None = None,
    user_prompt: str = "Say hello.",
    run_id: int | None = None,
    step_id: int | None = None,
) -> LlmCompletionInput:
    return LlmCompletionInput(
        config_key=config_key,
        default_llm_type=default_llm_type,
        purpose=purpose,
        system_prompt=build_llm_system_prompt_input() if system_prompt is None else system_prompt,
        user_prompt=user_prompt,
        run_id=run_id,
        step_id=step_id,
    )


def build_get_llm_config_result(
    *,
    config_key: str = "test-config-key",
    provider: LlmProviderType = LlmProviderType.OPENAI,
    model_name: str = "gpt-5.4-nano",
    reasoning_effort: LlmReasoningEffortType | None = None,
    max_output_tokens: int | None = None,
    messages: list[LlmConfigMessageResult] | None = None,
    variation_key: str = "test-variation",
    variation_version: int = 1,
    source_payload: dict[str, Any] | None = None,
) -> GetLlmConfigResult:
    return GetLlmConfigResult(
        config_key=config_key,
        provider=provider,
        model_name=model_name,
        reasoning_effort=reasoning_effort,
        max_output_tokens=max_output_tokens,
        messages=(
            [LlmConfigMessageResult(role="system", content="Served prompt.")]
            if messages is None
            else messages
        ),
        variation_key=variation_key,
        variation_version=variation_version,
        source_payload={} if source_payload is None else source_payload,
    )


def build_resolve_llm_config_result(
    *,
    config_key: str = "test-config-key",
    model_settings: LlmModelSettings | None = None,
    system_prompt: str = "You are a helpful assistant.",
    llm_config_source_result: GetLlmConfigResult | None = None,
) -> ResolveLlmConfigResult:
    return ResolveLlmConfigResult(
        config_key=config_key,
        model_settings=build_llm_model_settings() if model_settings is None else model_settings,
        system_prompt=system_prompt,
        llm_config_source_result=llm_config_source_result,
    )


def build_llm_provider_completion_input(
    *,
    model_name: str = "test-model",
    system_prompt: str | None = "You are a helpful assistant.",
    user_prompt: str = "Say hello.",
    max_output_tokens: int = 2048,
    request_timeout_seconds: int = 30,
    reasoning_effort: LlmReasoningEffortType | None = None,
) -> LlmProviderCompletionInput:
    return LlmProviderCompletionInput(
        model_name=model_name,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        max_output_tokens=max_output_tokens,
        request_timeout_seconds=request_timeout_seconds,
        reasoning_effort=reasoning_effort,
    )


def build_llm_completion_result(
    *,
    content: str = "Hello there.",
    input_tokens: int = 100,
    output_tokens: int = 50,
) -> LlmCompletionResult:
    return LlmCompletionResult(
        llm_call_identity=uuid4(),
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def build_llm_provider_completion_result(
    *,
    content: str = "Hello there.",
    parsed_output: BaseModel | None = None,
    reason: LlmCallReasonType | None = None,
    input_tokens: int = 100,
    output_tokens: int = 50,
    cached_input_tokens: int = 0,
    reasoning_tokens: int = 0,
    provider_request_reference: str | None = "req_stub",
) -> LlmProviderCompletionResult:
    return LlmProviderCompletionResult(
        content=content,
        parsed_output=parsed_output,
        reason=reason,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_input_tokens=cached_input_tokens,
        reasoning_tokens=reasoning_tokens,
        provider_request_reference=provider_request_reference,
    )


async def insert_llm_call_row(
    db_session: AsyncSession,
    *,
    created_by_id: int,
    run_id: int | None = None,
    step_id: int | None = None,
    provider: LlmProviderType = LlmProviderType.OPENAI,
    model_name: str = "test-model",
    purpose: str = "test_purpose",
    status: LlmCallStatusType = LlmCallStatusType.SUCCEEDED,
    input_tokens: int | None = 100,
    output_tokens: int | None = 50,
    cost_usd: Decimal | None = Decimal("0.01"),
) -> LlmCallOrm:
    llm_call_record = LlmCallOrm(
        provider=provider,
        model_name=model_name,
        purpose=purpose,
        system_prompt=None,
        user_prompt="Say hello.",
        status=status,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cost_usd=cost_usd,
        run_id=run_id,
        step_id=step_id,
        created_by_id=created_by_id,
        updated_by_id=created_by_id,
    )
    db_session.add(llm_call_record)
    await db_session.flush()
    return llm_call_record


def build_llm_model_settings(
    *,
    provider: LlmProviderType = LlmProviderType.OPENAI,
    model_name: str = "test-model",
    max_output_tokens: int = 2048,
    request_timeout_seconds: int = 30,
    reasoning_effort: LlmReasoningEffortType | None = None,
    accepted_reasoning_efforts: frozenset[LlmReasoningEffortType] = ALL_REASONING_EFFORTS,
    input_usd_per_million_tokens: Decimal = Decimal("2.00"),
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.50"),
    output_usd_per_million_tokens: Decimal = Decimal("8.00"),
) -> LlmModelSettings:
    return LlmModelSettings(
        provider=provider,
        model_name=model_name,
        max_output_tokens=max_output_tokens,
        request_timeout_seconds=request_timeout_seconds,
        reasoning_effort=reasoning_effort,
        accepted_reasoning_efforts=accepted_reasoning_efforts,
        input_usd_per_million_tokens=input_usd_per_million_tokens,
        cached_input_usd_per_million_tokens=cached_input_usd_per_million_tokens,
        output_usd_per_million_tokens=output_usd_per_million_tokens,
    )
