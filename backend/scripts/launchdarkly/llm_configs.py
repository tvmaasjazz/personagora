"""The LaunchDarkly AI Configs the blog post steps read, one per config key."""

from pydantic import BaseModel

from libs.generate_text.graphs.blog_post.step_config import BLOG_POST_STEP_CONFIGS
from libs.generate_text.settings import GenerateTextSettings
from libs.llm.types import LlmType


class LlmConfigDeclaration(BaseModel):
    config_key: str
    name: str
    default_llm_type: LlmType
    system_template: str


# The seed targets remote environments, so it uses the code defaults, not the local .env
_GENERATE_TEXT_SETTINGS = GenerateTextSettings()

LLM_CONFIG_DECLARATIONS: list[LlmConfigDeclaration] = [
    LlmConfigDeclaration(
        config_key=llm_config_key,
        name=f"{step_config.llm_config_name} ({step_tier.value.lower()})",
        default_llm_type=step_config.read_standard_llm_type(_GENERATE_TEXT_SETTINGS),
        system_template=step_config.prompt.system_prompt_template,
    )
    for step_config in BLOG_POST_STEP_CONFIGS
    for step_tier, llm_config_key in step_config.llm_config_key_by_tier.items()
]
