# Makefile for the V2Ray Scanner Ultimate project

# --- Variables ---
PYTHON = python3
VENV_DIR = .venv

# --- Targets ---

.PHONY: install
install:
	@echo "Creating virtual environment..."
	$(PYTHON) -m venv $(VENV_DIR)
	@echo "Installing dependencies..."
	$(VENV_DIR)/bin/pip install -r requirements.txt
	$(VENV_DIR)/bin/pip install -r requirements-dev.txt

.PHONY: test
test:
	@echo "Running tests..."
	SKIP_BINARY_CHECKS=1 $(VENV_DIR)/bin/pytest

.PHONY: run
run:
	@echo "Running the application..."
	$(VENV_DIR)/bin/python -m src.main

.PHONY: clean
clean:
	@echo "Cleaning up..."
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	rm -rf .pytest_cache

.PHONY: docker-build
docker-build:
	@echo "Building Docker image..."
	docker build -t v2ray-scanner-ultimate .

.PHONY: docker-run
docker-run:
	@echo "Running Docker container..."
	docker run -p 8080:8080 -p 9090:9090 v2ray-scanner-ultimate
