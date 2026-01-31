"""Export Claude Code configuration for CI environments."""

import json
import subprocess
from pathlib import Path

from harness.models import ClaudeConfigSnapshot


class ConfigExporter:
    """Exports Claude Code configuration for CI reproducibility."""

    def __init__(self, claude_home: Path | None = None):
        """Initialize exporter.

        Args:
            claude_home: Path to Claude home directory (default: ~/.claude)
        """
        self.claude_home = claude_home or Path.home() / ".claude"

    def export_snapshot(self) -> ClaudeConfigSnapshot:
        """Export current config as portable snapshot.

        Returns:
            ClaudeConfigSnapshot with all configuration data
        """
        return ClaudeConfigSnapshot(
            claude_version=self._get_claude_version(),
            global_claude_md=self._read_global_claude_md(),
            settings=self._read_settings(),
            mcp_servers=self._extract_mcp_servers(),
            skills=self._export_skills(),
        )

    def _get_claude_version(self) -> str:
        """Get the installed Claude Code version."""
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.stdout.strip().split("\n")[0] if result.stdout else "unknown"
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return "unknown"

    def _read_global_claude_md(self) -> str | None:
        """Read the global CLAUDE.md file."""
        claude_md_path = self.claude_home / "CLAUDE.md"
        if claude_md_path.exists():
            try:
                return claude_md_path.read_text()
            except OSError:
                return None
        return None

    def _read_settings(self) -> dict:
        """Read settings.json."""
        settings_path = self.claude_home / "settings.json"
        if settings_path.exists():
            try:
                return json.loads(settings_path.read_text())
            except (OSError, json.JSONDecodeError):
                return {}
        return {}

    def _extract_mcp_servers(self) -> dict:
        """Extract MCP server configurations.

        Note: MCP servers are typically disabled in CI for isolation,
        but we capture them for reference.
        """
        # Check for mcp_servers.json or similar
        mcp_config_path = self.claude_home / "mcp_servers.json"
        if mcp_config_path.exists():
            try:
                return json.loads(mcp_config_path.read_text())
            except (OSError, json.JSONDecodeError):
                return {}

        # Also check settings for MCP config
        settings = self._read_settings()
        return settings.get("mcp_servers", {})

    def _export_skills(self) -> dict[str, str]:
        """Export skills as name -> content mapping.

        Returns:
            Dictionary mapping skill file paths to their content
        """
        skills = {}
        skills_dir = self.claude_home / "skills"

        if not skills_dir.exists():
            return skills

        # Export all .md files from skills directory
        for skill_file in skills_dir.rglob("*.md"):
            try:
                rel_path = skill_file.relative_to(skills_dir)
                skills[str(rel_path)] = skill_file.read_text()
            except (OSError, ValueError):
                continue

        return skills

    def save_snapshot(self, output_path: Path) -> None:
        """Export and save snapshot to file.

        Args:
            output_path: Path to save the snapshot JSON
        """
        snapshot = self.export_snapshot()
        output_path.write_text(snapshot.model_dump_json(indent=2))
