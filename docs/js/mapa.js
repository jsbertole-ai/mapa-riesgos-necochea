/* Mapa para la gestión del riesgo del partido de Necochea.
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
    amenity: { fire_station: "Cuartel de bomberos", ranger_station: "Base de guardaparques" },
    office: { government: "Oficina pública", lifeguard: "Oficina de guardavidas" },
    emergency: { lifeguard: "Guardavidas" },
  };
  const ORDEN_CLAVES = ["waterway", "natural", "man_made", "harbour", "landuse", "industrial", "railway", "highway", "hgv", "emergency", "amenity", "office"];
  const TIPO_GUARDAVIDAS = { base: "Base de guardavidas", tower: "Puesto de guardavidas" };

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
  // Líneas de energía (AT030): dominios del metadato del IGN.
  const TENSION_IGN = { 2: "Baja tensión (hasta 1 kV)", 3: "Media tensión (más de 1 kV y hasta 66 kV)", 6: "Alta tensión (más de 66 kV y hasta 220 kV)", 9: "Extra alta tensión (más de 220 kV y hasta 800 kV)", 17: "Ultra alta tensión (más de 800 kV)" };
  const ESTADO_IGN = { 2: "Abandonado", 4: "Desmantelado", 6: "Activo", 9: "En construcción" };
  const COLOR_FUERA_DE_USO = "#8c8c8c";
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
    if (p.lifeguard && TIPO_GUARDAVIDAS[p.lifeguard]) filas.push(["Tipo", TIPO_GUARDAVIDAS[p.lifeguard]]);
    if (p.seasonal === "summer") filas.push(["Temporada", "Funciona en verano"]);
    return (
      "<h3>" + esc(p.name || categoriaOsm(p) || "Elemento de OpenStreetMap") + "</h3>" +
      (p.name && categoriaOsm(p) ? "<div>" + esc(categoriaOsm(p)) + "</div>" : "") +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      '<p class="nota">Fuente: ' + enlace("https://www.openstreetmap.org/" + p.osm, "OpenStreetMap, " + p.osm) + " (ODbL).</p>"
    );
  }

  function notaFuente(p) {
    if (p.fuente === "Provincia de Buenos Aires") {
      return '<p class="nota">Fuente: ' + enlace("https://catalogo.datos.gba.gob.ar/es_AR/dataset/comisarias", "Ministerio de Seguridad de la Provincia de Buenos Aires, Comisarías") + " (CC BY 4.0).</p>";
    }
    if (p.fuente === "Colaborador") return '<p class="nota">' + esc(p.nota) + "</p>";
    return p.fuente === "IGN"
      ? (p.nota ? '<p class="nota">' + esc(p.nota) + "</p>" : "") + '<p class="nota">' + esc(CITA_IGN) + (p.fuente_captura ? " Fuente de captura: " + esc(p.fuente_captura) + "." : "") + "</p>"
      : (p.nota ? '<p class="nota">' + esc(p.nota) + "</p>" : "") + '<p class="nota">Fuente: ' + enlace("https://www.openstreetmap.org/" + p.ref, "OpenStreetMap, " + p.ref) + " (ODbL).</p>";
  }

  // Organismos de respuesta: IGN (policía, Prefectura, bomberos) y OpenStreetMap (el resto).
  function popupOrganismo(p) {
    const filas = [["Organismo", p.organismo]];
    if (p.official_name) filas.push(["Nombre oficial", p.official_name]);
    if (p.description) filas.push(["Descripción (según OSM)", p.description]);
    if (p.lifeguard && TIPO_GUARDAVIDAS[p.lifeguard]) filas.push(["Tipo", TIPO_GUARDAVIDAS[p.lifeguard]]);
    if (p.police === "traffic_police") filas.push(["Tipo", "Policía vial o de tránsito"]);
    if (p.seasonal === "summer") filas.push(["Temporada", "Funciona en verano"]);
    if (p.localidad) filas.push(["Localidad", p.localidad]);
    if (p.partido) filas.push(["Partido", p.partido + " (fuera del partido de Necochea; asiste en él)"]);
    return (
      "<h3>" + esc(p.nombre || p.organismo) + "</h3>" +
      "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" +
      notaFuente(p)
    );
  }

  // Red de asistencia: organizaciones que asisten a la población vulnerable (puntos de colaboradores).
  function popupVulnerabilidad(p) {
    const pc = function (v) { return v === null || v === undefined ? "s/d" : String(v).replace(".", ",") + " %"; };
    const filas = p.pct_nbi === undefined
      ? '<p class="nota">Menos de 20 hogares: no se calculan porcentajes.</p>'
      : "<ul>" +
        "<li>Hogares con NBI: " + pc(p.pct_nbi) + "</li>" +
        "<li>Hacinamiento (más de 2 personas por cuarto): " + pc(p.pct_hacinamiento) + "</li>" +
        "<li>Sin agua de red para beber y cocinar: " + pc(p.pct_sin_agua_red) + "</li>" +
        "<li>Sin cloaca: " + pc(p.pct_sin_cloaca) + "</li>" +
        "<li>Cocinan con garrafa o leña: " + pc(p.pct_garrafa_lena) + "</li>" +
        "<li>Personas con salud solo pública: " + pc(p.pct_solo_salud_publica) + "</li>" +
        "<li>Personas de 0 a 17 años: " + pc(p.pct_0a17) + "</li>" +
        "<li>Personas de 70 años o más: " + pc(p.pct_70ymas) + "</li></ul>";
    return (
      "<h3>Radio censal " + esc(p.radio) + "</h3>" +
      "<div>" + esc(p.tipo || "") + " · " + numero(p.poblacion) + " habitantes · " + numero(p.hogares) + " hogares</div>" +
      filas +
      '<p class="nota">Censo 2022 (INDEC), indicadores de de Grande y Salvia (2024). NBI mide carencias materiales, no toda la vulnerabilidad.</p>'
    );
  }

  function popupPoblacion(p) {
    return (
      "<h3>Radio censal " + esc(p.radio) + "</h3>" +
      "<div>" + numero(p.poblacion) + " habitantes · " + esc(String(p.densidad_hab_ha).replace(".", ",")) + " hab/ha</div>" +
      "<div>Superficie: " + esc(String(p.area_ha).replace(".", ",")) + " ha</div>" +
      '<p class="nota">Población residente del Censo 2022 (INDEC), según Boccolini (2026). No incluye la población turística.</p>'
    );
  }

  function popupGasoducto(p) {
    return (
      "<h3>" + esc(p.nombre || "Gasoducto") + "</h3>" +
      "<div>" + esc([p.tipo, p.subtipo].filter(Boolean).join(" · ")) + "</div>" +
      (p.tramo ? "<div>Tramo: " + esc(p.tramo) + "</div>" : "") +
      (p.licenciataria ? "<div>Licenciataria: " + esc(p.licenciataria) + "</div>" : "") +
      '<p class="nota">Traza declarada ante ENARGAS: no sirve para ubicar el caño en el terreno.</p>'
    );
  }

  function popupConectividad(p) {
    const filas = (p.tecnologias || []).map(function (t) {
      return "<li>" + esc(t[0]) + ": " + numero(t[1]) + "</li>";
    }).join("");
    const minima = p.categoria !== "Con fibra óptica" && p.fibra
      ? '<p class="nota">La fibra óptica existe pero es mínima: ' + numero(p.fibra) + " accesos.</p>" : "";
    return (
      "<h3>" + esc(p.localidad) + "</h3>" +
      "<div>" + esc(p.categoria) + " · " + numero(p.accesos) + " accesos a Internet fijo</div>" +
      "<ul>" + filas + "</ul>" + minima +
      '<p class="nota">Accesos declarados por los prestadores ante ENACOM (período no informado). No es un mapa de cobertura. ' + esc(p.punto) + "</p>"
    );
  }

  function popupAsistencia(p) {
    return "<h3>" + esc(p.nombre) + "</h3>" + "<div>" + esc(p.tipo) + "</div>" + '<p class="nota">' + esc(p.nota) + "</p>";
  }

  // Servicios de playa: el punto sale del mapa municipal de 2023 o de OpenStreetMap; la vigencia, de una nota municipal.
  function popupPlaya(p) {
    const filas = [["Tipo", p.tipo], ["Temporada", p.temporada === "verano" ? "Funciona en verano" : "Todo el año"]];
    return (
      "<h3>" + esc(p.nombre) + "</h3>" +
      "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" +
      (p.nota ? '<p class="nota">' + esc(p.nota) + "</p>" : "") +
      '<p class="nota">' + esc(p.vigencia) + (p.url_vigencia ? " " + enlace(p.url_vigencia, "Ver la nota") + "." : "") + "</p>" +
      '<p class="nota">Ubicación: ' + esc(p.origen) + "</p>" +
      (p.ref
        ? '<p class="nota">Fuente: ' + enlace("https://www.openstreetmap.org/" + p.ref, "OpenStreetMap, " + p.ref) + " (ODbL).</p>"
        : '<p class="nota">Fuente: ' + enlace("https://necochea.gov.ar/mapas-utiles/", "Municipalidad de Necochea, Mapas Útiles") + ".</p>")
    );
  }

  function popupRefugio(p) {
    return (
      "<h3>" + esc(p.nombre || p.tipo) + "</h3>" +
      "<div>Refugio: " + esc(p.uso.charAt(0).toLowerCase() + p.uso.slice(1)) + " (" + esc(p.tipo.toLowerCase()) + ")</div>" +
      '<p class="nota">' + esc(p.fuente) + " Ante una emergencia, el lugar de evacuación lo indica Defensa Civil.</p>" +
      notaFuente({ fuente: "OpenStreetMap", ref: p.ref })
    );
  }

  function popupTorre(p) {
    const kv = (p.tension_kv || []).map(function (v) { return String(v).replace(".", ",") + " kV"; }).join(" y ");
    return (
      "<h3>" + (p.power === "tower" ? "Torre" : "Poste") + " de línea eléctrica" + (kv ? ", " + esc(kv) : "") + "</h3>" +
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

  // Postes de la vía pública (OpenStreetMap).
  function popupPoste(p) {
    const filas = [];
    if (p.operator) filas.push(["Operador (según OSM)", p.operator]);
    if (p.material) filas.push(["Material", p.material]);
    if (p.height) filas.push(["Altura", p.height + " m"]);
    return (
      "<h3>" + esc(p.tipo) + "</h3>" +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      '<p class="nota">Fuente: ' + enlace("https://www.openstreetmap.org/" + p.osm, "OpenStreetMap, " + p.osm) + " (ODbL).</p>"
    );
  }

  // Antenas y torres de comunicaciones (OpenStreetMap).
  function popupEnvases(p) {
    const filas = [["Dirección (según la fuente)", p.direccion || "s/d"]];
    if (p.capacidad_envases) filas.push(["Capacidad", numero(p.capacidad_envases) + " envases"]);
    return (
      "<h3>Centro de acopio transitorio de envases vacíos de agroquímicos</h3>" +
      "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" +
      '<p class="nota">Guarda envases ya lavados, no productos. Fuente: Secretaría de Agricultura, Ganadería y Pesca (Ley 27.279), datos de 2019, CC BY 4.0.</p>'
    );
  }

  // Sustancias peligrosas: uno o varios establecimientos de los listados de la Secretaría de Energía en un mismo punto.
  function popupSustancias(p) {
    const registros = p.registros;
    return (
      "<h3>" + esc(registros.length === 1 ? registros[0].tipo : registros.length + " establecimientos en este punto") + "</h3>" +
      registros.map(function (r) {
        const filas = [];
        if (registros.length > 1) filas.push(["Tipo", r.tipo]);
        if (r.detalle) filas.push(["Detalle", r.detalle]);
        if (r.direccion) filas.push(["Dirección (según la fuente)", r.direccion]);
        if (r.localidad) filas.push(["Localidad", r.localidad]);
        return (
          '<div class="registro">' +
          "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" +
          '<div class="nota">Ubicación del punto: ' + esc(r.punto) + "</div>" +
          '<div class="nota">Fuente: ' + esc(r.fuente) + ", Secretaría de Energía (CC BY 4.0).</div>" +
          "</div>"
        );
      }).join("") +
      '<p class="nota">No informa cantidades almacenadas. No se publican titulares ni datos de contacto.</p>'
    );
  }

  function popupAntena(p) {
    const tipos = { mast: "Mástil", tower: "Torre", antenna: "Antena", communications_tower: "Torre de comunicaciones" };
    const servicios = { mobile_phone: "telefonía móvil", radio: "radio", television: "televisión", amateur_radio: "radioaficionados", microwave: "microondas" };
    const usos = Object.keys(p).filter(function (k) { return k.indexOf("communication:") === 0 && p[k] !== "no"; })
      .map(function (k) { return servicios[k.slice(14)] || k.slice(14); });
    const filas = [];
    if (p.tipo) filas.push(["Clasificación", p.tipo]);
    if (usos.length) filas.push(["Uso", usos.join(", ")]);
    if (p.operator) filas.push(["Operador (según OSM)", p.operator]);
    if (p.height) filas.push(["Altura", p.height + " m"]);
    return (
      "<h3>" + esc(p.name || tipos[p.man_made] || "Antena") + "</h3>" +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      (p.nota ? '<p class="nota">' + esc(p.nota) + "</p>" : "") +
      '<p class="nota">Fuente: ' + enlace("https://www.openstreetmap.org/" + p.osm, "OpenStreetMap, " + p.osm) + " (ODbL).</p>"
    );
  }

  // Barrios populares (RENABAP): condiciones del barrio, no de personas.
  function popupBarrio(p) {
    const titulo = { SI: "Mayoritariamente sí", NO: "Mayoritariamente no" };
    const filas = [];
    if (p.localidad) filas.push(["Localidad", p.localidad]);
    if (p.clasificacion) filas.push(["Tipo", p.clasificacion]);
    if (p.familias) filas.push(["Familias (aprox.)", numero(p.familias)]);
    if (p.viviendas) filas.push(["Viviendas (aprox.)", numero(p.viviendas)]);
    if (p.decada) filas.push(["Origen", p.decada]);
    if (p.energia) filas.push(["Electricidad", p.energia]);
    if (p.agua) filas.push(["Agua", p.agua]);
    if (p.cloacas) filas.push(["Cloacas", p.cloacas]);
    if (p.cocina) filas.push(["Cocina", p.cocina]);
    if (p.calefaccion) filas.push(["Calefacción", p.calefaccion]);
    if (p.titulo) filas.push(["Título de propiedad", titulo[p.titulo] || p.titulo]);
    return (
      "<h3>" + esc(p.nombre || "Barrio popular") + "</h3>" +
      "<div>Barrio popular del RENABAP</div>" +
      "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" +
      '<p class="nota">Fuente: ' + enlace("https://datos.gob.ar/dataset/registro-nacional-de-barrios-populares", "Subsecretaría de Integración Socio Urbana, RENABAP") + ", corte del 05/12/2023 (Creative Commons Atribución).</p>"
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
          (r.punto ? '<div class="nota">Ubicación del punto: ' + esc(r.punto) + "</div>" : "") +
          '<div class="nota">Fuente: ' + enlace(r.fuente_url, r.fuente_medio + (r.fuente_fecha ? ", " + fecha(r.fuente_fecha) : "")) + "</div>" +
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
    if (p.ten !== undefined) filas.push(["Tensión", TENSION_IGN[p.ten] || "s/d"]);
    if (p.fun !== undefined) filas.push(["Estado", ESTADO_IGN[p.fun] || "s/d"]);
    // En el catálogo del IGN, "Activo" quiere decir "capaz de funcionar completamente", no que haya servicio.
    if (p.fun === 6 && /^(Ferrocarril|Estación de ferrocarril)$/.test(p.tipo)) filas.push(["Nota", "Según el IGN, capaz de funcionar; no quiere decir que circulen trenes"]);
    if (p.fdc) filas.push(["Fuente de captura", p.fdc]);
    const titulo = p.crv !== undefined ? "Curva de nivel: " + numero(p.crv) + " m"
      : p.fna || (p.hct !== undefined && p.rtn ? (JURISDICCION_IGN[p.hct] || "Ruta") + " " + p.rtn : p.tipo);
    return (
      "<h3>" + esc(titulo) + "</h3>" +
      (filas.length ? "<table>" + filas.map(function (f) { return "<tr><td>" + esc(f[0]) + "</td><td>" + esc(f[1]) + "</td></tr>"; }).join("") + "</table>" : "") +
      '<p class="nota">' + esc(CITA_IGN) + ".</p>"
    );
  }

  // Cuenca del Quequén Grande (COHIFE): área y reparto aproximado entre partidos.
  function popupCuenca(p) {
    const partidos = Object.keys(p.partidos || {}).map(function (k) {
      return "<tr><td>" + esc(k) + "</td><td>" + esc(String(p.partidos[k]).replace(".", ",")) + " %</td></tr>";
    }).join("");
    return (
      "<h3>Cuenca del " + esc(p.nombre) + "</h3>" +
      "<div>Unos " + numero(p.area_km2) + " km² en total. Parte aproximada en cada partido:</div>" +
      (partidos ? "<table>" + partidos + "</table>" : "") +
      '<p class="nota">Fuente: Secretaría de Energía de la Nación, Consejo Hídrico Federal (COHIFE), CC BY 4.0. El área y el reparto se calcularon sobre este polígono y son aproximados.</p>'
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

  function trazoDe(e, tipo) {
    if (!e.lineas || !tipo) return null;
    if (tipo in e.lineas) return e.lineas[tipo];
    return tipo.indexOf("Subterr") === 0 ? e.lineas["Subterránea"] : e.lineas["Aérea"];
  }

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
        // Trazo por tipo (red hídrica de la cuenca: perenne, intermitente, zanja). En media tensión,
        // los tipos que no están en la lista se agrupan en aéreo o subterráneo.
        dashArray: trazoDe(e, feature.properties.tipo) || e.trazo || null,
        fill: esArea && e.relleno !== false,
        fillColor: (esArea && e.colores && e.colores[feature.properties[e.campo_color]]) || e.relleno || e.color,
        fillOpacity: esArea && e.colores ? 0.6 : 0.45,
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
      // Lo que el IGN marca como abandonado o desmantelado va en gris punteado, sin los trazos blancos.
      const esLinea = function (f) { return f.geometry.type !== "Point" && f.geometry.type !== "MultiPoint"; };
      const activa = function (f) { return f.properties.fun === undefined || f.properties.fun === 6; };
      const base = L.geoJSON(datos, {
        style: function (f) {
          return activa(f)
            ? { color: e.color, weight: 5, pane: "dibujo", renderer: lienzo("dibujo") }
            : { color: COLOR_FUERA_DE_USO, weight: 3, dashArray: "2 6", pane: "dibujo", renderer: lienzo("dibujo") };
        },
        attribution: ATRIBUCION_IGN,
        pointToLayer: function (f, latlng) {
          return L.circleMarker(latlng, { pane: "dibujo", renderer: lienzo("dibujo"), radius: 4, color: activa(f) ? e.color : COLOR_FUERA_DE_USO, weight: 2, fillColor: "#ffffff", fillOpacity: 1 });
        },
        onEachFeature: function (f, l) { l.bindPopup(function () { return popupIgn(f.properties); }); },
      });
      const trazos = L.geoJSON(datos, { filter: function (f) { return esLinea(f) && activa(f); }, style: { color: "#ffffff", weight: 2.5, dashArray: "7 7", pane: "dibujo", renderer: lienzo("dibujo") }, interactive: false });
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
          // Organismos de respuesta: un color por organismo; refugios: un color por uso.
          fillColor: (e.colores && e.colores[f.properties[e.campo_color || "organismo"]]) || e.color,
          fillOpacity: 0.85,
        });
      },
      onEachFeature: function (f, l) {
        if (capa.id === "limite") return;
        l.bindPopup(function () {
          if (capa.id === "inventario_local") return popupInventario(f.properties);
          if (capa.id === "organismos") return popupOrganismo(f.properties);
          if (capa.id === "refugios") return popupRefugio(f.properties);
          if (capa.id === "servicios_playa") return popupPlaya(f.properties);
          if (capa.id === "red_asistencia") return popupAsistencia(f.properties);
          if (capa.id === "conectividad_localidades") return popupConectividad(f.properties);
          if (capa.id === "gasoductos") return popupGasoducto(f.properties);
          if (capa.id === "poblacion_radios") return popupPoblacion(f.properties);
          if (capa.id === "vulnerabilidad_radios") return popupVulnerabilidad(f.properties);
          if (capa.id === "media_tension") return popupMediaTension(f.properties);
          if (capa.id === "torres_postes") return popupTorre(f.properties);
          if (capa.id === "postes_via_publica") return popupPoste(f.properties);
          if (capa.id === "barrios_populares") return popupBarrio(f.properties);
          if (capa.id === "antenas") return popupAntena(f.properties);
          if (capa.id === "envases_fitosanitarios") return popupEnvases(f.properties);
          if (capa.id === "sustancias_peligrosas") return popupSustancias(f.properties);
          if (capa.id === "cuenca_quequen") return popupCuenca(f.properties);
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
    // Capas que exceden el partido (la cuenca del Quequén): al activarlas, el mapa se aleja para mostrarlas enteras.
    if ((capa.estilo || {}).encuadrar) mapa.fitBounds(nueva.getBounds(), { padding: [16, 16] });
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
    // Leyenda por organismo, con la cantidad de cada uno (0 = todavía sin cargar).
    const colores = (capa.estilo || {}).colores;
    const lineas = (capa.estilo || {}).lineas;
    const leyenda = !verificada ? ""
      : colores ? '<ul class="leyenda-tipos">' + Object.keys(colores).map(function (k) {
          const n = (capa.por_organismo || capa.por_tipo || {})[k] || 0;
          return '<li><span class="punto-leyenda" style="background:' + esc(colores[k]) + '"></span>' + esc(k) + " (" + numero(n) + ")</li>";
        }).join("") + "</ul>"
      : (capa.estilo || {}).bicolor && capa.por_tipo ? '<ul class="leyenda-tipos">' + Object.keys(capa.por_tipo).sort().map(function (k) {
          const estacion = k.indexOf("Estación") === 0;
          const enUso = / activa$/.test(k);
          const muestra = estacion
            ? '<span class="punto-leyenda estacion" style="border-color:' + (enUso ? "#222" : COLOR_FUERA_DE_USO) + '"></span>'
            : enUso ? '<span class="muestra ferro"></span>'
            : '<span class="linea-leyenda punteada" style="border-color:' + COLOR_FUERA_DE_USO + '"></span>';
          return "<li>" + muestra + esc(k) + (enUso ? " según el IGN" : "") + " (" + numero(capa.por_tipo[k]) + ")</li>";
        }).join("") + "</ul>"
      : lineas ? '<ul class="leyenda-tipos">' + Object.keys(lineas).map(function (k) {
          const n = (capa.por_tipo || {})[k] || 0;
          return '<li><span class="linea-leyenda' + (lineas[k] ? " punteada" : "") + '" style="border-color:' + esc(capa.estilo.color) + '"></span>' + esc(k) + " (" + numero(n) + ")</li>";
        }).join("") + "</ul>"
      : "";
    div.innerHTML =
      '<div class="capa-fila">' +
      (verificada
        ? '<label><input type="checkbox" id="casilla-' + esc(capa.id) + '"' + (capa.activa_al_inicio ? " checked" : "") + ">" +
          muestraDe(capa) + '<span><span class="capa-nombre">' + esc(capa.nombre) + "</span><br>" + cuenta + "</span></label>"
        : "<label>" + muestraDe(capa) + '<span><span class="capa-nombre">' + esc(capa.nombre) + '</span><br><span class="etiqueta-pendiente">pendiente de fuente</span></span></label>') +
      '<button type="button" class="capa-info" aria-expanded="false" aria-controls="ficha-' + esc(capa.id) + '">Fuente</button>' +
      "</div>" + leyenda +
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
