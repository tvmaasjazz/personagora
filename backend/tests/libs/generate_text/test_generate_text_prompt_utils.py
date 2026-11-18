from libs.generate_text.results import BuildPromptResult
from libs.generate_text.utils import GenerateTextPromptUtils
from libs.llm.inputs import LlmSystemPromptInput
from tests.stubs.generate_text import GenerateTextOutputFormatStub


def test_build_system_prompt_input_with_output_format_adds_format_rules_and_requires_them() -> None:
    build_prompt_result = BuildPromptResult(
        system_prompt_template="Hi {{name}}. {{format_rules}}",
        system_prompt_variables={"name": "Ada"},
        user_prompt="Write.",
    )

    llm_system_prompt_input = GenerateTextPromptUtils.build_system_prompt_input(
        build_prompt_result, GenerateTextOutputFormatStub()
    )

    assert llm_system_prompt_input == LlmSystemPromptInput(
        default_template="Hi {{name}}. {{format_rules}}",
        variables={"name": "Ada", "format_rules": "Stub format rules."},
        required_variable_names=frozenset({"format_rules"}),
    )


def test_build_system_prompt_input_without_output_format_passes_variables_through() -> None:
    build_prompt_result = BuildPromptResult(
        system_prompt_template="Hi {{name}}.",
        system_prompt_variables={"name": "Ada"},
        user_prompt="Write.",
    )

    llm_system_prompt_input = GenerateTextPromptUtils.build_system_prompt_input(
        build_prompt_result, None
    )

    assert llm_system_prompt_input == LlmSystemPromptInput(
        default_template="Hi {{name}}.",
        variables={"name": "Ada"},
        required_variable_names=frozenset(),
    )


def test_build_system_prompt_input_leaves_the_build_prompt_result_unchanged() -> None:
    build_prompt_result = BuildPromptResult(
        system_prompt_template="{{format_rules}}",
        system_prompt_variables={"name": "Ada"},
        user_prompt="Write.",
    )

    GenerateTextPromptUtils.build_system_prompt_input(
        build_prompt_result, GenerateTextOutputFormatStub()
    )

    assert build_prompt_result.system_prompt_variables == {"name": "Ada"}
