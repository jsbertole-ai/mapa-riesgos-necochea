"""Arma dos capas con datos que publica la Municipalidad de Necochea (decisión de Sebastián, 05/10/2026).

Uso:  python3 scripts/descargar_municipio.py            (descarga y arma)
      python3 scripts/descargar_municipio.py --offline  (arma con lo guardado en datos/crudos/municipio/)

Zonificación (ordenamiento territorial): la capa ZONIFICACIONWEB del Visor de Información Territorial y
Urbanística de la Secretaría de Planeamiento, Obras y Servicios Públicos, hecho con qgis2web. El visor
publica la capa como GeoJSON dentro de un archivo JavaScript; se toma tal cual, sin redibujar nada. De cada
zona se publican el nombre, la sigla y las observaciones; la categoría de uso, solo para el color, sale de
datos/zonificacion_categorias.json. Las parcelas del visor (de ARBA) no se usan.

Pozos de agua y cámaras de bombeo: el mapa de Obras Sanitarias (Google My Maps, cargado por el municipio),
exportado como KML. Se publican la ubicación, el tipo y la dirección. El estado ("activado", "fuera de
servicio") no se publica: la tabla dice ser en tiempo real, pero sus fechas de actualización son de 2021 y
2022.
"""

import json
import re
import sys
import xml.etree.ElementTree as ET

from comun import (CRUDOS, RAIZ, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, coleccion, descargar,
                   escribir_json, leer_json, sha256)

ZONIFICACION_URL = "https://necochea.gov.ar/descargas/planeamiento/qgis/data/ZONIFICACIONWEB_2.js"
POZOS_URL = "https://www.google.com/maps/d/kml?mid=1MgtytVAe0iBcq8nbGEWAVSQfK1k-laSO&forcekml=1"
CRUDO_ZONIFICACION = CRUDOS / "municipio" / "ZONIFICACIONWEB_2.js"
CRUDO_POZOS = CRUDOS / "municipio" / "pozos_obras_sanitarias.kml"
CATEGORIAS = RAIZ / "datos" / "zonificacion_categorias.json"
KML = "{http://www.opengis.net/kml/2.2}"
DECIMALES = 6


def bajar(url, ruta, offline, nombre):
    if not offline:
        try:
            descargar(url, ruta, timeout=180)
        except ErrorRed as e:
            aviso(f"{nombre}: {e}")
    if not ruta.exists():
        aviso(f"Falta {ruta.relative_to(RAIZ)}: no se arma la capa {nombre}.")
        return None
    return ruta.read_bytes()


def redondear(coords):
    """Redondea las coordenadas y descarta los anillos o polígonos vacíos que trae el visor."""
    if coords and isinstance(coords[0], (int, float)):
        return [round(coords[0], DECIMALES), round(coords[1], DECIMALES)]
    return [r for r in (redondear(c) for c in coords) if r]


def texto(valor):
    """Los campos vacíos del visor llegan como null; se publican vacíos."""
    return re.sub(r"\s+", " ", str(valor)).strip() if valor not in (None, "") else None


def zonificacion(offline):
    crudo = bajar(ZONIFICACION_URL, CRUDO_ZONIFICACION, offline, "Zonificación")
    if crudo is None:
        return False
    t = crudo.decode("utf-8")
    fc = json.loads(t[t.index("{"): t.rindex("}") + 1])
    categorias = {texto(k): v for k, v in leer_json(CATEGORIAS)["categorias"].items()}
    features, sin_categoria = [], set()
    for f in fc["features"]:
        coords = redondear(f["geometry"]["coordinates"]) if f.get("geometry") else []
        if not coords:
            continue
        p = f["properties"]
        zona = texto(p.get("descripcio"))
        categoria = categorias.get(zona)
        if not categoria:
            sin_categoria.add(zona)
            categoria = "Sin categoría"
        features.append({"type": "Feature",
                         "geometry": {"type": f["geometry"]["type"], "coordinates": coords},
                         "properties": {"zona": zona, "sigla": texto(p.get("SIGLA")), "categoria": categoria,
                                        "observaciones": texto(p.get("OBSERV."))}})
    if sin_categoria:
        aviso(f"Zonas sin categoría en {CATEGORIAS.name}: {sorted(sin_categoria)}")
    escribir_json(SITIO_DATOS / "zonificacion.geojson", coleccion(features), compacto=True)
    por_tipo = {}
    for f in features:
        por_tipo[f["properties"]["categoria"]] = por_tipo.get(f["properties"]["categoria"], 0) + 1
    anotar_procesamiento("portuaria_zonificacion", {
        "archivo_crudo": "municipio/ZONIFICACIONWEB_2.js",
        "sha256_crudo": sha256(crudo),
        "elementos": len(features),
        "por_tipo": por_tipo,
        "zonas_sin_categoria": sorted(sin_categoria),
    })
    print(f"Zonificación: {len(features)} zonas ({por_tipo}).")
    return True


def pozos(offline):
    crudo = bajar(POZOS_URL, CRUDO_POZOS, offline, "Pozos y cámaras de bombeo")
    if crudo is None:
        return False
    features, fechas = [], []
    for pm in ET.fromstring(crudo).iter(KML + "Placemark"):
        nombre = (pm.findtext(KML + "name") or "").strip()
        desc = pm.findtext(KML + "description") or ""
        campos = dict(re.findall(r"([^<>:]+?):\s*([^<]*)(?:<br>|$)", desc))
        coords = (pm.findtext(".//" + KML + "coordinates") or "").split(",")
        if len(coords) < 2:
            aviso(f"{nombre}: sin coordenadas; no se publica.")
            continue
        fecha = re.match(r"(\d{1,2})/(\d{1,2})/(\d{4})", campos.get("Fecha de Actualización", "").strip())
        if fecha:
            fechas.append((int(fecha[3]), int(fecha[2]), int(fecha[1])))
        features.append({"type": "Feature",
                         "geometry": {"type": "Point", "coordinates": redondear([float(coords[0]), float(coords[1])])},
                         "properties": {"nombre": nombre, "tipo": texto(campos.get("Tipo")), "direccion": texto(campos.get("Dirección"))}})
    escribir_json(SITIO_DATOS / "agua_pozos_bombeo.geojson", coleccion(features), compacto=True)
    por_tipo = {}
    for f in features:
        por_tipo[f["properties"]["tipo"]] = por_tipo.get(f["properties"]["tipo"], 0) + 1
    rango = (f"{min(fechas)[2]:02d}/{min(fechas)[1]:02d}/{min(fechas)[0]} y {max(fechas)[2]:02d}/{max(fechas)[1]:02d}/{max(fechas)[0]}"
             if fechas else "sin fecha")
    anotar_procesamiento("agua_pozos_bombeo", {
        "archivo_crudo": "municipio/pozos_obras_sanitarias.kml",
        "sha256_crudo": sha256(crudo),
        "elementos": len(features),
        "por_tipo": por_tipo,
        # El KML del mapa y la tabla de la página no traen las mismas fechas (la tabla llega a noviembre de 2022).
        "fecha_datos": f"Mapa de Obras Sanitarias (Google My Maps del municipio); fechas de actualización de los puntos entre el {rango}.",
    })
    print(f"Pozos y cámaras de bombeo: {len(features)} ({por_tipo}); actualizaciones entre el {rango}.")
    return True


def main():
    offline = "--offline" in sys.argv
    ok = [zonificacion(offline), pozos(offline)]
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
