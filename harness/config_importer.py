"""Import Claude Code configuration for CI environments."""

import json
from pathlib import Path
from typing import Any

from harness.models import ClaudeConfigSnapshot


class ConfigImporter:
    """Sets up Claude Code environment in CI from snapshot."""

    def setup_ci_environment(
        self,
        snapshot: ClaudeConfigSnapshot,
        temp_dir: Path,
        disable_mcp: bool = True,
    ) -> dict[str, str]:
        """Create isolated Claude home from snapshot.

        Args:
            snapshot: The configuration snapshot to import
            temp_dir: Temporary directory to create environment in
            disable_mcp: Whether to disable MCP servers in CI (recommended)

        Returns:
            Dictionary of environment variables to set
        """
        claude_home = temp_dir / ".claude"
        claude_home.mkdir(parents=True, exist_ok=True)

        # Write global CLAUDE.md
        if snapshot.global_claude_md:
            (claude_home / "CLAUDE.md").write_text(snapshot.global_claude_md)

        # Write sanitized settings
        settings = self._sanitize_for_ci(snapshot.settings, disable_mcp)
        (claude_home / "settings.json").write_text(json.dumps(settings, indent=2))

        # Write MCP config (empty if disabled)
        mcp_config = {} if disable_mcp else snapshot.mcp_servers
        (claude_home / "mcp_servers.json").write_text(json.dumps(mcp_config, indent=2))

        # Restore skills
        self._restore_skills(claude_home / "skills", snapshot.skills)

        return {
            "HOME": str(temp_dir),
            "CLAUDE_HOME": str(claude_home),
        }

    def _sanitize_for_ci(
        self,
        settings: dict[str, Any],
        disable_mcp: bool,
    ) -> dict[str, Any]:
        """Sanitize settings for CI environment.

        Args:
            settings: Original settings dictionary
            disable_mcp: Whether to disable MCP servers

        Returns:
            Sanitized settings safe for CI
        """
        # Create a copy to avoid modifying original
        sanitized = dict(settings)

        # CI-specific overrides
        sanitized["analytics"] = False
        sanitized["telemetry"] = False

        # Disable MCP servers if requested
        if disable_mcp:
            sanitized["mcp_servers"] = {}
            sanitized["mcpServers"] = {}  # Handle both naming conventions

        # Remove any local paths that won't exist in CI
        keys_to_remove = [
            "workspace",
            "recent_projects",
            "last_opened",
        ]
        for key in keys_to_remove:
            sanitized.pop(key, None)

        return sanitized

    def _restore_skills(self, skills_dir: Path, skills: dict[str, str]) -> None:
        """Restore skills from snapshot.

        Args:
            skills_dir: Directory to write skills to
            skills: Mapping of relative paths to skill content
        """
        if not skills:
            return

        skills_dir.mkdir(parents=True, exist_ok=True)

        for rel_path, content in skills.items():
            skill_path = skills_dir / rel_path

            # Create parent directories if needed
            skill_path.parent.mkdir(parents=True, exist_ok=True)

            skill_path.write_text(content)

    def load_snapshot(self, snapshot_path: Path) -> ClaudeConfigSnapshot:
        """Load a snapshot from file.

        Args:
            snapshot_path: Path to snapshot JSON file

        Returns:
            Parsed ClaudeConfigSnapshot
        """
        return ClaudeConfigSnapshot.model_validate_json(snapshot_path.read_text())
