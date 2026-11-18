from libs.generate_text.types import GenerateTextRunStatusType

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

# The persona and tone placeholders of a step's system template. Served templates in
# LaunchDarkly use these names, so renaming one makes every served template fall back.
PERSONA_SECTION_VARIABLE_NAME = "persona_section"
TONE_AND_AUDIENCE_SECTION_VARIABLE_NAME = "tone_and_audience_section"
