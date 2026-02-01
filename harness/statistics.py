"""Statistical analysis for evaluation results.

Provides statistical rigor for regression detection and A/B testing,
including:
- Power analysis for sample size recommendations
- Mann-Whitney U test for comparing configurations
- Cohen's d effect size calculation
- Unbiased pass@k estimator (Chen et al. 2021)
"""

from dataclasses import dataclass
from math import comb, sqrt
from typing import TYPE_CHECKING

from scipy import stats
import numpy as np

if TYPE_CHECKING:
    from harness.models import EvalResult


@dataclass
class StabilityMetrics:
    """Metrics for result stability/variance."""

    variance: float
    std_dev: float
    coefficient_of_variation: float  # CV = std_dev / mean
    min_score: float
    max_score: float
    score_range: float


@dataclass
class EfficiencyComparison:
    """Token and timing comparison between configs."""

    tokens_a_mean: float
    tokens_b_mean: float
    tokens_delta: float  # b - a
    tokens_delta_pct: float  # (b - a) / a * 100

    duration_a_mean: float
    duration_b_mean: float
    duration_delta: float  # b - a
    duration_delta_pct: float  # (b - a) / a * 100

    cost_a_mean: float
    cost_b_mean: float
    cost_delta: float
    cost_delta_pct: float

    tokens_p_value: float | None  # Mann-Whitney on token counts
    duration_p_value: float | None  # Mann-Whitney on durations

    recommendation: str


@dataclass
class ComparisonResult:
    """Result of statistical comparison between two configurations."""

    # Raw metrics
    mean_a: float
    mean_b: float
    n_a: int
    n_b: int

    # Statistical test results
    statistic: float  # Mann-Whitney U statistic
    p_value: float
    is_significant: bool  # p < 0.05

    # Effect size
    effect_size: float  # Cohen's d
    effect_magnitude: str  # "negligible", "small", "medium", "large"

    # Practical interpretation
    delta: float  # mean_b - mean_a
    relative_change: float  # (mean_b - mean_a) / mean_a as percentage
    recommendation: str  # Human-readable recommendation


@dataclass
class PowerAnalysisResult:
    """Result of power analysis for sample size determination."""

    baseline_rate: float
    min_detectable_effect: float
    recommended_sample_size: int
    power: float
    alpha: float
    notes: str


class StatisticalAnalyzer:
    """Statistical analysis utilities for evaluation results."""

    # Effect size thresholds (Cohen's d)
    EFFECT_NEGLIGIBLE = 0.2
    EFFECT_SMALL = 0.5
    EFFECT_MEDIUM = 0.8

    @staticmethod
    def minimum_sample_size(
        baseline_rate: float,
        min_effect: float = 0.1,
        power: float = 0.8,
        alpha: float = 0.05,
    ) -> PowerAnalysisResult:
        """Calculate minimum sample size for detecting an effect.

        Uses approximation based on normal distribution for proportions.

        Args:
            baseline_rate: Expected baseline pass rate (0-1)
            min_effect: Minimum effect size to detect (absolute change in rate)
            power: Statistical power (1 - beta), default 0.8
            alpha: Significance level, default 0.05

        Returns:
            PowerAnalysisResult with recommended sample size
        """
        # Validate inputs
        if not 0 < baseline_rate < 1:
            return PowerAnalysisResult(
                baseline_rate=baseline_rate,
                min_detectable_effect=min_effect,
                recommended_sample_size=30,  # Minimum reasonable sample
                power=power,
                alpha=alpha,
                notes="Invalid baseline rate. Using minimum sample size of 30.",
            )

        # Expected rate under alternative hypothesis
        alt_rate = baseline_rate + min_effect
        if alt_rate >= 1:
            alt_rate = 0.99
        if alt_rate <= 0:
            alt_rate = 0.01

        # Pooled proportion
        p_pooled = (baseline_rate + alt_rate) / 2

        # Z-scores for alpha and power
        z_alpha = stats.norm.ppf(1 - alpha / 2)  # Two-tailed
        z_power = stats.norm.ppf(power)

        # Sample size formula for comparing two proportions
        numerator = (
            z_alpha * sqrt(2 * p_pooled * (1 - p_pooled))
            + z_power * sqrt(
                baseline_rate * (1 - baseline_rate)
                + alt_rate * (1 - alt_rate)
            )
        ) ** 2
        denominator = (baseline_rate - alt_rate) ** 2

        if denominator == 0:
            n = 30
            notes = "Effect size is 0. Using minimum sample size of 30."
        else:
            n = int(np.ceil(numerator / denominator))
            n = max(n, 5)  # Minimum 5 samples
            notes = f"Sample size provides {power:.0%} power to detect {min_effect:.0%} change."

        return PowerAnalysisResult(
            baseline_rate=baseline_rate,
            min_detectable_effect=min_effect,
            recommended_sample_size=n,
            power=power,
            alpha=alpha,
            notes=notes,
        )

    @staticmethod
    def compare_configs(
        results_a: list["EvalResult"],
        results_b: list["EvalResult"],
        alpha: float = 0.05,
    ) -> ComparisonResult:
        """Compare two sets of results using Mann-Whitney U test.

        The Mann-Whitney U test is a non-parametric test that doesn't assume
        normal distribution, making it suitable for pass rates and scores.

        Args:
            results_a: Results from first configuration
            results_b: Results from second configuration
            alpha: Significance level for hypothesis test

        Returns:
            ComparisonResult with test statistics and interpretation
        """
        # Extract scores
        scores_a = np.array([r.overall_score for r in results_a])
        scores_b = np.array([r.overall_score for r in results_b])

        n_a, n_b = len(scores_a), len(scores_b)
        mean_a, mean_b = np.mean(scores_a), np.mean(scores_b)
        delta = mean_b - mean_a

        # Handle edge cases
        if n_a < 2 or n_b < 2:
            return ComparisonResult(
                mean_a=float(mean_a),
                mean_b=float(mean_b),
                n_a=n_a,
                n_b=n_b,
                statistic=0.0,
                p_value=1.0,
                is_significant=False,
                effect_size=0.0,
                effect_magnitude="negligible",
                delta=float(delta),
                relative_change=0.0,
                recommendation="Insufficient samples for statistical comparison (need at least 2 per group).",
            )

        # Mann-Whitney U test
        statistic, p_value = stats.mannwhitneyu(
            scores_a, scores_b, alternative="two-sided"
        )

        # Cohen's d effect size
        pooled_std = np.sqrt(
            ((n_a - 1) * np.var(scores_a, ddof=1) + (n_b - 1) * np.var(scores_b, ddof=1))
            / (n_a + n_b - 2)
        )
        if pooled_std > 0:
            effect_size = abs(delta) / pooled_std
        else:
            effect_size = 0.0

        # Interpret effect size
        if effect_size < StatisticalAnalyzer.EFFECT_NEGLIGIBLE:
            effect_magnitude = "negligible"
        elif effect_size < StatisticalAnalyzer.EFFECT_SMALL:
            effect_magnitude = "small"
        elif effect_size < StatisticalAnalyzer.EFFECT_MEDIUM:
            effect_magnitude = "medium"
        else:
            effect_magnitude = "large"

        # Statistical significance
        is_significant = p_value < alpha

        # Relative change
        relative_change = (delta / mean_a * 100) if mean_a > 0 else 0.0

        # Generate recommendation
        recommendation = StatisticalAnalyzer._generate_recommendation(
            delta=float(delta),
            p_value=p_value,
            effect_magnitude=effect_magnitude,
            is_significant=is_significant,
            n_a=n_a,
            n_b=n_b,
        )

        return ComparisonResult(
            mean_a=float(mean_a),
            mean_b=float(mean_b),
            n_a=n_a,
            n_b=n_b,
            statistic=float(statistic),
            p_value=float(p_value),
            is_significant=is_significant,
            effect_size=float(effect_size),
            effect_magnitude=effect_magnitude,
            delta=float(delta),
            relative_change=float(relative_change),
            recommendation=recommendation,
        )

    @staticmethod
    def compare_efficiency(
        results_a: list["EvalResult"],
        results_b: list["EvalResult"],
    ) -> EfficiencyComparison:
        """Compare token usage and timing between two config runs.

        Calculates mean tokens, duration, and cost for each group,
        and performs Mann-Whitney U tests on tokens and duration
        to determine statistical significance of efficiency differences.

        Args:
            results_a: Results from first configuration
            results_b: Results from second configuration

        Returns:
            EfficiencyComparison with efficiency metrics and statistical tests
        """
        from harness.models import CostMetrics

        # Extract token counts, durations, and costs
        tokens_a = np.array([r.trace.usage.total_tokens for r in results_a])
        tokens_b = np.array([r.trace.usage.total_tokens for r in results_b])

        durations_a = np.array([r.trace.duration_seconds for r in results_a])
        durations_b = np.array([r.trace.duration_seconds for r in results_b])

        costs_a = np.array([
            CostMetrics.from_usage(r.trace.usage).total_cost_usd
            for r in results_a
        ])
        costs_b = np.array([
            CostMetrics.from_usage(r.trace.usage).total_cost_usd
            for r in results_b
        ])

        # Calculate means
        tokens_a_mean = float(np.mean(tokens_a)) if len(tokens_a) > 0 else 0.0
        tokens_b_mean = float(np.mean(tokens_b)) if len(tokens_b) > 0 else 0.0
        duration_a_mean = float(np.mean(durations_a)) if len(durations_a) > 0 else 0.0
        duration_b_mean = float(np.mean(durations_b)) if len(durations_b) > 0 else 0.0
        cost_a_mean = float(np.mean(costs_a)) if len(costs_a) > 0 else 0.0
        cost_b_mean = float(np.mean(costs_b)) if len(costs_b) > 0 else 0.0

        # Calculate deltas
        tokens_delta = tokens_b_mean - tokens_a_mean
        tokens_delta_pct = (tokens_delta / tokens_a_mean * 100) if tokens_a_mean > 0 else 0.0

        duration_delta = duration_b_mean - duration_a_mean
        duration_delta_pct = (duration_delta / duration_a_mean * 100) if duration_a_mean > 0 else 0.0

        cost_delta = cost_b_mean - cost_a_mean
        cost_delta_pct = (cost_delta / cost_a_mean * 100) if cost_a_mean > 0 else 0.0

        # Perform Mann-Whitney U tests if sufficient samples
        tokens_p_value: float | None = None
        duration_p_value: float | None = None

        if len(tokens_a) >= 2 and len(tokens_b) >= 2:
            try:
                _, tokens_p_value = stats.mannwhitneyu(
                    tokens_a, tokens_b, alternative="two-sided"
                )
            except ValueError:
                tokens_p_value = None

            try:
                _, duration_p_value = stats.mannwhitneyu(
                    durations_a, durations_b, alternative="two-sided"
                )
            except ValueError:
                duration_p_value = None

        # Generate recommendation
        recommendation = StatisticalAnalyzer._generate_efficiency_recommendation(
            tokens_delta_pct=tokens_delta_pct,
            duration_delta_pct=duration_delta_pct,
            tokens_p_value=tokens_p_value,
            duration_p_value=duration_p_value,
            n_a=len(results_a),
            n_b=len(results_b),
        )

        return EfficiencyComparison(
            tokens_a_mean=tokens_a_mean,
            tokens_b_mean=tokens_b_mean,
            tokens_delta=tokens_delta,
            tokens_delta_pct=tokens_delta_pct,
            duration_a_mean=duration_a_mean,
            duration_b_mean=duration_b_mean,
            duration_delta=duration_delta,
            duration_delta_pct=duration_delta_pct,
            cost_a_mean=cost_a_mean,
            cost_b_mean=cost_b_mean,
            cost_delta=cost_delta,
            cost_delta_pct=cost_delta_pct,
            tokens_p_value=tokens_p_value,
            duration_p_value=duration_p_value,
            recommendation=recommendation,
        )

    @staticmethod
    def _generate_efficiency_recommendation(
        tokens_delta_pct: float,
        duration_delta_pct: float,
        tokens_p_value: float | None,
        duration_p_value: float | None,
        n_a: int,
        n_b: int,
    ) -> str:
        """Generate human-readable recommendation for efficiency comparison."""
        min_n = min(n_a, n_b)

        if min_n < 2:
            return "Insufficient samples for efficiency comparison (need at least 2 per group)."

        parts = []

        # Analyze token efficiency
        tokens_sig = tokens_p_value is not None and tokens_p_value < 0.05
        if abs(tokens_delta_pct) > 10:
            direction = "fewer" if tokens_delta_pct < 0 else "more"
            sig_note = " (statistically significant)" if tokens_sig else ""
            parts.append(f"B uses {abs(tokens_delta_pct):.0f}% {direction} tokens{sig_note}.")

        # Analyze duration efficiency
        duration_sig = duration_p_value is not None and duration_p_value < 0.05
        if abs(duration_delta_pct) > 10:
            direction = "faster" if duration_delta_pct < 0 else "slower"
            sig_note = " (statistically significant)" if duration_sig else ""
            parts.append(f"B is {abs(duration_delta_pct):.0f}% {direction}{sig_note}.")

        if not parts:
            return "No significant efficiency differences detected between configurations."

        # Overall assessment
        both_better = tokens_delta_pct < -10 and duration_delta_pct < -10
        both_worse = tokens_delta_pct > 10 and duration_delta_pct > 10

        if both_better:
            parts.append("B is more efficient overall.")
        elif both_worse:
            parts.append("B is less efficient overall.")

        return " ".join(parts)

    @staticmethod
    def _generate_recommendation(
        delta: float,
        p_value: float,
        effect_magnitude: str,
        is_significant: bool,
        n_a: int,
        n_b: int,
    ) -> str:
        """Generate human-readable recommendation from comparison."""
        min_n = min(n_a, n_b)

        if min_n < 5:
            return (
                f"Sample size too small (n={min_n}). "
                "Collect at least 5 runs per configuration for reliable comparison."
            )

        if not is_significant:
            if min_n < 10:
                return (
                    f"No significant difference detected (p={p_value:.3f}). "
                    "Consider increasing sample size for more statistical power."
                )
            return (
                f"No significant difference detected (p={p_value:.3f}). "
                "The configurations appear equivalent."
            )

        direction = "improvement" if delta > 0 else "regression"

        if effect_magnitude == "negligible":
            return (
                f"Statistically significant but negligible {direction} "
                f"(p={p_value:.3f}, d={effect_magnitude}). "
                "The practical difference is minimal."
            )
        elif effect_magnitude == "small":
            return (
                f"Statistically significant small {direction} "
                f"(p={p_value:.3f}, d={effect_magnitude}). "
                "Consider whether this is practically meaningful."
            )
        elif effect_magnitude == "medium":
            return (
                f"Significant medium {direction} detected "
                f"(p={p_value:.3f}, d={effect_magnitude}). "
                "This is a meaningful difference."
            )
        else:  # large
            return (
                f"Significant large {direction} detected "
                f"(p={p_value:.3f}, d={effect_magnitude}). "
                "This is a substantial difference."
            )

    @staticmethod
    def pass_at_k_unbiased(results: list["EvalResult"], k: int) -> float:
        """Calculate unbiased pass@k estimator.

        Uses the estimator from Chen et al. 2021 "Evaluating Large Language
        Models Trained on Code" which provides an unbiased estimate of the
        probability that at least one of k samples passes.

        Formula: pass@k = 1 - C(n-c, k) / C(n, k)
        where n = total samples, c = number of correct samples

        Args:
            results: List of evaluation results
            k: Number of samples to consider

        Returns:
            Unbiased pass@k probability (0-1)
        """
        n = len(results)
        c = sum(1 for r in results if r.passed)

        if n == 0:
            return 0.0

        if k > n:
            # Fall back to simple estimate if k > n
            return c / n if n > 0 else 0.0

        if c == n:
            # All passed
            return 1.0

        if c == 0:
            # None passed
            return 0.0

        # Unbiased estimator: 1 - C(n-c, k) / C(n, k)
        # Using comb() for numerical stability
        try:
            numerator = comb(n - c, k)
            denominator = comb(n, k)
            if denominator == 0:
                return 0.0
            return 1.0 - (numerator / denominator)
        except (ValueError, OverflowError):
            # Fallback for numerical issues
            return c / n

    @staticmethod
    def calculate_stability(results: list["EvalResult"]) -> StabilityMetrics:
        """Calculate stability metrics for a set of results.

        Args:
            results: List of evaluation results

        Returns:
            StabilityMetrics with variance and related measures
        """
        if not results:
            return StabilityMetrics(
                variance=0.0,
                std_dev=0.0,
                coefficient_of_variation=0.0,
                min_score=0.0,
                max_score=0.0,
                score_range=0.0,
            )

        scores = [r.overall_score for r in results]
        mean = np.mean(scores)
        variance = float(np.var(scores, ddof=1)) if len(scores) > 1 else 0.0
        std_dev = float(np.sqrt(variance))

        # Coefficient of variation (handle zero mean)
        cv = float(std_dev / mean) if mean > 0 else 0.0

        min_score = float(np.min(scores))
        max_score = float(np.max(scores))

        return StabilityMetrics(
            variance=variance,
            std_dev=std_dev,
            coefficient_of_variation=cv,
            min_score=min_score,
            max_score=max_score,
            score_range=max_score - min_score,
        )

    @staticmethod
    def is_regression(
        baseline_results: list["EvalResult"],
        current_results: list["EvalResult"],
        threshold: float = 0.05,
        require_significance: bool = True,
    ) -> tuple[bool, ComparisonResult]:
        """Check if current results represent a regression from baseline.

        Args:
            baseline_results: Baseline evaluation results
            current_results: Current evaluation results
            threshold: Minimum pass rate drop to consider a regression
            require_significance: Require statistical significance

        Returns:
            Tuple of (is_regression, comparison_result)
        """
        comparison = StatisticalAnalyzer.compare_configs(
            baseline_results, current_results
        )

        # Check for regression
        is_regressed = comparison.delta < -threshold

        if require_significance:
            is_regressed = is_regressed and comparison.is_significant

        return is_regressed, comparison
