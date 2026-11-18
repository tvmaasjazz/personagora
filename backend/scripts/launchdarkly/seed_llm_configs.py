"""Creates the blog post steps' AI Configs in LaunchDarkly, create-only.

Each config gets a "default" variation holding the code default's model and system
template, served to everyone in the environment. Anything that already exists is left
alone. Needs LAUNCHDARKLY_API_TOKEN in backend/.env.launchdarkly or the environment.

Run from backend/:

    uv run python -m scripts.launchdarkly.seed_llm_configs --environment staging
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import dotenv_values

from apps.api.core.config import AppSettings
from libs.llm.services import LlmConfigService
from libs.llm.services.default_llm_config_source_service import DefaultLlmConfigSourceService
from scripts.launchdarkly.llm_configs import LLM_CONFIG_DECLARATIONS, LlmConfigDeclaration

API_BASE_URL = "https://app.launchdarkly.com/api/v2"
PROJECT_KEY = "personagora"
VARIATION_KEY = "default"
TOKEN_FILE = Path(".env.launchdarkly")
TOKEN_NAME = "LAUNCHDARKLY_API_TOKEN"
SEMANTIC_PATCH_CONTENT_TYPE = "application/json; domain-model=launchdarkly.semanticpatch"


def _parse_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argument_parser.add_argument(
        "--environment", required=True, help="LaunchDarkly environment key, e.g. staging"
    )
    return argument_parser.parse_args()


def _read_token() -> str:
    launchdarkly_api_token = os.environ.get(TOKEN_NAME) or (
        dotenv_values(TOKEN_FILE).get(TOKEN_NAME) or ""
    )
    if not launchdarkly_api_token:
        raise SystemExit(
            f"{TOKEN_NAME} is missing. Put {TOKEN_NAME}=<api access token> in "
            f"backend/{TOKEN_FILE}, or export it, then run again."
        )
    return launchdarkly_api_token


def _fail(http_response: httpx.Response, action: str) -> None:
    print(
        f"FAILED {action}: HTTP {http_response.status_code}\n{http_response.text}", file=sys.stderr
    )
    raise SystemExit(1)


def _expect(http_response: httpx.Response, action: str, ok_statuses: tuple[int, ...]) -> None:
    if http_response.status_code not in ok_statuses:
        _fail(http_response, action)


def _get_variations(config_body: dict[str, Any]) -> list[dict[str, Any]]:
    return config_body.get("variations") or []


def _seed_config(
    http_client: httpx.Client,
    declaration: LlmConfigDeclaration,
    model_name: str,
    environment: str,
) -> None:
    config_key = declaration.config_key
    config_url = f"/projects/{PROJECT_KEY}/ai-configs/{config_key}"

    # The config
    http_response = http_client.get(config_url)
    if http_response.status_code == 404:
        http_response = http_client.post(
            f"/projects/{PROJECT_KEY}/ai-configs",
            json={"key": config_key, "name": declaration.name, "mode": "completion"},
        )
        _expect(http_response, f"create config {config_key}", (200, 201))
        print(f"{config_key}: config created")
        config_body: dict[str, Any] = http_response.json()
    else:
        _expect(http_response, f"read config {config_key}", (200,))
        print(f"{config_key}: config exists")
        config_body = http_response.json()

    # The variation
    variations = _get_variations(config_body)
    if not variations:
        http_response = http_client.post(
            f"{config_url}/variations",
            json={
                "key": VARIATION_KEY,
                "name": f"Code default: {model_name}",
                "modelConfigKey": f"OpenAI.{model_name}",
                "model": {"name": model_name, "parameters": {}},
                "messages": [{"role": "system", "content": declaration.system_template}],
            },
        )
        _expect(http_response, f"create variation for {config_key}", (200, 201))
        print(f"{config_key}: variation '{VARIATION_KEY}' created")
        variation_body: dict[str, Any] = http_response.json()
        variation_id = _get_variation_id(variation_body)
    else:
        print(f"{config_key}: variation exists")
        variation_id = _get_variation_id(variations[0])

    # The environment's fallthrough
    http_response = http_client.get(f"{config_url}/targeting")
    _expect(http_response, f"read targeting for {config_key}", (200,))
    targeting_body = http_response.json()
    environments = targeting_body.get("environments") or {}
    environment_targeting = environments.get(environment)
    if environment_targeting is None:
        print(
            f"FAILED {config_key}: no environment '{environment}' in targeting "
            f"(found: {sorted(environments)})",
            file=sys.stderr,
        )
        raise SystemExit(1)
    fallthrough = environment_targeting.get("fallthrough") or {}
    # LaunchDarkly points a new config's fallthrough at its first variation itself
    fallthrough_index = fallthrough.get("variation")
    if fallthrough.get("rollout"):
        print(f"{config_key}: fallthrough in {environment} is a rollout, left alone")
        return
    if fallthrough_index is not None:
        targeting_variations = targeting_body.get("variations") or []
        served_name = (
            targeting_variations[fallthrough_index].get("name")
            if fallthrough_index < len(targeting_variations)
            else f"variation {fallthrough_index}"
        )
        print(f"{config_key}: fallthrough in {environment} serves '{served_name}'")
        return
    http_response = http_client.patch(
        f"{config_url}/targeting",
        headers={"Content-Type": SEMANTIC_PATCH_CONTENT_TYPE},
        json={
            "environmentKey": environment,
            "instructions": [
                {"kind": "updateFallthroughVariationOrRollout", "variationId": variation_id}
            ],
        },
    )
    _expect(http_response, f"set fallthrough for {config_key}", (200, 201))
    print(f"{config_key}: fallthrough set in {environment}")


def _get_variation_id(variation_body: dict[str, Any]) -> str:
    variation_id = variation_body.get("_id")
    if not isinstance(variation_id, str):
        print(f"FAILED: variation response has no _id: {variation_body}", file=sys.stderr)
        raise SystemExit(1)
    return variation_id


def main() -> None:
    arguments = _parse_arguments()
    launchdarkly_api_token = _read_token()
    llm_config_service = LlmConfigService(DefaultLlmConfigSourceService(), AppSettings().llm)
    print(f"Seeding {len(LLM_CONFIG_DECLARATIONS)} configs in {arguments.environment}")
    with httpx.Client(
        base_url=API_BASE_URL,
        headers={"Authorization": launchdarkly_api_token, "LD-API-Version": "beta"},
        timeout=30,
    ) as http_client:
        for declaration in LLM_CONFIG_DECLARATIONS:
            model_name = llm_config_service.get_model_settings(
                declaration.default_llm_type
            ).model_name
            _seed_config(http_client, declaration, model_name, arguments.environment)
    print("Done")


if __name__ == "__main__":
    main()
