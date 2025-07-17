# Contributing Guide

This document explains how to set up a development environment and contribute to this project.

## Setting Up Development Environment

1. Clone the repository
2. Install dependencies using uv:
   ```bash
   uv sync --all-groups --extra dev
   ```

3. Install pre-commit hooks:
   ```bash
   uv run pre-commit install --install-hooks
   uv run pre-commit install --hook-type pre-push
   ```

## Code Quality Tools

This project uses several tools to ensure code quality:

### pre-commit

We use [pre-commit](https://pre-commit.com/) to run code quality checks before each commit.

- **pre-commit hooks**: Run automatically on `git commit` to check code style and formatting
- **pre-push hooks**: Run tests automatically before pushing to the remote repository

### Ruff

[Ruff](https://github.com/astral-sh/ruff) is used for linting and formatting Python code.

- To check code: `uv run ruff check .`
- To format code: `uv run ruff format .`

### pytest

Tests are run using pytest:

```bash
uv run pytest
```

## Development Workflow

1. Create a new branch for your changes
2. Make your changes
3. Ensure all tests pass: `uv run pytest`
4. Commit your changes (pre-commit hooks will run automatically)
5. Push your changes (pre-push hooks will run tests automatically)
6. Create a pull request

## Manual Quality Checks

If you want to run checks manually:

```bash
# Run linting
uv run ruff check .

# Run formatting
uv run ruff format .

# Run all tests
uv run pytest
```