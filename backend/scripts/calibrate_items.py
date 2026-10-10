"""Offline calibration of IRT item parameters on synthetic candidates.

This is deliberately independent from FastAPI/SQLAlchemy. It uses the same
2PL likelihood as production and writes reproducible calibration metrics.
"""
from __future__ import annotations

import json
import math
import random
import hashlib
import sys
from pathlib import Path

from app.domain.irt import probability

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import VALIDATION as OUT  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)

GRADE_B = {"junior": -1.2, "middle": 0.1, "senior": 1.15, "lead": 2.25}


def fit_ab(thetas, responses, init_a=1.0, init_b=0.0):
    # Small deterministic coordinate grid around the generating anchor. This
    # is intentionally transparent and robust enough for demo calibration.
    best = (float("-inf"), init_a, init_b)
    for a in [round(0.4 + i * 0.1, 2) for i in range(17)]:
        for b in [round(-2.8 + i * 0.2, 2) for i in range(29)]:
            ll = 0.0
            for theta, u in zip(thetas, responses):
                p = min(max(probability(theta, a, b), 1e-8), 1 - 1e-8)
                ll += u * math.log(p) + (1 - u) * math.log(1 - p)
            if ll > best[0]:
                best = (ll, a, b)
    return best[1], best[2], best[0]


def main():
    rng = random.Random(20261007)
    thetas = [max(-3.5, min(3.5, rng.gauss(0, 1.25))) for _ in range(200)]
    rows = []
    for specialization in ["backend", "frontend", "mobile", "data", "devops", "qa"]:
        for grade, anchor_b in GRADE_B.items():
            for variant in range(5):
                true_a = round(2.0 + 0.12 * variant, 2)
                true_b = round(anchor_b + (variant - 2) * 0.06, 2)
                stable = int.from_bytes(hashlib.sha256(f'{specialization}:{grade}:{variant}'.encode()).digest()[:4], 'big')
                local = random.Random(20261007 + stable % 100000)
                responses = [
                    int(local.random() < probability(theta, true_a, true_b))
                    for theta in thetas
                ]
                a_hat, b_hat, ll = fit_ab(thetas, responses, true_a, true_b)
                rows.append({
                    "specialization": specialization,
                    "grade": grade,
                    "variant": variant,
                    "true_a": true_a,
                    "true_b": true_b,
                    "a_hat": a_hat,
                    "b_hat": b_hat,
                    "log_likelihood": round(ll, 3),
                })
    report = {
        "seed": 20261007,
        "n_candidates": len(thetas),
        "n_calibrated_templates": len(rows),
        "rows": rows,
    }
    (OUT / "item_calibration.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"calibrated {len(rows)} template families -> {OUT / 'item_calibration.json'}")


if __name__ == "__main__":
    main()
