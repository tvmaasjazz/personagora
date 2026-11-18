from collections.abc import Awaitable, Callable
from typing import Any


class LaunchDarklyAiSdkStub:
    """Stands in for the three launchdarkly_ai_server functions the config source calls."""

    def __init__(self) -> None:
        self.inspect_config_inputs: list[tuple[str, dict[str, Any]]] = []
        self.inspect_config_result: dict[str, Any] = {
            "enabled": False,
            "config": None,
            "meta": None,
        }
        self.create_handler_inputs: list[tuple[tuple[str, str], bool | None]] = []
        self.execute_and_track_inputs: list[dict[str, Any]] = []
        self.execute_and_track_handler_outputs: list[dict[str, Any]] = []
        self.execute_and_track_error: Exception | None = None
        # False raises before the handler runs, True raises after it returned
        self.execute_and_track_is_error_after_handler = False
        # Raised instead of the handler's own exception when the handler raises
        self.execute_and_track_replacement_error: Exception | None = None
        # True returns without running the handler
        self.execute_and_track_is_handler_skipped = False

    async def inspect_config(self, config_key: str, context: dict[str, Any]) -> dict[str, Any]:
        self.inspect_config_inputs.append((config_key, context))
        return self.inspect_config_result

    def create_handler(
        self,
        provider_and_mode: tuple[str, str],
        handler_function: Callable[..., Awaitable[dict[str, Any]]],
        *,
        capture_content: bool | None = None,
    ) -> Callable[..., Awaitable[dict[str, Any]]]:
        self.create_handler_inputs.append((provider_and_mode, capture_content))
        return handler_function

    async def execute_and_track(
        self,
        *,
        config_key: str,
        config: dict[str, Any],
        meta: dict[str, Any],
        user_context: dict[str, Any],
        handler: Callable[..., Awaitable[dict[str, Any]]],
    ) -> dict[str, Any]:
        self.execute_and_track_inputs.append(
            {
                "config_key": config_key,
                "config": config,
                "meta": meta,
                "user_context": user_context,
            }
        )
        if (
            self.execute_and_track_error is not None
            and not self.execute_and_track_is_error_after_handler
        ):
            raise self.execute_and_track_error
        if self.execute_and_track_is_handler_skipped:
            return {"usage": {}, "response": "", "track_data": {}}
        try:
            handler_output = await handler(config, "", {}, {}, [])
        except Exception:
            if self.execute_and_track_replacement_error is not None:
                raise self.execute_and_track_replacement_error from None
            raise
        self.execute_and_track_handler_outputs.append(handler_output)
        if self.execute_and_track_error is not None:
            raise self.execute_and_track_error
        return {"usage": {}, "response": "", "track_data": {}}
