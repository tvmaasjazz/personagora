"""The LaunchDarkly AI Configs the blog post steps read, one per config key."""

from pydantic import BaseModel

from libs.generate_text.constants import BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER
from libs.generate_text.graphs.blog_post.prompts.blog_post_draft_prompt import (
    DRAFT_SYSTEM_TEMPLATE,
)
from libs.generate_text.graphs.blog_post.prompts.blog_post_humanize_prompt import (
    HUMANIZE_SYSTEM_TEMPLATE,
)
from libs.generate_text.graphs.blog_post.prompts.blog_post_outline_prompt import (
    OUTLINE_SYSTEM_TEMPLATE,
)
from libs.generate_text.settings import GenerateTextSettings
from libs.generate_text.types import GenerateTextNodeType, GenerateTextStepTierType
from libs.llm.types import LlmType


class LlmConfigDeclaration(BaseModel):
    config_key: str
    name: str
    default_llm_type: LlmType
    system_template: str


_STANDARD = GenerateTextStepTierType.STANDARD
_BLOG_POST_STEP_SETTINGS = GenerateTextSettings().blog_post

LLM_CONFIG_DECLARATIONS: list[LlmConfigDeclaration] = [
    LlmConfigDeclaration(
        config_key=BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER[
            (GenerateTextNodeType.GENERATE_OUTLINE, _STANDARD)
        ],
        name="Blog post outline (standard)",
        default_llm_type=_BLOG_POST_STEP_SETTINGS.outline.standard,
        system_template=OUTLINE_SYSTEM_TEMPLATE,
    ),
    LlmConfigDeclaration(
        config_key=BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER[
            (GenerateTextNodeType.GENERATE_DRAFT, _STANDARD)
        ],
        name="Blog post draft (standard)",
        default_llm_type=_BLOG_POST_STEP_SETTINGS.draft.standard,
        system_template=DRAFT_SYSTEM_TEMPLATE,
    ),
    LlmConfigDeclaration(
        config_key=BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER[
            (GenerateTextNodeType.HUMANIZE, _STANDARD)
        ],
        name="Blog post humanize (standard)",
        default_llm_type=_BLOG_POST_STEP_SETTINGS.humanize.standard,
        system_template=HUMANIZE_SYSTEM_TEMPLATE,
    ),
]
