# Day 2 acceptance

## Scope

Day 2 implements the testing/categorization block from `SPEC.md` and the FSP technical specification.

### Implemented

- candidate survey: industry + specialization + declared grade;
- 6 specializations and 4 grades = 24 categories;
- 30 active item templates per specialization × grade = 720 active templates;
- 5 distinct task families per specialization × 6 variants, so a backend test is not a single repeated arithmetic family;
- deterministic item generation from `(template_code, seed)`;
- parameter space ≥ 10^4 distinguishable instances per template and answer entropy ≥ 6 bits on representative families;
- 2PL probability `P(u=1|θ)`;
- Fisher-information CAT;
- adaptive stop rule: at least 8, standard cap 15, early stop when `SE < 0.3`; if `SE > 0.45` at 15 items, up to 5 additional items are allowed;
- server-side grading with no answer key in API responses or database;
- θ-based grade assignment;
- 90-day restriction for changing an already confirmed grade, scoped per candidate + specialization; a candidate can independently test multiple specializations;
- development-only `POST /api/v1/dev/time-travel`;
- offline calibration and test–retest scripts;
- candidate UI for survey, adaptive test and result;
- Russian-language task statements covering the six specialization skill cores from SPEC.

### Task-family matrix

| Specialization | Task families |
|---|---|
| Backend | algorithms, SQL, API, concurrency, cache |
| Frontend | JS/TS, browser, layout, state, HTTP |
| Mobile | lifecycle, async, storage, battery, networking |
| Data/ML | SQL analytics, statistics, classification, pipeline, quality |
| DevOps | Linux, networking, CI/CD, containers, observability |
| QA | boundary testing, pairwise, API assertions, requirements, automation |

## Acceptance checks

1. Two candidates receive different generated conditions because seeds differ.
2. `GET /test/attempts/{id}/next` returns only the task statement and metadata.
3. `TestItem` stores the candidate answer and correctness flag, but not the expected answer.
4. Re-running a generator with the same `(template, seed)` gives the same condition.
5. The test uses Fisher information to choose the next unused template.
6. A result is based on θ, not raw percentage.
7. The candidate cannot finish before 8 answered items; normal automatic stop is possible from item 8 when `SE < 0.3`, with a standard cap of 15.
8. If `SE > 0.45` at item 15, the implementation allows up to 5 additional items before finalization.
9. The same API is used for a second attempt with new seeds.
10. Offline validation uses 200 simulated candidates and produces `data/validation/day2_test_retest.json`.
11. Calibration produces `data/validation/item_calibration.json`.
12. Representative generators have 10,000 distinct prompt instances and answer entropy ≥ 6 bits.

## API

- `POST /api/v1/survey`
- `GET /api/v1/me/testing/specializations` — confirmed/requested specialization states and per-specialization cooldowns
- `POST /api/v1/test/attempts`
- `GET /api/v1/test/attempts/{id}/next`
- `POST /api/v1/test/items/{id}/answer`
- `POST /api/v1/test/attempts/{id}/finish`
- `POST /api/v1/dev/time-travel` (dev only)

The next item response never contains an expected answer.

## Current offline validation result

The reproducible Day 2 simulation on the 200 synthetic candidates currently reports:

- test–retest correlation: **0.941** (target ≥ 0.85) — pass;
- θ RMSE: **0.306** (target ≤ 0.35) — pass;
- grade agreement: **0.810** (target ≥ 0.80) — pass;
- mean number of items: about **8.6** per run.

The validation target values come from `SPEC.md`; the reported values are the actual reproducible run after the item-bank update.
