"""Code-based graders for objective evaluation checks.

Supports partial credit grading and static analysis checks:
- tests_pass: Partial credit based on passed/failed test ratio
- ruff_clean: Linting check with partial credit per violation
- mypy_clean: Type checking with partial credit per error
"""

import json
import re
import subprocess
from pathlib import Path

from harness.models import CodeAssertion, CodeCheckType, GradeResult


class CodeGrader:
    """Grader for code-based objective checks."""

    def _create_grade_result(
        self,
        assertion_name: str,
        passed: bool,
        score: float,
        details: str,
        full_output: str = "",
    ) -> GradeResult:
        """Create a GradeResult with common fields populated.

        Args:
            assertion_name: Name/ID of the assertion (e.g., 'tests_pass')
            passed: Whether the assertion passed
            score: Score from 0.0 to 1.0
            details: Human-readable details
            full_output: Full output from the check (optional)

        Returns:
            GradeResult with fields populated
        """
        return GradeResult(
            assertion_id=assertion_name,
            assertion_type="code",
            assertion_name=assertion_name,
            passed=passed,
            score=score,
            details=details,
            full_output=full_output,
        )

    def grade(self, assertion: CodeAssertion, env_path: Path) -> GradeResult:
        """Grade a code assertion.

        Args:
            assertion: The assertion to check
            env_path: Path to the evaluation environment

        Returns:
            GradeResult with pass/fail and score
        """
        match assertion.check:
            case CodeCheckType.TESTS_PASS:
                return self.grade_tests_pass(env_path, assertion.command or "pytest")
            case CodeCheckType.FILE_CONTAINS:
                if not assertion.file or not assertion.pattern:
                    return self._create_grade_result(
                        "file_contains", False, 0.0,
                        "file_contains requires file and pattern",
                    )
                return self.grade_file_contains(env_path, assertion.file, assertion.pattern)
            case CodeCheckType.FILE_EXISTS:
                if not assertion.file:
                    return self._create_grade_result(
                        "file_exists", False, 0.0,
                        "file_exists requires file",
                    )
                return self.grade_file_exists(env_path, assertion.file)
            case CodeCheckType.FILE_NOT_CONTAINS:
                if not assertion.file or not assertion.pattern:
                    return self._create_grade_result(
                        "file_not_contains", False, 0.0,
                        "file_not_contains requires file and pattern",
                    )
                return self.grade_file_not_contains(
                    env_path, assertion.file, assertion.pattern
                )
            case CodeCheckType.COMMAND_SUCCEEDS:
                if not assertion.command:
                    return self._create_grade_result(
                        "command_succeeds", False, 0.0,
                        "command_succeeds requires command",
                    )
                return self.grade_command_succeeds(env_path, assertion.command)
            case CodeCheckType.RUFF_CLEAN:
                return self.grade_ruff_clean(env_path, assertion.pattern)
            case CodeCheckType.MYPY_CLEAN:
                return self.grade_mypy_clean(env_path, assertion.pattern)
            case _:
                return self._create_grade_result(
                    "unknown", False, 0.0,
                    f"Unknown check type: {assertion.check}",
                )

    def grade_tests_pass(
        self,
        env_path: Path,
        command: str,
        pass_threshold: float = 0.8,
    ) -> GradeResult:
        """Check if tests pass with partial credit.

        Parses pytest output to calculate score based on passed/failed ratio.
        Agent fixing 9/10 tests gets 0.9 score instead of 0.0.

        Args:
            env_path: Path to evaluation environment
            command: Test command to run
            pass_threshold: Minimum pass ratio required (default 80%)

        Returns:
            GradeResult with partial credit score
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=env_path,
                capture_output=True,
                text=True,
                timeout=120,
            )
            full_output = f"{result.stdout}\n{result.stderr}".strip()

            # Try to extract test counts from pytest output
            # Pattern: "5 passed, 2 failed" or "5 passed" or "2 failed"
            passed_match = re.search(r"(\d+)\s+passed", full_output)
            failed_match = re.search(r"(\d+)\s+failed", full_output)
            error_match = re.search(r"(\d+)\s+error", full_output)

            passed_count = int(passed_match.group(1)) if passed_match else 0
            failed_count = int(failed_match.group(1)) if failed_match else 0
            error_count = int(error_match.group(1)) if error_match else 0

            total_tests = passed_count + failed_count + error_count

            if total_tests > 0:
                # Partial credit based on pass ratio
                score = passed_count / total_tests
                all_passed = result.returncode == 0
                meets_threshold = score >= pass_threshold

                details = f"{passed_count}/{total_tests} tests passed ({score:.0%})"
                if error_count > 0:
                    details += f", {error_count} errors"

                return self._create_grade_result(
                    "tests_pass",
                    all_passed or meets_threshold,
                    score,
                    details,
                    full_output,
                )
            else:
                # Couldn't parse test output, fall back to binary
                passed = result.returncode == 0
                details = result.stdout if passed else f"{result.stdout}\n{result.stderr}"
                return self._create_grade_result(
                    "tests_pass",
                    passed,
                    1.0 if passed else 0.0,
                    details[:2000],
                    full_output,
                )
        except subprocess.TimeoutExpired:
            return self._create_grade_result(
                "tests_pass", False, 0.0,
                "Test command timed out",
                "Test command timed out after 120 seconds",
            )
        except subprocess.SubprocessError as e:
            return self._create_grade_result(
                "tests_pass", False, 0.0,
                f"Subprocess error running tests: {e}",
                str(e),
            )
        except OSError as e:
            return self._create_grade_result(
                "tests_pass", False, 0.0,
                f"OS error running tests: {e}",
                str(e),
            )

    def grade_ruff_clean(
        self,
        env_path: Path,
        config_path: str | None = None,
    ) -> GradeResult:
        """Check if code passes ruff linting with partial credit.

        Score is reduced by 0.1 for each violation (minimum 0.0).

        Args:
            env_path: Path to evaluation environment
            config_path: Optional path to ruff config file

        Returns:
            GradeResult with linting status
        """
        try:
            # Build command
            cmd = ["ruff", "check", "--output-format", "json"]
            if config_path:
                cmd.extend(["--config", config_path])
            cmd.append(".")

            result = subprocess.run(
                cmd,
                cwd=env_path,
                capture_output=True,
                text=True,
                timeout=60,
            )

            full_output = result.stdout or result.stderr

            # Parse JSON output
            try:
                violations = json.loads(result.stdout) if result.stdout else []
            except json.JSONDecodeError:
                violations = []

            violation_count = len(violations)

            if violation_count == 0:
                return self._create_grade_result(
                    "ruff_clean", True, 1.0,
                    "No linting violations",
                    full_output,
                )

            # Partial credit: -0.1 per violation, minimum 0.0
            score = max(0.0, 1.0 - violation_count * 0.1)

            # Summarize violations by rule
            rule_counts: dict[str, int] = {}
            for v in violations[:20]:  # Limit to first 20 for summary
                rule = v.get("code", "unknown")
                rule_counts[rule] = rule_counts.get(rule, 0) + 1

            summary_parts = [f"{rule}: {count}" for rule, count in sorted(rule_counts.items())]
            details = f"{violation_count} violations: {', '.join(summary_parts[:5])}"
            if len(summary_parts) > 5:
                details += f" (+{len(summary_parts) - 5} more rules)"

            return self._create_grade_result(
                "ruff_clean",
                score >= 0.7,
                score,
                details,
                full_output,
            )

        except FileNotFoundError:
            return self._create_grade_result(
                "ruff_clean", False, 0.0,
                "ruff not found - install with: pip install ruff",
                "ruff command not found",
            )
        except subprocess.TimeoutExpired:
            return self._create_grade_result(
                "ruff_clean", False, 0.0,
                "ruff command timed out",
                "ruff command timed out after 60 seconds",
            )
        except subprocess.SubprocessError as e:
            return self._create_grade_result(
                "ruff_clean", False, 0.0,
                f"Subprocess error running ruff: {e}",
                str(e),
            )
        except json.JSONDecodeError as e:
            return self._create_grade_result(
                "ruff_clean", False, 0.0,
                f"Error parsing ruff output: {e}",
                str(e),
            )

    def grade_mypy_clean(
        self,
        env_path: Path,
        config_path: str | None = None,
    ) -> GradeResult:
        """Check if code passes mypy type checking with partial credit.

        Score is reduced by 0.05 for each error (minimum 0.0).

        Args:
            env_path: Path to evaluation environment
            config_path: Optional path to mypy config file

        Returns:
            GradeResult with type checking status
        """
        try:
            # Build command
            cmd = ["mypy", "--no-error-summary"]
            if config_path:
                cmd.extend(["--config-file", config_path])
            cmd.append(".")

            result = subprocess.run(
                cmd,
                cwd=env_path,
                capture_output=True,
                text=True,
                timeout=120,
            )

            full_output = f"{result.stdout}\n{result.stderr}".strip()

            # Count errors from output
            # mypy format: "file.py:line: error: message"
            error_lines = [
                line for line in result.stdout.split("\n")
                if ": error:" in line
            ]
            error_count = len(error_lines)

            if result.returncode == 0 or error_count == 0:
                return self._create_grade_result(
                    "mypy_clean", True, 1.0,
                    "No type errors",
                    full_output,
                )

            # Partial credit: -0.05 per error, minimum 0.0
            score = max(0.0, 1.0 - error_count * 0.05)

            # Summarize first few errors
            summary = error_lines[:3]
            details = f"{error_count} type errors. First few: {'; '.join(summary)}"
            if error_count > 3:
                details = f"{error_count} type errors"

            return self._create_grade_result(
                "mypy_clean",
                score >= 0.7,
                score,
                details,
                full_output,
            )

        except FileNotFoundError:
            return self._create_grade_result(
                "mypy_clean", False, 0.0,
                "mypy not found - install with: pip install mypy",
                "mypy command not found",
            )
        except subprocess.TimeoutExpired:
            return self._create_grade_result(
                "mypy_clean", False, 0.0,
                "mypy command timed out",
                "mypy command timed out after 120 seconds",
            )
        except subprocess.SubprocessError as e:
            return self._create_grade_result(
                "mypy_clean", False, 0.0,
                f"Subprocess error running mypy: {e}",
                str(e),
            )
        except OSError as e:
            return self._create_grade_result(
                "mypy_clean", False, 0.0,
                f"OS error running mypy: {e}",
                str(e),
            )

    def grade_file_contains(
        self, env_path: Path, file: str, pattern: str
    ) -> GradeResult:
        """Check if file contains pattern.

        Args:
            env_path: Path to evaluation environment
            file: Relative path to file
            pattern: Regex pattern to search for

        Returns:
            GradeResult indicating if pattern was found
        """
        file_path = env_path / file
        if not file_path.exists():
            return self._create_grade_result(
                "file_contains", False, 0.0,
                f"File not found: {file}",
                f"Expected file {file} does not exist",
            )

        try:
            content = file_path.read_text()
            match = re.search(pattern, content)
            passed = match is not None
            return self._create_grade_result(
                "file_contains",
                passed,
                1.0 if passed else 0.0,
                f"Pattern {'found' if passed else 'not found'}: {pattern}",
                content[:5000] if len(content) > 5000 else content,
            )
        except OSError as e:
            return self._create_grade_result(
                "file_contains", False, 0.0,
                f"Error reading file: {e}",
                str(e),
            )
        except re.error as e:
            return self._create_grade_result(
                "file_contains", False, 0.0,
                f"Invalid regex pattern: {e}",
                str(e),
            )

    def grade_file_not_contains(
        self, env_path: Path, file: str, pattern: str
    ) -> GradeResult:
        """Check if file does not contain pattern.

        Args:
            env_path: Path to evaluation environment
            file: Relative path to file
            pattern: Regex pattern that should not be present

        Returns:
            GradeResult indicating if pattern was absent
        """
        file_path = env_path / file
        if not file_path.exists():
            return self._create_grade_result(
                "file_not_contains", False, 0.0,
                f"File not found: {file}",
                f"Expected file {file} does not exist",
            )

        try:
            content = file_path.read_text()
            match = re.search(pattern, content)
            passed = match is None
            return self._create_grade_result(
                "file_not_contains",
                passed,
                1.0 if passed else 0.0,
                f"Pattern {'absent' if passed else 'found'}: {pattern}",
                content[:5000] if len(content) > 5000 else content,
            )
        except OSError as e:
            return self._create_grade_result(
                "file_not_contains", False, 0.0,
                f"Error reading file: {e}",
                str(e),
            )
        except re.error as e:
            return self._create_grade_result(
                "file_not_contains", False, 0.0,
                f"Invalid regex pattern: {e}",
                str(e),
            )

    def grade_file_exists(self, env_path: Path, file: str) -> GradeResult:
        """Check if file exists.

        Args:
            env_path: Path to evaluation environment
            file: Relative path to file

        Returns:
            GradeResult indicating if file exists
        """
        file_path = env_path / file
        passed = file_path.exists()
        return self._create_grade_result(
            "file_exists",
            passed,
            1.0 if passed else 0.0,
            f"File {'exists' if passed else 'not found'}: {file}",
            f"Checked path: {file_path}",
        )

    def grade_command_succeeds(self, env_path: Path, command: str) -> GradeResult:
        """Check if a command succeeds.

        Args:
            env_path: Path to evaluation environment
            command: Command to run

        Returns:
            GradeResult indicating if command succeeded
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=env_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            passed = result.returncode == 0
            full_output = f"{result.stdout}\n{result.stderr}".strip()
            return self._create_grade_result(
                "command_succeeds",
                passed,
                1.0 if passed else 0.0,
                result.stdout[:1000] if passed else result.stderr[:1000],
                full_output,
            )
        except subprocess.TimeoutExpired:
            return self._create_grade_result(
                "command_succeeds", False, 0.0,
                "Command timed out",
                "Command timed out after 60 seconds",
            )
        except subprocess.SubprocessError as e:
            return self._create_grade_result(
                "command_succeeds", False, 0.0,
                f"Subprocess error running command: {e}",
                str(e),
            )
        except OSError as e:
            return self._create_grade_result(
                "command_succeeds", False, 0.0,
                f"OS error running command: {e}",
                str(e),
            )
