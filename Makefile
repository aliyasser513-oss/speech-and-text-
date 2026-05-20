# Speech & Text Analyzer — development Makefile

SHELL := /bin/bash
ROOT  := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

PYTHON     ?= python3
VENV       := $(ROOT).venv
VENV_BIN   := $(VENV)/bin
PY         := $(VENV_BIN)/python
PIP        := $(VENV_BIN)/pip

MOBILE_DIR := $(ROOT)mobile
NPM        ?= npm

.PHONY: help install install-python install-npm \
        api gui cli analyzer mobile dev clean

.DEFAULT_GOAL := help

help: ## Show available targets
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

install: install-python install-npm ## Install Python (venv) and mobile (npm) dependencies

install-python: $(VENV_BIN)/python ## Create .venv and pip install requirements.txt

$(VENV_BIN)/python: $(ROOT)requirements.txt
	@test -d $(VENV) || $(PYTHON) -m venv $(VENV)
	$(PIP) install -U pip
	$(PIP) install -r $(ROOT)requirements.txt

install-npm: ## npm ci in mobile/ (uses package-lock.json)
	cd $(MOBILE_DIR) && $(NPM) ci

# ---------------------------------------------------------------------------
# Run (one process per target)
# ---------------------------------------------------------------------------

api: $(VENV_BIN)/python ## Flask REST API on :5000
	$(PY) $(ROOT)api.py

gui: $(VENV_BIN)/python ## Desktop Tkinter UI
	$(PY) $(ROOT)gui.py

cli: $(VENV_BIN)/python ## Interactive CLI (analyzer.py)
	$(PY) $(ROOT)analyzer.py

analyzer: cli ## Alias for cli

mobile: install-npm ## Expo dev server (scan QR with Expo Go)
	cd $(MOBILE_DIR) && npx expo start

# ---------------------------------------------------------------------------
# Dev — API + mobile together
# ---------------------------------------------------------------------------

dev: install ## Run API and Expo in parallel (Ctrl+C stops both)
	@echo "Starting API (http://0.0.0.0:5000) and Expo …"
	@echo "Set mobile/App.js API_BASE to the IP printed by the API."
	@trap 'kill 0' INT TERM EXIT; \
		$(PY) $(ROOT)api.py & \
		cd $(MOBILE_DIR) && npx expo start & \
		wait

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean: ## Remove Python cache files
	find $(ROOT) -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
