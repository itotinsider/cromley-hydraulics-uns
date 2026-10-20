# Dam simulator: reservoir, spillway, bottom outlet, three units, plant controller. Publishes the customer tree.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/*.py common/
COPY damsim/*.py ./


EXPOSE 8123
USER nobody
CMD ["python", "main.py"]
