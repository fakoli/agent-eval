# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project: agent-eval

CI evaluation harness for testing Claude Code configurations. Detects behavioral regressions when agent instruction files change.

## Commands

```bash
# Setup
uv sync

# Run evaluations
uv run python -m harness run --task evals/tasks/coding/fix-auth-bypass.task.yaml --config evals/configs/full/config.yaml
uv run python -m harness matrix --tasks "evals/tasks/**/*.task.yaml" --configs "evals/configs/*/config.yaml" --runs 3

# Validate files
uv run python -m harness validate-task -t evals/tasks/coding/fix-auth-bypass.task.yaml
uv run python -m harness validate-config -c evals/configs/full/config.yaml

# Tests
uv run pytest                                      # Harness tests
cd fixtures/sample-project && uv run pytest tests/ # Fixture tests

# Environment
uv run python -m harness --env-file ~/.env env-status
```

## Architecture

See `docs/ARCHITECTURE.md` for full technical documentation.

**Core flow:** Task loading → Environment isolation → Claude CLI execution → Grading → Reporting

**Key files:** `runner.py`, `isolator.py`, `executor.py`, `graders/`

## Known Issues

**Fixture venv paths:** If you relocate this project, `fixtures/sample-project/.venv/bin/pytest` contains a hardcoded shebang path that will break. Recreate the venv or fix the shebang.

**Stale bytecode:** After moving the project, delete `__pycache__` directories to avoid import errors from stale `.pyc` files with embedded paths.

**Model name hardcoding:** The grading model is hardcoded in `harness/graders/llm_graders.py` and `harness/graders/composite_grader.py`. Update if using a different model.

## Environment Variables

`ANTHROPIC_API_KEY` - Required for LLM grading. Load with `--env-file ~/.env`.
