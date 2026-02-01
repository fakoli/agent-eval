"""Tests for the enhanced models."""

import pytest
from datetime import datetime

from harness.models import (
    CodeCheckType,
    CostMetrics,
    LLMAssertion,
    ReadabilityMetrics,
    Task,
    TaskCategory,
    TaskDifficulty,
    TokenUsage,
    ToolCall,
    ToolCallPattern,
)


class TestLLMAssertionCalibration:
    """Tests for LLM assertion calibration examples."""

    def test_basic_assertion(self):
        """Basic LLM assertion without calibration examples."""
        assertion = LLMAssertion(
            rubric="The code should validate input correctly."
        )
        assert assertion.rubric == "The code should validate input correctly."
        assert assertion.passing_example is None
        assert assertion.failing_example is None
        assert assertion.borderline_example is None

    def test_with_calibration_examples(self):
        """LLM assertion with calibration examples."""
        assertion = LLMAssertion(
            rubric="The code should validate input correctly.",
            passing_example="def validate(x): return x > 0",
            failing_example="def validate(x): return True",
            borderline_example="def validate(x): return x >= 0",
        )
        assert assertion.passing_example is not None
        assert assertion.failing_example is not None
        assert assertion.borderline_example is not None


class TestTaskPassThreshold:
    """Tests for per-task pass threshold."""

    def test_default_threshold(self):
        """Task without explicit threshold uses None."""
        task = Task(
            id="test",
            category=TaskCategory.CODING,
            description="Test task",
            prompt="Fix the bug",
        )
        assert task.pass_threshold is None

    def test_custom_threshold(self):
        """Task with explicit threshold."""
        task = Task(
            id="test",
            category=TaskCategory.CODING,
            description="Test task",
            prompt="Fix the bug",
            pass_threshold=0.9,
        )
        assert task.pass_threshold == 0.9


class TestCodeCheckTypeExtensions:
    """Tests for new code check types."""

    def test_ruff_clean_exists(self):
        """RUFF_CLEAN check type exists."""
        assert CodeCheckType.RUFF_CLEAN.value == "ruff_clean"

    def test_mypy_clean_exists(self):
        """MYPY_CLEAN check type exists."""
        assert CodeCheckType.MYPY_CLEAN.value == "mypy_clean"


class TestCostMetrics:
    """Tests for cost tracking."""

    def test_from_usage(self):
        """Cost calculation from token usage."""
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=500_000)
        costs = CostMetrics.from_usage(usage)

        # Default prices: $3/1M input, $15/1M output
        assert costs.input_cost_usd == pytest.approx(3.0, abs=0.01)
        assert costs.output_cost_usd == pytest.approx(7.5, abs=0.01)
        assert costs.total_cost_usd == pytest.approx(10.5, abs=0.01)

    def test_custom_prices(self):
        """Cost calculation with custom prices."""
        usage = TokenUsage(input_tokens=1_000_000, output_tokens=1_000_000)
        costs = CostMetrics.from_usage(
            usage,
            input_cost_per_1m=5.0,
            output_cost_per_1m=20.0,
        )

        assert costs.input_cost_usd == pytest.approx(5.0, abs=0.01)
        assert costs.output_cost_usd == pytest.approx(20.0, abs=0.01)
        assert costs.total_cost_usd == pytest.approx(25.0, abs=0.01)


class TestToolCallPattern:
    """Tests for tool call pattern analysis."""

    def test_empty_calls(self):
        """Empty tool calls list."""
        pattern = ToolCallPattern.from_tool_calls([])
        assert pattern.read_before_write is False
        assert pattern.test_driven is False
        assert pattern.error_recovery_attempts == 0
        assert pattern.exploration_ratio == 0.0

    def test_read_before_write(self):
        """Detect read-before-write pattern."""
        calls = [
            ToolCall(name="Read", input={"file_path": "test.py"}),
            ToolCall(name="Edit", input={"file_path": "test.py"}),
        ]
        pattern = ToolCallPattern.from_tool_calls(calls)
        assert pattern.read_before_write is True

    def test_write_before_read(self):
        """Detect write-before-read (bad practice)."""
        calls = [
            ToolCall(name="Write", input={"file_path": "new.py"}),
            ToolCall(name="Read", input={"file_path": "other.py"}),
        ]
        pattern = ToolCallPattern.from_tool_calls(calls)
        assert pattern.read_before_write is False

    def test_exploration_ratio(self):
        """Calculate exploration ratio."""
        calls = [
            ToolCall(name="Read", input={}),
            ToolCall(name="Glob", input={}),
            ToolCall(name="Grep", input={}),
            ToolCall(name="Edit", input={}),
        ]
        pattern = ToolCallPattern.from_tool_calls(calls)
        # 3 reads, 1 write = 0.75 exploration ratio
        assert pattern.exploration_ratio == pytest.approx(0.75, abs=0.01)

    def test_error_counting(self):
        """Count error recovery attempts."""
        calls = [
            ToolCall(name="Read", input={}, error=None),
            ToolCall(name="Edit", input={}, error="File not found"),
            ToolCall(name="Edit", input={}, error="Permission denied"),
            ToolCall(name="Edit", input={}, error=None),
        ]
        pattern = ToolCallPattern.from_tool_calls(calls)
        assert pattern.error_recovery_attempts == 2


class TestReadabilityMetrics:
    """Tests for readability metrics."""

    def test_from_content(self):
        """Calculate readability from content."""
        content = """
        # Build Commands

        Run the tests with pytest. Use the following command:

        ```bash
        pytest tests/
        ```

        This will run all tests in the tests directory.
        """
        metrics = ReadabilityMetrics.from_content(content)

        assert metrics.word_count > 0
        assert metrics.sentence_count > 0
        # These are calculated by textstat
        assert isinstance(metrics.flesch_reading_ease, float)
        assert isinstance(metrics.flesch_kincaid_grade, float)

    def test_empty_content(self):
        """Handle empty content."""
        metrics = ReadabilityMetrics.from_content("")
        assert metrics.word_count == 0
