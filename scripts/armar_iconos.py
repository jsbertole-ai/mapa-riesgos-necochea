"""Arma docs/vendor/lucide/iconos.js con los íconos del mapa (decisión de Sebastián, 08/11/2026).

Uso:  python3 scripts/armar_iconos.py RUTA/A/lucide-static/package

Los íconos salen del paquete npm "lucide-static" (licencia ISC; algunos íconos, MIT, derivados de
Feather). Para obtenerlo:  npm pack lucide-static@1.59.0 && tar xzf lucide-static-1.59.0.tgz
Se guarda solo el contenido de cada SVG (los trazos), no el archivo entero, y se copia la licencia
a docs/vendor/lucide/LICENSE, como pide la ISC.

La lista de abajo es la única que usa el sitio: para sumar un ícono, agregarlo acá y volver a correr.
"""

import json
import re
import shutil
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "docs" / "vendor" / "lucide"

ICONOS = sorted(set("""
waves flame factory building-2 users shield-plus history
bridge
fuel database cylinder sprout flask-conical anchor lighthouse flag-triangle-right zap trash-2 droplets
graduation-cap hospital droplet waves-arrow-up radio-tower smartphone tv
fire-extinguisher shield siren heart-pulse cctv trees life-buoy radio house hand-heart cooking-pot bed
stone cloud-lightning tornado wind tree-pine skull triangle-alert brick-wall circle-alert
cloud-rain cloud-hail snowflake thermometer-snowflake thermometer-sun sun bomb car-front bug cloud-fog
construction wheat utility-pole
""".split()))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 1
    paquete = Path(sys.argv[1])
    version = json.loads((paquete / "package.json").read_text(encoding="utf-8"))["version"]
    salida = {}
    for nombre in ICONOS:
        texto = (paquete / "icons" / f"{nombre}.svg").read_text(encoding="utf-8")
        salida[nombre] = re.sub(r"\s+", " ", re.search(r"<svg[^>]*>(.*)</svg>", texto, re.S).group(1)).strip()
    DESTINO.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(paquete / "LICENSE", DESTINO / "LICENSE")
    (DESTINO / "iconos.js").write_text(
        f"/* Íconos de Lucide (lucide-static {version}), https://lucide.dev\n"
        " * Licencia ISC (algunos íconos, MIT, derivados de Feather): ver LICENSE en esta carpeta.\n"
        " * Generado por scripts/armar_iconos.py: solo los trazos de cada ícono que usa el mapa. */\n"
        "window.ICONOS = " + json.dumps(salida, ensure_ascii=False, indent=0) + ";\n",
        encoding="utf-8",
    )
    print(f"{len(salida)} íconos de lucide-static {version} en {DESTINO.relative_to(RAIZ)}/iconos.js")
    return 0


if __name__ == "__main__":
    sys.exit(main())
