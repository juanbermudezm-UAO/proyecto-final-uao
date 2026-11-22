import os
import socket
import time

from flask import Flask, Response, g, jsonify, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

app = Flask(__name__)

INSTANCE_ID = os.getenv("INSTANCE_ID", "desconocida")
HOSTNAME = socket.gethostname()

# Contador de solicitudes: permite calcular req/s con rate()
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total de solicitudes HTTP recibidas por el backend",
    ["instance_id", "method", "endpoint", "status"],
)

# Histograma de latencia: permite calcular p50/p95/p99 con histogram_quantile()
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "Latencia de las solicitudes HTTP en segundos",
    ["instance_id", "method", "endpoint"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
)


@app.before_request
def start_timer():
    g.start_time = time.perf_counter()


@app.after_request
def record_metrics(response):
    # No medimos /metrics para no contaminar las estadisticas
    if request.path == "/metrics":
        return response

    # Usamos el patron de la ruta (no la URL real) para limitar la cardinalidad
    endpoint = request.url_rule.rule if request.url_rule else "no_encontrada"
    elapsed = time.perf_counter() - g.start_time

    REQUEST_COUNT.labels(
        instance_id=INSTANCE_ID,
        method=request.method,
        endpoint=endpoint,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.labels(
        instance_id=INSTANCE_ID,
        method=request.method,
        endpoint=endpoint,
    ).observe(elapsed)

    # Encabezado para ver desde el cliente que instancia respondio
    response.headers["X-Instance-ID"] = INSTANCE_ID
    return response


@app.route("/")
def index():
    return jsonify(
        mensaje="Hola desde el backend",
        instancia=INSTANCE_ID,
        contenedor=HOSTNAME,
    )


@app.route("/health")
def health():
    return jsonify(estado="ok", instancia=INSTANCE_ID)


@app.route("/slow")
def slow():
    # Simula una operacion lenta (200 ms) para ver cambios en la latencia
    time.sleep(0.2)
    return jsonify(mensaje="Respuesta lenta", instancia=INSTANCE_ID)


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)