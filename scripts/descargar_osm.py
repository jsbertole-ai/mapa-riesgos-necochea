"""Hidrografía detallada e infraestructura portuaria e industrial desde OpenStreetMap.

Uso:  python3 scripts/descargar_osm.py            (consulta Overpass y procesa)
      python3 scripts/descargar_osm.py --offline  (procesa lo ya guardado en datos/crudos/osm/)
      python3 scripts/descargar_osm.py respuesta  (solo una consulta: hidrografia, portuaria, torres, respuesta o antenas)

Requiere el límite del partido (scripts/descargar_limite.py). La consulta usa
la caja envolvente del límite y después recorta por el polígono: queda todo
elemento con al menos un vértice dentro del partido.

Exclusiones (DATOS.md, sección 4): se descartan en la consulta y otra vez al
procesar los elementos con man_made=surveillance o claves de
vigilancia (ver comun.excluido_osm). Las comisarías y los demás cuerpos de respuesta
sí se publican. Además solo se conservan las etiquetas de la lista TAGS_CONSERVADAS,
para no arrastrar teléfonos, correos ni otros datos de contacto.

Licencia: ODbL 1.0. Los archivos resultantes son una base derivada de
OpenStreetMap y se publican bajo la misma licencia.
"""

import json
import re
import sys
import time
import urllib.parse

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, registrar_descarga, es_prefectura, excluido_osm, aviso, cargar_limite, coleccion, descargar, escribir_json,
                   punto_en_geometria, sha256, vertices)

OVERPASS = "https://overpass-api.de/api/interpreter"
# Servidor de respaldo, autorizado por Sebastián el 27/09/2026 cuando overpass-api.de cortaba las conexiones
# del entorno y le respondía 403 a él. Es una instancia pública de la lista de la wiki de OSM
# (https://wiki.openstreetmap.org/wiki/Overpass_API), de VK Maps; sirve la misma base de OSM, bajo ODbL.
# Qué servidor respondió queda anotado en el procesamiento de cada capa.
OVERPASS_RESPALDO = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

EXCLUIR_EN_CONSULTA = """
  nwr["man_made"="surveillance"]({caja});
  nwr["surveillance"]({caja});
  nwr["surveillance:type"]({caja});
"""

CONSULTAS = {
    "hidrografia": """
  way["waterway"~"^(river|stream|canal|drain|ditch)$"]({caja});
  nwr["natural"="water"]({caja});
  way["natural"="coastline"]({caja});
""",
    "portuaria": """
  nwr["landuse"~"^(industrial|port)$"]({caja});
  nwr["industrial"="port"]({caja});
  nwr["harbour"]({caja});
  nwr["man_made"~"^(silo|storage_tank|pier|breakwater)$"]({caja});
""",
    # Torres y postes de las líneas eléctricas; las líneas se piden para saber la tensión de cada poste.
    # También todo otro poste de la vía pública (pedido de Sebastián, 27/09/2026): postes de servicios,
    # de telecomunicaciones y columnas de alumbrado.
    "torres": """
  way["power"~"^(line|minor_line|cable)$"]({caja});
  node["power"~"^(tower|pole)$"]({caja});
  node["man_made"="utility_pole"]({caja});
  node["telecom"="pole"]({caja});
  node["highway"="street_lamp"]({caja});
""",
    "respuesta": """
  nwr["amenity"="fire_station"]({caja});
  nwr["amenity"="police"]({caja});
  nwr["name"~"Cruz Roja",i][!"highway"]({caja});
  nwr["name"~"Defensa Civil",i]({caja});
  nwr["name"~"Centro Operativo de Monitoreo",i]({caja});
  nwr["emergency"="lifeguard"]({caja});
  nwr["office"="lifeguard"]({caja});
  nwr["amenity"="ranger_station"]({caja});
  nwr["name"~"prefectura",i][!"highway"]({caja});
  nwr["operator"~"prefectura",i][!"highway"]({caja});
  nwr["club"="amateur_radio"]({caja});
  nwr["name"~"radio ?club",i][!"highway"]({caja});
""",
    # Antenas y torres de comunicaciones (telefonía, radio, televisión, radioaficionados). Pedido de
    # Sebastián (27/09/2026): toda antena debe figurar, sea del Estado o privada.
    "antenas": """
  nwr["man_made"~"^(mast|tower|antenna|communications_tower)$"]({caja});
""",
}

# Elementos con ubicación en duda: se descartan mientras sigan en la posición registrada acá.
# Si alguien los corrige en OSM (los mueve más de 100 m), vuelven a entrar solos.
EN_REVISION = {
    # Defensa Civil figuraba en el Palacio Municipal (calle 56), donde no funciona desde hace años; según el
    # municipio está "sobre avenida 10, casi Pinolandia". Sebastián movió el nodo en OSM (versión 8,
    # 26/09/2026). La entrada se mantiene para que una respuesta vieja de Overpass no reintroduzca la
    # posición del Palacio: el nodo movido está a casi 3 km y ya no la cumple.
    "node/4092470096": (-58.7387, -38.5560),
}


def en_revision(el, geom):
    registro = EN_REVISION.get(f"{el['type']}/{el['id']}")
    if not registro or geom["type"] != "Point":
        return False
    x, y = geom["coordinates"]
    return abs(x - registro[0]) * 87 < 0.1 and abs(y - registro[1]) * 111 < 0.1  # 100 m, en km por grado


# En la capa de respuesta solo se conserva qué es y su nombre: el operador de un cuartel
# puede ser el nombre de una persona.
TAGS_RESPUESTA = {"name", "official_name", "description", "amenity", "office", "government", "emergency", "lifeguard",
                  "seasonal", "police", "club"}

# Antenas: se descartan las torres que no son de comunicaciones (campanarios, miradores, iluminación, etc.).
TORRES_NO_COMUNICACION = {"lighting", "bell_tower", "observation", "defensive", "minaret", "watchtower", "cooling",
                          "pagoda", "lightning_protection", "transition", "anchor", "siren", "radar", "monitoring"}
TAGS_ANTENAS = {"name", "man_made", "tower:type", "tower:construction", "operator", "height", "ele"}

TAGS_CONSERVADAS = {
    "name", "waterway", "natural", "water", "intermittent", "landuse", "industrial", "harbour",
    "man_made", "content", "product", "operator",
}

# El ferrocarril y las rutas salen del IGN (descargar_ign.py). Si una respuesta vieja de Overpass
# todavía los trae, se descartan acá.
def capa_portuaria(tags):
    if "railway" in tags or "highway" in tags or "hgv" in tags:
        if not any(k in tags for k in ("landuse", "industrial", "harbour", "man_made")):
            return None
    return "portuaria_instalaciones"


def procesar_torres(datos, limite, caja):
    """Torres y postes eléctricos, con la tensión de la línea a la que pertenecen (si se conoce)."""
    tension = {}
    for el in datos.get("elements", []):
        t = el.get("tags") or {}
        if el["type"] == "way" and t.get("power") in ("line", "minor_line", "cable") and t.get("voltage"):
            kv = [round(int(v) / 1000, 1) for v in t["voltage"].split(";") if v.strip().isdigit()]
            for n in el.get("nodes", []):
                tension.setdefault(n, set()).update(kv)
    features, postes = [], []
    for el in datos.get("elements", []):
        t = el.get("tags") or {}
        if el["type"] != "node" or excluido(t):
            continue
        if not punto_en_geometria(el["lon"], el["lat"], limite, caja):
            continue
        punto_osm = {"type": "Point", "coordinates": [round(el["lon"], DECIMALES), round(el["lat"], DECIMALES)]}
        kv = sorted(tension.get(el["id"], []))
        # Torres, y postes de líneas con tensión conocida: capa de torres y postes de líneas eléctricas.
        if t.get("power") == "tower" or (t.get("power") == "pole" and kv and max(kv) >= 1):
            props = {"power": t["power"], "osm": f"node/{el['id']}"}
            if kv:
                props["tension_kv"] = kv
            features.append({"type": "Feature", "properties": props, "geometry": punto_osm})
            continue
        tipo = tipo_de_poste(t)
        if tipo:
            props = {"tipo": tipo, "osm": f"node/{el['id']}"}
            for k in ("operator", "utility", "material", "height"):
                if t.get(k):
                    props[k] = t[k]
            postes.append({"type": "Feature", "properties": props, "geometry": punto_osm})
    return {"torres_postes": features, "postes_via_publica": postes}


def tipo_de_poste(t):
    """Tipo de poste de la vía pública según sus etiquetas de OSM (None si no es un poste)."""
    usos = (t.get("utility") or "").split(";")
    if t.get("power") == "pole":
        return "Poste eléctrico de baja tensión o sin tensión informada"
    if t.get("highway") == "street_lamp":
        return "Columna de alumbrado público"
    if t.get("telecom") == "pole" or (t.get("man_made") == "utility_pole" and usos == ["telecom"]):
        return "Poste de telecomunicaciones"
    if t.get("man_made") == "utility_pole":
        if "power" in usos and "telecom" in usos:
            return "Poste compartido (electricidad y telecomunicaciones)"
        if "power" in usos:
            return "Poste eléctrico de baja tensión o sin tensión informada"
        if "street_lighting" in usos:
            return "Columna de alumbrado público"
        return "Poste de servicios (uso no informado)"
    return None


# Notas de colaboradores y fuentes para antenas puntuales (01/10/2026). El texto va a la ventana.
NOTAS_ANTENAS = {
    "node/14231588201": "La de uso más intensivo de la ciudad: es de Telefónica de Argentina y la comparten otras "
                        "empresas (según un colaborador). Se levanta en el predio de calle 61 entre 54 y 56, que la "
                        "estatal ENTel compró el 25 de julio de 1958 y donde en 1969 se puso en marcha la Central "
                        "Telefónica Automática (Ecos Diarios, 03/08/2025: https://elecos.com.ar/evolucion-del-servicio-"
                        "telefonico-en-necochea-a-traves-los-tiempos); la nota no menciona la torre.",
    "node/14235360716": "Antena de radiocomunicaciones de los Bomberos Voluntarios, en el predio lindero a la Unidad "
                        "Sanitaria que el municipio les cedió en comodato (Ordenanza 10009/2019).",
}


def uso_antena(t):
    """Clasifica la antena por servicio según sus etiquetas communication:* (pedido de Sebastián, 01/10/2026).
    Las que dan telefonía móvil y además radio o televisión son "de usos múltiples"."""
    def si(*claves):
        return any(t.get("communication:" + c) not in (None, "no") for c in claves)
    movil = si("mobile_phone", "gsm", "3g", "4g", "lte", "5g")
    radio = si("radio", "television", "amateur_radio", "broadcast")
    if movil and radio:
        return "Usos múltiples"
    if movil:
        return "Telefonía móvil"
    if radio:
        return "Radio y televisión"
    return "Sin clasificar"


def procesar_antenas(datos, limite, caja):
    """Antenas, mástiles y torres de comunicaciones como puntos (los edificios o predios, en su centro)."""
    features, descartadas = [], 0
    for el in datos.get("elements", []):
        t = el.get("tags") or {}
        if excluido(t):
            continue
        mm = t.get("man_made")
        tipo = t.get("tower:type")
        if mm == "tower" and tipo != "communication" and not any(k.startswith("communication:") for k in t):
            descartadas += 1
            continue
        if tipo in TORRES_NO_COMUNICACION:
            descartadas += 1
            continue
        geom = geometria(el, t)
        if geom is None:
            continue
        xs = [c[0] for c in vertices(geom)]
        ys = [c[1] for c in vertices(geom)]
        x, y = sum(xs) / len(xs), sum(ys) / len(ys)
        if not punto_en_geometria(x, y, limite, caja):
            continue
        props = {k: v for k, v in t.items() if k in TAGS_ANTENAS or k.startswith("communication:")}
        props["tipo"] = uso_antena(t)
        if f"{el['type']}/{el['id']}" in NOTAS_ANTENAS:
            props["nota"] = NOTAS_ANTENAS[f"{el['type']}/{el['id']}"]
        props["osm"] = f"{el['type']}/{el['id']}"
        features.append({"type": "Feature", "properties": props, "geometry": {
            "type": "Point", "coordinates": [round(x, DECIMALES), round(y, DECIMALES)]}})
    return {"antenas": features}


def organismo_osm(tags):
    """Organismo de respuesta al que corresponde un elemento de OSM (capa "Organismos de respuesta")."""
    if "highway" in tags:
        return None
    nombre = " ".join(tags.get(k, "") for k in ("name", "official_name")).lower()
    if es_prefectura(tags):
        return "Prefectura Naval"
    if tags.get("amenity") == "fire_station":
        return "Bomberos"
    if tags.get("club") == "amateur_radio" or re.search(r"radio ?club", nombre):
        return "Radioaficionados"
    if tags.get("amenity") == "police":
        return "Policía"
    if tags.get("emergency") == "lifeguard" or tags.get("office") == "lifeguard":
        return "Guardavidas"
    if tags.get("amenity") == "ranger_station":
        return "Guardaparques"
    if "cruz roja" in nombre:
        return "Cruz Roja"
    if "defensa civil" in nombre:
        return "Defensa Civil"
    if "centro operativo de monitoreo" in nombre:
        return "Centro Operativo de Monitoreo"
    return None


def armar_consulta(cuerpo, caja):
    s, o, n, e = caja[1], caja[0], caja[3], caja[2]
    c = f"{s},{o},{n},{e}"
    return (f"[out:json][timeout:180];\n"
            f"(\n{cuerpo.format(caja=c)}) -> .todo;\n"
            f"(\n{EXCLUIR_EN_CONSULTA.format(caja=c)}) -> .excluido;\n"
            f"(.todo; - .excluido;);\nout body geom;\n")


def excluido(tags):
    return excluido_osm(tags)


def es_area(tags):
    if tags.get("natural") == "coastline" or "waterway" in tags or "railway" in tags or "highway" in tags:
        return False
    if tags.get("man_made") in ("pier", "breakwater"):
        return tags.get("area") == "yes"
    return True


# Cinco decimales son alrededor de un metro: sobra para esta escala y aligera los archivos.
DECIMALES = 5


def coords_way(el):
    return [[round(p["lon"], DECIMALES), round(p["lat"], DECIMALES)] for p in el.get("geometry") or [] if p]


def unir_anillos(segmentos):
    """Une tramos de ways en anillos cerrados. Devuelve (anillos, tramos_sueltos)."""
    pendientes = [list(s) for s in segmentos if len(s) >= 2]
    anillos = []
    while pendientes:
        actual = pendientes.pop(0)
        cambio = True
        while actual[0] != actual[-1] and cambio:
            cambio = False
            for i, s in enumerate(pendientes):
                if s[0] == actual[-1]:
                    actual += s[1:]
                elif s[-1] == actual[-1]:
                    actual += s[::-1][1:]
                elif s[-1] == actual[0]:
                    actual = s + actual[1:]
                elif s[0] == actual[0]:
                    actual = s[::-1] + actual[1:]
                else:
                    continue
                pendientes.pop(i)
                cambio = True
                break
        if actual[0] == actual[-1] and len(actual) >= 4:
            anillos.append(actual)
        else:
            return anillos, True
    return anillos, False


def geometria(el, tags):
    if el["type"] == "node":
        return {"type": "Point", "coordinates": [round(el["lon"], DECIMALES), round(el["lat"], DECIMALES)]}
    if el["type"] == "way":
        c = coords_way(el)
        if len(c) < 2:
            return None
        if c[0] == c[-1] and len(c) >= 4 and es_area(tags):
            return {"type": "Polygon", "coordinates": [c]}
        return {"type": "LineString", "coordinates": c}
    # Relaciones multipolígono: se arman los anillos exteriores e interiores.
    exteriores = [coords_way(m) for m in el.get("members", []) if m["type"] == "way" and m.get("role") in ("outer", "")]
    interiores = [coords_way(m) for m in el.get("members", []) if m["type"] == "way" and m.get("role") == "inner"]
    ext, roto_e = unir_anillos(exteriores)
    inte, roto_i = unir_anillos(interiores)
    if roto_e or roto_i or not ext:
        return None
    poligonos = [[anillo] for anillo in ext]
    for hueco in inte:
        for p in poligonos:
            if punto_en_geometria(hueco[0][0], hueco[0][1], {"type": "Polygon", "coordinates": [p[0]]}):
                p.append(hueco)
                break
    return {"type": "MultiPolygon", "coordinates": poligonos}


def algun_vertice_dentro(geom, limite, caja):
    if geom["type"] == "Point":
        pts = [geom["coordinates"]]
    elif geom["type"] == "LineString":
        pts = geom["coordinates"]
    elif geom["type"] == "Polygon":
        pts = geom["coordinates"][0]
    else:
        pts = [v for p in geom["coordinates"] for v in p[0]]
    return any(punto_en_geometria(x, y, limite, caja) for x, y in pts)


def procesar(nombre, crudo, limite, caja):
    datos = json.loads(crudo)
    fecha_osm = (datos.get("osm3s") or {}).get("timestamp_osm_base")
    salidas = {}
    descartes = {"excluidos": 0, "fuera_del_partido": 0, "geometria_incompleta": 0}
    if nombre == "torres":
        return procesar_torres(datos, limite, caja), descartes, fecha_osm
    if nombre == "antenas":
        return procesar_antenas(datos, limite, caja), descartes, fecha_osm
    for el in datos.get("elements", []):
        tags = el.get("tags") or {}
        if excluido(tags):
            descartes["excluidos"] += 1
            continue
        geom = geometria(el, tags)
        if geom is None:
            descartes["geometria_incompleta"] += 1
            continue
        if not algun_vertice_dentro(geom, limite, caja):
            descartes["fuera_del_partido"] += 1
            continue
        if en_revision(el, geom):
            descartes["en_revision"] = descartes.get("en_revision", 0) + 1
            continue
        permitidas = TAGS_RESPUESTA if nombre == "respuesta" else TAGS_CONSERVADAS
        props = {k: v for k, v in tags.items() if k in permitidas}
        props["osm"] = f"{el['type']}/{el['id']}"
        if nombre == "respuesta":
            organismo = organismo_osm(tags)
            if organismo is None:
                continue
            props["organismo"] = organismo
            capa = "organismos"
        else:
            capa = nombre if nombre == "hidrografia" else capa_portuaria(tags)
        if capa is None:
            continue
        salidas.setdefault(capa, []).append({"type": "Feature", "properties": props, "geometry": geom})
    return salidas, descartes, fecha_osm


def leer_servidor(ruta):
    # Las respuestas guardadas antes del 27/09/2026 vinieron todas del servidor principal.
    return ruta.read_text(encoding="utf-8").strip() if ruta.exists() else OVERPASS


def consulta_incluye(ruta, texto):
    return ruta.exists() and texto in ruta.read_text(encoding="utf-8")


def respuesta_valida(crudo):
    """Una respuesta sirve si es JSON con elementos y Overpass no avisa de un error (por ejemplo, un
    tiempo agotado, que deja la respuesta incompleta)."""
    try:
        datos = json.loads(crudo)
    except ValueError:
        return False
    return isinstance(datos.get("elements"), list) and "error" not in (datos.get("remark") or "").lower()


def consultar_overpass(nombre, consulta, ruta):
    """Prueba el servidor principal y, si falla o responde algo inválido, el de respaldo. Guarda la
    respuesta en ruta solo si es válida (la anterior no se pisa con una incompleta) y devuelve el
    servidor que respondió, o None."""
    for servidor, reintentos in ((OVERPASS, 1), (OVERPASS_RESPALDO, 3)):
        aviso(f"Consultando Overpass ({servidor}): {nombre}")
        try:
            # GET en vez de POST: desde la nube, Overpass cortó los POST y aceptó los GET
            # espaciados (prueba del 26/09/2026). Entre consultas se espera un minuto.
            url = f"{servidor}?{urllib.parse.urlencode({'data': consulta})}"
            crudo = descargar(url, reintentos=reintentos)
        except ErrorRed as e:
            aviso(str(e))
            continue
        finally:
            time.sleep(60)
        if respuesta_valida(crudo):
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(crudo)
            registrar_descarga(url, ruta, crudo, None)
            return servidor
        aviso(f"{servidor} devolvió una respuesta vacía, incompleta o con error para {nombre}; no se usa.")
    return None


def main():
    offline = "--offline" in sys.argv
    # Se pueden pedir consultas sueltas: python3 scripts/descargar_osm.py respuesta
    pedidas = [a for a in sys.argv[1:] if not a.startswith("--")] or list(CONSULTAS)
    limite, caja = cargar_limite()
    carpeta = CRUDOS / "osm"
    resultado = 0
    for nombre, cuerpo in CONSULTAS.items():
        if nombre not in pedidas:
            continue
        ruta = carpeta / f"{nombre}.json"
        if not offline:
            consulta = armar_consulta(cuerpo, caja)
            (carpeta / f"{nombre}.overpassql").parent.mkdir(parents=True, exist_ok=True)
            (carpeta / f"{nombre}.overpassql").write_text(consulta, encoding="utf-8")
            servidor = consultar_overpass(nombre, consulta, ruta)
            if servidor:
                (carpeta / f"{nombre}.servidor").write_text(servidor, encoding="utf-8")
            else:
                # Si hay una respuesta anterior guardada, se reprocesa (por ejemplo, con un límite nuevo)
                # y se avisa que la base de OSM es la de esa descarga.
                aviso(f"Sin respuesta válida de Overpass: se reprocesa la respuesta anterior de {nombre}, si existe.")
                resultado = 1
        if not ruta.exists():
            aviso(f"No existe {ruta}; la capa {nombre} queda pendiente de fuente.")
            resultado = 1
            continue
        if nombre == "respuesta":
            # Esta consulta no se publica sola: la une con el IGN scripts/armar_respuesta.py.
            print("respuesta: descargada; la capa la arma scripts/armar_respuesta.py.")
            continue
        crudo = ruta.read_bytes()
        salidas, descartes, fecha_osm = procesar(nombre, crudo, limite, caja)
        if nombre == "torres" and not consulta_incluye(carpeta / "torres.overpassql", "utility_pole"):
            # La respuesta guardada es anterior a la consulta de postes de la vía pública: esa capa
            # quedaría incompleta, así que no se escribe y queda pendiente hasta la próxima descarga.
            aviso("postes_via_publica: la respuesta guardada no incluye los postes de la vía pública; queda pendiente.")
            salidas.pop("postes_via_publica", None)
        for capa, features in salidas.items():
            escribir_json(SITIO_DATOS / f"{capa}.geojson", coleccion(features), compacto=True)
            por_tipo = {}
            for ft in features:
                if "tipo" in ft["properties"]:
                    por_tipo[ft["properties"]["tipo"]] = por_tipo.get(ft["properties"]["tipo"], 0) + 1
            anotar_procesamiento(capa, {
                "archivo_crudo": f"osm/{ruta.name}",
                "sha256_crudo": sha256(crudo),
                "elementos": len(features),
                **({"por_tipo": por_tipo} if por_tipo else {}),
                "fecha_datos": fecha_osm,
                "servidor_overpass": leer_servidor(carpeta / f"{nombre}.servidor"),
                "descartes_de_la_consulta": descartes,
            })
            print(f"{capa}: {len(features)} elementos (base OSM del {fecha_osm}); descartes {descartes}")
    return resultado


if __name__ == "__main__":
    sys.exit(main())
