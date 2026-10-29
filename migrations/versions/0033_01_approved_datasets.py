"""Conjuntos privados aprovados, independentes da publicação individual."""

from pathlib import Path
from alembic import op

revision = "0033_01"
down_revision = "0031_01"
branch_labels = None
depends_on = None


def upgrade():
    op.get_bind().exec_driver_sql(
        (Path(__file__).parents[1] / "sql/0033_01_approved_datasets.sql").read_text(
            encoding="utf-8"
        ),
        execution_options={"no_parameters": True},
    )


def downgrade():
    op.execute("""DO $$ BEGIN
      IF EXISTS(SELECT FROM lb.dataset_policy) OR EXISTS(SELECT FROM lb.approved_dataset)
      THEN RAISE EXCEPTION 'Rollback bloqueado: conjuntos/políticas preenchidos'; END IF;
    END $$""")
    op.execute("""DROP VIEW lb.approved_dataset_info,lb.approved_external_draw_reference,lb.approved_component_value,
      lb.approved_result_attribute,lb.approved_result_series,lb.approved_prize_tier_result,
      lb.approved_monetary_fact,lb.approved_draw_revision""")
    op.execute(
        "DROP TABLE lb.active_dataset,lb.dataset_decision,lb.dataset_member,lb.approved_dataset,lb.dataset_policy"
    )
    op.execute("""DROP FUNCTION lb.guard_dataset(),lb.guard_dataset_member(),lb.check_dataset(),
      lb.guard_active_dataset(),lb.check_active_dataset()""")
    op.execute("ALTER TABLE lb.candidate_observation DROP CONSTRAINT observation_revision_context")
