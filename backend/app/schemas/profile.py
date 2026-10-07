from pydantic import BaseModel, EmailStr
class CandidateProfileIn(BaseModel):
    display_name: str = ""
    city: str = ""
    work_format: str = "remote"
    bio: str = ""
class CandidateProfileOut(CandidateProfileIn):
    id: int; email: EmailStr; is_email_verified: bool; is_searchable: bool
class EmployerProfileIn(BaseModel):
    company_name: str = ""
    description: str = ""
    contact: str = ""
class EmployerProfileOut(EmployerProfileIn):
    id: int; email: EmailStr; is_email_verified: bool
