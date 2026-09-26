# Mapa interactivo de riesgos del partido de Necochea

Mapa de riesgos del partido de Necochea (provincia de Buenos Aires, Argentina), hecho solo con datos abiertos y publicado como sitio estático en GitHub Pages. Es una pieza de divulgación y la carta de presentación profesional de Juan Sebastián Bértole, estudiante de la Licenciatura en Gestión de Riesgos y Siniestralidad (Instituto Universitario Vucetich). Importa más el rigor de las fuentes que la cantidad de capas.

## Reglas que no se negocian

- **Nunca inventar, estimar ni simular datos** para completar una capa. Una capa sin datos verificados se muestra como "pendiente de fuente".
- Cada fuente se registra en `DATOS.md` con: organismo, URL exacta, fecha de los datos, licencia, formato, cobertura y limitaciones. Estado: verificada, identificada o sin fuente.
- Si el entorno no deja descargar un sitio, no se buscan rodeos: se anota la URL en `DATOS.md` para que Sebastián la descargue a mano.
- **Exclusiones:** ninguna ubicación de cámaras de videovigilancia, infraestructura de seguridad (comisarías, centros de monitoreo) ni datos personales. Filtrar de forma explícita `man_made=surveillance` y `amenity=police` en las consultas a OpenStreetMap.
- Todo el sitio y la documentación, en español rioplatense. Comillas clásicas, sin guiones largos.

## Plan

**Fase 1 (hecha, 26/09/2026):** relevamiento de fuentes en `DATOS.md` para tres amenazas: inundaciones y anegamientos, incendios de pastizal y rurales, y actividad portuaria e industrial. Ninguna fuente quedó verificada porque la red del entorno las bloqueaba.

**Fase 2 (aprobada por Sebastián; pendiente):**
- Primero, descargar y verificar las fuentes con scripts en Python en `/scripts`, y actualizar `DATOS.md` pasando cada fuente de "identificada" a "verificada", con fecha y licencia reales.
- Sitio estático (HTML, CSS y JS) con Leaflet o MapLibre, sin backend.
- Capas activables por separado, con leyenda clara y un panel por capa que muestre fuente, fecha y licencia.
- Límite del partido como referencia (Georef, CC BY 4.0, geometría del IGN).
- Página "Metodología": qué representa cada capa, qué **no** representa y sus limitaciones (por ejemplo, un foco de calor de FIRMS no es un incendio confirmado).
- Diseño sobrio, legible en celular, e instalable como aplicación web (PWA: manifiesto más service worker). Aclarar que el mapa de fondo necesita conexión.
- README con instrucciones para publicar en GitHub Pages y para actualizar los datos.
- Atribución de OpenStreetMap visible ("© colaboradores de OpenStreetMap", ODbL) y cita de cada fuente.

Trabajar por etapas y dejar un resumen al final de cada una.

## Licencias

- Código: MIT (archivo `LICENSE`).
- Los datos conservan la licencia de su fuente; no se relicencian. Lo derivado de OpenStreetMap se publica bajo ODbL.

## Red del entorno

Dominios que tienen que estar habilitados en el "Network access" del entorno: ver la sección 5 de `DATOS.md`. Las librerías del sitio se obtienen desde npm (`registry.npmjs.org`), que ya está permitido.
