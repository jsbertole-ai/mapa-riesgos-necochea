# Mapa de riesgos del partido de Necochea

Mapa interactivo de amenazas del partido de Necochea (provincia de Buenos Aires, Argentina) hecho solo con datos abiertos: inundaciones y anegamientos, incendios de pastizal y rurales, y actividad portuaria e industrial. Es un sitio estático, sin servidor propio, pensado para publicarse en GitHub Pages y para instalarse como aplicación en el celular.

Proyecto de Juan Sebastián Bértole, estudiante de la Licenciatura en Gestión de Riesgos y Siniestralidad (Instituto Universitario Vucetich).

Una vez publicado, el sitio queda en https://jsbertole-ai.github.io/mapa-riesgos-necochea/

## Qué hay en el repositorio

| Carpeta o archivo | Contenido |
|---|---|
| `docs/` | El sitio completo: `index.html` (mapa), `metodologia.html`, estilos, código, íconos, manifiesto y service worker. |
| `docs/datos/` | Las capas ya procesadas (GeoJSON) y `capas.json`, el registro que lee el sitio con fuente, fecha, licencia y estado de cada capa. |
| `docs/vendor/leaflet/` | Leaflet 1.9.4 (licencia BSD de 2 cláusulas), copiado desde npm. |
| `scripts/` | Scripts en Python para descargar, recortar y verificar los datos. Solo usan la biblioteca estándar. |
| `datos/fuentes.json` | Datos fijos de cada capa: organismo, URL, licencia, qué representa y qué no. |
| `datos/*.json` | Constancias de la última actualización: descargas con huella SHA-256, resultados del procesamiento y lecturas de las páginas de licencia. |
| `DATOS.md` | Registro completo de fuentes, verificadas, identificadas y descartadas. |

Los archivos crudos que se descargan (`datos/crudos/`) no se suben al repositorio: se regeneran con los scripts y su huella queda en `datos/registro_descargas.json`.

## Ver el sitio en tu computadora

El sitio tiene que servirse por HTTP; abriendo `index.html` directo desde el disco no carga las capas. Con Python alcanza:

```
python3 -m http.server 8080 --directory docs
```

y después abrir http://localhost:8080 en el navegador.

## Publicar en GitHub Pages

GitHub Pages publica desde una rama y una carpeta. Este sitio está en la carpeta `docs` de la rama `main`.

1. Asegurate de que los cambios estén en `main` (si trabajaste en otra rama, uní esa rama a `main` con un pull request).
2. En GitHub, entrá al repositorio y abrí **Settings**.
3. En la barra lateral, sección "Code, planning, and automation", elegí **Pages**.
4. En "Build and deployment", en "Source", elegí **Deploy from a branch**.
5. En el selector de rama elegí `main` y en el de carpeta, `/docs`. Tocá **Save**.
6. A los pocos minutos el sitio aparece en https://jsbertole-ai.github.io/mapa-riesgos-necochea/ y se vuelve a publicar solo cada vez que se sube un cambio a `main`.

Con una cuenta gratuita, GitHub Pages funciona solo si el repositorio es público (este lo es). Fuente: documentación de GitHub, "Configuring a publishing source for your GitHub Pages site", consultada el 26/09/2026.

La carpeta `docs` incluye un archivo vacío `.nojekyll` para que GitHub publique los archivos tal cual, sin procesarlos con Jekyll.

## Actualizar los datos

Hace falta Python 3.9 o posterior. No hay que instalar nada más.

```
python3 scripts/actualizar.py
```

Eso corre, en orden:

1. `descargar_limite.py`: baja el archivo de departamentos de Georef y extrae el partido de Necochea. Sin límite no se puede recortar nada, así que si falla, se corta ahí.
2. `descargar_firms.py`: baja los resúmenes anuales de focos de calor de NASA FIRMS para la Argentina (MODIS desde 2000, VIIRS S-NPP desde 2012), guarda solo lo que cae en la zona y recorta por el partido. Los años que FIRMS todavía no publicó responden 404 y se saltean.
3. `descargar_osm.py`: consulta OpenStreetMap por la API Overpass (hidrografía, instalaciones portuarias e industriales, rutas y ferrocarril), descarta vigilancia y policía, y recorta por el partido.
4. `verificar.py`: controla cada capa (archivo válido, dentro del partido, sin etiquetas excluidas y con la licencia confirmada en la página de la fuente) y genera `docs/datos/capas.json`. Una capa que no pasa los controles se publica como "pendiente de fuente".

Después de actualizar:

- Revisá lo que cambió (`git diff --stat`) y anotá en `DATOS.md` la nueva fecha de los datos.
- Subí en uno la versión de `CACHE` en `docs/sw.js` (por ejemplo, de `mapa-riesgos-v1` a `mapa-riesgos-v2`), así los celulares con la aplicación instalada descartan la copia vieja.
- Subí los cambios a `main`.

### Si un sitio no deja descargar

Cualquier archivo se puede bajar a mano, dejarlo en `datos/crudos/` y reprocesar sin conexión:

```
python3 scripts/actualizar.py --offline
```

- Límite: el GeoJSON de https://apis.datos.gob.ar/georef/api/departamentos.geojson, guardado como `datos/crudos/departamentos.geojson`.
- Focos de calor: los CSV de https://firms.modaps.eosdis.nasa.gov/data/country/modis/AÑO/modis_AÑO_Argentina.csv y https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/AÑO/viirs-snpp_AÑO_Argentina.csv, guardados con su nombre original en `datos/crudos/firms/`.
- OpenStreetMap: al correr `descargar_osm.py`, la consulta queda escrita en `datos/crudos/osm/hidrografia.overpassql` y `datos/crudos/osm/portuaria.overpassql` aunque la descarga falle. Se puede repetir a mano con curl, por ejemplo:

  ```
  curl -G --data-urlencode data@datos/crudos/osm/hidrografia.overpassql https://overpass-api.de/api/interpreter -o datos/crudos/osm/hidrografia.json
  ```

Overpass a veces corta la conexión cuando recibe muchos pedidos seguidos; el script reintenta con esperas crecientes y deja un minuto entre consultas.

## Reglas del proyecto

- Ningún dato se inventa, estima ni simula. Una capa sin datos verificados se muestra como "pendiente de fuente".
- No se publica la ubicación de cámaras de videovigilancia ni de infraestructura de seguridad, ni datos personales.
- Cada fuente se registra en `DATOS.md` con organismo, URL, fecha, licencia, formato, cobertura y limitaciones.

## Licencias

- Código (sitio y scripts): MIT, ver `LICENSE`.
- Leaflet: licencia BSD de 2 cláusulas, ver `docs/vendor/leaflet/LICENSE`.
- Datos: cada capa conserva la licencia de su fuente y no se relicencia. Detalle en `docs/datos/LEAME.md`.
  - Mapa de fondo y capas derivadas de OpenStreetMap: © colaboradores de OpenStreetMap, Open Database License (ODbL) 1.0. Los GeoJSON derivados se publican bajo ODbL.
  - Límite del partido: Georef (datos.gob.ar), geometría del IGN, Creative Commons Atribución 4.0.
  - Focos de calor: NASA FIRMS, CC0 según la política de datos de Earthdata, con cita y enlace al aviso legal de FIRMS.
