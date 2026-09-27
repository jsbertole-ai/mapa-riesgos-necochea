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
| `docs/vendor/source-serif-4/` | Tipografía del título, Source Serif 4 SemiBold (Adobe, licencia SIL OFL 1.1), copiada del paquete npm `@fontsource/source-serif-4`. |
| `scripts/` | Scripts en Python para descargar, recortar y verificar los datos. Solo usan la biblioteca estándar. |
| `datos/inventario/` | Formulario del inventario local: `formulario.json` (listas de tipos de evento, efectos, localidades y servicios) y `formulario_inventario.xlsx`, generado a partir de él para subir a KoboToolbox. |
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

1. `descargar_limite.py`: pide al servicio WFS del IGN el límite del partido de Necochea (código 06581), de origen catastral. Sin límite no se puede recortar nada, así que si falla, se corta ahí.
2. `descargar_firms.py`: baja los resúmenes anuales de focos de calor de NASA FIRMS para la Argentina (MODIS desde 2000, VIIRS S-NPP desde 2012), guarda solo lo que cae en la zona y recorta por el partido. Los años que FIRMS todavía no publicó responden 404 y se saltean.
3. `descargar_osm.py`: consulta OpenStreetMap por la API Overpass (hidrografía detallada e instalaciones portuarias e industriales), descarta vigilancia y policía, y recorta por el partido.
4. `descargar_ign.py`: pide al servicio WFS del Instituto Geográfico Nacional, solo para la zona del partido, catorce capas (hidrografía, curvas de nivel, vegetación hidrófila, puentes, forestaciones, puerto, energía, industria, ferrocarril, rutas, localidades, planta urbana, escuelas y salud) y las recorta por el partido. Es el mismo servicio que usa el botón "Descargar capa" del sitio del IGN.
4 bis. `descargar_energia.py`: líneas de media tensión de la Secretaría de Energía (CC BY 4.0). Su servidor solo sirve por HTTP; si la descarga falla, usa el ZIP bajado a mano en `datos/crudos/energia/` (la URL está en el script).
5. `descargar_indicadores.py`: indicadores del IGN para el partido (eventos registrados en DesInventar entre 1970 y 2015, índice de vulnerabilidad social frente a desastres y niveles regionales del SINAGIR), que la Metodología muestra en "El partido en las estadísticas nacionales".
6. `procesar_inventario.py`: toma la exportación más reciente de KoboToolbox que haya en `datos/crudos/inventario/` y publica solo los registros aprobados que pasan los controles (ver "Inventario local"). Si no hay exportación, no hace nada.
7. `verificar.py`: controla cada capa (archivo válido, dentro del partido, sin etiquetas excluidas y con la licencia confirmada en la página de la fuente) y genera `docs/datos/capas.json`. Una capa que no pasa los controles se publica como "pendiente de fuente".

Después de actualizar:

- Revisá lo que cambió (`git diff --stat`) y anotá en `DATOS.md` la nueva fecha de los datos.
- Subí en uno la versión de `CACHE` en `docs/sw.js` (por ejemplo, de `mapa-riesgos-v6` a `mapa-riesgos-v7`), así los celulares con la aplicación instalada descartan la copia vieja.
- Subí los cambios a `main`.

### Si un sitio no deja descargar

Cualquier archivo se puede bajar a mano, dejarlo en `datos/crudos/` y reprocesar sin conexión:

```
python3 scripts/actualizar.py --offline
```

- Límite: la capa "Departamento" del IGN en GeoJSON (https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG), guardada como `datos/crudos/ign/departamento_06581.geojson`; el script toma solo el partido 06581.
- Focos de calor: los CSV de https://firms.modaps.eosdis.nasa.gov/data/country/modis/AÑO/modis_AÑO_Argentina.csv y https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/AÑO/viirs-snpp_AÑO_Argentina.csv, guardados con su nombre original en `datos/crudos/firms/`.
- IGN: cada capa se puede bajar desde https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG en formato GeoJSON. Para usarla con `--offline`, guardarla en `datos/crudos/ign/` con el nombre de la capa del servicio (por ejemplo, `lineas_de_transporte_ferroviario_AN010.geojson`; la lista está en `scripts/descargar_ign.py`). Ojo: la descarga del sitio trae todo el país, y el script recorta igual.
- OpenStreetMap: al correr `descargar_osm.py`, la consulta queda escrita en `datos/crudos/osm/hidrografia.overpassql` y `datos/crudos/osm/portuaria.overpassql` aunque la descarga falle. Se puede repetir a mano con curl, por ejemplo:

  ```
  curl -G --data-urlencode data@datos/crudos/osm/hidrografia.overpassql https://overpass-api.de/api/interpreter -o datos/crudos/osm/hidrografia.json
  ```

Overpass a veces corta la conexión cuando recibe muchos pedidos seguidos; el script reintenta con esperas crecientes y deja un minuto entre consultas.

## Archivo de alertas del SMN

`scripts/archivar_alertas_smn.py` guarda en `docs/datos/alertas_smn.json` las alertas y avisos del Servicio Meteorológico Nacional que alcanzan al partido. No forma parte de `actualizar.py`: lo corre cada hora la tarea de GitHub Actions `.github/workflows/alertas-smn.yml`, que hace un commit en `main` solo cuando entra una alerta nueva. Las tareas programadas de GitHub corren solo en la rama principal, así que se activa después de mergear. Se puede correr a mano desde la pestaña Actions ("Run workflow") o con `python3 scripts/archivar_alertas_smn.py`. Si un repositorio público pasa 60 días sin actividad, GitHub pausa las tareas programadas: se reactivan desde la misma pestaña.

## Inventario local (KoboToolbox)

Los registros de eventos y vulnerabilidades se cargan con un formulario de KoboToolbox y se publican solo después de revisarlos.

**Preparar el formulario (una vez, o cada vez que cambie `formulario.json`):**

1. `python3 scripts/generar_formulario.py` escribe `datos/inventario/formulario_inventario.xlsx`.
2. En https://kf.kobotoolbox.org: NEW, "Upload an XLSForm", elegir ese archivo y desplegar (DEPLOY). Si el proyecto ya existe, se reemplaza el formulario desde FORM y se vuelve a desplegar.
3. En FORM, dentro de "Collect data", activar "Allow submissions to this form without a username and password" y copiar el enlace del formulario web.
4. Pegar ese enlace como `url_formulario` en la capa `inventario_local` de `datos/fuentes.json` y correr `python3 scripts/verificar.py`: el mapa y la Metodología muestran entonces el enlace "Sumar un registro".
5. No activar "Anyone can view submissions made to this form": expondría también los envíos no aprobados.

**Revisar y publicar:**

1. En DATA, abrir cada envío, controlar la nota de origen y que no haya datos personales, y marcarlo "Approved" (o "Not Approved").
2. Exportar en DOWNLOADS: tipo CSV, "XML values and headers". Guardar el archivo en `datos/crudos/inventario/` (esa carpeta no se sube al repositorio, porque tiene envíos sin revisar y el título de cada nota).
3. `python3 scripts/procesar_inventario.py` y después `python3 scripts/verificar.py`. El primero avisa en pantalla qué registros aprobados no se publicaron y por qué (dato personal posible, punto fuera del partido, duplicado, campo inválido); se corrigen en Kobo y se vuelve a exportar.

El control de datos personales es automático solo para correos, teléfonos, DNI y domicilios con número de puerta; los nombres de personas se revisan al aprobar. KoboToolbox guarda en su historial interno la dirección IP de cada envío: ese historial no se exporta ni se publica.

## Reglas del proyecto

- Ningún dato se inventa, estima ni simula. Una capa sin datos verificados se muestra como "pendiente de fuente".
- No se publica la ubicación de cámaras de videovigilancia ni de infraestructura de seguridad, ni datos personales.
- Cada fuente se registra en `DATOS.md` con organismo, URL, fecha, licencia, formato, cobertura y limitaciones.

## Licencias

- Código (sitio y scripts): MIT, ver `LICENSE`.
- Leaflet: licencia BSD de 2 cláusulas, ver `docs/vendor/leaflet/LICENSE`.
- Datos: cada capa conserva la licencia de su fuente y no se relicencia. Detalle en `docs/datos/LEAME.md`.
  - Mapa de fondo y capas derivadas de OpenStreetMap: © colaboradores de OpenStreetMap, Open Database License (ODbL) 1.0. Los GeoJSON derivados se publican bajo ODbL.
  - Límite del partido y todas las capas del IGN (hidrografía oficial, curvas de nivel, ferrocarril, rutas, vegetación, energía, industria, puerto y elementos expuestos): "FUENTE: Instituto Geográfico Nacional de la República Argentina", según los términos y condiciones del IGN (uso libre y gratuito, con cita de la fuente y de la fecha de los datos).
  - Focos de calor: NASA FIRMS, CC0 según la política de datos de Earthdata, con cita y enlace al aviso legal de FIRMS.
