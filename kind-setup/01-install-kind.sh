#!/bin/bash
# Step 1: Install Kind (Kubernetes in Docker)
# This script installs Kind on your system

set -e

echo "=================================================="
echo "Step 1: Installing Kind (Kubernetes in Docker)"
echo "=================================================="

# Check if kind is already installed
if command -v kind &> /dev/null; then
    echo "✓ Kind is already installed: $(kind version)"
    exit 0
fi

# Download and install kind
echo "➜ Downloading Kind..."
curl -Lo ./kind https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64

echo "➜ Making kind executable..."
chmod +x ./kind

echo "➜ Moving kind to /usr/local/bin/ (requires sudo)..."
sudo mv ./kind /usr/local/bin/kind

# Verify installation
if command -v kind &> /dev/null; then
    echo "✓ Kind installed successfully: $(kind version)"
else
    echo "✗ Kind installation failed"
    exit 1
fi

echo ""
echo "=================================================="
echo "Kind Installation Complete!"
echo "=================================================="
echo "Next step: Run ./kind-setup/02-create-kind-cluster.sh"
