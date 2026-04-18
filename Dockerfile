FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends gosu \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && rm -rf /var/lib/apt/lists/*

COPY . /app

RUN addgroup --system bot \
    && adduser --system --ingroup bot bot \
    && mkdir -p /app/data /app/logs /app/exports /app/storage \
    && chmod +x /app/docker/entrypoint.sh

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["python", "bot.py"]
