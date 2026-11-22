FROM python:3.12.16-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY exporter.py .

EXPOSE 9274

HEALTHCHECK --interval=20s --timeout=5s \
  --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:9274/health', timeout=3)"

CMD ["python", "-u", "exporter.py"]
