"""Adapter seam for the FSP participant registry.

The real registry is not available during the hackathon and its data shapes are
deliberately not published, so this module is the single place that would be
replaced by a real HTTP client. Everything above it — scoring, ranking, the UI —
depends only on the achievement rows stored locally, which is what keeps the
integration a one-file change later.

The local implementation is a mock: an FSP ID is accepted when it matches the
agreed format, and whatever achievements were preloaded for that ID are used.
A candidate with no FSP history is a first-class case, not an error.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.fsp import Achievement, summary
from app.models.models import FspAchievement, FspLink

# FSP-xxxxxx, the format used by the seeded demo registry.
FSP_ID_RE = re.compile(r"^FSP-\d{6}$")


class FspRegistryError(ValueError):
    pass


def validate_id(fsp_id: str) -> str:
    value = (fsp_id or "").strip().upper()
    if not FSP_ID_RE.match(value):
        raise FspRegistryError("ФСП ID должен иметь формат FSP-000000")
    return value


async def achievements_for(db: AsyncSession, fsp_id: str) -> list[Achievement]:
    rows = (
        await db.scalars(
            select(FspAchievement).where(FspAchievement.fsp_id == fsp_id).order_by(FspAchievement.held_on.desc())
        )
    ).all()
    return [
        Achievement(
            event_name=row.event_name,
            event_level=row.event_level,
            place=row.place,
            participants_count=row.participants_count,
            held_on=row.held_on,
        )
        for row in rows
    ]


async def profile_for_candidate(db: AsyncSession, candidate_id: int) -> dict:
    """Achievement summary for one candidate, empty-but-valid when unlinked."""
    link = await db.scalar(select(FspLink).where(FspLink.candidate_id == candidate_id))
    if not link:
        return {"linked": False, "fsp_id": None, **summary([])}
    items = await achievements_for(db, link.fsp_id)
    return {
        "linked": True,
        "fsp_id": link.fsp_id,
        "linked_at": link.linked_at.isoformat() if link.linked_at else None,
        "verified_by": link.verified_by,
        **summary(items, datetime.now(timezone.utc)),
        "achievements": [
            {
                "event_name": a.event_name,
                "event_level": a.event_level,
                "place": a.place,
                "participants_count": a.participants_count,
                "held_on": a.held_on.isoformat(),
            }
            for a in items
        ],
    }
