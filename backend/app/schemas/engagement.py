from pydantic import BaseModel, Field, model_validator

GRADE = "^(junior|middle|senior|lead)$"


class InvitationIn(BaseModel):
    candidate_id: int
    vacancy_id: int | None = None
    need_id: int | None = None
    offer_description: str = Field(min_length=10, max_length=4000)
    salary_from: int = Field(gt=0)
    salary_to: int = Field(gt=0)
    contact_method: str = Field(min_length=3, max_length=320)

    @model_validator(mode="after")
    def check_salary(self):
        if self.salary_from > self.salary_to:
            raise ValueError("Нижняя граница вилки больше верхней")
        return self


class InvitationEventOut(BaseModel):
    status: str
    created_at: str


class InvitationOut(BaseModel):
    id: int
    status: str
    company_name: str
    offer_description: str
    salary_from: int
    salary_to: int
    contact_method: str
    created_at: str
    viewed_at: str | None = None
    responded_at: str | None = None
    vacancy_id: int | None = None
    vacancy_title: str | None = None
    need_id: int | None = None
    employer: dict = {}
    candidate: dict | None = None
    history: list[InvitationEventOut] = []


class InvitationDecisionIn(BaseModel):
    decision: str = Field(pattern="^(accepted|declined)$")


class VacancyIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=8000)
    specialization_code: str = Field(min_length=2, max_length=32)
    grade: str = Field(pattern=GRADE)
    skills: list[str] = []
    city: str = Field(default="", max_length=120)
    work_format: str = Field(default="remote", max_length=80)
    salary_from: int = Field(gt=0)
    salary_to: int = Field(gt=0)
    is_published: bool = True

    @model_validator(mode="after")
    def check_salary(self):
        if self.salary_from > self.salary_to:
            raise ValueError("Нижняя граница вилки больше верхней")
        return self


class VacancyOut(VacancyIn):
    id: int
    created_at: str
    skill_labels: list[str] = []
    company_name: str = ""
    employer: dict = {}
    applications_count: int = 0
    my_application_status: str | None = None


class ApplicationIn(BaseModel):
    message: str = Field(default="", max_length=2000)


class ApplicationOut(BaseModel):
    id: int
    status: str
    message: str
    created_at: str
    responded_at: str | None = None
    vacancy_id: int
    vacancy_title: str = ""
    company_name: str = ""
    candidate: dict | None = None


class ApplicationDecisionIn(BaseModel):
    decision: str = Field(pattern="^(accepted|declined|viewed)$")


class SpotTaskIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    prompt: str = Field(default="", max_length=4000)
    kind: str = Field(default="open", pattern="^(open|generated)$")
    specialization_code: str = Field(min_length=2, max_length=32)
    grade: str = Field(pattern=GRADE)
    is_active: bool = True


class SpotTaskOut(SpotTaskIn):
    id: int
    created_at: str
    assigned_count: int = 0
    answered_count: int = 0


class SpotAssignmentOut(BaseModel):
    id: int
    task_id: int
    title: str
    prompt: str
    kind: str
    status: str
    assigned_at: str
    answered_at: str | None = None
    answer_text: str | None = None
    is_correct: bool | None = None
    company_name: str = ""
    candidate_name: str | None = None


class SpotAnswerIn(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
