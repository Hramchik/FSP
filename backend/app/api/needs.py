"""Employer needs and the shortlists generated from them.

This is the reverse-hiring entry point: the employer describes who they need,
the platform routes that need to categories and returns ranked people with the
reason each of them is there. The employer never writes a search query over
résumés, because there are no résumés to search.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_role
from app.domain import matching
from app.domain import skills as skills_vocab
from app.models.models import (
    CandidateProfile,
    EmployerNeed,
    EmployerProfile,
    Invitation,
    Shortlist,
    ShortlistItem,
    Specialization,
    UserRole,
)
from app.schemas.matching import NeedIn, NeedOut, RefinementIn, ShortlistOut
from app.services import candidates as candidate_service
from app.services.cards import candidate_card

router = APIRouter(tags=["needs"])

SHORTLIST_POOL_LIMIT = 100


async def _employer(db: AsyncSession, user_id: int) -> EmployerProfile:
    profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user_id))
    if not profile:
        raise HTTPException(404, "Employer profile not found")
    return profile


async def _need_or_404(db: AsyncSession, need_id: int, employer_id: int) -> EmployerNeed:
    need = await db.get(EmployerNeed, need_id)
    if not need or need.employer_id != employer_id:
        raise HTTPException(404, "Потребность не найдена")
    return need


def _need_domain(need: EmployerNeed) -> matching.Need:
    return matching.Need(
        specialization=need.specialization_code,
        grade=need.grade,
        skills=tuple(need.skills or []),
        city=need.city or "",
        work_format=need.work_format or "",
        require_fsp=bool(need.require_fsp),
    )


async def _need_out(db: AsyncSession, need: EmployerNeed) -> NeedOut:
    shortlist = await db.scalar(
        select(Shortlist).where(Shortlist.need_id == need.id).order_by(Shortlist.id.desc()).limit(1)
    )
    return NeedOut(
        id=need.id,
        title=need.title,
        text=need.text,
        specialization_code=need.specialization_code,
        grade=need.grade,
        skills=list(need.skills or []),
        skill_labels=skills_vocab.labels(need.skills or []),
        city=need.city,
        work_format=need.work_format,
        salary_from=need.salary_from,
        salary_to=need.salary_to,
        require_fsp=need.require_fsp,
        created_at=need.created_at.isoformat(),
        shortlist_id=shortlist.id if shortlist else None,
        routed_categories=matching.routing_explanation(_need_domain(need)),
    )


async def _validate_specialization(db: AsyncSession, code: str) -> Specialization:
    specialization = await db.scalar(select(Specialization).where(Specialization.code == code))
    if not specialization:
        raise HTTPException(400, "Неизвестная специализация")
    return specialization


def _merge_skills(data: NeedIn) -> list[str]:
    """Typed skills plus whatever the free-text description names.

    The employer should be able to just write a paragraph: the structured
    requirement is derived from it, and the chips they picked take priority.
    """
    explicit = skills_vocab.normalize_many(data.skills)
    from_text = [code for code in skills_vocab.extract(data.text) if code not in explicit]
    return explicit + from_text


@router.post("/needs", response_model=NeedOut, status_code=201)
async def create_need(
    data: NeedIn,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await _employer(db, u.id)
    await _validate_specialization(db, data.specialization_code)
    need = EmployerNeed(
        employer_id=employer.id,
        title=data.title or f"{data.specialization_code} / {data.grade}",
        text=data.text,
        specialization_code=data.specialization_code,
        grade=data.grade,
        skills=_merge_skills(data),
        city=data.city,
        work_format=data.work_format,
        salary_from=data.salary_from,
        salary_to=data.salary_to,
        require_fsp=data.require_fsp,
    )
    db.add(need)
    await db.commit()
    await db.refresh(need)
    return await _need_out(db, need)


@router.get("/needs", response_model=list[NeedOut])
async def list_needs(u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)):
    employer = await _employer(db, u.id)
    rows = (
        await db.scalars(
            select(EmployerNeed).where(EmployerNeed.employer_id == employer.id).order_by(EmployerNeed.id.desc())
        )
    ).all()
    return [await _need_out(db, need) for need in rows]


@router.get("/needs/{need_id}", response_model=NeedOut)
async def get_need(need_id: int, u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)):
    employer = await _employer(db, u.id)
    return await _need_out(db, await _need_or_404(db, need_id, employer.id))


@router.put("/needs/{need_id}", response_model=NeedOut)
async def update_need(
    need_id: int,
    data: NeedIn,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await _employer(db, u.id)
    need = await _need_or_404(db, need_id, employer.id)
    await _validate_specialization(db, data.specialization_code)
    need.title = data.title or need.title
    need.text = data.text
    need.specialization_code = data.specialization_code
    need.grade = data.grade
    need.skills = _merge_skills(data)
    need.city = data.city
    need.work_format = data.work_format
    need.salary_from = data.salary_from
    need.salary_to = data.salary_to
    need.require_fsp = data.require_fsp
    await db.commit()
    await db.refresh(need)
    return await _need_out(db, need)


@router.delete("/needs/{need_id}", status_code=204)
async def delete_need(need_id: int, u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)):
    employer = await _employer(db, u.id)
    need = await _need_or_404(db, need_id, employer.id)
    await db.delete(need)
    await db.commit()


@router.post("/needs/{need_id}/shortlist", response_model=ShortlistOut, status_code=201)
async def build_shortlist(
    need_id: int,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """Run the matcher and persist the result.

    The stored list is the employer's working set: refinements filter it, they
    never re-run the matcher, so narrowing a search can always be undone.
    """
    employer = await _employer(db, u.id)
    need = await _need_or_404(db, need_id, employer.id)

    now = datetime.now(timezone.utc)
    features, profiles = await candidate_service.features_for_specialization(db, need.specialization_code, now)
    results = matching.rank(_need_domain(need), features, now, limit=SHORTLIST_POOL_LIMIT)

    shortlist = Shortlist(need_id=need.id, weights_version=matching.WEIGHTS_VERSION, refinement={})
    db.add(shortlist)
    await db.flush()
    for result in results:
        db.add(
            ShortlistItem(
                shortlist_id=shortlist.id,
                candidate_id=result.candidate_id,
                score=result.score,
                rank=result.rank,
                reasons=[{"code": r.code, "text": r.text, "contribution": r.contribution} for r in result.reasons],
                components=result.components,
                category=result.category,
                matched_skills=result.matched_skills,
                missing_skills=result.missing_skills,
            )
        )
    await db.commit()
    return await _render_shortlist(db, shortlist, need, employer.id, RefinementIn())


def _passes(item: ShortlistItem, profile: CandidateProfile, refinement: RefinementIn, fsp_strength: float,
            invited: bool) -> bool:
    if refinement.min_score is not None and item.score < refinement.min_score:
        return False
    if refinement.grades and (item.category.split("/")[-1].strip() not in refinement.grades):
        return False
    if refinement.skills and not set(refinement.skills).issubset(set(profile.skills or [])):
        return False
    if refinement.city and (profile.city or "").strip().lower() != refinement.city.strip().lower():
        return False
    if refinement.work_format and (profile.work_format or "") != refinement.work_format:
        return False
    if refinement.fsp_only and fsp_strength <= 0:
        return False
    if refinement.hide_invited and invited:
        return False
    return True


async def _render_shortlist(
    db: AsyncSession,
    shortlist: Shortlist,
    need: EmployerNeed,
    employer_id: int,
    refinement: RefinementIn,
) -> ShortlistOut:
    rows = (
        await db.scalars(
            select(ShortlistItem).where(ShortlistItem.shortlist_id == shortlist.id).order_by(ShortlistItem.rank)
        )
    ).all()

    invited_ids = set(
        (
            await db.scalars(
                select(Invitation.candidate_id).where(Invitation.employer_id == employer_id)
            )
        ).all()
    )

    items = []
    for item in rows:
        profile = await db.get(CandidateProfile, item.candidate_id)
        if not profile:
            continue
        fsp_strength = float((item.components or {}).get("fsp", 0.0))
        if not _passes(item, profile, refinement, fsp_strength, item.candidate_id in invited_ids):
            continue
        card = await candidate_card(db, profile, need.specialization_code, employer_id)
        items.append(
            {
                "rank": item.rank,
                "score": item.score,
                "category": item.category,
                "components": item.components or {},
                "reasons": item.reasons or [],
                "matched_skills": item.matched_skills or [],
                "missing_skills": item.missing_skills or [],
                "candidate": card,
            }
        )

    sort_key = {
        "score": lambda row: row["score"],
        "fsp": lambda row: row["components"].get("fsp", 0.0),
        "proof": lambda row: row["components"].get("proof", 0.0),
        "experience": lambda row: row["candidate"]["years_experience"],
    }[refinement.sort]
    items.sort(key=sort_key, reverse=True)
    # Ranks are re-numbered for the filtered view; the stored rank stays intact.
    for position, row in enumerate(items, start=1):
        row["rank"] = position

    await db.commit()
    return ShortlistOut(
        shortlist_id=shortlist.id,
        need_id=need.id,
        weights_version=shortlist.weights_version,
        created_at=shortlist.created_at.isoformat(),
        total_in_pool=len(rows),
        total_shown=len(items),
        routed_categories=matching.routing_explanation(_need_domain(need)),
        weights=matching.WEIGHTS,
        refinement=refinement,
        items=items,
    )


@router.get("/shortlists/{shortlist_id}", response_model=ShortlistOut)
async def get_shortlist(
    shortlist_id: int,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await _employer(db, u.id)
    shortlist = await db.get(Shortlist, shortlist_id)
    if not shortlist:
        raise HTTPException(404, "Подборка не найдена")
    need = await _need_or_404(db, shortlist.need_id, employer.id)
    refinement = RefinementIn(**(shortlist.refinement or {}))
    return await _render_shortlist(db, shortlist, need, employer.id, refinement)


@router.post("/shortlists/{shortlist_id}/refine", response_model=ShortlistOut)
async def refine_shortlist(
    shortlist_id: int,
    data: RefinementIn,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    """Narrow the stored selection. The underlying list is never discarded."""
    employer = await _employer(db, u.id)
    shortlist = await db.get(Shortlist, shortlist_id)
    if not shortlist:
        raise HTTPException(404, "Подборка не найдена")
    need = await _need_or_404(db, shortlist.need_id, employer.id)
    shortlist.refinement = data.model_dump()
    await db.commit()
    return await _render_shortlist(db, shortlist, need, employer.id, data)


@router.post("/shortlists/{shortlist_id}/reset", response_model=ShortlistOut)
async def reset_refinement(
    shortlist_id: int,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await _employer(db, u.id)
    shortlist = await db.get(Shortlist, shortlist_id)
    if not shortlist:
        raise HTTPException(404, "Подборка не найдена")
    need = await _need_or_404(db, shortlist.need_id, employer.id)
    shortlist.refinement = {}
    await db.commit()
    return await _render_shortlist(db, shortlist, need, employer.id, RefinementIn())
