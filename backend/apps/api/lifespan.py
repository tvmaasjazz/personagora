import asyncio
import os
import secrets
import socket
from collections.abc import AsyncGenerator, Awaitable
from contextlib import asynccontextmanager

import launchdarkly_ai_server
import structlog
from fastapi import FastAPI
from httpx import AsyncClient
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.checkpoint.redis.aio import AsyncRedisSaver
from ldclient import Config, LDClient
from openai import AsyncOpenAI
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import create_async_engine

from apps.api.core.config import AppSettings
from apps.api.core.event_loop_monitor import monitor_event_loop_lag
from apps.api.core.logging import configure_logging
from apps.api.core.types import EnvironmentType
from apps.api.domains.generate_text.dependencies import build_generate_text_run_pickup_service
from libs.core.services import BackgroundJobService
from libs.database.session import create_db_session_factory
from libs.generate_text.types import GraphCheckpointerType

logger = structlog.get_logger(__name__)

WORKER_ID_SUFFIX_BYTES = 2
WORKER_ID_REPLICA_LENGTH = 8


def build_worker_id(app_settings: AppSettings) -> str:
    """Names this process by where it runs, its PID and a random suffix."""
    # The suffix keeps a restarted process that reuses a PID from matching the lease its
    # predecessor held
    host_name = app_settings.railway_replica_id or socket.gethostname()
    random_suffix = secrets.token_hex(WORKER_ID_SUFFIX_BYTES)
    return f"{host_name[:WORKER_ID_REPLICA_LENGTH]}-pid{os.getpid()}-{random_suffix}"


async def connect_launchdarkly(app_settings: AppSettings) -> LDClient:
    """Builds the LaunchDarkly client off the event loop and hands it to the AI SDK."""
    assert app_settings.launchdarkly_sdk_key is not None
    launchdarkly_client = await asyncio.to_thread(
        LDClient,
        Config(app_settings.launchdarkly_sdk_key),
        app_settings.launchdarkly.start_wait_seconds,
    )
    if not launchdarkly_client.is_initialized():
        # Steps use their code defaults until the client connects in the background
        logger.warning("launchdarkly_not_connected")
    await launchdarkly_ai_server.init_client(client=launchdarkly_client)
    return launchdarkly_client


async def disconnect_launchdarkly(launchdarkly_client: LDClient) -> None:
    """Closes the client off the event loop, flushing its events, then the AI SDK's own."""
    # Closing blocks while it flushes; the AI SDK's shutdown then finds the client already
    # closed and returns at once
    await asyncio.to_thread(launchdarkly_client.close)
    await launchdarkly_ai_server.shutdown()


async def connect_launchdarkly_if_enabled(app_settings: AppSettings) -> LDClient | None:
    """Connects to LaunchDarkly when it's enabled, else returns None."""
    if not app_settings.launchdarkly.is_enabled:
        return None
    return await connect_launchdarkly(app_settings)


async def set_up_graph_checkpointer(
    app_settings: AppSettings, redis_client: Redis
) -> BaseCheckpointSaver:
    """Returns the graph checkpointer the settings choose, set up and ready."""
    if app_settings.generate_text.checkpointer is not GraphCheckpointerType.REDIS:
        return InMemorySaver()
    # Redis only indexes database 0, so on any other database its setup refuses to create
    # the index and the app stops here
    graph_checkpointer = AsyncRedisSaver(
        redis_client=redis_client,
        ttl={
            "default_ttl": app_settings.generate_text.checkpoint_ttl_minutes,
            "refresh_on_read": True,
        },
    )
    await graph_checkpointer.asetup()
    return graph_checkpointer


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncGenerator[None]:
    # Create the app-scoped resources
    app_settings = fastapi_app.state.settings
    configure_logging(app_settings)
    db_engine = create_async_engine(app_settings.database_url)
    redis_client = Redis.from_url(app_settings.redis_url)
    http_client = AsyncClient()
    openai_client = AsyncOpenAI(api_key=app_settings.openai_api_key, max_retries=0)
    background_job_service = BackgroundJobService(worker_id=build_worker_id(app_settings))
    fastapi_app.state.background_job_service = background_job_service
    fastapi_app.state.db_engine = db_engine
    fastapi_app.state.db_session_factory = create_db_session_factory(db_engine)
    fastapi_app.state.redis_client = redis_client
    fastapi_app.state.http_client = http_client
    fastapi_app.state.openai_client = openai_client

    # Set up the graph checkpointer and connect to LaunchDarkly, which don't depend on
    # each other
    is_redis_checkpointer = app_settings.generate_text.checkpointer is GraphCheckpointerType.REDIS
    graph_checkpointer, launchdarkly_client = await asyncio.gather(
        set_up_graph_checkpointer(app_settings, redis_client),
        connect_launchdarkly_if_enabled(app_settings),
    )
    fastapi_app.state.graph_checkpointer = graph_checkpointer

    logger.info(
        "api_started",
        app_name=app_settings.app_name,
        environment=app_settings.environment,
    )
    # Start the background loops
    event_loop_monitor_task = None
    if app_settings.environment is EnvironmentType.DEVELOPMENT:
        event_loop_monitor_task = asyncio.create_task(monitor_event_loop_lag())
    generate_text_run_pickup_task = None
    generate_text_run_handoff_task = None
    # Picking up another process's run needs the state it left in Redis
    if app_settings.environment is not EnvironmentType.TEST and is_redis_checkpointer:
        generate_text_run_pickup_service = build_generate_text_run_pickup_service(fastapi_app.state)
        generate_text_run_pickup_task = asyncio.create_task(
            generate_text_run_pickup_service.pick_up_expired_runs()
        )
        generate_text_run_handoff_task = asyncio.create_task(
            generate_text_run_pickup_service.pick_up_handed_off_runs()
        )
    try:
        yield
    finally:
        # Stop the pickup loops first, so a stopping process claims no new run
        generate_text_run_tasks = [
            generate_text_run_task
            for generate_text_run_task in (
                generate_text_run_pickup_task,
                generate_text_run_handoff_task,
            )
            if generate_text_run_task is not None
        ]
        for generate_text_run_task in generate_text_run_tasks:
            generate_text_run_task.cancel()
        await asyncio.gather(*generate_text_run_tasks, return_exceptions=True)
        # Drain running jobs before the clients close, since a running graph still needs them
        background_job_service.request_stop()
        await background_job_service.drain(app_settings.background_jobs.shutdown_drain_seconds)
        if event_loop_monitor_task is not None:
            event_loop_monitor_task.cancel()
            await asyncio.gather(event_loop_monitor_task, return_exceptions=True)
        # Close the clients and the engine together
        close_awaitables: list[Awaitable[None]] = [
            http_client.aclose(),
            redis_client.aclose(),
            db_engine.dispose(),
            openai_client.close(),
        ]
        if launchdarkly_client is not None:
            close_awaitables.append(disconnect_launchdarkly(launchdarkly_client))
        await asyncio.gather(*close_awaitables)
        logger.info("api_stopped", app_name=app_settings.app_name)
