"""The employer-facing view of a candidate.

A single builder is used by the shortlist, the candidate bank and the
invitation screens, so a field can never be visible in one place and hidden in
another. Contacts come from `app.services.visibility` and nowhere else.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import skills as skills_vocab
from app.models.models import (
    CandidateProfile,
    CandidateSpecialization,
    Invitation,
    Specialization,
)
from app.services import fsp_registry, visibility

GRADE_RU = {"junior": "Junior", "middle": "Middle", "senior": "Senior", "lead": "Lead"}


def salary_expectation_text(profile: CandidateProfile) -> str | None:
    if not profile.show_salary_expectation:
        return None
    low, high = profile.salary_expectation_from, profile.salary_expectation_to
    if low and high:
        return f"{low:,} — {high:,} ₽".replace(",", " ")
    if low:
        return f"от {low:,} ₽".replace(",", " ")
    if high:
        return f"до {high:,} ₽".replace(",", " ")
    return None


async def candidate_card(
    db: AsyncSession,
    profile: CandidateProfile,
    specialization_code: str,
    employer_id: int | None = None,
    include_contacts: bool = True,
) -> dict:
    specialization = await db.scalar(select(Specialization).where(Specialization.code == specialization_code))
    candidate_spec = None
    if specialization:
        candidate_spec = await db.scalar(
            select(CandidateSpecialization).where(
                CandidateSpecialization.candidate_id == profile.id,
                CandidateSpecialization.specialization_id == specialization.id,
            )
        )

    grade = candidate_spec.confirmed_grade if candidate_spec else None
    card = {
        "candidate_id": profile.id,
        "display_name": profile.display_name or f"Кандидат #{profile.id}",
        "specialization": specialization_code,
        "grade": grade or "",
        "category": (
            f"{specialization.name} · {GRADE_RU.get(grade, grade)}"
            if specialization and grade
            else "Категория не подтверждена"
        ),
        "theta": round(candidate_spec.theta, 2) if candidate_spec and candidate_spec.theta is not None else None,
        "city": profile.city if profile.show_city else "",
        "work_format": profile.work_format or "",
        "years_experience": profile.years_experience or 0.0,
        "skills": list(profile.skills or []),
        "skill_labels": skills_vocab.labels(profile.skills or []),
        "roles": list(profile.roles or []),
        "soft_skills": list(profile.soft_skills or []),
        "bio": profile.bio or "",
        "salary_expectation": salary_expectation_text(profile),
        "fsp": {},
        "contacts": None,
        "contacts_locked_reason": None,
        "invitation_status": None,
    }

    if profile.show_fsp:
        fsp = await fsp_registry.profile_for_candidate(db, profile.id)
        card["fsp"] = {
            "linked": fsp["linked"],
            "count": fsp["count"],
            "strength": fsp["strength"],
            "podium_count": fsp["podium_count"],
            "best_level": fsp["best_level"],
            "highlights": fsp["highlights"],
        }
    else:
        card["fsp"] = {"linked": False, "count": 0, "strength": 0.0, "podium_count": 0,
                       "best_level": None, "highlights": [], "hidden_by_candidate": True}

    if employer_id is not None:
        last = await db.scalar(
            select(Invitation)
            .where(Invitation.employer_id == employer_id, Invitation.candidate_id == profile.id)
            .order_by(Invitation.id.desc())
            .limit(1)
        )
        card["invitation_status"] = last.status if last else None
        if include_contacts:
            contacts = await visibility.contacts_for(db, employer_id, profile)
            card["contacts"] = contacts
            if not contacts:
                card["contacts_locked_reason"] = (
                    "Контакты откроются после того, как кандидат примет приглашение "
                    "или откликнется на вашу вакансию"
                )
    return card
