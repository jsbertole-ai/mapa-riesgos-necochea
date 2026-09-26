"""Capas del IGN republicadas en el catálogo de datos abiertos de la provincia (CC BY 4.0).

Uso:  python3 scripts/procesar_catalogo_gba.py            (intenta descargar y procesa)
      python3 scripts/procesar_catalogo_gba.py --offline  (procesa los ZIP de datos/crudos/gba/)

Desde el entorno en la nube, el servidor del catálogo corta las descargas en
31.610 bytes (26/09/2026). Si pasa eso, bajar los ZIP a mano desde las páginas
de cada conjunto (ver CONJUNTOS) y dejarlos en datos/crudos/gba/ con su nombre
original. Un ZIP truncado se detecta y se descarta: nunca se procesa a medias.

Lee el shapefile sin dependencias. La proyección sale del .prj: si es
geográfica se usa tal cual; si es transversa de Mercator (Gauss-Krüger), se
convierte a latitud y longitud con los parámetros del propio .prj. Cualquier
otra proyección corta el proceso con un aviso, en lugar de suponer nada.
"""

import io
import json
import math
import re
import struct
import sys
import zipfile

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion, descargar,
                   escribir_json, punto_en_geometria, registrar_descarga, sha256)

BASE = "https://catalogo.datos.gba.gob.ar/dataset/"
CONJUNTOS = {
    "ferrocarril": {
        "pagina": BASE + "ferroviario",
        "zip": BASE + "343789d2-9cc9-4c4c-b19c-627a79f0e8d9/resource/50b8dbf6-6632-46b6-84f3-a33c590938ac/download/lineas-ferrocarril.zip",
    },
    "red_vial": {
        "pagina": BASE + "red-vial",
        "zip": BASE + "ce9bead9-878f-4a97-b2e0-d66ea6d12395/resource/c66015c7-9dae-4770-ae6d-44c615771230/download/red-vial-provincial.zip",
    },
    "curvas_nivel": {
        "pagina": BASE + "curvas-nivel",
        "zip": BASE + "0f0e47ed-a4d4-446b-936d-2db84a6c2a00/resource/dc7c60ff-15a7-411b-9071-088c0e827b38/download/curvas-nivel-pba.zip",
    },
    "cursos_agua": {
        "pagina": BASE + "cursos-agua",
        "zip": BASE + "4ac7ad19-2fc5-490f-82a2-6bd06fdc6251/resource/cd7ca981-c8d9-43c3-a4b5-93d18b217b53/download/cursos-agua-pba.zip",
    },
    "cuerpos_agua": {
        "pagina": BASE + "cuerpos-agua",
        "zip": BASE + "0896dec3-5fd6-42c9-b395-b0ff5caf3096/resource/87215d91-0218-442d-9909-81232860c036/download/cuerpos-agua-pba.zip",
    },
}
CARPETA = CRUDOS / "gba"
DECIMALES = 5


# ---------------------------------------------------------------------------
# Proyección
# ---------------------------------------------------------------------------

def leer_prj(texto):
    """Devuelve None si la proyección es geográfica, o los parámetros de la transversa de Mercator."""
    texto = texto.strip()
    if texto.upper().startswith("GEOGCS"):
        return None
    if not texto.upper().startswith("PROJCS"):
        raise ValueError(f"Proyección no reconocida: {texto[:80]}")
    proyeccion = re.search(r'PROJECTION\["([^"]+)"', texto)
    if not proyeccion or proyeccion.group(1).lower() not in ("transverse_mercator", "gauss_kruger"):
        raise ValueError(f"Solo se admite transversa de Mercator; el .prj dice {proyeccion.group(1) if proyeccion else '?'}")
    esferoide = re.search(r'SPHEROID\["[^"]*",\s*([\d.]+),\s*([\d.]+)', texto)
    unidad = re.findall(r'UNIT\["[^"]*",\s*([\d.]+)', texto)
    parametros = {k.lower(): float(v) for k, v in re.findall(r'PARAMETER\["([^"]+)",\s*(-?[\d.]+)', texto)}
    if not esferoide:
        raise ValueError("El .prj no declara el esferoide")
    if unidad and abs(float(unidad[-1]) - 1.0) > 1e-9:
        raise ValueError(f"Unidad lineal no métrica en el .prj ({unidad[-1]})")
    return {
        "a": float(esferoide.group(1)),
        "f": 1 / float(esferoide.group(2)),
        "lon0": math.radians(parametros.get("central_meridian", 0.0)),
        "lat0": math.radians(parametros.get("latitude_of_origin", 0.0)),
        "k0": parametros.get("scale_factor", 1.0),
        "fe": parametros.get("false_easting", 0.0),
        "fn": parametros.get("false_northing", 0.0),
    }


def _arco_meridiano(lat, a, e2):
    e4, e6 = e2 * e2, e2 * e2 * e2
    return a * ((1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * lat
                - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * lat)
                + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * lat)
                - (35 * e6 / 3072) * math.sin(6 * lat))


def tm_inversa(x, y, p):
    """Transversa de Mercator inversa (Snyder 1987, ecuaciones 8-12 a 8-25). Devuelve (lon, lat) en grados."""
    a, f, k0 = p["a"], p["f"], p["k0"]
    e2 = f * (2 - f)
    ep2 = e2 / (1 - e2)
    m = _arco_meridiano(p["lat0"], a, e2) + (y - p["fn"]) / k0
    mu = m / (a * (1 - e2 / 4 - 3 * e2 ** 2 / 64 - 5 * e2 ** 3 / 256))
    e1 = (1 - math.sqrt(1 - e2)) / (1 + math.sqrt(1 - e2))
    phi1 = (mu + (3 * e1 / 2 - 27 * e1 ** 3 / 32) * math.sin(2 * mu)
            + (21 * e1 ** 2 / 16 - 55 * e1 ** 4 / 32) * math.sin(4 * mu)
            + (151 * e1 ** 3 / 96) * math.sin(6 * mu)
            + (1097 * e1 ** 4 / 512) * math.sin(8 * mu))
    s, c, t = math.sin(phi1), math.cos(phi1), math.tan(phi1)
    c1, t1 = ep2 * c * c, t * t
    n1 = a / math.sqrt(1 - e2 * s * s)
    r1 = a * (1 - e2) / (1 - e2 * s * s) ** 1.5
    d = (x - p["fe"]) / (n1 * k0)
    lat = phi1 - (n1 * t / r1) * (d ** 2 / 2
                                  - (5 + 3 * t1 + 10 * c1 - 4 * c1 ** 2 - 9 * ep2) * d ** 4 / 24
                                  + (61 + 90 * t1 + 298 * c1 + 45 * t1 ** 2 - 252 * ep2 - 3 * c1 ** 2) * d ** 6 / 720)
    lon = p["lon0"] + (d - (1 + 2 * t1 + c1) * d ** 3 / 6
                       + (5 - 2 * c1 + 28 * t1 - 3 * c1 ** 2 + 8 * ep2 + 24 * t1 ** 2) * d ** 5 / 120) / c
    return math.degrees(lon), math.degrees(lat)


# ---------------------------------------------------------------------------
# Shapefile (.shp y .dbf)
# ---------------------------------------------------------------------------

def leer_dbf(datos, codificacion):
    n = struct.unpack("<I", datos[4:8])[0]
    largo_encabezado, largo_registro = struct.unpack("<HH", datos[8:12])
    campos, pos = [], 32
    while datos[pos] != 0x0D:
        nombre = datos[pos:pos + 11].split(b"\x00")[0].decode("ascii", "replace")
        campos.append((nombre, chr(datos[pos + 11]), datos[pos + 16]))
        pos += 32
    registros, pos = [], largo_encabezado
    for _ in range(n):
        crudo = datos[pos:pos + largo_registro]
        pos += largo_registro
        if not crudo or crudo[0:1] == b"*":
            registros.append(None)
            continue
        fila, i = {}, 1
        for nombre, tipo, largo in campos:
            valor = crudo[i:i + largo].decode(codificacion, "replace").strip()
            i += largo
            if valor == "":
                continue
            if tipo in "NF":
                try:
                    num = float(valor)
                    valor = int(num) if num.is_integer() else num
                except ValueError:
                    pass
            fila[nombre] = valor
        registros.append(fila)
    return registros


def area_con_signo(anillo):
    return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(anillo, anillo[1:])) / 2


def leer_shp(datos, convertir):
    """Itera las geometrías GeoJSON (o None) de un .shp. Admite puntos, líneas y polígonos, con o sin Z y M."""
    pos = 100
    while pos + 8 <= len(datos):
        largo = struct.unpack(">i", datos[pos + 4:pos + 8])[0] * 2
        contenido = datos[pos + 8:pos + 8 + largo]
        pos += 8 + largo
        tipo = struct.unpack("<i", contenido[0:4])[0]
        if tipo == 0:
            yield None
        elif tipo in (1, 11, 21):
            x, y = struct.unpack("<2d", contenido[4:20])
            yield {"type": "Point", "coordinates": convertir(x, y)}
        elif tipo in (8, 18, 28):
            n = struct.unpack("<i", contenido[36:40])[0]
            pts = struct.unpack(f"<{2 * n}d", contenido[40:40 + 16 * n])
            yield {"type": "MultiPoint", "coordinates": [convertir(pts[i], pts[i + 1]) for i in range(0, 2 * n, 2)]}
        elif tipo in (3, 13, 23, 5, 15, 25):
            n_partes, n_puntos = struct.unpack("<2i", contenido[36:44])
            partes = list(struct.unpack(f"<{n_partes}i", contenido[44:44 + 4 * n_partes])) + [n_puntos]
            inicio = 44 + 4 * n_partes
            pts = struct.unpack(f"<{2 * n_puntos}d", contenido[inicio:inicio + 16 * n_puntos])
            tramos = [[(pts[2 * i], pts[2 * i + 1]) for i in range(partes[k], partes[k + 1])] for k in range(n_partes)]
            if tipo in (3, 13, 23):
                lineas = [[convertir(x, y) for x, y in t] for t in tramos if len(t) >= 2]
                yield {"type": "MultiLineString", "coordinates": lineas} if len(lineas) != 1 else {"type": "LineString", "coordinates": lineas[0]}
            else:
                # En el shapefile los anillos exteriores van en sentido horario y los huecos al revés.
                exteriores = [t for t in tramos if len(t) >= 4 and area_con_signo(t) < 0]
                huecos = [t for t in tramos if len(t) >= 4 and area_con_signo(t) > 0]
                poligonos = [[e] for e in exteriores] or [[h] for h in huecos]
                if exteriores:
                    for h in huecos:
                        for p in poligonos:
                            if punto_en_geometria(h[0][0], h[0][1], {"type": "Polygon", "coordinates": [p[0]]}):
                                p.append(h)
                                break
                coords = [[[convertir(x, y) for x, y in anillo] for anillo in p] for p in poligonos]
                yield {"type": "MultiPolygon", "coordinates": coords} if len(coords) != 1 else {"type": "Polygon", "coordinates": coords[0]}
        else:
            raise ValueError(f"Tipo de geometría de shapefile no admitido: {tipo}")


def vertices_de(geom):
    t, c = geom["type"], geom["coordinates"]
    if t == "Point":
        return [c]
    if t in ("MultiPoint", "LineString"):
        return c
    if t == "MultiLineString":
        return [v for linea in c for v in linea]
    if t == "Polygon":
        return c[0]
    return [v for p in c for v in p[0]]


def procesar_zip(capa, ruta, limite, caja):
    contenido = ruta.read_bytes()
    z = zipfile.ZipFile(io.BytesIO(contenido))
    features = []
    detalle = {}
    for nombre_shp in [n for n in z.namelist() if n.lower().endswith(".shp")]:
        base = nombre_shp[:-4]
        miembros = {n.lower(): n for n in z.namelist()}
        prj = z.read(miembros[(base + ".prj").lower()]).decode("latin-1") if (base + ".prj").lower() in miembros else None
        if prj is None:
            raise ValueError(f"{nombre_shp} no trae .prj: no se supone ninguna proyección")
        cpg = (base + ".cpg").lower()
        codificacion = z.read(miembros[cpg]).decode("ascii").strip() if cpg in miembros else "latin-1"
        codificacion = {"UTF-8": "utf-8", "UTF8": "utf-8"}.get(codificacion.upper(), codificacion)
        parametros = leer_prj(prj)
        if parametros is None:
            convertir = lambda x, y: [round(x, DECIMALES), round(y, DECIMALES)]
        else:
            def convertir(x, y, p=parametros):
                lon, lat = tm_inversa(x, y, p)
                return [round(lon, DECIMALES), round(lat, DECIMALES)]
        geometrias = list(leer_shp(z.read(nombre_shp), convertir))
        registros = leer_dbf(z.read(miembros[(base + ".dbf").lower()]), codificacion)
        if len(geometrias) != len(registros):
            raise ValueError(f"{nombre_shp}: {len(geometrias)} geometrías y {len(registros)} registros no coinciden")
        dentro = 0
        for geom, props in zip(geometrias, registros):
            if geom is None or props is None:
                continue
            if any(punto_en_geometria(x, y, limite, caja) for x, y in vertices_de(geom)):
                features.append({"type": "Feature", "properties": props, "geometry": geom})
                dentro += 1
        detalle[nombre_shp] = {"proyeccion": "geográfica" if parametros is None else "transversa de Mercator",
                               "prj": prj[:200], "codificacion": codificacion,
                               "elementos_totales": len(geometrias), "elementos_en_el_partido": dentro}
    if not detalle:
        raise ValueError(f"{ruta.name} no contiene ningún .shp")
    escribir_json(SITIO_DATOS / f"{capa}.geojson", coleccion(features), compacto=True)
    anotar_procesamiento(capa, {
        "archivo_crudo": f"gba/{ruta.name}",
        "sha256_crudo": sha256(contenido),
        "elementos": len(features),
        "shapefiles": detalle,
        "fecha_datos": None,
    })
    print(f"{capa}: {len(features)} elementos dentro del partido; {json.dumps(detalle, ensure_ascii=False)[:300]}")


def zip_integro(ruta):
    try:
        with zipfile.ZipFile(ruta) as z:
            return z.testzip() is None
    except zipfile.BadZipFile:
        return False


def main():
    offline = "--offline" in sys.argv
    limite, caja = cargar_limite()
    CARPETA.mkdir(parents=True, exist_ok=True)
    resultado = 0
    for capa, conf in CONJUNTOS.items():
        ruta = CARPETA / conf["zip"].rsplit("/", 1)[1]
        if not ruta.exists() and not offline:
            # Se verifica en memoria antes de guardar: una descarga truncada no se guarda ni se registra.
            try:
                contenido = descargar(conf["zip"], timeout=300, reintentos=1)
                if zip_integro(io.BytesIO(contenido)):
                    ruta.write_bytes(contenido)
                    registrar_descarga(conf["zip"], ruta, contenido)
                else:
                    aviso(f"{capa}: la descarga llegó truncada ({len(contenido):,} bytes); no se guarda.")
            except ErrorRed as e:
                aviso(f"{capa}: {e}")
        if ruta.exists() and not zip_integro(ruta):
            aviso(f"{capa}: {ruta.name} está truncado o dañado; se descarta. Bajalo a mano desde {conf['pagina']}")
            ruta.unlink()
        if not ruta.exists():
            aviso(f"{capa}: falta {ruta.name}; queda pendiente. Página del conjunto: {conf['pagina']}")
            resultado = 1
            continue
        try:
            procesar_zip(capa, ruta, limite, caja)
        except ValueError as e:
            aviso(f"{capa}: {e}")
            resultado = 1
    return resultado


if __name__ == "__main__":
    sys.exit(main())
