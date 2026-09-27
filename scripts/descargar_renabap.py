"""Barrios populares del Registro Nacional de Barrios Populares (RENABAP) dentro del partido.

Uso:  python3 scripts/descargar_renabap.py            (descarga y procesa)
      python3 scripts/descargar_renabap.py --offline  (procesa lo ya guardado en datos/crudos/renabap/)

Conjunto "Registro Nacional de Barrios Populares" de datos.gob.ar (Subsecretaría de Integración
Socio Urbana), recurso GeoJSON "Barrios Populares de Argentina", corte del 05/12/2023 según el
nombre del archivo. Entra cada barrio con al menos un vértice dentro del límite del partido; se
controla además que el campo "departamento" diga Necochea. Son datos de barrios, no de personas.
"""

import sys

from comun import (CRUDOS, SITIO_DATOS, ErrorRed, anotar_procesamiento, aviso, cargar_limite, coleccion,
                   descargar, escribir_json, leer_json, punto_en_geometria, sha256, vertices)

URL = "https://archivo.infraestructura.gob.ar/dataset/ssisu/20231205_info_publica.geojson"
CRUDO = CRUDOS / "renabap" / "20231205_info_publica.geojson"
DECIMALES = 5

# Campos que se publican, con el nombre que usa el sitio.
CAMPOS = {
    "id_renabap": "id_renabap",
    "nombre_barrio": "nombre",
    "localidad": "localidad",
    "clasificacion_barrio": "clasificacion",
    "cantidad_familias_aproximada": "familias",
    "cantidad_viviendas_aproximadas": "viviendas",
    "decada_de_creacion": "decada",
    "energia_electrica": "energia",
    "efluentes_cloacales": "cloacas",
    "agua_corriente": "agua",
    "cocina": "cocina",
    "calefaccion": "calefaccion",
    "titulo_propiedad": "titulo",
    "superficie_m2": "superficie_m2",
}


def redondear(c):
    if isinstance(c[0], (int, float)):
        return [round(c[0], DECIMALES), round(c[1], DECIMALES)]
    return [redondear(s) for s in c]


def main():
    if "--offline" not in sys.argv:
        try:
            descargar(URL, CRUDO, timeout=300)
        except ErrorRed as e:
            aviso(f"{e}\nSe usa el archivo guardado en datos/crudos/renabap/, si existe.")
    if not CRUDO.exists():
        aviso(f"Falta {CRUDO.name}: la capa de barrios populares queda pendiente de fuente.")
        return 1
    contenido = CRUDO.read_bytes()
    datos = leer_json(CRUDO)
    limite, caja = cargar_limite()

    features, fuera_de_departamento = [], []
    for f in datos["features"]:
        g = f.get("geometry")
        if not g or not any(punto_en_geometria(x, y, limite, caja) for x, y, *_ in vertices(g)):
            continue
        p = f["properties"]
        if (p.get("departamento") or "").strip().lower() != "necochea":
            fuera_de_departamento.append(p.get("id_renabap"))
            continue
        props = {nuevo: p.get(viejo) for viejo, nuevo in CAMPOS.items() if p.get(viejo) not in (None, "")}
        features.append({"type": "Feature", "properties": props,
                         "geometry": {"type": g["type"], "coordinates": redondear(g["coordinates"])}})
    features.sort(key=lambda f: -(f["properties"].get("familias") or 0))
    if fuera_de_departamento:
        aviso(f"Barrios dentro del límite pero con otro departamento en la fuente (no se publican): {fuera_de_departamento}")

    escribir_json(SITIO_DATOS / "barrios_populares.geojson", coleccion(features), compacto=True)
    anotar_procesamiento("barrios_populares", {
        "archivo_crudo": f"renabap/{CRUDO.name}",
        "sha256_crudo": sha256(contenido),
        "elementos": len(features),
        "barrios_en_el_pais": len(datos["features"]),
        "familias_aproximadas": sum(f["properties"].get("familias") or 0 for f in features),
        "fecha_datos": "Corte del 05/12/2023, según el nombre del archivo publicado.",
    })
    print(f"Barrios populares: {len(features)} en el partido (de {len(datos['features'])} en el país).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
