# Database

This lib gives the app its async sessions, the Orm classes every table maps to, and
shared query helpers for database time and paging. `backend/migrations/` builds the
schema those classes mirror, from hand-written SQL that Alembic runs. How to write
tables, migrations and Orm classes is in `.claude/rules/database.md`.

## How it works

**A request's session**

1. On startup, `lifespan.py` creates the engine and stores
   `create_db_session_factory(db_engine)` on `app.state.db_session_factory`.
2. A route takes `DbSessionDep` (`apps/api/core/dependencies.py`): one session and one
   transaction per request, committed when the route returns, before the response is
   sent, and rolled back if it raises. Its ORM selects leave out soft-deleted rows.
3. After-response tasks, background jobs and services handed the factory open their
   own session with `async with db_session_factory() as db_session, db_session.begin()`.

**Migrations**

1. `uv run alembic upgrade head` follows `alembic.ini` to `migrations/env.py`, which
   connects with `DATABASE_URL` (env first, then `.env`) and runs each pending
   revision in its own transaction. Offline `--sql` mode raises.
2. A revision's `upgrade()` or `downgrade()` calls `MigrationRunner` with paths under
   `migrations/sql/`. `run_transactional` runs every statement in the file inside the
   revision's transaction; `run_non_transactional` runs a file's single statement in
   an autocommit block and raises if the file holds more than one.
3. Alembic records the applied revision in `alembic_version`.
4. `uv run python -m scripts.db.check_schema_drift` compares the migrated database with
   `BaseOrm.metadata`, prints any difference and exits 1.
5. `uv run pytest -m migration` rebuilds the test schema, then for every revision from
   the first: upgrade to it, downgrade one, upgrade again. CI runs `upgrade head`, the
   drift check and this test against an empty database.

**Reading and writing**

1. Every Orm class extends `BaseOrm`, which maps the shared columns and the annotation
   types: `str` to `Text`, `datetime` to `UtcDateTime`, `UUID` to `Uuid`.
   `UtcDateTime` stores naive UTC, returns aware UTC, and rejects a naive datetime.
2. `DatabaseClockUtils` builds the database's current UTC time as SQL
   (`build_utc_now_sql`, `build_utc_now_plus_sql(seconds)`) for use inside a statement.
3. A paged query pairs a `PaginationConfig` (search, sort, filter and tiebreak columns)
   with a `BasePageInput`. `PaginationService.find_page` returns Orm entities and
   `find_mapping_page` returns row mappings, both as a `FindPageResult`.
4. `PaginationQueryUtils` builds the queries behind it: filters and search words, one
   page carrying a window total, and a count only for an empty page past the first.

## Pieces

- `session.py`: `create_db_session_factory()` and `SoftDeleteSession`, which filters
  soft-deleted rows; sessions don't expire objects on commit.
- `base.py`: `BaseOrm` (shared columns, naming convention, type map) and
  `SoftDeleteMixin` (`deleted_at`).
- `column_types.py`, `constants.py`: `UtcDateTime`; `NAMING_CONVENTION`, `UTC_NOW_SQL`.
- `orm/`: one Orm class per table; `orm/__init__.py` imports them all, which registers
  every mapper on `BaseOrm.metadata`.
- `utils/`: `DatabaseClockUtils` and `PaginationQueryUtils`.
- `services/`: `PaginationService`, which runs a page query on the session it's given.
- `pagination_config.py`, `results.py`: `PaginationConfig`, `PaginationFilterConfig`
  and `FindPageResult`.
- `migrations/migration_runner.py`: `MigrationRunner`, which reads SQL files and sends
  each statement untouched through `exec_driver_sql`.
- `migrations/script.py.mako`: the template a new revision starts from.
- `scripts/db/check_schema_drift.py`: the drift check.
