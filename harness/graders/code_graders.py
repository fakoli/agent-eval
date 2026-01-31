"""Code-based graders for objective evaluation checks."""

import re
import subprocess
from pathlib import Path

from harness.models import CodeAssertion, CodeCheckType, GradeResult


class CodeGrader:
    """Grader for code-based objective checks."""

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
                    return GradeResult(
                        passed=False,
                        score=0.0,
                        details="file_contains requires file and pattern",
                    )
                return self.grade_file_contains(env_path, assertion.file, assertion.pattern)
            case CodeCheckType.FILE_EXISTS:
                if not assertion.file:
                    return GradeResult(
                        passed=False,
                        score=0.0,
                        details="file_exists requires file",
                    )
                return self.grade_file_exists(env_path, assertion.file)
            case CodeCheckType.FILE_NOT_CONTAINS:
                if not assertion.file or not assertion.pattern:
                    return GradeResult(
                        passed=False,
                        score=0.0,
                        details="file_not_contains requires file and pattern",
                    )
                return self.grade_file_not_contains(
                    env_path, assertion.file, assertion.pattern
                )
            case CodeCheckType.COMMAND_SUCCEEDS:
                if not assertion.command:
                    return GradeResult(
                        passed=False,
                        score=0.0,
                        details="command_succeeds requires command",
                    )
                return self.grade_command_succeeds(env_path, assertion.command)
            case _:
                return GradeResult(
                    passed=False,
                    score=0.0,
                    details=f"Unknown check type: {assertion.check}",
                )

    def grade_tests_pass(self, env_path: Path, command: str) -> GradeResult:
        """Check if tests pass.

        Args:
            env_path: Path to evaluation environment
            command: Test command to run

        Returns:
            GradeResult indicating if tests passed
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
            passed = result.returncode == 0
            full_output = f"{result.stdout}\n{result.stderr}".strip()
            details = result.stdout if passed else f"{result.stdout}\n{result.stderr}"
            return GradeResult(
                assertion_id="tests_pass",
                assertion_type="code",
                assertion_name="tests_pass",
                passed=passed,
                score=1.0 if passed else 0.0,
                details=details[:2000],  # Truncate for summary
                full_output=full_output,  # Keep full output
            )
        except subprocess.TimeoutExpired:
            return GradeResult(
                assertion_id="tests_pass",
                assertion_type="code",
                assertion_name="tests_pass",
                passed=False,
                score=0.0,
                details="Test command timed out",
                full_output="Test command timed out after 120 seconds",
            )
        except Exception as e:
            return GradeResult(
                assertion_id="tests_pass",
                assertion_type="code",
                assertion_name="tests_pass",
                passed=False,
                score=0.0,
                details=f"Error running tests: {e}",
                full_output=str(e),
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
            return GradeResult(
                assertion_id="file_contains",
                assertion_type="code",
                assertion_name="file_contains",
                passed=False,
                score=0.0,
                details=f"File not found: {file}",
                full_output=f"Expected file {file} does not exist",
            )

        try:
            content = file_path.read_text()
            match = re.search(pattern, content)
            passed = match is not None
            return GradeResult(
                assertion_id="file_contains",
                assertion_type="code",
                assertion_name="file_contains",
                passed=passed,
                score=1.0 if passed else 0.0,
                details=f"Pattern {'found' if passed else 'not found'}: {pattern}",
                full_output=content[:5000] if len(content) > 5000 else content,
            )
        except Exception as e:
            return GradeResult(
                assertion_id="file_contains",
                assertion_type="code",
                assertion_name="file_contains",
                passed=False,
                score=0.0,
                details=f"Error reading file: {e}",
                full_output=str(e),
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
            return GradeResult(
                assertion_id="file_not_contains",
                assertion_type="code",
                assertion_name="file_not_contains",
                passed=False,
                score=0.0,
                details=f"File not found: {file}",
                full_output=f"Expected file {file} does not exist",
            )

        try:
            content = file_path.read_text()
            match = re.search(pattern, content)
            passed = match is None
            return GradeResult(
                assertion_id="file_not_contains",
                assertion_type="code",
                assertion_name="file_not_contains",
                passed=passed,
                score=1.0 if passed else 0.0,
                details=f"Pattern {'absent' if passed else 'found'}: {pattern}",
                full_output=content[:5000] if len(content) > 5000 else content,
            )
        except Exception as e:
            return GradeResult(
                assertion_id="file_not_contains",
                assertion_type="code",
                assertion_name="file_not_contains",
                passed=False,
                score=0.0,
                details=f"Error reading file: {e}",
                full_output=str(e),
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
        return GradeResult(
            assertion_id="file_exists",
            assertion_type="code",
            assertion_name="file_exists",
            passed=passed,
            score=1.0 if passed else 0.0,
            details=f"File {'exists' if passed else 'not found'}: {file}",
            full_output=f"Checked path: {file_path}",
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
            return GradeResult(
                assertion_id="command_succeeds",
                assertion_type="code",
                assertion_name="command_succeeds",
                passed=passed,
                score=1.0 if passed else 0.0,
                details=result.stdout[:1000] if passed else result.stderr[:1000],
                full_output=full_output,
            )
        except subprocess.TimeoutExpired:
            return GradeResult(
                assertion_id="command_succeeds",
                assertion_type="code",
                assertion_name="command_succeeds",
                passed=False,
                score=0.0,
                details="Command timed out",
                full_output="Command timed out after 60 seconds",
            )
        except Exception as e:
            return GradeResult(
                assertion_id="command_succeeds",
                assertion_type="code",
                assertion_name="command_succeeds",
                passed=False,
                score=0.0,
                details=f"Error running command: {e}",
                full_output=str(e),
            )
