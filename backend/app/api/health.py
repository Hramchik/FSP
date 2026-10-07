from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
router=APIRouter(tags=["system"])
@router.get("/health")
async def health(db:AsyncSession=Depends(get_db)):
    await db.execute(text("select 1")); return {"status":"ok"}
