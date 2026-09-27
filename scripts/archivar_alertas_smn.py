"""Archivo propio de las alertas y avisos del Servicio Meteorológico Nacional (SMN) que alcanzan al partido.

Uso:  python3 scripts/archivar_alertas_smn.py

Lee el canal de alertas del SMN en formato CAP 1.2 (https://ssl.smn.gob.ar/CAP/AR.php),
que declara "Licencia CC BY 4.0", baja cada alerta o aviso vigente y guarda en
docs/datos/alertas_smn.json los que alcanzan al partido de Necochea. El canal solo
muestra lo vigente: el archivo se arma hacia adelante, desde el día en que se encendió
(ver "desde"). Una GitHub Action lo corre cada hora (.github/workflows/alertas-smn.yml).

"Alcanza al partido" quiere decir que el polígono de la alerta y el límite del partido
se tocan: algún vértice del límite (uno de cada diez, cada 100 m aproximadamente) cae
dentro del polígono, o algún vértice del polígono cae dentro del partido. Además se
anotan las localidades del IGN que quedan dentro. No se deduce el color de la alerta:
se guarda la severidad del estándar CAP y el titular tal como lo escribe el SMN.

El archivo solo cambia cuando entra una alerta nueva: no guarda la hora de cada consulta,
para no generar un commit por hora.
"""

import datetime as dt
import sys
import time
import xml.etree.ElementTree as ET

from comun import (SITIO_DATOS, ErrorRed, aviso, caja_envolvente, cargar_limite, descargar, escribir_json, leer_json,
                   punto_en_geometria, vertices)

CANAL = "https://ssl.smn.gob.ar/CAP/AR.php"
ARCHIVO = SITIO_DATOS / "alertas_smn.json"
NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}
SEVERIDAD = {"Minor": "Menor", "Moderate": "Moderada", "Severe": "Severa", "Extreme": "Extrema", "Unknown": "Desconocida"}
CERTEZA = {"Observed": "Observado", "Likely": "Probable", "Possible": "Posible", "Unlikely": "Poco probable",
           "Unknown": "Desconocida"}
URGENCIA = {"Immediate": "Inmediata", "Expected": "Esperada", "Future": "Futura", "Past": "Pasada", "Unknown": "Desconocida"}
MENSAJE = {"Alert": "Emisión", "Update": "Actualización", "Cancel": "Cancelación"}


def texto(nodo, etiqueta):
    e = nodo.find("cap:" + etiqueta, NS)
    return (e.text or "").strip() if e is not None and e.text else None


def poligono(cadena):
    """Polígono CAP ("lat,lon lat,lon ...") a GeoJSON en [lon, lat]."""
    anillo = []
    for par in cadena.split():
        lat, lon = par.split(",")
        anillo.append([float(lon), float(lat)])
    return {"type": "Polygon", "coordinates": [anillo]}


def alcance(geom, limite, caja, muestra, localidades):
    c = caja_envolvente(geom)
    if c[2] < caja[0] or c[0] > caja[2] or c[3] < caja[1] or c[1] > caja[3]:
        return None
    dentro = sum(punto_en_geometria(x, y, geom) for x, y in muestra)
    if not dentro and not any(punto_en_geometria(x, y, limite, caja) for x, y, *_ in vertices(geom)):
        return None
    return {
        "alcance": "todo el partido" if dentro == len(muestra) else "parte del partido",
        "localidades": [nombre for nombre, (x, y) in localidades if punto_en_geometria(x, y, geom)],
    }


def main():
    limite, caja = cargar_limite()
    muestra = [(x, y) for i, (x, y, *_) in enumerate(vertices(limite)) if i % 10 == 0]
    locs = leer_json(SITIO_DATOS / "localidades.geojson", {"features": []})
    localidades = [(f["properties"].get("fna"), f["geometry"]["coordinates"][0] if f["geometry"]["type"] == "MultiPoint"
                    else f["geometry"]["coordinates"]) for f in locs["features"]]
    archivo = leer_json(ARCHIVO) or {
        "fuente": "Servicio Meteorológico Nacional (SMN), canal de alertas en formato CAP 1.2: " + CANAL,
        "licencia": "CC BY 4.0, declarada en el canal (\"Derechos de autor, Servicio Meteorologico Nacional (SMN). "
                    "Licencia CC BY 4.0.\")",
        "desde": dt.date.today().isoformat(),
        "criterio": "Alertas y avisos cuyo polígono toca el límite del partido. El archivo empieza en la fecha "
                    "\"desde\": el canal del SMN no tiene historia.",
        "alertas": [],
    }
    conocidas = {a["id"] for a in archivo["alertas"]}

    try:
        canal = ET.fromstring(descargar(CANAL, timeout=60))
    except (ErrorRed, ET.ParseError) as e:
        aviso(f"No se pudo leer el canal del SMN: {e}")
        return 1
    enlaces = sorted({(i.findtext("link") or "").strip() for i in canal.iter("item")} - {""})
    nuevas, errores = 0, 0
    for url in enlaces:
        time.sleep(0.5)
        try:
            alerta = ET.fromstring(descargar(url, timeout=60, reintentos=2))
        except (ErrorRed, ET.ParseError) as e:
            aviso(f"{url}: {e}")
            errores += 1
            continue
        identificador = texto(alerta, "identifier")
        if not identificador or identificador in conocidas:
            continue
        for info in alerta.findall("cap:info", NS):
            zonas = []
            for area in info.findall("cap:area", NS):
                for p in area.findall("cap:polygon", NS):
                    if p.text and p.text.strip():
                        r = alcance(poligono(p.text), limite, caja, muestra, localidades)
                        if r:
                            zonas.append(dict(r, zona=texto(area, "areaDesc")))
            if not zonas:
                continue
            severidad = texto(info, "severity")
            archivo["alertas"].append({
                "id": identificador,
                "tipo": "aviso a corto plazo" if "/avisocortoplazo/" in url else "alerta",
                "mensaje": MENSAJE.get(texto(alerta, "msgType"), texto(alerta, "msgType")),
                "enviado": texto(alerta, "sent"),
                "evento": texto(info, "event"),
                "titular": texto(info, "headline"),
                "descripcion": texto(info, "description"),
                "severidad": SEVERIDAD.get(severidad, severidad),
                "certeza": CERTEZA.get(texto(info, "certainty"), texto(info, "certainty")),
                "urgencia": URGENCIA.get(texto(info, "urgency"), texto(info, "urgency")),
                "inicio": texto(info, "onset") or texto(alerta, "sent"),
                "fin": texto(info, "expires"),
                "alcance": "todo el partido" if any(z["alcance"] == "todo el partido" for z in zonas) else "parte del partido",
                "localidades": sorted({n for z in zonas for n in z["localidades"]}),
                "referencias": texto(alerta, "references"),
                "url": url,
            })
            conocidas.add(identificador)
            nuevas += 1
            break
    archivo["alertas"].sort(key=lambda a: a.get("enviado") or "")
    if nuevas or not ARCHIVO.exists():
        escribir_json(ARCHIVO, archivo)
    print(f"Canal del SMN: {len(enlaces)} alertas y avisos vigentes; {nuevas} nuevas para el partido; "
          f"{len(archivo['alertas'])} en el archivo desde {archivo['desde']}."
          + (f" {errores} no se pudieron leer." if errores else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
