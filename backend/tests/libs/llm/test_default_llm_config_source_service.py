from libs.llm.results import LlmProviderCompletionResult
from libs.llm.services.default_llm_config_source_service import DefaultLlmConfigSourceService
from tests.factories.auth import build_auth_user
from tests.factories.llm import build_llm_config_source_result, build_llm_provider_completion_result


async def test_find_config_returns_none() -> None:
    default_llm_config_source_service = DefaultLlmConfigSourceService()

    find_config_result = await default_llm_config_source_service.find_config(
        "test-config-key", build_auth_user()
    )

    assert find_config_result is None


async def test_track_call_returns_the_calls_result() -> None:
    default_llm_config_source_service = DefaultLlmConfigSourceService()
    expected_result = build_llm_provider_completion_result(content="From the call")
    call_count = 0

    async def call() -> LlmProviderCompletionResult:
        nonlocal call_count
        call_count += 1
        return expected_result

    track_call_result = await default_llm_config_source_service.track_call(
        build_llm_config_source_result(), build_auth_user(), call
    )

    assert track_call_result == expected_result
    assert call_count == 1
