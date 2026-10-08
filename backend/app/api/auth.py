from datetime import datetime, timedelta, timezone
from secrets import token_urlsafe
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.models import User, EmailVerificationToken, CandidateProfile, EmployerProfile, UserRole
from app.schemas.auth import RegisterIn, RegisterOut, VerifyIn, LoginIn, RefreshIn, TokenOut
from app.core.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from app.core.config import settings
from app.deps import current_user

router=APIRouter(prefix="/auth", tags=["auth"])

@router.post("/register", response_model=RegisterOut, status_code=201)
async def register(data:RegisterIn, db:AsyncSession=Depends(get_db)):
    if await db.scalar(select(User).where(User.email==data.email.lower())): raise HTTPException(409,"Email already registered")
    u=User(email=data.email.lower(), password_hash=hash_password(data.password), role=data.role)
    db.add(u); await db.flush()
    if data.role==UserRole.candidate: db.add(CandidateProfile(user_id=u.id))
    else: db.add(EmployerProfile(user_id=u.id))
    token=token_urlsafe(32); db.add(EmailVerificationToken(user_id=u.id, token=token, expires_at=datetime.now(timezone.utc)+timedelta(hours=24)))
    await db.commit()
    return RegisterOut(user_id=u.id,email=u.email,role=u.role,verification_token=token,detail="Verification token returned for local development")

@router.post("/verify-email")
async def verify(data:VerifyIn, db:AsyncSession=Depends(get_db)):
    row=await db.scalar(select(EmailVerificationToken).where(EmailVerificationToken.token==data.token))
    if not row or row.used_at or row.expires_at < datetime.now(timezone.utc): raise HTTPException(400,"Invalid or expired token")
    u=await db.get(User,row.user_id); u.is_email_verified=True; row.used_at=datetime.now(timezone.utc); await db.commit()
    return {"verified":True}

@router.post("/login", response_model=TokenOut)
async def login(data:LoginIn, db:AsyncSession=Depends(get_db)):
    u=await db.scalar(select(User).where(User.email==data.email.lower()))
    if not u or not verify_password(data.password,u.password_hash): raise HTTPException(401,"Invalid credentials")
    if not u.is_email_verified: raise HTTPException(403,"Email is not verified")
    return TokenOut(access_token=create_access_token(str(u.id),u.role.value),refresh_token=create_refresh_token(str(u.id),u.role.value))

@router.get("/me")
async def me(u=Depends(current_user)): return {"id":u.id,"email":u.email,"role":u.role,"verified":u.is_email_verified}


@router.post("/refresh", response_model=TokenOut)
async def refresh(data: RefreshIn, db: AsyncSession = Depends(get_db)):
    try: payload = decode_token(data.refresh_token)
    except Exception: raise HTTPException(401, "Invalid refresh token")
    if payload.get("kind") != "refresh": raise HTTPException(401, "Refresh token required")
    u = await db.get(User, int(payload["sub"]))
    if not u: raise HTTPException(401, "User not found")
    return TokenOut(access_token=create_access_token(str(u.id),u.role.value),refresh_token=create_refresh_token(str(u.id),u.role.value))
