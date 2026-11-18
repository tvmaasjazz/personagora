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

DRAFT_SYSTEM_TEMPLATE = (
    "Write a complete blog post draft from the outline and brief provided. Write the "
    "full prose, ready for review — not another outline.\n\n{{format_rules}}"
    "{{persona_section}}{{tone_and_audience_section}}"
)

DRAFT_USER_TEMPLATE = (
    "Outline:\n\n{outline_text}\n\nBrief:\n\n{prompt_text}{additional_context_prompt_section}"
)

DRAFT_REWRITE_USER_TEMPLATE = (
    "Brief:\n\n{prompt_text}\n\n"
    "Current draft:\n\n{previous_output}\n\n"
    "A reviewer left the following feedback. Rewrite the draft to address it:\n\n{feedback_text}"
)


class BlogPostDraftPrompt(BaseGenerateTextPrompt):
    """Prompts for writing the full blog post draft from the outline and brief."""

    def build_generate_prompt(self, state: GenerateTextState) -> BuildPromptResult:
        """Puts the newest step output, normally the outline, in the user prompt."""
        additional_context_prompt_section = self._build_additional_context_prompt_section(
            state.additional_context
        )
        user_prompt = DRAFT_USER_TEMPLATE.format(
            outline_text=state.latest_output(),
            prompt_text=state.prompt_text,
            additional_context_prompt_section=additional_context_prompt_section,
        )
        return BuildPromptResult(
            system_prompt_template=DRAFT_SYSTEM_TEMPLATE,
            system_prompt_variables=self._build_system_prompt_variables(state),
            required_system_prompt_variable_names=frozenset({FORMAT_RULES_VARIABLE_NAME}),
            user_prompt=user_prompt,
        )

    def build_rewrite_prompt(
        self, state: GenerateTextState, previous_output: str, feedback_text: str
    ) -> BuildPromptResult:
        """Asks for the previous draft rewritten to address the reviewer's feedback."""
        user_prompt = DRAFT_REWRITE_USER_TEMPLATE.format(
            prompt_text=state.prompt_text,
            previous_output=previous_output,
            feedback_text=feedback_text,
        )
        return BuildPromptResult(
            system_prompt_template=DRAFT_SYSTEM_TEMPLATE,
            system_prompt_variables=self._build_system_prompt_variables(state),
            required_system_prompt_variable_names=frozenset({FORMAT_RULES_VARIABLE_NAME}),
            user_prompt=user_prompt,
        )

    def _build_system_prompt_variables(self, state: GenerateTextState) -> dict[str, str]:
        persona = state.build_persona()
        persona_prompt_section = self._build_persona_prompt_section(
            persona, ["name", "bio", "background", "writing_style", "sample_writing"]
        )
        tone_and_audience_prompt_section = self._build_tone_and_audience_prompt_section(
            state.tone, state.target_audience
        )
        return {
            FORMAT_RULES_VARIABLE_NAME: BLOG_POST_BODY_FORMAT_RULES,
            PERSONA_SECTION_VARIABLE_NAME: persona_prompt_section,
            TONE_AND_AUDIENCE_SECTION_VARIABLE_NAME: tone_and_audience_prompt_section,
        }
