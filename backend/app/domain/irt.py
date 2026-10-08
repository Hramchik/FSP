"""Pure IRT 2PL and CAT helpers for Day 2."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable


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
        theta_new = theta + step
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
