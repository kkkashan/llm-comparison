#!/bin/bash
# test-vllm-k8s.sh
# Test script for vLLM deployed on Kubernetes

set -e

VLLM_URL="${VLLM_URL:-http://localhost:8000}"

echo "=================================================="
echo "Testing vLLM on Kubernetes"
echo "=================================================="
echo "Target URL: ${VLLM_URL}"
echo ""

# Test 1: Check models endpoint
echo "Test 1: Models endpoint"
echo "----------------------"
response=$(curl -s ${VLLM_URL}/v1/models)
echo "$response" | jq . 2>/dev/null || echo "$response"
echo ""

# Test 2: Simple completion
echo "Test 2: Completion request"
echo "-------------------------"
response=$(curl -s ${VLLM_URL}/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "prompt": "What is Kubernetes?",
    "max_tokens": 100
  }')
echo "$response" | jq . 2>/dev/null || echo "$response"
echo ""

# Test 3: Health check
echo "Test 3: Health check"
echo "-------------------"
response=$(curl -s ${VLLM_URL}/health)
echo "$response"
echo ""

# Test 4: Chat completion
echo "Test 4: Chat completion"
echo "----------------------"
response=$(curl -s ${VLLM_URL}/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "messages": [
      {"role": "user", "content": "Explain Kubernetes in one sentence."}
    ],
    "max_tokens": 50
  }')
echo "$response" | jq . 2>/dev/null || echo "$response"
echo ""

echo "=================================================="
echo "All tests completed!"
echo "=================================================="
