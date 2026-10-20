# Test runner image: the services' Python and libraries (paho-mqtt) plus pytest and a Mosquitto
# broker for the end-to-end tests. The repo is bind-mounted at /w, so tests always run against the
# working tree (no rebuild needed after a code change). Run with:  docker compose run --rm tests
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN apt-get update && apt-get install -y --no-install-recommends mosquitto && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /tmp/requirements.txt
COPY tests/requirements.txt /tmp/test-requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/test-requirements.txt

WORKDIR /w
CMD ["python", "-m", "pytest"]
