from collections.abc import Awaitable, Callable

from libs.auth.results import AuthUser
from libs.llm.results import GetLlmConfigResult, LlmProviderCompletionResult
from libs.llm.services.base_llm_config_source_service import BaseLlmConfigSourceService


class DefaultLlmConfigSourceService(BaseLlmConfigSourceService):
    """Serves nothing, so every call uses its code default; used when LaunchDarkly is off."""

    async def get_config(self, config_key: str, auth_user: AuthUser) -> GetLlmConfigResult | None:
        """Returns None, since this source serves no config."""
        return None

    async def track_call(
        self,
        llm_config_source_result: GetLlmConfigResult,
        auth_user: AuthUser,
        call: Callable[[], Awaitable[LlmProviderCompletionResult]],
    ) -> LlmProviderCompletionResult:
        """Runs call and reports nothing."""
        return await call()
