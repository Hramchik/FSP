"""Reproducible synthetic world for offline evaluation.

No real dataset of candidates, vacancies or relevance labels is provided for
the hackathon, so the team generates its own and states the rules out loud.

Three artefacts are produced:

* `data/synthetic/candidates.json` — 200 people with a true θ, a confirmed
  grade derived from it, a stack, an FSP record and profile metadata;
* `data/synthetic/vacancies.json` — 30 employer needs;
* `data/labels/relevance_labels.csv` — two independent annotations per pair
  plus an adjudicated label.

The annotation rubric is deliberately *not* the ranking formula: it uses only
specialization, grade distance and stack coverage, and knows nothing about
θ position inside a band, FSP strength, profile freshness or the
overqualification discount. Scoring the ranker against labels built from its
own weights would prove nothing.
"""
import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _paths import LABELS as LAB, SYNTHETIC as OUT  # noqa: E402

OUT.mkdir(parents=True, exist_ok=True)
LAB.mkdir(parents=True, exist_ok=True)

SEED = 20261010
rng = random.Random(SEED)

SPECS = ["backend", "frontend", "mobile", "data", "devops", "qa"]
GRADES = ["junior", "middle", "senior", "lead"]
CITIES = ["Москва", "Санкт-Петербург", "Казань", "Екатеринбург", "Новосибирск", "Воронеж"]
FORMATS = ["remote", "hybrid", "office"]

CORE = {
    "backend": ["python", "go", "java", "postgresql", "sql", "api-design", "kafka", "redis",
                "docker", "microservices", "highload", "fastapi", "django", "spring"],
    "frontend": ["typescript", "javascript", "react", "vue", "nextjs", "nodejs", "ci-cd"],
    "mobile": ["kotlin", "swift", "java", "flutter", "android", "ios", "sql"],
    "data": ["python", "sql", "statistics", "pytorch", "pandas", "spark", "airflow", "mlops", "clickhouse"],
    "devops": ["docker", "kubernetes", "linux", "terraform", "ansible", "ci-cd", "prometheus", "grafana", "nginx"],
    "qa": ["pytest", "selenium", "playwright", "postman", "test-design", "autotests", "jmeter", "sql", "python"],
}

EVENTS = [
    ("Международный кубок ФСП", "international", 1200),
    ("Всероссийский чемпионат по спортивному программированию", "national", 640),
    ("Региональный чемпионат ФСП", "regional", 180),
    ("Студенческий кубок ФСП", "student", 320),
    ("Открытый хакатон ФСП", "open", 90),
]

# Same thresholds the testing module assigns grades with.
BANDS = [("junior", -9.0, -0.5), ("middle", -0.5, 0.7), ("senior", 0.7, 1.8), ("lead", 1.8, 9.0)]


def grade_for(theta: float) -> str:
    for name, low, high in BANDS:
        if low <= theta < high:
            return name
    return "lead"


def make_candidates(count: int = 200) -> list[dict]:
    people = []
    for index in range(count):
        # Distribution kept identical to the Day 2 generator so that the
        # test-retest numbers stay comparable across regenerations.
        theta = max(-2.5, min(3.0, rng.gauss(0, 1.25)))
        spec = rng.choice(SPECS)
        pool = CORE[spec]
        stack = rng.sample(pool, k=rng.randint(2, min(7, len(pool))))
        # A quarter of the population carries skills from a neighbouring area,
        # which is what makes stack coverage a non-trivial signal.
        if rng.random() < 0.25:
            other = rng.choice([s for s in SPECS if s != spec])
            stack.append(rng.choice(CORE[other]))
        grade = grade_for(theta)
        has_fsp = index < 110
        achievements = []
        if has_fsp:
            strong = grade in ("senior", "lead") and rng.random() < 0.6
            for _ in range(rng.randint(1, 4) if strong else rng.randint(1, 2)):
                name, level, field = rng.choice(EVENTS)
                achievements.append(
                    {
                        "event_name": name,
                        "event_level": level,
                        "place": rng.randint(1, 3) if strong else rng.randint(4, 60),
                        "participants_count": field,
                        "days_ago": rng.randint(30, 1700),
                    }
                )
        people.append(
            {
                "id": index + 1,
                "pseudo": f"A-{1000 + index:04d}",
                "theta": round(theta, 4),
                # SE reflects how precisely the adaptive test measured this person.
                "se": round(rng.uniform(0.19, 0.44), 3),
                "specialization": spec,
                "confirmed_grade": grade,
                "skills": sorted(set(stack)),
                "fsp": has_fsp,
                "achievements": achievements,
                "city": rng.choice(CITIES),
                "work_format": rng.choice(FORMATS),
                "years_experience": max(0.0, round(theta + 2.4 + rng.random() * 2, 1)),
                "profile_completeness": round(rng.uniform(0.45, 1.0), 2),
                "confirmed_days_ago": rng.randint(2, 420),
                "spot_tasks_answered": rng.choice([0, 0, 0, 1, 2, 3]),
            }
        )
    return people


def make_needs(count: int = 30) -> list[dict]:
    needs = []
    for index in range(count):
        spec = SPECS[index % len(SPECS)]
        grade = rng.choice(GRADES)
        required = rng.sample(CORE[spec], k=rng.randint(2, 4))
        needs.append(
            {
                "id": index + 1,
                "title": f"{spec} {grade} #{index + 1}",
                "specialization": spec,
                "grade": grade,
                "skills": required,
                "city": rng.choice(CITIES) if rng.random() < 0.5 else "",
                "work_format": rng.choice(FORMATS) if rng.random() < 0.5 else "",
                "require_fsp": rng.random() < 0.15,
                "description": (
                    f"Нужен специалист ({spec}), уровень {grade}. "
                    f"Стек: {', '.join(required)}."
                ),
            }
        )
    return needs


GRADE_INDEX = {name: position for position, name in enumerate(GRADES)}


def rubric_label(need: dict, person: dict) -> int:
    """The written instruction both annotators follow.

    0 — не подходит; 1 — можно рассмотреть; 2 — релевантен.
    Only specialization, grade distance and stack coverage are considered.
    """
    if person["specialization"] != need["specialization"]:
        return 0
    distance = GRADE_INDEX[person["confirmed_grade"]] - GRADE_INDEX[need["grade"]]
    if abs(distance) > 1:
        return 0
    coverage = len(set(need["skills"]) & set(person["skills"])) / len(need["skills"])
    if need["require_fsp"] and not person["fsp"]:
        return 0
    if distance == 0 and coverage >= 2 / 3:
        return 2
    if coverage >= 2 / 3 or (distance == 0 and coverage >= 1 / 3):
        return 1
    if coverage < 1 / 3:
        return 0
    return 1


def annotate(truth: int) -> int:
    """One annotator: the rubric plus realistic disagreement."""
    if rng.random() < 0.2:
        truth += rng.choice([-1, 1])
    return max(0, min(2, truth))


def main():
    people = make_candidates()
    needs = make_needs()
    json.dump(people, open(OUT / "candidates.json", "w", encoding="utf8"), ensure_ascii=False, indent=2)
    json.dump(needs, open(OUT / "vacancies.json", "w", encoding="utf8"), ensure_ascii=False, indent=2)

    rows = 0
    agreements = 0
    with open(LAB / "relevance_labels.csv", "w", newline="", encoding="utf8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["vacancy_id", "candidate_id", "annotator_a", "annotator_b", "adjudicated"])
        for need in needs:
            # Annotate the same-specialization pool plus a control sample from
            # other specializations, so precision is not measured on a set that
            # was already filtered to the right answer.
            same = [p for p in people if p["specialization"] == need["specialization"]]
            other = [p for p in people if p["specialization"] != need["specialization"]]
            pool = rng.sample(same, k=min(20, len(same))) + rng.sample(other, k=min(5, len(other)))
            for person in pool:
                truth = rubric_label(need, person)
                a, b = annotate(truth), annotate(truth)
                adjudicated = truth if a != b else a
                agreements += int(a == b)
                writer.writerow([need["id"], person["id"], a, b, adjudicated])
                rows += 1

    print(f"seed={SEED}")
    print(f"candidates={len(people)} needs={len(needs)} labelled_pairs={rows}")
    print(f"annotator raw agreement={agreements / rows:.3f}")


if __name__ == "__main__":
    main()
