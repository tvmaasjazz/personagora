from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import structlog

from libs.auth.results import AuthUser
from libs.llm.results import (
    GetLlmConfigResult,
    LlmProviderCompletionResult,
)
from libs.llm.services.base_llm_config_source_service import BaseLlmConfigSourceService
from libs.llm.utils import LaunchDarklyLlmConfigUtils

logger = structlog.get_logger(__name__)


class _NoUsableOutputException(Exception):
    """Raised inside the handler so LaunchDarkly counts a call with no usable output as an error."""


class LaunchDarklyAiSdkProtocol(Protocol):
    """The launchdarkly_ai_server functions this source calls; the module itself satisfies it."""

    async def inspect_config(self, config_key: str, context: dict[str, Any], /) -> dict[str, Any]:
        """Returns the config served to the context, never raising."""
        ...

    def create_handler(
        self,
        provides_for: tuple[str, Any],
        fn: Callable[..., Awaitable[dict[str, Any]]],
        /,
        *,
        capture_content: bool | None = None,
    ) -> Any:
        """Wraps fn as a provider handler."""
        ...

    async def execute_and_track(
        self,
        *,
        config_key: str,
        config: dict[str, Any],
        meta: dict[str, Any],
        user_context: dict[str, Any],
        handler: Any,
    ) -> dict[str, Any]:
        """Runs the handler and reports its duration, tokens and outcome."""
        ...


class LaunchDarklyLlmConfigSourceService(BaseLlmConfigSourceService):
    """Serves each call's config from LaunchDarkly AI Configs and reports the call back to it."""

    def __init__(self, launchdarkly_ai_sdk: LaunchDarklyAiSdkProtocol) -> None:
        self._launchdarkly_ai_sdk = launchdarkly_ai_sdk

    async def get_config(self, config_key: str, auth_user: AuthUser) -> GetLlmConfigResult | None:
        """Returns the config LaunchDarkly serves this user, or None when it serves none."""
        # Ask LaunchDarkly, which never raises
        inspect_config_result = await self._launchdarkly_ai_sdk.inspect_config(
            config_key, self._build_context(auth_user)
        )
        return LaunchDarklyLlmConfigUtils.parse_config(config_key, inspect_config_result)

    async def track_call(
        self,
        llm_config_source_result: GetLlmConfigResult,
        auth_user: AuthUser,
        call: Callable[[], Awaitable[LlmProviderCompletionResult]],
    ) -> LlmProviderCompletionResult:
        """Runs call and reports it to LaunchDarkly; a tracking failure never fails the call."""
        call_outcome: dict[str, Any] = {}

        async def run_call(
            config: Any, user_input: Any, tool_handlers: Any, variables: Any, history: Any
        ) -> dict[str, Any]:
            try:
                provider_completion_result = await call()
            except BaseException as call_exception:
                call_outcome["exception"] = call_exception
                raise
            call_outcome["result"] = provider_completion_result
            # A truncated, filtered, refused or unfinished call is an error to LaunchDarkly too
            if provider_completion_result.reason is not None:
                raise _NoUsableOutputException(str(provider_completion_result.reason))
            return {
                "output": "",
                "usage": {
                    "input_tokens": provider_completion_result.input_tokens,
                    "output_tokens": provider_completion_result.output_tokens,
                },
            }

        # The provider name comes from the served config, so a config for another provider
        # is still tracked
        provider_name = llm_config_source_result.source_payload["config"]["provider"]["name"]
        handler = self._launchdarkly_ai_sdk.create_handler(
            (provider_name, "messages"),
            run_call,
            capture_content=False,
        )
        try:
            await self._launchdarkly_ai_sdk.execute_and_track(
                config_key=llm_config_source_result.config_key,
                config=llm_config_source_result.source_payload["config"],
                meta=llm_config_source_result.source_payload["meta"],
                user_context=self._build_context(auth_user),
                handler=handler,
            )
        except Exception as tracking_exception:
            # The SDK re-raises the provider's own error, which isn't a tracking failure
            is_call_failure = isinstance(tracking_exception, _NoUsableOutputException) or (
                tracking_exception is call_outcome.get("exception")
            )
            if not is_call_failure:
                logger.warning(
                    "launchdarkly_llm_call_tracking_failed",
                    config_key=llm_config_source_result.config_key,
                    exc_info=True,
                )

        # The provider's own error or result wins over whatever the SDK did, and the paid
        # call never runs twice
        if "exception" in call_outcome:
            raise call_outcome["exception"]
        if "result" in call_outcome:
            return call_outcome["result"]
        # Tracking failed before the call started, so run it untracked
        return await call()

    def _build_context(self, auth_user: AuthUser) -> dict[str, Any]:
        return {"kind": "user", "key": str(auth_user.identity), "role": auth_user.role.value}
