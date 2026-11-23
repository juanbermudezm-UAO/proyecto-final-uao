# Proyecto Final – Infraestructura containerizada con Nginx, Prometheus y Grafana

## Descripción

Este proyecto despliega con Docker Compose una infraestructura web con monitoreo. Un servidor Nginx recibe las solicitudes y las reparte, con balanceo de carga, entre tres instancias de un backend en Python que exponen métricas de latencia y solicitudes. Prometheus recolecta esas métricas junto con las de Nginx y las de uso de recursos de cada contenedor, y Grafana las muestra en un dashboard que se carga automáticamente.

Toda la infraestructura se define como código y se levanta con un solo comando, sin pasos manuales. El objetivo es explorar herramientas modernas de administración y supervisión de servicios en un entorno containerizado y reproducible.

## Stack Tecnológico

### Contenedores y orquestación
- Docker y Docker Compose v2.
- Red personalizada `devops-lab-net` y volúmenes `prometheus_data` y `grafana_data`.

### Backend
- Python 3.12 + Flask 3.0.3, servido con Gunicorn 22.0.0 (1 worker y 4 hilos).
- Métricas con `prometheus-client` 0.20.0.

### Proxy y balanceo
- Nginx 1.30.7 con round-robin, reintentos automáticos y `stub_status`.

### Monitoreo
- Prometheus v3.15.0 y Grafana 12.4.15.
- Nginx Prometheus Exporter 1.5.3 y cAdvisor v0.61.1.
- docker-stats-exporter: exportador propio en Python (red y disco por contenedor).

### Pruebas de carga y entorno
- k6 0.56.0, en contenedor o instalado en el host.
- Git y GitHub. Desarrollado en Windows (PowerShell) con Docker Desktop (WSL2).

## Arquitectura del Sistema

![Diagrama de Arquitectura](./docs/arquitectura.png)

### Descripción
- El cliente entra por Nginx (puerto 8080), que reparte las peticiones entre los tres backends.
- Prometheus recoge las métricas de los backends, de Nginx (vía su exporter), de cAdvisor (CPU y memoria) y del exporter propio (red y disco).
- Grafana lee de Prometheus y muestra todo en un dashboard provisionado automáticamente.
- Los servicios comparten la red `devops-lab-net` y los puertos solo se abren en `127.0.0.1`.
- Todas las imágenes usan versión fija (sin `latest`) para que el despliegue sea reproducible.

### Estructura del repositorio

```
proyecto-final-uao/
├── docker-compose.yml
├── backend/                 # app Flask y su Dockerfile
├── docker-stats-exporter/   # exporter propio de red y disco
├── nginx/nginx.conf
├── prometheus/prometheus.yml
├── grafana/                 # datasource y dashboards
├── k6/                      # pruebas de carga
└── docs/
```

## Integrantes del Equipo

- **Juan Esteban Bermudez**
- **Sebastian Cobos**
- **Alan Yesid Basante**
- **Ana Lia Castro**

## Instalación y Ejecución Local

**Requisitos previos:** Docker y Docker Compose v2, Git, y los puertos `8080`, `9090`, `3000`, `8082`, `9113` y `9274` libres.

1. **Clonar el repositorio:**
   ```bash
   git clone https://github.com/juanbermudezm-UAO/proyecto-final-uao.git
   cd proyecto-final-uao
   ```

2. **Levantar toda la infraestructura:**
   ```bash
   docker compose up -d --build
   ```

3. **Verificar los servicios** (los que tienen healthcheck deben quedar en `healthy`):
   ```bash
   docker compose ps
   ```

4. **Abrir las aplicaciones** con las URLs de la tabla siguiente.

5. **Detener la infraestructura:**
   ```bash
   docker compose down      # conserva los datos
   docker compose down -v   # borra también los datos de Prometheus y Grafana
   ```

## URLs de acceso

| Servicio | URL | Notas |
| --- | --- | --- |
| Aplicación (vía Nginx) | http://localhost:8080 | Punto de entrada con balanceo |
| Prometheus | http://localhost:9090 | Targets en `/targets` |
| Grafana | http://localhost:3000 | Sin login (laboratorio); dashboard en la carpeta "Proyecto Final" |
| cAdvisor | http://localhost:8082 | CPU y memoria por contenedor |
| Nginx Exporter | http://localhost:9113/metrics | Métricas de Nginx |
| docker-stats-exporter | http://localhost:9274/metrics | Red y disco por contenedor |

**Endpoints del backend:** `/` (mensaje e `instance`), `/health`, `/work?delay_ms=N` (retardo de 0 a 200 ms) y `/metrics`.

## Verificación

### Balanceo de carga

**Windows PowerShell:**
```powershell
1..9 | ForEach-Object { (Invoke-RestMethod http://localhost:8080/).instance }
```

**Linux / macOS / Git Bash:**
```bash
for i in $(seq 1 9); do curl -s http://localhost:8080/; echo; done
```

Resultado esperado: el campo `instance` rota entre `backend-1`, `backend-2` y `backend-3`, con tres respuestas de cada uno.

### Tolerancia a fallos

```bash
docker compose stop backend-2    # solo responden backend-1 y backend-3, sin errores
docker compose start backend-2   # tras unos segundos vuelve a la rotación
```

Nginx marca un backend como caído tras 1 fallo (`max_fails=1`) durante 5 s (`fail_timeout=5s`) y reintenta la petición en otro (`proxy_next_upstream`).

### Monitoreo

1. En http://localhost:9090/targets los 7 targets deben estar **UP**.
2. En http://localhost:9090/graph prueba `up` o `sum by (instance_id) (rate(backend_http_requests_total{endpoint!="/health"}[1m]))`.
3. En Grafana (http://localhost:3000), carpeta **Proyecto Final**, abre el dashboard **Proyecto Final DevOps | Infraestructura y rendimiento**. Tiene 16 paneles (solicitudes, latencia p50/p95/p99, errores, Nginx, CPU, RAM, red y disco) y se actualiza cada 5 s. El detalle de cada consulta está en el informe.

## Pruebas de carga con k6

Con la infraestructura arriba:

**Windows PowerShell:**
```powershell
.\k6\ejecutar-prueba.ps1
```

**Linux / macOS / Git Bash:**
```bash
bash k6/ejecutar-prueba.sh
```

Con k6 instalado en el host: `k6 run k6/load-test.js`.

La prueba dura unos 90 segundos y ejecuta dos escenarios: `carga_normal` (hasta 10 usuarios virtuales) y `pico_trafico` (hasta 45). Los umbrales son menos del 1 % de fallos y p95 por debajo de 500 ms.

**Resultado de referencia:** 18 136 solicitudes (201,4 req/s), 0 % de fallos y p95 de 84,3 ms.

## Funcionalidades Principales

- Despliegue completo con un solo comando.
- Balanceo round-robin con tolerancia a fallos.
- Identificación de la instancia que atiende cada solicitud.
- Monitoreo de aplicación, Nginx y CPU, memoria, red y disco por contenedor.
- Dashboard de Grafana provisionado automáticamente y datos persistentes en volúmenes.
- Pruebas de carga con escenarios de carga normal y de pico.

## Solución de problemas

- **Puerto ocupado:** libéralo o cambia el mapeo en `docker-compose.yml`.
- **Un servicio no queda `healthy`:** revisa `docker compose logs <servicio>`.
- **Prometheus sin datos al inicio:** espera unos segundos (recolecta cada 5 s).
- **Paneles de CPU o memoria vacíos en Windows/macOS:** en Docker Desktop cAdvisor puede no ver algunas métricas del host.
- **Error en los scripts de k6:** confirma que la infraestructura está arriba y que existe la red `proyecto-final-devops_devops-lab-net` (`docker network ls`).
