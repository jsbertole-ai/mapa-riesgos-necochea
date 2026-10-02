# Mapa para la gestión del riesgo del partido de Necochea

Mapa para la gestión del riesgo del partido de Necochea (provincia de Buenos Aires, Argentina; nombre decidido por Sebastián el 28/09/2026, porque según Lavell, 2007, p. 37, un "mapa de riesgos" marca probabilidades y este no lo hace), hecho solo con datos abiertos y publicado como sitio estático en GitHub Pages. Es una pieza de divulgación, en construcción y colectiva (decisión de Sebastián, 27/09/2026: el mapa no es de una persona, se arma entre quienes aportan datos). Lo empezó Juan Sebastián Bértole, estudiante de la Licenciatura en Gestión de Riesgos y Siniestralidad (Instituto Universitario Vucetich). Importa más el rigor de las fuentes que la cantidad de capas.

## Reglas que no se negocian

- **Nunca inventar, estimar ni simular datos** para completar una capa. Una capa sin datos verificados se muestra como "pendiente de fuente".
- Cada fuente se registra en `DATOS.md` con: organismo, URL exacta, fecha de los datos, licencia, formato, cobertura y limitaciones. Estado: verificada, identificada o sin fuente.
- Si el entorno no deja descargar un sitio, no se buscan rodeos: se anota la URL en `DATOS.md` para que Sebastián la descargue a mano.
- **Exclusiones:** no se publican datos personales.
- La base conceptual y metodológica está en `MARCO_CONCEPTUAL.md` (decisión de Sebastián, 27/09/2026). Cada cita se verifica contra el texto original, con su página; lo que es lectura propia se marca como "Para el mapa".
- **Inventario local** (decisiones de Sebastián, 28/09/2026): abarca los eventos desde el 1/1/1980. Cada evento que alguien cargue en el formulario, o que arme el proyecto desde el archivo de prensa, se pondera antes de publicarse: abrir la nota y comprobar que dice lo que dice el registro (fecha, lugar, cifras), revisar el período, que no haya datos personales, que el tipo siga la guía de DesInventar, que no repita un registro ya cargado y que el punto esté bien puesto. **Ubicación** (decisión de Sebastián, 28/09/2026): cuando la nota remite a un lugar específico, se lo georreferencia. Un lugar público con nombre (puente, escuela, hospital, balneario, club, plaza) se toma de una capa verificada o de OpenStreetMap; una esquina o un tramo de calle, del cruce o del tramo de las calles en OpenStreetMap. Si el lugar es una vivienda particular, se publica. **Sin distancias en las ventanas** (decisión de Sebastián, 28/09/2026): nunca se escribe que un punto "queda a tantos metros" del templo, de la esquina o de otra referencia, porque se lee como un error y el mapa sirve justamente para ubicar el lugar sin una dirección. Una parroquia no es solo el templo: incluye el salón, las duchas, el comedor y los demás espacios, y el punto que marca el colaborador es el del lugar donde funciona el servicio. Después se le presenta a Sebastián con una recomendación (aprobar, corregir o descartar, con el motivo) y **nada se publica sin su aprobación**.
- **Capa de sustancias peligrosas** (decisión de Sebastián, 28/09/2026): la regla de ubicación del inventario se amplía a esta capa. Los establecimientos que figuren en un listado oficial (agroquímicos, residuos especiales, combustibles, terminales, etc.) se georreferencian uno por uno a partir de su dirección, tomando el punto de OpenStreetMap (edificio, predio o tramo de calle) o de una capa verificada, y cada punto dice de dónde sale. Son empresas, no personas: no se publican nombres de personas, teléfonos ni correos aunque el listado los traiga. Si un establecimiento funciona en una vivienda particular, el punto se generaliza a una grilla de unos 200 m, igual que en el inventario. Cada punto se controla contra las capas del mapa antes de publicarse y nada se publica sin la aprobación de Sebastián.
- **Fuentes judiciales primero** (decisión de Sebastián, 28/09/2026): para eventos graves, sobre todo los tecnológicos, se busca primero si hubo causa judicial. Una sentencia firme, con los hechos que el tribunal tuvo por probados, pesa más que la prensa, que puede ocultar, tener intereses o quedar incompleta, y además sirve a los investigadores. Se cita con tribunal, sala, número de causa, fecha y páginas de los hechos probados, con enlace al fallo; nunca se reproducen nombres ni iniciales de las personas. La prensa queda como complemento y, cuando contradice al fallo, se aclara en el registro.
- Todo el sitio y la documentación, en español rioplatense. Comillas clásicas, sin guiones largos.

## Plan

**Fase 1 (hecha, 26/09/2026):** relevamiento de fuentes en `DATOS.md` para tres amenazas: inundaciones y anegamientos, incendios de pastizal y rurales, y actividad portuaria e industrial. Ninguna fuente quedó verificada porque la red del entorno las bloqueaba.

**Fase 2 (aprobada por Sebastián; en curso desde el 26/09/2026):**
- Primero, descargar y verificar las fuentes con scripts en Python en `/scripts`, y actualizar `DATOS.md` pasando cada fuente de "identificada" a "verificada", con fecha y licencia reales.
- Sitio estático (HTML, CSS y JS) con Leaflet o MapLibre, sin backend.
- Capas activables por separado, con leyenda clara y un panel por capa que muestre fuente, fecha y licencia.
- Límite del partido como referencia (Georef, CC BY 4.0, geometría del IGN).
- Página "Metodología": qué representa cada capa, qué **no** representa y sus limitaciones (por ejemplo, un foco de calor de FIRMS no es un incendio confirmado).
- Diseño sobrio, legible en celular, e instalable como aplicación web (PWA: manifiesto más service worker). Aclarar que el mapa de fondo necesita conexión.
- README con instrucciones para publicar en GitHub Pages y para actualizar los datos.
- Atribución de OpenStreetMap visible ("© colaboradores de OpenStreetMap", ODbL) y cita de cada fuente.

Estado al 26/09/2026: límite (Georef), focos de calor (FIRMS), instalaciones portuarias e hidrografía detallada (OpenStreetMap) e hidrografía oficial, curvas de nivel, ferrocarril y rutas (IGN, por WFS) descargados y verificados; sitio en `docs/` (Leaflet 1.9.4, PWA); tubería completa con `python3 scripts/actualizar.py`. Lo que falta está en la sección 5 de `DATOS.md`.

Trabajar por etapas y dejar un resumen al final de cada una.
Usa la skill de TypeSafe (https://docs.typesafe.ai) cuando necesites clasificar, evaluar o extraer datos de los registros

## Licencias

- Código: MIT (archivo `LICENSE`).
- Los datos conservan la licencia de su fuente; no se relicencian. Lo derivado de OpenStreetMap se publica bajo ODbL.

## Red del entorno

Dominios que tienen que estar habilitados en el "Network access" del entorno: ver la sección 5 de `DATOS.md`. Las librerías del sitio se obtienen desde npm (`registry.npmjs.org`), que ya está permitido.
