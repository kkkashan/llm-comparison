# vLLM on Kubernetes - Step-by-Step Guide

This guide provides comprehensive instructions for deploying vLLM on Kubernetes with GPU support.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Step-by-Step Installation](#step-by-step-installation)
4. [Kubernetes Manifests](#kubernetes-manifests)
5. [Deployment Options](#deployment-options)
6. [Testing and Validation](#testing-and-validation)
7. [Scaling and Load Balancing](#scaling-and-load-balancing)
8. [Monitoring](#monitoring)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Components
- Kubernetes cluster (v1.23+)
- kubectl CLI tool installed
- NVIDIA GPU nodes with GPU operator installed
- Access to container registry
- Minimum 8GB GPU memory per pod

### Verify Prerequisites

```bash
# Check kubectl is installed
kubectl version --client

# Check cluster access
kubectl cluster-info

# Check GPU nodes
kubectl get nodes -l nvidia.com/gpu=true

# Verify GPU operator
kubectl get pods -n gpu-operator-resources
```

---

## Quick Start

For experienced users, deploy vLLM with a single command:

```bash
kubectl apply -f kubernetes/vllm-deployment.yaml
kubectl apply -f kubernetes/vllm-service.yaml
```

Then expose the service:
```bash
kubectl port-forward service/vllm-service 8000:8000
```

---

## Step-by-Step Installation

### Step 1: Create Namespace

Create a dedicated namespace for vLLM:

```bash
# Create namespace
kubectl create namespace vllm

# Set as default namespace (optional)
kubectl config set-context --current --namespace=vllm

# Verify
kubectl get namespaces
```

### Step 2: Install NVIDIA GPU Operator (if not installed)

```bash
# Add NVIDIA Helm repository
helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update

# Install GPU operator
helm install --wait --generate-name \
     -n gpu-operator --create-namespace \
     nvidia/gpu-operator

# Verify installation
kubectl get pods -n gpu-operator
```

### Step 3: Create Kubernetes Manifests

Create the following YAML files in a `kubernetes/` directory:

#### 3a. Create Deployment (`vllm-deployment.yaml`)

See [Kubernetes Manifests](#kubernetes-manifests) section below.

#### 3b. Create Service (`vllm-service.yaml`)

See [Kubernetes Manifests](#kubernetes-manifests) section below.

### Step 4: Create ConfigMap (Optional)

For managing vLLM configuration:

```bash
kubectl create configmap vllm-config \
  --from-literal=MODEL_NAME="TinyLlama/TinyLlama-1.1B-Chat-v1.0" \
  --from-literal=MAX_MODEL_LEN="2048" \
  --from-literal=GPU_MEMORY_UTILIZATION="0.9" \
  -n vllm
```

### Step 5: Create PersistentVolume for Model Cache (Recommended)

```yaml
# Save as kubernetes/vllm-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: vllm-model-cache
  namespace: vllm
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 20Gi
  storageClassName: standard
```

Apply:
```bash
kubectl apply -f kubernetes/vllm-pvc.yaml
```

### Step 6: Deploy vLLM

```bash
# Apply deployment
kubectl apply -f kubernetes/vllm-deployment.yaml

# Verify deployment
kubectl get deployments -n vllm

# Check pod status
kubectl get pods -n vllm

# Watch pod startup
kubectl get pods -n vllm -w
```

### Step 7: Create Service

```bash
# Apply service
kubectl apply -f kubernetes/vllm-service.yaml

# Verify service
kubectl get services -n vllm

# Get service details
kubectl describe service vllm-service -n vllm
```

### Step 8: Expose Service

**Option A: Port Forward (Development)**
```bash
kubectl port-forward service/vllm-service 8000:8000 -n vllm
```

**Option B: LoadBalancer (Cloud)**
```bash
# Service will get external IP
kubectl get service vllm-service -n vllm
```

**Option C: Ingress (Production)**
```bash
kubectl apply -f kubernetes/vllm-ingress.yaml
```

### Step 9: Verify Deployment

```bash
# Check logs
kubectl logs -f deployment/vllm-deployment -n vllm

# Test API (if port-forwarded)
curl http://localhost:8000/v1/models

# Test completion
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "prompt": "Hello, world!",
    "max_tokens": 50
  }'
```

---

## Kubernetes Manifests

### Deployment Manifest

```yaml
# kubernetes/vllm-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vllm-deployment
  namespace: vllm
  labels:
    app: vllm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: vllm
  template:
    metadata:
      labels:
        app: vllm
    spec:
      containers:
      - name: vllm
        image: vllm/vllm-openai:latest
        ports:
        - containerPort: 8000
          name: http
        env:
        - name: NVIDIA_VISIBLE_DEVICES
          value: "all"
        - name: CUDA_VISIBLE_DEVICES
          value: "0"
        args:
        - --model
        - TinyLlama/TinyLlama-1.1B-Chat-v1.0
        - --host
        - 0.0.0.0
        - --port
        - "8000"
        - --tensor-parallel-size
        - "1"
        - --gpu-memory-utilization
        - "0.9"
        - --max-model-len
        - "2048"
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
            nvidia.com/gpu: 1
          limits:
            memory: "16Gi"
            cpu: "4"
            nvidia.com/gpu: 1
        volumeMounts:
        - name: cache
          mountPath: /root/.cache/huggingface
        - name: shm
          mountPath: /dev/shm
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 120
          periodSeconds: 30
          timeoutSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 60
          periodSeconds: 10
          timeoutSeconds: 5
      volumes:
      - name: cache
        persistentVolumeClaim:
          claimName: vllm-model-cache
      - name: shm
        emptyDir:
          medium: Memory
          sizeLimit: 16Gi
      nodeSelector:
        nvidia.com/gpu: "true"
      tolerations:
      - key: nvidia.com/gpu
        operator: Exists
        effect: NoSchedule
```

### Service Manifest

```yaml
# kubernetes/vllm-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service
  namespace: vllm
  labels:
    app: vllm
spec:
  type: ClusterIP
  selector:
    app: vllm
  ports:
  - name: http
    port: 8000
    targetPort: 8000
    protocol: TCP
```

### LoadBalancer Service (Cloud)

```yaml
# kubernetes/vllm-service-lb.yaml
apiVersion: v1
kind: Service
metadata:
  name: vllm-service-lb
  namespace: vllm
  labels:
    app: vllm
spec:
  type: LoadBalancer
  selector:
    app: vllm
  ports:
  - name: http
    port: 8000
    targetPort: 8000
    protocol: TCP
```

### Ingress Manifest

```yaml
# kubernetes/vllm-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: vllm-ingress
  namespace: vllm
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
spec:
  ingressClassName: nginx
  rules:
  - host: vllm.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: vllm-service
            port:
              number: 8000
```

### HorizontalPodAutoscaler

```yaml
# kubernetes/vllm-hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: vllm-hpa
  namespace: vllm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: vllm-deployment
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

---

## Deployment Options

### Option 1: Single GPU Deployment (Basic)

```bash
kubectl apply -f kubernetes/vllm-deployment.yaml
kubectl apply -f kubernetes/vllm-service.yaml
```

### Option 2: Multi-GPU Deployment (Tensor Parallelism)

Modify deployment args:
```yaml
args:
- --tensor-parallel-size
- "2"  # Use 2 GPUs
```

Update resources:
```yaml
resources:
  limits:
    nvidia.com/gpu: 2
```

### Option 3: Multiple Replicas (Load Balancing)

```bash
kubectl scale deployment vllm-deployment --replicas=3 -n vllm
```

### Option 4: Helm Chart Deployment

Create `helm-values.yaml`:
```yaml
replicaCount: 1

image:
  repository: vllm/vllm-openai
  tag: latest
  pullPolicy: IfNotPresent

model:
  name: TinyLlama/TinyLlama-1.1B-Chat-v1.0
  maxLength: 2048
  gpuMemoryUtilization: 0.9

resources:
  limits:
    nvidia.com/gpu: 1
  requests:
    memory: 8Gi
    cpu: 2

service:
  type: ClusterIP
  port: 8000

ingress:
  enabled: false
```

---

## Testing and Validation

### Test Script

```bash
#!/bin/bash
# test-vllm-k8s.sh

VLLM_URL="http://localhost:8000"

echo "Testing vLLM on Kubernetes..."

# Test 1: Check models endpoint
echo "Test 1: Models endpoint"
curl -s ${VLLM_URL}/v1/models | jq .

# Test 2: Simple completion
echo -e "\nTest 2: Completion request"
curl -s ${VLLM_URL}/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "prompt": "What is Kubernetes?",
    "max_tokens": 100
  }' | jq .

# Test 3: Health check
echo -e "\nTest 3: Health check"
curl -s ${VLLM_URL}/health

echo -e "\n\nAll tests completed!"
```

### Load Testing

```bash
# Install hey (HTTP load testing tool)
go install github.com/rakyll/hey@latest

# Run load test
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"TinyLlama/TinyLlama-1.1B-Chat-v1.0","prompt":"Hello","max_tokens":50}' \
  http://localhost:8000/v1/completions
```

---

## Scaling and Load Balancing

### Manual Scaling

```bash
# Scale up
kubectl scale deployment vllm-deployment --replicas=3 -n vllm

# Scale down
kubectl scale deployment vllm-deployment --replicas=1 -n vllm

# Check replica status
kubectl get pods -n vllm -l app=vllm
```

### Auto-scaling

```bash
# Apply HPA
kubectl apply -f kubernetes/vllm-hpa.yaml

# Monitor HPA
kubectl get hpa -n vllm -w

# Describe HPA
kubectl describe hpa vllm-hpa -n vllm
```

---

## Monitoring

### View Logs

```bash
# Tail logs
kubectl logs -f deployment/vllm-deployment -n vllm

# View logs from specific pod
kubectl logs -f <pod-name> -n vllm

# View previous logs (if pod crashed)
kubectl logs --previous <pod-name> -n vllm
```

### Resource Usage

```bash
# Pod resource usage
kubectl top pods -n vllm

# Node resource usage
kubectl top nodes

# Detailed pod info
kubectl describe pod <pod-name> -n vllm
```

### GPU Monitoring

```bash
# Exec into pod and check GPU
kubectl exec -it <pod-name> -n vllm -- nvidia-smi

# Watch GPU usage
kubectl exec -it <pod-name> -n vllm -- watch -n 1 nvidia-smi
```

---

## Troubleshooting

### Common Issues

#### 1. Pod Stuck in Pending

```bash
# Check events
kubectl describe pod <pod-name> -n vllm

# Common causes:
# - No GPU nodes available
# - Insufficient resources
# - PVC not bound
```

**Solution:**
```bash
# Check GPU nodes
kubectl get nodes -l nvidia.com/gpu=true

# Check PVC status
kubectl get pvc -n vllm
```

#### 2. Pod CrashLoopBackOff

```bash
# Check logs
kubectl logs <pod-name> -n vllm

# Common causes:
# - OOM (Out of Memory)
# - CUDA errors
# - Model download failed
```

**Solution:**
```bash
# Increase memory limits
# Check GPU driver compatibility
# Ensure internet access for model download
```

#### 3. Model Download Slow

```bash
# Check pod events
kubectl get events -n vllm --sort-by='.lastTimestamp'

# Monitor download progress
kubectl logs -f <pod-name> -n vllm | grep -i download
```

**Solution:**
- Use PVC to cache models
- Pre-download models to persistent volume
- Use faster internet connection

#### 4. Service Not Accessible

```bash
# Check service
kubectl get svc -n vllm

# Check endpoints
kubectl get endpoints -n vllm

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n vllm \
  -- curl vllm-service:8000/v1/models
```

### Debug Commands

```bash
# Get all resources
kubectl get all -n vllm

# Describe deployment
kubectl describe deployment vllm-deployment -n vllm

# Check pod details
kubectl describe pod <pod-name> -n vllm

# Exec into pod
kubectl exec -it <pod-name> -n vllm -- /bin/bash

# Check GPU in pod
kubectl exec <pod-name> -n vllm -- nvidia-smi

# Port forward for debugging
kubectl port-forward <pod-name> 8000:8000 -n vllm
```

---

## Clean Up

```bash
# Delete all resources
kubectl delete -f kubernetes/ -n vllm

# Delete namespace
kubectl delete namespace vllm

# Or delete specific resources
kubectl delete deployment vllm-deployment -n vllm
kubectl delete service vllm-service -n vllm
kubectl delete pvc vllm-model-cache -n vllm
```

---

## Production Considerations

### Security
- Use network policies to restrict traffic
- Enable RBAC
- Use secrets for sensitive configuration
- Scan container images for vulnerabilities

### High Availability
- Deploy multiple replicas
- Use anti-affinity rules
- Configure proper resource requests/limits
- Set up health checks

### Performance
- Use local SSDs for model cache
- Enable GPU time-slicing for better utilization
- Configure appropriate batch sizes
- Monitor and tune based on workload

### Cost Optimization
- Use spot/preemptible instances
- Scale down during off-peak hours
- Share GPU resources when possible
- Monitor and right-size resources

---

## Next Steps

- Monitor performance with Prometheus/Grafana
- Set up CI/CD pipeline for deployments
- Implement blue-green or canary deployments
- Configure backup and disaster recovery
- Explore multi-cluster deployments

---

## Resources

- [vLLM Documentation](https://docs.vllm.ai/)
- [Kubernetes GPU Documentation](https://kubernetes.io/docs/tasks/manage-gpus/scheduling-gpus/)
- [NVIDIA GPU Operator](https://docs.nvidia.com/datacenter/cloud-native/gpu-operator/overview.html)
- [vLLM GitHub](https://github.com/vllm-project/vllm)

---

**Last Updated**: January 7, 2026  
**Tested Versions**: Kubernetes v1.28, vLLM v0.13.0
