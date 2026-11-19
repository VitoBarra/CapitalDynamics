.DEFAULT_GOAL := run

# Optional local settings, using Makefile-style KEY=value assignments.
-include .env.local

IMAGE ?= capital-dynamics
PORT ?= 8501

.PHONY: build run test help

build: ## Build the Docker image
	docker build -t "$(IMAGE)" .

run: build ## Build and start the dashboard
	docker run --rm -p "$(PORT):8501" "$(IMAGE)"

test: build ## Run the regression suite in Docker
	docker run --rm --entrypoint python -v "$(CURDIR)/tests:/app/tests:ro" "$(IMAGE)" -m unittest discover -s tests -v

help: ## Show available commands
	@echo "make build  - Build the Docker image"
	@echo "make run    - Build and run the dashboard (PORT=8501)"
	@echo "make test   - Run tests in Docker"
	@echo "Override settings with, for example, make run PORT=8502"
