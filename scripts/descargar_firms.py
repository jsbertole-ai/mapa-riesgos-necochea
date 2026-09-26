"""Focos de calor de NASA FIRMS (MODIS C6.1 y VIIRS 375 m S-NPP) en el partido de Necochea.

Uso:  python3 scripts/descargar_firms.py            (descarga y procesa)
      python3 scripts/descargar_firms.py --offline  (procesa lo ya guardado en datos/crudos/firms/)

Fuente: resúmenes anuales por país de FIRMS (archivo estándar, no tiempo real):
  https://firms.modaps.eosdis.nasa.gov/data/country/{sensor}/{año}/{sensor}_{año}_Argentina.csv
Cada CSV nacional se descarga, se anota su huella SHA-256 en datos/registro_descargas.json
y se guardan solo las filas dentro de la caja envolvente del partido
(datos/crudos/firms/{sensor}_{año}_Argentina_caja.csv). Si se bajan los CSV a mano,
dejarlos en datos/crudos/firms/ con su nombre original y usar --offline.

Después se recorta por el polígono del partido y se escribe un GeoJSON por sensor.
No se filtra por confianza ni por tipo: esos campos se muestran en el mapa.
"""

import csv
import io
import sys

from comun import (CRUDOS, RAIZ, SITIO_DATOS, ErrorRed, ahora, anotar_procesamiento, aviso, cargar_limite,
                   coleccion, descargar, escribir_json, leer_json, punto_en_geometria, REGISTRO, sha256)

URL = "https://firms.modaps.eosdis.nasa.gov/data/country/{s}/{a}/{s}_{a}_Argentina.csv"
SENSORES = {
    "modis": {"capa": "incendios_modis", "desde": 2000},
    "viirs-snpp": {"capa": "incendios_viirs", "desde": 2012},
}
CAMPOS = ["acq_date", "acq_time", "satellite", "confidence", "frp", "daynight", "type", "version"]
CARPETA = CRUDOS / "firms"


def dentro_de_caja(fila, caja):
    x, y = float(fila["longitude"]), float(fila["latitude"])
    return caja[0] <= x <= caja[2] and caja[1] <= y <= caja[3]


def guardar_subconjunto(texto, destino, caja):
    lector = csv.DictReader(io.StringIO(texto))
    filas = [f for f in lector if dentro_de_caja(f, caja)]
    destino.parent.mkdir(parents=True, exist_ok=True)
    with destino.open("w", newline="", encoding="utf-8") as sal:
        escritor = csv.DictWriter(sal, fieldnames=lector.fieldnames)
        escritor.writeheader()
        escritor.writerows(filas)
    return len(filas)


def descargar_anio(sensor, anio, caja):
    url = URL.format(s=sensor, a=anio)
    destino = CARPETA / f"{sensor}_{anio}_Argentina_caja.csv"
    contenido = descargar(url)
    n = guardar_subconjunto(contenido.decode("utf-8"), destino, caja)
    registro = leer_json(REGISTRO, {})
    registro[str(destino.relative_to(RAIZ))] = {
        "url": url,
        "descargado": ahora(),
        "bytes_archivo_nacional": len(contenido),
        "sha256_archivo_nacional": sha256(contenido),
        "nota": "Se guardan solo las filas dentro de la caja envolvente del partido.",
    }
    escribir_json(REGISTRO, registro)
    aviso(f"  {sensor} {anio}: {len(contenido):,} bytes, {n} filas en la caja")


def descargar_todo(caja):
    import datetime as dt
    for sensor, conf in SENSORES.items():
        for anio in range(conf["desde"], dt.date.today().year + 1):
            if (CARPETA / f"{sensor}_{anio}_Argentina_caja.csv").exists():
                continue
            try:
                descargar_anio(sensor, anio, caja)
            except ErrorRed as e:
                # Los años sin resumen publicado responden 404: se anotan y se sigue.
                aviso(f"  {sensor} {anio}: no disponible ({e})")


def leer_filas(sensor, caja):
    """Filas de los subconjuntos y de los CSV nacionales bajados a mano, sin duplicar años."""
    anios = set()
    for ruta in sorted(CARPETA.glob(f"{sensor}_*_Argentina_caja.csv")):
        anios.add(ruta.name.split("_")[1])
        with ruta.open(encoding="utf-8") as f:
            yield from csv.DictReader(f)
    for ruta in sorted(CARPETA.glob(f"{sensor}_*_Argentina.csv")):
        if ruta.name.split("_")[1] in anios:
            continue
        with ruta.open(encoding="utf-8") as f:
            yield from (fila for fila in csv.DictReader(f) if dentro_de_caja(fila, caja))


def main():
    limite, caja = cargar_limite()
    if "--offline" not in sys.argv:
        aviso("Descargando resúmenes anuales de FIRMS para Argentina…")
        descargar_todo(caja)
    resultado = 0
    for sensor, conf in SENSORES.items():
        features = []
        for fila in leer_filas(sensor, caja):
            x, y = float(fila["longitude"]), float(fila["latitude"])
            if not punto_en_geometria(x, y, limite, caja):
                continue
            props = {k: fila.get(k) for k in CAMPOS}
            props["frp"] = float(props["frp"]) if props["frp"] else None
            props["type"] = int(props["type"]) if props["type"] not in (None, "") else None
            features.append({"type": "Feature", "properties": props,
                             "geometry": {"type": "Point", "coordinates": [x, y]}})
        if not features:
            aviso(f"{sensor}: no hay datos procesables; la capa queda pendiente de fuente.")
            resultado = 1
            continue
        features.sort(key=lambda f: (f["properties"]["acq_date"], f["properties"]["acq_time"]))
        fechas = [f["properties"]["acq_date"] for f in features]
        por_anio, por_tipo = {}, {}
        for f in features:
            a = f["properties"]["acq_date"][:4]
            por_anio[a] = por_anio.get(a, 0) + 1
            t = str(f["properties"]["type"])
            por_tipo[t] = por_tipo.get(t, 0) + 1
        anios_con_archivo = sorted({r.name.split("_")[1] for r in CARPETA.glob(f"{sensor}_*_Argentina*.csv")})
        escribir_json(SITIO_DATOS / f"{conf['capa']}.geojson", coleccion(features), compacto=True)
        anotar_procesamiento(conf["capa"], {
            "archivo_crudo": f"firms/{sensor}_*_Argentina_caja.csv",
            "elementos": len(features),
            "fecha_datos": f"{fechas[0]} a {fechas[-1]}",
            "anios_con_archivo": anios_con_archivo,
            "focos_por_anio": por_anio,
            "focos_por_tipo": por_tipo,
            "versiones": sorted({f["properties"]["version"] for f in features}),
        })
        print(f"{conf['capa']}: {len(features)} focos, {fechas[0]} a {fechas[-1]}; por tipo {por_tipo}")
    return resultado


if __name__ == "__main__":
    sys.exit(main())
