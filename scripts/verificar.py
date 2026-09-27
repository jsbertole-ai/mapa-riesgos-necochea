"""Verifica las capas procesadas y genera docs/datos/capas.json para el sitio.

Uso:  python3 scripts/verificar.py            (vuelve a leer las páginas de licencia)
      python3 scripts/verificar.py --offline  (usa la última lectura guardada)

Una capa queda "verificada" solo si pasa todos los controles:
  1. el archivo existe, es GeoJSON válido y tiene elementos;
  2. todos los elementos tocan el partido (al menos un vértice dentro de su caja);
  3. ningún elemento lleva etiquetas excluidas (vigilancia), ni en el
     archivo publicado ni en la respuesta cruda de OpenStreetMap;
  4. la página de licencia de la fuente contiene la frase esperada (fuentes.json).
     En el inventario local, que es fuente propia, la licencia no se lee de una página:
     la acepta cada colaborador en el formulario ("licencia_propia" en fuentes.json).
Si falla uno, la capa se publica como "pendiente de fuente" y el motivo queda anotado.
"""

import html
import json
import re
import sys

from comun import (CRUDOS, FUENTES, PROCESAMIENTO, RAIZ, REGISTRO,
                   SITIO_DATOS, ErrorRed, ahora, aviso, descargar, escribir_json, excluido_osm, hoy, leer_json, vertices)

LICENCIAS = RAIZ / "datos" / "licencias_verificadas.json"


def texto_plano(contenido):
    t = contenido.decode("utf-8", "replace")
    t = re.sub(r"<script.*?</script>|<style.*?</style>", " ", t, flags=re.S)
    t = html.unescape(re.sub(r"<[^>]+>", " ", t))
    return re.sub(r"\s+", " ", t)


def verificar_licencia(capa, offline, cache):
    if capa.get("licencia_propia"):
        return True, capa["licencia_propia"]
    # Si la licencia está declarada en otro lugar (por ejemplo, la API de datos.gob.ar), se controla ahí;
    # url_licencia sigue siendo el texto de la licencia que ve el público.
    url, frase = capa.get("url_declaracion_licencia") or capa.get("url_licencia"), capa.get("frase_licencia")
    if not url or not frase:
        return False, "Sin URL o frase de licencia en fuentes.json."
    if not offline:
        try:
            texto = texto_plano(descargar(url, timeout=60))
            i = texto.lower().find(frase.lower())
            cache[url] = {
                "leido": ahora(),
                "frase": frase,
                "encontrada": i >= 0,
                "fragmento": texto[max(0, i - 150): i + len(frase) + 250].strip() if i >= 0 else None,
            }
        except ErrorRed as e:
            aviso(f"No se pudo leer la licencia {url}: {e}")
    lectura = cache.get(url)
    if not lectura or lectura.get("frase") != frase:
        return False, f"No hay lectura de {url} que confirme la licencia."
    if not lectura["encontrada"]:
        return False, f"La página {url} no contiene la frase esperada."
    return True, f"Licencia confirmada en {url} (leída el {lectura['leido'][:10]})."


def excluido(tags):
    return excluido_osm(tags)


def verificar_archivo(capa, caja):
    ruta = SITIO_DATOS / capa["archivo"]
    if not ruta.exists():
        return False, capa.get("mensaje_sin_archivo", "No se descargó todavía."), 0
    try:
        fc = json.loads(ruta.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        return False, f"GeoJSON inválido: {e}", 0
    features = fc.get("features") or []
    if fc.get("type") != "FeatureCollection" or not features:
        return False, "El archivo no tiene elementos.", 0
    fuera = 0
    for f in features:
        if not any(caja[0] <= x <= caja[2] and caja[1] <= y <= caja[3] for x, y, *_ in vertices(f["geometry"])):
            fuera += 1
    if fuera:
        return False, f"{fuera} elementos no tocan el partido.", len(features)
    prohibidos = sum(excluido(f.get("properties") or {}) for f in features)
    if prohibidos:
        return False, f"{prohibidos} elementos con etiquetas excluidas.", len(features)
    return True, f"{len(features)} elementos, todos dentro de la caja del partido y sin etiquetas excluidas.", len(features)


def verificar_crudo_osm(proc):
    ruta = CRUDOS / proc["archivo_crudo"]
    if not ruta.exists():
        return True, "Respuesta cruda de Overpass no disponible en esta copia; se confía en el control del archivo publicado."
    datos = json.loads(ruta.read_text(encoding="utf-8"))
    n = sum(excluido(e.get("tags") or {}) for e in datos.get("elements", []))
    if n:
        return False, f"La respuesta cruda de Overpass trae {n} elementos excluidos (la consulta no los filtró)."
    return True, "La respuesta cruda de Overpass no trae elementos de vigilancia."


def fecha_de_datos(capa, proc, registro):
    if capa.get("fecha_datos_fija"):
        # Capas cuya fuente no informa la fecha en los datos: se deja la nota de fuentes.json y el día de la consulta.
        return f"{capa['fecha_datos_fija']} Consulta al servicio: {(proc.get('procesado') or '')[:10]}."
    if capa["id"] == "limite":
        entrada = registro.get("datos/crudos/" + proc.get("archivo_crudo", ""), {})
        lm = entrada.get("last_modified")
        return f"Archivo publicado el {lm} (según el servidor); fecha de la geometría del IGN no informada." if lm else None
    if capa["licencia"].startswith("ODbL"):
        return f"Base de OpenStreetMap al {proc.get('fecha_datos')} (UTC)."
    return proc.get("fecha_datos")


def main():
    offline = "--offline" in sys.argv
    fuentes = leer_json(FUENTES)
    procesamiento = leer_json(PROCESAMIENTO, {})
    registro = leer_json(REGISTRO, {})
    cache = leer_json(LICENCIAS, {})
    limite = procesamiento.get("limite", {})
    caja = limite.get("caja")

    salida = []
    for capa in fuentes["capas"]:
        c = dict(capa)
        c.pop("frase_licencia", None)
        c.pop("fecha_datos_fija", None)
        c.pop("licencia_propia", None)
        c.pop("licencias_extra", None)
        c.pop("crudo_osm", None)
        c.pop("mensaje_sin_archivo", None)
        if not capa.get("archivo"):
            c["estado"] = "sin_fuente"
            salida.append(c)
            print(f"{capa['id']:26} sin fuente")
            continue
        controles = []
        if caja is None:
            controles.append((False, "Falta el límite del partido para verificar la cobertura."))
            n = 0
        else:
            ok, msj, n = verificar_archivo(capa, caja)
            controles.append((ok, msj))
        proc = procesamiento.get(capa["id"], {})
        if (capa["licencia"].startswith("ODbL") or capa.get("crudo_osm")) and proc and proc.get("sha256_crudo"):
            controles.append(verificar_crudo_osm(proc))
        controles.append(verificar_licencia(capa, offline, cache))
        # Capas con más de una fuente (por ejemplo, IGN y OpenStreetMap): se confirma cada licencia.
        for extra in capa.get("licencias_extra", []):
            controles.append(verificar_licencia(extra, offline, cache))
        verificada = all(ok for ok, _ in controles)
        c["estado"] = "verificada" if verificada else "pendiente"
        if verificada:
            c.pop("motivo_pendiente", None)
        c["elementos"] = n
        c["fecha_datos"] = fecha_de_datos(capa, proc, registro) if proc else None
        c["procesado"] = proc.get("procesado")
        if proc.get("por_organismo") is not None:
            c["por_organismo"] = proc["por_organismo"]
        if proc.get("por_tipo") is not None:
            c["por_tipo"] = proc["por_tipo"]
        if capa["id"].startswith("incendios_"):
            c["focos_por_anio"] = proc.get("focos_por_anio")
            c["focos_por_tipo"] = proc.get("focos_por_tipo")
        c["verificacion"] = {"fecha": hoy(), "controles": [m for _, m in controles]}
        salida.append(c)
        print(f"{capa['id']:26} {c['estado']}: " + " | ".join(m for _, m in controles))

    escribir_json(LICENCIAS, cache)
    escribir_json(SITIO_DATOS / "capas.json", {"generado": ahora(), "grupos": fuentes["grupos"], "capas": salida})
    return 0


if __name__ == "__main__":
    sys.exit(main())
