from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from libs.llm.types import LlmProviderType, LlmReasoningEffortType

ALL_REASONING_EFFORTS = frozenset(LlmReasoningEffortType)
REASONING_EFFORTS_WITHOUT_NONE = ALL_REASONING_EFFORTS - {LlmReasoningEffortType.NONE}


class LlmModelSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: LlmProviderType
    model_name: str
    max_output_tokens: int
    request_timeout_seconds: int
    # None omits it, so the model's own default applies
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType]
    input_usd_per_million_tokens: Decimal
    cached_input_usd_per_million_tokens: Decimal
    output_usd_per_million_tokens: Decimal

    @model_validator(mode="after")
    def validate_reasoning_effort_is_accepted(self) -> Self:
        """Rejects a reasoning_effort the model doesn't accept."""
        if (
            self.reasoning_effort is not None
            and self.reasoning_effort not in self.reasoning_efforts
        ):
            raise ValueError(
                f"reasoning_effort {self.reasoning_effort} is not accepted by {self.model_name}"
            )
        return self


# One class per model, so one value can be overridden alone (LLM__GPT_5_6_SOL__MAX_OUTPUT_TOKENS)
class Gpt54NanoLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-5.4-nano"
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 30
    reasoning_effort: LlmReasoningEffortType | None = LlmReasoningEffortType.LOW
    reasoning_efforts: frozenset[LlmReasoningEffortType] = frozenset(
        {
            LlmReasoningEffortType.NONE,
            LlmReasoningEffortType.LOW,
            LlmReasoningEffortType.MEDIUM,
            LlmReasoningEffortType.HIGH,
            LlmReasoningEffortType.XHIGH,
        }
    )
    input_usd_per_million_tokens: Decimal = Decimal("0.20")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.02")
    output_usd_per_million_tokens: Decimal = Decimal("1.25")


class Gpt56LunaLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-5.6-luna"
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 120
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType] = ALL_REASONING_EFFORTS
    input_usd_per_million_tokens: Decimal = Decimal("0.20")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.02")
    output_usd_per_million_tokens: Decimal = Decimal("1.20")


class Gpt56TerraLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-5.6-terra"
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 120
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType] = ALL_REASONING_EFFORTS
    input_usd_per_million_tokens: Decimal = Decimal("2.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.20")
    output_usd_per_million_tokens: Decimal = Decimal("12.00")


class Gpt56SolLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-5.6-sol"
    max_output_tokens: int = 4096
    request_timeout_seconds: int = 120
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType] = ALL_REASONING_EFFORTS
    input_usd_per_million_tokens: Decimal = Decimal("4.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.40")
    output_usd_per_million_tokens: Decimal = Decimal("20.00")


class Gpt6LunaLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-6-luna"
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 120
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType] = ALL_REASONING_EFFORTS
    input_usd_per_million_tokens: Decimal = Decimal("0.10")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.01")
    output_usd_per_million_tokens: Decimal = Decimal("0.50")


class Gpt61TerraLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-6.1-terra"
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 120
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType] = ALL_REASONING_EFFORTS
    input_usd_per_million_tokens: Decimal = Decimal("1.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.05")
    output_usd_per_million_tokens: Decimal = Decimal("5.00")


class Gpt62SolLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-6.2-sol"
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 120
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType] = REASONING_EFFORTS_WITHOUT_NONE
    input_usd_per_million_tokens: Decimal = Decimal("2.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.10")
    output_usd_per_million_tokens: Decimal = Decimal("10.00")


class Gpt62AstraLlmModelSettings(LlmModelSettings):
    provider: LlmProviderType = LlmProviderType.OPENAI
    model_name: str = "gpt-6.2-astra"
    max_output_tokens: int = 8192
    request_timeout_seconds: int = 120
    reasoning_effort: LlmReasoningEffortType | None = None
    reasoning_efforts: frozenset[LlmReasoningEffortType] = REASONING_EFFORTS_WITHOUT_NONE
    input_usd_per_million_tokens: Decimal = Decimal("8.00")
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.40")
    output_usd_per_million_tokens: Decimal = Decimal("40.00")


class LlmSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

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
