# KubeHealer Cluster Configuration

This directory contains cluster setup and infrastructure configuration files for the KubeHealer system.

## Files Overview

### 🐳 kind-kubehealer-cluster.yaml
Kind (Kubernetes in Docker) cluster configuration that defines:
- **Cluster Name**: `kubehealer`
- **Node Configuration**: 1 control-plane + 3 worker nodes
- **Port Mappings**: 
  - Port 30080 (TCP) - For application access
  - Port 30081 (TCP) - For monitoring/dashboard access

**Usage:**
```bash
# Create the Kind cluster
kind create cluster --config=kind-kubehealer-cluster.yaml

# Verify cluster is running
kubectl cluster-info --context kind-kubehealer
```

### 📦 sc.yaml
Storage Class configuration for persistent storage requirements. Defines storage policies and provisioning for:
- Application data persistence
- Monitoring data storage
- ML model artifacts

### 🗄️ values-minio.yaml
MinIO configuration values for object storage. MinIO provides:
- S3-compatible object storage
- Data persistence for ML models
- Artifact storage for the ETL pipeline
- Backup and recovery capabilities

**Features:**
- High-availability configuration
- Persistent volume claims
- Access policies and authentication
- Integration with Kubernetes secrets

## Quick Setup

1. **Create the cluster:**
   ```bash
   kind create cluster --config=kind-kubehealer-cluster.yaml
   ```

2. **Apply storage configuration:**
   ```bash
   kubectl apply -f sc.yaml
   ```

3. **Install MinIO (if using Helm):**
   ```bash
   helm install minio minio/minio -f values-minio.yaml
   ```

## Cluster Architecture

```
┌─────────────────┐
│  Control Plane  │
│    (1 node)     │
└─────────────────┘
         │
    ┌────┴────┐
    │         │
┌───▼──┐ ┌───▼──┐ ┌───▼──┐
│Worker│ │Worker│ │Worker│
│  #1  │ │  #2  │ │  #3  │
└──────┘ └──────┘ └──────┘
```

## Port Mappings

| Port  | Purpose                | Access                    |
|-------|------------------------|---------------------------|
| 30080 | Application Services   | http://localhost:30080    |
| 30081 | Monitoring Dashboard   | http://localhost:30081    |

## Prerequisites

- Docker Desktop or Docker Engine
- Kind CLI tool
- kubectl CLI tool
- Helm (for MinIO installation)

## Troubleshooting

**Cluster creation fails:**
```bash
# Check Docker is running
docker ps

# Delete existing cluster if needed
kind delete cluster --name kubehealer
```

**Storage issues:**
```bash
# Verify storage class
kubectl get storageclass

# Check persistent volumes
kubectl get pv,pvc
```
