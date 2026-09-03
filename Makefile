SHELL := /usr/bin/env bash

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
INSTALL_STAMP := $(VENV)/.vibe-installed
DEV_STAMP := $(VENV)/.vibe-dev-installed

.DEFAULT_GOAL := help

.PHONY: help install install-dev ubuntu-install run samples test lint check build \
	test-ubuntu screenshot-ubuntu docs clean

help:
	@echo "Vibe Viewer"
	@echo ""
	@echo "  make install         создать .venv и установить программу"
	@echo "  make run             запустить программу"
	@echo "  make build           собрать wheel в папку dist/"
	@echo "  make test            запустить тесты"
	@echo "  make check           тесты и проверка стиля"
	@echo "  make test-ubuntu     проверить в Ubuntu через Docker/OrbStack"
	@echo "  make screenshot-ubuntu сохранить снимок Ubuntu-интерфейса в work/"
	@echo "  make ubuntu-install  установить системные пакеты и программу в Ubuntu"
	@echo "  make samples         создать демонстрационные файлы"
	@echo "  make docs            собрать документацию Doxygen"

$(VENV_PYTHON):
	$(PYTHON) -m venv $(VENV)

$(INSTALL_STAMP): $(VENV_PYTHON) requirements.txt pyproject.toml
	$(VENV_PYTHON) -m pip install --upgrade pip setuptools wheel
	$(VENV_PYTHON) -m pip install -r requirements.txt
	$(VENV_PYTHON) -m pip install --no-build-isolation --no-deps -e .
	@touch $(INSTALL_STAMP)

install: $(INSTALL_STAMP)

$(DEV_STAMP): $(INSTALL_STAMP) requirements-dev.txt
	$(VENV_PYTHON) -m pip install -r requirements-dev.txt
	@touch $(DEV_STAMP)

install-dev: $(DEV_STAMP)

ubuntu-install:
	./scripts/install_ubuntu.sh

run: install
	$(VENV)/bin/vibe-viewer

samples: install
	$(VENV_PYTHON) scripts/generate_samples.py

test: install-dev
	QT_QPA_PLATFORM=offscreen $(VENV_PYTHON) -m pytest -q

lint: install-dev
	$(VENV_PYTHON) -m ruff check src tests scripts

check: test lint

build: install
	@mkdir -p dist
	$(VENV_PYTHON) -m pip wheel --no-build-isolation --no-deps --wheel-dir dist .

test-ubuntu:
	docker compose build tests
	docker compose run --rm tests
	docker compose run --rm gui-smoke

screenshot-ubuntu:
	@mkdir -p work
	docker compose build gui-capture
	docker compose run --rm gui-capture

docs:
	@command -v doxygen >/dev/null || { echo "Установите Doxygen и повторите make docs"; exit 1; }
	doxygen Doxyfile

clean:
	rm -rf build dist .pytest_cache .ruff_cache docs/html
	find src tests scripts -type d -name __pycache__ -prune -exec rm -rf {} +
