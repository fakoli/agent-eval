"""Scaffold generator for skill-testing directory structures."""

import shutil
from pathlib import Path

# Template constants
README_TEMPLATE = """# {name} - Skill Testing

This directory contains an A/B comparison test for evaluating skills.

## Structure

```
{name}/
├── tasks/           # Task definitions (what to test)
├── configs/         # Configuration variants (baseline vs with-skill)
├── fixtures/        # Test codebases
├── skills/          # Skill files to test
└── results/         # Output from test runs
```

## Running the Comparison

```bash
# Set your API key
export ANTHROPIC_API_KEY="your-key-here"

# Run comparison
./run-comparison.sh

# Or run manually with the harness
uv run python -m harness matrix \\
    --tasks "{name}/tasks/*.yaml" \\
    --configs "{name}/configs/*/config.yaml" \\
    --runs 3
```

## Interpreting Results

Compare the `overall_score` between baseline and with-skill runs:
- Higher scores with the skill = skill is effective
- Similar scores = skill may not help for this task type
- Lower scores = skill may be counterproductive

## Customizing

1. Add your skill to `skills/`
2. Update `configs/with-skill/config.yaml` to reference it
3. Create tasks in `tasks/` that test specific skill principles
4. Modify `fixtures/` to have intentional issues your skill helps fix
"""

BASELINE_CONFIG_TEMPLATE = """name: baseline
description: No skill - control group

# No custom instructions
claude_md: null

# No skills
skills_path: null

# No agents
agents_md: null

# Model configuration
model: claude-sonnet-4-20250514
max_turns: 10

# Standard tools
allowed_tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
"""

WITH_SKILL_CONFIG_TEMPLATE = """name: with-skill
description: With skill loaded

# No additional CLAUDE.md - testing skill in isolation
claude_md: null

# Update this path to point to your skill
skills_path: ../../skills/{skill_name}

# No agents
agents_md: null

# Model configuration
model: claude-sonnet-4-20250514
max_turns: 10

# Standard tools
allowed_tools:
  - Read
  - Edit
  - Write
  - Bash
  - Grep
  - Glob
"""

TASK_TEMPLATE = """id: {task_id}
category: coding
description: {description}
difficulty: medium

prompt: |
  Fix the issue in the codebase.

  Your task:
  1. Identify the problem
  2. Implement the fix
  3. Ensure tests pass

# Path to fixture project (relative to this file)
fixture_path: ../fixtures/{fixture_name}

assertions:
  # Objective check: tests pass
  - type: code
    check: tests_pass
    command: "{test_command}"

  # Subjective check: LLM evaluates quality
  - type: llm
    rubric: |
      Evaluate the implementation:

      1. Correctness (0-40 points):
         - Does the fix address the actual problem?
         - Are edge cases handled?

      2. Code Quality (0-30 points):
         - Is the code clean and readable?
         - Does it follow project conventions?

      3. Best Practices (0-30 points):
         - Does it follow relevant best practices?
         - Is it maintainable?

scoring:
  tests_pass: 50
  llm_quality: 50

timeout_seconds: 300
"""

RUN_COMPARISON_TEMPLATE = """#!/bin/bash
#
# Skill Testing: A/B Comparison Script
#
# Runs evaluations with and without skills to measure their impact.
# Usage: ./run-comparison.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
NC='\\033[0m' # No Color

echo "=========================================="
echo "  {name}: A/B Skill Comparison"
echo "=========================================="
echo ""

# Load environment variables from ~/.env if it exists
if [ -f ~/.env ]; then
    echo "Loading environment from ~/.env..."
    set -a
    source ~/.env
    set +a
fi

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${{RED}}Error: ANTHROPIC_API_KEY is not set.${{NC}}"
    echo "Set it with: export ANTHROPIC_API_KEY='your-key-here'"
    exit 1
fi

# Create results directory
mkdir -p "$SCRIPT_DIR/results"

echo -e "${{YELLOW}}Running comparison...${{NC}}"
echo ""

# Run baseline (no skill)
echo "Step 1/2: Running baseline (no skill)..."
uv run python -m harness matrix \\
    --tasks "$SCRIPT_DIR/tasks/*.yaml" \\
    --configs "$SCRIPT_DIR/configs/baseline/config.yaml" \\
    --runs 2 \\
    --output "$SCRIPT_DIR/results/baseline.json" \\
    2>&1 | tee "$SCRIPT_DIR/results/baseline.log"

# Run with skill
echo ""
echo "Step 2/2: Running with skill..."
uv run python -m harness matrix \\
    --tasks "$SCRIPT_DIR/tasks/*.yaml" \\
    --configs "$SCRIPT_DIR/configs/with-skill/config.yaml" \\
    --runs 2 \\
    --output "$SCRIPT_DIR/results/with-skill.json" \\
    2>&1 | tee "$SCRIPT_DIR/results/with-skill.log"

echo ""
echo -e "${{GREEN}}Comparison complete!${{NC}}"
echo ""
echo "Results:"
echo "  Baseline:   $SCRIPT_DIR/results/baseline.json"
echo "  With Skill: $SCRIPT_DIR/results/with-skill.json"
echo ""
echo "To compare, look at 'overall_score' in each result."
"""

# Python fixture templates
PYTHON_PYPROJECT_TEMPLATE = """[project]
name = "{name}"
version = "0.1.0"
description = "Test fixture for skill evaluation"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
"""

PYTHON_MAIN_TEMPLATE = '''"""Main module for the test fixture."""


def process_data(data: dict) -> dict:
    """Process input data.

    TODO: This function has issues that need to be fixed.
    """
    result = {}
    for key, value in data.items():
        result[key] = value
    return result


def validate_input(user_input: str) -> bool:
    """Validate user input.

    TODO: This validation is incomplete.
    """
    if user_input:
        return True
    return False
'''

PYTHON_TEST_TEMPLATE = '''"""Tests for the main module."""

import pytest
from src.main import process_data, validate_input


class TestProcessData:
    """Tests for process_data function."""

    def test_basic_processing(self):
        """Test basic data processing."""
        data = {"key": "value"}
        result = process_data(data)
        assert result == {"key": "value"}

    def test_empty_input(self):
        """Test with empty input."""
        result = process_data({})
        assert result == {}


class TestValidateInput:
    """Tests for validate_input function."""

    def test_valid_input(self):
        """Test with valid input."""
        assert validate_input("hello") is True

    def test_empty_string(self):
        """Test with empty string."""
        # TODO: This test may need adjustment based on requirements
        assert validate_input("") is False
'''

PYTHON_INIT_TEMPLATE = '''"""Package initialization."""
'''

# JavaScript fixture templates
JS_PACKAGE_JSON_TEMPLATE = """{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "Test fixture for skill evaluation",
  "main": "src/index.js",
  "scripts": {{
    "test": "node --test tests/"
  }},
  "devDependencies": {{}}
}}
"""

JS_INDEX_TEMPLATE = '''/**
 * Main module for the test fixture.
 */

/**
 * Process input data.
 * TODO: This function has issues that need to be fixed.
 * @param {Object} data - Input data
 * @returns {Object} Processed data
 */
function processData(data) {
    const result = {};
    for (const key in data) {
        result[key] = data[key];
    }
    return result;
}

/**
 * Validate user input.
 * TODO: This validation is incomplete.
 * @param {string} input - User input
 * @returns {boolean} Whether input is valid
 */
function validateInput(input) {
    if (input) {
        return true;
    }
    return false;
}

module.exports = { processData, validateInput };
'''

JS_TEST_TEMPLATE = '''/**
 * Tests for main module.
 */
const { test } = require('node:test');
const assert = require('node:assert');
const { processData, validateInput } = require('../src/index.js');

test('processData - basic processing', () => {
    const data = { key: 'value' };
    const result = processData(data);
    assert.deepStrictEqual(result, { key: 'value' });
});

test('processData - empty input', () => {
    const result = processData({});
    assert.deepStrictEqual(result, {});
});

test('validateInput - valid input', () => {
    assert.strictEqual(validateInput('hello'), true);
});

test('validateInput - empty string', () => {
    // TODO: This test may need adjustment based on requirements
    assert.strictEqual(validateInput(''), false);
});
'''

SKILL_TEMPLATE = """---
name: {skill_name}
description: {description}
---

# {skill_name}

## Principles

1. **Principle One**: Description of the first principle.

2. **Principle Two**: Description of the second principle.

3. **Principle Three**: Description of the third principle.

## Guidelines

- Guideline A
- Guideline B
- Guideline C

## Examples

### Good Example

```python
# Example of following the principles
```

### Bad Example

```python
# Example of violating the principles
```
"""


class ScaffoldGenerator:
    """Generates skill-testing directory structures."""

    def __init__(self, name: str, output_dir: Path | None = None):
        """Initialize the scaffold generator.

        Args:
            name: Name of the skill test (used for directory and display)
            output_dir: Output directory (defaults to current directory)
        """
        self.name = name
        self.output_dir = output_dir or Path.cwd()
        self.root = self.output_dir / name

    def generate(
        self,
        fixture_type: str = "python",
        skill_path: Path | None = None,
    ) -> Path:
        """Generate the complete scaffold structure.

        Args:
            fixture_type: Type of fixture to generate ('python' or 'javascript')
            skill_path: Optional path to an existing skill to copy

        Returns:
            Path to the generated directory
        """
        # Create directory structure
        self._create_directories()

        # Generate files
        self._generate_readme()
        self._generate_configs(skill_path)
        self._generate_fixture(fixture_type)
        self._generate_task(fixture_type)
        self._generate_run_script()
        self._generate_results_gitignore()

        # Copy skill if provided
        if skill_path:
            self._copy_skill(skill_path)
        else:
            self._generate_placeholder_skill()

        return self.root

    def _create_directories(self) -> None:
        """Create the directory structure."""
        dirs = [
            self.root,
            self.root / "tasks",
            self.root / "configs" / "baseline",
            self.root / "configs" / "with-skill",
            self.root / "fixtures" / "sample-project" / "src",
            self.root / "fixtures" / "sample-project" / "tests",
            self.root / "skills",
            self.root / "results",
        ]
        for d in dirs:
            d.mkdir(parents=True, exist_ok=True)

    def _generate_readme(self) -> None:
        """Generate README.md."""
        content = README_TEMPLATE.format(name=self.name)
        (self.root / "README.md").write_text(content)

    def _generate_configs(self, skill_path: Path | None = None) -> None:
        """Generate config files."""
        # Baseline config
        (self.root / "configs" / "baseline" / "config.yaml").write_text(
            BASELINE_CONFIG_TEMPLATE
        )

        # With-skill config
        skill_name = skill_path.name if skill_path else "your-skill"
        content = WITH_SKILL_CONFIG_TEMPLATE.format(skill_name=skill_name)
        (self.root / "configs" / "with-skill" / "config.yaml").write_text(content)

    def _generate_fixture(self, fixture_type: str) -> None:
        """Generate fixture project files."""
        fixture_dir = self.root / "fixtures" / "sample-project"
        src_dir = fixture_dir / "src"
        tests_dir = fixture_dir / "tests"

        if fixture_type == "python":
            # pyproject.toml
            content = PYTHON_PYPROJECT_TEMPLATE.format(name=f"{self.name}-fixture")
            (fixture_dir / "pyproject.toml").write_text(content)

            # src/__init__.py
            (src_dir / "__init__.py").write_text(PYTHON_INIT_TEMPLATE)

            # src/main.py
            (src_dir / "main.py").write_text(PYTHON_MAIN_TEMPLATE)

            # tests/__init__.py
            (tests_dir / "__init__.py").write_text(PYTHON_INIT_TEMPLATE)

            # tests/test_main.py
            (tests_dir / "test_main.py").write_text(PYTHON_TEST_TEMPLATE)

        elif fixture_type == "javascript":
            # package.json
            content = JS_PACKAGE_JSON_TEMPLATE.format(name=f"{self.name}-fixture")
            (fixture_dir / "package.json").write_text(content)

            # src/index.js
            (src_dir / "index.js").write_text(JS_INDEX_TEMPLATE)

            # tests/test_main.js
            (tests_dir / "test_main.js").write_text(JS_TEST_TEMPLATE)

    def _generate_task(self, fixture_type: str) -> None:
        """Generate task file."""
        test_command = (
            "uv run pytest tests/ -v"
            if fixture_type == "python"
            else "npm test"
        )

        content = TASK_TEMPLATE.format(
            task_id=f"{self.name}-example",
            description="Example task for skill evaluation",
            fixture_name="sample-project",
            test_command=test_command,
        )
        (self.root / "tasks" / "example.task.yaml").write_text(content)

    def _generate_run_script(self) -> None:
        """Generate run-comparison.sh script."""
        content = RUN_COMPARISON_TEMPLATE.format(name=self.name)
        script_path = self.root / "run-comparison.sh"
        script_path.write_text(content)
        script_path.chmod(0o755)

    def _generate_results_gitignore(self) -> None:
        """Generate .gitignore for results directory."""
        content = """# Ignore result files
*.json
*.log

# Keep the directory
!.gitkeep
!.gitignore
"""
        (self.root / "results" / ".gitignore").write_text(content)
        (self.root / "results" / ".gitkeep").write_text("")

    def _copy_skill(self, skill_path: Path) -> None:
        """Copy an existing skill into the skills directory."""
        if not skill_path.exists():
            raise ValueError(f"Skill path does not exist: {skill_path}")

        dest = self.root / "skills" / skill_path.name
        if skill_path.is_dir():
            shutil.copytree(skill_path, dest)
        else:
            dest.mkdir(parents=True, exist_ok=True)
            shutil.copy2(skill_path, dest / skill_path.name)

    def _generate_placeholder_skill(self) -> None:
        """Generate a placeholder skill file."""
        skill_dir = self.root / "skills" / "your-skill"
        skill_dir.mkdir(parents=True, exist_ok=True)

        content = SKILL_TEMPLATE.format(
            skill_name="Your Skill",
            description="Description of what this skill does",
        )
        (skill_dir / "SKILL.md").write_text(content)
