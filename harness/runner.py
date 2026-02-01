"""Main evaluation runner orchestrating the test matrix."""

import json
from datetime import datetime
from pathlib import Path

import yaml

from harness.executor import ClaudeExecutor, Executor
from harness.graders.composite_grader import CompositeGrader
from harness.isolator import EnvironmentIsolator
from harness.models import (
    AssertionType,
    CodeAssertion,
    CodeCheckType,
    Config,
    ConfigSnapshot,
    EvalResult,
    LLMAssertion,
    Task,
    TaskCategory,
    TaskDifficulty,
)


class EvalRunner:
    """Orchestrates evaluation runs across tasks, configs, and models."""

    def __init__(
        self,
        executor: Executor | None = None,
        grader: CompositeGrader | None = None,
        isolator: EnvironmentIsolator | None = None,
        results_dir: Path | None = None,
    ):
        """Initialize the runner.

        Args:
            executor: Executor for running prompts (default: ClaudeExecutor)
            grader: Grader for evaluation (default: CompositeGrader)
            isolator: Environment isolator (default: EnvironmentIsolator)
            results_dir: Directory to store results
        """
        self.executor = executor or ClaudeExecutor()
        self.grader = grader or CompositeGrader()
        self.isolator = isolator or EnvironmentIsolator()
        self.results_dir = results_dir or Path("evals/results")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    def run_single(
        self,
        task: Task,
        config: Config,
        run_index: int = 0,
    ) -> EvalResult:
        """Run a single task with a single config.

        Args:
            task: Task to evaluate
            config: Configuration to use
            run_index: Index of this run (for repeated runs)

        Returns:
            EvalResult with scores and trace
        """
        # Create isolated environment
        with self.isolator.create_environment(
            fixture_path=task.fixture_path,
            claude_md=config.claude_md,
            skills_path=config.skills_path,
            agents_md=config.agents_md,
        ) as env:
            # Snapshot files before execution
            before_state = self.isolator.snapshot_files(env.path)

            # Execute the prompt
            trace = self.executor.run(
                prompt=task.prompt,
                config=config,
                working_dir=env.path,
                timeout=task.timeout_seconds,
            )

            # Capture file changes
            trace.file_changes = self.isolator.diff_files(before_state, env.path)
            trace.claude_prompt = task.prompt
            trace.config_snapshot = ConfigSnapshot(
                model=config.model,
                claude_md=config.claude_md[:200] if config.claude_md else None,
                skills_path=str(config.skills_path) if config.skills_path else None,
                max_turns=config.max_turns,
            )
            trace.max_turns = config.max_turns
            trace.hit_turn_limit = trace.num_turns >= config.max_turns

            # Grade the results
            grades, overall_score, passed = self.grader.grade(task, trace, env.path)

            return EvalResult(
                task_id=task.id,
                config_name=config.name,
                model=config.model,
                run_index=run_index,
                trace=trace,
                grades=grades,
                overall_score=overall_score,
                passed=passed,
            )

    def run_matrix(
        self,
        tasks: list[Task],
        configs: list[Config],
        models: list[str] | None = None,
        runs_per_combo: int = 3,
        callback=None,
    ) -> list[EvalResult]:
        """Run full evaluation matrix.

        Args:
            tasks: List of tasks to evaluate
            configs: List of configs to test
            models: List of models (overrides config.model if provided)
            runs_per_combo: Number of runs per combination
            callback: Optional callback(task, config, model, run, result) for progress

        Returns:
            List of all EvalResults
        """
        results = []

        for task in tasks:
            for config in configs:
                models_to_test = models or [config.model]

                for model in models_to_test:
                    # Create config variant with this model
                    config_with_model = config.model_copy()
                    config_with_model.model = model

                    for run_idx in range(runs_per_combo):
                        result = self.run_single(task, config_with_model, run_idx)
                        results.append(result)

                        if callback:
                            callback(task, config, model, run_idx, result)

        return results

    def save_results(
        self,
        results: list[EvalResult],
        filename: str | None = None,
        save_debug: bool = True,
    ) -> Path:
        """Save results to JSON file.

        Args:
            results: Results to save
            filename: Optional filename (default: timestamped)
            save_debug: Whether to save detailed debug log (default: True)

        Returns:
            Path to saved file
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results_{timestamp}.json"

        output_path = self.results_dir / filename

        # Convert to JSON-serializable format (summary data)
        data = {
            "timestamp": datetime.now().isoformat(),
            "num_results": len(results),
            "results": [r.model_dump(mode="json") for r in results],
        }

        output_path.write_text(json.dumps(data, indent=2, default=str))

        # Save detailed debug log
        if save_debug:
            debug_path = output_path.with_suffix(".debug.json")
            debug_data = {
                "timestamp": datetime.now().isoformat(),
                "num_results": len(results),
                "results": [self._full_result_dump(r) for r in results],
                "execution_summary": self._build_execution_summary(results),
            }
            debug_path.write_text(json.dumps(debug_data, indent=2, default=str))

        return output_path

    def _full_result_dump(self, result: EvalResult) -> dict:
        """Create full result dump with all debug information.

        Args:
            result: EvalResult to dump

        Returns:
            Dict with complete debug information
        """
        data = result.model_dump(mode="json")

        # Add enhanced trace data
        data["trace"]["file_changes_summary"] = [
            {"path": fc.path, "action": fc.action}
            for fc in result.trace.file_changes
        ]
        data["trace"]["tool_call_timeline"] = [
            {
                "name": tc.name,
                "had_error": tc.error is not None,
                "timestamp": tc.timestamp.isoformat() if tc.timestamp else None,
            }
            for tc in result.trace.tool_calls
        ]

        # Add grading details
        data["grading_breakdown"] = [
            {
                "assertion_id": g.assertion_id,
                "assertion_type": g.assertion_type,
                "assertion_name": g.assertion_name,
                "passed": g.passed,
                "score": g.score,
                "has_full_output": bool(g.full_output),
                "has_grading_prompt": bool(g.grading_prompt),
                "num_criteria": len(g.criteria_scores),
            }
            for g in result.grades
        ]

        return data

    def _build_execution_summary(self, results: list[EvalResult]) -> dict:
        """Build summary of execution across all results.

        Args:
            results: List of EvalResults

        Returns:
            Summary dict
        """
        total_files_changed = sum(len(r.trace.file_changes) for r in results)
        total_tool_calls = sum(len(r.trace.tool_calls) for r in results)
        hit_turn_limit_count = sum(1 for r in results if r.trace.hit_turn_limit)

        return {
            "total_results": len(results),
            "total_passed": sum(1 for r in results if r.passed),
            "total_failed": sum(1 for r in results if not r.passed),
            "total_files_changed": total_files_changed,
            "total_tool_calls": total_tool_calls,
            "hit_turn_limit_count": hit_turn_limit_count,
            "unique_tasks": len(set(r.task_id for r in results)),
            "unique_configs": len(set(r.config_name for r in results)),
        }

    def load_results(self, path: Path) -> list[EvalResult]:
        """Load results from JSON file.

        Args:
            path: Path to results file

        Returns:
            List of EvalResults
        """
        data = json.loads(path.read_text())
        return [EvalResult.model_validate(r) for r in data["results"]]

    @staticmethod
    def load_task(path: Path) -> Task:
        """Load a task from YAML file.

        Args:
            path: Path to .task.yaml file

        Returns:
            Parsed Task object
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        # Parse assertions
        assertions = []
        for a in data.get("assertions", []):
            if a["type"] == "code":
                assertions.append(
                    CodeAssertion(
                        type=AssertionType.CODE,
                        check=CodeCheckType(a["check"]),
                        command=a.get("command"),
                        file=a.get("file"),
                        pattern=a.get("pattern"),
                    )
                )
            elif a["type"] == "llm":
                assertions.append(
                    LLMAssertion(
                        type=AssertionType.LLM,
                        rubric=a["rubric"],
                    )
                )

        # Resolve fixture path relative to task file
        fixture_path = None
        if "fixture_path" in data:
            fixture_path = path.parent / data["fixture_path"]

        return Task(
            id=data["id"],
            category=TaskCategory(data["category"]),
            description=data["description"],
            difficulty=TaskDifficulty(data.get("difficulty", "medium")),
            prompt=data["prompt"],
            assertions=assertions,
            scoring=data.get("scoring", {}),
            fixture_path=fixture_path,
            timeout_seconds=data.get("timeout_seconds", 300),
        )

    @staticmethod
    def load_config(path: Path) -> Config:
        """Load a config from YAML file.

        Args:
            path: Path to config.yaml file

        Returns:
            Parsed Config object
        """
        with open(path) as f:
            data = yaml.safe_load(f)

        return Config(
            name=data["name"],
            description=data.get("description", ""),
            claude_md=data.get("claude_md"),
            skills_path=Path(data["skills_path"]) if data.get("skills_path") else None,
            agents_md=data.get("agents_md"),
            model=data.get("model", "claude-sonnet-4-20250514"),
            max_turns=data.get("max_turns", 10),
            allowed_tools=data.get("allowed_tools", "all"),
        )

    def load_tasks_from_glob(self, pattern: str) -> list[Task]:
        """Load all tasks matching a glob pattern.

        Args:
            pattern: Glob pattern like "evals/tasks/**/*.task.yaml"

        Returns:
            List of Task objects
        """
        tasks = []
        for path in Path(".").glob(pattern):
            try:
                tasks.append(self.load_task(path))
            except Exception as e:
                print(f"Warning: Failed to load task {path}: {e}")
        return tasks

    def load_configs_from_glob(self, pattern: str) -> list[Config]:
        """Load all configs matching a glob pattern.

        Args:
            pattern: Glob pattern like "evals/configs/*/config.yaml"

        Returns:
            List of Config objects
        """
        configs = []
        for path in Path(".").glob(pattern):
            try:
                configs.append(self.load_config(path))
            except Exception as e:
                print(f"Warning: Failed to load config {path}: {e}")
        return configs
