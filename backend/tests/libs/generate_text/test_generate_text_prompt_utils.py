from libs.generate_text.results import BuildPromptResult
from libs.generate_text.utils import GenerateTextPromptUtils
from libs.llm.inputs import LlmSystemPromptInput


def test_build_system_prompt_input_without_output_format_requires_nothing() -> None:
    build_prompt_result = BuildPromptResult(
        system_prompt_template="Be {{style}}.",
        system_prompt_variables={"style": "brief"},
        user_prompt="Write.",
    )

    system_prompt_input = GenerateTextPromptUtils.build_system_prompt_input(
        build_prompt_result, has_output_format=False
    )

    assert system_prompt_input == LlmSystemPromptInput(
        default_template="Be {{style}}.",
        variables={"style": "brief"},
        required_variable_names=frozenset(),
    )


def test_build_system_prompt_input_with_output_format_requires_format_rules() -> None:
    build_prompt_result = BuildPromptResult(
        system_prompt_template="Follow {{format_rules}}.",
        system_prompt_variables={"format_rules": "Use markdown."},
        user_prompt="Write.",
    )

    system_prompt_input = GenerateTextPromptUtils.build_system_prompt_input(
        build_prompt_result, has_output_format=True
    )

    assert system_prompt_input == LlmSystemPromptInput(
        default_template="Follow {{format_rules}}.",
        variables={"format_rules": "Use markdown."},
        required_variable_names=frozenset({"format_rules"}),
    )
