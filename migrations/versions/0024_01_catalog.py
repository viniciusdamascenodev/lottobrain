"""Catálogo mínimo independente da modalidade."""
from pathlib import Path

from alembic import op

revision = "0024_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql((Path(__file__).parents[1] / "sql/0024_01_catalog.sql").read_text(encoding="utf-8"), execution_options={"no_parameters": True})


def downgrade():
    # Nunca apagar evidência/população sob o pretexto de rollback de DDL.
    op.execute("""DO $$ BEGIN
      IF EXISTS (SELECT FROM lb.lottery) THEN
        RAISE EXCEPTION 'Rollback bloqueado: catálogo preenchido; usar recuperação forward/backup';
      END IF;
    END $$""")
    op.execute("DROP SCHEMA lb CASCADE")
    # btree_gist pode servir a outros schemas: não remover a extensão compartilhada.
