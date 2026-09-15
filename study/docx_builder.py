# -*- coding: utf-8 -*-
"""docx_builder.py — constructor bilingüe de manuscritos Word (Times New Roman 12, A4, 2,5 cm, interlineado 1,5).

Generaliza `paper/build_docx.py`: recibe una lista de bloques
  ("title", str) ("authors", list) ("h1"|"h2"|"h3", str) ("p", str) ("bullets", [str]) ("eq", (paths, number))
  ("table", dict(df=DataFrame, title=str, note=str)) ("figure", dict(path=Path, caption=str))
  ("panel", dict(title=str, items=[(heading, text), ...]))  # p. ej. Research in context
  ("pagebreak", None) ("refs", [str])
y un idioma (`es`|`en`) que decide los rótulos «Tabla/Table», «Figura/Figure», «Nota/Note».
Las citas se escriben en el texto como [@clave] y se numeran por orden de aparición con `references.Citations`.
"""
from __future__ import annotations

import copy
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.table import _Cell
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))   # study/: references.py lives beside this module
from references import Citations, parse_bib  # noqa: E402

FUENTE = "Times New Roman"
CUERPO_PT = 12
TEXT_WIDTH_CM = 16.0
WORDS = {
    "table": {"es": "Tabla", "en": "Table"}, "figure": {"es": "Figura", "en": "Figure"}, "note": {"es": "Nota.", "en": "Note."},
    "references": {"es": "Referencias", "en": "References"}, "supplementary": {"es": "Suplementaria", "en": "Supplementary"},
    # La marca de ecuación lleva su palabra delante. Sin ella el apéndice separado imprimía «(19)» junto a la
    # ecuación (19) y a la cita (19) —cuya numeración vuelve a empezar en 1 en ese archivo— en la misma
    # página, y las dos referencias no podían distinguirse a simple vista.
    "equation_tag": {"es": "Ec.", "en": "Eq."},
    # Cola de una leyenda que no cabe en la página de su lámina y termina en la página siguiente: se
    # rotula para que el lector sepa de qué figura es el bloque de texto pequeño con el que abre la página.
    "continued": {"es": "continuación", "en": "continued"},
}


def _set_font(run, size=CUERPO_PT, bold=False, italic=False, name=FUENTE, superscript=False):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    if superscript:
        run.font.superscript = True
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), name)


_REF_RE = re.compile(r"\b(?:Tabla|Figura|Tablas|Figuras|Table|Figure|Tables|Figures)\s[S]?\d+[a-fA-F]?(?:\s(?:y|a|and|to)\s[S]?\d*[a-fA-F]?)?\b")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
# La cursiva se abre solo con un «*» que no siga a una letra, cifra o «_»: así «Gi*», «S*.csv» o «M*.png»
# conservan su asterisco literal y no abren un tramo en cursiva (antes «LISA y Gi*, … Gi*» perdía los dos
# asteriscos y ponía en cursiva el texto intermedio).
_ITAL_RE = re.compile(r"(?<![\w*])\*(?!\*)(.+?)(?<!\*)\*(?!\*)")


def _add_text(p, texto, size=CUERPO_PT, bold=False, italic=False, refs_bold=True):
    texto = texto_indivisible(texto)
    pos = 0
    for m in _BOLD_RE.finditer(texto):
        if m.start() > pos:
            _add_ital(p, texto[pos:m.start()], size, bold, italic, refs_bold)
        _set_font(p.add_run(m.group(1)), size=size, bold=True, italic=italic)
        pos = m.end()
    _add_ital(p, texto[pos:], size, bold, italic, refs_bold)


def _add_ital(p, texto, size, bold, italic, refs_bold):
    pos = 0
    for m in _ITAL_RE.finditer(texto):
        if m.start() > pos:
            _add_plain(p, texto[pos:m.start()], size, bold, italic, refs_bold)
        _set_font(p.add_run(m.group(1)), size=size, bold=bold, italic=True)
        pos = m.end()
    _add_plain(p, texto[pos:], size, bold, italic, refs_bold)


# Marcadores privados (U+E000/U+E001) que envuelven el NÚMERO de una cita en modo revista: el resolutor de
# `build_document(journal=…)` los escribe detrás del signo de puntuación que sigue a la cita y `_add_plain`
# los imprime como un run en superíndice («…colleagues.15»). Fuera del modo revista no existen.
_SUP_OPEN, _SUP_CLOSE = "\ue000", "\ue001"
_SUP_RE = re.compile("\ue000([^\ue001]*)\ue001")


def _add_plain(p, texto, size, bold, italic, refs_bold):
    pos = 0
    for m in _SUP_RE.finditer(texto):
        if m.start() > pos:
            _add_runs(p, texto[pos:m.start()], size, bold, italic, refs_bold)
        _set_font(p.add_run(m.group(1)), size=size, superscript=True)
        pos = m.end()
    _add_runs(p, texto[pos:], size, bold, italic, refs_bold)


def _add_runs(p, texto, size, bold, italic, refs_bold):
    pos = 0
    if refs_bold:
        for m in _REF_RE.finditer(texto):
            if m.start() > pos:
                _set_font(p.add_run(texto[pos:m.start()]), size=size, bold=bold, italic=italic)
            _set_font(p.add_run(m.group(0)), size=size, bold=True, italic=italic)
            pos = m.end()
    _set_font(p.add_run(texto[pos:]), size=size, bold=bold, italic=italic)


def parrafo(doc, texto, size=CUERPO_PT, bold=False, italic=False, align=WD_ALIGN_PARAGRAPH.JUSTIFY, space_after=6, space_before=0,
            line=1.5, first_line_indent=None, keep_with_next=False, refs_bold=True):
    p = doc.add_paragraph()
    p.alignment = align
    pf = p.paragraph_format
    pf.space_after, pf.space_before, pf.line_spacing, pf.keep_with_next = Pt(space_after), Pt(space_before), line, keep_with_next
    if first_line_indent is not None:
        pf.first_line_indent = Cm(first_line_indent)
    _add_text(p, texto, size=size, bold=bold, italic=italic, refs_bold=refs_bold)
    return p


def titulo(doc, texto, nivel=1, pt=None, line: float = 1.15):
    """Título de sección. `pt` (modo revista) sustituye el cuerpo por nivel; sin él, 14/12,5/12 como siempre."""
    tam = {1: 14, 2: 12.5, 3: 12}[nivel] if pt is None else pt
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing, pf.keep_with_next = Pt(18 if nivel == 1 else 12), Pt(6), line, True
    _set_font(p.add_run(texto_indivisible(texto)), size=tam, bold=True, italic=(nivel == 3))
    return p


def _cell_border(cell, **kwargs):
    tcPr = cell._tc.get_or_add_tcPr()
    borders = tcPr.find(qn("w:tcBorders"))
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tcPr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        spec = kwargs.get(edge)
        el = borders.find(qn("w:" + edge))
        if el is None:
            el = OxmlElement("w:" + edge)
            borders.append(el)
        if spec is None:
            el.set(qn("w:val"), "nil")
        else:
            el.set(qn("w:val"), spec.get("val", "single"))
            el.set(qn("w:sz"), str(spec.get("sz", 6)))
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), spec.get("color", "000000"))


def _repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader")
    el.set(qn("w:val"), "true")
    trPr.append(el)


def _no_autofit(table, total_cm=None):
    table.autofit = False
    tblPr = table._tbl.tblPr
    for tag in ("w:tblLayout", "w:tblW"):
        el = tblPr.find(qn(tag))
        if el is not None:
            tblPr.remove(el)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)
    if total_cm:
        w = OxmlElement("w:tblW")
        w.set(qn("w:type"), "dxa")
        w.set(qn("w:w"), str(int(total_cm * 567)))
        tblPr.append(w)


def _aplicar_anchos(table, anchos_cm):
    """Escribe los anchos en la rejilla y en las celdas, DESPUÉS de garantizar que no parten un número.

    Es la última mano que toca la rejilla de una tabla, tanto al construirla (`insertar_tabla`) como cuando
    el posproceso de 10_manuscript la rehace apaisada, así que la garantía de la tarea F4-1 vive aquí y no
    en el cálculo de anchos: llegue el reparto de donde llegue, de aquí no sale una columna más estrecha
    que su número más largo mientras alguna otra tenga texto que sí se pueda partir."""
    anchos_cm = _proteger_numeros(table, list(anchos_cm))
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for gc, w in zip(grid.findall(qn("w:gridCol")), anchos_cm):
            gc.set(qn("w:w"), str(int(w * 567)))
    for j, w in enumerate(anchos_cm):
        for row in table.rows:
            row.cells[j].width = Cm(w)
    # Una celda FUSIONADA a lo ancho (fila de encabezado interno del modo revista) mide la suma de las
    # columnas que abarca; el bucle de arriba le deja el ancho de la última. Sin celdas fusionadas no hay
    # nada que corregir y la rejilla queda exactamente como siempre.
    for row in table.rows:
        tcs = row._tr.tc_lst
        if len(tcs) == len(anchos_cm):
            continue
        j = 0
        for tc in tcs:
            span = int(tc.grid_span or 1)
            if span > 1:
                _Cell(tc, table).width = Cm(sum(anchos_cm[j:j + span]))
            j += span


_ANCHO_CAR = {}
for _c in "0123456789":
    _ANCHO_CAR[_c] = 0.50
for _c in "abcdefghijklmnopqrstuvwxyzáéíóúüñ":
    _ANCHO_CAR[_c] = 0.47
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZÁÉÍÓÚÑ":
    _ANCHO_CAR[_c] = 0.70
for _c in " .,;:()[]-+/%<>=–·":
    _ANCHO_CAR[_c] = 0.34
# El blanco que no parte mide lo que el blanco que parte (el estrecho, algo menos): entra en la medida
# porque viaja DENTRO del trozo indivisible «1,1\u00a0%», y no medirlo lo dejaba corto por 0,34 em.
_ANCHO_CAR["\u00a0"] = 0.34
for _c in "\u202f\u2009":
    _ANCHO_CAR[_c] = 0.20


def _ancho_texto(txt, pt, bold=False):
    ems = sum(_ANCHO_CAR.get(c, 0.55) for c in str(txt))
    return ems * (1.06 if bold else 1.0) * pt / 28.3465


# ---------------------------------------------------------------------------
# El ancho de un trozo INDIVISIBLE se mide con el avance REAL de Times New Roman
# ---------------------------------------------------------------------------
# `_ANCHO_CAR` es una calibración de PROSA: mete toda la puntuación en un mismo cajón de 0,34 em porque para
# medir un párrafo de cien caracteres los errores de signo a signo se compensan. Para un trozo indivisible de
# seis caracteres no se compensa ninguno, y uno de esos signos estaba muy mal medido: el de porcentaje, que
# Times New Roman traza a 0,833 em —de los glifos más anchos de la fuente— y el modelo daba por 0,34. En «14,0 %»
# eso son 0,12 cm de menos sobre 0,70: la columna se concedía a 1,03 cm creyendo que bastaba, LibreOffice medía
# 0,70 + margen y no le cabía, y partía el trozo pese al espacio duro. Ahí seguían 30 signos huérfanos en la
# sonda española DESPUÉS de poner el espacio duro: el blanco ya no era el punto de corte, pero la caja seguía
# siendo más estrecha que lo que había que meter en ella.
#
# Por eso los ATOMOS —y sólo ellos— se miden aquí, con el avance real de la fuente (unidades/em = 2048). La
# medida de la prosa NO se toca: las leyendas de las 244 láminas y el reparto de las páginas están calibrados
# contra `_ANCHO_CAR` y una corrección global movería una maquetación ya revisada por otro camino. Un modelo
# para medir renglones y otro para medir trozos que no se pueden partir; el segundo no puede quedarse corto.
_ANCHO_NUM = dict(_ANCHO_CAR)
_ANCHO_NUM.update({c: 0.500 for c in "0123456789"})
_ANCHO_NUM.update({c: 0.250 for c in ".,"})
_ANCHO_NUM.update({c: 0.278 for c in ";:"})
_ANCHO_NUM.update({c: 0.333 for c in "()[]"})
_ANCHO_NUM.update({c: 0.564 for c in "<>=+±"})
_ANCHO_NUM.update({c: 0.549 for c in "≤≥≈"})
_ANCHO_NUM["~"] = 0.541
_ANCHO_NUM["·"] = 0.250                    # decimal a media altura del envío a la revista
_ANCHO_NUM["%"] = 0.833                    # el que rompía la cuenta
_ANCHO_NUM["‰"] = 1.000
_ANCHO_NUM[" "] = 0.250
_ANCHO_NUM["\u00a0"] = 0.250
for _c in "\u202f\u2009":
    _ANCHO_NUM[_c] = 0.200
_NUM_SEGURO = 1.02                         # kerning y redondeo del maquetador: dos centésimas de holgura


def _ancho_numero(txt, pt, bold=False):
    """Ancho de un trozo que Word tiene que imprimir de una pieza, con el avance real de la fuente."""
    ems = sum(_ANCHO_NUM.get(c, 0.60) for c in str(txt))
    return ems * _NUM_SEGURO * (1.06 if bold else 1.0) * pt / 28.3465


# ---------------------------------------------------------------------------
# Ningún número se parte en dos líneas (fase 4f, tarea F4-1)
# ---------------------------------------------------------------------------
# Word parte una palabra que no cabe en su celda por donde le toque —carácter a carácter, sin punto de
# corte— y en las tablas suplementarias más anchas eso imprimía «1,085,8» en una línea y «13» en la
# siguiente: un número roto en dos, que el lector lee como una errata y no como un salto de línea. Ocurría
# en los OCHO documentos largos y en ninguno de los cuatro del artículo, porque las tablas que lo sufren
# —S14, S15, S16, S24, S25, S37, S38, S43, S48 y la de modelos— tienen de 14 a 21 columnas, ya no caben ni
# apaisadas a 6 pt y el reparto a prorrata baja algunas columnas por debajo de su cifra más larga.
#
# LA REGLA. Ninguna columna puede quedar más estrecha que el número más largo que imprime. Lo que Word
# puede partir sin dañar la lectura —una palabra de texto corrido, una ruta de archivo, un hash— cede el
# milímetro que le falta al número, y el ancho TOTAL de la tabla no cambia: no se ensancha la caja, se
# reparte distinto. Por eso el arreglo no toca ni el cuerpo de la tabla ni su orientación y no mueve una
# sola página de los doce documentos.
#
# QUÉ ES «UN NÚMERO» AQUÍ. El trozo entre puntos de corte de Word (espacio, «/», guion, raya, «+») formado
# sólo por cifras y por la puntuación que no se separa de ellas: separador de millares, coma o punto
# decimal, paréntesis, corchete, signo de porcentaje, signo de comparación. Así se protegen enteros
# «1.085.813», «1,085,813», «(18,1», «22.4)», «2,6%», «100,000» y «2019»; NO son números —y siguen
# pudiendo partirse, que es lo que hace falta para que quepan las tablas de procedencia— «F84.2»,
# «GRD_PUBLICO_2019.csv», «study/pipeline/06_models.py» ni un SHA-256 como «1b86155938fd».
# La regla se aplica igual en los dos idiomas porque el separador de millares —«,» en inglés, «.» en
# español— entra en el mismo conjunto de puntuación pegada a la cifra.
#
# POR QUÉ ENSANCHAR Y NO ENCOGER LA LETRA. Los déficits medidos sobre los doce documentos de 2026-09-07
# van de 0,02 a 0,42 cm sobre columnas de 0,7 a 1,7 cm: meter «1.608,07» en 0,37 cm de caja útil pediría
# bajar esa celda de 6,0 a 3,7 pt, que no se lee. Ensanchar la columna 0,42 cm a costa de una columna de
# texto corrido no le cuesta nada al lector. El cuerpo reducido queda como ÚLTIMO recurso (`NUM_MIN_PT`),
# para la tabla en la que no quedara holgura que mover, y nunca se aplica a la fila de cabecera: el
# posproceso de 10_manuscript lee de ella el cuerpo de la tabla (`_table_font_pt`) para recalcular los
# anchos apaisados, y encogerla le mentiría.
CELL_PAD_CM = 0.40          # margen interior de una celda (Word pone 0,19 cm por lado) con holgura
NUM_MIN_PT = 5.5            # suelo del último recurso: cuerpo de una celda cuyo número no cabe ni así
_EM_ANCHO = 0.75            # em del carácter más ancho de estas tablas (mayúscula 0,70): suelo absoluto
# Word guarda los anchos en TWIPS enteros y `_aplicar_anchos` trunca al escribirlos, de modo que una
# columna a la que se le concede exactamente el ancho de su número se imprime hasta un twip más estrecha y
# el número vuelve a partirse por 0,001 cm. Se conceden dos twips de más: 0,0035 cm que nadie ve y que
# absorben el truncamiento en las dos escrituras (la rejilla y el ancho de celda).
_TWIP_CM = 1 / 567
NUM_HOLGURA_CM = 2 * _TWIP_CM

# Puntos donde Word SÍ puede cortar dentro de una palabra sin partir una cifra.
# El espacio DURO no es uno de ellos, y por eso se enumera aquí el blanco que sí parte (\s en Python
# incluye U+00A0, U+202F y U+2009): tomarlos por punto de corte hacía que «1,1 %» —escrito con espacio
# duro para que el signo no se separe de su cifra— midiera sólo «1,1» y la columna saliera más estrecha
# que el trozo que Word tiene que imprimir de una pieza, que es exactamente como se parte un número.
_NUM_BREAK_RE = re.compile(r"[ \t\n\r\f\v/\\|‐‑‒–—―−+-]+")
# Un trozo es un NÚMERO si empieza por cifra (tras la puntuación de apertura) y no lleva más que cifras y
# puntuación pegada a ellas
_NUM_ATOM_RE = re.compile(r"^[(\[<>≤≥≈~±]*\d[\d.,·   ]*[%‰)\]]*[.,;:]?$")   # «·»: decimal a media altura del envío a la revista
# UN NÚMERO PUEDE VIAJAR DETRÁS DE UNA ETIQUETA. La regla de arriba mira el trozo entero y pide que EMPIECE
# por cifra, de modo que no veía «blank=184963» —etiqueta, signo igual y frecuencia— y la Tabla S43 imprimía
# «blank=18496» con un «3» suelto en la línea siguiente: el lector se lleva 18.496 en vez de 184.963, un orden
# de magnitud. El guardián estaba ciego por dónde parte Word y no por qué es un número: dentro de ese trozo no
# hay UN SOLO punto de corte —ni blanco, ni barra, ni guion—, así que Word lo parte carácter a carácter y cae
# dentro de la cifra. Proteger sólo «184963» no bastaría: si la columna admite la cifra pero no la etiqueta,
# Word sigue partiendo por donde llene la línea y vuelve a cortar dígitos. Lo indivisible es el trozo ENTERO,
# y eso es lo que se declara aquí.
#
# La etiqueta tiene que ser una PALABRA (empieza por letra) y el valor, la cifra que llega hasta el final del
# trozo. Así entra «blank=184963», «blanco=173910;» y «Sí=11053», y NO entran los identificadores con dígitos
# que las tablas de procedencia necesitan poder partir para caber: «F84.2» y «D15_11» no llevan signo igual;
# «GRD_PUBLICO_2019.csv» y «1b86155938fd» sí llevan cifras, pero no al final y sin separador de asignación;
# «06_models.py::canonical» empieza por cifra y no por letra. El umbral de dos dígitos es el que hace daño:
# partir «=1» no cambia ninguna magnitud, partir «=11» ya imprime «1».
_NUM_ETIQUETA_RE = re.compile(r"^[^\W\d_]{1,24}=\d{2}[\d.,·   ]*[%‰)\]]*[.,;:]?$")


# MODO REVISTA (`set_journal_atoms(True)`; apagado por defecto, y entonces nada de lo que sigue se ejecuta): el
# trozo indivisible se define por donde LibreOffice puede partir de verdad (UAX #14), que no es por donde partía
# la regla del corpus. Medido sobre el suplemento de la revista (2026-09-09, lectores de la segunda ronda):
#   · «29 587/1 151 475»: la barra entre cifras NO es punto de corte (SY × NU) y los espacios finos de millares
#     son pegamento (GL), de modo que el trozo entero es indivisible; el corpus lo medía en dos mitades y la
#     columna salía más estrecha que el trozo: «1 151 4|75» partido dentro de la cifra;
#   · «(−20·1»: el signo delante de una cifra no se separa de ella (PR × NU, HY × NU); el corpus partía en el
#     signo y no medía «(−»;
#   · «30·0–42·1» y «2019–2024»: la raya SÍ es punto de corte (BA), por eso el corpus la partía; en modo revista
#     los rangos de las celdas llegan ATADOS con un unificador a ambos lados (journal_config.tie_ranges) y el
#     trozo atado se mide entero, que es lo que hace falta para que ninguna línea abra con «–2024»;
#   · el espacio de anchura cero (U+200B, `journal_config.soft_breaks`) es un punto de corte que el modo revista
#     mete dentro de las rutas de archivo y las URL muy largas para que una columna no tenga que medir 34 cm.
# Los caracteres que sólo aparecen en trozos del modo revista llevan aquí su avance real para `_ancho_numero`;
# en un trozo del corpus no pueden aparecer (la regla del corpus parte por ellos), así que la medida del corpus
# no cambia.
JOURNAL_ATOMS = False
_NUM_BREAK_JOURNAL_RE = re.compile("[ \t\n\r\f\v\u200b|\\\\]+|/(?!\\d)|-(?!\\d)|(?<!\u2060)[‐‑‒–—―](?!\u2060)")
_NUM_ATOM_JOURNAL_RE = re.compile("^[(\\[<>≤≥≈~±−+-]*\\d[\\d.,·\xa0\u202f\u2009\u2060–−+/-]*[%‰)\\]]*[.,;:]?$")
_ANCHO_NUM["\u2060"] = 0.0
_ANCHO_NUM["\u200b"] = 0.0
_ANCHO_NUM["–"] = 0.500
_ANCHO_NUM["-"] = 0.333
_ANCHO_NUM["/"] = 0.278


def set_journal_atoms(flag: bool) -> None:
    """Enciende (modo revista) o apaga la definición de trozo indivisible de UAX #14 (véase arriba)."""
    global JOURNAL_ATOMS
    JOURNAL_ATOMS = bool(flag)


def numeros_de(texto) -> list[str]:
    """Los NÚMEROS de una celda: los trozos que Word no puede partir sin romper una cifra en dos líneas."""
    if JOURNAL_ATOMS:
        return [t for t in _NUM_BREAK_JOURNAL_RE.split(str(texto).replace("\n", " "))
                if t and any(c.isdigit() for c in t) and (_NUM_ATOM_JOURNAL_RE.match(t) or _NUM_ETIQUETA_RE.match(t))]
    return [t for t in _NUM_BREAK_RE.split(str(texto).replace("\n", " "))
            if t and any(c.isdigit() for c in t) and (_NUM_ATOM_RE.match(t) or _NUM_ETIQUETA_RE.match(t))]


_PALABRA_RE = re.compile("[\\s\u200b]+")


def _palabras(texto) -> list[str]:
    """Las palabras de una celda tal como puede partirlas el maquetador: por blancos y por el espacio de anchura
    cero (U+200B) que el modo revista mete en las rutas largas. Sin U+200B es exactamente `str.split()`."""
    return [w for w in _PALABRA_RE.split(str(texto).replace("\n", " ")) if w]


def _min_numeros_cm(textos_por_col, cols=None, fuente_pt: float = 7.0) -> list[float]:
    """Ancho mínimo de cada columna para que ninguno de sus números se parta (cabecera incluida)."""
    pad_cm, seguro = CELL_PAD_CM, 1.08
    out = []
    for j, celdas in enumerate(textos_por_col):
        anchos = [_ancho_numero(x, fuente_pt) for t in celdas for x in numeros_de(t)]
        if cols is not None:
            anchos += [_ancho_numero(x, fuente_pt, bold=True) for x in numeros_de(cols[j])]
        out.append(max(anchos or [0.0]) * seguro + pad_cm)
    return out


def _repartir_para_numeros(anchos, necesita, blando, duro):
    """Sube cada columna hasta el ancho de su número más largo quitándoselo a las que pueden partir texto.

    Dos niveles de donante, en este orden: primero lo que a una columna le sobra por encima de su CABECERA
    (ceder ahí no parte nada), y sólo si no basta, lo que le sobra por encima de su propio número y del
    carácter más ancho que imprime. La suma de los anchos no cambia."""
    salida = list(anchos)
    n = len(salida)
    for piso in (blando, duro):
        falta = [max(0.0, necesita[j] - salida[j]) for j in range(n)]
        total_falta = sum(falta)
        if total_falta < 1e-9:
            break
        sobra = [max(0.0, salida[j] - piso[j]) for j in range(n)]
        total_sobra = sum(sobra)
        if total_sobra < 1e-9:
            continue
        mueve = min(total_sobra, total_falta)
        for j in range(n):
            salida[j] += falta[j] * mueve / total_falta - sobra[j] * mueve / total_sobra
    return salida



# ---------------------------------------------------------------------------
# El signo de porcentaje no se queda solo en la línea siguiente
# ---------------------------------------------------------------------------
# El español escribe «1,1 %» con espacio entre la cifra y el signo (el inglés lo pega: «1.1%»). Escrito con
# el espacio NORMAL, ese blanco es un punto de corte como cualquier otro: en las tablas suplementarias, con
# columnas de 1 a 2 cm, Word imprimía «26 (1,1» en una línea y «%)» en la siguiente, y el lector encuentra
# un paréntesis y un signo huérfanos debajo de una cifra que parece no llevar unidad. Medido sobre los doce
# documentos del 2026-09-08: 1.285-1.290 fragmentos huérfanos por documento largo español, en 34 páginas, y
# 28 en cada documento largo INGLÉS (la columna «RSE» de la tabla de diseño complejo, que sí lleva espacio).
#
# El arreglo vive AQUÍ y no en los diez módulos que dan formato a un porcentaje, porque aquí pasa TODO lo
# que se imprime —celda, cabecera, nota y párrafo— y así no puede quedarse un generador fuera. Se cambia el
# blanco por un espacio DURO: la misma composición, el mismo número, y un trozo que Word ya no puede partir.
# Que el trozo sea indivisible obliga a la otra punta: `_NUM_BREAK_RE` dejó de tomar el espacio duro por
# punto de corte, de modo que la columna se mide sobre «1,1\u00a0%» entero y no sobre «1,1».
_PCT_BREAK_RE = re.compile(r"(?<=\d)[ \t\u2009\u202f]+(?=%)")


def pct_indivisible(texto):
    """«1,1 %» con espacio duro: el signo de porcentaje nunca cae solo en la línea siguiente."""
    return _PCT_BREAK_RE.sub("\u00a0", str(texto))


#: Un nombre compuesto con raya («Gauss–Newton», «Getis–Ord», «Benjamini–Hochberg») no debe partirse en dos
#: líneas. La raya es clase «break after» de Unicode, de modo que sin ayuda el corte cae detrás de ella; con un
#: unificador SÓLO detrás, el corte se muda delante y la línea siguiente abre con la raya, que es peor. Medido
#: en esta cadena (python-docx → LibreOffice → PDF) sobre catorce posiciones de corte por variante: sin ayuda
#: 6 cortes, con unificador detrás 4 (todos delante de la raya), con unificador a AMBOS lados 0.
#: U+FEFF, not U+2060: both stop the break, but LibreOffice stretches justified text at a WORD JOINER and
#: not at a ZERO WIDTH NO-BREAK SPACE (measured: 3 gaps of up to 1·21 pt against none over the same sweep).
_WJ = "\ufeff"
_COMPOUND_DASH_RE = re.compile(r"(?<=[^\W\d_])\u2013(?=[^\W\d_])", re.UNICODE)


def compound_indivisible(texto):
    """La raya que une dos palabras queda atada por los dos lados; los rangos numéricos («2019–2024») no."""
    return _COMPOUND_DASH_RE.sub(_WJ + "\u2013" + _WJ, str(texto))


def texto_indivisible(texto):
    """Las dos reglas de atadura que toda cadena impresa atraviesa: el porcentaje y el nombre compuesto."""
    return compound_indivisible(pct_indivisible(texto))


def _cell_pt(cell) -> float | None:
    """Cuerpo real de una celda: el primer run con tamaño (el primero está vacío, véase insertar_tabla)."""
    for p in cell.paragraphs:
        for r in p.runs:
            if r.font.size is not None:
                return float(r.font.size.pt)
    return None


def _medir_tabla(table, ncols: int) -> dict:
    """Lee de la tabla YA construida lo que decide si un número cabe: por columna, el número más ancho, la
    palabra de cabecera más ancha, el carácter más ancho y el cuerpo mayor."""
    necesita, cabecera, cuerpo = [0.0] * ncols, [0.0] * ncols, [0.0] * ncols
    filas = []
    for i, row in enumerate(table.rows):
        celdas = row.cells
        fila = []
        for j in range(min(ncols, len(celdas))):
            cell = celdas[j]
            pt = _cell_pt(cell)
            if pt is None:
                fila.append(None)
                continue
            txt = cell.text
            cuerpo[j] = max(cuerpo[j], pt)
            ancho = max([_ancho_numero(x, pt, bold=(i == 0)) for x in numeros_de(txt)] or [0.0])
            necesita[j] = max(necesita[j], ancho + CELL_PAD_CM if ancho else 0.0)
            if i == 0:
                for w in str(txt).split():
                    cabecera[j] = max(cabecera[j], _ancho_texto(w, pt, bold=True) + CELL_PAD_CM)
            fila.append((cell, pt, ancho))
        filas.append(fila)
    return dict(necesita=necesita, cabecera=cabecera, cuerpo=cuerpo, filas=filas)


def _proteger_numeros(table, anchos_cm):
    """Reparto final: ninguna columna más estrecha que su número más largo; el total no cambia.

    Se mide sobre la tabla construida —no sobre el DataFrame— para que valga también cuando el posproceso
    de 10_manuscript recalcula los anchos apaisados y vuelve a llamar aquí: ésta es la última mano que toca
    la rejilla, y por eso es donde se puede GARANTIZAR la regla."""
    ncols = len(anchos_cm)
    if ncols == 0 or not table.rows:
        return list(anchos_cm)
    m = _medir_tabla(table, ncols)
    if not any(m["necesita"]):
        return list(anchos_cm)
    pide = [x + NUM_HOLGURA_CM if x else 0.0 for x in m["necesita"]]
    car = [CELL_PAD_CM + _EM_ANCHO * (pt or 7.0) / 28.3465 for pt in m["cuerpo"]]
    duro = [max(pide[j], car[j]) for j in range(ncols)]
    blando = [max(duro[j], m["cabecera"][j]) for j in range(ncols)]
    nuevos = _repartir_para_numeros(list(anchos_cm), pide, blando, duro)
    # El cuerpo reducido sólo se toca cuando la tabla ya está en su ancho DEFINITIVO —la caja apaisada de
    # 24,7 cm—, nunca en el paso vertical intermedio: una tabla ancha se compone primero a 16 cm y el
    # posproceso de 10_manuscript la rehace apaisada, así que encoger celdas a 16 cm dejaría una tabla con
    # dos cuerpos distintos por un ahogo que a 24,7 cm ya no existe. Una tabla que se QUEDA vertical no lo
    # necesita: si sus mínimos caben en 16 cm, sus números caben con ellos, y si no caben, el posproceso la
    # gira. En los doce documentos de 2026-09-07 esta rama no se usa ni una vez.
    if sum(anchos_cm) > TEXT_WIDTH_CM + 0.5:
        _encoger_celdas_rebeldes(m, nuevos)
    return nuevos


def _encoger_celdas_rebeldes(medida: dict, anchos_cm) -> int:
    """Último recurso: la celda cuyo número sigue sin caber tras repartir se compone algo más pequeña.

    Nunca la fila de cabecera (el posproceso lee de ella el cuerpo de la tabla) y nunca por debajo de
    `NUM_MIN_PT`."""
    tocadas = 0
    for i, fila in enumerate(medida["filas"]):
        if i == 0:
            continue
        for j, dato in enumerate(fila):
            if dato is None or j >= len(anchos_cm):
                continue
            cell, pt, ancho = dato
            util = anchos_cm[j] - CELL_PAD_CM
            if ancho <= util + 1e-9 or ancho <= 0 or util <= 0:
                continue
            nuevo = max(NUM_MIN_PT, int(pt * util / ancho * 4) / 4)
            if nuevo >= pt:
                continue
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(nuevo)
            tocadas += 1
    return tocadas


def numeros_partidos(table) -> list[dict]:
    """Comprobación: los números de una tabla YA compuesta que no caben en el ancho de su columna.

    Devuelve una lista vacía cuando ninguna línea puede terminar dentro de un número. Es la misma medida
    que impone `_proteger_numeros`, leída al revés, y la usan `revisar_documento` y la prueba de la fase 4f."""
    grid = table._tbl.find(qn("w:tblGrid"))
    if grid is None:
        return []
    anchos = [int(gc.get(qn("w:w")) or 0) / 567.0 for gc in grid.findall(qn("w:gridCol"))]
    m = _medir_tabla(table, len(anchos))
    fallos = []
    for i, fila in enumerate(m["filas"]):
        for j, dato in enumerate(fila):
            if dato is None or j >= len(anchos):
                continue
            cell, pt, ancho = dato
            if ancho <= 0:
                continue
            util = anchos[j] - CELL_PAD_CM
            if ancho > util + 1e-9:
                peor = max(numeros_de(cell.text), key=lambda x: _ancho_numero(x, pt, bold=(i == 0)))
                fallos.append(dict(row=i, col=j, number=peor, pt=pt, width_cm=round(anchos[j], 3),
                                   needs_cm=round(ancho + CELL_PAD_CM, 3)))
    return fallos


def revisar_documento(path) -> list[dict]:
    """Recorre un DOCX ya construido y devuelve todo número que pueda quedar partido entre dos líneas.

    Es la comprobación que pide la tarea F4-1: se pasa sobre los doce documentos publicados y tiene que
    salir vacía. Mide sobre la rejilla impresa y el cuerpo impreso de cada celda, de modo que ve la tabla
    tal como la compone Word —incluidas las que el posproceso de 10_manuscript rehace apaisadas—."""
    doc = Document(str(path))
    fallos = []
    for k, tbl in enumerate(doc.tables):
        for f in numeros_partidos(tbl):
            fallos.append(dict(table=k, **f))
    return fallos


# ---------------------------------------------------------------------------
# Ninguna cifra se queda sin su unidad: la comprobación sobre el documento IMPRESO
# ---------------------------------------------------------------------------
# `revisar_documento` mide la REJILLA del DOCX y ve un número a punto de partirse antes de imprimirlo. No ve
# lo otro que el lector encuentra en la página: una cifra arriba y su unidad sola debajo. Son dos defectos
# hermanos —un trozo que se lee como UNA cosa, partido en dos líneas— y hasta ahora sólo el primero tenía
# guardián; el segundo llegó al papel 1.286-1.292 veces por documento largo español y 29 por documento largo
# inglés. Esta comprobación es la pareja de aquélla: se pasa sobre el TEXTO del PDF ya compuesto, que es donde
# el defecto existe (en el DOCX la celda dice «26 (1,1 %)» y parece sana; el corte lo pone Word al maquetar).
#
# LAS DOS CARAS DEL MISMO SUCESO, que son las dos que se buscan:
#   A. una línea que EMPIEZA por el signo, con la línea de encima terminando en cifra — el caso de la prosa
#      justificada, donde la cifra queda al final del renglón y el signo abre el siguiente;
#   B. una cifra al final de su celda y la unidad sola en la línea siguiente de esa MISMA columna — el caso de
#      la tabla, donde ni la cifra ni el signo tocan el margen y lo que los une es la vertical.
#
# Lo que NO es un huérfano, y por eso se pide una condición más: un signo que en su línea va pegado a su
# propia cifra («35,6 %» de la prosa, a un espacio) no es huérfano aunque encima de él pase otra cifra. Sin
# esa salvedad la comprobación marcaba 28 párrafos correctos del artículo español.
UNIDADES = ("%", "‰")
_UNIDAD_SOLA_RE = re.compile(r"^[%‰][)\]]?[.,;]?$")
_CIFRA_FINAL_RE = re.compile(r"^\(?\d[\d.,\u00a0\u202f\u2009]*$")


def _piezas(linea: str) -> list[tuple[int, int, str]]:
    """Cada trozo no blanco de una línea con la COLUMNA en la que se imprime (pdftotext -layout)."""
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", linea)]


def unidades_partidas(texto: str) -> list[dict]:
    """Toda unidad que el documento impreso deja sola en la línea siguiente a la cifra que la gobierna.

    `texto` es la salida de `pdftotext -layout` del PDF construido. Devuelve una lista vacía cuando ninguna
    cifra perdió su unidad. Es la pareja de `revisar_documento`, del otro lado de la maquetación."""
    lineas = texto.split("\n")
    fuera = []
    for i in range(len(lineas) - 1):
        arriba, abajo = _piezas(lineas[i]), _piezas(lineas[i + 1])
        if not arriba:
            continue
        # Un renglón CORRIDO no tiene huecos anchos entre sus trozos; una fila de tabla sí. La distinción
        # decide cuál de las dos caras se puede invocar: la del margen izquierdo sólo vale sobre prosa,
        # porque en una tabla el primer trozo de la línea pertenece a la primera columna y la cifra del
        # final de la línea de encima pertenece a la última, que es otra celda y no tiene nada que ver.
        corrido = all(b[0] - a[1] < 3 for a, b in zip(arriba, arriba[1:]))
        for k, (b0, b1, cola) in enumerate(abajo):
            if not _UNIDAD_SOLA_RE.match(cola):
                continue
            if k > 0 and b0 - abajo[k - 1][1] < 2:      # va pegada a su cifra en su propia línea
                continue
            hallazgo = None
            # Dentro de una tabla, la unidad huérfana está SOLA en su celda. Si lleva algo pegado a la
            # derecha es la cabeza de una glosa y no la cola de una cifra: la cabecera «% (IC 95 %)» abre
            # celda con un «%» suelto, y bajo el folio de la página anterior el detector la tomaba por
            # huérfana. En la prosa no vale la misma prueba —tras el signo sigue el renglón—, y por eso
            # sólo se le pide al caso de columna.
            solo = k + 1 >= len(abajo) or abajo[k + 1][0] - b1 >= 2
            for a0, a1, cabeza in arriba:               # B: misma columna, la cifra justo encima
                if solo and _CIFRA_FINAL_RE.match(cabeza) and min(a1, b1) - max(a0, b0) > 0:
                    hallazgo = dict(line=i + 1, head=cabeza, tail=cola, caso="columna")
                    break
            if hallazgo is None and k == 0 and b0 <= 2 and corrido and _CIFRA_FINAL_RE.match(arriba[-1][2]):
                hallazgo = dict(line=i + 1, head=arriba[-1][2], tail=cola, caso="linea")   # A: abre renglón
            if hallazgo is not None:
                fuera.append(hallazgo)
    return fuera


def revisar_pdf(path) -> list[dict]:
    """Recorre un PDF ya compuesto y devuelve toda unidad que se quedó sola bajo su cifra.

    Es la comprobación que se pasa sobre los doce documentos publicados, al lado de `revisar_documento`:
    aquélla mira la rejilla del DOCX, ésta la página impresa. Devuelve `None` si no hay `pdftotext`."""
    import subprocess
    try:
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return unidades_partidas(r.stdout) if r.returncode == 0 else None


def _min_cabeceras_cm(cols, fuente_pt: float) -> float:
    """Ancho total mínimo para que ninguna CABECERA se parta por la mitad."""
    pad_cm, seguro = 0.40, 1.08
    return sum(max([_ancho_texto(w, fuente_pt, bold=True) for w in str(c).split()] or [0.0]) * seguro + pad_cm
               for c in cols)


def _anchos(cols, textos_por_col, fuente_pt, total_cm=TEXT_WIDTH_CM):
    """Ancho de cada columna: nunca por debajo del ancho de su CABECERA mientras quede sitio.

    Cuando la suma de los mínimos no cabe —una tabla de dieciséis columnas con texto verbatim— el reparto
    a prorrata dejaba las cabeceras partidas por la mitad («Y ea r», «Weigh t», «Estimabi lity»). Ahora se
    reserva primero el ancho de las cabeceras y se reparte el resto en proporción a lo que cada columna
    pediría de más; el texto largo de las celdas sí se parte, que es donde el lector lo tolera.

    Con el suelo de las cabeceras viaja el de los NÚMEROS (tarea F4-1): cuando ni unas ni otros caben, se
    reservan los dos y, si aun así no hay sitio, manda el número. Una cabecera partida se lee («Y ea r»
    sigue diciendo «Year»); un número partido —«1,085,8» y debajo «13»— no."""
    pad_cm, seguro = 0.40, 1.08
    min_num = _min_numeros_cm(textos_por_col, cols, fuente_pt)
    min_cab, minimos, deseados = [], [], []
    for j, c in enumerate(cols):
        celdas = [str(t) for t in textos_por_col[j]]
        tok = 0.0
        for t in celdas:
            for w in _palabras(t):
                tok = max(tok, _ancho_texto(w, fuente_pt))
        cab_tok = max([_ancho_texto(w, fuente_pt, bold=True) for w in str(c).split()] or [0.0])
        min_cab.append(cab_tok * seguro + pad_cm)
        minimos.append(max(tok, cab_tok) * seguro + pad_cm)
        anchos_celda = sorted(max(_ancho_texto(line, fuente_pt) for line in t.split("\n")) for t in celdas) or [0.0]
        p90 = anchos_celda[int(0.9 * (len(anchos_celda) - 1))]
        cab = _ancho_texto(c, fuente_pt, bold=True) / 2.2
        deseados.append(max(p90, cab) * seguro + pad_cm)
    deseados = [max(d, m) for d, m in zip(deseados, minimos)]
    pisos = [max(c, n) for c, n in zip(min_cab, min_num)]        # cabecera Y número: los dos indivisibles
    tot_min, tot_des, tot_piso = sum(minimos), sum(deseados), sum(pisos)
    if tot_min >= total_cm:
        if tot_piso >= total_cm:
            # ni las cabeceras con sus números caben: reparto a prorrata y, encima, se rescatan los números
            # quitándole el sitio a las columnas que sí pueden partir texto
            base = [total_cm * m / tot_min for m in minimos]
            car = [pad_cm + _EM_ANCHO * fuente_pt / 28.3465] * len(base)
            duro = [max(n, c) for n, c in zip(min_num, car)]
            return _repartir_para_numeros(base, min_num, [max(d, c) for d, c in zip(duro, min_cab)], duro)
        libre = total_cm - tot_piso
        extra = [m - p for m, p in zip(minimos, pisos)]
        tot_extra = sum(extra) or 1.0
        return [p + libre * e / tot_extra for p, e in zip(pisos, extra)]
    if tot_des <= total_cm:
        return [total_cm * d / tot_des for d in deseados]
    holgura = total_cm - tot_min
    extra = [d - m for d, m in zip(deseados, minimos)]
    tot_extra = sum(extra) or 1.0
    return [m + holgura * e / tot_extra for m, e in zip(minimos, extra)]


def insertar_tabla(doc, df: pd.DataFrame, fuente_pt=None, block_bold: bool = False, max_pt: float | None = None,
                   min_pt: float | None = None, cant_split: bool = False):
    """Tabla del documento. `block_bold` (modo revista) imprime en NEGRITA y a todo lo ancho —celdas
    fusionadas— las filas de encabezado interno (la primera celda con texto y las demás vacías), que llevan
    keepNext para no quedarse solas al pie de una página; por defecto van en cursiva en su columna, como
    siempre. `max_pt` acota el cuerpo automático (la revista pide 8 pt) y `min_pt` (modo revista) es el suelo:
    sin él una tabla que no cabe baja como siempre hasta 6 pt antes de partir palabras. `cant_split` (modo revista)
    marca cada fila como indivisible (w:cantSplit: una fila nunca se parte entre dos páginas) y ata las dos últimas
    filas entre sí y a la nota (keepNext), para que ninguna página abra con una fila suelta y su nota."""
    df = df.fillna("").astype(str).map(texto_indivisible)
    cols = [texto_indivisible(c) for c in df.columns]
    ncols = len(cols)
    if fuente_pt is None:
        fuente_pt = 9 if ncols <= 5 else (8.5 if ncols <= 7 else (7.5 if ncols <= 9 else 7))
        if max_pt is not None:
            fuente_pt = min(fuente_pt, max_pt)
        if min_pt is not None:                  # modo revista: el cuerpo por defecto de una tabla ancha (7–7,5 pt) sube al suelo
            fuente_pt = max(fuente_pt, float(min_pt))
        # Una tabla muy ancha (16 columnas en el diccionario JUNAEB) no cabe ni con las columnas en su
        # mínimo: al repartir el ancho a prorrata, las cabeceras se partían por la mitad («Y ea r»,
        # «Weigh t», «Estimabi lity»). Antes de partir palabras se baja el cuerpo, con suelo de 6 pt.
        suelo = max(6.0, float(min_pt)) if min_pt is not None else 6.0
        while fuente_pt > suelo and _min_cabeceras_cm(cols, fuente_pt) > TEXT_WIDTH_CM:
            fuente_pt = round(fuente_pt - 0.5, 1)
    tbl = doc.add_table(rows=1, cols=ncols)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_autofit(tbl, TEXT_WIDTH_CM)
    textos = [[str(v) for v in df.iloc[:, j].tolist()] for j in range(ncols)]
    anchos = _anchos(cols, textos, fuente_pt)
    izquierda = {0} | {j for j in range(ncols) if sorted(len(t) for t in textos[j])[len(textos[j]) // 2] > 22}
    hdr = tbl.rows[0]
    _repeat_header(hdr)
    for j, c in enumerate(cols):
        cell = hdr.cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT if j in izquierda else WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before, p.paragraph_format.space_after, p.paragraph_format.line_spacing = Pt(3), Pt(3), 1.0
        _set_font(p.add_run(c), size=fuente_pt, bold=True)
        _cell_border(cell, top={"sz": 12}, bottom={"sz": 8}, left=None, right=None)
    n = len(df)
    for i in range(n):
        row = tbl.add_row()
        block_header = all(str(df.iat[i, k]) == "" for k in range(1, ncols))
        for j in range(ncols):
            val = str(df.iat[i, j])
            cell = row.cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            if j in izquierda:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                if j == 0 and val.startswith("  "):
                    p.paragraph_format.left_indent = Cm(0.35)
                    val = val.strip()
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before, p.paragraph_format.space_after, p.paragraph_format.line_spacing = Pt(1.5), Pt(1.5), 1.0
            _set_font(p.add_run(val), size=fuente_pt, bold=(block_header and j == 0 and block_bold),
                      italic=(block_header and j == 0 and not block_bold))
            _cell_border(cell, top=None, bottom={"sz": 12} if i == n - 1 else None, left=None, right=None)
        if block_header and block_bold and ncols > 1:
            # a todo lo ancho: la fusión concatena los párrafos vacíos de las celdas absorbidas y hay que quitarlos,
            # o el encabezado se imprime con siete líneas en blanco debajo
            fusionada = row.cells[0].merge(row.cells[ncols - 1])
            for extra in fusionada.paragraphs[1:]:
                extra._p.getparent().remove(extra._p)
            for par in fusionada.paragraphs:          # el encabezado interno viaja con la fila que anuncia
                par.paragraph_format.keep_with_next = True
    if cant_split:
        for row in tbl.rows:
            tr_pr = row._tr.get_or_add_trPr()
            if tr_pr.find(qn("w:cantSplit")) is None:
                tr_pr.append(OxmlElement("w:cantSplit"))
        for row in list(tbl.rows)[-2:]:
            for cell in row.cells:
                for par in cell.paragraphs:
                    par.paragraph_format.keep_with_next = True
    _aplicar_anchos(tbl, anchos)
    return tbl


def agrupar_por_columna(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """Filas agrupadas bajo un ENCABEZADO INTERNO (modo revista): cada tramo consecutivo de un mismo valor
    de `col` abre una fila cuya primera celda es ese valor y las demás van vacías, y la columna desaparece.
    `insertar_tabla(block_bold=True)` imprime esas filas en negrita y a todo lo ancho."""
    if col not in df.columns or df.shape[1] < 2:
        return df
    resto = [c for c in df.columns if c != col]
    filas, previo = [], object()
    for _, fila in df.iterrows():
        if fila[col] != previo:
            previo = fila[col]
            filas.append({c: "" for c in resto} | {resto[0]: str(previo)})
        filas.append({c: fila[c] for c in resto})
    return pd.DataFrame(filas, columns=resto)


def rotulo_tabla(doc, etiqueta, titulo_txt, pt: float = 11, bold_title: bool = False):
    """Rótulo («Table 1») y título de una tabla, en dos párrafos que viajan con ella. En modo revista
    (`pt=10, bold_title=True`) los dos van en negrita a 10 pt: el «main table heading» de la revista."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after, p.paragraph_format.line_spacing, p.paragraph_format.keep_with_next = Pt(12), Pt(0), 1.0, True
    _set_font(p.add_run(etiqueta), size=pt, bold=True)
    p2 = doc.add_paragraph()
    p2.paragraph_format.space_before, p2.paragraph_format.space_after, p2.paragraph_format.line_spacing, p2.paragraph_format.keep_with_next = Pt(0), Pt(4), 1.0, True
    _set_font(p2.add_run(texto_indivisible(titulo_txt)), size=pt, bold=bold_title, italic=not bold_title)


def nota_tabla(doc, texto, lang, size: float = 9, refs_bold: bool = True):
    """Nota al pie de una tabla. NO se parte entre dos páginas (`keep_together`).

    Cuando detrás de la tabla se abre una sección apaisada —tabla ancha— el corte de sección obliga a
    empezar página, de modo que lo que la nota deje al otro lado del corte se queda solo en una página
    portrait. Impreso, eso daba páginas con dos líneas sueltas a media frase («…intervención con efecto
    estimable. Archivos fuente: …»). Con `keep_together` la nota viaja entera: la página que abre lo hace
    con la nota completa —rotulada «Nota.»— y no con su cola. El sitio en blanco que queda al pie de la
    tabla es el mismo; lo que cambia es que se lee un bloque entero y no un fragmento."""
    if not texto:
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.line_spacing, pf.keep_together = Pt(3), Pt(12), 1.0, True
    _set_font(p.add_run(WORDS["note"][lang] + " "), size=size, italic=True)
    _add_text(p, texto, size=size, refs_bold=refs_bold)     # modo revista: las referencias cruzadas van sin negrita


MAX_ALTO_CM = 21.5

# ---------------------------------------------------------------------------
# Láminas a página completa
# ---------------------------------------------------------------------------
# Las láminas del estudio se dibujan 1:1 a 180 × 245 mm (600 ppp) para imprimirse UNA POR PÁGINA sin
# encogerse. Una página A4 con los márgenes del cuerpo (2,5 cm) sólo deja 16,0 × 24,7 cm, de modo que la
# lámina se reducía al 88 % y su leyenda se partía entre dos páginas. Aquí cada lámina vertical abre su
# propia SECCIÓN con márgenes de 3–7 mm: 19,6 × 28,68 cm de caja. En esa caja tienen que caber, en este
# orden, la frase de presentación que la precede en el texto (si es corta), la imagen y la leyenda
# completa. Ese presupuesto —y no un ajuste arbitrario— decide el ancho impreso:
#
#   ancho = min(180 mm, (alto de caja − presentación − leyenda − holgura) / (alto/ancho de la lámina))
#
# La lámina NO se encoge nunca: se imprime a sus 180 mm —reducirla al ancho de la columna de texto
# bajaría sus anotaciones de 6 pt a 5,3 pt— y lo que se ajusta al presupuesto de la página es el texto.
# Cuando la leyenda no cabe entera, continúa en la página siguiente, que no se desperdicia: la lámina
# siguiente se coloca en ella, con su presupuesto vertical reducido en lo que ocupa la cola.
# En la página de la lámina entran además los títulos de sección que la preceden («Análisis espacial y
# correlación territorial»), porque dejarlos fuera imprimiría una página con un solo encabezado.
# Una lámina APAISADA heredada (432 × 277 mm) no entra en este camino: ocupa media página y sigue en el
# flujo del texto como hasta ahora.
#
# PAGINACIÓN (fase 4d). La frase de presentación se quedaba SIEMPRE fuera: a 12 pt con interlineado 1,5
# ocupa 2,4–3,2 cm y la caja sólo dejaba 3,2 cm para ella y la leyenda juntas, así que las 54 láminas
# suplementarias imprimían 43 páginas con dos líneas y nada más. Tres cambios lo cierran:
#
#   1. la caja de la sección de lámina se estira a 19,6 × 28,68 cm (márgenes de 3,0–7,2 mm; el pie con el
#      número de página, 9 pt a 2,5 mm del borde, queda 1 mm por debajo de la caja);
#   2. la ENTRADILLA viaja SIEMPRE con su lámina —con keepNext, sin excepción— y se compone al cuerpo que
#      quepa (12 → 9 → 8 → 7,5 → 7 pt), nunca menor que la leyenda: es la presentación de la lámina, no un
#      párrafo del cuerpo;
#   3. cuando ni al suelo de la escala (7,0 pt) cabe la leyenda entera, su cola pasa a la página siguiente,
#      que NUNCA la lleva sola: en ella entra la lámina siguiente, con su presupuesto reducido en lo que la
#      cola ocupa. La cola se compone al mismo cuerpo que su cabeza —la leyenda es un solo párrafo— y sólo
#      cuando la comprobación dice que la lámina siguiente ya no cabe en esa página se baja medio punto
#      (`PLATE_CAP_STRAND_PT`), que es lo único que devuelve el presupuesto sin cobrárselo al lector;
#   4. la leyenda que no cabe entera bajo su lámina se parte SIEMPRE en el código (`split_caption_lines`) y
#      su cola se imprime rotulada «Figura N (continuación).» al principio de la página siguiente. Dónde
#      cae esa página depende del sitio, pero el rótulo no: con la sección cerrada detrás —las cinco
#      figuras del artículo y la última lámina de cada tanda— la cola pasa al CUERPO del texto después del
#      corte, donde la sigue el párrafo siguiente y la página se llena (sin eso, el artículo imprimía 3–4
#      páginas por documento con cuatro líneas y 28 cm de papel en blanco); dentro de una tanda la cola abre
#      la página de la lámina SIGUIENTE, encima de su entradilla, y el salto de página lo pone la propia
#      cola. Hasta la fase 4j sólo se rotulaba el primer caso y el segundo viajaba como un párrafo que Word
#      partía por su cuenta: 100 colas sin rótulo en los ocho documentos largos, hasta el 88 % de una
#      leyenda impresa en una página que no era la de su lámina y sin nada que dijera de quién era;
#   5. bajo la lámina se imprimen SIEMPRE al menos `PLATE_CAP_MIN_LINES` líneas de leyenda. El reparto de
#      líneas admitía cero —el presupuesto descuenta la cola de la leyenda anterior, que es una predicción
#      y a veces no llega— y una lámina salió impresa con el rótulo «Figura S54.» y ni una línea debajo.
#
# LO QUE NO SE PUEDE CERRAR. Una lámina de 245 mm deja 3,88 cm de texto en una caja A4 de 28,68 cm y hay
# 18 de las 54 leyendas del suplemento que, aun a 6,5 pt y con la entradilla a 7,0, piden entre 4,3 y 5,6 cm.
# En una tanda larga de ésas la cola crece hasta que la lámina siguiente ya no cabe en su página: quedan
# CUATRO páginas por documento en inglés y SEIS en español con la cola de una leyenda y nada más (fase 4j:
# con la cola compuesta de verdad, rótulo incluido, la cuenta dejó de quedarse corta y son las que la
# aritmética pide). Sale de la aritmética de la caja, no de la composición, y la alternativa —bajar la
# leyenda a 6,0 pt en trece láminas— cambia unas páginas flojas por trece leyendas ilegibles. Por eso
# 7,0 pt es el suelo y `PLATE_CAP_STRAND_PT` (6,5) el único escalón por debajo: se gasta donde salva una
# página entera, no donde sólo evita partir un párrafo. Y esas páginas no son párrafos huérfanos: llevan
# de 938 a 1.974 caracteres y abren con «Figura N (continuación).» y su número de figura.
PAGE_W_CM, PAGE_H_CM = 21.0, 29.7                     # A4
PLATE_MARGIN_CM = dict(top=0.30, bottom=0.72, left=0.70, right=0.70, header=0.15, footer=0.25)
# La caja de la sección de lámina mide 19,6 × 28,68 cm. Los 3,3 mm que se le ganaron a los márgenes en la
# fase 4d (arriba 4,5 → 3,0 mm, abajo 9,0 → 7,2 mm con el pie a 2,5 mm del borde y el folio a 9 pt) valen
# UNA página casi vacía por documento: con 28,35 cm de caja, tres colas de leyenda por documento crecían
# hasta empujar la lámina siguiente fuera de su página; con 28,68 cm queda una sola. El folio (9 pt,
# 3,65 mm de alto, borde inferior a 2,5 mm del papel) ocupa de 29,09 a 29,45 cm y la caja termina en
# 28,98 cm: 1,0 mm de aire entre el texto y el número de página.
BODY_MARGIN_CM = dict(top=2.5, bottom=2.5, left=2.5, right=2.5, header=1.25, footer=1.25)
PLATE_TEXT_W_CM = PAGE_W_CM - PLATE_MARGIN_CM["left"] - PLATE_MARGIN_CM["right"]     # 19,6 cm
PLATE_TEXT_H_CM = PAGE_H_CM - PLATE_MARGIN_CM["top"] - PLATE_MARGIN_CM["bottom"]     # 28,68 cm
PLATE_NATURAL_W_CM = 18.0        # 180 mm: el ancho al que se dibuja la lámina
PLATE_MIN_W_CM = 18.0            # y también el suelo: la lámina se imprime SIEMPRE a 1:1, nunca reducida.
                                 # Reducirla al ancho de la columna de texto (160 mm) la encogía al 89 % y
                                 # bajaba sus anotaciones de 6 pt a 5,3 pt, por debajo del mínimo de la
                                 # revista. La caja de la sección de lámina (196 × 286,8 mm) admite los 180
                                 # mm; lo que cede cuando no cabe todo es la LEYENDA (continúa en la
                                 # página siguiente) y la entradilla (se queda en el texto), no la lámina.
PLATE_LEAD_MAX_CM = 5.0          # tope de la entradilla que viaja con la lámina: hasta seis líneas de cuerpo.
                                 # Las frases de presentación del suplemento ocupan 3–5 líneas y TIENEN que
                                 # entrar en la página de la lámina: si se quedaran fuera, la sección anterior
                                 # terminaría con una sola frase y se imprimiría una página casi vacía. Un
                                 # párrafo de Resultados (11–13 cm) no es una entradilla y se queda en el texto.
# TIPOGRAFÍA DE LA LEYENDA (fase 4e, tarea Y2). El SUELO de la leyenda es 7,0 pt y la leyenda no se
# encoge por debajo de él para caber: cuando no cabe, se PARTE. Antes había un escalón más —6,0 pt, el
# suelo de las anotaciones dibujadas dentro de la lámina— que se usaba para meter entera una leyenda que se
# quedaba a una línea de caber, y seis leyendas de los doce documentos se imprimían así: la Figura 3 de los
# cuatro documentos en español y la Figura S54 de los dos con_rett en español. Seis puntos es tamaño de
# anotación dentro de un gráfico —una palabra suelta que se lee junto al trazo que rotula—, no tamaño de un
# párrafo de trece a dieciséis líneas de texto corrido, que es lo que es una leyenda de lámina. Las tres salidas
# posibles se midieron sobre los doce documentos:
#
#   * ENCOGER LA LÁMINA los pocos milímetros que liberan las líneas que faltan. Bajo una lámina de 245,0 mm
#     la caja de 28,68 cm deja 3,88 cm, que a 7,0 pt son TRECE líneas; la leyenda de la Figura 3 pide
#     dieciséis. Habría que bajar la lámina a 237,3 mm de alto (174,3 mm de ancho) y con ella sus
#     anotaciones de 6,0 a 5,8 pt, POR DEBAJO del suelo de la revista. La lámina se imprime 1:1
#     (`PLATE_MIN_W_CM`) y esta salida está cerrada por el propio estándar del estudio.
#   * APRETAR EL INTERLINEADO Y PARTIR PALABRAS. El interlineado ya es sencillo (`LINE_FACTOR` 1,15, medido
#     sobre el PDF); bajarlo a 1,10 gana media línea de las tres que faltan, y la partición de palabras de
#     Word en un párrafo justificado de 7 pt gana un 3–6 %: ninguna de las dos —ni las dos juntas— llega al
#     13 % que hace falta, y las dos empeoran la lectura del mismo párrafo que se quiere hacer legible.
#   * PARTIR LA LEYENDA Y HACER QUE LA COLA CAIGA ACOMPAÑADA. Es la que se implementa. La cola no se queda
#     sola en ninguno de los doce documentos: detrás de las cinco láminas del artículo y de la S54 hay
#     entre 6 y 189 bloques de texto corrido (un título de sección y sus párrafos, o las tablas
#     suplementarias), que es lo que llena la página que abre la cola; y dentro de una tanda de láminas la
#     cola cae sobre la página de la lámina SIGUIENTE. El builder lo COMPRUEBA en vez de suponerlo, y sólo
#     si la comprobación falla —si la cola fuera a quedarse sola— usa el único escalón que queda por debajo
#     del suelo, `PLATE_CAP_STRAND_PT`.
PLATE_CAP_PT = (9.0, 8.5, 8.0, 7.5, 7.0)   # tamaños de leyenda admisibles, de mayor a menor; el último es
                                 # el SUELO: ninguna leyenda se compone por debajo de 7,0 pt para caber.
PLATE_CAP_MIN_PT = PLATE_CAP_PT[-1]        # 7,0 pt, el suelo tipográfico de una leyenda de lámina
PLATE_CAP_STANDALONE_PT = PLATE_CAP_MIN_PT # cuando detrás de la lámina se CIERRA la sección —las figuras del
                                 # artículo y la última lámina de la tanda—, la cola no cae sobre otra lámina
                                 # sino sobre el texto corrido, no le quita presupuesto a nadie y no hay
                                 # ninguna razón para apretar la leyenda: se queda en el suelo.
PLATE_CAP_STRAND_PT = 6.5        # ÚNICO escalón por debajo del suelo, y sólo para lo que el suelo no puede
                                 # resolver por sí mismo: la leyenda cuya cola se quedaría SOLA en una página.
                                 # Ocurre en dos sitios y en los dos se comprueba, no se supone: (a) dentro de
                                 # una tanda, cuando la cola crece tanto que la lámina siguiente ya no cabe en
                                 # la página que la lleva (`_unit_min_cm`), y (b) detrás de una lámina tras la
                                 # cual se cierra la sección sin que la siga ningún bloque de texto. Si medio
                                 # punto menos NO evita la página suelta, no se usa: encoger la leyenda sin
                                 # ganar nada es el defecto que esta regla corrige. En los doce documentos de
                                 # 2026-09-07 el caso (b) no se da y el caso (a) se da en las tandas largas
                                 # del suplemento.
PLATE_CAP_FALLBACK_PT = PLATE_CAP_MIN_PT   # 7,0 pt: cuerpo de la leyenda cuando NINGUNO cabe entero. La cola
                                 # es presupuesto de la página siguiente y componerla más pequeña se lo
                                 # devuelve, pero el que paga esa devolución es el lector de las trece
                                 # líneas que van BAJO la lámina, no la página siguiente: quien devuelve el
                                 # presupuesto sin cobrárselo a nadie es `PLATE_CAP_STRAND_PT`, que sólo se
                                 # usa cuando de verdad salva una página.
PLATE_LEAD_PT = (12.0, 9.0, 8.0, 7.5, 7.0)    # cuerpos de la entradilla, de mayor a menor; nunca menor que
                                 # la leyenda de su propia lámina, para que la frase que presenta la lámina no
                                 # se lea más pequeña que el pie que la explica. Su suelo, 7,0 pt, es ahora el
                                 # mismo que el de la leyenda: entradilla y leyenda se encuentran ahí y ninguna
                                 # de las dos baja. El escalón de 7,0 pt existe para las tandas de láminas con
                                 # leyenda larga: ahí la entradilla a 7,5 pt costaba 2 mm por página que la cola
                                 # de la leyenda necesitaba.
PLATE_LEAD_LINE = 1.15           # interlineado de la entradilla cuando se compone por debajo del cuerpo
PLATE_CAP_MIN_LINES = 3          # líneas de LEYENDA que se imprimen bajo la lámina como mínimo cuando la
                                 # leyenda se parte. El presupuesto de la página se estima descontando la cola
                                 # de la leyenda ANTERIOR, y esa cola es una predicción: cuando no llega (Word
                                 # metió la leyenda entera en su propia página), la estimación deja cero líneas
                                 # y la lámina se imprime con el rótulo «Figura S54.» y ni una línea de leyenda
                                 # debajo —una figura sin pie, leída a tamaño de impresión—. Tres líneas son el
                                 # título de la leyenda y sus primeros paneles: lo mínimo para que la lámina se
                                 # entienda en su propia página. No se sube de ahí porque cada línea de más
                                 # arriesga empujar la IMAGEN a la página siguiente (la imagen lleva keepNext).
# TODA COLA VA ROTULADA (fase 4j, tarea J1). La regla es una y no admite excepción: la leyenda que no cabe
# bajo su lámina se parte EN EL CÓDIGO y su cola se imprime rotulada «Figura N (continuación).» al principio
# de la página siguiente, se cierre o no la sección detrás de la lámina. Antes se rotulaba sólo en dos casos
# —sección cerrada detrás, o desbordamiento estructural mayor que `PLATE_SPILL_LABEL_CM`— y en todos los
# demás la leyenda viajaba como UN párrafo que Word partía donde quería: en los ocho documentos largos del
# 2026-09-08 eso dejaba 100 colas sin rótulo —doce por documento largo en inglés y trece en español, las
# láminas espaciales S41 a S53—, con hasta el 88 % de una leyenda impresa fuera de la página de su lámina,
# de modo que doce o trece páginas por documento abrían con un párrafo de letra pequeña cuyo dueño no se veía. Las otras dos salidas se descartaron sobre la misma medida: ACORTAR la leyenda no se
# puede —las de las láminas espaciales llevan el aviso de lugar de atención y los recuentos por clase, que
# son norma del estudio— y ENCOGER la lámina tampoco —está fijada a 180 mm por `PLATE_MIN_W_CM`, y los
# milímetros que liberarían las líneas bajarían sus anotaciones por debajo del suelo de 6 pt de la revista—.
# Partir y rotular no quita ni una palabra a la leyenda, no toca la lámina y no mueve ninguna cifra: sólo
# pone el nombre a la cola que ya estaba impresa.
#
# LO QUE CUESTA. Al partir en el código, el corte lo decide `caption_lines_page` (una estimación) y no Word
# (que es exacto), y la estimación es CONSERVADORA: mide de más el ancho de la prosa (`_ANCHO_CAR`) y
# reserva además `PLATE_GAP_CM`. Sobre los doce PDF del 2026-09-08 la cuenta se queda una línea corta en la
# mayoría de las leyendas, nunca larga. Ese sentido del error es el que hay que tener: quedarse corto deja
# una línea de aire bajo la lámina, pasarse haría que Word partiera además la cabeza y la página siguiente
# abriera con una línea huérfana ANTES del rótulo, que es el defecto que se está cerrando.
PLATE_SPILL_LABEL_CM = 3.0       # ya NO decide quién se rotula —se rotulan todas—: marca en el informe la
                                 # leyenda que no cabe NI con la página entera a su disposición, es decir el
                                 # desbordamiento ESTRUCTURAL, que no depende de la cola de la leyenda
                                 # anterior. Lo pedía la Figura 1 del artículo (37–39 líneas); la fase 4e la
                                 # acortó y hoy ninguna leyenda de los doce documentos lo dispara. Se queda
                                 # como diagnóstico: una leyenda por encima de este umbral pide prosa más
                                 # corta, no otra composición.
PLATE_CAP_CONT_AFTER_PT = 6.0    # aire bajo la cola rotulada cuando lo que la sigue es la ENTRADILLA de la
                                 # lámina siguiente, dentro de una tanda. Los 12 pt que se usan cuando la cola
                                 # cae sobre el texto corrido son medio renglón de leyenda (0,42 cm) que ahí
                                 # no le cuesta nada a nadie y aquí se le cobran a la lámina siguiente: en una
                                 # tanda de catorce láminas con leyendas de catorce líneas, esos 12 pt por
                                 # página son casi dos páginas de más. Seis puntos separan el bloque de letra
                                 # pequeña de la frase que presenta la lámina siguiente sin gastar renglón.
PLATE_MIN_ASPECT = 1.15          # sólo las láminas VERTICALES ocupan página propia
PLATE_MIN_PX = 3500              # y sólo si se dibujaron a tamaño de lámina (≥ 3500 px de ancho)
PLATE_GAP_CM = 0.30              # holgura para los espacios entre párrafos y el redondeo de Word: 8,5 pt,
                                 # una línea de leyenda. Es la ÚNICA reserva del presupuesto, ahora que el
                                 # recuento de líneas está calibrado contra el PDF impreso.
CM_PER_PT = 1 / 28.3465
LINE_FACTOR = 1.15               # alto de línea de Times New Roman con interlineado sencillo, MEDIDO sobre el
                                 # PDF: el paso entre líneas de leyenda es 9,2 pt a 8 pt y 8,05 pt a 7 pt, es
                                 # decir 1,15 × cuerpo. El 1,20 anterior inflaba cada bloque de texto un 4 %.


def _wrapped_lines(texto: str, pt: float, ancho_cm: float) -> int:
    """Líneas que ocupa `texto` a `pt` en una columna de `ancho_cm`, con la métrica de _ancho_texto.

    El recuento es exacto, no una cota: contrastado con las leyendas impresas de las Figuras S1 (971
    caracteres a 8 pt), S3 (1410 a 7 pt) y S48 (2290 a 7 pt), que ocupan 7, 9 y 14 líneas en el PDF y 7, 9
    y 14 aquí. El 4 % de mayoración que antes se aplicaba añadía una línea entera a cada párrafo —media
    línea de leyenda y hasta un 50 % en una entradilla de dos— y era la razón de que la frase de
    presentación no cupiera nunca en la página de su lámina. La reserva del presupuesto es PLATE_GAP_CM."""
    espacio = _ancho_texto(" ", pt)
    n, cur = 1, 0.0
    for palabra in str(texto).split():
        w = _ancho_texto(palabra, pt)
        if cur and cur + espacio + w > ancho_cm:
            n, cur = n + 1, w
        else:
            cur += (espacio if cur else 0.0) + w
    return n


def _text_cm(texto: str, pt: float, ancho_cm: float, line: float = 1.0, space_before: float = 0.0,
             space_after: float = 0.0) -> float:
    """Alto en cm de un párrafo de `texto` (interlineado `line`, espacios en puntos)."""
    return _wrapped_lines(texto, pt, ancho_cm) * pt * LINE_FACTOR * line * CM_PER_PT + \
        (space_before + space_after) * CM_PER_PT


def is_full_page_plate(path) -> bool:
    """¿Es una lámina vertical a tamaño de página (180 × 245 mm) y no un gráfico apaisado heredado?"""
    try:
        with Image.open(path) as im:
            w_px, h_px = im.size
    except (OSError, ValueError):
        return False
    return w_px >= PLATE_MIN_PX and h_px / w_px >= PLATE_MIN_ASPECT


HEADING_PT = {"h1": 14, "h2": 12.5, "h3": 12}
HEADING_SPACE_BEFORE = {"h1": 18, "h2": 12, "h3": 12}


def heading_cm(kind: str, texto: str) -> float:
    """Alto de un título de sección tal como lo compone `titulo()` (para el presupuesto de la página)."""
    return _text_cm(texto, HEADING_PT[kind], PLATE_TEXT_W_CM, line=1.15,
                    space_before=HEADING_SPACE_BEFORE[kind], space_after=6)


def lead_line_spacing(pt: float) -> float:
    """Interlineado de la entradilla: 1,5 al cuerpo del texto, 1,15 cuando se compone más pequeña."""
    return 1.5 if pt >= CUERPO_PT else PLATE_LEAD_LINE


def lead_cm_at(texto: str | None, pt: float) -> float:
    """Alto de la entradilla compuesta al cuerpo `pt` con su interlineado y su espacio posterior."""
    if not texto:
        return 0.0
    return _text_cm(texto, pt, PLATE_TEXT_W_CM, line=lead_line_spacing(pt),
                    space_after=6 if pt >= CUERPO_PT else 3)


def is_lead_paragraph(texto: str | None, pt: float = CUERPO_PT, max_cm: float = PLATE_LEAD_MAX_CM) -> bool:
    """¿Es una frase de PRESENTACIÓN de la lámina y no un párrafo del cuerpo?

    Se mide al cuerpo del texto (12 pt, interlineado 1,5): las frases del suplemento ocupan 3–4 líneas
    (2,4–3,2 cm) y un párrafo de Resultados 11–13 cm. En modo revista se mide al cuerpo real de la entradilla
    (`pt` = 10) y con el tope `lead_max_cm` del documento: el párrafo de presentación del apéndice de la
    revista (qué muestra, por qué importa, qué añade) es más largo que la frase del corpus y sin esto se
    quedaba SOLO en una página, delante de la sección de su lámina."""
    return bool(texto) and lead_cm_at(texto, pt) <= max_cm


def plate_layout(path, caption: str, label: str = "", lead_text: str | None = None, extra_cm: float = 0.0,
                 budget_cm: float | None = None, spill_pt: float | None = None,
                 cap_ladder: tuple | None = None, lead_ladder: tuple | None = None,
                 min_w_cm: float | None = None, min_lines: int | None = None,
                 lead_check_pt: float = CUERPO_PT, lead_max_cm: float = PLATE_LEAD_MAX_CM) -> dict:
    """Composición de la página de una lámina vertical: la lámina SIEMPRE a 180 mm, lo demás se ajusta.

    La lámina se dibuja 1:1 a 180 × 245 mm y a 180 mm se imprime: encogerla al ancho de la columna de texto
    bajaría su tipografía de 6 pt a 5,3 pt y ése es justamente el defecto que esta norma corrige. La caja de
    la sección de lámina (196 × 286,8 mm) la admite entera y deja 3,88 cm para la ENTRADILLA y la LEYENDA,
    que es lo que se ajusta:

      * se busca el par (leyenda, entradilla) MAYOR que quepa en esos 3,88 cm, recorriendo la leyenda de 9 a
        7,0 pt —su SUELO— y, para cada tamaño de leyenda, la entradilla de 12 a 7,0 pt sin bajar nunca por
        debajo de la leyenda;
      * si ningún par cabe, la leyenda NO se encoge por debajo del suelo: se compone a `PLATE_CAP_FALLBACK_PT`
        (7,0 pt) y continúa en la página siguiente (`spill_cm`), que no se desperdicia: `plan_full_page_plates`
        pone en ella la lámina siguiente y sólo si esa lámina ya no cabe reconsidera el cuerpo
        (`PLATE_CAP_STRAND_PT`). `cap_ladder` es esa escala y quien llama puede alargarla con el escalón de
        6,5 pt para preguntar precisamente eso.

    La entradilla NO se abandona nunca: dejarla en el texto imprimía una página con dos líneas por lámina
    (43 de las 116 páginas de la región de láminas del suplemento). `lead_text=None` significa que esta
    lámina no tiene entradilla o que va en la página anterior, no que se haya descartado.

    `caption_lines_page` es cuántas líneas de la leyenda caben bajo la imagen: es el punto por el que
    `split_caption_lines` la parte. Cuando la leyenda no cabe entera nunca baja de `PLATE_CAP_MIN_LINES`:
    el presupuesto de una página que arrastra la cola de la leyenda anterior llegaba a dejar CERO, y con
    cero la lámina se imprime con el rótulo y ni una línea de leyenda debajo.

    `extra_cm` es lo que ya ocupan en esa página los títulos de sección absorbidos con la lámina y
    `budget_cm` el alto disponible (menor que la caja completa cuando la página arrastra la cola de la
    leyenda anterior).

    Devuelve dict(width_cm, height_cm, caption_pt, caption_cm, lead_cm, lead_pt, lead_line, extra_cm,
    spill_cm, mode, caption_lines_page, caption_lines_total) con mode ∈ {natural, spill}: `natural` = todo
    dentro de la página; `spill` = la leyenda continúa en la página siguiente (spill_cm es cuánto)."""
    with Image.open(path) as im:
        w_px, h_px = im.size
    aspect = h_px / w_px
    # la escala se resuelve AQUÍ y no en la firma: como valor por defecto quedaría congelada al definir la
    # función y un cambio de `PLATE_CAP_PT` (una prueba, una variante de composición) no llegaría nunca.
    cap_ladder = PLATE_CAP_PT if cap_ladder is None else cap_ladder
    lead_ladder = PLATE_LEAD_PT if lead_ladder is None else lead_ladder   # modo revista: la entradilla al cuerpo
    budget = PLATE_TEXT_H_CM if budget_cm is None else budget_cm
    texto = (label + ". " if label else "") + str(caption)

    def caption_cm(cap_pt: float) -> float:
        return _text_cm(texto, cap_pt, PLATE_TEXT_W_CM, line=1.0, space_before=3)

    lead_text = lead_text if is_lead_paragraph(lead_text, lead_check_pt, lead_max_cm) else None
    w = min(PLATE_NATURAL_W_CM, PLATE_TEXT_W_CM)
    alto = w * aspect
    sitio = budget - extra_cm - alto - PLATE_GAP_CM        # lo que queda para entradilla y leyenda
    elegido = None
    for cap_pt in cap_ladder:
        cap = caption_cm(cap_pt)
        if not lead_text:
            if cap <= sitio:
                elegido = (None, 0.0, cap_pt, cap)
                break
            continue
        for lead_pt in lead_ladder:
            if lead_pt < cap_pt:                            # la entradilla nunca menor que la leyenda
                continue
            lc = lead_cm_at(lead_text, lead_pt)
            if lc + cap <= sitio:
                elegido = (lead_pt, lc, cap_pt, cap)
                break
        if elegido is not None:
            break
    if elegido is None:                 # ni al menor cuerpo cabe: la leyenda continúa en la página siguiente
        cap_pt = spill_pt or PLATE_CAP_FALLBACK_PT
        lead_pt = max(lead_ladder[-1], cap_pt) if lead_text else None
        elegido = (lead_pt, lead_cm_at(lead_text, lead_pt) if lead_text else 0.0, cap_pt, caption_cm(cap_pt))
    lead_pt, lead_cm, cap_pt, cap = elegido
    spill = max(0.0, lead_cm + extra_cm + alto + PLATE_GAP_CM + cap - budget)
    if min_w_cm is not None and spill > 1e-9:
        # MODO REVISTA (`min_w_cm`): la leyenda no se encoge (10 pt fijos) y la lámina SÍ puede hacerlo, nunca
        # por debajo de `min_w_cm` (la revista pide 107 mm; 140 mm deja 4.251 px a 770 ppp). Primero se prueba
        # el ancho al que la leyenda ENTERA cabe bajo la imagen; si ese ancho queda por debajo del suelo, la
        # lámina se encoge sólo lo justo para que bajo ella queden `min_lines` líneas de leyenda con su
        # entradilla, y la cola continúa rotulada en la página siguiente. Sin `min_w_cm` nada de esto se ejecuta:
        # la lámina va a 180 mm y la leyenda se parte donde caiga (corpus).
        linea_cm = cap_pt * LINE_FACTOR * CM_PER_PT
        n_min = PLATE_CAP_MIN_LINES if min_lines is None else int(min_lines)
        w_full = (budget - (lead_cm + extra_cm + cap + PLATE_GAP_CM)) / aspect
        w_min = (budget - (lead_cm + extra_cm + n_min * linea_cm + 3 * CM_PER_PT + PLATE_GAP_CM)) / aspect
        if w_full >= min_w_cm:
            w = min(w, w_full)
        elif w_min < w:
            w = max(min_w_cm, w_min)
        alto = w * aspect
        sitio = budget - extra_cm - alto - PLATE_GAP_CM
        spill = max(0.0, lead_cm + extra_cm + alto + PLATE_GAP_CM + cap - budget)
    # Cuántas LÍNEAS de la leyenda caben debajo de la lámina. Sirve para partir la leyenda en su sitio
    # cuando la sección de la lámina se cierra justo después (véase `split_caption_lines`): la cabeza se
    # imprime bajo la imagen y la cola pasa al cuerpo del texto, donde la sigue el párrafo siguiente.
    linea_cm = cap_pt * LINE_FACTOR * CM_PER_PT
    hueco = sitio - lead_cm - 3 * CM_PER_PT                # 3 pt de espacio anterior de la leyenda
    lineas_pagina = max(0, int((hueco + 1e-9) / linea_cm))
    lineas_total = _wrapped_lines(texto, cap_pt, PLATE_TEXT_W_CM)
    # Bajo la lámina se imprimen SIEMPRE al menos `PLATE_CAP_MIN_LINES` líneas de leyenda cuando la leyenda
    # se va a partir: una lámina cuyo pie es sólo el rótulo es una figura sin leyenda. El presupuesto que
    # deja cero líneas es el de la página que arrastra la cola de la leyenda anterior, y esa cola es una
    # predicción que a menudo no llega; el suelo la corrige sin arriesgar la imagen, que es lo que nunca
    # cede.
    if lineas_total > lineas_pagina:
        lineas_pagina = max(lineas_pagina, PLATE_CAP_MIN_LINES)
    return dict(width_cm=w, height_cm=alto, caption_pt=cap_pt, caption_cm=cap, lead_cm=lead_cm,
                lead_pt=lead_pt, lead_line=lead_line_spacing(lead_pt) if lead_pt else None,
                extra_cm=extra_cm, spill_cm=spill, mode="natural" if spill <= 1e-9 else "spill",
                caption_lines_page=min(lineas_pagina, lineas_total), caption_lines_total=lineas_total)


def caption_tail_text(label: str, caption: str, layout: dict) -> str:
    """La cola de la leyenda tal como se va a imprimir, SIN su rótulo. Vacía si la leyenda cabe entera."""
    if layout["mode"] != "spill":
        return ""
    _, cola = split_caption_lines(f"{label}. ", str(caption), layout["caption_pt"],
                                  layout["caption_lines_page"])
    return cola


def caption_tail_cm(layout: dict, label: str, caption: str, lang: str,
                    space_after_pt: float = PLATE_CAP_CONT_AFTER_PT) -> float:
    """Alto que ocupa la COLA rotulada de una leyenda partida en la página que la recibe.

    Es la cuenta que sustituye a `spill_cm` en el arrastre de la cadena de láminas. `spill_cm` mide cuánto
    NO cabe —un número continuo, calculado antes de saber por dónde se corta— y servía cuando la leyenda
    viajaba como un solo párrafo y era Word quien la partía. Ahora la parte el código, y lo que le quita a
    la página siguiente es un párrafo concreto: la cola CON SU RÓTULO. El rótulo importa y por eso se compone
    aquí en vez de restar renglones: «Figure S50 (continued). » son veinticuatro caracteres que no estaban en
    la leyenda original y que empujan una línea entera en 20 de las 260 colas de los doce documentos. Contarlas por
    `caption_lines_total − caption_lines_page` —que es lo que la primera versión de esta cuenta hacía— deja
    el presupuesto de la lámina siguiente holgado por esa línea, que es holgura en la dirección peligrosa:
    la cabeza de SU leyenda se compone para un sitio que no existe. Componer el párrafo cuesta lo mismo y
    no hay que fiarse de una diferencia."""
    cola = caption_tail_text(label, caption, layout)
    if not cola:
        return 0.0
    prefijo = f"{label} ({WORDS['continued'][lang]}). "
    return _text_cm(prefijo + cola, layout["caption_pt"], PLATE_TEXT_W_CM, line=1.0,
                    space_after=space_after_pt)


def split_caption_lines(prefix: str, texto: str, pt: float, n_lines: int,
                        ancho_cm: float = PLATE_TEXT_W_CM, hard_spaces: bool = False) -> tuple[str, str]:
    """Parte la leyenda tras las primeras `n_lines` líneas de `prefix + texto` compuestas a `pt`.

    Devuelve (cabeza, cola) SIN el rótulo, que lo imprime quien llama. La cuenta de líneas es la misma
    que la del presupuesto de la página (`_wrapped_lines`), de modo que la cabeza es exactamente lo que
    cabe debajo de la lámina y la cola es lo que sobra. Con `n_lines` menor o igual que las líneas que
    ocupa el propio rótulo, la cabeza es vacía y la leyenda entera pasa a la cola.

    EL CORTE NO CAE NUNCA EN UN ESPACIO DURO. `str.split()` parte también por U+00A0, que es justo el
    blanco que el corpus escribe entre una cifra y su signo de porcentaje para que el signo no se quede
    solo (`_pct_nbsp`). Mientras esta función partía cinco leyendas por documento el riesgo era pequeño;
    partiendo las 260 de los doce documentos, tarde o temprano el corte cae ahí y el «%» abre la página
    siguiente separado de su número —el defecto que otra fase cerró en 5.266 sitios—. Cuando el corte cae
    en un espacio duro se retrocede al blanco anterior: la cabeza pierde una palabra y la norma se
    mantiene."""
    entero = prefix + str(texto)
    # `hard_spaces` (modo revista): `str.split()` parte también por U+202F y U+00A0 y la reunión con « »
    # convertía «100 000» en «100 000» con un blanco que sí parte; se parte sólo por el blanco ASCII.
    palabras = re.split(r"[ \t\r\n\f\v]+", entero.strip()) if hard_spaces else entero.split()
    # el blanco que precede a cada palabra, para poder rechazar el corte que caería en un espacio duro
    trozos = re.split(r"(\s+)", entero.strip())
    seps = trozos[1::2] if len(trozos) > 1 else []
    duro = [any(c in "\u00a0\u202f\u2009" for c in sp) for sp in seps]
    k = len(prefix.split())
    if n_lines <= 0:
        return "", " ".join(palabras[k:])
    espacio = _ancho_texto(" ", pt)
    n, cur, corte = 1, 0.0, len(palabras)
    for j, palabra in enumerate(palabras):
        w = _ancho_texto(palabra, pt)
        if cur and cur + espacio + w > ancho_cm:
            n, cur = n + 1, w
            if n > n_lines:
                corte = j
                break
        else:
            cur += (espacio if cur else 0.0) + w
    while k < corte < len(palabras) and corte - 1 < len(duro) and duro[corte - 1]:
        corte -= 1                       # el corte caería entre una cifra y su unidad: se retrocede
    if corte >= len(palabras):
        return " ".join(palabras[k:]), ""
    if corte <= k:
        return "", " ".join(palabras[k:])
    return " ".join(palabras[k:corte]), " ".join(palabras[corte:])


def _sectpr_paragraph(doc, margins_cm: dict):
    """Párrafo vacío (1 pt, sin espacios) cuyo w:sectPr CIERRA la sección precedente con esos márgenes.

    Copia el sectPr final del documento —con sus referencias de encabezado y pie— y sólo cambia el tamaño
    de página (A4 vertical) y los márgenes, de modo que la numeración de páginas se hereda intacta."""
    base = doc.element.body.find(qn("w:sectPr"))
    sp = copy.deepcopy(base) if base is not None else OxmlElement("w:sectPr")
    pg = sp.find(qn("w:pgSz"))
    if pg is None:
        pg = OxmlElement("w:pgSz")
        sp.append(pg)
    pg.set(qn("w:w"), str(int(PAGE_W_CM * 567)))
    pg.set(qn("w:h"), str(int(PAGE_H_CM * 567)))
    if pg.get(qn("w:orient")) is not None:
        del pg.attrib[qn("w:orient")]
    mar = sp.find(qn("w:pgMar"))
    if mar is None:
        mar = OxmlElement("w:pgMar")
        pg.addnext(mar)
    for side in ("top", "bottom", "left", "right", "header", "footer"):
        mar.set(qn("w:" + side), str(int(margins_cm[side] * 567)))
    mar.set(qn("w:gutter"), "0")
    p = OxmlElement("w:p")
    ppr = OxmlElement("w:pPr")
    spacing = OxmlElement("w:spacing")
    for attr, val in (("w:before", "0"), ("w:after", "0"), ("w:line", "20"), ("w:lineRule", "exact")):
        spacing.set(qn(attr), val)
    rpr = OxmlElement("w:rPr")
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "2")
    rpr.append(sz)
    ppr.append(spacing)
    ppr.append(rpr)
    ppr.append(sp)
    p.append(ppr)
    body = doc.element.body
    final = body.find(qn("w:sectPr"))
    if final is not None:
        final.addprevious(p)
    else:
        body.append(p)
    return p


def _absorb_trailing_section(doc) -> bool:
    """Modo revista: cuando el documento TERMINA con una lámina, el párrafo que cierra su sección deja detrás
    una sección final vacía que Word imprime como una página en blanco con su folio. Se quita ese párrafo y
    sus márgenes de lámina pasan al sectPr final del cuerpo, que así es el de la última página. Devuelve si
    hubo algo que absorber."""
    body = doc.element.body
    final = body.find(qn("w:sectPr"))
    if final is None:
        return False
    last = final.getprevious()
    if last is None or last.tag != qn("w:p"):
        return False
    ppr = last.find(qn("w:pPr"))
    sp = ppr.find(qn("w:sectPr")) if ppr is not None else None
    if sp is None or "".join(t.text or "" for t in last.iter(qn("w:t"))).strip():
        return False
    for tag in ("w:pgSz", "w:pgMar"):
        src, dst = sp.find(qn(tag)), final.find(qn(tag))
        if src is None:
            continue
        if dst is not None:
            final.replace(dst, copy.deepcopy(src))
        else:
            final.append(copy.deepcopy(src))
    body.remove(last)
    return True


def _page_break_before(p) -> None:
    ppr = p._p.get_or_add_pPr()
    if ppr.find(qn("w:pageBreakBefore")) is None:
        ppr.insert(0, OxmlElement("w:pageBreakBefore"))


def _flatten_white(im):
    if im.mode in ("RGBA", "LA", "P"):
        rgba = im.convert("RGBA")
        fondo = Image.new("RGB", rgba.size, "white")
        fondo.paste(rgba, mask=rgba.split()[-1])
        return fondo
    return im.convert("RGB") if im.mode != "RGB" else im


def embed_copy(path, ancho_cm: float, dpi: int | None, cache_dir: Path | None) -> Path:
    """Copia de la lámina remuestreada a `dpi` para el ancho al que se imprime; el original no se toca.

    Sin `dpi` (o si la lámina ya está por debajo de esa resolución) devuelve el original: las figuras del
    artículo se incrustan siempre a su resolución de 600 ppp."""
    path = Path(path)
    if not dpi or not cache_dir:
        return path
    destino_px = int(round(ancho_cm / 2.54 * dpi))
    with Image.open(path) as im:
        w_px, h_px = im.size
    if w_px <= destino_px * 1.02:
        return path
    st = path.stat()
    clave = hashlib.sha1(f"{path}|{st.st_mtime_ns}|{st.st_size}|{destino_px}".encode()).hexdigest()[:12]
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    out = cache_dir / f"{path.stem}_{destino_px}px_{clave}.png"
    if not out.is_file():
        with Image.open(path) as im:
            small = _flatten_white(im).resize((destino_px, max(1, round(h_px * destino_px / w_px))), Image.LANCZOS)
            small.save(out, format="PNG", optimize=True, dpi=(dpi, dpi))
    else:
        out.touch()          # marca de uso: el módulo 10 borra de la caché lo que este build no ha tocado
    return out


def insertar_figura(doc, path, ancho_cm=TEXT_WIDTH_CM, full_page: bool = False, embed_dpi: int | None = None,
                    cache_dir: Path | None = None):
    with Image.open(path) as im:
        w_px, h_px = im.size
    if not full_page:
        alto_cm = ancho_cm * h_px / w_px
        if alto_cm > MAX_ALTO_CM:
            ancho_cm = ancho_cm * MAX_ALTO_CM / alto_cm
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = p.paragraph_format
    pf.space_before, pf.space_after, pf.keep_with_next = (Pt(0), Pt(2), True) if full_page else (Pt(10), Pt(2), True)
    if full_page:
        pf.line_spacing = 1.0
    p.add_run().add_picture(str(embed_copy(path, ancho_cm, embed_dpi, cache_dir)), width=Cm(ancho_cm))
    return p


def pie_figura(doc, etiqueta, texto, size: float = 10, space_after: float = 14, heading: str | None = None):
    """Leyenda de una figura. `heading` (modo revista) es el TÍTULO de la figura, que la revista quiere en
    negrita al principio de la leyenda: si la leyenda empieza por él se imprime en negrita y el resto no."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before, p.paragraph_format.space_after, p.paragraph_format.line_spacing = \
        Pt(3 if size < 10 else 4), Pt(space_after), 1.0
    _set_font(p.add_run(etiqueta + ". "), size=size, bold=True)
    if heading and str(texto).startswith(heading):
        resto = str(texto)[len(heading):]
        # el punto que cierra el título va en el mismo run en negrita: en el límite entre dos runs pdftotext
        # intercala a veces un blanco («syndrome) .») que no existe en el documento
        if resto.startswith("."):
            heading, resto = heading + ".", resto[1:]
        _set_font(p.add_run(texto_indivisible(heading)), size=size, bold=True)
        texto = resto
    _add_text(p, texto, size=size, refs_bold=False)
    return p


def pie_continuacion(doc, etiqueta, texto, lang: str, size: float = 7.0, space_after: float = 12):
    """Cola de una leyenda que no cabía bajo su lámina, impresa al principio de la página siguiente.

    Va rotulada «Figura N (continuación).» para que el bloque de letra pequeña con el que abre la página
    se lea como lo que es: SIEMPRE, caiga sobre el texto corrido (detrás de la lámina se cierra la sección)
    o sobre la página de la lámina siguiente (dentro de una tanda). El rótulo es lo único que distingue una
    cola de leyenda de un párrafo sin dueño, y Word no lo pone cuando parte un párrafo por su cuenta.

    `space_after` es el aire que la separa de lo que la sigue: 12 pt cuando la sigue el texto del documento
    y `PLATE_CAP_CONT_AFTER_PT` cuando la sigue la entradilla de la lámina siguiente, que paga ese aire con
    renglones de su propia leyenda."""
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    p.paragraph_format.space_before, p.paragraph_format.space_after, p.paragraph_format.line_spacing = \
        Pt(0), Pt(space_after), 1.0
    _set_font(p.add_run(f"{etiqueta} ({WORDS['continued'][lang]}). "), size=size, bold=True)
    _add_text(p, texto, size=size, refs_bold=False)
    return p


def insertar_ecuacion(doc, paths, numero, lang: str = "en", size: float = CUERPO_PT, keep_together: bool = False):
    """Ecuación (una o más líneas de imagen) con su número. `keep_together` (modo revista) impide que la fila
    se parta entre dos páginas: una segunda línea de fórmula sola en la página siguiente no se lee."""
    paths = list(paths)
    tbl = doc.add_table(rows=1, cols=2)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_autofit(tbl, TEXT_WIDTH_CM)
    if keep_together:
        tr_pr = tbl.rows[0]._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            tr_pr.append(OxmlElement("w:cantSplit"))
    c0, c1 = tbl.rows[0].cells
    for cell in (c0, c1):
        cell.text = ""
        _cell_border(cell, top=None, bottom=None, left=None, right=None)
    for k, path in enumerate(paths):
        with Image.open(path) as im:
            w_px, _ = im.size
        ancho_cm = min(w_px / 600 * 2.54, 14.0)
        p0 = c0.paragraphs[0] if k == 0 else c0.add_paragraph()
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_before, p0.paragraph_format.space_after = Pt(3), Pt(3)
        p0.add_run().add_picture(str(path), width=Cm(ancho_cm))
    p1 = c1.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    c1.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    _set_font(p1.add_run(f"{WORDS['equation_tag'][lang]} {numero}"), size=size)
    _aplicar_anchos(tbl, [TEXT_WIDTH_CM - 1.6, 1.6])


def panel(doc, title, items, lang, pt: float | None = None, line: float = 1.15):
    """Panel con recuadro (p. ej. Research in context): tabla de una celda con borde fino.

    `pt` (modo revista) es el cuerpo del texto del panel; sin él, 11 pt el título y 10,5 pt el resto."""
    t_pt, i_pt = (11, 10.5) if pt is None else (pt + 0.5, pt)
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_autofit(tbl, TEXT_WIDTH_CM)
    cell = tbl.rows[0].cells[0]
    cell.text = ""
    _cell_border(cell, top={"sz": 8}, bottom={"sz": 8}, left={"sz": 8}, right={"sz": 8})
    p = cell.paragraphs[0]
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(4), Pt(4)
    _set_font(p.add_run(texto_indivisible(title)), size=t_pt, bold=True)
    for heading, text in items:
        q = cell.add_paragraph()
        q.paragraph_format.space_before, q.paragraph_format.space_after, q.paragraph_format.line_spacing = Pt(4), Pt(0), line
        _set_font(q.add_run(texto_indivisible(heading)), size=i_pt, bold=True, italic=True)
        r = cell.add_paragraph()
        r.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        r.paragraph_format.space_after, r.paragraph_format.line_spacing = Pt(4), line
        _add_text(r, text, size=i_pt, refs_bold=False)
    _aplicar_anchos(tbl, [TEXT_WIDTH_CM])
    doc.add_paragraph()


def nuevo_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21), Cm(29.7)
    for side in ("top_margin", "bottom_margin", "left_margin", "right_margin"):
        setattr(sec, side, Cm(2.5))
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = FUENTE, Pt(CUERPO_PT)
    rpr = normal.element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.append(rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), FUENTE)
    return doc


def plan_full_page_plates(blocks: list, lang: str, supplementary_prefix: bool = False,
                          journal: dict | None = None) -> dict:
    """Plan de página completa de cada lámina vertical: qué entra en su página, cuánto mide y dónde cortan
    las secciones.

    Devuelve {índice del bloque «figure»: dict(layout, lead_index, start_index, label, open_section,
    close_section, page_break, lead_keep, own_page, carry_in_cm, split_caption, structural_spill_cm)}.
    Tres reglas gobiernan el plan:

      * la UNIDAD de una lámina son los títulos de sección que la preceden inmediatamente, la frase de
        presentación que la introduce (si es una entradilla y no un párrafo de Resultados), la imagen y la
        leyenda: todo eso comparte página. Si el título se quedara fuera, la sección anterior terminaría
        con un encabezado suelto y se imprimiría una página con una sola línea;
      * dos unidades consecutivas —el patrón «frase, lámina» que se repite 54 veces en la parte
        suplementaria— comparten UNA sección: abrir y cerrar una por lámina dejaría entre ellas una página
        vertical vacía. Dentro de la sección NO se fuerza el salto de página: la entradilla lleva keepNext y
        arrastra su lámina, así que Word pone cada lámina en su propia página sin ayuda;
      * cuando una leyenda no cabe entera, su cola pasa a la página siguiente y allí entra también la
        lámina siguiente, con su presupuesto reducido en lo que la cola ocupa. Si ni así cabe, la entradilla
        se queda con la cola (`lead_keep=False` se lo permite) y sólo la imagen pasa de página, que recupera
        todo el presupuesto. Así ninguna página lleva sólo la frase de presentación, y una cola que llegue a
        quedarse sola mide por construcción más de 2,7 cm: nueve líneas de leyenda, nunca dos.

    `journal` (modo revista, véase `build_document`) fija el cuerpo de la leyenda en `legend_pt` (10 pt: la
    revista no admite otro) y el de la entradilla en `body_pt`, de modo que la leyenda que no cabe se PARTE
    —cola rotulada «(continued)»— y nunca se encoge; y con `one_figure_per_page` cada lámina abre su propia
    página con el presupuesto entero, de modo que la cola de una leyenda nunca comparte página con la lámina
    siguiente. Sin `journal` nada cambia."""
    fijo = None
    own_all = False
    if journal:
        cap_pt = float(journal.get("legend_pt", 10))
        fijo = dict(cap_ladder=(cap_pt,), spill_pt=cap_pt, lead_ladder=(float(journal.get("body_pt", 10)),),
                    min_w_cm=journal.get("plate_min_w_cm"), min_lines=journal.get("plate_min_lines"),
                    lead_check_pt=float(journal.get("body_pt", 10)),
                    lead_max_cm=float(journal.get("lead_max_cm", PLATE_LEAD_MAX_CM)))
        own_all = bool(journal.get("one_figure_per_page", True))
    lead_check_pt = fijo["lead_check_pt"] if fijo else CUERPO_PT
    lead_max_cm = fijo["lead_max_cm"] if fijo else PLATE_LEAD_MAX_CM

    def _lay(*args, **kw):
        if fijo:
            kw = dict(kw, **fijo)
        return plate_layout(*args, **kw)

    F = WORDS["figure"][lang]
    pref = "S" if supplementary_prefix else ""
    unidades, n_fig = [], 0
    for i, (kind, payload) in enumerate(blocks):
        if kind != "figure":
            continue
        n_fig += 1
        if not is_full_page_plate(payload["path"]):
            continue
        label = payload.get("label") or f"{F} {pref}{n_fig}"
        lead_index, lead_text = None, None
        if i and blocks[i - 1][0] == "p" and is_lead_paragraph(str(blocks[i - 1][1]), lead_check_pt, lead_max_cm):
            lead_index, lead_text = i - 1, str(blocks[i - 1][1])
        if lead_index is not None and fijo and fijo.get("min_w_cm") and float(fijo["min_w_cm"]) >= PLATE_NATURAL_W_CM - 1e-6:
            # MODO REVISTA SIN ENCOGER LA LÁMINA (180 mm fijos): la entradilla sólo viaja con la lámina si bajo
            # ésta quedan `min_lines` líneas de leyenda con su rótulo; si no caben, la entradilla se queda en el
            # texto (cierra la página anterior) y la lámina abre la suya con la leyenda debajo. Sin esta regla,
            # Word empujaba la CABECERA de la leyenda entera a la página siguiente y la lámina quedaba sin pie
            # (lectores, segunda ronda: Figuras S2, S3 y S36).
            alto = min(PLATE_NATURAL_W_CM, PLATE_TEXT_W_CM) * _plate_aspect(payload["path"])
            linea = float(fijo["cap_ladder"][0]) * LINE_FACTOR * CM_PER_PT
            n_min = int(fijo.get("min_lines") or PLATE_CAP_MIN_LINES)
            cabezas, j = 0.0, lead_index - 1
            while j >= 0 and blocks[j][0] in HEADING_PT:
                cabezas += heading_cm(blocks[j][0], str(blocks[j][1]))
                j -= 1
            if (cabezas + lead_cm_at(lead_text, float(fijo["lead_ladder"][0])) + alto + PLATE_GAP_CM
                    + n_min * linea + 6 * CM_PER_PT > PLATE_TEXT_H_CM):
                lead_index, lead_text = None, None
        inicio = lead_index if lead_index is not None else i
        extra_cm, j = 0.0, inicio - 1
        while j >= 0 and blocks[j][0] in HEADING_PT:          # títulos que preceden a la unidad
            extra_cm += heading_cm(blocks[j][0], str(blocks[j][1]))
            inicio, j = j, j - 1
        unidades.append(dict(index=i, label=label, lead_index=lead_index, lead_text=lead_text,
                             start_index=inicio, extra_cm=extra_cm, path=payload["path"],
                             caption=payload.get("caption", "")))
    # Cuántos bloques de texto corrido siguen a cada lámina antes de que la unidad siguiente abra su página:
    # son los que ACOMPAÑAN a la cola de su leyenda cuando detrás de la lámina se cierra la sección. Con cero,
    # la cola se quedaría sola en su página y la segunda pasada prueba el escalón de `PLATE_CAP_STRAND_PT`.
    for n, u in enumerate(unidades):
        fin = unidades[n + 1]["start_index"] if n + 1 < len(unidades) else len(blocks)
        u["following_blocks"] = sum(1 for k, _ in blocks[u["index"] + 1:fin] if k != "pagebreak")
    plan, carry, previo = {}, 0.0, None
    for n, u in enumerate(unidades):
        lead_index, lead_text, extra_cm = u["lead_index"], u["lead_text"], u["extra_cm"]
        contiguo = previo is not None and u["start_index"] == previo["index"] + 1
        if not contiguo:
            carry = 0.0
        # ¿cabe la UNIDAD entera —títulos, entradilla e imagen— en la página que arrastra la cola de la
        # leyenda anterior? La entradilla va con su lámina siempre, así que se mide con ella dentro.
        minimo = _unit_min_cm(u)
        # Dentro de una tanda NO se fuerza el salto de página mientras la unidad quepa: la entradilla lleva
        # keepNext y arrastra su lámina, de modo que Word —cuyo presupuesto es exacto y el de aquí una
        # estimación— pone la cola de la leyenda anterior, la entradilla y la lámina en la MISMA página. El
        # salto se escribe sólo cuando la cuenta dice que la unidad YA NO CABE (`own_page`), porque entonces
        # la leyenda se compone con el presupuesto de una página entera y tiene que aterrizar en una: véase
        # el comentario de `page_break` más abajo. Esa página se queda con la cola de la leyenda anterior y
        # nada más; sale de la aritmética de la caja (una lámina de 245 mm deja 3,88 cm de texto —trece
        # líneas a 7 pt— y 18 de las 54 leyendas piden más), no de la composición, y desde la fase 4j esa
        # cola va rotulada, de modo que la página se lee como la continuación que es.
        own_page = own_all or (carry > 1e-9 and carry + minimo > PLATE_TEXT_H_CM)
        # la lámina que abre página por sí sola compone su leyenda con todo el presupuesto
        budget = PLATE_TEXT_H_CM - (0.0 if own_page else carry)
        layout = _lay(u["path"], u["caption"], u["label"], lead_text, extra_cm=extra_cm,
                      budget_cm=budget)
        # LA COLA NO PUEDE QUEDARSE SOLA (tarea Y2). La leyenda se compone al suelo de 7,0 pt y, si no cabe,
        # se parte: la cola cae sobre la página de la lámina SIGUIENTE y esa página se llena. Pero dentro de
        # una tanda larga la cola crece hasta que la lámina siguiente ya no cabe en ella, y entonces la
        # página lleva la cola y nada más. Ahí —y sólo ahí— se prueba el escalón de 6,5 pt: si medio punto
        # menos devuelve el presupuesto que la lámina siguiente necesita, se usa; si no lo devuelve, la
        # leyenda se queda en su suelo, porque encogerla sin salvar la página no le ahorra nada a nadie.
        siguiente = unidades[n + 1] if n + 1 < len(unidades) else None
        if siguiente is not None and siguiente["start_index"] == u["index"] + 1 and layout["spill_cm"] > 1e-9:
            minimo_prox = _unit_min_cm(siguiente)
            if caption_tail_cm(layout, u["label"], u["caption"], lang) + minimo_prox > PLATE_TEXT_H_CM:
                menor = _lay(u["path"], u["caption"], u["label"], lead_text, extra_cm=extra_cm,
                             budget_cm=budget, spill_pt=PLATE_CAP_STRAND_PT,
                             cap_ladder=PLATE_CAP_PT + (PLATE_CAP_STRAND_PT,))
                if caption_tail_cm(menor, u["label"], u["caption"], lang) + minimo_prox <= PLATE_TEXT_H_CM:
                    layout = menor
        # keepNext en la entradilla SIEMPRE. Antes se soltaba cuando la página traía la cola de la leyenda
        # anterior, para que la frase se quedase con esa cola en vez de dejarla sola; el resultado impreso
        # era que 6 a 12 de las 54 láminas de cada documento imprimían su frase de presentación en la página
        # ANTERIOR a su lámina, que es justo lo que la frase no puede hacer: presenta la lámina. Se elige la
        # regla que el lector nota —la frase con su lámina— y el sitio en blanco se ataca donde nace, en el
        # presupuesto de la página (caja de 28,68 cm, leyenda y entradilla con el mismo suelo de 7,0 pt).
        #
        # LA LÁMINA QUE ABRE PÁGINA PROPIA LA ABRE DE VERDAD (fase 4j). `own_page` decide que la unidad ya no
        # cabe en la página que trae la cola de la leyenda anterior, y con esa decisión la leyenda se compone
        # con el PRESUPUESTO DE UNA PÁGINA ENTERA. Mientras la leyenda viajaba como un solo párrafo, dejar el
        # salto en manos de Word no costaba nada: si Word metía la lámina en la página de la cola, partía la
        # leyenda donde hiciera falta. Con la leyenda partida en el código el corte ya está decidido, y una
        # lámina compuesta para doce líneas que aterriza en una página donde caben dos imprime diez líneas
        # fuera de sitio, sin rótulo y por delante de la cola rotulada: es el defecto de J1, movido un sitio.
        # Se midió sobre el PDF: tres leyendas por documento largo salían así. Por eso el salto se escribe.
        plan[u["index"]] = dict(layout=layout, lead_index=lead_index, lead_text=lead_text,
                                start_index=u["start_index"],
                                label=u["label"], open_section=not contiguo, close_section=True,
                                page_break=own_page, own_page=own_page, break_index=u["start_index"],
                                lead_keep=True, carry_in_cm=round(carry, 2), budget_cm=budget)
        if previo is not None and contiguo:
            plan[previo["index"]]["close_section"] = False
        carry, previo = caption_tail_cm(layout, u["label"], u["caption"], lang), u
    # Segunda pasada: recompone la leyenda de las láminas detrás de las cuales se CIERRA la sección, cuya
    # cola no cae sobre la página de otra lámina sino sobre el texto corrido:
    #   * la leyenda que no cabe se parte y se compone al SUELO de 7,0 pt (`PLATE_CAP_STANDALONE_PT`): la
    #     cola pasa al cuerpo del documento, donde la siguen el título y los párrafos que vienen detrás de
    #     la lámina, y no le quita presupuesto a ninguna otra lámina;
    #   * salvo que detrás de la lámina no venga NINGÚN bloque de texto antes de que la unidad siguiente
    #     abra su página: entonces la cola sí se quedaría sola y se prueba el escalón de 6,5 pt
    #     (`PLATE_CAP_STRAND_PT`), que es la única razón que queda para bajar del suelo. En los doce
    #     documentos de 2026-09-07 no ocurre —detrás de las cinco figuras del artículo y de la S54 hay entre
    #     6 y 189 bloques—, pero se comprueba en vez de suponerse.
    # QUIÉN se parte ya no se decide aquí: se parte TODA leyenda que no cabe bajo su lámina, y su cola va
    # rotulada. Lo único que sigue dependiendo del sitio es el CUERPO al que se compone.
    por_indice = {u["index"]: u for u in unidades}
    for i, v in plan.items():
        u = por_indice[i]
        # ¿Desborda la leyenda con la PÁGINA ENTERA por presupuesto, sin descontar la cola de la leyenda
        # anterior? Ése es el desbordamiento ESTRUCTURAL: el que no depende de ninguna predicción. Ya no
        # decide nada —se rotulan todas las colas—, pero se informa: por encima de `PLATE_SPILL_LABEL_CM`
        # la leyenda no cabe ni con la página entera y lo que pide es prosa más corta, no otra composición.
        entera = _lay(u["path"], u["caption"], u["label"], u["lead_text"], extra_cm=u["extra_cm"],
                      budget_cm=PLATE_TEXT_H_CM)
        v["structural_spill_cm"] = round(entera["spill_cm"], 2)
        v["structural_overflow"] = bool(entera["spill_cm"] > PLATE_SPILL_LABEL_CM)
        # LA REGLA (fase 4j): la leyenda que no cabe bajo su lámina se parte en el código y su cola se
        # imprime rotulada «(continuación)» al principio de la página siguiente. Sin excepción y sin umbral:
        # una cola sin rótulo es un párrafo sin dueño, y da igual que caiga sobre el texto corrido o sobre
        # la página de la lámina siguiente. Antes se rotulaban sólo las de la primera clase.
        v["split_caption"] = v["layout"]["mode"] == "spill"
        if not v["split_caption"]:
            continue
        if not v["close_section"]:
            # La cola cae sobre la página de la lámina SIGUIENTE: se queda con el cuerpo y el reparto de
            # líneas que ya fijó la primera pasada —de los que depende el arrastre de la cadena, y donde ya
            # se comprobó que esa página no se queda con la cola sola—. Lo único que cambia aquí es que la
            # cola se parte en el código y va rotulada.
            continue
        # La cola se va a partir de todos modos y cae sobre el TEXTO CORRIDO, no sobre otra lámina: no le
        # quita el sitio a nadie y la leyenda se compone al suelo (7,0 pt). La excepción es la lámina detrás
        # de la cual no viene ningún bloque antes de la página siguiente: allí la cola se quedaría sola y se
        # prueba antes el escalón de 6,5 pt, por si la leyenda entra entera bajo su lámina.
        if not u["following_blocks"]:
            apretada = _lay(u["path"], u["caption"], u["label"], u["lead_text"], extra_cm=u["extra_cm"],
                            budget_cm=v["budget_cm"],
                            cap_ladder=PLATE_CAP_PT + (PLATE_CAP_STRAND_PT,))
            if apretada["mode"] == "natural":
                v["layout"], v["split_caption"] = apretada, False
                continue
        v["layout"] = _lay(u["path"], u["caption"], u["label"], u["lead_text"], extra_cm=u["extra_cm"],
                           budget_cm=v["budget_cm"], spill_pt=PLATE_CAP_STANDALONE_PT)
        v["split_caption"] = v["layout"]["mode"] == "spill"
    return plan


def _plate_aspect(path) -> float:
    with Image.open(path) as im:
        w_px, h_px = im.size
    return h_px / w_px


#: Alto del bloque de leyenda que SIEMPRE tiene que caber bajo la lámina: `PLATE_CAP_MIN_LINES` renglones al
#: suelo tipográfico más el espacio anterior de la leyenda. Es la traducción a centímetros de la regla de
#: `PLATE_CAP_MIN_LINES`, y tiene que entrar en la cuenta de si una lámina cabe en una página: antes la regla
#: se aplicaba SÓLO al repartir las líneas (`plate_layout` subía el reparto a tres) y no al decidir la página,
#: de modo que una página podía admitir la lámina con sitio para UNA línea de leyenda y el reparto imprimir
#: TRES. Mientras Word partía la leyenda por su cuenta eso no se notaba —Word ponía las que cupieran—; con la
#: leyenda partida en el código y la cola con salto de página delante, las dos líneas de más se irían solas a
#: la página siguiente, DELANTE del rótulo «(continuación)», que es exactamente el párrafo huérfano que esta
#: fase cierra. Contándolas aquí, la lámina que no quepa con sus tres líneas abre página propia y compone su
#: leyenda con el presupuesto entero.
PLATE_CAP_MIN_CM = PLATE_CAP_MIN_LINES * PLATE_CAP_MIN_PT * LINE_FACTOR * CM_PER_PT + 3 * CM_PER_PT


def _unit_min_cm(u: dict) -> float:
    """Lo MÍNIMO que ocupa la unidad de una lámina en su página: títulos, entradilla al menor cuerpo, imagen,
    las tres líneas de leyenda que van siempre bajo la lámina y la holgura. Es la cuenta con la que se decide
    si la unidad cabe todavía en la página que trae la cola de la leyenda anterior —y, mirando hacia adelante,
    si esa cola dejaría a la lámina siguiente sin página."""
    return (u["extra_cm"] + lead_cm_at(u["lead_text"], PLATE_LEAD_PT[-1])
            + PLATE_NATURAL_W_CM * _plate_aspect(u["path"]) + PLATE_CAP_MIN_CM + PLATE_GAP_CM)


# ---------------------------------------------------------------------------
# Modo revista: citas en superíndice tras la puntuación, índice
# ---------------------------------------------------------------------------
# `build_document(journal=dict(...))` compone el mismo bloque de entrada con la tipografía que pide la revista.
# Las claves del diccionario y sus efectos (todas opcionales; sin `journal` nada de esto se ejecuta):
#   body_pt, line_spacing      cuerpo e interlineado de los párrafos (artículo 12/1,5; suplemento 10/1,0)
#   aux_line_spacing           interlineado de subtítulo, autores, «small», títulos, referencias, panel y
#                              entradillas (1,15 por defecto; el suplemento pide 1,0: «single spaced»)
#   table_rows_cant_split      ninguna fila de tabla se parte entre páginas; las dos últimas viajan con la nota
#   heading_pt                 cuerpo de h1/h2/h3 (negrita; h3 además cursiva)
#   title_pt                   cuerpo del título del documento (el «main heading» de 12 pt del suplemento)
#   table_heading_pt, table_pt rótulo/título de tabla (negrita) y cuerpo de tabla y de su nota (8 pt);
#                              las filas de encabezado interno se imprimen en negrita
#   legend_pt                  cuerpo de la leyenda (10 pt, a un espacio) con el título de la figura en negrita
#   one_figure_per_page        cada lámina abre su página; la leyenda que no cabe continúa rotulada
#   superscript_citations      «[@clave]» → número en superíndice DETRÁS del signo de puntuación que lo sigue,
#                              dos citas separadas por coma, tres o más consecutivas con raya corta
#   refs_pt, panel_pt          cuerpo de la lista de referencias y del panel (Research in context)
#   toc                        admite el bloque ("toc", dict(title, entries=[dict(level, text, page)]))
_CIT_MARKER_RE = re.compile(r"\s*\[(@[^\]]+)\]([,.;:]?)")


def journal_resolve(cit: Citations, text: str) -> str:
    """Resuelve los marcadores [@a; @b] como la revista: superíndice tras la puntuación, «1,2» o «1–3»."""
    def repl(m):
        keys = [k.strip().lstrip("@") for k in m.group(1).split(";")]
        nums = cit._format_numbers([cit.number(k) for k in keys]).strip("()").replace("-", "\u2013")
        return m.group(2) + _SUP_OPEN + nums + _SUP_CLOSE
    return _CIT_MARKER_RE.sub(repl, str(text))


def prenumber_citations(cit: Citations, blocks: list) -> list:
    """Numera las citas por orden de aparición en los BLOQUES, tablas y figuras incluidas.

    En el envío a la revista las tablas y las figuras van DETRÁS de las Referencias, de modo que una cita que
    sólo apareciera en una nota o en una leyenda recibiría su número después de impresa la lista. Se recorren
    los bloques antes de escribir nada, en el mismo orden en que `prose_en.citation_keys` los lee."""
    from references import MARKER

    def scan(text):
        for m in MARKER.finditer(str(text)):
            for part in m.group(1).split(";"):
                key = part.strip().lstrip("@")
                if key:
                    cit.number(key)

    for kind, payload in blocks:
        if kind in ("p", "small"):
            scan(payload)
        elif kind == "bullets":
            for item in payload:
                scan(item)
        elif kind == "panel":
            for _, text in payload["items"]:
                scan(text)
        elif kind == "table":
            scan(payload.get("note", ""))
        elif kind == "figure":
            scan(payload.get("caption", ""))
    return list(cit.order)


def indice(doc, title: str, entries: list, pt: float = 10, title_pt: float = 12) -> int:
    """Índice del suplemento: una línea por entrada con el número de página al margen derecho (tabulador
    con puntos de guía). `page` en None imprime el marcador de la primera pasada, del mismo ancho que un
    folio de tres cifras, para que la segunda pasada no mueva ni una línea."""
    titulo(doc, title, 1, pt=title_pt)
    for e in entries:
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(1.5), 1.0
        nivel = int(e.get("level", 0))
        pf.left_indent, pf.first_line_indent = Cm(0.5 * nivel + 0.6), Cm(-0.6)
        pf.tab_stops.add_tab_stop(Cm(TEXT_WIDTH_CM), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        _set_font(p.add_run(texto_indivisible(str(e["text"]))), size=pt, bold=(nivel == 0))
        page = e.get("page")
        _set_font(p.add_run("\t" + (str(page) if page else str(e.get("placeholder", "000")))), size=pt)
    return len(entries)


def build_document(blocks: list, lang: str, out: Path, bib_path: Path | None = None, supplementary_prefix: bool = False,
                   embed_cache: Path | None = None, journal: dict | None = None) -> dict:
    """Construye el DOCX; devuelve conteos (palabras del cuerpo, tablas, figuras, referencias).

    `journal` (dict, véase arriba) activa el modo revista; con `None` el documento es el de siempre."""
    cit = Citations(parse_bib(bib_path)) if bib_path else Citations()
    J = dict(journal) if journal else None
    body_pt = float(J.get("body_pt", CUERPO_PT)) if J else CUERPO_PT
    line_sp = float(J.get("line_spacing", 1.5)) if J else 1.5
    # interlineado de lo que no es párrafo del cuerpo (subtítulo, autores, «small», referencias, entradillas de
    # lámina): 1,15 como siempre salvo que la revista pida otra cosa (el suplemento, «single spaced», pide 1,0)
    aux_sp = float(J.get("aux_line_spacing", 1.15)) if J else 1.15
    heading_pt = float(J.get("heading_pt", body_pt)) if J else None
    resolve = (lambda t: journal_resolve(cit, t)) if (J and J.get("superscript_citations")) else cit.resolve
    if J:
        prenumber_citations(cit, blocks)
    doc = nuevo_doc()
    n_tab = n_fig = 0
    n_refs_printed = 0
    words = 0
    after_heading = True
    T, F = WORDS["table"][lang], WORDS["figure"][lang]
    pref = "S" if supplementary_prefix else ""
    plates = plan_full_page_plates(blocks, lang, supplementary_prefix, journal=J)
    lead_of = {v["lead_index"]: i for i, v in plates.items() if v["lead_index"] is not None}
    start_of = {v["start_index"]: v for v in plates.values()}
    # dónde se imprime el salto de página de cada unidad: en su primer bloque (título o entradilla) o, cuando
    # la entradilla se queda con la cola de la leyenda anterior, en la imagen
    break_at = {v["break_index"] for v in plates.values() if v["page_break"]}
    plate_report = []
    for i, (kind, payload) in enumerate(blocks):
        inicio = start_of.get(i)
        if inicio is not None and inicio["open_section"]:
            _sectpr_paragraph(doc, BODY_MARGIN_CM)
        if kind == "title":
            if J:
                parrafo(doc, payload, size=float(J.get("title_pt", 14)), bold=True, align=WD_ALIGN_PARAGRAPH.CENTER,
                        line=1.2, space_after=10, refs_bold=False)
            else:
                parrafo(doc, payload, size=15, bold=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=1.2, space_after=10, refs_bold=False)
        elif kind == "subtitle":
            parrafo(doc, payload, size=11, italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, line=aux_sp, space_after=10, refs_bold=False)
        elif kind == "authors":
            a_pt, l_pt = (body_pt, max(body_pt - 1, 9)) if J else (12, 11)
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            for i, (name, aff) in enumerate(payload["authors"]):
                _set_font(p.add_run(name), size=a_pt)
                _set_font(p.add_run(aff), size=a_pt, superscript=True)
                if i < len(payload["authors"]) - 1:
                    _set_font(p.add_run(", "), size=a_pt)
            for aff, text in payload["affiliations"]:
                q = doc.add_paragraph()
                q.alignment = WD_ALIGN_PARAGRAPH.CENTER
                q.paragraph_format.line_spacing = aux_sp
                _set_font(q.add_run(aff), size=l_pt, superscript=True)
                _set_font(q.add_run(" " + text), size=l_pt)
            for line in payload.get("lines", []):
                parrafo(doc, line, size=l_pt, align=WD_ALIGN_PARAGRAPH.CENTER, line=aux_sp, space_before=6, refs_bold=False)
        elif kind == "pagebreak":
            doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
        elif kind == "toc":
            if J and J.get("toc"):
                indice(doc, payload.get("title") or "Contents", payload.get("entries") or [], pt=body_pt,
                       title_pt=float(J.get("title_pt", 12)))
            after_heading = True
        elif kind in ("h1", "h2", "h3"):
            par = titulo(doc, payload, int(kind[1]), pt=heading_pt, line=aux_sp)
            if i in break_at:
                _page_break_before(par)
            after_heading = True
        elif kind == "p":
            text = resolve(payload)
            words += len(text.split())
            if i in lead_of:                      # entradilla de una lámina a página completa
                entrada = plates[lead_of[i]]
                lay = entrada["layout"]
                pt = lay.get("lead_pt") or CUERPO_PT
                # la entradilla que sigue a la cola de una leyenda NO lleva keepNext: arrastraría las dos a
                # la página siguiente y dejaría la cola sola
                par = parrafo(doc, text, size=pt, line=(aux_sp if J else (lay.get("lead_line") or 1.5)),
                              space_after=6 if pt >= CUERPO_PT else 3,
                              first_line_indent=None if (after_heading or J) else 0.75,
                              keep_with_next=entrada["lead_keep"], refs_bold=not J)
                if i in break_at:
                    _page_break_before(par)
            elif J:
                # la revista separa los párrafos con espacio y prohíbe la sangría de primera línea
                parrafo(doc, text, size=body_pt, line=line_sp, first_line_indent=None, refs_bold=False)
            else:
                parrafo(doc, text, first_line_indent=None if after_heading else 0.75)
            after_heading = False
        elif kind == "small":
            parrafo(doc, resolve(payload), size=min(10, body_pt), line=aux_sp, space_after=4, refs_bold=not J)
            after_heading = True
        elif kind == "bullets":
            for item in payload:
                text = resolve(item)
                words += len(text.split())
                if J:
                    parrafo(doc, "• " + text, size=body_pt, line=line_sp, first_line_indent=0, space_after=3,
                            refs_bold=False)
                else:
                    parrafo(doc, "• " + text, first_line_indent=0, space_after=3)
            after_heading = True
        elif kind == "eq":
            paths, number = payload
            insertar_ecuacion(doc, paths, number, lang, size=body_pt, keep_together=bool(J))
            after_heading = True
        elif kind == "table":
            n_tab += 1
            label = payload.get("label") or f"{T} {pref}{n_tab}"
            if J:
                t_pt = float(J.get("table_pt", 8))
                rotulo_tabla(doc, label, payload["title"], pt=float(J.get("table_heading_pt", 10)), bold_title=True)
                df = payload["df"]
                if payload.get("heading_column"):           # la columna de grupo se imprime como encabezados internos
                    df = agrupar_por_columna(df, payload["heading_column"])
                insertar_tabla(doc, df, payload.get("font_pt"), block_bold=True, max_pt=t_pt,
                               min_pt=(float(J["table_min_pt"]) if J.get("table_min_pt") else None),
                               cant_split=bool(J.get("table_rows_cant_split")))
                # la revista pide la leyenda (nota) de la tabla a 10 pt, como la de las figuras
                nota_tabla(doc, resolve(payload.get("note", "")), lang, size=float(J.get("table_note_pt", t_pt)),
                           refs_bold=False)
            else:
                rotulo_tabla(doc, label, payload["title"])
                insertar_tabla(doc, payload["df"], payload.get("font_pt"))
                nota_tabla(doc, cit.resolve(payload.get("note", "")), lang)
            after_heading = True
        elif kind == "figure":
            n_fig += 1
            label = payload.get("label") or f"{F} {pref}{n_fig}"
            heading = payload.get("heading") if J else None
            entrada = plates.get(i)
            if entrada is None:
                insertar_figura(doc, payload["path"], embed_dpi=payload.get("embed_dpi"), cache_dir=embed_cache)
                if J:
                    pie_figura(doc, label, resolve(payload["caption"]), size=float(J.get("legend_pt", 10)),
                               heading=heading)
                else:
                    pie_figura(doc, label, cit.resolve(payload["caption"]))
            else:
                lay = entrada["layout"]
                img = insertar_figura(doc, payload["path"], ancho_cm=lay["width_cm"], full_page=True,
                                      embed_dpi=payload.get("embed_dpi"), cache_dir=embed_cache)
                if i in break_at:
                    _page_break_before(img)
                cap_txt = cap_full = resolve(payload["caption"])
                cola = ""
                # La leyenda se parte aquí —la cabeza bajo la imagen, la cola rotulada «(continuación)»—
                # SIEMPRE que no quepa entera bajo su lámina (`split_caption`), y la cola cae en uno de dos
                # sitios. Con la sección CERRADA justo detrás —las cinco figuras del artículo y la última
                # lámina de cada tanda del suplemento— la cola no puede fluir hacia la lámina siguiente: el
                # corte de sección abre página y la cola se quedaría sola con 27,6–28,7 cm de papel en
                # blanco; se parte y pasa AL CUERPO del texto, después del corte, donde la sigue el párrafo
                # siguiente y la página se llena. Con la sección ABIERTA —dentro de una tanda de láminas— la
                # cola abre la página de la lámina SIGUIENTE, encima de su entradilla. En los dos sitios
                # lleva el rótulo, que es lo único que Word no puede poner cuando parte un párrafo por su
                # cuenta y lo único que le dice al lector de quién es el párrafo con el que abre la página.
                parte = entrada.get("split_caption", entrada["close_section"])
                if parte and lay["spill_cm"] > 1e-9:
                    cabeza, cola = split_caption_lines(label + ". ", cap_txt, lay["caption_pt"],
                                                       lay["caption_lines_page"], hard_spaces=bool(J))
                    if cola:
                        cap_txt = cabeza
                pie_figura(doc, label, cap_txt, size=lay["caption_pt"], space_after=0, heading=heading)
                if entrada["close_section"]:
                    _sectpr_paragraph(doc, PLATE_MARGIN_CM)
                    if cola:
                        pie_continuacion(doc, label, cola, lang, size=lay["caption_pt"])
                elif cola:
                    # La sección NO se cierra detrás de la lámina: nada abre página por sí solo, así que el
                    # salto se pone aquí. Sin él, la cola empezaría bajo la cabeza en la misma página y el
                    # rótulo «(continuación)» aparecería a media página. Con él, la página siguiente abre
                    # rotulada, que es lo que le faltaba a las doce a veintidós leyendas por documento que
                    # Word partía sin decir de quién era la mitad que caía fuera.
                    _page_break_before(pie_continuacion(doc, label, cola, lang, size=lay["caption_pt"],
                                                        space_after=PLATE_CAP_CONT_AFTER_PT))
                plate_report.append(dict(label=label, file=Path(payload["path"]).name, width_mm=round(lay["width_cm"] * 10, 1),
                                         height_mm=round(lay["height_cm"] * 10, 1), caption_pt=lay["caption_pt"],
                                         lead_in=entrada["lead_index"] is not None, lead_pt=lay.get("lead_pt"),
                                         lead_head=" ".join(str(entrada.get("lead_text") or "").split()[:7]),
                                         caption_head=" ".join(str(cap_full).split()[:7]),
                                         own_page=entrada["own_page"], mode=lay["mode"],
                                         headings_cm=round(lay["extra_cm"], 2), spill_cm=round(lay["spill_cm"], 2),
                                         carry_in_cm=entrada["carry_in_cm"], page_break=entrada["page_break"],
                                         caption_split=bool(cola), caption_lines_page=lay["caption_lines_page"],
                                         caption_lines_total=lay["caption_lines_total"],
                                         # las últimas palabras de la leyenda COMPLETA y las primeras de la
                                         # cola: con ellas la auditoría del PDF impreso comprueba, sin volver
                                         # a leer el DOCX, que la leyenda termina en la página de su lámina o
                                         # que su cola abre la siguiente ya rotulada
                                         caption_end=" ".join(str(cap_full).split()[-8:]),
                                         caption_tail_head=" ".join(str(cola).split()[:8]),
                                         structural_overflow=entrada.get("structural_overflow", False),
                                         embed_dpi=payload.get("embed_dpi") or 600))
            after_heading = True
        elif kind == "panel":
            panel(doc, payload["title"], [(h, resolve(t)) for h, t in payload["items"]], lang,
                  pt=(float(J["panel_pt"]) if J and J.get("panel_pt") else None), line=aux_sp)
            after_heading = True
        elif kind == "refs":
            # ("refs", None) lists every reference resolved so far; ("refs", {"continue": True, "title": "..."})
            # lists only the ones that no earlier reference section of the same document has already printed, so a
            # single file can carry the article's References and, after them, the supplementary references.
            opts = payload if isinstance(payload, dict) else {}
            titulo(doc, opts.get("title") or WORDS["references"][lang], 1, pt=heading_pt, line=aux_sp)
            refs = cit.reference_list()
            start = n_refs_printed if opts.get("continue") else 0
            r_pt = float(J.get("refs_pt", 10)) if J else 11
            for i, ref in enumerate(refs[start:], start + 1):
                p = doc.add_paragraph()
                pf = p.paragraph_format
                pf.left_indent, pf.first_line_indent, pf.space_after, pf.line_spacing = Cm(0.9), Cm(-0.9), Pt(4), aux_sp
                _set_font(p.add_run(f"{i}.\t"), size=r_pt)
                if J:      # modo revista: el rango de páginas de una referencia («101–33») no se parte en la raya
                    ref = re.sub(r"(?<=\d)\u2013(?=\d)", "\u2060\u2013\u2060", ref)
                _set_font(p.add_run(texto_indivisible(ref)), size=r_pt)
            n_refs_printed = len(refs)
    if J:
        _absorb_trailing_section(doc)     # la última lámina no deja una página en blanco detrás
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    doc.save(out)
    return dict(path=str(out), words=words, tables=n_tab, figures=n_fig, references=len(cit.order),
                full_page_plates=plate_report)


if __name__ == "__main__":
    import tempfile
    blocks = [("title", "Prueba"), ("h1", "1. Sección"), ("p", "Texto con cita [@zeidan2022] y **negrita** y *cursiva*; ver Tabla 1."),
              ("table", dict(df=pd.DataFrame({"A": [1, 2], "B": ["x", "y"]}), title="Tabla de prueba", note="Nota de prueba.")),
              ("panel", dict(title="Research in context", items=[("Evidence before this study", "Texto."), ("Added value", "Texto.")])),
              ("refs", None)]
    with tempfile.TemporaryDirectory() as tmp:
        print(build_document(blocks, "en", Path(tmp) / "t.docx"))
