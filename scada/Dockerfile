# Dam SCADA server + hub page: subscribes the customer tree, publishes Cmd topics.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/*.py common/
COPY scada/*.py ./
COPY scada/web ./web

EXPOSE 8120
USER nobody
CMD ["python", "main.py"]
