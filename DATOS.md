# Relevamiento de fuentes de datos abiertos

Mapa interactivo de riesgos del partido de Necochea (provincia de Buenos Aires, Argentina).
Fase 1 (relevamiento con buscador): 26/09/2026. Fase 2 (descarga y verificación con los scripts de `/scripts`): 26/09/2026.

## Cómo leer este documento

Cada fuente lleva uno de estos estados:

- **Verificada**: se descargó el dato, se abrió y se confirmaron fecha, licencia, formato y cobertura contra la fuente original.
- **Identificada**: la fuente existe según su propio sitio o documentación oficial, pero **no se descargó ni se abrió el dato**. Fecha, cobertura y a veces licencia quedan por confirmar.
- **Sin fuente**: no se encontró un dato abierto que cubra la necesidad.

Desde la Fase 2, la verificación la hacen los scripts: cada capa pasa cuatro controles (archivo GeoJSON válido y con elementos, todos los elementos dentro del partido, ninguna etiqueta excluida y la frase de la licencia presente en la página de la fuente). El resultado de cada control queda en `docs/datos/capas.json`, las huellas SHA-256 de cada descarga en `datos/registro_descargas.json` y las lecturas de las páginas de licencia, con el fragmento encontrado, en `datos/licencias_verificadas.json`.

Regla del proyecto: ninguna capa se completa con datos inventados, estimados ni simulados. Una capa sin datos verificados se muestra en el mapa como **"pendiente de fuente"**.

## Estado de la red del entorno (26/09/2026)

- **Fase 1 y comienzo de la Fase 2:** el proxy del entorno rechazaba por política (403 al abrir el túnel) todos los dominios de datos. Se probaron doce: los ocho de la sección 5 de la Fase 1 más datosgobar.github.io, download.geofabrik.de, tile.openstreetmap.org y overpass.kumi.systems.
- **Después del ajuste del "Network access" hecho por Sebastián:** el proxy dejó de rechazar conexiones. Responden apis.datos.gob.ar e infra.datos.gob.ar (la raíz de ambos devuelve 403 del propio servidor, pero la API y las descargas funcionan), datosgobar.github.io, www.ign.gob.ar, firms.modaps.eosdis.nasa.gov, ideba.gba.gob.ar, www.openstreetmap.org, tile.openstreetmap.org, www.earthdata.nasa.gov, operations.osmfoundation.org, docs.github.com, www.geofabrik.de y overpass-turbo.eu.
- **Cortan la conexión desde el entorno:** ada.gba.gov.ar, riesgohidrico.ada.gba.gov.ar y download.geofabrik.de, siempre; overpass-api.de, de forma intermitente (pasó con pedidos GET espaciados y reintentos). El túnel se abre y el corte llega después del saludo TLS, así que no es el filtro del entorno. Sebastián comprobó el mismo día que ada.gba.gov.ar, www.geofabrik.de y overpass-turbo.eu abren desde su conexión. **Inferido:** esos servidores (o sus redes) rechazan conexiones que llegan desde la nube.

---

## 0. Referencia: límite del partido de Necochea

### 0.1 Georef (Servicio de Normalización de Datos Geográficos de Argentina) · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Organismo | Secretaría de Innovación Pública, Presidencia de la Nación (datos.gob.ar). Las geometrías provienen del IGN (atributo `"fuente": "IGN"`). |
| URL usada | https://apis.datos.gob.ar/georef/api/departamentos.geojson, enlazada desde https://datosgobar.github.io/georef-ar-api/download/. Redirige a https://infra.datos.gob.ar/georef/departamentos.geojson. |
| Licencia | Creative Commons Atribución 4.0 Internacional (CC BY 4.0). Texto en https://datosgobar.github.io/georef-ar-api/terms/, leído el 26/09/2026: "Los datos del Servicio de Normalización de Datos Geográficos de Argentina se disponibilizan bajo la licencia Creative Commons Attribution 4.0 y pueden ser usados para cualquier fin, incluyendo fines comerciales." |
| Formato | GeoJSON: FeatureCollection de 529 departamentos con geometría Polygon o MultiPolygon. |
| Fecha de los datos | El servidor declara `Last-Modified: Wed, 19 Aug 2026 15:02:17 GMT`. Es la fecha del archivo publicado, **no la de la geometría**: Georef no informa de qué versión de la capa del IGN sale. |
| Cobertura | Nacional. Necochea: id `06581`, "Partido de Necochea", provincia `06` (Buenos Aires), categoría "Partido". |
| Huella | SHA-256 `31afdfe5983b6d7648eba1eafc7a5a8fe3c591abdca4b17c311c08c75d361e92`, 1.193.417 bytes. Dos descargas separadas dieron la misma huella. |
| Limitaciones | Geometría muy generalizada: el partido es un Polygon de **57 vértices**, con caja envolvente de longitud -59,67703 a -58,619452 y latitud -38,736675 a -37,616925. La costa y los bordes con los partidos vecinos son aproximados. Límite administrativo, no catastral. |
| Corrección a la Fase 1 | La consulta por API propuesta en la Fase 1 (`/georef/api/departamentos?provincia=06&nombre=necochea&formato=geojson`) **no sirve para el límite**: aun con `campos=completo`, devuelve solo el centroide (Point, -59,1673869; -38,2554110). El polígono está únicamente en el archivo de descarga completo. |
| Archivo publicado | `docs/datos/limite.geojson`. Script: `scripts/descargar_limite.py`. |

### 0.2 IGN, capa "Departamentos" · **Identificada** · alternativa · en revisión (Fase 2)

| Campo | Detalle |
|---|---|
| Organismo | Instituto Geográfico Nacional (IGN) |
| URL | https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG |
| Licencia | **No confirmada.** La documentación del IGN describe la licencia como "libre según Freedom Defined", pero no se pudo leer el texto exacto. Georef, que usa estas geometrías, las publica bajo CC BY 4.0. |
| Formato | SHP, KML, GeoJSON; también WMS y WFS (https://www.ign.gob.ar/geoservicios). |
| Fecha / cobertura | A confirmar al descargar. Nacional. |
| Limitaciones | Igual que Georef. |
| Por qué importa | Si el IGN publica la misma capa con más detalle y licencia explícita, mejoraría la costa y los bordes del límite de Georef (57 vértices). |

**Decisión:** el mapa usa Georef (0.1) por tener licencia explícita comprobada, y cita al IGN como origen de la geometría.

---

## 1. Inundaciones y anegamientos

### 1.1 Autoridad del Agua (ADA), cartas de riesgo hídrico · **Sin fuente para Necochea (confirmado)**

| Campo | Detalle |
|---|---|
| Organismo | Autoridad del Agua, Subsecretaría de Recursos Hídricos, provincia de Buenos Aires |
| URLs | https://riesgohidrico.ada.gba.gov.ar/mapas-de-peligrosidad-por-cuencas/ · https://ada.gba.gov.ar/cartas-de-riesgo-hidrico/ |
| Qué se sabe | Los mapas de peligrosidad usan cuatro categorías (muy alta, alta, media, baja o nula). Las cuencas publicadas según el buscador son del conurbano y el Gran La Plata: Reconquista, Luján, La Plata, San Francisco, Las Piedras, Sarandí y Santo Domingo. **No apareció ninguna para el río Quequén Grande ni para Necochea.** |
| Licencia / formato / fecha | A confirmar. No se encontró licencia explícita. |
| Limitaciones | Si no hay mapa para la cuenca, esta es la fuente oficial que falta, no una que se pueda reemplazar. |
| Fase 2 | **Confirmado a mano por Sebastián el 26/09/2026** en https://ada.gba.gov.ar/cartas-de-riesgo-hidrico/: la carta de riesgo hídrico de la cuenca del río Quequén Grande no existe todavía (no está hecha). Desde el entorno en la nube los sitios de la ADA cortan la conexión, así que la comprobación es solo la manual. |

### 1.1 bis ADA, visor GIS: capa de cuencas `cuencas_ssrh2` · **Identificada, sin servicio abierto ni licencia** · no se usa

| Campo | Detalle |
|---|---|
| Organismo | Autoridad del Agua, provincia de Buenos Aires |
| URL | https://gis.ada.gba.gov.ar/gis/?l=cuencas_ssrh2&b=13 (la encontró Sebastián el 26/09/2026) |
| Qué muestra | Límites de cuencas hidrográficas; según Sebastián, incluye la del río Quequén Grande. |
| Qué no es | **No es un mapa de peligrosidad**: indica hacia dónde escurre el agua, no qué zonas se inundan. Serviría como referencia, no como amenaza. |
| Acceso desde el entorno | El visor responde. Es la aplicación de gestión de la ADA (incluye denuncias, resoluciones, certificados y pluviómetros), no un portal de datos. La lista de capas que el visor pide por detrás (`/gis/process/?process=1&action=1`) contesta `{"error":"-1"}` aun con la cookie de sesión de la página. En el código del visor no figura ningún servicio WMS o WFS público de la capa. |
| Licencia | No encontrada. |
| Decisión | No se usa: sin servicio abierto ni licencia no se puede redistribuir, y extraer la capa de una aplicación interna sería un rodeo. Entraría como referencia si la ADA o IDEBA la publican por WFS o descarga con licencia. **Adivinando:** "ssrh" puede aludir a la Subsecretaría de Recursos Hídricos (provincial o nacional); si fuera la delimitación nacional de cuencas, podría estar publicada como dato abierto en otro sitio. |

Contexto institucional verificado en el sitio de la ADA (vía buscador): el Comité de Cuenca Hídrica del Río Quequén Grande se creó el 05/07/2002 por Resolución 004/02 e integra a Necochea, Lobería, Tandil, Adolfo Gonzales Chaves, Benito Juárez y San Cayetano (https://ada.gba.gov.ar/listado-de-los-comites-de-cuencas/).

### 1.2 IDEBA, geoservicios provinciales (incluida la ADA) · **Identificada** · en revisión (Fase 2)

| Campo | Detalle |
|---|---|
| Organismo | Infraestructura de Datos Espaciales de la Provincia de Buenos Aires (Subsecretaría de Gobierno Digital) |
| URLs | https://ideba.gba.gob.ar/geoservicios · visor de la ADA: https://ideba.gba.gob.ar/index.php/es/visualizador/autoridad-del-agua |
| Qué ofrece | Listado de servicios WMS y WFS de organismos provinciales. |
| Licencia / formato / fecha / cobertura | A confirmar capa por capa al descargar. |
| Limitaciones | Un WMS es solo una imagen; para reutilizar el dato hace falta WFS o descarga vectorial. |

### 1.3 Hidrografía: IGN (cursos y cuerpos de agua, línea de costa) · **Identificada** · no se usa

| Campo | Detalle |
|---|---|
| Organismo | Instituto Geográfico Nacional |
| URL | https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG (clase Hidrografía y oceanografía) |
| Licencia | No confirmada (ver 0.2). |
| Formato | SHP, KML, GeoJSON; WMS y WFS. |
| Fecha / cobertura | A confirmar. Nacional. |
| Limitaciones | Representa dónde corre el agua, **no** dónde se inunda. Sirve de referencia, no de amenaza. |
| Fase 2 | No se descargó: la capa de referencia hidrográfica sale de OpenStreetMap (1.4), que tiene licencia comprobada. |

### 1.4 Hidrografía: OpenStreetMap · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Organismo | Fundación OpenStreetMap y colaboradores |
| URL usada | API Overpass, https://overpass-api.de/api/interpreter. La consulta exacta queda en `datos/crudos/osm/hidrografia.overpassql` cada vez que corre `scripts/descargar_osm.py`. |
| Qué se consulta | `waterway=river`, `stream`, `canal`, `drain` y `ditch`; `natural=water`; `natural=coastline`. Dentro de la caja del límite (0.1), recortado después por el polígono: entra todo elemento con al menos un vértice dentro del partido. |
| Licencia | Open Database License (ODbL) 1.0. Texto en https://www.openstreetmap.org/copyright, leído el 26/09/2026: "OpenStreetMap is open data, licensed under the Open Data Commons Open Database License (ODbL) by the OpenStreetMap Foundation (OSMF)." Obliga a citar "© colaboradores de OpenStreetMap" y a publicar los derivados bajo ODbL. |
| Formato | Respuesta JSON de Overpass convertida a GeoJSON; coordenadas redondeadas a 5 decimales (alrededor de 1 m); solo se conservan las etiquetas que describen el elemento. |
| Fecha de los datos | Base de OpenStreetMap al 2026-09-26T17:21:54Z (campo `timestamp_osm_base` de la respuesta). |
| Resultado | 2.290 elementos: 1.932 cuerpos de agua, 122 arroyos, 91 canales, 67 zanjas, 43 desagües, 19 tramos de río y 16 tramos de línea de costa. Otros 2.326 elementos de la caja quedaron fuera del partido. |
| Limitaciones | Carga voluntaria, sin control oficial: la completitud en zona rural es desigual. Un río que cruza el límite se ve completo, incluso fuera del partido. |
| Archivo publicado | `docs/datos/hidrografia.geojson` (2,2 MB). |

### 1.5 INTA, cartas de suelos (drenaje, anegabilidad) · **Identificada, licencia no confirmada**

| Campo | Detalle |
|---|---|
| Organismo | Instituto Nacional de Tecnología Agropecuaria (GeoINTA) |
| URLs | https://visor.geointa.inta.gob.ar/ · http://www.geointa.inta.gob.ar/ · https://geo.inta.gob.ar/ |
| Qué ofrece | Mapas de suelos con atributos de las series; se publican por WMS. |
| Licencia | **No encontrada.** Sin licencia explícita no se puede redistribuir. |
| Limitaciones | Un atributo de drenaje de suelos es un indicador de propensión al anegamiento, no un mapa de peligrosidad. |

### 1.6 Otras referencias encontradas (no son capas)

- Oficina de Riesgo Agropecuario, mapas de déficit y exceso hídrico: http://www.ora.gob.ar/riesgo_mapas.php (imágenes de monitoreo agroclimático; sirven para la Metodología, no como capa vectorial).
- Artículo académico sobre un modelo de anegamiento en el sudeste bonaerense, *GeoFocus*: https://www.geofocus.org/index.php/geofocus/article/view/262 (bibliografía; no es un dato abierto descargable, a confirmar).

**Estado de la amenaza "Inundaciones":** la referencia (hidrografía y costa) está verificada, pero **no hay un mapa oficial de peligrosidad hídrica para el partido**: la ADA todavía no elaboró la carta de riesgo hídrico de la cuenca del Quequén Grande (1.1). La capa de amenaza sigue **"pendiente de fuente"** hasta que se publique.

---

## 2. Incendios de pastizal y rurales

### 2.1 NASA FIRMS, focos de calor MODIS y VIIRS · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Organismo | NASA, LANCE / FIRMS (Fire Information for Resource Management System). Los datos estándar los procesa la Universidad de Maryland. |
| URLs usadas | `https://firms.modaps.eosdis.nasa.gov/data/country/modis/AÑO/modis_AÑO_Argentina.csv` y `https://firms.modaps.eosdis.nasa.gov/data/country/viirs-snpp/AÑO/viirs-snpp_AÑO_Argentina.csv`. La página https://firms.modaps.eosdis.nasa.gov/country/ arma los enlaces con JavaScript; el patrón se comprobó pidiendo los archivos. |
| Disponibilidad (26/09/2026) | MODIS: 2000 a 2024. VIIRS S-NPP: 2012 a 2024. Los años 2025 y 2026 responden 404: el resumen anual todavía no está publicado. Con los patrones `viirs-noaa20` y `viirs-noaa21` no respondió ningún año. |
| Licencia | El léame de FIRMS (https://firms.modaps.eosdis.nasa.gov/download/Readme.txt) pide citar y "replicate or provide a link to the disclaimer", y remite a la política de Earthdata (https://www.earthdata.nasa.gov/engage/open-data-services-software-policies/data-use-policy), que dice, leída el 26/09/2026: "Unless the content is marked with a use restriction or license, data provided from a NASA-led mission are licensed as Creative Commons Zero (CC0)." Queda como **CC0 con pedido de cita y enlace al aviso legal**. |
| Aviso legal (textual) | "Due to the spatial resolution and other characteristics of these data, their use for tactical decision-making or informing about conditions at a local scale are not advised." Los datos se entregan "as is". Va citado en la Metodología. |
| Faltantes declarados | Según el léame: faltan datos MODIS de fines de junio a principios de julio de 2001, en varias partes de 2002, desde mediados de agosto de 2007 y parte del 21 y todo el 22 de abril de 2009. |
| Formato | CSV. Campos MODIS: latitude, longitude, brightness, scan, track, acq_date, acq_time, satellite, instrument, confidence (0 a 100), version, bright_t31, frp, daynight, type. VIIRS: igual, con bright_ti4 y bright_ti5, y confidence en l, n o h (baja, nominal, alta). Coordenadas en WGS84. |
| Versión | MODIS mezcla colecciones según el año: el campo `version` vale 6.2 (2000 a 2017), 6.03 (2018 a 2022) y 61.03 (2023 y 2024). **Inferido:** 6.x es la Colección 6 y 61.x la 6.1. La FAQ de FIRMS (https://www.earthdata.nasa.gov/data/tools/firms/faq) dice que la 6.1 no cambió el algoritmo de detección, solo la calibración. VIIRS: `version` 2 en toda la serie. |
| Campo `type` | Según https://www.earthdata.nasa.gov/data/tools/firms/active-fire-data-attributes-modis-viirs: "0 = presumed vegetation fire 1 = active volcano 2 = other static land source 3 = offshore". No se filtra: se muestra en el mapa. |
| Resultado en el partido | **MODIS: 658 focos** del 16/11/2000 al 12/11/2024 (641 de tipo 0 y 17 de tipo 2; 49 con confianza menor al 30 %). **VIIRS: 600 focos** del 10/02/2012 al 20/12/2024, todos de tipo 0 (494 de confianza nominal, 70 baja y 36 alta). Los focos por año quedan en `docs/datos/capas.json` y en la Metodología. |
| Controles hechos | Los 17 focos MODIS de tipo 2 (entre el 31/10/2018 y el 12/11/2024) están cerca del puerto: la mitad, a menos de 3,4 km del nodo "Puerto Quequén" de OSM. Con píxeles de 1 km no se atribuyen a ninguna instalación. En la caja del partido, VIIRS registró además 612 detecciones de tipo 2 concentradas en un punto (alrededor de -59,39; -37,68), **fuera del límite**, que el recorte excluye. En ese mismo punto OSM tiene un desvío ferroviario de Ferro Sur Roca con `usage=industrial` (comprobado); que se trate de una planta industrial es inferencia. |
| Huellas | SHA-256 de cada CSV nacional en `datos/registro_descargas.json`. Del archivo nacional se guardan solo las filas de la caja del partido. |
| Limitaciones | Un foco de calor es una **anomalía térmica detectada por satélite**, no un incendio confirmado: incluye quemas agrícolas, fuentes industriales y falsos positivos. No mide superficie quemada. La resolución (alrededor de 1 km en MODIS y 375 m en VIIRS), la hora de paso y la nubosidad provocan omisiones. MODIS y VIIRS pueden detectar el mismo fuego: las capas no se suman. |
| Archivos publicados | `docs/datos/incendios_modis.geojson` y `docs/datos/incendios_viirs.geojson`. Script: `scripts/descargar_firms.py`. |

### 2.2 Servicio Nacional de Manejo del Fuego (SNMF), estadísticas · **Identificada, sin escala de partido**

| Campo | Detalle |
|---|---|
| Organismo | SNMF, Ministerio de Seguridad de la Nación (a confirmar la dependencia vigente) |
| URLs | https://www.argentina.gob.ar/servicio-nacional-de-manejo-del-fuego · informes mensuales en PDF, por ejemplo https://www.argentina.gob.ar/sites/default/files/informe_ocurrencia_junio2025.pdf |
| Qué ofrece | Cantidad de incendios y superficie afectada por provincia, según lo que reportan las jurisdicciones. |
| Licencia / fecha | A confirmar. |
| Limitaciones | Según lo encontrado, **agrega por provincia**, sin geometría ni detalle por partido. Sirve para contexto en la Metodología, no como capa. |

### 2.3 Índice de peligro de incendio (SMN) · **Identificada, no aplica como capa**

https://www.smn.gob.ar/indices_peligro_fuego. Es un índice meteorológico diario, no un registro histórico. Se puede mencionar en la Metodología.

### 2.4 INTA, superficie quemada · **Sin fuente**

No se encontró un producto abierto del INTA con superficie quemada para el sudeste bonaerense. Queda pendiente de búsqueda manual.

**Estado de la amenaza "Incendios":** capa publicada con FIRMS (2.1), aclarando que muestra **focos de calor, no incendios**. La superficie quemada sigue **"pendiente de fuente"**.

---

## 3. Actividad portuaria e industrial

### 3.1 OpenStreetMap: puerto, silos, zonas industriales, ferrocarril y rutas · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Qué se consulta | `landuse=industrial`, `landuse=port`, `industrial=port`, `harbour=*`, `man_made=silo`, `man_made=storage_tank`, `man_made=pier`, `man_made=breakwater`, `railway=rail`, `highway=trunk`, `highway=primary` y `hgv=designated`, en la caja del límite y recortado por el polígono. Consulta exacta en `datos/crudos/osm/portuaria.overpassql`. |
| Licencia, URL y formato | Igual que 1.4 (ODbL 1.0, misma lectura de la página de licencia). |
| Fecha de los datos | Base de OpenStreetMap al 2026-09-26T17:24:01Z. |
| Resultado: instalaciones | 646 elementos (`docs/datos/portuaria_instalaciones.geojson`): 575 silos (462 puntos y 113 polígonos), 40 tanques de almacenamiento, 16 zonas industriales (dos con rubro: `industrial=agriculture` e `industrial=gas`), 13 muelles, 1 escollera ("Escollera Norte") y 1 nodo `harbour=yes` ("Puerto Quequén"). **No hay ningún elemento `landuse=port` ni `industrial=port` dentro del partido.** |
| Resultado: transporte | 66 tramos (`docs/datos/portuaria_transporte.geojson`): 48 troncales y 18 primarios, con referencias RN228, RP227, RP72, RP75, RP86, RP88 y 076-09. **Ninguna vía `railway=rail` dentro del partido:** las 12 de la caja están en partidos vecinos. Tampoco hay vías con `hgv=designated`. |
| Exclusiones | La consulta resta `man_made=surveillance`, `amenity=police`, `surveillance=*` y `surveillance:type=*`; el script vuelve a filtrar al procesar. Las respuestas crudas no trajeron ningún elemento excluido. |
| Limitaciones | Completitud desconocida y carga voluntaria. Los accesos de camiones no están etiquetados y **no se deducen**. La capa muestra **dónde están** las instalaciones, **no cuánto riesgo generan**: no hay datos abiertos sobre sustancias, volúmenes ni planes de contingencia. |
| Pregunta abierta | Con qué etiqueta figura en OSM el ramal ferroviario a Quequén (puede estar como `disused`, `abandoned` u otra). La consulta de control del 26/09/2026 se cortó; revisar a mano en https://www.openstreetmap.org. |

### 3.2 Consorcio de Gestión del Puerto Quequén · **Identificada, sin datos geográficos abiertos**

| Campo | Detalle |
|---|---|
| Organismo | Consorcio de Gestión del Puerto Quequén (ente de derecho público no estatal, Ley provincial 11.414: https://normas.gba.gob.ar/documentos/B3zPPcjx.html) |
| URL | https://puertoquequen.com · informe de gestión: https://puertoquequen.com/informe-de-gestion/ |
| Qué se encontró | Información institucional y operativa (terminales, capacidad de almacenamiento, sistema AIS). **No se encontró cartografía descargable ni licencia de reutilización.** |
| Uso posible | Contexto y cita en la Metodología; no como capa. |

### 3.3 Municipalidad de Necochea, zonificación (Código de Ordenamiento Territorial) · **Sin fuente geográfica**

| Campo | Detalle |
|---|---|
| Qué se encontró | La zonificación del complejo urbano Necochea-Quequén surge de la Ordenanza 2005/81 (modificada por la Ordenanza 2358/91). La Ordenanza 5558/05 asignó al sector "Uso Específico 13" de Quequén la zona "C" (industrial mixta), según el Decreto provincial 1741/96. El municipio trabaja en una actualización del código (https://necochea.gov.ar/el-municipio-suma-consenso-tecnico-para-avanzar-en-la-actualizacion-del-codigo-de-ordenamiento-territorial/). |
| Limitaciones | No se encontró la zonificación como dato geográfico abierto. Sin archivo oficial, **no se digitaliza a ojo desde un plano**. |
| Acción manual | Consultar al municipio si publica la zonificación en SHP o GeoJSON, y con qué licencia. |

**Estado de la amenaza "Portuaria e industrial":** capas publicadas con OpenStreetMap. Muestran dónde están las instalaciones y la red vial principal, no cuánto riesgo generan. La zonificación sigue **"pendiente de fuente"**.

---

## 4. Exclusiones (no se incluyen en ninguna capa)

- Cámaras de videovigilancia y cualquier infraestructura de seguridad (comisarías, centros de monitoreo, etcétera).
- Datos personales.
- Cómo se aplica: las consultas a OpenStreetMap restan `man_made=surveillance`, `amenity=police`, `surveillance=*` y `surveillance:type=*`; el script de OSM vuelve a descartar esos elementos al procesar; `scripts/verificar.py` revisa tanto la respuesta cruda como el archivo publicado, y si encontrara alguno, la capa no se publica. De cada elemento solo se conservan etiquetas descriptivas (nombre, tipo, operador, referencia), nunca teléfonos, correos ni otros datos de contacto.

---

## 5. Pendientes y descargas manuales

**Dominios que usan los scripts** (tienen que estar habilitados en el "Network access" del entorno): `apis.datos.gob.ar`, `infra.datos.gob.ar`, `datosgobar.github.io`, `firms.modaps.eosdis.nasa.gov`, `overpass-api.de`, `www.openstreetmap.org` y `www.earthdata.nasa.gov`. Si Overpass corta desde la nube, correr `scripts/descargar_osm.py` desde una computadora propia.

Pendientes a mano:

1. **ADA (1.1): hecho.** Sebastián revisó https://ada.gba.gov.ar/cartas-de-riesgo-hidrico/ el 26/09/2026: la carta de la cuenca del Quequén Grande no está hecha. Volver a mirar esa página en cada actualización.
2. **Ferrocarril en OSM (3.1):** revisar en https://www.openstreetmap.org con qué etiqueta está el ramal a Quequén.
3. **FIRMS 2025 (2.1):** cuando FIRMS publique el resumen anual de 2025, volver a correr `python3 scripts/actualizar.py`.
4. **INTA (1.5 y 2.4) y SNMF (2.2):** sin cambios desde la Fase 1.

Si un sitio no deja descargar, cada archivo se puede bajar a mano y dejar en `datos/crudos/` para procesarlo con `python3 scripts/actualizar.py --offline` (instrucciones en el README).

---

## 6. Resumen por capa

| Capa | Fuente | Estado | En el mapa |
|---|---|---|---|
| Límite del partido | Georef (geometría del IGN) | Verificada, CC BY 4.0; archivo del 19/08/2026 | Publicada |
| Inundaciones: peligrosidad | ADA | Sin fuente: la carta de riesgo hídrico del Quequén Grande no está hecha (confirmado a mano) | Pendiente de fuente |
| Inundaciones: hidrografía y costa | OpenStreetMap | Verificada, ODbL; base del 26/09/2026 | Publicada (2.290 elementos) |
| Incendios: focos de calor MODIS | NASA FIRMS | Verificada, CC0 con cita; 2000 a 2024 | Publicada (658 focos) |
| Incendios: focos de calor VIIRS S-NPP | NASA FIRMS | Verificada, CC0 con cita; 2012 a 2024 | Publicada (600 focos) |
| Incendios: superficie quemada | Ninguna | Sin fuente | Pendiente de fuente |
| Portuaria e industrial: instalaciones | OpenStreetMap | Verificada, ODbL; base del 26/09/2026 | Publicada (646 elementos) |
| Portuaria e industrial: rutas y ferrocarril | OpenStreetMap | Verificada, ODbL; sin vías férreas en el partido | Publicada (66 tramos) |
| Portuaria e industrial: zonificación | Municipio | Sin fuente geográfica | Pendiente de fuente |
