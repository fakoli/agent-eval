# Extending the Harness

This guide explains how to extend agent-eval with custom executors, graders, and assertion types.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Adding New Executors](#adding-new-executors)
- [Adding New Code Check Types](#adding-new-code-check-types)
- [Adding New Assertion Types](#adding-new-assertion-types)
- [Creating Custom Configs](#creating-custom-configs)
- [Creating Fixture Projects](#creating-fixture-projects)

---

## Architecture Overview

The harness is designed with extensibility in mind:

```
┌─────────────────────────────────────────────────────────────┐
│                        EvalRunner                           │
│                    (Orchestration Layer)                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Executor   │  │   Isolator   │  │ CompositeGrader  │  │
│  │     (ABC)    │  │              │  │                  │  │
│  ├──────────────┤  │  Creates     │  │  ┌────────────┐  │  │
│  │ClaudeExecutor│  │  isolated    │  │  │ CodeGrader │  │  │
│  │              │  │  environments│  │  └────────────┘  │  │
│  │ (extendable) │  │              │  │  ┌────────────┐  │  │
│  └──────────────┘  └──────────────┘  │  │ LLMGrader  │  │  │
│                                       │  └────────────┘  │  │
│                                       └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Extension Points:**
1. **Executor**: Add support for new AI tools (Cursor, Copilot)
2. **Container Execution**: Run evaluations in isolated Docker containers
3. **CodeGrader**: Add new objective check types
4. **Assertion Types**: Add new assertion categories
5. **Configs**: Create custom configuration variants
6. **Fixtures**: Create test codebases
7. **Scaffold Templates**: Customize skill-testing scaffolds

---

## Adding New Executors

Create a new executor to support different AI coding tools.

### Step 1: Create the Executor Class

**File:** `harness/executor.py`

```python
from harness.executor import Executor
from harness.models import Config, ExecutionTrace, TokenUsage, ToolCall


class CursorExecutor(Executor):
    """Executor for Cursor IDE automation."""

    def __init__(
        self,
        cursor_path: str = "cursor",
        headless: bool = True,
    ):
        """Initialize Cursor executor.

        Args:
            cursor_path: Path to Cursor CLI or automation script
            headless: Run without UI (for CI)
        """
        self.cursor_path = cursor_path
        self.headless = headless

    def run(
        self,
        prompt: str,
        config: Config,
        working_dir: Path,
        timeout: int = 300,
        env_override: dict[str, str] | None = None,
    ) -> ExecutionTrace:
        """Execute a prompt using Cursor.

        Args:
            prompt: The prompt to execute
            config: Configuration to use
            working_dir: Working directory for execution
            timeout: Timeout in seconds
            env_override: Optional environment variable overrides

        Returns:
            ExecutionTrace with results and metadata
        """
        # 1. Build command or API call
        cmd = self._build_command(prompt, config)

        # 2. Execute with timeout
        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env={**os.environ, **(env_override or {})},
            )
            duration = time.time() - start_time

            # 3. Parse output into ExecutionTrace
            return self._parse_output(result.stdout, result.stderr, duration)

        except subprocess.TimeoutExpired:
            return ExecutionTrace(
                result="Execution timed out",
                is_error=True,
                duration_seconds=time.time() - start_time,
            )

    def _build_command(self, prompt: str, config: Config) -> list[str]:
        """Build Cursor CLI command."""
        cmd = [self.cursor_path]

        if self.headless:
            cmd.append("--headless")

        cmd.extend(["--prompt", prompt])

        # Add config-specific options
        if config.allowed_tools != "all":
            cmd.extend(["--tools", ",".join(config.allowed_tools)])

        return cmd

    def _parse_output(
        self,
        stdout: str,
        stderr: str,
        duration: float,
    ) -> ExecutionTrace:
        """Parse Cursor output into ExecutionTrace."""
        # Implementation depends on Cursor's output format
        return ExecutionTrace(
            result=stdout,
            is_error=bool(stderr),
            duration_seconds=duration,
            raw_output={"stdout": stdout, "stderr": stderr},
        )
```

### Step 2: Use the New Executor

```python
from harness.runner import EvalRunner
from harness.executor import CursorExecutor

# Use custom executor
executor = CursorExecutor(headless=True)
runner = EvalRunner(executor=executor)

result = runner.run_single(task, config)
```

### Step 3: Add CLI Integration (Optional)

**File:** `harness/__main__.py`

```python
@cli.command()
@click.option("--executor", type=click.Choice(["claude", "cursor"]), default="claude")
def run(task, config, executor, ...):
    """Run evaluation with selected executor."""
    if executor == "cursor":
        exec = CursorExecutor()
    else:
        exec = ClaudeExecutor()

    runner = EvalRunner(executor=exec)
    # ...
```

---

## Using Container Execution

Run evaluations in isolated Docker containers for security and reproducibility.

### Step 1: Build the Container Image

```bash
uv run python -m harness build-image
```

This creates an image with:
- Claude Code CLI
- Python with uv package manager
- Node.js for JavaScript fixtures
- Non-root `eval` user

### Step 2: Run with Container Flag

```python
from harness.runner import EvalRunner

# Via CLI
# uv run python -m harness run -t task.yaml -c config.yaml --container

# Via Python
runner = EvalRunner(use_container=True)
result = runner.run_single(task, config)
```

### Step 3: Customize Container Configuration

```python
from harness.container_executor import ContainerExecutor
from harness.container_manager import ContainerConfig

config = ContainerConfig(
    memory_limit="8g",        # More memory
    cpu_limit=4.0,            # More CPUs
    network_enabled=False,    # Disable network
    timeout=600,              # 10 minute timeout
)

executor = ContainerExecutor(config=config)
runner = EvalRunner(executor=executor)
```

### Step 4: Modify the Dockerfile (Advanced)

**File:** `docker/Dockerfile`

```dockerfile
# Add custom dependencies
RUN apt-get update && apt-get install -y \
    my-custom-tool \
    && rm -rf /var/lib/apt/lists/*

# Add custom scripts
COPY custom-script.sh /home/eval/
```

Rebuild after modifications:
```bash
uv run python -m harness build-image --no-cache
```

---

## Adding New Code Check Types

Add new objective check types to the CodeGrader.

### Step 1: Add Check Type to Enum

**File:** `harness/models.py`

```python
class CodeCheckType(str, Enum):
    """Types of code-based checks."""

    TESTS_PASS = "tests_pass"
    FILE_CONTAINS = "file_contains"
    FILE_EXISTS = "file_exists"
    FILE_NOT_CONTAINS = "file_not_contains"
    COMMAND_SUCCEEDS = "command_succeeds"

    # New check types
    IMPORT_SUCCEEDS = "import_succeeds"      # Verify module imports
    LINT_PASSES = "lint_passes"              # Run linter
    TYPE_CHECK_PASSES = "type_check_passes"  # Run type checker
```

### Step 2: Implement the Check

**File:** `harness/graders/code_graders.py`

```python
class CodeGrader:
    def grade(self, assertion: CodeAssertion, env_path: Path) -> GradeResult:
        match assertion.check:
            # ... existing cases ...

            case CodeCheckType.IMPORT_SUCCEEDS:
                if not assertion.module:
                    return GradeResult(
                        passed=False,
                        score=0.0,
                        details="import_succeeds requires module field",
                    )
                return self.grade_import_succeeds(env_path, assertion.module)

            case CodeCheckType.LINT_PASSES:
                return self.grade_lint_passes(
                    env_path,
                    assertion.command or "ruff check .",
                )

    def grade_import_succeeds(
        self,
        env_path: Path,
        module: str,
    ) -> GradeResult:
        """Check if a Python module can be imported.

        Args:
            env_path: Path to evaluation environment
            module: Module name to import (e.g., "src.auth")

        Returns:
            GradeResult indicating if import succeeded
        """
        try:
            result = subprocess.run(
                ["python", "-c", f"import {module}"],
                cwd=env_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            passed = result.returncode == 0
            return GradeResult(
                assertion_id="import_succeeds",
                assertion_type="code",
                assertion_name="import_succeeds",
                passed=passed,
                score=1.0 if passed else 0.0,
                details=f"Import {'succeeded' if passed else 'failed'}: {module}",
                full_output=result.stderr if not passed else "",
            )
        except Exception as e:
            return GradeResult(
                assertion_id="import_succeeds",
                assertion_type="code",
                assertion_name="import_succeeds",
                passed=False,
                score=0.0,
                details=f"Error checking import: {e}",
            )

    def grade_lint_passes(
        self,
        env_path: Path,
        command: str,
    ) -> GradeResult:
        """Check if linting passes.

        Args:
            env_path: Path to evaluation environment
            command: Lint command to run

        Returns:
            GradeResult indicating if linting passed
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=env_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            passed = result.returncode == 0
            return GradeResult(
                assertion_id="lint_passes",
                assertion_type="code",
                assertion_name="lint_passes",
                passed=passed,
                score=1.0 if passed else 0.0,
                details=result.stdout[:1000] if passed else result.stdout[:1000],
                full_output=f"{result.stdout}\n{result.stderr}",
            )
        except Exception as e:
            return GradeResult(
                assertion_id="lint_passes",
                assertion_type="code",
                assertion_name="lint_passes",
                passed=False,
                score=0.0,
                details=f"Error running lint: {e}",
            )
```

### Step 3: Update CodeAssertion Model

**File:** `harness/models.py`

```python
class CodeAssertion(Assertion):
    """Code-based assertion for objective checks."""

    type: Literal[AssertionType.CODE] = AssertionType.CODE
    check: CodeCheckType
    command: str | None = None
    file: str | None = None
    pattern: str | None = None
    module: str | None = None  # New field for import_succeeds
```

### Step 4: Update Task Loading

**File:** `harness/runner.py`

```python
@staticmethod
def load_task(path: Path) -> Task:
    # ... existing code ...

    for a in data.get("assertions", []):
        if a["type"] == "code":
            assertions.append(
                CodeAssertion(
                    type=AssertionType.CODE,
                    check=CodeCheckType(a["check"]),
                    command=a.get("command"),
                    file=a.get("file"),
                    pattern=a.get("pattern"),
                    module=a.get("module"),  # New field
                )
            )
```

### Step 5: Use in Tasks

```yaml
assertions:
  - type: code
    check: import_succeeds
    module: "src.new_feature"

  - type: code
    check: lint_passes
    command: "ruff check src/"
```

---

## Adding New Assertion Types

Add entirely new assertion categories (beyond code and llm).

### Step 1: Define the Assertion Type

**File:** `harness/models.py`

```python
class AssertionType(str, Enum):
    """Types of assertions for grading."""

    CODE = "code"
    LLM = "llm"
    PERFORMANCE = "performance"  # New type


class PerformanceAssertion(Assertion):
    """Performance-based assertion for timing checks."""

    type: Literal[AssertionType.PERFORMANCE] = AssertionType.PERFORMANCE
    command: str                    # Command to benchmark
    max_duration_seconds: float     # Maximum acceptable duration
    warmup_runs: int = 3           # Warmup iterations
    benchmark_runs: int = 10       # Benchmark iterations
```

### Step 2: Create the Grader

**File:** `harness/graders/performance_grader.py`

```python
import subprocess
import statistics
from pathlib import Path

from harness.models import GradeResult, PerformanceAssertion


class PerformanceGrader:
    """Grader for performance-based assertions."""

    def grade(
        self,
        assertion: PerformanceAssertion,
        env_path: Path,
    ) -> GradeResult:
        """Grade a performance assertion.

        Args:
            assertion: The performance assertion to check
            env_path: Path to evaluation environment

        Returns:
            GradeResult with timing data
        """
        durations = []

        # Warmup runs
        for _ in range(assertion.warmup_runs):
            subprocess.run(
                assertion.command,
                shell=True,
                cwd=env_path,
                capture_output=True,
            )

        # Benchmark runs
        for _ in range(assertion.benchmark_runs):
            start = time.time()
            result = subprocess.run(
                assertion.command,
                shell=True,
                cwd=env_path,
                capture_output=True,
            )
            duration = time.time() - start

            if result.returncode == 0:
                durations.append(duration)

        if not durations:
            return GradeResult(
                assertion_id="performance",
                assertion_type="performance",
                assertion_name="performance",
                passed=False,
                score=0.0,
                details="All benchmark runs failed",
            )

        avg_duration = statistics.mean(durations)
        passed = avg_duration <= assertion.max_duration_seconds

        # Score: 1.0 if under threshold, decreasing linearly to 0 at 2x threshold
        if passed:
            score = 1.0
        else:
            overage = avg_duration / assertion.max_duration_seconds
            score = max(0.0, 2.0 - overage)

        return GradeResult(
            assertion_id="performance",
            assertion_type="performance",
            assertion_name="performance",
            passed=passed,
            score=score,
            details=f"Avg: {avg_duration:.3f}s (max: {assertion.max_duration_seconds}s)",
            full_output=f"Durations: {durations}",
        )
```

### Step 3: Integrate with CompositeGrader

**File:** `harness/graders/composite_grader.py`

```python
from harness.graders.performance_grader import PerformanceGrader
from harness.models import PerformanceAssertion


class CompositeGrader:
    def __init__(self, ...):
        self.code_grader = CodeGrader()
        self.llm_grader = LLMGrader(...)
        self.performance_grader = PerformanceGrader()

    def grade(self, task, trace, env_path):
        grades = []

        # ... existing code ...

        # Grade performance assertions
        for i, assertion in enumerate(task.performance_assertions):
            grade = self.performance_grader.grade(assertion, env_path)
            grade.assertion_id = f"performance_{i}"
            grades.append(grade)
```

### Step 4: Update Task Model

**File:** `harness/models.py`

```python
class Task(BaseModel):
    # ... existing fields ...

    @property
    def performance_assertions(self) -> list[PerformanceAssertion]:
        """Get only performance-based assertions."""
        return [a for a in self.assertions if isinstance(a, PerformanceAssertion)]
```

### Step 5: Update Task Loading

**File:** `harness/runner.py`

```python
@staticmethod
def load_task(path: Path) -> Task:
    # ... existing code ...

    for a in data.get("assertions", []):
        if a["type"] == "performance":
            assertions.append(
                PerformanceAssertion(
                    type=AssertionType.PERFORMANCE,
                    command=a["command"],
                    max_duration_seconds=a["max_duration_seconds"],
                    warmup_runs=a.get("warmup_runs", 3),
                    benchmark_runs=a.get("benchmark_runs", 10),
                )
            )
```

---

## Creating Custom Configs

Create configuration variants for A/B testing.

### Step 1: Create Config Directory

```bash
mkdir -p evals/configs/my-custom-config
```

### Step 2: Create config.yaml

**File:** `evals/configs/my-custom-config/config.yaml`

```yaml
name: my-custom-config
description: Custom configuration for testing specific behavior

claude_md: |
  # Custom Instructions

  ## Special Behavior
  - Always add type hints
  - Use dataclasses for data structures
  - Prefer composition over inheritance

  ## Forbidden Patterns
  - No global variables
  - No mutable default arguments

skills_path: ~/.claude/skills/custom

model: claude-sonnet-4-20250514
max_turns: 20

# Restrict tools for security testing
allowed_tools:
  - Read
  - Write
  - Bash
  - Grep
  - Glob
```

### Step 3: Use in Evaluations

```bash
# Single run
uv run python -m harness run \
  -t evals/tasks/coding/my-task.yaml \
  -c evals/configs/my-custom-config/config.yaml

# Matrix with custom config
uv run python -m harness matrix \
  -t "evals/tasks/**/*.yaml" \
  -c "evals/configs/my-custom-config/config.yaml"
```

---

## Creating Fixture Projects

Create test codebases for evaluations.

### Step 1: Create Fixture Directory

```bash
mkdir -p fixtures/my-project
cd fixtures/my-project
```

### Step 2: Set Up Project Structure

```
fixtures/my-project/
├── pyproject.toml       # Project dependencies
├── src/
│   ├── __init__.py
│   ├── main.py          # Main application code
│   └── auth.py          # Code with intentional bugs
├── tests/
│   ├── __init__.py
│   ├── test_main.py
│   └── test_auth.py
└── README.md
```

### Step 3: Create pyproject.toml

```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = []

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

### Step 4: Create Code with Intentional Bug

**File:** `fixtures/my-project/src/auth.py`

```python
"""Authentication module with intentional vulnerability."""


def authenticate(username: str, password: str) -> tuple[bool, str]:
    """Authenticate a user.

    Args:
        username: The username
        password: The password

    Returns:
        Tuple of (success, message)

    BUG: This function accepts empty passwords!
    """
    # Vulnerable: doesn't check for empty password
    if username == "admin" and password == "secret":
        return True, "Login successful"

    return False, "Invalid credentials"
```

### Step 5: Create Tests

**File:** `fixtures/my-project/tests/test_auth.py`

```python
"""Tests for authentication module."""

import pytest
from src.auth import authenticate


def test_valid_credentials():
    """Test authentication with valid credentials."""
    success, message = authenticate("admin", "secret")
    assert success is True
    assert "successful" in message.lower()


def test_invalid_credentials():
    """Test authentication with invalid credentials."""
    success, message = authenticate("admin", "wrong")
    assert success is False


def test_empty_password_rejected():
    """Test that empty passwords are rejected.

    This test will FAIL until the bug is fixed!
    """
    success, message = authenticate("admin", "")
    assert success is False, "Empty passwords should be rejected"


def test_none_password_rejected():
    """Test that None passwords are rejected."""
    success, message = authenticate("admin", None)
    assert success is False
```

### Step 6: Initialize Virtual Environment

```bash
cd fixtures/my-project
uv venv
uv sync --extra dev
```

### Step 7: Verify Tests Fail (Bug Present)

```bash
uv run pytest tests/ -v
# test_empty_password_rejected should FAIL
```

### Step 8: Create Task Using Fixture

**File:** `evals/tasks/coding/fix-my-project-auth.task.yaml`

```yaml
id: fix-my-project-auth
category: coding
description: Fix authentication bug in my-project fixture
difficulty: medium

prompt: |
  The authentication in src/auth.py has a bug where empty passwords
  are accepted. Fix this vulnerability.

fixture_path: ../../../fixtures/my-project

assertions:
  - type: code
    check: tests_pass
    command: "pytest tests/test_auth.py -v"

  - type: code
    check: file_contains
    file: "src/auth.py"
    pattern: "not\\s+password|len\\(password\\)"

  - type: llm
    rubric: |
      The fix should:
      - Reject empty passwords
      - Return appropriate error message
      - Handle None gracefully

scoring:
  tests_pass: 60
  file_contains: 20
  llm_quality: 20
```

---

## Customizing Scaffold Templates

Modify the scaffold generator to create custom project structures.

### Step 1: Understand Template Constants

**File:** `harness/scaffold.py`

The scaffold generator uses template constants:
- `README_TEMPLATE`: README.md content
- `BASELINE_CONFIG_TEMPLATE`: Baseline config.yaml
- `WITH_SKILL_CONFIG_TEMPLATE`: With-skill config.yaml
- `TASK_TEMPLATE`: Example task file
- `RUN_COMPARISON_TEMPLATE`: Shell script
- `PYTHON_*_TEMPLATE`: Python fixture files
- `JS_*_TEMPLATE`: JavaScript fixture files

### Step 2: Add New Fixture Types

To add a new fixture type (e.g., Go):

```python
# harness/scaffold.py

GO_MOD_TEMPLATE = """module {name}

go 1.21
"""

GO_MAIN_TEMPLATE = '''package main

func ProcessData(data map[string]string) map[string]string {
    // TODO: Implementation with issues to fix
    return data
}
'''

GO_TEST_TEMPLATE = '''package main

import "testing"

func TestProcessData(t *testing.T) {
    data := map[string]string{"key": "value"}
    result := ProcessData(data)
    if result["key"] != "value" {
        t.Errorf("Expected value, got %s", result["key"])
    }
}
'''

class ScaffoldGenerator:
    def _generate_fixture(self, fixture_type: str) -> None:
        # ... existing code ...

        elif fixture_type == "go":
            content = GO_MOD_TEMPLATE.format(name=f"{self.name}-fixture")
            (fixture_dir / "go.mod").write_text(content)
            (fixture_dir / "main.go").write_text(GO_MAIN_TEMPLATE)
            (fixture_dir / "main_test.go").write_text(GO_TEST_TEMPLATE)
```

### Step 3: Add Fixture Type to CLI

**File:** `harness/__main__.py`

```python
@cli.command()
@click.option(
    "--fixture-type",
    type=click.Choice(["python", "javascript", "go"]),
    default="python",
    help="Type of fixture project to generate",
)
def scaffold(...):
    # ...
```

### Step 4: Update Task Templates

Modify `TASK_TEMPLATE` to include fixture-specific test commands:

```python
def _generate_task(self, fixture_type: str) -> None:
    test_commands = {
        "python": "uv run pytest tests/ -v",
        "javascript": "npm test",
        "go": "go test -v ./...",
    }

    content = TASK_TEMPLATE.format(
        task_id=f"{self.name}-example",
        description="Example task for skill evaluation",
        fixture_name="sample-project",
        test_command=test_commands.get(fixture_type, "echo 'No tests'"),
    )
```

---

## Using Artifact Preservation

Enable artifact preservation for debugging and reproducibility.

### Step 1: Enable via CLI

```bash
uv run python -m harness run \
  -t task.yaml \
  -c config.yaml \
  --preserve-artifacts
```

### Step 2: Enable via Python

```python
runner = EvalRunner(preserve_artifacts=True, artifacts_dir=Path("my-artifacts"))
result = runner.run_single(task, config)
```

### Step 3: Examine Artifacts

```
evals/artifacts/eval_20250131_103022_abc12345/
├── metadata.json          # Run configuration and results
├── fixture_before.tar.gz  # Original fixture state
├── fixture_after.tar.gz   # Modified fixture state
├── file_changes.diff      # Unified diff of changes
├── claude_output.json     # Full Claude response
└── test_output.log        # Test execution output
```

### Step 4: Customize Archive Contents

**File:** `harness/isolator.py`

```python
def archive_run(
    self,
    env: IsolatedEnv,
    run_id: str,
    artifacts_dir: Path,
    before_state: dict[str, str],
    metadata: dict[str, Any] | None = None,
    claude_output: dict[str, Any] | None = None,
    test_output: str | None = None,
    custom_files: dict[str, str] | None = None,  # Add custom files
) -> Path:
    # ... existing code ...

    # Add custom files to archive
    if custom_files:
        for filename, content in custom_files.items():
            (archive_dir / filename).write_text(content)
```
