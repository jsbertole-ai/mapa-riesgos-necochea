"""Procesa la exportación de KoboToolbox del inventario local de eventos y vulnerabilidades.

Uso:  python3 scripts/procesar_inventario.py

Lee el CSV más reciente de datos/crudos/inventario/ (exportación de KoboToolbox en CSV
con "XML values and headers"; Kobo usa punto y coma como separador) y datos/inventario/registros_proyecto.csv
(registros que arma el proyecto a partir del archivo de prensa, con las mismas columnas que la exportación), y
publica solo los registros que Sebastián marcó como aprobados (en Kobo, o en la columna _validation_status del
archivo del proyecto). Cada registro aprobado pasa además estos controles; si falla uno,
no se publica y el motivo se informa en pantalla (nunca en un archivo público):

  1. campos obligatorios completos y valores dentro de las listas de formulario.json;
  2. fechas válidas (entre 1900 y hoy; día/mes/año o año-mes-día), evento desde el 1/1/1980 (criterio de Sebastián,
     28/09/2026: incluye la inundación de abril de 1980, la mayor registrada) y enlace que
     empieza con http:// o https://;
  3. cantidades enteras mayores o iguales a cero;
  4. sin rastros de datos personales en el lugar ni en la descripción (correos,
     teléfonos, DNI); las direcciones con número sí se publican (decisión de Sebastián,
     02/10/2026: el punto va en el lugar exacto, también si es una vivienda);
  5. si trae un punto, que caiga dentro del partido.

Los registros con exactamente el mismo punto comparten marcador. Los registros sin punto se ubican en el punto de su
localidad (IGN, BAHRA) y se agrupan: el mapa muestra un solo marcador por localidad, aclarado como ubicación
por localidad, no como lugar del evento. Los registros de "zona rural" sin punto
solo cuentan en el resumen.

Nunca se publican el título de la nota, el usuario de Kobo ni ningún campo que
no esté en la lista de campos publicados.

Escribe docs/datos/inventario_local.geojson y docs/datos/inventario_resumen.json.
"""

import csv
import datetime as dt
import io
import json
import re
import sys
import urllib.parse

from comun import (CRUDOS, RAIZ, SITIO_DATOS, anotar_procesamiento, aviso, cargar_limite, coleccion, escribir_json,
                   leer_json, punto_en_geometria, sha256)

CONFIG = RAIZ / "datos" / "inventario" / "formulario.json"
CARPETA = CRUDOS / "inventario"
# Comienzo del período del inventario (decisión de Sebastián, 28/09/2026; antes eran los últimos 100 años).
DESDE = dt.date(1980, 1, 1)
# Registros cargados por el proyecto desde notas de prensa (público: solo lleva campos publicables y la nota de origen).
PROYECTO = RAIZ / "datos" / "inventario" / "registros_proyecto.csv"

# Columna y valores del estado de validación en la exportación de Kobo: el identificador con
# "XML values and headers" y la etiqueta en inglés con "Labels" (fijos en el código de KoboToolbox,
# DEFAULT_VALIDATION_STATUSES, sin traducción).
COLUMNA_VALIDACION = "_validation_status"
APROBADO = {"validation_status_approved", "Approved"}

# El formulario simplificado (decisión de Sebastián, 03/10/2026) ya no pide medio ni fecha de la fuente:
# los completa quien revisa al aprobar el registro, y si faltan, la ventana muestra el sitio del enlace.
OBLIGATORIOS_COMUNES = ("tipo_registro", "fecha", "localidad", "descripcion", "fuente_url", "licencia")

RASTROS_PERSONALES = [
    ("correo electrónico", re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")),
    ("teléfono", re.compile(r"(\+?54[\s-]?)?(\(?0?\d{2,4}\)?[\s-]?)?\d{2,4}[\s-]\d{4}\b|\b\d{8,}\b")),
    ("DNI", re.compile(r"\bD\.?\s?N\.?\s?I\b|\b\d{1,2}\.\d{3}\.\d{3}\b", re.I)),
]


# En los textos libres, [texto](https://...) se muestra como enlace en la ventana del mapa. Para los topes de largo
# y el control de datos personales cuenta solo el texto visible: la dirección no es parte de lo que se lee.
ENLACE_MARCADO = re.compile(r"\[([^\]]+)\]\(https?://[^\s)]+\)")


def visible(texto):
    return ENLACE_MARCADO.sub(r"\1", texto)


def leer_csv(ruta):
    texto = ruta.read_bytes().decode("utf-8-sig")
    primera = texto.splitlines()[0] if texto else ""
    separador = max((";", ",", "\t"), key=primera.count)
    return list(csv.DictReader(io.StringIO(texto), delimiter=separador))


def fecha_valida(valor):
    """Acepta dd/mm/aaaa (el formulario, desde el 03/10/2026) y aaaa-mm-dd (envíos anteriores y registros del proyecto)."""
    valor = (valor or "").strip()
    try:
        m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", valor)
        d = dt.date(int(m[3]), int(m[2]), int(m[1])) if m else dt.date.fromisoformat(valor[:10])
    except ValueError:
        return None
    return d if dt.date(1900, 1, 1) <= d <= dt.date.today() else None


def punto(fila):
    """Devuelve (lon, lat) del geopoint de Kobo ("lat lon alt precisión") o None."""
    partes = (fila.get("ubicacion") or "").split()
    if len(partes) < 2:
        lat, lon = fila.get("_ubicacion_latitude"), fila.get("_ubicacion_longitude")
        partes = [lat, lon] if lat and lon else []
    try:
        return (round(float(partes[1]), 5), round(float(partes[0]), 5)) if partes else None
    except ValueError:
        return False


def controlar(fila, cfg, etiquetas, limite, caja):
    """Devuelve (registro publicable, None) o (None, motivo)."""
    tipo = fila.get("tipo_registro")
    obligatorios = OBLIGATORIOS_COMUNES + (("tipo_evento",) if tipo == "evento" else ("tipo_vulnerabilidad",))
    faltan = [k for k in obligatorios if not (fila.get(k) or "").strip()]
    if faltan:
        return None, "faltan campos obligatorios: " + ", ".join(faltan)
    if tipo not in ("evento", "vulnerabilidad"):
        return None, f"tipo de registro desconocido ({tipo})"
    lista = "tipo_evento" if tipo == "evento" else "tipo_vulnerabilidad"
    for campo, lista_cfg in ((lista, lista), ("localidad", "localidades")):
        if fila[campo] not in etiquetas[lista_cfg]:
            return None, f"{campo} fuera de la lista ({fila[campo]})"
    servicios = (fila.get("servicios_afectados") or "").split() if tipo == "evento" else []
    if any(s not in etiquetas["servicios"] for s in servicios):
        return None, "servicio afectado fuera de la lista"
    fecha = fecha_valida(fila["fecha"])
    fecha_nota = fecha_valida(fila.get("fuente_fecha")) if (fila.get("fuente_fecha") or "").strip() else None
    if not fecha or ((fila.get("fuente_fecha") or "").strip() and not fecha_nota):
        return None, "fecha inválida"
    if fecha < DESDE:
        return None, f"evento anterior al {DESDE.strftime('%d/%m/%Y')} (fuera del período del inventario)"
    url = fila["fuente_url"].strip()
    if not re.match(r"^https?://\S+$", url):
        return None, "enlace inválido"
    efectos = {}
    if tipo == "evento":
        for e in cfg["efectos"]:
            v = (fila.get(e["name"]) or "").strip()
            if not v:
                continue
            if e.get("tipo") == "decimal":
                if not re.fullmatch(r"\d+(\.\d+)?", v):
                    return None, f"cantidad inválida en {e['name']} ({v})"
                efectos[e["label"]] = float(v)
            else:
                if not re.fullmatch(r"\d+", v):
                    return None, f"cantidad inválida en {e['name']} ({v})"
                efectos[e["label"]] = int(v)
    lugar = (fila.get("lugar") or "").strip()
    # De dónde sale el punto (solo en los registros del proyecto): un lugar público que la nota nombra,
    # tomado de una capa verificada; nunca una dirección convertida en coordenadas.
    punto_fuente = (fila.get("ubicacion_fuente") or "").strip()
    descripcion = fila["descripcion"].strip()
    observaciones = (fila.get("observaciones_efectos") or "").strip() if tipo == "evento" else ""
    if (len(visible(lugar)) > 120 or len(visible(descripcion)) > 400 or len(visible(observaciones)) > 300
            or len(visible(punto_fuente)) > 200 or len(descripcion) + len(observaciones) + len(punto_fuente) > 1200):
        return None, "texto más largo que lo permitido"
    for nombre, patron in RASTROS_PERSONALES:
        if any(patron.search(visible(t)) for t in (lugar, descripcion, observaciones, punto_fuente)):
            return None, f"posible dato personal ({nombre}); revisar y corregir en Kobo"
    p = punto(fila)
    if p is False:
        return None, "punto con coordenadas ilegibles"
    if p and not punto_en_geometria(p[0], p[1], limite, caja):
        return None, "el punto cae fuera del partido"
    registro = {
        "id": fila.get("_id") or fila.get("_uuid"),
        "tipo_registro": tipo,
        "tipo": etiquetas[lista][fila[lista]],
        "fecha": fecha.isoformat(),
        "localidad": etiquetas["localidades"][fila["localidad"]],
        "lugar": lugar or None,
        "efectos": efectos,
        "observaciones_efectos": observaciones or None,
        "servicios": [etiquetas["servicios"][s] for s in servicios],
        "punto": punto_fuente if p and punto_fuente else None,
        "descripcion": descripcion,
        "fuente_medio": (fila.get("fuente_medio") or "").strip() or urllib.parse.urlsplit(url).hostname.removeprefix("www."),
        "fuente_fecha": fecha_nota.isoformat() if fecha_nota else None,
        "fuente_url": url,
    }
    return (registro, p, fila["localidad"]), None


def puntos_localidad(cfg):
    """Punto de cada localidad del formulario, tomado de la capa de localidades del IGN."""
    fc = leer_json(SITIO_DATOS / "localidades.geojson", {"features": []})
    por_nombre = {}
    for f in fc["features"]:
        c = f["geometry"]["coordinates"]
        por_nombre[f["properties"].get("fna")] = c[0] if f["geometry"]["type"] == "MultiPoint" else c
    return {l["name"]: por_nombre.get(l.get("ign")) for l in cfg["localidades"]}


def main():
    cfg = leer_json(CONFIG)
    # Se publica el nombre corto si lo hay (en los eventos, el de la guía de DesInventar).
    etiquetas = {clave: {t["name"]: t.get("nombre", t["label"]) for t in cfg[lista]}
                 for clave, lista in (("tipo_evento", "tipos_evento"), ("tipo_vulnerabilidad", "tipos_vulnerabilidad"),
                                      ("localidades", "localidades"), ("servicios", "servicios"))}
    exportaciones = sorted(CARPETA.glob("*.csv"), key=lambda r: r.stat().st_mtime) if CARPETA.exists() else []
    rutas = exportaciones[-1:] + ([PROYECTO] if PROYECTO.exists() else [])
    if not rutas:
        aviso(f"No hay exportaciones de Kobo en {CARPETA.relative_to(RAIZ)} ni registros del proyecto: el inventario queda como está.")
        return 0
    filas = []
    for ruta in rutas:
        propias = leer_csv(ruta)
        if propias and "tipo_registro" not in propias[0]:
            aviso(f"{ruta.name} no trae la columna tipo_registro (en Kobo, exportá con \"XML values and headers\"). No se publica nada.")
            return 1
        if propias and COLUMNA_VALIDACION not in propias[0]:
            aviso(f"{ruta.name} no trae la columna {COLUMNA_VALIDACION}: no se puede saber qué está aprobado. No se publica nada.")
            return 1
        filas += propias
    limite, caja = cargar_limite()
    ubic_localidad = puntos_localidad(cfg)

    aprobados = [f for f in filas if (f.get(COLUMNA_VALIDACION) or "").strip() in APROBADO]
    publicados, rechazos, vistos = [], [], set()
    for fila in aprobados:
        resultado, motivo = controlar(fila, cfg, etiquetas, limite, caja)
        if not resultado:
            rechazos.append((fila.get("_id"), motivo))
            continue
        # El lugar distingue eventos distintos de una misma nota (por ejemplo, dos focos de incendio el mismo día).
        clave = (resultado[0]["fuente_url"], resultado[0]["tipo"], resultado[0]["localidad"], resultado[0]["fecha"],
                 (resultado[0]["lugar"] or "").lower())
        if clave in vistos:
            rechazos.append((fila.get("_id"), "duplicado de otro registro aprobado (misma nota, tipo, localidad, fecha y lugar)"))
            continue
        vistos.add(clave)
        publicados.append(resultado)

    features, por_localidad, por_punto, sin_ubicacion = [], {}, {}, 0
    for registro, p, localidad in sorted(publicados, key=lambda r: r[0]["fecha"]):
        if p:
            # Los registros con exactamente el mismo punto (por ejemplo, el derrame de 2018 y la inspección en el
            # mismo establecimiento) comparten marcador, para que ninguno tape a los otros.
            if p in por_punto:
                por_punto[p]["properties"]["registros"].append(registro)
                continue
            por_punto[p] = {"type": "Feature", "properties": {"ubicacion": "punto", "registros": [registro]},
                            "geometry": {"type": "Point", "coordinates": list(p)}}
            features.append(por_punto[p])
        elif ubic_localidad.get(localidad):
            por_localidad.setdefault(localidad, []).append(registro)
        else:
            sin_ubicacion += 1
    for localidad, registros in por_localidad.items():
        features.append({"type": "Feature",
                         "properties": {"ubicacion": "localidad", "localidad": registros[0]["localidad"], "registros": registros},
                         "geometry": {"type": "Point", "coordinates": ubic_localidad[localidad]}})

    registros = [r for r, _, _ in publicados]
    resumen = {
        "exportacion": ", ".join(r.name for r in rutas),
        "registros_en_la_exportacion": len(filas),
        "aprobados": len(aprobados),
        "publicados": len(registros),
        "no_publicados_por_controles": len(rechazos),
        "sin_ubicacion_en_el_mapa": sin_ubicacion,
        "por_tipo": {},
        "por_anio": {},
        "por_localidad": {},
        "efectos": {},
        "periodo": [min(r["fecha"] for r in registros), max(r["fecha"] for r in registros)] if registros else None,
        "licencia": "CC BY 4.0",
    }
    for r in registros:
        for clave, valor in (("por_tipo", r["tipo"]), ("por_anio", r["fecha"][:4]), ("por_localidad", r["localidad"])):
            resumen[clave][valor] = resumen[clave].get(valor, 0) + 1
        for k, v in r["efectos"].items():
            resumen["efectos"][k] = round(resumen["efectos"].get(k, 0) + v, 2)

    for id_, motivo in rechazos:
        aviso(f"Registro {id_} aprobado pero no publicado: {motivo}.")
    if features:
        escribir_json(SITIO_DATOS / "inventario_local.geojson", coleccion(features), compacto=True)
    else:
        (SITIO_DATOS / "inventario_local.geojson").unlink(missing_ok=True)
    escribir_json(SITIO_DATOS / "inventario_resumen.json", resumen)
    anotar_procesamiento("inventario_local", {
        "archivo_crudo": ", ".join(str(r.relative_to(RAIZ)) for r in rutas),
        "sha256_crudo": {r.name: sha256(r.read_bytes()) for r in rutas},
        "elementos": len(features),
        "registros": len(registros),
        "fecha_datos": f"Registros aprobados al {dt.date.fromtimestamp(max(r.stat().st_mtime for r in rutas)).isoformat()}"
                       + (f"; eventos entre {resumen['periodo'][0]} y {resumen['periodo'][1]}" if registros else ""),
    })
    print(f"Inventario: {len(filas)} registros exportados, {len(aprobados)} aprobados, {len(registros)} publicados "
          f"en {len(features)} marcadores; {len(rechazos)} no pasaron los controles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
