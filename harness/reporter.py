"""Results reporting and analysis.

Features:
- Statistical significance testing for comparisons
- Stability metrics (variance, coefficient of variation)
- Unbiased pass@k estimation
- CLAUDE.md quality metrics
"""

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from harness.models import CostMetrics, EvalResult
from harness.statistics import (
    ComparisonResult,
    EfficiencyComparison,
    StabilityMetrics,
    StatisticalAnalyzer,
)


def _group_results_by_key(
    results: list[EvalResult],
    include_model: bool = True,
) -> dict[tuple, list[EvalResult]]:
    """Group evaluation results by task_id, config_name, and optionally model.

    Args:
        results: List of evaluation results to group
        include_model: Whether to include model in the grouping key (default: True)

    Returns:
        Dictionary mapping (task_id, config_name[, model]) tuples to result lists
    """
    grouped: dict[tuple, list[EvalResult]] = defaultdict(list)
    for r in results:
        if include_model:
            key = (r.task_id, r.config_name, r.model)
        else:
            key = (r.task_id, r.config_name)
        grouped[key].append(r)
    return grouped


@dataclass
class AggregatedMetrics:
    """Aggregated metrics for a group of results."""

    total_runs: int
    passed: int
    failed: int
    pass_rate: float
    avg_score: float
    avg_tokens: int
    avg_duration: float
    avg_cost: float  # USD cost from token usage
    pass_at_k: dict[int, float]  # k -> probability
    # Stability metrics
    stability: StabilityMetrics | None = None


class Reporter:
    """Generates reports from evaluation results."""

    def __init__(self, console: Console | None = None):
        """Initialize reporter.

        Args:
            console: Rich console for output (default: new Console)
        """
        self.console = console or Console()

    def print_summary(self, results: list[EvalResult]) -> None:
        """Print summary table of results.

        Args:
            results: List of evaluation results
        """
        if not results:
            self.console.print("[yellow]No results to display[/yellow]")
            return

        # Group by task
        by_task = defaultdict(list)
        for r in results:
            by_task[r.task_id].append(r)

        self.console.print()
        self.console.print(
            f"[bold]EVAL RESULTS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}[/bold]"
        )
        self.console.print("=" * 60)

        for task_id, task_results in sorted(by_task.items()):
            self._print_task_table(task_id, task_results)

    def _print_task_table(self, task_id: str, results: list[EvalResult]) -> None:
        """Print table for a single task."""
        self.console.print(f"\n[bold]Task: {task_id}[/bold]")

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Config")
        table.add_column("Model")
        table.add_column("Pass Rate")
        table.add_column("Avg Score")
        table.add_column("Tokens")
        table.add_column("Duration")

        # Group by config and model
        by_config_model = defaultdict(list)
        for r in results:
            key = (r.config_name, r.model)
            by_config_model[key].append(r)

        for (config, model), group in sorted(by_config_model.items()):
            metrics = self._calculate_metrics(group)

            pass_rate_str = f"{metrics.passed}/{metrics.total_runs} ({metrics.pass_rate:.0%})"
            avg_score_str = f"{metrics.avg_score:.2f}"
            tokens_str = f"{metrics.avg_tokens:,}"
            duration_str = f"{metrics.avg_duration:.1f}s"

            # Color coding
            if metrics.pass_rate >= 0.9:
                pass_rate_str = f"[green]{pass_rate_str}[/green]"
            elif metrics.pass_rate >= 0.5:
                pass_rate_str = f"[yellow]{pass_rate_str}[/yellow]"
            else:
                pass_rate_str = f"[red]{pass_rate_str}[/red]"

            table.add_row(config, model, pass_rate_str, avg_score_str, tokens_str, duration_str)

        self.console.print(table)

    def _calculate_metrics(self, results: list[EvalResult]) -> AggregatedMetrics:
        """Calculate aggregated metrics for a group of results."""
        total = len(results)
        passed = sum(1 for r in results if r.passed)

        avg_score = sum(r.overall_score for r in results) / total if total else 0
        avg_tokens = (
            int(sum(r.trace.usage.total_tokens for r in results) / total) if total else 0
        )
        avg_duration = (
            sum(r.trace.duration_seconds for r in results) / total if total else 0
        )

        # Calculate cost from token usage
        total_cost = sum(
            CostMetrics.from_usage(r.trace.usage).total_cost_usd
            for r in results
        )
        avg_cost = total_cost / total if total else 0

        # Calculate pass@k using unbiased estimator
        pass_at_k = {}
        for k in [1, 3, 5]:
            pass_at_k[k] = StatisticalAnalyzer.pass_at_k_unbiased(results, k)

        # Calculate stability metrics
        stability = StatisticalAnalyzer.calculate_stability(results) if results else None

        return AggregatedMetrics(
            total_runs=total,
            passed=passed,
            failed=total - passed,
            pass_rate=passed / total if total else 0,
            avg_score=avg_score,
            avg_tokens=avg_tokens,
            avg_duration=avg_duration,
            avg_cost=avg_cost,
            pass_at_k=pass_at_k,
            stability=stability,
        )

    def print_regression_comparison(
        self,
        baseline: list[EvalResult],
        current: list[EvalResult],
    ) -> None:
        """Print comparison between baseline and current results.

        Args:
            baseline: Previous baseline results
            current: Current results to compare
        """
        self.console.print("\n[bold]REGRESSION COMPARISON[/bold]")
        self.console.print("=" * 60)

        # Group by task + config + model
        baseline_grouped = _group_results_by_key(baseline)
        current_grouped = _group_results_by_key(current)

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Task")
        table.add_column("Config")
        table.add_column("Baseline")
        table.add_column("Current")
        table.add_column("Delta")
        table.add_column("Tok Δ%")
        table.add_column("Dur Δ%")

        all_keys = set(baseline_grouped.keys()) | set(current_grouped.keys())

        regressions = []
        improvements = []
        efficiency_regressions = []

        for key in sorted(all_keys):
            task_id, config, _ = key

            baseline_metrics = (
                self._calculate_metrics(baseline_grouped[key])
                if key in baseline_grouped
                else None
            )
            current_metrics = (
                self._calculate_metrics(current_grouped[key])
                if key in current_grouped
                else None
            )

            baseline_rate = baseline_metrics.pass_rate if baseline_metrics else 0
            current_rate = current_metrics.pass_rate if current_metrics else 0
            delta = current_rate - baseline_rate

            baseline_str = f"{baseline_rate:.0%}" if baseline_metrics else "N/A"
            current_str = f"{current_rate:.0%}" if current_metrics else "N/A"

            if delta > 0:
                delta_str = f"[green]+{delta:.0%}[/green]"
                improvements.append((key, delta))
            elif delta < 0:
                delta_str = f"[red]{delta:.0%}[/red]"
                regressions.append((key, delta))
            else:
                delta_str = "0%"

            # Calculate token and duration deltas
            baseline_tokens = baseline_metrics.avg_tokens if baseline_metrics else 0
            current_tokens = current_metrics.avg_tokens if current_metrics else 0
            baseline_dur = baseline_metrics.avg_duration if baseline_metrics else 0
            current_dur = current_metrics.avg_duration if current_metrics else 0

            if baseline_tokens > 0:
                tok_delta_pct = (current_tokens - baseline_tokens) / baseline_tokens * 100
                if tok_delta_pct > 10:
                    tok_str = f"[red]+{tok_delta_pct:.0f}%[/red]"
                    efficiency_regressions.append((key, "tokens", tok_delta_pct))
                elif tok_delta_pct < -10:
                    tok_str = f"[green]{tok_delta_pct:.0f}%[/green]"
                else:
                    tok_str = f"{tok_delta_pct:+.0f}%"
            else:
                tok_str = "N/A"

            if baseline_dur > 0:
                dur_delta_pct = (current_dur - baseline_dur) / baseline_dur * 100
                if dur_delta_pct > 10:
                    dur_str = f"[red]+{dur_delta_pct:.0f}%[/red]"
                    efficiency_regressions.append((key, "duration", dur_delta_pct))
                elif dur_delta_pct < -10:
                    dur_str = f"[green]{dur_delta_pct:.0f}%[/green]"
                else:
                    dur_str = f"{dur_delta_pct:+.0f}%"
            else:
                dur_str = "N/A"

            table.add_row(task_id, config, baseline_str, current_str, delta_str, tok_str, dur_str)

        self.console.print(table)

        # Summary
        self.console.print()
        if regressions:
            self.console.print(
                f"[red]Regressions: {len(regressions)} task(s) got worse[/red]"
            )
        if improvements:
            self.console.print(
                f"[green]Improvements: {len(improvements)} task(s) got better[/green]"
            )
        if efficiency_regressions:
            self.console.print(
                f"[yellow]Efficiency regressions: {len(efficiency_regressions)} metric(s) increased >10%[/yellow]"
            )
        if not regressions and not improvements:
            self.console.print("[yellow]No significant changes detected[/yellow]")

    def print_detailed_result(self, result: EvalResult, verbose: bool = False) -> None:
        """Print detailed view of a single result.

        Args:
            result: Result to display
            verbose: Whether to show full output (default: False)
        """
        self.console.print(f"\n[bold]Task: {result.task_id}[/bold]")
        self.console.print(f"Config: {result.config_name}")
        self.console.print(f"Model: {result.model}")
        self.console.print(f"Run: {result.run_index}")
        self.console.print(f"Passed: {'[green]Yes[/green]' if result.passed else '[red]No[/red]'}")
        self.console.print(f"Overall Score: {result.overall_score:.2f}")
        self.console.print()

        # Assertion results with pass/fail icons
        if result.grades:
            self.console.print("[bold]Assertions:[/bold]")
            for grade in result.grades:
                icon = "✓" if grade.passed else "✗"
                color = "green" if grade.passed else "red"
                name = grade.assertion_name or grade.assertion_id
                self.console.print(
                    f"  [{color}]{icon}[/] {name}: {grade.score:.2f}"
                )

                # Show details for failed assertions or in verbose mode
                if not grade.passed or verbose:
                    if grade.details:
                        details = grade.details[:200] + "..." if len(grade.details) > 200 else grade.details
                        self.console.print(f"    [dim]{details}[/dim]")

                    # Show full output in verbose mode
                    if verbose and grade.full_output:
                        self.console.print()
                        self.console.print(
                            Panel(
                                grade.full_output[:1000] + ("..." if len(grade.full_output) > 1000 else ""),
                                title=f"Full Output: {name}",
                                border_style="dim",
                            )
                        )

            self.console.print()

        # File changes
        if result.trace.file_changes:
            self.console.print("[bold]File Changes:[/bold]")
            for fc in result.trace.file_changes:
                if fc.action == "created":
                    self.console.print(f"  [green]+[/] {fc.path} [dim](created)[/dim]")
                elif fc.action == "modified":
                    self.console.print(f"  [yellow]~[/] {fc.path} [dim](modified)[/dim]")
                elif fc.action == "deleted":
                    self.console.print(f"  [red]-[/] {fc.path} [dim](deleted)[/dim]")

                # Show diff in verbose mode
                if verbose and fc.diff:
                    self.console.print()
                    self.console.print(
                        Syntax(fc.diff[:2000], "diff", theme="monokai", line_numbers=False)
                    )

            self.console.print()

        # Tool call timeline
        if result.trace.tool_calls:
            self.console.print("[bold]Tool Calls:[/bold]")
            for tc in result.trace.tool_calls:
                status = "[red]error[/red]" if tc.error else "[green]ok[/green]"
                self.console.print(f"  {tc.name} {status}")

                # Show error details
                if tc.error and verbose:
                    self.console.print(f"    [dim red]{tc.error[:200]}[/dim red]")

            self.console.print()

        # Execution metrics
        self.console.print("[bold]Execution Metrics[/bold]")
        self.console.print(f"Duration: {result.trace.duration_seconds:.1f}s")
        self.console.print(f"Turns: {result.trace.num_turns}", end="")
        if result.trace.hit_turn_limit:
            self.console.print(" [yellow](hit limit)[/yellow]")
        else:
            self.console.print()
        self.console.print(f"Input Tokens: {result.trace.usage.input_tokens:,}")
        self.console.print(f"Output Tokens: {result.trace.usage.output_tokens:,}")
        self.console.print(f"Tool Calls: {len(result.trace.tool_calls)}")

    def print_analysis(
        self,
        results: list[EvalResult],
        task_filter: str | None = None,
        failed_only: bool = False,
    ) -> None:
        """Print analysis of results with filtering.

        Args:
            results: List of results to analyze
            task_filter: Optional task ID to filter by
            failed_only: Show only failed results
        """
        # Apply filters
        filtered = results
        if task_filter:
            filtered = [r for r in filtered if task_filter in r.task_id]
        if failed_only:
            filtered = [r for r in filtered if not r.passed]

        if not filtered:
            self.console.print("[yellow]No results match the filter criteria[/yellow]")
            return

        self.console.print(f"\n[bold]ANALYSIS: {len(filtered)} results[/bold]")
        self.console.print("=" * 60)

        # Group by task
        by_task: dict[str, list[EvalResult]] = {}
        for r in filtered:
            by_task.setdefault(r.task_id, []).append(r)

        for task_id, task_results in sorted(by_task.items()):
            metrics = self._calculate_metrics(task_results)
            status = "[green]PASSING[/green]" if metrics.pass_rate >= 0.7 else "[red]FAILING[/red]"

            self.console.print(f"\n[bold]{task_id}[/bold] {status}")
            self.console.print(f"  Pass Rate: {metrics.pass_rate:.0%} ({metrics.passed}/{metrics.total_runs})")
            self.console.print(f"  Avg Score: {metrics.avg_score:.2f}")

            # Show assertion breakdown
            assertion_stats: dict[str, dict] = {}
            for r in task_results:
                for g in r.grades:
                    name = g.assertion_name or g.assertion_id
                    if name not in assertion_stats:
                        assertion_stats[name] = {"passed": 0, "total": 0}
                    assertion_stats[name]["total"] += 1
                    if g.passed:
                        assertion_stats[name]["passed"] += 1

            self.console.print("  [dim]Assertion breakdown:[/dim]")
            for name, stats in assertion_stats.items():
                rate = stats["passed"] / stats["total"] if stats["total"] > 0 else 0
                color = "green" if rate >= 0.7 else "yellow" if rate >= 0.5 else "red"
                self.console.print(
                    f"    [{color}]{name}[/{color}]: {stats['passed']}/{stats['total']} ({rate:.0%})"
                )

    def print_diff(
        self,
        results_a: list[EvalResult],
        results_b: list[EvalResult],
        label_a: str = "A",
        label_b: str = "B",
    ) -> None:
        """Print side-by-side comparison of two result sets.

        Args:
            results_a: First result set
            results_b: Second result set
            label_a: Label for first set
            label_b: Label for second set
        """
        self.console.print(f"\n[bold]DIFF: {label_a} vs {label_b}[/bold]")
        self.console.print("=" * 60)

        # Group by task + config (no model)
        grouped_a = _group_results_by_key(results_a, include_model=False)
        grouped_b = _group_results_by_key(results_b, include_model=False)

        all_keys = set(grouped_a.keys()) | set(grouped_b.keys())

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Task")
        table.add_column("Config")
        table.add_column(f"{label_a} Rate")
        table.add_column(f"{label_b} Rate")
        table.add_column("Delta")
        table.add_column(f"{label_a} Tok")
        table.add_column(f"{label_b} Tok")
        table.add_column("Tok Δ%")
        table.add_column("Winner")

        for key in sorted(all_keys):
            task_id, config = key

            metrics_a = self._calculate_metrics(grouped_a.get(key, []))
            metrics_b = self._calculate_metrics(grouped_b.get(key, []))

            rate_a = metrics_a.pass_rate if grouped_a.get(key) else 0
            rate_b = metrics_b.pass_rate if grouped_b.get(key) else 0
            delta = rate_b - rate_a

            rate_a_str = f"{rate_a:.0%}" if grouped_a.get(key) else "N/A"
            rate_b_str = f"{rate_b:.0%}" if grouped_b.get(key) else "N/A"

            # Token comparison
            tokens_a = metrics_a.avg_tokens if grouped_a.get(key) else 0
            tokens_b = metrics_b.avg_tokens if grouped_b.get(key) else 0
            tokens_a_str = f"{tokens_a:,}" if grouped_a.get(key) else "N/A"
            tokens_b_str = f"{tokens_b:,}" if grouped_b.get(key) else "N/A"

            if tokens_a > 0:
                tok_delta_pct = (tokens_b - tokens_a) / tokens_a * 100
                if tok_delta_pct > 10:
                    tok_delta_str = f"[red]+{tok_delta_pct:.0f}%[/red]"
                elif tok_delta_pct < -10:
                    tok_delta_str = f"[green]{tok_delta_pct:.0f}%[/green]"
                else:
                    tok_delta_str = f"{tok_delta_pct:+.0f}%"
            else:
                tok_delta_str = "N/A"

            if delta > 0.05:
                delta_str = f"[green]+{delta:.0%}[/green]"
                winner = f"[green]{label_b}[/green]"
            elif delta < -0.05:
                delta_str = f"[red]{delta:.0%}[/red]"
                winner = f"[green]{label_a}[/green]"
            else:
                delta_str = f"{delta:.0%}"
                winner = "[dim]tie[/dim]"

            table.add_row(
                task_id, config, rate_a_str, rate_b_str, delta_str,
                tokens_a_str, tokens_b_str, tok_delta_str, winner
            )

        self.console.print(table)

    def print_explain(self, result: EvalResult) -> None:
        """Print deep dive into a single result with full context.

        Args:
            result: Result to explain in detail
        """
        self.console.print(f"\n[bold]DEEP DIVE: {result.task_id}[/bold]")
        self.console.print("=" * 60)

        # Config used
        self.console.print("\n[bold]Configuration[/bold]")
        self.console.print(f"  Config: {result.config_name}")
        self.console.print(f"  Model: {result.model}")
        self.console.print(f"  Max Turns: {result.trace.max_turns}")
        if result.trace.config_snapshot.claude_md:
            self.console.print(
                f"  CLAUDE.md Preview: {result.trace.config_snapshot.claude_md[:100]}..."
            )

        # Prompt sent
        if result.trace.claude_prompt:
            self.console.print("\n[bold]Prompt Sent[/bold]")
            self.console.print(
                Panel(
                    result.trace.claude_prompt[:2000] + ("..." if len(result.trace.claude_prompt) > 2000 else ""),
                    border_style="blue",
                )
            )

        # Claude's response
        if result.trace.claude_response:
            self.console.print("\n[bold]Claude's Response[/bold]")
            self.console.print(
                Panel(
                    result.trace.claude_response[:3000] + ("..." if len(result.trace.claude_response) > 3000 else ""),
                    border_style="green",
                )
            )

        # File changes with full diffs
        if result.trace.file_changes:
            self.console.print("\n[bold]File Changes (Full Diffs)[/bold]")
            for fc in result.trace.file_changes:
                self.console.print(f"\n  [bold]{fc.action.upper()}:[/bold] {fc.path}")
                if fc.diff:
                    self.console.print(
                        Syntax(fc.diff, "diff", theme="monokai", line_numbers=False)
                    )
                elif fc.content_after:
                    # Show first part of created file
                    preview = fc.content_after[:1000]
                    if len(fc.content_after) > 1000:
                        preview += "\n... (truncated)"
                    self.console.print(
                        Panel(preview, title="New File Content", border_style="green")
                    )

        # Full grading details
        self.console.print("\n[bold]Grading Details[/bold]")
        for grade in result.grades:
            name = grade.assertion_name or grade.assertion_id
            icon = "✓" if grade.passed else "✗"
            color = "green" if grade.passed else "red"

            self.console.print(f"\n  [{color}]{icon} {name}[/{color}] (score: {grade.score:.2f})")

            if grade.reasoning:
                self.console.print(f"    [dim]Reasoning: {grade.reasoning}[/dim]")

            # Show criteria breakdown for LLM grades
            if grade.criteria_scores:
                self.console.print("    [dim]Criteria Breakdown:[/dim]")
                for cs in grade.criteria_scores:
                    self.console.print(f"      - {cs.criterion}: {cs.score:.2f}")
                    if cs.reasoning:
                        self.console.print(f"        [dim]{cs.reasoning}[/dim]")

            # Show full output
            if grade.full_output:
                self.console.print("\n    [bold]Full Output:[/bold]")
                self.console.print(
                    Panel(
                        grade.full_output,
                        border_style="dim",
                    )
                )

            # Show grading prompt for LLM grades
            if grade.grading_prompt:
                self.console.print("\n    [bold]Grading Prompt Used:[/bold]")
                self.console.print(
                    Panel(
                        grade.grading_prompt[:3000] + ("..." if len(grade.grading_prompt) > 3000 else ""),
                        border_style="dim cyan",
                    )
                )

        # Execution summary
        self.console.print("\n[bold]Execution Summary[/bold]")
        self.console.print(f"  Duration: {result.trace.duration_seconds:.1f}s")
        self.console.print(f"  Turns: {result.trace.num_turns}/{result.trace.max_turns}")
        self.console.print(f"  Hit Turn Limit: {'Yes' if result.trace.hit_turn_limit else 'No'}")
        self.console.print(f"  Total Tokens: {result.trace.usage.total_tokens:,}")
        self.console.print(f"  Tool Calls: {len(result.trace.tool_calls)}")

        if result.trace.is_error:
            self.console.print(f"\n  [red]EXECUTION ERROR:[/red] {result.trace.result}")

    def export_json(self, results: list[EvalResult], path: Path) -> None:
        """Export results to JSON file.

        Args:
            results: Results to export
            path: Output path
        """
        data = {
            "timestamp": datetime.now().isoformat(),
            "num_results": len(results),
            "summary": self._generate_summary_dict(results),
            "results": [r.model_dump(mode="json") for r in results],
        }
        path.write_text(json.dumps(data, indent=2, default=str))
        self.console.print(f"[green]Results exported to {path}[/green]")

    def _generate_summary_dict(self, results: list[EvalResult]) -> dict:
        """Generate summary statistics as dict."""
        if not results:
            return {}

        metrics = self._calculate_metrics(results)
        return {
            "total_runs": metrics.total_runs,
            "passed": metrics.passed,
            "failed": metrics.failed,
            "pass_rate": metrics.pass_rate,
            "avg_score": metrics.avg_score,
            "avg_tokens": metrics.avg_tokens,
            "avg_duration_seconds": metrics.avg_duration,
            "pass_at_1": metrics.pass_at_k.get(1, 0),
            "pass_at_3": metrics.pass_at_k.get(3, 0),
        }

    def check_regression(
        self,
        baseline: list[EvalResult],
        current: list[EvalResult],
        threshold: float = 0.05,
        require_significance: bool = True,
    ) -> tuple[bool, dict]:
        """Check for regressions between baseline and current results.

        Uses statistical significance testing (Mann-Whitney U) to reduce
        false positives from random variance.

        Args:
            baseline: Previous baseline results
            current: Current results to compare
            threshold: Maximum acceptable drop in pass rate (default: 5%)
            require_significance: Require p < 0.05 for regression (default: True)

        Returns:
            Tuple of (has_regressions, comparison_data)
        """

        # Group by task + config + model
        baseline_grouped = _group_results_by_key(baseline)
        current_grouped = _group_results_by_key(current)

        regressions = []
        improvements = []
        all_comparisons = []

        all_keys = set(baseline_grouped.keys()) | set(current_grouped.keys())

        for key in sorted(all_keys):
            task_id, config, model = key

            baseline_results = baseline_grouped.get(key, [])
            current_results = current_grouped.get(key, [])

            baseline_metrics = (
                self._calculate_metrics(baseline_results)
                if baseline_results
                else None
            )
            current_metrics = (
                self._calculate_metrics(current_results)
                if current_results
                else None
            )

            baseline_rate = baseline_metrics.pass_rate if baseline_metrics else 0
            current_rate = current_metrics.pass_rate if current_metrics else 0
            delta = current_rate - baseline_rate

            # Run statistical comparison if both have results
            stat_comparison = None
            if baseline_results and current_results:
                stat_comparison = StatisticalAnalyzer.compare_configs(
                    baseline_results, current_results
                )

            comparison = {
                "task_id": task_id,
                "config": config,
                "model": model,
                "baseline_pass_rate": baseline_rate,
                "current_pass_rate": current_rate,
                "delta": delta,
            }

            # Add statistical details if available
            if stat_comparison:
                comparison["p_value"] = stat_comparison.p_value
                comparison["effect_size"] = stat_comparison.effect_size
                comparison["effect_magnitude"] = stat_comparison.effect_magnitude
                comparison["is_significant"] = stat_comparison.is_significant
                comparison["recommendation"] = stat_comparison.recommendation

            all_comparisons.append(comparison)

            # Check for regression with optional significance requirement
            is_regression = delta < -threshold
            if require_significance and stat_comparison:
                is_regression = is_regression and stat_comparison.is_significant

            is_improvement = delta > threshold
            if require_significance and stat_comparison:
                is_improvement = is_improvement and stat_comparison.is_significant

            if is_regression:
                regressions.append(comparison)
            elif is_improvement:
                improvements.append(comparison)

        has_regressions = len(regressions) > 0

        return has_regressions, {
            "has_regressions": has_regressions,
            "regression_count": len(regressions),
            "improvement_count": len(improvements),
            "threshold": threshold,
            "require_significance": require_significance,
            "regressions": regressions,
            "improvements": improvements,
            "comparisons": all_comparisons,
        }

    def print_statistical_comparison(
        self,
        results_a: list[EvalResult],
        results_b: list[EvalResult],
        label_a: str = "Baseline",
        label_b: str = "Current",
        show_efficiency: bool = True,
        show_cost: bool = False,
    ) -> tuple[ComparisonResult, EfficiencyComparison | None]:
        """Print detailed statistical comparison between two result sets.

        Args:
            results_a: First result set
            results_b: Second result set
            label_a: Label for first set
            label_b: Label for second set
            show_efficiency: Include token/timing comparison (default: True)
            show_cost: Include cost comparison (default: False)

        Returns:
            Tuple of (ComparisonResult, EfficiencyComparison or None)
        """
        comparison = StatisticalAnalyzer.compare_configs(results_a, results_b)

        self.console.print(f"\n[bold]STATISTICAL COMPARISON: {label_a} vs {label_b}[/bold]")
        self.console.print("=" * 60)

        # Summary table
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric")
        table.add_column(label_a)
        table.add_column(label_b)
        table.add_column("Delta")

        table.add_row(
            "Mean Score",
            f"{comparison.mean_a:.3f}",
            f"{comparison.mean_b:.3f}",
            f"{comparison.delta:+.3f}",
        )
        table.add_row(
            "Sample Size",
            str(comparison.n_a),
            str(comparison.n_b),
            "",
        )
        self.console.print(table)

        # Statistical test results
        self.console.print("\n[bold]Statistical Test (Mann-Whitney U)[/bold]")
        sig_color = "green" if comparison.is_significant else "yellow"
        self.console.print(f"  U-statistic: {comparison.statistic:.2f}")
        self.console.print(f"  p-value: {comparison.p_value:.4f}")
        self.console.print(
            f"  Significant: [{sig_color}]{'Yes' if comparison.is_significant else 'No'}[/{sig_color}] (alpha=0.05)"
        )

        # Effect size
        self.console.print("\n[bold]Effect Size (Cohen's d)[/bold]")
        self.console.print(f"  Effect size: {comparison.effect_size:.3f}")
        self.console.print(f"  Magnitude: {comparison.effect_magnitude}")

        # Efficiency analysis
        efficiency: EfficiencyComparison | None = None
        if show_efficiency:
            efficiency = StatisticalAnalyzer.compare_efficiency(results_a, results_b)
            self._print_efficiency_comparison(efficiency, label_a, label_b, show_cost)

        # Recommendation
        self.console.print("\n[bold]Recommendation[/bold]")
        self.console.print(f"  {comparison.recommendation}")
        if efficiency:
            self.console.print(f"  {efficiency.recommendation}")

        return comparison, efficiency

    def _print_efficiency_comparison(
        self,
        efficiency: EfficiencyComparison,
        label_a: str,  # noqa: ARG002
        label_b: str,  # noqa: ARG002
        show_cost: bool = False,
    ) -> None:
        """Print efficiency comparison section."""
        # label_a and label_b reserved for future use in table headers
        self.console.print("\n[bold]Efficiency Analysis[/bold]")

        # Tokens
        tok_delta_pct = efficiency.tokens_delta_pct
        tok_p = efficiency.tokens_p_value
        tok_sig = "*" if tok_p is not None and tok_p < 0.05 else ""
        tok_sig += "*" if tok_p is not None and tok_p < 0.01 else ""

        if tok_delta_pct < -10:
            tok_color = "green"
            tok_direction = f"{abs(tok_delta_pct):.1f}% fewer"
        elif tok_delta_pct > 10:
            tok_color = "red"
            tok_direction = f"+{tok_delta_pct:.1f}% more"
        else:
            tok_color = "dim"
            tok_direction = f"{tok_delta_pct:+.1f}%"

        tok_p_str = f"p={tok_p:.3f}{tok_sig}" if tok_p is not None else "p=N/A"
        self.console.print(
            f"  Tokens:   {efficiency.tokens_a_mean:,.0f} → {efficiency.tokens_b_mean:,.0f} "
            f"([{tok_color}]{tok_direction}[/{tok_color}], {tok_p_str})"
        )

        # Duration
        dur_delta_pct = efficiency.duration_delta_pct
        dur_p = efficiency.duration_p_value
        dur_sig = "*" if dur_p is not None and dur_p < 0.05 else ""
        dur_sig += "*" if dur_p is not None and dur_p < 0.01 else ""

        if dur_delta_pct < -10:
            dur_color = "green"
            dur_direction = f"{abs(dur_delta_pct):.1f}% faster"
        elif dur_delta_pct > 10:
            dur_color = "red"
            dur_direction = f"+{dur_delta_pct:.1f}% slower"
        else:
            dur_color = "dim"
            dur_direction = f"{dur_delta_pct:+.1f}%"

        dur_p_str = f"p={dur_p:.3f}{dur_sig}" if dur_p is not None else "p=N/A"
        self.console.print(
            f"  Duration: {efficiency.duration_a_mean:.1f}s → {efficiency.duration_b_mean:.1f}s "
            f"([{dur_color}]{dur_direction}[/{dur_color}], {dur_p_str})"
        )

        # Cost (optional)
        if show_cost:
            cost_delta_pct = efficiency.cost_delta_pct
            if cost_delta_pct < -5:
                cost_color = "green"
            elif cost_delta_pct > 5:
                cost_color = "red"
            else:
                cost_color = "dim"

            self.console.print(
                f"  Cost:     ${efficiency.cost_a_mean:.4f} → ${efficiency.cost_b_mean:.4f} "
                f"([{cost_color}]{cost_delta_pct:+.1f}%[/{cost_color}])"
            )
