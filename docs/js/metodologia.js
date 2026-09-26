/* Genera las fichas de cada capa en la página de metodología a partir de datos/capas.json. */
(function () {
  "use strict";

  const ESTADOS = { verificada: "Verificada", pendiente: "Pendiente de fuente", sin_fuente: "Pendiente de fuente" };

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function enlace(url, texto) {
    return '<a href="' + esc(url) + '" rel="noopener">' + esc(texto || url) + "</a>";
  }

  function fila(titulo, valor) {
    return valor ? "<dt>" + esc(titulo) + "</dt><dd>" + valor + "</dd>" : "";
  }

  function focosPorAnio(capa) {
    const a = capa.focos_por_anio;
    if (!a) return "";
    return Object.keys(a).sort().map(function (k) { return k + ": " + a[k]; }).join(" · ");
  }

  function ficha(capa, grupo) {
    return (
      '<section class="ficha-capa" id="' + esc(capa.id) + '">' +
      "<h3>" + esc(capa.nombre) + ' <span class="estado ' + esc(capa.estado) + '">' + esc(ESTADOS[capa.estado] || capa.estado) + "</span></h3>" +
      "<dl>" +
      fila("Amenaza o grupo", esc(grupo)) +
      fila("Qué representa", esc(capa.que_representa)) +
      fila("Qué no representa", esc(capa.que_no_representa)) +
      fila("Limitaciones", esc(capa.limitaciones)) +
      fila("Por qué está pendiente", esc(capa.motivo_pendiente)) +
      fila("Organismo", esc(capa.organismo)) +
      fila("Fuente", capa.url_fuente ? enlace(capa.url_fuente) : "") +
      fila("Datos descargados de", capa.url_datos ? esc(capa.url_datos) : "") +
      fila("Fecha de los datos", esc(capa.fecha_datos)) +
      fila("Licencia", capa.licencia ? esc(capa.licencia) + (capa.url_licencia ? ". " + enlace(capa.url_licencia, "Texto") : "") : "") +
      fila("Cita", esc(capa.cita)) +
      fila("Formato", esc(capa.formato)) +
      fila("Elementos", capa.elementos ? esc(Number(capa.elementos).toLocaleString("es-AR")) : "") +
      fila("Focos por año", esc(focosPorAnio(capa))) +
      fila("Verificación", capa.verificacion ? esc(capa.verificacion.fecha) + ": " + capa.verificacion.controles.map(esc).join(" ") : "") +
      "</dl></section>"
    );
  }

  fetch("datos/capas.json")
    .then(function (r) { return r.json(); })
    .then(function (registro) {
      const nombres = {};
      registro.grupos.forEach(function (g) { nombres[g.id] = g.nombre; });
      document.getElementById("fichas").innerHTML = registro.capas
        .map(function (c) { return ficha(c, nombres[c.grupo]); })
        .join("");
      if (location.hash) {
        const destino = document.getElementById(location.hash.slice(1));
        if (destino) destino.scrollIntoView();
      }
    })
    .catch(function () {
      document.getElementById("fichas").innerHTML = "<p>No se pudo cargar el registro de capas.</p>";
    });
})();
