# LLM

Every LLM call in the app goes through `LlmService`. It picks the call's model and system
prompt (served by LaunchDarkly when that is on and valid, else the caller's code
default), logs the call to `psg_llm_call`, asks the provider, and prices the tokens.

## How it works

1. A caller builds an `LlmCompletionInput` (its config key, default `LlmType`, system
   prompt template and variables) and calls `LlmService.complete` or `complete_structured`.
2. `LlmConfigService.resolve_config` asks the config source for the key's served config.
   It uses the served model and prompt when every check passes: the model is one of ours
   for that provider, the served parameters are valid for it, the prompt is one system
   message, every placeholder has a variable, and the required placeholders are kept.
   Otherwise it falls back to the code default and logs `llm_config_fallback` with the
   reason (`model_not_allowed`, `parameter_invalid`, `messages_not_one_system_message`,
   `placeholder_without_variable`, `required_placeholder_missing`). A source that serves
   nothing (off, disabled, malformed, unmapped provider or parameter) also gives the default.
3. `LlmCallService.create_pending_llm_call` commits a `PENDING` row with the resolved
   config's key, variation and model.
4. `LlmConfigService.track_call` runs the provider call. For a served config it goes
   through the source's `track_call`, which reports duration, tokens and outcome to
   LaunchDarkly; a fallback is never reported. The provider's own error is always the one
   raised, and the call never runs twice.
5. The provider service (`OpenAiLlmService`) makes the request and maps its response or
   error to ours.
6. `LlmCallService.complete_llm_call` (or `fail_llm_call`) records the result, tokens and
   cost; then a call with no usable output raises its `LlmException`.

## Services

- `LlmService`: the entry point; orders the steps above.
- `LlmConfigService`: resolves and checks each call's config, and holds each model's settings.
- `BaseLlmConfigSourceService`: serves a config and tracks a call.
  `DefaultLlmConfigSourceService` serves nothing; `LaunchDarklyLlmConfigSourceService`
  serves from LaunchDarkly AI Configs.
- `LlmCallService`: writes `psg_llm_call` rows, each in its own committed transaction.
- `BaseLlmProviderService`: one provider's API; `OpenAiLlmService` is the only one.

## Utils

- `LaunchDarklyLlmConfigUtils`: parses a served config into our types.
- `LlmUtils`: status, exception and cost for a call.
- `OpenAiLlmUtils`: OpenAI request arguments and response and error mapping.
- `PromptTemplateUtils`: finds and fills `{{name}}` placeholders.

## LaunchDarkly

`launchdarkly.is_enabled` is off by default. When on, `apps/api/lifespan.py` builds the
`LDClient` off the event loop (it needs `LAUNCHDARKLY_SDK_KEY`), hands it to the AI SDK
with `init_client`, and the source service uses the SDK. A client that hasn't connected
leaves every call on its code default. When off, `DefaultLlmConfigSourceService` is used.

Two scripts, run from `backend/`:

- `scripts/llm_config_check.py`: prints the source, model, variation and rendered system
  prompt each blog post step would run on now.
- `scripts/launchdarkly/seed_llm_configs.py`: creates each step's AI Config and default
  variation in a LaunchDarkly environment, leaving anything that exists alone.
