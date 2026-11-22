FROM python:3.12-slim

# No generar .pyc y mostrar logs al instante
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Primero las dependencias: aprovecha la cache de capas de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# Usuario sin privilegios
RUN useradd --create-home appuser
USER appuser

EXPOSE 5000

# 1 worker + 4 hilos: las metricas en memoria quedan consistentes
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "app:app"]