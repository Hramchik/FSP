"""day 2 testing, IRT, CAT and candidate survey

Revision ID: 0002_day2_testing
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_day2_testing"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("candidate_profile", sa.Column("specialization_id", sa.Integer(), nullable=True))
    op.add_column("candidate_profile", sa.Column("declared_grade", sa.String(32), nullable=True))
    op.add_column("candidate_profile", sa.Column("confirmed_grade", sa.String(32), nullable=True))
    op.add_column("candidate_profile", sa.Column("grade_change_allowed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_candidate_profile_specialization_id", "candidate_profile", ["specialization_id"])
    op.create_foreign_key(
        "fk_candidate_profile_specialization",
        "candidate_profile",
        "specialization",
        ["specialization_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_candidate_profile_specialization", "candidate_profile", type_="foreignkey")
    op.drop_index("ix_candidate_profile_specialization_id", table_name="candidate_profile")
    op.drop_column("candidate_profile", "grade_change_allowed_at")
    op.drop_column("candidate_profile", "confirmed_grade")
    op.drop_column("candidate_profile", "declared_grade")
    op.drop_column("candidate_profile", "specialization_id")
