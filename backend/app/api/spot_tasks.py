"""Regular short tasks from employers.

The specification asks for a periodic nudge that keeps a profile current. Two
kinds exist, and the difference matters for the anti-sharing property:

* ``generated`` draws from the calibrated item bank with a per-candidate seed,
  so the wording and the numbers differ for every person and the answer is
  recomputed on the server — sharing it is useless;
* ``open`` is the employer's own question where the candidate describes an
  approach; it is read by a human, which is the point.

A candidate is never handed more than one open assignment per employer task,
and answering refreshes the activity component of their match score.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_role
from app.domain.items.templates import generate, grade as grade_answer
from app.models.models import (
    CandidateProfile,
    CandidateSpecialization,
    EmployerProfile,
    ItemTemplate,
    Specialization,
    SpotTask,
    SpotTaskAssignment,
    UserRole,
)
from app.schemas.engagement import SpotAnswerIn, SpotAssignmentOut, SpotTaskIn, SpotTaskOut

router = APIRouter(tags=["spot-tasks"])

# How often a candidate may be handed a new regular task.
ASSIGNMENT_COOLDOWN = timedelta(days=7)


async def _employer(db: AsyncSession, user_id: int) -> EmployerProfile:
    profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
    if not profile:
        raise HTTPException(404, "Профиль работодателя не найден")
    return profile


async def _task_out(db: AsyncSession, task: SpotTask) -> SpotTaskOut:
    assigned = await db.scalar(
        select(func.count(SpotTaskAssignment.id)).where(SpotTaskAssignment.task_id == task.id)
    )
    answered = await db.scalar(
        select(func.count(SpotTaskAssignment.id)).where(
            SpotTaskAssignment.task_id == task.id, SpotTaskAssignment.status == "answered"
        )
    )
    return SpotTaskOut(
        id=task.id,
        title=task.title,
        prompt=task.prompt,
        kind=task.kind,
        specialization_code=task.specialization_code,
        grade=task.grade,
        is_active=task.is_active,
        created_at=task.created_at.isoformat(),
        assigned_count=assigned or 0,
        answered_count=answered or 0,
    )


@router.post("/spot-tasks", response_model=SpotTaskOut, status_code=201)
async def create_task(
    data: SpotTaskIn, u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)
):
    employer = await _employer(db, u.id)
    if not await db.scalar(select(Specialization).where(Specialization.code == data.specialization_code)):
        raise HTTPException(400, "Неизвестная специализация")
    if data.kind == "open" and len(data.prompt.strip()) < 10:
        raise HTTPException(400, "Для открытого задания нужен текст вопроса")
    task = SpotTask(
        employer_id=employer.id,
        title=data.title,
        prompt=data.prompt,
        kind=data.kind,
        specialization_code=data.specialization_code,
        grade=data.grade,
        is_active=data.is_active,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return await _task_out(db, task)


@router.get("/spot-tasks", response_model=list[SpotTaskOut])
async def list_tasks(u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)):
    employer = await _employer(db, u.id)
    rows = (
        await db.scalars(select(SpotTask).where(SpotTask.employer_id == employer.id).order_by(SpotTask.id.desc()))
    ).all()
    return [await _task_out(db, row) for row in rows]


@router.get("/spot-tasks/{task_id}/answers", response_model=list[SpotAssignmentOut])
async def task_answers(
    task_id: int, u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)
):
    employer = await _employer(db, u.id)
    task = await db.get(SpotTask, task_id)
    if not task or task.employer_id != employer.id:
        raise HTTPException(404, "Задание не найдено")
    rows = (
        await db.scalars(
            select(SpotTaskAssignment)
            .where(SpotTaskAssignment.task_id == task_id, SpotTaskAssignment.status == "answered")
            .order_by(SpotTaskAssignment.answered_at.desc())
        )
    ).all()
    out = []
    for row in rows:
        profile = await db.get(CandidateProfile, row.candidate_id)
        out.append(
            SpotAssignmentOut(
                id=row.id,
                task_id=row.task_id,
                title=task.title,
                prompt=row.prompt,
                kind=task.kind,
                status=row.status,
                assigned_at=row.assigned_at.isoformat(),
                answered_at=row.answered_at.isoformat() if row.answered_at else None,
                answer_text=row.answer_text,
                is_correct=row.is_correct,
                company_name=employer.company_name,
                candidate_name=(profile.display_name or f"Кандидат #{row.candidate_id}") if profile else None,
            )
        )
    return out


async def _materialize(db: AsyncSession, task: SpotTask, profile: CandidateProfile) -> SpotTaskAssignment:
    """Create one assignment, generating a per-candidate variant if needed."""
    template_code, seed, prompt = None, None, task.prompt
    if task.kind == "generated":
        specialization = await db.scalar(
            select(Specialization).where(Specialization.code == task.specialization_code)
        )
        templates = (
            await db.scalars(
                select(ItemTemplate).where(
                    ItemTemplate.specialization_id == specialization.id,
                    ItemTemplate.is_active.is_(True),
                    ItemTemplate.code.like(f"%_{task.grade}"),
                )
            )
        ).all()
        if not templates:
            raise HTTPException(503, "Банк заданий по этой категории пуст")
        digest = hashlib.sha256(f"spot:{task.id}:{profile.id}".encode()).digest()
        template = templates[int.from_bytes(digest[:2], "big") % len(templates)]
        seed = int.from_bytes(digest[2:6], "big") % 2_000_000_000
        template_code = template.code
        prompt = generate(template.code, seed).prompt

    assignment = SpotTaskAssignment(
        task_id=task.id,
        candidate_id=profile.id,
        template_code=template_code,
        seed=seed,
        prompt=prompt,
        status="assigned",
    )
    db.add(assignment)
    return assignment


@router.get("/me/spot-tasks", response_model=list[SpotAssignmentOut])
async def my_spot_tasks(u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)):
    """The candidate's regular-task inbox; hands out a new one when due.

    Assignment happens on read rather than from a scheduler: the MVP has no
    background worker, and the cadence rule is the same either way.
    """
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
    if not profile:
        return []

    if profile.accepts_spot_tasks:
        now = datetime.now(timezone.utc)
        last = await db.scalar(
            select(func.max(SpotTaskAssignment.assigned_at)).where(SpotTaskAssignment.candidate_id == profile.id)
        )
        pending = await db.scalar(
            select(func.count(SpotTaskAssignment.id)).where(
                SpotTaskAssignment.candidate_id == profile.id, SpotTaskAssignment.status == "assigned"
            )
        )
        due = not pending and (last is None or (now - (last if last.tzinfo else last.replace(tzinfo=timezone.utc))) >= ASSIGNMENT_COOLDOWN)
        if due:
            confirmed = (
                await db.execute(
                    select(CandidateSpecialization, Specialization)
                    .join(Specialization, CandidateSpecialization.specialization_id == Specialization.id)
                    .where(
                        CandidateSpecialization.candidate_id == profile.id,
                        CandidateSpecialization.confirmed_grade.is_not(None),
                    )
                )
            ).all()
            taken = set(
                (
                    await db.scalars(
                        select(SpotTaskAssignment.task_id).where(SpotTaskAssignment.candidate_id == profile.id)
                    )
                ).all()
            )
            for candidate_spec, specialization in confirmed:
                task = await db.scalar(
                    select(SpotTask)
                    .where(
                        SpotTask.is_active.is_(True),
                        SpotTask.specialization_code == specialization.code,
                        SpotTask.grade == candidate_spec.confirmed_grade,
                        SpotTask.id.notin_(taken) if taken else True,
                    )
                    .order_by(SpotTask.id.desc())
                    .limit(1)
                )
                if task:
                    await _materialize(db, task, profile)
                    break
            await db.commit()

    rows = (
        await db.scalars(
            select(SpotTaskAssignment)
            .where(SpotTaskAssignment.candidate_id == profile.id)
            .order_by(SpotTaskAssignment.id.desc())
        )
    ).all()
    out = []
    for row in rows:
        task = await db.get(SpotTask, row.task_id)
        employer = await db.get(EmployerProfile, task.employer_id) if task else None
        out.append(
            SpotAssignmentOut(
                id=row.id,
                task_id=row.task_id,
                title=task.title if task else "Задание",
                prompt=row.prompt,
                kind=task.kind if task else "open",
                status=row.status,
                assigned_at=row.assigned_at.isoformat(),
                answered_at=row.answered_at.isoformat() if row.answered_at else None,
                answer_text=row.answer_text,
                is_correct=row.is_correct,
                company_name=employer.company_name if employer else "",
            )
        )
    return out


@router.post("/me/spot-tasks/{assignment_id}/answer", response_model=SpotAssignmentOut)
async def answer_spot_task(
    assignment_id: int,
    data: SpotAnswerIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
    assignment = await db.get(SpotTaskAssignment, assignment_id)
    if not assignment or not profile or assignment.candidate_id != profile.id:
        raise HTTPException(404, "Задание не найдено")
    if assignment.status == "answered":
        raise HTTPException(409, "Ответ уже отправлен")

    task = await db.get(SpotTask, assignment.task_id)
    assignment.answer_text = data.answer
    assignment.status = "answered"
    assignment.answered_at = datetime.now(timezone.utc)
    # A generated task is graded on the server from (template, seed); the
    # reference answer never existed in the database or in any response.
    if assignment.template_code is not None and assignment.seed is not None:
        assignment.is_correct = grade_answer(assignment.template_code, assignment.seed, data.answer)
    profile.last_activity_at = assignment.answered_at
    await db.commit()
    await db.refresh(assignment)

    employer = await db.get(EmployerProfile, task.employer_id) if task else None
    return SpotAssignmentOut(
        id=assignment.id,
        task_id=assignment.task_id,
        title=task.title if task else "Задание",
        prompt=assignment.prompt,
        kind=task.kind if task else "open",
        status=assignment.status,
        assigned_at=assignment.assigned_at.isoformat(),
        answered_at=assignment.answered_at.isoformat(),
        answer_text=assignment.answer_text,
        is_correct=assignment.is_correct,
        company_name=employer.company_name if employer else "",
    )
