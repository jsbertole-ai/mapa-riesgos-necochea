# Licencias de los datos de esta carpeta

Cada archivo conserva la licencia de su fuente. Nada de esto se relicencia bajo la licencia MIT del código.

| Archivo | Fuente | Licencia | Atribución |
|---|---|---|---|
| `limite.geojson` | Georef, Servicio de Normalización de Datos Geográficos de Argentina (datos.gob.ar); geometría del IGN | Creative Commons Atribución 4.0 (https://datosgobar.github.io/georef-ar-api/terms/) | "Georef (datos.gob.ar), geometría del IGN, CC BY 4.0" |
| `hidrografia.geojson`, `portuaria_instalaciones.geojson`, `portuaria_transporte.geojson` | OpenStreetMap, vía la API Overpass | Open Database License (ODbL) 1.0 (https://www.openstreetmap.org/copyright). Son bases de datos derivadas y se publican bajo ODbL. | "© colaboradores de OpenStreetMap" |
| `incendios_modis.geojson`, `incendios_viirs.geojson` | NASA LANCE / FIRMS, resúmenes anuales por país | CC0 según la política de datos de Earthdata (https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-policy); FIRMS pide citar y enlazar su aviso legal (https://firms.modaps.eosdis.nasa.gov/download/Readme.txt) | "NASA FIRMS (LANCE, NASA ESDIS)" |
| `capas.json` | Registro generado por `scripts/verificar.py` a partir de `datos/fuentes.json` | MIT, como el código | |

Qué representa cada capa, qué no representa y sus limitaciones: ver `metodologia.html` y `DATOS.md` en el repositorio.
