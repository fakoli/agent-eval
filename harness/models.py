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
    RUFF_CLEAN = "ruff_clean"
    MYPY_CLEAN = "mypy_clean"


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
    # Calibration examples for anchoring LLM scoring (research-based)
    passing_example: str | None = None
    failing_example: str | None = None
    borderline_example: str | None = None


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
    # Optional per-task pass threshold (overrides difficulty-based threshold)
    pass_threshold: float | None = None

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


class CostMetrics(BaseModel):
    """Cost tracking for evaluation runs."""

    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    total_cost_usd: float = 0.0

    @classmethod
    def from_usage(
        cls,
        usage: "TokenUsage",
        input_cost_per_1m: float = 3.0,
        output_cost_per_1m: float = 15.0,
    ) -> "CostMetrics":
        """Calculate costs from token usage.

        Default prices are for Claude 3.5 Sonnet.
        """
        input_cost = (usage.input_tokens / 1_000_000) * input_cost_per_1m
        output_cost = (usage.output_tokens / 1_000_000) * output_cost_per_1m
        return cls(
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            total_cost_usd=input_cost + output_cost,
        )


class ToolCallPattern(BaseModel):
    """Behavioral patterns extracted from tool calls."""

    read_before_write: bool = False  # Good practice indicator
    test_driven: bool = False  # Ran tests early
    error_recovery_attempts: int = 0  # How many fix cycles
    exploration_ratio: float = 0.0  # Read vs Write ratio

    @classmethod
    def from_tool_calls(cls, tool_calls: list["ToolCall"]) -> "ToolCallPattern":
        """Analyze tool calls to extract behavioral patterns."""
        if not tool_calls:
            return cls()

        read_tools = {"Read", "Glob", "Grep", "LS"}
        write_tools = {"Write", "Edit"}
        test_tools = {"Bash"}  # Detect pytest/test commands

        read_count = 0
        write_count = 0
        first_write_idx = None
        first_read_idx = None
        first_test_idx = None
        error_count = 0

        for idx, tc in enumerate(tool_calls):
            if tc.name in read_tools:
                read_count += 1
                if first_read_idx is None:
                    first_read_idx = idx
            if tc.name in write_tools:
                write_count += 1
                if first_write_idx is None:
                    first_write_idx = idx
            if tc.name in test_tools and tc.input:
                cmd = tc.input.get("command", "")
                if "pytest" in cmd or "test" in cmd.lower():
                    if first_test_idx is None:
                        first_test_idx = idx
            if tc.error:
                error_count += 1

        # Calculate patterns
        read_before_write = (
            first_read_idx is not None
            and first_write_idx is not None
            and first_read_idx < first_write_idx
        )
        test_driven = (
            first_test_idx is not None
            and first_write_idx is not None
            and first_test_idx < first_write_idx
        )
        total_rw = read_count + write_count
        exploration_ratio = read_count / total_rw if total_rw > 0 else 0.0

        return cls(
            read_before_write=read_before_write,
            test_driven=test_driven,
            error_recovery_attempts=error_count,
            exploration_ratio=exploration_ratio,
        )


class ReadabilityMetrics(BaseModel):
    """Readability metrics for CLAUDE.md content quality."""

    flesch_reading_ease: float = 0.0
    flesch_kincaid_grade: float = 0.0
    word_count: int = 0
    sentence_count: int = 0
    is_accessible: bool = False  # FRE >= 50

    @classmethod
    def from_content(cls, content: str) -> "ReadabilityMetrics":
        """Calculate readability metrics from text content.

        Requires textstat package.
        """
        try:
            import textstat

            fre = textstat.flesch_reading_ease(content)
            fkg = textstat.flesch_kincaid_grade(content)
            words = textstat.lexicon_count(content, removepunct=True)
            sentences = textstat.sentence_count(content)

            return cls(
                flesch_reading_ease=fre,
                flesch_kincaid_grade=fkg,
                word_count=words,
                sentence_count=sentences,
                is_accessible=fre >= 50,
            )
        except ImportError:
            # textstat not installed
            words = len(content.split())
            return cls(
                flesch_reading_ease=0.0,
                flesch_kincaid_grade=0.0,
                word_count=words,
                sentence_count=0,
                is_accessible=False,
            )


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
