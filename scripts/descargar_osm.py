"""Hidrografía detallada e infraestructura portuaria e industrial desde OpenStreetMap.

Uso:  python3 scripts/descargar_osm.py            (consulta Overpass y procesa)
      python3 scripts/descargar_osm.py --offline  (procesa lo ya guardado en datos/crudos/osm/)
      python3 scripts/descargar_osm.py respuesta  (solo una consulta: hidrografia, portuaria o respuesta)

Requiere el límite del partido (scripts/descargar_limite.py). La consulta usa
la caja envolvente del límite y después recorta por el polígono: queda todo
elemento con al menos un vértice dentro del partido.

Exclusiones (DATOS.md, sección 4): se descartan en la consulta y otra vez al
procesar los elementos con man_made=surveillance, amenity=police o claves de
vigilancia. Única excepción: la Prefectura Naval Argentina, que se publica por su
función de salvamento (ver comun.excluido_osm). Además solo se conservan las etiquetas de la lista TAGS_CONSERVADAS,
para no arrastrar teléfonos, correos ni otros datos de contacto.

Licencia: ODbL 1.0. Los archivos resultantes son una base derivada de
OpenStreetMap y se publican bajo la misma licencia.
"""

import json
import sys
import time
import urllib.parse

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, es_prefectura, excluido_osm, aviso, cargar_limite, coleccion, descargar, escribir_json,
                   punto_en_geometria, sha256)

OVERPASS = "https://overpass-api.de/api/interpreter"

# La policía se excluye salvo la Prefectura Naval (salvamento; decisión de Sebastián, 27/09/2026).
POLICIA_EN_CONSULTA = """
(nwr["amenity"="police"]({caja});) -> .policia;
(nwr.policia["name"~"prefectura",i]; nwr.policia["official_name"~"prefectura",i];
 nwr.policia["operator"~"prefectura",i];) -> .prefectura;
(.policia; - .prefectura;) -> .policia_excluida;
"""

EXCLUIR_EN_CONSULTA = """
  nwr["man_made"="surveillance"]({caja});
  .policia_excluida;
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
    "respuesta": """
  nwr["amenity"="fire_station"]({caja});
  nwr["name"~"Defensa Civil",i]({caja});
  nwr["name"~"Centro Operativo de Monitoreo",i]({caja});
  nwr["name"~"prefectura",i][!"highway"]({caja});
  nwr["operator"~"prefectura",i][!"highway"]({caja});
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
TAGS_RESPUESTA = {"name", "official_name", "description", "amenity", "office", "government", "emergency"}

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


def armar_consulta(cuerpo, caja):
    s, o, n, e = caja[1], caja[0], caja[3], caja[2]
    c = f"{s},{o},{n},{e}"
    return (f"[out:json][timeout:180];\n"
            f"(\n{cuerpo.format(caja=c)}) -> .todo;\n"
            f"{POLICIA_EN_CONSULTA.format(caja=c)}"
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
            nombre_el = tags.get("name", "").lower()
            if tags.get("amenity") == "fire_station":
                capa = "bomberos"
            elif "defensa civil" in nombre_el:
                capa = "defensa_civil"
            elif "monitoreo" in nombre_el:
                capa = "monitoreo"
            elif es_prefectura(tags) and "highway" not in tags:
                # No se publica la etiqueta de policía: se muestra como lo que es, Prefectura Naval.
                props.pop("amenity", None)
                capa = "prefectura"
            else:
                continue
        else:
            capa = nombre if nombre == "hidrografia" else capa_portuaria(tags)
        if capa is None:
            continue
        salidas.setdefault(capa, []).append({"type": "Feature", "properties": props, "geometry": geom})
    return salidas, descartes, fecha_osm


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
            try:
                aviso(f"Consultando Overpass: {nombre}")
                # GET en vez de POST: desde la nube, Overpass cortó los POST y aceptó los GET
                # espaciados (prueba del 26/09/2026). Entre consultas se espera un minuto.
                descargar(f"{OVERPASS}?{urllib.parse.urlencode({'data': consulta})}", ruta)
                time.sleep(60)
            except ErrorRed as e:
                # Si hay una respuesta anterior guardada, se reprocesa (por ejemplo, con un límite nuevo)
                # y se avisa que la base de OSM es la de esa descarga.
                aviso(f"{e}\nSin conexión con Overpass: se reprocesa la respuesta anterior de {nombre}, si existe.")
                resultado = 1
        if not ruta.exists():
            aviso(f"No existe {ruta}; la capa {nombre} queda pendiente de fuente.")
            resultado = 1
            continue
        crudo = ruta.read_bytes()
        salidas, descartes, fecha_osm = procesar(nombre, crudo, limite, caja)
        for capa, features in salidas.items():
            escribir_json(SITIO_DATOS / f"{capa}.geojson", coleccion(features), compacto=True)
            anotar_procesamiento(capa, {
                "archivo_crudo": f"osm/{ruta.name}",
                "sha256_crudo": sha256(crudo),
                "elementos": len(features),
                "fecha_datos": fecha_osm,
                "descartes_de_la_consulta": descartes,
            })
            print(f"{capa}: {len(features)} elementos (base OSM del {fecha_osm}); descartes {descartes}")
    return resultado


if __name__ == "__main__":
    sys.exit(main())
