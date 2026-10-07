.PHONY: up down logs validate seed generate
up:
	docker compose up --build
up-d:
	docker compose up -d --build
seed:
	docker compose exec api python scripts/seed.py
generate:
	python3 backend/scripts/generate_validation_data.py
validate:
	python3 backend/scripts/generate_validation_data.py
	python3 -m compileall -q backend/app backend/scripts

down:
	docker compose down
logs:
	docker compose logs -f
