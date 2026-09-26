"""Prueba la conexión con los dominios de las fuentes (DATOS.md, sección 5).

Uso:  python3 scripts/probar_conexion.py

Guarda el resultado en datos/prueba_conexion.json para dejar constancia de
qué se pudo alcanzar y cuándo.
"""

import sys

from comun import RAIZ, ErrorRed, ahora, descargar, escribir_json

DOMINIOS = [
    "apis.datos.gob.ar",
    "infra.datos.gob.ar",
    "datosgobar.github.io",
    "www.ign.gob.ar",
    "firms.modaps.eosdis.nasa.gov",
    "overpass-api.de",
    "ideba.gba.gob.ar",
    "riesgohidrico.ada.gba.gov.ar",
    "ada.gba.gov.ar",
]


def main():
    resultados = []
    for dominio in DOMINIOS:
        url = f"https://{dominio}/"
        try:
            descargar(url, timeout=30, reintentos=0)
            estado = "accesible"
        except ErrorRed as e:
            texto = str(e)
            if " respondió " in texto:
                # El servidor contestó (aunque sea con error en la raíz): hay conexión.
                estado = "accesible (" + texto.split(" respondió ")[1] + " en la raíz)"
            elif "Tunnel connection failed" in texto:
                estado = "bloqueado por la política de red del entorno"
            else:
                estado = f"conexión cortada o sin respuesta: {texto.split(': ', 1)[-1]}"
        print(f"{dominio:32} {estado}")
        resultados.append({"dominio": dominio, "estado": estado})
    escribir_json(RAIZ / "datos" / "prueba_conexion.json", {"fecha": ahora(), "resultados": resultados})
    return 0 if all(r["estado"].startswith("accesible") for r in resultados) else 1


if __name__ == "__main__":
    sys.exit(main())
