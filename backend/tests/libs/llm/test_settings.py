import pytest
from pydantic import ValidationError

from libs.llm.settings import (
    Gpt56SolLlmModelSettings,
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


def test_gpt_5_6_sol_model_settings_different_model_name_raises_validation_error() -> None:
    with pytest.raises(ValidationError):
        Gpt56SolLlmModelSettings.model_validate({"model_name": "gpt-4o-mini"})


@pytest.mark.parametrize(
    "model_settings_class", [Gpt56SolLlmModelSettings, Gpt62SolLlmModelSettings]
)
@pytest.mark.parametrize(
    "max_output_tokens", [pytest.param(0, id="zero"), pytest.param(-1, id="negative")]
)
def test_llm_model_settings_non_positive_max_output_tokens_raises_validation_error(
    model_settings_class: type[Gpt56SolLlmModelSettings | Gpt62SolLlmModelSettings],
    max_output_tokens: int,
) -> None:
    with pytest.raises(ValidationError):
        model_settings_class(max_output_tokens=max_output_tokens)


def test_llm_model_settings_positive_max_output_tokens_is_accepted() -> None:
    llm_model_settings = Gpt56SolLlmModelSettings(max_output_tokens=1)

    assert llm_model_settings.max_output_tokens == 1
