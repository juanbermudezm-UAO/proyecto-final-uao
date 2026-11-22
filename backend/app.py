import os
import time

from flask import Flask, Response, jsonify, g, request
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    generate_latest,
)

app = Flask(__name__)

INSTANCE_ID = os.getenv("BACKEND_ID", "backend-local")

# Contador de solicitudes HTTP.
HTTP_REQUESTS = Counter(
    "backend_http_requests",
    "Total de solicitudes HTTP recibidas",
    ["instance_id", "method", "endpoint", "status_code"],
)

# Histograma de duracion de solicitudes.
HTTP_LATENCY = Histogram(
    "backend_http_request_duration_seconds",
    "Duracion de solicitudes HTTP en segundos",
    ["instance_id", "method", "endpoint"],
    buckets=(
        0.005,
        0.01,
        0.025,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
        10.0,
        float("inf"),
    ),
)


@app.before_request
def start_timer():
    g.start_time = time.perf_counter()


@app.after_request
def record_metrics(response):
    response.headers["X-Backend-Instance"] = INSTANCE_ID

    # Evitar contabilizar las consultas de Prometheus.
    if request.path == "/metrics":
        return response

    duration = time.perf_counter() - g.start_time

    endpoint = (
        request.url_rule.rule
        if request.url_rule
        else "unmatched"
    )

    HTTP_REQUESTS.labels(
        instance_id=INSTANCE_ID,
        method=request.method,
        endpoint=endpoint,
        status_code=str(response.status_code),
    ).inc()

    HTTP_LATENCY.labels(
        instance_id=INSTANCE_ID,
        method=request.method,
        endpoint=endpoint,
    ).observe(duration)

    return response


@app.get("/")
def index():
    return jsonify({
        "message": "Proyecto Final - Backend Python",
        "instance": INSTANCE_ID,
        "status": "ok",
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "healthy",
        "instance": INSTANCE_ID,
    })


@app.get("/work")
def work():
    try:
        delay_ms = int(request.args.get("delay_ms", "20"))
    except ValueError:
        return jsonify({
            "error": "delay_ms debe ser un numero entero"
        }), 400

    if not 0 <= delay_ms <= 200:
        return jsonify({
            "error": "delay_ms debe estar entre 0 y 200"
        }), 400

    time.sleep(delay_ms / 1000)

    return jsonify({
        "message": "Trabajo simulado completado",
        "instance": INSTANCE_ID,
        "delay_ms": delay_ms,
        "status": "ok",
    })


@app.get("/metrics")
def metrics():
    return Response(
        generate_latest(),
        mimetype=CONTENT_TYPE_LATEST,
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=8000,
        debug=False,
    )
