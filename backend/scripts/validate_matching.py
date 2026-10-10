"""Offline evaluation of the matching mechanic.

Runs the real ranker (`app.domain.matching`) over the synthetic world and the
adjudicated labels produced by `generate_validation_data.py`, and reports the
metrics the team commits to:

* Precision@5 / @10 (strict, label = 2) and the same figure normalized by the
  achievable ceiling. A judged pool of ~25 people usually holds only one to
  three fully relevant candidates, so raw Precision@5 is bounded by supply
  rather than by ranking quality; the normalized form divides by
  `min(k, relevant_total)` and is the number the team actually commits to;
* Precision@5 (lenient, label >= 1) — the share of the top five a recruiter
  would keep in play;
* Success@5 — did the top five contain at least one fully relevant person;
* Recall@10 — how much of the relevant pool the top ten captures;
* nDCG@10 — ranking quality with graded relevance (0/1/2);
* MAP — averaged precision over the whole ranking;
* a hard check that nobody without a confirmed category ever surfaces;
* a hard check that every returned card carries an explanation.

Reproducible: the same seed in, the same numbers out.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from _paths import LABELS, SYNTHETIC  # noqa: E402

from app.domain import fsp as fsp_domain  # noqa: E402
from app.domain.matching import CandidateFeatures, Need, rank  # noqa: E402

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
RELEVANT = 2  # labels are 0/1/2; a "relevant" hit means the top grade


def load():
    people = json.load(open(SYNTHETIC / "candidates.json", encoding="utf8"))
    needs = json.load(open(SYNTHETIC / "vacancies.json", encoding="utf8"))
    labels: dict[int, dict[int, int]] = defaultdict(dict)
    with open(LABELS / "relevance_labels.csv", encoding="utf8") as handle:
        for row in csv.DictReader(handle):
            labels[int(row["vacancy_id"])][int(row["candidate_id"])] = int(row["adjudicated"])
    return people, needs, labels


def to_features(person: dict) -> CandidateFeatures:
    achievements = [
        fsp_domain.Achievement(
            event_name=a["event_name"],
            event_level=a["event_level"],
            place=a["place"],
            participants_count=a["participants_count"],
            held_on=NOW - timedelta(days=a["days_ago"]),
        )
        for a in person.get("achievements", [])
    ]
    return CandidateFeatures(
        candidate_id=person["id"],
        specialization=person["specialization"],
        confirmed_grade=person["confirmed_grade"],
        theta=person["theta"],
        se=person["se"],
        skills=tuple(person["skills"]),
        fsp_strength=fsp_domain.profile_strength(achievements, NOW),
        fsp_reason=fsp_domain.reason(achievements, NOW),
        city=person["city"],
        work_format=person["work_format"],
        years_experience=person["years_experience"],
        profile_completeness=person["profile_completeness"],
        confirmed_at=NOW - timedelta(days=person["confirmed_days_ago"]),
        spot_tasks_answered=person["spot_tasks_answered"],
    )


def dcg(gains: list[int]) -> float:
    return sum(gain / math.log2(position + 2) for position, gain in enumerate(gains))


def average_precision(labels_in_order: list[int]) -> float:
    hits, total = 0, 0.0
    relevant = sum(1 for value in labels_in_order if value >= RELEVANT)
    if not relevant:
        return 0.0
    for position, value in enumerate(labels_in_order, start=1):
        if value >= RELEVANT:
            hits += 1
            total += hits / position
    return total / relevant


def main() -> int:
    people, needs, labels = load()
    by_id = {person["id"]: person for person in people}
    features = [to_features(person) for person in people]

    precision5, precision10, recall10, ndcg10, maps = [], [], [], [], []
    precision5_norm, precision5_lenient, success5 = [], [], []
    relevant_counts = []
    evaluated = 0
    missing_reasons = 0
    unconfirmed_leaks = 0

    for need in needs:
        judged = labels.get(need["id"], {})
        if not judged:
            continue
        relevant_total = sum(1 for value in judged.values() if value >= RELEVANT)
        if not relevant_total:
            continue
        evaluated += 1

        domain_need = Need(
            specialization=need["specialization"],
            grade=need["grade"],
            skills=tuple(need["skills"]),
            city=need["city"],
            work_format=need["work_format"],
            require_fsp=need["require_fsp"],
        )
        # Only annotated candidates can be scored, so the ranking is restricted
        # to the judged pool — the standard pooled-evaluation convention.
        pool = [f for f in features if f.candidate_id in judged]
        results = rank(domain_need, pool, NOW)

        for result in results:
            if not result.reasons:
                missing_reasons += 1
            if not by_id[result.candidate_id]["confirmed_grade"]:
                unconfirmed_leaks += 1

        ordered = [judged.get(result.candidate_id, 0) for result in results]
        top5, top10 = ordered[:5], ordered[:10]

        hits5 = sum(1 for value in top5 if value >= RELEVANT)
        relevant_counts.append(relevant_total)
        precision5.append(hits5 / max(len(top5), 1))
        precision10.append(sum(1 for value in top10 if value >= RELEVANT) / max(len(top10), 1))
        # Ceiling-normalized: a need with two relevant people cannot score more
        # than 2/5, and penalizing the ranker for that would be meaningless.
        precision5_norm.append(hits5 / max(min(5, relevant_total), 1))
        precision5_lenient.append(sum(1 for value in top5 if value >= 1) / max(len(top5), 1))
        success5.append(1.0 if hits5 else 0.0)
        recall10.append(sum(1 for value in top10 if value >= RELEVANT) / relevant_total)
        ideal = sorted(judged.values(), reverse=True)[:10]
        ndcg10.append(dcg(top10) / dcg(ideal) if dcg(ideal) else 0.0)
        maps.append(average_precision(ordered))

    def mean(values):
        return sum(values) / len(values) if values else 0.0

    print("=" * 62)
    print("Валидация механики подбора")
    print("=" * 62)
    print(f"Потребностей в оценке      : {evaluated}")
    print(f"Кандидатов в банке         : {len(people)}")
    print(f"Размеченных пар            : {sum(len(v) for v in labels.values())}")
    print(f"Релевантных на потребность : {mean(relevant_counts):.1f} (медиана {sorted(relevant_counts)[len(relevant_counts)//2]})")
    print("-" * 62)
    print(f"Precision@5  (строгая, =2) : {mean(precision5):.3f}  — ограничена числом релевантных")
    print(f"Precision@5  с поправкой   : {mean(precision5_norm):.3f}  — делится на min(5, релевантных)")
    print(f"Precision@5  (мягкая, >=1) : {mean(precision5_lenient):.3f}")
    print(f"Success@5                  : {mean(success5):.3f}")
    print(f"Precision@10 (строгая)     : {mean(precision10):.3f}")
    print(f"Recall@10                  : {mean(recall10):.3f}")
    print(f"nDCG@10                    : {mean(ndcg10):.3f}")
    print(f"MAP                        : {mean(maps):.3f}")
    print("-" * 62)
    print(f"Карточек без объяснения    : {missing_reasons}")
    print(f"Без подтверждённой категории в выдаче: {unconfirmed_leaks}")

    targets = {
        "Precision@5 с поправкой ≥ 0.80": mean(precision5_norm) >= 0.80,
        "Precision@5 мягкая ≥ 0.70": mean(precision5_lenient) >= 0.70,
        "Success@5 ≥ 0.90": mean(success5) >= 0.90,
        "Recall@10 ≥ 0.90": mean(recall10) >= 0.90,
        "nDCG@10 ≥ 0.80": mean(ndcg10) >= 0.80,
        "MAP ≥ 0.60": mean(maps) >= 0.60,
        "объяснение у каждой карточки": missing_reasons == 0,
        "нет кандидатов без категории": unconfirmed_leaks == 0,
    }
    print("-" * 62)
    for name, passed in targets.items():
        print(f"  [{'OK ' if passed else 'FAIL'}] {name}")
    print("=" * 62)
    return 0 if all(targets.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
