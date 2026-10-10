"""add candidate industry for survey

Revision ID: 0003_candidate_industry
Revises: 0002_day2_testing
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_candidate_industry"
down_revision = "0002_day2_testing"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("candidate_profile", sa.Column("industry", sa.String(120), nullable=False, server_default="IT"))
    op.alter_column("candidate_profile", "industry", server_default=None)


def downgrade():
    op.drop_column("candidate_profile", "industry")
