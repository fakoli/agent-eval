# Architecture

This document describes the technical architecture of agent-eval.

## Vision: Three-Layer System

agent-eval is designed as the **evaluation layer** of a larger vision for managing agent instructions across multi-agent development environments.

```
Layer 1: Canonical Specification (future)
         ├── Tool-agnostic instruction format
         └── Single source of truth for behaviors

Layer 2: Tool Adapters (future)
         ├── Claude Code adapter → CLAUDE.md
         ├── Cursor adapter → .cursorrules
         └── Future tool adapters

Layer 3: Evaluation Harness (this project)
         ├── Behavioral regression testing
         ├── A/B comparison across configurations
         └── CI/CD integration
```

The current implementation focuses on **Layer 3**: a CI evaluation harness that detects behavioral regressions when agent instructions change. Layers 1 and 2 represent future work toward a unified multi-agent instruction system.

## Current Implementation

### Core Components

```
harness/
├── __main__.py          # CLI entry point (Click commands)
├── runner.py            # EvalRunner - orchestrates test matrix
├── executor.py          # Executor ABC + ClaudeExecutor
├── container_executor.py # ContainerExecutor - Docker-based execution
├── container_manager.py # Docker lifecycle management
├── isolator.py          # EnvironmentIsolator - temp dir + artifact archiving
├── scaffold.py          # ScaffoldGenerator - skill-testing templates
├── reporter.py          # Result formatting and comparison
├── statistics.py        # Statistical analysis (Mann-Whitney U, power analysis, efficiency)
├── models.py            # Pydantic data models
├── config_exporter.py   # Export Claude config for CI
├── config_importer.py   # Import Claude config in CI
└── graders/
    ├── code_graders.py      # Objective checks (tests, files)
    ├── llm_graders.py       # LLM-as-judge evaluation
    └── composite_grader.py  # Combined grading logic

docker/
├── Dockerfile           # Container image definition
└── entrypoint.sh        # Container entry script
```

### Execution Flow

```
1. Load Task & Config
   ├── Parse .task.yaml (prompt, assertions, scoring)
   └── Parse config.yaml (model, CLAUDE.md, skills)
                 │
                 ▼
2. Create Isolated Environment
   ├── Create temp directory
   ├── Copy fixture project files
   ├── Inject CLAUDE.md, skills, agents.md
   └── Snapshot file state (for diff tracking)
                 │
                 ▼
3. Execute Prompt
   ├── Build Claude CLI command
   ├── Run with JSON output format
   ├── Capture stdout, stderr, timing
   └── Parse ExecutionTrace
                 │
                 ▼
4. Grade Results
   ├── Code graders: run tests, check files
   ├── LLM grader: evaluate against rubric
   └── Combine scores with weights
                 │
                 ▼
5. Report Results
   ├── EvalResult with scores, trace, grades
   ├── Save to JSON (summary + debug)
   └── Optional regression comparison
```

### Key Abstractions

#### Executor (ABC)

The `Executor` abstract base class defines the interface for running prompts:

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
    ) -> ExecutionTrace:
        pass
```

Currently implemented:
- `ClaudeExecutor`: Wraps the Claude Code CLI
- `ContainerExecutor`: Runs Claude Code in isolated Docker containers

Designed for future extension:
- `CursorExecutor`: Could wrap Cursor IDE automation
- `MockExecutor`: For testing without actual LLM calls

#### ContainerExecutor

For isolated execution, the `ContainerExecutor` runs evaluations inside Docker containers:

```python
from harness.container_executor import ContainerExecutor

executor = ContainerExecutor(
    network_enabled=True,   # Allow dependency fetching
    memory_limit="4g",      # Resource limits
    cpu_limit=2.0,
)
runner = EvalRunner(executor=executor)
```

The container provides:
- **Isolation**: Prevents bad evals from affecting the host
- **Resource limits**: Memory and CPU constraints
- **Non-root execution**: Runs as `eval` user inside container
- **Auto-cleanup**: Containers removed after execution

#### CompositeGrader

Combines multiple grading strategies:

```python
grader.grade(task, trace, working_dir) -> (grades, overall_score, passed)
```

- **CodeGrader**: Objective checks (tests pass, file contains pattern)
- **LLMGrader**: Subjective quality evaluation using Claude Haiku

Scores are combined using weights from the task definition.

#### EnvironmentIsolator

Manages execution isolation:

```python
with isolator.create_environment(
    fixture_path=task.fixture_path,
    claude_md=config.claude_md,
    skills_path=config.skills_path,
) as env:
    # env.path is a temp directory with all files
    trace = executor.run(prompt, config, env.path)
```

Features:
- Creates temp directory per run
- Copies fixture project files
- Injects configuration files (CLAUDE.md, agents.md)
- Tracks file changes (before/after diff)
- Automatic cleanup on exit
- **Artifact archiving** for reproducibility

#### Artifact Preservation

When `preserve_artifacts=True`, the isolator archives each run:

```python
runner = EvalRunner(preserve_artifacts=True)
# Archives saved to evals/artifacts/{run_id}/
```

Archive contents:
- `metadata.json`: Run configuration and results summary
- `fixture_before.tar.gz`: Original fixture state
- `fixture_after.tar.gz`: Modified fixture state
- `file_changes.diff`: Unified diff of all changes
- `claude_output.json`: Full Claude execution output
- `test_output.log`: Test execution output

#### ScaffoldGenerator

Generates skill-testing directory structures:

```python
from harness.scaffold import ScaffoldGenerator

generator = ScaffoldGenerator(name="my-skill-test")
generator.generate(fixture_type="python", skill_path=Path("~/.claude/skills/my-skill"))
```

Generated structure:
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

## Data Models

### Task

```python
class Task(BaseModel):
    id: str                          # Unique identifier
    category: TaskCategory           # coding, refactoring, exploration
    description: str                 # What this task tests
    difficulty: TaskDifficulty       # easy, medium, hard
    prompt: str                      # The prompt to execute
    assertions: list[Assertion]      # Code and LLM assertions
    scoring: dict[str, float]        # Weight per assertion
    fixture_path: Path | None        # Test codebase location
    timeout_seconds: int             # Max execution time
```

### Config

```python
class Config(BaseModel):
    name: str                        # Config variant name
    description: str                 # What this tests
    claude_md: str | None            # CLAUDE.md content
    skills_path: Path | None         # Skills directory
    agents_md: str | None            # Agents definition
    model: str                       # Model ID
    max_turns: int                   # Turn limit
    allowed_tools: list[str] | "all" # Tool restrictions
```

### ExecutionTrace

```python
class ExecutionTrace(BaseModel):
    session_id: str | None           # Claude session ID
    result: str                      # Final response
    is_error: bool                   # Did execution fail?
    usage: TokenUsage                # Token counts
    tool_calls: list[ToolCall]       # Tools used
    duration_seconds: float          # Wall clock time
    num_turns: int                   # API round trips
    file_changes: list[FileChange]   # Files modified
    hit_turn_limit: bool             # Reached max_turns?
```

### EvalResult

```python
class EvalResult(BaseModel):
    task_id: str                     # Which task
    config_name: str                 # Which config
    model: str                       # Which model
    run_index: int                   # Run number (for pass@k)
    timestamp: datetime              # When executed
    trace: ExecutionTrace            # Full execution data
    grades: list[GradeResult]        # Individual assertion grades
    overall_score: float             # Weighted combined score
    passed: bool                     # Met passing threshold?
```

## Extension Points

### Adding New Executors

1. Subclass `Executor` in `harness/executor.py`
2. Implement the `run()` method
3. Return an `ExecutionTrace` with populated fields

### Adding New Graders

1. Add check logic to `harness/graders/code_graders.py`
2. Register the check type in `CodeCheckType` enum
3. Handle in `CodeGrader.grade()` method

### Adding New Assertion Types

1. Add to `AssertionType` enum in `models.py`
2. Create Pydantic model for the assertion
3. Update `EvalRunner.load_task()` to parse it
4. Add corresponding grader logic

## CI Integration

### Config Export/Import

For reproducible CI runs, export local Claude config:

```bash
# On developer machine
uv run python -m harness export-config -o ci-snapshot.json

# In CI environment
uv run python -m harness import-config -s ci-snapshot.json -o /tmp/ci-home
```

This captures:
- Claude CLI version
- Global CLAUDE.md
- Settings
- MCP servers
- Skills

### Buildkite Integration

See `buildkite/` directory for pipeline configuration:

```yaml
# Run evaluation matrix
uv run python -m harness matrix \
  --tasks "evals/tasks/**/*.task.yaml" \
  --configs "evals/configs/*/config.yaml" \
  --runs 3
```

## File Organization

```
agent-eval/
├── evals/
│   ├── tasks/                    # Task definitions
│   │   ├── coding/               # Bug fixes, features
│   │   │   ├── fix-auth-bypass.task.yaml
│   │   │   └── add-pagination.task.yaml
│   │   └── exploration/          # Analysis tasks
│   │       └── find-auth-flow.task.yaml
│   ├── configs/                  # Configuration variants
│   │   ├── baseline/             # Control (no customization)
│   │   ├── skills-only/          # Skills without CLAUDE.md
│   │   ├── claude-md-only/       # CLAUDE.md without skills
│   │   └── full/                 # Everything enabled
│   └── results/                  # Output (gitignored)
├── fixtures/
│   └── sample-project/           # Test codebase with bugs
│       ├── src/
│       └── tests/
├── harness/                      # Core implementation
├── tests/                        # Harness unit tests
└── docs/                         # Documentation
```

## Performance Considerations

- Each evaluation run creates a temp directory (I/O bound)
- Claude API calls are the primary latency source
- LLM grading adds additional API calls (uses Haiku for cost efficiency)
- Matrix runs are currently sequential (parallelization is a future improvement)

## Security Notes

- API keys should be in `.env` (gitignored)
- Evaluation results may contain sensitive data (gitignored)
- `.claude/` directory is user-specific (gitignored)
- Fixture projects run arbitrary code in temp directories
