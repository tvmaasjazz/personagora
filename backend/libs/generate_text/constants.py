from libs.generate_text.types import (
    GenerateTextNodeType,
    GenerateTextRunStatusType,
    GenerateTextStepTierType,
)

# Key a text step's text is stored under in the JSONB output column
STEP_OUTPUT_TEXT_KEY = "text"

# A run in one of these hasn't finished, so failing it still means something
UNFINISHED_RUN_STATUSES = (
    GenerateTextRunStatusType.PENDING,
    GenerateTextRunStatusType.RUNNING,
    GenerateTextRunStatusType.AWAITING_REVIEW,
)

# The Redis list a stopping process pushes a released run's id onto. Every deployed
# version must use the same key, or a handoff reaches no listener.
RUN_HANDOFF_QUEUE_KEY = "generate_text:run_handoff"

# Stored on a run picked up while still PENDING: its job never started, so
# there is no checkpoint to resume from.
RUN_NEVER_STARTED_ERROR_CODE = "RunNeverStarted"
RUN_NEVER_STARTED_ERROR_MESSAGE = "This run never started. Start it again."

# Stored on a run that was picked up more often than the settings allow.
RUN_PICKED_UP_TOO_OFTEN_ERROR_CODE = "RunPickedUpTooOften"
RUN_PICKED_UP_TOO_OFTEN_ERROR_MESSAGE = "This run kept being interrupted. Start it again."

# Stored on a run still unfinished when its user was suspended.
USER_SUSPENDED_ERROR_CODE = "UserSuspended"
USER_SUSPENDED_ERROR_MESSAGE = "This run stopped because the account was suspended."

# Stored on a run still unfinished when its user was made a reader.
USER_ROLE_CHANGED_ERROR_CODE = "UserRoleChanged"
USER_ROLE_CHANGED_ERROR_MESSAGE = (
    "This run stopped because the account can no longer generate text."
)

# The placeholder a step's system template holds the output format's rules in; a served
# template for a validated step must keep it
FORMAT_RULES_VARIABLE_NAME = "format_rules"

# These keys must match the LaunchDarkly configs the seed script creates
BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER: dict[
    tuple[GenerateTextNodeType, GenerateTextStepTierType], str
] = {
    (
        GenerateTextNodeType.GENERATE_OUTLINE,
        GenerateTextStepTierType.STANDARD,
    ): "blog-post-outline-standard",
    (
        GenerateTextNodeType.GENERATE_DRAFT,
        GenerateTextStepTierType.STANDARD,
    ): "blog-post-draft-standard",
    (
        GenerateTextNodeType.HUMANIZE,
        GenerateTextStepTierType.STANDARD,
    ): "blog-post-humanize-standard",
}
