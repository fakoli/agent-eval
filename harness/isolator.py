"""Environment isolation for evaluation runs."""

import difflib
import json
import shutil
import tarfile
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from harness.models import FileChange


@dataclass
class IsolatedEnv:
    """An isolated environment for a single evaluation run."""

    path: Path
    temp_root: Path
    _cleaned_up: bool = field(default=False, repr=False)

    def cleanup(self) -> None:
        """Clean up the isolated environment."""
        if not self._cleaned_up and self.temp_root.exists():
            shutil.rmtree(self.temp_root)
            self._cleaned_up = True

    def __enter__(self) -> "IsolatedEnv":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()


class EnvironmentIsolator:
    """Creates isolated environments for evaluation runs."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize isolator.

        Args:
            base_dir: Base directory for temp environments. Defaults to system temp.
        """
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.gettempdir())

    def create_environment(
        self,
        fixture_path: Path | None = None,
        claude_md: str | None = None,
        skills_path: Path | None = None,
        agents_md: str | None = None,
    ) -> IsolatedEnv:
        """Create an isolated test environment.

        Args:
            fixture_path: Path to fixture project to copy
            claude_md: Content for CLAUDE.md file
            skills_path: Path to skills directory to copy
            agents_md: Content for agents.md file

        Returns:
            IsolatedEnv with the environment path
        """
        # Create temp directory
        temp_root = Path(tempfile.mkdtemp(prefix="eval_", dir=self.base_dir))
        project_dir = temp_root / "project"
        project_dir.mkdir()

        # Copy fixture if provided
        if fixture_path and fixture_path.exists():
            shutil.copytree(fixture_path, project_dir, dirs_exist_ok=True)

        # Write CLAUDE.md if specified
        if claude_md:
            (project_dir / "CLAUDE.md").write_text(claude_md)

        # Write agents.md if specified
        if agents_md:
            (project_dir / "agents.md").write_text(agents_md)

        # Copy skills if specified
        if skills_path and skills_path.exists():
            claude_dir = temp_root / ".claude"
            claude_dir.mkdir()
            shutil.copytree(skills_path, claude_dir / "skills")

        return IsolatedEnv(path=project_dir, temp_root=temp_root)

    def create_environment_for_task(
        self,
        task_fixture: Path | None,
        claude_md: str | None = None,
        skills_path: Path | None = None,
        agents_md: str | None = None,
    ) -> IsolatedEnv:
        """Create environment for a specific task.

        This is a convenience method that uses task's fixture path.

        Args:
            task_fixture: Path to task's fixture directory
            claude_md: Content for CLAUDE.md
            skills_path: Path to skills directory
            agents_md: Content for agents.md

        Returns:
            IsolatedEnv ready for task execution
        """
        return self.create_environment(
            fixture_path=task_fixture,
            claude_md=claude_md,
            skills_path=skills_path,
            agents_md=agents_md,
        )

    def snapshot_files(
        self,
        env_path: Path,
        patterns: list[str] | None = None,
    ) -> dict[str, str]:
        """Capture file contents before execution.

        Args:
            env_path: Path to the evaluation environment
            patterns: Glob patterns for files to track (default: source files)

        Returns:
            Dict mapping relative path to file content
        """
        if patterns is None:
            patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.java", "**/*.go", "**/*.rs"]

        snapshot: dict[str, str] = {}

        for pattern in patterns:
            for file_path in env_path.glob(pattern):
                if file_path.is_file():
                    try:
                        rel_path = str(file_path.relative_to(env_path))
                        # Skip very large files (> 1MB)
                        if file_path.stat().st_size <= 1_000_000:
                            snapshot[rel_path] = file_path.read_text(errors="replace")
                    except (OSError, UnicodeDecodeError):
                        continue

        return snapshot

    def diff_files(
        self,
        before: dict[str, str],
        env_path: Path,
        patterns: list[str] | None = None,
    ) -> list[FileChange]:
        """Calculate file changes after execution.

        Args:
            before: Snapshot from snapshot_files()
            env_path: Path to the evaluation environment
            patterns: Glob patterns for files to track (default: source files)

        Returns:
            List of FileChange records
        """
        if patterns is None:
            patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.java", "**/*.go", "**/*.rs"]

        # Get current state
        after: dict[str, str] = {}
        for pattern in patterns:
            for file_path in env_path.glob(pattern):
                if file_path.is_file():
                    try:
                        rel_path = str(file_path.relative_to(env_path))
                        if file_path.stat().st_size <= 1_000_000:
                            after[rel_path] = file_path.read_text(errors="replace")
                    except (OSError, UnicodeDecodeError):
                        continue

        changes: list[FileChange] = []

        # Find created and modified files
        for path, content in after.items():
            if path not in before:
                # New file created
                changes.append(
                    FileChange(
                        path=path,
                        action="created",
                        content_after=content[:10000] if len(content) > 10000 else content,
                    )
                )
            elif before[path] != content:
                # File modified - compute unified diff
                diff = self._compute_diff(before[path], content, path)
                changes.append(
                    FileChange(
                        path=path,
                        action="modified",
                        diff=diff,
                    )
                )

        # Find deleted files
        for path in before:
            if path not in after:
                changes.append(
                    FileChange(
                        path=path,
                        action="deleted",
                    )
                )

        return changes

    def _compute_diff(
        self,
        before_content: str,
        after_content: str,
        path: str,
    ) -> str:
        """Compute unified diff between two file contents.

        Args:
            before_content: Original file content
            after_content: Modified file content
            path: File path for diff header

        Returns:
            Unified diff string
        """
        before_lines = before_content.splitlines(keepends=True)
        after_lines = after_content.splitlines(keepends=True)

        diff_lines = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
        )

        diff_text = "".join(diff_lines)
        # Truncate very long diffs
        if len(diff_text) > 10000:
            diff_text = diff_text[:10000] + "\n... (truncated)"

        return diff_text

    def archive_run(
        self,
        env: IsolatedEnv,
        run_id: str,
        artifacts_dir: Path,
        before_state: dict[str, str],
        metadata: dict[str, Any] | None = None,
        claude_output: dict[str, Any] | None = None,
        test_output: str | None = None,
    ) -> Path:
        """Archive the results of an evaluation run.

        Creates a directory with all artifacts from the run, including:
        - Original fixture state (before.tar.gz)
        - Modified fixture state (after.tar.gz)
        - File changes diff
        - Claude output JSON
        - Test output log
        - Metadata JSON

        Args:
            env: The isolated environment
            run_id: Unique identifier for this run
            artifacts_dir: Base directory for storing artifacts
            before_state: Snapshot of files before execution (from snapshot_files)
            metadata: Additional metadata to include
            claude_output: Claude execution output (raw JSON)
            test_output: Test execution output

        Returns:
            Path to the archive directory
        """
        # Create archive directory
        archive_dir = artifacts_dir / run_id
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Create metadata
        run_metadata = {
            "run_id": run_id,
            "timestamp": datetime.now().isoformat(),
            "env_path": str(env.path),
            "files_before_count": len(before_state),
        }
        if metadata:
            run_metadata.update(metadata)

        # Calculate file changes
        changes = self.diff_files(before_state, env.path)
        run_metadata["files_changed_count"] = len(changes)

        # Write metadata
        metadata_path = archive_dir / "metadata.json"
        metadata_path.write_text(json.dumps(run_metadata, indent=2, default=str))

        # Create before snapshot tarball
        before_tar_path = archive_dir / "fixture_before.tar.gz"
        self._create_tarball_from_snapshot(before_state, before_tar_path)

        # Create after snapshot tarball
        after_tar_path = archive_dir / "fixture_after.tar.gz"
        self._create_tarball_from_dir(env.path, after_tar_path)

        # Write file changes diff
        if changes:
            diff_content = self._generate_combined_diff(before_state, changes)
            (archive_dir / "file_changes.diff").write_text(diff_content)

        # Write Claude output if provided
        if claude_output:
            claude_output_path = archive_dir / "claude_output.json"
            claude_output_path.write_text(
                json.dumps(claude_output, indent=2, default=str)
            )

        # Write test output if provided
        if test_output:
            (archive_dir / "test_output.log").write_text(test_output)

        return archive_dir

    def _create_tarball_from_snapshot(
        self,
        snapshot: dict[str, str],
        tar_path: Path,
    ) -> None:
        """Create a tarball from a file snapshot.

        Args:
            snapshot: Dict mapping relative paths to file contents
            tar_path: Path to create the tarball at
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Write all files from snapshot
            for rel_path, content in snapshot.items():
                file_path = temp_path / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)

            # Create tarball
            with tarfile.open(tar_path, "w:gz") as tar:
                for file_path in temp_path.rglob("*"):
                    if file_path.is_file():
                        arcname = str(file_path.relative_to(temp_path))
                        tar.add(file_path, arcname=arcname)

    def _create_tarball_from_dir(
        self,
        source_dir: Path,
        tar_path: Path,
        exclude_patterns: list[str] | None = None,
    ) -> None:
        """Create a tarball from a directory.

        Args:
            source_dir: Directory to archive
            tar_path: Path to create the tarball at
            exclude_patterns: Patterns to exclude (e.g., '__pycache__', '.git')
        """
        if exclude_patterns is None:
            exclude_patterns = [
                "__pycache__",
                ".git",
                ".venv",
                "node_modules",
                "*.pyc",
                "*.pyo",
            ]

        def filter_func(tarinfo):
            """Filter out excluded patterns."""
            for pattern in exclude_patterns:
                if pattern in tarinfo.name:
                    return None
            return tarinfo

        with tarfile.open(tar_path, "w:gz") as tar:
            for item in source_dir.iterdir():
                tar.add(item, arcname=item.name, filter=filter_func)

    def _generate_combined_diff(
        self,
        before_state: dict[str, str],
        changes: list[FileChange],
    ) -> str:
        """Generate a combined diff of all file changes.

        Args:
            before_state: Original file contents
            changes: List of file changes

        Returns:
            Combined unified diff string
        """
        diff_parts = []

        for change in changes:
            if change.action == "created":
                # Show as new file
                diff_parts.append(f"--- /dev/null")
                diff_parts.append(f"+++ b/{change.path}")
                if change.content_after:
                    for line in change.content_after.splitlines():
                        diff_parts.append(f"+{line}")
                diff_parts.append("")

            elif change.action == "deleted":
                # Show as deleted file
                diff_parts.append(f"--- a/{change.path}")
                diff_parts.append(f"+++ /dev/null")
                if change.path in before_state:
                    for line in before_state[change.path].splitlines():
                        diff_parts.append(f"-{line}")
                diff_parts.append("")

            elif change.action == "modified" and change.diff:
                diff_parts.append(change.diff)
                diff_parts.append("")

        return "\n".join(diff_parts)
