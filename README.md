# FSP Career Platform — Day 1

Рабочий каркас цифровой платформы обратного найма IT-специалистов по внутреннему SPEC команды и исходному ТЗ ФСП.

## Что готово в Day 1

- FastAPI-монолит со слоями `api / core / db / models / schemas / services`.
- PostgreSQL + Alembic initial migration.
- Роли `candidate` / `employer`, разграничение доступа.
- Регистрация, dev-поток подтверждения e-mail, JWT access/refresh, `GET /auth/me`.
- Профили кандидата и работодателя.
- Справочник 6 специализаций × 4 грейда = 24 категории.
- Каркас сущностей тестирования, ФСП, потребностей, подборок, приглашений и контактов для следующих дней.
- React/Vite фронтенд: стартовый экран, два кабинета, роутинг и тема.
- Docker Compose: `db`, `api`, `web`, `keycloak`.
- OpenAPI доступен на `http://localhost:8000/docs`.
- Генератор валидационных данных: 200 кандидатов, 30 потребностей и разметка пар.

## Запуск

Требуется Docker Desktop / Docker Engine с Compose.

```bash
docker compose up --build
```

После запуска:

- Web: http://localhost:5173
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Keycloak: http://localhost:8080

Демо-аккаунты после seed:

- candidate: `demo.candidate@fsp.local` / `DemoPass123!`
- employer: `demo.employer@fsp.local` / `DemoPass123!`

Для локальной разработки endpoint регистрации возвращает verification token, чтобы не требовать SMTP. В production этот ответ заменяется почтовым адаптером.

## Валидационные данные

```bash
python3 backend/scripts/generate_validation_data.py
```

Получаются:

- `data/synthetic/candidates.json` — 200 кандидатов с истинной θ, специализацией, стеком и признаком ФСП;
- `data/synthetic/vacancies.json` — 30 описаний потребностей;
- `data/labels/relevance_labels.csv` — до 20 кандидатов на потребность, два независимых оценивания и adjudicated label.

Фиксированный seed: `20261006`, поэтому генерация воспроизводима.

## Границы Day 1

IRT/CAT, генераторы заданий, калибровка, scoring, shortlist и приглашения как рабочая бизнес-механика намеренно не реализуются раньше соответствующих дней. Сущности и API-границы для них заложены в миграции, чтобы следующие этапы не ломали схему.

## Архитектурное правило

Верхние слои знают о нижних, нижние о верхних — никогда. Domain-механики следующих дней должны оставаться чистыми функциями без зависимости от БД/FastAPI.
