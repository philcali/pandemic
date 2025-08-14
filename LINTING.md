# Code Quality and Formatting

The Pandemic monorepo uses a comprehensive suite of linting and formatting tools to maintain code quality and consistency.

## Tools Used

### 🎨 **Black** - Code Formatter
- **Purpose**: Automatic code formatting
- **Configuration**: 100 character line length, Python 3.10 target
- **Usage**: `make format` or `black packages/*/src packages/*/tests`

### 📦 **isort** - Import Sorter  
- **Purpose**: Sorts and organizes imports
- **Configuration**: Black-compatible profile
- **Usage**: Runs automatically with `make format`

### 🔍 **Flake8** - Style Guide Enforcement
- **Purpose**: PEP 8 compliance and code quality checks
- **Configuration**: 100 character line length, docstring checks disabled for now
- **Usage**: `make lint` or `flake8 packages/*/src packages/*/tests`

### 🔧 **MyPy** - Type Checking (Optional)
- **Purpose**: Static type checking
- **Configuration**: Lenient settings for initial development
- **Usage**: `make type-check` (separate from main lint for now)

### 🪝 **Pre-commit** - Git Hooks
- **Purpose**: Automated quality checks before commits
- **Configuration**: `.pre-commit-config.yaml`
- **Usage**: `pre-commit install` then automatic on commits

## Quick Commands

```bash
# Format all code
make format

# Check formatting without changes
make format-check

# Run linting
make lint

# Run type checking
make type-check

# Run all quality checks
make quality

# Auto-fix what can be fixed
make fix

# Pre-commit checks
make pre-commit
```

## Configuration Files

### `.flake8`
```ini
[flake8]
max-line-length = 100
extend-ignore = E203,W503,D100,D103,D104,D105,D107,D401,D403,F401,F841,E722
exclude = .git,__pycache__,build,dist,.eggs,*.egg-info,.venv,.mypy_cache
docstring-convention = google
```

### `pyproject.toml` (Black & isort)
```toml
[tool.black]
line-length = 100
target-version = ['py310']

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
```

## Development Workflow

### 1. Before Committing
```bash
# Format code
make format

# Check quality
make quality

# Run tests
make test
```

### 2. Setting up Pre-commit (Optional)
```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Run on all files
pre-commit run --all-files
```

### 3. IDE Integration

#### VS Code
```json
{
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length=100"],
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true
}
```

#### PyCharm
- Install Black plugin
- Configure Flake8 as external tool
- Set line length to 100 in Code Style settings

## Ignored Rules

We currently ignore these rules for pragmatic development:

- **E203, W503**: Conflicts with Black formatting
- **D100-D107**: Docstring requirements (can enable later)
- **F401, F841**: Unused imports/variables (can tighten later)
- **E722**: Bare except clauses (will fix gradually)

## Gradual Improvement

The linting configuration is intentionally lenient to start. As the codebase matures:

1. **Enable stricter docstring requirements**
2. **Remove F401/F841 ignores** (fix unused imports)
3. **Enable full MyPy type checking**
4. **Add more specific linting rules**

## Package-Specific Linting

Each package can have additional linting rules in their `pyproject.toml`:

```toml
[tool.mypy]
# Package-specific mypy settings

[tool.black]
# Package-specific black settings
```

## Continuous Integration

In CI/CD pipelines, run:

```bash
# Check formatting
make format-check

# Run linting
make lint

# Run tests
make test

# Type checking (when ready)
make type-check
```

## Troubleshooting

### Common Issues

1. **Line too long**: Black should handle this, but manual breaks may be needed
2. **Import order**: Run `make format` to fix automatically
3. **Unused imports**: Remove manually or add `# noqa: F401` temporarily

### Disabling Rules

For specific lines:
```python
# Disable specific rule
some_code()  # noqa: E501

# Disable multiple rules  
some_code()  # noqa: E501,F401
```

For entire files:
```python
# flake8: noqa
```

## Benefits

- **Consistent code style** across all packages
- **Reduced code review friction** 
- **Automatic formatting** saves time
- **Early bug detection** through linting
- **Professional code quality** standards