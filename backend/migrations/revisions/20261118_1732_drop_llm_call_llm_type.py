from migration_runner import MigrationRunner

revision = "20261118_1732"
down_revision = "20261106_1828"

MIGRATION_RUNNER = MigrationRunner()


def upgrade() -> None:
    MIGRATION_RUNNER.run_transactional("psg_llm_call/0003_drop_llm_type.up.sql")


def downgrade() -> None:
    MIGRATION_RUNNER.run_transactional("psg_llm_call/0003_drop_llm_type.down.sql")
