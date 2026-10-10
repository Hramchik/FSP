"""day 3: needs, shortlists, invitations, vacancies, spot tasks, résumé profiles"""

from alembic import op
import sqlalchemy as sa

revision = "0005_day3_matching"
down_revision = "0004_candidate_specializations"
branch_labels = None
depends_on = None


def candidate_columns():
    return [
        sa.Column("phone", sa.String(64), server_default="", nullable=False),
        sa.Column("telegram", sa.String(64), server_default="", nullable=False),
        sa.Column("github", sa.String(120), server_default="", nullable=False),
        sa.Column("skills", sa.JSON, server_default="[]", nullable=False),
        sa.Column("roles", sa.JSON, server_default="[]", nullable=False),
        sa.Column("soft_skills", sa.JSON, server_default="[]", nullable=False),
        sa.Column("years_experience", sa.Float, server_default="0", nullable=False),
        sa.Column("salary_expectation_from", sa.Integer),
        sa.Column("salary_expectation_to", sa.Integer),
        sa.Column("resume_text", sa.Text, server_default="", nullable=False),
        sa.Column("show_fsp", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("show_salary_expectation", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("show_city", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("consent_publication", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("accepts_spot_tasks", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("last_activity_at", sa.DateTime(timezone=True)),
    ]

def employer_columns():
    return [
        sa.Column("website", sa.String(200), server_default="", nullable=False),
        sa.Column("industry", sa.String(120), server_default="", nullable=False),
        sa.Column("city", sa.String(120), server_default="", nullable=False),
        sa.Column("team_size", sa.String(64), server_default="", nullable=False),
    ]

def need_columns():
    return [
        sa.Column("title", sa.String(200), server_default="", nullable=False),
        sa.Column("city", sa.String(120), server_default="", nullable=False),
        sa.Column("work_format", sa.String(80), server_default="", nullable=False),
        sa.Column("salary_from", sa.Integer),
        sa.Column("salary_to", sa.Integer),
        sa.Column("require_fsp", sa.Boolean, server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]

def vacancy_columns():
    return [
        sa.Column("specialization_code", sa.String(32), server_default="backend", nullable=False),
        sa.Column("grade", sa.String(32), server_default="middle", nullable=False),
        sa.Column("skills", sa.JSON, server_default="[]", nullable=False),
        sa.Column("city", sa.String(120), server_default="", nullable=False),
        sa.Column("work_format", sa.String(80), server_default="remote", nullable=False),
        sa.Column("is_published", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    ]

def shortlist_item_columns():
    return [
        sa.Column("components", sa.JSON, server_default="{}", nullable=False),
        sa.Column("category", sa.String(80), server_default="", nullable=False),
        sa.Column("matched_skills", sa.JSON, server_default="[]", nullable=False),
        sa.Column("missing_skills", sa.JSON, server_default="[]", nullable=False),
    ]

def application_columns():
    return [
        sa.Column("message", sa.Text, server_default="", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("responded_at", sa.DateTime(timezone=True)),
    ]


def upgrade():
    for column in candidate_columns():
        op.add_column("candidate_profile", column)
    for column in employer_columns():
        op.add_column("employer_profile", column)
    for column in need_columns():
        op.add_column("employer_need", column)
    for column in vacancy_columns():
        op.add_column("vacancy", column)
    for column in shortlist_item_columns():
        op.add_column("shortlist_item", column)
    for column in application_columns():
        op.add_column("application", column)

    op.add_column("shortlist", sa.Column("refinement", sa.JSON, server_default="{}", nullable=False))
    op.add_column("invitation", sa.Column("need_id", sa.Integer, sa.ForeignKey("employer_need.id", ondelete="SET NULL")))
    op.add_column("invitation", sa.Column("viewed_at", sa.DateTime(timezone=True)))
    op.add_column("invitation", sa.Column("responded_at", sa.DateTime(timezone=True)))
    op.create_index("ix_employer_need_employer_id", "employer_need", ["employer_id"])
    op.create_unique_constraint("uq_application_pair", "application", ["candidate_id", "vacancy_id"])

    op.create_table(
        "spot_task",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("employer_id", sa.Integer, sa.ForeignKey("employer_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text, server_default="", nullable=False),
        sa.Column("kind", sa.String(16), server_default="open", nullable=False),
        sa.Column("specialization_code", sa.String(32), nullable=False),
        sa.Column("grade", sa.String(32), nullable=False),
        sa.Column("is_active", sa.Boolean, server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("kind in ('open','generated')", name="ck_spot_task_kind"),
    )
    op.create_index("ix_spot_task_employer_id", "spot_task", ["employer_id"])

    op.create_table(
        "spot_task_assignment",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("task_id", sa.Integer, sa.ForeignKey("spot_task.id", ondelete="CASCADE"), nullable=False),
        sa.Column("candidate_id", sa.Integer, sa.ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("template_code", sa.String(120)),
        sa.Column("seed", sa.Integer),
        sa.Column("prompt", sa.Text, nullable=False),
        sa.Column("status", sa.String(16), server_default="assigned", nullable=False),
        sa.Column("answer_text", sa.Text),
        sa.Column("is_correct", sa.Boolean),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("answered_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("task_id", "candidate_id", name="uq_spot_task_candidate"),
    )
    op.create_index("ix_spot_task_assignment_task_id", "spot_task_assignment", ["task_id"])
    op.create_index("ix_spot_task_assignment_candidate_id", "spot_task_assignment", ["candidate_id"])

    op.create_table(
        "resume_upload",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("candidate_id", sa.Integer, sa.ForeignKey("candidate_profile.id", ondelete="CASCADE"), nullable=False),
        sa.Column("filename", sa.String(260), nullable=False),
        sa.Column("parsed", sa.JSON, server_default="{}", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_resume_upload_candidate_id", "resume_upload", ["candidate_id"])


def downgrade():
    op.drop_table("resume_upload")
    op.drop_table("spot_task_assignment")
    op.drop_table("spot_task")
    op.drop_constraint("uq_application_pair", "application", type_="unique")
    op.drop_index("ix_employer_need_employer_id", table_name="employer_need")
    for column in ("need_id", "viewed_at", "responded_at"):
        op.drop_column("invitation", column)
    op.drop_column("shortlist", "refinement")
    for column in application_columns():
        op.drop_column("application", column.name)
    for column in shortlist_item_columns():
        op.drop_column("shortlist_item", column.name)
    for column in vacancy_columns():
        op.drop_column("vacancy", column.name)
    for column in need_columns():
        op.drop_column("employer_need", column.name)
    for column in employer_columns():
        op.drop_column("employer_profile", column.name)
    for column in candidate_columns():
        op.drop_column("candidate_profile", column.name)
