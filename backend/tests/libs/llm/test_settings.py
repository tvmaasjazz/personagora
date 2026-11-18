import pytest
from pydantic import ValidationError

from libs.llm.settings import (
    Gpt56SolLlmModelSettings,
    Gpt62AstraLlmModelSettings,
    Gpt62SolLlmModelSettings,
    LlmSettings,
)
from libs.llm.types import LlmProviderType, LlmReasoningEffortType, LlmType
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


@pytest.mark.parametrize(
    ("llm_type", "expected_model_name"),
    [
        pytest.param(LlmType.GPT_5_4_NANO, "gpt-5.4-nano", id="gpt_5_4_nano"),
        pytest.param(LlmType.GPT_5_6_LUNA, "gpt-5.6-luna", id="gpt_5_6_luna"),
        pytest.param(LlmType.GPT_5_6_TERRA, "gpt-5.6-terra", id="gpt_5_6_terra"),
        pytest.param(LlmType.GPT_5_6_SOL, "gpt-5.6-sol", id="gpt_5_6_sol"),
        pytest.param(LlmType.GPT_6_LUNA, "gpt-6-luna", id="gpt_6_luna"),
        pytest.param(LlmType.GPT_6_1_TERRA, "gpt-6.1-terra", id="gpt_6_1_terra"),
        pytest.param(LlmType.GPT_6_2_SOL, "gpt-6.2-sol", id="gpt_6_2_sol"),
        pytest.param(LlmType.GPT_6_2_ASTRA, "gpt-6.2-astra", id="gpt_6_2_astra"),
    ],
)
def test_get_model_settings_returns_the_types_model(
    llm_type: LlmType, expected_model_name: str
) -> None:
    llm_settings = LlmSettings()

    model_settings = llm_settings.get_model_settings(llm_type)

    assert model_settings.model_name == expected_model_name


def test_get_model_settings_returns_the_configured_value() -> None:
    llm_settings = LlmSettings(gpt_6_2_sol=Gpt62SolLlmModelSettings(max_output_tokens=321))

    model_settings = llm_settings.get_model_settings(LlmType.GPT_6_2_SOL)

    assert model_settings == Gpt62SolLlmModelSettings(max_output_tokens=321)


def test_get_model_settings_by_model_name_known_model_returns_its_settings() -> None:
    llm_settings = LlmSettings(gpt_6_2_sol=Gpt62SolLlmModelSettings(max_output_tokens=321))

    model_settings = llm_settings.get_model_settings_by_model_name(
        LlmProviderType.OPENAI, "gpt-6.2-sol"
    )

    assert model_settings == Gpt62SolLlmModelSettings(max_output_tokens=321)


def test_get_model_settings_by_model_name_other_provider_returns_none() -> None:
    llm_settings = LlmSettings()

    model_settings = llm_settings.get_model_settings_by_model_name(
        LlmProviderType.ANTHROPIC, "gpt-6.2-sol"
    )

    assert model_settings is None


def test_get_model_settings_by_model_name_unknown_model_returns_none() -> None:
    llm_settings = LlmSettings()

    model_settings = llm_settings.get_model_settings_by_model_name(
        LlmProviderType.OPENAI, "gpt-4o-mini"
    )

    assert model_settings is None
