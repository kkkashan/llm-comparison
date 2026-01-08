#!/bin/bash
# deploy-vllm-k8s.sh
# Automated deployment script for vLLM on Kubernetes

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}➜${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check prerequisites
print_info "Checking prerequisites..."

if ! command -v kubectl &> /dev/null; then
    print_error "kubectl is not installed"
    exit 1
fi
print_success "kubectl is installed"

if ! kubectl cluster-info &> /dev/null; then
    print_error "Cannot connect to Kubernetes cluster"
    exit 1
fi
print_success "Kubernetes cluster is accessible"

# Create namespace
print_info "Creating namespace..."
kubectl apply -f kubernetes/namespace.yaml
print_success "Namespace created"

# Create PVC
print_info "Creating PersistentVolumeClaim..."
kubectl apply -f kubernetes/vllm-pvc.yaml
print_success "PVC created"

# Wait for PVC to be bound
print_info "Waiting for PVC to be bound..."
kubectl wait --for=condition=bound pvc/vllm-model-cache -n vllm --timeout=60s
print_success "PVC is bound"

# Deploy vLLM
print_info "Deploying vLLM..."
kubectl apply -f kubernetes/vllm-deployment.yaml
print_success "Deployment created"

# Create service
print_info "Creating service..."
kubectl apply -f kubernetes/vllm-service.yaml
print_success "Service created"

# Wait for deployment
print_info "Waiting for deployment to be ready (this may take several minutes)..."
kubectl wait --for=condition=available --timeout=600s deployment/vllm-deployment -n vllm
print_success "Deployment is ready"

# Show status
echo ""
echo "=================================================="
echo "vLLM Deployment Status"
echo "=================================================="
kubectl get all -n vllm

echo ""
echo "=================================================="
echo "Next Steps"
echo "=================================================="
echo "1. Port forward to access the service:"
echo "   kubectl port-forward service/vllm-service 8000:8000 -n vllm"
echo ""
echo "2. Test the API:"
echo "   curl http://localhost:8000/v1/models"
echo ""
echo "3. View logs:"
echo "   kubectl logs -f deployment/vllm-deployment -n vllm"
echo ""
echo "4. Run tests:"
echo "   ./kubernetes/test-vllm-k8s.sh"
echo "=================================================="
