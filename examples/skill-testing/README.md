# Skill Testing Example

Test whether your skills improve AI coding assistant behavior using A/B comparisons.

## Quick Start

```bash
# 1. Install dependencies
cd /path/to/agent-eval
uv sync

# 2. Set up your API key
export ANTHROPIC_API_KEY="your-key-here"
# Or create ~/.env with: ANTHROPIC_API_KEY=your-key-here

# 3. Run comparison
cd examples/skill-testing
./run-comparison.sh backend   # Test backend skill
./run-comparison.sh frontend  # Test frontend skill
./run-comparison.sh all       # Test both
```

## What This Tests

### Backend Development Principles Skill

Tests Python/FastAPI development practices:

| Task | What It Tests |
|------|---------------|
| `add-api-endpoint` | API design, thin handlers, type hints |
| `fix-error-handling` | Exception handling, error responses |
| `refactor-route-handler` | Service layer extraction, separation of concerns |

### Frontend Design Principles Skill

Tests UX, accessibility, and visual design:

| Task | What It Tests |
|------|---------------|
| `fix-accessibility` | Semantic HTML, ARIA, keyboard support |
| `implement-component` | Component design, reusability, focus states |
| `add-responsive-layout` | Responsive design, contrast, spacing |

## Understanding Results

Each evaluation produces:

```json
{
  "task_id": "fix-error-handling",
  "config_name": "backend-skill",
  "overall_score": 0.85,
  "passed": true,
  "grades": [
    {"assertion": "tests_pass", "score": 1.0},
    {"assertion": "llm_quality", "score": 0.75}
  ]
}
```

Compare `overall_score` between baseline and skill runs:

- **Score improved**: Skill is helping
- **Score unchanged**: Skill may be too generic
- **Score decreased**: Skill might be adding noise

## Testing Your Own Skill

1. Copy the `_template/` folder:
   ```bash
   cp -r _template/ my-skill-test/
   ```

2. Add your skill to `my-skill-test/skills/`

3. Update `my-skill-test/configs/with-skill/config.yaml`:
   ```yaml
   skills_path: ../skills/your-skill-name
   ```

4. Create tasks that test your skill's principles

5. Create a fixture with intentional issues your skill should help fix

6. Run the comparison:
   ```bash
   uv run python -m harness matrix \
     --tasks "examples/skill-testing/my-skill-test/tasks/*.yaml" \
     --configs "examples/skill-testing/my-skill-test/configs/*/config.yaml" \
     --runs 3
   ```

## Directory Structure

```
examples/skill-testing/
├── README.md               # This file
├── run-comparison.sh       # One-command A/B comparison
├── tasks/
│   ├── backend/            # Backend skill tasks
│   └── frontend/           # Frontend skill tasks
├── configs/
│   ├── baseline/           # No skill (control group)
│   ├── backend-skill/      # With backend-development-principles
│   └── frontend-skill/     # With frontend-design-principles
├── fixtures/
│   ├── backend-api/        # FastAPI project with issues
│   └── frontend-app/       # HTML/CSS/JS with issues
├── skills/                 # Copied skills for portability
│   ├── backend-development-principles/
│   └── frontend-design-principles/
└── _template/              # Template for your own skill tests
```

## Tips for Effective Skill Testing

1. **Match tasks to skill principles**: If your skill emphasizes "thin handlers", create a task that requires refactoring a fat handler.

2. **Create fixtures with intentional issues**: The fixture should have problems your skill should help solve better.

3. **Use multiple runs**: Run 3-5 times per configuration to account for variance. Use `--runs 3` flag.

4. **Focus on measurable principles**: "Write good code" is hard to test. "Always handle errors with specific exceptions" is testable.

5. **Check the LLM grader rubric**: The rubric should evaluate against specific skill principles.

## Troubleshooting

**Tests fail to run**: Make sure you've run `uv sync` in the project root.

**API key errors**: Check `~/.env` contains `ANTHROPIC_API_KEY=...`

**Fixture tests fail**: Some tests are designed to fail initially. Check if they pass after the AI makes changes.

**Results look the same**: Your skill might not be specific enough for the task, or the task doesn't exercise the skill's principles.
