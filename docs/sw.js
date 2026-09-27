/* Service worker del mapa de riesgos.
 * Guarda solo archivos del propio sitio (páginas, estilos, código y capas).
 * Estrategia: primero la red, y si no hay conexión, la copia guardada; así
 * una actualización de datos se ve apenas hay red.
 * Las teselas del mapa de fondo (tile.openstreetmap.org) no se interceptan
 * ni se guardan: la política de uso de OpenStreetMap prohíbe el uso sin
 * conexión y la descarga anticipada.
 */
const CACHE = "mapa-riesgos-v6";
const BASE = [
  "./",
  "index.html",
  "metodologia.html",
  "css/estilo.css",
  "js/mapa.js",
  "js/metodologia.js",
  "vendor/leaflet/leaflet.js",
  "vendor/leaflet/leaflet.css",
  "vendor/source-serif-4/source-serif-4-latin-600-normal.woff2",
  "datos/capas.json",
  "datos/limite.geojson",
  "manifest.webmanifest",
  "iconos/icono.svg",
  "iconos/icono-192.png",
];

self.addEventListener("install", (evento) => {
  evento.waitUntil(caches.open(CACHE).then((c) => c.addAll(BASE)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches.keys()
      .then((claves) => Promise.all(claves.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (evento) => {
  const url = new URL(evento.request.url);
  if (evento.request.method !== "GET" || url.origin !== self.location.origin) return;
  evento.respondWith(
    fetch(evento.request)
      .then((respuesta) => {
        if (respuesta.ok) {
          const copia = respuesta.clone();
          caches.open(CACHE).then((c) => c.put(evento.request, copia));
        }
        return respuesta;
      })
      .catch(() => caches.match(evento.request).then((r) => r || caches.match("index.html")))
  );
});
