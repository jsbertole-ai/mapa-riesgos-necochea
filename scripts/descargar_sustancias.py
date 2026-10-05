"""Capa "Sustancias peligrosas": combustibles, gas envasado, plantas aceiteras y terminales de fertilizantes del partido.

Uso:  python3 scripts/descargar_sustancias.py            (descarga y procesa)
      python3 scripts/descargar_sustancias.py --offline  (procesa lo ya guardado en datos/crudos/sustancias/)

Listados oficiales de la Secretaría de Energía (Datos Argentina, CC BY 4.0):
  - Padrón de operadores autorizados para la venta de combustibles líquidos (Res. SE 1102/2004):
    Excel 97 dentro de un ZIP, que se lee con scripts/leer_xls.py. Trae dirección, no coordenadas.
    Se descartan los fleteros (distribuidores por cuenta de terceros), que no almacenan.
  - Distribuidoras de GLP (registro de la Res. SE 800/2004), con coordenadas.
  - Plantas productoras y refinadoras de aceite vegetal, con coordenadas.
Además, los establecimientos sin listado oficial con ubicación que documenta otra fuente pública (la
terminal de fertilizantes Pier Doce, por su presentación ante la ANMaC), en "otras_fuentes" de
datos/sustancias/ubicaciones.json.

Regla de ubicación (CLAUDE.md, decisión de Sebastián del 28/09/2026): cada establecimiento se ubica
uno por uno y el punto, con su origen, queda en datos/sustancias/ubicaciones.json; se publica solo
lo que Sebastián aprobó. Lo que aparezca nuevo en los listados queda sin publicar hasta que se lo
ubique y se lo apruebe. No se publican titulares, CUIT, teléfonos ni correos, aunque la fuente los
traiga: solo el tipo de establecimiento, la dirección que da la fuente y el origen del punto.
"""

import csv
import io
import json
import re
import sys
import unicodedata
import zipfile

from comun import (CRUDOS, RAIZ, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion,
                   descargar, escribir_json, leer_json, punto_en_geometria, sha256)
from leer_xls import leer_xls

CARPETA = CRUDOS / "sustancias"
UBICACIONES = RAIZ / "datos" / "sustancias" / "ubicaciones.json"
PADRON = ("http://sgda.energia.gob.ar/sgdaint/publico/res1102-padronoperadores-publico.xls.zip",
          CARPETA / "res1102-padronoperadores-publico.xls.zip")
GLP = ("http://datos.energia.gob.ar/dataset/075c393d-5ad1-4cb0-a653-e953c313796d/resource/"
       "7f0464ef-9067-4f00-91b3-00b46fde1c39/download/distribuidoras-de-glp.csv",
       CARPETA / "distribuidoras-de-glp.csv")
ACEITERAS = ("http://datos.energia.gob.ar/dataset/a9115f5b-084c-4169-92a5-ea85f4a166eb/resource/"
             "3f177450-8d92-48e9-a846-91537db5322e/download/plantas-productoras-y-refinadoras-de-aceite-vegetal.csv",
             CARPETA / "plantas-productoras-y-refinadoras-de-aceite-vegetal.csv")

# Localidades del partido tal como las escribe el padrón (sin tildes). "Arroyo Dulce" es de Salto.
LOCALIDADES = {"NECOCHEA", "QUEQUEN", "PUERTO QUEQUEN", "LA DULCE", "NICANOR OLIVERA", "ENERGIA",
               "JUAN N FERNANDEZ", "JUAN N. FERNANDEZ", "JUAN NEPOMUCENO FERNANDEZ", "CLARAZ",
               "RAMON SANTAMARINA", "SANTAMARINA", "MEDANO BLANCO", "COSTA BONITA"}
NOMBRES = {"QUEQUEN": "Quequén", "PUERTO QUEQUEN": "Quequén", "PTO. QUEQUEN": "Quequén", "ENERGIA": "Energía", "JUAN N FERNANDEZ": "Juan N. Fernández",
           "JUAN N. FERNANDEZ": "Juan N. Fernández", "JUAN NEPOMUCENO FERNANDEZ": "Juan N. Fernández",
           "RAMON SANTAMARINA": "Ramón Santamarina", "SANTAMARINA": "Ramón Santamarina", "MEDANO BLANCO": "Médano Blanco"}
ESTACIONES = "Estaciones de servicio"
DEPOSITOS = "Depósitos de combustible"
GAS = "Gas envasado (GLP)"
ACEITE = "Plantas aceiteras"
FERTILIZANTES = "Terminales de fertilizantes"
# Si en un mismo punto hay más de un establecimiento, el color es el de la categoría que va primero.
PRIORIDAD = (DEPOSITOS, FERTILIZANTES, GAS, ACEITE, ESTACIONES)


def sin_tildes(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto or "") if unicodedata.category(c) != "Mn")


def limpio(texto):
    return " ".join((texto or "").split())


def direccion_publicable(texto):
    """La dirección tal como la da la fuente, sin el "0" de relleno del padrón ni etiquetas HTML."""
    texto = re.sub(r"<[^>]+>", " ", texto or "")
    return limpio(re.sub(r"(?<=\s)0(?=\s|$)", " ", " " + texto + " "))


def localidad(texto):
    clave = sin_tildes(limpio(texto)).upper()
    return NOMBRES.get(clave, limpio(texto).title())


def categoria_padron(tipo):
    t = sin_tildes(tipo).lower()
    if "fletero" in t:
        return None
    if "venta por menor" in t:
        return ESTACIONES
    return DEPOSITOS


def bajar(fuente, offline):
    url, ruta = fuente
    if not offline:
        try:
            descargar(url, ruta, timeout=180)
        except ErrorRed as e:
            aviso(f"{e}\nSe usa el archivo guardado en {ruta.parent.relative_to(RAIZ)}/, si existe.")
    return ruta.read_bytes() if ruta.exists() else None


def leer_csv(contenido):
    texto = contenido.decode("utf-8-sig", errors="replace")
    separador = max((";", ","), key=texto.splitlines()[0].count)
    return list(csv.DictReader(io.StringIO(texto), delimiter=separador))


def registros_padron(contenido):
    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        nombre = next(n for n in z.namelist() if n.lower().endswith(".xls"))
        hojas = leer_xls(z.read(nombre))
    filas = next(iter(hojas.values()))
    actualizado = next((limpio(str(f[0])) for f in filas[:5] if "ACTUALIZADO" in str(f[0]).upper()), None)
    i = next(k for k, f in enumerate(filas) if str(f[0]).strip().upper() == "EXPEDIENTE")
    col = {sin_tildes(limpio(str(c))).upper(): k for k, c in enumerate(filas[i])}
    salida = []
    for f in filas[i + 1:]:
        if sin_tildes(limpio(f[col["PROVINCIA"]])).upper() != "BUENOS AIRES":
            continue
        if sin_tildes(limpio(f[col["LOCALIDAD"]])).upper() not in LOCALIDADES:
            continue
        tipo = limpio(f[col["TIPO NEGOCIO"]])
        salida.append({
            "clave": limpio(f[col["EXPEDIENTE"]]),
            "categoria": categoria_padron(tipo),
            "tipo": tipo.replace("general(", "general ("),
            "detalle": limpio(f[col["TIPO BOCA EXPENDIO"]]) or None,
            "direccion": direccion_publicable(f[col["DIRECCION"]]),
            "localidad": localidad(f[col["LOCALIDAD"]]),
            "fuente": "Padrón de operadores de combustibles líquidos (Res. SE 1102/2004)",
        })
    return salida, actualizado


def registros_glp(contenido):
    salida = []
    for f in leer_csv(contenido):
        if sin_tildes(limpio(f.get("partido"))).upper() != "NECOCHEA" or limpio(f.get("provincia")).upper() != "BUENOS AIRES":
            continue
        try:
            coord = [float(f["lat_gis"]), float(f["lon_gis"])]
        except (KeyError, ValueError):
            coord = None
        actividad = limpio(re.sub(r"<[^>]+>", " ", f.get("actividad", "")))
        m = re.search(r"hasta (\d+) kgrs.*categoria (\d)", sin_tildes(actividad), re.I)
        actividad = f"Envases de hasta {m.group(1)} kg (categoría {m.group(2)})" if m else actividad.capitalize()
        salida.append({"clave": direccion_publicable(f.get("direccion")), "categoria": GAS,
                       "tipo": "Distribuidora de gas envasado (GLP)", "detalle": actividad,
                       "direccion": direccion_publicable(f.get("direccion")).replace(" N/KM ", " "),
                       "localidad": localidad(f.get("localidad")), "coord_fuente": coord,
                       "fuente": "Registro de la industria del GLP (Res. SE 800/2004), distribuidoras"})
    return salida


def registros_aceiteras(contenido):
    salida = []
    for f in leer_csv(contenido):
        if limpio(f.get("departamento")) != "Necochea" or limpio(f.get("provincia")).upper() != "BUENOS AIRES":
            continue
        try:
            coord = json.loads(f["geojson"])["coordinates"]
            coord = [coord[1], coord[0]]
        except (KeyError, ValueError, TypeError, IndexError):
            coord = None
        detalle = f"{limpio(f.get('tipo_planta'))}; {limpio(f.get('grano'))}"
        if limpio(f.get("tn_prod_diar")).isdigit():
            detalle += f"; {int(f['tn_prod_diar']):,} toneladas por día".replace(",", ".")
        salida.append({"clave": limpio(f.get("establecimiento")), "categoria": ACEITE, "tipo": "Planta aceitera",
                       "detalle": detalle, "direccion": None, "localidad": localidad(f.get("localidad")),
                       "coord_fuente": coord,
                       "fuente": "Plantas productoras y refinadoras de aceite vegetal"})
    return salida


def main():
    offline = "--offline" in sys.argv
    ubicaciones = leer_json(UBICACIONES, {})
    limite, caja = cargar_limite()
    crudos = {"padron": bajar(PADRON, offline), "glp": bajar(GLP, offline), "aceiteras": bajar(ACEITERAS, offline)}
    if not all(crudos.values()):
        faltan = [k for k, v in crudos.items() if not v]
        aviso(f"Faltan listados ({', '.join(faltan)}): la capa de sustancias peligrosas no se arma.")
        return 1
    padron, actualizado = registros_padron(crudos["padron"])
    listas = {"padron_1102": padron, "glp": registros_glp(crudos["glp"]), "aceiteras": registros_aceiteras(crudos["aceiteras"])}

    por_punto, estado = {}, {"publicados": 0, "sin_aprobar": [], "sin_ubicar": [], "nuevos": [], "fuera_del_partido": [],
                              "fleteros": 0}
    for lista, registros in listas.items():
        conocidos = ubicaciones.get(lista, {})
        for r in registros:
            if r["categoria"] is None:
                estado["fleteros"] += 1
                continue
            u = conocidos.get(r["clave"])
            if u is None:
                estado["nuevos"].append(f"{lista}: {r['clave']}")
                continue
            if "sin_ubicar" in u:
                estado["sin_ubicar"].append(f"{lista}: {r['clave']} ({u['sin_ubicar']})")
                continue
            if not u.get("aprobado"):
                estado["sin_aprobar"].append(f"{lista}: {r['clave']}")
                continue
            punto = r.get("coord_fuente") if u["punto"] == "fuente" else u["punto"]
            if not punto:
                estado["sin_ubicar"].append(f"{lista}: {r['clave']} (la fuente dejó de traer coordenadas)")
                continue
            lat, lon = round(punto[0], 5), round(punto[1], 5)
            if not punto_en_geometria(lon, lat, limite, caja):
                estado["fuera_del_partido"].append(f"{lista}: {r['clave']}")
                continue
            registro = {k: r[k] for k in ("categoria", "tipo", "detalle", "direccion", "localidad", "fuente") if r.get(k)}
            registro["punto"] = u["fuente_punto"]
            por_punto.setdefault((lon, lat), []).append(registro)
            estado["publicados"] += 1

    # Establecimientos sin listado oficial con ubicación, documentados por otra fuente pública
    # (por ejemplo, la terminal de fertilizantes Pier Doce): traen sus datos y su fuente completos.
    for clave, u in ubicaciones.get("otras_fuentes", {}).items():
        if clave.startswith("_"):
            continue
        if not u.get("aprobado"):
            estado["sin_aprobar"].append(f"otras_fuentes: {clave}")
            continue
        lat, lon = round(u["punto"][0], 5), round(u["punto"][1], 5)
        if not punto_en_geometria(lon, lat, limite, caja):
            estado["fuera_del_partido"].append(f"otras_fuentes: {clave}")
            continue
        registro = {k: u[k] for k in ("categoria", "tipo", "detalle", "localidad", "fuentes") if u.get(k)}
        registro["punto"] = u["fuente_punto"]
        por_punto.setdefault((lon, lat), []).append(registro)
        estado["publicados"] += 1

    features = []
    for (lon, lat), registros in sorted(por_punto.items()):
        categoria = next(c for c in PRIORIDAD if any(r["categoria"] == c for r in registros))
        features.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
                         "properties": {"categoria": categoria, "registros": registros}})
    por_tipo = {c: sum(1 for f in features if f["properties"]["categoria"] == c) for c in PRIORIDAD}
    escribir_json(SITIO_DATOS / "sustancias_peligrosas.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("sustancias_peligrosas", {
        "archivo_crudo": "sustancias/",
        "sha256_crudo": {PADRON[1].name: sha256(crudos["padron"]), GLP[1].name: sha256(crudos["glp"]),
                         ACEITERAS[1].name: sha256(crudos["aceiteras"])},
        "elementos": len(features),
        "registros": estado["publicados"],
        "por_tipo": por_tipo,
        "fleteros_descartados": estado["fleteros"],
        "sin_aprobar": estado["sin_aprobar"],
        "sin_ubicar": estado["sin_ubicar"],
        "nuevos_en_los_listados": estado["nuevos"],
        "fuera_del_partido": estado["fuera_del_partido"],
        "fecha_datos": (f"Padrón de combustibles {actualizado.lower() if actualizado else 'sin fecha'}; "
                        "distribuidoras de GLP y plantas aceiteras según la fecha de cada recurso en Datos Argentina."),
    })
    print(f"Sustancias peligrosas: {estado['publicados']} establecimientos publicados en {len(features)} puntos {por_tipo}; "
          f"{len(estado['sin_aprobar'])} esperan la aprobación de Sebastián, {len(estado['sin_ubicar'])} sin ubicar, "
          f"{len(estado['nuevos'])} nuevos en los listados, {estado['fleteros']} fleteros descartados.")
    for n in estado["nuevos"]:
        aviso(f"  Nuevo en el listado, sin ubicar ni aprobar: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
