# Assertions Reference

Complete reference for all assertion types supported by the agent-eval harness.

## Table of Contents

- [Overview](#overview)
- [Code Assertions](#code-assertions)
  - [tests_pass](#tests_pass)
  - [file_contains](#file_contains)
  - [file_not_contains](#file_not_contains)
  - [file_exists](#file_exists)
  - [command_succeeds](#command_succeeds)
- [LLM Assertions](#llm-assertions)
- [Scoring Configuration](#scoring-configuration)
- [Examples](#examples)

---

## Overview

Assertions define how evaluation results are graded. Each task can have multiple assertions of different types.

### Assertion Types

| Type | Purpose | Scoring |
|------|---------|---------|
| `code` | Objective, deterministic checks | Binary: 0.0 or 1.0 |
| `llm` | Subjective quality evaluation | Continuous: 0.0 to 1.0 |

### Basic Structure

```yaml
assertions:
  - type: code
    check: tests_pass
    command: "pytest"

  - type: llm
    rubric: "Evaluation criteria..."
```

---

## Code Assertions

Code assertions perform objective checks and produce binary scores (pass = 1.0, fail = 0.0).

### tests_pass

Runs a test command and checks the exit code.

**Schema:**
```yaml
- type: code
  check: tests_pass
  command: "pytest tests/test_auth.py -v"  # Optional, default: "pytest"
```

**Fields:**

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `type` | string | Yes | - | Must be `"code"` |
| `check` | string | Yes | - | Must be `"tests_pass"` |
| `command` | string | No | `"pytest"` | Test command to execute |

**Behavior:**
- Executes command in isolated environment
- Passes if exit code is 0
- Timeout: 120 seconds
- Captures stdout/stderr for debugging

**Examples:**

```yaml
# Default pytest
- type: code
  check: tests_pass

# Specific test file
- type: code
  check: tests_pass
  command: "pytest tests/test_auth.py -v"

# With coverage
- type: code
  check: tests_pass
  command: "pytest --cov=src --cov-fail-under=80"

# JavaScript tests
- type: code
  check: tests_pass
  command: "npm test"

# Go tests
- type: code
  check: tests_pass
  command: "go test ./..."
```

---

### file_contains

Checks if a file contains a regex pattern.

**Schema:**
```yaml
- type: code
  check: file_contains
  file: "path/to/file.py"
  pattern: "regex_pattern"
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"code"` |
| `check` | string | Yes | Must be `"file_contains"` |
| `file` | string | Yes | Relative path to file |
| `pattern` | string | Yes | Python regex pattern |

**Behavior:**
- Reads file content
- Searches for pattern using `re.search()`
- Passes if pattern is found anywhere in file
- Fails if file doesn't exist

**Regex Notes:**
- Uses Python `re` module syntax
- Escape backslashes in YAML: `\\d` for `\d`
- Use `(?i)` for case-insensitive matching
- Use `(?s)` to make `.` match newlines

**Examples:**

```yaml
# Check for specific function call
- type: code
  check: file_contains
  file: "src/auth.py"
  pattern: "if not password"

# Multiple valid patterns (OR)
- type: code
  check: file_contains
  file: "src/auth.py"
  pattern: "len\\(password\\)|password\\s*==\\s*['\"]|not\\s+password"

# Case-insensitive match
- type: code
  check: file_contains
  file: "README.md"
  pattern: "(?i)installation"

# Check for import statement
- type: code
  check: file_contains
  file: "src/main.py"
  pattern: "^from typing import|^import typing"

# Verify error handling
- type: code
  check: file_contains
  file: "src/api.py"
  pattern: "try:.*except.*Exception"
```

---

### file_not_contains

Checks that a file does NOT contain a pattern.

**Schema:**
```yaml
- type: code
  check: file_not_contains
  file: "path/to/file.py"
  pattern: "unwanted_pattern"
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"code"` |
| `check` | string | Yes | Must be `"file_not_contains"` |
| `file` | string | Yes | Relative path to file |
| `pattern` | string | Yes | Python regex pattern |

**Behavior:**
- Reads file content
- Passes if pattern is NOT found
- Fails if file doesn't exist
- Fails if pattern is found

**Examples:**

```yaml
# Ensure no debug statements
- type: code
  check: file_not_contains
  file: "src/main.py"
  pattern: "print\\(|console\\.log"

# No hardcoded credentials
- type: code
  check: file_not_contains
  file: "src/config.py"
  pattern: "password\\s*=\\s*['\"]\\w+"

# No TODO comments
- type: code
  check: file_not_contains
  file: "src/auth.py"
  pattern: "#\\s*TODO"

# No deprecated function calls
- type: code
  check: file_not_contains
  file: "src/api.py"
  pattern: "old_function\\("

# Ensure vulnerability is removed
- type: code
  check: file_not_contains
  file: "src/auth.py"
  pattern: "return True\\s*$"
```

---

### file_exists

Checks if a file exists.

**Schema:**
```yaml
- type: code
  check: file_exists
  file: "path/to/expected_file.py"
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"code"` |
| `check` | string | Yes | Must be `"file_exists"` |
| `file` | string | Yes | Relative path to file |

**Behavior:**
- Checks if file exists at specified path
- Passes if file exists (including empty files)
- Passes for directories too

**Examples:**

```yaml
# Check new file was created
- type: code
  check: file_exists
  file: "src/new_feature.py"

# Check config file exists
- type: code
  check: file_exists
  file: ".env.example"

# Check test file was added
- type: code
  check: file_exists
  file: "tests/test_new_feature.py"

# Check directory structure
- type: code
  check: file_exists
  file: "src/utils/__init__.py"
```

---

### command_succeeds

Runs an arbitrary command and checks if it succeeds.

**Schema:**
```yaml
- type: code
  check: command_succeeds
  command: "your_command_here"
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"code"` |
| `check` | string | Yes | Must be `"command_succeeds"` |
| `command` | string | Yes | Shell command to execute |

**Behavior:**
- Executes command via shell
- Passes if exit code is 0
- Timeout: 60 seconds
- Captures stdout/stderr for debugging

**Examples:**

```yaml
# Syntax check
- type: code
  check: command_succeeds
  command: "python -m py_compile src/main.py"

# Import check
- type: code
  check: command_succeeds
  command: "python -c 'import src.auth'"

# Linting
- type: code
  check: command_succeeds
  command: "ruff check src/"

# Type checking
- type: code
  check: command_succeeds
  command: "mypy src/"

# Build verification
- type: code
  check: command_succeeds
  command: "npm run build"

# Custom validation script
- type: code
  check: command_succeeds
  command: "./scripts/validate.sh"

# Database migrations
- type: code
  check: command_succeeds
  command: "python manage.py migrate --check"
```

---

## LLM Assertions

LLM assertions use Claude to evaluate quality against a rubric.

**Schema:**
```yaml
- type: llm
  rubric: |
    Multi-line evaluation criteria
    describing what to check...
```

**Fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | Must be `"llm"` |
| `rubric` | string | Yes | Evaluation criteria for Claude |

**Behavior:**
- Sends task context and rubric to Claude
- Claude evaluates and returns structured JSON
- Produces continuous score from 0.0 to 1.0
- Includes per-criterion breakdown

### Writing Effective Rubrics

**Structure:**
```yaml
rubric: |
  The implementation should:
  - [Criterion 1]
  - [Criterion 2]
  - [Criterion 3]

  It should NOT:
  - [Anti-pattern 1]
  - [Anti-pattern 2]
```

**Best Practices:**

1. **Be specific and measurable**
   ```yaml
   rubric: |
     The fix should:
     - Add validation for empty passwords
     - Return HTTP 401 for invalid credentials
     - Log authentication failures without exposing passwords
   ```

2. **Include edge cases**
   ```yaml
   rubric: |
     Handle these edge cases:
     - Empty string input
     - None/null input
     - Whitespace-only input
     - Very long input (>10000 chars)
   ```

3. **Specify quality dimensions**
   ```yaml
   rubric: |
     Evaluate:

     Correctness:
     - Bug is fixed as described
     - No new bugs introduced

     Code Quality:
     - Clear, readable implementation
     - Follows project conventions

     Security:
     - No new vulnerabilities
     - Proper input validation
   ```

4. **Define pass/fail threshold**
   ```yaml
   rubric: |
     Minimum requirements (must all be met):
     - Input validation present
     - Error handling added

     Nice to have:
     - Unit tests added
     - Documentation updated
   ```

### Examples

**Bug Fix:**
```yaml
- type: llm
  rubric: |
    The authentication fix should:
    - Validate that password is not empty or whitespace-only
    - Return an appropriate error message for empty passwords
    - Not break existing authentication for valid passwords
    - Handle edge cases like None password gracefully
    - Follow existing code style
```

**New Feature:**
```yaml
- type: llm
  rubric: |
    The pagination implementation should:
    - Accept page and page_size parameters
    - Return appropriate metadata (total_count, has_next, has_prev)
    - Handle invalid page numbers gracefully
    - Maintain backward compatibility with existing API
    - Include appropriate tests
```

**Code Quality:**
```yaml
- type: llm
  rubric: |
    Evaluate the code refactoring:

    Structure:
    - Logical organization of functions
    - Appropriate use of classes/modules
    - Clear separation of concerns

    Readability:
    - Meaningful variable/function names
    - Appropriate comments where needed
    - Consistent formatting

    Maintainability:
    - No code duplication
    - Easy to extend
    - Well-defined interfaces
```

---

## Scoring Configuration

Use the `scoring` field to weight different assertions.

**Schema:**
```yaml
scoring:
  assertion_key: weight
```

**Matching Rules:**
- Keys match against assertion IDs
- Assertion IDs are: `code_N_checktype` or `llm_N`
- Partial matching: key found in ID
- Default weight: 1.0 if not specified

**Examples:**

```yaml
# Weight by check type
scoring:
  tests_pass: 50
  file_contains: 20
  llm_quality: 30

# Equal weights (explicit)
scoring:
  tests_pass: 1
  file_contains: 1
  llm_quality: 1

# Heavily favor tests
scoring:
  tests_pass: 80
  llm_quality: 20

# No scoring = equal weights
# assertions:
#   ...
# (no scoring key)
```

---

## Examples

### Complete Bug Fix Task

```yaml
id: fix-auth-bypass
category: coding
description: Fix authentication bypass vulnerability
difficulty: medium

prompt: |
  There's a security vulnerability in src/auth.py where users can bypass
  authentication by providing an empty password. Fix this vulnerability.

fixture_path: ../../../fixtures/sample-project

assertions:
  # Primary: tests must pass
  - type: code
    check: tests_pass
    command: "pytest tests/test_auth.py -v"

  # Verify fix approach
  - type: code
    check: file_contains
    file: "src/auth.py"
    pattern: "len\\(password\\)|password\\s*==\\s*['\"]|not\\s+password"

  # Ensure no early returns
  - type: code
    check: file_not_contains
    file: "src/auth.py"
    pattern: "return True\\s*$"

  # Quality evaluation
  - type: llm
    rubric: |
      The fix should:
      - Validate password is not empty
      - Return appropriate error message
      - Handle None gracefully
      - Not break valid authentication

scoring:
  tests_pass: 50
  file_contains: 20
  file_not_contains: 10
  llm_quality: 20

timeout_seconds: 300
```

### New Feature Task

```yaml
id: add-rate-limiting
category: coding
description: Add rate limiting to API endpoints
difficulty: hard

prompt: |
  Implement rate limiting for the /api/login endpoint.
  Limit to 5 requests per minute per IP address.

fixture_path: ../../../fixtures/api-project

assertions:
  - type: code
    check: tests_pass
    command: "pytest tests/ -v"

  - type: code
    check: file_exists
    file: "src/middleware/rate_limiter.py"

  - type: code
    check: file_contains
    file: "src/middleware/rate_limiter.py"
    pattern: "(?i)rate.*limit|limit.*rate"

  - type: code
    check: command_succeeds
    command: "python -c 'from src.middleware.rate_limiter import RateLimiter'"

  - type: llm
    rubric: |
      The rate limiting implementation should:
      - Track requests per IP address
      - Use sliding window or token bucket algorithm
      - Return HTTP 429 when limit exceeded
      - Include appropriate Retry-After header
      - Be thread-safe

scoring:
  tests_pass: 40
  file_exists: 10
  file_contains: 10
  command_succeeds: 10
  llm_quality: 30
```

### Exploration Task

```yaml
id: explain-architecture
category: exploration
description: Analyze and explain codebase architecture
difficulty: easy

prompt: |
  Analyze the codebase structure and create a document explaining
  the overall architecture, key components, and data flow.

fixture_path: ../../../fixtures/sample-project

assertions:
  - type: code
    check: file_exists
    file: "ARCHITECTURE.md"

  - type: code
    check: file_contains
    file: "ARCHITECTURE.md"
    pattern: "(?i)(component|module|service|layer)"

  - type: llm
    rubric: |
      The architecture document should:
      - Identify main components/modules
      - Explain relationships between components
      - Describe data flow through the system
      - Be accurate to the actual code
      - Be clear and well-organized

scoring:
  file_exists: 10
  file_contains: 10
  llm_quality: 80
```
