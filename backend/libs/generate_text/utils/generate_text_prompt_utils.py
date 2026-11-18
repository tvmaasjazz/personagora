from libs.generate_text.constants import FORMAT_RULES_VARIABLE_NAME
from libs.generate_text.results import BuildPromptResult
from libs.llm.inputs import LlmSystemPromptInput


class GenerateTextPromptUtils:
    """Shapes a step's built prompt into what an LLM call takes."""

    @staticmethod
    def build_system_prompt_input(
        build_prompt_result: BuildPromptResult, has_output_format: bool
    ) -> LlmSystemPromptInput:
        """Returns the input, requiring the format rules for a step with an output format."""
        return LlmSystemPromptInput(
            default_template=build_prompt_result.system_prompt_template,
            variables=build_prompt_result.system_prompt_variables,
            required_variable_names=(
                frozenset({FORMAT_RULES_VARIABLE_NAME}) if has_output_format else frozenset()
            ),
        )
