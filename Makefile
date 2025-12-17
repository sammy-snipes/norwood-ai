# Makefile for norwood-ai

SHELL := /bin/bash

# Variables
REDIS_CONTAINER_NAME = norwood-redis

# Default target
.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo "Norwood AI Makefile"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "---------------- One-Time Setup -----------------"
	@echo "  install           Install Python and frontend dependencies"
	@echo "  setup-services    Pull Redis image and create container (run once)"
	@echo ""
	@echo "---------------- Code Quality -----------------"
	@echo "  format            Format code with black and ruff"
	@echo "  lint              Check code with ruff"
	@echo "  check             Run format check + lint (no changes)"
	@echo ""
	@echo "---------------- Build -----------------"
	@echo "  build-frontend    Build Vue frontend for production"
	@echo ""
	@echo "---------------- Service Management -----------------"
	@echo "  ensure-redis      Ensure Redis container is running (starts if stopped)"
	@echo "  stop-redis        Stop Redis container"
	@echo "  services-status   Check status of Redis container"
	@echo ""
	@echo "---------------- Database -----------------"
	@echo "  migrate           Run all SQL migrations"
	@echo ""
	@echo "---------------- Run Application -----------------"
	@echo "  run-app           Build frontend + run FastAPI (port 8000)"
	@echo "  run-celery        Run Celery worker (ensures Redis is running)"
	@echo "  run-frontend      Run Vue dev server (port 5173) - for frontend development"
	@echo ""

# ==============================================================================
# Installation
# ==============================================================================
.PHONY: install
install:
	@echo "Installing Python dependencies..."
	uv sync --extra dev
	@echo "Installing frontend dependencies..."
	cd frontend && npm install
	@echo "Installation complete."

# ==============================================================================
# Code Quality
# ==============================================================================
.PHONY: format
format:
	@echo "Formatting code with black and ruff..."
	uv run black app tests
	uv run ruff check --fix app tests
	@echo "Formatting complete."

.PHONY: lint
lint:
	@echo "Linting code with ruff..."
	uv run ruff check app tests
	@echo "Lint complete."

.PHONY: check
check:
	@echo "Checking code formatting and linting..."
	uv run black --check app tests
	uv run ruff check app tests
	@echo "All checks passed."

# ==============================================================================
# Build
# ==============================================================================
.PHONY: build-frontend
build-frontend:
	@echo "Building Vue frontend..."
	cd frontend && npm run build
	@echo "Frontend built to frontend/dist/"

# ==============================================================================
# Service Management (Redis)
# ==============================================================================
.PHONY: setup-services
setup-services:
	@echo "Pulling Redis image and creating container..."
	docker pull redis:latest
	@if docker ps -a -f name=$(REDIS_CONTAINER_NAME) --format "{{.Names}}" | grep -qw $(REDIS_CONTAINER_NAME); then \
		echo "Redis container already exists."; \
	else \
		echo "Creating Redis container..."; \
		docker run --name $(REDIS_CONTAINER_NAME) -d -p 6379:6379 redis:latest; \
	fi
	@echo "Redis setup complete."

.PHONY: ensure-redis
ensure-redis:
	@echo "Ensuring Redis container ($(REDIS_CONTAINER_NAME)) is running..."
	@if docker ps -f name=$(REDIS_CONTAINER_NAME) --format "{{.Names}}" | grep -qw $(REDIS_CONTAINER_NAME); then \
		echo "Redis container is already running."; \
	elif docker ps -a -f name=$(REDIS_CONTAINER_NAME) --format "{{.Names}}" | grep -qw $(REDIS_CONTAINER_NAME); then \
		echo "Redis container exists but is stopped. Starting it..."; \
		docker start $(REDIS_CONTAINER_NAME); \
		sleep 2; \
	else \
		echo "Redis container not found. Run 'make setup-services' first."; \
		exit 1; \
	fi

.PHONY: stop-redis
stop-redis:
	@echo "Stopping Redis container..."
	-docker stop $(REDIS_CONTAINER_NAME) > /dev/null 2>&1 || true
	@echo "Redis stopped."

.PHONY: services-status
services-status:
	@echo "Redis container status:"
	@docker ps -a -f name=$(REDIS_CONTAINER_NAME)

# ==============================================================================
# Database
# ==============================================================================
.PHONY: migrate
migrate:
	@echo "Running migrations..."
	@for file in $$(ls -1 migrations/*.sql | sort); do \
		echo "Applying $$file..."; \
		psql "$$DATABASE_URL" -f "$$file"; \
	done
	@echo "Migrations complete."

# ==============================================================================
# Run Application
# ==============================================================================
.PHONY: run-app
run-app: build-frontend
	@echo "Starting FastAPI backend with built frontend on port 8000..."
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: run-dev
run-dev:
	@echo "Starting frontend (5173) + backend (8000) with hot reload..."
	@trap 'kill 0' EXIT; \
	cd frontend && npm run dev & \
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
	wait

.PHONY: run-celery
run-celery: ensure-redis
	@echo "Starting Celery worker..."
	uv run celery -A app.celery_worker.celery_app worker --loglevel=info --concurrency=2

.PHONY: run-celery-beat
run-celery-beat: ensure-redis
	@echo "Starting Celery Beat scheduler..."
	uv run celery -A app.celery_worker.celery_app beat --loglevel=info

.PHONY: run-frontend
run-frontend:
	@echo "Starting Vue frontend dev server (for development with hot reload)..."
	cd frontend && npm run dev
