"""Who may see what about a candidate.

Two rules from the specification live here and nowhere else:

* contact details are released to an employer only after the candidate accepted
  that employer's invitation or applied to one of their vacancies;
* every release is written to ``contact_disclosure``, so the candidate can be
  shown exactly who holds their contacts and why.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import (
    Application,
    CandidateProfile,
    ContactDisclosure,
    Invitation,
    User,
    Vacancy,
)

# Fields that are never part of a search result or a shortlist card.
CONTACT_FIELDS = ("email", "phone", "telegram", "github")


async def disclosure_reason(db: AsyncSession, employer_id: int, candidate_id: int) -> tuple[str | None, int | None]:
    """Return (reason, invitation_id) if this employer earned the contacts."""
    invitation = await db.scalar(
        select(Invitation)
        .where(
            Invitation.employer_id == employer_id,
            Invitation.candidate_id == candidate_id,
            Invitation.status == "accepted",
        )
        .order_by(Invitation.id)
        .limit(1)
    )
    if invitation:
        return "invitation_accepted", invitation.id

    application = await db.scalar(
        select(Application)
        .join(Vacancy, Application.vacancy_id == Vacancy.id)
        .where(Application.candidate_id == candidate_id, Vacancy.employer_id == employer_id)
        .order_by(Application.id)
        .limit(1)
    )
    if application:
        return "application_received", None
    return None, None


async def contacts_for(
    db: AsyncSession, employer_id: int, candidate: CandidateProfile
) -> dict | None:
    """Contacts if allowed, otherwise None. Records the disclosure once."""
    reason, invitation_id = await disclosure_reason(db, employer_id, candidate.id)
    if not reason:
        return None

    if invitation_id is not None:
        already = await db.scalar(
            select(ContactDisclosure).where(ContactDisclosure.invitation_id == invitation_id)
        )
        if not already:
            db.add(
                ContactDisclosure(
                    invitation_id=invitation_id,
                    candidate_id=candidate.id,
                    employer_id=employer_id,
                    reason=reason,
                )
            )

    user = await db.get(User, candidate.user_id)
    return {
        "email": user.email if user else "",
        "phone": candidate.phone,
        "telegram": candidate.telegram,
        "github": candidate.github,
        "reason": reason,
    }
