"""separate candidate specialization state and per-specialization cooldown

Revision ID: 0003_candidate_specializations
Revises: 0002_day2_testing
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_candidate_specializations"
down_revision = "0003_candidate_industry"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "candidate_specialization",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("specialization_id", sa.Integer(), sa.ForeignKey("specialization.id", ondelete="CASCADE"), nullable=False),
        sa.Column("declared_grade", sa.String(32), nullable=False),
        sa.Column("confirmed_grade", sa.String(32), nullable=True),
        sa.Column("category_id", sa.Integer(), sa.ForeignKey("category.id"), nullable=True),
        sa.Column("theta", sa.Float(), nullable=True),
        sa.Column("grade_change_allowed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("candidate_id", "specialization_id", name="uq_candidate_specialization"),
    )
    op.create_index("ix_candidate_specialization_candidate_id", "candidate_specialization", ["candidate_id"])
    op.create_index("ix_candidate_specialization_specialization_id", "candidate_specialization", ["specialization_id"])

    op.add_column("test_attempt", sa.Column("specialization_id", sa.Integer(), nullable=True))
    op.create_index("ix_test_attempt_specialization_id", "test_attempt", ["specialization_id"])
    op.create_foreign_key(
        "fk_test_attempt_specialization",
        "test_attempt",
        "specialization",
        ["specialization_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.add_column("grade_change_log", sa.Column("specialization_id", sa.Integer(), nullable=True))
    op.create_index("ix_grade_change_log_specialization_id", "grade_change_log", ["specialization_id"])
    op.create_foreign_key(
        "fk_grade_change_log_specialization",
        "grade_change_log",
        "specialization",
        ["specialization_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Preserve existing Day 2 state by converting the old single-specialization
    # candidate fields into one per-specialization record.
    op.execute(sa.text("""
        INSERT INTO candidate_specialization
            (candidate_id, specialization_id, declared_grade, confirmed_grade, category_id, theta, grade_change_allowed_at)
        SELECT id, specialization_id, COALESCE(declared_grade, 'middle'), confirmed_grade,
               category_id, theta, grade_change_allowed_at
        FROM candidate_profile
        WHERE specialization_id IS NOT NULL
    """))
    op.execute(sa.text("""
        UPDATE test_attempt ta
        SET specialization_id = cp.specialization_id
        FROM candidate_profile cp
        WHERE ta.candidate_id = cp.id
          AND ta.specialization_id IS NULL
          AND cp.specialization_id IS NOT NULL
    """))
    op.execute(sa.text("""
        UPDATE grade_change_log g
        SET specialization_id = cp.specialization_id
        FROM candidate_profile cp
        WHERE g.candidate_id = cp.id
          AND cp.specialization_id IS NOT NULL
    """))


def downgrade():
    op.drop_constraint("fk_grade_change_log_specialization", "grade_change_log", type_="foreignkey")
    op.drop_index("ix_grade_change_log_specialization_id", table_name="grade_change_log")
    op.drop_column("grade_change_log", "specialization_id")

    op.drop_constraint("fk_test_attempt_specialization", "test_attempt", type_="foreignkey")
    op.drop_index("ix_test_attempt_specialization_id", table_name="test_attempt")
    op.drop_column("test_attempt", "specialization_id")

    op.drop_index("ix_candidate_specialization_specialization_id", table_name="candidate_specialization")
    op.drop_index("ix_candidate_specialization_candidate_id", table_name="candidate_specialization")
    op.drop_table("candidate_specialization")
