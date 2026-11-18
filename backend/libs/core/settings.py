from pydantic import BaseModel, ConfigDict


class BackgroundJobSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    # Keep above the slowest model's 120s timeout and under Railway's drainingSeconds
    shutdown_drain_seconds: int = 150


class LaunchDarklySettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    is_enabled: bool = False
    # How long startup waits for LaunchDarkly to connect before steps use their defaults
    start_wait_seconds: float = 5
