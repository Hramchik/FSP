from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, profiles, health, testing

app = FastAPI(
    title=settings.app_name,
    version="0.2.0-day2",
    description="FSP reverse hiring platform — Day 2 testing, IRT and CAT",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(profiles.router, prefix="/api/v1")
app.include_router(testing.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": settings.app_name, "docs": "/docs", "day": "2"}
