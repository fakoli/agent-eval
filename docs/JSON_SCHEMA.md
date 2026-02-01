# JSON Schema Documentation

This document describes the data formats used by agent-eval for tasks, configs, and results.

## Table of Contents

- [Task YAML Schema](#task-yaml-schema)
- [Config YAML Schema](#config-yaml-schema)
- [Results JSON Schema](#results-json-schema)
- [Debug Results JSON](#debug-results-json)

---

## Task YAML Schema

Task files define what to evaluate and how to grade results.

**Location:** `evals/tasks/<category>/<task-name>.task.yaml`

### Schema

```yaml
# Required fields
id: string                    # Unique identifier (e.g., "fix-auth-bypass")
category: enum                # "coding" | "refactoring" | "exploration"
description: string           # What this task tests
prompt: string                # The prompt sent to Claude

# Optional fields
difficulty: enum              # "easy" | "medium" (default) | "hard"
fixture_path: string          # Relative path to fixture project
assertions: list              # List of assertions (code or llm)
scoring: object               # Weight configuration
timeout_seconds: integer      # Max execution time (default: 300)
```

### Field Details

#### id (required)
```yaml
id: fix-auth-bypass
```
Unique identifier for the task. Used in results and filtering.

#### category (required)
```yaml
category: coding  # or "refactoring" or "exploration"
```

| Value | Description |
|-------|-------------|
| `coding` | Bug fixes, new features |
| `refactoring` | Code improvements |
| `exploration` | Code analysis tasks |

#### description (required)
```yaml
description: Fix authentication bypass vulnerability where empty passwords are accepted
```
Human-readable description of what this task tests.

#### prompt (required)
```yaml
prompt: |
  There's a security vulnerability in src/auth.py where users can bypass
  authentication by providing an empty password. The authenticate() function
  doesn't properly validate that the password is non-empty.

  Find and fix this vulnerability. Make sure:
  1. Empty passwords are rejected
  2. An appropriate error message is returned
  3. Existing tests still pass
```
The actual prompt sent to Claude Code.

#### difficulty (optional)
```yaml
difficulty: medium  # default
```

| Value | Description |
|-------|-------------|
| `easy` | Simple, single-step tasks |
| `medium` | Moderate complexity (default) |
| `hard` | Complex, multi-step tasks |

#### fixture_path (optional)
```yaml
fixture_path: ../../../fixtures/sample-project
```
Relative path (from task file) to the fixture project to copy into the isolated environment.

#### assertions (optional)
```yaml
assertions:
  - type: code
    check: tests_pass
    command: "pytest tests/test_auth.py -v"

  - type: code
    check: file_contains
    file: "src/auth.py"
    pattern: "if not password"

  - type: llm
    rubric: |
      The fix should validate empty passwords...
```

**Code Assertion:**
```yaml
- type: code
  check: enum          # "tests_pass" | "file_contains" | "file_exists" |
                       # "file_not_contains" | "command_succeeds"
  command: string      # For tests_pass, command_succeeds
  file: string         # For file_* checks
  pattern: string      # For file_contains, file_not_contains
```

**LLM Assertion:**
```yaml
- type: llm
  rubric: string       # Evaluation criteria
```

#### scoring (optional)
```yaml
scoring:
  tests_pass: 50
  file_contains: 20
  llm_quality: 30
```
Maps assertion type keywords to weights. Keys are matched against assertion IDs.

#### timeout_seconds (optional)
```yaml
timeout_seconds: 300  # default
```
Maximum time (in seconds) for the Claude Code execution.

### Complete Example

```yaml
id: fix-auth-bypass
category: coding
description: Fix authentication bypass vulnerability where empty passwords are accepted
difficulty: medium

prompt: |
  There's a security vulnerability in src/auth.py where users can bypass
  authentication by providing an empty password. The authenticate() function
  doesn't properly validate that the password is non-empty before checking
  credentials.

  Find and fix this vulnerability. Make sure:
  1. Empty passwords are rejected
  2. An appropriate error message is returned
  3. Existing tests still pass

fixture_path: ../../../fixtures/sample-project

assertions:
  - type: code
    check: tests_pass
    command: "pytest tests/test_auth.py -v"
  - type: code
    check: file_contains
    file: "src/auth.py"
    pattern: "len\\(password\\)|password\\s*==\\s*['\"]|not\\s+password"
  - type: llm
    rubric: |
      The fix should:
      - Validate that password is not empty or whitespace-only
      - Return an appropriate error message for empty passwords
      - Not break the existing authentication logic for valid passwords
      - Handle edge cases like None password gracefully

scoring:
  tests_pass: 50
  file_contains: 20
  llm_quality: 30

timeout_seconds: 300
```

---

## Config YAML Schema

Config files define how Claude Code is configured for evaluation runs.

**Location:** `evals/configs/<config-name>/config.yaml`

### Schema

```yaml
# Required fields
name: string                  # Config variant name

# Optional fields
description: string           # What this config tests
claude_md: string             # CLAUDE.md content to inject
skills_path: string           # Path to skills directory
agents_md: string             # Agents definition content
model: string                 # Model ID (default: "claude-sonnet-4-20250514")
max_turns: integer            # Turn limit (default: 10)
allowed_tools: list | "all"   # Tool restrictions (default: "all")
```

### Field Details

#### name (required)
```yaml
name: full
```
Identifier for this configuration variant.

#### description (optional)
```yaml
description: Full configuration with skills, CLAUDE.md, and agents
```

#### claude_md (optional)
```yaml
claude_md: |
  # Project Coding Standards

  ## Code Style
  - Use Python 3.11+ features
  - Follow PEP 8 conventions
  ...
```
Content injected as `CLAUDE.md` in the isolated environment.

#### skills_path (optional)
```yaml
skills_path: ~/.claude/skills
```
Path to skills directory to copy into the environment.

#### agents_md (optional)
```yaml
agents_md: |
  ## Available Agents

  ### code-reviewer
  Reviews code changes for quality, security, and best practices.
  ...
```
Content injected as `agents.md` in the environment.

#### model (optional)
```yaml
model: claude-sonnet-4-20250514  # default
```
Model ID to use for the evaluation.

#### max_turns (optional)
```yaml
max_turns: 10  # default
```
Maximum API round-trips before stopping.

#### allowed_tools (optional)
```yaml
allowed_tools: all  # default
# or
allowed_tools:
  - Read
  - Write
  - Bash
```
Tool restrictions. Use `"all"` for no restrictions or a list of tool names.

### Complete Example

```yaml
name: full
description: Full configuration with skills, CLAUDE.md, and agents

claude_md: |
  # Project Coding Standards

  ## Code Style
  - Use Python 3.11+ features
  - Follow PEP 8 conventions
  - Use type hints for all functions
  - Keep functions small and focused

  ## Error Handling
  - Always handle exceptions explicitly
  - Log errors with context
  - Return meaningful error messages

  ## Security
  - Never log sensitive data
  - Validate all input at boundaries
  - Follow OWASP guidelines

skills_path: ~/.claude/skills

agents_md: |
  ## Available Agents

  ### code-reviewer
  Reviews code changes for quality, security, and best practices.
  Use when: Making significant code changes

  ### debugger
  Systematic debugging for errors and failures.
  Use when: Encountering bugs or test failures

model: claude-sonnet-4-20250514
max_turns: 15
allowed_tools: all
```

---

## Results JSON Schema

Results files contain evaluation outcomes.

**Location:** `evals/results/results_<timestamp>.json`

### Schema

```json
{
  "timestamp": "ISO 8601 datetime",
  "num_results": "integer",
  "results": [
    {
      "task_id": "string",
      "config_name": "string",
      "model": "string",
      "run_index": "integer",
      "timestamp": "ISO 8601 datetime",
      "trace": "ExecutionTrace",
      "grades": ["GradeResult"],
      "overall_score": "float (0.0-1.0)",
      "passed": "boolean"
    }
  ]
}
```

### ExecutionTrace Schema

```json
{
  "session_id": "string | null",
  "result": "string",
  "is_error": "boolean",
  "usage": {
    "input_tokens": "integer",
    "output_tokens": "integer",
    "cache_read_tokens": "integer",
    "cache_creation_tokens": "integer"
  },
  "tool_calls": [
    {
      "name": "string",
      "input": "object",
      "output": "string | null",
      "error": "string | null",
      "timestamp": "ISO 8601 datetime | null"
    }
  ],
  "duration_seconds": "float",
  "num_turns": "integer",
  "raw_output": "object",
  "file_changes": [
    {
      "path": "string",
      "action": "created | modified | deleted",
      "diff": "string | null",
      "content_after": "string | null"
    }
  ],
  "claude_prompt": "string",
  "claude_response": "string",
  "config_snapshot": {
    "model": "string",
    "claude_md": "string | null",
    "skills_path": "string | null",
    "max_turns": "integer"
  },
  "max_turns": "integer",
  "hit_turn_limit": "boolean",
  "stderr": "string"
}
```

### GradeResult Schema

```json
{
  "assertion_id": "string",
  "assertion_type": "code | llm",
  "assertion_name": "string",
  "passed": "boolean",
  "score": "float (0.0-1.0)",
  "details": "string",
  "reasoning": "string",
  "full_output": "string",
  "grading_prompt": "string",
  "criteria_scores": [
    {
      "criterion": "string",
      "score": "float (0.0-1.0)",
      "reasoning": "string"
    }
  ]
}
```

### Complete Example

```json
{
  "timestamp": "2025-01-31T10:30:00.000000",
  "num_results": 1,
  "results": [
    {
      "task_id": "fix-auth-bypass",
      "config_name": "full",
      "model": "claude-sonnet-4-20250514",
      "run_index": 0,
      "timestamp": "2025-01-31T10:29:45.123456",
      "trace": {
        "session_id": "abc123",
        "result": "I've fixed the authentication bypass vulnerability...",
        "is_error": false,
        "usage": {
          "input_tokens": 1500,
          "output_tokens": 800,
          "cache_read_tokens": 0,
          "cache_creation_tokens": 0
        },
        "tool_calls": [
          {
            "name": "Read",
            "input": {"file_path": "src/auth.py"},
            "output": "...",
            "error": null,
            "timestamp": "2025-01-31T10:29:46.000000"
          },
          {
            "name": "Edit",
            "input": {"file_path": "src/auth.py", "...": "..."},
            "output": "File edited",
            "error": null,
            "timestamp": "2025-01-31T10:29:47.000000"
          }
        ],
        "duration_seconds": 15.5,
        "num_turns": 3,
        "raw_output": {},
        "file_changes": [
          {
            "path": "src/auth.py",
            "action": "modified",
            "diff": "--- a/src/auth.py\n+++ b/src/auth.py\n@@ -10,6 +10,8 @@\n def authenticate(...):\n+    if not password:\n+        return False, 'Password required'\n",
            "content_after": null
          }
        ],
        "claude_prompt": "There's a security vulnerability...",
        "claude_response": "I've fixed the authentication bypass...",
        "config_snapshot": {
          "model": "claude-sonnet-4-20250514",
          "claude_md": "# Project Coding Standards...",
          "skills_path": null,
          "max_turns": 15
        },
        "max_turns": 15,
        "hit_turn_limit": false,
        "stderr": ""
      },
      "grades": [
        {
          "assertion_id": "code_0_tests_pass",
          "assertion_type": "code",
          "assertion_name": "tests_pass",
          "passed": true,
          "score": 1.0,
          "details": "All tests passed",
          "reasoning": "",
          "full_output": "===== 5 passed =====",
          "grading_prompt": "",
          "criteria_scores": []
        },
        {
          "assertion_id": "code_1_file_contains",
          "assertion_type": "code",
          "assertion_name": "file_contains",
          "passed": true,
          "score": 1.0,
          "details": "Pattern found: if not password",
          "reasoning": "",
          "full_output": "...",
          "grading_prompt": "",
          "criteria_scores": []
        },
        {
          "assertion_id": "llm_0",
          "assertion_type": "llm",
          "assertion_name": "llm_quality",
          "passed": true,
          "score": 0.9,
          "details": "- Password validation: 1.0\n- Error handling: 0.8",
          "reasoning": "Good implementation with comprehensive validation",
          "full_output": "{\"criteria_scores\": [...], \"overall_score\": 0.9}",
          "grading_prompt": "You are evaluating...",
          "criteria_scores": [
            {
              "criterion": "Password validation",
              "score": 1.0,
              "reasoning": "Correctly validates empty passwords"
            },
            {
              "criterion": "Error handling",
              "score": 0.8,
              "reasoning": "Good error messages but could be more specific"
            }
          ]
        }
      ],
      "overall_score": 0.94,
      "passed": true
    }
  ]
}
```

---

## Debug Results JSON

Debug files contain additional execution details for troubleshooting.

**Location:** `evals/results/results_<timestamp>.debug.json`

### Schema

```json
{
  "timestamp": "ISO 8601 datetime",
  "num_results": "integer",
  "results": [
    "... (full EvalResult with extended data) ..."
  ],
  "execution_summary": {
    "total_results": "integer",
    "total_passed": "integer",
    "total_failed": "integer",
    "total_files_changed": "integer",
    "total_tool_calls": "integer",
    "hit_turn_limit_count": "integer",
    "unique_tasks": "integer",
    "unique_configs": "integer"
  }
}
```

### Extended Result Data

Debug results include additional fields:

```json
{
  "... (standard EvalResult fields) ...",
  "trace": {
    "... (standard trace fields) ...",
    "file_changes_summary": [
      {"path": "string", "action": "string"}
    ],
    "tool_call_timeline": [
      {
        "name": "string",
        "had_error": "boolean",
        "timestamp": "ISO 8601 datetime | null"
      }
    ]
  },
  "grading_breakdown": [
    {
      "assertion_id": "string",
      "assertion_type": "string",
      "assertion_name": "string",
      "passed": "boolean",
      "score": "float",
      "has_full_output": "boolean",
      "has_grading_prompt": "boolean",
      "num_criteria": "integer"
    }
  ]
}
```

### Execution Summary

```json
{
  "execution_summary": {
    "total_results": 12,
    "total_passed": 9,
    "total_failed": 3,
    "total_files_changed": 24,
    "total_tool_calls": 156,
    "hit_turn_limit_count": 1,
    "unique_tasks": 4,
    "unique_configs": 3
  }
}
```
