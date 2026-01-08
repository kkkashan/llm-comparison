#!/bin/bash
# Step 4: Wait for vLLM and Test
# This script waits for vLLM to be ready and tests the API

set -e

echo "=================================================="
echo "Step 4: Waiting for vLLM to be Ready"
echo "=================================================="

# Function to show pod logs
show_logs() {
    echo ""
    echo "--- Recent Pod Logs ---"
    kubectl logs deployment/vllm-deployment -n vllm --tail=20 2>/dev/null || echo "No logs yet"
    echo "------------------------"
}

# Check pod status
echo "➜ Checking pod status..."
kubectl get pods -n vllm

# Wait for pod to be running
echo ""
echo "➜ Waiting for pod to be running..."
echo "  (This may take 2-5 minutes for image pull and model download)"
echo ""

MAX_WAIT=600  # 10 minutes
INTERVAL=10
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    POD_STATUS=$(kubectl get pods -n vllm -o jsonpath='{.items[0].status.phase}' 2>/dev/null || echo "Unknown")
    CONTAINER_STATUS=$(kubectl get pods -n vllm -o jsonpath='{.items[0].status.containerStatuses[0].ready}' 2>/dev/null || echo "false")
    
    echo "[$(date +%H:%M:%S)] Pod: $POD_STATUS | Ready: $CONTAINER_STATUS | Elapsed: ${ELAPSED}s"
    
    if [ "$CONTAINER_STATUS" == "true" ]; then
        echo ""
        echo "✓ Pod is ready!"
        break
    fi
    
    # Check for crash
    if [ "$POD_STATUS" == "Failed" ] || [ "$POD_STATUS" == "Error" ]; then
        echo ""
        echo "✗ Pod failed!"
        show_logs
        kubectl describe pod -n vllm | tail -30
        exit 1
    fi
    
    # Show logs every 30 seconds
    if [ $((ELAPSED % 30)) -eq 0 ] && [ $ELAPSED -gt 0 ]; then
        show_logs
    fi
    
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo ""
    echo "✗ Timeout waiting for pod to be ready"
    show_logs
    kubectl describe pod -n vllm | tail -30
    exit 1
fi

# Test the API
echo ""
echo "=================================================="
echo "Testing vLLM API"
echo "=================================================="

# Get the node IP (for Kind, this is localhost)
NODE_PORT=30000
VLLM_URL="http://localhost:${NODE_PORT}"

echo "➜ Testing endpoint: ${VLLM_URL}"
echo ""

# Test models endpoint
echo "Test 1: Models endpoint"
echo "----------------------"
if curl -s "${VLLM_URL}/v1/models" | head -c 500; then
    echo ""
    echo "✓ Models endpoint working"
else
    echo "✗ Models endpoint failed"
fi

echo ""
echo ""

# Test completion
echo "Test 2: Completion request"
echo "-------------------------"
RESPONSE=$(curl -s "${VLLM_URL}/v1/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "prompt": "Hello, how are you?",
    "max_tokens": 50,
    "temperature": 0.7
  }')

echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
echo ""

echo ""
echo "=================================================="
echo "vLLM is Ready on Kind Cluster!"
echo "=================================================="
echo ""
echo "API Endpoint: http://localhost:30000/v1"
echo ""
echo "Next step: Run ./kind-setup/05-run-benchmark.sh"
