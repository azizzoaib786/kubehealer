FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir minio ujson scikit-learn prometheus-client

WORKDIR /app

COPY ml_scorer.py .

EXPOSE 9105

ENTRYPOINT ["python","ml_scorer.py"]
