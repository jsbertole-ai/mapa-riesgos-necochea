"""Lector mínimo de planillas Excel 97-2003 (.xls, BIFF8) con la biblioteca estándar.

Alcanza para los padrones que publica la Secretaría de Energía: lee textos (tabla de cadenas
compartidas y celdas de texto sueltas), números y resultados de fórmulas. No interpreta
formatos: una fecha llega como el número de serie de Excel.

Uso:  from leer_xls import leer_xls
      hojas = leer_xls(contenido)   # {nombre de la hoja: [[valor, ...], ...]}

Referencias: Microsoft, "[MS-CFB] Compound File Binary File Format" y "[MS-XLS] Excel Binary
File Format (.xls) Structure" (documentación pública de los formatos).
"""

import struct

FIN_DE_CADENA = 0xFFFFFFFE
LIBRE = 0xFFFFFFFF


class ErrorXls(Exception):
    pass


def _flujo_workbook(datos):
    """Devuelve el flujo "Workbook" (o "Book") de un archivo compuesto de Microsoft (CFB)."""
    if datos[:8] != b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ErrorXls("no es un archivo .xls (falta la firma del formato compuesto)")
    tam_sector = 1 << struct.unpack("<H", datos[30:32])[0]
    n_fat, primer_dir = struct.unpack("<I", datos[44:48])[0], struct.unpack("<I", datos[48:52])[0]
    corte_mini = struct.unpack("<I", datos[56:60])[0]
    primer_difat, n_difat = struct.unpack("<II", datos[68:76])

    def sector(i):
        inicio = (i + 1) * tam_sector
        return datos[inicio:inicio + tam_sector]

    difat = [s for s in struct.unpack("<109I", datos[76:512]) if s != LIBRE]
    s, por_sector = primer_difat, tam_sector // 4
    for _ in range(n_difat):
        entradas = struct.unpack(f"<{por_sector}I", sector(s))
        difat += [e for e in entradas[:-1] if e != LIBRE]
        s = entradas[-1]
    fat = []
    for s in difat[:n_fat]:
        fat += struct.unpack(f"<{por_sector}I", sector(s))

    def cadena(inicio):
        partes, s, vistos = [], inicio, set()
        while s != FIN_DE_CADENA:
            if s in vistos or s >= len(fat):
                raise ErrorXls("cadena de sectores dañada")
            vistos.add(s)
            partes.append(sector(s))
            s = fat[s]
        return b"".join(partes)

    directorio = cadena(primer_dir)
    for k in range(0, len(directorio), 128):
        e = directorio[k:k + 128]
        largo = struct.unpack("<H", e[64:66])[0]
        nombre = e[:max(largo - 2, 0)].decode("utf-16-le", errors="replace")
        if nombre in ("Workbook", "Book") and e[66] == 2:
            inicio, tam = struct.unpack("<II", e[116:124])
            if tam < corte_mini:
                raise ErrorXls("flujo Workbook en el mini flujo: planilla demasiado chica para este lector")
            return cadena(inicio)[:tam]
    raise ErrorXls("no se encontró el flujo Workbook")


class _Trozos:
    """Recorre un registro SST y sus CONTINUE respetando los cortes entre registros."""

    def __init__(self, trozos):
        self.trozos, self.i, self.p = trozos, 0, 0

    def _siguiente(self):
        self.i += 1
        self.p = 0
        if self.i >= len(self.trozos):
            raise ErrorXls("tabla de cadenas incompleta")

    def leer(self, n):
        salida = b""
        while n:
            t = self.trozos[self.i]
            if self.p >= len(t):
                self._siguiente()
                continue
            k = min(n, len(t) - self.p)
            salida += t[self.p:self.p + k]
            self.p += k
            n -= k
        return salida

    def caracteres(self, n, ancho):
        # Si la cadena se corta entre registros, el CONTINUE empieza con un byte de opciones
        # que vuelve a decir si los caracteres que siguen son de 1 o de 2 bytes.
        partes = []
        while n:
            t = self.trozos[self.i]
            if self.p >= len(t):
                self._siguiente()
                ancho = 2 if self.trozos[self.i][0] & 1 else 1
                self.p = 1
                continue
            k = min(n, (len(t) - self.p) // ancho)
            crudo = t[self.p:self.p + k * ancho]
            partes.append(crudo.decode("utf-16-le" if ancho == 2 else "latin-1"))
            self.p += k * ancho
            n -= k
        return "".join(partes)


def _tabla_de_cadenas(trozos):
    r = _Trozos(trozos)
    _, unicas = struct.unpack("<II", r.leer(8))
    cadenas = []
    for _ in range(unicas):
        largo, opciones = struct.unpack("<HB", r.leer(3))
        corridas = struct.unpack("<H", r.leer(2))[0] if opciones & 8 else 0
        extra = struct.unpack("<I", r.leer(4))[0] if opciones & 4 else 0
        cadenas.append(r.caracteres(largo, 2 if opciones & 1 else 1))
        r.leer(4 * corridas + extra)
    return cadenas


def _cadena_suelta(datos, largo_campo=2):
    largo = struct.unpack("<H" if largo_campo == 2 else "<B", datos[:largo_campo])[0]
    opciones = datos[largo_campo]
    p = largo_campo + 1
    if opciones & 8:
        p += 2
    if opciones & 4:
        p += 4
    if opciones & 1:
        return datos[p:p + 2 * largo].decode("utf-16-le")
    return datos[p:p + largo].decode("latin-1")


def _rk(valor):
    if valor & 2:
        n = struct.unpack("<i", struct.pack("<I", valor))[0] >> 2
    else:
        n = struct.unpack("<d", struct.pack("<Q", (valor & 0xFFFFFFFC) << 32))[0]
    return n / 100 if valor & 1 else n


def _registros(flujo):
    p = 0
    while p + 4 <= len(flujo):
        tipo, largo = struct.unpack("<HH", flujo[p:p + 4])
        yield p, tipo, flujo[p + 4:p + 4 + largo]
        p += 4 + largo


def leer_xls(contenido):
    flujo = _flujo_workbook(contenido)
    hojas_por_posicion, sst, trozos_sst = {}, None, None
    for p, tipo, d in _registros(flujo):
        if tipo == 0x0085:  # BOUNDSHEET
            hojas_por_posicion[struct.unpack("<I", d[:4])[0]] = _cadena_suelta(d[6:], largo_campo=1)
        elif tipo == 0x00FC:  # SST
            trozos_sst = [d]
        elif tipo == 0x003C and trozos_sst is not None and sst is None:  # CONTINUE del SST
            trozos_sst.append(d)
        elif trozos_sst is not None and sst is None:
            sst = _tabla_de_cadenas(trozos_sst)
        if tipo == 0x000A:  # EOF del bloque global
            break
    sst = sst or []

    hojas = {}
    for inicio, nombre in sorted(hojas_por_posicion.items()):
        celdas, formula_pendiente = {}, None
        for p, tipo, d in _registros(flujo[inicio:]):
            if tipo == 0x000A:  # EOF de la hoja
                break
            if tipo in (0x00FD, 0x0203, 0x027E, 0x0204, 0x0006, 0x0205):
                fila, col = struct.unpack("<HH", d[:4])
            if tipo == 0x00FD:  # LABELSST
                celdas[fila, col] = sst[struct.unpack("<I", d[6:10])[0]]
            elif tipo == 0x0203:  # NUMBER
                celdas[fila, col] = struct.unpack("<d", d[6:14])[0]
            elif tipo == 0x027E:  # RK
                celdas[fila, col] = _rk(struct.unpack("<I", d[6:10])[0])
            elif tipo == 0x00BD:  # MULRK
                fila, primera = struct.unpack("<HH", d[:4])
                for k in range((len(d) - 6) // 6):
                    celdas[fila, primera + k] = _rk(struct.unpack("<I", d[4 + 6 * k + 2:4 + 6 * k + 6])[0])
            elif tipo == 0x0204:  # LABEL
                celdas[fila, col] = _cadena_suelta(d[6:])
            elif tipo == 0x0205:  # BOOLERR
                celdas[fila, col] = bool(d[6]) if d[7] == 0 else None
            elif tipo == 0x0006:  # FORMULA
                resultado = d[6:14]
                if resultado[6:8] == b"\xff\xff":
                    if resultado[0] == 0:
                        formula_pendiente = (fila, col)  # el texto llega en el registro STRING
                    else:
                        celdas[fila, col] = bool(resultado[2]) if resultado[0] == 1 else None
                else:
                    celdas[fila, col] = struct.unpack("<d", resultado)[0]
            elif tipo == 0x0207 and formula_pendiente:  # STRING
                celdas[formula_pendiente] = _cadena_suelta(d)
                formula_pendiente = None
        if not celdas:
            hojas[nombre] = []
            continue
        n_filas = max(f for f, _ in celdas) + 1
        n_cols = max(c for _, c in celdas) + 1
        hojas[nombre] = [[celdas.get((f, c), "") for c in range(n_cols)] for f in range(n_filas)]
    return hojas
