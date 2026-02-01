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

### self-test

Run internal verification checks to validate the harness is working correctly.

```bash
uv run python -m harness self-test
```

Validates:
- Constants module is importable
- TokenUsage.from_dict() works
- Result grouping utility works
- CodeGrader helper works
- Config validation works
- Task validation works
- API key status

**Example Output:**
```
agent-eval Self-Test
========================================

[1/6] Constants module.............. ✓
[2/6] TokenUsage.from_dict()........ ✓
[3/6] Result grouping utility....... ✓
[4/6] CodeGrader helper............. ✓
[5/6] Config validation............. ✓
[6/6] Task validation............... ✓

API Key Status: ✓ ANTHROPIC_API_KEY is set

All checks passed!
```

---

### ls

List available tasks and configs.

```bash
uv run python -m harness ls [tasks|configs] [OPTIONS]
```

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `tasks` or `configs` | No | both | Filter to tasks or configs only |
| `--path PATH` | No | current dir | Base directory to search |

**Examples:**
```bash
# List all tasks and configs
uv run python -m harness ls

# List tasks only
uv run python -m harness ls tasks

# List configs only
uv run python -m harness ls configs

# Search specific directory
uv run python -m harness ls --path examples/getting-started/
```

**Example Output:**
```
Tasks
----------------------------------------
  ✓ examples/getting-started/tasks/fix-bug.task.yaml
    ID: fix-division-bug | coding | easy
  ✓ examples/getting-started/tasks/add-feature.task.yaml
    ID: add-email-validation | coding | medium

Configs
----------------------------------------
  ✓ examples/getting-started/configs/baseline/config.yaml
    Name: baseline | Model: claude-sonnet-4-20250514
```

---

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
| `--container` | - | No | False | Run evaluation in an isolated Docker container |
| `--preserve-artifacts` | - | No | False | Preserve full artifacts from the run |
| `--dry-run` | - | No | False | Validate task and config without executing (no API calls) |
| `--limit N` | `-l` | No | - | Limit to N runs for quick testing |

**Examples:**
```bash
# Validate configuration without executing (dry-run)
uv run python -m harness run \
  -t examples/getting-started/tasks/fix-bug.task.yaml \
  -c examples/getting-started/configs/baseline/config.yaml \
  --dry-run

# Basic run
uv run python -m harness run \
  --task evals/tasks/coding/fix-auth-bypass.task.yaml \
  --config evals/configs/full/config.yaml \
  --verbose

# Run in Docker container (requires build-image first)
uv run python -m harness run \
  -t evals/tasks/coding/fix-auth-bypass.task.yaml \
  -c evals/configs/full/config.yaml \
  --container

# Preserve artifacts for debugging
uv run python -m harness run \
  -t evals/tasks/coding/fix-auth-bypass.task.yaml \
  -c evals/configs/full/config.yaml \
  --preserve-artifacts
```

**Dry-run Output:**
```
Loading task from examples/getting-started/tasks/fix-bug.task.yaml...
Loading config from examples/getting-started/configs/baseline/config.yaml...

Dry-run validation
========================================

✓ Task loaded successfully
  ID: fix-division-bug
  Category: coding
  Difficulty: easy
  Assertions: 3 (3 code, 0 LLM)
  Fixture: ✓ examples/getting-started/fixtures/python-utils

✓ Config loaded successfully
  Name: baseline
  Model: claude-sonnet-4-20250514
  Max turns: 10
  CLAUDE.md: No
  Skills: No

✓ ANTHROPIC_API_KEY is set

Dry-run complete. No API calls were made.
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
| `--container` | - | No | False | Run evaluations in isolated Docker containers |
| `--preserve-artifacts` | - | No | False | Preserve full artifacts from each run |
| `--dry-run` | - | No | False | Validate tasks and configs without executing (no API calls) |
| `--limit N` | `-l` | No | - | Limit to N total runs for quick testing |

**Examples:**
```bash
# Validate matrix configuration (dry-run)
uv run python -m harness matrix \
  --tasks "examples/getting-started/tasks/*.yaml" \
  --configs "examples/getting-started/configs/*/config.yaml" \
  --runs 3 \
  --dry-run

# Quick test with limit
uv run python -m harness matrix \
  --tasks "evals/tasks/**/*.task.yaml" \
  --configs "evals/configs/*/config.yaml" \
  --limit 5

# Standard matrix run
uv run python -m harness matrix \
  --tasks "evals/tasks/**/*.task.yaml" \
  --configs "evals/configs/*/config.yaml" \
  --models "claude-sonnet-4-20250514,claude-3-5-haiku-20241022" \
  --runs 3

# Matrix in containers with artifact preservation
uv run python -m harness matrix \
  --tasks "evals/tasks/**/*.task.yaml" \
  --configs "evals/configs/*/config.yaml" \
  --container \
  --preserve-artifacts
```

---

### regression

Compare current results against baseline for regression detection.

```bash
uv run python -m harness regression [OPTIONS]
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--baseline PATH` | `-b` | Yes | - | Path to baseline results JSON |
| `--current PATH` | `-c` | Yes | - | Path to current results JSON |
| `--statistical` / `--no-statistical` | - | No | True | Use statistical significance testing |
| `--threshold` | `-t` | No | 0.05 | Regression threshold (5% default) |

**Example:**
```bash
uv run python -m harness regression \
  --baseline evals/results/baseline.json \
  --current evals/results/current.json \
  --statistical

# Without statistical significance testing
uv run python -m harness regression \
  --baseline baseline.json \
  --current current.json \
  --no-statistical \
  --threshold 0.1
```

---

### compare

Compare two result sets with statistical analysis.

```bash
uv run python -m harness compare RESULT_A RESULT_B [OPTIONS]
```

| Argument/Option | Required | Default | Description |
|-----------------|----------|---------|-------------|
| `RESULT_A` | Yes | - | Path to first results JSON |
| `RESULT_B` | Yes | - | Path to second results JSON |
| `--label-a LABEL` | No | "A" | Label for first result set |
| `--label-b LABEL` | No | "B" | Label for second result set |
| `--statistical` | No | True | Show statistical comparison |
| `--efficiency` / `--no-efficiency` | No | True | Include token/timing comparison |
| `--cost` | No | False | Include USD cost comparison |

Shows:
- Side-by-side pass rate comparison
- Token usage comparison with delta percentages
- Mann-Whitney U statistical test results
- Effect size (Cohen's d) with magnitude
- Duration comparison with p-values
- Cost comparison (with `--cost` flag)
- Actionable recommendations

**Examples:**
```bash
# Full comparison with efficiency metrics
uv run python -m harness compare baseline.json current.json --statistical

# Include cost analysis
uv run python -m harness compare baseline.json current.json --efficiency --cost

# Score-only comparison (no efficiency metrics)
uv run python -m harness compare baseline.json current.json --no-efficiency

# Custom labels
uv run python -m harness compare baseline.json with-skill.json \
  --label-a "No Skill" --label-b "With Skill"
```

**Example Output:**
```
STATISTICAL COMPARISON: Baseline vs Current
============================================================
┏━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ Metric      ┃ Baseline ┃ Current ┃ Delta  ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ Mean Score  │ 0.720    │ 0.850   │ +0.130 │
│ Sample Size │ 30       │ 30      │        │
└─────────────┴──────────┴─────────┴────────┘

Statistical Test (Mann-Whitney U)
  U-statistic: 245.50
  p-value: 0.0031
  Significant: Yes (alpha=0.05)

Effect Size (Cohen's d)
  Effect size: 1.23
  Magnitude: large

Efficiency Analysis
  Tokens:   12,450 → 9,960 (-20.0% fewer, p=0.012*)
  Duration: 98.6s → 70.3s (-28.7% faster, p=0.008**)
  Cost:     $0.4200 → $0.3400 (-19.0%)

Recommendation
  Significant large improvement detected (p=0.003, d=large).
  B uses 20% fewer tokens (statistically significant). B is 29% faster (statistically significant). B is more efficient overall.
```

---

### power-analysis

Calculate recommended sample size for reliable A/B testing.

```bash
uv run python -m harness power-analysis [OPTIONS]
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--baseline-rate` | `-b` | Yes | - | Expected baseline pass rate (0.0-1.0) |
| `--min-effect` | `-e` | No | 0.1 | Minimum effect size to detect (10% default) |
| `--power` | `-p` | No | 0.8 | Statistical power (80% default) |
| `--alpha` | `-a` | No | 0.05 | Significance level |

Uses power analysis to determine how many evaluation runs are needed to reliably detect a given effect size.

**Examples:**
```bash
# How many runs to detect 10% improvement from 70% baseline?
uv run python -m harness power-analysis -b 0.7 -e 0.1

# Detect smaller 5% effect (requires more samples)
uv run python -m harness power-analysis -b 0.7 -e 0.05

# Higher power requirement
uv run python -m harness power-analysis -b 0.7 -e 0.1 -p 0.9
```

**Example Output:**
```
POWER ANALYSIS RESULTS
==================================================
  Baseline pass rate: 70%
  Minimum detectable effect: 10%
  Statistical power: 80%
  Significance level (alpha): 0.05

  Recommended sample size: 62

  Sample size provides 80% power to detect 10% change.

Run this many evaluations per configuration for reliable comparison.
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

### scaffold

Generate a skill-testing directory structure.

```bash
uv run python -m harness scaffold [OPTIONS]
```

| Option | Short | Required | Default | Description |
|--------|-------|----------|---------|-------------|
| `--name NAME` | `-n` | Yes | - | Name of the skill test (directory name) |
| `--output PATH` | `-o` | No | current dir | Output directory |
| `--fixture-type TYPE` | - | No | python | Fixture type: `python` or `javascript` |
| `--skill-path PATH` | - | No | - | Path to existing skill to copy |

Creates a complete scaffold for A/B testing a skill:
- Task definitions
- Baseline and with-skill configs
- Sample fixture project with tests
- Run comparison script
- Results directory with .gitignore

**Examples:**
```bash
# Generate Python scaffold
uv run python -m harness scaffold --name my-skill-test

# Generate JavaScript scaffold
uv run python -m harness scaffold --name my-skill-test --fixture-type javascript

# Generate and copy existing skill
uv run python -m harness scaffold \
  --name my-skill-test \
  --skill-path ~/.claude/skills/my-skill
```

**Generated Structure:**
```
my-skill-test/
├── README.md
├── run-comparison.sh
├── tasks/
│   └── example.task.yaml
├── configs/
│   ├── baseline/config.yaml
│   └── with-skill/config.yaml
├── fixtures/
│   └── sample-project/
├── skills/
│   └── your-skill/
└── results/
```

---

### build-image

Build the Docker container image for isolated evaluations.

```bash
uv run python -m harness build-image [OPTIONS]
```

| Option | Required | Default | Description |
|--------|----------|---------|-------------|
| `--no-cache` | No | False | Build without using Docker cache |

The image includes:
- Claude Code CLI
- Python with uv package manager
- Node.js for JavaScript fixtures
- Non-root `eval` user for security

**Example:**
```bash
# Build the image
uv run python -m harness build-image

# Force rebuild without cache
uv run python -m harness build-image --no-cache
```

---

### image-status

Check the status of the evaluation container image.

```bash
uv run python -m harness image-status
```

**Example Output:**
```
Checking image: agent-eval:latest
Image exists
  Created: 2025-01-31T10:30:00Z
  Size: 1234.5 MB
```

Or if image doesn't exist:
```
Checking image: agent-eval:latest
Image not found
Build with: uv run python -m harness build-image
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

### Testing a New Skill

```bash
# 1. Generate scaffold for skill testing
uv run python -m harness scaffold \
  --name my-skill-test \
  --skill-path ~/.claude/skills/my-skill

# 2. Customize the generated files
cd my-skill-test
# Edit tasks/example.task.yaml
# Update fixtures/sample-project/ with relevant test code

# 3. Run A/B comparison
./run-comparison.sh

# 4. Or manually with containers for isolation
uv run python -m harness build-image  # first time only
uv run python -m harness matrix \
  -t "my-skill-test/tasks/*.yaml" \
  -c "my-skill-test/configs/*/config.yaml" \
  --container \
  --preserve-artifacts
```

### Debugging a Failed Evaluation

```bash
# 1. Run with artifact preservation
uv run python -m harness run \
  -t evals/tasks/coding/my-task.yaml \
  -c evals/configs/full/config.yaml \
  --preserve-artifacts

# 2. Examine artifacts
ls evals/artifacts/eval_*/
# metadata.json - run configuration
# fixture_before.tar.gz - original state
# fixture_after.tar.gz - modified state
# file_changes.diff - all changes
# claude_output.json - full Claude response

# 3. Use explain for detailed breakdown
uv run python -m harness explain evals/results/results.json -i 0
```
