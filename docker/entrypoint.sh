#!/bin/bash
#
# Entrypoint script for agent-eval container
# Runs Claude Code evaluation and captures output

set -eo pipefail

# Configuration from environment
PROMPT_FILE="${PROMPT_FILE:-/workspace/prompt.txt}"
OUTPUT_FILE="${OUTPUT_FILE:-/workspace/results/output.json}"
MODEL="${EVAL_MODEL:-claude-sonnet-4-20250514}"
MAX_TURNS="${EVAL_MAX_TURNS:-10}"

# Ensure results directory exists
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Check for required files
if [ ! -f "$PROMPT_FILE" ]; then
    echo '{"error": "Prompt file not found", "is_error": true}' > "$OUTPUT_FILE"
    exit 1
fi

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo '{"error": "ANTHROPIC_API_KEY not set", "is_error": true}' > "$OUTPUT_FILE"
    exit 1
fi

# Read prompt
PROMPT=$(cat "$PROMPT_FILE")

# Run Claude Code
echo "Starting evaluation..."
echo "Model: $MODEL"
echo "Max turns: $MAX_TURNS"
echo "Working directory: $(pwd)"

# Execute Claude with JSON output
# Use PIPESTATUS to capture the exit code of claude, not tee
claude \
    -p "$PROMPT" \
    --model "$MODEL" \
    --max-turns "$MAX_TURNS" \
    --output-format json \
    --dangerously-skip-permissions \
    --no-session-persistence \
    2>&1 | tee "$OUTPUT_FILE"

# Capture exit code from claude command (first command in pipeline)
EXIT_CODE=${PIPESTATUS[0]}

# Check if output is valid JSON
if ! jq -e . "$OUTPUT_FILE" > /dev/null 2>&1; then
    # Wrap non-JSON output
    CONTENT=$(cat "$OUTPUT_FILE")
    cat > "$OUTPUT_FILE" <<EOF
{
    "result": $(echo "$CONTENT" | jq -R -s .),
    "is_error": $([ $EXIT_CODE -eq 0 ] && echo "false" || echo "true"),
    "exit_code": $EXIT_CODE
}
EOF
fi

echo "Evaluation complete. Exit code: $EXIT_CODE"
exit $EXIT_CODE
