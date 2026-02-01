"""Container-based executor for running evaluations in Docker."""

import json
import tempfile
from pathlib import Path

from harness.container_manager import ContainerConfig, ContainerManager
from harness.executor import Executor
from harness.models import Config, ExecutionTrace, TokenUsage, ToolCall


class ContainerExecutor(Executor):
    """Executor that runs evaluations inside Docker containers."""

    def __init__(
        self,
        manager: ContainerManager | None = None,
        config: ContainerConfig | None = None,
        network_enabled: bool = True,
        memory_limit: str = "4g",
        cpu_limit: float = 2.0,
    ):
        """Initialize the container executor.

        Args:
            manager: ContainerManager instance (created if not provided)
            config: Container configuration
            network_enabled: Whether to enable network access
            memory_limit: Memory limit for container
            cpu_limit: CPU limit for container
        """
        self.manager = manager or ContainerManager()
        self.config = config or ContainerConfig(
            network_enabled=network_enabled,
            memory_limit=memory_limit,
            cpu_limit=cpu_limit,
        )

    def run(
        self,
        prompt: str,
        config: Config,
        working_dir: Path,
        timeout: int = 300,
        env_override: dict[str, str] | None = None,
    ) -> ExecutionTrace:
        """Execute a prompt in a Docker container.

        Args:
            prompt: The prompt to execute
            config: Configuration to use
            working_dir: Working directory (fixture path)
            timeout: Timeout in seconds
            env_override: Optional environment variable overrides

        Returns:
            ExecutionTrace with results and metadata
        """
        # Check if Docker is available
        if not self.manager.is_docker_available():
            return ExecutionTrace(
                result="Docker is not available",
                is_error=True,
                duration_seconds=0.0,
            )

        # Check if image exists
        if not self.manager.image_exists():
            return ExecutionTrace(
                result="Docker image not found. Run 'uv run python -m harness build-image' first.",
                is_error=True,
                duration_seconds=0.0,
            )

        # Create temp directory for results
        with tempfile.TemporaryDirectory(prefix="eval_results_") as results_dir:
            results_path = Path(results_dir)

            # Update container config with timeout
            container_config = ContainerConfig(
                image=self.config.image,
                memory_limit=self.config.memory_limit,
                cpu_limit=self.config.cpu_limit,
                network_enabled=self.config.network_enabled,
                timeout=timeout,
                user=self.config.user,
            )

            # Prepare environment variables, including allowed tools if configured
            env_vars: dict[str, str] = dict(env_override) if env_override is not None else {}
            if getattr(config, "allowed_tools", None) is not None:
                # Pass allowed tools as JSON so the container entrypoint can enforce them
                env_vars["ALLOWED_TOOLS"] = json.dumps(config.allowed_tools)

            # Run evaluation in container
            result = self.manager.run_evaluation(
                prompt=prompt,
                fixture_path=working_dir,
                results_path=results_path,
                config=container_config,
                env_vars=env_vars,
                claude_md=config.claude_md,
                skills_path=config.skills_path,
                model=config.model,
                max_turns=config.max_turns,
            )

            # Parse output into ExecutionTrace
            return self._parse_container_output(result, results_path)

    def _parse_container_output(
        self,
        result,
        results_path: Path,
    ) -> ExecutionTrace:
        """Parse container output into ExecutionTrace.

        Args:
            result: ContainerResult from container execution
            results_path: Path to results directory

        Returns:
            ExecutionTrace
        """
        # Try to read JSON output from results
        output_file = results_path / "output.json"
        if output_file.exists():
            try:
                output = json.loads(output_file.read_text())
                return self._trace_from_json(output, result.duration_seconds)
            except (json.JSONDecodeError, OSError):
                pass

        # Fall back to parsing stdout
        if result.stdout.strip():
            try:
                output = json.loads(result.stdout)
                return self._trace_from_json(output, result.duration_seconds)
            except json.JSONDecodeError:
                pass

        # Return error trace if execution failed
        if result.exit_code != 0:
            return ExecutionTrace(
                result=result.stderr or result.stdout or "Container execution failed",
                is_error=True,
                duration_seconds=result.duration_seconds,
                raw_output={
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        # Return stdout as result
        return ExecutionTrace(
            result=result.stdout,
            is_error=False,
            duration_seconds=result.duration_seconds,
            raw_output={
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    def _trace_from_json(
        self,
        output: dict,
        duration: float,
    ) -> ExecutionTrace:
        """Create ExecutionTrace from JSON output.

        Args:
            output: Parsed JSON output
            duration: Execution duration in seconds

        Returns:
            ExecutionTrace
        """
        # Extract token usage
        usage = TokenUsage.from_dict(output.get("usage", {}))

        # Extract tool calls
        tool_calls = []
        for call in output.get("tool_calls", []):
            tool_calls.append(
                ToolCall(
                    name=call.get("name", "unknown"),
                    input=call.get("input", {}),
                    output=call.get("output"),
                    error=call.get("error"),
                )
            )

        return ExecutionTrace(
            session_id=output.get("session_id"),
            result=output.get("result", ""),
            is_error=output.get("is_error", False),
            usage=usage,
            tool_calls=tool_calls,
            duration_seconds=duration,
            num_turns=output.get("num_turns", len(tool_calls)),
            raw_output=output,
        )

    def ensure_image(self, force_rebuild: bool = False) -> bool:
        """Ensure the Docker image exists, building if necessary.

        Args:
            force_rebuild: Force rebuild even if image exists

        Returns:
            True if image is available
        """
        if not force_rebuild and self.manager.image_exists():
            return True

        return self.manager.build_image()
