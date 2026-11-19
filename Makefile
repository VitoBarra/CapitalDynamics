.DEFAULT_GOAL := run

# Optional local settings, using Makefile-style KEY=value assignments.
-include .env.local
export

PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python
APP ?= app.py
PORT ?= 8501
HOST ?= localhost
HEADLESS ?= false
STREAMLIT_ARGS ?=

.PHONY: run install test help init-env

run: install ## Install dependencies and launch the app
	"$(VENV_PYTHON)" -m streamlit run "$(APP)" --server.port="$(PORT)" --server.address="$(HOST)" --server.headless="$(HEADLESS)" $(STREAMLIT_ARGS)

init-env: ## Create .env.local with defaults without overwriting existing settings
	@if [ -e .env.local ]; then \
		echo ".env.local already exists; leaving it unchanged."; \
	else \
		printf '%s\n' \
			'# Local launch settings (Makefile syntax; do not quote values).' \
			'PYTHON=python3' \
			'VENV=.venv' \
			'APP=app.py' \
			'PORT=8501' \
			'HOST=localhost' \
			'HEADLESS=false' \
			'STREAMLIT_ARGS=' > .env.local; \
		echo "Created .env.local with default settings. Edit it to customize your launch."; \
	fi

install: $(VENV)/.installed ## Set up the virtual environment and dependencies

$(VENV)/.installed: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@touch $@

test: install ## Run model and interface checks
	$(VENV_PYTHON) -m unittest discover -s tests -v

help: ## Show this help message
	@echo ""
	@echo "================================================================================"
	@echo "  Capital Dynamics — Makefile targets"
	@echo "================================================================================"
	@echo ""
	@echo "  ENVIRONMENT:"
	@grep -E '^(help|init-env|install):.*##' Makefile | \
		awk -F ':.*## ' '{printf "    \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "  APPLICATION:"
	@grep -E '^(run|test):.*##' Makefile | \
		awk -F ':.*## ' '{printf "    \033[36m%-30s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "================================================================================"
	@echo ""
