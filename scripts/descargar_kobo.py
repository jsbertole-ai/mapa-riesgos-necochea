"""Baja las respuestas del formulario del inventario local desde la API de KoboToolbox.

Uso:  python3 scripts/descargar_kobo.py

Necesita la variable de entorno KOBO_TOKEN (la API Key de la cuenta de Sebastián, cargada en
el entorno, nunca en el repositorio). El servidor es https://kf.kobotoolbox.org salvo que se
indique otro en KOBO_SERVIDOR. La API espera el encabezado "Authorization: Token <clave>"
(esquema TokenAuth de https://kf.kobotoolbox.org/api/v2/schema/, leído el 28/09/2026).

Busca el formulario por su título (datos/inventario/formulario.json) y guarda todas las
respuestas en datos/crudos/inventario/kobo_AAAA-MM-DD.csv, con las mismas columnas que la
exportación "XML values and headers", para que las procese scripts/procesar_inventario.py.
Esa carpeta no se sube al repositorio: tiene envíos sin aprobar.

Muestra en pantalla (nunca en un archivo público) los envíos que esperan la ponderación y la
decisión de Sebastián: los que no están aprobados ni rechazados en Kobo.
"""

import csv
import datetime as dt
import json
import os
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request

from comun import CRUDOS, RAIZ, aviso, leer_json

CONFIG = RAIZ / "datos" / "inventario" / "formulario.json"
CARPETA = CRUDOS / "inventario"
APROBADO = "validation_status_approved"
RECHAZADO = "validation_status_not_approved"


def pedir(url, token):
    pedido = urllib.request.Request(url, headers={"Authorization": f"Token {token}", "Accept": "application/json"})
    with urllib.request.urlopen(pedido, timeout=120, context=ssl.create_default_context()) as r:
        return json.loads(r.read())


def todas(url, token):
    """Recorre una lista paginada de la API (campos results y next)."""
    resultados = []
    while url:
        pagina = pedir(url, token)
        resultados += pagina.get("results", [])
        url = pagina.get("next")
    return resultados


def estado(envio):
    v = envio.get("_validation_status") or {}
    return v.get("uid", "") if isinstance(v, dict) else str(v)


def main():
    token = os.environ.get("KOBO_TOKEN", "").strip()
    if not token:
        aviso("Falta la variable de entorno KOBO_TOKEN: no se puede consultar Kobo.")
        return 1
    servidor = os.environ.get("KOBO_SERVIDOR", "https://kf.kobotoolbox.org").rstrip("/")
    titulo = leer_json(CONFIG)["titulo"]
    try:
        activos = todas(f"{servidor}/api/v2/assets/?{urllib.parse.urlencode({'format': 'json', 'q': 'asset_type:survey'})}", token)
        propios = [a for a in activos if (a.get("name") or "").strip() == titulo]
        if len(propios) != 1:
            aviso(f"Se esperaba un formulario llamado \"{titulo}\" y se encontraron {len(propios)}.")
            return 1
        uid = propios[0]["uid"]
        envios = todas(f"{servidor}/api/v2/assets/{uid}/data/?format=json", token)
    except urllib.error.HTTPError as e:
        aviso(f"Kobo respondió {e.code} {e.reason}" + (" (¿clave vencida o mal cargada?)" if e.code in (401, 403) else ""))
        return 1
    except (urllib.error.URLError, OSError) as e:
        aviso(f"No se pudo conectar con {servidor}: {e}")
        return 1

    # Mismas columnas que la exportación "XML values and headers"; el estado de validación, plano.
    columnas = []
    for e in envios:
        for k in e:
            if k not in columnas and not isinstance(e[k], (dict, list)):
                columnas.append(k)
    for k in ("_validation_status", "_id", "_submission_time"):
        if k not in columnas:
            columnas.append(k)
    CARPETA.mkdir(parents=True, exist_ok=True)
    ruta = CARPETA / f"kobo_{dt.date.today().isoformat()}.csv"
    with open(ruta, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=columnas, extrasaction="ignore")
        w.writeheader()
        for e in envios:
            fila = {k: e.get(k, "") for k in columnas}
            fila["_validation_status"] = estado(e)
            w.writerow(fila)

    pendientes = [e for e in envios if estado(e) not in (APROBADO, RECHAZADO)]
    aprobados = sum(1 for e in envios if estado(e) == APROBADO)
    print(f"Kobo: {len(envios)} envíos ({aprobados} aprobados, {len(envios) - aprobados - len(pendientes)} rechazados, "
          f"{len(pendientes)} esperan la decisión de Sebastián). Guardados en {ruta.relative_to(RAIZ) if ruta.is_relative_to(RAIZ) else ruta}.")
    for e in sorted(pendientes, key=lambda e: e.get("_submission_time", "")):
        print(f"- Envío {e.get('_id')} (cargado el {e.get('_submission_time', '')[:10]}, estado: {estado(e) or 'sin revisar'}): "
              f"{e.get('tipo_registro', '')} {e.get('tipo_evento') or e.get('tipo_vulnerabilidad') or ''}, "
              f"{e.get('fecha', '')}, {e.get('localidad', '')}. Nota: {e.get('fuente_url', '')}")
        print(f"  {(e.get('descripcion') or '').strip()[:400]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
