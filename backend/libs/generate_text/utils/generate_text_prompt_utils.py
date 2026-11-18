from libs.generate_text.constants import FORMAT_RULES_VARIABLE_NAME
from libs.generate_text.output_formats import BaseGenerateTextOutputFormat
from libs.generate_text.results import BuildPromptResult
from libs.llm.inputs import LlmSystemPromptInput


class GenerateTextPromptUtils:
    """Shapes a step's built prompt into what the LLM service takes."""

    @staticmethod
    def build_system_prompt_input(
        build_prompt_result: BuildPromptResult, output_format: BaseGenerateTextOutputFormat | None
    ) -> LlmSystemPromptInput:
        """Returns the system prompt input; a step with an output format also gets its rules."""
        system_prompt_variables = dict(build_prompt_result.system_prompt_variables)
        required_variable_names: frozenset[str] = frozenset()
        if output_format is not None:
            # A served template must keep the rules, or the output check would be unexplained
            system_prompt_variables[FORMAT_RULES_VARIABLE_NAME] = output_format.format_rules
            required_variable_names = frozenset({FORMAT_RULES_VARIABLE_NAME})
        return LlmSystemPromptInput(
            default_template=build_prompt_result.system_prompt_template,
            variables=system_prompt_variables,
            required_variable_names=required_variable_names,
        )
