# CH asset viewer: the machine builder's view of the CH tree.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/*.py common/
COPY chviewer/*.py ./
COPY chviewer/web ./web

EXPOSE 8122
USER nobody
CMD ["python", "main.py"]
