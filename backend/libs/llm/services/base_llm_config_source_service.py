from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from libs.auth.results import AuthUser
from libs.llm.results import LlmConfigSourceResult, LlmProviderCompletionResult


class BaseLlmConfigSourceService(ABC):
    """Serves a call's model and system prompt from outside the code, and reports the call back."""

    @abstractmethod
    async def find_config(
        self, config_key: str, auth_user: AuthUser
    ) -> LlmConfigSourceResult | None:
        """Returns the config served to this user, or None when the source serves nothing."""

    @abstractmethod
    async def track_call(
        self,
        llm_config_source_result: LlmConfigSourceResult,
        auth_user: AuthUser,
        call: Callable[[], Awaitable[LlmProviderCompletionResult]],
    ) -> LlmProviderCompletionResult:
        """Runs call and reports its outcome to the source; re-raises whatever call raises."""
