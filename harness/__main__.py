"""CLI interface for the evaluation harness."""

import os
import subprocess
import sys
from pathlib import Path

import click
from dotenv import load_dotenv
from rich.console import Console

from harness.config_exporter import ConfigExporter
from harness.config_importer import ConfigImporter
from harness.reporter import Reporter
from harness.runner import EvalRunner
from harness.scaffold import ScaffoldGenerator
from harness.statistics import StatisticalAnalyzer

console = Console()


def require_api_key(command_name: str) -> None:
    """Check that ANTHROPIC_API_KEY is set, exit with error if not.

    Use this for commands that require LLM grading to fail fast
    instead of failing later during execution.

    Args:
        command_name: Name of the command requiring the key (for error message)
    """
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            f"[red]Error: ANTHROPIC_API_KEY is required for '{command_name}'.[/red]"
        )
        console.print(
            "[dim]Set it in your .env file or environment before running this command.[/dim]"
        )
        sys.exit(1)


def load_env_file(env_file: Path | None = None) -> bool:
    """Load environment variables from .env file.

    Args:
        env_file: Explicit path to .env file. If None, searches default locations.

    Returns:
        True if a .env file was loaded, False otherwise.
    """
    if env_file:
        if env_file.exists():
            load_dotenv(env_file)
            return True
        else:
            console.print(f"[yellow]Warning: .env file not found at {env_file}[/yellow]")
            return False

    # Search default locations in order
    default_locations = [
        Path.cwd() / ".env",           # Current directory
        Path.home() / ".env",          # Home directory
        Path.cwd() / ".env.local",     # Local override
    ]

    for loc in default_locations:
        if loc.exists():
            load_dotenv(loc)
            return True

    return False


@click.group()
@click.option(
    "--env-file",
    "-e",
    type=click.Path(exists=False, path_type=Path),
    default=None,
    envvar="EVAL_ENV_FILE",
    help="Path to .env file (default: searches ./.env, ~/.env)",
)
@click.pass_context
def cli(ctx: click.Context, env_file: Path | None):
    """Claude Code Evaluation Harness.

    Run evaluations to test skills, CLAUDE.md configurations, and model versions.

    Environment variables can be loaded from a .env file. By default, searches
    for .env in the current directory and home directory. Use --env-file to
    specify a custom location.
    """
    ctx.ensure_object(dict)

    # Load environment variables from .env file
    loaded = load_env_file(env_file)
    ctx.obj["env_loaded"] = loaded
    ctx.obj["env_file"] = env_file

    # Check for required API key
    if not os.getenv("ANTHROPIC_API_KEY"):
        console.print(
            "[yellow]Warning: ANTHROPIC_API_KEY not set. "
            "LLM grading will fail.[/yellow]"
        )
        console.print(
            "[dim]Set it in your .env file or environment.[/dim]"
        )


@cli.command()
@click.option(
    "--task",
    "-t",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to task YAML file",
)
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to config YAML file",
)
@click.option(
    "--model",
    "-m",
    default=None,
    help="Model to use (overrides config)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for results",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed output including full test output and diffs",
)
@click.option(
    "--container",
    is_flag=True,
    help="Run evaluation in an isolated Docker container",
)
@click.option(
    "--preserve-artifacts",
    is_flag=True,
    help="Preserve full artifacts from the run (fixtures, output, diffs)",
)
def run(
    task: Path,
    config: Path,
    model: str | None,
    output: Path | None,
    verbose: bool,
    container: bool,
    preserve_artifacts: bool,
):
    """Run a single evaluation task."""
    # Fail early if API key is missing (needed for LLM grading)
    require_api_key("run")

    runner = EvalRunner(
        use_container=container,
        preserve_artifacts=preserve_artifacts,
    )
    reporter = Reporter(console)

    if container:
        console.print("[dim]Running in container mode[/dim]")
    if preserve_artifacts:
        console.print(f"[dim]Artifacts will be saved to {runner.artifacts_dir}[/dim]")

    console.print(f"Loading task from {task}...")
    task_obj = runner.load_task(task)

    console.print(f"Loading config from {config}...")
    config_obj = runner.load_config(config)

    if model:
        config_obj.model = model

    console.print(f"Running evaluation: {task_obj.id} with {config_obj.name}...")
    console.print()

    result = runner.run_single(task_obj, config_obj)

    reporter.print_detailed_result(result, verbose=verbose)

    if output:
        runner.save_results([result], output.name)
        console.print(f"\n[green]Results saved to {output}[/green]")


@cli.command()
@click.option(
    "--tasks",
    "-t",
    required=True,
    help="Glob pattern for task files (e.g., 'evals/tasks/**/*.task.yaml')",
)
@click.option(
    "--configs",
    "-c",
    required=True,
    help="Glob pattern for config files (e.g., 'evals/configs/*/config.yaml')",
)
@click.option(
    "--models",
    "-m",
    default=None,
    help="Comma-separated list of models to test",
)
@click.option(
    "--runs",
    "-r",
    default=3,
    type=int,
    help="Number of runs per combination",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file for results",
)
@click.option(
    "--container",
    is_flag=True,
    help="Run evaluations in isolated Docker containers",
)
@click.option(
    "--preserve-artifacts",
    is_flag=True,
    help="Preserve full artifacts from each run",
)
def matrix(
    tasks: str,
    configs: str,
    models: str | None,
    runs: int,
    output: Path | None,
    container: bool,
    preserve_artifacts: bool,
):
    """Run full evaluation matrix."""
    # Fail early if API key is missing (needed for LLM grading)
    require_api_key("matrix")

    runner = EvalRunner(
        use_container=container,
        preserve_artifacts=preserve_artifacts,
    )
    reporter = Reporter(console)

    if container:
        console.print("[dim]Running in container mode[/dim]")
    if preserve_artifacts:
        console.print(f"[dim]Artifacts will be saved to {runner.artifacts_dir}[/dim]")

    console.print(f"Loading tasks from {tasks}...")
    task_list = runner.load_tasks_from_glob(tasks)
    console.print(f"Found {len(task_list)} task(s)")

    console.print(f"Loading configs from {configs}...")
    config_list = runner.load_configs_from_glob(configs)
    console.print(f"Found {len(config_list)} config(s)")

    model_list = models.split(",") if models else None

    total_combos = len(task_list) * len(config_list) * (len(model_list) if model_list else 1) * runs
    console.print(f"\nRunning {total_combos} total evaluations...")
    console.print()

    completed = [0]

    def progress_callback(task, config, model, run_idx, result):
        completed[0] += 1
        status = "[green]PASS[/green]" if result.passed else "[red]FAIL[/red]"
        console.print(
            f"[{completed[0]}/{total_combos}] {task.id} | {config.name} | {model} | Run {run_idx + 1} | {status}"
        )

    results = runner.run_matrix(
        tasks=task_list,
        configs=config_list,
        models=model_list,
        runs_per_combo=runs,
        callback=progress_callback,
    )

    console.print()
    reporter.print_summary(results)

    output_path = runner.save_results(results, output.name if output else None)
    console.print(f"\n[green]Results saved to {output_path}[/green]")


@cli.command()
@click.option(
    "--baseline",
    "-b",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to baseline results JSON",
)
@click.option(
    "--current",
    "-c",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to current results JSON",
)
@click.option(
    "--statistical/--no-statistical",
    default=True,
    help="Use statistical significance testing (default: True)",
)
@click.option(
    "--threshold",
    "-t",
    type=float,
    default=0.05,
    help="Regression threshold (default: 0.05 = 5%)",
)
def regression(baseline: Path, current: Path, statistical: bool, threshold: float):
    """Compare current results against baseline for regression detection.

    Uses statistical significance testing (Mann-Whitney U) by default to
    reduce false positives from random variance.
    """
    runner = EvalRunner()
    reporter = Reporter(console)

    console.print(f"Loading baseline from {baseline}...")
    baseline_results = runner.load_results(baseline)

    console.print(f"Loading current from {current}...")
    current_results = runner.load_results(current)

    reporter.print_regression_comparison(baseline_results, current_results)

    # Check for regressions with statistical testing
    has_regressions, comparison_data = reporter.check_regression(
        baseline_results,
        current_results,
        threshold=threshold,
        require_significance=statistical,
    )

    if statistical:
        console.print("\n[dim]Using statistical significance testing (p < 0.05)[/dim]")

    if has_regressions:
        console.print(f"\n[red]REGRESSION DETECTED: {comparison_data['regression_count']} task(s)[/red]")
        for reg in comparison_data["regressions"]:
            console.print(f"  - {reg['task_id']}: {reg['delta']:+.0%}")
            if "p_value" in reg:
                console.print(f"    p-value: {reg['p_value']:.4f}, effect: {reg['effect_magnitude']}")
        raise SystemExit(1)
    else:
        console.print("\n[green]No regressions detected[/green]")


@cli.command()
@click.option(
    "--results",
    "-r",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to results JSON file",
)
def report(results: Path):
    """Generate report from existing results file."""
    runner = EvalRunner()
    reporter = Reporter(console)

    console.print(f"Loading results from {results}...")
    result_list = runner.load_results(results)

    reporter.print_summary(result_list)


@cli.command()
@click.argument("results_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--task",
    "-t",
    default=None,
    help="Filter by task ID (substring match)",
)
@click.option(
    "--failed-only",
    "-f",
    is_flag=True,
    help="Show only failed results",
)
def analyze(results_file: Path, task: str | None, failed_only: bool):
    """Analyze eval results with detailed breakdowns.

    Provides assertion-level analysis and identifies patterns in failures.
    """
    runner = EvalRunner()
    reporter = Reporter(console)

    console.print(f"Loading results from {results_file}...")
    results = runner.load_results(results_file)

    reporter.print_analysis(results, task_filter=task, failed_only=failed_only)


@cli.command("diff")
@click.argument("result_a", type=click.Path(exists=True, path_type=Path))
@click.argument("result_b", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--label-a",
    default="A",
    help="Label for first result set (default: A)",
)
@click.option(
    "--label-b",
    default="B",
    help="Label for second result set (default: B)",
)
def diff_results(result_a: Path, result_b: Path, label_a: str, label_b: str):
    """Compare two eval runs side-by-side.

    Useful for A/B testing different configurations or model versions.
    """
    runner = EvalRunner()
    reporter = Reporter(console)

    console.print(f"Loading {label_a} from {result_a}...")
    results_a = runner.load_results(result_a)

    console.print(f"Loading {label_b} from {result_b}...")
    results_b = runner.load_results(result_b)

    reporter.print_diff(results_a, results_b, label_a=label_a, label_b=label_b)


@cli.command()
@click.argument("results_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--result-index",
    "-i",
    type=int,
    required=True,
    help="Index of the result to explain (0-based)",
)
def explain(results_file: Path, result_index: int):
    """Deep dive into a single result with full context.

    Shows complete execution trace, file diffs, grading prompts,
    and full test output without truncation.
    """
    runner = EvalRunner()
    reporter = Reporter(console)

    console.print(f"Loading results from {results_file}...")
    results = runner.load_results(results_file)

    if result_index < 0 or result_index >= len(results):
        console.print(f"[red]Invalid index: {result_index}. Valid range: 0-{len(results)-1}[/red]")
        raise SystemExit(1)

    result = results[result_index]
    reporter.print_explain(result)


@cli.command()
@click.option(
    "--task",
    "-t",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to task YAML file",
)
def validate_task(task: Path):
    """Validate a task YAML file."""
    runner = EvalRunner()

    try:
        task_obj = runner.load_task(task)
        console.print(f"[green]Task '{task_obj.id}' is valid[/green]")
        console.print(f"  Category: {task_obj.category.value}")
        console.print(f"  Difficulty: {task_obj.difficulty.value}")
        console.print(f"  Assertions: {len(task_obj.assertions)}")
        console.print(f"  Code assertions: {len(task_obj.code_assertions)}")
        console.print(f"  LLM assertions: {len(task_obj.llm_assertions)}")
    except Exception as e:
        console.print(f"[red]Task validation failed: {e}[/red]")
        raise SystemExit(1)


@cli.command()
@click.option(
    "--config",
    "-c",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to config YAML file",
)
def validate_config(config: Path):
    """Validate a config YAML file."""
    runner = EvalRunner()

    try:
        config_obj = runner.load_config(config)
        console.print(f"[green]Config '{config_obj.name}' is valid[/green]")
        console.print(f"  Model: {config_obj.model}")
        console.print(f"  Max turns: {config_obj.max_turns}")
        console.print(f"  Has CLAUDE.md: {'Yes' if config_obj.claude_md else 'No'}")
        console.print(f"  Has skills: {'Yes' if config_obj.skills_path else 'No'}")
    except Exception as e:
        console.print(f"[red]Config validation failed: {e}[/red]")
        raise SystemExit(1)


@cli.command("export-config")
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Output file for config snapshot",
)
@click.option(
    "--claude-home",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to Claude home directory (default: ~/.claude)",
)
def export_config(output: Path, claude_home: Path | None):
    """Export current Claude Code configuration for CI.

    Creates a snapshot of your Claude Code configuration that can be
    imported in CI environments for reproducible evaluations.
    """
    exporter = ConfigExporter(claude_home)
    snapshot = exporter.export_snapshot()

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(snapshot.model_dump_json(indent=2))

    console.print(f"[green]Configuration exported to {output}[/green]")
    console.print(f"  Claude version: {snapshot.claude_version}")
    console.print(f"  Has CLAUDE.md: {'Yes' if snapshot.global_claude_md else 'No'}")
    console.print(f"  Skills exported: {len(snapshot.skills)}")
    console.print(f"  Source machine: {snapshot.source_machine}")


@cli.command("import-config")
@click.option(
    "--snapshot",
    "-s",
    required=True,
    type=click.Path(exists=True, path_type=Path),
    help="Path to config snapshot JSON",
)
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory to create CI environment in",
)
@click.option(
    "--enable-mcp/--disable-mcp",
    default=False,
    help="Enable MCP servers in CI (default: disabled)",
)
def import_config(snapshot: Path, output: Path, enable_mcp: bool):
    """Set up CI environment from exported snapshot.

    Creates an isolated Claude Code environment from a snapshot for CI use.
    Outputs environment variables to set.
    """
    importer = ConfigImporter()
    snapshot_data = importer.load_snapshot(snapshot)

    output.mkdir(parents=True, exist_ok=True)
    env_vars = importer.setup_ci_environment(
        snapshot_data,
        output,
        disable_mcp=not enable_mcp,
    )

    console.print("[green]CI environment created[/green]")
    console.print(f"  Location: {output}")
    console.print()
    console.print("[bold]Set these environment variables:[/bold]")
    for key, value in env_vars.items():
        console.print(f"export {key}={value}")


@cli.command("check-version")
def check_version():
    """Check Claude Code version and compatibility."""
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        version = result.stdout.strip().split("\n")[0] if result.stdout else "unknown"
        console.print(f"Claude Code version: {version}")

        # Check if it's a known compatible version
        if "unknown" not in version.lower():
            console.print("[green]Claude Code is installed and accessible[/green]")
        else:
            console.print("[yellow]Could not determine Claude Code version[/yellow]")
    except FileNotFoundError:
        console.print("[red]Claude Code not found - please install it first[/red]")
        raise SystemExit(1)
    except subprocess.TimeoutExpired:
        console.print("[red]Claude Code command timed out[/red]")
        raise SystemExit(1)


@cli.command("env-status")
@click.pass_context
def env_status(ctx: click.Context):
    """Show environment configuration status.

    Displays which .env file was loaded (if any) and the status of
    required environment variables.
    """
    console.print("[bold]Environment Status[/bold]")
    console.print("=" * 40)

    # Show .env file status
    env_file = ctx.obj.get("env_file")
    env_loaded = ctx.obj.get("env_loaded", False)

    if env_file:
        if env_loaded:
            console.print(f"[green]Loaded .env from: {env_file}[/green]")
        else:
            console.print(f"[red]Failed to load: {env_file}[/red]")
    elif env_loaded:
        # Find which default location was used
        for loc in [Path.cwd() / ".env", Path.home() / ".env", Path.cwd() / ".env.local"]:
            if loc.exists():
                console.print(f"[green]Loaded .env from: {loc}[/green]")
                break
    else:
        console.print("[yellow]No .env file loaded[/yellow]")
        console.print("[dim]Searched: ./.env, ~/.env, ./.env.local[/dim]")

    console.print()
    console.print("[bold]Required Environment Variables[/bold]")

    # Check required variables
    required_vars = [
        ("ANTHROPIC_API_KEY", "Required for LLM grading"),
    ]

    optional_vars = [
        ("EVAL_ENV_FILE", "Custom .env file path"),
        ("CLAUDE_HOME", "Claude Code home directory"),
    ]

    for var, description in required_vars:
        value = os.getenv(var)
        if value:
            # Mask the value for security
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            console.print(f"  [green]{var}[/green]: {masked}")
        else:
            console.print(f"  [red]{var}[/red]: NOT SET - {description}")

    console.print()
    console.print("[bold]Optional Environment Variables[/bold]")

    for var, description in optional_vars:
        value = os.getenv(var)
        if value:
            console.print(f"  [green]{var}[/green]: {value}")
        else:
            console.print(f"  [dim]{var}[/dim]: not set - {description}")


@cli.command()
@click.option(
    "--name",
    "-n",
    required=True,
    help="Name of the skill test (used for directory name)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory (default: current directory)",
)
@click.option(
    "--fixture-type",
    type=click.Choice(["python", "javascript"]),
    default="python",
    help="Type of fixture project to generate",
)
@click.option(
    "--skill-path",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to existing skill to copy into the scaffold",
)
def scaffold(
    name: str,
    output: Path | None,
    fixture_type: str,
    skill_path: Path | None,
):
    """Generate a skill-testing directory structure.

    Creates a complete scaffold for A/B testing a skill, including:
    - Task definitions
    - Baseline and with-skill configs
    - Sample fixture project
    - Run comparison script

    Example:
        uv run python -m harness scaffold --name my-skill-test --fixture-type python
    """
    generator = ScaffoldGenerator(name=name, output_dir=output)

    try:
        result_path = generator.generate(
            fixture_type=fixture_type,
            skill_path=skill_path,
        )
        console.print(f"[green]Scaffold created at: {result_path}[/green]")
        console.print()
        console.print("Generated structure:")
        console.print(f"  {result_path}/")
        console.print("  ├── README.md")
        console.print("  ├── run-comparison.sh")
        console.print("  ├── tasks/")
        console.print("  │   └── example.task.yaml")
        console.print("  ├── configs/")
        console.print("  │   ├── baseline/config.yaml")
        console.print("  │   └── with-skill/config.yaml")
        console.print("  ├── fixtures/")
        console.print("  │   └── sample-project/")
        console.print("  ├── skills/")
        if skill_path:
            console.print(f"  │   └── {skill_path.name}/")
        else:
            console.print("  │   └── your-skill/")
        console.print("  └── results/")
        console.print()
        console.print("Next steps:")
        console.print("  1. Add your skill to skills/")
        console.print("  2. Update configs/with-skill/config.yaml")
        console.print("  3. Customize tasks/ and fixtures/")
        console.print("  4. Run: ./run-comparison.sh")
    except Exception as e:
        console.print(f"[red]Failed to create scaffold: {e}[/red]")
        raise SystemExit(1)


@cli.command("power-analysis")
@click.option(
    "--baseline-rate",
    "-b",
    type=float,
    required=True,
    help="Expected baseline pass rate (0.0-1.0)",
)
@click.option(
    "--min-effect",
    "-e",
    type=float,
    default=0.1,
    help="Minimum effect size to detect (default: 0.1 = 10%)",
)
@click.option(
    "--power",
    "-p",
    type=float,
    default=0.8,
    help="Statistical power (default: 0.8 = 80%)",
)
@click.option(
    "--alpha",
    "-a",
    type=float,
    default=0.05,
    help="Significance level (default: 0.05)",
)
def power_analysis(baseline_rate: float, min_effect: float, power: float, alpha: float):
    """Calculate recommended sample size for reliable A/B testing.

    Uses power analysis to determine how many evaluation runs are needed
    to reliably detect a given effect size.

    Example:
        # How many runs to detect 10% improvement from 70% baseline?
        uv run python -m harness power-analysis -b 0.7 -e 0.1
    """
    result = StatisticalAnalyzer.minimum_sample_size(
        baseline_rate=baseline_rate,
        min_effect=min_effect,
        power=power,
        alpha=alpha,
    )

    console.print("\n[bold]POWER ANALYSIS RESULTS[/bold]")
    console.print("=" * 50)
    console.print(f"  Baseline pass rate: {result.baseline_rate:.0%}")
    console.print(f"  Minimum detectable effect: {result.min_detectable_effect:.0%}")
    console.print(f"  Statistical power: {result.power:.0%}")
    console.print(f"  Significance level (alpha): {result.alpha}")
    console.print()
    console.print(f"  [bold green]Recommended sample size: {result.recommended_sample_size}[/bold green]")
    console.print()
    console.print(f"  {result.notes}")
    console.print()
    console.print("[dim]Run this many evaluations per configuration for reliable comparison.[/dim]")


@cli.command("compare")
@click.argument("result_a", type=click.Path(exists=True, path_type=Path))
@click.argument("result_b", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--label-a",
    default="A",
    help="Label for first result set (default: A)",
)
@click.option(
    "--label-b",
    default="B",
    help="Label for second result set (default: B)",
)
@click.option(
    "--statistical",
    is_flag=True,
    default=True,
    help="Show statistical comparison (default: True)",
)
@click.option(
    "--efficiency/--no-efficiency",
    default=True,
    help="Include token/timing comparison (default: True)",
)
@click.option(
    "--cost",
    is_flag=True,
    default=False,
    help="Include USD cost comparison (default: False)",
)
def compare(
    result_a: Path,
    result_b: Path,
    label_a: str,
    label_b: str,
    statistical: bool,
    efficiency: bool,
    cost: bool,
):
    """Compare two result sets with statistical analysis.

    Shows side-by-side comparison with Mann-Whitney U test,
    effect size (Cohen's d), and actionable recommendations.

    Use --efficiency to show token and timing comparisons with
    statistical significance testing. Use --cost to add USD cost.

    Example:
        uv run python -m harness compare baseline.json current.json --statistical
        uv run python -m harness compare baseline.json current.json --efficiency --cost
    """
    runner = EvalRunner()
    reporter = Reporter(console)

    console.print(f"Loading {label_a} from {result_a}...")
    results_a = runner.load_results(result_a)

    console.print(f"Loading {label_b} from {result_b}...")
    results_b = runner.load_results(result_b)

    # Basic diff
    reporter.print_diff(results_a, results_b, label_a=label_a, label_b=label_b)

    # Statistical comparison if requested
    if statistical:
        reporter.print_statistical_comparison(
            results_a,
            results_b,
            label_a=label_a,
            label_b=label_b,
            show_efficiency=efficiency,
            show_cost=cost,
        )


@cli.command("build-image")
@click.option(
    "--no-cache",
    is_flag=True,
    help="Build without using cache",
)
def build_image(no_cache: bool):
    """Build the Docker container image for isolated evaluations.

    The image includes:
    - Claude Code CLI
    - Python with uv package manager
    - Node.js for JavaScript fixtures
    - Non-root user for security

    Example:
        uv run python -m harness build-image
    """
    from harness.container_manager import ContainerManager

    manager = ContainerManager()

    # Check Docker availability
    if not manager.is_docker_available():
        console.print("[red]Docker is not available.[/red]")
        console.print("Please install Docker and ensure it's running.")
        raise SystemExit(1)

    console.print("Building evaluation container image...")
    console.print(f"  Image: {manager.full_image}")
    if no_cache:
        console.print("  [dim]Building without cache[/dim]")

    try:
        success = manager.build_image(no_cache=no_cache)
        if success:
            console.print("[green]Image built successfully![/green]")
            console.print()
            console.print("You can now run evaluations in containers:")
            console.print("  uv run python -m harness run -t task.yaml -c config.yaml --container")
        else:
            console.print("[red]Image build failed.[/red]")
            console.print("Check the Docker build output above for errors.")
            raise SystemExit(1)
    except FileNotFoundError:
        console.print("[red]Dockerfile not found.[/red]")
        console.print("Ensure docker/Dockerfile exists in the project root.")
        raise SystemExit(1)
    except Exception as e:
        console.print(f"[red]Build failed: {e}[/red]")
        raise SystemExit(1)


@cli.command("image-status")
def image_status():
    """Check the status of the evaluation container image."""
    from harness.container_manager import ContainerManager

    manager = ContainerManager()

    if not manager.is_docker_available():
        console.print("[red]Docker is not available.[/red]")
        raise SystemExit(1)

    console.print(f"Checking image: {manager.full_image}")

    if manager.image_exists():
        console.print("[green]Image exists[/green]")

        info = manager.get_image_info()
        if info:
            created = info.get("Created", "unknown")
            size = info.get("Size", 0)
            size_mb = size / (1024 * 1024) if size else 0
            console.print(f"  Created: {created}")
            console.print(f"  Size: {size_mb:.1f} MB")
    else:
        console.print("[yellow]Image not found[/yellow]")
        console.print("Build with: uv run python -m harness build-image")


if __name__ == "__main__":
    cli()
