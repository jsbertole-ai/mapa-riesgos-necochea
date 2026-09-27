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
    amenity: { fire_station: "Cuartel de bomberos" },
    office: { government: "Oficina pública" },
  };
  const ORDEN_CLAVES = ["waterway", "natural", "man_made", "harbour", "landuse", "industrial", "railway", "highway", "hgv", "amenity", "office"];

  const TIPOS_FIRMS = {
    0: "Presunto incendio de vegetación",
    1: "Volcán activo",
    2: "Otra fuente terrestre estática (por ejemplo, industrial)",
    3: "Costa afuera",
  };
  const CONFIANZA_VIIRS = { l: "baja", n: "nominal", h: "alta" };

  // Dominios de la red vial del IGN, según la documentación de la capa.
  const JURISDICCION_IGN = { 1: "Ruta nacional", 2: "Ruta provincial", 4: "Camino terciario", 5: "Camino vecinal" };
  const SUPERFICIE_IGN = { 1: "Pavimentado", 2: "Consolidado", 3: "Tierra" };
  const METODO_CURVAS_IGN = { 1: "Por restitución", 2: "Por modelo digital de elevaciones", 3: "Por plancheta", 4: "Por fotogrametría" };
  const ATRIBUCION_IGN = 'FUENTE: <a href="https://www.ign.gob.ar/">Instituto Geográfico Nacional de la República Argentina</a>';

  // Las capas del IGN se reconocen por su cita, que la licencia del IGN obliga a incluir.
  function esIgn(capa) {
    return (capa.cita || "").indexOf("Instituto Geográfico Nacional") >= 0;
  }
  const CITA_IGN = "FUENTE: Instituto Geográfico Nacional de la República Argentina";

  const estado = { capas: {}, datos: {}, capasLeaflet: {}, anios: null };

  const mapa = L.map("mapa", { preferCanvas: true, zoomSnap: 0.5 }).setView(VISTA_INICIAL.centro, VISTA_INICIAL.zoom);
  mapa.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');

  L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '© <a href="https://www.openstreetmap.org/copyright">colaboradores de OpenStreetMap</a> (ODbL)',
  }).addTo(mapa);

  // Todas las capas se dibujan en un solo lienzo: con un lienzo por capa de dibujo, el de arriba se queda
  // con los clics y las líneas y polígonos de abajo no responden. El orden (polígonos abajo, líneas en el
  // medio, puntos arriba) lo mantiene ordenarDibujo(). El límite va aparte, encima de todo y sin clics.
  // La tolerancia de 6 px permite tocar líneas finas (media tensión, arroyos) en el celular.
  [["dibujo", 420], ["limite", 440]].forEach(function (p) {
    mapa.createPane(p[0]).style.zIndex = p[1];
  });
  mapa.getPane("limite").style.pointerEvents = "none";
  const LIENZOS = {
    dibujo: L.canvas({ pane: "dibujo", tolerance: 6 }),
    limite: L.canvas({ pane: "limite" }),
  };
  function lienzo(pane) {
    return pane === "limite" ? LIENZOS.limite : LIENZOS.dibujo;
  }

  function cadaTrazo(capa, fn) {
    if (capa.eachLayer) capa.eachLayer(function (l) { cadaTrazo(l, fn); });
    else if (capa.bringToFront) fn(capa);
  }

  function ordenarDibujo() {
    const capas = Object.values(estado.capasLeaflet).filter(function (c) { return mapa.hasLayer(c); });
    [L.Polyline, L.CircleMarker].forEach(function (clase) {
      capas.forEach(function (c) {
        cadaTrazo(c, function (l) {
          if (l instanceof clase && !(clase === L.Polyline && l instanceof L.Polygon)) l.bringToFront();
        });
      });
    });
  }

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
    return null;
  }

  function popupOsm(p) {
    const filas = [];
    if (p.industrial) filas.push(["Rubro (según OSM)", ETIQUETAS_OSM.industrial[p.industrial] || p.industrial]);
    if (p.official_name) filas.push(["Nombre oficial", p.official_name]);
    if (p.description) filas.push(["Descripción (según OSM)", p.description]);
    if (p.ref) filas.push(["Referencia", p.ref]);
    if (p.operator) filas.push(["Operador (según OSM)", p.operator]);
    if (p.content || p.product) filas.push(["Contenido (según OSM)", p.content || p.product]);
    if (p.intermittent === "yes") filas.push(["Curso", "Intermitente"]);
    return (
      "<h3>" + esc(p.name || categoriaOsm(p) || "Elemento de OpenStreetMap") + "</h3>" +
      (p.name && categoriaOsm(p) ? "<div>" + esc(categoriaOsm(p)) + "</div>" : "") +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      '<p class="nota">Fuente: ' + enlace("https://www.openstreetmap.org/" + p.osm, "OpenStreetMap, " + p.osm) + " (ODbL).</p>"
    );
  }

  // Media tensión (Secretaría de Energía): tensión y tipo de cada tramo.
  function popupMediaTension(p) {
    const filas = [];
    if (p.tipo) filas.push(["Tendido", p.tipo]);
    if (p.clase) filas.push(["Clase", p.clase]);
    if (p.funcion) filas.push(["Función", p.funcion]);
    if (p.cooperativa) filas.push(["Cooperativa", p.cooperativa]);
    return (
      "<h3>Línea de media tensión" + (p.tension_kv ? ", " + esc(String(p.tension_kv).replace(".", ",")) + " kV" : "") + "</h3>" +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      '<p class="nota">Fuente: Secretaría de Energía de la Nación (CFEE), datos de 2022. CC BY 4.0.</p>'
    );
  }

  // Inventario local: cada marcador trae uno o varios registros (los ubicados por localidad van juntos).
  function popupInventario(p) {
    const registros = p.registros.slice().reverse();
    const titulo = p.ubicacion === "localidad"
      ? registros.length + (registros.length === 1 ? " registro en " : " registros en ") + p.localidad
      : registros[0].tipo;
    return (
      "<h3>" + esc(titulo) + "</h3>" +
      (p.ubicacion === "localidad" ? '<p class="nota">' + (registros.length === 1 ? "Ubicado" : "Ubicados") + ' en el punto de la localidad (IGN): no marca el lugar del evento.</p>' : "") +
      registros.map(function (r) {
        const efectos = Object.keys(r.efectos || {}).map(function (k) { return k + ": " + numero(r.efectos[k]); });
        return (
          '<div class="registro">' +
          "<strong>" + esc(fecha(r.fecha)) + ". " + esc(r.tipo) + "</strong>" +
          (r.lugar ? " (" + esc(r.lugar) + ")" : "") +
          "<div>" + esc(r.descripcion) + "</div>" +
          (efectos.length ? "<div>" + esc(efectos.join(" · ")) + "</div>" : "") +
          (r.observaciones_efectos ? "<div>Observaciones: " + esc(r.observaciones_efectos) + "</div>" : "") +
          (r.servicios && r.servicios.length ? "<div>Servicios afectados: " + esc(r.servicios.join(", ")) + "</div>" : "") +
          '<div class="nota">Fuente: ' + enlace(r.fuente_url, r.fuente_medio + ", " + fecha(r.fuente_fecha)) + "</div>" +
          "</div>"
        );
      }).join("") +
      '<p class="nota">Inventario local (CC BY 4.0). Registros tomados de medios y revisados antes de publicarse; no es un registro oficial.</p>'
    );
  }

  function popupIgn(p) {
    const filas = [];
    if (p.fna && p.tipo) filas.push(["Tipo", p.tipo]);
    if (p.tipo_asent) filas.push(["Tipo de asentamiento", p.tipo_asent]);
    if (p.hct !== undefined) filas.push(["Jurisdicción", JURISDICCION_IGN[p.hct] || "s/d"]);
    if (p.rtn) filas.push(["Número", p.rtn]);
    if (p.rst !== undefined) filas.push(["Superficie", SUPERFICIE_IGN[p.rst] || "s/d"]);
    if (p.mo2 !== undefined) filas.push(["Método", METODO_CURVAS_IGN[p.mo2] || "Código " + p.mo2 + " (no figura en la documentación)"]);
    if (p.fdc) filas.push(["Fuente de captura", p.fdc]);
    const titulo = p.crv !== undefined ? "Curva de nivel: " + numero(p.crv) + " m"
      : p.fna || (p.hct !== undefined && p.rtn ? (JURISDICCION_IGN[p.hct] || "Ruta") + " " + p.rtn : p.tipo);
    return (
      "<h3>" + esc(titulo) + "</h3>" +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      '<p class="nota">' + esc(CITA_IGN) + ".</p>"
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
        pane: capa.id === "limite" ? "limite" : "dibujo",
        renderer: lienzo(capa.id === "limite" ? "limite" : "dibujo"),
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
    if (e.bicolor) {
      // Simbología de vía férrea: línea negra de base (la que recibe los clics) con trazos blancos encima;
      // las estaciones, como círculos blancos con borde negro.
      const esLinea = function (f) { return f.geometry.type !== "Point" && f.geometry.type !== "MultiPoint"; };
      const base = L.geoJSON(datos, {
        style: { color: e.color, weight: 5, pane: "dibujo", renderer: lienzo("dibujo") },
        attribution: ATRIBUCION_IGN,
        pointToLayer: function (f, latlng) {
          return L.circleMarker(latlng, { pane: "dibujo", renderer: lienzo("dibujo"), radius: 4, color: e.color, weight: 2, fillColor: "#ffffff", fillOpacity: 1 });
        },
        onEachFeature: function (f, l) { l.bindPopup(function () { return popupIgn(f.properties); }); },
      });
      const trazos = L.geoJSON(datos, { filter: esLinea, style: { color: "#ffffff", weight: 2.5, dashArray: "7 7", pane: "dibujo", renderer: lienzo("dibujo") }, interactive: false });
      return L.featureGroup([base, trazos]);
    }
    return L.geoJSON(datos, {
      style: estiloDe(capa),
      filter: filtroAnios(capa),
      interactive: capa.id !== "limite",
      attribution: capa.id.startsWith("incendios_") ? 'Focos de calor: <a href="https://firms.modaps.eosdis.nasa.gov/">NASA FIRMS</a>'
        : esIgn(capa) ? ATRIBUCION_IGN
        : capa.id === "media_tension" ? 'Media tensión: <a href="https://datos.gob.ar/dataset/redes-de-distribucion-electrica-del-consejo-federal">Secretaría de Energía</a> (CC BY 4.0)'
        : null,
      pointToLayer: function (f, latlng) {
        const n = f.properties.registros ? f.properties.registros.length : 1;
        return L.circleMarker(latlng, {
          pane: "dibujo", renderer: lienzo("dibujo"),
          // En el inventario, los marcadores por localidad crecen con la cantidad de registros.
          radius: (e.radio || 4) + (n > 1 ? Math.min(8, Math.sqrt(n) * 2) : 0),
          color: "#ffffff",
          weight: 1,
          fillColor: e.color,
          fillOpacity: 0.85,
        });
      },
      onEachFeature: function (f, l) {
        if (capa.id === "limite") return;
        l.bindPopup(function () {
          if (capa.id === "inventario_local") return popupInventario(f.properties);
          if (capa.id === "media_tension") return popupMediaTension(f.properties);
          if (capa.id.startsWith("incendios_")) return popupFirms(f.properties, capa);
          if (esIgn(capa)) return popupIgn(f.properties);
          return popupOsm(f.properties);
        }, { maxHeight: 320 });
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
    // Si la casilla se destildó mientras se descargaba el archivo, no se dibuja.
    const casilla = document.getElementById("casilla-" + capa.id);
    if (casilla && !casilla.checked) return;
    if (actual) mapa.removeLayer(actual);
    const nueva = crearCapaLeaflet(capa, datos).addTo(mapa);
    estado.capasLeaflet[capa.id] = nueva;
    ordenarDibujo();
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
    const clase = e.bicolor ? "ferro" : capa.geometria === "punto" ? "punto" : capa.geometria === "linea" ? "linea" : "";
    const discontinua = e.trazo ? " discontinua" : "";
    const fondo = capa.geometria === "punto" ? "" : e.relleno && e.relleno !== false ? "background:" + e.relleno + ";" : "";
    return '<span class="muestra ' + clase + discontinua + '" style="color:' + esc(e.color || "#888") + ";" + fondo + '"></span>';
  }

  // Enlace al formulario de carga (solo el inventario local lo tiene, y solo cuando está publicado en Kobo).
  function colaborar(capa) {
    return capa.url_formulario
      ? "<dt>Colaborar</dt><dd>" + enlace(capa.url_formulario, "Sumar un registro") + ". Se publica después de revisar la nota de origen.</dd>"
      : "";
  }

  function fichaDe(capa) {
    if (capa.estado !== "verificada") {
      return (
        "<dl><dt>Estado</dt><dd>Pendiente de fuente.</dd>" +
        (capa.motivo_pendiente ? "<dt>Por qué</dt><dd>" + esc(capa.motivo_pendiente) + "</dd>" : "") +
        (capa.verificacion ? "<dt>Controles</dt><dd>" + capa.verificacion.controles.map(esc).join("<br>") + "</dd>" : "") +
        (capa.que_representa ? "<dt>Qué representaría</dt><dd>" + esc(capa.que_representa) + "</dd>" : "") +
        (capa.url_fuente ? "<dt>Fuente a revisar</dt><dd>" + enlace(capa.url_fuente) + "</dd>" : "") +
        colaborar(capa) +
        "</dl>"
      );
    }
    return (
      "<dl>" +
      "<dt>Qué representa</dt><dd>" + esc(capa.que_representa) + "</dd>" +
      "<dt>Qué no representa</dt><dd>" + esc(capa.que_no_representa) + "</dd>" +
      "<dt>Fuente</dt><dd>" + esc(capa.organismo) + "." + (capa.url_fuente ? " " + enlace(capa.url_fuente) : "") + "</dd>" +
      "<dt>Fecha de los datos</dt><dd>" + esc(capa.fecha_datos || "s/d") + "</dd>" +
      "<dt>Licencia</dt><dd>" + esc(capa.licencia) + ". " + enlace(capa.url_licencia, "Texto de la licencia") +
      (capa.url_aviso_legal ? ". " + enlace(capa.url_aviso_legal, "Aviso legal de FIRMS") : "") + "</dd>" +
      "<dt>Cita</dt><dd>" + esc(capa.cita) + "</dd>" +
      "<dt>Verificación</dt><dd>" + esc(capa.verificacion ? capa.verificacion.fecha : "") + ". " +
      '<a href="metodologia.html#' + esc(capa.id) + '">Limitaciones y controles</a></dd>' +
      colaborar(capa) +
      "</dl>"
    );
  }

  function filaCapa(capa) {
    const div = document.createElement("div");
    const verificada = capa.estado === "verificada";
    div.className = "capa" + (verificada ? "" : " pendiente");
    const cuenta = verificada && capa.id !== "limite" ? '<span class="capa-cuenta">' + numero(capa.elementos) + (capa.elementos === 1 ? " elemento" : " elementos") + "</span>" : "";
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
