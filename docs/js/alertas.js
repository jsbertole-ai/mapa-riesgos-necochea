/* Alertas del SMN para el partido, leídas de datos/alertas_smn.json (lo actualiza cada hora el workflow
 * alertas-smn.yml). Lo usan la portada (index.html) y el mapa (mapa.html).
 * No se deduce nada que el archivo no diga: ni el color de la alerta ni localidades que el SMN no nombra
 * (las localidades salen de cruzar el polígono del aviso con las del IGN, en scripts/archivar_alertas_smn.py).
 */
(function () {
  "use strict";

  const ARCHIVO = "datos/alertas_smn.json";
  const PAGINA_SMN = "https://www.smn.gob.ar/alertas";

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  // "2026-09-29T09:00:00-03:00" pasa a "29/09/2026 09:00" (hora que informa el SMN, la de la Argentina).
  function fechaHora(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(iso || "");
    return m ? m[3] + "/" + m[2] + "/" + m[1] + " " + m[4] + ":" + m[5] : esc(iso || "s/d");
  }

  function lista(xs) {
    return xs.length < 2 ? xs.join("") : xs.slice(0, -1).join(", ") + " y " + xs[xs.length - 1];
  }

  function cargar() {
    return fetch(ARCHIVO).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    });
  }

  // Mismo criterio que la metodología: los mensajes de un mismo evento y vigencia (uno por zona, más sus
  // actualizaciones) forman un episodio; de cada uno se toma el mensaje más reciente.
  function episodios(a) {
    const grupos = {};
    (a.alertas || []).forEach(function (x) {
      const k = [x.tipo, x.evento, x.inicio, x.fin].join("|");
      const e = grupos[k] || (grupos[k] = { x: x, localidades: {}, todo: false, severidades: {} });
      if ((x.enviado || "") > (e.x.enviado || "")) e.x = x;
      (x.localidades || []).forEach(function (l) { e.localidades[l] = true; });
      if (x.alcance === "todo el partido") e.todo = true;
      if (x.severidad) e.severidades[x.severidad] = true;
    });
    return Object.keys(grupos).map(function (k) {
      const e = grupos[k];
      return {
        x: e.x, todo: e.todo,
        localidades: Object.keys(e.localidades).sort(),
        severidades: Object.keys(e.severidades),
        desde: Date.parse(e.x.inicio), hasta: Date.parse(e.x.fin),
      };
    });
  }

  // Vigente: empezó antes de ahora y termina después.
  function estado(a, ahora) {
    const eps = episodios(a);
    const t = ahora == null ? Date.now() : ahora;
    const vigentes = eps.filter(function (e) { return e.desde <= t && e.hasta > t; })
      .sort(function (p, q) { return p.hasta - q.hasta; });
    const ultima = eps.slice().sort(function (p, q) { return (q.x.enviado || "").localeCompare(p.x.enviado || ""); })[0] || null;
    return { vigentes: vigentes, ultima: ultima };
  }

  const ORDEN = ["Menor", "Moderada", "Severa", "Extrema"];
  function severidadMayor(e) {
    return e.severidades.slice().sort(function (p, q) { return ORDEN.indexOf(q) - ORDEN.indexOf(p); })[0] || "s/d";
  }

  // La severidad se distingue por el texto, por el ícono (triángulo hueco, lleno u octógono) y por el color.
  function chip(sev) {
    const clase = { Menor: "menor", Moderada: "moderada", Severa: "severa", Extrema: "extrema" }[sev] || "sd";
    const icono = clase === "extrema"
      ? '<path d="M8 1h8l7 7v8l-7 7H8l-7-7V8z" fill="currentColor"/><path d="M12 6v8M12 17v1.5" stroke="#000" stroke-width="2.4" stroke-linecap="round"/>'
      : clase === "severa"
        ? '<path d="M12 2 23 21H1z" fill="currentColor"/><path d="M12 9v5M12 17v1" stroke="#000" stroke-width="2.4" stroke-linecap="round"/>'
        : '<path d="M12 3 22 20H2z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M12 9v5M12 17v1" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"/>';
    return '<span class="sev sev-' + clase + '"><svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">' + icono +
      "</svg>Severidad " + esc(sev.toLowerCase()) + "</span>";
  }

  function nombre(e) {
    return e.x.tipo === "alerta" ? e.x.evento : e.x.titular || e.x.evento;
  }

  function periodo(e) {
    return "Del " + fechaHora(e.x.inicio) + " al " + fechaHora(e.x.fin);
  }

  function alcanzadas(e) {
    if (e.todo) return "Todo el partido" + (e.localidades.length ? " (" + esc(lista(e.localidades)) + ")" : "");
    return e.localidades.length
      ? "Localidades dentro de la zona: " + esc(lista(e.localidades))
      : "La zona toca el partido, pero no contiene ninguna de sus localidades";
  }

  function fichaVigente(e) {
    return '<article class="alerta-smn">' +
      '<p class="alerta-cabeza">' + chip(severidadMayor(e)) + '<strong class="alerta-evento">' + esc(nombre(e)) + "</strong></p>" +
      '<p class="alerta-dato">' + periodo(e) + "</p>" +
      '<p class="alerta-dato">' + alcanzadas(e) + "</p>" +
      '<p class="alerta-dato"><a href="' + esc(e.x.url) + '" target="_blank" rel="noopener">Aviso original del SMN</a>' +
      " (emitido el " + fechaHora(e.x.enviado) + ")</p>" +
      "</article>";
  }

  // HTML del bloque completo. "conexion" es false cuando se muestra la copia guardada.
  function bloque(a, ahora, conexion) {
    const s = estado(a, ahora);
    let cuerpo;
    if (s.vigentes.length) {
      cuerpo = '<h2 class="alertas-titulo">' + (s.vigentes.length === 1 ? "Alerta vigente del SMN" : s.vigentes.length + " alertas vigentes del SMN") +
        " para el partido</h2>" + s.vigentes.map(fichaVigente).join("");
    } else {
      cuerpo = '<h2 class="alertas-titulo">Sin alertas vigentes del SMN para el partido</h2>';
      const u = s.ultima;
      cuerpo += u
        ? '<p class="alerta-dato">Última alerta emitida: <strong>' + esc(nombre(u)) + "</strong>, severidad " + esc(severidadMayor(u).toLowerCase()) +
          ", emitida el " + fechaHora(u.x.enviado) + ", vigente del " + fechaHora(u.x.inicio) + " al " + fechaHora(u.x.fin) +
          '. <a href="' + esc(u.x.url) + '" target="_blank" rel="noopener">Aviso original</a></p>'
        : '<p class="alerta-dato">No hay alertas registradas desde el ' + esc((a.desde || "").split("-").reverse().join("/")) + ".</p>";
    }
    return cuerpo +
      (conexion === false ? '<p class="alertas-nota alertas-offline">Sin conexión: es la última copia guardada; puede haber alertas nuevas.</p>' : "") +
      '<p class="alertas-nota">Se revisa cada hora. <a href="' + PAGINA_SMN + '" target="_blank" rel="noopener">Alertas en smn.gob.ar</a>. ' +
      "Fuente: Servicio Meteorológico Nacional, licencia CC BY 4.0.</p>";
  }

  /* Monta el bloque en "el" y lo refresca cada 10 minutos (y al recuperar la conexión).
   * Devuelve una promesa que se cumple con el primer dibujo; "alCambiar" se llama en cada dibujo posterior. */
  function montar(el, alCambiar) {
    let ultimo = null;
    function dibujar(a) {
      ultimo = a;
      el.innerHTML = bloque(a, Date.now(), navigator.onLine);
      el.hidden = false;
    }
    function refrescar() {
      return cargar().then(dibujar).catch(function () {
        if (ultimo) { dibujar(ultimo); return; }
        el.innerHTML = '<h2 class="alertas-titulo">Alertas del SMN</h2><p class="alerta-dato">No se pudo leer el archivo de alertas. ' +
          '<a href="' + PAGINA_SMN + '" target="_blank" rel="noopener">Ver las alertas en smn.gob.ar</a>.</p>';
        el.hidden = false;
      });
    }
    const primera = refrescar();
    const luego = function () { refrescar().then(function () { if (alCambiar) alCambiar(); }); };
    setInterval(luego, 10 * 60 * 1000);
    window.addEventListener("online", luego);
    window.addEventListener("offline", function () { if (ultimo) { dibujar(ultimo); if (alCambiar) alCambiar(); } });
    return primera;
  }

  window.AlertasSMN = { cargar: cargar, episodios: episodios, estado: estado, bloque: bloque, montar: montar,
                        fechaHora: fechaHora, esc: esc, nombre: nombre, severidadMayor: severidadMayor, chip: chip, periodo: periodo };
})();
