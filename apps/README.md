# KubeHealer Applications

This directory contains the core applications that make up the KubeHealer system - a Kubernetes-based self-healing demonstration platform that combines ETL simulation, machine learning, and reinforcement learning.

## Applications Overview

### 📊 etl-sim
The ETL simulator is the primary data processing component that:
- Simulates Extract, Transform, Load operations
- Generates metrics and provides control APIs for testing failure scenarios
- Exposes endpoints to artificially trigger failures, slowdowns, and anomalies
- Includes Prometheus metrics for monitoring
- Provides REST API for runtime configuration

**Key Features:**
- Configurable failure rates and response times
- Anomaly detection and flagging
- Weather data simulation with temperature Z-score thresholds
- Sticky flag mechanism for persistent anomaly states

### 🤖 ml-scorer
The machine learning scorer component that:
- Analyzes metrics from the ETL simulator
- Provides anomaly scoring based on configurable thresholds
- Supports probability-based and fraction-based scoring
- Integrates with monitoring stack for real-time analysis

**Key Features:**
- Configurable probability and fraction thresholds
- Minimum fit requirements for scoring
- Real-time anomaly scoring
- Integration with Prometheus metrics

### 🧠 rl-agent
The reinforcement learning agent that:
- Monitors system health and performance
- Makes autonomous decisions for system healing
- Learns from system behavior patterns
- Implements self-healing actions based on ML scorer input

**Key Features:**
- Kubernetes RBAC integration for cluster operations
- Autonomous healing actions
- Learning-based decision making
- Integration with monitoring and alerting

## Building and Running

Each application includes:
- `Dockerfile` for containerization
- Python source code
- Dependencies specification (where applicable)

To build all applications:
```bash
# Build ETL Simulator
cd etl-sim
docker build -t kubehealer/etl-sim .

# Build ML Scorer
cd ../ml-scorer
docker build -t kubehealer/ml-scorer .

# Build RL Agent
cd ../rl-agent
docker build -t kubehealer/rl-agent .
```

## Configuration

Applications can be configured through environment variables. Key configuration options include:

### ETL Simulator
- `ANOMALY_FAIL_THRESH`: Failure rate threshold for anomaly detection
- `ANOMALY_SLOW_THRESH`: Slow response threshold for anomaly detection
- `WEATHER_TEMP_Z_THRESH`: Temperature Z-score threshold
- `ANOMALY_CLEAR_WINDOWS`: Number of windows required to clear anomaly state

### ML Scorer
- `PROB_THRESH`: Probability threshold for anomaly scoring
- `FRAC_THRESH`: Fraction threshold for anomaly detection
- `MIN_FIT`: Minimum data points required for scoring

## API Endpoints

### ETL Simulator Control API
- `POST /act/fail_rate?value=X`: Set failure rate (0.0-1.0)
- `POST /act/slow?rate=X&ms=Y`: Set slow response rate and duration
- `POST /act/anomaly`: Toggle anomaly flag state

## Integration

These applications work together to create a complete self-healing system:
1. **etl-sim** generates workload and exposes failure scenarios
2. **ml-scorer** analyzes patterns and scores anomalies
3. **rl-agent** takes corrective actions based on ML insights

See the main project Guide for complete setup and testing instructions.
