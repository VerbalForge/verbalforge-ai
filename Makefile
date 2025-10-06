# Makefile for VerbalForge Server
SHELL := /bin/bash
.PHONY: help install clean clean-db test lint format run dev

# Default target
help:
	@echo "VerbalForge Question Generation Server"
	@echo "======================================"
	@echo ""
	@echo "Available commands:"
	@echo "  install    Install package and dependencies"
	@echo "  run        Run server (production mode)"
	@echo "  dev        Run server (development mode)"
	@echo "  clean      Clean build artifacts and cache"
	@echo "  clean-db   Wipe MongoDB database (WARNING: deletes all data!)"
	@echo "  test       Run all tests"
	@echo "  lint       Run code linting"
	@echo "  format     Format code with black"

# Installation
install:
	@echo "Installing VerbalForge Server..."
	pip install -e .
	pip install pytest pytest-asyncio black flake8
	@echo "Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Configure .env with MongoDB and API credentials"
	@echo "  2. Run 'make dev' to start development server"

# Run server
run:
	@echo "Starting VerbalForge Server..."
	./scripts/start_server.sh

dev:
	@echo "Starting VerbalForge Server (development mode)..."
	@cd src && PYTHONPATH=. ../.venv/bin/python -m server.main

# Clean up
clean:
	@echo "Cleaning up..."
	rm -rf build/ dist/ *.egg-info/
	rm -rf .pytest_cache/ htmlcov/ .coverage
	rm -rf __pycache__/ */__pycache__/ */*/__pycache__/ */*/*/__pycache__/ 
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	@echo "Cleanup complete!"

# Clean MongoDB database
clean-db:
	@python3 scripts/clean_db.py

lint:
	@echo "Running code linting..."
	python -m flake8 src --max-line-length=100

format:
	@echo "Formatting code..."
	python -m black src --line-length=100
