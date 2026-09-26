# Relevamiento de fuentes de datos abiertos

Mapa interactivo de riesgos del partido de Necochea (provincia de Buenos Aires, Argentina).
Fase 1, relevamiento hecho el 26/09/2026.

## Cómo leer este documento

Cada fuente lleva uno de estos estados:

- **Verificada**: se descargó el dato, se abrió y se confirmaron fecha, licencia, formato y cobertura contra la fuente original.
- **Identificada**: la fuente existe según su propio sitio o documentación oficial encontrada con el buscador, pero **no se descargó ni se abrió el dato**. Fecha, cobertura y a veces licencia quedan por confirmar.
- **Sin fuente**: no se encontró un dato abierto que cubra la necesidad.

**Al cierre de la Fase 1 ninguna fuente está verificada.** El entorno de trabajo en la nube bloquea la conexión a todos los sitios de datos (se probó el 26/09/2026: IGN, IDERA, IDEBA, Autoridad del Agua, INTA, NASA FIRMS, OpenStreetMap, Overpass, Geofabrik, datos.gob.ar, argentina.gob.ar, Municipalidad de Necochea y Puerto Quequén devolvieron conexión rechazada por el proxy). Solo se pudo usar un buscador web. Por eso cada fuente trae la URL para descargarla a mano, y los campos que dependen de abrir el dato dicen **"a confirmar al descargar"**.

Regla del proyecto: ninguna capa se completa con datos inventados, estimados ni simulados. Una capa sin datos verificados se muestra en el mapa como **"pendiente de fuente"**.

---

## 0. Referencia: límite del partido de Necochea

### 0.1 Georef (Servicio de Normalización de Datos Geográficos de Argentina) · **Identificada** · recomendada

| Campo | Detalle |
|---|---|
| Organismo | Secretaría de Innovación Pública, Presidencia de la Nación (datos.gob.ar). Las geometrías provienen del IGN. |
| URL de la API | https://apis.datos.gob.ar/georef/ |
| URL de descarga completa | https://datosgobar.github.io/georef-ar-api/download/ (enlaza a los archivos en infra.datos.gob.ar) |
| Licencia | Creative Commons Atribución 4.0 Internacional (CC BY 4.0), según las condiciones de uso publicadas: https://datosgobar.github.io/georef-ar-api/terms/ y https://www.argentina.gob.ar/georef/condiciones-de-uso-y-licencia |
| Formato | CSV, JSON, GeoJSON y NDJSON. La entidad "departamentos" incluye geometría MultiPolygon; en Buenos Aires, los departamentos son los partidos. |
| Fecha de los datos | A confirmar al descargar. |
| Cobertura | Nacional. |
| Limitaciones | Límite administrativo, no catastral. Su precisión depende de la capa de origen del IGN. |
| Descarga manual | El archivo completo de departamentos en GeoJSON desde la página de descarga, filtrando "Necochea". Consulta alternativa por API, **sintaxis a confirmar**: `https://apis.datos.gob.ar/georef/api/departamentos?provincia=06&nombre=necochea&formato=geojson&max=1`. |

### 0.2 IGN, capa "Departamentos" · **Identificada** · alternativa

| Campo | Detalle |
|---|---|
| Organismo | Instituto Geográfico Nacional (IGN) |
| URL | https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG |
| Licencia | **No confirmada.** La documentación del IGN describe la licencia como "libre según Freedom Defined", pero no se pudo leer el texto exacto. Georef, que usa estas geometrías, las publica bajo CC BY 4.0. |
| Formato | SHP, KML, GeoJSON; también WMS y WFS (https://www.ign.gob.ar/geoservicios). |
| Fecha / cobertura | A confirmar al descargar. Nacional. |
| Limitaciones | Igual que Georef. |

**Decisión propuesta:** usar Georef (0.1) por tener licencia explícita, y citar al IGN como origen de la geometría.

---

## 1. Inundaciones y anegamientos

### 1.1 Autoridad del Agua (ADA), mapas de peligrosidad hídrica · **Sin fuente para Necochea (a confirmar)**

| Campo | Detalle |
|---|---|
| Organismo | Autoridad del Agua, Subsecretaría de Recursos Hídricos, provincia de Buenos Aires |
| URLs | https://riesgohidrico.ada.gba.gov.ar/mapas-de-peligrosidad-por-cuencas/ · https://ada.gba.gov.ar/cartas-de-riesgo-hidrico/ |
| Qué se sabe | Los mapas de peligrosidad usan cuatro categorías (muy alta, alta, media, baja o nula). Las cuencas publicadas según el buscador son del conurbano y el Gran La Plata: Reconquista, Luján, La Plata, San Francisco, Las Piedras, Sarandí y Santo Domingo. **No apareció ninguna para el río Quequén Grande ni para Necochea.** |
| Licencia / formato / fecha | A confirmar. No se encontró licencia explícita. |
| Limitaciones | Si no hay mapa para la cuenca, esta es la fuente oficial que falta, no una que se pueda reemplazar. |
| Acción manual | Revisar las dos URLs y el visor de IDEBA (1.2) para confirmar si existe cartografía de la cuenca del Quequén Grande. |

Contexto institucional verificado en el sitio de la ADA (vía buscador): el Comité de Cuenca Hídrica del Río Quequén Grande se creó el 05/07/2002 por Resolución 004/02 e integra a Necochea, Lobería, Tandil, Adolfo Gonzales Chaves, Benito Juárez y San Cayetano (https://ada.gba.gov.ar/listado-de-los-comites-de-cuencas/).

### 1.2 IDEBA, geoservicios provinciales (incluida la ADA) · **Identificada**

| Campo | Detalle |
|---|---|
| Organismo | Infraestructura de Datos Espaciales de la Provincia de Buenos Aires (Subsecretaría de Gobierno Digital) |
| URLs | https://ideba.gba.gob.ar/geoservicios · visor de la ADA: https://ideba.gba.gob.ar/index.php/es/visualizador/autoridad-del-agua |
| Qué ofrece | Listado de servicios WMS y WFS de organismos provinciales. |
| Licencia / formato / fecha / cobertura | A confirmar capa por capa al descargar. |
| Limitaciones | Un WMS es solo una imagen; para reutilizar el dato hace falta WFS o descarga vectorial. |

### 1.3 Hidrografía: IGN (cursos y cuerpos de agua, línea de costa) · **Identificada**

| Campo | Detalle |
|---|---|
| Organismo | Instituto Geográfico Nacional |
| URL | https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG (clase Hidrografía y oceanografía) |
| Licencia | No confirmada (ver 0.2). |
| Formato | SHP, KML, GeoJSON; WMS y WFS. |
| Fecha / cobertura | A confirmar. Nacional. |
| Limitaciones | Representa dónde corre el agua, **no** dónde se inunda. Sirve de referencia, no de amenaza. |

### 1.4 Hidrografía: OpenStreetMap (`waterway=*`, `natural=water`, `natural=coastline`) · **Identificada**

| Campo | Detalle |
|---|---|
| Organismo | Fundación OpenStreetMap y colaboradores |
| URLs | Consulta por Overpass: https://overpass-api.de/api/interpreter · extracto de Argentina: https://download.geofabrik.de/south-america/argentina.html |
| Licencia | Open Database License (ODbL) 1.0. Obliga a citar "© colaboradores de OpenStreetMap" con enlace a https://www.openstreetmap.org/copyright y a publicar los derivados bajo ODbL (https://osmfoundation.org/wiki/Licence/Attribution_Guidelines). |
| Formato | Overpass devuelve JSON u OSM XML; se convierte a GeoJSON. |
| Fecha | La fecha de la consulta. Debe registrarse en cada actualización. |
| Limitaciones | Carga voluntaria: la completitud en zona rural es desigual y no tiene control oficial. |

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

**Estado de la amenaza "Inundaciones":** hay datos de referencia (hidrografía y costa), pero **no se encontró un mapa oficial de peligrosidad hídrica para el partido.** Salvo que la ADA o IDEBA lo tengan, la capa de amenaza propiamente dicha queda **"pendiente de fuente"**.

---

## 2. Incendios de pastizal y rurales

### 2.1 NASA FIRMS, focos de calor MODIS y VIIRS · **Identificada** · recomendada

| Campo | Detalle |
|---|---|
| Organismo | NASA, LANCE / FIRMS (Fire Information for Resource Management System) |
| URLs | Descarga de archivo histórico: https://firms.modaps.eosdis.nasa.gov/download/; ahí se ofrecen resúmenes anuales por país en CSV (por ejemplo `modis_2020_Argentina.csv`) · API (requiere MAP_KEY gratuita): https://firms.modaps.eosdis.nasa.gov/api/ · léame y aviso legal: https://firms.modaps.eosdis.nasa.gov/download/Readme.txt |
| Cobertura temporal | MODIS C6.1 desde noviembre de 2000; VIIRS 375 m S-NPP desde el 20/01/2012; NOAA-20 desde el 01/04/2018; NOAA-21 desde el 17/01/2024 (según la documentación de disponibilidad de FIRMS). |
| Licencia | Según FIRMS, "no hay restricciones de uso" y se pide citar los datos. Según la guía de NASA Earthdata, los datos de misiones de la NASA sin otra marca se publican como CC0 (https://www.earthdata.nasa.gov/learn/use-data/data-citations-acknowledgements). Si se redistribuyen, hay que citar y enlazar el aviso legal. |
| Formato | CSV (resúmenes por país y año), SHP, KML; JSON y CSV por API. |
| Cobertura espacial | Global; se recorta al polígono del partido (0.1) con un script. |
| Limitaciones | Un foco de calor es una **anomalía térmica detectada por satélite**, no un incendio confirmado: incluye quemas agrícolas autorizadas, fuentes industriales y falsos positivos. No mide superficie quemada. La resolución (1 km MODIS, 375 m VIIRS) y la nubosidad provocan omisiones. **Hay que decirlo en la Metodología.** |

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

**Estado de la amenaza "Incendios":** la capa es viable con FIRMS (2.1), siempre que quede claro que muestra **focos de calor, no incendios**.

---

## 3. Actividad portuaria e industrial

### 3.1 OpenStreetMap: puerto, silos, zonas industriales, ferrocarril y rutas · **Identificada** · recomendada

| Campo | Detalle |
|---|---|
| Etiquetas previstas | `landuse=industrial`, `landuse=port`, `industrial=port`, `harbour=*`, `man_made=silo`, `man_made=storage_tank`, `man_made=pier`, `man_made=breakwater`, `railway=rail`, `highway=trunk/primary` y accesos al puerto, más `hgv=designated` donde esté cargado |
| Licencia, URLs y formato | Igual que 1.4 (ODbL). |
| Limitaciones | Completitud desconocida hasta consultar. Los accesos de camiones rara vez están etiquetados como tales; si no figuran, **no se deducen**: se muestra la red vial sin afirmar que sea ruta de camiones. |

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

**Estado de la amenaza "Portuaria e industrial":** viable con OpenStreetMap para ubicar la infraestructura. La capa muestra **dónde están** las instalaciones, **no cuánto riesgo generan**: no hay datos abiertos sobre sustancias, volúmenes ni planes de contingencia.

---

## 4. Exclusiones (no se incluyen en ninguna capa)

- Cámaras de videovigilancia y cualquier infraestructura de seguridad (comisarías, centros de monitoreo, etcétera).
- Datos personales.
- De las consultas a OpenStreetMap se filtran de forma explícita etiquetas como `man_made=surveillance` y `amenity=police`, aunque aparezcan dentro del área consultada.

---

## 5. Descargas pendientes (para hacer a mano o habilitando la red)

Hay dos caminos:

**A. Habilitar dominios en el entorno** (Configuración del entorno, "Network access"): `apis.datos.gob.ar`, `infra.datos.gob.ar`, `www.ign.gob.ar`, `firms.modaps.eosdis.nasa.gov`, `overpass-api.de`, `ideba.gba.gob.ar`, `riesgohidrico.ada.gba.gov.ar`, `ada.gba.gov.ar`. Con eso los scripts de `/scripts` descargan y verifican solos.

**B. Descarga manual** y subida a `datos/crudos/`:

1. Límite del partido: el GeoJSON de departamentos desde https://datosgobar.github.io/georef-ar-api/download/, filtrado a Necochea → guardar como `datos/crudos/limite_necochea_georef.geojson`.
2. Focos de calor: desde https://firms.modaps.eosdis.nasa.gov/download/ (sección de resúmenes anuales por país), los CSV anuales de Argentina de MODIS y VIIRS (S-NPP), por ejemplo de 2012 a 2025 → `datos/crudos/firms/`.
3. Revisar https://riesgohidrico.ada.gba.gov.ar/mapas-de-peligrosidad-por-cuencas/ y https://ideba.gba.gob.ar/geoservicios, buscar "Quequén" y anotar si existe algo.
4. Revisar en https://www.ign.gob.ar/NuestrasActividades/InformacionGeoespacial/CapasSIG el texto exacto de la licencia y copiarlo.
5. OpenStreetMap: se resuelve con un script de Overpass apenas se habilite `overpass-api.de`. Hacerlo a mano no conviene.

---

## 6. Resumen por capa

| Capa | Fuente propuesta | Estado | En el mapa |
|---|---|---|---|
| Límite del partido | Georef (IGN) | Identificada, CC BY 4.0 | Viable |
| Inundaciones: peligrosidad | ADA / IDEBA | Sin fuente para Necochea | Pendiente de fuente |
| Inundaciones: hidrografía y costa | OSM (ODbL); IGN como alternativa | Identificada | Viable como referencia |
| Incendios: focos de calor | NASA FIRMS | Identificada, uso libre con cita | Viable |
| Incendios: superficie quemada | Ninguna | Sin fuente | Pendiente de fuente |
| Portuaria e industrial: infraestructura | OSM (ODbL) | Identificada | Viable |
| Portuaria e industrial: zonificación | Municipio | Sin fuente geográfica | Pendiente de fuente |
