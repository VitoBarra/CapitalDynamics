PYTHON ?= python3
VENV ?= .venv
VENV_PYTHON := $(VENV)/bin/python

.PHONY: run install test help

run: install
	$(VENV_PYTHON) -m streamlit run app.py

install: $(VENV)/.installed

$(VENV)/.installed: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(VENV_PYTHON) -m pip install -r requirements.txt
	@touch $@

test: install
	$(VENV_PYTHON) -m unittest discover -s tests -v

help:
	@printf 'make run      Install dependencies and launch the app\nmake install  Set up the virtual environment and dependencies\nmake test     Run model and interface checks\n'
