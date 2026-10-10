from pydantic import BaseModel, Field


class SurveyIn(BaseModel):
    industry: str = Field(min_length=2, max_length=120)
    specialization: str = Field(min_length=2, max_length=32)
    declared_grade: str = Field(pattern="^(junior|middle|senior|lead)$")


class SurveyOut(BaseModel):
    industry: str
    specialization: str
    declared_grade: str
    category_id: int | None = None
    confirmed_grade: str | None = None
    grade_change_allowed_at: str | None


class SpecializationStatusOut(BaseModel):
    specialization: str
    specialization_name: str
    declared_grade: str
    confirmed_grade: str | None
    theta: float | None
    grade_change_allowed_at: str | None
    recommended_grade: str | None = None


class AttemptStartIn(BaseModel):
    specialization: str = Field(min_length=2, max_length=32)
    grade: str = Field(pattern="^(junior|middle|senior|lead)$")


class AttemptOut(BaseModel):
    id: int
    requested_grade: str
    theta: float
    se: float
    status: str
    answered_count: int
    specialization: str | None = None
    resumed: bool = False
    max_items: int = 15
    extended_max_items: int = 20
    min_items: int = 8


class NextItemOut(BaseModel):
    attempt_id: int
    item_id: int
    prompt: str
    answer_type: str
    progress: int
    min_items: int = 8
    max_items: int = 15
    extended_max_items: int = 20


class AnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=2000)


class AnswerOut(BaseModel):
    correct: bool
    theta: float
    se: float
    progress: int
    finished: bool
    grade: str | None = None


class FinishOut(BaseModel):
    attempt_id: int
    status: str
    theta: float
    se: float
    grade: str | None
    category: str | None
    specialization: str | None
    grade_change_allowed_at: str | None
    recommended_grade: str | None = None
