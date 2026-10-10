"""Reference data plus a demo world that is enough to run the whole scenario.

Re-running is safe: reference rows are upserted, demo rows are created once.
"""
import asyncio
import hashlib
import random
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.domain.irt import probability
from app.models.models import (
    Category, CandidateProfile, CandidateSpecialization, EmployerNeed, EmployerProfile,
    FspAchievement, FspLink, ItemTemplate, Skill, SkillAlias, Specialization, SpotTask,
    TestAttempt, User, UserRole, Vacancy,
)

SPECS = {
    "backend": "Бэкенд-разработка",
    "frontend": "Фронтенд-разработка",
    "mobile": "Мобильная разработка",
    "data": "Данные и ML",
    "devops": "DevOps и инфраструктура",
    "qa": "Тестирование",
}
GRADES = [("junior", None, -0.5), ("middle", -0.5, 0.7), ("senior", 0.7, 1.8), ("lead", 1.8, None)]
SKILLS = [
    "python", "go", "java", "typescript", "javascript", "react", "postgresql", "sql",
    "docker", "kubernetes", "linux", "ci-cd", "statistics", "pytorch", "pytest", "api-design",
]
ALIASES = {"golang": "go", "postgres": "postgresql", "ts": "typescript", "js": "javascript"}

# Five distinct task families × six deterministic variants = 30 active templates
# for every specialization × grade, while keeping the same calibrated IRT scale.
TASK_FAMILIES = {
    "backend": ["algorithms", "sql", "api", "concurrency", "cache"],
    "frontend": ["js_ts", "browser", "layout", "state", "http"],
    "mobile": ["lifecycle", "async", "storage", "battery", "mobile_networking"],
    "data": ["sql_analytics", "statistics", "classification", "pipeline", "quality"],
    "devops": ["linux", "devops_networking", "cicd", "containers", "observability"],
    "qa": ["boundaries", "pairwise", "api_assertions", "requirements", "automation"],
}
ANCHORS = {"junior": -1.2, "middle": 0.1, "senior": 1.15, "lead": 2.25}
GRADE_THETA = {"junior": -1.1, "middle": 0.1, "senior": 1.2, "lead": 2.2}

DEMO_PASSWORD = "DemoPass123!"
SEED = 20261010

EVENTS = [
    ("Всероссийский чемпионат по спортивному программированию", "national", 640),
    ("Международный кубок ФСП", "international", 1200),
    ("Региональный чемпионат ФСП", "regional", 180),
    ("Студенческий кубок ФСП", "student", 320),
    ("Открытый хакатон ФСП", "open", 90),
]

# (e-mail, name, spec, grade, city, format, years, stack, roles, softs, fsp_id, bio)
DEMO_CANDIDATES = [
    ("anna.belova@fsp.example", "Белова Анна", "backend", "senior", "Москва", "remote", 7.0,
     ["python", "fastapi", "postgresql", "kafka", "docker", "kubernetes", "api-design", "highload"],
     ["Разработка", "Архитектура", "Код-ревью"], ["Командная работа", "Наставничество", "Английский язык"],
     "FSP-100001", "Проектирую и сопровождаю высоконагруженные сервисы на Python. Люблю аккуратные границы между модулями."),
    ("ilya.sokolov@fsp.example", "Соколов Илья", "backend", "senior", "Казань", "hybrid", 6.0,
     ["go", "postgresql", "redis", "microservices", "docker", "api-design"],
     ["Разработка", "Код-ревью"], ["Ответственность", "Коммуникация"],
     "FSP-100002", "Go-разработчик, делал платёжный шлюз и биллинг. Отвечаю за SLA сервиса."),
    ("marina.orlova@fsp.example", "Орлова Марина", "backend", "middle", "Санкт-Петербург", "remote", 3.5,
     ["python", "django", "postgresql", "sql", "docker"],
     ["Разработка"], ["Командная работа", "Ответственность"],
     None, "Бэкенд на Django, пишу интеграции и фоновые задачи."),
    ("pavel.ivanov@fsp.example", "Иванов Павел", "backend", "lead", "Москва", "office", 10.0,
     ["java", "spring", "postgresql", "kafka", "kubernetes", "microservices", "highload", "api-design"],
     ["Тимлид", "Архитектура", "Менторство"], ["Командная работа", "Публичные выступления"],
     "FSP-100003", "Веду команду из восьми человек, отвечаю за архитектуру платформы."),
    ("oleg.kuzmin@fsp.example", "Кузьмин Олег", "backend", "junior", "Новосибирск", "remote", 1.0,
     ["python", "sql", "git"], ["Разработка"], ["Ответственность"],
     "FSP-100004", "Год в коммерческой разработке, активно участвую в олимпиадах."),
    ("daria.nikitina@fsp.example", "Никитина Дарья", "frontend", "senior", "Москва", "remote", 6.5,
     ["typescript", "react", "nextjs", "javascript", "nodejs", "ci-cd"],
     ["Разработка", "Код-ревью", "Менторство"], ["Командная работа", "Коммуникация"],
     "FSP-100005", "Фронтенд-архитектура, дизайн-системы, производительность интерфейсов."),
    ("sergey.volkov@fsp.example", "Волков Сергей", "frontend", "middle", "Екатеринбург", "hybrid", 3.0,
     ["javascript", "typescript", "react", "vue"], ["Разработка"], ["Ответственность"],
     None, "Пишу интерфейсы на React, занимаюсь доступностью."),
    ("ekaterina.popova@fsp.example", "Попова Екатерина", "data", "senior", "Москва", "remote", 5.5,
     ["python", "sql", "pandas", "pytorch", "statistics", "airflow", "mlops", "clickhouse"],
     ["Разработка", "Аналитика"], ["Командная работа", "Английский язык"],
     "FSP-100006", "ML-инженер: рекомендации, ранжирование, продуктовая аналитика."),
    ("artem.lebedev@fsp.example", "Лебедев Артём", "devops", "senior", "Санкт-Петербург", "remote", 7.5,
     ["kubernetes", "docker", "terraform", "linux", "ci-cd", "prometheus", "grafana", "ansible"],
     ["Эксплуатация", "Архитектура"], ["Ответственность", "Командная работа"],
     "FSP-100007", "Строю платформу и CI/CD, дежурю в on-call ротации."),
    ("nikita.morozov@fsp.example", "Морозов Никита", "qa", "middle", "Казань", "remote", 3.0,
     ["pytest", "python", "selenium", "test-design", "autotests", "postman"],
     ["Разработка", "Аналитика"], ["Ответственность", "Коммуникация"],
     "FSP-100008", "Автоматизирую регресс, занимаюсь тест-дизайном API."),
    ("alina.gusev@fsp.example", "Гусева Алина", "mobile", "middle", "Москва", "hybrid", 4.0,
     ["kotlin", "android", "java", "sql"], ["Разработка", "Код-ревью"], ["Командная работа"],
     None, "Android-разработчик, фокус на офлайн-режиме и производительности."),
    ("roman.zaytsev@fsp.example", "Зайцев Роман", "frontend", "junior", "Воронеж", "remote", 1.2,
     ["javascript", "react", "typescript"], ["Разработка"], ["Ответственность"],
     "FSP-100009", "Недавно перешёл из вёрстки в React, активно участвую в соревнованиях ФСП."),
]

DEMO_EMPLOYERS = [
    ("demo.employer@fsp.example", "ФСП Демо Тех", "Продуктовая ИТ-компания, делаем платформу для спортивных соревнований.",
     "hr@fsp.example", "https://fsp.example", "Информационные технологии", "Москва", "120 человек"),
    ("hr.finflow@fsp.example", "ФинФлоу", "Финтех: платежи, биллинг, антифрод.",
     "jobs@finflow.example", "https://finflow.example", "Финтех", "Санкт-Петербург", "350 человек"),
]

DEMO_NEEDS = [
    (0, "Senior Python в платформенную команду",
     "Ищем сильного бэкендера на Python и FastAPI. Нужен реальный опыт с PostgreSQL и Kafka, "
     "понимание высоких нагрузок, Docker и Kubernetes. Команда из шести человек, продукт в проде три года.",
     "backend", "senior", "Москва", "remote", 280000, 400000, False),
    (1, "Senior Frontend (React/TypeScript)",
     "Нужен фронтенд-разработчик уровня senior: TypeScript, React, Next.js. "
     "Работаем над личным кабинетом клиента, важна производительность и доступность.",
     "frontend", "senior", "", "remote", 250000, 350000, False),
    (1, "DevOps-инженер с опытом Kubernetes",
     "Требуется инженер для развития платформы: Kubernetes, Terraform, CI/CD, Prometheus и Grafana. "
     "Дежурства в ротации, инфраструктура на bare-metal и в облаке.",
     "devops", "senior", "Санкт-Петербург", "hybrid", 300000, 420000, True),
]

DEMO_VACANCIES = [
    (0, "Backend-разработчик (Python, middle)",
     "Разработка сервисов на Python/FastAPI, интеграции, PostgreSQL. Готовы брать после 2+ лет коммерческого опыта.",
     "backend", "middle", "Москва", "hybrid", 180000, 260000),
    (1, "QA-инженер (автоматизация)",
     "Автотесты на Python и pytest, тест-дизайн, работа с API через Postman. Удалённо.",
     "qa", "middle", "", "remote", 150000, 220000),
]

DEMO_SPOT_TASKS = [
    (0, "Короткая задача от платформенной команды", "generated", "backend", "senior", ""),
    (0, "Как бы вы спроектировали идемпотентность?", "open", "backend", "senior",
     "Сервис принимает платёжные запросы по HTTP. Клиент может повторить запрос при таймауте. "
     "Опишите в 5–10 предложениях, как вы обеспечите идемпотентность и что положите в хранилище."),
    (1, "Деградация фронтенда при медленном API", "open", "frontend", "senior",
     "API отвечает за 3–5 секунд в пиковые часы. Опишите, как вы перестроите загрузку личного кабинета, "
     "чтобы пользователь увидел полезный интерфейс раньше."),
]


async def ensure_reference(db):
    specs = {s.code: s for s in (await db.scalars(select(Specialization))).all()}
    for code, name in SPECS.items():
        if code not in specs:
            specialization = Specialization(code=code, name=name)
            db.add(specialization)
            await db.flush()
            specs[code] = specialization
            for grade, low, high in GRADES:
                db.add(Category(specialization_id=specialization.id, grade=grade, theta_min=low, theta_max=high))

    if not await db.scalar(select(Skill).limit(1)):
        created = {}
        for code in SKILLS:
            skill = Skill(code=code, name=code)
            db.add(skill)
            await db.flush()
            created[code] = skill
        for alias, code in ALIASES.items():
            db.add(SkillAlias(skill_id=created[code].id, alias=alias))

    desired = 0
    for spec_code, specialization in specs.items():
        if spec_code not in TASK_FAMILIES:
            continue
        # Retire the original one-family arithmetic bank from the active pool.
        await db.execute(
            update(ItemTemplate).where(ItemTemplate.specialization_id == specialization.id).values(is_active=False)
        )
        for grade in ANCHORS:
            for family_index, family in enumerate(TASK_FAMILIES[spec_code]):
                for variant in range(6):
                    global_variant = family_index * 6 + variant
                    code = f"{spec_code}_{family}_v{variant:02d}_{grade}"
                    desired += 1
                    irt_a = round(2.0 + (global_variant % 10) * 0.12, 3)
                    irt_b = round(ANCHORS[grade] + (global_variant - 14) * 0.025, 3)
                    template = await db.scalar(select(ItemTemplate).where(ItemTemplate.code == code))
                    if template is None:
                        db.add(ItemTemplate(
                            code=code, specialization_id=specialization.id, kind="numeric",
                            irt_a=irt_a, irt_b=irt_b, param_space_size=100000 + global_variant * 1000,
                            is_active=True,
                        ))
                    else:
                        template.is_active = True
                        template.irt_a = irt_a
                        template.irt_b = irt_b
                        template.param_space_size = 100000 + global_variant * 1000
    return specs, desired


async def ensure_user(db, email: str, role: UserRole) -> tuple[User, bool]:
    user = await db.scalar(select(User).where(User.email == email))
    if user:
        return user, False
    user = User(email=email, password_hash=hash_password(DEMO_PASSWORD), role=role, is_email_verified=True)
    db.add(user)
    await db.flush()
    return user, True


async def seed_achievements(db, rng, fsp_id: str, strong: bool):
    if await db.scalar(select(FspAchievement).where(FspAchievement.fsp_id == fsp_id).limit(1)):
        return
    now = datetime.now(timezone.utc)
    for _ in range(rng.randint(2, 4) if strong else rng.randint(1, 2)):
        name, level, field = rng.choice(EVENTS)
        place = rng.randint(1, 3) if strong else rng.randint(4, 40)
        db.add(FspAchievement(
            fsp_id=fsp_id, event_name=name, event_level=level, place=place,
            participants_count=field, held_on=now - timedelta(days=rng.randint(60, 1500)),
            raw={"source": "mock-registry", "discipline": "продуктовое программирование"},
        ))


async def main():
    rng = random.Random(SEED)
    async with SessionLocal() as db:
        specs, templates = await ensure_reference(db)
        await db.commit()

        employers = []
        for email, name, description, contact, website, industry, city, size in DEMO_EMPLOYERS:
            user, _ = await ensure_user(db, email, UserRole.employer)
            profile = await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id == user.id))
            if not profile:
                profile = EmployerProfile(user_id=user.id)
                db.add(profile)
                await db.flush()
            profile.company_name, profile.description, profile.contact = name, description, contact
            profile.website, profile.industry, profile.city, profile.team_size = website, industry, city, size
            employers.append(profile)
        await db.commit()

        now = datetime.now(timezone.utc)
        for (email, name, spec_code, grade, city, work_format, years, stack,
             roles, softs, fsp_id, bio) in DEMO_CANDIDATES:
            user, created = await ensure_user(db, email, UserRole.candidate)
            profile = await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id == user.id))
            if not profile:
                profile = CandidateProfile(user_id=user.id)
                db.add(profile)
                await db.flush()
            specialization = specs[spec_code]
            theta = GRADE_THETA[grade] + rng.uniform(-0.18, 0.18)
            profile.display_name, profile.city, profile.work_format = name, city, work_format
            profile.bio, profile.skills, profile.roles, profile.soft_skills = bio, stack, roles, softs
            profile.years_experience = years
            profile.industry = "IT"
            profile.specialization_id = specialization.id
            profile.declared_grade = profile.confirmed_grade = grade
            profile.theta = round(theta, 4)
            profile.is_searchable = True
            profile.consent_publication = True
            profile.last_activity_at = now - timedelta(days=rng.randint(0, 25))
            profile.salary_expectation_from = int(90000 + years * 22000)
            profile.salary_expectation_to = int(130000 + years * 32000)
            profile.phone = f"+7 9{rng.randint(10, 99)} {rng.randint(100, 999)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}"
            profile.telegram = "@" + email.split("@")[0].replace(".", "_")

            link = await db.scalar(select(CandidateSpecialization).where(
                CandidateSpecialization.candidate_id == profile.id,
                CandidateSpecialization.specialization_id == specialization.id,
            ))
            if not link:
                link = CandidateSpecialization(
                    candidate_id=profile.id, specialization_id=specialization.id, declared_grade=grade
                )
                db.add(link)
                await db.flush()
            category = await db.scalar(select(Category).where(
                Category.specialization_id == specialization.id, Category.grade == grade
            ))
            link.declared_grade = link.confirmed_grade = grade
            link.theta = round(theta, 4)
            link.category_id = category.id if category else None
            link.grade_change_allowed_at = now + timedelta(days=rng.randint(20, 85))

            # A finished attempt is what the matcher reads SE and recency from,
            # so the demo world must contain one rather than only a θ value.
            attempt = await db.scalar(select(TestAttempt).where(
                TestAttempt.candidate_id == profile.id,
                TestAttempt.specialization_id == specialization.id,
                TestAttempt.status == "finished",
            ))
            if not attempt:
                finished = now - timedelta(days=rng.randint(3, 120))
                db.add(TestAttempt(
                    candidate_id=profile.id, specialization_id=specialization.id, requested_grade=grade,
                    theta=round(theta, 4), se=round(rng.uniform(0.21, 0.33), 3), status="finished",
                    started_at=finished - timedelta(minutes=18), finished_at=finished,
                ))

            if fsp_id:
                existing = await db.scalar(select(FspLink).where(FspLink.candidate_id == profile.id))
                if not existing:
                    db.add(FspLink(candidate_id=profile.id, fsp_id=fsp_id, verified_by="mock-registry"))
                await seed_achievements(db, rng, fsp_id, strong=grade in ("senior", "lead"))
        await db.commit()

        for (index, title, text, spec_code, grade, city, work_format,
             salary_from, salary_to, require_fsp) in DEMO_NEEDS:
            employer = employers[index]
            if await db.scalar(select(EmployerNeed).where(
                EmployerNeed.employer_id == employer.id, EmployerNeed.title == title
            )):
                continue
            from app.domain import skills as skills_vocab
            db.add(EmployerNeed(
                employer_id=employer.id, title=title, text=text, specialization_code=spec_code,
                grade=grade, skills=skills_vocab.extract(text), city=city, work_format=work_format,
                salary_from=salary_from, salary_to=salary_to, require_fsp=require_fsp,
            ))

        for index, title, description, spec_code, grade, city, work_format, salary_from, salary_to in DEMO_VACANCIES:
            employer = employers[index]
            if await db.scalar(select(Vacancy).where(Vacancy.employer_id == employer.id, Vacancy.title == title)):
                continue
            from app.domain import skills as skills_vocab
            db.add(Vacancy(
                employer_id=employer.id, title=title, description=description,
                specialization_code=spec_code, grade=grade, skills=skills_vocab.extract(description),
                city=city, work_format=work_format, salary_from=salary_from, salary_to=salary_to,
                is_published=True,
            ))

        for index, title, kind, spec_code, grade, prompt in DEMO_SPOT_TASKS:
            employer = employers[index]
            if await db.scalar(select(SpotTask).where(SpotTask.employer_id == employer.id, SpotTask.title == title)):
                continue
            db.add(SpotTask(
                employer_id=employer.id, title=title, prompt=prompt, kind=kind,
                specialization_code=spec_code, grade=grade, is_active=True,
            ))

        await db.commit()
        print(
            f"Seeded {templates} active task templates, {len(DEMO_CANDIDATES)} demo candidates, "
            f"{len(DEMO_EMPLOYERS)} employers, {len(DEMO_NEEDS)} needs, {len(DEMO_VACANCIES)} vacancies, "
            f"{len(DEMO_SPOT_TASKS)} spot tasks."
        )


asyncio.run(main())
