"""Límite del partido de Necochea, del Instituto Geográfico Nacional (IGN).

Uso:  python3 scripts/descargar_limite.py            (consulta el WFS del IGN)
      python3 scripts/descargar_limite.py --offline  (usa datos/crudos/ign/departamento_06581.geojson)

Pide al WFS del IGN la capa "Departamento" filtrada por el código del partido
(06581) y escribe docs/datos/limite.geojson. Según su atributo de fuente de
captura, la geometría viene de ARBA (Gerencia de Servicios Catastrales). Tiene
decenas de miles de vértices: todas las demás capas se recortan con ella.

Licencia: Términos y Condiciones del IGN (https://www.ign.gob.ar/descargas/tyc1.html).

Alternativa documentada en DATOS.md (0.1): Georef, con licencia CC BY 4.0, pero
con una geometría generalizada de 57 vértices.
"""

import json
import sys
import urllib.parse

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, caja_envolvente, coleccion, descargar,
                   escribir_json, poligonos, sha256)

CODIGO = "06581"
URL = "https://wms.ign.gob.ar/geoserver/wfs?" + urllib.parse.urlencode({
    "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "ign:departamento",
    "outputFormat": "application/json", "srsName": "EPSG:4326", "CQL_FILTER": f"in1='{CODIGO}'",
})
CRUDO = CRUDOS / "ign" / f"departamento_{CODIGO}.geojson"
DECIMALES = 5

# Caja amplia de la provincia de Buenos Aires: solo sirve para descartar un archivo equivocado.
CAJA_PROVINCIA = (-63.5, -41.2, -56.5, -33.2)


def redondear(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], DECIMALES), round(c[1], DECIMALES)]
    return [redondear(x) for x in c]


def main():
    if "--offline" not in sys.argv:
        try:
            descargar(URL, CRUDO, timeout=180)
        except ErrorRed as e:
            aviso(f"{e}\nSin conexión con el IGN. Bajá la capa \"Departamento\" en GeoJSON desde "
                  "https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG y guardala como "
                  f"{CRUDO.relative_to(CRUDOS.parent.parent)} (el script toma solo el partido {CODIGO}).")
    if not CRUDO.exists():
        aviso(f"Falta {CRUDO.name}: no se escribe el límite.")
        return 1

    contenido = CRUDO.read_bytes()
    features = [f for f in json.loads(contenido).get("features", [])
                if str((f.get("properties") or {}).get("in1")) == CODIGO]
    if len(features) != 1:
        aviso(f"Se esperaba un solo departamento {CODIGO} y hubo {len(features)}. No se escribe nada.")
        return 1
    f = features[0]
    geom = f.get("geometry") or {}
    if geom.get("type") not in ("Polygon", "MultiPolygon"):
        aviso(f"La geometría no es poligonal ({geom.get('type')}). No se escribe nada.")
        return 1
    geom = {"type": geom["type"], "coordinates": redondear(geom["coordinates"])}
    caja = caja_envolvente(geom)
    if not (CAJA_PROVINCIA[0] <= caja[0] and caja[2] <= CAJA_PROVINCIA[2]
            and CAJA_PROVINCIA[1] <= caja[1] and caja[3] <= CAJA_PROVINCIA[3]):
        aviso(f"La geometría cae fuera de la provincia de Buenos Aires ({caja}). No se escribe nada.")
        return 1

    p = f["properties"]
    vertices = sum(len(anillo) for pol in poligonos(geom) for anillo in pol)
    escribir_json(SITIO_DATOS / "limite.geojson", coleccion([{
        "type": "Feature",
        "properties": {"nombre": p.get("fna"), "id": p.get("in1"), "fuente_captura": p.get("fdc"), "autoridad": p.get("sag")},
        "geometry": geom,
    }]), compacto=True)
    anotar_procesamiento("limite", {
        "archivo_crudo": f"ign/{CRUDO.name}",
        "sha256_crudo": sha256(contenido),
        "elementos": 1,
        "vertices": vertices,
        "caja": caja,
        "atributos_origen": {k: v for k, v in p.items() if v not in (None, "")},
        "fecha_datos": None,
    })
    print(f"Límite del IGN escrito en docs/datos/limite.geojson: {vertices} vértices, caja {caja}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
