.PHONY: install dev infra-up storage-up infra-down build test lint

install:
	pnpm install
	cd services/commerce-api && ./mvnw dependency:go-offline
	python3 -m pip install -e 'services/ai-service[dev]'

dev:
	pnpm dev

infra-up:
	docker compose up -d postgres redis rabbitmq

storage-up:
	docker compose --profile storage up -d minio

infra-down:
	docker compose down

build:
	pnpm build
	cd services/commerce-api && ./mvnw verify

test:
	cd services/commerce-api && ./mvnw test
	python3 -m pytest services/ai-service

lint:
	pnpm lint
	python3 -m ruff check services/ai-service
	python3 -m mypy services/ai-service/src
