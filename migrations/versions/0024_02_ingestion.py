"""Evidências e revisões tipadas, imutáveis após selo."""
from pathlib import Path
from alembic import op

revision = "0024_02"
down_revision = "0024_01"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql((Path(__file__).parents[1] / "sql/0024_02_ingestion.sql").read_text(encoding="utf-8"), execution_options={"no_parameters": True})


def downgrade():
    op.get_bind().exec_driver_sql((Path(__file__).parents[1] / "sql/0024_02_down.sql").read_text(encoding="utf-8"), execution_options={"no_parameters": True})
