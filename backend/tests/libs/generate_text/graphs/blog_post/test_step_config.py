import pytest

from libs.generate_text.graphs.blog_post.step_config import (
    BLOG_POST_DRAFT_STEP_CONFIG,
    BLOG_POST_HUMANIZE_STEP_CONFIG,
    BLOG_POST_OUTLINE_STEP_CONFIG,
    BLOG_POST_STEP_CONFIGS,
    BlogPostStepConfig,
)
from libs.generate_text.types import GenerateTextNodeType, GenerateTextStepTierType


@pytest.mark.parametrize(
    ("blog_post_step_config", "expected_llm_config_key"),
    [
        pytest.param(BLOG_POST_OUTLINE_STEP_CONFIG, "blog-post-outline-standard", id="outline"),
        pytest.param(BLOG_POST_DRAFT_STEP_CONFIG, "blog-post-draft-standard", id="draft"),
        pytest.param(BLOG_POST_HUMANIZE_STEP_CONFIG, "blog-post-humanize-standard", id="humanize"),
    ],
)
def test_blog_post_step_config_standard_tier_key_is_the_deployed_launchdarkly_key(
    blog_post_step_config: BlogPostStepConfig, expected_llm_config_key: str
) -> None:
    llm_config_key_by_tier = blog_post_step_config.llm_config_key_by_tier

    assert llm_config_key_by_tier == {GenerateTextStepTierType.STANDARD: expected_llm_config_key}


def test_blog_post_step_configs_are_listed_in_run_order() -> None:
    node_types = [step_config.node_type for step_config in BLOG_POST_STEP_CONFIGS]

    assert node_types == [
        GenerateTextNodeType.GENERATE_OUTLINE,
        GenerateTextNodeType.GENERATE_DRAFT,
        GenerateTextNodeType.HUMANIZE,
    ]
