from datetime import datetime, timedelta, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_role
from app.models.models import (
    CandidateProfile,
    CandidateSpecialization,
    Category,
    GradeChangeLog,
    ItemTemplate,
    Specialization,
    TestAttempt,
    TestItem,
    UserRole,
)
from app.schemas.testing import (
    SurveyIn, SurveyOut, AttemptStartIn, AttemptOut, NextItemOut,
    AnswerIn, AnswerOut, FinishOut, SpecializationStatusOut,
)
from app.domain.irt import estimate_theta, fisher_information, grade_for_theta
from app.domain.items.templates import generate, grade


router = APIRouter(tags=["testing"])

MIN_ITEMS = 8
MAX_ITEMS = 15
EXTENDED_MAX_ITEMS = 20
GRADE_ORDER = ["junior", "middle", "senior", "lead"]


def _next_grade(grade_name: str) -> str | None:
    try:
        idx = GRADE_ORDER.index(grade_name)
    except ValueError:
        return None
    return GRADE_ORDER[idx + 1] if idx + 1 < len(GRADE_ORDER) else None


async def _candidate(db: AsyncSession, user_id: int) -> CandidateProfile:
    p = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
    if not p:
        raise HTTPException(404, "Candidate profile not found")
    return p


async def _candidate_specialization(
    db: AsyncSession, candidate_id: int, specialization_id: int
) -> CandidateSpecialization | None:
    return await db.scalar(
        select(CandidateSpecialization).where(
            CandidateSpecialization.candidate_id == candidate_id,
            CandidateSpecialization.specialization_id == specialization_id,
        )
    )


async def _responses(db: AsyncSession, attempt: TestAttempt):
    rows = (
        await db.execute(
            select(TestItem, ItemTemplate)
            .join(ItemTemplate, TestItem.template_id == ItemTemplate.id)
            .where(TestItem.attempt_id == attempt.id, TestItem.answered_at.is_not(None))
            .order_by(TestItem.id)
        )
    ).all()
    return [(1 if item.is_correct else 0, tpl.irt_a, tpl.irt_b) for item, tpl in rows]


async def _recompute(db: AsyncSession, attempt: TestAttempt) -> None:
    responses = await _responses(db, attempt)
    state = estimate_theta(responses, initial_theta=attempt.theta)
    attempt.theta = state.theta
    attempt.se = state.se


async def _category_for(
    db: AsyncSession, specialization_id: int, grade_name: str
) -> Category | None:
    return await db.scalar(
        select(Category).where(
            Category.specialization_id == specialization_id,
            Category.grade == grade_name,
        )
    )


async def _finalize(db: AsyncSession, attempt: TestAttempt) -> FinishOut:
    candidate = await db.get(CandidateProfile, attempt.candidate_id)
    if not candidate or not attempt.specialization_id:
        raise HTTPException(500, "Attempt specialization is missing")

    candidate_spec = await _candidate_specialization(
        db, candidate.id, attempt.specialization_id
    )
    if not candidate_spec:
        raise HTTPException(500, "Candidate specialization record is missing")

    requested = attempt.requested_grade
    lower_requested = {"junior": -float("inf"), "middle": -0.5, "senior": 0.7, "lead": 1.8}[requested]
    upper_requested = {"junior": -0.5, "middle": 0.7, "senior": 1.8, "lead": float("inf")}[requested]

    confirmed = None
    recommended_grade = None
    if attempt.se <= 0.45:
        if lower_requested <= attempt.theta < upper_requested:
            confirmed = requested
        elif attempt.theta >= upper_requested:
            recommended_grade = _next_grade(requested)
    category_name = None
    if confirmed:
        category = await _category_for(db, attempt.specialization_id, confirmed)
        specialization = await db.get(Specialization, attempt.specialization_id)
        if category:
            candidate_spec.confirmed_grade = confirmed
            candidate_spec.category_id = category.id
            candidate_spec.theta = attempt.theta
            candidate_spec.grade_change_allowed_at = datetime.now(timezone.utc) + timedelta(days=90)
            category_name = f"{specialization.code} / {confirmed}" if specialization else confirmed
            db.add(
                GradeChangeLog(
                    candidate_id=candidate.id,
                    specialization_id=attempt.specialization_id,
                    old_grade=None,
                    new_grade=confirmed,
                )
            )
            # Keep legacy Day 1 fields synchronized with the most recent result.
            candidate.specialization_id = attempt.specialization_id
            candidate.declared_grade = candidate_spec.declared_grade
            candidate.confirmed_grade = confirmed
            candidate.category_id = category.id
            candidate.theta = attempt.theta

    attempt.status = "finished"
    attempt.finished_at = datetime.now(timezone.utc)
    await db.flush()

    return FinishOut(
        attempt_id=attempt.id,
        status=attempt.status,
        theta=round(attempt.theta, 4),
        se=round(attempt.se, 4),
        grade=confirmed,
        category=category_name,
        specialization=specialization.code if confirmed and specialization else None,
        recommended_grade=recommended_grade,
        grade_change_allowed_at=(
            candidate_spec.grade_change_allowed_at.isoformat()
            if confirmed and candidate_spec.grade_change_allowed_at
            else None
        ),
    )


@router.get("/me/testing/specializations", response_model=list[SpecializationStatusOut])
async def my_testing_specializations(
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    p = await _candidate(db, u.id)
    rows = (
        await db.execute(
            select(CandidateSpecialization, Specialization)
            .join(Specialization, CandidateSpecialization.specialization_id == Specialization.id)
            .where(CandidateSpecialization.candidate_id == p.id)
            .order_by(Specialization.name)
        )
    ).all()
    return [
        SpecializationStatusOut(
            specialization=s.code,
            specialization_name=s.name,
            declared_grade=cs.declared_grade,
            confirmed_grade=cs.confirmed_grade,
            theta=round(cs.theta, 4) if cs.theta is not None else None,
            grade_change_allowed_at=(
                cs.grade_change_allowed_at.isoformat()
                if cs.grade_change_allowed_at
                else None
            ),
        )
        for cs, s in rows
    ]


@router.post("/survey", response_model=SurveyOut)
async def save_survey(
    data: SurveyIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    p = await _candidate(db, u.id)
    specialization = await db.scalar(
        select(Specialization).where(Specialization.code == data.specialization)
    )
    if not specialization:
        raise HTTPException(400, "Unknown specialization")
    category = await _category_for(db, specialization.id, data.declared_grade)
    if not category:
        raise HTTPException(400, "Unknown grade")

    existing = await _candidate_specialization(db, p.id, specialization.id)
    if existing and existing.grade_change_allowed_at and existing.grade_change_allowed_at > datetime.now(timezone.utc):
        if existing.confirmed_grade and existing.confirmed_grade != data.declared_grade:
            raise HTTPException(409, "Grade change for this specialization is not available yet")

    if not existing:
        existing = CandidateSpecialization(
            candidate_id=p.id,
            specialization_id=specialization.id,
            declared_grade=data.declared_grade,
        )
        db.add(existing)
    else:
        existing.declared_grade = data.declared_grade

    p.industry = data.industry.strip()
    # Legacy fields remain synchronized with the currently selected specialization.
    p.specialization_id = specialization.id
    p.declared_grade = data.declared_grade
    await db.commit()

    return SurveyOut(
        industry=p.industry,
        specialization=specialization.code,
        declared_grade=data.declared_grade,
        category_id=existing.category_id,
        confirmed_grade=existing.confirmed_grade,
        grade_change_allowed_at=(
            existing.grade_change_allowed_at.isoformat()
            if existing.grade_change_allowed_at
            else None
        ),
    )


@router.post("/test/attempts", response_model=AttemptOut, status_code=201)
async def start_attempt(
    data: AttemptStartIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    p = await _candidate(db, u.id)
    specialization = await db.scalar(
        select(Specialization).where(Specialization.code == data.specialization)
    )
    if not specialization:
        raise HTTPException(400, "Unknown specialization")
    candidate_spec = await _candidate_specialization(db, p.id, specialization.id)
    if not candidate_spec:
        raise HTTPException(400, "Complete the survey for this specialization first")
    if candidate_spec.grade_change_allowed_at and candidate_spec.grade_change_allowed_at > datetime.now(timezone.utc):
        if candidate_spec.confirmed_grade and candidate_spec.confirmed_grade != data.grade:
            raise HTTPException(409, "Grade change is not available yet for this specialization")
    active = await db.scalar(
        select(TestAttempt).where(
            TestAttempt.candidate_id == p.id,
            TestAttempt.status == "active",
        )
    )
    if active:
        raise HTTPException(409, "An active test attempt already exists")
    if data.grade != candidate_spec.declared_grade:
        raise HTTPException(400, "Attempt grade must match the declared grade for this specialization")
    count = await db.scalar(
        select(func.count(ItemTemplate.id)).where(
            ItemTemplate.specialization_id == specialization.id,
            ItemTemplate.is_active.is_(True),
        )
    )
    if (count or 0) < 30:
        raise HTTPException(503, "Testing pool is not calibrated")
    attempt = TestAttempt(
        candidate_id=p.id,
        specialization_id=specialization.id,
        requested_grade=data.grade,
        theta=0.0,
        se=1.0,
        status="active",
    )
    db.add(attempt)
    await db.commit()
    await db.refresh(attempt)
    return AttemptOut(
        id=attempt.id,
        requested_grade=attempt.requested_grade,
        theta=attempt.theta,
        se=attempt.se,
        status=attempt.status,
        answered_count=0,
    )


@router.get("/test/attempts/{attempt_id}/next", response_model=NextItemOut)
async def next_item(
    attempt_id: int,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    p = await _candidate(db, u.id)
    attempt = await db.get(TestAttempt, attempt_id)
    if not attempt or attempt.candidate_id != p.id:
        raise HTTPException(404, "Attempt not found")
    if attempt.status != "active":
        raise HTTPException(409, "Test attempt is finished")
    if not attempt.specialization_id:
        raise HTTPException(500, "Attempt specialization is missing")

    answered = (
        await db.scalar(
            select(func.count(TestItem.id)).where(
                TestItem.attempt_id == attempt.id,
                TestItem.answered_at.is_not(None),
            )
        )
        or 0
    )
    if answered >= EXTENDED_MAX_ITEMS or (answered >= MAX_ITEMS and attempt.se <= 0.45) or (answered >= MIN_ITEMS and attempt.se < 0.3):
        raise HTTPException(409, "Stop rule reached; finish the attempt")

    used = set((await db.scalars(select(TestItem.template_id).where(TestItem.attempt_id == attempt.id))).all())
    templates = (
        await db.scalars(
            select(ItemTemplate).where(
                ItemTemplate.specialization_id == attempt.specialization_id,
                ItemTemplate.is_active.is_(True),
            )
        )
    ).all()
    available = [tpl for tpl in templates if tpl.id not in used]
    if not available:
        raise HTTPException(409, "No unused test items remain")

    template = max(available, key=lambda tpl: fisher_information(attempt.theta, tpl.irt_a, tpl.irt_b))
    seed = (
        int.from_bytes(
            hashlib.sha256(f"{p.id}:{attempt.id}:{template.id}".encode()).digest()[:4],
            "big",
        )
        % 2_000_000_000
    )
    item = TestItem(
        attempt_id=attempt.id,
        candidate_id=p.id,
        template_id=template.id,
        seed=seed,
        theta_before=attempt.theta,
        se_before=attempt.se,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    inst = generate(template.code, seed)
    return NextItemOut(
        attempt_id=attempt.id,
        item_id=item.id,
        prompt=inst.prompt,
        answer_type=inst.answer_type,
        progress=answered,
    )


@router.post("/test/items/{item_id}/answer", response_model=AnswerOut)
async def answer_item(
    item_id: int,
    data: AnswerIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    p = await _candidate(db, u.id)
    row = await db.scalar(select(TestItem).where(TestItem.id == item_id, TestItem.candidate_id == p.id))
    if not row:
        raise HTTPException(404, "Test item not found")
    if row.answered_at:
        raise HTTPException(409, "Item already answered")
    attempt = await db.get(TestAttempt, row.attempt_id)
    if not attempt or attempt.status != "active":
        raise HTTPException(409, "Attempt is not active")
    template = await db.get(ItemTemplate, row.template_id)
    if not template:
        raise HTTPException(404, "Template not found")

    correct = grade(template.code, row.seed, data.answer)
    row.answer_raw = data.answer
    row.is_correct = correct
    row.answered_at = datetime.now(timezone.utc)
    await _recompute(db, attempt)

    answered = (
        await db.scalar(
            select(func.count(TestItem.id)).where(
                TestItem.attempt_id == attempt.id,
                TestItem.answered_at.is_not(None),
            )
        )
        or 0
    )
    finished = answered >= EXTENDED_MAX_ITEMS or (answered >= MAX_ITEMS and attempt.se <= 0.45) or (answered >= MIN_ITEMS and attempt.se < 0.3)
    result_grade = None
    if finished:
        result = await _finalize(db, attempt)
        result_grade = result.grade
    await db.commit()
    return AnswerOut(
        correct=correct,
        theta=round(attempt.theta, 4),
        se=round(attempt.se, 4),
        progress=answered,
        finished=finished,
        grade=result_grade,
    )


@router.post("/test/attempts/{attempt_id}/finish", response_model=FinishOut)
async def finish_attempt(
    attempt_id: int,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    p = await _candidate(db, u.id)
    attempt = await db.get(TestAttempt, attempt_id)
    if not attempt or attempt.candidate_id != p.id:
        raise HTTPException(404, "Attempt not found")
    if attempt.status == "finished":
        candidate_spec = await _candidate_specialization(db, p.id, attempt.specialization_id) if attempt.specialization_id else None
        specialization = await db.get(Specialization, attempt.specialization_id) if attempt.specialization_id else None
        category = await db.get(Category, candidate_spec.category_id) if candidate_spec and candidate_spec.category_id else None
        recommended_grade = _next_grade(attempt.requested_grade) if attempt.se <= 0.45 and attempt.theta >= {"junior": -0.5, "middle": 0.7, "senior": 1.8, "lead": float("inf")}[attempt.requested_grade] else None
        return FinishOut(
            attempt_id=attempt.id,
            status=attempt.status,
            theta=round(attempt.theta, 4),
            se=round(attempt.se, 4),
            grade=candidate_spec.confirmed_grade if candidate_spec else None,
            recommended_grade=recommended_grade,
            category=f"{specialization.code} / {candidate_spec.confirmed_grade}" if category and specialization and candidate_spec and candidate_spec.confirmed_grade else None,
            specialization=specialization.code if specialization else None,
            grade_change_allowed_at=(
                candidate_spec.grade_change_allowed_at.isoformat()
                if candidate_spec and candidate_spec.grade_change_allowed_at
                else None
            ),
        )
    answered = (
        await db.scalar(select(func.count(TestItem.id)).where(TestItem.attempt_id == attempt.id, TestItem.answered_at.is_not(None)))
        or 0
    )
    if answered < MIN_ITEMS:
        raise HTTPException(400, f"At least {MIN_ITEMS} answered items are required")
    await _recompute(db, attempt)
    result = await _finalize(db, attempt)
    await db.commit()
    return result


@router.post("/dev/time-travel")
async def time_travel(
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    from app.core.config import settings
    if settings.app_env != "dev":
        raise HTTPException(404, "Not found")
    p = await _candidate(db, u.id)
    rows = (await db.scalars(select(CandidateSpecialization).where(CandidateSpecialization.candidate_id == p.id))).all()
    for row in rows:
        row.grade_change_allowed_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db.commit()
    return {"ok": True, "updated_specializations": len(rows)}
