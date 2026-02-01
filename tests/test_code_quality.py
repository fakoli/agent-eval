"""Code quality tests converted from manual-test/run-tests.sh.

These tests verify that the harness components work correctly after
tech debt cleanup changes.
"""

import os
from pathlib import Path

import pytest


class TestConstants:
    """Tests for centralized constants module."""

    def test_constants_importable(self):
        """Verify constants module is importable with expected values."""
        from harness.constants import (
            DEFAULT_EXECUTION_MODEL,
            DEFAULT_GRADING_MODEL,
            DEFAULT_MAX_TURNS,
            DEFAULT_EXECUTION_TIMEOUT,
        )

        assert DEFAULT_EXECUTION_MODEL == "claude-sonnet-4-20250514"
        assert DEFAULT_GRADING_MODEL == "claude-3-5-haiku-20241022"
        assert DEFAULT_MAX_TURNS == 10
        assert DEFAULT_EXECUTION_TIMEOUT == 300

    def test_timeout_constants(self):
        """Verify timeout constants exist and are reasonable."""
        from harness.constants import (
            DEFAULT_TEST_TIMEOUT,
            DEFAULT_LINT_TIMEOUT,
            DEFAULT_CONTAINER_TIMEOUT,
        )

        assert DEFAULT_TEST_TIMEOUT == 120
        assert DEFAULT_LINT_TIMEOUT == 60
        assert DEFAULT_CONTAINER_TIMEOUT == 600

    def test_docker_constants(self):
        """Verify Docker-related constants exist."""
        from harness.constants import (
            DEFAULT_DOCKER_IMAGE_NAME,
            DEFAULT_DOCKER_IMAGE_TAG,
        )

        assert DEFAULT_DOCKER_IMAGE_NAME == "agent-eval"
        assert DEFAULT_DOCKER_IMAGE_TAG == "latest"


class TestTokenUsage:
    """Tests for TokenUsage.from_dict() method."""

    def test_from_dict_full_data(self):
        """TokenUsage.from_dict() works with complete data."""
        from harness.models import TokenUsage

        data = {
            "input_tokens": 1000,
            "output_tokens": 500,
            "cache_read_tokens": 100,
        }
        usage = TokenUsage.from_dict(data)

        assert usage.input_tokens == 1000
        assert usage.output_tokens == 500
        assert usage.cache_read_tokens == 100
        assert usage.total_tokens == 1500

    def test_from_dict_partial_data(self):
        """TokenUsage.from_dict() works with partial data."""
        from harness.models import TokenUsage

        partial = TokenUsage.from_dict({"input_tokens": 200})

        assert partial.input_tokens == 200
        assert partial.output_tokens == 0
        assert partial.cache_read_tokens == 0

    def test_from_dict_empty_data(self):
        """TokenUsage.from_dict() works with empty dict."""
        from harness.models import TokenUsage

        empty = TokenUsage.from_dict({})

        assert empty.input_tokens == 0
        assert empty.output_tokens == 0
        assert empty.total_tokens == 0


class TestResultGrouping:
    """Tests for _group_results_by_key() utility."""

    def test_group_results_by_key(self):
        """_group_results_by_key() groups results correctly."""
        from harness.reporter import _group_results_by_key
        from harness.models import EvalResult, ExecutionTrace

        results = [
            EvalResult(
                task_id="task1",
                config_name="cfg1",
                model="m1",
                run_index=0,
                trace=ExecutionTrace(),
                passed=True,
            ),
            EvalResult(
                task_id="task1",
                config_name="cfg1",
                model="m1",
                run_index=1,
                trace=ExecutionTrace(),
                passed=False,
            ),
            EvalResult(
                task_id="task2",
                config_name="cfg1",
                model="m1",
                run_index=0,
                trace=ExecutionTrace(),
                passed=True,
            ),
        ]

        grouped = _group_results_by_key(results, include_model=True)

        assert len(grouped) == 2
        assert len(grouped[("task1", "cfg1", "m1")]) == 2

    def test_group_results_without_model(self):
        """_group_results_by_key() works without model grouping."""
        from harness.reporter import _group_results_by_key
        from harness.models import EvalResult, ExecutionTrace

        results = [
            EvalResult(
                task_id="task1",
                config_name="cfg1",
                model="m1",
                run_index=0,
                trace=ExecutionTrace(),
                passed=True,
            ),
            EvalResult(
                task_id="task1",
                config_name="cfg1",
                model="m2",
                run_index=0,
                trace=ExecutionTrace(),
                passed=True,
            ),
        ]

        grouped = _group_results_by_key(results, include_model=False)

        # Both should be grouped together when model is excluded
        assert len(grouped) == 1


class TestCodeGrader:
    """Tests for CodeGrader helper methods."""

    def test_create_grade_result(self):
        """CodeGrader._create_grade_result() creates valid results."""
        from harness.graders.code_graders import CodeGrader

        grader = CodeGrader()
        result = grader._create_grade_result(
            "test_assertion",
            True,
            0.95,
            "Test passed with details",
            "Full output here",
        )

        assert result.assertion_id == "test_assertion"
        assert result.assertion_type == "code"
        assert result.passed is True
        assert result.score == 0.95
        assert result.details == "Test passed with details"
        assert result.full_output == "Full output here"

    def test_create_grade_result_failed(self):
        """CodeGrader._create_grade_result() works for failed results."""
        from harness.graders.code_graders import CodeGrader

        grader = CodeGrader()
        result = grader._create_grade_result(
            "failed_check",
            False,
            0.0,
            "Check failed",
        )

        assert result.passed is False
        assert result.score == 0.0


class TestConfigValidation:
    """Tests for config file validation."""

    def test_load_test_config(self):
        """Config validation works with test config."""
        from harness.runner import EvalRunner

        test_config = Path(__file__).parent.parent / "examples/getting-started/configs/baseline/config.yaml"

        if not test_config.exists():
            pytest.skip("Test config file not found")

        runner = EvalRunner()
        config = runner.load_config(test_config)

        assert config.name == "baseline"
        assert config.claude_md is None
        assert config.skills_path is None


class TestTaskValidation:
    """Tests for task file validation."""

    def test_load_test_task(self):
        """Task validation works with test task."""
        from harness.runner import EvalRunner

        test_task = Path(__file__).parent.parent / "examples/getting-started/tasks/fix-bug.task.yaml"

        if not test_task.exists():
            pytest.skip("Test task file not found")

        runner = EvalRunner()
        task = runner.load_task(test_task)

        assert task.id == "fix-division-bug"
        assert task.category.value == "coding"
        assert task.difficulty.value == "easy"
        assert len(task.assertions) >= 1


class TestRequireApiKey:
    """Tests for require_api_key() function."""

    def test_require_api_key_missing(self):
        """require_api_key() exits when key is missing."""
        # Save and clear the key
        saved_key = os.environ.pop("ANTHROPIC_API_KEY", None)

        try:
            from harness.__main__ import require_api_key

            with pytest.raises(SystemExit) as exc_info:
                require_api_key("test-command")

            assert exc_info.value.code == 1
        finally:
            # Restore the key
            if saved_key:
                os.environ["ANTHROPIC_API_KEY"] = saved_key

    def test_require_api_key_present(self):
        """require_api_key() passes when key is set."""
        # Ensure key is set
        saved_key = os.environ.get("ANTHROPIC_API_KEY")
        os.environ["ANTHROPIC_API_KEY"] = "test-key-value"

        try:
            from harness.__main__ import require_api_key

            # Should not raise
            require_api_key("test-command")
        finally:
            # Restore original state
            if saved_key:
                os.environ["ANTHROPIC_API_KEY"] = saved_key
            else:
                os.environ.pop("ANTHROPIC_API_KEY", None)
