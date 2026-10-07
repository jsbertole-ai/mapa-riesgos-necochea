"""Arma la capa "Frecuencia de anegamiento observada (1984 a 2024)" (aprobada por Sebastián el 07/10/2026).

Uso:  python3 scripts/armar_anegamiento.py            (descarga las hojas del JRC si faltan y arma)
      python3 scripts/armar_anegamiento.py --offline  (arma con lo guardado en datos/crudos/gsw/)

Dato: Global Surface Water del Joint Research Centre de la Comisión Europea, versión 1.5 (1984 a 2024),
capas de ocurrencia (en qué proporción de los meses observados hubo agua) y recurrencia (en qué
proporción de los años volvió el agua), a 30 m, a partir de imágenes Landsat. Licencia: programa
Copernicus, libre de cargo y sin restricción de uso, con cita obligatoria (Pekel et al., 2016).

Método: el del Ministerio de Desarrollo Agrario de la provincia para su "Mapa de Riesgo Hídrico"
(documento "Mapa de riesgo hídrico. Información complementaria", 2020): cada capa se divide en cinco
clases de 20 % y la combinación se clasifica con su matriz (ver MATRIZ). El Ministerio usó la versión
1984 a 2018; acá se aplica a la de 1984 a 2024. La clase "excepcional" que muestra el visor de la
Autoridad del Agua no figura en el documento del Ministerio y no se usa.

Las hojas del JRC vienen comprimidas con ZSTD, que la biblioteca estándar de Python no lee: este es el
único script del proyecto que necesita una librería externa (`pip install zstandard`). Sin ella, avisa
y no toca la capa publicada.

Salida: una imagen PNG con un color por clase, recortada al partido y reproyectada a la proyección
del mapa (Web Mercator, filas equiespaciadas), y un JSON con sus límites y la superficie de cada clase.
"""

import math
import struct
import sys
import zlib

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, descargar,
                   escribir_json, poligonos, sha256)

BASE = "https://s3.waw4-1.cloudferro.com/swift/v1/global-surface-water/download2024/Aggregated/VER1-5"
HOJAS = {c: (f"{BASE}/{c}/{c}_60W_30S_v1_5_2024.tif", CRUDOS / "gsw" / f"{c}_60W_30S_v1_5_2024.tif")
         for c in ("occurrence", "recurrence")}
CLASES = ["Mínima", "Media", "Alta", "Agua permanente"]
# Matriz del Ministerio de Desarrollo Agrario: fila = clase de recurrencia (1-20, 21-40, 41-60, 61-80,
# 81-100 %), columna = clase de ocurrencia; 0 mínima, 1 media, 2 alta, 3 agua permanente.
MATRIZ = [
    [0, 0, 1, 1, 2],
    [0, 1, 1, 2, 2],
    [1, 1, 1, 2, 2],
    [1, 1, 2, 2, 3],
    [2, 2, 3, 3, 3],
]
COLORES = [(0x91, 0xcf, 0x60), (0xff, 0xe0, 0x33), (0xe3, 0x1a, 0x1c), (0x1f, 0x6f, 0xc5)]
RESOLUCION_M = 30  # tamaño del píxel de salida sobre el terreno
R_TIERRA = 6378137.0


def clase_20(v):
    """1-20 -> 0, 21-40 -> 1, ..., 81-100 -> 4."""
    return min(4, (v - 1) // 20)


class Hoja:
    """GeoTIFF en mosaicos (tiles) de 8 bits, comprimido con ZSTD, en grados (EPSG:4326)."""

    def __init__(self, ruta, zstd):
        self.f = open(ruta, "rb")
        h = self.f.read(8)
        self.bo = "<" if h[:2] == b"II" else ">"
        if struct.unpack(self.bo + "H", h[2:4])[0] != 42:
            raise ValueError(f"{ruta.name}: no es un TIFF clásico")
        self.f.seek(struct.unpack(self.bo + "I", h[4:8])[0])
        n = struct.unpack(self.bo + "H", self.f.read(2))[0]
        tags = {}
        for _ in range(n):
            tag, tipo, cuenta, valor = struct.unpack(self.bo + "HHII", self.f.read(12))
            tags[tag] = (tipo, cuenta, valor)
        self.ancho, self.alto = self._valor(tags, 256), self._valor(tags, 257)
        self.tw, self.th = self._valor(tags, 322), self._valor(tags, 323)
        if self._valor(tags, 259) != 50000 or self._valor(tags, 258) != 8:
            raise ValueError(f"{ruta.name}: se esperaba ZSTD y 8 bits")
        self.offsets = self._lista(tags[324])
        self.cuentas = self._lista(tags[325])
        escala = self._dobles(tags[33550])
        punto = self._dobles(tags[33922])
        self.dx, self.dy = escala[0], escala[1]
        self.x0, self.y0 = punto[3] - punto[0] * self.dx, punto[4] + punto[1] * self.dy
        self.mosaicos_ancho = (self.ancho + self.tw - 1) // self.tw
        self.zstd = zstd.ZstdDecompressor()
        self.cache = {}

    def _valor(self, tags, tag):
        tipo, cuenta, valor = tags[tag]
        return valor & 0xFFFF if tipo == 3 and self.bo == "<" else valor

    def _lista(self, tag):
        tipo, cuenta, offset = tag
        self.f.seek(offset)
        fmt = {3: "H", 4: "I", 16: "Q"}[tipo]
        return struct.unpack(self.bo + fmt * cuenta, self.f.read(struct.calcsize(fmt) * cuenta))

    def _dobles(self, tag):
        _, cuenta, offset = tag
        self.f.seek(offset)
        return struct.unpack(self.bo + "d" * cuenta, self.f.read(8 * cuenta))

    def mosaico(self, i, j):
        clave = (i, j)
        if clave not in self.cache:
            k = i * self.mosaicos_ancho + j
            self.f.seek(self.offsets[k])
            self.cache[clave] = self.zstd.decompress(self.f.read(self.cuentas[k]), max_output_size=self.tw * self.th)
        return self.cache[clave]

    def fila(self, lat, lon0, lon1, n):
        """Valores de la fila de la hoja más cercana a `lat`, muestreados en n columnas entre lon0 y lon1."""
        r = int((self.y0 - lat) / self.dy)
        i, rr = divmod(r, self.th)
        salida = bytearray(n)
        paso = (lon1 - lon0) / n
        for c in range(n):
            col = int((lon0 + (c + 0.5) * paso - self.x0) / self.dx)
            j, cc = divmod(col, self.tw)
            salida[c] = self.mosaico(i, j)[rr * self.tw + cc]
        return salida


def merc_y(lat):
    return R_TIERRA * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def lat_de_merc(y):
    return math.degrees(2 * math.atan(math.exp(y / R_TIERRA)) - math.pi / 2)


def tramos(anillos, lat):
    """Longitudes donde la fila `lat` cruza el borde del partido (regla par-impar)."""
    xs = []
    for anillo in anillos:
        for (x1, y1), (x2, y2) in zip(anillo, anillo[1:]):
            if (y1 > lat) != (y2 > lat):
                xs.append(x1 + (lat - y1) * (x2 - x1) / (y2 - y1))
    xs.sort()
    return list(zip(xs[0::2], xs[1::2]))


def png_paleta(ruta, ancho, alto, filas, paleta):
    def bloque(tipo, datos):
        return struct.pack(">I", len(datos)) + tipo + datos + struct.pack(">I", zlib.crc32(tipo + datos) & 0xFFFFFFFF)
    crudo = b"".join(b"\x00" + bytes(f) for f in filas)
    plte = b"".join(bytes(c) for c in [(0, 0, 0)] + paleta)
    trns = bytes([0] + [255] * len(paleta))
    datos = (b"\x89PNG\r\n\x1a\n" + bloque(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 3, 0, 0, 0))
             + bloque(b"PLTE", plte) + bloque(b"tRNS", trns) + bloque(b"IDAT", zlib.compress(crudo, 9)) + bloque(b"IEND", b""))
    ruta.write_bytes(datos)
    return datos


def main():
    offline = "--offline" in sys.argv
    try:
        import zstandard
    except ImportError:
        aviso("Falta la librería zstandard (pip install zstandard): la capa de anegamiento no se rearma.")
        return 1
    for nombre, (url, ruta) in HOJAS.items():
        if not ruta.exists() and not offline:
            try:
                descargar(url, ruta, timeout=900)
            except ErrorRed as e:
                aviso(f"{nombre}: {e}")
        if not ruta.exists():
            aviso(f"Falta {ruta.name}: la capa de anegamiento no se arma.")
            return 1
    ocu = Hoja(HOJAS["occurrence"][1], zstandard)
    rec = Hoja(HOJAS["recurrence"][1], zstandard)
    limite, caja = cargar_limite()
    anillos = [anillo for pol in poligonos(limite) for anillo in pol]
    lon0, lat0, lon1, lat1 = caja
    lat_media = (lat0 + lat1) / 2
    # Píxel de salida de ~30 m sobre el terreno, expresado en la proyección del mapa.
    paso_merc = RESOLUCION_M / math.cos(math.radians(lat_media))
    ancho = math.ceil((math.radians(lon1 - lon0) * R_TIERRA) / paso_merc)
    y_norte, y_sur = merc_y(lat1), merc_y(lat0)
    alto = math.ceil((y_norte - y_sur) / paso_merc)
    paso_lon = (lon1 - lon0) / ancho
    filas, conteo = [], [0, 0, 0, 0]
    for f in range(alto):
        lat = lat_de_merc(y_norte - (f + 0.5) * paso_merc)
        fila = bytearray(ancho)
        dentro = tramos(anillos, lat)
        if dentro:
            vo = ocu.fila(lat, lon0, lon1, ancho)
            vr = rec.fila(lat, lon0, lon1, ancho)
            for a, b in dentro:
                for c in range(max(0, int((a - lon0) / paso_lon)), min(ancho, int((b - lon0) / paso_lon) + 1)):
                    o, r = vo[c], vr[c]
                    if 1 <= o <= 100 and 1 <= r <= 100:
                        k = MATRIZ[clase_20(r)][clase_20(o)]
                        fila[c] = k + 1
                        conteo[k] += 1
        filas.append(fila)
    # Superficie: el píxel mide paso_lon grados por (paso en latitud) grados; se usa el área en la latitud media.
    m_lon = math.radians(paso_lon) * R_TIERRA * math.cos(math.radians(lat_media))
    m_lat = (math.radians(lat1 - lat0) * R_TIERRA) / alto
    ha = [round(n * m_lon * m_lat / 10000) for n in conteo]
    salida_png = SITIO_DATOS / "anegamiento.png"
    datos = png_paleta(salida_png, ancho, alto, filas, COLORES)
    escribir_json(SITIO_DATOS / "anegamiento.json", {
        "imagen": "anegamiento.png",
        "limites": [[round(lat0, 6), round(lon0, 6)], [round(lat1, 6), round(lon1, 6)]],
        "clases": CLASES,
        "hectareas": dict(zip(CLASES, ha)),
        "pixeles": {"ancho": ancho, "alto": alto, "resolucion_m": RESOLUCION_M},
    })
    anotar_procesamiento("inundaciones_peligrosidad", {
        "archivo_crudo": "gsw/",
        "sha256_crudo": {r.name: sha256(r.read_bytes()) for _, r in HOJAS.values()},
        "elementos": sum(conteo),
        "por_tipo": dict(zip(CLASES, ha)),
        "png_bytes": len(datos),
        "fecha_datos": "Global Surface Water 1.5 del JRC: imágenes Landsat de 1984 a 2024 (publicado el 01/07/2026).",
    })
    print(f"Anegamiento: {ancho} x {alto} píxeles, {len(datos) / 1e6:.1f} MB; hectáreas por clase {dict(zip(CLASES, ha))}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
