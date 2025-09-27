FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
COPY ./requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY ./etl_sim.py ./
EXPOSE 8000 8080
ENTRYPOINT ["python", "etl_sim.py"]
