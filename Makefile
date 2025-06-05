.PHONY: run install clean reload test

# Default Python interpreter
PYTHON = python3

# Uvicorn settings
HOST = 0.0.0.0
PORT = 8000
APP = dermaAssistant:app
RELOAD = --reload

# Install dependencies
install:
	uv sync

# Run the application with hot reload for development
run:
	uvicorn $(APP) --host $(HOST) --port $(PORT) $(RELOAD)

# Run without reload for production
run-prod:
	uvicorn $(APP) --host $(HOST) --port $(PORT)

# Clean up Python cache files
clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	find . -type f -name "*.pyd" -delete
	rm -rf .uv

# Run tests
test:
	pytest

# Default target
.DEFAULT_GOAL := run
