from libs.generate_text.constants import (
    FORMAT_RULES_VARIABLE_NAME,
    PERSONA_SECTION_VARIABLE_NAME,
    TONE_AND_AUDIENCE_SECTION_VARIABLE_NAME,
)
from libs.generate_text.graphs.blog_post.blog_post_body_output_format import (
    BLOG_POST_BODY_FORMAT_RULES,
)
from libs.generate_text.prompts import BaseGenerateTextPrompt
from libs.generate_text.results import BuildPromptResult
from libs.generate_text.states import GenerateTextState

HUMANIZE_SYSTEM_TEMPLATE = (
    "Rewrite the given blog post draft so it reads like a person wrote it: vary "
    "sentence rhythm, cut filler and hedging, and remove anything that reads as "
    "AI-generated, while keeping the meaning and structure intact.\n\n{{format_rules}}"
    "{{persona_section}}{{tone_and_audience_section}}"
)

HUMANIZE_USER_TEMPLATE = "Draft:\n\n{draft_text}{additional_context_prompt_section}"

HUMANIZE_REWRITE_USER_TEMPLATE = (
    "Current humanized version:\n\n{previous_output}\n\n"
    "A reviewer left the following feedback. Rewrite it to address the feedback:\n\n{feedback_text}"
)


class BlogPostHumanizePrompt(BaseGenerateTextPrompt):
    """Prompts for rewriting the draft so it reads as human-written."""

    def build_generate_prompt(self, state: GenerateTextState) -> BuildPromptResult:
        """Puts the newest step output, the draft, in the user prompt."""
        additional_context_prompt_section = self._build_additional_context_prompt_section(
            state.additional_context
        )
        user_prompt = HUMANIZE_USER_TEMPLATE.format(
            draft_text=state.latest_output(),
            additional_context_prompt_section=additional_context_prompt_section,
        )
        return BuildPromptResult(
            system_prompt_template=HUMANIZE_SYSTEM_TEMPLATE,
            system_prompt_variables=self._build_system_prompt_variables(state),
            required_system_prompt_variable_names=frozenset({FORMAT_RULES_VARIABLE_NAME}),
            user_prompt=user_prompt,
        )

    def build_rewrite_prompt(
        self, state: GenerateTextState, previous_output: str, feedback_text: str
    ) -> BuildPromptResult:
        """Asks for the previous humanized version revised, leaving the brief out."""
        user_prompt = HUMANIZE_REWRITE_USER_TEMPLATE.format(
            previous_output=previous_output,
            feedback_text=feedback_text,
        )
        return BuildPromptResult(
            system_prompt_template=HUMANIZE_SYSTEM_TEMPLATE,
            system_prompt_variables=self._build_system_prompt_variables(state),
            required_system_prompt_variable_names=frozenset({FORMAT_RULES_VARIABLE_NAME}),
            user_prompt=user_prompt,
        )

    def _build_system_prompt_variables(self, state: GenerateTextState) -> dict[str, str]:
        persona = state.build_persona()
        persona_prompt_section = self._build_persona_prompt_section(
            persona, ["name", "writing_style", "sample_writing"]
        )
        tone_and_audience_prompt_section = self._build_tone_and_audience_prompt_section(
            state.tone, state.target_audience
        )
        return {
            FORMAT_RULES_VARIABLE_NAME: BLOG_POST_BODY_FORMAT_RULES,
            PERSONA_SECTION_VARIABLE_NAME: persona_prompt_section,
            TONE_AND_AUDIENCE_SECTION_VARIABLE_NAME: tone_and_audience_prompt_section,
        }
