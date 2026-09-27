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

- Cámaras de videovigilancia, en ninguna capa y de ningún organismo. El Centro Operativo de Monitoreo se publica como espacio físico (su sede es información pública, decisión de Sebastián del 26/09/2026); la ubicación de sus cámaras, nunca.
- **Cambio del 27/09/2026 (decisión de Sebastián):** las comisarías dejan de excluirse. Todos los cuerpos que participan en la gestión del riesgo se publican juntos en la capa "Organismos de respuesta" (sección 9): sin saber dónde están, no hay gestión del riesgo posible, y la policía suele ser el primer contacto. Hasta ese día se excluían `amenity=police` y los edificios de seguridad del IGN; la Prefectura había entrado un rato antes como excepción por salvamento.
- Datos personales.
- En las capas del IGN no se incluyen instalaciones militares, instituciones penitenciarias ni puestos de control. Las estructuras operativas de policía, Prefectura y bomberos sí (sección 9). En las estaciones de servicio se descartan los nombres, porque identifican a sus titulares.
- Cómo se aplica: las consultas a OpenStreetMap restan `man_made=surveillance`, `surveillance=*` y `surveillance:type=*`; el script de OSM vuelve a descartar esos elementos al procesar (regla única en `comun.excluido_osm`); `scripts/verificar.py` revisa tanto la respuesta cruda como el archivo publicado, y si encontrara alguno, la capa no se publica. De cada elemento solo se conservan etiquetas descriptivas (nombre, tipo, referencia), nunca teléfonos, correos, operadores que puedan ser personas ni otros datos de contacto.

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
7. **Información naval (sección 11): pedidos enviados el 27/09/2026, sin respuesta todavía.** Sebastián envió tres correos al Servicio de Hidrografía Naval (ver 11.2). Si no hay respuesta, queda el pedido de acceso a la información pública (Ley 27.275) al Ministerio de Defensa; sus plazos se verifican antes de presentarlo.
7 bis. **Archivo de alertas del SMN (12.1):** se activa al mergear en `main` (las tareas programadas de GitHub solo corren en la rama principal). Después, revisar en la pestaña Actions que la primera corrida termine bien y que el commit automático llegue a Pages.
8. **Prefectura Naval (11.1):** Sebastián revisó https://www.argentina.gob.ar/prefecturanaval sin encontrar datos de interés; el recorrido del 27/09/2026 (60 páginas y la Memoria Anual 2025) tampoco: solo totales nacionales. Por decisión de Sebastián (27/09/2026) su sede se publica en la capa de respuesta, por su función de salvamento; falta traerla de OpenStreetMap cuando Overpass responda (`python3 scripts/descargar_osm.py respuesta`).
9. **SMN (sección 12):** revisar a mano la licencia en https://www.smn.gob.ar/descarga-de-datos (Cloudflare bloquea al entorno) y decidir si se arma un archivo propio de las alertas del SMN que alcanzan al partido.
10. **FIRMS 2025 (2.1):** cuando FIRMS publique el resumen anual de 2025, volver a correr `python3 scripts/actualizar.py`.
11. **INTA (1.5 y 2.4) y SNMF (2.2):** sin cambios desde la Fase 1.

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

No se usan: DesInventar físico-químico (`desinventar_fisico_quimico_riesgo`), porque no tiene metadato publicado y sus códigos (`des_incend`, `des_estruc`, `des_sobret`) y su período no están documentados. Inferido (27/09/2026), sin confirmación del IGN: los conteos coinciden con las fichas de la base argentina de DesInventar en Necochea, La Costa y General Pueyrredon, lo que sugiere `des_incend` = Incendio (FIRE), `des_estruc` = Colapso estructural (STRUCTURE) y `des_sobret` = Marejada (SURGE, no "sobretensión"); para Necochea darían 4 incendios, 5 colapsos estructurales y 1 marejada. Hasta que el IGN lo confirme, no se publica; y la superficie afectada por incendios de 2022 (`mayds_sup_afectada_2022`), porque es provincial.

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
| Energía | `lineas_de_energia_AT030`, `puntos_de_energia_AD010` y `_AD030` (y `lineas_de_estructura_asociada_ducto_subterraneo`) | 11 (15) | 7 líneas de transmisión eléctrica, la Central Térmica Necochea, el Parque Eólico Necochea y las estaciones transformadoras Necochea y Quequén. El ducto General San Martín está en la caja pero fuera del partido. Tensión y estado de las líneas: el metadato de la capa (https://www.ign.gob.ar/capas-sig/metadata/lineas_de_energia_AT030.pdf, leído el 27/09/2026) publica el dominio de `ten` y `fun`; las 7 líneas tienen `ten=6` ("Alta Tensión", más de 66 kV y hasta 220 kV) y `fun=6` ("Activo"). Corrige lo que decía esta fila hasta el 27/09/2026 ("códigos sin dominio publicado"). No indica potencia. |
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

## 9. Capacidad de respuesta: organismos de respuesta y lugares de refugio · **Verificada** · en uso

Desde el 27/09/2026 hay dos capas (decisión de Sebastián): **"Organismos de respuesta"**, con todos los cuerpos que intervienen en la gestión del riesgo y los siniestros, cada uno con su color, y **"Lugares de refugio"**. Las arma `scripts/armar_respuesta.py`. Respaldo de la idea en una fuente oficial: ante el temporal del 26/08/2021, el director de Defensa Civil destacó "el notable despliegue en conjunto" con "Bomberos de Necochea y Quequén, Guardaparques, personal de la Usina Popular Cooperativa, móviles de policía de comando y [...] voluntariado de la filial local de Cruz Roja Argentina" (https://necochea.gov.ar/arboles-y-postes-caidos-techos-volados-y-cuatro-auto-evacuados-por-los-fuertes-vientos/).

| Campo | Detalle |
|---|---|
| Organismos: Provincia de Buenos Aires | Ministerio de Seguridad, conjunto "Comisarías" de Datos Abiertos PBA: https://catalogo.datos.gba.gob.ar/es_AR/dataset/comisarias (indicado por Sebastián). CSV https://catalogo.datos.gba.gob.ar/dataset/bf79faeb-cb8a-4444-bbbe-5dc39479aa4a/resource/8d31bb16-3489-4ede-9e63-072f7f17383d/download/comisarias-pba-2026.csv, actualizado el 02/06/2026, 440 dependencias, bajado completo (54.713 bytes, igual que lo declarado). Licencia CC BY 4.0 (`"license_id": "CC-BY-4.0"` en la API del catálogo, leído el 27/09/2026). En el partido (código 6581): Comisaría Necochea 1° (sin coordenadas: solo dirección, no se convierte), Comisaría Necochea 2° y 3° y Subcomisaría J. Fernández. Se descartan teléfonos y direcciones. Comparación con el IGN: 2ª a 9 m, 3ª a 36 m; la Subcomisaría de Juan N. Fernández difiere en 482 m. La Provincia es la autoridad sobre sus comisarías (Sebastián, 27/09/2026), así que se usan sus posiciones, incluida la de Juan N. Fernández; la 1ª, sin coordenadas en la Provincia, sale del IGN. |
| Organismos: bomberos | Criterio de Sebastián (27/09/2026): los bomberos de la Policía de la Provincia deberían salir de la Provincia, y los voluntarios, del IGN. Al 27/09/2026 la Provincia no publica sus cuarteles: el catálogo solo tiene "Bomberos Voluntarios" (https://catalogo.datos.gba.gob.ar/es_AR/dataset/bomberos-voluntarios, CC BY 4.0, "Datos del Sistema Nacional de Bomberos Voluntarios en la provincia de Buenos Aires"; su CSV, https://catalogo.datos.gba.gob.ar/dataset/f3cf1025-b253-4627-b546-9c83457618f9/resource/9d601310-6bf9-4d82-b809-65fed2f3f63a/download/cuarteles-bomberos-082026.csv, se corta a los 31.656 de 155.641 bytes desde el entorno), y el conjunto de comisarías no incluye bomberos. Por eso el Cuartel de Bomberos Necochea sale del IGN, única fuente abierta que lo ubica, igual que los Bomberos Voluntarios de La Dulce. Si la Provincia publica sus cuarteles, pasan a tener prioridad. **Cuarteles del partido, según Sebastián (27/09/2026):** tres. Necochea y Quequén, de la Policía de la Provincia, y La Dulce (Nicanor Olivera), el único de bomberos voluntarios. **El de Quequén no figura en ninguna fuente abierta** (ni en el IGN, ni en la Provincia, ni en OpenStreetMap: Nominatim, 27/09/2026); lo respalda la nota municipal que nombra a los "Bomberos de Necochea y Quequén" (26/08/2021). **Resuelto el mismo día:** Sebastián lo cargó en OpenStreetMap, `node/14222511472` ("Bomberos Quequén", operador "Policía de la Provincia de Buenos Aires", 27/09/2026, 15:09 UTC), y está fijado en `datos/organismos_osm.json`. No se publican su teléfono ni su dirección. Corrige lo anotado el 26/09/2026 ("son todos los cuarteles del partido", sobre Necochea y La Dulce). |
| Organismos: Policía Federal | La planilla oficial de delegaciones de la PFA (https://www.argentina.gob.ar/seguridad/pfa/delegaciones, que lee una planilla pública de Google del Ministerio de Seguridad) ubica la Delegación Necochea en "Calle 67 nro. 1277"; no trae coordenadas. Se usa el punto del IGN ("Policía Federal Argentina Delegación Necochea", fuente de captura "OSM/Street View"), que Sebastián confirmó en el visor del IGN (27/09/2026); según él, OpenStreetMap la ubica enfrente. |
| Organismos: fijados en OSM | `datos/organismos_osm.json`: elementos cuya ubicación confirmó Sebastián, traídos de la API de OSM. Prefectura Naval Quequén, `way/698430678` (Sebastián, 27/09/2026: https://www.openstreetmap.org/#map=19/-38.574593/-58.703578), a unos 60 m del punto del IGN. Después Sebastián confirmó también el punto del IGN, que tiene prioridad sobre los fijados; el de OSM queda de respaldo. |
| Orden de prioridad | Provincia (autoridad sobre la policía bonaerense), IGN (lo federal, bomberos y lo que la Provincia no ubica), fijados en OSM, resto de OSM (decisiones de Sebastián, 27/09/2026; posiciones del IGN revisadas por él en el visor: https://mapa.ign.gob.ar/?zoom=14&lat=-38.5698&lng=-58.7245&layers=argenmap,estructuras_operativas_y_defensivas_FA517,estructuras_operativas_y_defensivas_090102). Un elemento se descarta si otro de mayor prioridad, del mismo organismo, está a menos de 200 m o tiene el mismo nombre (sin tildes ni ordinales). Con los datos del 27/09/2026: 11 organismos, 6 descartados por duplicados. |
| Organismos: IGN | WFS del IGN, capas `estructuras_operativas_y_defensivas_FA517` y `_090102` (términos del IGN, sección 8). En el partido, al 27/09/2026: Comisarías Necochea 1ª, 2ª y 3ª, Comisaría de la Mujer y la Familia Necochea, Subcomisaría J. N. Fernández, Policía Federal Argentina Delegación Necochea, Prefectura Naval Argentina Prefectura Quequén, Cuartel de Bomberos Necochea y Bomberos Voluntarios de La Dulce. El IGN no informa la fecha. Que estén todas las dependencias policiales del partido no está comprobado. |
| Organismos: OpenStreetMap | Consulta "respuesta" (Overpass, ODbL): Defensa Civil, Centro Operativo de Monitoreo, guardavidas (`emergency=lifeguard`, `office=lifeguard`), guardaparques (`amenity=ranger_station`), Cruz Roja (por nombre), y policía, Prefectura o bomberos. Un elemento de OSM del mismo organismo a menos de 200 m de uno del IGN se descarta (con la respuesta del 26/09/2026, los dos cuarteles de bomberos). Al 27/09/2026 no hay en OSM ni guardavidas, ni guardaparques, ni Cruz Roja (Nominatim no encuentra "Cruz Roja" en el partido). La filial sí existe: la página de filiales de Cruz Roja Argentina (https://www.cruzroja.org.ar/filiales/, consultada el 27/09/2026) la lista con la dirección "Calle 512 Nro 3030 (Filial) y Calle 57 2873 (Instituto Superior)", pero sin coordenadas propias: su mapa es de Google Maps, que no se usa, y una dirección no se convierte en coordenadas. Queda a la espera de que Sebastián cargue la filial en OpenStreetMap por conocimiento del lugar; después se fija su identificador en `datos/organismos_osm.json`. |
| Lugares de refugio | Lista en `datos/refugios.json`, indicada por Sebastián (27/09/2026): Polideportivo Municipal "Edgardo Hugo Yelpo" (`way/326255242`) y Parroquia Nuestra Señora de la Medalla Milagrosa (`way/1272959264`). Nombre y ubicación, de la API de OpenStreetMap (`api.openstreetmap.org`, que responde aunque Overpass corte). Según Sebastián (27/09/2026), Defensa Civil tiene un solo refugio designado para catástrofes: el Polideportivo. La parroquia es refugio para personas en situación de calle y no tiene relación con Defensa Civil (dato de Sebastián, 27/09/2026); la capa distingue los dos usos por color. En el sitio del municipio no se encontró una nota pública de la designación (búsqueda del 27/09/2026), así que el popup del Polideportivo dice de dónde sale el dato. |
| Símbolos | Los predios y edificios se publican como su punto central (centroide), para que cada organismo tenga un solo símbolo. |

Registro anterior (26 y 27/09/2026), cuando cada organismo tenía su capa:

Decisiones de Sebastián (26/09/2026): se publican los cuarteles de bomberos, voluntarios o no, Defensa Civil y el Centro Operativo de Monitoreo como espacio físico, porque su sede es información pública. Sus cámaras no se publican nunca.

| Campo | Detalle |
|---|---|
| Consulta | OpenStreetMap vía Overpass: `amenity=fire_station` y elementos con nombre "Defensa Civil" o "Centro Operativo de Monitoreo", en la caja del límite y recortados por el polígono. Script: `scripts/descargar_osm.py` (se puede correr sola con `python3 scripts/descargar_osm.py respuesta`). |
| Fecha de los datos | Base de OpenStreetMap al 2026-09-26T23:42:00Z. |
| Licencia | ODbL 1.0 (1.4). |
| Bomberos | 2 cuarteles: "Estación de bomberos" (Necochea, `node/4090042291`) y "Bomberos Voluntarios de La Dulce" (`node/5871881594`). Coinciden con los dos del IGN (capa `estructuras_operativas_y_defensivas_090102`; el de Necochea declara como fuente de captura "OSM/Street View"). Del operador no se guarda nada: en el cuartel de Necochea figura un nombre que puede ser el de una persona. Según Sebastián (26/09/2026), son todos los cuarteles del partido. Archivo: `docs/datos/bomberos.geojson`. |
| Defensa Civil | OSM tiene un punto "Defensa Civil" (`node/4092470096`, `office=government`, sobre calle 56, junto a la Municipalidad). Según el municipio, sus instalaciones están "sobre avenida 10, casi Pinolandia" (https://necochea.gov.ar/se-realizara-una-jornada-de-prevencion-del-suicidio-este-sabado-en-defensa-civil/, 17/09/2026), y Sebastián indicó una ubicación a unos 3 km del punto de OSM. Además, el punto de OSM está a unos 15 m del de la Municipalidad de Necochea en el IGN (`puntos_de_asentamientos_y_edificios_020101`), y Sebastián confirmó que marca el Palacio Municipal, donde Defensa Civil no funciona desde hace muchos años. El punto está desactualizado: el script lo descarta mientras siga a menos de 100 m de su posición actual, y vuelve a entrar solo si se corrige en OSM. Historial del nodo (API de OSM, consultada el 26/09/2026): creado el 02/04/2016 en calle 56 N° 2945; en la versión 7 (26/09/2026, 19:25 UTC) Sebastián cambió la dirección a "Calle 10" N° 4500, pero la posición sigue siendo la de 2016. La dirección sola no se convierte en coordenadas: sería interpolar sobre la cuadra, es decir, estimar. **Resuelto:** en la versión 8 (26/09/2026, 20:30 UTC) Sebastián movió el nodo 2.907 m, hasta calle 10 N° 4500, a partir de su conocimiento del lugar. Con la base de Overpass de las 20:35 UTC, Defensa Civil se publica (`docs/datos/defensa_civil.geojson`). La entrada de exclusión se mantiene en el script para que una respuesta vieja de Overpass no reintroduzca la posición del Palacio Municipal. La dirección oficial no tiene número, así que no se convierte en coordenadas (sería estimar). La ubicación que indicó Sebastián salió de Google Maps y no se usa: sus condiciones no permiten copiar esos datos. |
| Centro Operativo de Monitoreo | `node/14220751253`, creado en OpenStreetMap el 26/09/2026 a las 23:40 UTC: nombre "Centro Operativo de Monitoreo", nombre oficial "Subsecretaría de Prevención y Monitoreo.", descripción "Multiagencia", dirección sobre avenida 58. No tiene etiqueta de tipo ni ninguna etiqueta de vigilancia o policía, así que los filtros de exclusión no lo afectan; la consulta lo busca por nombre. Archivo: `docs/datos/monitoreo.geojson`. |
| Guardavidas | Capa preparada el 27/09/2026, pendiente de datos: OSM no tiene ningún elemento de guardavidas en el partido (consulta del agente, 27/09/2026). Sebastián los va a cargar por conocimiento local: puestos con `emergency=lifeguard` + `lifeguard=tower`, y la Jefatura de Guardavidas y Operativo en Playas (nombre oficial según el municipio, Secretaría de Gobierno) con `lifeguard=base` u `office=lifeguard`; todos con `seasonal=summer`, porque funcionan solo en verano, incluida la Jefatura. Etiquetas según la wiki de OSM (Tag:emergency=lifeguard, Key:lifeguard, Key:seasonal, leídas el 27/09/2026). Lista de puestos publicada por el municipio: https://necochea.gov.ar/se-amplio-el-servicio-de-guardavidas-con-mas-puestos-en-playa-y-sectores-del-rio/ (02/12/2025). No se cargan ni se publican datos de las personas que trabajan en el servicio. |
| Guardaparques | Capa preparada el 27/09/2026, pendiente de datos: OSM no tiene `amenity=ranger_station` en el partido. Se cargaría por conocimiento local. |
| Prefectura Naval | Desde el 27/09/2026 sale del IGN (`estructuras_operativas_y_defensivas_FA517.6076`). En OSM figura como `way/698430678`, "Prefectura Naval Quequén". |

---

## 10. Inventario local de eventos y vulnerabilidades · **Fuente propia, formulario abierto**

Decisión de Sebastián (27/09/2026): el proyecto arma su propio registro de eventos adversos y vulnerabilidades a partir de notas de medios locales, al estilo DesInventar, con carga de varios colaboradores.

| Campo | Detalle |
|---|---|
| Autoría | "Inventario local de eventos y vulnerabilidades del partido de Necochea", Juan Sebastián Bértole y colaboradores. |
| Licencia | Creative Commons Atribución 4.0 (CC BY 4.0). El formulario pide a quien carga que acepte esa licencia. |
| Herramienta de carga | KoboToolbox (https://kf.kobotoolbox.org, cuenta de Sebastián, plan gratuito según él). Comprobado en su documentación (https://support.kobotoolbox.org/viewing_validating_data.html, 26/09/2026): cada envío tiene estado de validación "Approved", "Not approved" u "On hold", y el formulario web puede aceptar envíos "without a username and password". |
| Exportación de Kobo | Comprobado en el código de KoboToolbox (repositorios kpi y formpack, leídos el 27/09/2026) y en su documentación (https://support.kobotoolbox.org/export_download.html): la columna es `_validation_status`; con "XML values and headers" vale `validation_status_approved`, y con etiquetas, `Approved` (fijo en inglés, sin traducción). El CSV usa punto y coma. El geopoint sale como "lat lon alt precisión" más columnas `_<nombre>_latitude` y `_<nombre>_longitude`. Sin probar todavía con una exportación real. |
| Datos de quien carga | En un formulario sin usuario, `_submitted_by` queda vacío y el formulario no pide datos personales. Comprobado en el código (kobo/apps/audit_log/models.py): el historial del proyecto guarda la IP y el navegador de cada envío, con una retención por defecto de 744 días (el valor real del servidor no se pudo comprobar). Ese historial no se exporta ni se publica, y el formulario lo avisa. |
| Revisión | Nada se publica sin estado "Approved". Sebastián verifica la nota de origen y que no haya datos personales; el script vuelve a validar al procesar la exportación. |
| Reglas | Nota enlazada obligatoria; sin nombres de personas ni domicilios particulares; ubicación por localidad o barrio, con punto exacto solo para lugares públicos que la nota nombre; una dirección no se convierte en coordenadas; no se copia el texto de las notas. |
| Clasificación | Tipos de evento y efectos de la "Guía Metodológica" de DesInventar, versión 8.1.9 (2009), en castellano: https://www.desinventar.org/docs/DesInventar-GuiaMetodologica-2.pdf (SHA-256 389e772f…, pp. 9 a 14 y 20 a 24). Se eligieron 21 tipos más "Otro", pertinentes para el partido; el valor interno es el código de la base argentina de DesInventar Sendai (https://www.desinventar.net/DesInventar/main.jsp?countrycode=arg&lang=ES), que usa el nombre en castellano con el código en inglés. Dos decisiones: (1) Incendio y Explosión siguen la definición castellana, que incluye causas humanas y tecnológicas (la versión Sendai en inglés los limita a los inducidos por fenómenos naturales); (2) la guía pide convertir familias a personas "según indicadores disponibles", pero eso sería estimar: las cifras por familias van en "Observaciones de efectos". "Afectados" tiene el sentido de la guía de 2009 (efectos indirectos), no el de "directly affected" de Sendai. La lista de vulnerabilidades es propia del proyecto. Todo en `datos/inventario/formulario.json`. |
| Exportaciones crudas | Van a `datos/crudos/inventario/`, que no se sube al repositorio: pueden contener envíos no aprobados. |
| Formulario y procesamiento | `scripts/generar_formulario.py` arma el XLSForm (`datos/inventario/formulario_inventario.xlsx`, convertido sin errores con pyxform, el mismo motor que usa KoboToolbox). `scripts/procesar_inventario.py` publica solo los aprobados que pasan los controles (campos, listas, fechas, enlace, cantidades, rastros de datos personales, punto dentro del partido, duplicados). Los registros sin punto se agrupan en el punto de su localidad (IGN). El título de la nota y el usuario de Kobo nunca se publican. |
| Formulario publicado | Desplegado por Sebastián el 27/09/2026 a las 01:21 UTC (proyecto `aD2nAa796eJ9xV2yCqiwXf`). Enlace público: https://ee.kobotoolbox.org/x/JsHKYrg5. Comprobado en la API de Kobo el mismo día: el formulario llegó completo (31 preguntas, 51 opciones) y el usuario anónimo tiene solo "Add submissions" y "View form"; los envíos no se leen sin sesión (404). |
| Estado | Formulario abierto a envíos; todavía no hay registros aprobados, así que la capa figura como "pendiente". |

### 12.1 Archivo propio de alertas del SMN (decisión de Sebastián, 27/09/2026)

- `scripts/archivar_alertas_smn.py` lee https://ssl.smn.gob.ar/CAP/AR.php, baja cada alerta o aviso vigente y guarda en `docs/datos/alertas_smn.json` los que alcanzan al partido: algún vértice del límite (uno de cada diez) dentro del polígono de la alerta, o algún vértice del polígono dentro del partido. Anota las localidades del IGN que quedan dentro. Guarda la severidad del estándar CAP y el titular del SMN; no deduce colores (las alertas no los informan en ningún campo; los avisos a corto plazo los traen en el titular).
- La tarea `.github/workflows/alertas-smn.yml` lo corre cada hora y hace un commit en `main` solo si entró una alerta nueva.
- Primera corrida (27/09/2026, 48 mensajes vigentes en el país): 3 mensajes alcanzan al partido, todos de un mismo episodio de lluvias (29/09/2026 de 9 a 15 h, severidad "Moderate"), que suman las seis localidades.
- Limitaciones: el archivo empieza el 27/09/2026; si una corrida falla, una alerta que dure menos de una hora se puede perder; los enlaces a los mensajes originales dejan de funcionar cuando el SMN los retira.

## 10 bis. Líneas de media tensión (Secretaría de Energía) · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Organismo | Secretaría de Energía de la Nación, con datos del Consejo Federal de la Energía Eléctrica (CFEE). |
| Conjunto | "Redes de distribución eléctrica del Consejo Federal", https://datos.gob.ar/dataset/redes-de-distribucion-electrica-del-consejo-federal. Recurso "Redes de distribución eléctrica de BUENOS AIRES (solo cooperativas) - CFEE - Líneas Media y Alta Tensión". |
| URL de descarga | http://datos.energia.gob.ar/dataset/ff99e7be-7bab-4617-9588-9a74ae046a40/resource/be371445-5d0a-4ad7-8346-f1cdfb89c66f/download/-buenos-aires-alta-tensin-media-tensin-lneas.zip (solo HTTP: el entorno no la alcanza; Sebastián la bajó a mano el 27/09/2026; SHA-256 4674d971f0d37658…). |
| Fecha | Recurso modificado el 30/05/2022 según datos.gob.ar; la fuente no informa la fecha del relevamiento. |
| Licencia | CC BY 4.0: `"license_id": "CC-BY-4.0"` en https://datos.gob.ar/api/3/action/package_show?id=redes-de-distribucion-electrica-del-consejo-federal (leído el 27/09/2026). |
| Formato | Shapefile de líneas, WGS 84; 225.185 tramos en la provincia. |
| Cobertura en el partido | 5.502 tramos (5.500 de 13,2 kV y 2 de 33 kV), alrededor de 1.850 km: las seis localidades y la zona rural. |
| Tendido | Desde el 27/09/2026 el mapa distingue el tendido aéreo (línea llena, 4.236 tramos) del subterráneo (punteada, 1.266 tramos), según el campo TIPO de la fuente. El tendido aéreo es el expuesto a caídas de postes y cables en temporales (pedido de Sebastián). |
| Limitaciones | Foto de 2022. El campo de cooperativa está vacío en casi todos los tramos del partido (inferido, sin confirmar: la red de Necochea y Quequén sería la de la Usina Popular Cooperativa). No incluye alta ni baja tensión. |

### 10 ter. Torres y postes de líneas eléctricas (OpenStreetMap) · **Verificada** · en uso

| Campo | Detalle |
|---|---|
| Fuente | OpenStreetMap vía Overpass, consulta "torres" de `scripts/descargar_osm.py` (líneas `power=line/minor_line/cable` y nodos `power=tower/pole`). ODbL 1.0. |
| Primera versión | Como Overpass corta desde el entorno, se usa la respuesta de Overpass que obtuvo el agente de energía el 27/09/2026 (base OSM de las 00:04 UTC), con una consulta más amplia que incluye estas mismas líneas y nodos (guardada en `datos/crudos/osm/torres_origen.overpassql`). La consulta propia la reemplaza cuando Overpass responda. |
| Cobertura en el partido | 1.475: 707 torres de 132 kV, 64 de 500 kV, 703 postes de la línea de 33 kV y 1 poste sin tensión informada. |
| Limitación principal | En OpenStreetMap no están cargados los postes de la red de 13,2 kV (la urbana y rural), ni los de telefonía o alumbrado: la capa no sirve para saber dónde hay postes en las ciudades. Para eso está el tendido aéreo de la capa de media tensión (10 bis). |

## 11. Información naval (Servicio de Hidrografía Naval) · **Identificada, sin licencia de reutilización** · no se usa como capa

Relevamiento del 27/09/2026, por HTTPS, desde el entorno. Los "datos de la Armada" están en el sitio del Servicio de Hidrografía Naval (SHN), https://www.hidro.gov.ar, que según su página institucional "tiene dependencia orgánica de la Subsecretaría de Investigación Científica y Política Industrial para la Defensa del Ministerio de Defensa". Los sitios de la Armada no publican datos.

**Condiciones de uso** (https://www.hidro.gov.ar/Institucional/Institucional.asp?op=6, apartado 6, leídas el 27/09/2026, citas textuales): "El Servicio de Hidrografía Naval retiene la propiedad de toda la información que suministra y el sólo hecho de copiar, vender, alquilar o distribuir copias o trabajos de cualquier clase de información a partir de este sitio, constituye un delito." y "A menos de contar con la autorización del Servicio de Hidrografía Naval, no se deberán establecer enlaces cuyo resultado sea la exhibición de una página o imagen del Servicio de Hidrografía Naval." El pie de todas las páginas, incluida "Datos Abiertos", dice "Todos los Derechos Reservados", y ninguna de sus fichas de metadatos declara licencia. Por eso no se descarga ni se redistribuye nada, y el sitio del mapa lo nombra sin enlazarlo hasta tener autorización.

| Fuente | URL | Qué aporta a Necochea | Uso |
|---|---|---|---|
| Datos Abiertos del SHN | https://www.hidro.gov.ar/DA/DatosAbiertos.asp | 9 conjuntos en HTML, sin licencia. | Ninguno por ahora. |
| Mareógrafo "Quequén" | https://www.hidro.gov.ar/Oceanografia/Mareografos.asp | Ficha: "Sitio 2 del Puerto Quequén", 38°34'31" S, 58°42'22" W. | Ya está en el mapa, desde el IGN (capa "Puerto y navegación"); las posiciones coinciden a 11,8 m. |
| Alturas horarias | https://www.hidro.gov.ar/Oceanografia/AlturasHorarias.asp | 11 mareógrafos, últimos 10 días. **Quequén no está.** | Vacío de información, anotado en la Metodología. |
| Tablas de marea de Puerto Quequén (H-610) | https://www.hidro.gov.ar/Oceanografia/Tmareas/Form_Tmareas.asp | Predicción astronómica 2022 a 2026 (no incluye el efecto del viento). | Solo con autorización. |
| Avisos y alertas de crecida, costa atlántica | https://www.hidro.gov.ar/oceanografia/ServiciosAACB.asp?op=2 (CAP 1.2: https://www.hidro.gob.ar/cap/CapCosta.asp) | Área: "Franja Costera de la Costa Atlántica Bonaerense desde la ciudad de Mar del Plata hasta San Clemente del Tuyú". Comprobado: el polígono del CAP no llega al partido (su extremo oeste está en 57,66° O; el partido empieza cerca de 58,4° O). | **Necochea queda fuera**: anotado en la Metodología. |
| Geoportal y GeoServer | https://geoportal.shn.gob.ar/ y https://wms.shn.gob.ar/geoserver/ows | En la zona: 46 curvas batimétricas, 6 tramos de línea de costa (solo conteo, sin bajar geometrías). | Capa posible (batimetría) solo con licencia por escrito. |
| Cartas náuticas y celdas ENC (AR402520 "Rada Quequén", AR502530 "Puerto Quequén") | https://www.hidro.gov.ar/nautica/CartasNauticas.asp?op=7 | Productos a la venta para navegar; Decreto 7.633/72, art. 5, remite a la Ley 11.723. | No se usan. |
| Informes del CEADO (Quequén 2005; niveles extremos 1994) | https://ceado.shn.gob.ar/explorar-datos/20/ | A pedido: ceado@hidro.gov.ar. | Bibliografía, si se obtienen. |
| PSMSL, estación 223 "QUEQUEN" | https://psmsl.org/data/obtaining/stations/223.php | Nivel medio mensual 1918 a 1982; la ficha avisa que en 1968 el mareógrafo se movió unos 340 m. | Sin licencia declarada: solo mención. |
| datos.gob.ar, organización SHN | https://datos.gob.ar/api/3/action/organization_show?id=servicio-de-hidrografia-naval | 0 conjuntos al 27/09/2026. | Volver a mirar en cada actualización. |

Sin comprobar: si el SHN considera que sus avisos valen también para Necochea (el texto habla de "la población costera de la Provincia de Buenos Aires (costa atlántica)", pero el área termina en Mar del Plata); el huso horario del CSV de alturas; la Prefectura Naval Argentina, que no se relevó.

### 11.2 Pedidos al SHN (enviados el 27/09/2026)

Enviados por Sebastián desde su cuenta de Outlook, sin otra dirección en la firma: las respuestas llegan ahí. Firmados como estudiante de la Licenciatura en Gestión de Riesgos y Siniestralidad del Instituto Universitario Vucetich. Las direcciones figuran en el sitio del SHN; la del CEADO, en https://ceado.shn.gob.ar/explorar-datos/20/ (ofuscada por Cloudflare y decodificada el 27/09/2026).

| Destinatario | Asunto | Qué se pidió | Estado |
|---|---|---|---|
| shn@hidro.gov.ar | Consulta sobre la licencia de uso de datos del SHN para un mapa de riesgos de Necochea | (a) Licencia de los conjuntos de "Datos Abiertos" y de las capas WFS (curvas batimétricas y línea de costa frente a Necochea); si autorizan reutilizarlas con cita, por ejemplo bajo CC BY 4.0. (b) Si autorizan enlaces simples, sin incrustar, a páginas del SHN. | Sin respuesta |
| pronomarea@hidro.gov.ar | Consulta sobre el mareógrafo de Puerto Quequén y la cobertura de los avisos de crecida | (a) Si existe una serie de alturas del mareógrafo "Quequén" (Sitio 2 del Puerto Quequén) y en qué condiciones se entrega. (b) Si los avisos de crecida, cuya área es "Franja Costera de la Costa Atlántica Bonaerense desde la ciudad de Mar del Plata hasta San Clemente del Tuyú", comprenden la costa de Necochea y Quequén, o si otro producto la cubre. | Sin respuesta |
| ceado@hidro.gov.ar | Solicitud de informes técnicos sobre Puerto Quequén | Copia y condiciones de uso de "Mediciones de parámetros oceanográficos en puerto Quequén, provincia de Buenos Aires, 2005" y "Niveles extremos de marea observados en la provincia de Buenos Aires, 1994". | Sin respuesta |

Cuando llegue una respuesta, anotar acá la fecha y lo que autoriza. Hasta entonces, ningún dato del SHN se usa en el mapa.

### 11.1 Prefectura Naval Argentina (27/09/2026)

Comprobado en https://www.argentina.gob.ar/prefecturanaval/ambitos-actuacion-despliegue-geografico: la Prefectura Quequén integra la Prefectura de Zona Mar Argentino Norte ("las Prefecturas de Mar del Plata, Quequén, Bahía Blanca, ..."), y la Prefectura actúa, entre otros ámbitos, "en las costas y playas marítimas y fluviales". Es la autoridad de la navegación en el puerto y la costa del partido.

- datos.gob.ar no tiene ninguna organización ni conjunto de la Prefectura (búsquedas "prefectura", "naufragio", "salvamento", "Quequén": 0 resultados).
- https://www.prefecturanaval.gob.ar/ devuelve 504 al entorno; https://prefecturanaval.gob.ar/ (sin www) es el acceso al correo institucional, no un sitio de datos. Sin rodeos: Sebastián revisa a mano si el sitio publica, para Quequén, el estado del puerto (cierres por mal tiempo), avisos a los navegantes o partes meteorológicos, y bajo qué condiciones de uso.
- El conjunto "Puertos" de la Secretaría de Transporte (https://datos.transporte.gob.ar/dataset/puertos, licencia "Other (Open)", relevamiento 2019) se sirve desde ide.transporte.gob.ar, cuyo certificado no valida desde el entorno; no se forzó. El puerto ya está en el mapa por el IGN y OpenStreetMap.
- El conjunto de entrada y salida de buques de la Secretaría de Transporte (CC BY 4.0) es solo del Puerto Buenos Aires: no sirve para Quequén.

## 12. Servicio Meteorológico Nacional (SMN) · **Alertas: verificadas, archivo propio desde el 27/09/2026** · datos de estaciones: no se usan

Relevamiento del 27/09/2026, por HTTPS, desde el entorno.

- **Licencia general del SMN (comprobada):** "Términos y condiciones de uso" (PDF "SMN_PAD_legales.pdf", año 2018, provisto por Sebastián el 27/09/2026 desde smn.gob.ar): "El SMN licencia todos sus contenidos bajo la licencia Creative Commons Atribución 2.5 Argentina, cuyo texto legal puede encontrarse en http://creativecommons.org/licenses/by/2.5/ar/legalcode." El canal de alertas declara CC BY 4.0 (abajo). Las dos permiten reutilizar citando al SMN.
- **www.smn.gob.ar no responde al entorno:** Cloudflare devuelve "Sorry, you have been blocked" (403) en la portada, en https://www.smn.gob.ar/descarga-de-datos y en los términos. Sin rodeos: Sebastián tiene que revisar a mano en esas páginas la licencia de los datos descargables.
- **Alertas en formato CAP 1.2:** https://ssl.smn.gob.ar/CAP/AR.php. El canal declara textualmente: "Copyright 2025 SMN | Derechos de autor, Servicio Meteorologico Nacional (SMN). Licencia CC BY 4.0." Cada alerta trae evento, severidad, certeza, vigencia (onset y expires), descripción, instrucciones y el polígono del área. Comprobado: el 27/09/2026 a las 00:48 UTC había 49 alertas vigentes, y 3 de ellas (lluvias, del 29/09 de 9 a 15 h, "precipitación acumulada entre 30 y 50 mm") abarcaban el partido. A diferencia de las del SHN (sección 11), las alertas del SMN sí cubren Necochea. Limitaciones: el canal solo muestra las vigentes (no hay archivo histórico en él) y no envía encabezados CORS, así que el sitio no lo puede leer desde el navegador.
- **Datos de estaciones** (datos.gob.ar, organización "servicio-meteorologico-nacional", 7 conjuntos: estaciones, datos horarios, temperaturas extremas, registro de 365 días, radiación solar, tiempo presente y pronóstico a 5 días; descarga en https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=...): el campo de licencia está vacío en los 7 ("isopen": false). Además, **ninguna estación del SMN está en el partido**: las más cercanas son Mar del Plata Aero (124 km del centro de Necochea), Benito Juárez Aero (131 km) y Tres Arroyos (136 km), según el listado de estaciones (https://ssl.smn.gob.ar/dpd/zipopendata.php?dato=estaciones). Sus series describen otros lugares, no el partido. El pronóstico a 5 días bajó vacío (0 bytes) el 27/09/2026.
