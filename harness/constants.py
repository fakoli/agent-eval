"""Centralized constants and defaults for the evaluation harness.

This module provides a single source of truth for configuration values
that were previously hardcoded across multiple files.
"""

# Default model for execution (used in configs, container execution)
DEFAULT_EXECUTION_MODEL = "claude-sonnet-4-20250514"

# Default model for LLM grading (smaller, faster, cost-effective)
DEFAULT_GRADING_MODEL = "claude-3-5-haiku-20241022"

# Timeout defaults (in seconds)
DEFAULT_EXECUTION_TIMEOUT = 300  # 5 minutes for evaluation runs
DEFAULT_TEST_TIMEOUT = 120  # 2 minutes for test execution
DEFAULT_LINT_TIMEOUT = 60  # 1 minute for linting
DEFAULT_CONTAINER_TIMEOUT = 600  # 10 minutes for container runs

# Max turns default
DEFAULT_MAX_TURNS = 10

# Docker image defaults
DEFAULT_DOCKER_IMAGE_NAME = "agent-eval"
DEFAULT_DOCKER_IMAGE_TAG = "latest"

# Container resource defaults
DEFAULT_CONTAINER_MEMORY = "4g"
DEFAULT_CONTAINER_CPU = 2.0
