#!/bin/bash
#
# Skill Testing: A/B Comparison Script
#
# Runs evaluations with and without skills to measure their impact.
# Usage: ./run-comparison.sh [backend|frontend|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  Skill Testing: A/B Comparison"
echo "=========================================="
echo ""

# Check prerequisites
if ! command -v uv &> /dev/null; then
    echo -e "${RED}Error: 'uv' is not installed.${NC}"
    echo "Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Load environment variables from ~/.env if it exists
if [ -f ~/.env ]; then
    echo "Loading environment from ~/.env..."
    set -a
    source ~/.env
    set +a
fi

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo -e "${RED}Error: ANTHROPIC_API_KEY is not set.${NC}"
    echo "Set it with: export ANTHROPIC_API_KEY='your-key-here'"
    echo "Or add it to ~/.env"
    exit 1
fi

# Parse arguments
TEST_TYPE="${1:-all}"

run_backend_comparison() {
    echo -e "${YELLOW}Running Backend Skill Comparison...${NC}"
    echo ""

    # Run baseline (no skill)
    echo "Step 1/2: Running baseline (no skill)..."
    cd "$PROJECT_ROOT"
    uv run python -m harness matrix \
        --tasks "examples/skill-testing/tasks/backend/*.yaml" \
        --configs "examples/skill-testing/configs/baseline/config.yaml" \
        --runs 2 \
        --output "examples/skill-testing/results/backend-baseline.json" \
        2>&1 | tee "$SCRIPT_DIR/results/backend-baseline.log"

    # Run with skill
    echo ""
    echo "Step 2/2: Running with backend skill..."
    uv run python -m harness matrix \
        --tasks "examples/skill-testing/tasks/backend/*.yaml" \
        --configs "examples/skill-testing/configs/backend-skill/config.yaml" \
        --runs 2 \
        --output "examples/skill-testing/results/backend-skill.json" \
        2>&1 | tee "$SCRIPT_DIR/results/backend-skill.log"

    echo ""
    echo -e "${GREEN}Backend comparison complete!${NC}"
    echo "Results saved to: $SCRIPT_DIR/results/"
}

run_frontend_comparison() {
    echo -e "${YELLOW}Running Frontend Skill Comparison...${NC}"
    echo ""

    # Run baseline (no skill)
    echo "Step 1/2: Running baseline (no skill)..."
    cd "$PROJECT_ROOT"
    uv run python -m harness matrix \
        --tasks "examples/skill-testing/tasks/frontend/*.yaml" \
        --configs "examples/skill-testing/configs/baseline/config.yaml" \
        --runs 2 \
        --output "examples/skill-testing/results/frontend-baseline.json" \
        2>&1 | tee "$SCRIPT_DIR/results/frontend-baseline.log"

    # Run with skill
    echo ""
    echo "Step 2/2: Running with frontend skill..."
    uv run python -m harness matrix \
        --tasks "examples/skill-testing/tasks/frontend/*.yaml" \
        --configs "examples/skill-testing/configs/frontend-skill/config.yaml" \
        --runs 2 \
        --output "examples/skill-testing/results/frontend-skill.json" \
        2>&1 | tee "$SCRIPT_DIR/results/frontend-skill.log"

    echo ""
    echo -e "${GREEN}Frontend comparison complete!${NC}"
    echo "Results saved to: $SCRIPT_DIR/results/"
}

# Create results directory
mkdir -p "$SCRIPT_DIR/results"

case "$TEST_TYPE" in
    backend)
        run_backend_comparison
        ;;
    frontend)
        run_frontend_comparison
        ;;
    all)
        run_backend_comparison
        echo ""
        echo "=========================================="
        echo ""
        run_frontend_comparison
        ;;
    *)
        echo "Usage: $0 [backend|frontend|all]"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "  Comparison Complete"
echo "=========================================="
echo ""
echo "To view results:"
echo "  cat examples/skill-testing/results/backend-baseline.json"
echo "  cat examples/skill-testing/results/backend-skill.json"
echo ""
echo "To compare scores, look at the 'overall_score' field in each result."
