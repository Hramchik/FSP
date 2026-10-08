# FSP Career Platform — Day 2

Рабочая версия цифровой платформы обратного найма IT-специалистов по внутреннему SPEC команды и исходному ТЗ ФСП. Day 2 добавляет механику тестирования с IRT 2PL, CAT и присвоением категории.

## Что готово в Day 1 + Day 2

- FastAPI-монолит со слоями `api / core / db / models / schemas / services`.
- PostgreSQL + Alembic initial migration.
- Роли `candidate` / `employer`, разграничение доступа.
- Регистрация, dev-поток подтверждения e-mail, JWT access/refresh, `GET /auth/me`.
- Профили кандидата и работодателя.
- Справочник 6 специализаций × 4 грейда = 24 категории.
- Каркас сущностей ФСП, потребностей, подборок, приглашений и контактов для следующих дней.
- 720 активных шаблонов: 30 на каждую из 24 категорий, по 5 разным семействам заданий × 6 вариантов.
- Детерминированные русскоязычные генераторы заданий `(template, seed)` с пространством параметров ≥ 10⁴ и проверкой энтропии ответов.
- IRT 2PL: оценка θ/SE и выбор следующего задания по информации Фишера.
- CAT: минимум 8, стандартный максимум 15, остановка при SE < 0.3; при SE > 0.45 допускаются ещё 5 заданий.
- Опрос отрасли/специализации/грейда и присвоение категории после теста; состояние грейда и 90-дневный cooldown хранятся отдельно для каждой специализации кандидата, поэтому один аккаунт может пройти тесты по нескольким направлениям.
- Защита эталона: ответ пересчитывается на сервере и не хранится в БД.
- Оффлайн-скрипты калибровки `a/b` и test–retest на 200 кандидатах.
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

## Границы Day 2

Рабочая механика подбора, shortlist, приглашений и раскрытия контактов остаётся задачей Day 3. Keycloak и FSP ID на Day 2 представлены подготовленной архитектурой и локальными заглушками.

## Архитектурное правило

Верхние слои знают о нижних, нижние о верхних — никогда. Domain-механики следующих дней должны оставаться чистыми функциями без зависимости от БД/FastAPI.

## Day 2 validation

`python scripts/validate_day2.py` runs the CAT simulation on the 200 synthetic candidates. Current reproducible result: test–retest `r=0.941`, θ RMSE `0.306`, grade agreement `0.810`, mean test length `8.6` items. All three Day 2 target thresholds from SPEC are met.

`python scripts/calibrate_items.py` performs reproducible offline calibration on representative template families and writes `data/validation/item_calibration.json`.
