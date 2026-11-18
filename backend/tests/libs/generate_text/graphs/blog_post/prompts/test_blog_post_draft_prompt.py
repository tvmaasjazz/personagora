from libs.generate_text.graphs.blog_post.blog_post_body_output_format import (
    BLOG_POST_BODY_FORMAT_RULES,
)
from libs.generate_text.graphs.blog_post.prompts import BlogPostDraftPrompt
from libs.llm.utils import PromptTemplateUtils
from tests.factories.generate_text import build_generate_text_state

EXPECTED_FORMAT_RULES = (
    "Write the post body in Markdown. Start with a single `# Title` line and nothing "
    "before it: no preamble, no restated instructions. Use exactly one H1, the title. "
    "An optional one-line subtitle may follow the title as a single italic line, e.g. "
    "`*A one-line subtitle.*`, and nothing else goes between the title and the body. "
    "Below it, use `##` and `###` headings only, and never skip a level (an H1 is "
    "followed by `##`, never straight to `###`). Paragraphs, bold and italic, lists, "
    "blockquotes, links, and code are all fine. Never use raw HTML, and never include "
    "images."
)


def test_build_generate_prompt_includes_format_rules_in_system_prompt() -> None:
    state = build_generate_text_state()

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert BLOG_POST_BODY_FORMAT_RULES in system_prompt


def test_build_generate_prompt_puts_persona_fields_in_system_prompt() -> None:
    state = build_generate_text_state(
        persona_name="Marta Quill",
        persona_bio="Writes about sourdough.",
        persona_background="Former baker.",
        persona_writing_style="Short punchy sentences.",
        persona_sample_writing="The starter bubbled all night.",
    )

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert "Marta Quill" in system_prompt
    assert "Writes about sourdough." in system_prompt
    assert "Former baker." in system_prompt
    assert "Short punchy sentences." in system_prompt
    assert "The starter bubbled all night." in system_prompt


def test_build_generate_prompt_puts_tone_and_target_audience_in_system_prompt() -> None:
    state = build_generate_text_state(tone="Playful", target_audience="Home bakers")

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert "Playful" in system_prompt
    assert "Home bakers" in system_prompt


def test_build_generate_prompt_omits_empty_tone_and_target_audience() -> None:
    state = build_generate_text_state(tone=None, target_audience=None)

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert "Tone:" not in system_prompt
    assert "Target audience:" not in system_prompt


def test_build_generate_prompt_puts_prompt_text_and_outline_in_user_prompt() -> None:
    state = build_generate_text_state(
        prompt_text="Write about sourdough starters.",
        step_outputs={"GENERATE_OUTLINE": "I. Intro II. Feeding schedule"},
    )

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    assert "Write about sourdough starters." in build_prompt_result.user_prompt
    assert "I. Intro II. Feeding schedule" in build_prompt_result.user_prompt


def test_build_generate_prompt_puts_additional_context_in_user_prompt() -> None:
    state = build_generate_text_state(additional_context="Reference: https://example.com/guide")

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    assert "Reference: https://example.com/guide" in build_prompt_result.user_prompt


def test_build_generate_prompt_omits_empty_additional_context() -> None:
    state = build_generate_text_state(additional_context=None)

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    assert "Additional context:" not in build_prompt_result.user_prompt


def test_build_rewrite_prompt_puts_brief_output_and_feedback_in_user_prompt() -> None:
    state = build_generate_text_state(prompt_text="Write about sourdough starters.")

    build_prompt_result = BlogPostDraftPrompt().build_rewrite_prompt(
        state, "A full draft about sourdough.", "Make it shorter."
    )

    assert "Write about sourdough starters." in build_prompt_result.user_prompt
    assert "A full draft about sourdough." in build_prompt_result.user_prompt
    assert "Make it shorter." in build_prompt_result.user_prompt


def test_build_rewrite_prompt_shares_generate_prompts_system_prompt() -> None:
    state = build_generate_text_state(persona_name="Marta Quill")

    generate_result = BlogPostDraftPrompt().build_generate_prompt(state)
    rewrite_result = BlogPostDraftPrompt().build_rewrite_prompt(state, "draft", "feedback")

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

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert system_prompt == (
        "Write a complete blog post draft from the outline and brief provided. Write the "
        "full prose, ready for review — not another outline.\n\n"
        + EXPECTED_FORMAT_RULES
        + "\n\nWho you are writing as:\n"
        "Name: Marta Quill\nBio: Writes about sourdough.\nBackground: Former baker.\n"
        "Writing style: Short punchy sentences.\nSample writing: The starter bubbled all night."
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

    build_prompt_result = BlogPostDraftPrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        build_prompt_result.system_prompt_variables,
    )
    assert system_prompt == (
        "Write a complete blog post draft from the outline and brief provided. Write the "
        "full prose, ready for review — not another outline.\n\n" + EXPECTED_FORMAT_RULES
    )
