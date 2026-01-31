# Contributing to agent-eval

Thank you for your interest in contributing to agent-eval! This document provides guidelines and instructions for contributing.

## Development Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) package manager
- Claude Code CLI (for running actual evaluations)

### Installation

```bash
# Clone the repository
git clone https://github.com/sekoudoumbouya/agent-eval.git
cd agent-eval

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv sync

# Install dev dependencies
uv pip install -e ".[dev]"
```

### Environment Variables

Create a `.env` file (never commit this):

```bash
ANTHROPIC_API_KEY=your-key-here
```

Load with:
```bash
uv run python -m harness --env-file ~/.env <command>
```

## Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run a specific test file
uv run pytest tests/test_runner.py

# Run a specific test function
uv run pytest tests/test_runner.py::test_load_task -v

# Run fixture project tests
cd fixtures/sample-project && uv run pytest tests/
```

## Adding Tasks

Tasks define evaluation scenarios. Create a `.task.yaml` file in `evals/tasks/<category>/`:

```yaml
id: fix-example-bug
category: coding  # coding, refactoring, or exploration
description: Short description of what this tests
difficulty: medium  # easy, medium, or hard

prompt: |
  Detailed prompt describing what the agent should do.
  Be specific about the expected outcome.

fixture_path: ../../fixtures/sample-project

assertions:
  - type: code
    check: tests_pass
    command: "pytest tests/test_example.py -v"
  - type: code
    check: file_contains
    file: "src/example.py"
    pattern: "expected_pattern"
  - type: llm
    rubric: |
      Quality criteria for LLM-based evaluation.

scoring:
  tests_pass: 50
  file_contains: 20
  llm_quality: 30

timeout_seconds: 300
```

### Task Categories

- **coding**: Bug fixes (`fix-*`) and feature implementations (`add-*`)
- **exploration**: Codebase analysis (`find-*`, `explain-*`)
- **refactoring**: Code improvement tasks

### Assertion Types

**Code assertions** (objective):
- `tests_pass`: Run a test command, check exit code
- `file_contains`: Check file contains a pattern
- `file_exists`: Check file exists
- `file_not_contains`: Check file does NOT contain pattern
- `command_succeeds`: Run arbitrary command, check success

**LLM assertions** (subjective):
- Provides a rubric for Claude to grade the result quality

## Adding Graders

Graders evaluate execution results. See `harness/graders/` for examples.

### Code Graders

Implement objective checks in `harness/graders/code_graders.py`:

```python
def check_custom(assertion: CodeAssertion, working_dir: Path) -> GradeResult:
    """Custom check implementation."""
    # Your logic here
    passed = ...
    return GradeResult(
        assertion_id="custom_check",
        assertion_type="code",
        assertion_name="custom",
        passed=passed,
        score=1.0 if passed else 0.0,
        details="Explanation of result",
    )
```

### LLM Graders

For quality evaluation, modify `harness/graders/llm_graders.py`. The LLM grader uses Claude Haiku to evaluate results against rubrics.

## Adding Configurations

Configs define Claude Code environment variants. Create `evals/configs/<name>/config.yaml`:

```yaml
name: my-config
description: Description of what this config tests

claude_md: |
  # Custom CLAUDE.md content
  Instructions for the agent...

skills_path: ~/.claude/skills  # or null
agents_md: null  # or agent definitions

model: claude-sonnet-4-5-20250514
max_turns: 15
allowed_tools: all  # or list of specific tools
```

## Code Style

- Format code with [ruff](https://github.com/astral-sh/ruff)
- Type hints required for all public functions
- Docstrings for all modules, classes, and public functions
- Follow existing patterns in the codebase

## Pull Request Process

1. **Fork** the repository
2. **Create a branch** for your feature: `git checkout -b feature/my-feature`
3. **Make changes** and add tests
4. **Run tests** to ensure everything passes
5. **Commit** with clear messages describing what and why
6. **Push** to your fork
7. **Open a PR** against `main`

### PR Guidelines

- Keep PRs focused on a single concern
- Include tests for new functionality
- Update documentation if behavior changes
- Ensure all CI checks pass

## Reporting Issues

When reporting issues, please include:

- Python version (`python --version`)
- OS and version
- Steps to reproduce
- Expected vs actual behavior
- Relevant logs or error messages

## Questions?

Open an issue with the `question` label if you need help or clarification.
