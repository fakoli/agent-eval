"""Composite grader combining code and LLM graders."""

from pathlib import Path

from harness.graders.code_graders import CodeGrader
from harness.graders.llm_graders import LLMGrader
from harness.models import (
    CodeAssertion,
    ExecutionTrace,
    GradeResult,
    LLMAssertion,
    Task,
)


class CompositeGrader:
    """Combines code and LLM graders with weighted scoring."""

    def __init__(
        self,
        llm_model: str = "claude-haiku-4-5-20250514",
        api_key: str | None = None,
    ):
        """Initialize composite grader.

        Args:
            llm_model: Model to use for LLM grading
            api_key: Anthropic API key for LLM grading
        """
        self.code_grader = CodeGrader()
        self.llm_grader = LLMGrader(model=llm_model, api_key=api_key)

    def grade(
        self,
        task: Task,
        trace: ExecutionTrace,
        env_path: Path,
    ) -> tuple[list[GradeResult], float, bool]:
        """Grade a task execution against all assertions.

        Args:
            task: The task with assertions
            trace: Execution trace from the run
            env_path: Path to evaluation environment

        Returns:
            Tuple of (list of grades, overall score, passed)
        """
        grades = []

        # Grade code assertions
        for i, assertion in enumerate(task.code_assertions):
            grade = self.code_grader.grade(assertion, env_path)
            grade.assertion_id = f"code_{i}_{assertion.check.value}"
            grades.append(grade)

        # Grade LLM assertions
        for i, assertion in enumerate(task.llm_assertions):
            grade = self.llm_grader.grade(assertion, task, trace, env_path)
            grade.assertion_id = f"llm_{i}"
            grades.append(grade)

        # Calculate overall score using task's scoring weights
        overall_score = self._calculate_weighted_score(grades, task.scoring)

        # Determine pass/fail
        # Pass if overall score >= 0.7 OR all code assertions pass
        code_grades = [g for g in grades if g.assertion_id.startswith("code_")]
        all_code_passed = all(g.passed for g in code_grades) if code_grades else True
        passed = overall_score >= 0.7 or all_code_passed

        return grades, overall_score, passed

    def _calculate_weighted_score(
        self,
        grades: list[GradeResult],
        weights: dict[str, float],
    ) -> float:
        """Calculate weighted average score.

        Args:
            grades: List of grade results
            weights: Mapping of assertion types to weights

        Returns:
            Weighted average score
        """
        if not grades:
            return 0.0

        # If no weights specified, use equal weighting
        if not weights:
            return sum(g.score for g in grades) / len(grades)

        # Map grades to their weight categories
        total_weight = 0.0
        weighted_sum = 0.0

        for grade in grades:
            # Try to find matching weight
            weight = 0.0
            for key, w in weights.items():
                if key in grade.assertion_id:
                    weight = w
                    break

            if weight == 0:
                # Default weight if not specified
                weight = 1.0

            total_weight += weight
            weighted_sum += grade.score * weight

        return weighted_sum / total_weight if total_weight > 0 else 0.0

    def grade_single_assertion(
        self,
        assertion: CodeAssertion | LLMAssertion,
        task: Task,
        trace: ExecutionTrace,
        env_path: Path,
    ) -> GradeResult:
        """Grade a single assertion.

        Args:
            assertion: The assertion to grade
            task: The task being evaluated
            trace: Execution trace
            env_path: Environment path

        Returns:
            Grade result for the assertion
        """
        if isinstance(assertion, CodeAssertion):
            return self.code_grader.grade(assertion, env_path)
        else:
            return self.llm_grader.grade(assertion, task, trace, env_path)
