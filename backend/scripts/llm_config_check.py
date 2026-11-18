"""Shows which model and system prompt each blog post step would run on right now.

Resolves each step's config the way a call does, for a sample user, and prints the
source, model, variation and rendered system prompt. Uses LaunchDarkly when
LAUNCHDARKLY__IS_ENABLED=true and LAUNCHDARKLY_SDK_KEY are set, else the code defaults.

Run from backend/:

    uv run python -m scripts.llm_config_check --role ADMIN
"""

import argparse
import asyncio
from uuid import UUID

from ldclient import LDClient

from apps.api.core.config import AppSettings
from apps.api.core.dependencies import build_llm_config_source_service
from apps.api.lifespan import connect_launchdarkly, disconnect_launchdarkly
from libs.auth.results import AuthUser
from libs.generate_text.constants import BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER
from libs.generate_text.graphs.blog_post.prompts.blog_post_draft_prompt import BlogPostDraftPrompt
from libs.generate_text.graphs.blog_post.prompts.blog_post_humanize_prompt import (
    BlogPostHumanizePrompt,
)
from libs.generate_text.graphs.blog_post.prompts.blog_post_outline_prompt import (
    BlogPostOutlinePrompt,
)
from libs.generate_text.prompts import BaseGenerateTextPrompt
from libs.generate_text.states import GenerateTextState
from libs.generate_text.types import GenerateTextNodeType, GenerateTextStepTierType
from libs.llm.inputs import LlmCompletionInput, LlmSystemPromptInput
from libs.llm.services import LlmConfigService
from libs.llm.types import LlmType
from libs.permissions.types import RoleType

SAMPLE_IDENTITY = "00000000-0000-4000-8000-000000000001"


def _parse_arguments() -> argparse.Namespace:
    argument_parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argument_parser.add_argument(
        "--identity", default=SAMPLE_IDENTITY, help="the sample user's identity (a UUID)"
    )
    argument_parser.add_argument(
        "--role", default=RoleType.ADMIN.value, help="the sample user's role, e.g. ADMIN"
    )
    return argument_parser.parse_args()


def _build_sample_state(auth_user: AuthUser) -> GenerateTextState:
    return GenerateTextState(
        auth_user_id=auth_user.id,
        auth_user_identity=auth_user.identity,
        auth_user_role=auth_user.role.value,
        auth_user_permissions=[],
        generate_text_run_id=1,
        generate_text_run_identity=UUID(SAMPLE_IDENTITY),
        graph_version="check",
        text_type="BLOG_POST",
        prompt_text="Why slow mornings make for better work",
        persona_name="Sample Persona",
        persona_bio="A sample persona for checking prompts.",
        persona_background="Ten years in product design.",
        persona_writing_style="Warm, plain-spoken, short paragraphs.",
        persona_sample_writing="I used to rush every morning. Then I stopped.",
        tone="Reflective",
        target_audience="Busy knowledge workers",
    )


async def _check() -> None:
    arguments = _parse_arguments()
    app_settings = AppSettings()
    auth_user = AuthUser(
        id=0,
        identity=UUID(arguments.identity),
        role=RoleType(arguments.role),
        permissions=frozenset(),
    )

    launchdarkly_client: LDClient | None = None
    if app_settings.launchdarkly.is_enabled:
        launchdarkly_client = await connect_launchdarkly(app_settings)
    else:
        print("LaunchDarkly is off (set LAUNCHDARKLY__IS_ENABLED=true); showing code defaults")
    llm_config_source_service = build_llm_config_source_service(app_settings)
    llm_config_service = LlmConfigService(llm_config_source_service, app_settings.llm)

    state = _build_sample_state(auth_user)
    step_tier = GenerateTextStepTierType.STANDARD
    step_settings = app_settings.generate_text.blog_post
    outline_llm_type = step_settings.outline.standard
    draft_llm_type = step_settings.draft.standard
    humanize_llm_type = step_settings.humanize.standard
    steps: list[tuple[GenerateTextNodeType, BaseGenerateTextPrompt, LlmType]] = [
        (GenerateTextNodeType.GENERATE_OUTLINE, BlogPostOutlinePrompt(), outline_llm_type),
        (GenerateTextNodeType.GENERATE_DRAFT, BlogPostDraftPrompt(), draft_llm_type),
        (GenerateTextNodeType.HUMANIZE, BlogPostHumanizePrompt(), humanize_llm_type),
    ]
    try:
        for node_type, prompt, default_llm_type in steps:
            config_key = BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER[(node_type, step_tier)]
            build_prompt_result = prompt.build_generate_prompt(state)
            llm_completion_input = LlmCompletionInput(
                config_key=config_key,
                default_llm_type=default_llm_type,
                purpose="llm_config_check",
                system_prompt=LlmSystemPromptInput(
                    default_template=build_prompt_result.system_prompt_template,
                    variables=build_prompt_result.system_prompt_variables,
                    required_variable_names=(
                        build_prompt_result.required_system_prompt_variable_names
                    ),
                ),
                user_prompt=build_prompt_result.user_prompt,
            )
            resolve_llm_config_result = await llm_config_service.resolve_config(
                llm_completion_input, auth_user
            )
            source_name = (
                "default" if resolve_llm_config_result.variation_key is None else "LaunchDarkly"
            )
            print(f"\n=== {config_key}")
            print(f"source:    {source_name}")
            print(f"model:     {resolve_llm_config_result.model_settings.model_name}")
            variation_key = resolve_llm_config_result.variation_key
            variation_version = resolve_llm_config_result.variation_version
            print(f"variation: {variation_key} (version {variation_version})")
            print(f"system prompt:\n{resolve_llm_config_result.system_prompt}")
    finally:
        if launchdarkly_client is not None:
            await disconnect_launchdarkly(launchdarkly_client)


if __name__ == "__main__":
    asyncio.run(_check())
