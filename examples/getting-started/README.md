# Getting Started with agent-eval

This example demonstrates how to use the evaluation harness to test Claude Code configurations.

## Quick Start

```bash
# 1. Verify the harness is working
uv run python -m harness self-test

# 2. Discover available tasks and configs
uv run python -m harness ls --path examples/getting-started/

# 3. Validate without executing (dry-run)
uv run python -m harness run \
    -t examples/getting-started/tasks/fix-bug.task.yaml \
    -c examples/getting-started/configs/baseline/config.yaml \
    --dry-run

# 4. Run a single evaluation (requires ANTHROPIC_API_KEY)
uv run python -m harness run \
    -t examples/getting-started/tasks/fix-bug.task.yaml \
    -c examples/getting-started/configs/baseline/config.yaml

# 5. Compare baseline vs with-instructions (A/B test)
uv run python -m harness matrix \
    -t "examples/getting-started/tasks/*.yaml" \
    -c "examples/getting-started/configs/*/config.yaml" \
    --runs 3
```

## Structure

```
getting-started/
├── README.md                     # This file
├── tasks/
│   ├── fix-bug.task.yaml        # Easy: Fix a bug in calculator
│   ├── add-feature.task.yaml    # Medium: Add new validation
│   └── refactor.task.yaml       # Medium: Improve code structure
├── configs/
│   ├── baseline/
│   │   └── config.yaml          # No custom instructions
│   └── with-instructions/
│       └── config.yaml          # With helpful CLAUDE.md
└── fixtures/
    └── python-utils/            # Sample Python project
        ├── src/
        │   ├── calculator.py    # Math operations (has bugs)
        │   └── validator.py     # Input validation
        └── tests/
            ├── test_calculator.py
            └── test_validator.py
```

## Tasks

### fix-bug (Easy)
The `calculator.py` module has a bug in the `divide` function - it doesn't handle division by zero. The task asks Claude to fix this bug so the tests pass.

### add-feature (Medium)
Add email validation to `validator.py`. This tests Claude's ability to implement new functionality following existing patterns.

### refactor (Medium)
Refactor `calculator.py` to use a class-based design while keeping all tests passing. Tests Claude's ability to restructure code safely.

## Configs

### baseline
No custom instructions. Tests Claude's default behavior.

### with-instructions
Includes a CLAUDE.md with project-specific guidance:
- Coding standards
- Test-first approach
- Error handling patterns

## Interpreting Results

After running evaluations, the harness will show:
- **Pass rate**: Percentage of assertions that passed
- **Score**: Weighted score based on assertion weights
- **Details**: Specific assertion results

Compare baseline vs with-instructions to measure the impact of your CLAUDE.md instructions.

## Next Steps

1. **Customize tasks**: Edit tasks to match your evaluation needs
2. **Add assertions**: Add more code or LLM assertions
3. **Test your own skills**: Copy a skill to `configs/with-skill/` and compare
4. **Run statistical analysis**: Use `--runs 10` and `harness compare` for significance testing
