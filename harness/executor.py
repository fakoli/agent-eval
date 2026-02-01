"""Claude Code executor for running evaluations."""

import json
import os
import subprocess
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path

from harness.models import Config, ExecutionTrace, TokenUsage, ToolCall


class Executor(ABC):
    """Abstract base class for code execution."""

    @abstractmethod
    def run(
        self,
        prompt: str,
        config: Config,
        working_dir: Path,
        timeout: int = 300,
        env_override: dict[str, str] | None = None,
    ) -> ExecutionTrace:
        """Execute a prompt and return the trace.

        Args:
            prompt: The prompt to execute
            config: Configuration to use
            working_dir: Working directory for execution
            timeout: Timeout in seconds
            env_override: Optional environment variable overrides

        Returns:
            ExecutionTrace with results and metadata
        """
        pass


class ClaudeExecutor(Executor):
    """Executor that uses the Claude Code CLI."""

    def __init__(
        self,
        claude_path: str = "claude",
        ci_mode: bool = False,
        mcp_config_path: Path | None = None,
        skip_permissions: bool = True,
    ):
        """Initialize executor.

        Args:
            claude_path: Path to claude CLI executable
            ci_mode: Whether running in CI mode (adds isolation flags)
            mcp_config_path: Optional path to MCP config file for CI
            skip_permissions: Skip permission checks for automated execution
        """
        self.claude_path = claude_path
        self.ci_mode = ci_mode
        self.mcp_config_path = mcp_config_path
        self.skip_permissions = skip_permissions

    def run(
        self,
        prompt: str,
        config: Config,
        working_dir: Path,
        timeout: int = 300,
        env_override: dict[str, str] | None = None,
    ) -> ExecutionTrace:
        """Execute a prompt using Claude Code CLI.

        Args:
            prompt: The prompt to execute
            config: Configuration to use
            working_dir: Working directory for execution
            timeout: Timeout in seconds
            env_override: Optional environment variable overrides

        Returns:
            ExecutionTrace with results and metadata
        """
        cmd = self._build_command(prompt, config)

        # Set up environment
        env = os.environ.copy()
        if env_override:
            env.update(env_override)

        start_time = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
            duration = time.time() - start_time

            return self._parse_output(result.stdout, result.stderr, duration)
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return ExecutionTrace(
                result="Execution timed out",
                is_error=True,
                duration_seconds=duration,
            )
        except Exception as e:
            duration = time.time() - start_time
            return ExecutionTrace(
                result=f"Execution failed: {e}",
                is_error=True,
                duration_seconds=duration,
            )

    def _build_command(self, prompt: str, config: Config) -> list[str]:
        """Build the CLI command."""
        cmd = [
            self.claude_path,
            "-p",
            prompt,
            "--model",
            config.model,
            "--output-format",
            "json",
            "--max-turns",
            str(config.max_turns),
        ]

        # Skip permission checks for automated execution
        if self.skip_permissions:
            cmd.append("--dangerously-skip-permissions")

        # CI isolation flags
        if self.ci_mode:
            # Disable session persistence for reproducibility
            cmd.append("--no-session-persistence")
            # Use specific MCP config if provided
            if self.mcp_config_path:
                cmd.extend(["--mcp-config", str(self.mcp_config_path)])

        # Add allowed tools
        if config.allowed_tools != "all":
            cmd.extend(["--allowedTools", ",".join(config.allowed_tools)])

        # Add system prompt from CLAUDE.md if specified
        if config.claude_md:
            cmd.extend(["--append-system-prompt", config.claude_md])

        return cmd

    def _parse_output(
        self, stdout: str, stderr: str, duration: float
    ) -> ExecutionTrace:
        """Parse CLI output into ExecutionTrace."""
        try:
            # Try to parse JSON output
            output = json.loads(stdout) if stdout.strip() else {}

            # Extract fields from JSON output
            session_id = output.get("session_id")
            result_text = output.get("result", stdout)
            is_error = output.get("is_error", False)

            # Extract token usage
            usage_data = output.get("usage", {})
            usage = TokenUsage(
                input_tokens=usage_data.get("input_tokens", 0),
                output_tokens=usage_data.get("output_tokens", 0),
                cache_read_tokens=usage_data.get("cache_read_tokens", 0),
                cache_creation_tokens=usage_data.get("cache_creation_tokens", 0),
            )

            # Extract tool calls
            tool_calls = self._extract_tool_calls(output)

            # Count turns
            num_turns = output.get("num_turns", len(tool_calls))

            return ExecutionTrace(
                session_id=session_id,
                result=result_text,
                is_error=is_error,
                usage=usage,
                tool_calls=tool_calls,
                duration_seconds=duration,
                num_turns=num_turns,
                raw_output=output,
            )
        except json.JSONDecodeError:
            # Fallback for non-JSON output
            return ExecutionTrace(
                result=stdout or stderr,
                is_error=bool(stderr),
                duration_seconds=duration,
                raw_output={"stdout": stdout, "stderr": stderr},
            )

    def _extract_tool_calls(self, output: dict) -> list[ToolCall]:
        """Extract tool calls from output."""
        tool_calls = []
        raw_calls = output.get("tool_calls", [])

        for call in raw_calls:
            tool_calls.append(
                ToolCall(
                    name=call.get("name", "unknown"),
                    input=call.get("input", {}),
                    output=call.get("output"),
                    error=call.get("error"),
                    timestamp=datetime.fromisoformat(call["timestamp"])
                    if "timestamp" in call
                    else None,
                )
            )

        return tool_calls
