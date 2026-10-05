/* Service worker del mapa para la gestión del riesgo.
 * Guarda solo archivos del propio sitio (páginas, estilos, código y capas).
 * Estrategia: primero la red (revalidando siempre con el servidor), y si no
 * hay conexión, la copia guardada; así una actualización se ve apenas hay red.
 * Las teselas del mapa de fondo (tile.openstreetmap.org) no se interceptan
 * ni se guardan: la política de uso de OpenStreetMap prohíbe el uso sin
 * conexión y la descarga anticipada.
 */
const CACHE = "mapa-riesgos-v104";
const BASE = [
  "./",
  "index.html",
  "metodologia.html",
  "css/estilo.css",
  "js/mapa.js",
  "js/metodologia.js",
  "vendor/leaflet/leaflet.js",
  "vendor/leaflet/leaflet.css",
  "vendor/josefin-sans/josefin-sans-latin-600-normal.woff2",
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
  // "no-cache": el navegador pregunta al servidor si el archivo cambió en lugar de usar su copia HTTP
  // (GitHub Pages permite guardarla 10 minutos). Sin esto, una versión nueva tardaba en verse.
  // Una navegación no admite opciones sobre el pedido original: se arma uno nuevo con la misma URL.
  const pedido = evento.request.mode === "navigate"
    ? new Request(url.href, { cache: "no-cache", credentials: "same-origin" })
    : new Request(evento.request, { cache: "no-cache" });
  evento.respondWith(
    fetch(pedido)
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
