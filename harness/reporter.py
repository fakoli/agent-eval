"""Results reporting and analysis."""

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from harness.models import EvalResult


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
    pass_at_k: dict[int, float]  # k -> probability


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

        # Calculate pass@k
        pass_at_k = {}
        for k in [1, 3, 5]:
            if k <= total:
                # pass@k = 1 - (C(n-c, k) / C(n, k)) where c = num passed
                # Simplified: probability of at least one pass in k tries
                p = passed / total if total else 0
                pass_at_k[k] = 1 - (1 - p) ** k
            else:
                pass_at_k[k] = passed / total if total else 0

        return AggregatedMetrics(
            total_runs=total,
            passed=passed,
            failed=total - passed,
            pass_rate=passed / total if total else 0,
            avg_score=avg_score,
            avg_tokens=avg_tokens,
            avg_duration=avg_duration,
            pass_at_k=pass_at_k,
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

        # Group by task + config
        def group_key(r: EvalResult) -> tuple:
            return (r.task_id, r.config_name, r.model)

        baseline_grouped = defaultdict(list)
        for r in baseline:
            baseline_grouped[group_key(r)].append(r)

        current_grouped = defaultdict(list)
        for r in current:
            current_grouped[group_key(r)].append(r)

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Task")
        table.add_column("Config")
        table.add_column("Baseline")
        table.add_column("Current")
        table.add_column("Delta")

        all_keys = set(baseline_grouped.keys()) | set(current_grouped.keys())

        regressions = []
        improvements = []

        for key in sorted(all_keys):
            task_id, config, model = key

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

            table.add_row(task_id, config, baseline_str, current_str, delta_str)

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

        # Group by task + config
        def group_key(r: EvalResult) -> tuple:
            return (r.task_id, r.config_name)

        grouped_a: dict = {}
        for r in results_a:
            grouped_a.setdefault(group_key(r), []).append(r)

        grouped_b: dict = {}
        for r in results_b:
            grouped_b.setdefault(group_key(r), []).append(r)

        all_keys = set(grouped_a.keys()) | set(grouped_b.keys())

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Task")
        table.add_column("Config")
        table.add_column(f"{label_a} Pass Rate")
        table.add_column(f"{label_b} Pass Rate")
        table.add_column("Delta")
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

            if delta > 0.05:
                delta_str = f"[green]+{delta:.0%}[/green]"
                winner = f"[green]{label_b}[/green]"
            elif delta < -0.05:
                delta_str = f"[red]{delta:.0%}[/red]"
                winner = f"[green]{label_a}[/green]"
            else:
                delta_str = f"{delta:.0%}"
                winner = "[dim]tie[/dim]"

            table.add_row(task_id, config, rate_a_str, rate_b_str, delta_str, winner)

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
    ) -> tuple[bool, dict]:
        """Check for regressions between baseline and current results.

        Args:
            baseline: Previous baseline results
            current: Current results to compare
            threshold: Maximum acceptable drop in pass rate (default: 5%)

        Returns:
            Tuple of (has_regressions, comparison_data)
        """

        def group_key(r: EvalResult) -> tuple:
            return (r.task_id, r.config_name, r.model)

        baseline_grouped = defaultdict(list)
        for r in baseline:
            baseline_grouped[group_key(r)].append(r)

        current_grouped = defaultdict(list)
        for r in current:
            current_grouped[group_key(r)].append(r)

        regressions = []
        improvements = []
        all_comparisons = []

        all_keys = set(baseline_grouped.keys()) | set(current_grouped.keys())

        for key in sorted(all_keys):
            task_id, config, model = key

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

            comparison = {
                "task_id": task_id,
                "config": config,
                "model": model,
                "baseline_pass_rate": baseline_rate,
                "current_pass_rate": current_rate,
                "delta": delta,
            }
            all_comparisons.append(comparison)

            # Check against threshold
            if delta < -threshold:
                regressions.append(comparison)
            elif delta > threshold:
                improvements.append(comparison)

        has_regressions = len(regressions) > 0

        return has_regressions, {
            "has_regressions": has_regressions,
            "regression_count": len(regressions),
            "improvement_count": len(improvements),
            "threshold": threshold,
            "regressions": regressions,
            "improvements": improvements,
            "comparisons": all_comparisons,
        }
