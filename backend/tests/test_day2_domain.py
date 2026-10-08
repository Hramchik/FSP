import math
from app.domain.irt import probability, fisher_information, estimate_theta, grade_for_theta
from app.domain.items.templates import generate, grade, parameter_fingerprint
from app.domain.items.templates.numeric import _task


def test_generator_is_deterministic_and_has_large_space():
    values = {parameter_fingerprint("backend_algorithms_v00_middle", seed) for seed in range(10000)}
    assert len(values) == 10000
    a = generate("backend_algorithms_v00_middle", 123)
    b = generate("backend_algorithms_v00_middle", 123)
    assert a == b
    assert generate("backend_algorithms_v00_middle", 123).prompt != generate("backend_algorithms_v00_middle", 124).prompt


def test_answer_is_recomputed_without_exposing_it():
    item = generate("backend_algorithms_v00_middle", 42)
    assert not hasattr(item, "answer")
    # Wrong answer should be false; the correct answer is not exposed.
    assert grade("backend_algorithms_v00_middle", 42, "0") is False


def test_2pl_and_grade_thresholds():
    assert 0 < probability(0, 1, 0) < 1
    assert fisher_information(0, 1, 0) > 0
    assert grade_for_theta(-1) == "junior"
    assert grade_for_theta(0) == "middle"
    assert grade_for_theta(1) == "senior"
    assert grade_for_theta(2) == "lead"


def test_theta_estimation_moves_with_responses():
    hard = [(1, 1.2, -1.0)] * 8
    easy = [(0, 1.2, -1.0)] * 8
    assert estimate_theta(hard).theta > 0
    assert estimate_theta(easy).theta < 0


def test_all_specializations_have_distinct_task_families():
    task_families = {
        "backend": ["algorithms", "sql", "api", "concurrency", "cache"],
        "frontend": ["js_ts", "browser", "layout", "state", "http"],
        "mobile": ["lifecycle", "async", "storage", "battery", "mobile_networking"],
        "data": ["sql_analytics", "statistics", "classification", "pipeline", "quality"],
        "devops": ["linux", "devops_networking", "cicd", "containers", "observability"],
        "qa": ["boundaries", "pairwise", "api_assertions", "requirements", "automation"],
    }
    assert set(task_families) == {"backend", "frontend", "mobile", "data", "devops", "qa"}
    assert all(len(families) == 5 for families in task_families.values())
    assert all(len(set(families)) == 5 for families in task_families.values())


def test_template_has_10k_distinguishable_instances_and_answer_entropy():
    import math
    template_codes = [
        "backend_algorithms_v00_middle",
        "frontend_js_ts_v00_middle",
        "mobile_async_v00_middle",
        "data_statistics_v00_middle",
        "devops_cicd_v00_middle",
        "qa_boundaries_v00_middle",
    ]
    for code in template_codes:
        prompts = set()
        answers = []
        for seed in range(10000):
            prompt, expected = _task(code, seed)
            prompts.add(prompt)
            answers.append(expected)
        assert len(prompts) == 10000
        counts = {}
        for answer in answers:
            counts[answer] = counts.get(answer, 0) + 1
        entropy = -sum((n / len(answers)) * math.log2(n / len(answers)) for n in counts.values())
        assert entropy >= 6.0
