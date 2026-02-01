# CLI Reference

Complete reference for all commands in the agent-eval CLI.

## Global Options

```bash
uv run python -m harness [OPTIONS] COMMAND [ARGS]
```

| Option | Short | Environment Variable | Description |
|--------|-------|---------------------|-------------|
| `--env-file PATH` | `-e` | `EVAL_ENV_FILE` | Path to .env file (default: searches ./.env, ~/.env) |

The CLI automatically loads environment variables from `.env` files in this order:
1. Path specified via `--env-file`
2. Current directory (`./.env`)
3. Home directory (`~/.env`)
4. Local override (`./.env.local`)

---

## Commands

### run

Run a single evaluation task.

```bash
uv run python -m harness run [OPTIONS]
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--task PATH` | `-t` | Yes | - | Path to task YAML file |
| `--config PATH` | `-c` | Yes | - | Path to config YAML file |
| `--model MODEL` | `-m` | No | config value | Model to use (overrides config) |
| `--output PATH` | `-o` | No | - | Output file for results |
| `--verbose` | `-v` | No | False | Show detailed output including full test output and diffs |

**Example:**
```bash
uv run python -m harness run \
  --task evals/tasks/coding/fix-auth-bypass.task.yaml \
  --config evals/configs/full/config.yaml \
  --verbose
```

---

### matrix

Run full evaluation matrix (tasks × configs × models × runs).

```bash
uv run python -m harness matrix [OPTIONS]
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--tasks PATTERN` | `-t` | Yes | - | Glob pattern for task files |
| `--configs PATTERN` | `-c` | Yes | - | Glob pattern for config files |
| `--models MODELS` | `-m` | No | config values | Comma-separated list of models |
| `--runs N` | `-r` | No | 3 | Number of runs per combination |
| `--output PATH` | `-o` | No | timestamped | Output file for results |

**Example:**
```bash
uv run python -m harness matrix \
  --tasks "evals/tasks/**/*.task.yaml" \
  --configs "evals/configs/*/config.yaml" \
  --models "claude-sonnet-4-20250514,claude-3-5-haiku-20241022" \
  --runs 3
```

---

### regression

Compare current results against baseline for regression detection.

```bash
uv run python -m harness regression [OPTIONS]
```

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--baseline PATH` | `-b` | Yes | Path to baseline results JSON |
| `--current PATH` | `-c` | Yes | Path to current results JSON |

**Example:**
```bash
uv run python -m harness regression \
  --baseline evals/results/baseline.json \
  --current evals/results/current.json
```

---

### report

Generate report from existing results file.

```bash
uv run python -m harness report [OPTIONS]
```

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--results PATH` | `-r` | Yes | Path to results JSON file |

**Example:**
```bash
uv run python -m harness report --results evals/results/results_20250131.json
```

---

### analyze

Analyze eval results with detailed breakdowns.

```bash
uv run python -m harness analyze RESULTS_FILE [OPTIONS]
```

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `RESULTS_FILE` | Yes | - | Path to results JSON file |
| `--task ID` | No | - | Filter by task ID (substring match) |
| `--failed-only` / `-f` | No | False | Show only failed results |

**Example:**
```bash
# Analyze all results
uv run python -m harness analyze evals/results/results.json

# Filter to specific task
uv run python -m harness analyze evals/results/results.json --task fix-auth

# Show only failures
uv run python -m harness analyze evals/results/results.json --failed-only
```

---

### diff

Compare two eval runs side-by-side (A/B testing).

```bash
uv run python -m harness diff RESULT_A RESULT_B [OPTIONS]
```

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `RESULT_A` | Yes | - | Path to first results JSON |
| `RESULT_B` | Yes | - | Path to second results JSON |
| `--label-a LABEL` | No | "A" | Label for first result set |
| `--label-b LABEL` | No | "B" | Label for second result set |

**Example:**
```bash
uv run python -m harness diff \
  evals/results/baseline.json \
  evals/results/with_skills.json \
  --label-a "No Skills" \
  --label-b "With Skills"
```

---

### explain

Deep dive into a single result with full context.

```bash
uv run python -m harness explain RESULTS_FILE [OPTIONS]
```

| Argument/Option | Short | Required | Description |
|-----------------|-------|----------|-------------|
| `RESULTS_FILE` | - | Yes | Path to results JSON file |
| `--result-index N` | `-i` | Yes | Index of the result to explain (0-based) |

Shows:
- Configuration used
- Full prompt sent
- Claude's complete response
- All file changes with full diffs
- Detailed grading breakdown
- Grading prompts (for LLM grades)
- Execution metrics

**Example:**
```bash
# Explain the first failed result
uv run python -m harness explain evals/results/results.json --result-index 0
```

---

### validate-task

Validate a task YAML file.

```bash
uv run python -m harness validate-task [OPTIONS]
```

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--task PATH` | `-t` | Yes | Path to task YAML file |

**Example:**
```bash
uv run python -m harness validate-task -t evals/tasks/coding/fix-auth-bypass.task.yaml
```

**Output:**
```
Task 'fix-auth-bypass' is valid
  Category: coding
  Difficulty: medium
  Assertions: 3
  Code assertions: 2
  LLM assertions: 1
```

---

### validate-config

Validate a config YAML file.

```bash
uv run python -m harness validate-config [OPTIONS]
```

| Option | Short | Required | Description |
|--------|-------|----------|-------------|
| `--config PATH` | `-c` | Yes | Path to config YAML file |

**Example:**
```bash
uv run python -m harness validate-config -c evals/configs/full/config.yaml
```

**Output:**
```
Config 'full' is valid
  Model: claude-sonnet-4-20250514
  Max turns: 15
  Has CLAUDE.md: Yes
  Has skills: Yes
```

---

### export-config

Export current Claude Code configuration for CI.

```bash
uv run python -m harness export-config [OPTIONS]
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--output PATH` | `-o` | Yes | - | Output file for config snapshot |
| `--claude-home PATH` | - | No | ~/.claude | Path to Claude home directory |

Creates a snapshot containing:
- Claude CLI version
- Global CLAUDE.md content
- Settings
- MCP server configurations
- Skills

**Example:**
```bash
uv run python -m harness export-config -o ci-snapshot.json
```

---

### import-config

Set up CI environment from exported snapshot.

```bash
uv run python -m harness import-config [OPTIONS]
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--snapshot PATH` | `-s` | Yes | - | Path to config snapshot JSON |
| `--output PATH` | `-o` | Yes | - | Directory to create CI environment in |
| `--enable-mcp` / `--disable-mcp` | - | No | disabled | Enable/disable MCP servers in CI |

**Example:**
```bash
uv run python -m harness import-config \
  --snapshot ci-snapshot.json \
  --output /tmp/ci-home

# Output shows environment variables to set:
# export HOME=/tmp/ci-home
# export CLAUDE_HOME=/tmp/ci-home/.claude
```

---

### check-version

Check Claude Code version and compatibility.

```bash
uv run python -m harness check-version
```

**Example Output:**
```
Claude Code version: 1.0.8
Claude Code is installed and accessible
```

---

### env-status

Show environment configuration status.

```bash
uv run python -m harness env-status
```

Shows:
- Which .env file was loaded (if any)
- Status of required environment variables
- Status of optional environment variables

**Example Output:**
```
Environment Status
========================================
Loaded .env from: /Users/user/.env

Required Environment Variables
  ANTHROPIC_API_KEY: sk-ant-...key4

Optional Environment Variables
  EVAL_ENV_FILE: not set - Custom .env file path
  CLAUDE_HOME: not set - Claude Code home directory
```

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation failed, file not found, etc.) |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | **Required** for LLM grading |
| `EVAL_ENV_FILE` | Custom .env file path |
| `CLAUDE_HOME` | Claude Code home directory |

---

## Common Workflows

### Local Development Testing

```bash
# 1. Validate your task and config
uv run python -m harness validate-task -t evals/tasks/coding/my-task.task.yaml
uv run python -m harness validate-config -c evals/configs/full/config.yaml

# 2. Run single evaluation with verbose output
uv run python -m harness run \
  -t evals/tasks/coding/my-task.task.yaml \
  -c evals/configs/full/config.yaml \
  --verbose

# 3. If failed, deep dive into the result
uv run python -m harness explain evals/results/results.json -i 0
```

### A/B Testing Configurations

```bash
# 1. Run matrix with baseline config
uv run python -m harness matrix \
  -t "evals/tasks/**/*.task.yaml" \
  -c "evals/configs/baseline/config.yaml" \
  -o baseline.json

# 2. Run matrix with new config
uv run python -m harness matrix \
  -t "evals/tasks/**/*.task.yaml" \
  -c "evals/configs/full/config.yaml" \
  -o full.json

# 3. Compare results
uv run python -m harness diff baseline.json full.json \
  --label-a "Baseline" --label-b "Full Config"
```

### CI Pipeline Integration

```bash
# 1. On developer machine: export config
uv run python -m harness export-config -o ci-snapshot.json

# 2. In CI: import config
uv run python -m harness import-config \
  -s ci-snapshot.json \
  -o /tmp/ci-home

# 3. Set environment variables (from import output)
export HOME=/tmp/ci-home
export CLAUDE_HOME=/tmp/ci-home/.claude

# 4. Run evaluation matrix
uv run python -m harness matrix \
  -t "evals/tasks/**/*.task.yaml" \
  -c "evals/configs/*/config.yaml" \
  -r 3 \
  -o current.json

# 5. Compare against baseline
uv run python -m harness regression \
  -b baseline.json \
  -c current.json
```
