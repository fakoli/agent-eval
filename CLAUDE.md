# CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## Project: agent-eval

CI evaluation harness for testing Claude Code configurations. Detects behavioral regressions when agent instruction files change.

## Commands

```bash
# Setup
uv sync

# Self-test (verify harness is working)
uv run python -m harness self-test

# Discover tasks and configs
uv run python -m harness ls                        # List all tasks and configs
uv run python -m harness ls tasks                  # List tasks only
uv run python -m harness ls configs                # List configs only
uv run python -m harness ls --path evals/          # Search specific directory

# Dry-run (validate without executing)
uv run python -m harness run -t examples/getting-started/tasks/fix-bug.task.yaml \
    -c examples/getting-started/configs/baseline/config.yaml --dry-run
uv run python -m harness matrix -t "examples/getting-started/tasks/*.yaml" \
    -c "examples/getting-started/configs/*/config.yaml" --dry-run

# Run evaluations
uv run python -m harness run --task evals/tasks/coding/fix-auth-bypass.task.yaml --config evals/configs/full/config.yaml
uv run python -m harness matrix --tasks "evals/tasks/**/*.task.yaml" --configs "evals/configs/*/config.yaml" --runs 3

# Quick testing with --limit
uv run python -m harness run -t task.yaml -c config.yaml --limit 1
uv run python -m harness matrix -t "tasks/*.yaml" -c "configs/*" --limit 5

# Run with artifact preservation (saves fixtures, output, diffs to evals/artifacts/)
uv run python -m harness run -t task.yaml -c config.yaml --preserve-artifacts

# Run in Docker container (isolated execution)
uv run python -m harness build-image              # Build container image first
uv run python -m harness run -t task.yaml -c config.yaml --container

# Generate skill-testing scaffold
uv run python -m harness scaffold --name my-skill-test --fixture-type python
uv run python -m harness scaffold --name my-skill-test --skill-path ~/.claude/skills/my-skill

# Validate files
uv run python -m harness validate-task -t evals/tasks/coding/fix-auth-bypass.task.yaml
uv run python -m harness validate-config -c evals/configs/full/config.yaml

# Tests
uv run pytest tests/                               # Harness tests
uv run pytest tests/test_code_quality.py -v        # Code quality tests
cd fixtures/sample-project && uv run pytest tests/ # Fixture tests

# Environment
uv run python -m harness --env-file ~/.env env-status
uv run python -m harness image-status             # Check Docker image status

# Statistical Analysis
uv run python -m harness power-analysis -b 0.7 -e 0.1  # Sample size recommendation
uv run python -m harness compare baseline.json current.json --statistical
uv run python -m harness compare baseline.json current.json --efficiency --cost  # Token/timing/cost analysis
uv run python -m harness regression -b baseline.json -c current.json --statistical
```

## Architecture

See `docs/ARCHITECTURE.md` for full technical documentation.

**Core flow:** Task loading → Environment isolation → Claude CLI execution → Grading → Reporting

**Key files:**
- `runner.py` - Orchestrates evaluation runs, supports container mode and artifact preservation
- `isolator.py` - Environment isolation and artifact archiving
- `executor.py` - Claude CLI execution
- `container_executor.py` - Docker-based execution
- `container_manager.py` - Docker lifecycle management
- `scaffold.py` - Skill-testing scaffold generation
- `statistics.py` - Statistical analysis (Mann-Whitney U, power analysis, pass@k, efficiency comparison)
- `graders/` - Code and LLM grading logic
- `docker/` - Dockerfile and entrypoint for container isolation

## Known Issues

**Fixture venv paths:** If you relocate this project, `fixtures/sample-project/.venv/bin/pytest` contains a hardcoded shebang path that will break. Recreate the venv or fix the shebang.

**Stale bytecode:** After moving the project, delete `__pycache__` directories to avoid import errors from stale `.pyc` files with embedded paths.

**Model name hardcoding:** The grading model is hardcoded in `harness/graders/llm_graders.py` and `harness/graders/composite_grader.py`. Update if using a different model.

**Container mode requires Docker:** The `--container` flag requires Docker to be installed and running. Build the image first with `build-image`.

## Environment Variables

`ANTHROPIC_API_KEY` - Required for LLM grading. Load with `--env-file ~/.env`.

## Scaffold Structure

The `scaffold` command generates this structure for skill A/B testing:

```
my-skill-test/
├── README.md
├── run-comparison.sh
├── tasks/example.task.yaml
├── configs/
│   ├── baseline/config.yaml
│   └── with-skill/config.yaml
├── fixtures/sample-project/
├── skills/
└── results/
```

## Documentation Sync

When adding or modifying harness features, update these files:

| File | What to Update |
|------|----------------|
| `CLAUDE.md` | Commands section, key files, known issues |
| `docs/ARCHITECTURE.md` | Core components, execution flow, data models |
| `docs/CLI_REFERENCE.md` | Command options, examples, workflows |
| `docs/EXTENDING.md` | Extension points, code examples |
| `README.md` | Quick start, architecture diagram |

Key files that affect documentation:
- `harness/__main__.py` → CLI commands and options
- `harness/runner.py` → EvalRunner flags and behavior
- `harness/executor.py` → Executor implementations
- `harness/isolator.py` → Environment and artifact handling
- `harness/scaffold.py` → Scaffold templates
