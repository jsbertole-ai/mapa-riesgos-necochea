# Licencias de los datos de esta carpeta

Cada archivo conserva la licencia de su fuente. Nada de esto se relicencia bajo la licencia MIT del código.

| Archivo | Fuente | Licencia | Atribución |
|---|---|---|---|
| `hidrografia.geojson`, `portuaria_instalaciones.geojson` | OpenStreetMap, vía la API Overpass | Open Database License (ODbL) 1.0 (https://www.openstreetmap.org/copyright). Son bases de datos derivadas y se publican bajo ODbL. | "© colaboradores de OpenStreetMap" |
| `limite.geojson`, `localidades.geojson`, `hidrografia_ign.geojson`, `curvas_nivel.geojson`, `vegetacion_hidrofila.geojson`, `puentes_vados.geojson`, `forestaciones.geojson`, `puerto_navegacion.geojson`, `energia.geojson`, `industria_residuos.geojson`, `ferrocarril.geojson`, `red_vial.geojson`, `planta_urbana.geojson`, `educacion.geojson`, `salud.geojson` | Instituto Geográfico Nacional, servicio WFS de sus Capas SIG, recortado al partido | Términos y Condiciones del IGN (https://www.ign.gob.ar/descargas/tyc1.html): uso libre y gratuito; en productos derivados hay que citar la fuente y mencionar la fecha de los datos originales (ver `capas.json`) | "FUENTE: Instituto Geográfico Nacional de la República Argentina" |
| `incendios_modis.geojson`, `incendios_viirs.geojson` | NASA LANCE / FIRMS, resúmenes anuales por país | CC0 según la política de datos de Earthdata (https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-policy); FIRMS pide citar y enlazar su aviso legal (https://firms.modaps.eosdis.nasa.gov/download/Readme.txt) | "NASA FIRMS (LANCE, NASA ESDIS)" |
| `capas.json` | Registro generado por `scripts/verificar.py` a partir de `datos/fuentes.json` | MIT, como el código | |

Qué representa cada capa, qué no representa y sus limitaciones: ver `metodologia.html` y `DATOS.md` en el repositorio.
