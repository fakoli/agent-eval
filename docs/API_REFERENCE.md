# API Reference

Complete reference for all public classes, methods, and data models in the agent-eval harness.

## Table of Contents

- [Data Models](#data-models)
  - [Task](#task)
  - [Config](#config)
  - [Assertions](#assertions)
  - [ExecutionTrace](#executiontrace)
  - [GradeResult](#graderesult)
  - [EvalResult](#evalresult)
  - [Supporting Models](#supporting-models)
- [Core Components](#core-components)
  - [EvalRunner](#evalrunner)
  - [Executor](#executor)
  - [EnvironmentIsolator](#environmentisolator)
  - [CompositeGrader](#compositegrader)
  - [Reporter](#reporter)
- [Configuration Management](#configuration-management)
  - [ConfigExporter](#configexporter)
  - [ConfigImporter](#configimporter)

---

## Data Models

All data models are defined in `harness/models.py` using Pydantic for validation and serialization.

### Task

Definition of an evaluation task.

```python
class Task(BaseModel):
    id: str                                    # Unique identifier
    category: TaskCategory                     # coding, refactoring, exploration
    description: str                           # What this task tests
    difficulty: TaskDifficulty = "medium"      # easy, medium, hard
    prompt: str                                # The prompt to execute
    assertions: list[CodeAssertion | LLMAssertion] = []  # Grading criteria
    scoring: dict[str, float] = {}             # Weight per assertion
    fixture_path: Path | None = None           # Test codebase location
    timeout_seconds: int = 300                 # Max execution time
```

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `code_assertions` | `list[CodeAssertion]` | Filters to code-based assertions only |
| `llm_assertions` | `list[LLMAssertion]` | Filters to LLM-based assertions only |

#### Enums

**TaskCategory**
```python
class TaskCategory(str, Enum):
    CODING = "coding"           # Bug fixes, new features
    REFACTORING = "refactoring" # Code improvements
    EXPLORATION = "exploration"  # Code analysis tasks
```

**TaskDifficulty**
```python
class TaskDifficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
```

---

### Config

Configuration variant for evaluation runs.

```python
class Config(BaseModel):
    name: str                              # Config variant name
    description: str = ""                  # What this tests
    claude_md: str | None = None           # CLAUDE.md content to inject
    skills_path: Path | None = None        # Path to skills directory
    agents_md: str | None = None           # Agents definition content
    model: str = "claude-sonnet-4-20250514"  # Model ID
    max_turns: int = 10                    # Turn limit
    allowed_tools: list[str] | "all" = "all"  # Tool restrictions
```

---

### Assertions

#### AssertionType

```python
class AssertionType(str, Enum):
    CODE = "code"  # Objective, deterministic checks
    LLM = "llm"    # Subjective, LLM-evaluated quality
```

#### CodeAssertion

Code-based assertion for objective checks.

```python
class CodeAssertion(Assertion):
    type: Literal[AssertionType.CODE] = AssertionType.CODE
    check: CodeCheckType          # Type of check to perform
    command: str | None = None    # Command to run (for tests_pass, command_succeeds)
    file: str | None = None       # File path (for file_* checks)
    pattern: str | None = None    # Regex pattern (for file_contains/not_contains)
```

**CodeCheckType**
```python
class CodeCheckType(str, Enum):
    TESTS_PASS = "tests_pass"              # Run pytest, check exit code
    FILE_CONTAINS = "file_contains"         # Regex pattern matching
    FILE_EXISTS = "file_exists"             # File existence check
    FILE_NOT_CONTAINS = "file_not_contains" # Inverse pattern matching
    COMMAND_SUCCEEDS = "command_succeeds"   # Arbitrary command execution
```

#### LLMAssertion

LLM-based assertion for quality evaluation.

```python
class LLMAssertion(Assertion):
    type: Literal[AssertionType.LLM] = AssertionType.LLM
    rubric: str  # Evaluation criteria for LLM grader
```

---

### ExecutionTrace

Trace of a Claude Code execution.

```python
class ExecutionTrace(BaseModel):
    session_id: str | None = None          # Claude session ID
    result: str = ""                       # Final response text
    is_error: bool = False                 # Did execution fail?
    usage: TokenUsage                      # Token counts
    tool_calls: list[ToolCall] = []        # Tools used during execution
    duration_seconds: float = 0.0          # Wall clock time
    num_turns: int = 0                     # API round trips
    raw_output: dict[str, Any] = {}        # Full CLI output

    # Enhanced execution data
    file_changes: list[FileChange] = []    # Files modified
    claude_prompt: str = ""                # The actual prompt sent
    claude_response: str = ""              # Full response text
    config_snapshot: ConfigSnapshot        # Config used
    max_turns: int = 0                     # Turn limit for context
    hit_turn_limit: bool = False           # Reached max_turns?
    stderr: str = ""                       # Capture stderr
```

#### TokenUsage

```python
class TokenUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
```

#### ToolCall

```python
class ToolCall(BaseModel):
    name: str                         # Tool name
    input: dict[str, Any] = {}        # Tool input parameters
    output: str | None = None         # Tool output
    error: str | None = None          # Error if failed
    timestamp: datetime | None = None # When called
```

#### FileChange

```python
class FileChange(BaseModel):
    path: str                              # Relative file path
    action: Literal["created", "modified", "deleted"]
    diff: str | None = None                # Unified diff for modifications
    content_after: str | None = None       # Full content for created files
```

---

### GradeResult

Result of grading a single assertion.

```python
class GradeResult(BaseModel):
    assertion_id: str = ""             # Unique identifier
    assertion_type: str = ""           # "code" or "llm"
    assertion_name: str = ""           # Human-readable name
    passed: bool                       # Did the assertion pass?
    score: float                       # 0.0 to 1.0
    details: str = ""                  # Summary details
    reasoning: str = ""                # Explanation of score

    # Enhanced grading context
    full_output: str = ""              # Untruncated output
    grading_prompt: str = ""           # For LLM grades: prompt used
    criteria_scores: list[CriterionScore] = []  # Breakdown
```

#### CriterionScore

```python
class CriterionScore(BaseModel):
    criterion: str           # What was evaluated
    score: float             # 0.0 to 1.0
    reasoning: str = ""      # Why this score
```

---

### EvalResult

Complete result of an evaluation run.

```python
class EvalResult(BaseModel):
    task_id: str                     # Which task
    config_name: str                 # Which config
    model: str                       # Which model
    run_index: int                   # Run number (for pass@k)
    timestamp: datetime              # When executed
    trace: ExecutionTrace            # Full execution data
    grades: list[GradeResult] = []   # Individual assertion grades
    overall_score: float = 0.0       # Weighted combined score (0.0-1.0)
    passed: bool = False             # Met passing threshold?
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `calculate_overall_score` | `weights: dict[str, float]` | `float` | Calculate weighted score from grades |

---

### Supporting Models

#### ConfigSnapshot

Snapshot of configuration used for a run.

```python
class ConfigSnapshot(BaseModel):
    model: str = ""
    claude_md: str | None = None      # First 200 chars for context
    skills_path: str | None = None
    max_turns: int = 0
```

#### ClaudeConfigSnapshot

Snapshot for CI reproducibility.

```python
class ClaudeConfigSnapshot(BaseModel):
    claude_version: str = ""
    snapshot_timestamp: datetime
    global_claude_md: str | None = None
    settings: dict[str, Any] = {}
    mcp_servers: dict[str, Any] = {}
    skills: dict[str, str] = {}        # path -> content
    source_machine: str                # platform.node()
```

---

## Core Components

### EvalRunner

Orchestrates evaluation runs across tasks, configs, and models.

**Location:** `harness/runner.py`

```python
class EvalRunner:
    def __init__(
        self,
        executor: Executor | None = None,
        grader: CompositeGrader | None = None,
        isolator: EnvironmentIsolator | None = None,
        results_dir: Path | None = None,
    )
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `run_single` | `task: Task, config: Config, run_index: int = 0` | `EvalResult` | Run single task with single config |
| `run_matrix` | `tasks, configs, models, runs_per_combo, callback` | `list[EvalResult]` | Run full evaluation matrix |
| `save_results` | `results: list[EvalResult], filename: str | None, save_debug: bool` | `Path` | Save results to JSON |
| `load_results` | `path: Path` | `list[EvalResult]` | Load results from JSON file |
| `load_task` | `path: Path` | `Task` | Load task from YAML file (static) |
| `load_config` | `path: Path` | `Config` | Load config from YAML file (static) |
| `load_tasks_from_glob` | `pattern: str` | `list[Task]` | Load all tasks matching glob |
| `load_configs_from_glob` | `pattern: str` | `list[Config]` | Load all configs matching glob |

#### Example Usage

```python
from harness.runner import EvalRunner

runner = EvalRunner()

# Load task and config
task = runner.load_task(Path("evals/tasks/coding/fix-auth-bypass.task.yaml"))
config = runner.load_config(Path("evals/configs/full/config.yaml"))

# Run single evaluation
result = runner.run_single(task, config)

# Run matrix evaluation
tasks = runner.load_tasks_from_glob("evals/tasks/**/*.task.yaml")
configs = runner.load_configs_from_glob("evals/configs/*/config.yaml")
results = runner.run_matrix(tasks, configs, runs_per_combo=3)

# Save results
runner.save_results(results, "results.json")
```

---

### Executor

Abstract base class for code execution.

**Location:** `harness/executor.py`

```python
class Executor(ABC):
    @abstractmethod
    def run(
        self,
        prompt: str,
        config: Config,
        working_dir: Path,
        timeout: int = 300,
        env_override: dict[str, str] | None = None,
    ) -> ExecutionTrace
```

#### ClaudeExecutor

Executor that uses the Claude Code CLI.

```python
class ClaudeExecutor(Executor):
    def __init__(
        self,
        claude_path: str = "claude",
        ci_mode: bool = False,
        mcp_config_path: Path | None = None,
        skip_permissions: bool = True,
    )
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `claude_path` | `str` | `"claude"` | Path to claude CLI executable |
| `ci_mode` | `bool` | `False` | Adds isolation flags for CI |
| `mcp_config_path` | `Path | None` | `None` | Optional MCP config file for CI |
| `skip_permissions` | `bool` | `True` | Skip permission checks for automation |

#### Internal Methods

| Method | Description |
|--------|-------------|
| `_build_command` | Build CLI command with all flags |
| `_parse_output` | Parse CLI output into ExecutionTrace |
| `_extract_tool_calls` | Extract tool calls from JSON output |

---

### EnvironmentIsolator

Creates isolated environments for evaluation runs.

**Location:** `harness/isolator.py`

```python
class EnvironmentIsolator:
    def __init__(self, base_dir: Path | None = None)
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `create_environment` | `fixture_path, claude_md, skills_path, agents_md` | `IsolatedEnv` | Create isolated test environment |
| `create_environment_for_task` | `task_fixture, claude_md, skills_path, agents_md` | `IsolatedEnv` | Convenience method using task fixture |
| `snapshot_files` | `env_path: Path, patterns: list[str] | None` | `dict[str, str]` | Capture file contents before execution |
| `diff_files` | `before: dict, env_path: Path, patterns: list[str] | None` | `list[FileChange]` | Calculate file changes after execution |

#### IsolatedEnv

Context manager for isolated environments.

```python
@dataclass
class IsolatedEnv:
    path: Path           # Working directory path
    temp_root: Path      # Root temp directory

    def cleanup(self) -> None
    def __enter__(self) -> "IsolatedEnv"
    def __exit__(self, exc_type, exc_val, exc_tb) -> None
```

#### Example Usage

```python
from harness.isolator import EnvironmentIsolator

isolator = EnvironmentIsolator()

with isolator.create_environment(
    fixture_path=Path("fixtures/sample-project"),
    claude_md="# Instructions...",
    skills_path=Path("~/.claude/skills"),
) as env:
    # env.path is the isolated working directory
    # Run execution here
    pass
# Automatic cleanup on exit
```

---

### CompositeGrader

Combines code and LLM graders with weighted scoring.

**Location:** `harness/graders/composite_grader.py`

```python
class CompositeGrader:
    def __init__(
        self,
        llm_model: str = "claude-3-5-haiku-20241022",
        api_key: str | None = None,
    )
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `grade` | `task, trace, env_path` | `tuple[list[GradeResult], float, bool]` | Grade all assertions, return (grades, score, passed) |
| `grade_single_assertion` | `assertion, task, trace, env_path` | `GradeResult` | Grade a single assertion |

#### CodeGrader

**Location:** `harness/graders/code_graders.py`

```python
class CodeGrader:
    def grade(self, assertion: CodeAssertion, env_path: Path) -> GradeResult
    def grade_tests_pass(self, env_path: Path, command: str) -> GradeResult
    def grade_file_contains(self, env_path: Path, file: str, pattern: str) -> GradeResult
    def grade_file_not_contains(self, env_path: Path, file: str, pattern: str) -> GradeResult
    def grade_file_exists(self, env_path: Path, file: str) -> GradeResult
    def grade_command_succeeds(self, env_path: Path, command: str) -> GradeResult
```

#### LLMGrader

**Location:** `harness/graders/llm_graders.py`

```python
class LLMGrader:
    def __init__(
        self,
        model: str = "claude-3-5-haiku-20241022",
        api_key: str | None = None,
    )

    def grade(
        self,
        assertion: LLMAssertion,
        task: Task,
        trace: ExecutionTrace,
        env_path: Path,
    ) -> GradeResult
```

---

### Reporter

Generates reports from evaluation results.

**Location:** `harness/reporter.py`

```python
class Reporter:
    def __init__(self, console: Console | None = None)
```

#### Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `print_summary` | `results: list[EvalResult]` | `None` | Print summary table |
| `print_regression_comparison` | `baseline, current` | `None` | Compare baseline vs current |
| `print_detailed_result` | `result, verbose=False` | `None` | Detailed view of single result |
| `print_analysis` | `results, task_filter, failed_only` | `None` | Filtered analysis with breakdowns |
| `print_diff` | `results_a, results_b, label_a, label_b` | `None` | Side-by-side comparison |
| `print_explain` | `result: EvalResult` | `None` | Deep dive with full context |
| `export_json` | `results, path` | `None` | Export to JSON file |
| `check_regression` | `baseline, current, threshold=0.05` | `tuple[bool, dict]` | Check for regressions |

#### AggregatedMetrics

```python
@dataclass
class AggregatedMetrics:
    total_runs: int
    passed: int
    failed: int
    pass_rate: float
    avg_score: float
    avg_tokens: int
    avg_duration: float
    pass_at_k: dict[int, float]  # k -> probability
```

---

## Configuration Management

### ConfigExporter

Exports Claude Code configuration for CI reproducibility.

**Location:** `harness/config_exporter.py`

```python
class ConfigExporter:
    def __init__(self, claude_home: Path | None = None)

    def export_snapshot(self) -> ClaudeConfigSnapshot
    def save_snapshot(self, output_path: Path) -> None
```

Captures:
- Claude CLI version
- Global CLAUDE.md content
- Settings from settings.json
- MCP server configurations
- Skills (all .md files from skills directory)

---

### ConfigImporter

Sets up Claude Code environment in CI from snapshot.

**Location:** `harness/config_importer.py`

```python
class ConfigImporter:
    def setup_ci_environment(
        self,
        snapshot: ClaudeConfigSnapshot,
        temp_dir: Path,
        disable_mcp: bool = True,
    ) -> dict[str, str]  # Returns env vars to set

    def load_snapshot(self, snapshot_path: Path) -> ClaudeConfigSnapshot
```

CI Environment Setup:
- Creates `.claude` directory structure
- Writes global CLAUDE.md
- Sanitizes settings (disables analytics/telemetry)
- Optionally disables MCP servers
- Restores skills
- Returns environment variables to set (`HOME`, `CLAUDE_HOME`)
