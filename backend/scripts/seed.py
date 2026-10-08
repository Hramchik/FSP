import asyncio
from sqlalchemy import select, update
from app.db.session import SessionLocal
from app.models.models import (
    Specialization, Category, Skill, SkillAlias, ItemTemplate,
    User, CandidateProfile, EmployerProfile, UserRole,
)
from app.core.security import hash_password

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
ALIASES = {"golang": "go", "postgres": "postgresql", "postgresql": "postgresql", "ts": "typescript", "js": "javascript"}

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


async def main():
    async with SessionLocal() as db:
        # Always load the complete reference data, including on an existing DB.
        specs = {s.code: s for s in (await db.scalars(select(Specialization))).all()}
        for code, name in SPECS.items():
            if code not in specs:
                s = Specialization(code=code, name=name)
                db.add(s)
                await db.flush()
                specs[code] = s
                for grade, lo, hi in GRADES:
                    db.add(Category(specialization_id=s.id, grade=grade, theta_min=lo, theta_max=hi))

        if not await db.scalar(select(Skill).limit(1)):
            skills = {}
            for code in SKILLS:
                sk = Skill(code=code, name=code)
                db.add(sk)
                await db.flush()
                skills[code] = sk
            for alias, code in ALIASES.items():
                db.add(SkillAlias(skill_id=skills[code].id, alias=alias))

        desired_codes = set()
        for spec_code, spec in specs.items():
            if spec_code not in TASK_FAMILIES:
                continue
            # Retire the original one-family arithmetic bank from the active pool.
            await db.execute(
                update(ItemTemplate)
                .where(ItemTemplate.specialization_id == spec.id)
                .values(is_active=False)
            )
            for grade in ANCHORS:
                for family in TASK_FAMILIES[spec_code]:
                    for variant in range(6):
                        family_index = TASK_FAMILIES[spec_code].index(family)
                        global_variant = family_index * 6 + variant
                        code = f"{spec_code}_{family}_v{variant:02d}_{grade}"
                        desired_codes.add(code)
                        template = await db.scalar(select(ItemTemplate).where(ItemTemplate.code == code))
                        if template is None:
                            template = ItemTemplate(
                                code=code,
                                specialization_id=spec.id,
                                kind="numeric",
                                irt_a=round(2.0 + (global_variant % 10) * 0.12, 3),
                                irt_b=round(ANCHORS[grade] + (global_variant - 14) * 0.025, 3),
                                param_space_size=100000 + global_variant * 1000,
                                is_active=True,
                            )
                            db.add(template)
                        else:
                            template.is_active = True
                            template.irt_a = round(2.0 + (global_variant % 10) * 0.12, 3)
                            template.irt_b = round(ANCHORS[grade] + (global_variant - 14) * 0.025, 3)
                            template.param_space_size = 100000 + global_variant * 1000

        if not await db.scalar(select(User).where(User.email == "demo.candidate@fsp.local")):
            u = User(email="demo.candidate@fsp.local", password_hash=hash_password("DemoPass123!"), role=UserRole.candidate, is_email_verified=True)
            db.add(u)
            await db.flush()
            db.add(CandidateProfile(user_id=u.id, display_name="Demo Candidate", city="Berlin", is_searchable=True))
        if not await db.scalar(select(User).where(User.email == "demo.employer@fsp.local")):
            u = User(email="demo.employer@fsp.local", password_hash=hash_password("DemoPass123!"), role=UserRole.employer, is_email_verified=True)
            db.add(u)
            await db.flush()
            db.add(EmployerProfile(user_id=u.id, company_name="FSP Demo Tech", description="Demo employer", contact="hr@fsp.local"))

        await db.commit()
        print(f"Seeded {len(desired_codes)} active task templates across six specializations.")


asyncio.run(main())
