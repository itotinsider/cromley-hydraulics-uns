# Instructor station: hidden fault scenarios, talks to the simulators over HTTP (never MQTT).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/*.py common/
COPY instructor/*.py ./
COPY instructor/web ./web

EXPOSE 8121
USER nobody
CMD ["python", "main.py"]
