# 🔄 KubeHealer

[![MIT License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.28+-blue.svg)](https://kubernetes.io/)
[![Docker](https://img.shields.io/badge/Docker-20.10+-blue.svg)](https://www.docker.com/)
[![GitHub Issues](https://img.shields.io/github/issues/azizzoaib786/kubehealer)](https://github.com/azizzoaib786/kubehealer/issues)
[![GitHub Stars](https://img.shields.io/github/stars/azizzoaib786/kubehealer)](https://github.com/azizzoaib786/kubehealer/stargazers)
[![GitHub Forks](https://img.shields.io/github/forks/azizzoaib786/kubehealer)](https://github.com/azizzoaib786/kubehealer/network)

> **A Kubernetes-based Self-Healing System Demonstration Platform**

KubeHealer is a comprehensive demonstration platform that showcases autonomous system healing in Kubernetes environments through the integration of ETL simulation, machine learning, and reinforcement learning. It provides a complete observable system where failures can be artificially induced and automatically remediated.

🔗 **Repository**: [https://github.com/azizzoaib786/kubehealer](https://github.com/azizzoaib786/kubehealer)

## 🎯 Overview

KubeHealer demonstrates how modern cloud-native applications can achieve self-healing capabilities by combining:

- **Synthetic Workloads**: ETL simulator that generates realistic failure scenarios
- **Intelligent Monitoring**: ML-based anomaly detection and scoring
- **Autonomous Remediation**: RL agent that learns and applies healing actions
- **Complete Observability**: Comprehensive monitoring and visualization stack

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KubeHealer System                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
│  │   ETL-SIM   │───▶│  ML-SCORER  │───▶│  RL-AGENT   │          │
│  │             │    │             │    │             │          │
│  │ • Workload  │    │ • Analysis  │    │ • Healing   │          │
│  │ • Failures  │    │ • Scoring   │    │ • Learning  │          │
│  │ • Metrics   │    │ • Alerts    │    │ • Actions   │          │
│  └─────────────┘    └─────────────┘    └─────────────┘          │
│         │                   │                   │               │
│         └───────────────────┼───────────────────┘               │
│                             ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Monitoring Stack                           │    │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │    │
│  │  │ Prometheus  │  │   Grafana   │  │ AlertManager│      │    │
│  │  └─────────────┘  └─────────────┘  └─────────────┘      │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker Desktop or Docker Engine
- [Kind](https://kind.sigs.k8s.io/) (Kubernetes in Docker)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [Helm](https://helm.sh/) (for monitoring stack)

### 1. Create Kubernetes Cluster

```bash
# Create Kind cluster with the provided configuration
kind create cluster --config=cluster/kind-kubehealer-cluster.yaml

# Verify cluster is running
kubectl cluster-info --context kind-kubehealer
```

### 2. Deploy Applications

```bash
# Deploy all applications in correct order
kubectl create namespace kubehealer
kubectl apply -f k8s/ -R
```

### 3. Setup Monitoring (Optional)

```bash
# Install Prometheus stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  -f monitoring/prometheus-values-base.yaml \
  -n monitoring --create-namespace

# Apply service monitors
kubectl apply -f monitoring/ -n monitoring
```

### 4. Access Services

```bash
# Port forward to ETL simulator
kubectl -n kubehealer port-forward svc/etl-sim 8080:8080

# Access Grafana (if monitoring installed)
kubectl -n monitoring port-forward svc/prometheus-grafana 3000:80
```

## 📊 Components

### [`apps/`](./apps/README.md) - Core Applications
- **etl-sim**: ETL simulator with controllable failure injection
- **ml-scorer**: Machine learning anomaly detection and scoring
- **rl-agent**: Reinforcement learning autonomous healing agent

### [`cluster/`](./cluster/README.md) - Infrastructure
- **Kind cluster configuration**: Multi-node Kubernetes setup
- **Storage classes**: Persistent storage configuration  
- **MinIO setup**: S3-compatible object storage

### [`k8s/`](./k8s/README.md) - Kubernetes Manifests
- **Deployments**: Application deployment specifications
- **Services**: Network service configurations
- **RBAC**: Role-based access control for cluster operations

### [`monitoring/`](./monitoring/README.md) - Observability Stack
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards
- **ServiceMonitors**: Application metrics scraping

## 🔧 Testing Scenarios

### Trigger System Failures

```bash
# Port forward to control API
kubectl -n kubehealer port-forward svc/etl-sim 8080:8080

# Induce high failure rate
curl -s -XPOST 'http://127.0.0.1:8080/act/fail_rate?value=0.20'

# Trigger slow responses
curl -s -XPOST 'http://127.0.0.1:8080/act/slow?rate=0.30&ms=1200'

# Reset to healthy state
curl -s -XPOST 'http://127.0.0.1:8080/act/fail_rate?value=0'
curl -s -XPOST 'http://127.0.0.1:8080/act/slow?rate=0&ms=0'
curl -s -XPOST 'http://127.0.0.1:8080/act/anomaly'
```

### Configure ML Scoring Sensitivity

```bash
# Conservative thresholds (fewer alerts)
kubectl -n kubehealer set env deploy/ml-scorer \
  PROB_THRESH=0.99 \
  FRAC_THRESH=1.0

# Aggressive thresholds (more sensitive)
kubectl -n kubehealer set env deploy/ml-scorer \
  PROB_THRESH=0.60 \
  FRAC_THRESH=0.05 \
  MIN_FIT=100
```

### Adjust ETL Anomaly Detection

```bash
# Sensitive anomaly detection
kubectl -n kubehealer set env deploy/etl-sim \
  ANOMALY_FAIL_THRESH=0.02 \
  ANOMALY_SLOW_THRESH=0.05 \
  WEATHER_TEMP_Z_THRESH=2.0 \
  ANOMALY_CLEAR_WINDOWS=10

# Conservative anomaly detection  
kubectl -n kubehealer set env deploy/etl-sim \
  ANOMALY_FAIL_THRESH=0.10 \
  ANOMALY_SLOW_THRESH=0.20 \
  WEATHER_TEMP_Z_THRESH=5.0 \
  ANOMALY_CLEAR_WINDOWS=2
```

## 📈 Key Metrics

### ETL Simulator
- `etl_requests_total`: Total HTTP requests processed
- `etl_request_duration_seconds`: Request latency distribution  
- `etl_failure_rate`: Current failure rate percentage
- `etl_anomaly_flag`: Binary anomaly state indicator
- `weather_temperature_zscore`: Weather anomaly detection

### ML Scorer  
- `ml_anomaly_score`: Real-time anomaly probability scores
- `ml_threshold_breaches`: Count of threshold violations
- `ml_model_accuracy`: Prediction accuracy metrics

### RL Agent
- `rl_actions_total`: Total autonomous actions taken
- `rl_healing_success_rate`: Success rate of healing interventions
- `rl_decision_latency`: Time to decision making

## 🎛️ Control API

The ETL simulator exposes a REST API for runtime control:

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/act/fail_rate` | POST | `value=0.0-1.0` | Set failure rate percentage |
| `/act/slow` | POST | `rate=0.0-1.0&ms=<duration>` | Configure slow responses |
| `/act/anomaly` | POST | None | Toggle anomaly flag state |
| `/metrics` | GET | None | Prometheus metrics endpoint |

## 📊 Dashboards

Access the Grafana dashboard for comprehensive system visualization:

1. **System Overview**: High-level health indicators
2. **ETL Performance**: Request rates, latencies, error rates
3. **Weather Simulation**: Temperature trends and Z-score analysis  
4. **ML Scoring**: Anomaly detection results and thresholds
5. **RL Agent**: Healing actions and learning progress
6. **Infrastructure**: Resource utilization and pod health

## 🔍 Monitoring Access

```bash
# Prometheus (metrics and alerts)
kubectl -n monitoring port-forward svc/prometheus-server 9090:80
# http://localhost:9090

# Grafana (dashboards)  
kubectl -n monitoring port-forward svc/prometheus-grafana 3000:80
# http://localhost:3000 (admin/prom-operator)

# AlertManager (alert routing)
kubectl -n monitoring port-forward svc/prometheus-alertmanager 9093:9093
# http://localhost:9093
```

## 🛠️ Development

### Building Applications

```bash
# Build ETL Simulator
cd apps/etl-sim
docker build -t kubehealer/etl-sim .

# Build ML Scorer  
cd ../ml-scorer
docker build -t kubehealer/ml-scorer .

# Build RL Agent
cd ../rl-agent
docker build -t kubehealer/rl-agent .
```

### Testing Changes

```bash
# Redeploy after changes
kubectl -n kubehealer rollout restart deployment/etl-sim
kubectl -n kubehealer rollout restart deployment/ml-scorer
kubectl -n kubehealer rollout restart deployment/rl-agent

# Check deployment status
kubectl -n kubehealer get pods
kubectl -n kubehealer logs -l app=etl-sim --tail=50
```

## 🚨 Troubleshooting

### Common Issues

**Cluster Creation Fails:**
```bash
# Ensure Docker is running
docker ps

# Delete existing cluster
kind delete cluster --name kubehealer
```

**Pods Not Starting:**
```bash
# Check pod status and events
kubectl -n kubehealer describe pod <pod-name>

# View logs for errors
kubectl -n kubehealer logs <pod-name> --previous
```

**Service Discovery Issues:**
```bash
# Test internal connectivity
kubectl -n kubehealer run test --rm -i --tty --image=busybox -- nslookup etl-sim

# Check service endpoints
kubectl -n kubehealer get endpoints
```

**Metrics Not Appearing:**
```bash
# Verify service monitor configuration
kubectl -n monitoring get servicemonitor

# Test metrics endpoint directly
kubectl -n kubehealer port-forward svc/etl-sim 8080:8080
curl http://localhost:8080/metrics
```

### Cleanup

```bash
# Remove applications
kubectl delete namespace kubehealer

# Remove monitoring (if installed)
kubectl delete namespace monitoring  

# Delete Kind cluster
kind delete cluster --name kubehealer
```

## 🎓 Learning Objectives

This platform demonstrates:

- **Cloud-Native Architecture**: Microservices, containers, Kubernetes
- **Observability**: Metrics, logging, distributed tracing
- **Failure Engineering**: Chaos testing, fault injection
- **Machine Learning Operations**: Real-time ML inference and monitoring
- **Autonomous Systems**: Self-healing, adaptive behavior
- **DevOps Practices**: GitOps, Infrastructure as Code

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

This is an open-source project created for demonstration and educational purposes. All contributions are welcome!

## 🤝 Contributing

We welcome contributions from the community! Please see our [Contributing Guide](CONTRIBUTING.md) for detailed information on how to get started.

**Quick Start for Contributors:**
1. Fork the repository at [https://github.com/azizzoaib786/kubehealer](https://github.com/azizzoaib786/kubehealer)
2. Clone your fork and create a feature branch
3. Make your changes and test thoroughly
4. Submit a pull request

### Areas We Need Help With
- 🐛 Bug fixes and improvements
- 📚 Documentation enhancements  
- 🚀 New failure scenarios and test cases
- 🤖 ML model improvements
- 📊 Additional monitoring and dashboards
- 🔧 Infrastructure and deployment optimizations

### Reporting Issues
Found a bug or have a feature request? Please [open an issue](https://github.com/azizzoaib786/kubehealer/issues) on GitHub.

**Code of Conduct**: Please be respectful and constructive in all interactions. We're here to learn and build something awesome together!

---

**Happy Self-Healing!**
