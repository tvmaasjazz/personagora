from pydantic import BaseModel

from libs.llm.types import LlmReasoningEffortType, LlmType


class LlmSystemPromptInput(BaseModel):
    # The code default, in {{name}} syntax; a config served by LaunchDarkly may replace it
    default_template: str
    variables: dict[str, str]
    # Placeholders a served template must keep, such as format_rules for a step whose
    # output is validated against those rules
    required_variable_names: frozenset[str] = frozenset()


class LlmCompletionInput(BaseModel):
    config_key: str
    default_llm_type: LlmType
    purpose: str
    system_prompt: LlmSystemPromptInput
    user_prompt: str
    run_id: int | None = None
    step_id: int | None = None


class LlmProviderCompletionInput(BaseModel):
    model_name: str
    system_prompt: str | None
    user_prompt: str
    max_output_tokens: int
    request_timeout_seconds: int
    reasoning_effort: LlmReasoningEffortType | None = None
