#!/bin/bash
# Run ALL steps to set up Kind + vLLM

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================="
echo "Complete Kind + vLLM Setup"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Install Kind (if needed)"
echo "  2. Create Kind cluster"
echo "  3. Deploy vLLM"
echo "  4. Wait for vLLM to be ready"
echo "  5. Run benchmark"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Make all scripts executable
chmod +x "$SCRIPT_DIR"/*.sh

# Run each step
echo ""
echo "=========================================="
echo "Step 1: Installing Kind"
echo "=========================================="
"$SCRIPT_DIR/01-install-kind.sh"

echo ""
echo "=========================================="
echo "Step 2: Creating Cluster"
echo "=========================================="
"$SCRIPT_DIR/02-create-kind-cluster.sh"

echo ""
echo "=========================================="
echo "Step 3: Deploying vLLM"
echo "=========================================="
"$SCRIPT_DIR/03-deploy-vllm.sh"

echo ""
echo "=========================================="
echo "Step 4: Waiting for vLLM"
echo "=========================================="
"$SCRIPT_DIR/04-wait-and-test.sh"

echo ""
echo "=========================================="
echo "Step 5: Running Benchmark"
echo "=========================================="
"$SCRIPT_DIR/05-run-benchmark.sh"

echo ""
echo "=========================================="
echo "ALL DONE!"
echo "=========================================="
echo ""
echo "Results are in:"
echo "  - kind_vllm_benchmark.png"
echo "  - kind_vllm_benchmark_results.json"
echo ""
echo "To clean up: ./06-cleanup.sh"
