/* Mapa de riesgos del partido de Necochea.
 * Lee docs/datos/capas.json (generado por scripts/verificar.py) y dibuja
 * solo las capas en estado "verificada". El resto se lista como
 * "pendiente de fuente". Los GeoJSON se piden recién al activar cada capa.
 */
(function () {
  "use strict";

  // Centroide del partido según Georef, solo para la vista inicial antes de cargar el límite.
  const VISTA_INICIAL = { centro: [-38.2554, -59.1674], zoom: 9 };

  const ETIQUETAS_OSM = {
    waterway: { river: "Río", stream: "Arroyo", canal: "Canal", drain: "Desagüe", ditch: "Zanja" },
    natural: { water: "Cuerpo de agua", coastline: "Línea de costa" },
    landuse: { industrial: "Zona industrial", port: "Zona portuaria" },
    industrial: { port: "portuario", agriculture: "agropecuario", gas: "gas" },
    man_made: { silo: "Silo", storage_tank: "Tanque de almacenamiento", pier: "Muelle", breakwater: "Escollera" },
    railway: { rail: "Vía férrea" },
    highway: { trunk: "Ruta troncal", primary: "Ruta primaria" },
    hgv: { designated: "Vía designada para camiones" },
  };
  const ORDEN_CLAVES = ["waterway", "natural", "man_made", "harbour", "landuse", "industrial", "railway", "highway", "hgv"];

  const TIPOS_FIRMS = {
    0: "Presunto incendio de vegetación",
    1: "Volcán activo",
    2: "Otra fuente terrestre estática (por ejemplo, industrial)",
    3: "Costa afuera",
  };
  const CONFIANZA_VIIRS = { l: "baja", n: "nominal", h: "alta" };

  const estado = { capas: {}, datos: {}, capasLeaflet: {}, anios: null };

  const mapa = L.map("mapa", { preferCanvas: true, zoomSnap: 0.5 }).setView(VISTA_INICIAL.centro, VISTA_INICIAL.zoom);
  mapa.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">colaboradores de OpenStreetMap</a> (ODbL)',
  }).addTo(mapa);

  // Capas de dibujo: polígonos abajo, puntos arriba, límite encima de todo y sin clics.
  [["poligonos", 410], ["lineas", 420], ["puntos", 430], ["limite", 440]].forEach(function (p) {
    mapa.createPane(p[0]).style.zIndex = p[1];
  });
  mapa.getPane("limite").style.pointerEvents = "none";

  function esc(v) {
    return String(v == null ? "" : v).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }

  function enlace(url, texto) {
    return '<a href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(texto || url) + "</a>";
  }

  function numero(n) {
    return Number(n).toLocaleString("es-AR");
  }

  // "2024-11-12" pasa a "12/11/2024".
  function fecha(iso) {
    const partes = String(iso || "").split("-");
    return partes.length === 3 ? partes[2] + "/" + partes[1] + "/" + partes[0] : iso;
  }

  // ---------- Ventanas emergentes ----------

  function categoriaOsm(p) {
    for (const k of ORDEN_CLAVES) {
      if (p[k] !== undefined) {
        if (k === "harbour") return "Puerto";
        if (k === "industrial") return "Área industrial";
        return (ETIQUETAS_OSM[k] && ETIQUETAS_OSM[k][p[k]]) || k + "=" + p[k];
      }
    }
    return "Elemento de OpenStreetMap";
  }

  function popupOsm(p) {
    const filas = [];
    if (p.industrial) filas.push(["Rubro (según OSM)", ETIQUETAS_OSM.industrial[p.industrial] || p.industrial]);
    if (p.ref) filas.push(["Referencia", p.ref]);
    if (p.operator) filas.push(["Operador (según OSM)", p.operator]);
    if (p.content || p.product) filas.push(["Contenido (según OSM)", p.content || p.product]);
    if (p.intermittent === "yes") filas.push(["Curso", "Intermitente"]);
    return (
      "<h3>" + esc(p.name || categoriaOsm(p)) + "</h3>" +
      (p.name ? "<div>" + esc(categoriaOsm(p)) + "</div>" : "") +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      '<p class="nota">Fuente: ' + enlace("https://www.openstreetmap.org/" + p.osm, "OpenStreetMap, " + p.osm) + " (ODbL).</p>"
    );
  }

  function popupFirms(p, capa) {
    const hora = p.acq_time ? String(p.acq_time).padStart(4, "0") : "";
    const esViirs = capa.id === "incendios_viirs";
    const confianza = esViirs ? (CONFIANZA_VIIRS[p.confidence] || p.confidence) : p.confidence + " %";
    const satelite = esViirs ? "Suomi NPP (VIIRS)" : (p.satellite || "") + " (MODIS)";
    const filas = [
      ["Fecha", fecha(p.acq_date)],
      ["Hora", hora ? hora.slice(0, 2) + ":" + hora.slice(2) + " UTC" : "s/d"],
      ["Satélite", satelite],
      ["Confianza", confianza],
      ["Potencia radiativa", p.frp != null ? numero(p.frp) + " MW" : "s/d"],
      ["Pasada", p.daynight === "D" ? "Diurna" : p.daynight === "N" ? "Nocturna" : "s/d"],
      ["Tipo inferido", TIPOS_FIRMS[p.type] || "s/d"],
    ];
    return (
      "<h3>Foco de calor</h3><table>" +
      filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") +
      '</table><p class="nota">Es una anomalía térmica detectada por satélite, no un incendio confirmado. Fuente: NASA FIRMS.</p>'
    );
  }

  // ---------- Capas ----------

  function estiloDe(capa) {
    const e = capa.estilo || {};
    return function (feature) {
      const tipo = feature.geometry.type;
      // Los puntos ya tienen su estilo en pointToLayer; devolver algo acá lo pisaría.
      if (tipo === "Point" || tipo === "MultiPoint") return {};
      const esArea = tipo === "Polygon" || tipo === "MultiPolygon";
      return {
        color: e.color,
        weight: capa.id === "limite" ? 2.5 : e.grosor || (esArea ? 1 : 1.8),
        dashArray: e.trazo || null,
        fill: esArea && e.relleno !== false,
        fillColor: e.relleno || e.color,
        fillOpacity: 0.45,
        pane: capa.id === "limite" ? "limite" : esArea ? "poligonos" : "lineas",
      };
    };
  }

  function filtroAnios(capa) {
    if (!capa.id.startsWith("incendios_") || !estado.anios) return null;
    const desde = estado.anios.desde, hasta = estado.anios.hasta;
    return function (f) {
      const a = Number(String(f.properties.acq_date).slice(0, 4));
      return a >= desde && a <= hasta;
    };
  }

  function crearCapaLeaflet(capa, datos) {
    const e = capa.estilo || {};
    return L.geoJSON(datos, {
      style: estiloDe(capa),
      filter: filtroAnios(capa),
      interactive: capa.id !== "limite",
      attribution: capa.id === "limite" ? "Límite: Georef / IGN (CC BY 4.0)"
        : capa.id.startsWith("incendios_") ? 'Focos de calor: <a href="https://firms.modaps.eosdis.nasa.gov/">NASA FIRMS</a>'
        : null,
      pointToLayer: function (f, latlng) {
        return L.circleMarker(latlng, {
          pane: "puntos",
          radius: e.radio || 4,
          color: "#ffffff",
          weight: 1,
          fillColor: e.color,
          fillOpacity: 0.85,
        });
      },
      onEachFeature: function (f, l) {
        if (capa.id === "limite") return;
        l.bindPopup(function () {
          return capa.id.startsWith("incendios_") ? popupFirms(f.properties, capa) : popupOsm(f.properties);
        });
      },
    });
  }

  async function cargarDatos(capa) {
    if (!estado.datos[capa.id]) {
      const r = await fetch("datos/" + capa.archivo);
      if (!r.ok) throw new Error("No se pudo cargar " + capa.archivo);
      estado.datos[capa.id] = await r.json();
    }
    return estado.datos[capa.id];
  }

  async function mostrar(capa, visible) {
    const actual = estado.capasLeaflet[capa.id];
    if (!visible) {
      if (actual) mapa.removeLayer(actual);
      return;
    }
    const datos = await cargarDatos(capa);
    if (actual) mapa.removeLayer(actual);
    const nueva = crearCapaLeaflet(capa, datos).addTo(mapa);
    estado.capasLeaflet[capa.id] = nueva;
    if (capa.id === "limite" && !estado.encuadrado) {
      mapa.fitBounds(nueva.getBounds(), { padding: [16, 16] });
      estado.encuadrado = true;
    }
  }

  function refrescarIncendios() {
    Object.values(estado.capas).forEach(function (c) {
      const casilla = document.getElementById("casilla-" + c.id);
      if (c.id.startsWith("incendios_") && casilla && casilla.checked) mostrar(c, true);
    });
  }

  // ---------- Panel ----------

  function muestraDe(capa) {
    const e = capa.estilo || {};
    const clase = capa.geometria === "punto" ? "punto" : capa.geometria === "linea" ? "linea" : "";
    const discontinua = e.trazo ? " discontinua" : "";
    const fondo = capa.geometria === "punto" ? "" : e.relleno && e.relleno !== false ? "background:" + e.relleno + ";" : "";
    return '<span class="muestra ' + clase + discontinua + '" style="color:' + esc(e.color || "#888") + ";" + fondo + '"></span>';
  }

  function fichaDe(capa) {
    if (capa.estado !== "verificada") {
      return (
        "<dl><dt>Estado</dt><dd>Pendiente de fuente.</dd>" +
        (capa.motivo_pendiente ? "<dt>Por qué</dt><dd>" + esc(capa.motivo_pendiente) + "</dd>" : "") +
        (capa.verificacion ? "<dt>Controles</dt><dd>" + capa.verificacion.controles.map(esc).join("<br>") + "</dd>" : "") +
        (capa.que_representa ? "<dt>Qué representaría</dt><dd>" + esc(capa.que_representa) + "</dd>" : "") +
        (capa.url_fuente ? "<dt>Fuente a revisar</dt><dd>" + enlace(capa.url_fuente) + "</dd>" : "") +
        "</dl>"
      );
    }
    return (
      "<dl>" +
      "<dt>Qué representa</dt><dd>" + esc(capa.que_representa) + "</dd>" +
      "<dt>Qué no representa</dt><dd>" + esc(capa.que_no_representa) + "</dd>" +
      "<dt>Fuente</dt><dd>" + esc(capa.organismo) + ". " + enlace(capa.url_fuente) + "</dd>" +
      "<dt>Fecha de los datos</dt><dd>" + esc(capa.fecha_datos || "s/d") + "</dd>" +
      "<dt>Licencia</dt><dd>" + esc(capa.licencia) + ". " + enlace(capa.url_licencia, "Texto de la licencia") +
      (capa.url_aviso_legal ? ". " + enlace(capa.url_aviso_legal, "Aviso legal de FIRMS") : "") + "</dd>" +
      "<dt>Cita</dt><dd>" + esc(capa.cita) + "</dd>" +
      "<dt>Verificación</dt><dd>" + esc(capa.verificacion ? capa.verificacion.fecha : "") + ". " +
      '<a href="metodologia.html#' + esc(capa.id) + '">Limitaciones y controles</a></dd>' +
      "</dl>"
    );
  }

  function filaCapa(capa) {
    const div = document.createElement("div");
    const verificada = capa.estado === "verificada";
    div.className = "capa" + (verificada ? "" : " pendiente");
    const cuenta = verificada && capa.id !== "limite" ? '<span class="capa-cuenta">' + numero(capa.elementos) + " elementos</span>" : "";
    div.innerHTML =
      '<div class="capa-fila">' +
      (verificada
        ? '<label><input type="checkbox" id="casilla-' + esc(capa.id) + '"' + (capa.activa_al_inicio ? " checked" : "") + ">" +
          muestraDe(capa) + '<span><span class="capa-nombre">' + esc(capa.nombre) + "</span><br>" + cuenta + "</span></label>"
        : "<label>" + muestraDe(capa) + '<span><span class="capa-nombre">' + esc(capa.nombre) + '</span><br><span class="etiqueta-pendiente">pendiente de fuente</span></span></label>') +
      '<button type="button" class="capa-info" aria-expanded="false" aria-controls="ficha-' + esc(capa.id) + '">Fuente</button>' +
      "</div>" +
      '<div class="ficha" id="ficha-' + esc(capa.id) + '" hidden>' + fichaDe(capa) + "</div>";

    const boton = div.querySelector(".capa-info");
    const ficha = div.querySelector(".ficha");
    boton.addEventListener("click", function () {
      ficha.hidden = !ficha.hidden;
      boton.setAttribute("aria-expanded", String(!ficha.hidden));
    });
    const casilla = div.querySelector("input");
    if (casilla) {
      casilla.addEventListener("change", function () {
        mostrar(capa, casilla.checked).catch(avisarError);
      });
    }
    return div;
  }

  function selectorAnios(capas) {
    const anios = [];
    capas.forEach(function (c) {
      Object.keys(c.focos_por_anio || {}).forEach(function (a) { anios.push(Number(a)); });
    });
    if (!anios.length) return null;
    const min = Math.min.apply(null, anios), max = Math.max.apply(null, anios);
    estado.anios = { desde: min, hasta: max };
    const opciones = function (sel) {
      let h = "";
      for (let a = min; a <= max; a++) h += "<option" + (a === sel ? " selected" : "") + ">" + a + "</option>";
      return h;
    };
    const div = document.createElement("div");
    div.className = "filtro-anios";
    div.innerHTML =
      '<label for="anio-desde">Años:</label> <select id="anio-desde">' + opciones(min) + "</select>" +
      ' <label for="anio-hasta">a</label> <select id="anio-hasta">' + opciones(max) + "</select>";
    const desde = div.querySelector("#anio-desde"), hasta = div.querySelector("#anio-hasta");
    function cambiar() {
      let d = Number(desde.value), h = Number(hasta.value);
      if (d > h) { h = d; hasta.value = h; }
      estado.anios = { desde: d, hasta: h };
      refrescarIncendios();
    }
    desde.addEventListener("change", cambiar);
    hasta.addEventListener("change", cambiar);
    return div;
  }

  function avisarError(e) {
    console.error(e);
    const lista = document.getElementById("lista-capas");
    const p = document.createElement("p");
    p.className = "aviso";
    p.textContent = "No se pudo cargar una capa. Si estás sin conexión, abrila una vez con conexión para que quede guardada.";
    lista.prepend(p);
  }

  async function iniciar() {
    const r = await fetch("datos/capas.json");
    const registro = await r.json();
    const lista = document.getElementById("lista-capas");
    lista.innerHTML = "";
    registro.grupos.forEach(function (g) {
      const capas = registro.capas.filter(function (c) { return c.grupo === g.id; });
      if (!capas.length) return;
      const sec = document.createElement("section");
      sec.className = "grupo";
      sec.innerHTML = "<h2>" + esc(g.nombre) + "</h2>";
      if (g.id === "incendios") {
        const filtro = selectorAnios(capas.filter(function (c) { return c.estado === "verificada"; }));
        if (filtro) sec.appendChild(filtro);
      }
      capas.forEach(function (c) {
        estado.capas[c.id] = c;
        sec.appendChild(filaCapa(c));
      });
      lista.appendChild(sec);
    });
    Object.values(estado.capas).forEach(function (c) {
      if (c.estado === "verificada" && c.activa_al_inicio) mostrar(c, true).catch(avisarError);
    });
  }

  // ---------- Panel en celular, conexión y aplicación instalable ----------

  const boton = document.getElementById("boton-capas");
  const panel = document.getElementById("panel");
  boton.addEventListener("click", function () {
    const abierto = panel.classList.toggle("abierto");
    boton.setAttribute("aria-expanded", String(abierto));
  });

  mapa.on("click", function () {
    panel.classList.remove("abierto");
    boton.setAttribute("aria-expanded", "false");
  });

  function actualizarConexion() {
    document.getElementById("aviso-sin-conexion").hidden = navigator.onLine;
  }
  window.addEventListener("online", actualizarConexion);
  window.addEventListener("offline", actualizarConexion);
  actualizarConexion();

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("sw.js").catch(function (e) { console.warn("Service worker:", e); });
    });
  }

  iniciar().catch(avisarError);
})();
