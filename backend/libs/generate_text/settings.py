from pydantic import BaseModel, ConfigDict, Field

from libs.generate_text.types import GraphCheckpointerType
from libs.llm.types import LlmType


class BlogPostOutlineStepSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    standard: LlmType = LlmType.GPT_5_4_NANO


class BlogPostDraftStepSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    standard: LlmType = LlmType.GPT_5_6_SOL


class BlogPostHumanizeStepSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    standard: LlmType = LlmType.GPT_5_6_SOL


class BlogPostStepSettings(BaseModel):
    """The model each blog post step runs on, per tier."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    outline: BlogPostOutlineStepSettings = Field(default_factory=BlogPostOutlineStepSettings)
    draft: BlogPostDraftStepSettings = Field(default_factory=BlogPostDraftStepSettings)
    humanize: BlogPostHumanizeStepSettings = Field(default_factory=BlogPostHumanizeStepSettings)


class GenerateTextSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    checkpointer: GraphCheckpointerType = GraphCheckpointerType.REDIS
    max_rewrite_passes: int = 3
    checkpoint_ttl_minutes: int = 10080
    max_output_format_retries: int = 1
    poll_interval_ms: int = 2000
    lease_seconds: int = 60
    lease_heartbeat_seconds: int = 15
    run_pickup_interval_seconds: int = 30
    max_run_pickups: int = 3
    max_active_runs_per_user: int = 2
    # Under redis-py's 5s socket timeout, or an empty wait raises instead of returning
    run_handoff_wait_seconds: int = 2
    blog_post: BlogPostStepSettings = Field(default_factory=BlogPostStepSettings)
