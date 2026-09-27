"""Cuenca del río Quequén Grande completa (COHIFE) y su red hídrica (IGN), aunque exceden el partido.

Uso:  python3 scripts/descargar_cuenca.py            (descarga y procesa)
      python3 scripts/descargar_cuenca.py --offline  (procesa lo ya guardado en datos/crudos/)

Necochea y Quequén están en la desembocadura: lo que pasa aguas arriba (lluvias, anegamientos,
obras de drenaje) llega al partido por el río. Por eso estas dos capas no se recortan por el
límite del partido sino por la cuenca, que ocupa partes de siete partidos.

1. Límite de la cuenca: conjunto "Cuencas Hídricas - COHIFE" de datos.gob.ar (Secretaría de
   Energía, con información compilada por el Consejo Hídrico Federal; CC BY 4.0), registro con
   CUENCA = "Río Quequén Grande". El shapefile se lee con la biblioteca estándar.
2. Red hídrica: WFS del IGN (cursos de agua perennes e intermitentes, y acequias, zanjas o
   zanjones) pedido en la caja de la cuenca; entra cada tramo con al menos un vértice dentro.

La parte de la cuenca en cada partido se estima contando puntos de una grilla de 0,02 grados
dentro de la cuenca (límites de departamentos de Georef, ya descargados por descargar_limite.py).
"""

import io
import json
import struct
import sys
import zipfile

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, caja_envolvente, coleccion,
                   descargar, escribir_json, leer_json, punto_en_geometria, sha256, vertices)
from descargar_ign import consulta

URL_COHIFE = ("http://datos.energia.gob.ar/dataset/2c8b870a-7d6b-4ad0-ace0-86c4a9c9e3c0/resource/"
              "ace98ef1-e7a8-4d5d-8f44-2e85a2d824a4/download/cuencas-hdricas-cohife.zip")
CRUDO_COHIFE = CRUDOS / "cuencas" / "cuencas-hdricas-cohife.zip"
CUENCA = "Río Quequén Grande"
DEPARTAMENTOS = CRUDOS / "departamentos.geojson"
DECIMALES = 5
PASO_GRILLA = 0.02

RED_IGN = {
    "lineas_de_aguas_continentales_perenne": "Corriente de agua perenne",
    "lineas_de_aguas_continentales_intermitentes": "Corriente de agua intermitente",
    "lineas_de_aguas_continentales_BH030": "Acequia, zanja o zanjón",
}


def leer_dbf(datos):
    n = struct.unpack("<I", datos[4:8])[0]
    largo_cabecera, largo_registro = struct.unpack("<HH", datos[8:12])
    campos, pos = [], 32
    while datos[pos] != 0x0D:
        campos.append((datos[pos:pos + 11].split(b"\0")[0].decode("latin1"), datos[pos + 16]))
        pos += 32
    for i in range(n):
        r = datos[largo_cabecera + i * largo_registro: largo_cabecera + (i + 1) * largo_registro]
        fila, p = {}, 1
        for nombre, largo in campos:
            fila[nombre] = r[p:p + largo].decode("utf-8", "replace").strip()
            p += largo
        yield fila


def leer_poligonos(datos):
    """Anillos de cada registro de un shapefile de polígonos (tipos 5 y 15; la Z se ignora)."""
    pos = 100
    while pos < len(datos):
        _, largo = struct.unpack(">ii", datos[pos:pos + 8])
        c = datos[pos + 8: pos + 8 + largo * 2]
        pos += 8 + largo * 2
        if struct.unpack("<i", c[:4])[0] == 0:
            yield None
            continue
        n_partes, n_puntos = struct.unpack("<ii", c[36:44])
        inicios = list(struct.unpack(f"<{n_partes}i", c[44:44 + 4 * n_partes])) + [n_puntos]
        base = 44 + 4 * n_partes
        puntos = [struct.unpack("<2d", c[base + 16 * k: base + 16 * k + 16]) for k in range(n_puntos)]
        yield [puntos[inicios[j]:inicios[j + 1]] for j in range(n_partes)]


def area_km2(anillo):
    """Área aproximada de un anillo en km² (proyección equirectangular local)."""
    import math
    lat0 = sum(y for _, y in anillo) / len(anillo)
    kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57
    return abs(sum(anillo[i][0] * kx * anillo[i + 1][1] * ky - anillo[i + 1][0] * kx * anillo[i][1] * ky
                   for i in range(len(anillo) - 1)) / 2)


def redondear(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], DECIMALES), round(c[1], DECIMALES)]
    return [redondear(x) for x in c]


def cuenca_cohife(offline):
    if not offline:
        try:
            descargar(URL_COHIFE, CRUDO_COHIFE, timeout=300)
        except ErrorRed as e:
            aviso(f"{e}\nSe usa el ZIP guardado en datos/crudos/cuencas/, si existe (se baja a mano desde {URL_COHIFE}).")
    if not CRUDO_COHIFE.exists():
        return None, None
    contenido = CRUDO_COHIFE.read_bytes()
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombres = z.namelist()
        prj = z.read(next(n for n in nombres if n.endswith(".prj"))).decode("latin1")
        if 'GEOGCS["WGS 84"' not in prj:
            aviso(f"Proyección inesperada ({prj[:80]}): no se procesa.")
            return None, None
        shp = z.read(next(n for n in nombres if n.endswith(".shp")))
        dbf = z.read(next(n for n in nombres if n.endswith(".dbf")))
    for fila, anillos in zip(leer_dbf(dbf), leer_poligonos(shp)):
        if fila.get("CUENCA") == CUENCA and anillos:
            geometria = {"type": "Polygon", "coordinates": [[list(p) for p in a] for a in anillos]}
            return {"fila": fila, "geometria": geometria, "sha256": sha256(contenido)}, len(anillos)
    aviso(f"No se encontró la cuenca \"{CUENCA}\" en el archivo del COHIFE.")
    return None, None


def partidos_en_la_cuenca(geometria, caja):
    """Porcentaje aproximado de la cuenca en cada partido, por muestreo en grilla."""
    deptos = leer_json(DEPARTAMENTOS)
    if not deptos:
        return None
    candidatos = []
    for f in deptos["features"]:
        if (f["properties"].get("provincia") or {}).get("nombre") != "Buenos Aires":
            continue
        c = caja_envolvente(f["geometry"])
        if not (c[2] < caja[0] or c[0] > caja[2] or c[3] < caja[1] or c[1] > caja[3]):
            candidatos.append((f["properties"]["nombre"], f["geometry"], c))
    conteo, total = {}, 0
    y = caja[1]
    while y < caja[3]:
        x = caja[0]
        while x < caja[2]:
            if punto_en_geometria(x, y, geometria, caja):
                total += 1
                for nombre, g, c in candidatos:
                    if punto_en_geometria(x, y, g, c):
                        conteo[nombre] = conteo.get(nombre, 0) + 1
                        break
            x += PASO_GRILLA
        y += PASO_GRILLA
    return {k: round(100 * v / total, 1) for k, v in sorted(conteo.items(), key=lambda kv: -kv[1]) if 100 * v / total >= 0.5}


def main():
    offline = "--offline" in sys.argv
    cuenca, _ = cuenca_cohife(offline)
    if not cuenca:
        aviso("Sin el límite de la cuenca, las capas de la cuenca quedan pendientes de fuente.")
        return 1
    g = cuenca["geometria"]
    caja = caja_envolvente(g)
    area = round(area_km2(g["coordinates"][0]))
    reparto = partidos_en_la_cuenca(g, caja)
    escribir_json(SITIO_DATOS / "cuenca_quequen.geojson", coleccion([{"type": "Feature", "properties": {
        "nombre": cuenca["fila"]["CUENCA"], "sistema": cuenca["fila"].get("SISTEMA__S"),
        "region": cuenca["fila"].get("REG_HIDR"), "area_km2": area, "partidos": reparto,
    }, "geometry": {"type": "Polygon", "coordinates": redondear(g["coordinates"])}}]), compacto=True)
    anotar_procesamiento("cuenca_quequen", {
        "archivo_crudo": f"cuencas/{CRUDO_COHIFE.name}",
        "sha256_crudo": cuenca["sha256"],
        "elementos": 1,
        "area_km2_aproximada": area,
        "partidos_porcentaje_aproximado": reparto,
        "caja_verificacion": caja,
        "fecha_datos": None,
    })
    print(f"Cuenca del {CUENCA}: {area} km² aproximados; reparto por partido {reparto}.")

    carpeta = CRUDOS / "ign_cuenca"
    features, huellas, detalle, por_tipo = [], {}, {}, {}
    for capa_wfs, etiqueta in RED_IGN.items():
        ruta = carpeta / f"{capa_wfs}.geojson"
        if not offline:
            try:
                descargar(consulta(capa_wfs, caja), ruta, timeout=300)
            except ErrorRed as e:
                aviso(f"{capa_wfs}: {e}")
        if not ruta.exists():
            aviso(f"{capa_wfs}: falta {ruta.name}; la red hídrica de la cuenca queda pendiente.")
            return 1
        crudo = ruta.read_bytes()
        huellas[capa_wfs] = sha256(crudo)
        datos = json.loads(crudo)
        dentro = 0
        for f in datos.get("features", []):
            geom = f.get("geometry")
            if not geom or not any(punto_en_geometria(x, y, g, caja) for x, y, *_ in vertices(geom)):
                continue
            p = f.get("properties") or {}
            props = {k: p[k] for k in ("fna", "gna", "nam") if p.get(k)}
            props["tipo"] = etiqueta
            props["ign"] = f.get("id")
            features.append({"type": "Feature", "properties": props,
                             "geometry": {"type": geom["type"], "coordinates": redondear(geom["coordinates"])}})
            dentro += 1
        detalle[capa_wfs] = {"en_la_caja": len(datos.get("features", [])), "en_la_cuenca": dentro}
        por_tipo[etiqueta] = dentro
    escribir_json(SITIO_DATOS / "red_hidrica_cuenca.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("red_hidrica_cuenca", {
        "archivo_crudo": "ign_cuenca/*.geojson",
        "sha256_crudos": huellas,
        "elementos": len(features),
        "capas_wfs": detalle,
        "por_tipo": por_tipo,
        "caja_verificacion": caja,
        "fecha_datos": None,
    })
    print(f"Red hídrica de la cuenca (IGN): {len(features)} tramos; {por_tipo}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
