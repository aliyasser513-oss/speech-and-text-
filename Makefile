# Speech & Text Analyzer — development Makefile
# Works on Linux, macOS, and Windows (Git Bash / MSYS / cmd via GNU Make).

ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

# --- OS detection (Windows_NT is set on native Windows and Git Bash) ---
ifeq ($(OS),Windows_NT)
  IS_WIN        := 1
  VENV_BIN      := $(ROOT).venv/Scripts
  PY            := "$(VENV_BIN)/python.exe"
  PIP           := "$(VENV_BIN)/pip.exe"
  PYTHON        ?= python
  NPM           ?= npm.cmd
  NPX           ?= npx.cmd
  RUN_SCRIPT    = $(PY) "$(ROOT)scripts/$(1)"
  CD_MOBILE     = cd /d "$(MOBILE_DIR)"
else
  IS_WIN        :=
  VENV_BIN      := $(ROOT).venv/bin
  PY            := $(VENV_BIN)/python
  PIP           := $(VENV_BIN)/pip
  PYTHON        ?= python3
  NPM           ?= npm
  NPX           ?= npx
  RUN_SCRIPT    = $(PY) $(ROOT)scripts/$(1)
  CD_MOBILE     = cd "$(MOBILE_DIR)"
endif

VENV         := $(ROOT).venv
MOBILE_DIR   := $(ROOT)mobile
VENV_STAMP   := $(VENV_BIN)/python$(if $(IS_WIN),.exe,)

.PHONY: help install install-python install-npm \
        api gui cli analyzer mobile dev clean \
        test test-setup test-api check-ollama

.DEFAULT_GOAL := help

help: ## Show available targets
ifeq ($(IS_WIN),1)
	@$(PYTHON) -c "import re,pathlib; [print(f'  {m.group(1):18} {m.group(2)}') for m in re.finditer(r'^([a-zA-Z0-9_-]+):.*?## (.*)$$', pathlib.Path(r'$(ROOT)Makefile').read_text(encoding='utf-8'), re.M)]"
else
	@grep -E '^[a-zA-Z0-9_-]+:.*##' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
endif

# ---------------------------------------------------------------------------
# Install
# ---------------------------------------------------------------------------

install: install-python install-npm ## Install Python (venv) and mobile (npm) dependencies

install-python: $(VENV_STAMP) ## Create .venv and pip install requirements.txt

$(VENV_STAMP): $(ROOT)requirements.txt
ifeq ($(IS_WIN),1)
	@if not exist "$(VENV)" "$(PYTHON)" -m venv "$(VENV)"
	$(PIP) install -U pip
	$(PIP) install -r "$(ROOT)requirements.txt"
else
	@test -d "$(VENV)" || $(PYTHON) -m venv "$(VENV)"
	$(PIP) install -U pip
	$(PIP) install -r "$(ROOT)requirements.txt"
endif

install-npm: ## npm ci in mobile/ (uses package-lock.json)
	$(CD_MOBILE) && $(NPM) ci

# ---------------------------------------------------------------------------
# Run (one process per target)
# ---------------------------------------------------------------------------

api: $(VENV_STAMP) ## Flask REST API on :5000 (debug + INFO request logs)
	$(PY) "$(ROOT)api.py"

gui: $(VENV_STAMP) ## Desktop Tkinter UI
	$(PY) "$(ROOT)gui.py"

cli: $(VENV_STAMP) ## Interactive CLI (analyzer.py)
	$(PY) "$(ROOT)analyzer.py"

analyzer: cli ## Alias for cli

mobile: install-npm ## Expo dev server on LAN (scan QR with Expo Go)
	$(CD_MOBILE) && $(NPX) expo start --lan

# ---------------------------------------------------------------------------
# Dev — API + mobile together
# ---------------------------------------------------------------------------

dev: install ## Run API and Expo in parallel (Ctrl+C stops both)
	$(call RUN_SCRIPT,dev.py)

# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

test: $(VENV_STAMP) test-setup ## Pytest + mobile layout checks (no API server)
	$(PIP) install -q -r "$(ROOT)requirements-dev.txt"
	$(PY) -m pytest "$(ROOT)tests/" -q

test-setup: ## Verify mobile + project layout (Python, no venv required)
	$(PYTHON) "$(ROOT)scripts/check_mobile.py"

test-api: ## Live API smoke test (requires: make api in another terminal)
	$(PYTHON) "$(ROOT)scripts/test_api_live.py"

check-ollama: $(VENV_STAMP) ## Probe whether Ollama is running and llama3 is available
	$(PY) -c "from ollama_util import check_ollama; from analyzer import Config; ok=check_ollama(Config.LLM_MODEL); print('ollama:', 'ok' if ok else 'down'); raise SystemExit(0 if ok else 1)"

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------

clean: ## Remove Python __pycache__ directories
ifeq ($(IS_WIN),1)
	@if exist "$(VENV_STAMP)" $(PY) "$(ROOT)scripts/clean_pycache.py"
else
	@$(if $(wildcard $(VENV_STAMP)),$(PY) $(ROOT)scripts/clean_pycache.py,):
endif
