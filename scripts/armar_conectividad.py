"""Conectividad por localidad: accesos a Internet fijo por tecnología (ENACOM).

Uso:  python3 scripts/armar_conectividad.py

Lee el archivo "internet_accesos_tecnologias_localidades.csv" de los Datos Abiertos de ENACOM
(https://indicadores.enacom.gob.ar/Files/DatosAbiertos/internet_accesos_tecnologias_localidades.csv),
que el servidor de ENACOM no deja descargar desde el entorno: lo baja un colaborador a mano y se
guarda en datos/crudos/enacom/. Toma las filas del partido de Necochea, suma los accesos por
localidad y le da a cada una un color según la tecnología:

- "Con fibra óptica": la fibra es la tecnología con más accesos.
- "Sin fibra o con fibra mínima": hay accesos terrestres, pero la fibra no predomina
  o no existe.
- "Solo satelital": todos los accesos son satelitales.

El punto de cada localidad es el de la capa de localidades del IGN; Costa Bonita, que el IGN no
trae, usa el punto central de su límite en OpenStreetMap. Las filas sin localidad ("Otros") no
tienen punto y solo se cuentan. Son cantidades de accesos por localidad: no dicen por dónde pasa
la red ni qué parte de cada localidad cubre.
"""

import csv
import io
import sys

from comun import CRUDOS, SITIO_DATOS, anotar_procesamiento, aviso, coleccion, escribir_json, leer_json, sha256

URL = "https://indicadores.enacom.gob.ar/Files/DatosAbiertos/internet_accesos_tecnologias_localidades.csv"
CRUDO = CRUDOS / "enacom" / "internet_accesos_tecnologias_localidades.csv"
DESCARGA = "01/10/2026"

# Nombre en ENACOM -> nombre en la capa de localidades del IGN.
ALIAS = {"Nicanor Olivera  (Est. La Dulce)": "Nicanor Olivera"}

# Localidades que el IGN no trae: punto central de su límite en OpenStreetMap (Nominatim, 01/10/2026).
PUNTOS_OSM = {"Costa Bonita": ([-58.62895, -38.56113], "Punto central del límite de Costa Bonita en OpenStreetMap (relation/21212013).")}

NOMBRES = {
    "FIBRA OPTICA": "Fibra óptica", "CABLEMODEM": "Cable módem", "ADSL": "ADSL", "WIRELESS": "Inalámbrico",
    "SATELITAL": "Satelital", "DIAL UP": "Telefónico (dial up)", "CELULAR": "Celular", "OTROS": "Otras",
}


def categoria(tec):
    if tec.get("FIBRA OPTICA", 0) and max(tec, key=tec.get) == "FIBRA OPTICA":
        return "Con fibra óptica"
    if set(tec) == {"SATELITAL"}:
        return "Solo satelital"
    return "Sin fibra o con fibra mínima"


def main():
    if not CRUDO.exists():
        aviso(f"Falta {CRUDO.relative_to(CRUDOS.parent.parent)}: bajalo a mano de {URL}. La capa queda pendiente.")
        return 1
    contenido = CRUDO.read_bytes()
    filas = list(csv.DictReader(io.StringIO(contenido.decode("utf-8-sig"))))
    por_localidad, sin_localidad = {}, {}
    for f in filas:
        if f["provincia"].strip().upper() != "BUENOS AIRES" or f["partido"].strip() != "Necochea":
            continue
        loc, tec, n = f["localidad"].strip(), f["tecnologia"].strip().upper(), int(f["accesos"])
        destino = sin_localidad if loc.upper() == "OTROS" else por_localidad.setdefault(loc, {})
        destino[tec] = destino.get(tec, 0) + n

    puntos = {}
    for g in leer_json(SITIO_DATOS / "localidades.geojson")["features"]:
        c = g["geometry"]["coordinates"]
        puntos[g["properties"]["fna"]] = (c[0] if g["geometry"]["type"] == "MultiPoint" else c,
                                          "Punto de la localidad en la capa del IGN (BAHRA).")
    puntos.update(PUNTOS_OSM)

    features, sin_punto = [], []
    for loc, tec in sorted(por_localidad.items(), key=lambda x: -sum(x[1].values())):
        nombre = ALIAS.get(loc, loc)
        if nombre not in puntos:
            sin_punto.append(loc)
            continue
        coord, origen = puntos[nombre]
        orden = sorted(tec.items(), key=lambda x: -x[1])
        props = {
            "localidad": nombre,
            "localidad_enacom": loc,
            "categoria": categoria(tec),
            "accesos": sum(tec.values()),
            "tecnologias": [[NOMBRES.get(t, t.capitalize()), n] for t, n in orden],
            "fibra": tec.get("FIBRA OPTICA", 0),
            "punto": origen,
        }
        features.append({"type": "Feature", "properties": props,
                         "geometry": {"type": "Point", "coordinates": [round(coord[0], 5), round(coord[1], 5)]}})
    if sin_punto:
        aviso(f"Localidades de ENACOM sin punto en el mapa (no se publican): {sin_punto}")

    escribir_json(SITIO_DATOS / "conectividad_localidades.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("conectividad_localidades", {
        "archivo_crudo": f"enacom/{CRUDO.name}",
        "sha256_crudo": sha256(contenido),
        "elementos": len(features),
        "por_tipo": {c: sum(1 for f in features if f["properties"]["categoria"] == c)
                     for c in ("Con fibra óptica", "Sin fibra o con fibra mínima", "Solo satelital")},
        "accesos_sin_localidad": sin_localidad,
        "fecha_datos": f"ENACOM no informa el período en el archivo; descargado a mano el {DESCARGA}.",
    })
    print(f"Conectividad: {len(features)} localidades del partido; sin localidad: {sin_localidad}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
