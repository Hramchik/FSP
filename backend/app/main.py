from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api import auth, profiles, health, testing, needs, search, invitations, vacancies, spot_tasks

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    description=(
        "Платформа обратного найма ИТ-специалистов ФСП: категоризация кандидатов "
        "через адаптивное тестирование, подбор по потребности работодателя "
        "и выход на контакт по приглашению."
    ),
    openapi_tags=[
        {"name": "auth", "description": "Регистрация, подтверждение e-mail, JWT."},
        {"name": "profiles", "description": "Профили, резюме, ФСП ID, справочники."},
        {"name": "testing", "description": "Опрос, адаптивный тест, присвоение категории."},
        {"name": "needs", "description": "Потребности работодателя и подборки кандидатов."},
        {"name": "search", "description": "Поиск по банку кандидатов."},
        {"name": "invitations", "description": "Приглашения и раскрытие контактов."},
        {"name": "vacancies", "description": "Вакансии и отклики."},
        {"name": "spot-tasks", "description": "Регулярные короткие задания."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:5173", "http://localhost:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

for router in (health, auth, profiles, testing, needs, search, invitations, vacancies, spot_tasks):
    app.include_router(router.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {"name": settings.app_name, "docs": "/docs", "version": app.version}
