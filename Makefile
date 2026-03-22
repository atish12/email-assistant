.PHONY: build up down logs restart clean

## First-time setup: copy .env.example → .env, then fill in your API key
setup:
	cp .env.example .env
	@echo "Edit .env and add your ANTHROPIC_API_KEY"

## Build the Docker image
build:
	docker compose build

## Build (if needed) and start in the foreground
up:
	docker compose up --build

## Start in the background
start:
	docker compose up -d --build

## Stop containers (keeps data volume)
down:
	docker compose down

## Tail logs
logs:
	docker compose logs -f

## Restart the app
restart:
	docker compose restart

## Stop and delete everything including persistent data
clean:
	docker compose down -v --rmi local
