from pydantic import BaseModel, Field, model_validator

GRADE = "^(junior|middle|senior|lead)$"


class NeedIn(BaseModel):
    title: str = Field(default="", max_length=200)
    text: str = Field(default="", max_length=4000)
    specialization_code: str = Field(min_length=2, max_length=32)
    grade: str = Field(pattern=GRADE)
    skills: list[str] = []
    city: str = Field(default="", max_length=120)
    work_format: str = Field(default="", max_length=80)
    salary_from: int | None = Field(default=None, ge=0)
    salary_to: int | None = Field(default=None, ge=0)
    require_fsp: bool = False

    @model_validator(mode="after")
    def check_salary(self):
        if self.salary_from is not None and self.salary_to is not None and self.salary_from > self.salary_to:
            raise ValueError("Нижняя граница вилки больше верхней")
        return self


class NeedOut(NeedIn):
    id: int
    created_at: str
    skill_labels: list[str] = []
    shortlist_id: int | None = None
    routed_categories: list[str] = []


class ReasonOut(BaseModel):
    code: str
    text: str
    contribution: float


class CandidateCardOut(BaseModel):
    """What an employer may see before contacts are unlocked."""
    candidate_id: int
    display_name: str
    category: str
    grade: str
    specialization: str
    theta: float | None = None
    se: float | None = None
    city: str = ""
    work_format: str = ""
    years_experience: float = 0.0
    skills: list[str] = []
    skill_labels: list[str] = []
    roles: list[str] = []
    soft_skills: list[str] = []
    bio: str = ""
    salary_expectation: str | None = None
    fsp: dict = {}
    contacts: dict | None = None
    contacts_locked_reason: str | None = None
    invitation_status: str | None = None


class ShortlistItemOut(BaseModel):
    rank: int
    score: float
    category: str
    components: dict
    reasons: list[ReasonOut]
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    candidate: CandidateCardOut


class RefinementIn(BaseModel):
    """Narrows an existing shortlist without rebuilding it."""
    min_score: float | None = Field(default=None, ge=0, le=100)
    grades: list[str] = []
    skills: list[str] = []
    city: str = ""
    work_format: str = ""
    fsp_only: bool = False
    hide_invited: bool = False
    sort: str = Field(default="score", pattern="^(score|fsp|proof|experience)$")


class ShortlistOut(BaseModel):
    shortlist_id: int
    need_id: int
    weights_version: str
    created_at: str
    total_in_pool: int
    total_shown: int
    routed_categories: list[str]
    weights: dict
    refinement: RefinementIn
    items: list[ShortlistItemOut]


class SearchQuery(BaseModel):
    specialization_code: str | None = None
    grades: list[str] = []
    skills: list[str] = []
    city: str = ""
    work_format: str = ""
    fsp_only: bool = False
    query: str = Field(default="", max_length=500)
    limit: int = Field(default=30, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class SearchOut(BaseModel):
    total: int
    items: list[CandidateCardOut]
