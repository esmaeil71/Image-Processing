FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
EXPOSE 8000

# Bind mount ./backend:/app overwrites image /app; host files may lack +x on this script.
# Invoking via `sh` avoids "permission denied" on ENTRYPOINT.
ENTRYPOINT ["sh", "/app/scripts/docker_entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
