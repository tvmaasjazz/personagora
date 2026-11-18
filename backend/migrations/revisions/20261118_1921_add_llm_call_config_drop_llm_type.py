from migration_runner import MigrationRunner

revision = "20261118_1921"
down_revision = "20261118_1732"

MIGRATION_RUNNER = MigrationRunner()


def upgrade() -> None:
    MIGRATION_RUNNER.run_transactional("psg_llm_call/0004_add_config_columns.up.sql")
    MIGRATION_RUNNER.run_transactional("psg_llm_call/0005_drop_llm_type.up.sql")


def downgrade() -> None:
    MIGRATION_RUNNER.run_transactional("psg_llm_call/0005_drop_llm_type.down.sql")
    MIGRATION_RUNNER.run_transactional("psg_llm_call/0004_add_config_columns.down.sql")
