# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a proof of concept to evaluate whether Temporal can meet the requirements for replacing dbt in a data analysis workflow. The project aims to transform machine learning analysis results into a structured database, moving from batch processing to more event-driven processing.

## Requirements

- Python (see .python-version file for specific version)
- uv for Python package management
- Temporal SDK for Python

## Project Structure

- `/workflows`: Directory for Temporal workflow definitions
- `/script`: Directory for utility scripts
- `/test`: Directory for test files

## Architecture

The project implements two main workflows:

1. **Proxy Workflow**: 
   - Receives push events from PubSub (or simulates them via REST API for testing)
   - Extracts job_id, tenant_id, analysis_type from request bodies
   - Sends signals to the Analysis Workflow

2. **Analysis Workflow**:
   - Triggered by signals from the Proxy Workflow
   - Processes analysis results when all required data is available
   - Outputs final results to files or database
   - Keeps intermediate data in memory only

## Development Commands

This project uses uv for dependency management and standard Temporal commands for execution:

### Setup Dependencies

```bash
# Install uv if needed
brew install uv

# Create virtual environment
uv venv

# Install dependencies
uv sync --all-groups --extra dev
```

### Setup Local Temporal Server

```bash
# Install Temporal CLI if needed
brew install temporalio/tap/temporal

# Start the Temporal server locally
temporal server start-dev
```

### Running Workflows

```bash
# Activate virtual environment
source .venv/bin/activate

# Start a worker to process workflows and activities
uv run python -m script.worker

# Trigger a workflow execution
uv run python -m script.trigger_analysis_workflow
# or
uv run python -m script.trigger_proxy_workflow
```

### Testing

```bash
# Run tests
uv sync --all-groups --extra dev
uv run pytest test/
```

### Linting

```bash
# Run Ruff linter
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check --fix .

# Format code with Ruff
uv run ruff format .
```

## Key Requirements

- Steps should be modular and independently testable
- Workflows should process approximately 20K events/minute
- Intermediate data should be kept in memory only
- Final results should be persisted to files or database
- Workflows should be testable locally
- Primary implementation language is Python