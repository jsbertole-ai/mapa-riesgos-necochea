"""Arma docs/datos/portada.json, los datos de la portada animada "Observatorio Necochea" (decisión de
Sebastián, 16/10/2026).

Uso:  python3 scripts/armar_portada.py

No descarga nada: toma capas ya verificadas del sitio y las simplifica para dibujarlas en la portada.
  - límite del partido e hidrografía (IGN), media tensión (Secretaría de Energía), gasoductos (ENARGAS);
  - localidades (IGN), focos de calor VIIRS (NASA FIRMS) y eventos del inventario local, con su año.
La costa se deduce del propio límite del IGN: es el tramo del borde que mira al mar, desde la esquina
sudoeste hacia el este. Como el límite está simplificado, la costa (y el mar que se dibuja debajo) es
aproximada; sirve para la portada, no para medir.
"""

import json
import math
import sys

from comun import SITIO_DATOS, aviso, escribir_json, leer_json

DECIMALES = 4


def simplificar(puntos, tolerancia):
    """Douglas-Peucker sin recursión."""
    if len(puntos) < 3:
        return puntos
    guardar = [False] * len(puntos)
    guardar[0] = guardar[-1] = True
    pila = [(0, len(puntos) - 1)]
    while pila:
        i0, i1 = pila.pop()
        (x1, y1), (x2, y2) = puntos[i0], puntos[i1]
        largo = math.dist(puntos[i0], puntos[i1])
        mejor, dmax = None, tolerancia
        for i in range(i0 + 1, i1):
            x, y = puntos[i]
            d = (abs((y2 - y1) * x - (x2 - x1) * y + x2 * y1 - y2 * x1) / largo) if largo else math.dist(puntos[i], puntos[i0])
            if d > dmax:
                mejor, dmax = i, d
        if mejor is not None:
            guardar[mejor] = True
            pila += [(i0, mejor), (mejor, i1)]
    return [p for p, g in zip(puntos, guardar) if g]


def redondear(p):
    return [round(p[0], DECIMALES), round(p[1], DECIMALES)]


def lineas(coordenadas):
    """Todas las líneas de una geometría lineal, la anide como la anide."""
    if coordenadas and isinstance(coordenadas[0][0], (int, float)):
        return [coordenadas]
    return [l for c in coordenadas for l in lineas(c)]


def largo(linea):
    return sum(math.dist(a, b) for a, b in zip(linea, linea[1:]))


def capa(nombre):
    datos = leer_json(SITIO_DATOS / nombre)
    if not datos:
        aviso(f"Falta docs/datos/{nombre}: la portada se arma sin esa capa.")
        return []
    return datos["features"]


def main():
    limite_fc = capa("limite.geojson")
    if not limite_fc:
        aviso("Sin límite no hay portada.")
        return 1
    geometria = limite_fc[0]["geometry"]
    anillos = [pol[0] for pol in (geometria["coordinates"] if geometria["type"] == "MultiPolygon" else [geometria["coordinates"]])]
    limite = [[redondear(p) for p in simplificar(a, 0.0015)] for a in anillos]

    # Costa: vértices del borde desde los que la vertical hacia el sur no vuelve a cruzar el partido.
    anillo = max(anillos, key=len)
    aristas = list(zip(anillo, anillo[1:]))

    def mira_al_sur(v):
        x, y = v
        for (x1, y1), (x2, y2) in aristas:
            if (x1 <= x < x2) or (x2 <= x < x1):
                if y1 + (x - x1) * (y2 - y1) / (x2 - x1) < y - 1e-7:
                    return False
        return True

    envolvente = sorted({tuple(v) for v in anillo if mira_al_sur(v)})
    sudoeste = min(envolvente, key=lambda p: p[1])
    costa = [redondear(p) for p in simplificar([list(p) for p in envolvente if p[0] >= sudoeste[0]], 0.0008)]

    rios = []
    for f in capa("hidrografia_ign.geojson"):
        principal = (f["properties"].get("fna") or "").startswith(("Río Quequén", "Arroyo Quequén"))
        for l in lineas(f["geometry"]["coordinates"]):
            s = [redondear(p) for p in simplificar(l, 0.0015)]
            if len(s) > 1:
                rios.append({"p": principal, "c": s})

    electricidad = []
    for f in capa("media_tension.geojson"):
        for l in lineas(f["geometry"]["coordinates"]):
            if largo(l) >= 0.01:
                s = [redondear(p) for p in simplificar(l, 0.002)]
                if len(s) > 1:
                    electricidad.append(s)

    gas = []
    for f in capa("gasoductos.geojson"):
        for l in lineas(f["geometry"]["coordinates"]):
            s = [redondear(p) for p in simplificar(l, 0.0015)]
            if len(s) > 1:
                gas.append(s)

    localidades = []
    for f in capa("localidades.geojson"):
        g = f["geometry"]
        c = g["coordinates"][0] if g["type"] == "MultiPoint" else g["coordinates"]
        localidades.append({"n": f["properties"]["fna"], "c": redondear(c)})

    eventos = []
    for f in capa("inventario_local.geojson"):
        if f["geometry"]["type"] != "Point":
            continue
        for r in f["properties"].get("registros", []):
            if r.get("fecha"):
                eventos.append({"a": int(r["fecha"][:4]), "c": redondear(f["geometry"]["coordinates"])})
    eventos.sort(key=lambda e: e["a"])

    focos = [{"a": int(f["properties"]["acq_date"][:4]), "c": redondear(f["geometry"]["coordinates"])}
             for f in capa("incendios_viirs.geojson")]

    escribir_json(SITIO_DATOS / "portada.json", {
        "nota": "Datos simplificados para la portada; las capas completas y sus fuentes están en el mapa (mapa.html).",
        "limite": limite, "costa": costa, "rios": rios, "electricidad": electricidad, "gas": gas,
        "localidades": localidades, "eventos": eventos, "focos": focos,
    }, compacto=True)
    print(f"Portada: límite {sum(map(len, limite))} vértices, costa {len(costa)}, ríos {len(rios)}, "
          f"media tensión {len(electricidad)}, gasoductos {len(gas)}, eventos {len(eventos)}, focos {len(focos)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
