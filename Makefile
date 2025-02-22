.PHONY: help install dev-install test format lint type-check clean build run

help:  ## Show this help menu
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

install:  ## Install production dependencies
	uv pip install .

dev-install:  ## Install development dependencies
	uv pip install -e ".[dev]"

test:  ## Run tests with pytest
	pytest -v --cov=src --cov-report=term-missing

format:  ## Format code with black and isort
	black .
	isort .

lint:  ## Lint code with ruff
	ruff check .

type-check:  ## Run type checking with mypy
	mypy src tests

clean:  ## Clean build artifacts
	rm -rf build/ dist/ *.egg-info/ .coverage .pytest_cache/ .mypy_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +

build:  ## Build Docker image
	docker build -t template-python .

run:  ## Run Docker container
	docker run -it --rm template-python

package:  ## Create requirements.txt
	uv pip freeze > requirements.txt

setup:  ## Initial project setup
	uv venv
	$(MAKE) dev-install
	cp .env.example .env