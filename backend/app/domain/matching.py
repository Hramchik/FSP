"""Reverse-hiring match: an employer need → a ranked, explained shortlist.

The platform never matches a need against a self-written résumé. Matching runs
in two stages:

1. **Routing.** The need is resolved to *categories* — (specialization, grade)
   pairs. The requested grade is the primary category; the neighbouring grades
   are secondary with a fixed discount. This is what makes the mechanic the
   reverse of a job board: the employer picks a category, not a person, and the
   people inside it were put there by a test, not by their own description.

2. **Ranking inside the categories.** Everyone in the routed categories is
   scored on five components that add up to 100. Every component produces a
   Russian sentence with its own contribution, so a card can always answer
   "почему этот кандидат здесь".

Everything in this module is a pure function over plain dataclasses: no DB
session, no request, no ORM. That keeps the mechanic testable offline, which is
exactly what `scripts/validate_matching.py` relies on.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.domain import skills as skills_vocab
from app.domain.fsp import plural

GRADE_ORDER = ["junior", "middle", "senior", "lead"]
GRADE_RU = {"junior": "Junior", "middle": "Middle", "senior": "Senior", "lead": "Lead"}

# θ band of each grade, identical to the testing module's thresholds.
GRADE_BANDS: dict[str, tuple[float, float]] = {
    "junior": (-3.0, -0.5),
    "middle": (-0.5, 0.7),
    "senior": (0.7, 1.8),
    "lead": (1.8, 3.5),
}

# Component ceilings. They sum to 100 and are the only place weights live.
WEIGHTS: dict[str, float] = {
    "category": 35.0,
    "skills": 25.0,
    "proof": 20.0,
    "fsp": 12.0,
    "activity": 8.0,
}
WEIGHTS_VERSION = "match-v1"

# Candidate grade offset relative to the requested grade → share of the
# category weight. A grade below the request is a bigger compromise than a
# grade above it, but an overqualified candidate is discounted too: they are
# usually out of the stated salary band.
GRADE_OFFSET_FIT: dict[int, float] = {0: 1.00, 1: 0.55, -1: 0.45}


@dataclass(frozen=True)
class Need:
    """A structured employer requirement, already normalized by the API layer."""
    specialization: str
    grade: str
    skills: tuple[str, ...] = ()
    city: str = ""
    work_format: str = ""
    require_fsp: bool = False


@dataclass(frozen=True)
class CandidateFeatures:
    """Everything the ranker is allowed to see about one candidate.

    Contact details are deliberately absent: the ranker cannot leak what it
    never receives.
    """
    candidate_id: int
    specialization: str
    confirmed_grade: str | None
    theta: float | None
    se: float | None
    skills: tuple[str, ...] = ()
    fsp_strength: float = 0.0
    fsp_reason: str | None = None
    city: str = ""
    work_format: str = ""
    years_experience: float = 0.0
    profile_completeness: float = 0.0  # 0..1
    confirmed_at: datetime | None = None
    spot_tasks_answered: int = 0
    last_activity_at: datetime | None = None


@dataclass
class Reason:
    code: str
    text: str
    contribution: float


@dataclass
class MatchResult:
    candidate_id: int
    score: float
    rank: int = 0
    category: str = ""
    grade_offset: int = 0
    components: dict[str, float] = field(default_factory=dict)
    reasons: list[Reason] = field(default_factory=list)
    matched_skills: list[str] = field(default_factory=list)
    missing_skills: list[str] = field(default_factory=list)


def _grade_index(grade: str | None) -> int | None:
    if grade in GRADE_ORDER:
        return GRADE_ORDER.index(grade)
    return None


def route_categories(need: Need) -> list[tuple[str, str, float, int]]:
    """Stage 1: need → (specialization, grade, weight, offset), best first.

    The returned weights are the shares of `WEIGHTS["category"]` used in stage
    2, and they double as the explanation the employer sees above the list.
    """
    index = _grade_index(need.grade)
    if index is None:
        return []
    routed: list[tuple[str, str, float, int]] = []
    for offset, share in sorted(GRADE_OFFSET_FIT.items(), key=lambda kv: -kv[1]):
        position = index + offset
        if 0 <= position < len(GRADE_ORDER):
            routed.append((need.specialization, GRADE_ORDER[position], share, offset))
    return routed


def routing_explanation(need: Need) -> list[str]:
    out = []
    for spec, grade, share, offset in route_categories(need):
        kind = "основная" if offset == 0 else ("смежная, грейд выше" if offset > 0 else "смежная, грейд ниже")
        out.append(f"{spec} / {GRADE_RU[grade]} — {kind}, вес {share:.2f}")
    return out


def _skill_component(need: Need, candidate: CandidateFeatures) -> tuple[float, list[str], list[str], str]:
    """Coverage of the required stack, plus a small bonus for adjacent depth."""
    required = list(dict.fromkeys(need.skills))
    owned = set(candidate.skills)
    if not required:
        # Nothing was asked for: judge by depth inside the specialization core
        # instead of handing everyone a free full score.
        core = skills_vocab.CORE_SKILLS.get(need.specialization, set())
        depth = len(owned & core)
        share = min(1.0, depth / 4.0)
        text = (
            f"Требования по стеку не заданы; в профиле {depth} "
            f"{plural(depth, 'ключевой навык', 'ключевых навыка', 'ключевых навыков')} специализации"
        )
        return WEIGHTS["skills"] * share, sorted(owned & core), [], text

    matched = [s for s in required if s in owned]
    missing = [s for s in required if s not in owned]
    coverage = len(matched) / len(required)

    # Extra skills from the same specialization core signal depth, but can add
    # at most 15% on top so that coverage of the actual request stays dominant.
    core = skills_vocab.CORE_SKILLS.get(need.specialization, set())
    extra = len((owned & core) - set(required))
    bonus = min(0.15, extra * 0.05)
    share = min(1.0, coverage + bonus * coverage)

    labels = ", ".join(skills_vocab.labels(matched)) if matched else "—"
    text = f"Стек: {len(matched)} из {len(required)} требований ({labels})"
    if missing:
        text += f"; не подтверждено: {', '.join(skills_vocab.labels(missing))}"
    return WEIGHTS["skills"] * share, matched, missing, text


def _proof_component(candidate: CandidateFeatures, target_grade: str) -> tuple[float, str]:
    """How strongly the test confirms the candidate's position in the band.

    Two independent things are rewarded: where θ sits inside the band of the
    grade the employer asked for, and how certain that θ is (low SE). A high θ
    measured with SE 0.6 is not evidence, and the formula says so.
    """
    if candidate.theta is None or candidate.confirmed_grade is None:
        return 0.0, "Грейд не подтверждён тестированием"

    low, high = GRADE_BANDS[target_grade]
    position = (candidate.theta - low) / max(high - low, 1e-6)
    position = max(0.0, min(1.0, position))

    se = candidate.se if candidate.se is not None else 0.6
    # SE ≤ 0.25 is a fully trusted measurement, SE ≥ 0.60 carries no weight.
    confidence = max(0.0, min(1.0, (0.60 - se) / 0.35))

    share = (0.40 + 0.60 * position) * (0.55 + 0.45 * confidence)
    text = (
        f"θ {candidate.theta:+.2f} (SE {se:.2f}) — "
        f"{'верхняя' if position >= 0.66 else 'средняя' if position >= 0.33 else 'нижняя'} часть "
        f"запрошенного диапазона {GRADE_RU[target_grade]}"
    )
    return WEIGHTS["proof"] * share, text


def _fsp_component(candidate: CandidateFeatures) -> tuple[float, str | None]:
    share = max(0.0, min(1.0, candidate.fsp_strength / 100.0))
    if share <= 0:
        return 0.0, None
    return WEIGHTS["fsp"] * share, candidate.fsp_reason or "Есть подтверждённые достижения ФСП"


def _activity_component(candidate: CandidateFeatures, now: datetime) -> tuple[float, str]:
    """Freshness of the profile: a stale confirmation is weaker evidence."""
    parts: list[float] = []
    notes: list[str] = []

    parts.append(max(0.0, min(1.0, candidate.profile_completeness)))
    if candidate.profile_completeness >= 0.8:
        notes.append("профиль заполнен")

    if candidate.confirmed_at:
        at = candidate.confirmed_at if candidate.confirmed_at.tzinfo else candidate.confirmed_at.replace(tzinfo=timezone.utc)
        days = max(0.0, (now - at).days)
        freshness = 0.5 ** (days / 180.0)  # half-life of six months
        parts.append(freshness)
        notes.append(f"тест пройден {int(days)} {plural(int(days), 'день', 'дня', 'дней')} назад")
    else:
        parts.append(0.0)

    answered = candidate.spot_tasks_answered
    parts.append(min(1.0, answered / 3.0))
    if answered:
        notes.append(f"{answered} {plural(answered, 'решённое регулярное задание', 'решённых регулярных задания', 'решённых регулярных заданий')}")

    share = sum(parts) / len(parts)
    return WEIGHTS["activity"] * share, "Активность: " + (", ".join(notes) if notes else "профиль малоактивен")


def score_candidate(need: Need, candidate: CandidateFeatures, now: datetime | None = None) -> MatchResult | None:
    """Stage 2. Returns None when the candidate is outside the routed categories."""
    now = now or datetime.now(timezone.utc)
    if candidate.specialization != need.specialization:
        return None
    if need.require_fsp and candidate.fsp_strength <= 0:
        return None

    need_index = _grade_index(need.grade)
    candidate_index = _grade_index(candidate.confirmed_grade)
    if need_index is None or candidate_index is None:
        return None
    offset = candidate_index - need_index
    if offset not in GRADE_OFFSET_FIT:
        return None

    reasons: list[Reason] = []
    components: dict[str, float] = {}

    category_score = WEIGHTS["category"] * GRADE_OFFSET_FIT[offset]
    components["category"] = round(category_score, 2)
    category_text = {
        0: f"Категория {need.specialization} / {GRADE_RU[candidate.confirmed_grade]} точно совпадает с запросом",
        1: f"Категория {need.specialization} / {GRADE_RU[candidate.confirmed_grade]} — на грейд выше запроса",
        -1: f"Категория {need.specialization} / {GRADE_RU[candidate.confirmed_grade]} — на грейд ниже запроса",
    }[offset]
    reasons.append(Reason("category", category_text, round(category_score, 2)))

    skill_score, matched, missing, skill_text = _skill_component(need, candidate)
    components["skills"] = round(skill_score, 2)
    reasons.append(Reason("skills", skill_text, round(skill_score, 2)))

    proof_score, proof_text = _proof_component(candidate, need.grade)
    components["proof"] = round(proof_score, 2)
    reasons.append(Reason("proof", proof_text, round(proof_score, 2)))

    fsp_score, fsp_text = _fsp_component(candidate)
    components["fsp"] = round(fsp_score, 2)
    if fsp_text:
        reasons.append(Reason("fsp", fsp_text, round(fsp_score, 2)))

    activity_score, activity_text = _activity_component(candidate, now)
    components["activity"] = round(activity_score, 2)
    reasons.append(Reason("activity", activity_text, round(activity_score, 2)))

    total = sum(components.values())

    # Soft preferences never gate the list, they only reorder it: a hard city
    # filter would silently hide strong people the employer would have taken.
    if need.city and candidate.city and need.city.strip().lower() == candidate.city.strip().lower():
        total += 2.0
        reasons.append(Reason("city", f"Город совпадает: {candidate.city}", 2.0))
    if need.work_format and candidate.work_format and need.work_format == candidate.work_format:
        total += 2.0
        reasons.append(Reason("work_format", f"Формат работы совпадает: {candidate.work_format}", 2.0))

    return MatchResult(
        candidate_id=candidate.candidate_id,
        score=round(min(100.0, total), 2),
        category=f"{need.specialization} / {candidate.confirmed_grade}",
        grade_offset=offset,
        components=components,
        reasons=reasons,
        matched_skills=matched,
        missing_skills=missing,
    )


def rank(need: Need, candidates, now: datetime | None = None, limit: int | None = None) -> list[MatchResult]:
    """Full pipeline: route, score, order, number."""
    now = now or datetime.now(timezone.utc)
    scored = [r for r in (score_candidate(need, c, now) for c in candidates) if r is not None]
    # Ties break on proof then on FSP, so the stronger confirmed profile wins —
    # exactly the in-category ordering the specification asks for.
    scored.sort(
        key=lambda r: (r.score, r.components.get("proof", 0.0), r.components.get("fsp", 0.0)),
        reverse=True,
    )
    for position, result in enumerate(scored, start=1):
        result.rank = position
    return scored[:limit] if limit else scored
