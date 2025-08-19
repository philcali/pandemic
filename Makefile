.PHONY: install install-dev test test-cov lint format clean build

# Install all packages in development mode
install:
	pip3 install -e packages/pandemic-common
	pip3 install -e packages/pandemic-core
	pip3 install -e packages/pandemic-cli
	pip3 install -e packages/pandemic-iam
	pip3 install -e packages/pandemic-rest
	pip3 install -e packages/pandemic-console
	pip3 install -e .

# Install with development dependencies
install-dev: install
	pip3 install -e "packages/pandemic-common[dev,test]"
	pip3 install -e "packages/pandemic-core[dev,test]"
	pip3 install -e "packages/pandemic-cli[dev,test]"
	pip3 install -e "packages/pandemic-iam[dev,test]"
	pip3 install -e "packages/pandemic-rest[dev,test]"
	pip3 install -e "packages/pandemic-console[dev,test]"
	pip3 install -e ".[dev,test]"

# Run tests for all packages
test:
	pytest

# Run tests with coverage for all packages
test-cov:
	pytest --cov=packages/pandemic-core/src/pandemic_core \
	       --cov=packages/pandemic-cli/src/pandemic_cli \
	       --cov=packages/pandemic-common/src/pandemic_common \
	       --cov=packages/pandemic-iam/src/pandemic_iam \
	       --cov=packages/pandemic-rest/src/pandemic_rest \
	       --cov=packages/pandemic-console/src/pandemic_console \
	       --cov-report=term-missing --cov-report=html

# Test specific package
test-core:
	cd packages/pandemic-core && pytest

test-cli:
	cd packages/pandemic-cli && pytest

test-common:
	cd packages/pandemic-common && pytest

test-iam:
	cd packages/pandemic-iam && pytest

test-rest:
	cd packages/pandemic-rest && pytest

test-console:
	cd packages/pandemic-console && pytest

# Format all code
format:
	@echo "🎨 Formatting code with black..."
	black --extend-exclude node_modules packages/*/src packages/*/tests
	@echo "📦 Sorting imports with isort..."
	isort packages/*/src packages/*/tests
	@echo "✅ Formatting complete!"

# Check formatting without making changes
format-check:
	@echo "🔍 Checking code formatting..."
	black --check --diff --extend-exclude node_modules packages/*/src packages/*/tests
	isort --check-only --diff packages/*/src packages/*/tests

# Lint all packages
lint:
	@echo "🔍 Running flake8..."
	flake8 --extend-exclude "*/node_modules/*" packages/*/src packages/*/tests
	@echo "✅ Linting complete!"

# Type check with mypy (separate command for now)
type-check:
	@echo "🔍 Running mypy..."
	mypy packages/pandemic-core/src packages/pandemic-cli/src packages/pandemic-common/src

# Run all quality checks
quality: format-check lint
	@echo "✅ All quality checks passed!"

# Fix all formatting and linting issues
fix: format
	@echo "🔧 Auto-fixing completed!"

# Clean build artifacts
clean:
	rm -rf build/ dist/ *.egg-info/
	rm -rf packages/*/build/ packages/*/dist/ packages/*/*.egg-info/
	rm -rf .pytest_cache/ htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Build all packages
build:
	cd packages/pandemic-common && python3 -m build
	cd packages/pandemic-core && python3 -m build
	cd packages/pandemic-client && python3 -m build
	cd packages/pandemic-iam && python3 -m build
	cd packages/pandemic-rest && python3 -m build

# Development workflow
dev-setup: install-dev
	@echo "✓ Development environment ready"
	@echo "Run 'make test' to run all tests"
	@echo "Run 'make format' to format code"
	@echo "Run 'make lint' to check code quality"
	@echo "Run 'make quality' to run all checks"

# Pre-commit checks (run before committing)
pre-commit: format-check lint test
	@echo "🚀 Ready to commit!"