"""Direct search over the candidate bank.

The shortlist is the primary mechanic; this is the manual fallback the
specification also asks for. It filters the same category-based pool and never
returns anyone who has not confirmed a category or who kept their profile
private.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_role
from app.domain import skills as skills_vocab
from app.models.models import (
    CandidateProfile,
    CandidateSpecialization,
    EmployerProfile,
    Specialization,
    UserRole,
)
from app.schemas.matching import CandidateCardOut, SearchOut, SearchQuery
from app.services import fsp_registry
from app.services.cards import candidate_card

router = APIRouter(tags=["search"])


@router.post("/candidates/search", response_model=SearchOut)
async def search_candidates(
    data: SearchQuery,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == u.id))
    employer_id = employer.id if employer else None

    stmt = (
        select(CandidateProfile, CandidateSpecialization, Specialization)
        .join(CandidateSpecialization, CandidateSpecialization.candidate_id == CandidateProfile.id)
        .join(Specialization, CandidateSpecialization.specialization_id == Specialization.id)
        .where(
            CandidateProfile.is_searchable.is_(True),
            CandidateSpecialization.confirmed_grade.is_not(None),
        )
    )
    if data.specialization_code:
        stmt = stmt.where(Specialization.code == data.specialization_code)
    if data.grades:
        stmt = stmt.where(CandidateSpecialization.confirmed_grade.in_(data.grades))

    rows = (await db.execute(stmt)).all()

    # The free-text box is resolved through the same vocabulary the employer
    # need uses, so "ищу питониста с кафкой" filters on python + kafka.
    wanted = set(skills_vocab.normalize_many(data.skills)) | set(skills_vocab.extract(data.query))

    matched = []
    for profile, candidate_spec, specialization in rows:
        owned = set(profile.skills or [])
        if wanted and not wanted.issubset(owned):
            continue
        if data.city and (profile.city or "").strip().lower() != data.city.strip().lower():
            continue
        if data.work_format and (profile.work_format or "") != data.work_format:
            continue
        if data.fsp_only:
            fsp = await fsp_registry.profile_for_candidate(db, profile.id)
            if not (fsp["linked"] and profile.show_fsp and fsp["count"]):
                continue
        matched.append((profile, candidate_spec, specialization))

    # Strongest confirmed profile first: θ, then experience.
    matched.sort(key=lambda row: ((row[1].theta if row[1].theta is not None else -9), row[0].years_experience or 0), reverse=True)
    page = matched[data.offset: data.offset + data.limit]

    items = [
        CandidateCardOut(**await candidate_card(db, profile, specialization.code, employer_id))
        for profile, _, specialization in page
    ]
    await db.commit()
    return SearchOut(total=len(matched), items=items)


@router.get("/candidates/{candidate_id}", response_model=CandidateCardOut)
async def candidate_detail(
    candidate_id: int,
    specialization: str,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == u.id))
    profile = await db.get(CandidateProfile, candidate_id)
    if not profile or not profile.is_searchable:
        from fastapi import HTTPException
        raise HTTPException(404, "Кандидат не найден или скрыл профиль")
    card = await candidate_card(db, profile, specialization, employer.id if employer else None)
    await db.commit()
    return CandidateCardOut(**card)
