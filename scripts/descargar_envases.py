"""Centros de almacenamiento transitorio (CAT) de envases vacíos de fitosanitarios dentro del partido.

Uso:  python3 scripts/descargar_envases.py            (descarga y procesa)
      python3 scripts/descargar_envases.py --offline  (procesa lo ya guardado en datos/crudos/envases/)

Conjunto "Producciones Sostenibles - Centros de almacenamiento transitorio envases productos
fitosanitarios" (Secretaría de Agricultura, Ganadería y Pesca; datos.gob.ar, CC BY 4.0), según la
Ley 27.279 y el Decreto 327/17. El recurso CSV trae latitud y longitud. Se publican solo la ubicación,
la dirección que da la fuente y la capacidad: el correo y el teléfono de contacto no se publican
(regla de datos personales), aunque la fuente los incluya.

Un CAT guarda envases vacíos de agroquímicos (ya lavados) hasta que se los lleva un operador; no es
un depósito de productos.
"""

import csv
import io
import sys

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion,
                   descargar, escribir_json, punto_en_geometria, sha256)

URL = ("https://datos.magyp.gob.ar/dataset/8d83f150-d079-4cfb-bb3e-d4200bf2b011/resource/"
       "d4a9cf05-3520-4f98-a4b8-32653ebbeaa6/download/centros-almacenamiento-transitorio-envases-fitosanitarios.csv")
CRUDO = CRUDOS / "envases" / "centros-almacenamiento-transitorio-envases-fitosanitarios.csv"
# Fecha del recurso según la API de datos.gob.ar ("last_modified" y "dataset_modified", leídos el 28/09/2026).
FECHA_DATOS = "Recurso actualizado por última vez el 11/09/2019, según datos.gob.ar."


def main():
    if "--offline" not in sys.argv:
        try:
            descargar(URL, CRUDO, timeout=120)
        except ErrorRed as e:
            aviso(f"{e}\nSe usa el archivo guardado en datos/crudos/envases/, si existe.")
    if not CRUDO.exists():
        aviso(f"Falta {CRUDO.name}: la capa de envases de fitosanitarios queda pendiente de fuente.")
        return 1
    contenido = CRUDO.read_bytes()
    # La fuente mezcla codificaciones (hay caracteres ilegibles en algunas direcciones).
    texto = contenido.decode("utf-8-sig", errors="replace")
    separador = max((";", ",", "\t"), key=texto.splitlines()[0].count)
    filas = list(csv.DictReader(io.StringIO(texto), delimiter=separador))
    limite, caja = cargar_limite()

    features, sin_punto, otro_departamento = [], 0, []
    for f in filas:
        try:
            lon, lat = float(f["longitud"]), float(f["latitud"])
        except (KeyError, ValueError):
            sin_punto += 1
            continue
        if not punto_en_geometria(lon, lat, limite, caja):
            continue
        if f.get("provincia_id") != "06" or f.get("departamento_id") != "581":
            otro_departamento.append(f.get("departamento"))
            continue
        props = {
            "tipo": "Centro de almacenamiento transitorio de envases vacíos de fitosanitarios",
            "direccion": " ".join(f.get("direccion", "").replace("�", " ").split()),
        }
        if (f.get("capacidad_de_envases") or "").strip().isdigit():
            props["capacidad_envases"] = int(f["capacidad_de_envases"])
        features.append({"type": "Feature", "properties": props,
                         "geometry": {"type": "Point", "coordinates": [round(lon, 5), round(lat, 5)]}})
    if otro_departamento:
        aviso(f"Centros dentro del límite pero con otro departamento en la fuente (no se publican): {otro_departamento}")

    escribir_json(SITIO_DATOS / "envases_fitosanitarios.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("envases_fitosanitarios", {
        "archivo_crudo": f"envases/{CRUDO.name}",
        "sha256_crudo": sha256(contenido),
        "elementos": len(features),
        "centros_en_el_pais": len(filas),
        "sin_coordenadas": sin_punto,
        "fecha_datos": FECHA_DATOS,
    })
    print(f"Envases de fitosanitarios: {len(features)} centros en el partido (de {len(filas)} en el país).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
