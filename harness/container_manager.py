"""Docker container lifecycle management for isolated eval runs."""

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ContainerConfig:
    """Configuration for container execution."""

    image: str = "agent-eval:latest"
    memory_limit: str = "4g"
    cpu_limit: float = 2.0
    network_enabled: bool = True
    timeout: int = 600  # 10 minutes max
    user: str = "eval"


@dataclass
class ContainerResult:
    """Result from container execution."""

    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    container_id: str | None = None
    artifacts_path: Path | None = None


class ContainerManager:
    """Manages Docker containers for isolated evaluation runs."""

    def __init__(
        self,
        docker_path: str = "docker",
        image_name: str = "agent-eval",
        image_tag: str = "latest",
    ):
        """Initialize the container manager.

        Args:
            docker_path: Path to docker executable
            image_name: Name of the container image
            image_tag: Tag for the container image
        """
        self.docker_path = docker_path
        self.image_name = image_name
        self.image_tag = image_tag
        self.full_image = f"{image_name}:{image_tag}"

    def is_docker_available(self) -> bool:
        """Check if Docker is available and running."""
        try:
            result = subprocess.run(
                [self.docker_path, "info"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def image_exists(self) -> bool:
        """Check if the eval image exists."""
        try:
            result = subprocess.run(
                [self.docker_path, "images", "-q", self.full_image],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return bool(result.stdout.strip())
        except subprocess.SubprocessError:
            return False

    def build_image(
        self,
        dockerfile_path: Path | None = None,
        context_path: Path | None = None,
        no_cache: bool = False,
    ) -> bool:
        """Build the evaluation container image.

        Args:
            dockerfile_path: Path to Dockerfile (defaults to docker/Dockerfile)
            context_path: Build context path (defaults to the Dockerfile's directory, e.g. docker/)
            no_cache: Whether to build without cache

        Returns:
            True if build succeeded, False otherwise
        """
        # Find the docker directory relative to this module
        if dockerfile_path is None:
            module_dir = Path(__file__).parent
            dockerfile_path = module_dir.parent / "docker" / "Dockerfile"

        if context_path is None:
            context_path = dockerfile_path.parent

        if not dockerfile_path.exists():
            raise FileNotFoundError(f"Dockerfile not found: {dockerfile_path}")

        cmd = [
            self.docker_path,
            "build",
            "-t",
            self.full_image,
            "-f",
            str(dockerfile_path),
        ]

        if no_cache:
            cmd.append("--no-cache")

        cmd.append(str(context_path))

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute build timeout
        )

        return result.returncode == 0

    def run_evaluation(
        self,
        prompt: str,
        fixture_path: Path,
        results_path: Path,
        config: ContainerConfig | None = None,
        env_vars: dict[str, str] | None = None,
        claude_md: str | None = None,
        skills_path: Path | None = None,
        model: str = "claude-sonnet-4-20250514",
        max_turns: int = 10,
    ) -> ContainerResult:
        """Run an evaluation in a container.

        Args:
            prompt: The evaluation prompt
            fixture_path: Path to fixture project to mount
            results_path: Path to store results
            config: Container configuration
            env_vars: Environment variables to pass (e.g., API keys)
            claude_md: CLAUDE.md content
            skills_path: Path to skills directory
            model: Model to use
            max_turns: Maximum turns

        Returns:
            ContainerResult with execution details
        """
        import time

        config = config or ContainerConfig()
        env_vars = env_vars or {}

        # Ensure ANTHROPIC_API_KEY is available
        if "ANTHROPIC_API_KEY" not in env_vars:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if api_key:
                env_vars["ANTHROPIC_API_KEY"] = api_key

        # Create results directory
        results_path.mkdir(parents=True, exist_ok=True)

        # Write prompt to temp file for mounting
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False
        ) as prompt_file:
            prompt_file.write(prompt)
            prompt_path = Path(prompt_file.name)

        # Write CLAUDE.md if provided
        claude_md_path = None
        if claude_md:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".md", delete=False
            ) as claude_file:
                claude_file.write(claude_md)
                claude_md_path = Path(claude_file.name)

        try:
            # Build docker command
            cmd = self._build_run_command(
                config=config,
                fixture_path=fixture_path,
                results_path=results_path,
                prompt_path=prompt_path,
                env_vars=env_vars,
                claude_md_path=claude_md_path,
                skills_path=skills_path,
                model=model,
                max_turns=max_turns,
            )

            start_time = time.time()

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=config.timeout,
            )

            duration = time.time() - start_time

            return ContainerResult(
                exit_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                duration_seconds=duration,
                artifacts_path=results_path,
            )

        except subprocess.TimeoutExpired:
            return ContainerResult(
                exit_code=-1,
                stdout="",
                stderr="Container execution timed out",
                duration_seconds=float(config.timeout),
            )
        finally:
            # Cleanup temp files
            prompt_path.unlink(missing_ok=True)
            if claude_md_path:
                claude_md_path.unlink(missing_ok=True)

    def _build_run_command(
        self,
        config: ContainerConfig,
        fixture_path: Path,
        results_path: Path,
        prompt_path: Path,
        env_vars: dict[str, str],
        claude_md_path: Path | None,
        skills_path: Path | None,
        model: str,
        max_turns: int,
    ) -> list[str]:
        """Build the docker run command."""
        # Use host UID:GID to avoid permission issues with mounted volumes
        # Get current user's UID and GID, fallback to config.user if not available
        import os
        uid = os.getuid() if hasattr(os, 'getuid') else None
        gid = os.getgid() if hasattr(os, 'getgid') else None
        user_spec = f"{uid}:{gid}" if uid is not None and gid is not None else config.user
        
        cmd = [
            self.docker_path,
            "run",
            "--rm",  # Auto-cleanup
            f"--memory={config.memory_limit}",
            f"--cpus={config.cpu_limit}",
            f"--user={user_spec}",
        ]

        # Network control
        if not config.network_enabled:
            cmd.append("--network=none")

        # Mount volumes
        cmd.extend([
            "-v",
            f"{fixture_path.absolute()}:/workspace/project:rw",
            "-v",
            f"{results_path.absolute()}:/workspace/results:rw",
            "-v",
            f"{prompt_path.absolute()}:/workspace/prompt.txt:ro",
        ])

        # Mount CLAUDE.md if provided
        if claude_md_path:
            cmd.extend([
                "-v",
                f"{claude_md_path.absolute()}:/workspace/project/CLAUDE.md:ro",
            ])

        # Mount skills if provided
        if skills_path and skills_path.exists():
            cmd.extend([
                "-v",
                f"{skills_path.absolute()}:/home/eval/.claude/skills:ro",
            ])

        # Environment variables
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])

        # Pass model and max_turns
        cmd.extend([
            "-e",
            f"EVAL_MODEL={model}",
            "-e",
            f"EVAL_MAX_TURNS={max_turns}",
        ])

        # Working directory
        cmd.extend(["-w", "/workspace/project"])

        # Image: use config.image if provided, otherwise fall back to self.full_image
        image = config.image if config.image else self.full_image
        cmd.append(image)

        return cmd

    def extract_results(
        self,
        container_id: str,
        dest_path: Path,
    ) -> bool:
        """Extract results from a container.

        Args:
            container_id: Container ID
            dest_path: Destination path for results

        Returns:
            True if extraction succeeded
        """
        cmd = [
            self.docker_path,
            "cp",
            f"{container_id}:/workspace/results/.",
            str(dest_path),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        return result.returncode == 0

    def cleanup_container(self, container_id: str) -> bool:
        """Remove a container.

        Args:
            container_id: Container ID to remove

        Returns:
            True if removal succeeded
        """
        cmd = [self.docker_path, "rm", "-f", container_id]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.returncode == 0

    def get_image_info(self) -> dict | None:
        """Get information about the eval image.

        Returns:
            Dict with image info or None if not found
        """
        try:
            result = subprocess.run(
                [
                    self.docker_path,
                    "inspect",
                    self.full_image,
                    "--format",
                    "{{json .}}",
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                return json.loads(result.stdout)
            return None
        except (subprocess.SubprocessError, json.JSONDecodeError):
            return None
