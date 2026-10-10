.PHONY: up up-d down logs seed test generate validate-day2 validate-match validate
up:
	docker compose up --build
up-d:
	docker compose up -d --build
down:
	docker compose down
logs:
	docker compose logs -f
seed:
	docker compose exec api python scripts/seed.py
test:
	docker compose exec api pytest -q
generate:
	python3 backend/scripts/generate_validation_data.py
validate-day2:
	docker compose exec api python scripts/validate_day2.py
	docker compose exec api python scripts/calibrate_items.py
validate-match:
	docker compose exec api python scripts/validate_matching.py
validate: generate validate-day2 validate-match test
