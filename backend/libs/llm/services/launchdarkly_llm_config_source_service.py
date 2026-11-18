from collections.abc import Awaitable, Callable
from typing import Any

import structlog
from launchdarkly_ai_server import (
    create_handler,
    execute_and_track,
    inspect_config,
)

from libs.auth.results import AuthUser
from libs.llm.results import (
    LlmConfigMessageResult,
    LlmConfigSourceResult,
    LlmProviderCompletionResult,
)
from libs.llm.services.base_llm_config_source_service import BaseLlmConfigSourceService

logger = structlog.get_logger(__name__)


class LaunchDarklyLlmConfigSourceService(BaseLlmConfigSourceService):
    """Serves each call's config from LaunchDarkly AI Configs and reports the call back to it."""

    async def find_config(
        self, config_key: str, auth_user: AuthUser
    ) -> LlmConfigSourceResult | None:
        """Returns the config LaunchDarkly serves this user, or None when it serves none."""
        # Ask LaunchDarkly, which never raises
        inspect_config_result = await inspect_config(config_key, self._build_context(auth_user))
        if not inspect_config_result.get("enabled"):
            self._log_not_served(config_key, "not_enabled")
            return None
        config = inspect_config_result.get("config")
        meta = inspect_config_result.get("meta")
        if not isinstance(config, dict) or not isinstance(meta, dict):
            self._log_not_served(config_key, "config_or_meta_missing")
            return None

        # Read the fields, refusing a config with one missing or of the wrong type
        model = config.get("model")
        provider = config.get("provider")
        messages = config.get("messages")
        variation_key = meta.get("variationKey")
        variation_version = meta.get("version")
        if (
            not isinstance(model, dict)
            or not isinstance(provider, dict)
            or not isinstance(messages, list)
            or not isinstance(variation_key, str)
            or not isinstance(variation_version, int)
            or isinstance(variation_version, bool)
        ):
            self._log_not_served(config_key, "field_missing_or_wrong_type")
            return None
        model_name = model.get("name")
        model_parameters = model.get("parameters") or {}
        provider_name = provider.get("name")
        if (
            not isinstance(model_name, str)
            or not isinstance(model_parameters, dict)
            or not isinstance(provider_name, str)
        ):
            self._log_not_served(config_key, "field_missing_or_wrong_type")
            return None
        message_results: list[LlmConfigMessageResult] = []
        for message in messages:
            if (
                not isinstance(message, dict)
                or not isinstance(message.get("role"), str)
                or not isinstance(message.get("content"), str)
            ):
                self._log_not_served(config_key, "message_wrong_type")
                return None
            message_results.append(
                LlmConfigMessageResult(role=message["role"], content=message["content"])
            )

        return LlmConfigSourceResult(
            config_key=config_key,
            provider_name=provider_name,
            model_name=model_name,
            model_parameters=model_parameters,
            messages=message_results,
            variation_key=variation_key,
            variation_version=variation_version,
            source_data={"config": config, "meta": meta},
        )

    async def track_call(
        self,
        llm_config_source_result: LlmConfigSourceResult,
        auth_user: AuthUser,
        call: Callable[[], Awaitable[LlmProviderCompletionResult]],
    ) -> LlmProviderCompletionResult:
        """Runs call and reports it to LaunchDarkly; a tracking failure never fails the call."""
        kept_results: list[LlmProviderCompletionResult] = []
        is_call_started = False

        async def run_call(
            config: Any, user_input: Any, tool_handlers: Any, variables: Any, history: Any
        ) -> dict[str, Any]:
            nonlocal is_call_started
            is_call_started = True
            provider_completion_result = await call()
            kept_results.append(provider_completion_result)
            return {
                "output": "",
                "usage": {
                    "input_tokens": provider_completion_result.input_tokens,
                    "output_tokens": provider_completion_result.output_tokens,
                },
            }

        # The provider name comes from the served config, so a config for another provider
        # is still tracked
        handler = create_handler(
            (llm_config_source_result.provider_name, "messages"),
            run_call,
            capture_content=False,
        )
        try:
            await execute_and_track(
                config_key=llm_config_source_result.config_key,
                config=llm_config_source_result.source_data["config"],
                meta=llm_config_source_result.source_data["meta"],
                user_context=self._build_context(auth_user),
                handler=handler,
            )
        except Exception:
            # call() raising is the caller's failure and propagates unchanged
            if is_call_started and not kept_results:
                raise
            logger.warning(
                "launchdarkly_llm_call_tracking_failed",
                config_key=llm_config_source_result.config_key,
                exc_info=True,
            )
        if not kept_results:
            # Tracking failed before the call ran, so run it untracked
            return await call()
        return kept_results[0]

    def _build_context(self, auth_user: AuthUser) -> dict[str, Any]:
        return {"kind": "user", "key": str(auth_user.identity), "role": auth_user.role.value}

    def _log_not_served(self, config_key: str, reason: str) -> None:
        logger.info("launchdarkly_llm_config_not_served", config_key=config_key, reason=reason)
