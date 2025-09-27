# KubeHealer Kubernetes Manifests

This directory contains Kubernetes deployment manifests and configurations for all KubeHealer applications. Each application has its own subdirectory with complete deployment specifications.

## Directory Structure

### 📊 etl-sim/
Kubernetes manifests for the ETL Simulator component:
- **etl-sim-deployment.yaml**: Deployment specification with configurable environment variables
- **etl-sim-service.yaml**: Service configuration for internal cluster communication

**Key Features:**
- Configurable failure thresholds and anomaly detection
- REST API endpoints for testing scenarios
- Prometheus metrics integration
- Horizontal pod autoscaling support

### 🤖 ml-scorer/
Kubernetes manifests for the ML Scorer component:
- **ml-scorer-deployment.yaml**: Deployment with ML scoring configuration
- **ml-scorer-service.yaml**: Service for ML scoring API access

**Key Features:**
- Real-time anomaly scoring
- Configurable probability and fraction thresholds
- Integration with ETL simulator metrics
- Scalable deployment configuration

### 🧠 rl-agent/
Kubernetes manifests for the Reinforcement Learning Agent:
- **rl-agent-deployment.yaml**: Main deployment configuration
- **rl-agent-service.yaml**: Service for agent communication
- **rl-agent-sa.yaml**: Service Account for cluster access
- **rl-agent-role.yaml**: RBAC Role definition
- **rl-agent-rb.yaml**: Role Binding for permissions

**Key Features:**
- Complete RBAC setup for cluster operations
- Autonomous healing capabilities
- Learning-based decision making
- Integration with monitoring stack

## Deployment Order

Deploy in the following sequence to ensure proper dependencies:

1. **Deploy ETL Simulator:**
   ```bash
   kubectl apply -f etl-sim/
   ```

2. **Deploy ML Scorer:**
   ```bash
   kubectl apply -f ml-scorer/
   ```

3. **Deploy RL Agent:**
   ```bash
   kubectl apply -f rl-agent/
   ```

## Configuration

### Environment Variables

Each application supports runtime configuration through environment variables:

**ETL Simulator:**
- `ANOMALY_FAIL_THRESH`: Failure rate threshold (default: 0.10)
- `ANOMALY_SLOW_THRESH`: Slow response threshold (default: 0.20)
- `WEATHER_TEMP_Z_THRESH`: Temperature Z-score threshold (default: 5.0)
- `ANOMALY_CLEAR_WINDOWS`: Windows to clear anomaly (default: 2)

**ML Scorer:**
- `PROB_THRESH`: Probability threshold (default: 0.99)
- `FRAC_THRESH`: Fraction threshold (default: 1.0)
- `MIN_FIT`: Minimum fit requirement (default: 100)

### Service Configuration

All services are configured for:
- Internal cluster communication
- Prometheus metrics scraping
- Health check endpoints
- Proper port mappings

## RBAC Configuration

The RL Agent requires specific Kubernetes permissions:
- **Service Account**: `rl-agent-sa` for identity
- **Role**: `rl-agent-role` with cluster operation permissions
- **Role Binding**: `rl-agent-rb` linking SA to Role

Permissions include:
- Pod management (create, delete, update)
- Service discovery and monitoring
- ConfigMap and Secret access
- Event creation for logging

## Networking

### Service Mesh Integration
- Services communicate via internal cluster DNS
- Metrics endpoints exposed for Prometheus scraping
- Load balancing for high availability

### Port Configuration
| Service    | Port | Target Port | Protocol |
|------------|------|-------------|----------|
| etl-sim    | 8080 | 8080       | TCP      |
| ml-scorer  | 8081 | 8081       | TCP      |
| rl-agent   | 8082 | 8082       | TCP      |

## Health Checks

All deployments include:
- **Readiness Probes**: Ensure services are ready to accept traffic
- **Liveness Probes**: Restart unhealthy containers
- **Startup Probes**: Handle slow-starting applications

## Scaling and Resources

### Resource Requests/Limits
Each deployment specifies:
- CPU requests and limits
- Memory requests and limits
- Appropriate resource quotas

### Horizontal Pod Autoscaling
Applications support HPA based on:
- CPU utilization
- Memory usage
- Custom metrics from Prometheus

## Quick Deployment

Deploy all applications:
```bash
# Deploy all at once
kubectl apply -f ./ -R

# Or deploy individually
kubectl apply -f etl-sim/
kubectl apply -f ml-scorer/
kubectl apply -f rl-agent/
```

Verify deployments:
```bash
# Check all pods
kubectl get pods -n kubehealer

# Check services
kubectl get services -n kubehealer

# Check RBAC
kubectl get sa,role,rolebinding -n kubehealer
```

## Troubleshooting

**Pod startup issues:**
```bash
# Check pod logs
kubectl logs -l app=etl-sim -n kubehealer

# Describe pod for events
kubectl describe pod <pod-name> -n kubehealer
```

**RBAC permission errors:**
```bash
# Verify service account
kubectl get sa rl-agent-sa -n kubehealer

# Check role binding
kubectl describe rolebinding rl-agent-rb -n kubehealer
```

**Service connectivity:**
```bash
# Test internal service resolution
kubectl run test-pod --rm -i --tty --image=busybox -- nslookup etl-sim.kubehealer.svc.cluster.local
```
