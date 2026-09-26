"""Funciones compartidas por los scripts de descarga y verificación.

Solo usa la biblioteca estándar de Python (3.9 o posterior), para que los
scripts corran en cualquier máquina sin instalar nada.
"""

import datetime as dt
import hashlib
import http.client
import json
import pathlib
import ssl
import sys
import time
import urllib.error
import urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
CRUDOS = RAIZ / "datos" / "crudos"
SITIO_DATOS = RAIZ / "docs" / "datos"
FUENTES = RAIZ / "datos" / "fuentes.json"
REGISTRO = RAIZ / "datos" / "registro_descargas.json"

AGENTE = "mapa-riesgos-necochea/1.0 (+https://github.com/jsbertole-ai/mapa-riesgos-necochea)"

# Etiquetas de OpenStreetMap que nunca entran al mapa (ver DATOS.md, sección 4).
EXCLUSIONES_OSM = {
    ("man_made", "surveillance"),
    ("amenity", "police"),
}
# Claves cuya sola presencia excluye el elemento (cámaras, sistemas de vigilancia).
CLAVES_EXCLUIDAS_OSM = ("surveillance", "surveillance:type", "camera:type", "police")


def hoy():
    return dt.date.today().isoformat()


def ahora():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def aviso(msj):
    print(msj, file=sys.stderr)


def descargar(url, destino=None, datos=None, timeout=180, reintentos=5):
    """Descarga una URL. Devuelve los bytes y, si hay destino, los guarda.

    Respeta HTTPS_PROXY y el almacén de certificados del sistema. Si la
    conexión se corta, reintenta contra el mismo servidor con espera creciente
    (2, 4, 8, 16 y 32 segundos); nunca prueba servidores alternativos. Una
    respuesta HTTP de error (404, 403, etc.) no se reintenta.
    """
    pedido = urllib.request.Request(url, data=datos, headers={"User-Agent": AGENTE})
    for intento in range(reintentos + 1):
        try:
            with urllib.request.urlopen(pedido, timeout=timeout, context=ssl.create_default_context()) as r:
                contenido = r.read()
                modificado = r.headers.get("Last-Modified")
            break
        except urllib.error.HTTPError as e:
            raise ErrorRed(f"{url} respondió {e.code} {e.reason}") from e
        except (urllib.error.URLError, OSError, http.client.HTTPException) as e:
            # HTTPException incluye IncompleteRead: el servidor cortó la transferencia a mitad de camino.
            if intento == reintentos:
                raise ErrorRed(f"Falló la conexión o la transferencia con {url[:90]}: {e}") from e
            espera = 2 ** (intento + 1)
            corta = url if len(url) < 90 else url[:87] + "..."
            aviso(f"  Conexión cortada con {corta} ({e}); reintento en {espera} s")
            time.sleep(espera)
    if destino is not None:
        destino = pathlib.Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(contenido)
        registrar_descarga(url, destino, contenido, modificado)
    return contenido


class ErrorRed(Exception):
    pass


def sha256(contenido):
    return hashlib.sha256(contenido).hexdigest()


def registrar_descarga(url, destino, contenido, modificado=None):
    """Anota cada descarga (URL, fecha, tamaño, huella y Last-Modified) en datos/registro_descargas.json."""
    registro = leer_json(REGISTRO, {})
    registro[str(pathlib.Path(destino).relative_to(RAIZ))] = {
        "url": url if len(url) < 300 else url.split("?")[0] + "?… (consulta abreviada; la completa la arma el script)",
        "descargado": ahora(),
        "last_modified": modificado,
        "bytes": len(contenido),
        "sha256": sha256(contenido),
    }
    escribir_json(REGISTRO, registro)


def leer_json(ruta, por_defecto=None):
    ruta = pathlib.Path(ruta)
    if not ruta.exists():
        return por_defecto
    return json.loads(ruta.read_text(encoding="utf-8"))


def escribir_json(ruta, objeto, compacto=False):
    ruta = pathlib.Path(ruta)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    if compacto:
        texto = json.dumps(objeto, ensure_ascii=False, separators=(",", ":"))
    else:
        texto = json.dumps(objeto, ensure_ascii=False, indent=2)
    ruta.write_text(texto + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Geometría mínima (sin dependencias): punto en polígono y cajas envolventes.
# Coordenadas en [longitud, latitud], como en GeoJSON.
# ---------------------------------------------------------------------------

def poligonos(geometria):
    """Devuelve la geometría como lista de polígonos (cada uno, lista de anillos)."""
    if geometria["type"] == "Polygon":
        return [geometria["coordinates"]]
    if geometria["type"] == "MultiPolygon":
        return geometria["coordinates"]
    raise ValueError(f"Se esperaba Polygon o MultiPolygon y llegó {geometria['type']}")


def _en_anillo(x, y, anillo):
    dentro = False
    j = len(anillo) - 1
    for i in range(len(anillo)):
        xi, yi = anillo[i][0], anillo[i][1]
        xj, yj = anillo[j][0], anillo[j][1]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            dentro = not dentro
        j = i
    return dentro


def punto_en_geometria(x, y, geometria, caja=None):
    if caja and not (caja[0] <= x <= caja[2] and caja[1] <= y <= caja[3]):
        return False
    for poligono in poligonos(geometria):
        if _en_anillo(x, y, poligono[0]) and not any(_en_anillo(x, y, h) for h in poligono[1:]):
            return True
    return False


def caja_envolvente(geometria):
    xs, ys = [], []
    for poligono in poligonos(geometria):
        for x, y, *_ in poligono[0]:
            xs.append(x)
            ys.append(y)
    return [min(xs), min(ys), max(xs), max(ys)]


def vertices(geometria):
    """Itera todos los vértices [x, y] de cualquier geometría GeoJSON."""
    def recorrer(c):
        if isinstance(c[0], (int, float)):
            yield c
        else:
            for sub in c:
                yield from recorrer(sub)
    yield from recorrer(geometria["coordinates"])


def cargar_limite():
    """Lee el límite procesado del partido. Sin límite no se recorta nada."""
    ruta = SITIO_DATOS / "limite.geojson"
    if not ruta.exists():
        aviso(
            "Falta docs/datos/limite.geojson. Corré primero scripts/descargar_limite.py "
            "(o dejá el archivo de Georef en datos/crudos/ y corré el mismo script)."
        )
        sys.exit(2)
    fc = leer_json(ruta)
    geometria = fc["features"][0]["geometry"]
    return geometria, caja_envolvente(geometria)


PROCESAMIENTO = RAIZ / "datos" / "procesamiento.json"


def anotar_procesamiento(capa, datos):
    """Guarda lo que surge de procesar una capa (cantidad, fechas, origen) para verificar.py."""
    registro = leer_json(PROCESAMIENTO, {})
    registro[capa] = {"procesado": ahora(), **datos}
    escribir_json(PROCESAMIENTO, registro)


def coleccion(features):
    return {"type": "FeatureCollection", "features": features}
