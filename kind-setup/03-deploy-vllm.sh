#!/bin/bash
# Step 3: Deploy vLLM to Kind Cluster
# This script deploys vLLM to the Kind cluster

set -e

# Get script directory for proper path resolution
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo "Step 3: Deploying vLLM to Kind Cluster"
echo "=================================================="

# Check if kubectl context is set to kind cluster
CURRENT_CONTEXT=$(kubectl config current-context)
if [[ "$CURRENT_CONTEXT" != *"kind"* ]]; then
    echo "⚠ Current context is not Kind: $CURRENT_CONTEXT"
    echo "➜ Switching to Kind context..."
    kubectl config use-context kind-vllm-cluster
fi

# Check if cluster is accessible
if ! kubectl cluster-info &> /dev/null; then
    echo "✗ Cannot connect to Kind cluster"
    echo "Run ./kind-setup/02-create-kind-cluster.sh first"
    exit 1
fi

echo "➜ Current Kubernetes context: $(kubectl config current-context)"
echo ""

# Pre-pull the image to the Kind node (speeds up deployment)
echo "➜ Loading vLLM image to Kind cluster (this may take a while)..."
echo "  (Pulling image first if not cached...)"

# Check if image exists locally
if ! sudo docker images | grep -q "vllm/vllm-openai"; then
    echo "➜ Pulling vLLM image..."
    sudo docker pull vllm/vllm-openai:latest
fi

# Load image into Kind
echo "➜ Loading image into Kind cluster..."
kind load docker-image vllm/vllm-openai:latest --name vllm-cluster

# Apply deployment
echo ""
echo "➜ Applying vLLM deployment..."
kubectl apply -f "$SCRIPT_DIR/vllm-kind-deployment.yaml"

# Show immediate status
echo ""
echo "➜ Deployment status:"
kubectl get all -n vllm

echo ""
echo "=================================================="
echo "vLLM Deployment Started!"
echo "=================================================="
echo ""
echo "The pod will take a few minutes to start (downloading model)."
echo ""
echo "Monitor with:"
echo "  kubectl get pods -n vllm -w"
echo "  kubectl logs -f deployment/vllm-deployment -n vllm"
echo ""
echo "Next step: Run ./kind-setup/04-wait-and-test.sh"
