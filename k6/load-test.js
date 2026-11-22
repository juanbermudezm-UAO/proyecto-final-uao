import http from 'k6/http';
import { check, sleep } from 'k6';

// ==========================================
// Proyecto final
// Pruebas de carga con k6
// ==========================================

export const options = {
  // Umbrales de calidad del servicio (SLOs)
  thresholds: {
    // Menos del 1% de errores (5xx/4xx)
    http_req_failed: ['rate<0.01'],

    // El 95% de peticiones bajo 500ms
    http_req_duration: ['p(95)<500'],
  },

  scenarios: {
    // ----------------------------------------
    // Escenario 1: Carga normal constante
    // ----------------------------------------
    carga_normal: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '10s', target: 10 }, // Subida a 10 VUs
        { duration: '30s', target: 10 }, // Carga sostenida
        { duration: '10s', target: 0 },  // Descenso ordenado
      ],
      gracefulRampDown: '5s',
      exec: 'testNormal',
    },

    // ----------------------------------------
    // Escenario 2: Pico de trafico (Spike)
    // ----------------------------------------
    pico_trafico: {
      executor: 'ramping-vus',
      startTime: '55s', // Inicia al culminar carga normal
      startVUs: 0,
      stages: [
        { duration: '5s', target: 45 },  // Subida rapida a 45 VUs
        { duration: '20s', target: 45 }, // Carga maxima
        { duration: '10s', target: 0 },  // Descenso rapido
      ],
      gracefulRampDown: '5s',
      exec: 'testSpike',
    },
  },
};

// URL del proxy Nginx
const BASE_URL = __ENV.TARGET_URL || 'http://localhost:8080';

// --------------------------------------------
// Logica para Escenario 1: Carga Normal
// --------------------------------------------
export function testNormal() {
  // Peticion al endpoint raiz (/)
  const resIndex = http.get(`${BASE_URL}/`, {
    tags: { name: 'GET_Root' },
  });

  check(resIndex, {
    'Normal: status 200': (r) => r.status === 200,
    'Normal: tiene instance_id': (r) => r.json('instance') !== undefined,
  });

  // Peticion al endpoint /work (15ms retardo)
  const resWork = http.get(`${BASE_URL}/work?delay_ms=15`, {
    tags: { name: 'GET_Work' },
  });

  check(resWork, {
    'Normal: /work status 200': (r) => r.status === 200,
    'Normal: retardo procesado': (r) => r.json('delay_ms') === 15,
  });

  // Pausa entre peticiones (100ms)
  sleep(0.1);
}

// --------------------------------------------
// Logica para Escenario 2: Pico de Trafico
// --------------------------------------------
export function testSpike() {
  // Peticion intensiva con retardo de 30ms
  const res = http.get(`${BASE_URL}/work?delay_ms=30`, {
    tags: { name: 'GET_Work_Spike' },
  });

  check(res, {
    'Spike: status 200': (r) => r.status === 200,
    'Spike: header upstream ok': (r) => r.headers['X-Upstream-Addr'] !== undefined,
  });

  // Pausa minima para concurrencia (50ms)
  sleep(0.05);
}

// Funcion por defecto para compatibilidad
export default function () {
  testNormal();
}
