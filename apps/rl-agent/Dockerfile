FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir kubernetes requests numpy prometheus-client

COPY rl_agent.py .

ENV PROM_URL="http://prometheus-operated:9090" \
    TARGET_NAMESPACE="kubehealer" \
    TARGET_DEPLOYMENT="etl-sim" \
    P95_SLO="2.0" FAIL_SLO="0.01" SLOW_SLO="0.02" \
    MIN_REPLICAS="1" MAX_REPLICAS="4" \
    TICK_SECS="30" METRICS_PORT="8000" COOLDOWN_SECS="30"

EXPOSE 8000
ENTRYPOINT ["python", "rl_agent.py"]
