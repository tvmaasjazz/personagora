import re

from libs.llm.exceptions import (
    LlmCancelledException,
    LlmContentFilteredException,
    LlmException,
    LlmFailedException,
    LlmNotFinishedException,
    LlmRateLimitedException,
    LlmRefusedException,
    LlmTruncatedException,
    LlmUnavailableException,
)
from libs.llm.types import LlmCallReasonType, LlmCallStatusType, LlmProviderType

# A call that produced no usable output is INCOMPLETE when the provider answered and FAILED
# when it didn't. Both maps must cover every LlmCallReasonType member.
LLM_STATUS_BY_REASON: dict[LlmCallReasonType, LlmCallStatusType] = {
    LlmCallReasonType.MAX_TOKENS: LlmCallStatusType.INCOMPLETE,
    LlmCallReasonType.CONTENT_FILTER: LlmCallStatusType.INCOMPLETE,
    LlmCallReasonType.REFUSAL: LlmCallStatusType.INCOMPLETE,
    LlmCallReasonType.PROVIDER_ERROR: LlmCallStatusType.FAILED,
    LlmCallReasonType.PROVIDER_UNAVAILABLE: LlmCallStatusType.FAILED,
    LlmCallReasonType.RATE_LIMITED: LlmCallStatusType.FAILED,
    LlmCallReasonType.CANCELLED: LlmCallStatusType.FAILED,
    LlmCallReasonType.NOT_FINISHED: LlmCallStatusType.FAILED,
}

LLM_EXCEPTION_BY_REASON: dict[LlmCallReasonType, type[LlmException]] = {
    LlmCallReasonType.MAX_TOKENS: LlmTruncatedException,
    LlmCallReasonType.CONTENT_FILTER: LlmContentFilteredException,
    LlmCallReasonType.REFUSAL: LlmRefusedException,
    LlmCallReasonType.PROVIDER_ERROR: LlmFailedException,
    LlmCallReasonType.PROVIDER_UNAVAILABLE: LlmUnavailableException,
    LlmCallReasonType.RATE_LIMITED: LlmRateLimitedException,
    LlmCallReasonType.CANCELLED: LlmCancelledException,
    LlmCallReasonType.NOT_FINISHED: LlmNotFinishedException,
}

PROMPT_TEMPLATE_PLACEHOLDER_PATTERN = re.compile(r"\{\{(\w+)\}\}")
# Any {{...}}, so one that isn't a valid placeholder can be found
PROMPT_TEMPLATE_BRACES_PATTERN = re.compile(r"\{\{.*?\}\}", re.DOTALL)

# The providers we have a service for, by the name LaunchDarkly gives them
LLM_PROVIDER_TYPE_BY_LAUNCHDARKLY_PROVIDER_NAME: dict[str, LlmProviderType] = {
    "OpenAI": LlmProviderType.OPENAI,
}

# The model parameters a served config may set
REASONING_EFFORT_PARAMETER_NAME = "reasoning_effort"
MAX_OUTPUT_TOKENS_PARAMETER_NAME = "max_output_tokens"
LLM_CONFIG_PARAMETER_NAMES = frozenset(
    {REASONING_EFFORT_PARAMETER_NAME, MAX_OUTPUT_TOKENS_PARAMETER_NAME}
)

# The role of the one message a served config may hold
SYSTEM_MESSAGE_ROLE = "system"
