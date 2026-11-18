from enum import StrEnum


class LlmType(StrEnum):
    """The model a call runs on; LlmSettings holds each one's definition."""

    GPT_5_4_NANO = "GPT_5_4_NANO"
    GPT_5_6_LUNA = "GPT_5_6_LUNA"
    GPT_5_6_TERRA = "GPT_5_6_TERRA"
    GPT_5_6_SOL = "GPT_5_6_SOL"
    GPT_6_LUNA = "GPT_6_LUNA"
    GPT_6_1_TERRA = "GPT_6_1_TERRA"
    GPT_6_2_SOL = "GPT_6_2_SOL"
    GPT_6_2_ASTRA = "GPT_6_2_ASTRA"


class LlmProviderType(StrEnum):
    OPENAI = "OPENAI"
    ANTHROPIC = "ANTHROPIC"


class LlmReasoningEffortType(StrEnum):
    """How hard a reasoning model thinks; each provider maps it to its own values."""

    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    XHIGH = "XHIGH"
    MAX = "MAX"


class LlmCallStatusType(StrEnum):
    """The coarse outcome of a call."""

    PENDING = "PENDING"
    SUCCEEDED = "SUCCEEDED"
    INCOMPLETE = "INCOMPLETE"
    FAILED = "FAILED"


class LlmCallReasonType(StrEnum):
    """Why a call produced no usable output."""

    MAX_TOKENS = "MAX_TOKENS"
    CONTENT_FILTER = "CONTENT_FILTER"
    REFUSAL = "REFUSAL"
    PROVIDER_ERROR = "PROVIDER_ERROR"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    RATE_LIMITED = "RATE_LIMITED"
    CANCELLED = "CANCELLED"
    NOT_FINISHED = "NOT_FINISHED"
