# Relevamiento de fuentes de datos abiertos

Mapa interactivo de riesgos del partido de Necochea (provincia de Buenos Aires, Argentina).
Fase 1 (relevamiento con buscador): 26/09/2026. Fase 2 (descarga y verificación con los scripts de `/scripts`): 26/09/2026. Desde el cambio al límite del IGN (0.2), todas las capas se recortan con él.

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
- **Corta las descargas:** catalogo.datos.gba.gob.ar (catálogo de datos abiertos de la provincia) responde, pero corta en 31.610 bytes cualquier archivo más grande (probado con un ZIP y un PDF, en HTTP/1.1 y HTTP/2, varias veces), sin fallas registradas en el proxy; un CSV de 5 KB llegó completo. gis.ada.gba.gov.ar (visor de la ADA) responde.
- **Catálogo provincial, también desde la conexión de Sebastián:** los siete ZIP que bajó llegaron truncados (de 220.726 a 220.730 bytes, cuando debían pesar entre 0,6 y 23 MB); el de curvas de nivel, bajado dos veces, dio las dos veces la misma huella SHA-256 (`03c89a98…`). El problema es del servidor del catálogo.
- **IGN:** www.ign.gob.ar y su servicio WFS (wms.ign.gob.ar) responden desde el entorno; el WFS corta alguna conexión suelta, que los reintentos del script resuelven.

---

## 0. Referencia: límite del partido de Necochea

### 0.1 Georef (Servicio de Normalización de Datos Geográficos de Argentina) · **Verificada** · alternativa (reemplazada por el IGN)

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
| Uso | Fue el límite del mapa hasta el 26/09/2026. Lo reemplazó el del IGN (0.2), que tiene 32.136 vértices frente a estos 57. |

### 0.2 IGN: términos y condiciones, servicio WFS y capa "Departamento" · **Verificada** · en uso (límite del partido)

| Campo | Detalle |
|---|---|
| Organismo | Instituto Geográfico Nacional (IGN) |
| Licencia | "Términos y Condiciones de uso de la información descargada del sitio web del Instituto Geográfico Nacional", https://www.ign.gob.ar/descargas/tyc1.html, leídos el 26/09/2026. Cláusulas textuales: "Debe citarse la fuente de los documentos objeto de la reutilización: 'FUENTE: Instituto Geográfico Nacional de la República Argentina'"; "No se podrá indicar, insinuar o sugerir que el Instituto Geográfico Nacional, participa, patrocina o apoya la utilización o reutilización de la misma"; "En el caso de que se generen productos derivados, deberá además mencionarse la fecha de los datos originales del IGN"; "Los datos descargados deben compartirse de manera libre y gratuita"; "Se permite su uso comercial únicamente en el caso de obras derivadas en que la información sea utilizada como insumo para generar un nuevo producto". La reutilización "puede incluir la copia, difusión, modificación, adaptación, extracción, reordenamiento y combinación de la información". |
| Lectura práctica | Compatible con un sitio público, gratuito y sin fines comerciales, siempre que se cite la fuente con esa fórmula, se conserven los metadatos y se mencione la fecha de los datos originales. Cuando el IGN no informa esa fecha, la ficha de la capa lo dice. |
| Servicio | WFS https://wms.ign.gob.ar/geoserver/wfs: 192 capas en el espacio `ign`, con salida GeoJSON. El botón "Descargar capa" de https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG llama a ese mismo servicio (comprobado en el código de la página), así que bajar por el WFS es descargar del sitio del IGN y rigen los términos de arriba. |
| Metadatos | Para ferrocarril, corrientes y espejos de agua, el enlace "Descargar metadato" está comentado en el código de la página y el archivo al que apunta (`ejemplo.pdf`) devuelve 404. La red vial provincial sí tiene metadato: https://www.ign.gob.ar/capas-sig/metadata/red_vial_provincial.pdf (creado el 24/10/2021, "Frecuencia de actualización: mensualmente"). |
| Capa "Departamento" (límite en uso) | `ign:departamento` filtrada por el código `06581`: un MultiPolygon de una parte, con 32.136 vértices. Fuente de captura: "ARBA - Gerencia de Servicios Catastrales". Área aproximada, calculada con una proyección local: 4.546 km² (la versión de Georef da 4.556 km²). Fecha no informada. Archivo: `docs/datos/limite.geojson` (0,7 MB). Script: `scripts/descargar_limite.py`. |
| Efecto del cambio | Con el límite detallado, 4 focos MODIS quedaron fuera y 1 VIIRS entró; la hidrografía oficial pasó de 129 a 138 elementos, las rutas de 21 a 19 tramos y las curvas de nivel de 231 a 229. Las capas de OpenStreetMap se reprocesaron con el mismo límite: hidrografía de 2.290 a 2.279 elementos e instalaciones de 646 a 643 (1.4 y 3.1). |

**Decisión (26/09/2026):** el mapa usa el límite del IGN (0.2), de origen catastral y con licencia comprobada. Georef (0.1) queda como alternativa documentada.

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

### 1.1 ter ADA, red hidrométrica y freatímetros · **Identificada, sin licencia** · no se usa

| Campo | Detalle |
|---|---|
| Organismo | Autoridad del Agua, provincia de Buenos Aires |
| URLs | Documento: https://ada.gba.gov.ar/wp-content/uploads/2025/03/capa-estaciones-hidrometricas-y-freatimetricas.pdf · visor, estaciones hidrométricas: https://gis.ada.gba.gov.ar/gis/?l=red_hidrometrica · visor, freatímetros: https://gis.ada.gba.gov.ar/gis/?l=freatimetros (las encontró Sebastián el 26/09/2026) · página de la red: https://ada.gba.gov.ar/red-hidrometrica/ (indicada por Sebastián; desde el entorno no abre) |
| Qué representa | La red con la que la ADA mide el nivel de los ríos (estaciones hidrométricas) y el de la napa freática (freatímetros). Para un mapa de riesgos es **capacidad de monitoreo** de la amenaza: dónde se mide. La napa importa para leer los anegamientos en la llanura. |
| Qué no representa | No es un mapa de amenaza ni de zonas inundables. Que haya una estación no implica que exista un sistema de alerta para esa zona. |
| Qué dice el documento de la ADA | Sebastián aportó una copia del PDF (2 páginas; metadatos: creado el 17/03/2025). Comprobado en su texto: la capa se abre directo con las URLs del visor; las estaciones se consultan con las herramientas Información o Selección y los resultados "se pueden descargar en formato Excel"; las mediciones (aforos, limnigrafías, niveles de escala y profundidad de agua subterránea) también se exportan a Excel; y con la opción "Descargar capa" del menú contextual "se podrá obtener en formato 'shapefile' (shp) las ubicaciones de las estaciones hidrométricas o freatimétricas". **No menciona licencia ni condiciones de uso.** |
| Acceso desde el entorno y licencia | ada.gba.gov.ar corta la conexión desde la nube; el visor responde, pero la descarga funciona dentro de la sesión del visor. La capa no figura en el catálogo de datos abiertos de la provincia (búsquedas del 26/09/2026 por "hidrometric", "freatimetr", "estaciones hidrom" y "autoridad del agua": cero resultados). Licencia: no encontrada. |
| Para que sea capa | La descarga en shapefile existe; falta la licencia explícita de la ADA. Sin licencia, se enlaza en la Metodología (la URL de acceso directo la publica la propia ADA) pero no se redistribuye (misma regla que 1.5). |
| Acción manual | Si se quiere como capa: pedirle a la ADA el permiso de uso o la licencia de la capa. La copia del PDF no se sube al repositorio. |

Contexto institucional verificado en el sitio de la ADA (vía buscador): el Comité de Cuenca Hídrica del Río Quequén Grande se creó el 05/07/2002 por Resolución 004/02 e integra a Necochea, Lobería, Tandil, Adolfo Gonzales Chaves, Benito Juárez y San Cayetano (https://ada.gba.gov.ar/listado-de-los-comites-de-cuencas/).

### 1.2 IDEBA, geoservicios provinciales (incluida la ADA) · **Identificada**

| Campo | Detalle |
|---|---|
| Organismo | Infraestructura de Datos Espaciales de la Provincia de Buenos Aires (Subsecretaría de Gobierno Digital) |
| URLs | https://ideba.gba.gob.ar/geoservicios · visor de la ADA: https://ideba.gba.gob.ar/index.php/es/visualizador/autoridad-del-agua |
| Qué ofrece | Listado de servicios WMS y WFS de organismos provinciales. |
| Licencia / formato / fecha / cobertura | A confirmar capa por capa al descargar. |
| Limitaciones | Un WMS es solo una imagen; para reutilizar el dato hace falta WFS o descarga vectorial. |
| Fase 2 | El sitio responde desde el entorno (26/09/2026), pero la revisión de sus geoservicios no se completó. Queda pendiente (sección 5). |

### 1.3 Hidrografía oficial: IGN por WFS · **Verificada** · en uso (capa principal)

| Campo | Detalle |
|---|---|
| Organismo | Instituto Geográfico Nacional (IGN), servicio WFS de sus Capas SIG (0.2) |
| Capas del WFS | `ign:lineas_de_aguas_continentales_perenne`, `_intermitentes`, `_BH020` (canal) y `_BH030` (acequia, zanja, zanjón); `ign:areas_de_aguas_continentales_perenne` (espejo de agua perenne), `_intermitente`, `_BH020`, `_BH140` (corriente de agua como área) y `_BH130` (embalse). |
| Licencia | Términos y Condiciones del IGN (0.2). Cita: "FUENTE: Instituto Geográfico Nacional de la República Argentina". |
| Formato | GeoJSON del WFS, pedido con la caja del límite y recortado por el polígono (entra todo elemento con algún vértice dentro); coordenadas redondeadas a 5 decimales; se conservan nombre, tipo, fuente de captura y autoridad. |
| Fecha de los datos | **No informada**: el IGN no publicó metadatos de estas capas (0.2). Consulta al servicio: 26/09/2026. |
| Resultado | 138 elementos: 34 corrientes de agua perennes, 54 intermitentes, 6 acequias o zanjas, 43 espejos de agua perennes y 1 corriente de agua como área. Con nombre: río Quequén Grande, arroyos Quequén Chico, Calenqueyú, Diamante, Dulce, El Pescado Castigado, El Puente, La Reserva, Mendoza, Quelacinta, de Zavala y de las Ovejas, y lagunas La Dulce Grande, La Salada, Tupungato y del Carrizal, entre otros. |
| Limitaciones | Mucho menos detallada que la de OpenStreetMap (138 elementos frente a 2.279): no trae la mayoría de los cuerpos de agua chicos ni la línea de costa. El IGN no informa escala ni fecha. Representa dónde corre el agua, **no** dónde se inunda. |
| Archivo publicado | `docs/datos/hidrografia_ign.geojson`. Script: `scripts/descargar_ign.py`. |

### 1.4 Hidrografía detallada: OpenStreetMap · **Verificada** · complementaria

| Campo | Detalle |
|---|---|
| Organismo | Fundación OpenStreetMap y colaboradores |
| URL usada | API Overpass, https://overpass-api.de/api/interpreter. La consulta exacta queda en `datos/crudos/osm/hidrografia.overpassql` cada vez que corre `scripts/descargar_osm.py`. |
| Qué se consulta | `waterway=river`, `stream`, `canal`, `drain` y `ditch`; `natural=water`; `natural=coastline`. Dentro de la caja del límite (0.1), recortado después por el polígono: entra todo elemento con al menos un vértice dentro del partido. |
| Licencia | Open Database License (ODbL) 1.0. Texto en https://www.openstreetmap.org/copyright, leído el 26/09/2026: "OpenStreetMap is open data, licensed under the Open Data Commons Open Database License (ODbL) by the OpenStreetMap Foundation (OSMF)." Obliga a citar "© colaboradores de OpenStreetMap" y a publicar los derivados bajo ODbL. |
| Formato | Respuesta JSON de Overpass convertida a GeoJSON; coordenadas redondeadas a 5 decimales (alrededor de 1 m); solo se conservan las etiquetas que describen el elemento. |
| Fecha de los datos | Base de OpenStreetMap al 2026-09-26T17:21:54Z (campo `timestamp_osm_base` de la respuesta). |
| Resultado | 2.279 elementos con el límite del IGN (2.290 con el de Georef): 1.921 cuerpos de agua, 124 arroyos, 88 canales, 67 zanjas, 43 desagües, 19 tramos de río y 17 tramos de línea de costa. Otros 2.337 elementos de la caja quedaron fuera del partido. |
| Caja de la consulta | La consulta a Overpass se hizo con la caja del límite de Georef; la del IGN se extiende unos 19 m más al norte. Un nuevo intento de consulta (26/09/2026, tarde) fue cortado por Overpass, así que la base sigue siendo la de las 17:21 UTC. La diferencia de caja solo podría dejar afuera algún elemento contenido por completo en esa franja. |
| Limitaciones | Carga voluntaria, sin control oficial: la completitud en zona rural es desigual. Un río que cruza el límite se ve completo, incluso fuera del partido. |
| Archivo publicado | `docs/datos/hidrografia.geojson` (2,2 MB). |
| Decisión (26/09/2026) | Sebastián eligió la hidrografía oficial (1.3). Como la oficial resultó mucho menos detallada, esta capa queda como complementaria, apagada al abrir el mapa, hasta que Sebastián decida si se mantiene o se retira. |

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
- Subsecretaría de Recursos Hídricos de la provincia, informes "Estado hídrico" del 23/09/2026 (Sebastián aportó copias; comprobado en su texto): humedad del suelo a partir de imágenes SMAP de la NASA procesadas en Google Earth Engine (humedad superficial de 0 a 5 cm, resolución de 9 km aproximadamente, promedio de los 7 días anteriores, con una clasificación de "riesgo por saturación de humedad del suelo"), https://ada.gba.gov.ar/wp-content/uploads/2026/09/Presentacion_Estado_HumedadPBA-23-09-2026.pdf; y precipitación estimada con PERSIANN PDIR-Now (4 km, desarrollado por el CHRS de la Universidad de California, Irvine; disponible en https://irain.eng.uci.edu) para el período del 17/09 al 23/09/2026, https://ada.gba.gov.ar/wp-content/uploads/2026/09/Presentacion_Precipitacion-Persiann-PBA-23-09-2026.pdf. Son informes de coyuntura en PDF, sin licencia a la vista: van a la Metodología como enlace, no como capa. Los de humedad del suelo se publican en https://ada.gba.gov.ar/humedad-suelo/ (indicada por Sebastián el 26/09/2026; desde el entorno no abre); esa página, y no los PDF fechados, es la que se enlaza en la Metodología, en el apartado "Dónde seguir la situación actual".
- Mapas de disponibilidad estimada de recurso hídrico superficial y de uso de los acuíferos libre, pampeano y puelche (imágenes aportadas por Sebastián, sin fuente ni fecha a la vista): clasifican la disponibilidad del recurso en buena, condicionada o restringida. Miden disponibilidad para usos, no amenaza; como imágenes no se pueden convertir en capa sin digitalizar a ojo. **Inferido:** la disponibilidad restringida del acuífero libre en la franja costera de Necochea habla de salinización y abastecimiento, fuera de las tres amenazas del proyecto.
- Artículo académico sobre un modelo de anegamiento en el sudeste bonaerense, *GeoFocus*: https://www.geofocus.org/index.php/geofocus/article/view/262 (bibliografía; no es un dato abierto descargable, a confirmar).

### 1.7 Catálogo de datos abiertos de la provincia: capas del IGN republicadas · **Descartado: descargas truncadas**

| Campo | Detalle |
|---|---|
| Qué publica | Ferrocarril, red vial, curvas de nivel, cursos de agua y cuerpos de agua, con autoría del IGN y licencia CC BY 4.0 según los metadatos del catálogo (API CKAN, 26/09/2026): https://catalogo.datos.gba.gob.ar/dataset/ferroviario, /red-vial, /curvas-nivel, /cursos-agua y /cuerpos-agua. |
| Problema | El servidor corta las descargas: desde el entorno, en 31.610 bytes; desde la conexión de Sebastián, alrededor de 220.726 bytes (ver "Estado de la red"). Ningún ZIP llegó entero. Por las cabeceras de los archivos truncados se ve que no traen shapefile sino GeoJSON (ferrocarril y curvas) y KML (cursos de agua). |
| Lo que sí sirvió | Los PDF de documentación de la red vial y de las curvas de nivel llegaron completos (239.413 y 229.373 bytes, igual que lo declarado por el catálogo): sistema de referencia EPSG:4326, fuente IGN, "Fecha de fuente de documentación: 24 de octubre de 2021" y los dominios de los campos, que se usan en el mapa para traducir los códigos. |
| Decisión | Se usa la fuente original, el WFS del IGN (1.3, 1.8 y 3.4), que entrega lo mismo recortado a la zona y sin estos cortes. |

### 1.8 Curvas de nivel: IGN por WFS · **Verificada** · en uso (apagada al inicio)

| Campo | Detalle |
|---|---|
| Capa del WFS | `ign:lineas_de_geomorfologia_CA010` (en la página de Capas SIG figura como "Curva de nivel GeoPackage"). |
| Licencia | Términos y Condiciones del IGN (0.2). |
| Formato | GeoJSON del WFS, recortado como las demás capas del IGN. |
| Fecha de los datos | **No informada** por el servicio; la documentación que republica la provincia es del 24/10/2021 (1.7). |
| Resultado | 229 curvas con algún vértice dentro del partido (551 en la caja envolvente), con cotas de 10 a 300 m. Según el campo de fuente de captura, 136 vienen del "Atlas 500k 1° Ediciónl" (así, con esa errata) y 93 del "SIG 250 mil". |
| Limitaciones | Escala 1:500.000 y 1:250.000 según su fuente de captura: sirven para leer el relieve general, **no** para decidir si una calle o un lote se inunda. Los intervalos no son regulares (cada 10 m hasta 150 m y después 200, 250 y 300 m). En 93 curvas el método de obtención tiene código 6, que no figura en la documentación de la capa. Una curva que cruza el límite se ve completa. |
| Archivo publicado | `docs/datos/curvas_nivel.geojson` (0,97 MB). |

**Estado de la amenaza "Inundaciones":** la referencia (hidrografía oficial del IGN, hidrografía detallada de OSM y curvas de nivel) está verificada, pero **no hay un mapa oficial de peligrosidad hídrica para el partido**: la ADA todavía no elaboró la carta de riesgo hídrico de la cuenca del Quequén Grande (1.1). La capa de amenaza sigue **"pendiente de fuente"** hasta que se publique.

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
| Resultado en el partido | **MODIS: 654 focos** del 16/11/2000 al 12/11/2024 (637 de tipo 0 y 17 de tipo 2; 49 con confianza menor al 30 %). **VIIRS: 601 focos** del 10/02/2012 al 20/12/2024, todos de tipo 0 (495 de confianza nominal, 70 baja y 36 alta). Recortados con el límite del IGN (0.2); con el de Georef eran 658 y 600. Los focos por año quedan en `docs/datos/capas.json` y en la Metodología. |
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

https://www.smn.gob.ar/indices_peligro_fuego. Es un índice meteorológico diario, no un registro histórico. Se puede mencionar en la Metodología. Fase 2: desde el entorno, smn.gob.ar responde 403 de Cloudflare (protección contra bots); Sebastián confirmó el 26/09/2026 que esta página y https://www.smn.gob.ar/alertas abren. Las dos se enlazan en la Metodología, en "Dónde seguir la situación actual".

### 2.4 INTA, superficie quemada · **Sin fuente**

No se encontró un producto abierto del INTA con superficie quemada para el sudeste bonaerense. Queda pendiente de búsqueda manual.

**Estado de la amenaza "Incendios":** capa publicada con FIRMS (2.1), aclarando que muestra **focos de calor, no incendios**. La superficie quemada sigue **"pendiente de fuente"**.

---

## 3. Actividad portuaria e industrial

### 3.1 OpenStreetMap: puerto, silos y zonas industriales · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Qué se consulta | `landuse=industrial`, `landuse=port`, `industrial=port`, `harbour=*`, `man_made=silo`, `man_made=storage_tank`, `man_made=pier` y `man_made=breakwater`, en la caja del límite y recortado por el polígono. Consulta exacta en `datos/crudos/osm/portuaria.overpassql`. |
| Licencia, URL y formato | Igual que 1.4 (ODbL 1.0, misma lectura de la página de licencia). |
| Fecha de los datos | Base de OpenStreetMap al 2026-09-26T17:24:01Z. |
| Resultado: instalaciones | 643 elementos con el límite del IGN (646 con el de Georef) en `docs/datos/portuaria_instalaciones.geojson`: 572 silos (459 puntos y 113 polígonos), 40 tanques de almacenamiento, 16 zonas industriales (dos con rubro: `industrial=agriculture` e `industrial=gas`), 13 muelles, 1 escollera ("Escollera Norte") y 1 nodo `harbour=yes` ("Puerto Quequén"). **No hay ningún elemento `landuse=port` ni `industrial=port` dentro del partido.** La consulta usó la caja de Georef (ver 1.4). |
| Transporte (retirado) | Hasta el 26/09/2026 esta consulta traía también rutas y ferrocarril. En la base de OSM de ese día no había ninguna vía `railway=rail` dentro del partido (las 12 de la caja estaban en partidos vecinos) y las rutas eran 66 tramos troncales y primarios. Ferrocarril y rutas salen ahora del IGN (3.4). |
| Exclusiones | La consulta resta `man_made=surveillance`, `amenity=police`, `surveillance=*` y `surveillance:type=*`; el script vuelve a filtrar al procesar. Las respuestas crudas no trajeron ningún elemento excluido. |
| Limitaciones | Completitud desconocida y carga voluntaria. Los accesos de camiones no están etiquetados y **no se deducen**. La capa muestra **dónde están** las instalaciones, **no cuánto riesgo generan**: no hay datos abiertos sobre sustancias, volúmenes ni planes de contingencia. |
| Nota | Con qué etiqueta figura en OSM el ramal a Quequén queda como pregunta sin consecuencia para el mapa: el ferrocarril sale del IGN. |

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

### 3.4 Ferrocarril y rutas: IGN por WFS · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Capas del WFS | `ign:lineas_de_transporte_ferroviario_AN010` (ferrocarril), `ign:vial_nacional` y `ign:vial_provincial`. La red terciaria (`ign:vial_terciaria`, 797 tramos en la caja envolvente) queda afuera para que el mapa se pueda leer. |
| Licencia | Términos y Condiciones del IGN (0.2). |
| Fecha de los datos | Ferrocarril: **no informada** (sin metadatos, 0.2). Red vial: metadato creado el 24/10/2021, con actualización mensual declarada; el servicio no informa la fecha de la versión consultada. Consulta: 26/09/2026. |
| Resultado: ferrocarril | 6 tramos con algún vértice dentro del partido (ramales R18, R21, R23, R25 y R27 del Ferrocarril General Roca) y 8 estaciones: Claraz, Energía, Juan N. Fernández, La Dulce, La Negra, Quequén, Ramón Santamarina y San José. Fuente de captura: "IGN/Ministerio de Transporte de la Nación", con "/Ferrosur" en tres tramos. Cubre el hueco de OSM (3.1). |
| Resultado: rutas | 19 tramos: 6 de rutas nacionales y 13 de rutas provinciales (números 227, 228, 30, 72, 80, 85, 86 y 88); 16 pavimentados, 1 consolidado y 2 de tierra. Fuente de captura: Dirección Nacional de Vialidad y "DVP Buenos Aires". Los códigos se traducen con los dominios de la documentación de la capa (1.7). |
| Qué no representa | No indica si el ramal está en servicio ni qué transporta; no es un mapa de rutas de camiones ni de cargas peligrosas. |
| Archivos publicados | `docs/datos/ferrocarril.geojson` y `docs/datos/red_vial.geojson`. |

El catálogo provincial también publica "Unidades Penitenciarias" (IDEBA): **queda excluida** por la regla de infraestructura de seguridad. Y los centros de almacenamiento transitorio de envases de fitosanitarios (Ministerio de Ambiente, CC BY 4.0): **no se usan**, porque el CSV no trae coordenadas (solo direcciones) e incluye nombres, teléfonos y correos de personas.

**Estado de la amenaza "Portuaria e industrial":** capas publicadas: instalaciones (OpenStreetMap), ferrocarril y rutas (IGN). Muestran dónde están las instalaciones y la infraestructura de transporte, no cuánto riesgo generan. La zonificación sigue **"pendiente de fuente"**.

---

## 4. Exclusiones (no se incluyen en ninguna capa)

- Cámaras de videovigilancia y comisarías. El Centro Operativo de Monitoreo se publica como espacio físico (su sede es información pública, decisión de Sebastián del 26/09/2026); la ubicación de sus cámaras, nunca.
- Datos personales.
- En las capas del IGN no se incluyen instalaciones militares, edificios de seguridad, instituciones penitenciarias ni puestos de control. Los cuarteles de bomberos (voluntarios o no) y Defensa Civil **sí se publican**: son capacidad de respuesta, no infraestructura de seguridad (decisión de Sebastián, 26/09/2026, quien además confirmó que Defensa Civil no comparte ubicación con infraestructura excluida). En las estaciones de servicio se descartan los nombres, porque identifican a sus titulares.
- Cómo se aplica: las consultas a OpenStreetMap restan `man_made=surveillance`, `amenity=police`, `surveillance=*` y `surveillance:type=*`; el script de OSM vuelve a descartar esos elementos al procesar; `scripts/verificar.py` revisa tanto la respuesta cruda como el archivo publicado, y si encontrara alguno, la capa no se publica. De cada elemento solo se conservan etiquetas descriptivas (nombre, tipo, operador, referencia), nunca teléfonos, correos ni otros datos de contacto.

---

## 5. Pendientes y descargas manuales

**Dominios que usan los scripts** (tienen que estar habilitados en el "Network access" del entorno): `apis.datos.gob.ar`, `infra.datos.gob.ar`, `datosgobar.github.io`, `firms.modaps.eosdis.nasa.gov`, `overpass-api.de`, `wms.ign.gob.ar`, `www.ign.gob.ar`, `www.openstreetmap.org` y `www.earthdata.nasa.gov`. Si Overpass corta desde la nube, correr `scripts/descargar_osm.py` desde una computadora propia.

Pendientes:

1. **Hidrografía de OSM (1.4):** decidir si queda como capa complementaria o se retira.
2. **Indicadores del partido del IGN (sección 7): hecho** para DesInventar hidrometeorológico, IVSD y SINAGIR. Pendiente: la escala y la metodología del IVSD (informe de consultoría no publicado) y la documentación de DesInventar físico-químico.
3. **Defensa Civil (sección 9): hecho.** Sebastián corrigió en OpenStreetMap el punto de Defensa Civil (a partir de su conocimiento del lugar o de las imágenes del editor de OSM, nunca copiando de Google Maps). Después, correr `python3 scripts/descargar_osm.py respuesta`.
4. **ADA (1.1): hecho.** Sebastián revisó https://ada.gba.gov.ar/cartas-de-riesgo-hidrico/ el 26/09/2026: la carta de la cuenca del Quequén Grande no está hecha. Volver a mirar esa página en cada actualización.
5. **Red hidrométrica y freatímetros de la ADA (1.1 ter):** la capa se descarga en shapefile desde el visor, sin licencia. Si se quiere como capa, pedirle a la ADA el permiso de uso.
6. **IDEBA (1.2):** revisar si sus geoservicios publican por WFS, con licencia, las capas de cuencas, red hidrométrica o freatímetros de la ADA.
7. **Información naval (Armada Argentina):** siguiente etapa, pedida por Sebastián.
8. **FIRMS 2025 (2.1):** cuando FIRMS publique el resumen anual de 2025, volver a correr `python3 scripts/actualizar.py`.
9. **INTA (1.5 y 2.4) y SNMF (2.2):** sin cambios desde la Fase 1.

Si un sitio no deja descargar, cada archivo se puede bajar a mano y dejar en `datos/crudos/` para procesarlo con `python3 scripts/actualizar.py --offline` (instrucciones en el README).

---

## 6. Resumen por capa

| Capa | Fuente | Estado | En el mapa |
|---|---|---|---|
| Límite del partido | IGN (WFS), de origen catastral (ARBA) | Verificada, términos del IGN; fecha no informada | Publicada (32.136 vértices) |
| Localidades | IGN (WFS, BAHRA) | Verificada, términos del IGN | Publicada, apagada al inicio (6) |
| Inundaciones: peligrosidad | ADA | Sin fuente: la carta de riesgo hídrico del Quequén Grande no está hecha (confirmado a mano) | Pendiente de fuente |
| Inundaciones: hidrografía oficial | IGN (WFS) | Verificada, términos del IGN; fecha no informada | Publicada (138 elementos) |
| Inundaciones: hidrografía detallada | OpenStreetMap | Verificada, ODbL; base del 26/09/2026 | Publicada, apagada al inicio (2.279 elementos) |
| Inundaciones: curvas de nivel | IGN (WFS) | Verificada, términos del IGN; escala 1:500.000 y 1:250.000 | Publicada, apagada al inicio (229 curvas) |
| Inundaciones: pajonales, juncales y totorales | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (40) |
| Inundaciones: puentes y vados | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (16) |
| Incendios: focos de calor MODIS | NASA FIRMS | Verificada, CC0 con cita; 2000 a 2024 | Publicada (654 focos) |
| Incendios: focos de calor VIIRS S-NPP | NASA FIRMS | Verificada, CC0 con cita; 2012 a 2024 | Publicada (601 focos) |
| Incendios: forestaciones y bosques | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (47) |
| Incendios: superficie quemada | Ninguna | Sin fuente | Pendiente de fuente |
| Portuaria e industrial: instalaciones | OpenStreetMap | Verificada, ODbL; base del 26/09/2026 | Publicada (643 elementos) |
| Portuaria e industrial: puerto y navegación | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (9) |
| Portuaria e industrial: energía | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (11) |
| Portuaria e industrial: industria, combustibles y residuos | IGN (WFS) | Verificada, términos del IGN; sin nombres de titulares | Publicada, apagada al inicio (31) |
| Portuaria e industrial: ferrocarril | IGN (WFS) | Verificada, términos del IGN; fecha no informada | Publicada (6 tramos y 8 estaciones) |
| Portuaria e industrial: rutas nacionales y provinciales | IGN (WFS) | Verificada, términos del IGN; metadato de 2021, actualización mensual declarada | Publicada, apagada al inicio (19 tramos) |
| Portuaria e industrial: zonificación | Municipio | Sin fuente geográfica | Pendiente de fuente |
| Expuestos: planta urbana | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (7) |
| Expuestos: establecimientos educativos | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (140) |
| Expuestos: establecimientos de salud | IGN (WFS) | Verificada, términos del IGN | Publicada, apagada al inicio (22) |
| Respuesta: cuarteles de bomberos | OpenStreetMap | Verificada, ODbL; completa según Sebastián | Publicada, apagada al inicio (2) |
| Respuesta: Defensa Civil | OpenStreetMap (corregido el 26/09/2026) | Verificada, ODbL | Publicada, apagada al inicio (1) |
| Respuesta: Centro Operativo de Monitoreo | OpenStreetMap | Verificada, ODbL; sin cámaras | Publicada, apagada al inicio (1) |

---

## 7. Indicadores del partido en el IGN (espacio `ign_riesgo`) · **Verificados** · en la Metodología ("El partido en las estadísticas nacionales")

El WFS del IGN tiene un espacio `ign_riesgo` con 66 capas (https://wms.ign.gob.ar/geoserver/ign_riesgo/ows). Se usan tres, como indicadores del partido y no como capas del mapa. Script: `scripts/descargar_indicadores.py`; archivo publicado: `docs/datos/ficha_partido.json`.

| Indicador | Qué dice para Necochea | Documentación comprobada |
|---|---|---|
| DesInventar, amenazas hidrometeorológicas (`desinventar_hidrometeorologico_riesgo`) | 25 eventos entre 1970 y 2015: inundaciones (9), tormentas (9), sequía (3), vientos fuertes (2), tormentas de nieve (1) y granizo (1). Categoría del IGN: "Baja cantidad de registros DESINVENTAR". El script comprueba que la suma por tipo coincida con el total. | Metadato https://www.ign.gob.ar/capas-sig/metadata/desinventar_hidrometeorologico_riesgo.pdf (creado el 07/09/2022, actualización anual declarada): georreferencia la "Base de DESINVENTAR Sendai, por departamento, 1970-2015" (UNDRR, https://www.desinventar.net/); advierte textualmente que "La misma presenta subregistros, nos brinda un contexto aproximado"; las categorías salen de cortes naturales (Jenks) en cinco clases; define cada campo (`des_inun` inundaciones, `des_torm` tormentas, `des_viefue` vientos fuertes, `des_tormni` tormenta de nieve, `des_graniz` granizo, `des_sequia` sequía, entre otros). Licencia: "Libre uso de la información, cumpliendo con la cita adecuada del Instituto Geográfico Nacional". |
| IVSD 2024 por departamento (`ivsd_2024_depto`) | 30. Entre 511 departamentos del país: de 11,6 a 75,5, mediana 41,8; 52 con valor menor. Entre 134 partidos de la provincia: de 11,6 a 46,4, mediana 32,7; 32 con valor menor. | Metadato https://www.ign.gob.ar/capas-sig/metadata/ivsd_2024_depto.pdf: índice sintético del Proyecto ARG19003 (Plan Nacional de Adaptación al Cambio Climático, MAyDS) con indicadores actualizados al Censo 2022, en dimensiones demográfica, vivienda, servicios y conectividad, salud, educación, trabajo, ingresos y familia. **No publica la escala ni la metodología** (remite a un informe de consultoría). Licencia: "Libre uso de la información, cumpliendo con la cita adecuada de acuerdo a los créditos". **Inferido:** un valor más alto indica más vulnerabilidad (en la provincia, los extremos bajos son Vicente López y San Isidro; los altos, José C. Paz y Presidente Perón). |
| SINAGIR, niveles de exposición por región (`sinagir_amenazas_hidrometeorologicas_riesgo` y `_fisico_quimicas_riesgo`) | Región Centro: "Alto nivel de exposicion SINAGIR Centro" (hidrometeorológicas) y "Muy alto nivel de exposicion SINAGIR Centro" (físico-químicas). | Resumen del servicio: "sumatoria de niveles de exposición de amenazas ... por región, PNRRD". Escala regional: no distingue partidos. |

No se usan: DesInventar físico-químico (`desinventar_fisico_quimico_riesgo`), porque no tiene metadato publicado y sus códigos (`des_incend`, `des_estruc`, `des_sobret`) y su período no están documentados; y la superficie afectada por incendios de 2022 (`mayds_sup_afectada_2022`), porque es provincial.

---

## 8. Capas adicionales del IGN (26/09/2026) · **Verificadas** · en uso

Del inventario de las 192 capas del WFS del IGN se sumaron las que aportan a las tres amenazas o a los elementos expuestos. Todas: licencia según los términos del IGN (0.2), fecha no informada, formato GeoJSON del WFS recortado con el límite del partido (entra todo elemento con algún vértice dentro) y script `scripts/descargar_ign.py`.

| Capa del mapa | Capas del WFS | En el partido (en la caja) | Qué representa y qué no |
|---|---|---|---|
| Localidades | `localidad_bahra` | 6 (15) | Necochea-Quequén, Claraz, Energía, Juan N. Fernández, Nicanor Olivera y Ramón Santamarina. No indica población. |
| Pajonales, juncales y totorales | `vegetacion_hidrofila_ED020` | 40 (107) | Vegetación de suelos húmedos o anegados: indicio de terrenos bajos que retienen agua. No es un mapa de zonas inundables. |
| Puentes y vados | `puntos_de_cruces_y_enlaces_AQ040` y `_BH070` | 16 (40) | 14 puentes y 2 vados. Registro posiblemente incompleto (inferido). No indica su estado. |
| Forestaciones y bosques | `vegetacion_arborea_060301`, `_EC015` y `plantacion_permanente_KB025` | 47 (76) | 36 forestaciones, 7 bosques y 4 plantaciones: vegetación leñosa, combustible distinto del pastizal. No indica especie ni carga de combustible. |
| Puerto y navegación | `puntos_de_puertos_y_muelles_BB005`, rompeolas (`_BB041`), `ayuda_a_la_navegacion_BC050` y `_BC101`, `mareas_y_corrientes_BG020` | 9 (9) | Puerto Quequén, 4 rompeolas, faro Quequén, balizas de las escolleras norte y sur, y el mareógrafo de la estación Quequén (fuente de captura: IGN y Servicio de Hidrografía Naval). |
| Energía | `lineas_de_energia_AT030`, `puntos_de_energia_AD010` y `_AD030` (y `lineas_de_estructura_asociada_ducto_subterraneo`) | 11 (15) | 7 líneas de transmisión eléctrica, la Central Térmica Necochea, el Parque Eólico Necochea y las estaciones transformadoras Necochea y Quequén. El ducto General San Martín está en la caja pero fuera del partido. No indica tensión ni potencia (códigos sin dominio publicado). |
| Industria, combustibles y residuos | `areas_de_fabricacion_y_procesamiento_AC070` y `_AC507`, `puntos_de_fabricacion_y_procesamiento_AC000` y `_AC507`, `infraestructura_de_transporte_AQ170`, `areas_de_gestion_de_residuos_AB000` | 31 (53) | 3 fábricas, el Sector Industrial Planificado, 22 estaciones de servicio, el basural municipal y 4 elementos de las plantas depuradoras de Necochea y Quequén. No informa sustancias ni volúmenes. |
| Estaciones de ferrocarril | `puntos_de_transporte_ferroviario_AN070` | 8 (20) | Se suman a la capa de ferrocarril (3.4). |
| Planta urbana | `areas_de_asentamientos_y_edificios_020105` | 7 (16) | Área urbanizada de cada localidad (fuente de captura: IGN e INDEC). No distingue densidad ni población. |
| Establecimientos educativos | `puntos_de_ciencia_y_educacion_020601` y `_020602` | 140 (227) | 137 escuelas e institutos y 3 sedes universitarias (fuente de captura: Mapa Educativo Nacional, entre otras). No informa matrícula. |
| Establecimientos de salud | `salud_020801` | 22 (32) | Hospitales, salas y centros de salud (fuente de captura: SISA). No informa capacidad. |

Criterios aplicados:

- **Datos personales:** en las estaciones de servicio el nombre es el del titular (por ejemplo, "Apellido Nombre (Marca)"), así que se descarta. Los nombres de escuelas y centros de salud son de instituciones y se conservan.
- **Exclusiones:** no se incluyen `instalacion_militar_SU001`, `estructuras_operativas_y_defensivas_FA517` (edificio de seguridad), `_090101` (institución penitenciaria) ni `controles_AH070` (puesto de control). Los cuarteles de bomberos del IGN (`_090102`, 2 en el partido) no se usan porque son los mismos dos de OpenStreetMap; la capa sale de OSM (sección 9).
- **Sin datos en el partido:** barriales, salinas, sedimento fluvial, playas de arena, canales, alcantarillas, diques, embalses rurales, tanques de combustible, rellenos sanitarios y canteras dieron cero elementos en la caja.
- **No incluidas por ahora:** médanos (4 en la caja), arenales (3) y accidentes costeros (2), para la etapa costera y naval; aeródromos (11) y puntos acotados (119), por no aportar a las tres amenazas.

---

## 9. Capacidad de respuesta: bomberos, Defensa Civil y Centro Operativo de Monitoreo · **Verificada** · en uso

Decisiones de Sebastián (26/09/2026): se publican los cuarteles de bomberos, voluntarios o no, Defensa Civil y el Centro Operativo de Monitoreo como espacio físico, porque su sede es información pública. Sus cámaras no se publican nunca.

| Campo | Detalle |
|---|---|
| Consulta | OpenStreetMap vía Overpass: `amenity=fire_station` y elementos con nombre "Defensa Civil" o "Centro Operativo de Monitoreo", en la caja del límite y recortados por el polígono. Script: `scripts/descargar_osm.py` (se puede correr sola con `python3 scripts/descargar_osm.py respuesta`). |
| Fecha de los datos | Base de OpenStreetMap al 2026-09-26T23:42:00Z. |
| Licencia | ODbL 1.0 (1.4). |
| Bomberos | 2 cuarteles: "Estación de bomberos" (Necochea, `node/4090042291`) y "Bomberos Voluntarios de La Dulce" (`node/5871881594`). Coinciden con los dos del IGN (capa `estructuras_operativas_y_defensivas_090102`; el de Necochea declara como fuente de captura "OSM/Street View"). Del operador no se guarda nada: en el cuartel de Necochea figura un nombre que puede ser el de una persona. Según Sebastián (26/09/2026), son todos los cuarteles del partido. Archivo: `docs/datos/bomberos.geojson`. |
| Defensa Civil | OSM tiene un punto "Defensa Civil" (`node/4092470096`, `office=government`, sobre calle 56, junto a la Municipalidad). Según el municipio, sus instalaciones están "sobre avenida 10, casi Pinolandia" (https://necochea.gov.ar/se-realizara-una-jornada-de-prevencion-del-suicidio-este-sabado-en-defensa-civil/, 17/09/2026), y Sebastián indicó una ubicación a unos 3 km del punto de OSM. Además, el punto de OSM está a unos 15 m del de la Municipalidad de Necochea en el IGN (`puntos_de_asentamientos_y_edificios_020101`), y Sebastián confirmó que marca el Palacio Municipal, donde Defensa Civil no funciona desde hace muchos años. El punto está desactualizado: el script lo descarta mientras siga a menos de 100 m de su posición actual, y vuelve a entrar solo si se corrige en OSM. Historial del nodo (API de OSM, consultada el 26/09/2026): creado el 02/04/2016 en calle 56 N° 2945; en la versión 7 (26/09/2026, 19:25 UTC) Sebastián cambió la dirección a "Calle 10" N° 4500, pero la posición sigue siendo la de 2016. La dirección sola no se convierte en coordenadas: sería interpolar sobre la cuadra, es decir, estimar. **Resuelto:** en la versión 8 (26/09/2026, 20:30 UTC) Sebastián movió el nodo 2.907 m, hasta calle 10 N° 4500, a partir de su conocimiento del lugar. Con la base de Overpass de las 20:35 UTC, Defensa Civil se publica (`docs/datos/defensa_civil.geojson`). La entrada de exclusión se mantiene en el script para que una respuesta vieja de Overpass no reintroduzca la posición del Palacio Municipal. La dirección oficial no tiene número, así que no se convierte en coordenadas (sería estimar). La ubicación que indicó Sebastián salió de Google Maps y no se usa: sus condiciones no permiten copiar esos datos. |
| Centro Operativo de Monitoreo | `node/14220751253`, creado en OpenStreetMap el 26/09/2026 a las 23:40 UTC: nombre "Centro Operativo de Monitoreo", nombre oficial "Subsecretaría de Prevención y Monitoreo.", descripción "Multiagencia", dirección sobre avenida 58. No tiene etiqueta de tipo ni ninguna etiqueta de vigilancia o policía, así que los filtros de exclusión no lo afectan; la consulta lo busca por nombre. Archivo: `docs/datos/monitoreo.geojson`. |

