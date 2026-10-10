"""Tests for the matching mechanic and the data it reads."""
from datetime import datetime, timedelta, timezone

import pytest

from app.domain import fsp as fsp_domain
from app.domain import skills as skills_vocab
from app.domain.matching import (
    GRADE_OFFSET_FIT,
    WEIGHTS,
    CandidateFeatures,
    Need,
    rank,
    route_categories,
    score_candidate,
)
from app.domain.resume import parse

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)


def candidate(**overrides) -> CandidateFeatures:
    base = dict(
        candidate_id=1,
        specialization="backend",
        confirmed_grade="senior",
        theta=1.2,
        se=0.25,
        skills=("python", "postgresql", "kafka"),
        fsp_strength=0.0,
        fsp_reason=None,
        city="Москва",
        work_format="remote",
        years_experience=6.0,
        profile_completeness=1.0,
        confirmed_at=NOW - timedelta(days=10),
        spot_tasks_answered=0,
    )
    base.update(overrides)
    return CandidateFeatures(**base)


NEED = Need("backend", "senior", ("python", "postgresql", "kafka"))


def test_weights_sum_to_one_hundred():
    assert sum(WEIGHTS.values()) == pytest.approx(100.0)


def test_routing_covers_requested_and_adjacent_grades():
    routed = route_categories(NEED)
    assert [grade for _, grade, _, _ in routed] == ["senior", "lead", "middle"]
    # The exact category must always carry the largest share.
    assert routed[0][2] == max(share for _, _, share, _ in routed)
    assert routed[0][2] == GRADE_OFFSET_FIT[0]


def test_other_specialization_never_matches():
    assert score_candidate(NEED, candidate(specialization="frontend"), NOW) is None


def test_candidate_without_confirmed_grade_never_matches():
    assert score_candidate(NEED, candidate(confirmed_grade=None, theta=None), NOW) is None


def test_grade_two_steps_away_is_out_of_scope():
    assert score_candidate(NEED, candidate(confirmed_grade="junior", theta=-1.2), NOW) is None


def test_require_fsp_filters_candidates_without_a_record():
    strict = Need("backend", "senior", ("python",), require_fsp=True)
    assert score_candidate(strict, candidate(fsp_strength=0.0), NOW) is None
    assert score_candidate(strict, candidate(fsp_strength=40.0), NOW) is not None


def test_full_stack_coverage_scores_higher_than_partial():
    full = score_candidate(NEED, candidate(), NOW)
    partial = score_candidate(NEED, candidate(skills=("python",)), NOW)
    assert full.components["skills"] > partial.components["skills"]
    assert full.components["skills"] == pytest.approx(WEIGHTS["skills"])
    assert partial.missing_skills == ["postgresql", "kafka"]


def test_uncertain_measurement_weighs_less_than_a_precise_one():
    precise = score_candidate(NEED, candidate(se=0.22), NOW)
    noisy = score_candidate(NEED, candidate(se=0.58), NOW)
    assert precise.components["proof"] > noisy.components["proof"]


def test_exact_category_outranks_adjacent_one_all_else_equal():
    exact = score_candidate(NEED, candidate(), NOW)
    higher = score_candidate(NEED, candidate(confirmed_grade="lead", theta=2.0), NOW)
    assert exact.components["category"] > higher.components["category"]


def test_every_result_explains_itself():
    result = score_candidate(NEED, candidate(fsp_strength=60.0, fsp_reason="ФСП: 2 призовых места"), NOW)
    codes = {reason.code for reason in result.reasons}
    assert {"category", "skills", "proof", "fsp", "activity"} <= codes
    # Contributions must add up to the score within the soft-preference bonus.
    assert sum(reason.contribution for reason in result.reasons) == pytest.approx(result.score, abs=0.05)


def test_rank_is_ordered_and_numbered():
    people = [
        candidate(candidate_id=1, skills=("python",)),
        candidate(candidate_id=2, skills=("python", "postgresql", "kafka"), fsp_strength=70.0),
        candidate(candidate_id=3, specialization="qa"),
    ]
    results = rank(NEED, people, NOW)
    assert [r.candidate_id for r in results] == [2, 1]
    assert [r.rank for r in results] == [1, 2]
    assert results[0].score >= results[1].score


def test_score_never_exceeds_one_hundred():
    strongest = candidate(theta=1.79, se=0.19, fsp_strength=100.0, spot_tasks_answered=9)
    assert score_candidate(NEED, strongest, NOW).score <= 100.0


# --- skills vocabulary -------------------------------------------------------

def test_skills_are_extracted_through_russian_inflection():
    found = skills_vocab.extract("ищу питониста с кафкой и постгресом")
    assert {"python", "kafka", "postgresql"} <= set(found)


def test_skill_extraction_avoids_lookalike_words():
    assert skills_vocab.extract("играет на гитаре и носит пандору") == []


def test_unknown_skills_are_dropped_on_normalization():
    assert skills_vocab.normalize_many(["golang", "выдуманный навык", "C++"]) == ["go", "cpp"]


# --- FSP scoring -------------------------------------------------------------

def achievement(level="national", place=1, field=500, days_ago=100):
    return fsp_domain.Achievement("Чемпионат", level, place, field, NOW - timedelta(days=days_ago))


def test_fsp_strength_is_bounded_and_monotonic():
    assert fsp_domain.profile_strength([], NOW) == 0.0
    one = fsp_domain.profile_strength([achievement()], NOW)
    many = fsp_domain.profile_strength([achievement()] * 5, NOW)
    assert 0 < one < many <= 100.0


def test_recent_results_outweigh_old_ones():
    fresh = fsp_domain.profile_strength([achievement(days_ago=30)], NOW)
    stale = fsp_domain.profile_strength([achievement(days_ago=2000)], NOW)
    assert fresh > stale


def test_higher_level_and_better_place_score_higher():
    assert fsp_domain.achievement_weight(achievement(level="international"), NOW) > \
           fsp_domain.achievement_weight(achievement(level="city"), NOW)
    assert fsp_domain.achievement_weight(achievement(place=1), NOW) > \
           fsp_domain.achievement_weight(achievement(place=50), NOW)


# --- résumé parsing ----------------------------------------------------------

RESUME = """Иванов Пётр Сергеевич
Senior Backend Developer
Москва · ivanov.p@example.com · +7 (916) 123-45-67 · t.me/petr_dev

О себе: Бэкенд-разработчик с опытом 7 лет. Проектирую сервисы, делаю код-ревью.

Опыт: Python, FastAPI, PostgreSQL, Kafka, Docker, Kubernetes.
"""


def test_resume_parsing_extracts_identity_contacts_and_stack():
    parsed = parse(RESUME)
    assert parsed.full_name == "Иванов Пётр Сергеевич"
    assert parsed.email == "ivanov.p@example.com"
    assert parsed.telegram == "@petr_dev"
    assert parsed.city == "Москва"
    assert parsed.years_experience == 7.0
    assert {"python", "fastapi", "postgresql", "kafka"} <= set(parsed.skills)


def test_resume_grade_is_only_a_hint_and_is_flagged():
    parsed = parse(RESUME)
    assert parsed.grade_hint == "senior"
    assert any("тестирование" in warning for warning in parsed.warnings)


def test_empty_resume_degrades_gracefully():
    parsed = parse("")
    assert parsed.full_name == ""
    assert parsed.warnings
