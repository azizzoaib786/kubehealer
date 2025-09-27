# KubeHealer Monitoring Configuration

This directory contains monitoring and observability configurations for the KubeHealer system. It includes Prometheus monitoring, Grafana dashboards, and service monitoring configurations.

## Files Overview

### 📊 Service Monitors

#### etl-sim-servicemonitor.yaml
Prometheus ServiceMonitor for ETL Simulator:
- Scrapes metrics from ETL simulator endpoints
- Monitors failure rates, response times, and anomaly flags
- Collects weather simulation data and Z-scores
- Configurable scraping intervals and paths

#### ml-scorer-servicemonitor.yaml
Prometheus ServiceMonitor for ML Scorer:
- Monitors anomaly scoring metrics
- Tracks probability and fraction thresholds
- Collects model performance indicators
- Real-time scoring accuracy metrics

#### rl-agent-servicemonitor.yaml
Prometheus ServiceMonitor for RL Agent:
- Monitors agent decision-making metrics
- Tracks healing actions and success rates
- Collects learning progress indicators
- Agent health and performance metrics

### 📈 Prometheus Configuration

#### prometheus-values-base.yaml
Base Prometheus configuration with:
- Core monitoring setup
- Alert manager configuration
- Storage and retention policies
- Service discovery rules

#### prometheus-values-renderer.yaml
Extended Prometheus configuration for:
- Advanced rendering capabilities
- Custom dashboards integration
- Enhanced visualization support
- Performance optimization settings

### 📋 Grafana Dashboards

#### grafana-dashboard-weather-exclude-rl.json
Comprehensive Grafana dashboard featuring:
- **Weather Simulation Metrics**: Temperature trends, Z-scores, anomaly detection
- **ETL Performance**: Success/failure rates, response times, throughput
- **ML Scoring**: Anomaly scores, threshold breaches, model accuracy
- **System Health**: Resource utilization, pod status, error rates

**Dashboard Sections:**
1. **Overview Panel**: System-wide health indicators
2. **ETL Metrics**: Detailed ETL simulator performance
3. **Weather Data**: Temperature simulations and anomaly triggers
4. **ML Scoring**: Real-time anomaly detection results
5. **Alerts**: Active alerts and threshold breaches

## Monitoring Stack Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Applications  │───▶│    Prometheus    │───▶│     Grafana     │
│                 │    │                  │    │                 │
│ • etl-sim       │    │ • Metrics Store  │    │ • Dashboards    │
│ • ml-scorer     │    │ • Alert Manager  │    │ • Visualization │
│ • rl-agent      │    │ • Service Disc   │    │ • Alerting      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Metrics Collection

### ETL Simulator Metrics
- `etl_requests_total`: Total HTTP requests
- `etl_request_duration_seconds`: Request duration histogram
- `etl_failure_rate`: Current failure rate
- `etl_anomaly_flag`: Binary anomaly indicator
- `weather_temperature`: Simulated temperature readings
- `weather_temperature_zscore`: Temperature Z-score values

### ML Scorer Metrics
- `ml_anomaly_score`: Real-time anomaly scores
- `ml_threshold_breaches`: Threshold violation counts
- `ml_model_accuracy`: Model prediction accuracy
- `ml_scoring_duration`: Scoring operation duration

### RL Agent Metrics
- `rl_actions_total`: Total actions taken by agent
- `rl_healing_success_rate`: Success rate of healing actions
- `rl_decision_latency`: Time to make decisions
- `rl_learning_progress`: Learning algorithm progress

## Installation

### Install Prometheus Stack
```bash
# Add Prometheus community Helm repository
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus with base configuration
helm install prometheus prometheus-community/kube-prometheus-stack \
  -f prometheus-values-base.yaml \
  -n monitoring --create-namespace

# Install enhanced renderer (optional)
helm upgrade prometheus prometheus-community/kube-prometheus-stack \
  -f prometheus-values-renderer.yaml \
  -n monitoring
```

### Apply Service Monitors
```bash
# Deploy all service monitors
kubectl apply -f etl-sim-servicemonitor.yaml
kubectl apply -f ml-scorer-servicemonitor.yaml  
kubectl apply -f rl-agent-servicemonitor.yaml
```

### Import Grafana Dashboard
```bash
# Copy dashboard JSON to Grafana
kubectl create configmap weather-dashboard \
  --from-file=grafana-dashboard-weather-exclude-rl.json \
  -n monitoring

# Or import via Grafana UI at http://localhost:3000
```

## Configuration

### Scraping Configuration
Service monitors are configured with:
- **Scrape Interval**: 15 seconds (configurable)
- **Metrics Path**: `/metrics` (Prometheus standard)
- **Port**: Application-specific metrics ports
- **Labels**: Automatic labeling for service discovery

### Alert Rules
Configure alerting for:
- High failure rates in ETL simulator
- Anomaly score threshold breaches
- Agent healing action failures
- Resource utilization limits

### Retention and Storage
- **Metrics Retention**: 15 days (configurable)
- **Storage Size**: 10GB (expandable)
- **Backup Policy**: Daily snapshots
- **Compression**: Enabled for storage efficiency

## Dashboard Features

### Real-time Monitoring
- Live metric updates every 5 seconds
- Interactive time range selection
- Drill-down capabilities for detailed analysis
- Multi-panel correlation views

### Alerting Integration
- Visual alert indicators
- Alert history and acknowledgment
- Integration with PagerDuty/Slack
- Custom notification channels

### Performance Analytics
- Trend analysis over configurable time periods
- Comparison views for before/after scenarios
- Performance regression detection
- Capacity planning insights

## Accessing Monitoring

### Prometheus
```bash
# Port forward to access Prometheus UI
kubectl port-forward svc/prometheus-server 9090:80 -n monitoring

# Access at: http://localhost:9090
```

### Grafana
```bash
# Port forward to access Grafana
kubectl port-forward svc/prometheus-grafana 3000:80 -n monitoring

# Access at: http://localhost:3000
# Default credentials: admin/prom-operator
```

### Alert Manager
```bash
# Port forward to access Alert Manager
kubectl port-forward svc/prometheus-alertmanager 9093:9093 -n monitoring

# Access at: http://localhost:9093
```

## Troubleshooting

### Service Discovery Issues
```bash
# Check service monitor status
kubectl get servicemonitor -n monitoring

# Verify target discovery in Prometheus
# Go to Status > Targets in Prometheus UI
```

### Missing Metrics
```bash
# Check application metrics endpoints
kubectl port-forward svc/etl-sim 8080:8080 -n kubehealer
curl http://localhost:8080/metrics

# Verify service monitor selectors
kubectl describe servicemonitor etl-sim-servicemonitor -n monitoring
```

### Dashboard Import Issues
```bash
# Check Grafana logs
kubectl logs -l app.kubernetes.io/name=grafana -n monitoring

# Verify dashboard ConfigMap
kubectl get configmap -n monitoring | grep dashboard
```

### Performance Issues
```bash
# Check Prometheus storage usage
kubectl exec -it prometheus-server-0 -n monitoring -- df -h

# Monitor scraping performance
# Check Status > Runtime & Build Information in Prometheus UI
```

## Custom Metrics

To add new metrics:

1. **Expose metrics** in your application at `/metrics` endpoint
2. **Create ServiceMonitor** following existing patterns
3. **Update Grafana dashboard** to visualize new metrics
4. **Configure alerts** for threshold monitoring

Example ServiceMonitor template:
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: my-app-servicemonitor
spec:
  selector:
    matchLabels:
      app: my-app
  endpoints:
  - port: metrics
    interval: 15s
    path: /metrics
```
