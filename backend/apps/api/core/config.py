from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    TomlConfigSettingsSource,
)

from apps.api.core.types import EnvironmentType
from libs.auth.settings import AuthSettings
from libs.content_engagement.settings import ContentEngagementSettings
from libs.core.settings import BackgroundJobSettings, LaunchDarklySettings
from libs.credits.settings import CreditSettings
from libs.generate_text.settings import GenerateTextSettings
from libs.google_auth.settings import GoogleAuthSettings
from libs.llm.settings import LlmSettings
from libs.users.settings import UserSettings


class AppSettings(BaseSettings):
    """The root settings, read from config.toml and the environment, which wins."""

    model_config = SettingsConfigDict(
        toml_file="config.toml",
        env_file=".env",
        env_nested_delimiter="__",
    )

    app_name: str = "Personagora API"
    environment: EnvironmentType
    database_url: str
    redis_url: str
    google_client_id: str
    google_client_secret: str
    openai_api_key: str = Field(min_length=1)
    launchdarkly_sdk_key: str | None = None
    railway_replica_id: str | None = None
    auth: AuthSettings = Field(default_factory=AuthSettings)
    background_jobs: BackgroundJobSettings = Field(default_factory=BackgroundJobSettings)
    content_engagement: ContentEngagementSettings = Field(default_factory=ContentEngagementSettings)
    credits: CreditSettings = Field(default_factory=CreditSettings)
    generate_text: GenerateTextSettings = Field(default_factory=GenerateTextSettings)
    google_auth: GoogleAuthSettings = Field(default_factory=GoogleAuthSettings)
    launchdarkly: LaunchDarklySettings = Field(default_factory=LaunchDarklySettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    users: UserSettings = Field(default_factory=UserSettings)

    @model_validator(mode="after")
    def validate_launchdarkly_sdk_key_is_set_when_enabled(self) -> Self:
        """Refuses to start with LaunchDarkly enabled and no SDK key."""
        if self.launchdarkly.is_enabled and not self.launchdarkly_sdk_key:
            raise ValueError("LAUNCHDARKLY_SDK_KEY is required when launchdarkly.is_enabled")
        return self

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Orders the sources so init values beat env vars, which beat .env, secrets and TOML."""
        toml_settings = TomlConfigSettingsSource(settings_cls)
        return (init_settings, env_settings, dotenv_settings, file_secret_settings, toml_settings)
