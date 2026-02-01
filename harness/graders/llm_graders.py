"""LLM-based graders for quality evaluation.

Enhanced with research-based techniques for improved reliability:
- Structured Chain-of-Thought prompting
- Bias mitigation (position and verbosity)
- Calibration examples for anchored scoring
- Criterion-by-criterion evaluation

Research sources:
- LLMs-as-Judges Survey (arxiv.org/html/2412.05579v2)
- Agent-as-a-Judge (arxiv.org/abs/2410.10934)
- LLM-as-a-Judge Survey (arxiv.org/html/2411.15594v6)
"""

import json
import os
from pathlib import Path

from anthropic import Anthropic

from harness.constants import DEFAULT_GRADING_MODEL
from harness.models import CriterionScore, ExecutionTrace, GradeResult, LLMAssertion, Task


# Bias mitigation header - research shows this improves LLM judge accuracy
BIAS_MITIGATION_HEADER = """
IMPORTANT EVALUATION RULES:
- Judge code quality, NOT output length or verbosity
- A short, correct fix is better than a verbose, over-engineered one
- Ignore formatting differences that don't affect functionality
- Focus on whether requirements are MET, not on code style preferences
- Do NOT favor the first solution you see (position bias)
- Evaluate based on correctness and completeness, not impressiveness
"""


class LLMGrader:
    """Grader that uses an LLM to evaluate against a rubric."""

    def __init__(
        self,
        model: str = DEFAULT_GRADING_MODEL,
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

        # Build grading prompt with calibration examples
        prompt = self._build_grading_prompt(
            task=task,
            rubric=assertion.rubric,
            trace=trace,
            final_code=final_code,
            assertion=assertion,
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
        assertion: LLMAssertion | None = None,
    ) -> str:
        """Build the grading prompt for the LLM.

        Uses structured Chain-of-Thought prompting with bias mitigation
        and optional calibration examples for anchored scoring.
        """
        # Build calibration section if examples are provided
        calibration_section = ""
        if assertion and (
            assertion.passing_example
            or assertion.failing_example
            or assertion.borderline_example
        ):
            calibration_section = """
## Calibration Examples (use these to anchor your scoring)
"""
            if assertion.passing_example:
                calibration_section += f"""
### PASSING Example (Score: 0.9-1.0)
{assertion.passing_example}
"""
            if assertion.failing_example:
                calibration_section += f"""
### FAILING Example (Score: 0.0-0.3)
{assertion.failing_example}
"""
            if assertion.borderline_example:
                calibration_section += f"""
### BORDERLINE Example (Score: 0.5-0.6)
{assertion.borderline_example}
"""

        return f"""You are evaluating an AI coding assistant's work on a task.

{BIAS_MITIGATION_HEADER}

## Task Description
{task.description}

## Task Prompt Given to the Assistant
{task.prompt}

## Evaluation Rubric
{rubric}
{calibration_section}
## Assistant's Output
{trace.result}

## Final Code State
{final_code}

## Step-by-Step Evaluation Process

Follow this structured evaluation process:

### Step 1: Identify Changes
List the specific code changes made by the assistant. Quote the relevant code.

### Step 2: Criterion-by-Criterion Evaluation
For each criterion in the rubric:
- Quote the relevant code that addresses this criterion
- Explain whether and how it meets the criterion
- Assign a score from 0.0 to 1.0 with clear justification

### Step 3: Check for Regressions
Verify no existing functionality was broken by the changes.
- Did the assistant modify anything that could break existing behavior?
- Are there any unintended side effects?

### Step 4: Calculate Overall Score
Weight criterion scores according to importance in the rubric.

## Output Format
Return your complete evaluation as JSON in this exact format:
{{
    "step1_changes": ["change1: description", "change2: description"],
    "criteria_scores": [
        {{
            "criterion": "criterion description",
            "evidence": "quoted code or observation",
            "score": 0.0-1.0,
            "reasoning": "explanation of score"
        }}
    ],
    "regression_check": {{
        "passed": true/false,
        "notes": "any concerns about regressions"
    }},
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

        Handles both the new structured CoT format and legacy format.

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

            # Handle new format with evidence field
            for c in criteria:
                criterion = c.get("criterion", "unknown")
                score = float(c.get("score", 0.0))
                reason = c.get("reasoning", "")
                evidence = c.get("evidence", "")

                # Include evidence in details if present
                if evidence:
                    details_parts.append(
                        f"- {criterion}: {score:.2f}\n  Evidence: {evidence}\n  Reasoning: {reason}"
                    )
                else:
                    details_parts.append(f"- {criterion}: {score:.2f} - {reason}")

                criteria_scores.append(
                    CriterionScore(
                        criterion=criterion,
                        score=score,
                        reasoning=f"{evidence}\n{reason}" if evidence else reason,
                    )
                )

            # Extract step 1 changes if present (new format)
            changes = data.get("step1_changes", [])
            if changes:
                changes_summary = "Changes identified: " + "; ".join(changes[:3])
                if len(changes) > 3:
                    changes_summary += f" (+{len(changes) - 3} more)"
                details_parts.insert(0, changes_summary)

            # Extract regression check if present (new format)
            regression = data.get("regression_check", {})
            if regression:
                reg_passed = regression.get("passed", True)
                reg_notes = regression.get("notes", "")
                if not reg_passed:
                    details_parts.append(f"REGRESSION WARNING: {reg_notes}")
                    # Penalize score for regressions
                    overall_score = min(overall_score, 0.5)
                    passed = False

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
