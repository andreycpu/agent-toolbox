# Agent Toolbox Development Makefile

.PHONY: help install install-dev test test-cov lint format clean build docs examples all

# Default target
all: install-dev test lint

# Help target
help:
	@echo "Available targets:"
	@echo "  install      - Install package in production mode"
	@echo "  install-dev  - Install package in development mode with dev dependencies"
	@echo "  test         - Run tests"
	@echo "  test-cov     - Run tests with coverage report"
	@echo "  lint         - Run linting (flake8)"
	@echo "  format       - Format code with black"
	@echo "  format-check - Check code formatting"
	@echo "  clean        - Clean up build artifacts"
	@echo "  build        - Build package"
	@echo "  docs         - Generate documentation"
	@echo "  examples     - Run example scripts"
	@echo "  all          - Install dev, test, and lint"

# Installation
install:
	pip install .

install-dev:
	pip install -e .[dev]
	pip install pytest pytest-cov black flake8 mypy

# Testing
test:
	pytest tests/ -v

test-cov:
	pytest tests/ --cov=agent_toolbox --cov-report=html --cov-report=term-missing -v

test-watch:
	pytest-watch -- tests/ -v

# Code quality
lint:
	flake8 agent_toolbox tests examples
	@echo "✓ Linting passed"

format:
	black agent_toolbox tests examples
	@echo "✓ Code formatted"

format-check:
	black --check --diff agent_toolbox tests examples

type-check:
	mypy agent_toolbox

# Cleanup
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

# Build
build: clean
	python -m build

build-check:
	twine check dist/*

# Documentation
docs:
	@echo "Documentation available in docs/ directory"
	@echo "  - docs/quickstart.md - Quick start guide"
	@echo "  - docs/api_reference.md - API reference"

# Examples
examples:
	@echo "Running basic usage example..."
	cd examples && python basic_usage.py
	@echo ""
	@echo "To run the advanced workflow example:"
	@echo "  cd examples && python agent_workflow.py"

# Development helpers
dev-setup: install-dev
	@echo "Development environment set up!"
	@echo "Try running: make test"

init-git-hooks:
	@echo "Setting up git hooks..."
	echo "#!/bin/sh\nmake format-check && make lint && make test" > .git/hooks/pre-commit
	chmod +x .git/hooks/pre-commit
	@echo "Pre-commit hook installed"

# Package management
upload-test:
	twine upload --repository testpypi dist/*

upload:
	twine upload dist/*

# Release helpers
version-patch:
	bump2version patch

version-minor:
	bump2version minor

version-major:
	bump2version major

release-prep: clean build build-check test-cov lint format-check
	@echo "Release preparation complete!"
	@echo "Ready to upload to PyPI"

# Utility
count-lines:
	@echo "Lines of code:"
	@find agent_toolbox -name "*.py" | xargs wc -l | tail -1
	@echo ""
	@echo "Lines of tests:"
	@find tests -name "*.py" | xargs wc -l | tail -1
	@echo ""
	@echo "Lines of documentation:"
	@find docs -name "*.md" | xargs wc -l | tail -1

todo:
	@echo "TODO items found:"
	@grep -r "TODO\|FIXME\|XXX" agent_toolbox tests examples || echo "No TODOs found!"

deps-update:
	pip-compile requirements.in
	pip-compile requirements-dev.in

# Git helpers
commit-count:
	@git rev-list --count HEAD

last-commit:
	@git log -1 --oneline