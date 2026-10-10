from pydantic import BaseModel, EmailStr, Field, model_validator

GRADE = "^(junior|middle|senior|lead)$"


class CandidateProfileIn(BaseModel):
    display_name: str = Field(default="", max_length=160)
    city: str = Field(default="", max_length=120)
    work_format: str = Field(default="remote", max_length=80)
    bio: str = Field(default="", max_length=4000)
    phone: str = Field(default="", max_length=64)
    telegram: str = Field(default="", max_length=64)
    github: str = Field(default="", max_length=120)
    skills: list[str] = []
    roles: list[str] = []
    soft_skills: list[str] = []
    years_experience: float = Field(default=0.0, ge=0, le=60)
    salary_expectation_from: int | None = Field(default=None, ge=0)
    salary_expectation_to: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def check_salary(self):
        low, high = self.salary_expectation_from, self.salary_expectation_to
        if low is not None and high is not None and low > high:
            raise ValueError("Нижняя граница зарплатных ожиданий больше верхней")
        return self


class CandidateSettingsIn(BaseModel):
    is_searchable: bool = False
    consent_publication: bool = False
    show_fsp: bool = True
    show_salary_expectation: bool = True
    show_city: bool = True
    accepts_spot_tasks: bool = True


class CandidateCategoryOut(BaseModel):
    specialization: str
    specialization_name: str
    grade: str
    theta: float | None = None
    confirmed_at: str | None = None


class CandidateProfileOut(CandidateProfileIn):
    id: int
    email: EmailStr
    is_email_verified: bool
    settings: CandidateSettingsIn
    skill_labels: list[str] = []
    completeness: float = 0.0
    categories: list[CandidateCategoryOut] = []
    fsp: dict = {}
    profile_ready: bool = False
    blocking_reasons: list[str] = []


class EmployerProfileIn(BaseModel):
    company_name: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=4000)
    contact: str = Field(default="", max_length=320)
    website: str = Field(default="", max_length=200)
    industry: str = Field(default="", max_length=120)
    city: str = Field(default="", max_length=120)
    team_size: str = Field(default="", max_length=64)


class EmployerProfileOut(EmployerProfileIn):
    id: int
    email: EmailStr
    is_email_verified: bool


class ResumeParseOut(BaseModel):
    parsed: dict
    applied: bool = False
    message: str = ""


class FspLinkIn(BaseModel):
    fsp_id: str = Field(min_length=3, max_length=120)
