from pathlib import Path
import json

ruta = Path('grafana/dashboards/devops-infra.json')
ruta.parent.mkdir(parents=True, exist_ok=True)
if ruta.exists() and ruta.stat().st_size > 0:
    raise SystemExit('El dashboard ya tiene contenido: haz una copia y revisalo antes de sustituirlo.')

ds = {'type': 'prometheus', 'uid': 'prometheus'}
paneles = []

def agregar(tipo, titulo, x, y, consultas, unidad='short', ancho=12, alto=8):
    objetivos = []
    for indice, (promql, leyenda) in enumerate(consultas):
        objetivos.append({
            'datasource': ds,
            'expr': promql,
            'refId': chr(65 + indice),
            'legendFormat': leyenda,
            'editorMode': 'code',
            'instant': tipo != 'timeseries',
            'range': tipo == 'timeseries',
        })
    opciones = {
        'timeseries': {
            'legend': {'displayMode': 'list', 'placement': 'bottom', 'calcs': []},
            'tooltip': {'mode': 'multi', 'sort': 'none'},
        },
        'stat': {
            'reduceOptions': {'calcs': ['lastNotNull'], 'fields': '', 'values': False},
            'orientation': 'auto', 'textMode': 'auto', 'colorMode': 'value',
            'graphMode': 'area',
        },
        'bargauge': {
            'reduceOptions': {'calcs': ['lastNotNull'], 'fields': '', 'values': False},
            'orientation': 'horizontal', 'displayMode': 'basic', 'showUnfilled': True,
        },
    }
    paneles.append({
        'id': len(paneles) + 1,
        'title': titulo, 'type': tipo,
        'datasource': ds, 'targets': objetivos,
        'gridPos': {'x': x, 'y': y, 'w': ancho, 'h': alto},
        'fieldConfig': {'defaults': {'unit': unidad, 'color': {'mode': 'palette-classic'}}, 'overrides': []},
        'options': opciones[tipo],
    })

agregar('stat', 'Targets UP', 0, 0, [('sum(up)', 'Targets')], ancho=6, alto=4)
agregar('stat', 'Solicitudes por segundo', 6, 0, [
    ('sum(rate(backend_http_requests_total{endpoint!="/health"}[1m])) or vector(0)', 'RPS')
], 'reqps', 6, 4)
agregar('stat', 'Errores HTTP en 5 min', 12, 0, [
    ('sum(increase(backend_http_requests_total{status_code=~"4..|5..",endpoint!="/health"}[5m])) or vector(0)', 'Errores')
], 'short', 6, 4)
agregar('stat', 'Nginx disponible', 18, 0, [('nginx_up', 'Nginx')], ancho=6, alto=4)

agregar('timeseries', 'RPS por backend', 0, 4, [
    ('sum by (instance_id) (rate(backend_http_requests_total{endpoint!="/health"}[1m]))', '{{instance_id}}')
], 'reqps')
agregar('timeseries', 'Latencia HTTP — p50, p95 y p99', 12, 4, [
    (f'histogram_quantile({q}, sum by (le) (rate(backend_http_request_duration_seconds_bucket{{endpoint!="/health"}}[5m])))', nombre)
    for q, nombre in [(0.50, 'p50'), (0.95, 'p95'), (0.99, 'p99')]
], 's')

agregar('timeseries', 'Solicitudes por código HTTP', 0, 12, [
    ('sum by (status_code) (rate(backend_http_requests_total{endpoint!="/health"}[1m]))', 'HTTP {{status_code}}')
], 'reqps')
agregar('bargauge', 'Distribución entre backends — últimos 5 min', 12, 12, [
    ('sum by (instance_id) (increase(backend_http_requests_total{endpoint!="/health"}[5m]))', '{{instance_id}}')
])

agregar('timeseries', 'Conexiones Nginx', 0, 20, [
    ('nginx_connections_active', 'Activas'),
    ('nginx_connections_reading', 'Leyendo'),
    ('nginx_connections_writing', 'Escribiendo'),
    ('nginx_connections_waiting', 'En espera'),
])
agregar('timeseries', 'Estado de los tres backends', 12, 20, [
    ('up{job="backends"}', '{{instance}}')
])

agregar('timeseries', 'CPU por contenedor — % de un núcleo', 0, 28, [
    ('label_replace(sum by (id) (rate(container_cpu_usage_seconds_total{job="cadvisor",id=~"/docker/[0-9a-f]+"}[1m])) * 100, "cid", "$1", "id", "/docker/([0-9a-f]{12}).*")', '{{cid}}')
], 'percent')
agregar('timeseries', 'RAM por contenedor', 12, 28, [
    ('label_replace(container_memory_working_set_bytes{job="cadvisor",id=~"/docker/[0-9a-f]+"}, "cid", "$1", "id", "/docker/([0-9a-f]{12}).*")', '{{cid}}')
], 'bytes')

agregar('timeseries', 'Red recibida por servicio', 0, 36, [
    ('sum by (service) (rate(docker_stats_network_receive_bytes_total{job="docker-stats"}[1m]))', '{{service}}')
], 'Bps')
agregar('timeseries', 'Red enviada por servicio', 12, 36, [
    ('sum by (service) (rate(docker_stats_network_transmit_bytes_total{job="docker-stats"}[1m]))', '{{service}}')
], 'Bps')

agregar('timeseries', 'Disco — lectura (Block I/O)', 0, 44, [
    ('sum by (service) (rate(docker_stats_block_read_bytes_total{job="docker-stats"}[5m]))', '{{service}}')
], 'Bps')
agregar('timeseries', 'Disco — escritura (Block I/O)', 12, 44, [
    ('sum by (service) (rate(docker_stats_block_write_bytes_total{job="docker-stats"}[5m]))', '{{service}}')
], 'Bps')

dashboard = {
    'id': None,
    'uid': 'devops-infra',
    'title': 'Proyecto Final DevOps | Infraestructura y rendimiento',
    'tags': ['devops', 'docker', 'nginx', 'prometheus', 'grafana'],
    'timezone': 'browser',
    'schemaVersion': 39,
    'version': 1,
    'refresh': '5s',
    'time': {'from': 'now-30m', 'to': 'now'},
    'timepicker': {},
    'editable': False,
    'panels': paneles,
    'annotations': {'list': []},
}
ruta.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'Dashboard creado: {ruta} ({len(paneles)} paneles)')
