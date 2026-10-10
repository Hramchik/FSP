"""Published vacancies and candidate-initiated applications.

Secondary to the invitation flow by design: this is the classic direction, kept
so that a candidate who has not been invited yet can still act. Contacts open
on an application for the same reason they open on an accepted invitation — the
candidate initiated the contact.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import current_user, require_role
from app.domain import skills as skills_vocab
from app.models.models import (
    Application,
    CandidateProfile,
    EmployerProfile,
    Specialization,
    UserRole,
    Vacancy,
)
from app.schemas.engagement import (
    ApplicationDecisionIn,
    ApplicationIn,
    ApplicationOut,
    VacancyIn,
    VacancyOut,
)
from app.services.cards import candidate_card

router = APIRouter(tags=["vacancies"])


async def _employer(db: AsyncSession, user_id: int) -> EmployerProfile:
    profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
    if not profile:
        raise HTTPException(404, "Профиль работодателя не найден")
    return profile


async def _vacancy_out(db: AsyncSession, vacancy: Vacancy, candidate_id: int | None = None) -> VacancyOut:
    employer = await db.get(EmployerProfile, vacancy.employer_id)
    count = await db.scalar(
        select(func.count(Application.id)).where(Application.vacancy_id == vacancy.id)
    )
    mine = None
    if candidate_id:
        row = await db.scalar(
            select(Application).where(
                Application.vacancy_id == vacancy.id, Application.candidate_id == candidate_id
            )
        )
        mine = row.status if row else None
    return VacancyOut(
        id=vacancy.id,
        title=vacancy.title,
        description=vacancy.description,
        specialization_code=vacancy.specialization_code,
        grade=vacancy.grade,
        skills=list(vacancy.skills or []),
        skill_labels=skills_vocab.labels(vacancy.skills or []),
        city=vacancy.city,
        work_format=vacancy.work_format,
        salary_from=vacancy.salary_from,
        salary_to=vacancy.salary_to,
        is_published=vacancy.is_published,
        created_at=vacancy.created_at.isoformat(),
        company_name=employer.company_name if employer else "",
        employer={
            "company_name": employer.company_name if employer else "",
            "description": employer.description if employer else "",
            "website": employer.website if employer else "",
            "city": employer.city if employer else "",
        },
        applications_count=count or 0,
        my_application_status=mine,
    )


@router.post("/vacancies", response_model=VacancyOut, status_code=201)
async def create_vacancy(
    data: VacancyIn, u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)
):
    employer = await _employer(db, u.id)
    if not await db.scalar(select(Specialization).where(Specialization.code == data.specialization_code)):
        raise HTTPException(400, "Неизвестная специализация")
    explicit = skills_vocab.normalize_many(data.skills)
    merged = explicit + [c for c in skills_vocab.extract(data.description) if c not in explicit]
    vacancy = Vacancy(
        employer_id=employer.id,
        title=data.title,
        description=data.description,
        specialization_code=data.specialization_code,
        grade=data.grade,
        skills=merged,
        city=data.city,
        work_format=data.work_format,
        salary_from=data.salary_from,
        salary_to=data.salary_to,
        is_published=data.is_published,
    )
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)
    return await _vacancy_out(db, vacancy)


@router.get("/employer/vacancies", response_model=list[VacancyOut])
async def my_vacancies(u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)):
    employer = await _employer(db, u.id)
    rows = (
        await db.scalars(select(Vacancy).where(Vacancy.employer_id == employer.id).order_by(Vacancy.id.desc()))
    ).all()
    return [await _vacancy_out(db, row) for row in rows]


@router.put("/vacancies/{vacancy_id}", response_model=VacancyOut)
async def update_vacancy(
    vacancy_id: int,
    data: VacancyIn,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await _employer(db, u.id)
    vacancy = await db.get(Vacancy, vacancy_id)
    if not vacancy or vacancy.employer_id != employer.id:
        raise HTTPException(404, "Вакансия не найдена")
    explicit = skills_vocab.normalize_many(data.skills)
    for field, value in data.model_dump().items():
        if field != "skills":
            setattr(vacancy, field, value)
    vacancy.skills = explicit + [c for c in skills_vocab.extract(data.description) if c not in explicit]
    await db.commit()
    await db.refresh(vacancy)
    return await _vacancy_out(db, vacancy)


@router.delete("/vacancies/{vacancy_id}", status_code=204)
async def delete_vacancy(
    vacancy_id: int, u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)
):
    employer = await _employer(db, u.id)
    vacancy = await db.get(Vacancy, vacancy_id)
    if not vacancy or vacancy.employer_id != employer.id:
        raise HTTPException(404, "Вакансия не найдена")
    await db.delete(vacancy)
    await db.commit()


@router.get("/vacancies", response_model=list[VacancyOut])
async def public_vacancies(
    specialization: str | None = None,
    grade: str | None = None,
    u=Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Vacancy).where(Vacancy.is_published.is_(True)).order_by(Vacancy.id.desc())
    if specialization:
        stmt = stmt.where(Vacancy.specialization_code == specialization)
    if grade:
        stmt = stmt.where(Vacancy.grade == grade)
    rows = (await db.scalars(stmt)).all()
    candidate_id = None
    if u.role == UserRole.candidate:
        profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
        candidate_id = profile.id if profile else None
    return [await _vacancy_out(db, row, candidate_id) for row in rows]


@router.post("/vacancies/{vacancy_id}/apply", response_model=ApplicationOut, status_code=201)
async def apply(
    vacancy_id: int,
    data: ApplicationIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
    if not profile:
        raise HTTPException(404, "Профиль кандидата не найден")
    vacancy = await db.get(Vacancy, vacancy_id)
    if not vacancy or not vacancy.is_published:
        raise HTTPException(404, "Вакансия не найдена")
    if await db.scalar(
        select(Application).where(Application.candidate_id == profile.id, Application.vacancy_id == vacancy_id)
    ):
        raise HTTPException(409, "Вы уже откликались на эту вакансию")

    application = Application(
        candidate_id=profile.id, vacancy_id=vacancy_id, message=data.message, status="sent"
    )
    db.add(application)
    profile.last_activity_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(application)
    return await _application_out(db, application)


async def _application_out(db: AsyncSession, application: Application, with_candidate: bool = False) -> ApplicationOut:
    vacancy = await db.get(Vacancy, application.vacancy_id)
    employer = await db.get(EmployerProfile, vacancy.employer_id) if vacancy else None
    payload = ApplicationOut(
        id=application.id,
        status=application.status,
        message=application.message,
        created_at=application.created_at.isoformat(),
        responded_at=application.responded_at.isoformat() if application.responded_at else None,
        vacancy_id=application.vacancy_id,
        vacancy_title=vacancy.title if vacancy else "",
        company_name=employer.company_name if employer else "",
    )
    if with_candidate and vacancy:
        profile = await db.get(CandidateProfile, application.candidate_id)
        if profile:
            # An application is a candidate-initiated contact, so the card is
            # built with contacts enabled; visibility still has the final say.
            payload.candidate = await candidate_card(db, profile, vacancy.specialization_code, vacancy.employer_id)
    return payload


@router.get("/me/applications", response_model=list[ApplicationOut])
async def my_applications(u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
    if not profile:
        return []
    rows = (
        await db.scalars(
            select(Application).where(Application.candidate_id == profile.id).order_by(Application.id.desc())
        )
    ).all()
    return [await _application_out(db, row) for row in rows]


@router.get("/employer/applications", response_model=list[ApplicationOut])
async def incoming_applications(
    vacancy_id: int | None = None,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await _employer(db, u.id)
    stmt = (
        select(Application)
        .join(Vacancy, Application.vacancy_id == Vacancy.id)
        .where(Vacancy.employer_id == employer.id)
        .order_by(Application.id.desc())
    )
    if vacancy_id:
        stmt = stmt.where(Application.vacancy_id == vacancy_id)
    rows = (await db.scalars(stmt)).all()
    out = [await _application_out(db, row, with_candidate=True) for row in rows]
    await db.commit()
    return out


@router.post("/employer/applications/{application_id}/decision", response_model=ApplicationOut)
async def decide_application(
    application_id: int,
    data: ApplicationDecisionIn,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await _employer(db, u.id)
    application = await db.get(Application, application_id)
    if not application:
        raise HTTPException(404, "Отклик не найден")
    vacancy = await db.get(Vacancy, application.vacancy_id)
    if not vacancy or vacancy.employer_id != employer.id:
        raise HTTPException(404, "Отклик не найден")
    application.status = data.decision
    if data.decision in ("accepted", "declined"):
        application.responded_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(application)
    out = await _application_out(db, application, with_candidate=True)
    await db.commit()
    return out
