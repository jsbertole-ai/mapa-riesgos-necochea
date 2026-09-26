"""Capas del Instituto Geográfico Nacional (IGN) por su servicio WFS.

Uso:  python3 scripts/descargar_ign.py            (consulta el WFS y procesa)
      python3 scripts/descargar_ign.py --offline  (procesa lo ya guardado en datos/crudos/ign/)

El botón "Descargar capa" de https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG
llama a este mismo servicio (https://wms.ign.gob.ar/geoserver/...&request=GetFeature), así que rigen los
Términos y Condiciones del IGN para la información descargada de su sitio
(https://www.ign.gob.ar/descargas/tyc1.html): citar "FUENTE: Instituto Geográfico Nacional de la
República Argentina", compartir de forma libre y gratuita, no sugerir respaldo del IGN, conservar los
metadatos y mencionar la fecha de los datos originales en los productos derivados.

Se pide solo la caja envolvente del partido y después se recorta por el polígono del límite: entra
todo elemento con al menos un vértice dentro.
"""

import json
import sys
import urllib.parse

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion,
                   descargar, escribir_json, punto_en_geometria, sha256, vertices)

WFS = "https://wms.ign.gob.ar/geoserver/wfs"
DECIMALES = 5

# Capa del mapa -> capas del WFS que la forman, con la etiqueta que se muestra.
CAPAS = {
    "ferrocarril": {
        "lineas_de_transporte_ferroviario_AN010": "Ferrocarril",
    },
    "red_vial": {
        "vial_nacional": "Ruta nacional",
        "vial_provincial": "Ruta provincial",
    },
    "curvas_nivel": {
        "lineas_de_geomorfologia_CA010": "Curva de nivel",
    },
    "hidrografia_ign": {
        "lineas_de_aguas_continentales_perenne": "Corriente de agua perenne",
        "lineas_de_aguas_continentales_intermitentes": "Corriente de agua intermitente",
        "lineas_de_aguas_continentales_BH020": "Canal",
        "lineas_de_aguas_continentales_BH030": "Acequia, zanja o zanjón",
        "areas_de_aguas_continentales_perenne": "Espejo de agua perenne",
        "areas_de_aguas_continentales_intermitente": "Espejo de agua intermitente",
        "areas_de_aguas_continentales_BH020": "Canal (área)",
        "areas_de_aguas_continentales_BH140": "Corriente de agua (área)",
        "areas_de_aguas_continentales_BH130": "Embalse",
    },
}

# Atributos del IGN que se conservan (el resto son códigos internos).
ATRIBUTOS = ("fna", "gna", "nam", "rtn", "typ", "rst", "hct", "crv", "mo2", "fdc", "sag")


def redondear(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], DECIMALES), round(c[1], DECIMALES)]
    return [redondear(x) for x in c]


def consulta(capa_wfs, caja):
    s, o, n, e = caja[1], caja[0], caja[3], caja[2]
    return WFS + "?" + urllib.parse.urlencode({
        "service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "ign:" + capa_wfs,
        "outputFormat": "application/json", "srsName": "EPSG:4326",
        "bbox": f"{s},{o},{n},{e},urn:ogc:def:crs:EPSG::4326",
    })


def main():
    offline = "--offline" in sys.argv
    limite, caja = cargar_limite()
    carpeta = CRUDOS / "ign"
    resultado = 0
    for capa, fuentes in CAPAS.items():
        features, detalle, huellas = [], {}, {}
        completa = True
        for capa_wfs, etiqueta in fuentes.items():
            ruta = carpeta / f"{capa_wfs}.geojson"
            if not offline:
                try:
                    descargar(consulta(capa_wfs, caja), ruta, timeout=180)
                except ErrorRed as e:
                    aviso(f"{capa_wfs}: {e}")
            if not ruta.exists():
                aviso(f"{capa_wfs}: falta {ruta.name}; la capa {capa} queda pendiente.")
                completa = False
                continue
            crudo = ruta.read_bytes()
            datos = json.loads(crudo)
            huellas[capa_wfs] = sha256(crudo)
            dentro = 0
            for f in datos.get("features", []):
                geom = f.get("geometry")
                if not geom or not any(punto_en_geometria(x, y, limite, caja) for x, y, *_ in vertices(geom)):
                    continue
                props = {k: v for k, v in (f.get("properties") or {}).items() if k in ATRIBUTOS and v not in (None, "")}
                props["tipo"] = etiqueta
                props["ign"] = f.get("id")
                features.append({"type": "Feature", "properties": props,
                                 "geometry": {"type": geom["type"], "coordinates": redondear(geom["coordinates"])}})
                dentro += 1
            detalle[capa_wfs] = {"en_la_caja": len(datos.get("features", [])), "en_el_partido": dentro}
        if not completa:
            resultado = 1
            continue
        escribir_json(SITIO_DATOS / f"{capa}.geojson", coleccion(features), compacto=True)
        anotar_procesamiento(capa, {
            "archivo_crudo": "ign/*.geojson",
            "sha256_crudos": huellas,
            "elementos": len(features),
            "capas_wfs": detalle,
            "fecha_datos": None,
        })
        print(f"{capa}: {len(features)} elementos en el partido; {detalle}")
    return resultado


if __name__ == "__main__":
    sys.exit(main())
