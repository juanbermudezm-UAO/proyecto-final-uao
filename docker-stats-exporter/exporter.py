import concurrent.futures
import http.client
import json
import os
import socket

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

SOCKET = "/var/run/docker.sock"
PROJECT = os.environ.get(
    "COMPOSE_PROJECT", "proyecto-final-devops"
)
API = "/v1.44"

METRICS = (
    ("docker_stats_network_receive_bytes_total",
     "Bytes received by a Docker container"),
    ("docker_stats_network_transmit_bytes_total",
     "Bytes transmitted by a Docker container"),
    ("docker_stats_block_read_bytes_total",
     "Bytes read from block devices by a Docker container"),
    ("docker_stats_block_write_bytes_total",
     "Bytes written to block devices by a Docker container"),
)


class UnixHTTPConnection(http.client.HTTPConnection):
    def connect(self):
        self.sock = socket.socket(
            socket.AF_UNIX, socket.SOCK_STREAM
        )
        self.sock.settimeout(self.timeout)
        self.sock.connect(SOCKET)


def docker_get(path):
    connection = UnixHTTPConnection(
        "localhost", timeout=4
    )
    try:
        connection.request("GET", API + path)
        response = connection.getresponse()
        payload = response.read()

        if response.status != 200:
            raise RuntimeError(
                f"Docker API HTTP {response.status}: "
                f"{payload[:250]!r}"
            )

        return json.loads(payload)
    finally:
        connection.close()


def escape_label(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace("\n", "\\n")
        .replace('"', '\\"')
    )


def container_sample(container):
    container_id = container["Id"]

    stats = docker_get(
        f"/containers/{container_id}/stats"
        "?stream=false&one-shot=true"
    )

    labels = container.get("Labels") or {}
    name = (
        container.get("Names") or [container_id[:12]]
    )[0].lstrip("/")

    service = labels.get(
        "com.docker.compose.service", "unknown"
    )

    samples = {}

    interfaces = stats.get("networks") or {}

    if interfaces:
        samples["docker_stats_network_receive_bytes_total"] = sum(
            int(v.get("rx_bytes", 0))
            for v in interfaces.values()
        )
        samples["docker_stats_network_transmit_bytes_total"] = sum(
            int(v.get("tx_bytes", 0))
            for v in interfaces.values()
        )

    blkio = (
        (stats.get("blkio_stats") or {})
        .get("io_service_bytes_recursive")
    )

    if blkio is not None:
        samples["docker_stats_block_read_bytes_total"] = sum(
            int(x.get("value", 0))
            for x in blkio
            if x.get("op", "").lower() == "read"
        )
        samples["docker_stats_block_write_bytes_total"] = sum(
            int(x.get("value", 0))
            for x in blkio
            if x.get("op", "").lower() == "write"
        )

    return name, service, samples


def collect():
    containers = [
        c for c in docker_get("/containers/json")
        if (c.get("Labels") or {}).get(
            "com.docker.compose.project"
        ) == PROJECT
    ]

    with concurrent.futures.ThreadPoolExecutor(
        max_workers=8
    ) as pool:
        results = list(
            pool.map(container_sample, containers)
        )

    lines = []

    for metric, help_text in METRICS:
        lines.extend((
            f"# HELP {metric} {help_text}",
            f"# TYPE {metric} counter",
        ))

        for name, service, samples in results:
            if metric not in samples:
                continue

            labels = (
                f'project="{escape_label(PROJECT)}",'
                f'service="{escape_label(service)}",'
                f'container="{escape_label(name)}"'
            )

            lines.append(
                f"{metric}{{{labels}}} {samples[metric]}"
            )

    lines.extend((
        "# HELP docker_stats_exporter_containers "
        "Number of Docker Compose containers queried",
        "# TYPE docker_stats_exporter_containers gauge",
        f"docker_stats_exporter_containers {len(results)}",
    ))

    return "\n".join(lines) + "\n"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            body = b"ok\n"
            status = 200
            content_type = "text/plain"

        elif self.path == "/metrics":
            try:
                body = collect().encode()
                status = 200
            except Exception as exc:
                print(
                    f"Scrape failed: {exc}",
                    flush=True
                )
                body = (
                    f"Scrape failed: {exc}\n"
                ).encode()
                status = 503

            content_type = (
                "text/plain; version=0.0.4; "
                "charset=utf-8"
            )
        else:
            body = b"Not found\n"
            status = 404
            content_type = "text/plain"

        self.send_response(status)
        self.send_header(
            "Content-Type", content_type
        )
        self.send_header(
            "Content-Length", str(len(body))
        )
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(
        ("0.0.0.0", 9274), Handler
    ).serve_forever()
