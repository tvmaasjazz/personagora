# Generate text

Writes text as one of the user's personas; `BLOG_POST` is the only text type. A
LangGraph graph runs the steps as a background job and can pause after a step for the
user to approve it or send it back with feedback. The client polls the run to its end.

## How it works

1. `POST /generate-text/blog-post` runs `validate_credit_balance_covers_run` and
   `validate_active_run_limit`, then `GenerateTextService.generate_text` builds the
   graph from the run's `options`, inserts a `PENDING` run already leased to this
   process, starts the job and returns `202`. `GET /generate-text/runs/{run_identity}`
   returns the run with its newest step's text.
2. The job moves the run to `RUNNING` and streams the graph, checkpointing after
   every step under the run's identity.
3. Each node pass writes a `psg_generate_text_step` row
   (`GenerateTextInstrumentationService`). Its LLM calls are logged to `psg_llm_call`; each
   step passes its config key (`BLOG_POST_LLM_CONFIG_KEY_BY_STEP_AND_TIER`) and default
   model, as `libs/llm/README.md` describes.
4. Credits: `complete_step` prices the step's LLM cost and charges it through
   `GenerateTextCreditService.charge_step` in the same transaction; `fail_run` refunds
   the steps after the last review (`refund_failed_run_segment`). See
   `libs/credits/README.md`.
5. Review: a review node calls `interrupt`, its step becomes `AWAITING_REVIEW`, the
   stream ends, and `record_awaiting_review` pauses the run and clears its lease.
6. Resume: `POST /generate-text/runs/{run_identity}/resume` (same guards) refuses a run
   on an old `graph_version`, claims it back to `RUNNING` (`claim_paused_run`), records
   the decision on the paused step and restarts the job with `Command(resume=...)`.
   Rejected output goes to the rewrite node, up to `max_rewrite_passes` times.
7. At the graph's end `complete_run` marks the run `COMPLETED` with its cost totals.
   An exception calls `fail_run`; the first ending recorded wins.
8. Leases: a `PENDING` or `RUNNING` run holds `lease_owner` (the process's `worker_id`)
   and `lease_expires_at` (database clock). `keep_lease_alive` renews it for
   `lease_seconds` every `lease_heartbeat_seconds`, and cancels the job if it is lost.
9. Handoff: a job that sees `BackgroundJobService.is_stopping` between steps, or is
   cancelled, calls `hand_off_run`: it expires its lease and pushes the run id onto the
   Redis list `generate_text:run_handoff`, where `pick_up_handed_off_runs` claims it.
10. Pickup: `pick_up_expired_runs` claims runs whose lease expired, at startup and
    every `run_pickup_interval_seconds`. It fails a `PENDING` run or one picked up more
    than `max_run_pickups` times, and continues the rest from their last checkpoint.
11. Shutdown: lifespan cancels the pickup loops, calls `request_stop()`, then `drain`
    waits up to `shutdown_drain_seconds` and cancels jobs still running.
12. Suspending a user or making them a reader fails their unfinished runs after the
    response (`fail_user_unfinished_runs`).

## Services

- `GenerateTextService`: starts, resumes and continues runs; records how each ended.
- `GenerateTextRunService`: writes `psg_generate_text_run` (status, lease, cost totals).
- `GenerateTextStepService`: writes `psg_generate_text_step` (status, output, decision).
- `GenerateTextCreditService`: charges and refunds steps in the caller's transaction.
- `GenerateTextRunLeaseService`: claims, renews, releases and hands off leases.
- `GenerateTextRunHandoffQueueService`: pushes and waits on the Redis handoff list.
- `GenerateTextRunPickupService`: both pickup loops; fails or continues a claimed run.
- `GenerateTextNodeService`: builds the generate, rewrite and review nodes.
- `GenerateTextInstrumentationService`: records each node pass as a timed step.
- `GenerateTextValidationService`: the active-run limit (`max_active_runs_per_user`).
- `GenerateTextGraphBuilderRegistry`: maps a `TextType` to its graph builder.
- `BlogPostGraphBuilder` (`graphs/blog_post/`): optional outline, draft, optional
  humanize, each with an optional review loop; its prompts and output format beside it.
- `after_response_tasks.py`: `fail_user_unfinished_runs`, queued by admin routes.
- `BackgroundJobService` (`libs/core/services/`): runs jobs as tasks, holds `worker_id`
  and the stop flag. `apps/api/lifespan.py` starts pickup and drains at shutdown.

## States

Run (`GenerateTextRunStatusType`): `PENDING → RUNNING ⇄ AWAITING_REVIEW`,
`RUNNING → COMPLETED`, and `PENDING | RUNNING | AWAITING_REVIEW → FAILED`. A
picked-up run stays `RUNNING` under a new lease. Nothing sets `CANCELLED`.

Step (`GenerateTextStepStatusType`): `RUNNING → SUCCEEDED | FAILED | AWAITING_REVIEW`,
and `AWAITING_REVIEW → RUNNING` when the review node reruns on resume. Nothing sets
`SKIPPED`.
