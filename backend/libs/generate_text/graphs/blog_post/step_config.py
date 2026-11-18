from collections.abc import Callable

from pydantic import BaseModel, ConfigDict

from libs.generate_text.graphs.blog_post.blog_post_body_output_format import (
    BlogPostBodyOutputFormat,
)
from libs.generate_text.graphs.blog_post.prompts import (
    BlogPostDraftPrompt,
    BlogPostHumanizePrompt,
    BlogPostOutlinePrompt,
)
from libs.generate_text.output_formats import BaseGenerateTextOutputFormat
from libs.generate_text.prompts import BaseGenerateTextPrompt
from libs.generate_text.settings import GenerateTextSettings
from libs.generate_text.types import GenerateTextNodeType, GenerateTextStepTierType
from libs.llm.types import LlmType


class BlogPostStepConfig(BaseModel):
    """Everything that varies between the blog post's generate steps, declared once."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    node_type: GenerateTextNodeType
    # The LaunchDarkly config's name, before the tier
    llm_config_name: str
    # These keys must match the LaunchDarkly configs the seed script creates
    llm_config_key_by_tier: dict[GenerateTextStepTierType, str]
    prompt: BaseGenerateTextPrompt
    output_format: BaseGenerateTextOutputFormat | None
    # Reads the standard tier's model from the settings, so an override still applies
    read_standard_llm_type: Callable[[GenerateTextSettings], LlmType]


BLOG_POST_OUTLINE_STEP_CONFIG = BlogPostStepConfig(
    node_type=GenerateTextNodeType.GENERATE_OUTLINE,
    llm_config_name="Blog post outline",
    llm_config_key_by_tier={GenerateTextStepTierType.STANDARD: "blog-post-outline-standard"},
    prompt=BlogPostOutlinePrompt(),
    output_format=None,
    read_standard_llm_type=lambda generate_text_settings: (
        generate_text_settings.blog_post.outline.standard
    ),
)

BLOG_POST_DRAFT_STEP_CONFIG = BlogPostStepConfig(
    node_type=GenerateTextNodeType.GENERATE_DRAFT,
    llm_config_name="Blog post draft",
    llm_config_key_by_tier={GenerateTextStepTierType.STANDARD: "blog-post-draft-standard"},
    prompt=BlogPostDraftPrompt(),
    output_format=BlogPostBodyOutputFormat(),
    read_standard_llm_type=lambda generate_text_settings: (
        generate_text_settings.blog_post.draft.standard
    ),
)

BLOG_POST_HUMANIZE_STEP_CONFIG = BlogPostStepConfig(
    node_type=GenerateTextNodeType.HUMANIZE,
    llm_config_name="Blog post humanize",
    llm_config_key_by_tier={GenerateTextStepTierType.STANDARD: "blog-post-humanize-standard"},
    prompt=BlogPostHumanizePrompt(),
    output_format=BlogPostBodyOutputFormat(),
    read_standard_llm_type=lambda generate_text_settings: (
        generate_text_settings.blog_post.humanize.standard
    ),
)

# In the order the steps run
BLOG_POST_STEP_CONFIGS = (
    BLOG_POST_OUTLINE_STEP_CONFIG,
    BLOG_POST_DRAFT_STEP_CONFIG,
    BLOG_POST_HUMANIZE_STEP_CONFIG,
)
