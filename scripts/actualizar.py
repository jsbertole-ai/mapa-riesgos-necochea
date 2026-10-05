"""Corre toda la actualización de datos en orden.

Uso:  python3 scripts/actualizar.py            (descarga todo y verifica)
      python3 scripts/actualizar.py --offline  (reprocesa lo que ya está en datos/crudos/)

Orden: límite (hace falta para recortar lo demás), FIRMS, OpenStreetMap, IGN, cuenca del Quequén,
organismos de respuesta, servicios de playa, media tensión, barrios populares (RENABAP), indicadores, inventario local (usa la última exportación de Kobo que haya en
datos/crudos/inventario/) y verificación. Un paso que falla no frena los siguientes: la capa afectada
queda "pendiente de fuente" y verificar.py lo anota.
"""

import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PASOS = ["descargar_limite.py", "descargar_firms.py", "descargar_osm.py", "descargar_ign.py", "descargar_cuenca.py", "armar_respuesta.py", "armar_playa.py", "descargar_municipio.py", "armar_conectividad.py", "armar_poblacion.py", "armar_vulnerabilidad.py", "descargar_energia.py", "descargar_gasoductos.py", "descargar_renabap.py", "descargar_envases.py", "descargar_sustancias.py", "descargar_indicadores.py",
         "procesar_inventario.py", "verificar.py"]


def main():
    extra = ["--offline"] if "--offline" in sys.argv else []
    fallos = []
    for paso in PASOS:
        print(f"\n== {paso}")
        args = [sys.executable, str(AQUI / paso)] + (extra if paso != "descargar_limite.py" else [])
        codigo = subprocess.call(args, cwd=AQUI)
        if codigo:
            fallos.append(paso)
            if paso == "descargar_limite.py":
                print("Sin límite del partido no se puede recortar nada: se corta acá.")
                return 1
    print("\nListo." if not fallos else f"\nTerminó con avisos en: {', '.join(fallos)}")
    print("Recordá subir la versión de CACHE en docs/sw.js para que los celulares con la app instalada tomen los datos nuevos.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
