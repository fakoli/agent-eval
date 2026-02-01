# Troubleshooting Guide

Common issues and solutions when using the agent-eval harness.

## Table of Contents

- [Known Issues](#known-issues)
- [Environment Setup](#environment-setup)
- [CLI Errors](#cli-errors)
- [Execution Failures](#execution-failures)
- [Grading Issues](#grading-issues)
- [CI/CD Integration](#cicd-integration)
- [Debugging Failed Evaluations](#debugging-failed-evaluations)

---

## Known Issues

### Fixture venv Paths

**Problem:** If you relocate the project, the fixture's virtual environment breaks.

**Symptoms:**
```
/old/path/to/.venv/bin/python: bad interpreter: No such file or directory
```

**Cause:** Python virtual environments contain hardcoded shebang paths in scripts like `pytest`.

**Solutions:**

1. **Recreate the venv:**
   ```bash
   cd fixtures/sample-project
   rm -rf .venv
   uv venv
   uv sync
   ```

2. **Fix the shebang manually:**
   ```bash
   # Check the current shebang
   head -1 fixtures/sample-project/.venv/bin/pytest

   # Replace with correct path
   sed -i '' "1s|.*|#!$(pwd)/fixtures/sample-project/.venv/bin/python|" \
     fixtures/sample-project/.venv/bin/pytest
   ```

---

### Stale Bytecode

**Problem:** Import errors after moving the project.

**Symptoms:**
```
ModuleNotFoundError: No module named 'harness'
ImportError: cannot import name 'X' from 'harness.models'
```

**Cause:** Python caches compiled bytecode in `__pycache__` directories with embedded paths.

**Solution:**
```bash
# Remove all __pycache__ directories
find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null

# Or use git clean
git clean -fdX
```

---

### Model Name Hardcoding

**Problem:** LLM grading fails with wrong model.

**Location:** The grading model is hardcoded in:
- `harness/graders/llm_graders.py`
- `harness/graders/composite_grader.py`

**Solution:** Update the model name in these files if using a different model:
```python
# In llm_graders.py and composite_grader.py
def __init__(
    self,
    model: str = "claude-3-5-haiku-20241022",  # Change this
    ...
)
```

---

## Environment Setup

### Missing ANTHROPIC_API_KEY

**Problem:** LLM grading fails.

**Symptoms:**
```
Warning: ANTHROPIC_API_KEY not set. LLM grading will fail.
LLM grading failed: Anthropic authentication failed
```

**Solutions:**

1. **Create a .env file:**
   ```bash
   echo "ANTHROPIC_API_KEY=your-key-here" > .env
   ```

2. **Use --env-file flag:**
   ```bash
   uv run python -m harness --env-file ~/.env run ...
   ```

3. **Check status:**
   ```bash
   uv run python -m harness env-status
   ```

---

### Claude Code Not Found

**Problem:** Claude CLI not installed or not in PATH.

**Symptoms:**
```
Claude Code not found - please install it first
FileNotFoundError: [Errno 2] No such file or directory: 'claude'
```

**Solution:**
```bash
# Check if claude is installed
which claude

# Install Claude Code (if not installed)
# See https://claude.ai/code for installation instructions

# Verify installation
uv run python -m harness check-version
```

---

### uv Not Found

**Problem:** uv package manager not installed.

**Symptoms:**
```
command not found: uv
```

**Solution:**
```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv

# Verify
uv --version
```

---

## CLI Errors

### Task Validation Failed

**Problem:** Task YAML is malformed.

**Symptoms:**
```
Task validation failed: 1 validation error for Task
category
  value is not a valid enumeration member
```

**Solutions:**

1. **Check the category value:**
   ```yaml
   # Valid values: coding, refactoring, exploration
   category: coding  # not "Coding" or "code"
   ```

2. **Check assertion format:**
   ```yaml
   assertions:
     - type: code      # not "Code"
       check: tests_pass  # not "TESTS_PASS"
   ```

3. **Validate before running:**
   ```bash
   uv run python -m harness validate-task -t your-task.yaml
   ```

---

### Config Validation Failed

**Problem:** Config YAML is malformed.

**Symptoms:**
```
Config validation failed: field required
```

**Solution:**
```bash
# Validate config
uv run python -m harness validate-config -c your-config.yaml
```

Ensure `name` field is present:
```yaml
name: my-config  # Required!
description: ...
```

---

### Glob Pattern Returns No Files

**Problem:** No tasks or configs found.

**Symptoms:**
```
Found 0 task(s)
Found 0 config(s)
```

**Solutions:**

1. **Check the pattern syntax:**
   ```bash
   # Patterns must be quoted in shell
   uv run python -m harness matrix \
     --tasks "evals/tasks/**/*.task.yaml" \
     --configs "evals/configs/*/config.yaml"
   ```

2. **Test the pattern:**
   ```bash
   # List matching files
   ls evals/tasks/**/*.task.yaml
   ls evals/configs/*/config.yaml
   ```

3. **Check working directory:**
   ```bash
   # Must run from project root
   pwd  # Should be /path/to/agent-eval
   ```

---

## Execution Failures

### Execution Timed Out

**Problem:** Claude Code takes too long.

**Symptoms:**
```
Execution timed out
```

**Solutions:**

1. **Increase timeout:**
   ```yaml
   # In task YAML
   timeout_seconds: 600  # 10 minutes instead of default 5
   ```

2. **Reduce task complexity:**
   - Break into smaller sub-tasks
   - Provide more specific instructions
   - Reduce fixture project size

3. **Check max_turns:**
   ```yaml
   # In config YAML
   max_turns: 20  # Allow more iterations
   ```

---

### Permission Denied

**Problem:** Can't execute in isolated environment.

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied
```

**Solutions:**

1. **Check temp directory permissions:**
   ```bash
   ls -la /tmp/  # Or your configured base_dir
   ```

2. **Check fixture permissions:**
   ```bash
   ls -la fixtures/sample-project/
   chmod -R u+rwX fixtures/
   ```

---

### JSON Parse Error

**Problem:** Claude CLI output is not valid JSON.

**Symptoms:**
```
JSONDecodeError: Expecting value: line 1 column 1
```

**Cause:** Claude Code didn't return JSON output format.

**Solutions:**

1. **Check Claude Code version:**
   ```bash
   uv run python -m harness check-version
   ```

2. **Verify --output-format flag is supported:**
   ```bash
   claude --help | grep -i json
   ```

---

## Grading Issues

### LLM Grading Failed

**Problem:** LLM grader can't evaluate.

**Symptoms:**
```
LLM grading failed: API error
Could not parse structured response
```

**Solutions:**

1. **Check API key:**
   ```bash
   uv run python -m harness env-status
   ```

2. **Check API limits:**
   - Rate limits may be exceeded
   - Account may need credits

3. **Simplify rubric:**
   - Shorter rubrics are more reliable
   - Remove ambiguous criteria

---

### Tests Pass Locally But Fail in Harness

**Problem:** Tests work locally but fail during evaluation.

**Solutions:**

1. **Check isolated environment:**
   - Fixture is copied fresh each run
   - Dependencies may not be installed
   - Environment variables may differ

2. **Add setup commands:**
   ```yaml
   assertions:
     - type: code
       check: command_succeeds
       command: "pip install -e ."

     - type: code
       check: tests_pass
       command: "pytest"
   ```

3. **Check paths:**
   - Use relative paths in tests
   - Don't hardcode absolute paths

---

### File Contains Pattern Not Matching

**Problem:** `file_contains` fails unexpectedly.

**Solutions:**

1. **Check regex escaping:**
   ```yaml
   # YAML requires escaping backslashes
   pattern: "\\d+"  # matches digits
   # Not: pattern: "\d+"
   ```

2. **Test pattern manually:**
   ```bash
   grep -E 'your_pattern' path/to/file
   ```

3. **Check file encoding:**
   - Ensure file is UTF-8
   - No BOM markers

---

## CI/CD Integration

### CI Environment Setup Fails

**Problem:** Can't import config snapshot.

**Solutions:**

1. **Check snapshot exists:**
   ```bash
   ls -la ci-snapshot.json
   ```

2. **Validate snapshot:**
   ```bash
   python -c "import json; json.load(open('ci-snapshot.json'))"
   ```

3. **Check output directory:**
   ```bash
   # Ensure directory is writable
   mkdir -p /tmp/ci-home
   ```

---

### Different Results in CI vs Local

**Problem:** Evaluations pass locally but fail in CI.

**Causes:**
- Different Claude Code versions
- Different environment variables
- Missing skills/CLAUDE.md

**Solutions:**

1. **Export local config:**
   ```bash
   uv run python -m harness export-config -o ci-snapshot.json
   ```

2. **Check versions match:**
   ```bash
   # Local
   claude --version

   # CI (in pipeline)
   uv run python -m harness check-version
   ```

3. **Debug CI environment:**
   ```bash
   uv run python -m harness env-status
   ```

---

## Debugging Failed Evaluations

### Step 1: Check the Summary

```bash
uv run python -m harness report -r results/results.json
```

Look for:
- Which tasks failed
- Which assertions failed
- Pass rates per config

### Step 2: Analyze Failures

```bash
# Filter to failed results
uv run python -m harness analyze results/results.json --failed-only
```

Look for:
- Assertion breakdown
- Patterns in failures

### Step 3: Deep Dive

```bash
# Get detailed view of specific result
uv run python -m harness explain results/results.json -i 0
```

This shows:
- Full prompt sent
- Claude's response
- All file changes with diffs
- Complete grading details
- Grading prompts used

### Step 4: Check Debug Log

```bash
# Debug file has extended data
cat results/results.debug.json | jq '.execution_summary'
```

Look for:
- Hit turn limit count
- Total tool calls
- File changes summary

### Step 5: Manual Reproduction

```bash
# Run single evaluation with verbose output
uv run python -m harness run \
  -t evals/tasks/coding/failing-task.yaml \
  -c evals/configs/full/config.yaml \
  --verbose
```

### Common Failure Patterns

| Symptom | Likely Cause |
|---------|--------------|
| All tests_pass fail | Fixture setup issue, missing dependencies |
| All llm assertions fail | API key issue, model access |
| Random failures | Non-deterministic behavior, flaky tests |
| Hit turn limit | Task too complex, unclear prompt |
| No file changes | Claude didn't modify files, prompt unclear |
