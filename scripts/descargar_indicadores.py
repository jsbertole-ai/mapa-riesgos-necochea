"""Indicadores de riesgo del partido de Necochea publicados por el IGN (espacio ign_riesgo).

Uso:  python3 scripts/descargar_indicadores.py            (consulta el WFS del IGN)
      python3 scripts/descargar_indicadores.py --offline  (no hace nada: deja la ficha anterior)

Escribe docs/datos/ficha_partido.json, que la página de Metodología muestra como
"Ficha del partido". No son capas del mapa: son valores por partido o por región.

- DesInventar, amenazas hidrometeorológicas 1970-2015 (metadato del IGN:
  https://www.ign.gob.ar/capas-sig/metadata/desinventar_hidrometeorologico_riesgo.pdf).
- Índice de vulnerabilidad social frente a desastres (IVSD) 2024 por departamento
  (https://www.ign.gob.ar/capas-sig/metadata/ivsd_2024_depto.pdf). Como la capa no
  publica la escala del índice, se agrega la distribución nacional y provincial
  calculada con la misma capa, para poder leer el valor de Necochea.
- Niveles de exposición del SINAGIR para la región Centro (escala regional).

La capa físico-química de DesInventar no se usa: no tiene metadato publicado y sus
códigos y su período no están documentados.
"""

import json
import statistics
import sys
import urllib.parse

from comun import SITIO_DATOS, ErrorRed, ahora, aviso, descargar, escribir_json

WFS = "https://wms.ign.gob.ar/geoserver/ign_riesgo/ows"
CODIGO = "06581"

# Alias de los campos según el metadato del IGN.
DESINVENTAR = {
    "des_inun": "Inundaciones", "des_torm": "Tormentas", "des_viefue": "Vientos fuertes",
    "des_tormni": "Tormentas de nieve", "des_niebla": "Niebla", "des_graniz": "Granizo", "des_sequia": "Sequía",
    "des_escarc": "Escarchas", "des_olasca": "Olas de calor", "des_lluvia": "Lluvias",
    "des_tormel": "Tormentas eléctricas", "des_tornad": "Tornados",
}


def pedir(capa, **extra):
    parametros = {"service": "WFS", "version": "2.0.0", "request": "GetFeature", "typeNames": "ign_riesgo:" + capa,
                  "outputFormat": "application/json"}
    parametros.update(extra)
    return json.loads(descargar(WFS + "?" + urllib.parse.urlencode(parametros), timeout=180))["features"]


def main():
    if "--offline" in sys.argv:
        print("Modo sin conexión: la ficha del partido queda como está (docs/datos/ficha_partido.json).")
        return 0
    try:
        des = pedir("desinventar_hidrometeorologico_riesgo", CQL_FILTER=f"in1='{CODIGO}'", propertyName=",".join(
            ["fna", "in1", "registros", "categoria", "fuente"] + list(DESINVENTAR)))
        ivsd = pedir("ivsd_2024_depto", propertyName="fna,in1,provincia,ivsd")
        sinagir = {tipo: pedir(f"sinagir_amenazas_{tipo}_riesgo", CQL_FILTER="region='Centro'",
                               propertyName="region,categoria,sumatoria,fuente")
                   for tipo in ("hidrometeorologicas", "fisico_quimicas")}
    except ErrorRed as e:
        aviso(f"{e}\nSin conexión con el IGN: la ficha del partido no se actualiza.")
        return 1

    if len(des) != 1:
        aviso(f"DesInventar: se esperaba un registro para {CODIGO} y hubo {len(des)}.")
        return 1
    p = des[0]["properties"]
    eventos = {DESINVENTAR[k]: p[k] for k in DESINVENTAR if p.get(k)}
    if sum(eventos.values()) != p.get("registros"):
        aviso(f"DesInventar: la suma de eventos ({sum(eventos.values())}) no coincide con 'registros' ({p.get('registros')}).")
        return 1

    valores = [f["properties"]["ivsd"] for f in ivsd if isinstance(f["properties"].get("ivsd"), (int, float))]
    filas_pba = sorted(((f["properties"]["ivsd"], f["properties"].get("fna")) for f in ivsd
                        if f["properties"].get("provincia") == "Buenos Aires" and isinstance(f["properties"].get("ivsd"), (int, float))),
                       key=lambda x: x[0])
    provincia = [x[0] for x in filas_pba]
    necochea = [f["properties"]["ivsd"] for f in ivsd if f["properties"].get("in1") == CODIGO]
    if len(necochea) != 1:
        aviso(f"IVSD: se esperaba un valor para {CODIGO} y hubo {len(necochea)}.")
        return 1
    v = necochea[0]

    def resumen(lista):
        return {"departamentos": len(lista), "minimo": min(lista), "maximo": max(lista),
                "mediana": statistics.median(lista), "con_valor_menor": sum(x < v for x in lista)}

    ficha = {
        "generado": ahora(),
        "partido": p.get("fna"),
        "desinventar": {
            "capa": "ign_riesgo:desinventar_hidrometeorologico_riesgo",
            "periodo": "1970-2015",
            "registros": p.get("registros"),
            "categoria": p.get("categoria"),
            "eventos": eventos,
            "fuente": "Base DesInventar Sendai (UNDRR), georreferenciada por el IGN.",
            "metadato": "https://www.ign.gob.ar/capas-sig/metadata/desinventar_hidrometeorologico_riesgo.pdf",
            "advertencia": "La misma presenta subregistros, nos brinda un contexto aproximado.",
        },
        "ivsd": {
            "capa": "ign_riesgo:ivsd_2024_depto",
            "valor": v,
            "nacional": resumen(valores),
            "provincia": dict(resumen(provincia),
                              valores_mas_bajos=[{"partido": n, "ivsd": x} for x, n in filas_pba[:2]],
                              valores_mas_altos=[{"partido": n, "ivsd": x} for x, n in filas_pba[::-1][:2]]),
            "fuente": "Proyecto ARG19003: Plan Nacional de Adaptación al Cambio Climático (MAyDS) e IGN, con indicadores del Censo 2022.",
            "metadato": "https://www.ign.gob.ar/capas-sig/metadata/ivsd_2024_depto.pdf",
            "advertencia": "La capa no publica la escala del índice ni su metodología (el metadato remite a un informe de consultoría).",
        },
        "sinagir": {tipo: (f[0]["properties"] if f else None) for tipo, f in sinagir.items()},
        "licencia": "Libre uso con cita del Instituto Geográfico Nacional, según los metadatos de cada capa; términos generales en https://www.ign.gob.ar/descargas/tyc1.html",
    }
    escribir_json(SITIO_DATOS / "ficha_partido.json", ficha)
    print(f"Ficha del partido: DesInventar {p.get('registros')} registros; IVSD {v} "
          f"(menor en {ficha['ivsd']['nacional']['con_valor_menor']} de {len(valores)} departamentos).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
