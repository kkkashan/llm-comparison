#!/bin/bash
# Step 6: Cleanup Kind cluster

echo "=========================================="
echo "Step 6: Cleanup Kind Cluster"
echo "=========================================="

# Check if cluster exists
if kind get clusters 2>/dev/null | grep -q vllm-cluster; then
    echo "Deleting Kind cluster 'vllm-cluster'..."
    kind delete cluster --name vllm-cluster
    echo "✅ Cluster deleted"
else
    echo "ℹ️ Cluster 'vllm-cluster' does not exist"
fi

# Clean up port forwards
echo ""
echo "Cleaning up any port-forward processes..."
pkill -f "kubectl port-forward" 2>/dev/null || echo "No port-forward processes found"

echo ""
echo "✅ Cleanup complete!"
