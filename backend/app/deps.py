from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.models import User, UserRole
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)

async def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: AsyncSession = Depends(get_db)) -> User:
    if not creds: raise HTTPException(status_code=401, detail="Authentication required")
    try: payload = decode_token(creds.credentials)
    except Exception: raise HTTPException(status_code=401, detail="Invalid token")
    if payload.get("kind") != "access": raise HTTPException(status_code=401, detail="Access token required")
    user = await db.scalar(select(User).where(User.id == int(payload["sub"])))
    if not user: raise HTTPException(status_code=401, detail="User not found")
    return user

def require_role(role: UserRole):
    async def dep(user: User = Depends(current_user)):
        if user.role != role: raise HTTPException(status_code=403, detail="Wrong role")
        return user
    return dep
