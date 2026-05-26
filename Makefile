SHELL := /bin/bash

APP_NAME ?= jackteamvn_bot
REPO_URL ?= https://github.com/hiepknor/jackteamvn_bot.git
BRANCH ?= master
APP_DIR ?= /opt/jackteamvn_bot/app
SSH_HOST ?= ubuntu@43.153.208.222

PYTHON ?= python3
PIP ?= .venv/bin/pip
DOCKER ?= docker
COMPOSE ?= $(DOCKER) compose

.DEFAULT_GOAL := help

.PHONY: help env install dirs check-env run test build up down restart ps logs prod-deploy deploy

help:
	@printf '%s\n' \
		'Targets:' \
		'  make env          Create .env from .env.example if missing' \
		'  make install      Create .venv and install Python dependencies' \
		'  make run          Run the bot locally' \
		'  make test         Run tests' \
		'  make build        Build Docker image via Compose' \
		'  make up           Start Docker Compose stack' \
		'  make down         Stop Docker Compose stack' \
		'  make restart      Restart Docker Compose stack' \
		'  make ps           Show Docker Compose status' \
		'  make logs         Follow bot logs' \
		'  make deploy       Deploy current origin/$(BRANCH) to $(SSH_HOST)' \
		'' \
		'Variables:' \
		'  BRANCH=$(BRANCH)' \
		'  SSH_HOST=$(SSH_HOST)' \
		'  APP_DIR=$(APP_DIR)'

env:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo 'Created .env. Set TELEGRAM_BOT_TOKEN before running the bot.'; \
	else \
		echo '.env already exists.'; \
	fi

install:
	$(PYTHON) -m venv .venv
	$(PIP) install -r requirements.txt

dirs:
	mkdir -p data logs exports storage

check-env:
	@test -f .env || { echo 'Missing .env. Run: make env'; exit 1; }
	@grep -Eq '^TELEGRAM_BOT_TOKEN=.+$$' .env \
		&& ! grep -q '^TELEGRAM_BOT_TOKEN=your_bot_token_here$$' .env \
		|| { echo 'TELEGRAM_BOT_TOKEN in .env is missing or invalid.'; exit 1; }

run: check-env dirs
	$(PYTHON) bot.py

test:
	pytest -q

build:
	$(COMPOSE) build

up: check-env dirs
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down --remove-orphans

restart: down up

ps:
	$(COMPOSE) ps

logs:
	$(COMPOSE) logs -f jackteamvn_bot

prod-deploy: check-env dirs
	git fetch origin $(BRANCH)
	git checkout $(BRANCH)
	git reset --hard origin/$(BRANCH)
	$(COMPOSE) down --remove-orphans || true
	$(COMPOSE) up -d --build
	$(COMPOSE) ps
	$(COMPOSE) logs --tail=50 jackteamvn_bot

deploy:
	ssh $(SSH_HOST) 'set -e; \
		sudo mkdir -p "$(dir $(APP_DIR))"; \
		sudo chown -R "$$(id -un):$$(id -gn)" "$(dir $(APP_DIR))"; \
		if [ ! -d "$(APP_DIR)/.git" ]; then \
			rm -rf "$(APP_DIR)"; \
			git clone -b "$(BRANCH)" "$(REPO_URL)" "$(APP_DIR)"; \
		fi; \
		cd "$(APP_DIR)"; \
		git fetch origin "$(BRANCH)"; \
		git checkout "$(BRANCH)"; \
		git reset --hard "origin/$(BRANCH)"; \
		if [ ! -f .env ]; then \
			cp .env.example .env; \
			echo "Created $(APP_DIR)/.env. Set TELEGRAM_BOT_TOKEN, then run: make -C $(APP_DIR) prod-deploy DOCKER=\"sudo docker\""; \
			exit 1; \
		fi; \
		make prod-deploy DOCKER="sudo docker"'
