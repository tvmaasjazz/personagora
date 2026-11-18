from decimal import Decimal

import pytest
import structlog.testing
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from libs.auth.results import AuthUser
from libs.database.orm.llm_call import LlmCallOrm
from libs.llm.exceptions import (
    LlmFailedException,
    LlmRefusedException,
    LlmTruncatedException,
    LlmUnavailableException,
)
from libs.llm.inputs import LlmProviderCompletionInput
from libs.llm.results import LlmCompletionResult, LlmStructuredCompletionResult
from libs.llm.services.llm_call_service import LlmCallService
from libs.llm.services.llm_service import LlmService
from libs.llm.settings import Gpt54NanoLlmModelSettings, LlmSettings
from libs.llm.types import (
    LlmCallReasonType,
    LlmCallStatusType,
    LlmProviderType,
    LlmReasoningEffortType,
    LlmType,
)
from tests.factories.auth import build_auth_user
from tests.factories.llm import (
    build_llm_completion_input,
    build_llm_provider_completion_result,
)
from tests.factories.users import insert_user_row
from tests.stubs.llm import LlmProviderServiceStub


class _SampleOutput(BaseModel):
    answer: str


def _build_llm_settings(
    *,
    model_name: str = "test-model",
    input_usd_per_million_tokens: Decimal = Decimal("2.00"),
    cached_input_usd_per_million_tokens: Decimal = Decimal("0.50"),
    output_usd_per_million_tokens: Decimal = Decimal("8.00"),
    provider: LlmProviderType = LlmProviderType.OPENAI,
    max_output_tokens: int = 2048,
    request_timeout_seconds: int = 30,
    reasoning_effort: LlmReasoningEffortType | None = None,
) -> LlmSettings:
    return LlmSettings(
        gpt_5_4_nano=Gpt54NanoLlmModelSettings(
            provider=provider,
            model_name=model_name,
            max_output_tokens=max_output_tokens,
            request_timeout_seconds=request_timeout_seconds,
            reasoning_effort=reasoning_effort,
            input_usd_per_million_tokens=input_usd_per_million_tokens,
            cached_input_usd_per_million_tokens=cached_input_usd_per_million_tokens,
            output_usd_per_million_tokens=output_usd_per_million_tokens,
        )
    )


async def _insert_auth_user(db_session: AsyncSession) -> AuthUser:
    user_record = await insert_user_row(db_session)
    await db_session.commit()
    return build_auth_user(user_id=user_record.id, user_identity=user_record.identity)


async def test_complete_succeeded_persists_row_and_returns_result(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_result = build_llm_provider_completion_result(
        content="Hello there.",
        reason=None,
        input_tokens=100,
        output_tokens=50,
        cached_input_tokens=20,
        reasoning_tokens=0,
        provider_request_reference="req_stub_1",
    )
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_settings = _build_llm_settings()
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=llm_settings,
    )
    llm_completion_input = build_llm_completion_input(
        llm_type=LlmType.GPT_5_4_NANO, purpose="succeeded-purpose"
    )

    complete_result = await llm_service.complete(llm_completion_input, auth_user)

    assert complete_result == LlmCompletionResult(
        llm_call_identity=complete_result.llm_call_identity,
        content="Hello there.",
        input_tokens=100,
        output_tokens=50,
    )
    llm_call_query = select(LlmCallOrm).where(
        LlmCallOrm.identity == complete_result.llm_call_identity
    )
    llm_call_record = await db_session.scalar(llm_call_query)
    assert llm_call_record is not None
    assert llm_call_record.status == LlmCallStatusType.SUCCEEDED
    assert llm_call_record.provider == LlmProviderType.OPENAI
    assert llm_call_record.model_name == "test-model"
    assert llm_call_record.purpose == "succeeded-purpose"
    assert llm_call_record.system_prompt == llm_completion_input.system_prompt
    assert llm_call_record.user_prompt == llm_completion_input.user_prompt
    assert llm_call_record.response_text == "Hello there."
    assert llm_call_record.input_tokens == 100
    assert llm_call_record.output_tokens == 50
    assert llm_call_record.cached_input_tokens == 20
    assert llm_call_record.reasoning_tokens == 0
    assert llm_call_record.reason is None
    assert llm_call_record.duration_ms is not None
    assert llm_call_record.provider_request_reference == "req_stub_1"
    assert llm_call_record.created_by_id == auth_user.id
    assert llm_call_record.updated_by_id == auth_user.id


async def test_complete_computes_cost_from_model_prices_billing_cached_tokens_at_cached_rate(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_result = build_llm_provider_completion_result(
        input_tokens=1000,
        output_tokens=500,
        cached_input_tokens=200,
    )
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_settings = _build_llm_settings(
        input_usd_per_million_tokens=Decimal("2.00"),
        cached_input_usd_per_million_tokens=Decimal("0.50"),
        output_usd_per_million_tokens=Decimal("8.00"),
    )
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=llm_settings,
    )
    llm_completion_input = build_llm_completion_input(purpose="cost-purpose")

    complete_result = await llm_service.complete(llm_completion_input, auth_user)

    llm_call_query = select(LlmCallOrm).where(
        LlmCallOrm.identity == complete_result.llm_call_identity
    )
    llm_call_record = await db_session.scalar(llm_call_query)
    assert llm_call_record is not None
    assert llm_call_record.cost_usd == Decimal("0.005700")


async def test_complete_provider_error_leaves_failed_row_with_provider_message_and_reraises(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_error = LlmUnavailableException(
        "The LLM provider is unavailable", provider_message="upstream said no capacity"
    )
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_settings = _build_llm_settings()
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=llm_settings,
    )
    llm_completion_input = build_llm_completion_input(purpose="failed-purpose")

    with pytest.raises(LlmUnavailableException):
        await llm_service.complete(llm_completion_input, auth_user)

    llm_call_query = select(LlmCallOrm).where(LlmCallOrm.purpose == "failed-purpose")
    llm_call_record = await db_session.scalar(llm_call_query)
    assert llm_call_record is not None
    assert llm_call_record.status == LlmCallStatusType.FAILED
    assert llm_call_record.error_code == "LlmUnavailableException"
    assert llm_call_record.reason == LlmCallReasonType.PROVIDER_UNAVAILABLE
    assert llm_call_record.error_message == "The LLM provider is unavailable"
    assert llm_call_record.provider_error_message == "upstream said no capacity"


@pytest.mark.parametrize(
    ("reason", "expected_status", "expected_exception"),
    [
        pytest.param(
            LlmCallReasonType.MAX_TOKENS,
            LlmCallStatusType.INCOMPLETE,
            LlmTruncatedException,
            id="max_tokens",
        ),
        pytest.param(
            LlmCallReasonType.PROVIDER_ERROR,
            LlmCallStatusType.FAILED,
            LlmFailedException,
            id="provider_error",
        ),
    ],
)
async def test_complete_reason_writes_its_status_and_raises_its_exception(
    db_session: AsyncSession,
    db_session_factory: async_sessionmaker[AsyncSession],
    reason: LlmCallReasonType,
    expected_status: LlmCallStatusType,
    expected_exception: type[Exception],
) -> None:
    user_record = await insert_user_row(db_session)
    await db_session.commit()
    auth_user = build_auth_user(user_id=user_record.id, user_identity=user_record.identity)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_result = build_llm_provider_completion_result(reason=reason)
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=LlmSettings(),
    )
    llm_completion_input = build_llm_completion_input()

    with pytest.raises(expected_exception):
        await llm_service.complete(llm_completion_input, auth_user)

    llm_call_query = select(LlmCallOrm).where(LlmCallOrm.purpose == llm_completion_input.purpose)
    llm_call_record = await db_session.scalar(llm_call_query)
    assert llm_call_record is not None
    assert llm_call_record.status == expected_status
    assert llm_call_record.reason == reason


async def test_complete_refusal_writes_incomplete_row_and_raises(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_result = build_llm_provider_completion_result(
        content="I can't help with that.", reason=LlmCallReasonType.REFUSAL
    )
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_settings = _build_llm_settings()
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=llm_settings,
    )
    llm_completion_input = build_llm_completion_input(purpose="refused-purpose")

    with pytest.raises(LlmRefusedException):
        await llm_service.complete(llm_completion_input, auth_user)

    llm_call_query = select(LlmCallOrm).where(LlmCallOrm.purpose == "refused-purpose")
    llm_call_record = await db_session.scalar(llm_call_query)
    assert llm_call_record is not None
    assert llm_call_record.status == LlmCallStatusType.INCOMPLETE
    assert llm_call_record.reason == LlmCallReasonType.REFUSAL
    assert llm_call_record.response_text == "I can't help with that."


async def test_complete_structured_parses_into_output_type(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_structured_result = build_llm_provider_completion_result(
        parsed_output=_SampleOutput(answer="42"), input_tokens=80, output_tokens=20
    )
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_settings = _build_llm_settings()
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=llm_settings,
    )
    llm_completion_input = build_llm_completion_input(purpose="structured-purpose")

    complete_structured_result = await llm_service.complete_structured(
        llm_completion_input, _SampleOutput, auth_user
    )

    assert complete_structured_result == LlmStructuredCompletionResult[_SampleOutput](
        llm_call_identity=complete_structured_result.llm_call_identity,
        output=_SampleOutput(answer="42"),
        input_tokens=80,
        output_tokens=20,
    )
    llm_call_query = select(LlmCallOrm).where(
        LlmCallOrm.identity == complete_structured_result.llm_call_identity
    )
    llm_call_record = await db_session.scalar(llm_call_query)
    assert llm_call_record is not None
    assert llm_call_record.response_json == {"answer": "42"}


async def test_complete_logs_llm_call_completed_with_token_counts(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_result = build_llm_provider_completion_result(
        input_tokens=100, output_tokens=50, cached_input_tokens=20, reasoning_tokens=5
    )
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_settings = _build_llm_settings()
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=llm_settings,
    )
    llm_completion_input = build_llm_completion_input(purpose="logging-purpose")

    with structlog.testing.capture_logs() as captured_log_events:
        await llm_service.complete(llm_completion_input, auth_user)

    llm_call_completed_events = [
        log_event for log_event in captured_log_events if log_event["event"] == "llm_call_completed"
    ]
    assert len(llm_call_completed_events) == 1
    assert llm_call_completed_events[0]["input_tokens"] == 100
    assert llm_call_completed_events[0]["output_tokens"] == 50
    assert llm_call_completed_events[0]["cached_input_tokens"] == 20
    assert llm_call_completed_events[0]["reasoning_tokens"] == 5


async def test_complete_model_provider_not_registered_raises_not_implemented_error(
    db_session_factory: async_sessionmaker[AsyncSession],
) -> None:
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_service = LlmService(
        llm_provider_services={},
        llm_call_service=llm_call_service,
        llm_settings=_build_llm_settings(provider=LlmProviderType.ANTHROPIC),
    )
    llm_completion_input = build_llm_completion_input(llm_type=LlmType.GPT_5_4_NANO)

    with pytest.raises(NotImplementedError):
        await llm_service.complete(llm_completion_input, build_auth_user())


@pytest.mark.parametrize("llm_type", list(LlmType))
async def test_complete_every_llm_type_resolves_to_a_model(
    db_session: AsyncSession,
    db_session_factory: async_sessionmaker[AsyncSession],
    llm_type: LlmType,
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=LlmSettings(),
    )
    llm_completion_input = build_llm_completion_input(llm_type=llm_type)

    await llm_service.complete(llm_completion_input, auth_user)

    assert len(llm_provider_service_stub.complete_inputs) == 1


@pytest.mark.parametrize(
    ("llm_type", "llm_settings_field_name"),
    [
        pytest.param(LlmType.GPT_5_4_NANO, "gpt_5_4_nano", id="gpt_5_4_nano"),
        pytest.param(LlmType.GPT_5_6_LUNA, "gpt_5_6_luna", id="gpt_5_6_luna"),
        pytest.param(LlmType.GPT_5_6_TERRA, "gpt_5_6_terra", id="gpt_5_6_terra"),
        pytest.param(LlmType.GPT_5_6_SOL, "gpt_5_6_sol", id="gpt_5_6_sol"),
        pytest.param(LlmType.GPT_6_LUNA, "gpt_6_luna", id="gpt_6_luna"),
        pytest.param(LlmType.GPT_6_1_TERRA, "gpt_6_1_terra", id="gpt_6_1_terra"),
        pytest.param(LlmType.GPT_6_2_SOL, "gpt_6_2_sol", id="gpt_6_2_sol"),
        pytest.param(LlmType.GPT_6_2_ASTRA, "gpt_6_2_astra", id="gpt_6_2_astra"),
    ],
)
async def test_complete_passes_the_llm_types_model_settings_to_provider(
    db_session: AsyncSession,
    db_session_factory: async_sessionmaker[AsyncSession],
    llm_type: LlmType,
    llm_settings_field_name: str,
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    default_model_settings = getattr(LlmSettings(), llm_settings_field_name)
    overridden_model_settings = type(default_model_settings)(
        model_name="overridden-model",
        max_output_tokens=777,
        request_timeout_seconds=11,
        reasoning_effort=LlmReasoningEffortType.HIGH,
    )
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=LlmSettings(**{llm_settings_field_name: overridden_model_settings}),
    )
    llm_completion_input = build_llm_completion_input(
        llm_type=llm_type, system_prompt="Be brief.", user_prompt="Say hi."
    )

    await llm_service.complete(llm_completion_input, auth_user)

    assert llm_provider_service_stub.complete_inputs == [
        LlmProviderCompletionInput(
            model_name="overridden-model",
            system_prompt="Be brief.",
            user_prompt="Say hi.",
            max_output_tokens=777,
            request_timeout_seconds=11,
            reasoning_effort=LlmReasoningEffortType.HIGH,
        )
    ]


async def test_complete_structured_model_without_reasoning_effort_passes_none(
    db_session: AsyncSession, db_session_factory: async_sessionmaker[AsyncSession]
) -> None:
    auth_user = await _insert_auth_user(db_session)
    llm_provider_service_stub = LlmProviderServiceStub()
    llm_provider_service_stub.complete_structured_result = build_llm_provider_completion_result(
        parsed_output=_SampleOutput(answer="42")
    )
    llm_call_service = LlmCallService(db_session_factory=db_session_factory)
    llm_service = LlmService(
        llm_provider_services={LlmProviderType.OPENAI: llm_provider_service_stub},
        llm_call_service=llm_call_service,
        llm_settings=_build_llm_settings(max_output_tokens=1024, request_timeout_seconds=90),
    )
    llm_completion_input = build_llm_completion_input(system_prompt=None, user_prompt="Say hi.")

    await llm_service.complete_structured(llm_completion_input, _SampleOutput, auth_user)

    assert llm_provider_service_stub.complete_structured_inputs == [
        LlmProviderCompletionInput(
            model_name="test-model",
            system_prompt=None,
            user_prompt="Say hi.",
            max_output_tokens=1024,
            request_timeout_seconds=90,
            reasoning_effort=None,
        )
    ]
