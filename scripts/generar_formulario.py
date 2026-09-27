"""Genera el formulario de KoboToolbox (XLSForm) del inventario local.

Uso:  python3 scripts/generar_formulario.py

Lee datos/inventario/formulario.json (listas de tipos de evento, localidades y
efectos, compartidas con scripts/procesar_inventario.py) y escribe
datos/inventario/formulario_inventario.xlsx, listo para subir a KoboToolbox
(NEW > Upload an XLSForm).

El XLSX se arma con la biblioteca estándar: es un ZIP con hojas XML.
"""

import json
import sys
import zipfile
from xml.sax.saxutils import escape

from comun import RAIZ

CONFIG = RAIZ / "datos" / "inventario" / "formulario.json"
SALIDA = RAIZ / "datos" / "inventario" / "formulario_inventario.xlsx"


def hoja_xml(filas):
    """Hoja con celdas de texto en línea (inlineStr), que openpyxl y pyxform leen sin problema."""
    def col(i):
        s = ""
        i += 1
        while i:
            i, r = divmod(i - 1, 26)
            s = chr(65 + r) + s
        return s
    xs = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
          '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>']
    for n, fila in enumerate(filas, start=1):
        xs.append(f'<row r="{n}">')
        for c, valor in enumerate(fila):
            if valor in (None, ""):
                continue
            xs.append(f'<c r="{col(c)}{n}" t="inlineStr"><is><t xml:space="preserve">{escape(str(valor))}</t></is></c>')
        xs.append("</row>")
    xs.append("</sheetData></worksheet>")
    return "".join(xs)


def escribir_xlsx(ruta, hojas):
    nombres = list(hojas)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ruta, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   + "".join(f'<Override PartName="/xl/worksheets/sheet{i + 1}.xml" '
                             'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                             for i in range(len(nombres)))
                   + "</Types>")
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   "</Relationships>")
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>'
                   + "".join(f'<sheet name="{escape(n)}" sheetId="{i + 1}" r:id="rId{i + 1}"/>' for i, n in enumerate(nombres))
                   + "</sheets></workbook>")
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   + "".join(f'<Relationship Id="rId{i + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                             f'Target="worksheets/sheet{i + 1}.xml"/>' for i in range(len(nombres)))
                   + "</Relationships>")
        for i, n in enumerate(nombres):
            z.writestr(f"xl/worksheets/sheet{i + 1}.xml", hoja_xml(hojas[n]))


def main():
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    cab = ["type", "name", "label", "hint", "required", "relevant", "constraint", "constraint_message", "appearance"]
    survey = [cab]

    def fila(**kw):
        survey.append([kw.get(k, "") for k in cab])

    fila(type="note", name="presentacion", label=cfg["presentacion"])
    fila(type="select_one tipo_registro", name="tipo_registro", label="¿Qué vas a registrar?", required="yes")
    fila(type="date", name="fecha", label="Fecha del evento o de la observación", required="yes",
         constraint=". <= today() and . >= date('1900-01-01')", constraint_message="La fecha tiene que estar entre 1900 y hoy.")
    fila(type="select_one tipo_evento", name="tipo_evento", label="Tipo de evento", required="yes",
         relevant="${tipo_registro} = 'evento'", hint="Clasificación compatible con DesInventar.")
    fila(type="select_one tipo_vulnerabilidad", name="tipo_vulnerabilidad", label="Tipo de vulnerabilidad", required="yes",
         relevant="${tipo_registro} = 'vulnerabilidad'")
    fila(type="select_one localidad", name="localidad", label="Localidad", required="yes")
    fila(type="text", name="lugar", label="Barrio, paraje o lugar público (opcional)",
         hint="Por ejemplo: barrio, esquina, puente, escuela. Nunca un domicilio particular.",
         constraint="string-length(.) <= 120", constraint_message="Máximo 120 caracteres.")
    fila(type="geopoint", name="ubicacion", label="Punto en el mapa (opcional)",
         hint="Marcalo solo si la nota nombra un lugar público concreto. Si no, dejalo vacío: alcanza con la localidad.")
    fila(type="note", name="nota_efectos", label="Efectos, según la nota (opcional)",
         hint="Cargá solo las cifras que da la nota. Un campo vacío significa sin dato, no cero.",
         relevant="${tipo_registro} = 'evento'")
    for e in cfg["efectos"]:
        decimal = e.get("tipo") == "decimal"
        fila(type="decimal" if decimal else "integer", name=e["name"], label=e["label"], hint=e.get("hint", ""),
             relevant="${tipo_registro} = 'evento'", constraint=". >= 0",
             constraint_message="Tiene que ser un número mayor o igual a cero." if decimal
             else "Tiene que ser un número entero mayor o igual a cero.")
    fila(type="text", name="observaciones_efectos", label="Observaciones de efectos (opcional)", appearance="multiline",
         relevant="${tipo_registro} = 'evento'",
         hint="Cifras en familias (no las pases a personas), cifras no confirmadas o diferencias entre fuentes.",
         constraint="string-length(.) <= 300", constraint_message="Máximo 300 caracteres.")
    fila(type="select_multiple servicio", name="servicios_afectados", label="Servicios o sectores afectados (opcional)",
         relevant="${tipo_registro} = 'evento'")
    fila(type="text", name="descripcion", label="Descripción breve", required="yes", appearance="multiline",
         hint="Qué pasó y dónde, en pocas líneas y con tus palabras. Sin nombres de personas ni domicilios.",
         constraint="string-length(.) <= 400", constraint_message="Máximo 400 caracteres.")
    fila(type="text", name="fuente_medio", label="Medio que publicó la nota", required="yes",
         hint="Escribilo siempre de la misma forma, para poder agrupar los registros por medio.")
    fila(type="text", name="fuente_titulo", label="Título de la nota", required="yes",
         hint="Sirve para revisar el registro; no se publica.")
    fila(type="date", name="fuente_fecha", label="Fecha de publicación de la nota", required="yes",
         constraint=". <= today()", constraint_message="La fecha no puede ser posterior a hoy.")
    fila(type="text", name="fuente_url", label="Enlace a la nota", required="yes",
         constraint="regex(., '^https?://.+')", constraint_message="Tiene que ser un enlace que empiece con http:// o https://")
    fila(type="acknowledge", name="licencia", label=cfg["texto_licencia"], required="yes")

    choices = [["list_name", "name", "label"]]
    choices += [["tipo_registro", "evento", "Un evento adverso que ocurrió"],
                ["tipo_registro", "vulnerabilidad", "Una vulnerabilidad observada"]]
    choices += [["tipo_evento", t["name"], t["label"]] for t in cfg["tipos_evento"]]
    choices += [["tipo_vulnerabilidad", t["name"], t["label"]] for t in cfg["tipos_vulnerabilidad"]]
    choices += [["localidad", t["name"], t["label"]] for t in cfg["localidades"]]
    choices += [["servicio", t["name"], t["label"]] for t in cfg["servicios"]]

    # KoboToolbox reemplaza form_id y version al desplegar; la versión útil es la columna __version__ de la exportación.
    settings = [["form_title", "form_id", "default_language"],
                [cfg["titulo"], cfg["form_id"], "Español (es)"]]
    escribir_xlsx(SALIDA, {"survey": survey, "choices": choices, "settings": settings})
    print(f"Formulario escrito en {SALIDA.relative_to(RAIZ)}: {len(survey) - 1} preguntas, {len(choices) - 1} opciones.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
