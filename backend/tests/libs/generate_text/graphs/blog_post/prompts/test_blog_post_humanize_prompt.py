from libs.generate_text.graphs.blog_post.prompts import BlogPostHumanizePrompt
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


def test_build_generate_prompt_puts_used_persona_fields_in_system_prompt() -> None:
    state = build_generate_text_state(
        persona_name="Marta Quill",
        persona_writing_style="Short punchy sentences.",
        persona_sample_writing="The starter bubbled all night.",
    )

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        {**build_prompt_result.system_prompt_variables, "format_rules": EXPECTED_FORMAT_RULES},
    )
    assert "Marta Quill" in system_prompt
    assert "Short punchy sentences." in system_prompt
    assert "The starter bubbled all night." in system_prompt


def test_build_generate_prompt_omits_fields_the_step_does_not_use() -> None:
    state = build_generate_text_state(
        persona_bio="Writes about sourdough.",
        persona_background="Former baker.",
    )

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        {**build_prompt_result.system_prompt_variables, "format_rules": EXPECTED_FORMAT_RULES},
    )
    assert "Writes about sourdough." not in system_prompt
    assert "Former baker." not in system_prompt


def test_build_generate_prompt_puts_tone_and_target_audience_in_system_prompt() -> None:
    state = build_generate_text_state(tone="Playful", target_audience="Home bakers")

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        {**build_prompt_result.system_prompt_variables, "format_rules": EXPECTED_FORMAT_RULES},
    )
    assert "Playful" in system_prompt
    assert "Home bakers" in system_prompt


def test_build_generate_prompt_omits_empty_tone_and_target_audience() -> None:
    state = build_generate_text_state(tone=None, target_audience=None)

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        {**build_prompt_result.system_prompt_variables, "format_rules": EXPECTED_FORMAT_RULES},
    )
    assert "Tone:" not in system_prompt
    assert "Target audience:" not in system_prompt


def test_build_generate_prompt_puts_draft_in_user_prompt() -> None:
    state = build_generate_text_state(
        step_outputs={"GENERATE_DRAFT": "A full draft about sourdough."}
    )

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    assert "A full draft about sourdough." in build_prompt_result.user_prompt


def test_build_generate_prompt_puts_additional_context_in_user_prompt() -> None:
    state = build_generate_text_state(additional_context="Reference: https://example.com/guide")

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    assert "Reference: https://example.com/guide" in build_prompt_result.user_prompt


def test_build_generate_prompt_omits_empty_additional_context() -> None:
    state = build_generate_text_state(additional_context=None)

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    assert "Additional context:" not in build_prompt_result.user_prompt


def test_build_rewrite_prompt_puts_previous_output_and_feedback_in_user_prompt() -> None:
    state = build_generate_text_state(prompt_text="Write about sourdough starters.")

    build_prompt_result = BlogPostHumanizePrompt().build_rewrite_prompt(
        state, "A humanized draft.", "Sound less robotic."
    )

    assert "A humanized draft." in build_prompt_result.user_prompt
    assert "Sound less robotic." in build_prompt_result.user_prompt


def test_build_rewrite_prompt_omits_the_brief() -> None:
    state = build_generate_text_state(prompt_text="Write about sourdough starters.")

    build_prompt_result = BlogPostHumanizePrompt().build_rewrite_prompt(
        state, "A humanized draft.", "Sound less robotic."
    )

    assert "Write about sourdough starters." not in build_prompt_result.user_prompt


def test_build_rewrite_prompt_shares_generate_prompts_system_prompt() -> None:
    state = build_generate_text_state(persona_name="Marta Quill")

    generate_result = BlogPostHumanizePrompt().build_generate_prompt(state)
    rewrite_result = BlogPostHumanizePrompt().build_rewrite_prompt(state, "draft", "feedback")

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

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        {**build_prompt_result.system_prompt_variables, "format_rules": EXPECTED_FORMAT_RULES},
    )
    assert system_prompt == (
        "Rewrite the given blog post draft so it reads like a person wrote it: vary "
        "sentence rhythm, cut filler and hedging, and remove anything that reads as "
        "AI-generated, while keeping the meaning and structure intact.\n\n"
        + EXPECTED_FORMAT_RULES
        + "\n\nWho you are writing as:\n"
        "Name: Marta Quill\nWriting style: Short punchy sentences.\n"
        "Sample writing: The starter bubbled all night."
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

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    system_prompt = PromptTemplateUtils.render(
        build_prompt_result.system_prompt_template,
        {**build_prompt_result.system_prompt_variables, "format_rules": EXPECTED_FORMAT_RULES},
    )
    assert system_prompt == (
        "Rewrite the given blog post draft so it reads like a person wrote it: vary "
        "sentence rhythm, cut filler and hedging, and remove anything that reads as "
        "AI-generated, while keeping the meaning and structure intact.\n\n" + EXPECTED_FORMAT_RULES
    )


def test_build_generate_prompt_system_template_has_format_rules_placeholder() -> None:
    state = build_generate_text_state()

    build_prompt_result = BlogPostHumanizePrompt().build_generate_prompt(state)

    assert "{{format_rules}}" in build_prompt_result.system_prompt_template
    assert "format_rules" not in build_prompt_result.system_prompt_variables


def test_build_rewrite_prompt_system_template_has_format_rules_placeholder() -> None:
    state = build_generate_text_state()

    build_prompt_result = BlogPostHumanizePrompt().build_rewrite_prompt(
        state, "A draft.", "Make it shorter."
    )

    assert "{{format_rules}}" in build_prompt_result.system_prompt_template
    assert "format_rules" not in build_prompt_result.system_prompt_variables
