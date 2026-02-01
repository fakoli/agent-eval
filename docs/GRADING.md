# Grading Guide

This guide explains how the agent-eval harness grades evaluation results, including the scoring algorithm, pass/fail criteria, and best practices for writing effective assertions.

## Table of Contents

- [Overview](#overview)
- [Scoring Algorithm](#scoring-algorithm)
- [Pass/Fail Criteria](#passfail-criteria)
- [Code Graders](#code-graders)
- [LLM Grader](#llm-grader)
- [Writing Effective Assertions](#writing-effective-assertions)
- [Scoring Weights](#scoring-weights)

---

## Overview

The grading system uses a **composite grader** that combines two types of assertions:

1. **Code Assertions**: Objective, deterministic checks (tests pass, file contains pattern)
2. **LLM Assertions**: Subjective quality evaluation using Claude as a judge

Each assertion produces a score from 0.0 to 1.0. These scores are combined using configurable weights to produce an overall score.

```
┌─────────────────────────────────────────────────────────────┐
│                    CompositeGrader                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐     ┌─────────────┐     ┌──────────────┐  │
│  │ CodeGrader  │     │ LLMGrader   │     │ Weighted     │  │
│  │             │     │             │     │ Scoring      │  │
│  │ • tests_pass│     │ • rubric    │ ──► │              │  │
│  │ • file_*    │     │   evaluation│     │ overall_score│  │
│  │ • command_* │     │             │     │ passed       │  │
│  └─────────────┘     └─────────────┘     └──────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Scoring Algorithm

### Weighted Score Calculation

The overall score is calculated as a weighted average:

```
overall_score = Σ(assertion_score × weight) / Σ(weights)
```

**Algorithm:**

1. Each assertion is graded, producing a score (0.0-1.0)
2. Weights are looked up from the task's `scoring` dictionary
3. If an assertion ID contains a key from `scoring`, that weight is used
4. Assertions without matching weights default to weight 1.0
5. Weighted average is computed

**Example:**

```yaml
# Task with weights
scoring:
  tests_pass: 50      # Code assertion weight
  file_contains: 20   # Code assertion weight
  llm_quality: 30     # LLM assertion weight
```

If the grades are:
- `tests_pass`: 1.0 (passed)
- `file_contains`: 0.0 (failed)
- `llm_quality`: 0.8

Then:
```
overall_score = (1.0 × 50 + 0.0 × 20 + 0.8 × 30) / (50 + 20 + 30)
             = (50 + 0 + 24) / 100
             = 0.74
```

### Equal Weighting (Default)

If no weights are specified in the task, all assertions are weighted equally:

```
overall_score = Σ(assertion_scores) / num_assertions
```

---

## Pass/Fail Criteria

A task **passes** if **either** of these conditions is true:

1. `overall_score >= 0.7` (70% threshold)
2. **All code assertions pass** (regardless of LLM assertion scores)

This dual criteria ensures:
- Tasks with strong objective results pass even if LLM grading is harsh
- Tasks can still pass on overall quality even if minor code checks fail

**Implementation:**

```python
# From composite_grader.py
code_grades = [g for g in grades if g.assertion_id.startswith("code_")]
all_code_passed = all(g.passed for g in code_grades) if code_grades else True
passed = overall_score >= 0.7 or all_code_passed
```

---

## Code Graders

Code graders perform objective, deterministic checks.

### tests_pass

Runs a test command and checks the exit code.

| Property | Value |
|----------|-------|
| Score on pass | 1.0 |
| Score on fail | 0.0 |
| Default command | `pytest` |
| Timeout | 120 seconds |

**Task YAML:**
```yaml
assertions:
  - type: code
    check: tests_pass
    command: "pytest tests/test_auth.py -v"
```

**How it works:**
1. Runs the command in the isolated environment
2. Checks `returncode == 0`
3. Captures stdout/stderr for debugging

### file_contains

Checks if a file contains a regex pattern.

| Property | Value |
|----------|-------|
| Score on match | 1.0 |
| Score on no match | 0.0 |
| Pattern syntax | Python `re` regex |

**Task YAML:**
```yaml
assertions:
  - type: code
    check: file_contains
    file: "src/auth.py"
    pattern: "len\\(password\\)|password\\s*==\\s*['\"]"
```

**Notes:**
- File path is relative to the isolated environment root
- Pattern uses Python regex syntax (escape backslashes in YAML)
- File must exist for the check to pass

### file_not_contains

Checks that a file does NOT contain a pattern.

| Property | Value |
|----------|-------|
| Score on absent | 1.0 |
| Score on present | 0.0 |

**Task YAML:**
```yaml
assertions:
  - type: code
    check: file_not_contains
    file: "src/auth.py"
    pattern: "dangerous_function\\s*\\("  # Ensure dangerous calls are removed
```

### file_exists

Checks if a file exists.

| Property | Value |
|----------|-------|
| Score on exists | 1.0 |
| Score on missing | 0.0 |

**Task YAML:**
```yaml
assertions:
  - type: code
    check: file_exists
    file: "src/new_feature.py"
```

### command_succeeds

Runs an arbitrary command and checks success.

| Property | Value |
|----------|-------|
| Score on success | 1.0 |
| Score on failure | 0.0 |
| Timeout | 60 seconds |

**Task YAML:**
```yaml
assertions:
  - type: code
    check: command_succeeds
    command: "python -c 'import src.auth'"
```

**Use cases:**
- Syntax checking: `python -m py_compile src/file.py`
- Linting: `ruff check src/`
- Type checking: `mypy src/`
- Custom validation scripts

---

## LLM Grader

The LLM grader uses Claude as a judge to evaluate quality against a rubric.

### How It Works

1. Reads modified source files from the environment
2. Constructs a grading prompt with:
   - Task description and original prompt
   - Evaluation rubric
   - Assistant's output
   - Final code state
3. Asks Claude to evaluate and return structured JSON
4. Parses response into scores

### Grading Model

By default, uses `claude-3-5-haiku-20241022` for cost efficiency. This can be configured in `CompositeGrader.__init__()`.

### Rubric Format

Rubrics should be clear, specific evaluation criteria:

```yaml
assertions:
  - type: llm
    rubric: |
      The fix should:
      - Validate that password is not empty or whitespace-only
      - Return an appropriate error message for empty passwords
      - Not break the existing authentication logic for valid passwords
      - Handle edge cases like None password gracefully
```

### LLM Response Format

The grader expects JSON with this structure:

```json
{
  "criteria_scores": [
    {
      "criterion": "Password validation",
      "score": 0.9,
      "reasoning": "Correctly validates empty passwords..."
    }
  ],
  "overall_score": 0.85,
  "overall_reasoning": "Good implementation with minor issues...",
  "passed": true
}
```

### Fallback Behavior

If JSON parsing fails, the grader falls back to:
- Looking for "passed" or "success" keywords in text
- Assigning 0.7 if found, 0.3 if not
- Including parse error in details

---

## Writing Effective Assertions

### Code Assertion Best Practices

**1. Always have a `tests_pass` assertion**
```yaml
assertions:
  - type: code
    check: tests_pass
    command: "pytest tests/ -v"
```

**2. Use specific test commands**
```yaml
# Good: targeted test file
command: "pytest tests/test_auth.py -v"

# Less good: runs all tests (slower, more noise)
command: "pytest"
```

**3. Verify the fix, not just absence of bugs**
```yaml
assertions:
  # Check the vulnerability is fixed
  - type: code
    check: file_contains
    file: "src/auth.py"
    pattern: "if not password"

  # Check the old vulnerable pattern is gone
  - type: code
    check: file_not_contains
    file: "src/auth.py"
    pattern: "return True\\s*$"  # No early return without validation
```

**4. Use regex patterns wisely**
```yaml
# Allow multiple valid implementations
pattern: "len\\(password\\)|password\\s*==\\s*['\"]|not\\s+password"

# Be specific enough to avoid false positives
pattern: "if\\s+(?:not\\s+)?password(?:\\s*==|\\s+is)"
```

### LLM Assertion Best Practices

**1. Be specific and measurable**
```yaml
# Good: specific criteria
rubric: |
  The implementation should:
  1. Add input validation for email format using regex
  2. Return HTTP 400 for invalid emails
  3. Include a helpful error message

# Avoid: vague criteria
rubric: |
  The code should be good and well-written.
```

**2. Include edge cases**
```yaml
rubric: |
  The fix should handle:
  - Empty string input
  - None/null input
  - Whitespace-only input
  - Unicode characters
```

**3. Specify what NOT to do**
```yaml
rubric: |
  The implementation should:
  - NOT use deprecated APIs
  - NOT introduce new dependencies
  - NOT modify unrelated files
```

**4. Consider quality dimensions**
```yaml
rubric: |
  Evaluate the following:

  Correctness (most important):
  - Does it fix the bug described in the prompt?
  - Does it handle edge cases?

  Code Quality:
  - Is the code readable and well-structured?
  - Are variable names descriptive?

  Safety:
  - Does it avoid introducing new vulnerabilities?
  - Is error handling appropriate?
```

---

## Scoring Weights

### Choosing Weights

Weights should reflect the relative importance of each criterion:

```yaml
scoring:
  tests_pass: 50      # Critical: code must work
  file_contains: 20   # Important: verify implementation approach
  llm_quality: 30     # Valuable: overall quality assessment
```

**Guidelines:**
- Give highest weight to objective correctness (`tests_pass`)
- Use pattern matching for implementation verification
- LLM quality adds nuance but shouldn't dominate

### Weight Scenarios

**Bug Fix Task:**
```yaml
scoring:
  tests_pass: 60       # Tests verify the bug is fixed
  file_contains: 20    # Verify fix approach
  llm_quality: 20      # Code quality check
```

**New Feature Task:**
```yaml
scoring:
  tests_pass: 40       # Feature works
  file_exists: 10      # Required files created
  file_contains: 20    # Implementation includes required patterns
  llm_quality: 30      # Design and quality matter more
```

**Exploration Task:**
```yaml
scoring:
  llm_quality: 80      # Primarily evaluated on explanation quality
  file_exists: 20      # Optional output file
```

### No Weights (Equal)

If you omit `scoring`, all assertions are weighted equally:

```yaml
assertions:
  - type: code
    check: tests_pass
  - type: llm
    rubric: "..."

# Implicit: each gets weight 1.0, so 50/50 split
```
