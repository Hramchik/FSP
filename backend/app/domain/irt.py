"""Pure IRT 2PL and CAT helpers for Day 2."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


# Границы шкалы, которые банк заданий реально измеряет: сложности b лежат
# примерно в [-1.6; 2.6]. За этими пределами ни одно задание не несёт
# информации, поэтому оценка вроде θ = +4.2 — артефакт, а не измерение.
THETA_MIN = -3.0
THETA_MAX = 3.5


@dataclass(frozen=True)
class IRTState:
    theta: float
    se: float


def probability(theta: float, a: float, b: float) -> float:
    z = max(-35.0, min(35.0, a * (theta - b)))
    return 1.0 / (1.0 + math.exp(-z))


def fisher_information(theta: float, a: float, b: float) -> float:
    p = probability(theta, a, b)
    return a * a * p * (1.0 - p)


def estimate_theta(
    responses: Iterable[tuple[int, float, float]],
    initial_theta: float = 0.0,
    max_iter: int = 30,
) -> IRTState:
    """MAP estimate with a weak N(0, 3^2) prior.

    responses: (correct 0/1, a, b)
    """
    items = list(responses)
    theta = float(initial_theta)
    if not items:
        return IRTState(theta=theta, se=1.0)

    prior_precision = 1.0 / 9.0
    info = prior_precision

    for _ in range(max_iter):
        score = -prior_precision * theta
        info = prior_precision
        for u, a, b in items:
            p = probability(theta, a, b)
            score += a * (float(u) - p)
            info += fisher_information(theta, a, b)

        step = score / max(info, 1e-9)
        step = max(-1.0, min(1.0, step))
        theta_new = max(THETA_MIN, min(THETA_MAX, theta + step))
        if abs(theta_new - theta) < 1e-4:
            theta = theta_new
            break
        theta = theta_new

    return IRTState(theta=theta, se=1.0 / math.sqrt(max(info, 1e-9)))


def grade_for_theta(theta: float) -> str:
    if theta < -0.5:
        return "junior"
    if theta < 0.7:
        return "middle"
    if theta < 1.8:
        return "senior"
    return "lead"


def fisher_rank(theta: float, items: Iterable[tuple[int, float, float]]) -> list[int]:
    scored = [(idx, fisher_information(theta, a, b)) for idx, a, b in items]
    return [idx for idx, _ in sorted(scored, key=lambda x: x[1], reverse=True)]


def target_grade_interval(grade: str) -> tuple[float | None, float | None]:
    return {
        "junior": (None, -0.5),
        "middle": (-0.5, 0.7),
        "senior": (0.7, 1.8),
        "lead": (1.8, None),
    }[grade]


# θ values that separate the four grades. Identical to `grade_for_theta`.
GRADE_BOUNDARIES: tuple[float, ...] = (-0.5, 0.7, 1.8)

MIN_ITEMS = 8
MAX_ITEMS = 15
EXTENDED_MAX_ITEMS = 20


def boundary_margin(theta: float) -> float:
    """Distance from θ to the nearest grade boundary."""
    return min(abs(theta - bound) for bound in GRADE_BOUNDARIES)


def grade_is_decided(theta: float, se: float, tolerance: float = 1.0) -> bool:
    """True when the measurement separates θ from the nearest boundary.

    A test that stops while θ sits within one standard error of a boundary
    produces a grade that flips on a retake. Since the decision the test makes
    is the *grade*, not θ itself, precision has to be judged against that
    boundary rather than against SE alone.
    """
    return boundary_margin(theta) > se * tolerance


def measurement_saturated(theta: float) -> bool:
    """θ прижат к краю измеримого диапазона — дальше спрашивать нечего."""
    return theta <= THETA_MIN + 1e-6 or theta >= THETA_MAX - 1e-6


def extreme_pattern(responses: Iterable[tuple[int, float, float]]) -> str | None:
    """Полностью верный или полностью неверный набор ответов.

    У таких наборов нет конечной оценки способности, а SE из информации
    Фишера для них не интерпретируется: информация вырождается, и SE растёт
    вместо того чтобы падать. Поэтому решение о грейде принимается по самому
    паттерну, а не по SE.
    """
    items = [u for u, _, _ in responses]
    if not items:
        return None
    if all(u == 1 for u in items):
        return "all_correct"
    if all(u == 0 for u in items):
        return "all_wrong"
    return None


def should_stop(
    answered_count: int,
    theta: float,
    se: float,
    min_items: int = MIN_ITEMS,
    max_items: int = MAX_ITEMS,
    hard_max: int = EXTENDED_MAX_ITEMS,
) -> bool:
    """The single CAT stop rule, shared by the API and the offline validation.

    * never before `min_items`;
    * standard stop: SE below 0.3 *and* the grade is unambiguous;
    * past `max_items` a looser margin is accepted, so a candidate sitting
      almost exactly on a boundary is not tested indefinitely;
    * `hard_max` always stops.
    """
    if answered_count < min_items:
        return False
    if answered_count >= hard_max:
        return True
    if se < 0.3 and grade_is_decided(theta, se):
        return True
    if answered_count >= max_items and se <= 0.45 and grade_is_decided(theta, se, tolerance=0.6):
        return True
    # θ упёрлось в край измеримого диапазона и дальше не сдвинется. Такие
    # попытки доводятся до стандартного предела — дополнительные задания ещё
    # уточняют SE, — но не до жёсткого: спрашивать больше нечего.
    if answered_count >= max_items and measurement_saturated(theta):
        return True
    return False
