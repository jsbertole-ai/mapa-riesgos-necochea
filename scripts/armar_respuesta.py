"""Arma las capas "Organismos de respuesta" y "Lugares de refugio".

Uso:  python3 scripts/armar_respuesta.py            (consulta el IGN y la API de OSM, y arma)
      python3 scripts/armar_respuesta.py --offline  (arma con lo guardado en datos/crudos/)

Organismos de respuesta: una sola capa con todos los cuerpos que intervienen en la gestión del
riesgo (decisión de Sebastián, 27/09/2026), cada uno con su color.
  - IGN (WFS, términos del IGN): policía, Prefectura Naval y bomberos, de las capas
    estructuras_operativas_y_defensivas_FA517 y _090102.
  - OpenStreetMap (consulta "respuesta" de descargar_osm.py, ODbL): Defensa Civil, Centro
    Operativo de Monitoreo, guardavidas, guardaparques, Cruz Roja, y policía, Prefectura o
    bomberos que el IGN no tenga. Un elemento de OSM a menos de 200 m de uno del IGN del mismo
    organismo se descarta: queda el del IGN.
  Las áreas (edificios, predios) se publican como su punto central, para que cada organismo se
  vea con un mismo símbolo.

Lugares de refugio: los que lista datos/refugios.json, con nombre y geometría tomados de la
API de OpenStreetMap por su identificador (no depende de Overpass).
"""

import json
import math
import sys

import descargar_ign
import descargar_osm
from comun import (CRUDOS, RAIZ, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion, descargar,
                   escribir_json, leer_json, poligonos, punto_en_geometria, sha256, vertices)

CAPAS_IGN = ("estructuras_operativas_y_defensivas_FA517", "estructuras_operativas_y_defensivas_090102")
REFUGIOS = RAIZ / "datos" / "refugios.json"
API_OSM = "https://api.openstreetmap.org/api/0.6"
DISTANCIA_DUPLICADO_M = 200
DECIMALES = 5


def centro(geom):
    """Punto que representa una geometría: el centroide de su área, o el promedio de sus vértices."""
    if geom["type"] == "Point":
        return geom["coordinates"][:2]
    if geom["type"] in ("Polygon", "MultiPolygon"):
        a = cx = cy = 0.0
        for pol in poligonos(geom):
            anillo = pol[0]
            for (x1, y1), (x2, y2) in zip(anillo, anillo[1:]):
                f = x1 * y2 - x2 * y1
                a += f
                cx += (x1 + x2) * f
                cy += (y1 + y2) * f
        if a:
            return [cx / (3 * a), cy / (3 * a)]
    pts = [(x, y) for x, y, *_ in vertices(geom)]
    return [sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)]


def punto(x, y):
    return {"type": "Point", "coordinates": [round(x, DECIMALES), round(y, DECIMALES)]}


def metros(a, b):
    return math.hypot((a[0] - b[0]) * 111320 * math.cos(math.radians(a[1])), (a[1] - b[1]) * 110570)


def organismo_ign(capa, props):
    if capa.endswith("_090102"):
        return "Bomberos"
    if "prefectura" in (props.get("gna") or "").lower():
        return "Prefectura Naval"
    return "Policía"


def organismos_ign(offline, limite, caja):
    features, huellas = [], {}
    for capa in CAPAS_IGN:
        ruta = CRUDOS / "ign" / f"{capa}.geojson"
        if not offline:
            try:
                descargar(descargar_ign.consulta(capa, caja), ruta, timeout=180)
            except ErrorRed as e:
                aviso(f"{capa}: {e}")
        if not ruta.exists():
            raise FileNotFoundError(ruta)
        crudo = ruta.read_bytes()
        huellas[capa] = sha256(crudo)
        for f in json.loads(crudo).get("features", []):
            geom = f.get("geometry")
            if not geom or not any(punto_en_geometria(x, y, limite, caja) for x, y, *_ in vertices(geom)):
                continue
            p = f.get("properties") or {}
            x, y = centro(geom)
            features.append({"type": "Feature", "geometry": punto(x, y), "properties": {
                "organismo": organismo_ign(capa, p), "nombre": p.get("fna"), "fuente": "IGN", "ref": f.get("id"),
                "fuente_captura": p.get("fdc")}})
    return features, huellas


def organismos_osm(limite, caja):
    ruta = CRUDOS / "osm" / "respuesta.json"
    if not ruta.exists():
        aviso("Falta la respuesta de Overpass (datos/crudos/osm/respuesta.json): solo se usa el IGN.")
        return [], None, None, {}
    crudo = ruta.read_bytes()
    salidas, descartes, fecha = descargar_osm.procesar("respuesta", crudo, limite, caja)
    features = []
    for f in salidas.get("organismos", []):
        p = f["properties"]
        x, y = centro(f["geometry"])
        props = {"organismo": p["organismo"], "nombre": p.get("name") or p.get("official_name"), "fuente": "OpenStreetMap",
                 "ref": p["osm"]}
        for k in ("official_name", "description", "lifeguard", "seasonal"):
            if p.get(k):
                props[k] = p[k]
        features.append({"type": "Feature", "geometry": punto(x, y), "properties": props})
    return features, sha256(crudo), fecha, descartes


def refugios(offline, limite, caja):
    lista = leer_json(REFUGIOS, {"refugios": []})["refugios"]
    features, fechas = [], []
    for r in lista:
        tipo_el, ident = r["osm"].split("/")
        ruta = CRUDOS / "osm" / "refugios" / f"{tipo_el}_{ident}.json"
        if not offline:
            try:
                descargar(f"{API_OSM}/{r['osm']}{'/full' if tipo_el != 'node' else ''}.json", ruta, timeout=60)
            except ErrorRed as e:
                aviso(f"{r['osm']}: {e}")
        if not ruta.exists():
            aviso(f"{r['osm']}: sin datos guardados; no se publica.")
            continue
        elementos = json.loads(ruta.read_bytes())["elements"]
        el = next(e for e in elementos if e["type"] == tipo_el and str(e["id"]) == ident)
        if tipo_el == "node":
            x, y = el["lon"], el["lat"]
        else:
            nodos = {e["id"]: (e["lon"], e["lat"]) for e in elementos if e["type"] == "node"}
            anillo = [list(nodos[n]) for n in el["nodes"]]
            x, y = centro({"type": "Polygon", "coordinates": [anillo]})
        if not punto_en_geometria(x, y, limite, caja):
            aviso(f"{r['osm']}: cae fuera del partido; no se publica.")
            continue
        tags = el.get("tags") or {}
        fechas.append(el.get("timestamp", "")[:10])
        features.append({"type": "Feature", "geometry": punto(x, y), "properties": {
            "nombre": tags.get("name"), "tipo": r["tipo"], "fuente": r["fuente"], "ref": r["osm"],
            "version_osm": el.get("version")}})
    return features, fechas


def main():
    offline = "--offline" in sys.argv
    limite, caja = cargar_limite()
    try:
        ign, huellas_ign = organismos_ign(offline, limite, caja)
    except FileNotFoundError as e:
        aviso(f"Falta {e}: sin el IGN no se arma la capa de organismos.")
        return 1
    osm, huella_osm, fecha_osm, descartes = organismos_osm(limite, caja)
    quedan = [f for f in osm if not any(
        g["properties"]["organismo"] == f["properties"]["organismo"]
        and metros(g["geometry"]["coordinates"], f["geometry"]["coordinates"]) < DISTANCIA_DUPLICADO_M for g in ign)]
    features = sorted(ign + quedan, key=lambda f: (f["properties"]["organismo"], f["properties"].get("nombre") or ""))
    por_organismo = {}
    for f in features:
        por_organismo[f["properties"]["organismo"]] = por_organismo.get(f["properties"]["organismo"], 0) + 1
    escribir_json(SITIO_DATOS / "organismos.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("organismos", {
        "archivo_crudo": "osm/respuesta.json",
        "sha256_crudo": huella_osm,
        "sha256_crudos_ign": huellas_ign,
        "elementos": len(features),
        "por_organismo": por_organismo,
        "descartados_por_duplicar_al_ign": len(osm) - len(quedan),
        "descartes_de_la_consulta": descartes,
        "fecha_datos": (f"OpenStreetMap al {fecha_osm} (UTC); IGN sin fecha informada." if fecha_osm
                        else "IGN sin fecha informada."),
    })
    print(f"Organismos de respuesta: {len(features)} ({por_organismo}); IGN {len(ign)}, OSM {len(osm)}, "
          f"{len(osm) - len(quedan)} de OSM descartados por duplicar al IGN.")

    ref, fechas = refugios(offline, limite, caja)
    escribir_json(SITIO_DATOS / "refugios.geojson", coleccion(ref), compacto=True)
    anotar_procesamiento("refugios", {
        "archivo_crudo": "osm/refugios/",
        "elementos": len(ref),
        "fecha_datos": max(fechas) if fechas else None,
    })
    print(f"Lugares de refugio: {len(ref)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
