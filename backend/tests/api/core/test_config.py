from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.api.core.config import AppSettings
from libs.generate_text.settings import (
    BlogPostDraftStepSettings,
    BlogPostHumanizeStepSettings,
    BlogPostOutlineStepSettings,
    BlogPostStepSettings,
)
from libs.llm.settings import Gpt56SolLlmModelSettings
from libs.llm.types import LlmType


def test_app_settings_toml_overrides_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_toml_path = tmp_path / "config.toml"
    config_toml_path.write_text('app_name = "From Toml"\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("APP_NAME", raising=False)

    loaded_app_settings = AppSettings()

    assert loaded_app_settings.app_name == "From Toml"


def test_app_settings_env_var_overrides_toml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config_toml_path = tmp_path / "config.toml"
    config_toml_path.write_text('app_name = "From Toml"\n')
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("APP_NAME", "From Env")

    loaded_app_settings = AppSettings()

    assert loaded_app_settings.app_name == "From Env"


@pytest.mark.parametrize(
    "required_variable_name",
    [
        pytest.param("DATABASE_URL", id="database_url"),
        pytest.param("REDIS_URL", id="redis_url"),
    ],
)
def test_app_settings_missing_connection_url_raises_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, required_variable_name: str
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(required_variable_name)

    with pytest.raises(ValidationError):
        AppSettings()


def test_app_settings_missing_openai_api_key_raises_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OPENAI_API_KEY")

    with pytest.raises(ValidationError):
        AppSettings()


def test_app_settings_blank_openai_api_key_raises_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("OPENAI_API_KEY", "")

    with pytest.raises(ValidationError):
        AppSettings()


def test_app_settings_generate_text_blog_post_draft_env_var_leaves_other_steps_at_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("GENERATE_TEXT__BLOG_POST__DRAFT__STANDARD", "GPT_6_LUNA")
    monkeypatch.delenv("GENERATE_TEXT__BLOG_POST__OUTLINE__STANDARD", raising=False)
    monkeypatch.delenv("GENERATE_TEXT__BLOG_POST__HUMANIZE__STANDARD", raising=False)

    loaded_app_settings = AppSettings()

    assert loaded_app_settings.generate_text.blog_post == BlogPostStepSettings(
        outline=BlogPostOutlineStepSettings(standard=LlmType.GPT_5_4_NANO),
        draft=BlogPostDraftStepSettings(standard=LlmType.GPT_6_LUNA),
        humanize=BlogPostHumanizeStepSettings(standard=LlmType.GPT_5_6_SOL),
    )


def test_app_settings_llm_model_env_var_overrides_one_field_and_keeps_the_rest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LLM__GPT_5_6_SOL__MAX_OUTPUT_TOKENS", "1234")
    monkeypatch.delenv("LLM__GPT_5_6_SOL__MODEL_NAME", raising=False)

    loaded_app_settings = AppSettings()

    assert loaded_app_settings.llm.gpt_5_6_sol == Gpt56SolLlmModelSettings(max_output_tokens=1234)


@pytest.mark.parametrize(
    "sdk_key",
    [
        pytest.param(None, id="missing_key"),
        pytest.param("", id="blank_key"),
    ],
)
def test_app_settings_launchdarkly_enabled_without_sdk_key_raises_validation_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sdk_key: str | None
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LAUNCHDARKLY__IS_ENABLED", "true")
    if sdk_key is None:
        monkeypatch.delenv("LAUNCHDARKLY_SDK_KEY", raising=False)
    else:
        monkeypatch.setenv("LAUNCHDARKLY_SDK_KEY", sdk_key)

    with pytest.raises(ValidationError):
        AppSettings()


def test_app_settings_launchdarkly_enabled_with_sdk_key_loads(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LAUNCHDARKLY__IS_ENABLED", "true")
    monkeypatch.setenv("LAUNCHDARKLY_SDK_KEY", "sdk-test-key")

    loaded_app_settings = AppSettings()

    assert loaded_app_settings.launchdarkly.is_enabled is True
    assert loaded_app_settings.launchdarkly_sdk_key == "sdk-test-key"
