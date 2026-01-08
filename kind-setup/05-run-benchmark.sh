#!/bin/bash
# Step 5: Run the benchmark on Kind cluster

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=========================================="
echo "Step 5: Running Benchmark on Kind"
echo "=========================================="

# Check if Kind cluster exists
if ! kind get clusters 2>/dev/null | grep -q vllm-cluster; then
    echo "❌ Kind cluster 'vllm-cluster' not found!"
    echo "   Run 02-create-kind-cluster.sh first"
    exit 1
fi

# Check if vLLM pod is running
echo "Checking vLLM pod status..."
kubectl get pods -n vllm

POD_STATUS=$(kubectl get pods -n vllm -l app=vllm -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "NotFound")

if [ "$POD_STATUS" != "Running" ]; then
    echo "❌ vLLM pod is not running (status: $POD_STATUS)"
    echo "   Check logs: kubectl logs -n vllm -l app=vllm"
    exit 1
fi

echo "✅ vLLM pod is running"

# Test API access
echo ""
echo "Testing API access on port 30000..."
if curl -s "http://localhost:30000/v1/models" > /dev/null 2>&1; then
    echo "✅ API is accessible"
    curl -s "http://localhost:30000/v1/models" | head -c 500
    echo ""
else
    echo "❌ Cannot access API on localhost:30000"
    echo "   Trying to set up port-forward..."
    kubectl port-forward -n vllm svc/vllm-service 30000:8000 &
    PF_PID=$!
    sleep 3
    
    if curl -s "http://localhost:30000/v1/models" > /dev/null 2>&1; then
        echo "✅ Port forward working"
    else
        echo "❌ Still cannot access API"
        kill $PF_PID 2>/dev/null || true
        exit 1
    fi
fi

# Install dependencies if needed
echo ""
echo "Checking Python dependencies..."
cd "$PARENT_DIR"

if [ -d ".venv" ]; then
    source .venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv .venv
    source .venv/bin/activate
fi

pip install aiohttp matplotlib numpy --quiet

# Run benchmark
echo ""
echo "=========================================="
echo "Starting Benchmark..."
echo "=========================================="

export VLLM_URL="http://localhost:30000/v1"
python3 "$SCRIPT_DIR/kind_benchmark.py"

# Check if graph was created
if [ -f "kind_vllm_benchmark.png" ]; then
    echo ""
    echo "✅ Benchmark completed successfully!"
    echo "   Graph: kind_vllm_benchmark.png"
    echo "   Results: kind_vllm_benchmark_results.json"
else
    echo "⚠️ Benchmark ran but graph not found"
fi
