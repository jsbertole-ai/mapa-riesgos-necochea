"""Arma las capas "Organismos de respuesta" y "Lugares de refugio".

Uso:  python3 scripts/armar_respuesta.py            (consulta el IGN y la API de OSM, y arma)
      python3 scripts/armar_respuesta.py --offline  (arma con lo guardado en datos/crudos/)

Organismos de respuesta: una sola capa con todos los cuerpos que intervienen en la gestión del
riesgo (decisión de Sebastián, 27/09/2026), cada uno con su color. Fuentes, en orden de prioridad
(si dos fuentes traen el mismo organismo a menos de 200 m, o con el mismo nombre, queda la primera):
  - Elementos de OpenStreetMap fijados por Sebastián en datos/organismos_osm.json (por ejemplo, la
    Prefectura Naval Quequén), traídos de la API de OSM.
  - Ministerio de Seguridad de la Provincia de Buenos Aires, conjunto "Comisarías" de Datos
    Abiertos PBA (CC BY 4.0): las dependencias del partido que traen coordenadas.
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

import csv
import io
import json
import math
import re
import sys
import unicodedata

import descargar_ign
import descargar_osm
from comun import (CRUDOS, RAIZ, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion, descargar,
                   escribir_json, leer_json, poligonos, punto_en_geometria, sha256, vertices)

CAPAS_IGN = ("estructuras_operativas_y_defensivas_FA517", "estructuras_operativas_y_defensivas_090102")
REFUGIOS = RAIZ / "datos" / "refugios.json"
FIJADOS_OSM = RAIZ / "datos" / "organismos_osm.json"
COMISARIAS_PBA = ("https://catalogo.datos.gba.gob.ar/dataset/bf79faeb-cb8a-4444-bbbe-5dc39479aa4a/resource/"
                  "8d31bb16-3489-4ede-9e63-072f7f17383d/download/comisarias-pba-2026.csv")
CODIGO_PBA = "6581"
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


def clave_nombre(nombre):
    """Palabras de un nombre sin tildes ni ordinales, para reconocer la misma dependencia en dos fuentes."""
    t = unicodedata.normalize("NFD", (nombre or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return set(re.findall(r"[a-z]+|\d+", t)) - {"n", "de", "la", "y"}


def mismo(a, b):
    pa, pb = a["properties"], b["properties"]
    if pa["organismo"] != pb["organismo"]:
        return False
    if metros(a["geometry"]["coordinates"], b["geometry"]["coordinates"]) < DISTANCIA_DUPLICADO_M:
        return True
    ka, kb = clave_nombre(pa.get("nombre")), clave_nombre(pb.get("nombre"))
    return bool(ka) and bool(kb) and (ka <= kb or kb <= ka)


def unir(*fuentes):
    """Une listas de elementos en orden de prioridad; descarta los que repiten uno ya incluido."""
    todos, descartados = [], 0
    for lista in fuentes:
        for f in lista:
            if any(mismo(f, g) for g in todos):
                descartados += 1
            else:
                todos.append(f)
    return todos, descartados


def geometria_api(ruta, tipo_el, ident):
    elementos = json.loads(ruta.read_bytes())["elements"]
    el = next(e for e in elementos if e["type"] == tipo_el and str(e["id"]) == ident)
    if tipo_el == "node":
        return el, (el["lon"], el["lat"])
    nodos = {e["id"]: (e["lon"], e["lat"]) for e in elementos if e["type"] == "node"}
    anillo = [list(nodos[n]) for n in el["nodes"]]
    return el, tuple(centro({"type": "Polygon", "coordinates": [anillo]}))


def bajar_api(osm, offline, carpeta):
    tipo_el, ident = osm.split("/")
    ruta = CRUDOS / "osm" / carpeta / f"{tipo_el}_{ident}.json"
    if not offline:
        try:
            descargar(f"{API_OSM}/{osm}{'/full' if tipo_el != 'node' else ''}.json", ruta, timeout=60)
        except ErrorRed as e:
            aviso(f"{osm}: {e}")
    return (ruta, tipo_el, ident) if ruta.exists() else None


def organismos_fijados(offline, limite, caja):
    features = []
    for r in leer_json(FIJADOS_OSM, {"elementos": []})["elementos"]:
        bajado = bajar_api(r["osm"], offline, "organismos")
        if not bajado:
            aviso(f"{r['osm']}: sin datos guardados; no se publica.")
            continue
        el, (x, y) = geometria_api(*bajado)
        if not punto_en_geometria(x, y, limite, caja):
            continue
        tags = el.get("tags") or {}
        features.append({"type": "Feature", "geometry": punto(x, y), "properties": {
            "organismo": r["organismo"], "nombre": tags.get("name") or r.get("nombre"), "fuente": "OpenStreetMap",
            "ref": r["osm"], "nota": r.get("fuente")}})
    return features


def comisarias_pba(offline, limite, caja):
    ruta = CRUDOS / "pba" / "comisarias-pba-2026.csv"
    if not offline:
        try:
            descargar(COMISARIAS_PBA, ruta, timeout=120)
        except ErrorRed as e:
            aviso(f"Comisarías PBA: {e}")
    if not ruta.exists():
        aviso("Faltan las comisarías de la Provincia: se usan las del IGN.")
        return [], None, []
    crudo = ruta.read_bytes()
    texto = crudo.decode("utf-8-sig", errors="replace")
    separador = max((";", ","), key=texto.splitlines()[0].count)
    features, sin_coordenadas = [], []
    for fila in csv.DictReader(io.StringIO(texto), delimiter=separador):
        if fila.get("municipio_id") != CODIGO_PBA:
            continue
        try:
            x, y = float(fila["longitud"]), float(fila["latitud"])
        except (TypeError, ValueError):
            # Una dirección no se convierte en coordenadas (sería estimar): queda la del IGN, si la hay.
            sin_coordenadas.append(fila.get("dependencia"))
            continue
        if not punto_en_geometria(x, y, limite, caja):
            continue
        features.append({"type": "Feature", "geometry": punto(x, y), "properties": {
            "organismo": "Policía", "nombre": fila.get("dependencia"), "fuente": "Provincia de Buenos Aires",
            "localidad": fila.get("localidad")}})
    return features, sha256(crudo), sin_coordenadas


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
        bajado = bajar_api(r["osm"], offline, "refugios")
        if not bajado:
            aviso(f"{r['osm']}: sin datos guardados; no se publica.")
            continue
        el, (x, y) = geometria_api(*bajado)
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
    fijados = organismos_fijados(offline, limite, caja)
    pba, huella_pba, pba_sin_coordenadas = comisarias_pba(offline, limite, caja)
    osm, huella_osm, fecha_osm, descartes = organismos_osm(limite, caja)
    unidos, duplicados = unir(fijados, pba, ign, osm)
    features = sorted(unidos, key=lambda f: (f["properties"]["organismo"], f["properties"].get("nombre") or ""))
    por_fuente = {}
    for f in features:
        por_fuente[f["properties"]["fuente"]] = por_fuente.get(f["properties"]["fuente"], 0) + 1
    por_organismo = {}
    for f in features:
        por_organismo[f["properties"]["organismo"]] = por_organismo.get(f["properties"]["organismo"], 0) + 1
    escribir_json(SITIO_DATOS / "organismos.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("organismos", {
        "archivo_crudo": "osm/respuesta.json",
        "sha256_crudo": huella_osm,
        "sha256_crudos_ign": huellas_ign,
        "sha256_comisarias_pba": huella_pba,
        "pba_sin_coordenadas": pba_sin_coordenadas,
        "elementos": len(features),
        "por_organismo": por_organismo,
        "por_fuente": por_fuente,
        "descartados_por_duplicados": duplicados,
        "descartes_de_la_consulta": descartes,
        "fecha_datos": (f"OpenStreetMap al {fecha_osm} (UTC); IGN sin fecha informada." if fecha_osm
                        else "IGN sin fecha informada."),
    })
    print(f"Organismos de respuesta: {len(features)} ({por_organismo}); por fuente {por_fuente}; "
          f"{duplicados} descartados por duplicados; PBA sin coordenadas: {pba_sin_coordenadas}.")

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
