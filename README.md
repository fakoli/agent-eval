# agent-eval

**CI evaluation harness for multi-agent development environments.**

## The Problem

Modern enterprises are drifting into multi-agent development where different tools serve different cognitive jobs: Claude for ideation, Cursor for precision, Copilot for completions. The result is tool coexistence, not tool choice.

In this environment, agent instruction files (CLAUDE.md, Cursor rules) become **shared dependencies**. A single line change can silently degrade productivity across repositories.

Today these files are maintained through informal trust networks and anecdotal testing. This cannot scale.

## What agent-eval Does

agent-eval provides the safety net: **behavioral regression tests** that detect negative drift, support safe contribution from a broad set of engineers, and make multi-agent workflows predictable in high-stakes enterprise settings.

The goal is not to perfectly grade agent quality. The goal is to **reliably detect "worse"** so teams can iterate with confidence.

## Quick Start

```bash
# Install
uv venv && source .venv/bin/activate
uv sync

# Validate configuration files
uv run python -m harness validate-task -t evals/tasks/coding/fix-auth-bypass.task.yaml
uv run python -m harness validate-config -c evals/configs/full/config.yaml

# Run a single evaluation
uv run python -m harness run \
  --task evals/tasks/coding/fix-auth-bypass.task.yaml \
  --config evals/configs/full/config.yaml

# Run full matrix (tasks x configs x runs)
uv run python -m harness matrix \
  --tasks "evals/tasks/**/*.task.yaml" \
  --configs "evals/configs/*/config.yaml" \
  --runs 3

# Compare results for regression detection
uv run python -m harness regression \
  --baseline results/baseline.json \
  --current results/current.json
```

## Architecture

```
Tasks (what to test)     Configs (how to configure)     Graders (how to score)
        │                         │                            │
        └─────────────────────────┼────────────────────────────┘
                                  │
                                  ▼
                          ┌─────────────┐
                          │  EvalRunner │
                          └─────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
              ┌──────────┐ ┌──────────┐ ┌──────────┐
              │ Isolator │ │ Executor │ │ Reporter │
              └──────────┘ └──────────┘ └──────────┘
```

- **Tasks**: YAML files defining prompts, assertions, and scoring weights
- **Configs**: Environment variants (baseline, skills-only, claude-md-only, full)
- **Graders**: Code-based (tests pass, file contains) + LLM-based (rubric evaluation)
- **Isolator**: Fresh temp directory per run with injected configuration
- **Executor**: Pluggable backend (Claude Code CLI, future: Cursor)
- **Reporter**: Results aggregation and regression comparison

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for detailed technical documentation.

## Documentation

| Guide | Description |
|-------|-------------|
| [API Reference](docs/API_REFERENCE.md) | Complete class and method reference |
| [CLI Reference](docs/CLI_REFERENCE.md) | All commands with options and examples |
| [Grading Guide](docs/GRADING.md) | Scoring algorithm and assertion writing |
| [Assertions Reference](docs/ASSERTIONS.md) | All assertion types with examples |
| [JSON Schema](docs/JSON_SCHEMA.md) | Task, config, and results formats |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [Extending](docs/EXTENDING.md) | Adding executors, graders, assertions |

## Key Metrics

| Metric | Description |
|--------|-------------|
| **Pass Rate** | % of tasks completed successfully |
| **Pass@3** | Success in at least 1 of 3 attempts |
| **Token Usage** | Input + output tokens (cost efficiency) |
| **Code Quality** | LLM-graded quality score (0-1) |

## Configuration Variants

Four presets for A/B testing different Claude Code setups:

| Config | Skills | CLAUDE.md | Purpose |
|--------|--------|-----------|---------|
| `baseline` | No | No | Control group |
| `skills-only` | Yes | No | Skills impact |
| `claude-md-only` | No | Yes | Instructions impact |
| `full` | Yes | Yes | Combined effect |

## Roadmap

This project implements **Layer 3** of a larger vision:

1. **Layer 1** (future): Canonical specification format for agent instructions
2. **Layer 2** (future): Tool adapters (Claude Code, Cursor, Copilot)
3. **Layer 3** (this project): CI evaluation harness for regression detection

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup and guidelines.

## License

MIT
