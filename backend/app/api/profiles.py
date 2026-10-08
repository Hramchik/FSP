from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.deps import current_user, require_role
from app.models.models import User, UserRole, CandidateProfile, EmployerProfile
from app.schemas.profile import CandidateProfileIn, CandidateProfileOut, EmployerProfileIn, EmployerProfileOut
router=APIRouter(tags=["profiles"])

@router.get("/me/candidate",response_model=CandidateProfileOut)
async def get_candidate(u=Depends(require_role(UserRole.candidate)),db:AsyncSession=Depends(get_db)):
    p=await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id==u.id)); return CandidateProfileOut(**p.__dict__,email=u.email)
@router.put("/me/candidate",response_model=CandidateProfileOut)
async def put_candidate(data:CandidateProfileIn,u=Depends(require_role(UserRole.candidate)),db:AsyncSession=Depends(get_db)):
    p=await db.scalar(select(CandidateProfile).where(CandidateProfile.user_id==u.id));
    for k,v in data.model_dump().items(): setattr(p,k,v)
    await db.commit(); return CandidateProfileOut(**p.__dict__,email=u.email)
@router.get("/me/employer",response_model=EmployerProfileOut)
async def get_employer(u=Depends(require_role(UserRole.employer)),db:AsyncSession=Depends(get_db)):
    p=await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id==u.id)); return EmployerProfileOut(**p.__dict__,email=u.email)
@router.put("/me/employer",response_model=EmployerProfileOut)
async def put_employer(data:EmployerProfileIn,u=Depends(require_role(UserRole.employer)),db:AsyncSession=Depends(get_db)):
    p=await db.scalar(select(EmployerProfile).where(EmployerProfile.user_id==u.id));
    for k,v in data.model_dump().items(): setattr(p,k,v)
    await db.commit(); return EmployerProfileOut(**p.__dict__,email=u.email)
