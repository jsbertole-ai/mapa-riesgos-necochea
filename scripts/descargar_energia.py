"""Líneas de media tensión de las cooperativas bonaerenses (Secretaría de Energía, CC BY 4.0).

Uso:  python3 scripts/descargar_energia.py            (intenta descargar y procesa)
      python3 scripts/descargar_energia.py --offline  (procesa lo ya guardado en datos/crudos/energia/)

Conjunto "Redes de distribución eléctrica del Consejo Federal" de datos.gob.ar, recurso
"Redes de distribución eléctrica de BUENOS AIRES (solo cooperativas) - CFEE - Líneas Media
y Alta Tensión" (shapefile, actualizado el 30/05/2022). El servidor datos.energia.gob.ar solo
sirve por HTTP, que el entorno de desarrollo no permite: si la descarga falla, se usa el ZIP
bajado a mano y guardado en datos/crudos/energia/ con su nombre original.

El shapefile se lee con la biblioteca estándar (líneas, tipo 3) y se recorta por el partido:
entra todo tramo con al menos un vértice dentro. Se conservan tensión, tipo, función, clase y
cooperativa; se descartan secciones y materiales de los conductores y la columna GEOJSON,
que repite la geometría.
"""

import io
import struct
import sys
import zipfile

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion,
                   descargar, escribir_json, punto_en_geometria, sha256)

URL = ("http://datos.energia.gob.ar/dataset/ff99e7be-7bab-4617-9588-9a74ae046a40/resource/"
       "be371445-5d0a-4ad7-8346-f1cdfb89c66f/download/-buenos-aires-alta-tensin-media-tensin-lneas.zip")
CRUDO = CRUDOS / "energia" / "-buenos-aires-alta-tensin-media-tensin-lneas.zip"
DECIMALES = 5

# Los valores vienen con mayúsculas y acentos dispares ("DISTRIBUCION" y "Distribucion").
NORMALIZAR = {
    "aereo": "Aérea", "aerea convencional": "Aérea", "aerea preensamblado": "Aérea preensamblada",
    "subterraneo": "Subterránea", "subterranea": "Subterránea", "distribucion": "Distribución",
    "mixto": "Mixta", "alumbrado publico": "Alumbrado público",
    "trifasico": "Trifásica", "monofasico": "Monofásica", "bifasico": "Bifásica",
}


def normalizar(valor):
    v = (valor or "").strip()
    return NORMALIZAR.get(v.lower(), v) if v else None


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
            fila[nombre] = r[p:p + largo].decode("latin1").strip()
            p += largo
        yield fila


def leer_shp(datos):
    """Devuelve (caja, partes) de cada registro de un shapefile de líneas; None si es nulo."""
    pos = 100
    while pos < len(datos):
        _, largo = struct.unpack(">ii", datos[pos:pos + 8])
        c = datos[pos + 8: pos + 8 + largo * 2]
        pos += 8 + largo * 2
        if struct.unpack("<i", c[:4])[0] == 0:
            yield None
            continue
        caja = struct.unpack("<4d", c[4:36])
        n_partes, n_puntos = struct.unpack("<ii", c[36:44])
        inicios = list(struct.unpack(f"<{n_partes}i", c[44:44 + 4 * n_partes])) + [n_puntos]
        base = 44 + 4 * n_partes
        puntos = [struct.unpack("<2d", c[base + 16 * k: base + 16 * k + 16]) for k in range(n_puntos)]
        yield caja, [puntos[inicios[j]:inicios[j + 1]] for j in range(n_partes)]


def main():
    if "--offline" not in sys.argv:
        try:
            descargar(URL, CRUDO, timeout=300)
        except ErrorRed as e:
            aviso(f"{e}\nSe usa el ZIP guardado en {CRUDO.relative_to(CRUDOS.parent.parent)}, si existe "
                  f"(se baja a mano desde {URL}).")
    if not CRUDO.exists():
        aviso(f"Falta {CRUDO.name}: la capa de media tensión queda pendiente de fuente.")
        return 1
    contenido = CRUDO.read_bytes()
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombres = z.namelist()
        prj = z.read(next(n for n in nombres if n.endswith(".prj"))).decode("latin1")
        if 'GEOGCS["WGS 84"' not in prj:
            aviso(f"Proyección inesperada ({prj[:80]}): no se procesa.")
            return 1
        shp = z.read(next(n for n in nombres if n.endswith(".shp")))
        dbf = z.read(next(n for n in nombres if n.endswith(".dbf")))

    limite, caja = cargar_limite()
    features, total, por_tension = [], 0, {}
    for fila, registro in zip(leer_dbf(dbf), leer_shp(shp)):
        total += 1
        if registro is None:
            continue
        (xmin, ymin, xmax, ymax), partes = registro
        if xmax < caja[0] or xmin > caja[2] or ymax < caja[1] or ymin > caja[3]:
            continue
        if not any(punto_en_geometria(x, y, limite, caja) for parte in partes for x, y in parte):
            continue
        tension = fila.get("TENSION")
        props = {
            "tension_kv": round(float(tension) / 1000, 1) if tension else None,
            "tipo": normalizar(fila.get("TIPO")),
            "funcion": normalizar(fila.get("FUNCION")),
            "clase": normalizar(fila.get("CLASE")),
            "cooperativa": fila.get("COOPERATIV") or None,
        }
        props = {k: v for k, v in props.items() if v is not None}
        por_tension[props.get("tension_kv")] = por_tension.get(props.get("tension_kv"), 0) + 1
        features.append({"type": "Feature", "properties": props, "geometry": {
            "type": "MultiLineString",
            "coordinates": [[[round(x, DECIMALES), round(y, DECIMALES)] for x, y in parte] for parte in partes]}})

    escribir_json(SITIO_DATOS / "media_tension.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("media_tension", {
        "archivo_crudo": f"energia/{CRUDO.name}",
        "sha256_crudo": sha256(contenido),
        "elementos": len(features),
        "tramos_en_la_provincia": total,
        "tramos_por_tension_kv": {str(k): v for k, v in por_tension.items()},
        "fecha_datos": None,
    })
    print(f"Media tensión: {len(features)} tramos en el partido (de {total} en la provincia); por tensión {por_tension}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
