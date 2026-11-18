from typing import Any
from uuid import UUID

from pydantic import BaseModel

from libs.llm.settings import LlmModelSettings
from libs.llm.types import LlmCallReasonType


class LlmCompletionResult(BaseModel):
    llm_call_identity: UUID
    content: str
    input_tokens: int
    output_tokens: int


class LlmStructuredCompletionResult[T: BaseModel](BaseModel):
    llm_call_identity: UUID
    output: T
    input_tokens: int
    output_tokens: int


class CreatePendingLlmCallResult(BaseModel):
    llm_call_id: int
    llm_call_identity: UUID


class CompleteLlmCallResult(BaseModel):
    llm_call_identity: UUID
    provider_completion_result: LlmProviderCompletionResult


class LlmProviderCompletionResult(BaseModel):
    content: str
    parsed_output: BaseModel | None
    reason: LlmCallReasonType | None
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    provider_request_reference: str | None


class LlmConfigMessageResult(BaseModel):
    role: str
    content: str


class LlmConfigSourceResult(BaseModel):
    """A config as a source served it, before it's checked against what we can run."""

    config_key: str
    provider_name: str
    model_name: str
    model_parameters: dict[str, Any]
    messages: list[LlmConfigMessageResult]
    variation_key: str
    variation_version: int
    # What the source needs to report the call back; only that source reads it
    source_data: dict[str, Any]


class ResolveLlmConfigResult(BaseModel):
    config_key: str
    model_settings: LlmModelSettings
    system_prompt: str
    # None when the code default is used
    variation_key: str | None
    variation_version: int | None
    llm_config_source_result: LlmConfigSourceResult | None
