"""Gasoductos que pasan por el partido (ENARGAS, vía la Secretaría de Energía; CC BY 4.0).

Uso:  python3 scripts/descargar_gasoductos.py            (descarga y procesa)
      python3 scripts/descargar_gasoductos.py --offline  (procesa lo ya guardado en datos/crudos/gas/)

Conjunto "Gasoductos (ENARGAS)" de datos.energia.gob.ar, recurso "Gasoductos de Distribución"
(CSV con la geometría en GeoJSON). Entra todo gasoducto con al menos un vértice dentro del
límite del partido. Los gasoductos de transporte (troncales) se revisaron el 01/10/2026 con el
shapefile del mismo conjunto: ninguno toca el partido (DATOS.md, sección 21).

Los gasoductos son a la vez línea vital (Lavell, 2007, p. 34) y fuente de amenaza tecnológica.
La fuente no informa diámetro, presión ni fecha de habilitación.
"""

import csv
import io
import json
import sys

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion,
                   descargar, escribir_json, punto_en_geometria, sha256)

URL = ("http://datos.energia.gob.ar/dataset/8758101a-1e0d-413f-8cc5-83e21ece6391/resource/"
       "3f7f87ab-bdcf-4a21-b361-f59732754330/download/gasoductos-de-distribucin.csv")
CRUDO = CRUDOS / "gas" / "gasoductos-de-distribucin.csv"
DECIMALES = 5


def puntos(c):
    if isinstance(c[0], (int, float)):
        yield c
    else:
        for s in c:
            yield from puntos(s)


def redondear(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], DECIMALES), round(c[1], DECIMALES)]
    return [redondear(s) for s in c]


def main():
    if "--offline" not in sys.argv:
        try:
            descargar(URL, CRUDO, timeout=600)
        except ErrorRed as e:
            aviso(f"{e}\nSe usa el CSV guardado en datos/crudos/gas/, si existe (se baja a mano desde {URL}).")
    if not CRUDO.exists():
        aviso(f"Falta {CRUDO.name}: la capa de gasoductos queda pendiente de fuente.")
        return 1
    contenido = CRUDO.read_bytes()
    csv.field_size_limit(10 ** 9)
    limite, caja = cargar_limite()
    features, total, sin_geometria = [], 0, 0
    for fila in csv.DictReader(io.StringIO(contenido.decode("utf-8-sig"))):
        total += 1
        if not (fila.get("geojson") or "").strip():
            sin_geometria += 1
            continue
        g = json.loads(fila["geojson"])
        if not any(punto_en_geometria(x, y, limite, caja) for x, y, *_ in puntos(g["coordinates"])):
            continue
        props = {
            "nombre": (fila.get("nombregaso") or "").strip() or None,
            "tramo": (fila.get("nombretram") or "").strip() or None,
            "licenciataria": (fila.get("licenciata") or "").strip() or None,
            "tipo": (fila.get("tipotramo") or "").strip() or None,
            "subtipo": (fila.get("subtipotra") or "").strip() or None,
        }
        if props["tramo"] == props["nombre"]:
            props.pop("tramo")
        features.append({"type": "Feature", "properties": {k: v for k, v in props.items() if v},
                         "geometry": {"type": g["type"], "coordinates": redondear(g["coordinates"])}})

    escribir_json(SITIO_DATOS / "gasoductos.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("gasoductos", {
        "archivo_crudo": f"gas/{CRUDO.name}",
        "sha256_crudo": sha256(contenido),
        "elementos": len(features),
        "gasoductos_en_el_pais": total,
        "sin_geometria": sin_geometria,
        "fecha_datos": None,
    })
    print(f"Gasoductos: {len(features)} en el partido (de {total} de distribución en el país): "
          + ", ".join(f["properties"].get("nombre", "?") for f in features))
    return 0


if __name__ == "__main__":
    sys.exit(main())
