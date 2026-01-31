"""LLM-based graders for quality evaluation."""

import json
import os
from pathlib import Path

from anthropic import Anthropic

from harness.models import CriterionScore, ExecutionTrace, GradeResult, LLMAssertion, Task


class LLMGrader:
    """Grader that uses an LLM to evaluate against a rubric."""

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20250514",
        api_key: str | None = None,
    ):
        """Initialize LLM grader.

        Args:
            model: Model to use for grading (default: Haiku for cost efficiency)
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
        """
        self.model = model
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))

    def grade(
        self,
        assertion: LLMAssertion,
        task: Task,
        trace: ExecutionTrace,
        env_path: Path,
    ) -> GradeResult:
        """Grade using LLM against the rubric.

        Args:
            assertion: The LLM assertion with rubric
            task: The task being evaluated
            trace: Execution trace from the run
            env_path: Path to evaluation environment

        Returns:
            GradeResult with LLM-based evaluation
        """
        # Read modified files for context
        final_code = self._read_modified_files(env_path)

        # Build grading prompt
        prompt = self._build_grading_prompt(
            task=task,
            rubric=assertion.rubric,
            trace=trace,
            final_code=final_code,
        )

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            response_text = response.content[0].text
            result = self._parse_response(response_text)
            # Attach the grading prompt and full response
            result.grading_prompt = prompt
            result.full_output = response_text
            return result
        except Exception as e:
            return GradeResult(
                assertion_id="llm_quality",
                assertion_type="llm",
                assertion_name="llm_quality",
                passed=False,
                score=0.0,
                details=f"LLM grading failed: {e}",
                full_output=str(e),
                grading_prompt=prompt if "prompt" in locals() else "",
            )

    def _build_grading_prompt(
        self,
        task: Task,
        rubric: str,
        trace: ExecutionTrace,
        final_code: str,
    ) -> str:
        """Build the grading prompt for the LLM."""
        return f"""You are evaluating an AI coding assistant's work on a task.

## Task Description
{task.description}

## Task Prompt Given to the Assistant
{task.prompt}

## Evaluation Rubric
{rubric}

## Assistant's Output
{trace.result}

## Final Code State
{final_code}

## Instructions
Evaluate the assistant's work against the rubric. For each criterion in the rubric:
1. Assess whether it was met
2. Provide a score from 0.0 to 1.0
3. Explain your reasoning

Return your evaluation as JSON in this exact format:
{{
    "criteria_scores": [
        {{"criterion": "description", "score": 0.0-1.0, "reasoning": "explanation"}}
    ],
    "overall_score": 0.0-1.0,
    "overall_reasoning": "summary of evaluation",
    "passed": true/false
}}

Only return valid JSON, no other text."""

    def _read_modified_files(self, env_path: Path, max_files: int = 10) -> str:
        """Read recently modified files from the environment.

        Args:
            env_path: Path to evaluation environment
            max_files: Maximum number of files to include

        Returns:
            Concatenated file contents with headers
        """
        # Find relevant source files
        patterns = ["**/*.py", "**/*.js", "**/*.ts", "**/*.java", "**/*.go"]
        files = []
        for pattern in patterns:
            files.extend(env_path.glob(pattern))

        # Sort by modification time, most recent first
        files = sorted(files, key=lambda f: f.stat().st_mtime, reverse=True)
        files = files[:max_files]

        # Build content string
        parts = []
        for file in files:
            try:
                content = file.read_text()
                rel_path = file.relative_to(env_path)
                parts.append(f"### {rel_path}\n```\n{content}\n```")
            except Exception:
                continue

        return "\n\n".join(parts) if parts else "(No source files found)"

    def _parse_response(self, response_text: str) -> GradeResult:
        """Parse LLM response into GradeResult.

        Args:
            response_text: Raw response from LLM

        Returns:
            Parsed GradeResult
        """
        try:
            # Try to extract JSON from response
            # Handle cases where LLM might include markdown code blocks
            text = response_text.strip()
            if text.startswith("```"):
                # Extract content between code blocks
                lines = text.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```") and not in_json:
                        in_json = True
                        continue
                    elif line.startswith("```") and in_json:
                        break
                    elif in_json:
                        json_lines.append(line)
                text = "\n".join(json_lines)

            data = json.loads(text)

            overall_score = float(data.get("overall_score", 0.0))
            passed = data.get("passed", overall_score >= 0.7)
            reasoning = data.get("overall_reasoning", "")

            # Build detailed breakdown
            criteria = data.get("criteria_scores", [])
            criteria_scores = []
            details_parts = []
            for c in criteria:
                criterion = c.get("criterion", "unknown")
                score = c.get("score", 0.0)
                reason = c.get("reasoning", "")
                details_parts.append(f"- {criterion}: {score:.2f} - {reason}")
                criteria_scores.append(
                    CriterionScore(
                        criterion=criterion,
                        score=score,
                        reasoning=reason,
                    )
                )

            details = "\n".join(details_parts) if details_parts else reasoning

            return GradeResult(
                assertion_id="llm_quality",
                assertion_type="llm",
                assertion_name="llm_quality",
                passed=passed,
                score=overall_score,
                details=details,
                reasoning=reasoning,
                criteria_scores=criteria_scores,
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            # Fallback: try to extract a simple pass/fail
            lower_text = response_text.lower()
            passed = "passed" in lower_text or "success" in lower_text
            return GradeResult(
                assertion_id="llm_quality",
                assertion_type="llm",
                assertion_name="llm_quality",
                passed=passed,
                score=0.7 if passed else 0.3,
                details=f"Could not parse structured response: {e}",
                reasoning=response_text[:500],
            )
