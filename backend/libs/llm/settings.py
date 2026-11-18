from decimal import Decimal
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from libs.llm.types import LlmProviderType, LlmReasoningEffortType

ALL_REASONING_EFFORTS = frozenset(LlmReasoningEffortType)
REASONING_EFFORTS_WITHOUT_NONE = ALL_REASONING_EFFORTS - {LlmReasoningEffortType.NONE}
REASONING_EFFORTS_WITHOUT_MAX = ALL_REASONING_EFFORTS - {LlmReasoningEffortType.MAX}


class LlmModelSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    provider: LlmProviderType
    model_name: str
    max_output_tokens: int
    request_timeout_seconds: int
    # None omits it, so the model's own default applies
    reasoning_effort: LlmReasoningEffortType | None = None
    accepted_reasoning_efforts: frozenset[LlmReasoningEffortType]
    input_usd_per_million_tokens: Decimal
    cached_input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal

    @model_validator(mode="after")
    def validate_reasoning_effort_is_accepted(self) -> Self:
        """Rejects a reasoning_effort the model doesn't accept."""
        if (
            self.reasoning_effort is not None
            and self.reasoning_effort not in self.accepted_reasoning_efforts
        ):
            raise ValueError(
                f"reasoning_effort {self.reasoning_effort} is not accepted by {self.model_name}"
            )
        return self


class BaseOpenAiLlmModelSettings(LlmModelSettings):
    """The defaults every OpenAI model shares unless its own class says otherwise."""

    provider: LlmProviderType = LlmProviderType.OPENAI
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 120
    accepted_reasoning_efforts: frozenset[LlmReasoningEffortType] = ALL_REASONING_EFFORTS


# One class per model, so one value can be overridden alone (LLM__GPT_5_6_SOL__MAX_OUTPUT_TOKENS).
# model_name is a Literal: the prices belong to that model, so an override can't swap it
class Gpt54NanoLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-5.4-nano"] = "gpt-5.4-nano"
    request_timeout_seconds: int = 30
    reasoning_effort: LlmReasoningEffortType | None = LlmReasoningEffortType.LOW
    accepted_reasoning_efforts: frozenset[LlmReasoningEffortType] = REASONING_EFFORTS_WITHOUT_MAX
    input_usd_per_million_tokens: Decimal = Decimal("0.20")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.02")
    output_usd_per_million_tokens: Decimal = Decimal("1.25")


class Gpt56LunaLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-5.6-luna"] = "gpt-5.6-luna"
    input_usd_per_million_tokens: Decimal = Decimal("0.20")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.02")
    output_usd_per_million_tokens: Decimal = Decimal("1.20")


class Gpt56TerraLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-5.6-terra"] = "gpt-5.6-terra"
    input_usd_per_million_tokens: Decimal = Decimal("2.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.20")
    output_usd_per_million_tokens: Decimal = Decimal("12.00")


class Gpt56SolLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-5.6-sol"] = "gpt-5.6-sol"
    max_output_tokens: int = 4096
    input_usd_per_million_tokens: Decimal = Decimal("4.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.40")
    output_usd_per_million_tokens: Decimal = Decimal("20.00")


class Gpt6LunaLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-6-luna"] = "gpt-6-luna"
    input_usd_per_million_tokens: Decimal = Decimal("0.10")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.01")
    output_usd_per_million_tokens: Decimal = Decimal("0.50")


class Gpt61TerraLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-6.1-terra"] = "gpt-6.1-terra"
    input_usd_per_million_tokens: Decimal = Decimal("1.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.05")
    output_usd_per_million_tokens: Decimal = Decimal("5.00")


class Gpt62SolLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-6.2-sol"] = "gpt-6.2-sol"
    accepted_reasoning_efforts: frozenset[LlmReasoningEffortType] = REASONING_EFFORTS_WITHOUT_NONE
    input_usd_per_million_tokens: Decimal = Decimal("2.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.10")
    output_usd_per_million_tokens: Decimal = Decimal("10.00")


class Gpt62AstraLlmModelSettings(BaseOpenAiLlmModelSettings):
    model_name: Literal["gpt-6.2-astra"] = "gpt-6.2-astra"
    accepted_reasoning_efforts: frozenset[LlmReasoningEffortType] = REASONING_EFFORTS_WITHOUT_NONE
    input_usd_per_million_tokens: Decimal = Decimal("8.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.40")
    output_usd_per_million_tokens: Decimal = Decimal("40.00")


class LlmSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    gpt_5_4_nano: Gpt54NanoLlmModelSettings = Field(default_factory=Gpt54NanoLlmModelSettings)
    gpt_5_6_luna: Gpt56LunaLlmModelSettings = Field(default_factory=Gpt56LunaLlmModelSettings)
    gpt_5_6_terra: Gpt56TerraLlmModelSettings = Field(default_factory=Gpt56TerraLlmModelSettings)
    gpt_5_6_sol: Gpt56SolLlmModelSettings = Field(default_factory=Gpt56SolLlmModelSettings)
    gpt_6_luna: Gpt6LunaLlmModelSettings = Field(default_factory=Gpt6LunaLlmModelSettings)
    gpt_6_1_terra: Gpt61TerraLlmModelSettings = Field(default_factory=Gpt61TerraLlmModelSettings)
    gpt_6_2_sol: Gpt62SolLlmModelSettings = Field(default_factory=Gpt62SolLlmModelSettings)
    gpt_6_2_astra: Gpt62AstraLlmModelSettings = Field(default_factory=Gpt62AstraLlmModelSettings)
    max_retries: int = 2
    retry_base_delay_seconds: float = 1.0
    retry_max_delay_seconds: float = 20.0
