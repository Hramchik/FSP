from datetime import datetime, timezone
from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base
import enum

class UserRole(str, enum.Enum):
    candidate = "candidate"
    employer = "employer"

class User(Base):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(512))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, values_callable=lambda x: [e.value for e in x], name="user_role"))
    is_email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class EmailVerificationToken(Base):
    __tablename__ = "email_verification_token"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    token: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class Consent(Base):
    __tablename__ = "consent"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class CandidateProfile(Base):
    __tablename__ = "candidate_profile"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), unique=True)
    display_name: Mapped[str] = mapped_column(String(160), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    industry: Mapped[str] = mapped_column(String(120), default="IT")
    work_format: Mapped[str] = mapped_column(String(80), default="remote")
    bio: Mapped[str] = mapped_column(Text, default="")
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    specialization_id: Mapped[int | None] = mapped_column(ForeignKey("specialization.id"))
    declared_grade: Mapped[str | None] = mapped_column(String(32))
    confirmed_grade: Mapped[str | None] = mapped_column(String(32))
    theta: Mapped[float | None] = mapped_column(Float)
    grade_change_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_searchable: Mapped[bool] = mapped_column(Boolean, default=False)
    phone: Mapped[str] = mapped_column(String(64), default="")
    telegram: Mapped[str] = mapped_column(String(64), default="")
    github: Mapped[str] = mapped_column(String(120), default="")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    roles: Mapped[list] = mapped_column(JSON, default=list)
    soft_skills: Mapped[list] = mapped_column(JSON, default=list)
    years_experience: Mapped[float] = mapped_column(Float, default=0.0)
    salary_expectation_from: Mapped[int | None] = mapped_column(Integer)
    salary_expectation_to: Mapped[int | None] = mapped_column(Integer)
    resume_text: Mapped[str] = mapped_column(Text, default="")
    # Visibility switches. Contacts are never shown before an accepted
    # invitation or an application, so there is no switch that can leak them.
    show_fsp: Mapped[bool] = mapped_column(Boolean, default=True)
    show_salary_expectation: Mapped[bool] = mapped_column(Boolean, default=True)
    show_city: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_publication: Mapped[bool] = mapped_column(Boolean, default=False)
    accepts_spot_tasks: Mapped[bool] = mapped_column(Boolean, default=True)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class EmployerProfile(Base):
    __tablename__ = "employer_profile"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id", ondelete="CASCADE"), unique=True)
    company_name: Mapped[str] = mapped_column(String(200), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    contact: Mapped[str] = mapped_column(String(320), default="")
    website: Mapped[str] = mapped_column(String(200), default="")
    industry: Mapped[str] = mapped_column(String(120), default="")
    city: Mapped[str] = mapped_column(String(120), default="")
    team_size: Mapped[str] = mapped_column(String(64), default="")

class Specialization(Base):
    __tablename__ = "specialization"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(120))

class Skill(Base):
    __tablename__ = "skill"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(120))

class SkillAlias(Base):
    __tablename__ = "skill_alias"
    id: Mapped[int] = mapped_column(primary_key=True)
    skill_id: Mapped[int] = mapped_column(ForeignKey("skill.id", ondelete="CASCADE"), index=True)
    alias: Mapped[str] = mapped_column(String(120), unique=True)

class Category(Base):
    __tablename__ = "category"
    id: Mapped[int] = mapped_column(primary_key=True)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specialization.id", ondelete="CASCADE"), index=True)
    grade: Mapped[str] = mapped_column(String(32))
    theta_min: Mapped[float | None] = mapped_column(Float)
    theta_max: Mapped[float | None] = mapped_column(Float)
    __table_args__ = (UniqueConstraint("specialization_id", "grade", name="uq_category_spec_grade"),)

class ItemTemplate(Base):
    __tablename__ = "item_template"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(120), unique=True)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specialization.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    irt_b: Mapped[float] = mapped_column(Float)
    irt_a: Mapped[float] = mapped_column(Float)
    param_space_size: Mapped[int] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    __table_args__ = (CheckConstraint("irt_a > 0", name="ck_item_irt_a_positive"), CheckConstraint("param_space_size >= 10000", name="ck_item_param_space"))

class CandidateSpecialization(Base):
    __tablename__ = "candidate_specialization"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    specialization_id: Mapped[int] = mapped_column(ForeignKey("specialization.id", ondelete="CASCADE"), index=True)
    declared_grade: Mapped[str] = mapped_column(String(32))
    confirmed_grade: Mapped[str | None] = mapped_column(String(32))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("category.id"))
    theta: Mapped[float | None] = mapped_column(Float)
    grade_change_allowed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("candidate_id", "specialization_id", name="uq_candidate_specialization"),)

class TestAttempt(Base):
    __tablename__ = "test_attempt"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    specialization_id: Mapped[int | None] = mapped_column(ForeignKey("specialization.id", ondelete="CASCADE"), index=True)
    requested_grade: Mapped[str] = mapped_column(String(32))
    theta: Mapped[float] = mapped_column(Float, default=0.0)
    se: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[str] = mapped_column(String(32), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

class TestItem(Base):
    __tablename__ = "test_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    attempt_id: Mapped[int] = mapped_column(ForeignKey("test_attempt.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("item_template.id", ondelete="CASCADE"), index=True)
    seed: Mapped[int] = mapped_column(Integer)
    served_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    answer_raw: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    theta_before: Mapped[float] = mapped_column(Float, default=0.0)
    se_before: Mapped[float] = mapped_column(Float, default=1.0)
    __table_args__ = (UniqueConstraint("attempt_id", "template_id", name="uq_test_item_template_once"), UniqueConstraint("candidate_id", "template_id", "seed", name="uq_candidate_template_seed"))

class GradeChangeLog(Base):
    __tablename__ = "grade_change_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    specialization_id: Mapped[int | None] = mapped_column(ForeignKey("specialization.id", ondelete="SET NULL"), index=True)
    old_grade: Mapped[str | None] = mapped_column(String(32))
    new_grade: Mapped[str] = mapped_column(String(32))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class FspLink(Base):
    __tablename__ = "fsp_link"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), unique=True)
    fsp_id: Mapped[str] = mapped_column(String(120), unique=True)
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    verified_by: Mapped[str] = mapped_column(String(80), default="mock")

class FspAchievement(Base):
    __tablename__ = "fsp_achievement"
    id: Mapped[int] = mapped_column(primary_key=True)
    fsp_id: Mapped[str] = mapped_column(String(120), index=True)
    event_name: Mapped[str] = mapped_column(String(240))
    event_level: Mapped[str] = mapped_column(String(64))
    place: Mapped[int] = mapped_column(Integer)
    participants_count: Mapped[int] = mapped_column(Integer)
    held_on: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

class Vacancy(Base):
    __tablename__ = "vacancy"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profile.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    salary_from: Mapped[int] = mapped_column(Integer)
    salary_to: Mapped[int] = mapped_column(Integer)
    specialization_code: Mapped[str] = mapped_column(String(32), default="backend")
    grade: Mapped[str] = mapped_column(String(32), default="middle")
    skills: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str] = mapped_column(String(120), default="")
    work_format: Mapped[str] = mapped_column(String(80), default="remote")
    is_published: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (CheckConstraint("salary_from > 0 AND salary_from <= salary_to", name="ck_vacancy_salary"),)

class EmployerNeed(Base):
    __tablename__ = "employer_need"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profile.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    text: Mapped[str] = mapped_column(Text)
    specialization_code: Mapped[str] = mapped_column(String(32))
    grade: Mapped[str] = mapped_column(String(32))
    skills: Mapped[list] = mapped_column(JSON, default=list)
    city: Mapped[str] = mapped_column(String(120), default="")
    work_format: Mapped[str] = mapped_column(String(80), default="")
    salary_from: Mapped[int | None] = mapped_column(Integer)
    salary_to: Mapped[int | None] = mapped_column(Integer)
    require_fsp: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class Shortlist(Base):
    __tablename__ = "shortlist"
    id: Mapped[int] = mapped_column(primary_key=True)
    need_id: Mapped[int] = mapped_column(ForeignKey("employer_need.id", ondelete="CASCADE"), index=True)
    weights_version: Mapped[str] = mapped_column(String(32), default="match-v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    # A refinement narrows the stored selection without regenerating it, so the
    # employer can always widen back to the list they originally received.
    refinement: Mapped[dict] = mapped_column(JSON, default=dict)

class ShortlistItem(Base):
    __tablename__ = "shortlist_item"
    id: Mapped[int] = mapped_column(primary_key=True)
    shortlist_id: Mapped[int] = mapped_column(ForeignKey("shortlist.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    score: Mapped[float] = mapped_column(Float, default=0)
    rank: Mapped[int] = mapped_column(Integer)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    category: Mapped[str] = mapped_column(String(80), default="")
    matched_skills: Mapped[list] = mapped_column(JSON, default=list)
    missing_skills: Mapped[list] = mapped_column(JSON, default=list)

class Invitation(Base):
    __tablename__ = "invitation"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profile.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    vacancy_id: Mapped[int | None] = mapped_column(ForeignKey("vacancy.id", ondelete="SET NULL"))
    need_id: Mapped[int | None] = mapped_column(ForeignKey("employer_need.id", ondelete="SET NULL"))
    company_name: Mapped[str] = mapped_column(String(200))
    offer_description: Mapped[str] = mapped_column(Text)
    salary_from: Mapped[int] = mapped_column(Integer)
    salary_to: Mapped[int] = mapped_column(Integer)
    contact_method: Mapped[str] = mapped_column(String(320))
    status: Mapped[str] = mapped_column(String(32), default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (CheckConstraint("salary_from > 0 AND salary_from <= salary_to", name="ck_invitation_salary"), UniqueConstraint("employer_id", "candidate_id", "vacancy_id", name="uq_invitation_pair"))

class InvitationEvent(Base):
    __tablename__ = "invitation_event"
    id: Mapped[int] = mapped_column(primary_key=True)
    invitation_id: Mapped[int] = mapped_column(ForeignKey("invitation.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ContactDisclosure(Base):
    __tablename__ = "contact_disclosure"
    id: Mapped[int] = mapped_column(primary_key=True)
    invitation_id: Mapped[int] = mapped_column(ForeignKey("invitation.id", ondelete="CASCADE"), unique=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"))
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profile.id", ondelete="CASCADE"))
    disclosed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    reason: Mapped[str] = mapped_column(String(32))

class Application(Base):
    __tablename__ = "application"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    vacancy_id: Mapped[int] = mapped_column(ForeignKey("vacancy.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(32), default="sent")
    message: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("candidate_id", "vacancy_id", name="uq_application_pair"),)


class SpotTask(Base):
    """A short recurring task authored by an employer.

    Two kinds are supported. ``generated`` reuses the calibrated item bank and
    is auto-graded from (template, seed), so the task text differs per
    candidate and cannot be shared. ``open`` is the employer's own question
    where the candidate describes an approach and the employer reads it.
    """
    __tablename__ = "spot_task"
    id: Mapped[int] = mapped_column(primary_key=True)
    employer_id: Mapped[int] = mapped_column(ForeignKey("employer_profile.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text, default="")
    kind: Mapped[str] = mapped_column(String(16), default="open")
    specialization_code: Mapped[str] = mapped_column(String(32))
    grade: Mapped[str] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    __table_args__ = (CheckConstraint("kind in ('open','generated')", name="ck_spot_task_kind"),)


class SpotTaskAssignment(Base):
    __tablename__ = "spot_task_assignment"
    id: Mapped[int] = mapped_column(primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("spot_task.id", ondelete="CASCADE"), index=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    template_code: Mapped[str | None] = mapped_column(String(120))
    seed: Mapped[int | None] = mapped_column(Integer)
    prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="assigned")
    answer_text: Mapped[str | None] = mapped_column(Text)
    is_correct: Mapped[bool | None] = mapped_column(Boolean)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    answered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("task_id", "candidate_id", name="uq_spot_task_candidate"),)


class ResumeUpload(Base):
    """Audit trail of an uploaded résumé and what the parser made of it."""
    __tablename__ = "resume_upload"
    id: Mapped[int] = mapped_column(primary_key=True)
    candidate_id: Mapped[int] = mapped_column(ForeignKey("candidate_profile.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(260))
    parsed: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
