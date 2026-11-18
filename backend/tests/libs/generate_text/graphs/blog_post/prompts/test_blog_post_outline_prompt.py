from libs.generate_text.graphs.blog_post.blog_post_body_output_format import (
    BLOG_POST_BODY_FORMAT_RULES,
)
from libs.generate_text.graphs.blog_post.prompts import BlogPostOutlinePrompt
from libs.llm.utils import PromptTemplateUtils
from tests.factories.generate_text import build_generate_text_state


def test_build_generate_prompt_excludes_format_rules_from_system_prompt() -> None:
    state = build_generate_text_state()

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert BLOG_POST_BODY_FORMAT_RULES not in system_prompt


def test_build_generate_prompt_puts_used_persona_fields_in_system_prompt() -> None:
    state = build_generate_text_state(
        persona_name="Marta Quill",
        persona_bio="Writes about sourdough.",
        persona_background="Former baker.",
    )

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert "Marta Quill" in system_prompt
    assert "Writes about sourdough." in system_prompt
    assert "Former baker." in system_prompt


def test_build_generate_prompt_omits_field_the_step_does_not_use() -> None:
    state = build_generate_text_state(
        persona_writing_style="Short punchy sentences.",
        persona_sample_writing="The starter bubbled all night.",
    )

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert "Short punchy sentences." not in system_prompt
    assert "The starter bubbled all night." not in system_prompt


def test_build_generate_prompt_puts_tone_and_target_audience_in_system_prompt() -> None:
    state = build_generate_text_state(tone="Playful", target_audience="Home bakers")

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert "Playful" in system_prompt
    assert "Home bakers" in system_prompt


def test_build_generate_prompt_omits_empty_tone_and_target_audience() -> None:
    state = build_generate_text_state(tone=None, target_audience=None)

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert "Tone:" not in system_prompt
    assert "Target audience:" not in system_prompt


def test_build_generate_prompt_puts_prompt_text_in_user_prompt() -> None:
    state = build_generate_text_state(prompt_text="Write about sourdough starters.")

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    assert "Write about sourdough starters." in build_prompt_result.user_prompt


def test_build_generate_prompt_puts_additional_context_in_user_prompt() -> None:
    state = build_generate_text_state(additional_context="Reference: https://example.com/guide")

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    assert "Reference: https://example.com/guide" in build_prompt_result.user_prompt


def test_build_generate_prompt_omits_empty_additional_context() -> None:
    state = build_generate_text_state(additional_context=None)

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    assert "Additional context:" not in build_prompt_result.user_prompt


def test_build_rewrite_prompt_puts_brief_output_and_feedback_in_user_prompt() -> None:
    state = build_generate_text_state(prompt_text="Write about sourdough starters.")

    build_prompt_result = BlogPostOutlinePrompt().build_rewrite_prompt(
        state, "I. Intro II. Feeding schedule", "Add a section on hydration ratios."
    )

    assert "Write about sourdough starters." in build_prompt_result.user_prompt
    assert "I. Intro II. Feeding schedule" in build_prompt_result.user_prompt
    assert "Add a section on hydration ratios." in build_prompt_result.user_prompt


def test_build_rewrite_prompt_shares_generate_prompts_system_prompt() -> None:
    state = build_generate_text_state(persona_name="Marta Quill")

    generate_result = BlogPostOutlinePrompt().build_generate_prompt(state)
    rewrite_result = BlogPostOutlinePrompt().build_rewrite_prompt(state, "outline", "feedback")

    assert rewrite_result.system_prompt_template == generate_result.system_prompt_template
    assert rewrite_result.system_prompt_variables == generate_result.system_prompt_variables


def test_build_generate_prompt_renders_system_prompt_with_persona_and_tone() -> None:
    state = build_generate_text_state(
        persona_name="Marta Quill",
        persona_bio="Writes about sourdough.",
        persona_background="Former baker.",
        persona_writing_style="Short punchy sentences.",
        persona_sample_writing="The starter bubbled all night.",
        tone="Playful",
        target_audience="Home bakers",
    )

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert system_prompt == (
        "Write an outline for a blog post: the sections it will cover, the key point each "
        "one makes, and the order they build in. Keep it a plan, not the prose itself."
        + "\n\nWho you are writing as:\n"
        "Name: Marta Quill\nBio: Writes about sourdough.\nBackground: Former baker."
        + "\n\nFor this piece:\nTone: Playful\nTarget audience: Home bakers"
    )


def test_build_generate_prompt_renders_system_prompt_with_empty_persona_and_tone() -> None:
    state = build_generate_text_state(
        persona_name="",
        persona_bio="",
        persona_background=None,
        persona_writing_style=None,
        persona_sample_writing=None,
        tone=None,
        target_audience=None,
    )

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert system_prompt == (
        "Write an outline for a blog post: the sections it will cover, the key point each "
        "one makes, and the order they build in. Keep it a plan, not the prose itself."
    )


def test_build_generate_prompt_lists_required_system_prompt_variable_names() -> None:
    state = build_generate_text_state()

    build_prompt_result = BlogPostOutlinePrompt().build_generate_prompt(state)

    assert build_prompt_result.required_system_prompt_variable_names == frozenset()


def test_build_rewrite_prompt_lists_required_system_prompt_variable_names() -> None:
    state = build_generate_text_state()

    build_prompt_result = BlogPostOutlinePrompt().build_rewrite_prompt(
        state, "A draft.", "Make it shorter."
    )

    assert build_prompt_result.required_system_prompt_variable_names == frozenset()
