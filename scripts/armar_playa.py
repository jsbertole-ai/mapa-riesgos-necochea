"""Arma la capa "Servicios de playa": guardavidas, postas sanitarias y de seguridad y puesto de verano de
Prefectura (aprobada por Sebastián el 05/10/2026). La base de guardaparques, que funciona todo el año, va en
"Organismos de respuesta" (datos/organismos_colaboradores.json).

Uso:  python3 scripts/armar_playa.py            (descarga el KML municipal y los elementos de OSM, y arma)
      python3 scripts/armar_playa.py --offline  (arma con lo guardado en datos/crudos/)

La lista de puntos está en datos/servicios_playa.json. Cada punto sale de una de dos fuentes:
  - el mapa "Info Zona Playa - 2023" de la Municipalidad de Necochea (Dirección de Relaciones con la
    Comunidad y DDHH, Área GIS), exportado como KML desde la página "Mapas Útiles". Los puntos los
    cargó el municipio: no son contenido de Google, que solo aloja el mapa. Se toma el punto por su
    nombre y su id dentro de la carpeta "PUNTOS DE INTERES";
  - un elemento de OpenStreetMap, traído de su API por identificador, para los puestos que el mapa
    municipal no tiene (decisión de Sebastián, 05/10/2026: un lugar con nombre o un cruce de calles).
Los puestos de playa se controlan contra la caja del partido y no contra su polígono: la costa del
límite del IGN está simplificada y deja afuera parte de la arena.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET

from armar_respuesta import bajar_api, centro, punto
from comun import (CRUDOS, RAIZ, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion,
                   descargar, escribir_json, leer_json, sha256)

LISTA = RAIZ / "datos" / "servicios_playa.json"
CRUDO_KML = CRUDOS / "municipio" / "info_zona_playa.kml"
KML_NS = {"k": "http://www.opengis.net/kml/2.2"}


def puntos_kml(contenido, carpeta):
    """Puntos de una carpeta del KML, por (nombre, id). El id va en la descripción ("id: 8")."""
    raiz = ET.fromstring(contenido)
    salida = {}
    for folder in raiz.iter("{%s}Folder" % KML_NS["k"]):
        if (folder.findtext("k:name", namespaces=KML_NS) or "").strip() != carpeta:
            continue
        for pm in folder.iter("{%s}Placemark" % KML_NS["k"]):
            nombre = (pm.findtext("k:name", namespaces=KML_NS) or "").strip()
            ident = re.search(r"id:\s*(\d+)", pm.findtext("k:description", namespaces=KML_NS) or "")
            coords = (pm.findtext(".//k:coordinates", namespaces=KML_NS) or "").split(",")
            if ident and len(coords) >= 2:
                salida[(nombre, int(ident.group(1)))] = (float(coords[0]), float(coords[1]))
    return salida


def punto_osm(osm, offline):
    bajado = bajar_api(osm, offline, "playa")
    if not bajado:
        return None, None
    ruta, tipo_el, ident = bajado
    elementos = json.loads(ruta.read_bytes())["elements"]
    el = next(e for e in elementos if e["type"] == tipo_el and str(e["id"]) == ident)
    if tipo_el == "node":
        return (el["lon"], el["lat"]), el
    nodos = {e["id"]: (e["lon"], e["lat"]) for e in elementos if e["type"] == "node"}
    linea = [list(nodos[n]) for n in el["nodes"]]
    # Un área cerrada (balneario, muelle) se publica como su punto central; una línea (un puente), como
    # el promedio de sus vértices.
    geom = {"type": "Polygon", "coordinates": [linea]} if el["nodes"][0] == el["nodes"][-1] else {"type": "LineString", "coordinates": linea}
    return tuple(centro(geom)), el


def main():
    offline = "--offline" in sys.argv
    _, caja = cargar_limite()
    lista = leer_json(LISTA)
    if not offline:
        try:
            descargar(lista["kml"]["url"], CRUDO_KML, timeout=120)
        except ErrorRed as e:
            aviso(f"Mapa municipal de playa: {e}")
    if not CRUDO_KML.exists():
        aviso("Falta el KML municipal (datos/crudos/municipio/info_zona_playa.kml): no se arma la capa.")
        return 1
    crudo = CRUDO_KML.read_bytes()
    kml = puntos_kml(crudo, lista["kml"]["carpeta"])
    features, faltan, fechas_osm = [], [], []
    for r in lista["elementos"]:
        if r.get("kml"):
            xy = kml.get((r["kml"][0], r["kml"][1]))
            origen, ref = "Mapa municipal \"Info Zona Playa - 2023\" (Área GIS de la Municipalidad de Necochea).", None
        else:
            xy, el = punto_osm(r["osm"], offline)
            origen, ref = r["origen"], r["osm"]
            if el:
                fechas_osm.append(el.get("timestamp", "")[:10])
        if not xy:
            faltan.append(r["nombre"])
            aviso(f"{r['nombre']}: no se encontró el punto; no se publica.")
            continue
        x, y = xy
        if not (caja[0] <= x <= caja[2] and caja[1] <= y <= caja[3]):
            faltan.append(r["nombre"])
            aviso(f"{r['nombre']}: cae fuera de la caja del partido; no se publica.")
            continue
        vig = lista["vigencia"][r["vigencia"]]
        features.append({"type": "Feature", "geometry": punto(x, y), "properties": {
            "nombre": r["nombre"], "tipo": r["tipo"], "temporada": r["temporada"], "origen": origen,
            **({"ref": ref} if ref else {}), **({"nota": r["nota"]} if r.get("nota") else {}),
            "vigencia": vig["texto"], **({"url_vigencia": vig["url"]} if vig.get("url") else {})}})
    escribir_json(SITIO_DATOS / "servicios_playa.geojson", coleccion(features), compacto=True)
    por_tipo = {}
    for f in features:
        por_tipo[f["properties"]["tipo"]] = por_tipo.get(f["properties"]["tipo"], 0) + 1
    anotar_procesamiento("servicios_playa", {
        "archivo_crudo": "municipio/info_zona_playa.kml",
        "sha256_kml": sha256(crudo),
        "elementos": len(features),
        "por_tipo": por_tipo,
        "no_publicados": faltan,
        "pendientes": [p["nombre"] for p in lista.get("pendientes", [])],
        "fecha_datos": ("Mapa municipal de 2023; vigencia según notas municipales de la temporada 2025-2026"
                        + (f"; OpenStreetMap al {max(fechas_osm)} (UTC)." if fechas_osm else ".")),
    })
    print(f"Servicios de playa: {len(features)} ({por_tipo}); no publicados: {faltan}.")
    return 1 if faltan else 0


if __name__ == "__main__":
    sys.exit(main())
