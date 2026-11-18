import pytest
from pydantic import ValidationError

from libs.llm.settings import (
    Gpt62AstraLlmModelSettings,
    Gpt62SolLlmModelSettings,
)
from libs.llm.types import LlmReasoningEffortType
from tests.factories.llm import build_llm_model_settings


@pytest.mark.parametrize(
    ("reasoning_effort", "accepted_reasoning_efforts"),
    [
        pytest.param(None, frozenset({LlmReasoningEffortType.LOW}), id="none_is_always_accepted"),
        pytest.param(
            LlmReasoningEffortType.LOW,
            frozenset({LlmReasoningEffortType.LOW, LlmReasoningEffortType.HIGH}),
            id="effort_in_accepted_set",
        ),
    ],
)
def test_llm_model_settings_accepted_reasoning_effort_is_kept(
    reasoning_effort: LlmReasoningEffortType | None,
    accepted_reasoning_efforts: frozenset[LlmReasoningEffortType],
) -> None:
    llm_model_settings = build_llm_model_settings(
        reasoning_effort=reasoning_effort, accepted_reasoning_efforts=accepted_reasoning_efforts
    )

    assert llm_model_settings.reasoning_effort == reasoning_effort


def test_llm_model_settings_reasoning_effort_outside_accepted_set_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        build_llm_model_settings(
            reasoning_effort=LlmReasoningEffortType.MAX,
            accepted_reasoning_efforts=frozenset({LlmReasoningEffortType.LOW}),
        )


@pytest.mark.parametrize(
    "model_settings_class", [Gpt62SolLlmModelSettings, Gpt62AstraLlmModelSettings]
)
def test_gpt_6_2_model_settings_none_reasoning_effort_raises_validation_error(
    model_settings_class: type[Gpt62SolLlmModelSettings | Gpt62AstraLlmModelSettings],
) -> None:
    with pytest.raises(ValidationError):
        model_settings_class(reasoning_effort=LlmReasoningEffortType.NONE)


@pytest.mark.parametrize(
    "model_settings_class", [Gpt62SolLlmModelSettings, Gpt62AstraLlmModelSettings]
)
def test_gpt_6_2_model_settings_low_reasoning_effort_is_accepted(
    model_settings_class: type[Gpt62SolLlmModelSettings | Gpt62AstraLlmModelSettings],
) -> None:
    llm_model_settings = model_settings_class(reasoning_effort=LlmReasoningEffortType.LOW)

    assert llm_model_settings.reasoning_effort == LlmReasoningEffortType.LOW
