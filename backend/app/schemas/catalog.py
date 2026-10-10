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
