"""Passagem explícita e auditada XLSX→JSON, sem reescrever migrations aplicadas."""
from pathlib import Path
from alembic import op

revision = "0030_01"
down_revision = "0024_03"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql((Path(__file__).parents[1]/"sql/0030_01_baseline_activation.sql").read_text(encoding="utf-8"),execution_options={"no_parameters":True})


def downgrade():
    op.get_bind().exec_driver_sql((Path(__file__).parents[1]/"sql/0030_01_down.sql").read_text(encoding="utf-8"),execution_options={"no_parameters":True})
