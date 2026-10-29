"""Lotes limitados e testemunho transacional de sincronização."""
from pathlib import Path
from alembic import op

revision="0031_01"
down_revision="0030_01"
branch_labels=None
depends_on=None

def upgrade():
    op.get_bind().exec_driver_sql((Path(__file__).parents[1]/"sql/0031_01_sync_batches.sql").read_text(encoding="utf-8"),execution_options={"no_parameters":True})

def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT FROM lb.sync_batch) THEN RAISE EXCEPTION 'Rollback bloqueado: lotes preenchidos'; END IF;
    END $$""")
    op.execute("DROP TABLE lb.sync_batch_operation,lb.sync_batch")
    op.execute("DROP FUNCTION lb.guard_sync_batch(),lb.guard_sync_operation(),lb.verify_sync_operation()")
