# Database

This lib gives the app its async sessions, the Orm classes every table maps to, and
shared query helpers for database time and paging. `backend/migrations/` builds the
schema those classes mirror, from hand-written SQL that Alembic runs. How to write
tables, migrations and Orm classes is in `.claude/rules/database.md`, and how services
use sessions is in `fastapi-structure.md` › Database.

## How it works

**A request's session**

1. On startup, `lifespan.py` creates the engine and stores the session factory on
   `app.state.db_session_factory`.
2. A route takes `DbSessionDep` (`apps/api/core/dependencies.py`): one session per
   request, committed before the response is sent.
3. After-response tasks and background jobs open their own session from the factory.

**Migrations**

1. `uv run alembic upgrade head` runs `migrations/env.py`, which connects with
   `DATABASE_URL` and applies each pending revision in its own transaction.
2. A revision's `upgrade()` or `downgrade()` hands `MigrationRunner` the SQL files under
   `migrations/sql/` to run, in order.
3. Alembic records the applied revision in `alembic_version`.
4. CI applies every migration to an empty database, then runs the drift check and the
   stairway test (`pytest -m migration`).

**Reading and writing**

1. Services query and write through Orm classes on the session they're given.
2. A statement that needs "now" takes it from `DatabaseClockUtils`.
3. A paged list pairs a `PaginationConfig` (search, sort and filter columns) with a
   `BasePageInput` (`libs/core/inputs.py`). `PaginationService` runs it and returns a
   `FindPageResult`, building its queries with `PaginationQueryUtils`.

## Pieces

- `session.py`: `create_db_session_factory()` and `SoftDeleteSession`.
- `base.py`, `column_types.py`, `constants.py`: `BaseOrm`, `SoftDeleteMixin`,
  `UtcDateTime` and the naming convention.
- `orm/`: one Orm class per table.
- `utils/`: `DatabaseClockUtils` and `PaginationQueryUtils`.
- `services/`: `PaginationService`.
- `pagination_config.py`, `results.py`: `PaginationConfig`, `PaginationFilterConfig`
  and `FindPageResult`.
- `migrations/migration_runner.py`: `MigrationRunner`, which runs SQL files.
- `migrations/script.py.mako`: the template a new revision starts from.
- `scripts/db/check_schema_drift.py`: the drift check.
