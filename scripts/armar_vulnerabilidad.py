"""Condiciones de vulnerabilidad por radio censal (Censo 2022) en el partido.

Uso:  python3 scripts/armar_vulnerabilidad.py            (descarga y procesa)
      python3 scripts/armar_vulnerabilidad.py --offline  (procesa lo ya guardado en datos/crudos/censo/)

Indicadores: de Grande, P. y Salvia, H. A., "Indicadores del Censo Nacional de Población,
Hogares y Viviendas, 2022", CONICET Digital (http://hdl.handle.net/11336/277944, CC BY 2.5),
elaborados con la base Redatam del INDEC. Geometría: radios censales 2022 de la Provincia de
Buenos Aires (https://catalogo.datos.gba.gob.ar/dataset/radios-censales, CC BY 4.0), que traen
los 229 radios del partido, también los rurales.

Cada radio lleva porcentajes calculados acá a partir de los conteos de la fuente. El color es el
porcentaje de hogares con al menos un indicador de necesidades básicas insatisfechas (NBI). En
los radios con menos de 20 hogares no se calcula: un porcentaje sobre tan pocos casos engaña.
NBI mide carencias materiales; la vulnerabilidad es más que eso (MARCO_CONCEPTUAL.md, sección 2).
"""

import csv
import io
import json
import sys
import zipfile

from comun import CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, coleccion, descargar, escribir_json, sha256

BASE = "https://ri.conicet.gov.ar/bitstream/handle/11336/277944/"
FUENTES = {
    "hogares": (BASE + "Indicadores_de_hogares__2022.zip?sequence=8&isAllowed=y",
                CRUDOS / "censo" / "Indicadores_de_hogares__2022.zip", "Indicadores de hogares. Radios, 2022.csv"),
    "personas": (BASE + "Indicadores_de_personas__2022.zip?sequence=5&isAllowed=y",
                 CRUDOS / "censo" / "Indicadores_de_personas__2022.zip", "Indicadores de personas. Radios, 2022.csv"),
    "radios": ("https://catalogo.datos.gba.gob.ar/dataset/33b080d2-e369-4076-acd4-511db0e9bffb/resource/"
               "151d80d2-87c1-4981-9bea-9aab38a82ec9/download/radios-censales-2022-geojson.zip",
               CRUDOS / "censo" / "radios-censales-2022-geojson.zip", "radios-censales.geojson"),
}
PARTIDO = "06581"
MINIMO_HOGARES = 20
DECIMALES = 5
CATEGORIAS = ["Menos de 2,5 %", "2,5 a 5 %", "5 a 10 %", "10 % o más", "Menos de 20 hogares"]


def categoria(pct, hogares):
    if hogares < MINIMO_HOGARES:
        return CATEGORIAS[4]
    if pct < 2.5:
        return CATEGORIAS[0]
    if pct < 5:
        return CATEGORIAS[1]
    if pct < 10:
        return CATEGORIAS[2]
    return CATEGORIAS[3]


def leer_csv(ruta, nombre):
    with zipfile.ZipFile(ruta) as z:
        texto = z.read(nombre).decode("utf-8-sig")
    filas = csv.reader(io.StringIO(texto))
    cabecera = next(filas)
    # La primera columna es el código de radio; algunas columnas se repiten al final: vale la primera.
    return {f[0]: {c: f[i] for i, c in reversed(list(enumerate(cabecera)))} for f in filas if f and f[0].startswith(PARTIDO)}


def numero(v):
    return float(v) if v not in (None, "") else 0.0


def pct(parte, total):
    return round(100 * parte / total, 1) if total else None


def redondear(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], DECIMALES), round(c[1], DECIMALES)]
    return [redondear(s) for s in c]


def main():
    if "--offline" not in sys.argv:
        for url, ruta, _ in FUENTES.values():
            try:
                descargar(url, ruta, timeout=900)
            except ErrorRed as e:
                aviso(f"{e}\nSe usa {ruta.name} guardado en datos/crudos/censo/, si existe.")
    faltan = [r.name for _, r, _ in FUENTES.values() if not r.exists()]
    if faltan:
        aviso(f"Faltan {faltan}: la capa de vulnerabilidad queda pendiente de fuente.")
        return 1
    hogares = leer_csv(FUENTES["hogares"][1], FUENTES["hogares"][2])
    personas = leer_csv(FUENTES["personas"][1], FUENTES["personas"][2])
    with zipfile.ZipFile(FUENTES["radios"][1]) as z:
        radios = json.loads(z.read(FUENTES["radios"][2]))

    features, por_tipo, sin_datos = [], {}, []
    for f in radios["features"]:
        p = f["properties"]
        codigo = p.get("LINK")
        if p.get("PROV") != "06" or p.get("DEPTO") != "581":
            continue
        h, pe = hogares.get(codigo), personas.get(codigo)
        if not h or not pe:
            sin_datos.append(codigo)
            continue
        th = numero(h["Total de hogares"])
        nbi = numero(h["Hogares con al menos un indicador NBI"])
        pob_hog = numero(pe["Población total (en hogares familiares)."])
        props = {
            "radio": codigo,
            "tipo": {"U": "Urbano", "M": "Mixto", "R": "Rural"}.get(p.get("TIPO"), p.get("TIPO")),
            "poblacion": int(numero(h["Población total"])),
            "hogares": int(th),
            "pct_nbi": pct(nbi, th),
            "pct_hacinamiento": pct(numero(h["Hogares con hacinamiento (más de 2 personas por cuarto)"]), th),
            "pct_sin_agua_red": pct(numero(h["Hogares sin agua para beber y cocinar proveniente de red pública"]), th),
            "pct_sin_cloaca": pct(numero(h["Hogares sin cloaca"]), th),
            "pct_garrafa_lena": pct(numero(h["Hogares con garrafa o leña como combustible usado principalmente para cocinar"]), th),
            "pct_solo_salud_publica": pct(numero(pe["Solo salud pública"]), pob_hog),
            "pct_0a17": pct(numero(pe["Población de 0 a 17 años."]), pob_hog),
            "pct_70ymas": pct(numero(pe["Población de 70 años y más."]), pob_hog),
            "nbi": categoria(pct(nbi, th) or 0, th),
        }
        if th < MINIMO_HOGARES:
            props = {k: v for k, v in props.items() if not k.startswith("pct_")}
        por_tipo[props["nbi"]] = por_tipo.get(props["nbi"], 0) + 1
        features.append({"type": "Feature", "properties": props,
                          "geometry": {"type": f["geometry"]["type"], "coordinates": redondear(f["geometry"]["coordinates"])}})
    if sin_datos:
        aviso(f"Radios sin indicadores (no se publican): {sin_datos}")
    features.sort(key=lambda x: x["properties"]["radio"])

    escribir_json(SITIO_DATOS / "vulnerabilidad_radios.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("vulnerabilidad_radios", {
        "archivos_crudos": {k: f"censo/{r.name}" for k, (_, r, _) in FUENTES.items()},
        "sha256_crudo": sha256(b"".join(r.read_bytes() for _, r, _ in FUENTES.values())),
        "elementos": len(features),
        "por_tipo": por_tipo,
        "hogares": sum(x["properties"]["hogares"] for x in features),
        "poblacion": sum(x["properties"]["poblacion"] for x in features),
        "fecha_datos": "Censo Nacional de Población, Hogares y Viviendas, 18/05/2022 (INDEC).",
    })
    print(f"Vulnerabilidad: {len(features)} radios; por % de hogares con NBI {por_tipo}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
