# API Evaluación de Desempeño - Cloud Run
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Cloud Run inyecta PORT (por defecto 8080)
ENV PORT=8080
EXPOSE 8080

# Gunicorn: 1 worker, varios threads (recomendado para Cloud Run)
CMD ["sh", "-c", "gunicorn --bind 0.0.0.0:${PORT} --workers 1 --threads 4 --timeout 120 app:app"]
