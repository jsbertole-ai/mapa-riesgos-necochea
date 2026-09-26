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

  function numero(n) {
    return Number(n).toLocaleString("es-AR");
  }

  function lista(partes) {
    return partes.length > 1 ? partes.slice(0, -1).join(", ") + " y " + partes[partes.length - 1] : partes.join("");
  }

  function fichaPartido(f) {
    const d = f.desinventar, iv = f.ivsd, n = iv.nacional, pr = iv.provincia;
    const eventos = Object.keys(d.eventos)
      .sort(function (a, b) { return d.eventos[b] - d.eventos[a]; })
      .map(function (k) { return k.toLowerCase() + " (" + numero(d.eventos[k]) + ")"; });
    const sin = f.sinagir || {};
    const regional = [];
    if (sin.hidrometeorologicas) regional.push("amenazas hidrometeorológicas, \"" + esc(sin.hidrometeorologicas.categoria) + "\"");
    if (sin.fisico_quimicas) regional.push("amenazas físico-químicas, \"" + esc(sin.fisico_quimicas.categoria) + "\"");
    return (
      '<section class="ficha-capa">' +
      "<h3>Eventos adversos registrados (DesInventar, " + esc(d.periodo.replace("-", " a ")) + ")</h3>" +
      "<p>La base DesInventar registra " + numero(d.registros) + " eventos de origen hidrometeorológico en el partido: " + esc(lista(eventos)) +
      ". El IGN clasifica ese total como \"" + esc(d.categoria) + "\", en cinco clases de alcance nacional.</p>" +
      "<p>Advertencia del propio IGN: \"" + esc(d.advertencia) + "\" Un evento no registrado no es un evento que no ocurrió.</p>" +
      '<p class="nota">Fuente: ' + esc(d.fuente) + ' <a href="' + esc(d.metadato) + '">Metadato de la capa</a>.</p>' +
      "</section>" +
      '<section class="ficha-capa">' +
      "<h3>Índice de vulnerabilidad social frente a desastres (IVSD 2024)</h3>" +
      "<p>Necochea tiene un IVSD de " + numero(iv.valor) + ". Entre los " + numero(n.departamentos) + " departamentos del país, el índice va de " +
      numero(n.minimo) + " a " + numero(n.maximo) + " (mediana " + numero(n.mediana) + ") y " + numero(n.con_valor_menor) + " tienen un valor menor. " +
      "Entre los " + numero(pr.departamentos) + " partidos de la provincia va de " + numero(pr.minimo) + " a " + numero(pr.maximo) +
      " (mediana " + numero(pr.mediana) + ") y " + numero(pr.con_valor_menor) + " tienen un valor menor.</p>" +
      "<p>La capa no publica la escala ni la metodología del índice. Que un valor más alto indique más vulnerabilidad es una lectura del patrón, no un dato de la fuente: en la provincia, los valores más bajos son los de " +
      esc(lista(pr.valores_mas_bajos.map(function (x) { return x.partido.replace("Partido de ", "") + " (" + numero(x.ivsd) + ")"; }))) +
      ", y los más altos, los de " +
      esc(lista(pr.valores_mas_altos.map(function (x) { return x.partido.replace("Partido de ", "") + " (" + numero(x.ivsd) + ")"; }))) + ".</p>" +
      '<p class="nota">Fuente: ' + esc(iv.fuente) + ' <a href="' + esc(iv.metadato) + '">Metadato de la capa</a>.</p>' +
      "</section>" +
      (regional.length ?
        '<section class="ficha-capa"><h3>Nivel de exposición regional (SINAGIR)</h3>' +
        "<p>Para la región Centro, que incluye a la provincia de Buenos Aires: " + regional.join("; ") +
        ". Es una clasificación regional: no distingue partidos.</p></section>" : "") +
      '<p class="nota">' + esc(f.licencia) + ". Indicadores consultados el " + esc((f.generado || "").slice(0, 10).split("-").reverse().join("/")) + ".</p>"
    );
  }

  fetch("datos/ficha_partido.json")
    .then(function (r) { return r.json(); })
    .then(function (f) { document.getElementById("ficha-partido").innerHTML = fichaPartido(f); })
    .catch(function () {
      document.getElementById("ficha-partido").innerHTML = "<p>No se pudo cargar la ficha del partido.</p>";
    });

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
