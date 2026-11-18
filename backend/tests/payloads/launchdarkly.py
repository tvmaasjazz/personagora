from typing import Any


def build_launchdarkly_inspect_config_payload(
    *,
    is_enabled: bool = True,
    has_config: bool = True,
    has_meta: bool = True,
    model_name: Any = "gpt-5.4-nano",
    model_parameters: Any = None,
    provider_name: Any = "OpenAI",
    messages: Any = None,
    variation_key: Any = "variation-a",
    variation_version: Any = 3,
) -> dict[str, Any]:
    config: dict[str, Any] | None = None
    if has_config:
        config = {
            "model": {
                "name": model_name,
                "parameters": {"reasoning_effort": "low"}
                if model_parameters is None
                else model_parameters,
            },
            "provider": {"name": provider_name},
            "messages": (
                [{"role": "system", "content": "Served {{persona_section}}."}]
                if messages is None
                else messages
            ),
        }
    meta: dict[str, Any] | None = None
    if has_meta:
        meta = {"variationKey": variation_key, "version": variation_version}
    return {"enabled": is_enabled, "config": config, "meta": meta}
