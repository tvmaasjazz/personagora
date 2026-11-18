from typing import Any
from uuid import UUID

from pydantic import BaseModel

from libs.llm.settings import LlmModelSettings
from libs.llm.types import LlmCallReasonType, LlmProviderType, LlmReasoningEffortType


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


class GetLlmConfigResult(BaseModel):
    """A config as a source served it, in our types, before it's checked against what we can run."""

    config_key: str
    provider: LlmProviderType
    model_name: str
    reasoning_effort: LlmReasoningEffortType | None
    max_output_tokens: int | None
    messages: list[LlmConfigMessageResult]
    variation_key: str
    variation_version: int
    # What the source needs to report the call back, in its own spellings; only that
    # source reads it
    source_payload: dict[str, Any]


class ResolveLlmConfigResult(BaseModel):
    config_key: str
    model_settings: LlmModelSettings
    system_prompt: str
    # None when the code default is used
    llm_config_source_result: GetLlmConfigResult | None

    @property
    def variation_key(self) -> str | None:
        """Returns the served variation's key, None when the code default is used."""
        if self.llm_config_source_result is None:
            return None
        return self.llm_config_source_result.variation_key

    @property
    def variation_version(self) -> int | None:
        """Returns the served variation's version, None when the code default is used."""
        if self.llm_config_source_result is None:
            return None
        return self.llm_config_source_result.variation_version
