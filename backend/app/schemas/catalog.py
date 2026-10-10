from pydantic import BaseModel


class SkillOut(BaseModel):
    code: str
    label: str


class SpecializationOut(BaseModel):
    code: str
    name: str
    core_skills: list[SkillOut]


class CatalogOut(BaseModel):
    specializations: list[SpecializationOut]
    grades: list[str]
    skills: list[SkillOut]
    work_formats: list[str]
    # Lets the client show dev-only affordances (such as resetting the grade
    # cooldown for a demo) instead of guessing from a 404.
    app_env: str = "dev"
