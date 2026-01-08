#!/bin/bash
# Step 2: Create Kind Cluster
# This script creates a Kind cluster configured for vLLM

set -e

echo "=================================================="
echo "Step 2: Creating Kind Cluster"
echo "=================================================="

CLUSTER_NAME="vllm-cluster"

# Check if kind is installed
if ! command -v kind &> /dev/null; then
    echo "✗ Kind is not installed. Run ./kind-setup/01-install-kind.sh first"
    exit 1
fi

# Check if cluster already exists
if kind get clusters 2>/dev/null | grep -q "$CLUSTER_NAME"; then
    echo "⚠ Cluster '$CLUSTER_NAME' already exists"
    read -p "Delete and recreate? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "➜ Deleting existing cluster..."
        kind delete cluster --name $CLUSTER_NAME
    else
        echo "Using existing cluster"
        kubectl cluster-info --context kind-$CLUSTER_NAME
        exit 0
    fi
fi

# Get script directory for proper path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Create cluster with configuration
echo "➜ Creating Kind cluster with config..."
kind create cluster --config "$SCRIPT_DIR/kind-config.yaml"

# Wait for cluster to be ready
echo "➜ Waiting for cluster to be ready..."
kubectl wait --for=condition=Ready nodes --all --timeout=120s

# Show cluster info
echo ""
echo "=================================================="
echo "Kind Cluster Created Successfully!"
echo "=================================================="
kubectl cluster-info --context kind-$CLUSTER_NAME
echo ""
kubectl get nodes
echo ""
echo "Next step: Run ./kind-setup/03-deploy-vllm.sh"
