# CH turbine PLCs: one per turbine, publishing the CH asset tree (process values + raw waveforms).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY common/*.py common/
COPY chplc/*.py ./


EXPOSE 8125
USER nobody
CMD ["python", "main.py"]
