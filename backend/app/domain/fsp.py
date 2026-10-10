"""Verified FSP competitive record → one comparable strength number.

Neither the FSP API nor the shape of its data is published for the hackathon,
so this module deliberately works on a minimal, self-chosen achievement record
(event, level, place, field size, date). Everything here is a pure function:
the API layer loads rows, this layer turns them into a score plus the Russian
sentences an employer sees next to a candidate.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

# How much a podium at this level is worth relative to an international final.
LEVEL_WEIGHT: dict[str, float] = {
    "international": 1.00,
    "national": 0.85,
    "federal": 0.85,
    "regional": 0.60,
    "student": 0.50,
    "open": 0.45,
    "city": 0.40,
}
LEVEL_RU: dict[str, str] = {
    "international": "международный",
    "national": "всероссийский",
    "federal": "всероссийский",
    "regional": "региональный",
    "student": "студенческий",
    "open": "открытый",
    "city": "городской",
}

# An achievement stops being evidence of current skill at some point. Half of
# the weight is gone after three years, which is also the horizon the grade
# cooldown is designed around.
HALF_LIFE_YEARS = 3.0


@dataclass(frozen=True)
class Achievement:
    event_name: str
    event_level: str
    place: int
    participants_count: int
    held_on: datetime


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def achievement_weight(item: Achievement, now: datetime | None = None) -> float:
    """Weight of a single result: level × placement × recency.

    Placement uses 1/log2(place+1) so that the gap between 1st and 2nd matters
    far more than the gap between 40th and 41st, and is scaled by how large the
    field was — winning among 500 people is not the same as winning among 6.
    """
    now = _aware(now or datetime.now(timezone.utc))
    level = LEVEL_WEIGHT.get(item.event_level.lower(), 0.45)
    place = max(1, item.place)
    placement = 1.0 / math.log2(place + 1.0)
    field = min(1.0, math.log10(max(item.participants_count, 2)) / 2.7)  # 500+ participants ≈ 1.0
    years = max(0.0, (now - _aware(item.held_on)).days / 365.25)
    recency = 0.5 ** (years / HALF_LIFE_YEARS)
    return level * placement * (0.45 + 0.55 * field) * recency


def profile_strength(achievements, now: datetime | None = None) -> float:
    """Saturating 0..100 score over the whole record.

    Saturation matters: a long tail of minor results must never outrank one
    strong national podium, and the score must stay bounded so that the FSP
    component cannot dominate the overall match score.
    """
    total = sum(achievement_weight(a, now) for a in achievements)
    if total <= 0:
        return 0.0
    return round(100.0 * (1.0 - math.exp(-1.15 * total)), 2)


def summary(achievements, now: datetime | None = None) -> dict:
    """Compact, employer-facing summary of the verified record."""
    items = list(achievements)
    if not items:
        return {"count": 0, "strength": 0.0, "podium_count": 0, "best_level": None, "highlights": []}
    ranked = sorted(items, key=lambda a: achievement_weight(a, now), reverse=True)
    podium = [a for a in items if a.place <= 3]
    best = max(items, key=lambda a: LEVEL_WEIGHT.get(a.event_level.lower(), 0.45))
    return {
        "count": len(items),
        "strength": profile_strength(items, now),
        "podium_count": len(podium),
        "best_level": LEVEL_RU.get(best.event_level.lower(), best.event_level),
        "highlights": [
            f"{a.event_name} — {a.place} место из {a.participants_count} "
            f"({LEVEL_RU.get(a.event_level.lower(), a.event_level)} уровень, {_aware(a.held_on).year})"
            for a in ranked[:3]
        ],
    }


def plural(n: int, one: str, few: str, many: str) -> str:
    """Russian numeral agreement, so shortlist cards read like normal text."""
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n %= 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def reason(achievements, now: datetime | None = None) -> str | None:
    """One line for the explainability block of a shortlist card."""
    items = list(achievements)
    if not items:
        return None
    data = summary(items, now)
    podium, total = data["podium_count"], data["count"]
    results = plural(total, "зачтённого результата", "зачтённых результатов", "зачтённых результатов")
    if podium:
        places = plural(podium, "призовое место", "призовых места", "призовых мест")
        return f"ФСП: {podium} {places} из {total} {results}, лучший уровень — {data['best_level']}"
    return f"ФСП: {total} {results}, лучший уровень — {data['best_level']}"
