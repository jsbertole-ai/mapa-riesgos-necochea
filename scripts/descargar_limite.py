"""Límite del partido de Necochea (Georef, geometría del IGN, CC BY 4.0).

Uso:  python3 scripts/descargar_limite.py

1. Si ya hay un archivo de Georef en datos/crudos/ (bajado a mano), usa ese:
   limite_necochea_georef.geojson, o el archivo completo de departamentos
   (departamentos.geojson).
2. Si no, intenta descargarlo: primero el archivo completo enlazado desde la
   página de descargas de Georef y después la API.
3. Filtra el partido de Necochea (provincia de Buenos Aires), comprueba que
   haya una sola coincidencia con geometría poligonal y escribe
   docs/datos/limite.geojson.
"""

import json
import re
import sys
import urllib.parse

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, caja_envolvente,
                   coleccion, descargar, escribir_json, sha256)

PAGINA_DESCARGAS = "https://datosgobar.github.io/georef-ar-api/download/"
API = ("https://apis.datos.gob.ar/georef/api/departamentos"
       "?provincia=06&nombre=Necochea&campos=completo&formato=geojson&max=10")
CANDIDATOS_MANUALES = ["limite_necochea_georef.geojson", "departamentos.geojson"]

# Caja amplia de la provincia de Buenos Aires: solo sirve para descartar un archivo equivocado.
CAJA_PROVINCIA = (-63.5, -41.2, -56.5, -33.2)


def aplanar(props, prefijo=""):
    plano = {}
    for clave, valor in props.items():
        if isinstance(valor, dict):
            plano.update(aplanar(valor, f"{prefijo}{clave}_"))
        else:
            plano[f"{prefijo}{clave}"] = valor
    return plano


def es_necochea(props):
    p = aplanar(props)
    nombre = str(p.get("nombre", "")).strip().lower()
    provincia = str(p.get("provincia_nombre", p.get("provincia", ""))).lower()
    provincia_id = str(p.get("provincia_id", ""))
    return nombre == "necochea" and (provincia_id == "06" or "buenos aires" in provincia)


def buscar_archivo_manual():
    for nombre in CANDIDATOS_MANUALES:
        ruta = CRUDOS / nombre
        if ruta.exists():
            return ruta
    return None


def descargar_georef():
    """Intenta el archivo completo de departamentos; si no aparece, la API."""
    try:
        html = descargar(PAGINA_DESCARGAS).decode("utf-8", "replace")
        enlaces = re.findall(r'href="([^"]+)"', html)
        # La página enlaza CSV, JSON, GeoJSON y NDJSON; solo el GeoJSON trae los polígonos.
        geojson = [e for e in enlaces if "departamento" in e.lower() and e.lower().endswith(".geojson")]
        if geojson:
            url = urllib.parse.urljoin(PAGINA_DESCARGAS, geojson[0])
            aviso(f"Descargando {url}")
            destino = CRUDOS / "departamentos.geojson"
            descargar(url, destino)
            return destino
        aviso("La página de descargas no enlaza un GeoJSON de departamentos; pruebo la API.")
    except ErrorRed as e:
        aviso(str(e))
    aviso(f"Consultando {API}")
    destino = CRUDOS / "limite_necochea_georef.geojson"
    descargar(API, destino)
    return destino


def main():
    ruta = buscar_archivo_manual()
    if ruta:
        aviso(f"Uso el archivo que ya está en {ruta.relative_to(CRUDOS.parent.parent)}")
    else:
        try:
            ruta = descargar_georef()
        except ErrorRed as e:
            aviso(f"{e}\nSin conexión con Georef. Bajá el archivo a mano (DATOS.md, sección 5.B.1) "
                  "y guardalo en datos/crudos/limite_necochea_georef.geojson.")
            return 1

    contenido = ruta.read_bytes()
    datos = json.loads(contenido)
    features = datos.get("features") or []
    candidatos = [f for f in features if es_necochea(f.get("properties") or {})]
    if len(candidatos) != 1:
        aviso(f"Se esperaba una sola coincidencia para Necochea y hubo {len(candidatos)}. No se escribe nada.")
        return 1
    f = candidatos[0]
    geom = f.get("geometry") or {}
    if geom.get("type") not in ("Polygon", "MultiPolygon"):
        aviso(f"La coincidencia no trae polígono (llegó {geom.get('type')}). "
              "La API puede devolver solo el centroide: usá el archivo completo de departamentos.")
        return 1
    caja = caja_envolvente(geom)
    if not (CAJA_PROVINCIA[0] <= caja[0] and caja[2] <= CAJA_PROVINCIA[2]
            and CAJA_PROVINCIA[1] <= caja[1] and caja[3] <= CAJA_PROVINCIA[3]):
        aviso(f"La geometría cae fuera de la provincia de Buenos Aires ({caja}). No se escribe nada.")
        return 1

    props = aplanar(f["properties"])
    salida = coleccion([{
        "type": "Feature",
        "properties": {"nombre": props.get("nombre"), "id": props.get("id"), "fuente": props.get("fuente")},
        "geometry": geom,
    }])
    escribir_json(SITIO_DATOS / "limite.geojson", salida, compacto=True)
    anotar_procesamiento("limite", {
        "archivo_crudo": ruta.name,
        "sha256_crudo": sha256(contenido),
        "elementos": 1,
        "caja": caja,
        "atributos_origen": props,
    })
    print(f"Límite escrito en docs/datos/limite.geojson (caja {caja}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
