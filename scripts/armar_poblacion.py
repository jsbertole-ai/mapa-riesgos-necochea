"""Población por radio censal (Censo 2022) en el partido, según Boccolini (2026), CONICET.

Uso:  python3 scripts/armar_poblacion.py            (descarga y procesa)
      python3 scripts/armar_poblacion.py --offline  (procesa lo ya guardado en datos/crudos/censo/)

Conjunto "Argentina (2022) radios censales con datos de cantidad de población y densidad de
población" (Boccolini, S. M., CONICET Digital, http://hdl.handle.net/11336/284095, CC BY 2.5 AR).
Es la cartografía de radios del INDEC con la población total de cada radio (base Redatam del
INDEC) y la densidad en habitantes por hectárea. Solo trae los radios con más de 1 hab/ha: la
mayor parte de la zona rural del partido no está.

El archivo es un GeoPackage (SQLite): se lee con sqlite3 y la geometría (WKB) se decodifica acá.
Se toman los radios cuyo departamento es Necochea.
"""

import sqlite3
import struct
import sys

from comun import CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, coleccion, descargar, escribir_json, sha256

URL = "https://ri.conicet.gov.ar/bitstream/handle/11336/284095/radios_2022_conDatos_1habHa.gpkg?sequence=2&isAllowed=y"
CRUDO = CRUDOS / "censo" / "radios_2022_conDatos_1habHa.gpkg"
DECIMALES = 5

# Categorías de densidad del propio conjunto (archivo de estilo .sld del repositorio), en hab/ha.
CATEGORIAS = {2: "1 a 20 hab/ha", 3: "20 a 40 hab/ha", 4: "40 a 80 hab/ha", 5: "80 a 150 hab/ha",
              6: "150 a 300 hab/ha", 7: "300 a 500 hab/ha", 8: "500 a 750 hab/ha", 9: "750 a 1500 hab/ha",
              10: "Más de 1500 hab/ha"}


def wkb(datos, pos=0):
    """Decodifica Polygon y MultiPolygon WKB; devuelve (tipo, coordenadas, posición final)."""
    orden = "<" if datos[pos] == 1 else ">"
    tipo = struct.unpack(orden + "I", datos[pos + 1:pos + 5])[0] % 1000
    pos += 5
    if tipo == 3:
        n_anillos = struct.unpack(orden + "I", datos[pos:pos + 4])[0]
        pos += 4
        anillos = []
        for _ in range(n_anillos):
            n = struct.unpack(orden + "I", datos[pos:pos + 4])[0]
            pos += 4
            pts = struct.unpack(orden + "%dd" % (2 * n), datos[pos:pos + 16 * n])
            pos += 16 * n
            anillos.append([[round(pts[i], DECIMALES), round(pts[i + 1], DECIMALES)] for i in range(0, 2 * n, 2)])
        return "Polygon", anillos, pos
    if tipo == 6:
        n = struct.unpack(orden + "I", datos[pos:pos + 4])[0]
        pos += 4
        poligonos = []
        for _ in range(n):
            _, anillos, pos = wkb(datos, pos)
            poligonos.append(anillos)
        return "MultiPolygon", poligonos, pos
    raise ValueError(f"Tipo de geometría WKB no previsto: {tipo}")


def geometria_gpkg(blob):
    # Cabecera GeoPackage: "GP", versión, banderas (bits 1-3: tipo de envolvente), srs_id, envolvente.
    banderas = blob[3]
    largo_envolvente = {0: 0, 1: 32, 2: 48, 3: 48, 4: 64}[(banderas >> 1) & 7]
    tipo, coords, _ = wkb(blob, 8 + largo_envolvente)
    return {"type": tipo, "coordinates": coords}


def main():
    if "--offline" not in sys.argv:
        try:
            descargar(URL, CRUDO, timeout=900)
        except ErrorRed as e:
            aviso(f"{e}\nSe usa el archivo guardado en datos/crudos/censo/, si existe.")
    if not CRUDO.exists():
        aviso(f"Falta {CRUDO.name}: la capa de población queda pendiente de fuente.")
        return 1
    con = sqlite3.connect(CRUDO)
    filas = con.execute(
        "SELECT CRO, CA3, areaHa, densHabHa, cat_dens, geom FROM radios_2022_condatos_1habha "
        "WHERE NOMPROV = 'Buenos Aires' AND NOMDEPTO = 'Necochea'").fetchall()
    total_pais = con.execute("SELECT COUNT(*) FROM radios_2022_condatos_1habha").fetchone()[0]
    con.close()

    features, por_tipo = [], {}
    for cro, poblacion, area, densidad, categoria, geom in filas:
        etiqueta = CATEGORIAS.get(categoria, "Sin categoría")
        por_tipo[etiqueta] = por_tipo.get(etiqueta, 0) + 1
        features.append({"type": "Feature", "geometry": geometria_gpkg(geom), "properties": {
            "radio": cro, "poblacion": poblacion, "area_ha": round(area, 1),
            "densidad_hab_ha": round(densidad, 1), "densidad": etiqueta}})
    features.sort(key=lambda f: f["properties"]["radio"])

    escribir_json(SITIO_DATOS / "poblacion_radios.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("poblacion_radios", {
        "archivo_crudo": f"censo/{CRUDO.name}",
        "sha256_crudo": sha256(CRUDO.read_bytes()),
        "elementos": len(features),
        "radios_en_el_pais": total_pais,
        "poblacion_en_los_radios": sum(f["properties"]["poblacion"] or 0 for f in features),
        "por_tipo": por_tipo,
        "fecha_datos": "Censo Nacional de Población, Hogares y Viviendas, 18/05/2022 (INDEC).",
    })
    print(f"Población: {len(features)} radios del partido con más de 1 hab/ha, "
          f"{sum(f['properties']['poblacion'] or 0 for f in features)} habitantes; por densidad {por_tipo}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
