"""Core data models for the evaluation harness."""

from abc import ABC
from datetime import datetime
from enum import Enum
from pathlib import Path
import platform
from typing import Any, Literal

from pydantic import BaseModel, Field


class FileChange(BaseModel):
    """Record of a file modification during execution."""

    path: str
    action: Literal["created", "modified", "deleted"]
    diff: str | None = None  # unified diff for modifications
    content_after: str | None = None  # full content for created files


class TaskCategory(str, Enum):
    """Categories of evaluation tasks."""

    CODING = "coding"
    REFACTORING = "refactoring"
    EXPLORATION = "exploration"


class TaskDifficulty(str, Enum):
    """Difficulty levels for tasks."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class AssertionType(str, Enum):
    """Types of assertions for grading."""

    CODE = "code"
    LLM = "llm"


class CodeCheckType(str, Enum):
    """Types of code-based checks."""

    TESTS_PASS = "tests_pass"
    FILE_CONTAINS = "file_contains"
    FILE_EXISTS = "file_exists"
    FILE_NOT_CONTAINS = "file_not_contains"
    COMMAND_SUCCEEDS = "command_succeeds"


class Assertion(BaseModel, ABC):
    """Base class for assertions."""

    type: AssertionType


class CodeAssertion(Assertion):
    """Code-based assertion for objective checks."""

    type: Literal[AssertionType.CODE] = AssertionType.CODE
    check: CodeCheckType
    command: str | None = None
    file: str | None = None
    pattern: str | None = None


class LLMAssertion(Assertion):
    """LLM-based assertion for quality evaluation."""

    type: Literal[AssertionType.LLM] = AssertionType.LLM
    rubric: str


class Task(BaseModel):
    """Definition of an evaluation task."""

    id: str
    category: TaskCategory
    description: str
    difficulty: TaskDifficulty = TaskDifficulty.MEDIUM
    prompt: str
    assertions: list[CodeAssertion | LLMAssertion] = Field(default_factory=list)
    scoring: dict[str, float] = Field(default_factory=dict)
    fixture_path: Path | None = None
    timeout_seconds: int = 300

    @property
    def code_assertions(self) -> list[CodeAssertion]:
        """Get only code-based assertions."""
        return [a for a in self.assertions if isinstance(a, CodeAssertion)]

    @property
    def llm_assertions(self) -> list[LLMAssertion]:
        """Get only LLM-based assertions."""
        return [a for a in self.assertions if isinstance(a, LLMAssertion)]


class Config(BaseModel):
    """Configuration variant for evaluation."""

    name: str
    description: str = ""
    claude_md: str | None = None
    skills_path: Path | None = None
    agents_md: str | None = None
    model: str = "claude-sonnet-4-20250514"
    max_turns: int = 10
    allowed_tools: list[str] | Literal["all"] = "all"


class ToolCall(BaseModel):
    """Record of a tool call made during execution."""

    name: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: str | None = None
    error: str | None = None
    timestamp: datetime | None = None


class TokenUsage(BaseModel):
    """Token usage statistics."""

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens


class ConfigSnapshot(BaseModel):
    """Snapshot of configuration used for a run."""

    model: str = ""
    claude_md: str | None = None  # First 200 chars for context
    skills_path: str | None = None
    max_turns: int = 0


class ExecutionTrace(BaseModel):
    """Trace of a Claude Code execution."""

    session_id: str | None = None
    result: str = ""
    is_error: bool = False
    usage: TokenUsage = Field(default_factory=TokenUsage)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    duration_seconds: float = 0.0
    num_turns: int = 0
    raw_output: dict[str, Any] = Field(default_factory=dict)

    # Enhanced execution data
    file_changes: list[FileChange] = Field(default_factory=list)
    claude_prompt: str = ""  # The actual prompt sent
    claude_response: str = ""  # Full response text
    config_snapshot: ConfigSnapshot = Field(default_factory=ConfigSnapshot)
    max_turns: int = 0  # Turn limit for context
    hit_turn_limit: bool = False
    stderr: str = ""  # Capture stderr from execution


class CriterionScore(BaseModel):
    """Score for a single criterion in LLM grading."""

    criterion: str
    score: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""


class GradeResult(BaseModel):
    """Result of grading a single assertion."""

    assertion_id: str = ""
    assertion_type: str = ""  # "code" or "llm"
    assertion_name: str = ""  # Human-readable (e.g., "tests_pass", "file_contains")
    passed: bool
    score: float = Field(ge=0.0, le=1.0)
    details: str = ""
    reasoning: str = ""

    # Enhanced grading context
    full_output: str = ""  # Untruncated test output or LLM response
    grading_prompt: str = ""  # For LLM grades: the prompt used
    criteria_scores: list[CriterionScore] = Field(default_factory=list)  # Breakdown


class EvalResult(BaseModel):
    """Complete result of an evaluation run."""

    task_id: str
    config_name: str
    model: str
    run_index: int
    timestamp: datetime = Field(default_factory=datetime.now)
    trace: ExecutionTrace
    grades: list[GradeResult] = Field(default_factory=list)
    overall_score: float = Field(ge=0.0, le=1.0, default=0.0)
    passed: bool = False

    def calculate_overall_score(self, weights: dict[str, float]) -> float:
        """Calculate weighted overall score from individual grades."""
        if not self.grades or not weights:
            return 0.0

        total_weight = sum(weights.values())
        if total_weight == 0:
            return 0.0

        weighted_sum = 0.0
        for grade in self.grades:
            weight = weights.get(grade.assertion_id, 0.0)
            weighted_sum += grade.score * weight

        return weighted_sum / total_weight


class ClaudeConfigSnapshot(BaseModel):
    """Snapshot of Claude Code configuration for CI reproducibility.

    This model captures the user's Claude Code environment so it can be
    replicated in CI environments for consistent evaluation runs.
    """

    claude_version: str = ""
    snapshot_timestamp: datetime = Field(default_factory=datetime.now)
    global_claude_md: str | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    mcp_servers: dict[str, Any] = Field(default_factory=dict)
    skills: dict[str, str] = Field(default_factory=dict)
    source_machine: str = Field(default_factory=lambda: platform.node())
