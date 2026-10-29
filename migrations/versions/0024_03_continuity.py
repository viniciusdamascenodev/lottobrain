"""Continuidade numérica e fencing, sem conectar o coletor."""
from pathlib import Path
from alembic import op

revision = "0024_03"
down_revision = "0024_02"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql((Path(__file__).parents[1] / "sql/0024_03_continuity.sql").read_text(encoding="utf-8"), execution_options={"no_parameters": True})


def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT FROM lb.ingestion_baseline) OR EXISTS (SELECT FROM lb.sync_checkpoint) THEN
        RAISE EXCEPTION 'Rollback bloqueado: continuidade preenchida';
      END IF;
    END $$""")
    op.execute("DROP TABLE lb.sync_step, lb.sync_checkpoint, lb.ingestion_baseline")
    op.execute("DROP FUNCTION lb.guard_checkpoint(), lb.check_step(), lb.verify_checkpoint()")
