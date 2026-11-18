from decimal import Decimal

from libs.llm.constants import LLM_EXCEPTION_BY_REASON, LLM_STATUS_BY_REASON
from libs.llm.exceptions import LlmException
from libs.llm.settings import LlmModelSettings
from libs.llm.types import LlmCallReasonType, LlmCallStatusType


class LlmUtils:
    """Maps a call's failure reason to its status and exception, and prices its tokens."""

    @staticmethod
    def resolve_status(reason: LlmCallReasonType | None) -> LlmCallStatusType:
        """Maps a call's failure reason to its status, SUCCEEDED when there is none."""
        if reason is None:
            return LlmCallStatusType.SUCCEEDED
        call_status = LLM_STATUS_BY_REASON.get(reason)
        if call_status is None:
            raise NotImplementedError(f"No status registered for {reason}")
        return call_status

    @staticmethod
    def build_reason_exception(reason: LlmCallReasonType) -> LlmException:
        """The exception to raise for a reason; NotImplementedError for one with none."""
        exception_class = LLM_EXCEPTION_BY_REASON.get(reason)
        if exception_class is None:
            raise NotImplementedError(f"No exception registered for {reason}")
        return exception_class()

    @staticmethod
    def compute_cost(
        model_settings: LlmModelSettings,
        input_tokens: int,
        output_tokens: int,
        cached_input_tokens: int,
    ) -> Decimal:
        """The call's cost in USD, priced from the model's own settings."""
        billed_input_tokens = input_tokens - cached_input_tokens
        million_tokens = Decimal(1_000_000)
        return (
            billed_input_tokens * model_settings.input_usd_per_million_tokens
            + cached_input_tokens * model_settings.cached_input_usd_per_million_tokens
            + output_tokens * model_settings.output_usd_per_million_tokens
        ) / million_tokens
