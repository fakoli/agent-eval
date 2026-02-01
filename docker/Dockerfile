# agent-eval container image
# Provides isolated environment for running Claude Code evaluations

FROM debian:bookworm-slim

# Build arguments
ARG CLAUDE_VERSION=latest
ARG UV_VERSION=0.5
ARG NODE_VERSION=20

# Environment variables
ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    PATH="/home/eval/.local/bin:/home/eval/.cargo/bin:$PATH" \
    UV_SYSTEM_PYTHON=1 \
    HOME=/home/eval

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    gnupg \
    jq \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_VERSION}.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for evaluations
RUN groupadd -r eval && useradd -r -g eval -m -d /home/eval eval

# Switch to eval user for remaining setup
USER eval
WORKDIR /home/eval

# Install uv (Python package manager)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Create workspace directories
RUN mkdir -p /home/eval/workspace/project \
    /home/eval/workspace/results \
    /home/eval/.claude/skills

# Copy entrypoint script
COPY --chown=eval:eval entrypoint.sh /home/eval/entrypoint.sh
RUN chmod +x /home/eval/entrypoint.sh

# Set working directory
WORKDIR /home/eval/workspace/project

# Default entrypoint
ENTRYPOINT ["/home/eval/entrypoint.sh"]
