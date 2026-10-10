"""Turn DB rows into the feature objects the matcher consumes.

Exists so that the shortlist endpoint, the candidate-bank search and the
offline validation script all score people the same way. Anything the ranker
must not see (contacts above all) simply never enters CandidateFeatures.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import fsp as fsp_domain
from app.domain.matching import CandidateFeatures
from app.models.models import (
    CandidateProfile,
    CandidateSpecialization,
    FspAchievement,
    FspLink,
    Specialization,
    SpotTaskAssignment,
    TestAttempt,
)

# Fields that make a profile useful to an employer; used for the activity score
# and for the "profile is N% complete" hint in the candidate's own cabinet.
COMPLETENESS_FIELDS = (
    "display_name", "city", "bio", "skills", "roles", "years_experience", "work_format",
)


def completeness(profile: CandidateProfile) -> float:
    filled = 0
    for name in COMPLETENESS_FIELDS:
        value = getattr(profile, name, None)
        if isinstance(value, (list, dict)):
            filled += 1 if value else 0
        elif isinstance(value, (int, float)):
            filled += 1 if value else 0
        else:
            filled += 1 if (value or "").strip() else 0
    return round(filled / len(COMPLETENESS_FIELDS), 3)


async def _fsp_index(db: AsyncSession, candidate_ids: list[int], now: datetime) -> dict[int, tuple[float, str | None]]:
    """One pass over links and achievements instead of a query per candidate."""
    if not candidate_ids:
        return {}
    links = (await db.execute(select(FspLink.candidate_id, FspLink.fsp_id).where(FspLink.candidate_id.in_(candidate_ids)))).all()
    if not links:
        return {}
    by_fsp: dict[str, list] = {}
    rows = (await db.scalars(select(FspAchievement).where(FspAchievement.fsp_id.in_([f for _, f in links])))).all()
    for row in rows:
        by_fsp.setdefault(row.fsp_id, []).append(
            fsp_domain.Achievement(row.event_name, row.event_level, row.place, row.participants_count, row.held_on)
        )
    out: dict[int, tuple[float, str | None]] = {}
    for candidate_id, fsp_id in links:
        items = by_fsp.get(fsp_id, [])
        out[candidate_id] = (fsp_domain.profile_strength(items, now), fsp_domain.reason(items, now))
    return out


async def features_for_specialization(
    db: AsyncSession, specialization_code: str, now: datetime | None = None
) -> tuple[list[CandidateFeatures], dict[int, CandidateProfile]]:
    """Every searchable candidate who holds a confirmed category here.

    A candidate enters the pool only with `is_searchable` and a grade confirmed
    by the test: the employer is choosing from categories, and a category that
    nobody earned must stay empty.
    """
    now = now or datetime.now(timezone.utc)
    specialization = await db.scalar(select(Specialization).where(Specialization.code == specialization_code))
    if not specialization:
        return [], {}

    rows = (
        await db.execute(
            select(CandidateProfile, CandidateSpecialization)
            .join(CandidateSpecialization, CandidateSpecialization.candidate_id == CandidateProfile.id)
            .where(
                CandidateSpecialization.specialization_id == specialization.id,
                CandidateSpecialization.confirmed_grade.is_not(None),
                CandidateProfile.is_searchable.is_(True),
            )
        )
    ).all()
    if not rows:
        return [], {}

    candidate_ids = [profile.id for profile, _ in rows]
    fsp_index = await _fsp_index(db, candidate_ids, now)

    # Latest finished attempt per candidate supplies SE and the confirmation date.
    attempts = (
        await db.scalars(
            select(TestAttempt)
            .where(
                TestAttempt.candidate_id.in_(candidate_ids),
                TestAttempt.specialization_id == specialization.id,
                TestAttempt.status == "finished",
            )
            .order_by(TestAttempt.finished_at)
        )
    ).all()
    attempt_index = {a.candidate_id: a for a in attempts}

    answered = (
        await db.execute(
            select(SpotTaskAssignment.candidate_id, SpotTaskAssignment.id)
            .where(
                SpotTaskAssignment.candidate_id.in_(candidate_ids),
                SpotTaskAssignment.status == "answered",
            )
        )
    ).all()
    spot_counts: dict[int, int] = {}
    for candidate_id, _ in answered:
        spot_counts[candidate_id] = spot_counts.get(candidate_id, 0) + 1

    features: list[CandidateFeatures] = []
    profiles: dict[int, CandidateProfile] = {}
    for profile, candidate_spec in rows:
        attempt = attempt_index.get(profile.id)
        strength, reason = fsp_index.get(profile.id, (0.0, None))
        if not profile.show_fsp:
            strength, reason = 0.0, None
        profiles[profile.id] = profile
        features.append(
            CandidateFeatures(
                candidate_id=profile.id,
                specialization=specialization_code,
                confirmed_grade=candidate_spec.confirmed_grade,
                theta=candidate_spec.theta,
                se=attempt.se if attempt else None,
                skills=tuple(profile.skills or []),
                fsp_strength=strength,
                fsp_reason=reason,
                city=profile.city if profile.show_city else "",
                work_format=profile.work_format or "",
                years_experience=profile.years_experience or 0.0,
                profile_completeness=completeness(profile),
                confirmed_at=attempt.finished_at if attempt else None,
                spot_tasks_answered=spot_counts.get(profile.id, 0),
                last_activity_at=profile.last_activity_at,
            )
        )
    return features, profiles
