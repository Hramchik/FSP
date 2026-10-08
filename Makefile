.PHONY: up down logs validate seed generate validate-day2 test
up:
	docker compose up --build
up-d:
	docker compose up -d --build
seed:
	docker compose exec api python scripts/seed.py
generate:
	python3 backend/scripts/generate_validation_data.py
validate-day2:
	docker compose exec api python scripts/validate_day2.py
	docker compose exec api python scripts/calibrate_items.py
test:
	docker compose exec api pytest -q
validate: generate validate-day2 test
down:
	docker compose down
logs:
	docker compose logs -f
