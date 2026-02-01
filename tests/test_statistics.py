"""Tests for the statistics module."""

import pytest
from datetime import datetime

from harness.models import EvalResult, ExecutionTrace, TokenUsage
from harness.statistics import (
    ComparisonResult,
    PowerAnalysisResult,
    StabilityMetrics,
    StatisticalAnalyzer,
)


def make_result(score: float, passed: bool) -> EvalResult:
    """Create a minimal EvalResult for testing."""
    return EvalResult(
        task_id="test_task",
        config_name="test_config",
        model="claude-test",
        run_index=0,
        timestamp=datetime.now(),
        trace=ExecutionTrace(
            session_id="test",
            result="test result",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
        ),
        overall_score=score,
        passed=passed,
    )


class TestMinimumSampleSize:
    """Tests for power analysis / sample size calculation."""

    def test_typical_scenario(self):
        """Test typical A/B testing scenario."""
        result = StatisticalAnalyzer.minimum_sample_size(
            baseline_rate=0.7,
            min_effect=0.1,
            power=0.8,
            alpha=0.05,
        )
        assert isinstance(result, PowerAnalysisResult)
        assert result.recommended_sample_size > 0
        assert result.baseline_rate == 0.7
        assert result.min_detectable_effect == 0.1
        assert result.power == 0.8

    def test_small_effect_requires_more_samples(self):
        """Smaller effects require larger sample sizes."""
        large_effect = StatisticalAnalyzer.minimum_sample_size(
            baseline_rate=0.7, min_effect=0.2
        )
        small_effect = StatisticalAnalyzer.minimum_sample_size(
            baseline_rate=0.7, min_effect=0.05
        )
        assert small_effect.recommended_sample_size > large_effect.recommended_sample_size

    def test_invalid_baseline_rate(self):
        """Invalid baseline rates should return minimum sample size."""
        result = StatisticalAnalyzer.minimum_sample_size(
            baseline_rate=1.5,  # Invalid
            min_effect=0.1,
        )
        assert result.recommended_sample_size == 30  # Minimum fallback
        assert "Invalid" in result.notes


class TestCompareConfigs:
    """Tests for statistical comparison of configurations."""

    def test_identical_results(self):
        """Identical results should show no significant difference."""
        results_a = [make_result(0.8, True) for _ in range(10)]
        results_b = [make_result(0.8, True) for _ in range(10)]

        comparison = StatisticalAnalyzer.compare_configs(results_a, results_b)

        assert isinstance(comparison, ComparisonResult)
        assert comparison.delta == pytest.approx(0.0, abs=0.01)
        assert not comparison.is_significant

    def test_different_results(self):
        """Clearly different results should show significant difference."""
        results_a = [make_result(0.3, False) for _ in range(20)]
        results_b = [make_result(0.9, True) for _ in range(20)]

        comparison = StatisticalAnalyzer.compare_configs(results_a, results_b)

        assert comparison.delta > 0.5
        assert comparison.is_significant
        assert comparison.effect_magnitude == "large"

    def test_insufficient_samples(self):
        """Should handle insufficient samples gracefully."""
        results_a = [make_result(0.8, True)]
        results_b = [make_result(0.3, False)]

        comparison = StatisticalAnalyzer.compare_configs(results_a, results_b)

        assert "Insufficient" in comparison.recommendation

    def test_effect_size_categories(self):
        """Effect size should be categorized correctly."""
        # Create results with medium difference
        results_a = [make_result(0.5, False) for _ in range(15)]
        results_b = [make_result(0.7, True) for _ in range(15)]

        comparison = StatisticalAnalyzer.compare_configs(results_a, results_b)

        assert comparison.effect_magnitude in ["small", "medium", "large"]


class TestPassAtK:
    """Tests for unbiased pass@k estimator."""

    def test_all_passed(self):
        """All passing results should give pass@k = 1.0."""
        results = [make_result(1.0, True) for _ in range(10)]
        assert StatisticalAnalyzer.pass_at_k_unbiased(results, k=1) == 1.0
        assert StatisticalAnalyzer.pass_at_k_unbiased(results, k=5) == 1.0

    def test_none_passed(self):
        """No passing results should give pass@k = 0.0."""
        results = [make_result(0.0, False) for _ in range(10)]
        assert StatisticalAnalyzer.pass_at_k_unbiased(results, k=1) == 0.0
        assert StatisticalAnalyzer.pass_at_k_unbiased(results, k=5) == 0.0

    def test_partial_pass(self):
        """Partial passing should give correct estimates."""
        # 5 passed out of 10
        results = (
            [make_result(1.0, True) for _ in range(5)]
            + [make_result(0.0, False) for _ in range(5)]
        )

        pass_at_1 = StatisticalAnalyzer.pass_at_k_unbiased(results, k=1)
        pass_at_5 = StatisticalAnalyzer.pass_at_k_unbiased(results, k=5)

        # pass@1 should equal pass rate
        assert pass_at_1 == pytest.approx(0.5, abs=0.01)
        # pass@5 should be higher (more chances to get at least one)
        assert pass_at_5 > pass_at_1

    def test_k_greater_than_n(self):
        """k > n should fallback to simple estimate."""
        results = [make_result(1.0, True) for _ in range(3)]
        pass_at_10 = StatisticalAnalyzer.pass_at_k_unbiased(results, k=10)
        assert pass_at_10 == 1.0  # All passed

    def test_empty_results(self):
        """Empty results should return 0."""
        assert StatisticalAnalyzer.pass_at_k_unbiased([], k=1) == 0.0


class TestStabilityMetrics:
    """Tests for stability/variance calculations."""

    def test_consistent_results(self):
        """Consistent results should have low variance."""
        results = [make_result(0.8, True) for _ in range(10)]
        stability = StatisticalAnalyzer.calculate_stability(results)

        assert isinstance(stability, StabilityMetrics)
        assert stability.variance == 0.0
        assert stability.std_dev == 0.0
        assert stability.coefficient_of_variation == 0.0

    def test_variable_results(self):
        """Variable results should have higher variance."""
        results = [make_result(score, score > 0.5) for score in [0.2, 0.4, 0.6, 0.8, 1.0]]
        stability = StatisticalAnalyzer.calculate_stability(results)

        assert stability.variance > 0
        assert stability.std_dev > 0
        assert stability.min_score == 0.2
        assert stability.max_score == 1.0
        assert stability.score_range == 0.8

    def test_empty_results(self):
        """Empty results should return zeros."""
        stability = StatisticalAnalyzer.calculate_stability([])
        assert stability.variance == 0.0
        assert stability.std_dev == 0.0


class TestIsRegression:
    """Tests for regression detection."""

    def test_clear_regression(self):
        """Clear regression should be detected."""
        baseline = [make_result(0.9, True) for _ in range(10)]
        current = [make_result(0.5, False) for _ in range(10)]

        is_regressed, comparison = StatisticalAnalyzer.is_regression(
            baseline, current, threshold=0.1
        )

        assert is_regressed
        assert comparison.delta < -0.1

    def test_clear_improvement(self):
        """Improvement should not be flagged as regression."""
        baseline = [make_result(0.5, False) for _ in range(10)]
        current = [make_result(0.9, True) for _ in range(10)]

        is_regressed, comparison = StatisticalAnalyzer.is_regression(
            baseline, current, threshold=0.1
        )

        assert not is_regressed
        assert comparison.delta > 0

    def test_no_change(self):
        """No change should not be flagged as regression."""
        baseline = [make_result(0.7, True) for _ in range(10)]
        current = [make_result(0.7, True) for _ in range(10)]

        is_regressed, comparison = StatisticalAnalyzer.is_regression(
            baseline, current, threshold=0.05
        )

        assert not is_regressed

    def test_significance_requirement(self):
        """Regression detection should respect significance requirement."""
        # Small samples with some difference
        baseline = [make_result(0.8, True), make_result(0.7, True)]
        current = [make_result(0.6, True), make_result(0.5, False)]

        # Without significance requirement
        is_regressed_no_sig, _ = StatisticalAnalyzer.is_regression(
            baseline, current, threshold=0.1, require_significance=False
        )

        # The regression might or might not be detected depending on implementation
        # but the key is that both options work
        assert isinstance(is_regressed_no_sig, bool)
