FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY . /app

RUN addgroup --system bot && adduser --system --ingroup bot bot \
    && mkdir -p /app/data /app/logs /app/exports /app/storage \
    && chown -R bot:bot /app

USER bot

CMD ["python", "bot.py"]
