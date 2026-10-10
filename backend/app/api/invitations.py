"""Invitations: the employer reaches out, the candidate decides.

This is the contact scenario the whole product is built around, so the rules
are enforced here rather than in the UI:

* an invitation always carries a salary range and a contact method;
* the candidate sees the terms before any conversation starts;
* contacts are released only after the candidate accepts;
* both sides read the same status history.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.deps import require_role
from app.models.models import (
    CandidateProfile,
    EmployerNeed,
    EmployerProfile,
    Invitation,
    InvitationEvent,
    UserRole,
    User,
    Vacancy,
)
from app.schemas.engagement import (
    InvitationDecisionIn,
    InvitationEventOut,
    InvitationIn,
    InvitationOut,
)
from app.services import visibility
from app.services.cards import candidate_card

router = APIRouter(tags=["invitations"])


async def _history(db: AsyncSession, invitation_id: int) -> list[InvitationEventOut]:
    rows = (
        await db.scalars(
            select(InvitationEvent)
            .where(InvitationEvent.invitation_id == invitation_id)
            .order_by(InvitationEvent.id)
        )
    ).all()
    return [InvitationEventOut(status=row.status, created_at=row.created_at.isoformat()) for row in rows]


async def _invitation_out(
    db: AsyncSession, invitation: Invitation, for_role: UserRole, include_candidate: bool = False
) -> InvitationOut:
    employer = await db.get(EmployerProfile, invitation.employer_id)
    vacancy = await db.get(Vacancy, invitation.vacancy_id) if invitation.vacancy_id else None
    payload = InvitationOut(
        id=invitation.id,
        status=invitation.status,
        company_name=invitation.company_name,
        offer_description=invitation.offer_description,
        salary_from=invitation.salary_from,
        salary_to=invitation.salary_to,
        contact_method=invitation.contact_method,
        created_at=invitation.created_at.isoformat(),
        viewed_at=invitation.viewed_at.isoformat() if invitation.viewed_at else None,
        responded_at=invitation.responded_at.isoformat() if invitation.responded_at else None,
        vacancy_id=invitation.vacancy_id,
        vacancy_title=vacancy.title if vacancy else None,
        need_id=invitation.need_id,
        employer={
            "company_name": employer.company_name if employer else invitation.company_name,
            "description": employer.description if employer else "",
            "website": employer.website if employer else "",
            "industry": employer.industry if employer else "",
            "city": employer.city if employer else "",
            "team_size": employer.team_size if employer else "",
        },
        history=await _history(db, invitation.id),
    )
    if include_candidate:
        profile = await db.get(CandidateProfile, invitation.candidate_id)
        if profile:
            specialization = ""
            if invitation.need_id:
                need = await db.get(EmployerNeed, invitation.need_id)
                specialization = need.specialization_code if need else ""
            if not specialization and vacancy:
                specialization = vacancy.specialization_code
            payload.candidate = await candidate_card(db, profile, specialization, invitation.employer_id)
    return payload


@router.post("/invitations", response_model=InvitationOut, status_code=201)
async def send_invitation(
    data: InvitationIn,
    u=Depends(require_role(UserRole.employer)),
    db: AsyncSession = Depends(get_db),
):
    employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == u.id))
    if not employer:
        raise HTTPException(404, "Профиль работодателя не найден")
    if not employer.company_name.strip():
        raise HTTPException(400, "Заполните название компании перед отправкой приглашений")

    candidate = await db.get(CandidateProfile, data.candidate_id)
    if not candidate or not candidate.is_searchable:
        raise HTTPException(404, "Кандидат не найден или скрыл профиль")

    if data.vacancy_id:
        vacancy = await db.get(Vacancy, data.vacancy_id)
        if not vacancy or vacancy.employer_id != employer.id:
            raise HTTPException(400, "Вакансия не найдена")
    if data.need_id:
        need = await db.get(EmployerNeed, data.need_id)
        if not need or need.employer_id != employer.id:
            raise HTTPException(400, "Потребность не найдена")

    existing = await db.scalar(
        select(Invitation).where(
            Invitation.employer_id == employer.id,
            Invitation.candidate_id == candidate.id,
            Invitation.vacancy_id.is_(None) if data.vacancy_id is None else Invitation.vacancy_id == data.vacancy_id,
        )
    )
    if existing:
        raise HTTPException(409, "Приглашение этому кандидату уже отправлено")

    invitation = Invitation(
        employer_id=employer.id,
        candidate_id=candidate.id,
        vacancy_id=data.vacancy_id,
        need_id=data.need_id,
        company_name=employer.company_name,
        offer_description=data.offer_description,
        salary_from=data.salary_from,
        salary_to=data.salary_to,
        contact_method=data.contact_method,
        status="sent",
    )
    db.add(invitation)
    await db.flush()
    db.add(InvitationEvent(invitation_id=invitation.id, status="sent"))
    await db.commit()
    await db.refresh(invitation)
    return await _invitation_out(db, invitation, UserRole.employer, include_candidate=True)


@router.get("/employer/invitations", response_model=list[InvitationOut])
async def employer_invitations(
    u=Depends(require_role(UserRole.employer)), db: AsyncSession = Depends(get_db)
):
    employer = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == u.id))
    if not employer:
        return []
    rows = (
        await db.scalars(
            select(Invitation).where(Invitation.employer_id == employer.id).order_by(Invitation.id.desc())
        )
    ).all()
    out = [await _invitation_out(db, row, UserRole.employer, include_candidate=True) for row in rows]
    await db.commit()
    return out


@router.get("/me/invitations", response_model=list[InvitationOut])
async def my_invitations(u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)):
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
    if not profile:
        return []
    rows = (
        await db.scalars(
            select(Invitation).where(Invitation.candidate_id == profile.id).order_by(Invitation.id.desc())
        )
    ).all()
    now = datetime.now(timezone.utc)
    for invitation in rows:
        # Opening the inbox is what "просмотрено" means for the employer.
        if invitation.status == "sent" and not invitation.viewed_at:
            invitation.status = "viewed"
            invitation.viewed_at = now
            db.add(InvitationEvent(invitation_id=invitation.id, status="viewed"))
    await db.flush()
    out = [await _invitation_out(db, row, UserRole.candidate) for row in rows]
    await db.commit()
    return out


@router.post("/me/invitations/{invitation_id}/decision", response_model=InvitationOut)
async def decide_invitation(
    invitation_id: int,
    data: InvitationDecisionIn,
    u=Depends(require_role(UserRole.candidate)),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
    invitation = await db.get(Invitation, invitation_id)
    if not invitation or not profile or invitation.candidate_id != profile.id:
        raise HTTPException(404, "Приглашение не найдено")
    if invitation.status in ("accepted", "declined"):
        raise HTTPException(409, "Решение по этому приглашению уже принято")

    invitation.status = data.decision
    invitation.responded_at = datetime.now(timezone.utc)
    db.add(InvitationEvent(invitation_id=invitation.id, status=data.decision))
    profile.last_activity_at = datetime.now(timezone.utc)
    await db.flush()

    if data.decision == "accepted":
        # Accepting is exactly the moment contacts become available, so the
        # disclosure record is written here and not when the employer looks.
        await visibility.contacts_for(db, invitation.employer_id, profile)

    await db.commit()
    await db.refresh(invitation)
    return await _invitation_out(db, invitation, UserRole.candidate)


@router.get("/me/disclosures")
async def my_disclosures(u=Depends(require_role(UserRole.candidate)), db: AsyncSession = Depends(get_db)):
    """Who holds this candidate's contacts, and on what grounds."""
    from app.models.models import ContactDisclosure

    profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == u.id))
    if not profile:
        return []
    rows = (
        await db.scalars(
            select(ContactDisclosure)
            .where(ContactDisclosure.candidate_id == profile.id)
            .order_by(ContactDisclosure.id.desc())
        )
    ).all()
    out = []
    for row in rows:
        employer = await db.get(EmployerProfile, row.employer_id)
        out.append(
            {
                "employer": employer.company_name if employer else "",
                "reason": row.reason,
                "disclosed_at": row.disclosed_at.isoformat(),
            }
        )
    return out
