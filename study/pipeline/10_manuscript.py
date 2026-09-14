# -*- coding: utf-8 -*-
"""10_manuscript.py — módulo 10: manuscritos y apéndices Word, PDF, miniaturas de revisión, memo e informe.

Para cada variante (`con_rett`, `sin_rett`) e idioma (`en`, `es`) construye con `docx_builder.build_document`:

  manuscript/manuscript_<variante>_<idioma>.docx
      Artículo + PARTE SUPLEMENTARIA en el mismo archivo. Artículo: portada con autores y afiliación tomados de
      `paper/prose.py` (AUTHORS, AFFILIATIONS), título corto y recuentos de palabras (calculados sobre
      `prose_*.article()`, no sobre el archivo completo); texto de `prose_en.py` / `prose_es.py` con la marca
      '[OPT] ' eliminada pero los párrafos opcionales conservados; Figuras 1–5 y Tablas 1–7; Referencias. Tras las
      Referencias, con salto de página, «Supplementary material» / «Material suplementario»: nota e índice, la
      metodología extendida de `prose_methods_extended.methods_blocks` (módulo 12) con las 33 ecuaciones numeradas
      de `equations.py`, las láminas suplementarias agrupadas por tema y las tablas suplementarias, todo con
      la numeración del registro compartido (Figura/Figure S1… y Tabla/Table S1…). Al final, la página «Optional
      material index» / «Índice de material opcional» que lista los párrafos opcionales.
  manuscript/supplement_<variante>_<idioma>.docx
      Apéndice suplementario separado: portada propia, contenido, métodos S1–S5 de `prose_*` y exactamente la misma
      parte suplementaria del manuscrito, construida desde el mismo registro, de modo que «Tabla S8» designa el
      mismo ítem en ambos documentos.
  manuscript/*.pdf                                  conversión con LibreOffice (`soffice --headless --convert-to pdf`)
  manuscript/review/<nombre>/page-NNN.png           miniaturas a 45 ppp (`pdftoppm`)
  manuscript/review/<nombre>_contact_sheet.png      hoja de contacto por documento
  manuscript/build_report.json                      recuentos de palabras, páginas, tablas, láminas y referencias
  memo_es.md                                        memo ejecutivo en español (cifras de outputs/values_<variante>.json)

Reglas: ninguna cifra del memo ni de la portada es literal; todas provienen de `outputs/values_<variante>.json`,
de `outputs/controls/controls_summary.csv` o de los recuentos calculados por `prose_*.word_counts`. Ninguna cita de
figura o tabla del artículo se escribe como literal: `prose_*` las produce con `R.mfig()` / `R.mtab()` a partir de
MAIN_FIGURES / MAIN_TABLES, y los ítems suplementarios con `R.fig()` / `R.tab()` a partir de SUPP_FIGURES /
SUPP_TABLES (véase `supplementary_material.py`).

Además, para cada variante e idioma:

  manuscript/article_<variante>_<idioma>.docx
      El ARTÍCULO SOLO, que termina en las Referencias: los mismos bloques de `prose_*.article()` con la marca
      '[OPT] ' eliminada, la misma portada (con una línea que dice dónde está la parte suplementaria y que
      comparte numeración) y sin índice de material opcional. El archivo combinado sigue siendo el entregable
      principal; este es de conveniencia para leer o circular sólo el artículo.

Colocación de las láminas: cada lámina VERTICAL a tamaño de norma (180 × 245 mm) se imprime SIEMPRE a 1:1,
en una sección de márgenes reducidos (19,6 × 28,68 cm de caja), y con ella entran en la misma página los
títulos que la preceden, su frase de presentación —compuesta al cuerpo que quepa, de 12 a 7 pt, y pegada
SIEMPRE a su lámina— y su leyenda —de 9 a 7 pt, y NUNCA por debajo de 7: la leyenda que no cabe se parte,
no se encoge—. Cuando la leyenda no cabe entera, su cola pasa a la página siguiente, donde entra también la
lámina siguiente; y cuando detrás de la leyenda se cierra la sección —las figuras del artículo— o la leyenda
desborda la página entera —la Figura 1—, la cola se parte en el código y se imprime rotulada
«(continuación)», y la sigue el texto que venía detrás de la lámina. El único cuerpo por debajo del suelo
son los 6,5 pt de `docx_builder.PLATE_CAP_STRAND_PT`, y sólo para la leyenda cuya cola, medio punto más
grande, dejaría una página con la cola y nada más: `plate_summary` dice cuáles son y `build_report.json`
las lleva anotadas una a una. Ninguna página lleva sólo la frase de presentación de
una lámina ni sólo la cola de una leyenda, y ninguna lámina se imprime sin al menos las primeras líneas de
su leyenda debajo: lo primero imprimía 43 de las 116 páginas de la región de láminas del suplemento, lo
segundo 3–4 páginas por documento en el artículo y lo tercero una lámina rotulada y muda.
`page_layout_audit` mide TODAS las regiones del PDF construido —artículo, láminas y tablas— en caracteres
y en ALTURA OCUPADA, POR SEPARADO (exigir las dos a la vez no ve la lámina sin leyenda, que llena la página
de imagen), y comprueba en el propio PDF que la entradilla de cada lámina está impresa en la página de su
lámina y que su leyenda empieza bajo ella; el recuento va a `build_report.json`.
Véase `docx_builder.plate_layout`, `docx_builder.split_caption_lines` y `docx_builder.plan_full_page_plates`.

Tamaño de los archivos: `--supp-dpi` (300 por defecto) incrusta las láminas SUPLEMENTARIAS remuestreadas a esa
resolución para el ancho al que se imprimen; las figuras del artículo se incrustan sin remuestrear y los PNG
del disco se quedan siempre a 600 ppp.

Uso:
    python study/pipeline/10_manuscript.py                    # todo (4 manuscritos + 4 apéndices + 4 artículos, PDF, miniaturas, memo)
    python study/pipeline/10_manuscript.py --langs en --variants con_rett --skip-pdf
    python study/pipeline/10_manuscript.py --supp-dpi 0       # sin remuestrear (archivos de ~135 MB)
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import copy
import datetime as dt
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent          # study/pipeline
LA = HERE.parent                                # study
REPO = LA.parent
for p in (str(LA), str(REPO / "paper")):
    if p not in sys.path:
        sys.path.insert(0, p)

import pandas as pd  # noqa: E402

import config as CFG  # noqa: E402
import controls_registry as CR  # noqa: E402  (ámbitos con nombre de los controles)
import prose_en  # noqa: E402
import prose_es  # noqa: E402
import references as REFS  # noqa: E402  (paper/references.py, shared Vancouver formatter)
import equations as EQ  # noqa: E402  (las 33 ecuaciones de la metodología extendida)
import labels as LB  # noqa: E402  (glosario de impresión: la forma que el lector ve)
from common import fmt_ci, fmt_number  # noqa: E402
import docx_builder as DB  # noqa: E402
from docx_builder import build_document  # noqa: E402

MANU = CFG.CORPUS                  # manuscript/02_others: the full two-variant corpus
REVIEW = MANU / "review"
REPORT_PATH = MANU / "build_report.json"
MEMO_PATH = LA / "memo_es.md"
CONTROLS_SUMMARY = CFG.OUT / "controls" / "controls_summary.csv"
VARIANTS = ("con_rett", "sin_rett")
LANGS = ("en", "es")
PROSE = {"en": prose_en, "es": prose_es}
OPT = prose_en.OPT
SOFFICE = shutil.which("soffice") or "/Applications/LibreOffice.app/Contents/MacOS/soffice"
PDFTOPPM = shutil.which("pdftoppm") or "pdftoppm"
PDFINFO = shutil.which("pdfinfo")
PDFTOTEXT = shutil.which("pdftotext")
THUMB_DPI = 45

W = {  # rótulos bilingües del módulo
    "opt_h1": {"en": "Optional material index", "es": "Índice de material opcional"},
    "opt_intro": {
        "en": ("The following {n} paragraphs ({w} words) are tagged as optional in the source text (prefix '[OPT] ', "
               "removed in this working version). They are candidates for removal or for transfer to the supplementary "
               "appendix when the manuscript is trimmed to the journal's 3500–5000-word limit; the core text "
               "(Introduction–Conclusion) without them has {core} words. Each entry gives the section, the number of "
               "words and the opening words of the paragraph."),
        "es": ("Los siguientes {n} párrafos ({w} palabras) están marcados como opcionales en el texto fuente (prefijo "
               "'[OPT] ', eliminado en esta versión de trabajo). Son candidatos a eliminarse o a trasladarse al apéndice "
               "suplementario cuando el manuscrito se recorte al límite de 3500–5000 palabras de la revista; el texto "
               "núcleo (Introducción–Conclusión) sin ellos tiene {core} palabras. Cada entrada indica la sección, el "
               "número de palabras y las primeras palabras del párrafo."),
    },
    "words": {"en": "words", "es": "palabras"},
    "corr": {"en": "Correspondence", "es": "Correspondencia"},
    "article": {"en": "Article type: Article (original research). Reporting guidelines: STROBE and RECORD.",
                "es": "Tipo de artículo: Artículo (investigación original). Guías de reporte: STROBE y RECORD."},
    "running": {"en": "Running title", "es": "Título corto"},
    "variant": {"en": "Analysis variant", "es": "Variante de análisis"},
    "counts": {
        "en": ("Word counts: Summary {summary}; Research in context {panel}; main text (Introduction–Conclusion) {core} "
               "words excluding the {n_opt} optional paragraphs ({opt} words) retained in this working version and listed "
               "in the Optional material index at the end; declarations {decl} words; {refs_core} references cited in the "
               "core text ({refs_all} including the optional paragraphs); {tables} tables and {figures} figures; "
               "supplementary part (after the References, in this same file) with {sfig} figures, {stab} tables and "
               "{neq} numbered equations."),
        "es": ("Recuentos de palabras: Resumen {summary}; Investigación en contexto {panel}; texto principal "
               "(Introducción–Conclusión) {core} palabras sin los {n_opt} párrafos opcionales ({opt} palabras) conservados "
               "en esta versión de trabajo y listados en el Índice de material opcional al final; declaraciones {decl} "
               "palabras; {refs_core} referencias citadas en el texto núcleo ({refs_all} incluidos los párrafos "
               "opcionales); {tables} tablas y {figures} láminas en el artículo; parte suplementaria (tras las "
               "Referencias, en este mismo archivo) con {sfig} láminas, {stab} tablas y {neq} ecuaciones."),
    },
    # Los límites de la revista se aplican al ENVÍO EN INGLÉS. El español es la traducción de trabajo del equipo:
    # se expande frente al inglés y debe mantener paridad de contenido y de cifras, no caber en los mismos límites.
    "limits": {"en": ("Journal limits — Summary 250 words, main text (Introduction–Conclusion) 3500–5000 words and 30 "
                      "references in the core text — apply to the English submission, which is the version to be "
                      "submitted and observes them. The Spanish file is the team's working translation: Spanish expands "
                      "against English, so it runs longer word for word, and it is checked for parity of content and of "
                      "every figure with the English text, never against the journal's word limits."),
               "es": ("Los límites de la revista —Resumen 250 palabras, texto principal (Introducción–Conclusión) "
                      "3500–5000 palabras y 30 referencias en el texto núcleo— se aplican al envío en inglés, que es la "
                      "versión que se envía y los cumple. Este archivo en español es la traducción de trabajo del equipo: "
                      "el español se expande frente al inglés, de modo que resulta más largo palabra por palabra, y se "
                      "comprueba por paridad de contenido y de todas las cifras con el texto en inglés, nunca contra los "
                      "límites de palabras de la revista.")},
    "built": {"en": ("Working version built on {date} by study/pipeline/10_manuscript.py from "
                     "outputs/values_{variant}.json; every number is traceable to the pipeline outputs. Not for submission "
                     "without the confirmations listed in memo_es.md."),
              "es": ("Versión de trabajo construida el {date} por study/pipeline/10_manuscript.py a partir de "
                     "outputs/values_{variant}.json; toda cifra es rastreable a las salidas del pipeline. No enviar sin las "
                     "confirmaciones listadas en memo_es.md.")},
    "supp_counts": {"en": "Supplementary appendix: {sfig} figures, {stab} tables and {neq} numbered equations, "
                          "identical to the supplementary part of the manuscript file.",
                    "es": "Apéndice suplementario: {sfig} láminas, {stab} tablas y {neq} ecuaciones numeradas, "
                          "idénticas a la parte suplementaria del archivo del manuscrito."},
}

# El archivo SÓLO CON EL ARTÍCULO no lleva ni el índice de material opcional ni la parte suplementaria, de
# modo que no puede imprimir la línea de recuentos del manuscrito combinado, que remite a las dos cosas.
W["counts_article_only"] = {
    "en": ("Word counts: Summary {summary}; Research in context {panel}; main text (Introduction–Conclusion) {core} "
           "words excluding the {n_opt} optional paragraphs ({opt} words) retained in this working version; "
           "declarations {decl} words; {refs_core} references cited in the core text ({refs_all} including the "
           "optional paragraphs); {tables} tables and {figures} figures. This file ends at the References: the "
           "supplementary part ({sfig} figures, {stab} tables and {neq} numbered equations) is in the combined "
           "manuscript file and in the standalone appendix, which carry the same numbering."),
    "es": ("Recuentos de palabras: Resumen {summary}; Investigación en contexto {panel}; texto principal "
           "(Introducción–Conclusión) {core} palabras sin los {n_opt} párrafos opcionales ({opt} palabras) conservados "
           "en esta versión de trabajo; declaraciones {decl} palabras; {refs_core} referencias citadas en el texto "
           "núcleo ({refs_all} incluidos los párrafos opcionales); {tables} tablas y {figures} láminas. Este archivo "
           "termina en las Referencias: la parte suplementaria ({sfig} láminas, {stab} tablas y {neq} ecuaciones "
           "numeradas) está en el archivo del manuscrito combinado y en el apéndice separado, que comparten la misma "
           "numeración."),
}

REQUIRED_SUPP_TABLES = ("T8_controls", "ST2_rem_code_dictionary", "ST7_provenance", "T7_models_cpa_full")

# Resolución a la que se INCRUSTAN las láminas suplementarias (el PNG del disco sigue a 600 ppp y las
# figuras del artículo se incrustan sin remuestrear). A 300 ppp una lámina de 180 mm entra con ~2126 px,
# más que suficiente para imprimir, y el archivo del manuscrito baja de ~135 MB a una fracción.
SUPP_DPI_DEFAULT = 300
EMBED_CACHE = MANU / ".embed_cache"


def log(msg: str) -> None:
    print(f"[10_manuscript] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Autores (paper/prose.py) y referencias en inglés
# ---------------------------------------------------------------------------
def load_paper_authors(path: Path = REPO / "paper" / "prose.py") -> tuple[list, list]:
    """AUTHORS y AFFILIATIONS de paper/prose.py leídos con `ast` (sin importar el módulo ni sus efectos)."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ("AUTHORS", "AFFILIATIONS"):
                found[name] = ast.literal_eval(node.value)
    if "AUTHORS" not in found or "AFFILIATIONS" not in found:
        raise RuntimeError(f"AUTHORS/AFFILIATIONS no encontrados en {path}")
    return found["AUTHORS"], found["AFFILIATIONS"]


#: Corchetes EDITORIALES de la entrada bibliográfica: son palabras del que cita —dicen dónde y con qué otro
#: rótulo aparece publicado el documento—, no el título de la fuente, y por eso se traducen igual que
#: «Disponible en:». El título entrecomillado que va dentro del corchete SÍ es de la fuente y se transcribe.
_ES_EDITORIAL = (
    ("[en el portal: ", "[on the portal: "),
    ("[título del informe en portada y en el portal: ", "[report title on the cover and on the portal: "),
    ("[base de datos y ", "[database and "),
    (", febrero de 2026]", ", February 2026]"),
)


def localise_reference(text: str, lang: str) -> str:
    """El formateador compartido escribe conectores en español; el documento en inglés los traduce.

    En ambos idiomas corrige dos artefactos del formateador: el rango de años con doble guion heredado del .bib
    («2020--2026» → «2020–2026») y el punto añadido tras un título que termina en «?» («Mortality?.» → «Mortality?»)."""
    text = re.sub(r"(\d)--(\d)", r"\1–\2", text).replace("?. ", "? ")
    if lang != "en":
        return text
    text = (text.replace(" Disponible en: ", " Available from: ").replace(", editores.", ", editors.")
            .replace(", editores", ", editors").replace(". En: ", ". In: "))
    for es, en in _ES_EDITORIAL:
        text = text.replace(es, en)
    return text


def journal_reference_entry(entry: dict) -> dict:
    """La entrada bibliográfica con el intervalo de páginas unido por RAYA CORTA («1687–92»), que es lo que
    pide la revista. Sólo se toca el campo `pages`: un DOI lleva guiones entre cifras que no son intervalos."""
    pages = entry.get("pages")
    if not pages:
        return entry
    out = dict(entry)
    out["pages"] = re.sub(r"(?<=\d)\s*-{1,2}\s*(?=\d)", "\u2013", str(pages))
    return out


#: Journal names abbreviated «in their standard form as in Index Medicus» (journal rule), keyed by the name
#: normalised to lower-case alphanumerics. Only the journals of references.bib that the submission or its
#: appendix cites; an unlisted journal is printed as it is in the .bib (and reported by `journal_unabbreviated`).
JOURNAL_ABBREVIATIONS = {
    "americanjournalofepidemiology": "Am J Epidemiol",
    "andespediatrica": "Andes Pediatr",
    "appliedstatistics": "J R Stat Soc Ser C Appl Stat",
    "autism": "Autism",
    "autismresearch": "Autism Res",
    "bmj": "BMJ",
    "biometrika": "Biometrika",
    "geographicalanalysis": "Geogr Anal",
    "jama": "JAMA",
    "jamapediatrics": "JAMA Pediatr",
    "journalofchildpsychologyandpsychiatry": "J Child Psychol Psychiatry",
    "journalofstatisticalsoftware": "J Stat Softw",
    "journaloftheamericanacademyofchildadolescentpsychiatry": "J Am Acad Child Adolesc Psychiatry",
    "journaloftheamericanstatisticalassociation": "J Am Stat Assoc",
    "journaloftheroyalstatisticalsocietyseriesbstatisticalmethodology": "J R Stat Soc Series B Stat Methodol",
    "mmwrsurveillancesummaries": "MMWR Surveill Summ",
    "newenglandjournalofmedicine": "N Engl J Med",
    "plosmedicine": "PLoS Med",
    "proceedingsoftheroyalsocietyoflondonseriesamathematicalandphysicalsciences": "Proc R Soc Lond A Math Phys Sci",
    "researchintegrityandpeerreview": "Res Integr Peer Rev",
    "statisticalscience": "Stat Sci",
    "statisticsinmedicine": "Stat Med",
    "thelancet": "Lancet",
    "lancet": "Lancet",
}
JOURNAL_UNABBREVIATED: list[str] = []      # journals met without an abbreviation (reported in the build)
_MONTHS_EN = {1: "Jan", 2: "Feb", 3: "March", 4: "April", 5: "May", 6: "June", 7: "July", 8: "Aug", 9: "Sept",
              10: "Oct", 11: "Nov", 12: "Dec"}
_MONTHS_ES = {1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 7: "julio", 8: "agosto",
              9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"}


def _journal_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower().replace("&", "").replace("\\", ""))


def journal_abbreviation(name: str) -> str:
    key = _journal_key(name)
    if key in JOURNAL_ABBREVIATIONS:
        return JOURNAL_ABBREVIATIONS[key]
    if name and name not in JOURNAL_UNABBREVIATED:
        JOURNAL_UNABBREVIATED.append(name)
    return name


def journal_page_range(pages: str) -> str:
    """The journal's own example: «Lancet 1998; 351: 1687–92» — the end page keeps only the digits that differ
    from the start page (same length, at least two digits kept); other forms («e1001885», «h1961») untouched."""
    m = re.fullmatch(r"(\d+)\u2013(\d+)", str(pages))
    if not m:
        return pages
    a, b = m.group(1), m.group(2)
    if len(a) != len(b) or len(b) < 3 or int(b) < int(a):
        return pages
    i = 0
    while i < len(a) - 2 and a[i] == b[i]:
        i += 1
    return f"{a}\u2013{b[i:]}"


def accessed_date(urldate: str, lang: str) -> str | None:
    """«(accessed Sept 4, 2026)» / «(consultado el 4 de septiembre de 2026)» from the ISO urldate of the .bib."""
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", str(urldate or "").strip())
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if lang == "es":
        return f"(consultado el {d} de {_MONTHS_ES[mo]} de {y})"
    return f"(accessed {_MONTHS_EN[mo]} {d}, {y})"


def journal_reference_style(text: str, entry: dict, lang: str) -> str:
    """The journal's reference form applied to a formatted entry (journal mode only): Index Medicus journal
    abbreviation, «J year; vol: pages.» without the issue number and with the shortened end page for journal
    articles, and the access date after the URL of online material (the .bib urldate)."""
    if entry.get("_kind") == "article" and entry.get("journal"):
        name = REFS._clean(entry["journal"])
        abbr = journal_abbreviation(name)
        # the title may end in «?» or «!» instead of a full stop (Iezzoni 1992, the readers' reference 27):
        # the punctuation mark that closes the title is kept and the journal form applied all the same
        rx = re.compile(r"([.?!]) " + re.escape(name) + r"\. (\d{4});([^(:;.\s]+)(?:\([^)]*\))?:([^.]+?)\.")
        text, n = rx.subn(lambda m: f"{m.group(1)} {abbr} {m.group(2)}; {m.group(3)}: {journal_page_range(m.group(4))}.",
                          text, count=1)
        if not n:
            for mark in (".", "?", "!"):
                if f"{mark} {name}. " in text:
                    text = text.replace(f"{mark} {name}. ", f"{mark} {abbr}. ", 1)
                    break
    if entry.get("url") and not entry.get("doi") and entry.get("urldate"):
        acc = accessed_date(entry["urldate"], lang)
        if acc:
            text = text.rstrip().rstrip(".") + " " + acc + "."
    return text


def journal_author_list(original):
    """Regla de autores de la revista: seis o menos, todos; siete o más, los tres primeros y «et al».

    El formateador compartido lista hasta seis y añade «et al» a partir del séptimo; aquí, cuando hay más de
    seis, se le pide que liste sólo tres."""
    def patched(raw: str, limit: int = 6) -> str:
        parts = [p.strip() for p in re.split(r"\s+and\s+", str(raw).strip()) if p.strip()]
        names = [p for p in parts if p.lower() != "others"]
        # «and others» en el .bib significa que la lista está truncada: hay más de seis
        more_than_six = len(names) > 6 or len(names) < len(parts)
        return original(raw, 3 if more_than_six else limit)
    return patched


@contextlib.contextmanager
def localised_references(lang: str, journal: bool = False):
    """Referencias en el idioma del documento; con `journal=True`, además con la regla de autores y la raya
    corta en las páginas que pide la revista (véanse `journal_author_list` y `journal_reference_entry`)."""
    original = REFS.format_vancouver
    original_authors = REFS._author_list

    def patched(entry):
        if journal:
            entry = journal_reference_entry(entry)
        text = localise_reference(original(entry), lang)
        return journal_reference_style(text, entry, lang) if journal else text

    REFS.format_vancouver = patched
    if journal:
        REFS._author_list = journal_author_list(original_authors)
    try:
        yield
    finally:
        REFS.format_vancouver = original
        REFS._author_list = original_authors


# ---------------------------------------------------------------------------
# Bloques: portada, párrafos opcionales, ecuaciones
# ---------------------------------------------------------------------------
_CIT = re.compile(r"\s*\[@[^\]]+\]")


def _wc(text: str) -> int:
    return len(_CIT.sub("", str(text)).replace(" ", "").split())


def excerpt(text: str, n_words: int = 12) -> str:
    clean = _CIT.sub("", str(text)).replace("**", "").replace(" ", " ")
    words = clean.split()
    return " ".join(words[:n_words]) + ("…" if len(words) > n_words else "")


def strip_opt_with_index(blocks: list, lang: str) -> tuple[list, list]:
    """Quita la marca '[OPT] ' conservando el párrafo; devuelve (bloques, índice de opcionales).

    Las palabras se cuentan con el mismo contador que `prose_<lang>.word_counts` para que el índice y la portada coincidan."""
    counter = getattr(PROSE.get(lang), "_wc", _wc)
    out, index = [], []
    h1 = h2 = None
    for kind, payload in blocks:
        if kind == "h1":
            h1, h2 = payload, None
        elif kind == "h2":
            h2 = payload
        if kind == "p" and str(payload).startswith(OPT):
            text = payload[len(OPT):]
            index.append(dict(n=len(index) + 1, section=h1, subsection=h2, words=counter(text), excerpt=excerpt(text)))
            out.append((kind, text))
        else:
            out.append((kind, payload))
    return out, index


def optional_index_blocks(index: list, lang: str, core_words: int) -> list:
    total = sum(e["words"] for e in index)
    items = []
    for e in index:
        where = e["section"] + (f" › {e['subsection']}" if e["subsection"] else "")
        items.append(f"{e['n']}. {where} — {e['words']} {W['words'][lang]} — “{e['excerpt']}”")
    intro = W["opt_intro"][lang].format(n=len(index), w=fmt_number(total, 0, lang), core=fmt_number(core_words, 0, lang))
    return [("pagebreak", None), ("h1", W["opt_h1"][lang]), ("p", intro), ("bullets", items)]


def authors_payload(lang: str, P, authors: list, affiliations: list, lines: list) -> dict:
    auth = [(name, aff) for name, aff, _ in authors]
    affs = []
    for aff, text in affiliations:
        # el marcador entre corchetes de paper/prose.py está en español; el documento en inglés usa el de prose_en
        affs.append((aff, P.AFFILIATION if (lang == "en" and text.startswith("[")) else text))
    return dict(authors=auth, affiliations=affs, lines=lines)


def title_page(blocks: list, lang: str, variant: str, P, authors: list, affiliations: list, counts: dict,
               supplement: bool = False, article_only: bool = False) -> list:
    kinds = [k for k, _ in blocks[:3]]
    if kinds != ["title", "subtitle", "authors"]:
        raise RuntimeError(f"portada inesperada en prose_{lang}: {kinds}")
    title = blocks[0][1]
    subtitle = blocks[1][1]
    email_author = next(((n, e) for n, _, e in authors if e), (authors[0][0], ""))
    lines = [f"{W['corr'][lang]}: {email_author[0]}" + (f" ({email_author[1]})" if email_author[1] else ""),
             W["article"][lang], f"{W['running'][lang]}: {P.RUNNING_TITLE}"]
    if supplement:
        lines.append(W["supp_counts"][lang].format(**counts))
    else:
        lines.append(W["counts_article_only" if article_only else "counts"][lang].format(**counts))
        lines.append(W["limits"][lang])
    lines.append(W["built"][lang].format(date=dt.date.today().isoformat(), variant=variant))
    return ([("title", title), ("subtitle", subtitle),
             ("authors", authors_payload(lang, P, authors, affiliations, lines))] + blocks[3:])


# ---------------------------------------------------------------------------
# Posproceso del DOCX: numeración de páginas y secciones apaisadas para tablas anchas
# ---------------------------------------------------------------------------
PAGE_W_CM, PAGE_H_CM, MARGIN_CM = 21.0, 29.7, 2.5
LANDSCAPE_TEXT_WIDTH_CM = PAGE_H_CM - 2 * MARGIN_CM   # 24,7 cm


MIN_TABLE_PT = 6.0            # tamaño mínimo de fuente de una tabla apaisada que no cabe a su tamaño original
#: Modo revista: el suelo de 8 pt rige mientras la tabla quepa apaisada a 8 pt con sus columnas no más estrechas que
#: su palabra más larga (acotada a CAP_MIN_COL_CM) salvo por esta tolerancia; por encima de ella (una tabla de
#: procedencia con 14 columnas de nombres de archivo y SHA-256 pide el doble del ancho de la página) las celdas se
#: partirían letra a letra y cada fila ocuparía una página: esa tabla baja como en el corpus y se informa por su nombre.
JOURNAL_TABLE_PT_TOLERANCE = 1.25
JOURNAL_TABLE_PT_EXCEPTION_FLOOR = 7.0   # y esa excepción no baja de 7 pt: a 6 pt las celdas se parten igual y se leen peor
CAP_MIN_COL_CM = 4.0          # tope del mínimo por columna: un token muy largo (URL, nombre de archivo) se parte en vez de
                              # comprimir las demás columnas por debajo de su palabra más larga


def _min_widths_cm(cols: list, textos: list, pt: float, cap_cm: float | None = None) -> list:
    """Anchos mínimos por columna (palabra más larga) con la misma regla que docx_builder._anchos.

    Con `cap_cm` el mínimo de cada columna se acota a ese valor (véase CAP_MIN_COL_CM)."""
    pad_cm, seguro = 0.40, 1.08
    out = []
    for j, c in enumerate(cols):
        tok = 0.0
        for t in textos[j]:
            for w in DB._palabras(t):          # = str.split() unless the journal's soft breaks (U+200B) are present
                tok = max(tok, DB._ancho_texto(w, pt))
        for w in str(c).split():
            tok = max(tok, DB._ancho_texto(w, pt, bold=True))
        m = tok * seguro + pad_cm
        out.append(min(m, cap_cm) if cap_cm else m)
    return out


def _anchos_capped(cols: list, textos: list, pt: float, total_cm: float, cap_cm: float) -> list:
    """docx_builder._anchos con los mínimos acotados a `cap_cm` (misma regla de reparto de la holgura)."""
    pad_cm, seguro = 0.40, 1.08
    minimos = _min_widths_cm(cols, textos, pt, cap_cm)
    deseados = []
    for j, c in enumerate(cols):
        celdas = [str(t) for t in textos[j]]
        anchos_celda = sorted(max(DB._ancho_texto(line, pt) for line in t.split("\n")) for t in celdas) or [0.0]
        p90 = anchos_celda[int(0.9 * (len(anchos_celda) - 1))]
        cab = DB._ancho_texto(c, pt, bold=True) / 2.2
        deseados.append(max(max(p90, cab) * seguro + pad_cm, minimos[j]))
    tot_min, tot_des = sum(minimos), sum(deseados)
    if tot_min >= total_cm:
        return [total_cm * m / tot_min for m in minimos]
    if tot_des <= total_cm:
        return [total_cm * d / tot_des for d in deseados]
    holgura = total_cm - tot_min
    extra = [d - m for d, m in zip(deseados, minimos)]
    tot_extra = sum(extra) or 1.0
    return [m + holgura * e / tot_extra for m, e in zip(minimos, extra)]


def _fit_font_pt(cols: list, textos: list, pt: float, total_cm: float, min_pt: float | None = None) -> float:
    """Reduce la fuente en pasos de 0,5 pt (hasta MIN_TABLE_PT, o hasta `min_pt` si es mayor: el suelo de 8 pt
    de la revista) hasta que los mínimos acotados quepan en `total_cm`."""
    suelo = max(MIN_TABLE_PT, float(min_pt)) if min_pt is not None else MIN_TABLE_PT
    while pt > suelo and sum(_min_widths_cm(cols, textos, pt, CAP_MIN_COL_CM)) > total_cm:
        pt = round(pt - 0.5, 1)
    return max(pt, suelo)


def _set_table_font(tbl, pt: float) -> None:
    from docx.shared import Pt
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(pt)


def _keep_last_row_with_next(tbl) -> None:
    """keepNext en los párrafos de la última fila para que la nota no quede sola en una página nueva."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    for cell in tbl.rows[-1].cells:
        for p in cell.paragraphs:
            ppr = p._p.get_or_add_pPr()
            if ppr.find(qn("w:keepNext")) is None:
                ppr.append(OxmlElement("w:keepNext"))


def _table_font_pt(tbl) -> float:
    """Tamaño de fuente real de la tabla: primer run con tamaño en la fila de cabecera.

    docx_builder.insertar_tabla escribe `cell.text = ""` antes de añadir el run con fuente, de modo que el primer run
    de cada celda está vacío y sin tamaño; leer solo `runs[0]` devolvía siempre el valor por defecto (8 pt) y los
    anchos apaisados se calculaban con una fuente distinta de la impresa. Sin ningún run con tamaño se aplica la
    misma regla por número de columnas que docx_builder."""
    for cell in tbl.rows[0].cells:
        for p in cell.paragraphs:
            for r in p.runs:
                if r.font.size is not None:
                    return float(r.font.size.pt)
    n = len(tbl.columns)
    return 9.0 if n <= 5 else (8.5 if n <= 7 else (7.5 if n <= 9 else 7.0))


def keep_equation_leads(doc) -> int:
    """keepNext en el párrafo «(n) …» que precede a cada ecuación (tabla de 2 columnas y 1 fila), para que la frase
    de uso no quede al pie de una página y la imagen de la fórmula al inicio de la siguiente. Devuelve cuántos."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    n = 0
    for tbl in doc.tables:
        if len(tbl.columns) != 2 or len(tbl.rows) != 1:
            continue
        prev = tbl._tbl.getprevious()
        if prev is None or prev.tag != qn("w:p"):
            continue
        txt = "".join(t.text or "" for t in prev.iter(qn("w:t")))
        if re.match(r"^\(\d{1,2}\)\s", txt):
            ppr = prev.find(qn("w:pPr"))
            if ppr is None:
                ppr = OxmlElement("w:pPr")
                prev.insert(0, ppr)
            if ppr.find(qn("w:keepNext")) is None:
                ppr.insert(0, OxmlElement("w:keepNext"))
            n += 1
    return n


def _is_kept_heading(el) -> bool:
    """Párrafo no vacío con keepNext (título de sección generado por docx_builder.titulo) que precede a un rótulo de tabla."""
    from docx.oxml.ns import qn
    if el is None or el.tag != qn("w:p"):
        return False
    ppr = el.find(qn("w:pPr"))
    if ppr is None or ppr.find(qn("w:keepNext")) is None or ppr.find(qn("w:sectPr")) is not None:
        return False
    return bool("".join(t.text or "" for t in el.iter(qn("w:t"))).strip())


def _is_section_heading(el) -> bool:
    """Título de sección PROPIAMENTE DICHO: keepNext ACTIVO, no el `keepNext w:val="0"` de un párrafo normal.

    `_is_kept_heading` sólo mira si el elemento `w:keepNext` está presente, y python-docx lo escribe también
    —con `w:val="0"`— cuando se pide `keep_with_next=False`, de modo que cualquier párrafo del cuerpo pasa
    por título. Esa lectura laxa gobierna desde hace tiempo lo que la sección apaisada absorbe y no se toca
    aquí; esta otra, estricta, es la que decide cuánto se retrocede cuando delante hay la cola de la leyenda
    de una lámina, donde absorber un párrafo de más deja esa página con la cola y nada más."""
    from docx.oxml.ns import qn
    if not _is_kept_heading(el):
        return False
    kn = el.find(qn("w:pPr")).find(qn("w:keepNext"))
    return kn.get(qn("w:val")) not in ("0", "false", "off")


def _sect_paragraph(sect_pr, landscape: bool):
    """Párrafo vacío cuyo w:sectPr cierra la sección precedente (vertical u horizontal)."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    sp = copy.deepcopy(sect_pr)
    pg = sp.find(qn("w:pgSz"))
    if pg is None:
        pg = OxmlElement("w:pgSz")
        sp.insert(0, pg)
    w_dxa, h_dxa = str(int(PAGE_W_CM * 567)), str(int(PAGE_H_CM * 567))
    if landscape:
        pg.set(qn("w:w"), h_dxa)
        pg.set(qn("w:h"), w_dxa)
        pg.set(qn("w:orient"), "landscape")
    else:
        pg.set(qn("w:w"), w_dxa)
        pg.set(qn("w:h"), h_dxa)
        if pg.get(qn("w:orient")) is not None:
            del pg.attrib[qn("w:orient")]
    p = OxmlElement("w:p")
    ppr = OxmlElement("w:pPr")
    ppr.append(sp)
    p.append(ppr)
    return p


FOLIO_PT = 9        # cuerpo del número de página. A 10 pt medía 4,7 mm de alto y, con el pie de la sección
                    # de lámina a 2,5 mm del borde, se metía dentro de la caja de texto; a 9 pt mide 3,65 mm
                    # y deja 1 mm de aire bajo la caja de 28,68 cm. Es el pie de TODO el documento: en las
                    # secciones del cuerpo, con 12,5 mm de pie, sobra sitio de cualquier modo.


def add_page_numbers(doc) -> int:
    """Folio centrado al pie de CADA sección del documento. Devuelve el número de secciones numeradas.

    Se escribe en TODAS y no sólo en la primera por cómo hereda Word: una sección sin `w:footerReference`
    propia toma el pie de la anterior, nunca de la siguiente, de modo que el pie escrito en una sección
    intermedia deja sin folio todo lo que va DELANTE. Eso es lo que dejaba el apéndice suelto con sus
    primeras páginas —de la portada a la Tabla S12 apaisada— sin numerar: el pie se escribía en
    `sections[0]` ANTES de que `landscape_wide_tables` partiera el documento, y cada sección nueva abierta
    por una tabla ancha se intercalaba por delante, empujando la única sección con pie hasta la posición 10
    de 61. El manuscrito no lo notaba porque ya abría una sección propia antes de la primera tabla ancha.
    Escribir el pie en cada sección hace el resultado independiente de cuántas secciones haya y de en qué
    orden se abran; llamarlo al FINAL del posproceso, cuando las secciones ya son las definitivas, hace que
    ninguna quede sin él.
    """
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Pt
    n = 0
    for section in doc.sections:
        footer = section.footer
        footer.is_linked_to_previous = False
        p = footer.paragraphs[0]
        # Idempotencia: si esta sección ya lleva su folio no se escribe un segundo campo PAGE.
        if p._p.findall(qn("w:fldSimple")):
            n += 1
            continue
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.space_before, pf.space_after, pf.line_spacing = Pt(0), Pt(0), 1.0
        fld = OxmlElement("w:fldSimple")
        fld.set(qn("w:instr"), "PAGE")
        r = OxmlElement("w:r")
        rpr = OxmlElement("w:rPr")
        sz = OxmlElement("w:sz")
        sz.set(qn("w:val"), str(int(FOLIO_PT * 2)))
        rpr.append(sz)
        r.append(rpr)
        t = OxmlElement("w:t")
        t.text = "1"
        r.append(t)
        fld.append(r)
        p._p.append(fld)
        n += 1
    return n


def keep_panels_together(doc) -> int:
    """Marca como indivisible (w:cantSplit) la fila única de los paneles de una celda (Research in context) para que el
    recuadro no se parta entre páginas dejando una línea huérfana; si no cabe en la página, pasa entero a la siguiente.
    Devuelve el número de paneles marcados."""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    n = 0
    for tbl in doc.tables:
        if len(tbl.rows) != 1 or len(tbl.columns) != 1:
            continue
        tr_pr = tbl.rows[0]._tr.get_or_add_trPr()
        if tr_pr.find(qn("w:cantSplit")) is None:
            tr_pr.append(OxmlElement("w:cantSplit"))
            n += 1
    return n


def landscape_wide_tables(doc, lang: str, force_labels: tuple = (), min_pt: float | None = None) -> list:
    """Coloca en una sección apaisada cada tabla cuyas columnas no caben sin partir palabras en 16 cm.

    Se conserva la tabla ya construida (fuente, cabecera repetida) y se recalculan los anchos con
    docx_builder._anchos para 24,7 cm; el rótulo y el título (dos párrafos previos) y la nota (párrafo siguiente)
    acompañan a la tabla dentro de la sección. Devuelve las etiquetas de las tablas apaisadas.

    `force_labels` (modo revista): rótulos («Table 1») de tablas que se apaisan aunque quepan en 16 cm.
    `min_pt` (modo revista): suelo del cuerpo (8 pt); una tabla que no cabe ni así reparte el ancho a prorrata
    y sus tokens largos se parten, en vez de bajar hasta 6 pt."""
    from docx.oxml.ns import qn
    body = doc.element.body
    final_sect = body.find(qn("w:sectPr"))
    label_words = ("Table", "Tabla")
    note_words = ("Note.", "Nota.")
    cont_re = re.compile(rf"^{DB.WORDS['figure'][lang]}\s+\S+\s+\({DB.WORDS['continued'][lang]}\)\.")

    def es_continuacion(el) -> bool:
        """¿Es el párrafo la COLA de la leyenda de una lámina («Figura 4 (continuación). …»)?"""
        if el is None or el.tag != qn("w:p"):
            return False
        return bool(cont_re.match("".join(t.text or "" for t in el.iter(qn("w:t")))))

    rotated = []
    prev_land_p = None                 # párrafo con sectPr apaisado insertado tras la tabla anterior
    for tbl in list(doc.tables):
        ncols = len(tbl.columns)
        if ncols < 3:                      # paneles (1 columna) y ecuaciones (2 columnas)
            continue
        _keep_last_row_with_next(tbl)
        rows = tbl.rows
        cols = [c.text for c in rows[0].cells]
        textos = [[] for _ in range(ncols)]
        for row in list(rows)[1:]:
            for j, cell in enumerate(row.cells[:ncols]):
                textos[j].append(cell.text)
        pt = _table_font_pt(tbl)
        forzada = False
        if force_labels:
            p1 = tbl._tbl.getprevious()
            p2 = p1.getprevious() if p1 is not None else None
            if p2 is not None and p2.tag == qn("w:p"):
                forzada = "".join(t.text or "" for t in p2.iter(qn("w:t"))).strip() in force_labels
        if sum(_min_widths_cm(cols, textos, pt)) <= DB.TEXT_WIDTH_CM and not forzada:
            continue
        if sum(_min_widths_cm(cols, textos, pt)) <= LANDSCAPE_TEXT_WIDTH_CM:
            widths = DB._anchos(cols, textos, pt, total_cm=LANDSCAPE_TEXT_WIDTH_CM)
        else:
            # la tabla no cabe apaisada a su tamaño: fuente reducida (≥ 6 pt) y mínimos por columna acotados, para que
            # ninguna columna quede por debajo de su palabra más larga y solo los tokens muy largos (URL, archivos) se partan
            floor = min_pt
            if min_pt is not None and sum(_min_widths_cm(cols, textos, float(min_pt), CAP_MIN_COL_CM)) > \
                    JOURNAL_TABLE_PT_TOLERANCE * LANDSCAPE_TEXT_WIDTH_CM:
                floor = JOURNAL_TABLE_PT_EXCEPTION_FLOOR   # excepción documentada: no cabe a 8 pt ni partiendo palabras
            new_pt = _fit_font_pt(cols, textos, pt, LANDSCAPE_TEXT_WIDTH_CM, floor)
            if new_pt != pt:
                _set_table_font(tbl, new_pt)
                pt = new_pt
            widths = _anchos_capped(cols, textos, pt, LANDSCAPE_TEXT_WIDTH_CM, CAP_MIN_COL_CM)
        DB._no_autofit(tbl, LANDSCAPE_TEXT_WIDTH_CM)
        DB._aplicar_anchos(tbl, widths)
        el = tbl._tbl
        first = el
        prev = el.getprevious()
        prev2 = prev.getprevious() if prev is not None else None
        label = ""
        if prev is not None and prev2 is not None and prev.tag == qn("w:p") and prev2.tag == qn("w:p"):
            txt2 = "".join(t.text or "" for t in prev2.iter(qn("w:t")))
            if txt2.startswith(label_words):
                first, label = prev2, txt2
                solo_rotulo = prev2
                # un título de sección («Tablas suplementarias») justo antes del rótulo entra en la misma sección
                # apaisada; de lo contrario queda huérfano al pie de la página vertical anterior
                if _is_kept_heading(first.getprevious()):
                    first = first.getprevious()
                # Un título seguido de su párrafo de entrada quedaría huérfano al pie de la página vertical
                # anterior: ambos entran en la sección apaisada junto con la tabla.
                while True:
                    p_prev = first.getprevious()
                    if p_prev is None or p_prev.tag != qn("w:p"):
                        break
                    if _is_kept_heading(p_prev):
                        first = p_prev
                        continue
                    ppr_prev = p_prev.find(qn("w:pPr"))
                    if ppr_prev is not None and ppr_prev.find(qn("w:sectPr")) is not None:
                        break
                    p_prev2 = p_prev.getprevious()
                    if p_prev2 is not None and p_prev2.tag == qn("w:p") and _is_kept_heading(p_prev2):
                        first = p_prev2
                        continue
                    break
                # El título y su párrafo de entrada se absorben para que no queden huérfanos al pie de la
                # página vertical anterior. Cuando lo que hay justo antes es la COLA de la leyenda de una
                # lámina, absorberlo TODO deja esa página con la cola y nada más —cuatro líneas y 22 cm de
                # papel en blanco, que es el defecto V5 del artículo—; no absorber NADA deja el subtítulo
                # que anuncia la tabla como última línea de esa misma página, con 18 cm en blanco detrás y
                # la Tabla S1 abriendo ya en la sección apaisada. Se absorbe lo justo: el rótulo de la tabla
                # y los subtítulos contiguos que lo preceden. El título de sección y su párrafo de entrada
                # se quedan con la cola en la página vertical, que así ni queda vacía ni termina en un
                # encabezado suelto; y el subtítulo viaja con la tabla que anuncia. Si el subtítulo va
                # pegado a la cola —no hay párrafo de entrada que llene la página—, se queda donde está:
                # llevárselo dejaría la cola sola.
                if es_continuacion(first.getprevious()):
                    first = solo_rotulo
                    while True:
                        anterior = first.getprevious()
                        if not _is_section_heading(anterior) or es_continuacion(anterior.getprevious()):
                            break
                        first = anterior
        last = el
        nxt = el.getnext()
        if nxt is not None and nxt.tag == qn("w:p"):
            txt = "".join(t.text or "" for t in nxt.iter(qn("w:t")))
            if txt.startswith(note_words):
                last = nxt
        if prev_land_p is not None and first.getprevious() is prev_land_p:
            # tablas anchas consecutivas: se extiende la sección apaisada en vez de abrir una página vertical vacía
            prev_land_p.getparent().remove(prev_land_p)
        else:
            first.addprevious(_sect_paragraph(final_sect, landscape=False))
        prev_land_p = _sect_paragraph(final_sect, landscape=True)
        last.addnext(prev_land_p)
        rotated.append((label or f"{ncols} columns") + (f" ({pt:g} pt)" if pt < (min_pt or 7) else ""))
    return rotated


def drop_empty_sections(doc) -> int:
    """Quita el salto de sección que no encierra nada y dejaría una página en blanco.

    Una lámina a página completa abre su sección al construir el documento y una tabla ancha abre la suya
    en el posproceso; cuando una sigue inmediatamente a la otra quedan dos párrafos de sectPr contiguos y
    la sección entre ambos —vacía— se imprime como una página en blanco. Se elimina el SEGUNDO: el
    primero ya cerró la sección anterior con sus propias propiedades y el contenido que sigue pasa a la
    sección que termina en el siguiente sectPr, que es la que le corresponde."""
    from docx.oxml.ns import qn

    def lleva_sect(el):
        if el is None or el.tag != qn("w:p"):
            return False
        ppr = el.find(qn("w:pPr"))
        return ppr is not None and ppr.find(qn("w:sectPr")) is not None

    quitados = 0
    for el in list(doc.element.body):
        if lleva_sect(el) and lleva_sect(el.getprevious()):
            el.getparent().remove(el)
            quitados += 1
    return quitados


def postprocess_docx(path: Path, lang: str, landscape_labels: tuple = (), min_table_pt: float | None = None) -> dict:
    """Posproceso del DOCX construido. `landscape_labels` (modo revista) apaisa además esas tablas; `min_table_pt`
    (modo revista) es el suelo del cuerpo de las tablas apaisadas."""
    from docx import Document
    doc = Document(str(path))
    keep_panels_together(doc)
    rotated = landscape_wide_tables(doc, lang, force_labels=tuple(landscape_labels), min_pt=min_table_pt)
    vacias = drop_empty_sections(doc)
    # EL FOLIO VA AL FINAL, sobre las secciones definitivas: `landscape_wide_tables` abre secciones nuevas y
    # `drop_empty_sections` quita las que sobran, de modo que antes de estas dos líneas todavía no se sabe
    # cuáles son las secciones del documento impreso (ver `add_page_numbers`).
    numeradas = add_page_numbers(doc)
    doc.save(str(path))
    return dict(landscape_tables=rotated, empty_sections_removed=vacias, sections_numbered=numeradas)


# ---------------------------------------------------------------------------
# Construcción de documentos
# ---------------------------------------------------------------------------
def prune_embed_cache(keep: set[Path]) -> int:
    """Borra de la caché de incrustación las copias que este build ya no usa (anchos de lámina antiguos)."""
    if not EMBED_CACHE.is_dir():
        return 0
    n = 0
    for path in EMBED_CACHE.glob("*.png"):
        if path not in keep:
            path.unlink()
            n += 1
    return n


def mark_embed_dpi(blocks: list, start: int, dpi: int | None) -> list:
    """Marca con `embed_dpi` las láminas SUPLEMENTARIAS (las del bloque `start` en adelante).

    El PNG del disco no se toca: `docx_builder.embed_copy` guarda una copia remuestreada en la caché y es
    esa copia la que se incrusta. Las figuras del artículo (índices anteriores a `start`) no se marcan y
    entran con sus 600 ppp."""
    if not dpi:
        return list(blocks)
    out = []
    for i, (kind, payload) in enumerate(blocks):
        if kind == "figure" and i >= start:
            payload = dict(payload, embed_dpi=dpi)
        out.append((kind, payload))
    return out


def plate_summary(builder: dict) -> dict:
    """Resumen del ajuste de las láminas a página completa (cuántas a 180 mm, cuántas ajustadas, anchos).

    Lleva además el control de la TIPOGRAFÍA DE LA LEYENDA (fase 4e, tarea Y2): el suelo son 7,0 pt
    (`docx_builder.PLATE_CAP_MIN_PT`) y la única leyenda que puede bajar de ahí es la que, medio punto más
    grande, dejaría una página con la cola de la leyenda y nada más (`PLATE_CAP_STRAND_PT`, 6,5 pt). Por eso
    el resumen no da sólo el mínimo: da QUÉ láminas están por debajo del suelo —que hay que poder justificar
    una a una— y cuántas por debajo del escalón, que tienen que ser cero siempre."""
    plates = builder.get("full_page_plates") or []
    if not plates:
        return dict(n=0)
    anchos = sorted(pl["width_mm"] for pl in plates)
    leads = [pl["lead_pt"] for pl in plates if pl.get("lead_pt")]
    return dict(n=len(plates), natural=sum(1 for pl in plates if pl["mode"] == "natural"),
                caption_spill=sum(1 for pl in plates if pl["mode"] == "spill"),
                width_mm_min=anchos[0], width_mm_median=anchos[len(anchos) // 2], width_mm_max=anchos[-1],
                caption_pt_min=min(pl["caption_pt"] for pl in plates),
                caption_pt_max=max(pl["caption_pt"] for pl in plates),
                caption_pt_floor=DB.PLATE_CAP_MIN_PT, caption_pt_strand=DB.PLATE_CAP_STRAND_PT,
                captions_below_floor=[pl["label"] for pl in plates
                                      if pl["caption_pt"] < DB.PLATE_CAP_MIN_PT],
                captions_below_strand=[pl["label"] for pl in plates
                                       if pl["caption_pt"] < DB.PLATE_CAP_STRAND_PT],
                with_lead_in=sum(1 for pl in plates if pl["lead_in"]),
                lead_pt_min=min(leads) if leads else None, lead_pt_max=max(leads) if leads else None,
                plates_opening_own_page=sum(1 for pl in plates if pl.get("own_page")),
                caption_split=sum(1 for pl in plates if pl.get("caption_split")),
                # la regla de la fase 4j: toda leyenda que no cabe se parte y su cola va rotulada, de modo
                # que estas dos cifras tienen que ser IGUALES. Si `caption_spill` supera a `caption_split`
                # hay colas viajando dentro de un solo párrafo, que es como Word las parte sin rótulo.
                captions_unsplit_spill=[pl["label"] for pl in plates
                                        if pl["mode"] == "spill" and not pl.get("caption_split")],
                captions_structural_overflow=[pl["label"] for pl in plates
                                              if pl.get("structural_overflow")],
                with_heading=sum(1 for pl in plates if pl.get("headings_cm")),
                spill_cm_max=round(max(pl.get("spill_cm", 0.0) for pl in plates), 2))


# ---------------------------------------------------------------------------
# El embudo del glosario de impresión: todo lo que el lector lee pasa por aquí
# ---------------------------------------------------------------------------
# Un anglicismo suelto en prosa española («crosswalk») y un par de apellidos con guion donde el corpus
# escribe raya corta («Getis-Ord») habían sobrevivido a tres lecturas porque los escriben NUEVE módulos
# distintos —prosa, metodología extendida, leyendas, notas y celdas de tabla— y arreglarlo en uno dejaba
# a los demás atrás. La regla se declara UNA vez en `labels.PRINTED_TERMS` y se aplica aquí, que es el
# único sitio por el que pasan los tres documentos enteros antes de escribirse: párrafos, títulos,
# entradillas, leyendas, notas, encabezados de columna y las celdas de las 125 tablas. Los módulos
# siguen escribiendo lo que quieran; el lector recibe una sola forma.
#
# La sustitución NO toca los identificadores de máquina (`comuna_crosswalk.csv`,
# `censo2024_comunas_not_in_crosswalk`), que se cruzan carácter a carácter con `outputs/`: el patrón del
# glosario exige que la palabra no lleve pegado `_`, `.`, `/` ni `-`. Y respeta el idioma: el término
# inglés se conserva entero en los documentos en inglés.
def _glossed(value, lang: str):
    """El glosario de impresión aplicado a cualquier carga de bloque, sea del tipo que sea."""
    if isinstance(value, str):
        return LB.printed_text(value, lang)
    if isinstance(value, pd.DataFrame):
        # por POSICIÓN y no por nombre: hay tablas anchas con dos columnas que se llaman igual, y
        # `df[nombre]` devolvería allí un DataFrame en vez de una columna
        df = value.copy()
        df.columns = [LB.printed_text(c, lang) for c in df.columns]
        for j in range(df.shape[1]):
            if df.dtypes.iloc[j] == object:
                df.isetitem(j, [LB.printed_text(v, lang) for v in df.iloc[:, j]])
        return df
    if isinstance(value, dict):
        return {k: _glossed(v, lang) for k, v in value.items()}
    if isinstance(value, list):
        return [_glossed(v, lang) for v in value]
    if isinstance(value, tuple):
        return tuple(_glossed(v, lang) for v in value)
    return value


def _printed_leaks(value, lang: str, ruta: str = "") -> list[str]:
    """Lo que el glosario habría cambiado y sigue en el bloque: la guarda que detiene la construcción."""
    if isinstance(value, str):
        return [f"{ruta}: {m}" for m in LB.printed_leak(value, lang)]
    if isinstance(value, pd.DataFrame):
        fuera = [f"{ruta}[col]: {m}" for c in value.columns for m in LB.printed_leak(c, lang)]
        for j in range(value.shape[1]):
            if value.dtypes.iloc[j] == object:
                fuera += [f"{ruta}[{value.columns[j]}]: {m}"
                          for v in value.iloc[:, j] for m in LB.printed_leak(v, lang)]
        return fuera
    if isinstance(value, dict):
        return [m for k, v in value.items() for m in _printed_leaks(v, lang, f"{ruta}.{k}")]
    if isinstance(value, (list, tuple)):
        return [m for i, v in enumerate(value) for m in _printed_leaks(v, lang, f"{ruta}[{i}]")]
    return []


def printed_blocks(blocks: list, lang: str, nombre: str = "") -> list:
    """Los bloques del documento con el glosario de impresión aplicado, y comprobado sobre el resultado."""
    out = [(kind, _glossed(payload, lang)) for kind, payload in blocks]
    fuera = [m for i, (kind, payload) in enumerate(out) for m in _printed_leaks(payload, lang, f"{kind}#{i}")]
    if fuera:                      # nunca debe ocurrir: la sustitución es total y el tipo, cubierto
        raise RuntimeError(f"el glosario de impresión no llegó a {len(fuera)} sitio(s) de {nombre or lang}: "
                           f"{'; '.join(fuera[:5])}")
    return out


def build_pair(variant: str, lang: str, authors: list, affiliations: list, supp_dpi: int | None = SUPP_DPI_DEFAULT) -> dict:
    """Manuscrito (artículo + parte suplementaria en el mismo archivo) y apéndice separado, con el mismo registro.

    Los recuentos de la portada (palabras del núcleo, referencias, tablas y láminas del artículo) se calculan sobre
    los bloques del ARTÍCULO —`P.article()`—, no sobre el archivo completo, porque la parte suplementaria que sigue a
    las Referencias no cuenta para los límites de la revista.
    """
    P = PROSE[lang]
    V = P.load_values(variant)
    # el glosario de impresión (labels.PRINTED_TERMS) se aplica AQUÍ, antes de contar palabras y de
    # escribir nada, de modo que lo que se cuenta y lo que se imprime son el mismo texto
    art = printed_blocks(P.article(variant, V), lang, f"article_{variant}_{lang}")
    main = printed_blocks(P.manuscript(variant, V), lang, f"manuscript_{variant}_{lang}")
    supp = printed_blocks(P.supplement(variant, V), lang, f"supplement_{variant}_{lang}")
    smap = P.supplementary_map(variant, V)
    for key in REQUIRED_SUPP_TABLES:
        if key not in smap["tables"]:
            raise RuntimeError(f"la tabla suplementaria obligatoria {key} no está en el registro ({variant}/{lang})")
    wc = P.word_counts(art)
    refs_core, refs_all = len(P.citation_keys(art)), len(P.citation_keys(art, True))
    n_eq = sum(1 for k, _ in main if k == "eq")
    counts = dict(summary=fmt_number(wc["summary"], 0, lang), panel=fmt_number(wc["panel"], 0, lang),
                  core=fmt_number(wc["core_body"], 0, lang), n_opt=wc["opt_paragraphs"],
                  opt=fmt_number(wc["opt_body"], 0, lang), decl=fmt_number(wc["declarations"], 0, lang),
                  refs_core=refs_core, refs_all=refs_all, tables=wc["tables"], figures=wc["figures"],
                  sfig=len(smap["figures"]), stab=len(smap["tables"]), neq=n_eq)

    # el manuscrito combinado: artículo (láminas a 600 ppp) + parte suplementaria (láminas a supp_dpi)
    stripped, opt_index = strip_opt_with_index(main, lang)
    stripped = title_page(stripped, lang, variant, P, authors, affiliations, counts)
    stripped = mark_embed_dpi(stripped, len(art), supp_dpi)
    stripped += optional_index_blocks(opt_index, lang, wc["core_body"])
    main_path = MANU / f"manuscript_{variant}_{lang}.docx"
    with localised_references(lang):
        r_main = build_document(stripped, lang, main_path, bib_path=P.BIB, embed_cache=EMBED_CACHE)
    post_main = postprocess_docx(main_path, lang)

    # el apéndice separado: todas sus láminas son suplementarias
    supp_blocks = title_page(supp, lang, variant, P, authors, affiliations, counts, supplement=True)
    supp_blocks = mark_embed_dpi(supp_blocks, 0, supp_dpi)
    supp_path = MANU / f"supplement_{variant}_{lang}.docx"
    with localised_references(lang):
        r_supp = build_document(supp_blocks, lang, supp_path, bib_path=P.BIB, embed_cache=EMBED_CACHE)
    post_supp = postprocess_docx(supp_path, lang)

    # el artículo solo, que termina en las Referencias (sus 5 figuras se incrustan a 600 ppp)
    art_blocks, art_opt = strip_opt_with_index(art, lang)
    art_blocks = title_page(art_blocks, lang, variant, P, authors, affiliations, counts, article_only=True)
    art_path = MANU / f"article_{variant}_{lang}.docx"
    with localised_references(lang):
        r_art = build_document(art_blocks, lang, art_path, bib_path=P.BIB, embed_cache=EMBED_CACHE)
    post_art = postprocess_docx(art_path, lang)
    return dict(
        manuscript=dict(path=str(main_path), size_mb=round(main_path.stat().st_size / 1e6, 1), builder=r_main,
                        word_counts=wc, citation_keys_core=refs_core, citation_keys_all=refs_all,
                        equations=n_eq, supplementary_map=smap, main_map=P.main_map(variant, V),
                        optional_paragraphs=opt_index, postprocess=post_main, supp_dpi=supp_dpi,
                        plates=plate_summary(r_main)),
        supplement=dict(path=str(supp_path), size_mb=round(supp_path.stat().st_size / 1e6, 1), builder=r_supp,
                        equations=sum(1 for k, _ in supp if k == "eq"), supplementary_map=smap, postprocess=post_supp,
                        supp_dpi=supp_dpi, plates=plate_summary(r_supp)),
        article=dict(path=str(art_path), size_mb=round(art_path.stat().st_size / 1e6, 1), builder=r_art,
                     word_counts=wc, citation_keys_core=refs_core, citation_keys_all=refs_all,
                     equations=sum(1 for k, _ in art if k == "eq"), main_map=P.main_map(variant, V),
                     optional_paragraphs=art_opt, postprocess=post_art, supp_dpi=None, plates=plate_summary(r_art)),
    )


# ---------------------------------------------------------------------------
# PDF, miniaturas y hoja de contacto
# ---------------------------------------------------------------------------
def to_pdf(docx: Path, outdir: Path, profile: Path, timeout: int = 1200) -> Path:
    profile.mkdir(parents=True, exist_ok=True)
    pdf = outdir / (docx.stem + ".pdf")
    if pdf.exists():
        pdf.unlink()
    cmd = [SOFFICE, "--headless", "--norestore", f"-env:UserInstallation={profile.as_uri()}",
           "--convert-to", "pdf", "--outdir", str(outdir), str(docx)]
    res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    if res.returncode != 0 or not pdf.exists():
        raise RuntimeError(f"LibreOffice no convirtió {docx.name}: rc={res.returncode}\n{res.stdout}\n{res.stderr}")
    return pdf


def pdf_pages(pdf: Path) -> int | None:
    if not PDFINFO:
        return None
    res = subprocess.run([PDFINFO, str(pdf)], capture_output=True, text=True, timeout=120)
    m = re.search(r"^Pages:\s+(\d+)", res.stdout, flags=re.M)
    return int(m.group(1)) if m else None


NEAR_EMPTY_CHARS = 300           # una página con menos texto que esto no lleva más que una frase suelta.
                                 # QUÉ SE CUENTA (fase 4j): los caracteres del texto que `pdftotext` extrae de
                                 # la página, con las PALABRAS UNIDAS POR UN ESPACIO y las LÍNEAS POR UN SALTO
                                 # —es decir, los separadores cuentan—, descontado el folio. Ésa es la cuenta
                                 # que informa el estudio y la única a la que se refiere el umbral. La otra
                                 # cuenta razonable —sólo los caracteres NO BLANCOS— da menos y se informa
                                 # aparte (`chars_nonws`, `min_chars_nonws`): las portadas de los apéndices
                                 # sueltos, que son un bloque de título completo y no una página floja, quedan
                                 # entre 272 y 302 y tres de ellas por debajo de 300. Decir «ninguna página
                                 # baja de 300 caracteres» sin decir cuál de las dos cuentas es no es una
                                 # afirmación comprobable, así que el informe dice las dos y nombra la suya.
SPARSE_GAP_CM = 15.0             # y una que deja más de esto en blanco AL PIE está medio vacía aunque lleve
                                 # dos mil caracteres: once líneas a 7 pt caben en 3 cm de papel. Contar sólo
                                 # caracteres no veía las páginas de cola de leyenda, que son el defecto.
XHTML = "{http://www.w3.org/1999/xhtml}"


def _pdf_page_boxes(pdf: Path) -> list[dict]:
    """Cada página del PDF con su alto, su texto y la caja que ese texto ocupa, SIN el folio.

    Mide con `pdftotext -bbox-layout`, que da la caja de cada línea. El número de página vive solo en el
    pie, dentro del último centímetro: se descarta comparando su caja con el alto de la página, porque si
    no toda página parecería ocupada hasta el borde inferior."""
    if not PDFTOTEXT or not pdf.is_file():
        return []
    import xml.etree.ElementTree as ET
    res = subprocess.run([PDFTOTEXT, "-bbox-layout", str(pdf), "-"], capture_output=True, text=True, timeout=900)
    try:
        root = ET.fromstring(res.stdout)
    except ET.ParseError:
        return []
    paginas = []
    for pg in root.iter(XHTML + "page"):
        alto = float(pg.get("height"))
        folio = alto - 2.0 * 28.3465          # el pie: los dos últimos centímetros de papel
        lineas = []
        for ln in pg.iter(XHTML + "line"):
            txt = " ".join((w.text or "") for w in ln.iter(XHTML + "word")).strip()
            if not txt:
                continue
            y0, y1 = float(ln.get("yMin")), float(ln.get("yMax"))
            if y0 > folio and re.fullmatch(r"\d{1,4}", txt):
                continue                       # número de página
            lineas.append((y0, y1, txt))
        texto = "\n".join(t for _, _, t in lineas)
        cm = 2.54 / 72.0
        paginas.append(dict(
            # `chars` = palabras unidas por un espacio y líneas por un salto (la cuenta que informa el
            # estudio); `chars_nonws` = sólo los caracteres no blancos de ese mismo texto. Las dos, porque
            # el umbral de 300 significa cosas distintas según cuál se use y las portadas caen en medio.
            height_cm=round(alto * cm, 2), lines=len(lineas), chars=len(texto),
            chars_nonws=len(re.sub(r"\s", "", texto)),
            top_cm=round(min((l[0] for l in lineas), default=alto) * cm, 2),
            end_cm=round(max((l[1] for l in lineas), default=0.0) * cm, 2),
            gap_cm=round((alto - max((l[1] for l in lineas), default=alto)) * cm, 2),
            text=texto, first=lineas[0][2][:90] if lineas else "", last=lineas[-1][2][:90] if lineas else ""))
    return paginas


COLA_RE = re.compile(r"^[a-z(\u00e1\u00e9\u00ed\u00f3\u00fa\u00f1\u00fc\u2019']")


def _chars_nonws(pagina: dict) -> int:
    """Caracteres NO BLANCOS de la página. `_pdf_page_boxes` ya los trae; una página construida a mano —las
    de las pruebas— sólo trae su texto, y la cuenta se hace aquí para que la medida no dependa de quién
    construyó el diccionario."""
    if "chars_nonws" in pagina:
        return pagina["chars_nonws"]
    return len(re.sub(r"\s", "", pagina.get("text", "")))


def _region_stats(paginas: list[dict], a: int, b: int, last_page: int) -> dict:
    """Recuento de páginas flojas de una región [a, b] (índices 0-based, ambos incluidos).

    Tres medidas INDEPENDIENTES, porque una sola no ve el defecto y su CONJUNCIÓN no ve ninguno:

      * `near_empty` cuenta CARACTERES y sólo caracteres —la página que no lleva más que una frase suelta—.
        Una página de LÁMINA con su leyenda entera pasa de los dos mil caracteres; una que se queda en 231
        es una lámina impresa con el rótulo «Figura S54.» y ni una línea de leyenda debajo, que es una figura
        sin pie. Esta medida estuvo un tiempo condicionada a que la página dejara además papel en blanco al
        pie, y así no podía ver ese caso NUNCA: los 245 mm de imagen no dejan hueco al pie, de modo que una
        lámina sin leyenda contaba como página llena. Las dos cosas se cuentan por separado;
      * `sparse` cuenta ALTURA OCUPADA: la página que deja más de SPARSE_GAP_CM en blanco al pie. Ve las
        páginas con dos mil caracteres de leyenda en 3 cm de papel, pero también la última página de una
        sección, que termina donde termina su texto y no es un defecto (un documento con veinte tablas
        apaisadas tiene veinte de ésas);
      * `tail` son las flojas que además ABREN A MEDIA FRASE —la primera línea empieza en minúscula—:
        la cola de una leyenda o de una nota sola en su página. Ése es el defecto que los verificadores
        leyeron y el que hay que llevar a cero.

    La última página del documento no cuenta: termina donde termina el texto."""
    idx = [i for i in range(a, b + 1) if i != last_page]
    if not idx:
        return {}
    gaps = sorted(paginas[i]["gap_cm"] for i in idx)
    casi = [i + 1 for i in idx if 0 < paginas[i]["chars"] < NEAR_EMPTY_CHARS]
    # la MISMA medida con la otra cuenta de caracteres, para que el umbral no dependa de una definición
    # tácita: `near_empty` usa `chars` (palabras unidas por un espacio) y ésta los no blancos
    casi_nw = [i + 1 for i in idx if 0 < _chars_nonws(paginas[i]) < NEAR_EMPTY_CHARS]
    flojas = [i for i in idx if paginas[i]["chars"] and paginas[i]["gap_cm"] >= SPARSE_GAP_CM]
    colas = [i for i in flojas if COLA_RE.match(paginas[i]["first"])]
    con_texto = [i for i in idx if paginas[i]["chars"]]
    return dict(first_page=a + 1, last_page=b + 1, pages=b - a + 1,
                near_empty_pages=len(casi), near_empty_at=casi,
                near_empty_nonws_pages=len(casi_nw), near_empty_nonws_at=casi_nw,
                min_chars=min((paginas[i]["chars"] for i in con_texto), default=0),
                min_chars_nonws=min((_chars_nonws(paginas[i]) for i in con_texto), default=0),
                sparse_pages=len(flojas), tail_pages=len(colas), max_gap_cm=gaps[-1],
                median_gap_cm=gaps[len(gaps) // 2],
                sparse_at=[dict(page=i + 1, lines=paginas[i]["lines"], chars=paginas[i]["chars"],
                                gap_cm=paginas[i]["gap_cm"], tail=i in colas, first=paginas[i]["first"])
                           for i in flojas[:30]])


def lead_in_audit(paginas: list[dict], lang: str, plates: list) -> dict:
    """¿Está impresa la frase de presentación de cada lámina en la PÁGINA de su lámina? Leído del PDF.

    La guardia anterior interrogaba al modelo (`lead_index`, `lead_keep`), que es una estimación: decía
    4 láminas con la entradilla en la página anterior donde el PDF impreso tenía 6, y 5 donde tenía 12.
    Aquí se localiza la página de cada lámina por el comienzo de SU leyenda y se busca en esa misma
    página el comienzo de su entradilla."""
    def norm(t: str) -> str:
        return re.sub(r"\s+", " ", t.replace("*", "").replace("\u2019", "'")).lower()

    fuera, sin_marca = [], []
    for pl in plates:
        cabeza = norm(pl.get("lead_head") or "")
        if not cabeza:
            continue
        marca = re.compile(r"^\s*" + re.escape(pl["label"]) + r"\.", flags=re.M)
        pagina = next((i for i, p in enumerate(paginas) if marca.search(p["text"])), None)
        if pagina is None:
            sin_marca.append(pl["label"])
            continue
        if cabeza not in norm(paginas[pagina]["text"]):
            fuera.append(dict(label=pl["label"], page=pagina + 1))
    return dict(plates=len([p for p in plates if p.get("lead_head")]),
                lead_off_plate_page=len(fuera), lead_off_at=fuera, caption_not_found=sin_marca)


def caption_audit(paginas: list[dict], plates: list) -> dict:
    """¿Se imprime bajo cada lámina, en SU página, el COMIENZO de su leyenda y no sólo el rótulo?

    El defecto que esta guardia mide se leyó impreso: una lámina cuyo pie era la palabra «Figura S54.» y
    nada más, con la leyenda entera en la página siguiente. Nace de que el reparto de líneas de la leyenda
    admitía cero líneas bajo la imagen (`docx_builder.PLATE_CAP_MIN_LINES` lo prohíbe ahora), y ninguna
    medida de página lo veía: la página lleva 245 mm de imagen, de modo que no deja papel en blanco al pie
    y sólo el recuento de caracteres —231, el único por debajo de 300 en los doce documentos— la delataba.
    Aquí se comprueba lo que le importa a quien lee: que la leyenda empiece bajo su lámina."""
    def norm(t: str) -> str:
        return re.sub(r"\s+", " ", t.replace("*", "").replace("\u2019", "'")).lower()

    sin_leyenda, sin_marca = [], []
    for pl in plates:
        cabeza = norm(pl.get("caption_head") or "")
        if not cabeza:
            continue
        # el rótulo de la cola («Figura S54 (continuación).») NO casa con esta marca, que exige el punto
        marca = re.compile(r"^\s*" + re.escape(pl["label"]) + r"\.", flags=re.M)
        con_marca = [i for i, p in enumerate(paginas) if marca.search(p["text"])]
        if not con_marca:
            sin_marca.append(pl["label"])
            continue
        # basta con que UNA de las páginas que abren con el rótulo lleve además el comienzo de la leyenda:
        # así una frase del cuerpo que empiece de línea con «Figura 3.» no cuenta como falso positivo
        if not any(cabeza in norm(paginas[i]["text"]) for i in con_marca):
            sin_leyenda.append(dict(label=pl["label"], page=con_marca[0] + 1))
    return dict(plates=len([p for p in plates if p.get("caption_head")]),
                caption_off_plate_page=len(sin_leyenda), caption_off_at=sin_leyenda,
                caption_not_found=sin_marca)


def caption_spill_audit(paginas: list[dict], plates: list, lang: str) -> dict:
    """¿Termina cada leyenda en la página de SU lámina y, si no termina, abre la siguiente ya rotulada?

    Es la guardia de la tarea J1, y se lee del PDF impreso porque ahí es donde se ve el defecto. Hasta la
    fase 4j el constructor rotulaba la cola de la leyenda sólo cuando detrás de la lámina se cerraba la
    sección; en los demás casos la leyenda viajaba al documento como UN párrafo y era Word quien la partía,
    sin poder poner rótulo alguno. Resultado medido sobre los doce PDF del 2026-09-08: **100 colas sin
    rótulo** en los ocho documentos largos —doce por documento en inglés y trece en español—, hasta el 88 %
    de una leyenda impresa en una página que no era la de su lámina, de modo que doce o trece páginas por
    documento abrían con un bloque de letra pequeña sin dueño visible.

    Ninguna de las otras medidas de página lo veía y por eso el defecto pasó tres verificaciones: esas
    páginas no están vacías (llevan la lámina siguiente), no dejan papel en blanco al pie (245 mm de imagen
    no dejan hueco) y `tail_pages` sólo mira las que están medio vacías. Aquí se compara, lámina a lámina,
    lo que el constructor dice que imprimió (`caption_end`, las últimas palabras de la leyenda completa) con
    lo que la página lleva impreso.
    """
    def norm(t: str) -> str:
        return re.sub(r"\s+", " ", str(t).replace("*", "").replace("\u2019", "'")).lower()

    def flat(t: str) -> str:
        """Flujo de caracteres SIN blancos: inmune al punto donde Word corta el renglón. Word parte
        «quasi-Poisson» por su guion al final de una línea y `pdftotext` devuelve dos palabras donde el
        documento tiene una; comparando por palabras eso se lee como un desbordamiento que no existe."""
        return re.sub(r"\s+", "", norm(t))

    cont = DB.WORDS["continued"][lang]
    sin_marca, sin_rotulo, rotuladas = [], [], []
    medidas = [pl for pl in plates if pl.get("caption_end")]
    for pl in medidas:
        marca = re.compile(r"^\s*" + re.escape(pl["label"]) + r"\.", flags=re.M)
        cabeza = norm(pl.get("caption_head") or "")
        con_marca = [i for i, p in enumerate(paginas) if marca.search(p["text"])]
        # la página de la lámina es la que abre de línea con el rótulo Y lleva el comienzo de la leyenda:
        # así una frase del cuerpo que empiece por «Figura 3.» no se confunde con el pie de la lámina
        pagina = next((i for i in con_marca if not cabeza or cabeza in norm(paginas[i]["text"])), None)
        if pagina is None:
            sin_marca.append(pl["label"])
            continue
        # se busca el final de la leyenda DESPUÉS de su rótulo y no en toda la página: las leyendas de las
        # láminas espaciales terminan todas con el mismo aviso de lugar de atención y la misma regla de
        # supresión, y la página de una lámina lleva encima la cola de la leyenda ANTERIOR, que acaba con
        # esas mismas palabras. Buscando en la página entera, la cola ajena hacía pasar por «terminada» una
        # leyenda que seguía en la página siguiente: dieciséis de veintidós desbordamientos invisibles.
        m = marca.search(paginas[pagina]["text"])
        if flat(pl["caption_end"]) in flat(paginas[pagina]["text"][m.end():]):
            continue                                     # la leyenda termina en la página de su lámina
        rotulo = flat(f"{pl['label']} ({cont}).")
        siguiente = flat(paginas[pagina + 1]["text"]) if pagina + 1 < len(paginas) else ""
        destino = rotuladas if siguiente.startswith(rotulo) else sin_rotulo
        destino.append(dict(label=pl["label"], page=pagina + 1))
    return dict(plates=len(medidas), spilled=len(rotuladas) + len(sin_rotulo), marked=len(rotuladas),
                unmarked_spills=len(sin_rotulo), unmarked_at=sin_rotulo[:30], caption_not_found=sin_marca)


def page_layout_audit(pdf: Path, lang: str, plates: list | None = None) -> dict:
    """Auditoría de composición de TODO el PDF, región a región, en caracteres y en altura ocupada.

    Regiones: `before_plates` (portada, artículo, metodología extendida), `plates` (de la primera a la
    última página que abre una leyenda «Figura/Figure S…») y `after_plates` (las tablas suplementarias).
    La medida anterior sólo miraba la región de láminas y sólo contaba caracteres, de modo que no veía ni
    las colas de leyenda del ARTÍCULO ni las colas de nota de las tablas."""
    paginas = _pdf_page_boxes(pdf)
    if not paginas:
        return {}
    marca = re.compile(rf"^\s*{DB.WORDS['figure'][lang]}\s+S\d+\.", flags=re.M)
    con_leyenda = [i for i, p in enumerate(paginas) if marca.search(p["text"])]
    ultima = len(paginas) - 1
    regiones = {}
    if con_leyenda:
        a, b = con_leyenda[0], con_leyenda[-1]
        if a:
            regiones["before_plates"] = _region_stats(paginas, 0, a - 1, ultima)
        regiones["plates"] = _region_stats(paginas, a, b, ultima)
        if b < ultima:
            regiones["after_plates"] = _region_stats(paginas, b + 1, ultima, ultima)
    else:
        regiones["document"] = _region_stats(paginas, 0, ultima, ultima)
    out = dict(pages=len(paginas), regions=regiones,
               sparse_pages=sum(r.get("sparse_pages", 0) for r in regiones.values()),
               tail_pages=sum(r.get("tail_pages", 0) for r in regiones.values()),
               near_empty_pages=sum(r.get("near_empty_pages", 0) for r in regiones.values()))
    out["min_chars"] = min((p["chars"] for p in paginas if p["chars"]), default=0)
    out["min_chars_nonws"] = min((_chars_nonws(p) for p in paginas if p["chars"]), default=0)
    out["near_empty_nonws_pages"] = sum(r.get("near_empty_nonws_pages", 0) for r in regiones.values())
    if plates:
        out["lead_in"] = lead_in_audit(paginas, lang, plates)
        out["captions"] = caption_audit(paginas, plates)
        out["caption_spill"] = caption_spill_audit(paginas, plates, lang)
    return out


def thumbnails(pdf: Path, outdir: Path, dpi: int = THUMB_DPI) -> list[Path]:
    outdir.mkdir(parents=True, exist_ok=True)
    for old in outdir.glob("page-*.png"):
        old.unlink()
    subprocess.run([PDFTOPPM, "-r", str(dpi), "-png", str(pdf), str(outdir / "page")], check=True, timeout=1200)
    return sorted(outdir.glob("page-*.png"))


def contact_sheet(pages: list[Path], out_png: Path, cols: int | None = None, thumb_w: int | None = None,
                  label_h: int = 16, margin: int = 6) -> Path:
    """Hoja de contacto de todas las páginas. Con documentos largos (la parte suplementaria añade cientos de páginas)
    se usan más columnas y miniaturas más pequeñas para que el PNG resultante siga siendo abrible."""
    from PIL import Image, ImageDraw, ImageFont
    if not pages:
        raise ValueError("sin páginas para la hoja de contacto")
    if cols is None:
        cols = 8 if len(pages) <= 200 else (12 if len(pages) <= 500 else 16)
    if thumb_w is None:
        thumb_w = 190 if len(pages) <= 200 else (130 if len(pages) <= 500 else 100)
    thumbs = []
    for p in pages:
        with Image.open(p) as im:
            im = im.convert("RGB")
            h = round(im.height * thumb_w / im.width)
            thumbs.append(im.resize((thumb_w, h)))
    thumb_h = max(t.height for t in thumbs)
    rows = -(-len(thumbs) // cols)
    sheet = Image.new("RGB", (margin + cols * (thumb_w + margin), margin + rows * (thumb_h + label_h + margin)), "#d9d9d9")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=12)
    except TypeError:  # Pillow < 10.1
        font = ImageFont.load_default()
    for i, t in enumerate(thumbs):
        x = margin + (i % cols) * (thumb_w + margin)
        y = margin + (i // cols) * (thumb_h + label_h + margin)
        sheet.paste(t, (x, y))
        draw.rectangle([x - 1, y - 1, x + thumb_w, y + t.height], outline="#7f7f7f")
        draw.text((x + 2, y + t.height + 2), f"p. {i + 1}", fill="#000000", font=font)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png, optimize=True)
    return out_png


def render_review(docx: Path, do_pdf: bool, do_thumbs: bool, profile: Path, lang: str = "en",
                  plates: list | None = None) -> dict:
    info = {}
    if not do_pdf:
        return info
    t0 = time.time()
    pdf = to_pdf(docx, MANU, profile)
    info.update(pdf=str(pdf), pdf_size_mb=round(pdf.stat().st_size / 1e6, 1), pages=pdf_pages(pdf),
                pdf_seconds=round(time.time() - t0))
    audit = page_layout_audit(pdf, lang, plates)
    if audit:
        info["layout"] = audit
    if do_thumbs:
        rdir = REVIEW / docx.stem
        pages = thumbnails(pdf, rdir)
        sheet = contact_sheet(pages, REVIEW / f"{docx.stem}_contact_sheet.png")
        info.update(thumbnails=str(rdir), n_thumbnails=len(pages), contact_sheet=str(sheet))
        if info.get("pages") is None:
            info["pages"] = len(pages)
    return info


# ---------------------------------------------------------------------------
# Memo ejecutivo (español)
# ---------------------------------------------------------------------------
class _K:
    def __init__(self, V: dict, variant: str):
        self.V, self.variant = V, variant

    def __call__(self, key):
        if key not in self.V:
            raise KeyError(f"values_{self.variant}.json no tiene la clave '{key}' citada por memo_es")
        return self.V[key]


def _n(x, dec=0):
    return fmt_number(x, dec, "es")


def _ci(lo, hi, dec=1):
    return fmt_ci(lo, hi, dec, "es")


def _series(k, tmpl, years, dec=0):
    return " / ".join(_n(k(tmpl.format(y=y)), dec) for y in years)


def differing_controls(scope: str = "pipeline") -> pd.DataFrame:
    """Filas 'differs' de UN ámbito del consolidado. El archivo trae dos ámbitos con nombre que cuentan cosas
    distintas (`pipeline`, un control por fila de cada <módulo>_controls.csv; `analysis_plan`, un control
    indicador-año del plan), de modo que sumarlos duplicaría las mismas diferencias."""
    df = pd.read_csv(CONTROLS_SUMMARY, dtype=str, keep_default_na=False)
    if "scope" in df.columns:
        df = df[df["scope"] == scope]
    return df[df["status"] == "differs"][["module", "name", "key", "expected", "observed"]]


# ---------------------------------------------------------------------------
# El estado del material NO se escribe a mano: se calcula de dos artefactos
# ---------------------------------------------------------------------------
# `memo_es.md` es el archivo al que la portada de los doce documentos remite al autor («Not for
# submission without the confirmations listed in memo_es.md»), y hasta la fase 4k llevaba escritas a
# mano cuatro afirmaciones de una ronda anterior: un total de páginas del corpus, «el material NO está
# terminado», «la lectura independiente no pasa» y la ficha de un defecto que la compilación ya había
# cerrado. Ninguna de las tres partes que lo producen podía verlas envejecer.
#
# Desde aquí, TODO estado y TODO recuento del memo sale de dos artefactos:
#   * `manuscript/build_report.json` — lo que la compilación mide de sí misma (páginas, colas de
#     leyenda, regiones, cuerpos, tamaños). Lo escribe esta misma corrida.
#   * `review_status.json` — el registro de las lecturas independientes y de los puntos abiertos:
#     qué comprobó cada lectura y con qué veredicto, qué puntos siguen abiertos, cuáles bloquean el
#     envío y cuáles están ya cerrados en la fuente, con la hora en que se cerraron.
#
# Y el registro lleva la COMPILACIÓN sobre la que se leyó. Si no es la que el memo describe, el memo lo
# dice en su primera frase de estado y fecha cada medida, en vez de presentarla como si fuera de ésta:
# ahí es donde nace toda afirmación rancia. Un punto cerrado en la fuente después de la compilación se
# imprime como cerrado EN LA FUENTE y todavía no en el papel, y pasa solo a «cerrado y en el papel» en
# cuanto una compilación posterior a su hora de cierre lo recoge, sin que nadie reescriba una línea.
STATUS_PATH = LA / "review_status.json"
HISTORY_PATH = MANU / "build_history.json"


def load_review_status(report: dict, path: Path | None = None) -> dict:
    """El registro de lecturas y puntos abiertos, con la guarda de compilación resuelta.

    Devuelve siempre un diccionario utilizable: `fresh` dice si las lecturas se hicieron sobre la
    compilación que el memo describe, y `readings` / `points` vienen vacíos si no hay registro, de modo
    que el memo diga «no hay lectura registrada» en vez de repetir la de otra compilación.
    """
    path = STATUS_PATH if path is None else path
    try:
        st = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(present=False, fresh=False, build=None, readings=[], points=[], previous={})
    st.setdefault("readings", [])
    st.setdefault("points", [])
    st.setdefault("previous", {})
    st["present"] = True
    for r in st["readings"]:
        checks = r.get("checks") or []
        r["n_checks"] = len(checks)
        r["n_pass"] = sum(1 for c in checks if c.get("verdict") == "pass")
        r["passes"] = bool(checks) and r["n_pass"] == r["n_checks"]
        # Cada lectura declara SU compilación; el `build` de la cabecera es sólo el valor por defecto.
        # Dos lecturas pueden haberse hecho sobre compilaciones distintas —lo normal cuando una ronda
        # arregla lo que la anterior encontró—, y entonces cada medida se fecha por separado.
        r["build"] = r.get("build") or st.get("build")
        r["fresh"] = bool(r["build"]) and r["build"] == report.get("date")
    st["fresh"] = bool(st["readings"]) and all(r["fresh"] for r in st["readings"])
    for p in st["points"]:
        fixed_at = p.get("fixed_at")
        p["open"] = p.get("state") != "fixed"
        # cerrado en la fuente ANTES de esta compilación = cerrado también en el papel
        p["on_page"] = (not p["open"]) and bool(fixed_at) and str(report.get("date") or "") >= str(fixed_at)
    return st


def record_build_history(report: dict, totals: dict, path: Path | None = None) -> list:
    """Anota los totales de ESTA compilación y devuelve el historial, para que el memo pueda decir el
    antes y el después sin que nadie escriba de memoria el total de la compilación anterior.

    Una segunda escritura del memo sobre el mismo informe reemplaza su propia anotación en vez de
    duplicarla: el historial tiene una entrada por compilación, no por corrida del memo.
    """
    path = HISTORY_PATH if path is None else path
    try:
        hist = json.loads(path.read_text(encoding="utf-8"))
        hist = hist if isinstance(hist, list) else []
    except (OSError, ValueError):
        hist = []
    row = dict(date=report.get("date"), **totals)
    hist = [h for h in hist if h.get("date") != row["date"]] + [row]
    hist.sort(key=lambda h: str(h.get("date") or ""))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(hist, indent=1, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass
    return hist


def write_memo(report: dict, path: Path = MEMO_PATH) -> Path:
    Vc = prose_en.load_values("con_rett")
    Vs = prose_en.load_values("sin_rett")
    k, ks = _K(Vc, "con_rett"), _K(Vs, "sin_rett")
    yg, ya, yr, ya27 = prose_en.YEARS_GRD, prose_en.YEARS_A05, prose_en.YEARS_REM, prose_en.YEARS_A27
    diff = differing_controls()
    today = dt.date.today().isoformat()
    ref_doc = report["documents"].get("con_rett_en") or next(iter(report["documents"].values()))
    smap = ref_doc["supplement"]["supplementary_map"]
    n_sfig, n_stab, n_eq = len(smap["figures"]), len(smap["tables"]), ref_doc["supplement"]["equations"]
    lab_t8 = smap["tables"]["T8_controls"].replace("Table", "Tabla")
    lab_dict = smap["tables"]["ST2_rem_code_dictionary"].replace("Table", "Tabla")
    lab_prov = smap["tables"]["ST7_provenance"].replace("Table", "Tabla")

    def doc_row(name, d):
        r = d.get("review", {})
        pages = r.get("pages", "—")
        wc = d.get("word_counts")
        words = (f"resumen {wc['summary']}, núcleo {_n(wc['core_body'])} (+{_n(wc['opt_body'])} opcionales en "
                 f"{wc['opt_paragraphs']} párrafos)") if wc else f"{d['builder']['tables']} tablas, {d['builder']['figures']} láminas"
        return (f"| `{Path(d['path']).name}` | {d['size_mb']} MB | {pages} | {d['builder']['tables']} | "
                f"{d['builder']['figures']} | {d['builder']['references']} | {words} |")

    rows = []
    for key, pair in report["documents"].items():
        rows.append(doc_row(key, pair["manuscript"]))
        rows.append(doc_row(key, pair["supplement"]))
        rows.append(doc_row(key, pair["article"]))

    def rng(part, field, unit, dec=1):
        """Rango observado de un campo (páginas, MB) entre los cuatro documentos de una parte."""
        vals = []
        for pair in report["documents"].values():
            d = pair[part]
            v = d[field] if field in d else d.get("review", {}).get(field)
            if v is not None:
                vals.append(v)
        lo, hi = min(vals), max(vals)
        s = lambda x: _n(x, dec)
        return f"{s(lo)} {unit}" if lo == hi else f"{s(lo)}–{s(hi)} {unit}"

    pg = {part: rng(part, "pages", "páginas", 0) for part in ("manuscript", "supplement", "article")}
    mb = {part: rng(part, "size_mb", "MB") for part in ("manuscript", "supplement", "article")}
    pdf = {part: rng(part, "pdf_size_mb", "MB") for part in ("manuscript", "supplement", "article")}
    n_plates = ref_doc["manuscript"]["builder"]["figures"]

    # --- hechos de la región de láminas y de la tipografía de la leyenda, leídos del auditor del PDF ---
    def _plate_regions(part):
        return {key: (pair[part]["review"]["layout"]["regions"].get("plates") or {})
                for key, pair in report["documents"].items()}

    def _by_lang(regs, field):
        return {lang: sorted({r[field] for k, r in regs.items() if k.endswith(lang) and field in r})
                for lang in ("en", "es")}

    def _lst(vals, dec=0):
        return "–".join(_n(v, dec) for v in vals) if len(vals) > 1 else _n(vals[0], dec)

    def _span(vals, dec=0):
        """Extremos observados, para una serie de más de dos valores («13 a 16», no «13–14–15–16»)."""
        lo, hi = min(vals), max(vals)
        return _n(lo, dec) if lo == hi else f"{_n(lo, dec)} a {_n(hi, dec)}"

    reg_supp = _plate_regions("supplement")
    reg_pages, reg_sparse = _by_lang(reg_supp, "pages"), _by_lang(reg_supp, "sparse_pages")
    reg_sparse_chars = sorted({s["chars"] for r in reg_supp.values() for s in r.get("sparse_at", [])})
    reg_near_empty = sum(r.get("near_empty_pages", 0) for r in reg_supp.values()) + \
        sum((pair["manuscript"]["review"]["layout"]["regions"].get("plates") or {}).get("near_empty_pages", 0)
            for pair in report["documents"].values())
    long_parts = [pair[p] for pair in report["documents"].values() for p in ("manuscript", "supplement")]
    # --- colas de leyenda rotuladas y páginas más cortas, leídas del PDF impreso (fase 4j, tarea J1) ---
    all_parts = [pair[p] for pair in report["documents"].values()
                 for p in ("manuscript", "supplement", "article")]

    def _layout(d, *claves, default=0):
        v = d.get("review", {}).get("layout") or {}
        for c in claves:
            v = (v or {}).get(c) if isinstance(v, dict) else None
        return default if v is None else v

    spill_marked = sum(_layout(d, "caption_spill", "marked") for d in all_parts)
    spill_unmarked = sum(_layout(d, "caption_spill", "unmarked_spills") for d in all_parts)
    # páginas del corpus, sumadas de la corrida y NO escritas a mano (la cifra se cita en tres sitios)
    total_pages = sum(d["review"]["pages"] for d in all_parts)
    spill_long = sorted({_layout(d, "caption_spill", "spilled") for d in long_parts})
    min_join = sorted({_layout(d, "min_chars") for d in all_parts if _layout(d, "min_chars")})
    min_nonws = sorted({_layout(d, "min_chars_nonws") for d in all_parts if _layout(d, "min_chars_nonws")})
    n_below_join = sum(_layout(d, "near_empty_pages") for d in all_parts)
    n_below_nonws = sum(_layout(d, "near_empty_nonws_pages") for d in all_parts)
    cap_floor = _n(ref_doc["supplement"]["plates"]["caption_pt_floor"], 1)
    cap_strand = _n(ref_doc["supplement"]["plates"]["caption_pt_strand"], 1)
    cap_min_long = _n(min(d["plates"]["caption_pt_min"] for d in long_parts), 1)
    cap_min_art = _n(min(pair["article"]["plates"]["caption_pt_min"] for pair in report["documents"].values()), 1)
    art_tail = sorted({pair["article"]["review"]["layout"]["tail_pages"] for pair in report["documents"].values()})
    after_sparse = sorted({(d["review"]["layout"]["regions"].get("after_plates") or {}).get("sparse_pages", 0)
                           for d in long_parts})
    strand_labels = {lang: sorted({p["label"] for k, pair in report["documents"].items() if k.endswith(lang)
                                   for p in pair["supplement"]["builder"]["full_page_plates"]
                                   if p["caption_pt"] < ref_doc["supplement"]["plates"]["caption_pt_floor"]},
                                  key=lambda s: int(s.split("S")[-1]))
                     for lang in ("en", "es")}
    def _strand_only():
        """Rótulos que gastan el escalón en UNA sola variante: se nombran, en vez de darlos por comunes."""
        per = {k: {p["label"] for p in pair["supplement"]["builder"]["full_page_plates"]
                   if p["caption_pt"] < ref_doc["supplement"]["plates"]["caption_pt_floor"]}
               for k, pair in report["documents"].items()}
        partes = []
        for lang in ("en", "es"):
            keys = [k for k in per if k.endswith(lang)]
            comunes = set.intersection(*(per[k] for k in keys)) if keys else set()
            for k in keys:
                for lab in sorted(per[k] - comunes, key=lambda s: int(s.split("S")[-1])):
                    partes.append(f"la {lab.split()[-1]} sólo en `{k[:-3]}`")
        return f" ({'; '.join(partes)})" if partes else ""

    strand_only = _strand_only()
    fig1 = [next(p for p in pair["article"]["builder"]["full_page_plates"] if p["label"].split()[-1] == "1")
            for pair in report["documents"].values()]
    fig1_lines = sorted({p["caption_lines_total"] for p in fig1})
    fig1_split = sum(1 for p in fig1 if p["caption_split"] or p["spill_cm"])

    # --- páginas que llevan SÓLO la cola rotulada de una leyenda, leídas del auditor del PDF ---
    # Es el precio en papel de la regla de la tarea J1, y se cuenta aquí en vez de escribirse: una
    # página de la región de láminas cuyo primer texto es «Figura N (continuación).» no lleva más que
    # esa cola, su número de figura y su folio.
    _CONT_RE = re.compile(r"^(Figure|Figura)\s+S?\d+\s*\((continued|continuación)\)")

    def _tail_only(d) -> list:
        regiones = ((d.get("review") or {}).get("layout") or {}).get("regions") or {}
        return [s for r in regiones.values() if r for s in (r.get("sparse_at") or [])
                if _CONT_RE.match(str(s.get("first") or ""))]

    tail_only = {f"{part}_{key}": _tail_only(pair[part])
                 for key, pair in report["documents"].items()
                 for part in ("manuscript", "supplement", "article")}
    n_tail_only = sum(len(v) for v in tail_only.values())
    tail_by_lang = {lang: sorted({len(v) for name, v in tail_only.items()
                                  if name.endswith(lang) and not name.startswith("article")})
                    for lang in ("en", "es")}
    tail_chars = sorted({s["chars"] for v in tail_only.values() for s in v})
    tail_gaps = sorted({s["gap_cm"] for v in tail_only.values() for s in v if s.get("gap_cm")})

    def _tail_pages_of(name: str) -> str:
        return ", ".join(f"{s['page']}" for s in tail_only.get(name, []))

    # --- el registro de las lecturas independientes y de los puntos abiertos (guarda de compilación) ---
    st = load_review_status(report)
    lect = {r["key"]: r for r in st["readings"]}
    abiertos = [p for p in st["points"] if p["open"]]
    cerrados = [p for p in st["points"] if not p["open"]]
    bloquean = [p for p in abiertos if p.get("blocks_submission")]
    defectos = [p for p in abiertos if p.get("reads_as_defect")]
    class _Num(dict):
        """El número que cada punto lleva en la tabla, calculado al imprimir. Un punto que ya no está
        abierto no tiene número, y la frase que lo citaba escribe «—» en vez de romper el memo."""

        def __missing__(self, clave):
            return "—"

    N = _Num({p["key"]: i + 1 for i, p in enumerate(abiertos)})
    ml = lect.get("layout", {}).get("measurements", {})            # medidas de la lectura de página y tipografía
    mc = lect.get("content", {}).get("measurements", {})           # medidas de la lectura de contenido
    prev = st.get("previous") or {}
    hist = record_build_history(report, dict(total_pages=total_pages, marked_caption_tails=spill_marked,
                                             unmarked_caption_tails=spill_unmarked,
                                             tail_only_pages=n_tail_only, documents=len(all_parts)))
    anterior = next((h for h in reversed(hist) if str(h.get("date") or "") < str(report.get("date") or "")), None)
    if anterior and anterior.get("total_pages"):
        # el ANTES sale del historial de compilaciones, no de la memoria de nadie: si no hay entrada
        # anterior anotada, el memo no dice de dónde viene el corpus, en vez de inventarlo
        _d = total_pages - int(anterior["total_pages"])
        delta_anterior = (f" —la compilación anterior anotada, la del "
                          f"{str(anterior['date']).replace('T', ' a las ')}, tenía "
                          f"{_n(anterior['total_pages'])} páginas: {'+' if _d >= 0 else '−'}{_n(abs(_d))}—")
    else:
        delta_anterior = (" —no hay compilación anterior anotada en `manuscript/build_history.json`, de modo que "
                          "este memo no dice de cuántas páginas viene el corpus; la siguiente compilación sí "
                          "podrá decirlo—")

    def _fecha(x) -> str:
        return str(x or "").replace("T", " a las ")

    def _sello(clave: str | None = None) -> str:
        """De qué compilación es una medida, dicho siempre que no sea de ésta.

        Con `clave` se sella la medida de UNA lectura; sin ella, la frase que mezcla varias. Si las
        lecturas registradas son de compilaciones distintas, el sello las nombra una a una en vez de
        atribuirlas todas a la misma, que es como una medida vieja se cuela como si fuera de hoy.
        """
        rs = [r for r in st["readings"] if clave is None or r.get("key") == clave]
        if not st["present"] or not rs:
            return " (sin lectura independiente registrada)"
        if all(r["fresh"] for r in rs):
            return ""
        if len({r.get("build") for r in rs}) == 1:
            b = _fecha(rs[0].get("build"))
            return f" (medido sobre la compilación del {b}, no sobre ésta)" if b else " (sin compilación anotada)"
        trozos = ", ".join(f"la de {r['es']} sobre "
                           + ("ésta" if r["fresh"] else f"la del {_fecha(r.get('build'))}") for r in rs)
        return f" (cada medida sobre la compilación de su lectura: {trozos})"

    def _registro_frase() -> str:
        """Si las lecturas registradas son de esta compilación, de otra, o unas de cada una."""
        if not st["present"] or not st["readings"]:
            return ("No hay lectura independiente registrada, de modo que este memo no da por buena ninguna.")
        frescas = [r for r in st["readings"] if r["fresh"]]
        if len(frescas) == len(st["readings"]):
            return "Las lecturas registradas son las de esta misma compilación."
        if not frescas:
            return "El registro no es de esta compilación, y por eso cada medida suya va fechada más abajo."
        return (f"{_n(len(frescas))} de las {_n(len(st['readings']))} lecturas registradas se hicieron sobre esta "
                f"misma compilación y {'la otra' if len(st['readings']) - len(frescas) == 1 else 'las otras'} no, "
                f"y por eso cada medida va fechada donde se cita.")

    def _frescura_frase() -> str:
        """Qué es posterior a la compilación, medido y no afirmado de memoria.

        Dos hechos distintos, y el memo no los confunde: (1) si algo de las cuatro carpetas
        `outputs/<variante>/<idioma>/` —lo que los documentos leen— es posterior a la compilación, hay
        un arreglo que vive sólo en `outputs/` y no está en el papel; (2) si un archivo de código del
        paquete se editó después, lo que ese cambio produzca tampoco está en estos doce archivos.
        """
        marca = str(report.get("date") or "")

        def _posteriores(paths) -> list[str]:
            fuera = []
            for q in paths:
                try:
                    if dt.datetime.fromtimestamp(q.stat().st_mtime).isoformat(timespec="seconds") > marca:
                        fuera.append(q.name)
                except OSError:
                    continue
            return sorted(set(fuera))

        salidas = _posteriores(q for v in VARIANTS for l in LANGS
                               for q in (CFG.OUT / v / l).rglob("*") if q.is_file())
        fuentes = _posteriores(list(LA.glob("*.py")) + list((LA / "pipeline").glob("*.py")))
        if salidas:
            a = (f"**{_n(len(salidas))} archivos de las cuatro carpetas `outputs/<variante>/<idioma>/` son "
                 f"posteriores a ella**, de modo que hay trabajo hecho que todavía no está en el papel")
        else:
            a = ("ningún archivo de las cuatro carpetas `outputs/<variante>/<idioma>/` que los documentos leen es "
                 "posterior a ella, de modo que en el papel está todo lo que antes estaba sólo en `outputs/`")
        if fuentes:
            b = (f"; sí lo {'es' if len(fuentes) == 1 else 'son'} {_n(len(fuentes))} archivo"
                 f"{'' if len(fuentes) == 1 else 's'} de código —{', '.join(f'`{f}`' for f in fuentes)}—, editado"
                 f"{'' if len(fuentes) == 1 else 's'} después de compilar: lo que cambien no está en estos doce "
                 f"archivos hasta la próxima reconstrucción")
        else:
            b = "; ninguna fuente del paquete se editó después de compilar"
        return a + b

    def _no_cierra_frase() -> str:
        """Lo que esta compilación deja abierto, leído del registro y nunca de la ronda anterior."""
        _plu = lambda n, uno, varios: uno if n == 1 else varios
        if not st["present"]:
            return ("falta `review_status.json`, de modo que este memo NO afirma que no quede nada abierto.")
        if not abiertos:
            return "el registro no deja ningún punto abierto."
        _lista = lambda ps: "; ".join(p.get("es", p["key"]) for p in ps)
        if bloquean:
            return (f"**{_n(len(bloquean))} {_plu(len(bloquean), 'punto bloquea', 'puntos bloquean')} el envío** "
                    f"—{_lista(bloquean)}—, y quedan {_n(len(abiertos))} puntos abiertos en total.")
        if defectos:
            return (f"quedan {_n(len(abiertos))} puntos abiertos, de los que {_n(len(defectos))} se "
                    f"{_plu(len(defectos), 'lee', 'leen')} como defecto —{_lista(defectos)}— y ninguno bloquea "
                    f"el envío.")
        return f"quedan {_n(len(abiertos))} puntos abiertos y ninguno se lee como defecto."

    def _m(clave, dic=None, dec=0):
        """Una medida del registro de lecturas, o «—» si no está: nunca una cifra escrita a mano."""
        v = (ml if dic is None else dic).get(clave)
        return "—" if v is None else (_n(v, dec) if isinstance(v, (int, float)) else str(v))

    lines = []
    A = lines.append
    A("# Memo ejecutivo — Reconocimiento administrativo del autismo en Chile, 2019–2025")
    A("")
    A(f"**Fecha:** {today}. **Módulo:** `study/pipeline/10_manuscript.py`. Todas las cifras y todos los "
      f"estados de este memo se calculan en la corrida que lo escribe, y ninguno se escribe a mano: las cifras del "
      f"estudio salen de `outputs/values_con_rett.json` (variante principal de trabajo), "
      f"`outputs/values_sin_rett.json`, `outputs/controls/controls_summary.csv` y de los recuentos de "
      f"`prose_en.word_counts` / `prose_es.word_counts`; las de la página impresa, de "
      f"`manuscript/build_report.json`, que esta misma corrida mide sobre los doce PDF; y el estado del material "
      f"—qué comprueba cada lectura independiente, con qué veredicto, qué queda abierto y qué bloquea el envío—, "
      f"de `review_status.json`, que lleva anotada la COMPILACIÓN sobre la que se leyó. "
      f"{_registro_frase()} "
      f"Lo único que se escribe como texto son los datos de diagnóstico de cada punto abierto —la página "
      f"donde se ve, la línea de código que lo produce, lo que costaría cerrarlo—, que viven en la ficha de "
      f"su punto y desaparecen con ella cuando el registro lo da por cerrado.")
    A("")
    A("## 1. Qué se construyó")
    A("")
    A("La carpeta `study/` contiene el pipeline reproducible (pasos 00–17), el plan de análisis, la procedencia con "
      "SHA-256, las tablas tidy, los controles de reproducción, las láminas y tablas por variante e idioma, y los "
      "manuscritos. El paso 10 genera, para cada variante (`con_rett` = familia F84 completa; `sin_rett` = F84 sin "
      "síndrome de Rett) y cada idioma (`en` para la revista; `es` de trabajo), el archivo del manuscrito —artículo más "
      "material suplementario en el mismo documento, que sigue siendo el entregable principal—, el apéndice suplementario "
      "separado y el archivo `article_<variante>_<idioma>.docx` sólo con el artículo hasta las Referencias, en Word, su "
      "conversión a PDF con "
      "LibreOffice, miniaturas de revisión a 45 ppp con hoja de contacto (`manuscript/review/`) y este memo. El paso 17 "
      "verifica el registro de numeración compartido y escribe `extended_material_index.md`.")
    A("")
    A("| Documento | Tamaño | Páginas PDF | Tablas | Láminas | Referencias | Palabras |")
    A("|---|---|---|---|---|---|---|")
    lines.extend(rows)
    A("")
    A(f"**Qué compilación es ésta.** Los doce archivos de la tabla son la compilación del "
      f"{report['date'].replace('T', ' a las ')} ({_n(report.get('seconds') or 0)} s), con "
      f"**{_n(total_pages)} páginas** en total, y es la ÚLTIMA: se construyó después de reejecutar, con el "
      f"verificador de composición armado, todos los módulos que producen lámina o tabla, y `07_controls.py` al "
      f"final. Medido sobre la marca de tiempo de cada archivo, {_frescura_frase()}. En el papel están ya, "
      f"medidos antes y después con el mismo instrumento sobre el documento impreso, **los tres defectos de "
      f"composición que la lectura independiente había declarado bloqueantes** y que cerró la fase 4j. "
      f"**(1) La cola de leyenda sin rótulo** (tarea J1): la leyenda que no cabe bajo "
      f"su lámina se parte ahora EN EL CÓDIGO y su cola se imprime rotulada «Figura N (continuación).» al "
      f"principio de la página siguiente —regla única, sin umbral y sin excepción—; "
      f"**{_m('colas_sin_rotulo', prev)} colas sin rótulo → {spill_unmarked}**, y las {spill_marked} colas que "
      f"esta compilación imprime llevan todas su rótulo. **(2) Dos trazos para el mismo intervalo** (tarea J2): "
      f"la regla de la raya se escribe UNA vez en `common.py` y se engancha a los dos embudos por los que pasa "
      f"todo lo que el lector lee —la escritura de tablas y el rotulado de láminas—, de modo que ningún módulo "
      f"declara ya su propia expresión del intervalo; en las láminas, **{_m('rangos_con_guion_en_lamina')} rangos "
      f"con guion en {_m('rotulos_de_lamina_medidos')} rótulos** de las {_m('construcciones_comprobadas')} "
      f"construcciones{_sello('layout')}. **(3) Dos errores de hecho y una glosa contradictoria** (tarea J3): la ventana "
      f"de años con guion que llegaba al lector en las Tablas S68 y S85 "
      f"(**{_m('rangos_de_ano_con_guion_en_celda_de_lectura', prev)} → 0** celdas de presentación); el encabezado "
      f"del Gi* de Getis–Ord, que prometía «(Ecuaciones 28, 29)» e imprimía sólo la 29 porque la 28 ya se había "
      f"impreso bajo `lisa` (**{_m('encabezados_de_ecuacion_desajustados', prev)} → "
      f"{_m('desajustes_encabezado_ecuacion', mc)}** desajustes por idioma, con los "
      f"{_m('encabezados_de_ecuacion', mc)} estimadores auditados y una guarda que detiene la construcción si "
      f"vuelve); y la glosa del panel fijo de 65, fijada desde los datos como «hospitales presentes en TODOS LOS "
      f"AÑOS 2019–2024» —los 65 tienen `n_years_present = 6` y la intersección de 2019–2022 y la de 2019–2024 son "
      f"el mismo conjunto—. **Lo que esto cuesta en papel**, contado en esta compilación y no de memoria: "
      f"**{n_tail_only} páginas** de las {_n(total_pages)} llevan sólo la cola rotulada de una leyenda "
      f"({_lst(tail_by_lang['en'])} por documento largo en inglés y {_lst(tail_by_lang['es'])} en español; "
      f"{_span(tail_chars)} caracteres cada una)"
      f"{delta_anterior}. "
      f"**Lo que esta compilación NO cierra** está en la sección 6, y sale del registro, no de la memoria: "
      f"{_no_cierra_frase()}")
    A("")
    n_mfig, n_mtab = len(prose_en.MAIN_FIGURES), len(prose_en.MAIN_TABLES)
    lab_sources = smap["tables"]["T1_sources"].replace("Table", "Tabla")
    lab_flow = smap["tables"]["T_dataflow_counts"].replace("Table", "Tabla")
    A(f"Estructura del archivo del manuscrito. **Artículo:** portada (autores y afiliación de `paper/prose.py`, título corto, "
      f"recuentos), Summary de cinco párrafos, panel «Research in context» sin referencias, Introduction, Methods, Results "
      f"(Tablas 1–{n_mtab} y Figuras 1–{n_mfig} tras su primera mención), Discussion, Conclusion, Contributors, Declaration of "
      f"interests, Data sharing statement, Funding, Acknowledgements, declaración de IA y References. La Figura 1 es la lámina "
      f"del módulo 08d, redibujada en la fase 4d a petición del autor como **esquema conceptual de qué se hizo con cada base "
      f"de datos**: seis carriles, uno por familia de fuentes, cada uno leído de izquierda a derecha —base de datos → pasos → "
      f"lo que entrega— con tres formas y ninguna más (cilindro = base de datos, caja redondeada = paso, bloque con punta = lo "
      f"que el carril entrega). La unidad de análisis va como UNA palabra en un distintivo sobre cada cilindro (cuadrado "
      f"«registro», círculo «persona», hexágono «comuna»); las cifras van solas sobre las flechas (n a la entrada, n tras la "
      f"selección de autismo y los extremos de la serie que el carril produce, 41 en total, leídas del registro en tiempo de "
      f"ejecución); las exclusiones que importan van en rojo con su signo menos; los quiebres de definición se marcan sobre la "
      f"flecha donde caen; y la regla de no enlace se enuncia UNA sola vez, como barrera en el centro de la lámina. No lleva "
      f"título impreso, ni frases completas, ni nombres de archivo, de script o de columna, ni un bloque de instrucciones: "
      f"118 palabras en español y 119 en inglés, sobre un presupuesto de 120 que el módulo cuenta en cada corrida. El "
      f"inventario de fuentes pasó al material suplementario como {lab_sources}. **Material "
      f"suplementario, en el mismo archivo, tras las Referencias y con salto de página:** nota e índice, métodos suplementarios "
      f"S1–S5, la metodología extendida (módulo 12) con las {n_eq} ecuaciones numeradas de `equations.py` citadas en el "
      f"encabezado del estimador que las aplica, las láminas S1–S{n_sfig} agrupadas por tema (láminas centrales; episodios "
      f"hospitalarios; ruta REM; denominadores, encuestas y educación; razón por sexo entre fuentes; diagnósticos de los modelos; "
      f"análisis espacial y correlación territorial) y las tablas S1–S{n_stab} (empezando por {lab_sources}, el inventario de "
      f"fuentes, y {lab_flow}, los recuentos de la Figura 1; la tabla completa de controles T8 = {lab_t8}, el diccionario REM "
      f"verificado = {lab_dict} y la procedencia = {lab_prov}), más las referencias suplementarias. Al final, la página «Optional "
      f"material index» con los párrafos marcados `[OPT]` (candidatos a recorte). Los apéndices separados "
      f"`supplement_<variante>_<idioma>.docx` contienen exactamente el mismo material suplementario, construido desde el mismo "
      f"registro: «{smap['tables']['T8_controls']}» designa el mismo ítem en ambos documentos.")
    A("")
    A(f"Norma de lámina (fase 4c, petición del autor). Las {n_plates} láminas del estudio ({n_mfig} del artículo y {n_sfig} "
      f"suplementarias) se dibujan a **180 × 245 mm en vertical, a escala 1:1 y 600 ppp** (4.251 × 5.787 píxeles), en una rejilla "
      f"de **3 filas × 2 columnas** con un máximo de seis paneles, cuerpo base 8 pt, título de panel 9 pt en negrita, marcas de "
      f"eje 7 pt y nada por debajo de 6 pt en ningún rótulo ni anotación. Las **letras de panel son minúsculas (a)–(f)** en la "
      f"lámina y en la leyenda, en los dos idiomas, como pide la revista. Cada lámina ocupa **una página propia** del documento, "
      f"en una sección vertical con márgenes de 7 mm arriba, 10 mm abajo y 8,5 mm a los lados, de modo que se imprime a tamaño "
      f"natural y no encogida. Ninguna lámina hubo que dividirla, añadirla ni renombrarla: la numeración suplementaria "
      f"(S1–S{n_sfig} y S1–S{n_stab}) no cambió con el rediseño.")
    A("")
    A(f"Legibilidad dentro del panel (fase 4d). La norma fijaba el lienzo; lo que fallaba era la ejecución dentro de los "
      f"paneles. Se añadió a `common.py` un **verificador de composición** (`check_layout` / `assert_layout_clean`) que mide la "
      f"lámina terminada sobre su renderizador real y denuncia nueve familias de defecto —texto sobre texto, texto fuera del "
      f"lienzo, título de eje sobre sus propias marcas, leyenda o nota sobre los datos, rótulo de valor sobre su marcador o su "
      f"barra de error, rótulo de valor cuyo recuadro tapa su propia barra, títulos de dos paneles vecinos sin hueco entre "
      f"ellos, marcas numéricas repetidas y recuento de paneles—, cada una con el panel, los artistas y el solape en puntos. "
      f"Las dos últimas nacieron de defectos que un lector humano vio y la máquina no: la barra mayor de la S37 (e) borrada por "
      f"el recuadro de su propio rótulo, y los títulos de la S45 (a) y (b) separados por 1,4 pt. Corre dentro de los "
      f"nueve módulos de lámina sin tocarlos, por los dos embudos que todos atraviesan (`plate_resolve` y `save_fig`), con "
      f"`PLATE_CHECK=off|report|strict`; el décimo módulo que dibuja láminas (`06_models.py`) se comprobó con el mismo "
      f"verificador desde fuera. Los defectos se arreglaron **en el módulo que dibuja**, nunca retocando la imagen: de 720 "
      f"defectos en la línea base de los tres módulos del artículo a **0 en los diez**, en las dos variantes y los dos "
      f"idiomas. En el mismo paso se rediseñó el **panel (a) de la Figura 2**, que era un mapa de calor con "
      f"dos recuadros opacos y una barra de color de 60–100 %: hoy cada celda de la rejilla es una barra apilada al 100 % de "
      f"los tres estados excluyentes de una celda REM (valor informado / cero explícito / no informado), con el % informado en "
      f"su propia banda encima, de modo que la escala abarca los datos por construcción y los tres estados se leen de un "
      f"vistazo.")
    A("")
    A(f"Paginación de la región de láminas (fase 4d). La frase que presenta cada lámina suplementaria no cabía nunca en la caja "
      f"—3,20 cm libres bajo una lámina de 24,50 cm, con la entradilla a 12 pt e interlineado 1,5— de modo que la regla «la "
      f"entradilla viaja con su lámina sólo si cabe» la dejaba caer en las {n_sfig} láminas de cada documento, y cada una se "
      f"imprimía después en una página propia con dos líneas de texto. Corregidos el factor de "
      f"línea y el margen de seguridad contra el PDF impreso, y ampliada la caja a 19,6 × 28,35 cm, la entradilla viaja SIEMPRE "
      f"con su lámina, al mayor cuerpo que quepa (12 → 9 → 8 → 7,5 pt) y nunca menor que su propia leyenda. La región de "
      f"láminas suplementarias pasó de 116–117 páginas con 43–44 casi vacías a **{_lst(reg_pages['en'])} páginas seguidas en "
      f"inglés y {_lst(reg_pages['es'])} en español, cada lámina en su página con su entradilla y su leyenda**, "
      f"{reg_near_empty} de ellas casi vacías. Las {_lst(reg_sparse['en'])} páginas de más en inglés y "
      f"{_lst(reg_sparse['es'])} en español son las que llevan la cola rotulada de una leyenda que ya no cabía con la "
      f"lámina siguiente (tarea J1, más abajo): {_span(reg_sparse_chars)} caracteres, abriendo con «Figura N "
      f"(continuación).» y su número de figura. "
      f"**Qué se cuenta cuando se dice «caracteres».** La cuenta del estudio es la del texto que `pdftotext` extrae de la "
      f"página **con las palabras unidas por un espacio y las líneas por un salto** —los separadores cuentan—, descontado "
      f"el folio; con ella la página más corta de los doce documentos lleva **{_n(min(min_join))} caracteres** "
      f"(la más corta de cada documento va de {_span(min_join)}) y **{n_below_join} páginas bajan de 300**. Contando "
      f"sólo los caracteres **no blancos** del mismo texto el mínimo del corpus es **{_n(min(min_nonws))}** "
      f"y bajan de 300 **{n_below_nonws} páginas**, todas ellas portadas de apéndice suelto: un bloque "
      f"de título completo, no una página floja. Las dos cuentas se escriben en cada corrida "
      f"(`review.layout.min_chars` y `min_chars_nonws`), de modo que la afirmación dice de cuál habla y se puede "
      f"comprobar. El módulo 10 audita el PDF construido en cada corrida y escribe el recuento en "
      f"`manuscript/build_report.json` (`review.layout`), de modo que el defecto se vería solo si volviera.")
    A("")
    A(f"Colas de leyenda rotuladas (fase 4j, tarea J1). Una leyenda de lámina que no cabe bajo su lámina continúa en la "
      f"página siguiente. Hasta esta fase el constructor sólo rotulaba esa cola cuando detrás de la lámina se cerraba la "
      f"sección; en los demás casos la leyenda viajaba al documento como UN párrafo y era Word quien la partía, sin poder "
      f"poner rótulo. En la compilación anterior{_sello('layout')}: **{_m('colas_sin_rotulo', prev)} colas sin rótulo** en "
      f"{prev.get('colas_sin_rotulo_documentos', 'los documentos largos')}, con hasta el 88 % de una "
      f"leyenda impresa en una página que no era la de su lámina, de modo que el lector se encontraba un párrafo de letra "
      f"pequeña sin dueño visible. Ninguna de las medidas de página lo veía: esas páginas no están vacías ni dejan papel "
      f"al pie, porque detrás de la cola va la lámina siguiente. **La regla es ahora una y sin excepción: la leyenda que "
      f"no cabe se parte en el código y su cola se imprime rotulada «Figura N (continuación).» al principio de la página "
      f"siguiente.** No se acortó ninguna leyenda —las de las láminas espaciales llevan el aviso de lugar de atención y "
      f"los recuentos por clase, que son norma del estudio— ni se encogió ninguna lámina, que sigue a 180 mm. En esta "
      f"compilación {_span(spill_long)} leyendas por documento largo continúan en la página siguiente, "
      f"**{spill_marked} colas rotuladas y {spill_unmarked} sin rotular** en los doce documentos, leídas del PDF impreso "
      f"por `review.layout.caption_spill`. Lo que cuesta, contado en el propio PDF de esta corrida: "
      f"**{n_tail_only} páginas** llevan sólo la cola rotulada de una leyenda "
      f"({_lst(tail_by_lang['en'])} por documento largo en inglés, {_lst(tail_by_lang['es'])} en español y "
      f"ninguna en los cuatro archivos sólo-artículo), cada una con {_span(tail_chars)} caracteres de leyenda "
      f"rotulada con su número de figura —no un párrafo huérfano— y {_span(tail_gaps, 1)} cm de blanco detrás. "
      f"Ninguna queda casi vacía: el mínimo de la región de láminas es "
      f"{_n(min(r['min_chars'] for r in reg_supp.values() if r.get('min_chars')))} caracteres.")
    A("")
    A(f"Tipografía de la leyenda de lámina (fase 4e). La leyenda se imprimía hasta a 6,0 pt con tal de que cupiera bajo su "
      f"lámina, un cuerpo que no se lee cómodamente en papel. El suelo pasó a **{cap_floor} pt** "
      f"(`docx_builder.PLATE_CAP_MIN_PT`) con un único escalón de {cap_strand} pt, reservado a la leyenda cuya cola se "
      f"quedaría sola en la página siguiente. Medido en el XML de los documentos construidos, y no tomado del informe de "
      f"construcción: ninguna leyenda baja de {cap_min_art} pt en los cuatro archivos sólo-artículo ni de {cap_min_long} pt "
      f"en los ocho largos, donde el escalón se gasta sólo en {', '.join(strand_labels['en'])} en inglés y "
      f"{', '.join(strand_labels['es'])} en español{strand_only}; ninguna se imprime a 6,0 pt. El coste es "
      f"que más leyendas llevan su cola al cuerpo del texto: la de la "
      f"**Figura 1 no**, que cabe entera bajo su lámina en los ocho sitios donde se imprime "
      f"({_lst(fig1_lines)} líneas, {fig1_split} con cola), tras acortarla en `pipeline/08d_figure_dataflow.py`.")
    A("")
    A("## 2. Resultados principales (variante `con_rett`; todas las cifras son reconocimiento administrativo, no prevalencia ni incidencia)")
    A("")
    A(f"- **GRD (núcleo hospitalario, 2019–2024).** Episodios con F84 documentado en cualquier posición: "
      f"{_series(k, 'grd_f84_any_n_{y}', yg)}; de {_n(k('grd_f84_any_rate_2019'), 1)} a {_n(k('grd_f84_any_rate_2024'), 1)} por "
      f"100.000 episodios GRD. CPA cuasi-Poisson {_n(k('apc_grd_any_obs'), 1)} % (IC 95 % {_ci(k('apc_grd_any_obs_lo'), k('apc_grd_any_obs_hi'))}); "
      f"entre {_n(k('apc_grd_any_sensitivity_min'), 1)} % y {_n(k('apc_grd_any_sensitivity_max'), 1)} % en las "
      f"{_n(k('apc_grd_any_sensitivity_n_specs'))} especificaciones de sensibilidad (panel fijo de {_n(k('grd_fixed_panel_n'))} hospitales, "
      f"actividad, posición, profundidad, ventana). F84 principal: {_series(k, 'grd_f84_principal_n_{y}', yg)}. En 2024 el "
      f"{_n(k('grd_f84_secondary_only_share_2024_pct'), 1)} % de los episodios F84 lo tenían solo como diagnóstico secundario y la "
      f"profundidad de codificación media de todos los episodios subió de {_n(k('grd_coding_depth_all_mean_2019'), 2)} a "
      f"{_n(k('grd_coding_depth_all_mean_2024'), 2)} diagnósticos. Panel observado 65/65/65/65/68/72 hospitales; panel fijo de 65: "
      f"{_n(k('grd_f84_any_fixed65_n_2023'))} (2023) y {_n(k('grd_f84_any_fixed65_n_2024'))} (2024).")
    A(f"- **REM (ruta administrativa agregada, sin enlace por persona).** Ingresos A05 por autismo estricto (05990022) 2021–2025: "
      f"{_series(k, 'a05_autism_entries_{y}', ya)} (CPA {_n(k('apc_a05_autism_count'), 1)} %, IC 95 % "
      f"{_ci(k('apc_a05_autism_count_lo'), k('apc_a05_autism_count_hi'))}). A27 referencia asistida M-CHAT-R/F 2023–2025: "
      f"{_series(k, 'a27_assisted_referral_{y}', ya27)} intervenciones. A28 ingresos TEA a rehabilitación 2023–2025: "
      f"{_series(k, 'a28_primary_{y}', ya27)} (APS) y {_series(k, 'a28_hospital_{y}', ya27)} (hospitalaria). P2 NANEAS con TEA "
      f"bajo control en diciembre 2019–2025 (stock): {_series(k, 'p2_tea_dec_{y}', yr)}, con {_n(k('p2_tea_dec_estab_2019'))} → "
      f"{_n(k('p2_tea_dec_estab_2025'))} establecimientos reportantes (CPA {_n(k('apc_p2_dec'), 1)} %, IC 95 % "
      f"{_ci(k('apc_p2_dec_lo'), k('apc_p2_dec_hi'))}). Las eras de definición (A03 2019–22 / 2023–24 / 2024 31–59 m / 2025; "
      f"TGD amplio 2019–20) se presentan en facetas separadas y nunca se unen.")
    A(f"- **Educación.** PIE armonizado TEA + TEA-Asperger 2019–2023 y SINACES 2024–2025: {_series(k, 'pie_harmonised_{y}', yr)} "
      f"(CPA {_n(k('apc_pie_harmonised'), 1)} %, IC 95 % {_ci(k('apc_pie_harmonised_lo'), k('apc_pie_harmonised_hi'))}). Regla 2022: se "
      f"adopta {_n(k('pie_2022_apuntes60_sum'))} (suma Apuntes 60 = total SINACES menos escuelas especiales) frente al "
      f"{_n(k('pie_2022_sinaces_printed'))} impreso (discrepancia de {_n(k('pie_2022_discrepancy_cases'))} casos). JUNAEB EVE 2025 "
      f"ponderado (EXP): prekínder/kínder {_n(k('junaeb_parvularia_all_pct_weighted_2025'), 2)} %, 1.º básico "
      f"{_n(k('junaeb_basico1_all_pct_weighted_2025'), 2)} %, 5.º básico {_n(k('junaeb_basico5_all_pct_weighted_2025'), 2)} %, "
      f"1.º medio {_n(k('junaeb_medio1_all_pct_weighted_2025'), 2)} %; 1.º medio 2024 «no estimable» (variable vacía), 2023 sin ponderador.")
    A(f"- **Encuestas (diseño complejo, Taylor).** ENDIDE 2022: autismo reportado en {_n(k('svy_endide_children_reported_total_pct'), 2)} % "
      f"(IC 95 % {_ci(k('svy_endide_children_reported_total_lo_pct'), k('svy_endide_children_reported_total_hi_pct'), 2)}) de los NNA de 2–17 años "
      f"y {_n(k('svy_endide_adults_reported_total_pct'), 2)} % (IC 95 % {_ci(k('svy_endide_adults_reported_total_lo_pct'), k('svy_endide_adults_reported_total_hi_pct'), 2)}) "
      f"de los adultos; confirmación profesional entre los NNA con autismo reportado {_n(k('svy_endide_children_confirmed_among_reported_total_pct'), 1)} %. "
      f"ENCAVI 2023–24: diagnóstico declarado en {_n(k('svy_encavi_15plus_diagnosed_total_pct'), 2)} % (IC 95 % "
      f"{_ci(k('svy_encavi_15plus_diagnosed_total_lo_pct'), k('svy_encavi_15plus_diagnosed_total_hi_pct'), 2)}) de las personas de 15 años o más. "
      f"Son referencias de autismo reportado, no validación de códigos ni prevalencia.")
    A(f"- **Variante `sin_rett`.** Excluir F84.2 cambia los episodios GRD con F84 en {_n(k('grd_f84_any_n_rett_only_difference_2019'))} (2019) y "
      f"{_n(k('grd_f84_any_n_rett_only_difference_2024'))} (2024): {_n(ks('grd_f84_any_n_2024'))} episodios en 2024 "
      f"({_n(ks('grd_f84_any_rate_2024'), 1)} por 100.000) y CPA {_n(ks('apc_grd_any_obs'), 1)} % (IC 95 % "
      f"{_ci(ks('apc_grd_any_obs_lo'), ks('apc_grd_any_obs_hi'))}); autismo estricto REM, F84 principal, A03/A27/A28/P2, educación y "
      f"encuestas son idénticos por construcción. Las conclusiones no cambian entre variantes.")
    A(f"- **Modelos.** {_n(k('models_n_variant'))} especificaciones convergentes por variante (cuasi-Poisson con offset; efectos fijos "
      f"y aleatorios por hospital; ajuste por profundidad y por disrupción 2020–2021; ventanas 2019–2024 y 2021–2024). Ninguna serie "
      f"identifica un efecto causal de la Ley 21.545 (marzo de 2023): coinciden recuperación pospandemia, expansión del reporte, "
      f"cambios de códigos y mayor profundidad de codificación.")
    A("")
    A("## 3. Controles de reproducción")
    A("")
    A(f"Los totales de control se declaran SIEMPRE con su ámbito, porque los dos ámbitos cuentan cosas distintas y no se suman. "
      f"(i) Ámbito `pipeline`, {CR.phrase(CR.PIPELINE, 'es')}: {_n(k('controls_csv_rows'))} comprobaciones consolidadas en "
      f"`outputs/controls/controls_summary.csv` ({_n(k('controls_csv_modules_n'))} archivos `<módulo>_controls.csv`, módulos 00 a 17), "
      f"repartidas en {_n(k('controls_csv_ok'))} `ok`, {_n(k('controls_csv_differs'))} `differs` y {_n(k('controls_csv_info'))} `info` "
      f"(valor sin referencia esperada); son las {_n(len(diff))} diferencias que lista la tabla siguiente y el total que imprimen la "
      f"Figura 1 y su tabla de recuentos. (ii) Ámbito `analysis_plan`, {CR.phrase(CR.ANALYSIS_PLAN, 'es')}: la Tabla 7 del manuscrito "
      f"(versión compacta, {_n(k('t8_control_families_n'))} claves distintas —las {_n(len(CFG.CONTROLS))} familias de control "
      f"preespecificadas de `config.CONTROLS` más {_n(k('t8_control_families_n') - len(CFG.CONTROLS))} controles del módulo, que no "
      f"son familias del protocolo—) y la {lab_t8} del apéndice reúnen "
      f"{_n(k('t8_rows'))} controles indicador-año ({_n(k('t8_ok'))} coinciden, {_n(k('t8_differs'))} difieren) y reproducen los totales "
      f"del protocolo. La fuente única de los dos totales es `study/controls_registry.py`; el consolidado los separa con su "
      f"columna `scope` y `controls_summary.md` los encabeza. Todas las diferencias están explicadas y ninguna es un error de lectura:")
    A("")
    A("| Módulo | Control | Clave | Esperado | Observado |")
    A("|---|---|---|---|---|")
    for _, r in diff.iterrows():
        # la clave puede traer una barra vertical (p. ej. «sin_rett|principal»), que partiría la fila de la tabla
        A(f"| {r['module']} | {r['name']} | {str(r['key']).replace('|', ' · ')} | {r['expected']} | {r['observed']} |")
    A("")
    A("Explicación (detalle en `outputs/controls/controls_summary.md`): (i) la hospitalización estricta 2023–2024 del protocolo se "
      "calculó sobre el panel fijo de 65 hospitales, mientras que la serie principal usa el panel observado (68 y 72 hospitales); "
      "la fila de comprobación sobre el panel fijo coincide exactamente y el módulo DEIS reproduce la misma diferencia como control "
      "cruzado; (ii) las personas únicas dentro del año difieren en exactamente 1 en cuatro años porque el protocolo contó el marcador "
      "de identificador inválido como una persona y el pipeline lo excluye (fila de comprobación coincidente); (iii) un par de filas "
      "F84 de 2020 es idéntico en las 45 columnas analizadas pero no en las 129 del archivo, y se conserva como dos episodios; (iv) una "
      "fila establecimiento-área-mes duplicada en REM-20 (junio de 2020) es aditiva y se conserva. Los esperados 0 de (iii) y (iv) son "
      "expectativas de calidad, no totales oficiales. Las diferencias de los módulos de material extendido, que el ámbito `pipeline` "
      "también consolida, son de la misma naturaleza: (v) fechas de ingreso o alta no analizables y altas anteriores al ingreso en el "
      "módulo 11, que se excluyen de la estadía y nunca se imputan, y la comparación con el primer estudio, cuya definición de caso no "
      "es idéntica y por eso se informa en lugar de forzarse; (vi) la suma por sexo o por edad del A05 excede en una unidad al total "
      "COL01 en 2025 (módulos 15 y 16) porque una celda establecimiento × mes viene vacía y vacío, cero y «no reportado» se mantienen "
      "como estados distintos; (vii) el propio módulo 07 marca cuántas filas de la tabla del plan toman su explicación de la nota del "
      "módulo sin redacción curada. Ninguna de estas diferencias cambia una cifra del artículo.")
    A("")
    A("## 4. Decisiones del módulo 10 y limitaciones pendientes")
    A("")
    A("- Los párrafos `[OPT]` se conservan sin la marca y se listan en la página final; la versión de revista debe eliminarlos "
      "(el texto núcleo ya cabe en 3500–5000 palabras y las referencias del núcleo no superan 30).")
    A("- **Los límites de la revista se aplican al envío en INGLÉS.** El inglés es la versión que se envía y cumple los tres límites "
      "(Resumen ≤ 250 palabras; texto núcleo 3500–5000 palabras; ≤ 30 referencias en el núcleo). El español es la traducción de "
      "trabajo del equipo: el español se expande frente al inglés, de modo que su Resumen y su texto núcleo son más largos palabra "
      "por palabra y quedan por encima de esos umbrales. Eso NO es un incumplimiento y NO se corrige recortando contenido, porque "
      "las dos versiones deben llevar exactamente las mismas cifras y los mismos párrafos: el español se comprueba por paridad de "
      "contenido con el inglés (razón de palabras dentro de 0,90–1,30) y no contra los límites de la revista. La portada de cada "
      "documento lo declara, el paso 17 lo controla con una fila por idioma que nombra el límite aplicable, y "
      "`reporting_checklist.md` lo repite en la fila de recuentos.")
    A(f"- La numeración suplementaria (Figura S1–S{n_sfig}, Tabla S1–S{n_stab}) es la posición en `SUPP_FIGURES` / `SUPP_TABLES` "
      f"(orden definido en `supplementary_material.py`), de modo que no depende de qué párrafos se conserven y es idéntica en el "
      f"manuscrito, en el apéndice separado y en los dos idiomas. Las citas de figuras y tablas del artículo las produce el "
      f"registro (`R.mfig()` / `R.mtab()`): no hay ningún número escrito a mano en `prose_en.py` ni en `prose_es.py`.")
    A("- Los conectores en español del formateador Vancouver compartido (`paper/references.py`: «Disponible en:», «editores», «En:») "
      "se traducen en los documentos en inglés dentro de este módulo sin modificar `paper/`.")
    A(f"- La última tabla del texto principal es la versión compacta de controles; la tabla completa va al material suplementario "
      f"({lab_t8}).")
    A("- La sección S6 del apéndice, que reproducía las 17 ecuaciones de `paper/equations.py`, fue sustituida por la metodología "
      f"extendida del módulo 12, que contiene las mismas fórmulas y {n_eq} en total, con una sola serie de numeración; ninguna "
      "fórmula se perdió.")
    A("- El análisis espacial y de correlación territorial (mapas comunales suavizados, LISA/Gi*, I de Moran bivariada, "
      "desigualdad territorial y asociación con la privación SAE 2024) ya no se pospone: está completo en el material "
      "suplementario, con la advertencia de que las asociaciones son ecológicas y de que REM localiza el lugar de atención y "
      "GRD la residencia.")
    A("- Las láminas usan letras de panel en MINÚSCULA y entre paréntesis, «(a)…(f)», en la figura y en la leyenda, en los dos "
      "idiomas, y las citas del texto también: las cinco que quedaban en mayúscula («Figure 3C», «Figure 5A», «Figure 5C», "
      "«Figure 5D–E», «Figure 5F») están corregidas y una prueba las vigila. La FORMA de la letra dentro de la lámina, que la "
      "fase 4d dejó abierta —39 de las 59 láminas imprimían «a» a secas—, se cerró en la fase 4e: los nueve módulos de lámina "
      "rotulan por `common.plate_panel_letter`, y el verificador independiente midió 0 mayúsculas y 0 letras sin paréntesis en "
      "las 118 construcciones con texto capturado. La COLOCACIÓN de esa letra, que la fase 4e dejó abierta —dieciséis letras "
      "desprendidas de su título en siete láminas de los módulos 13 y 14—, se cerró en la fase 4f anclando la letra al artista "
      "de su título: las 84 letras de esas siete láminas están hoy en la primera línea de su título en los dos idiomas, y una "
      "guarda dura (`letters_off_their_titles`) aborta los dos módulos si vuelve a ocurrir. En los paneles de mapa la letra se "
      "ancla al borde izquierdo de su celda y el título va centrado sobre los mapas, de modo que comparten línea con un hueco "
      "medido de 2,7 a 11,9 mm: es diferencia de estilo, no defecto. Las láminas siguen llevando título "
      "interno en cada panel, que la revista pide retirar en la versión de envío. El punto decimal a media altura (23·4) y los "
      "separadores de miles de la revista no se aplican.")
    A(f"- Las láminas del artículo se incrustan como PNG a 600 ppp y las suplementarias se remuestrean a "
      f"{report.get('supp_dpi') or 600} ppp (`--supp-dpi`, 0 = sin remuestrear). Con eso, el manuscrito completo pesa "
      f"{mb['manuscript']} ({pg['manuscript']}; PDF {pdf['manuscript']}), el apéndice suelto {mb['supplement']} "
      f"({pg['supplement']}; PDF {pdf['supplement']}) y el archivo sólo con el artículo {mb['article']} ({pg['article']}; PDF "
      f"{pdf['article']}). Para el envío lo natural es mandar `article_<variante>_en.docx` y el apéndice por separado, no el "
      f"archivo combinado.")
    A("- **Glosario de impresión** (fase 4k): la forma que el lector ve de un término se declara UNA vez en "
      "`labels.PRINTED_TERMS` y se aplica en el embudo por el que pasan los tres documentos enteros antes de "
      "escribirse —párrafos, títulos, entradillas, leyendas, notas, encabezados y celdas de tabla—, con una "
      "guarda que detiene la construcción si algo quedara sin aplicar. Hoy lleva dos reglas: la prosa española "
      "no imprime el anglicismo «crosswalk» sino «cuadro de equivalencias» (el inglés conserva el término, y "
      "los identificadores de máquina como `comuna_crosswalk.csv` no se tocan), y el par de apellidos "
      "«Getis–Ord» lleva la raya corta de Fay–Feuer o Clopper–Pearson en los dos idiomas. La regla se aplica "
      "ANTES de contar palabras, de modo que los recuentos de la portada describen el texto impreso.")
    A("- Sin enlace por persona entre fuentes: no hay cascada ni cocientes entre etapas; stocks (P2/P6, FONASA, APS, ISAPRE) y flujos "
      "(A03/A05/A27/A28, GRD, REM-20) se mantienen separados; lugar de atención y residencia no se mezclan.")
    A("- Del texto principal siguen fuera los mapas comunales, el catálogo de comorbilidades y las trayectorias GRD detalladas: "
      "están en el material suplementario y pueden sostener un segundo artículo, pero no engrosan el artículo.")
    A("")
    A("## 5. Lo que debe confirmar el equipo autor antes del envío")
    A("")
    A("1. **Afiliación institucional** de cada autor (marcador `[…]` en la portada, tomado de `paper/prose.py`).")
    A("2. **Financiamiento**: el texto declara «None»; confirmar o indicar la fuente y su rol.")
    A("3. **Segundo autor que verifique los datos**: la revista exige que más de un autor haya accedido y verificado los datos; hoy hay un solo autor.")
    A("4. **Límites de la revista**: confirmar en el sitio (bloqueo HTTP 403 a clientes automatizados) 3500–5000 palabras, 30 referencias, "
      "resumen de 250 palabras en cinco párrafos, «Research in context» sin referencias, y decidir qué párrafos `[OPT]` y qué tablas/láminas "
      "pasan al apéndice.")
    A("5. **Variante Rett**: elegir `con_rett` (familia F84 completa) o `sin_rett` (sin F84.2) como análisis principal; la otra queda como sensibilidad.")
    A("6. **Regla PIE 2022**: aceptar 42.940 (suma Apuntes 60 = total SINACES − escuelas especiales) frente a 42.945 impreso en el informe SINACES.")
    A("7. **Ponderadores JUNAEB**: EXP_REG (2024) y EXP (2025); 2023 sin ponderador (solo cifras no ponderadas); 1.º medio 2024 «no estimable».")
    A("8. **Ética**: el texto asume datos públicos desidentificados sin aprobación de comité; confirmar con la institución.")
    A("9. **Declaración de IA**: confirmar herramienta y versión (OpenAI Codex / Claude Code) y el alcance de la supervisión.")
    A("10. **Data sharing**: URL/DOI del repositorio de código y de las tablas derivadas; los microdatos GRD y de encuestas se citan por su fuente oficial.")
    A("11. **Research in context**: confirmar las cadenas de búsqueda exactas y la fecha (2026-09-04) contra `references_verification.csv`.")
    A("12. **Formularios ICMJE** de conflicto de intereses para cada autor.")
    A("")
    A("## 6. Lo que queda abierto tras las verificaciones (decidir antes de maquetar)")
    A("")
    # -----------------------------------------------------------------------
    # Todo lo que sigue —el estado, los veredictos, los recuentos y qué puntos
    # se imprimen— sale de `review_status.json` y de la medida de esta corrida.
    # Ninguna frase de estado se escribe a mano, y ninguna sobrevive a la ronda
    # que la arregla: cerrar un punto es cambiar su estado en el registro.
    # -----------------------------------------------------------------------
    n_open, n_block, n_defect = len(abiertos), len(bloquean), len(defectos)
    # un punto cerrado llega al papel sólo si su arreglo vive en los documentos: los que viven en un
    # archivo derivado (este memo, el índice del módulo 17) no esperan reconstrucción ninguna
    _en_docs = lambda p: (p.get("reaches_page") or "rebuild") == "rebuild"
    en_papel = [p for p in cerrados if _en_docs(p) and p["on_page"]]
    en_fuente = [p for p in cerrados if _en_docs(p) and not p["on_page"]]
    derivados = [p for p in cerrados if not _en_docs(p)]
    _plural = lambda n, uno, varios: uno if n == 1 else varios
    # cada lectura dice, junto a su veredicto, SOBRE QUÉ COMPILACIÓN se hizo: es la única manera de que
    # una lectura vieja no se lea como si fuera de estos doce archivos
    lect_frases = "; ".join(f"la de {r['es']} **{'pasa' if r['passes'] else 'no pasa'}**, "
                            f"{_n(r['n_pass'])} de {_n(r['n_checks'])} comprobaciones, "
                            f"{'sobre ESTOS doce documentos' if r['fresh'] else 'sobre la compilación del ' + _fecha(r.get('build'))}"
                            for r in st["readings"]) or "ninguna registrada"
    sobre = ("cada una sobre la compilación que declara"
             if st["readings"] else
             "NINGUNA: `review_status.json` no está o no se pudo leer, de modo que este memo no da por buena "
             "ninguna lectura")
    if not st["present"]:
        # un registro que falta NO es un material sin puntos abiertos: el memo lo dice así de claro
        A("**Estado en una frase: no se puede afirmar, y por eso este memo no afirma nada.** El registro de "
          "lecturas y puntos abiertos (`review_status.json`) no está o no se pudo leer, de modo que esta corrida "
          "no da por buena ninguna lectura anterior: sin él no hay veredicto, no hay lista de puntos abiertos y "
          "no se puede decir si el material se puede enviar. Reponer el registro —o rehacer la lectura "
          "independiente sobre esta compilación— es lo primero que hay que hacer.")
    elif n_block:
        A(f"**Estado en una frase: el material NO está terminado.** Las lecturas independientes registradas, "
          f"{sobre}: {lect_frases}. Quedan "
          f"**{_n(n_open)} puntos abiertos**, de los que {_n(n_defect)} se "
          f"{_plural(n_defect, 'lee', 'leen')} como defecto y **{_n(n_block)}** "
          f"{_plural(n_block, 'bloquea', 'bloquean')} el envío: "
          f"{'; '.join(p.get('es', p['key']) for p in bloquean)}. Todo lo demás de la tabla son convenciones "
          f"declaradas, decisiones ya tomadas que sólo hay que ratificar, deuda de herramienta o trabajo de la "
          f"pasada de maqueta de la revista.")
    else:
        A(f"**Estado en una frase: ningún punto abierto bloquea el envío.** Las lecturas independientes "
          f"registradas, {sobre}: {lect_frases}. Quedan **{_n(n_open)} puntos abiertos** y ninguno de ellos "
          f"detiene el envío: son convenciones declaradas, decisiones ya tomadas que sólo hay que ratificar, "
          f"deuda de herramienta o trabajo de la pasada de maqueta de la revista.")
    A("")
    if cerrados:
        _rep = [f"{_n(len(en_papel))} ya {_plural(len(en_papel), 'impreso', 'impresos')} en estos doce "
                f"archivos" if en_papel else "",
                f"{_n(len(en_fuente))} {_plural(len(en_fuente), 'cerrado', 'cerrados')} en la fuente, a "
                f"la espera de la próxima reconstrucción" if en_fuente else "",
                f"{_n(len(derivados))} en un archivo derivado que no se imprime en los doce documentos"
                if derivados else ""]
        A(f"**Cerrados desde esa lectura: {_n(len(cerrados))}** — {', '.join(x for x in _rep if x)}. "
          f"La distinción tampoco se escribe a mano: el registro anota la hora en que cada punto "
          f"se cerró y el memo la compara con la hora de la compilación que describe, de modo que pasan solos de "
          f"«en la fuente» a «en el papel» en cuanto una compilación posterior los recoge.")
        A("")
        for pt in cerrados:
            if (pt.get("reaches_page") or "rebuild") != "rebuild":
                # un arreglo que vive en un archivo derivado (este memo, el índice del módulo 17) no
                # espera reconstrucción ninguna: decir «todavía no en el papel» sería falso
                estado = "**cerrado**, en un archivo derivado que no se imprime en los doce documentos"
            else:
                estado = ("**ya en el papel**" if pt["on_page"] else
                          "**cerrado en la fuente**, todavía no en estos doce archivos")
            _cap = lambda s: (s[:1].upper() + s[1:]) if s else s
            A(f"* {_cap(pt.get('es', pt['key']))} — {estado} ({pt.get('fixed_by_es', 'sin autor anotado')}). "
              f"{_cap(pt.get('fix_es', '—'))}.")
        A("")
    A(f"**Lo que estas lecturas dieron por CORRECTO**{_sello()}, cada medida con su instrumento propio y su "
      f"control positivo, de modo que ningún cero es el silencio de un instrumento mudo: el folio, en "
      f"**{_n(total_pages)} de {_n(total_pages)} páginas**, siempre como último texto de la página y siempre igual "
      f"al índice (0 ausentes, 0 equivocados); **{spill_marked} colas de leyenda, todas rotuladas y "
      f"{spill_unmarked} sin rótulo**, contra las {_m('colas_sin_rotulo', prev)} sin rótulo de la compilación "
      f"anterior; **{_m('entradillas_en_su_pagina')} de {_m('entradillas_totales')} entradillas** impresas en la "
      f"página de su lámina, sobre {_m('leyendas_localizadas')} leyendas localizadas, 0 que abran en una página "
      f"sin lámina y 0 páginas con dos láminas; el verificador de composición, "
      f"**{_m('construcciones_comprobadas')} construcciones comprobadas y {_m('construcciones_con_defecto')} con "
      f"defectos** —su control positivo devuelve {_m('control_positivo_defectos')}—, con "
      f"{_m('laminas_identicas_byte')} de {_m('construcciones_comprobadas')} láminas idénticas byte a byte a las "
      f"impresas y las {_m('laminas_identicas_pixel')} idénticas píxel a píxel, de modo que lo comprobado es "
      f"exactamente lo que se imprime; **{_m('rangos_con_guion_en_lamina')} rangos con guion en "
      f"{_m('rotulos_de_lamina_medidos')} rótulos de lámina**; el porcentaje por idioma "
      f"({_m('porciento_pegado_en')} pegados en inglés contra {_m('porciento_espacio_duro_es')} con espacio duro "
      f"en español, **{_m('porciento_al_reves')} al revés**) y **{_m('cifras_separadas_de_su_signo')} cifras "
      f"separadas de su signo** por un corte de renglón; el reparto de signos, un oficio para cada uno (raya "
      f"corta {_m('raya_corta_manuscrito_en')}, guion {_m('guion_manuscrito_en')}, raya larga "
      f"{_m('raya_larga_manuscrito_en')}, menos U+2212 {_m('menos_manuscrito_en')} en el manuscrito inglés); el "
      f"cuerpo mínimo de lámina, **{_m('cuerpo_minimo_lamina_pt', dec=1)} pt** en las {_m('laminas_distintas')} "
      f"láminas distintas, todas dibujadas y colocadas a 180 mm; y la lectura a tamaño de impresión de "
      f"{_m('laminas_leidas_a_tamano')} láminas, **{_m('laminas_leidas_legibles')} legibles**. En el contenido: "
      f"numeración suplementaria S1–S{n_sfig} y S1–S{n_stab} sin hueco e idéntica entre cada manuscrito y su "
      f"apéndice, **{_m('referencias_cruzadas_colgadas', mc)} referencias cruzadas colgadas**, las {n_eq} "
      f"ecuaciones cada una una vez y en orden con **{_m('desajustes_encabezado_ecuacion', mc)} desajustes** entre "
      f"lo que promete un encabezado y lo que se imprime debajo, listas de referencias contiguas (artículo "
      f"{_m('referencias_articulo', mc)}, manuscrito {_m('referencias_manuscrito', mc)}, apéndice "
      f"{_m('referencias_apendice', mc)}), paridad numérica bilingüe sobre "
      f"{_m('celdas_comparadas_entre_idiomas', mc)} celdas con "
      f"{_m('diferencias_reales_entre_idiomas', mc)} diferencias reales, y "
      f"**{_m('infracciones_de_las_reglas_del_estudio', mc)} infracciones** de las reglas del estudio —ni "
      f"prevalencia, ni incidencia, ni cascada, ni enlace por persona, ni efecto causal de la Ley 21.545, stocks "
      f"y flujos nunca en el mismo eje, y el aviso de lugar de atención entero donde hace falta—.")
    A("")
    A(f"Todo lo verificado en las rondas anteriores sigue en pie y no se repite aquí: la estructura de los doce "
      f"documentos; la numeración (Figuras 1–{n_mfig} y S1–S{n_sfig}, Tablas 1–{n_mtab} y S1–S{n_stab}, completas, "
      f"únicas y sin huecos); que ninguna cita queda fuera de rango y ningún ítem definido queda sin citar; la "
      f"pureza de idioma en los dos sentidos, donde lo que queda es transcripción literal declarada; y la paridad "
      f"numérica entre gemelos.")
    A("")
    if n_defect:
        A(f"{'El punto' if n_defect == 1 else 'Los puntos'} "
          f"{', '.join(str(N[p['key']]) for p in defectos)} de la tabla "
          f"{_plural(n_defect, 'es el único que se lee', 'son los que se leen')} como un defecto. Los "
          f"{_n(n_open - n_defect)} restantes no cambian ninguna cifra del estudio ni ninguna conclusión, y son "
          f"convenciones declaradas, decisiones ya tomadas, deuda de herramienta o trabajo de la pasada de maqueta "
          f"de la revista. **La tabla no se edita a mano:** un punto se cierra cambiando su estado en "
          f"`review_status.json` (`state`, `fixed_at`, `fixed_by_es`, `fix_es`), y la tabla se renumera sola, sin "
          f"dejar hueco ni referencia colgada, en la primera corrida que escriba este memo.")
    else:
        A(f"Ninguno de los {_n(n_open)} puntos de la tabla se lee como un defecto: no cambian ninguna cifra del "
          f"estudio ni ninguna conclusión, y son convenciones declaradas, decisiones ya tomadas, deuda de "
          f"herramienta o trabajo de la pasada de maqueta de la revista.")
    A("")
    # La ficha de cada punto: el texto vive aquí, el ESTADO vive en el registro. La tabla imprime sólo
    # los abiertos, en el orden del registro, y el número de cada uno se calcula al imprimirlo, de modo
    # que cerrar un punto no deja huecos ni referencias cruzadas colgadas.
    v65 = mc.get("panel65_enunciado_viejo") or {}
    n65 = mc.get("panel65_enunciado_nuevo") or {}
    FICHA = {
        "panel65": (
            f"**EL ÚNICO QUE SE LEE COMO DEFECTO. El corpus imprime dos definiciones del mismo panel de 65 "
            f"hospitales.** «Panel fijo de 65 = hospitales presentes en 2019–2022» y «panel fijo de 65 = "
            f"hospitales presentes en todos los años 2019–2024» conviven en los doce documentos, y conviven "
            f"cerca: apéndice inglés **p. 361** (Tabla S62) dice «present in 2019–2022» y **p. 362** (Tabla S64) "
            f"dice «present in every year 2019–2024»; la Tabla S71 (p. 372) lo enuncia entero y la Tabla S105 "
            f"(p. 450) vuelve al enunciado viejo; en el artículo, p. 18 (nota de la Tabla 1) contra p. 49 (tabla "
            f"de controles). Contado sobre la página impresa{_sello('content')}: enunciado viejo contra enunciado nuevo, "
            f"{_m('manuscrito_en', v65)}/{_m('manuscrito_en', n65)} por manuscrito inglés, "
            f"{_m('manuscrito_es', v65)}/{_m('manuscrito_es', n65)} por manuscrito español, "
            f"{_m('apendice_en', v65)}/{_m('apendice_en', n65)} por apéndice inglés, "
            f"{_m('apendice_es', v65)}/{_m('apendice_es', n65)} por apéndice español y "
            f"{_m('articulo', v65)}/{_m('articulo', n65)} por artículo. | `11_grd_episode_detail.py` (166, 1332, "
            f"1338), `16_extra_tables.py` (429, 437, 705, 713), `09b_tables_supplementary.py` (615, 621, 1457), "
            f"`07_controls.py` (158, 159, 166, 167) —éste es el del artículo— y `06_models.py` (1161, 1162). En "
            f"`01_grd_core.py` (21, 593, 630) «2019–2022» describe la REGLA DE CONSTRUCCIÓN y **ahí es exacto y "
            f"no debe cambiarse** | **No hay nada que decidir sobre el fondo, y sí sobre el alcance.** Los dos "
            f"enunciados designan el MISMO conjunto: los 65 tienen `n_years_present = 6`, la intersección de "
            f"2019–2022 y la de 2019–2024 son el mismo conjunto, y dos controles que pasan garantizan su "
            f"presencia en 2023 y 2024. La glosa que el corpus debe decir, literal, ya está fijada: «panel fijo "
            f"de 65 = hospitales presentes en todos los años 2019–2024» / «fixed panel of 65 = hospitals present "
            f"in every year 2019–2024». Sigue abierto porque la tarea que la fijó sólo poseía tres de los ocho "
            f"módulos que la escriben. Coste: minutos de edición en cinco módulos, reejecutarlos, y "
            f"**reconstruir los doce documentos** (≈ 16 min)."),
        "caption_tail_pages": (
            f"**{n_tail_only} páginas de los doce documentos llevan sólo la cola rotulada de una leyenda**, y "
            f"detrás de ella {_span(tail_gaps, 1)} cm de blanco medidos en el propio PDF. "
            f"{_lst(tail_by_lang['en'])} por documento largo en inglés y {_lst(tail_by_lang['es'])} en español "
            f"—`manuscript_con_rett_en` pp. {_tail_pages_of('manuscript_con_rett_en')}; "
            f"`supplement_con_rett_es` pp. {_tail_pages_of('supplement_con_rett_es')}, y sus equivalentes en los "
            f"demás—. No están vacías: llevan su cola con rótulo, su número de figura y su folio, "
            f"{_span(tail_chars)} caracteres. Su guarda de página casi vacía (`near_empty_pages`, "
            f"{n_below_join} en los doce) no las ve, porque cuenta caracteres; el ojo sí las ve. | "
            f"`docx_builder.py`, regla de partición de la leyenda (tarea J1) | Es el **precio medido** de la "
            f"regla nueva, y la alternativa está medida y es peor: {_m('colas_sin_rotulo', prev)} colas de "
            f"leyenda sin dueño en la página siguiente. No hay nada que arreglar, hay algo que **ratificar**: se "
            f"acepta el blanco, o se vuelve a discutir el suelo tipográfico de la leyenda ({cap_floor} pt desde "
            f"la fase 4e) para que quepan más líneas bajo la lámina —que es lo que la fase 4e subió a "
            f"propósito—. Coste de cambiarlo: **reconstruir los doce documentos** (≈ 16 min) y releer la región "
            f"de láminas entera."),
        "hyphen_range_count": (
            "**La cifra declarada de rangos con guion se queda corta.** El informe de la reconstrucción declara "
            "**18 por documento largo** en dos tablas; la página imprime **267 por documento largo** (0 en los "
            "cuatro sólo-artículo), en seis columnas de cinco tablas: Tabla S122 «Model (identifier)» 220 claves "
            "de modelo (`grd_rate:con_rett:observed:all:any:none:2019-2024`), Tabla S16 «Meaning of COL01/COL02 "
            "(verbatim Spanish)» 38, Tabla S42 «Response codes» 4, Tabla S123 «Control family» 4 y Tabla S14 "
            "«Period» 1 («2014-07/2026»). | `tools/dash_audit.py --docx`, que cuenta las formas pegadas y no las "
            "que llevan espacios alrededor | **Falla la CIFRA, no la regla**: ningún intervalo de LECTURA queda "
            "con guion. Los 42 de S16 y S42 son la transcripción literal declarada —el diccionario oficial REM "
            "escribe «16 - 30 meses» en `DICCIONARIO CODIGOS SA_23_V1.4.xlsm`, fila 215— y los 225 restantes son "
            "identificadores de máquina que se cruzan carácter a carácter con `outputs/controls/*.csv`. Arreglo: "
            "que el instrumento cuente también las formas con espacios y que el informe declare las dos cuentas. "
            "Coste: minutos, sin reconstruir nada, porque no cambia ni una letra del papel."),
        "layout_checker_gap": (
            f"**Un hueco del verificador de composición, diagnosticado y no tapado.** Un rótulo de valor SIN "
            f"recuadro escrito encima de su propia barra cae entre dos reglas: `_ck_value_labels` lo mide contra "
            f"marcadores y barras de error, nunca contra el rectángulo de una barra, y `_ck_bar_masks` descarta "
            f"todo rótulo sin recuadro visible. La causa próxima de que no tuviera recuadro es un orden: "
            f"`_pl_backing` corre antes que `_pl_clip_guard`, de modo que cuando se decide que no hay tinta "
            f"debajo el rótulo todavía está fuera de la barra. | `common.py` (`_ck_value_labels` línea 2384, "
            f"`_ck_bar_masks` 2504 y 2528; `plate_resolve` 1648–1649) | No se tapó por riesgo, no por esfuerzo: "
            f"las dos curas candidatas cambian el motor que dibuja LAS {_m('construcciones_comprobadas')} láminas "
            f"y pueden encender defectos en láminas hoy limpias —en modo `strict` abortarían el módulo y "
            f"bloquearían la reconstrucción—. Comprobarlas honestamente pide reejecutar los nueve módulos de "
            f"lámina (≈ 50 min medidos) y releer a tamaño de impresión las que cambien. Es una ronda propia con "
            f"su propio presupuesto de comprobación."),
        "fige26b": (
            "**`figE26b` (Figura S42) no se reproduce byte a byte.** Ocho corridas del módulo 15 dan una de "
            "exactamente dos imágenes, en la secuencia 1, 2, 1, 2, 1, 2, 2, 1: no es un ciclo sino un sorteo "
            "entre dos estados. Descartados por medición el orden de iteración de un conjunto (dos corridas con "
            "`PYTHONHASHSEED=0` dan igualmente las dos), el generador aleatorio (los dos `np.random` del módulo "
            "llevan semilla fija y están en otra lámina) y «lee lo que escribe»; con `--only E26b` la lámina "
            "repite, de modo que la inestabilidad necesita que las otras nueve se dibujen antes en el mismo "
            "intérprete. | `pipeline/15_extra_figures_context.py`, panel (d), y `common.plate_text_width_pt` | "
            "Nada impreso cambia: las 72 razones con su IC 95 % se reencuentran verbatim en la tabla acompañante "
            "y las dos imágenes son indistinguibles a tamaño de impresión (0 píxeles distintos de 24,6 M en la "
            "comparación que hizo el lector de esta ronda; sólo difieren los metadatos del PNG). Sospecha "
            "razonada, sin comprobar: el eje del panel (d) se fija midiendo el rótulo más ancho sobre una figura "
            "oculta global, y la iteración que estira el eje para en medio píxel. Cerrarlo pide instrumentar "
            "esas dos rutas sobre corridas repetidas."),
        "rem20_area_names": (
            "**El nombre completo de las diez áreas funcionales REM-20 no está en ningún sitio del papel.** La "
            "Figura S37 (e) recorta con puntos suspensivos uno de sus diez rótulos en inglés y dos en español "
            "—el recorte es política declarada y `_abbrev_distinct` lo ensancha hasta que no queden dos rótulos "
            "iguales—, pero la Tabla S84, que acompaña a la lámina, no lista las áreas y el pie tampoco las "
            "nombra. | `pipeline/15_extra_figures_context.py` y la tabla que acompaña a la lámina | Es la "
            "excepción: la EF5, por ejemplo, recorta igual sus categorías CIE-10 y su tabla compañera las "
            "imprime enteras. Arreglo barato: añadir la columna de nombre completo a la tabla acompañante o "
            "nombrarlas en el pie. Coste: minutos, más **una reconstrucción** (≈ 16 min)."),
        "map_panel_letter": (
            "En los paneles de mapa la letra de panel se ancla al borde izquierdo de su celda y el título va "
            "centrado sobre los mapas, de modo que comparten línea pero con un hueco medido de 2,7 a 11,9 mm "
            "(S24 (d): 9,8 mm en español y 11,9 en inglés; S29 (d): 2,7 y 6,6). | `common.align_panel_titles` | "
            "Es consecuencia del anclaje que cerró el defecto de las letras desprendidas, y la guarda sólo exige "
            "que letra y título compartan la línea (2,0 pt de tolerancia vertical). El verificador lo lee sin "
            "ambigüedad y así lo leyó la verificación humana. Queda anotado como **diferencia de estilo a "
            "ratificar**, no como defecto."),
        "appendix_reference_numbering": (
            "El apéndice suelto reinicia la numeración de referencias en 1: «(19,20)» del apéndice designa lo "
            "que el manuscrito combinado numera «(36,37)». Su nota de apertura promete estabilidad sólo para "
            "figuras y tablas. | `pipeline/10_manuscript.py` (decisión C10) | Viene de la fase 4c y no se tocó: "
            "cada archivo es autónomo y su lista de referencias empieza donde empieza el archivo. La biyección "
            "se verificó correcta en las cuatro combinaciones. Decidir entre **añadir el aviso a la nota del "
            "apéndice** o numerar de corrido con el manuscrito."),
        "supp_methods_numbering": (
            "Los encabezados de «Métodos suplementarios» se numeran S1.–S5. y colisionan con los números de "
            "lámina y de tabla S1–S5. | `prose_en.py` / `prose_es.py` (encabezados de los métodos "
            "suplementarios) | Ningún texto los cita por ese número, de modo que hoy no rompe ninguna cita; "
            "queda como riesgo de lectura. Decidir si se renumeran (por ejemplo M1–M5) antes de maquetar."),
        "spanish_verbatim_in_english": (
            "Términos de la fuente en español dentro de los documentos ingleses, marcados pero no glosados: la "
            "unidad de observación de la Tabla S14 imprime «cotizantes and cargas», y las 21 categorías de "
            "`ESPECIALIDAD_MEDICA` de la Tabla S109 se imprimen verbatim en mayúsculas («PEDIATRÍA», "
            "«TRAUMATOLOGÍA Y ORTOPEDIA»). | `data_provenance.csv` (módulo 00) y "
            "`pipeline/09b_tables_supplementary.py` sobre `E4_grd_episode_features.csv` | Los dos están "
            "**marcados** como verbatim y la convención se declara en la nota de la S109, de modo que no son una "
            "fuga de idioma; lo que falta es la glosa que sí llevan la S16 y la S42. «cotizantes and cargas» ya "
            "lo glosa la Tabla S118, y cambiarlo obligaría a reescribir el CSV de procedencia y con él su "
            "SHA-256. `SERVICIO_SALUD` y `PREVISION` son nombres propios y no necesitan glosa; sólo "
            "`ESPECIALIDAD_MEDICA` es contenido que una glosa ayudaría a leer."),
        "white_foot_pages": (
            f"Páginas que dejan mucho papel al pie, todas ellas ABRIENDO un bloque y ninguna vacía: "
            f"{_lst(art_tail)} por archivo sólo-artículo antes de una sección apaisada; y de {_span(after_sparse)} "
            f"por documento largo en la región de tablas (más de 15 cm al pie). | `docx_builder.py` | Un cambio "
            f"de orientación obliga siempre a empezar página, y hay unas veinte tablas anchas por documento. Se "
            f"probó la alternativa —dejar que la sección apaisada se llevara el encabezado— y sale peor. Se "
            f"acepta o se dejan de rotar tablas, decisión anterior a esta fase. Las páginas de sola cola de "
            f"leyenda son el punto {N['caption_tail_pages']}, no éste."),
        "figure1_weaknesses": (
            "Figura 1, dos debilidades que el autor ya conoce y decidió no tratar: en el carril de encuestas los "
            "tres n de entrada (30.010 / 5.526 / 16.484) y los tres de salida (72 / 163 / 80) se emparejan con "
            "ENDIDE 18+ / ENDIDE 2–17 / ENCAVI 15+ **sólo por el orden de lectura**, y la fila MINEDUC · PIE / "
            "JUNAEB apila pares («475.710 / 239.332») cuyos miembros no se nombran en la lámina; y el PIE "
            "conserva el bloque «CÓMO ESTÁ DIBUJADO», que el encargo prohibía en la LÁMINA (donde no está) pero "
            "no en el pie. | `pipeline/08d_figure_dataflow.py` | Es decisión de contenido del autor: nombrar "
            "cada fuente junto a su cifra alargaría el carril, y el bloque «cómo está dibujado» del pie es lo "
            "que permitió quitarlo de la lámina. La lámina cumple el encargo en todo lo demás, verificado a 150 "
            "y 400 ppp en los dos idiomas."),
        "journal_typography": (
            "Requisitos tipográficos de la revista aún no aplicados: ancho de columna de 107 mm frente a los 180 "
            "mm de página completa, sin títulos internos de panel, punto decimal a media altura (23·4) y valores "
            "p con dos cifras significativas. | los nueve módulos de lámina y `docx_builder.py` | Es trabajo de "
            "la **versión de envío**, no de la versión de trabajo: la norma de 180 mm a página completa es la "
            "que el autor pidió para leer y revisar. Decidir cuándo se hace la pasada de maqueta."),
        "tooling_debt": (
            "Deuda de herramienta, anotada desde la fase 4g y sin cerrar: el formateador de porcentaje por "
            "idioma se escribe **una vez por módulo en nueve módulos** en vez de una sola vez en `common.py`; y "
            "los cuatro comandos de `tools/` (`caption_spill_audit`, `dash_audit`, `folio_audit`, `hyphen_scan`) "
            "no entran en la batería porque medir sobre láminas redibujadas cuesta unos 50 minutos por pasada. | "
            "`common.py` y los nueve módulos de lámina; `tests/` | No se ve en la página y no cambia una cifra: "
            "es riesgo de que una copia se quede atrás. **Decidir** si se centraliza el formateador antes de la "
            "pasada de maqueta, y si los cuatro comandos se corren a mano en cada reconstrucción (que es lo que "
            "se ha hecho hasta hoy) o se meten en la batería con un interruptor de entorno."),
    }
    faltan = [p["key"] for p in abiertos if p["key"] not in FICHA]
    if faltan:                     # un punto sin ficha se imprimiría como una fila muda
        raise RuntimeError(f"review_status.json abre puntos sin ficha en el memo: {', '.join(faltan)}")
    A("| # | Qué queda abierto | Dónde se produce | Por qué sigue abierto, y qué hay que decidir |")
    A("|---|---|---|---|")
    for p in abiertos:
        A(f"| {N[p['key']]} | {FICHA[p['key']]} |")
    A("")
    if not st["present"]:
        A("**¿Se puede enviar el material tal como está?** **No se puede responder desde este memo**: falta el "
          "registro de lecturas y puntos abiertos, y la respuesta se calcula de él. Las cifras de la página "
          "impresa que sí trae este memo vienen de `manuscript/build_report.json` y se sostienen.")
    elif n_block:
        A(f"**¿Se puede enviar el material tal como está?** Medido, la respuesta es **todavía no, y por "
          f"{'un solo punto' if n_block == 1 else _n(n_block) + ' puntos'}**. Los {_n(total_pages)} folios, las "
          f"{spill_marked} colas de leyenda rotuladas, las {_m('construcciones_comprobadas')} láminas "
          f"comprobadas, la numeración, las {n_eq} ecuaciones, las citas, las listas de referencias, la paridad "
          f"numérica entre idiomas y las reglas del estudio están verificadas{_sello()} y se sostienen; los doce "
          f"documentos se pueden leer de principio a fin y se pueden mandar a leer a un tercero. Lo que queda "
          f"entre estos archivos y el envío es "
          f"{', '.join(f'**el punto ' + str(N[p['key']]) + ' —' + p.get('es', p['key']) + '—**' for p in bloquean)}, "
          f"con su reconstrucción, más las decisiones del equipo autor de la sección 5 y la pasada de maqueta de "
          f"la revista (punto {N['journal_typography']}).")
    else:
        A(f"**¿Se puede enviar el material tal como está?** Medido, **ningún punto abierto lo impide**: los "
          f"{_n(total_pages)} folios, las {spill_marked} colas de leyenda rotuladas, las "
          f"{_m('construcciones_comprobadas')} láminas comprobadas, la numeración, las {n_eq} ecuaciones, las "
          f"citas, las listas de referencias, la paridad numérica entre idiomas y las reglas del estudio están "
          f"verificadas{_sello()} y se sostienen. Lo que queda son las decisiones del equipo autor de la "
          f"sección 5 y la pasada de maqueta de la revista (punto {N['journal_typography']}).")
    A("")
    A(f"**Dos observaciones que no son defectos pero conviene saber.** La conversión a PDF **remuestrea a "
      f"{report.get('supp_dpi') or 600} ppp** las cinco figuras del artículo, que el DOCX incrusta a "
      f"{report.get('article_dpi') or 600} ppp y 180 × 245 mm como se declaró; a tamaño de impresión las veinte "
      f"láminas leídas siguen siendo legibles, pero el archivo que se envíe a la revista debe ser el **DOCX**, no "
      f"su PDF, si se quiere conservar la resolución declarada. Y la afirmación «ninguna página por debajo de 300 "
      f"caracteres» **depende de la definición, y el informe dice ya de cuál habla**: la cuenta que el estudio "
      f"informa es la del texto que `pdftotext` extrae de la página con las palabras unidas por un espacio y las "
      f"líneas por un salto —los separadores cuentan—, descontado el folio, y con ella el mínimo del corpus es "
      f"**{_n(min(min_join))}** y no baja de 300 ninguna página; contando sólo los caracteres **no blancos** del "
      f"mismo texto el mínimo es **{_n(min(min_nonws))}** y quedan por debajo de 300 **{n_below_nonws} portadas de "
      f"apéndice suelto**. Son bloques de título completos, no páginas flojas, y las dos cuentas se escriben en "
      f"cada corrida (`review.layout.min_chars` y `min_chars_nonws`).")
    A("")
    A("### Lo que hay que decidir, y lo que queda abierto")
    A("")
    if defectos:
        A(f"**1 · {'Lo único que se lee como defecto' if n_defect == 1 else 'Lo que se lee como defecto'}, y qué "
          f"hay que decidir.**")
        A("")
        A(f"* **La glosa del panel fijo de 65, dicha de dos maneras** (punto {N['panel65']} de la tabla). *Qué hay "
          f"que decidir:* nada sobre el fondo —los dos enunciados designan el mismo conjunto de 65 hospitales, "
          f"establecido desde los datos— y sí sobre el alcance: adoptar en los cinco módulos que faltan la "
          f"redacción ya fijada, «panel fijo de 65 = hospitales presentes en todos los años 2019–2024» / «fixed "
          f"panel of 65 = hospitals present in every year 2019–2024», dejando intacta la de `01_grd_core.py`, "
          f"donde «presentes en 2019–2022» es la regla de construcción y es exacta. *Por qué sigue abierto:* la "
          f"tarea que fijó la glosa sólo poseía tres de los ocho módulos que la escriben. *Coste:* minutos de "
          f"edición, reejecutar cinco módulos y **reconstruir los doce documentos** (≈ 16 min); después, releer "
          f"las páginas donde las dos glosas convivían (apéndice inglés pp. 361–362 y 372, artículo pp. 18 y 49).")
        A("")
    else:
        A("**1 · Ningún punto abierto se lee como defecto.**")
        A("")
    A("**2 · Decisiones que sólo puede tomar el equipo autor** (ninguna la puede aportar el pipeline; el detalle "
      "está en la sección 5). Cada una con su razón y su coste:")
    A("")
    A("* **Afiliación institucional de cada autor.** *Razón:* la portada lleva el marcador `[…]`. *Coste:* un dato; "
      "se aplica en `paper/prose.py` y pide una reconstrucción (≈ 16 min).")
    A("* **Financiamiento y su rol.** *Razón:* el texto declara «None» y la revista exige declararlo. *Coste:* un "
      "dato y una reconstrucción.")
    A("* **Segundo autor que acceda y verifique los datos.** *Razón:* la revista lo exige y hoy hay un solo autor. "
      "*Coste:* una persona y su firma; no toca el pipeline.")
    A("* **Confirmar los límites de la revista y recortar los párrafos `[OPT]`.** *Razón:* el sitio bloquea a los "
      "clientes automatizados (HTTP 403) y los límites se citan del PDF archivado. *Coste:* una lectura del sitio; "
      "el recorte, si se decide, es una reconstrucción.")
    A("* **Variante Rett principal** (`con_rett` o `sin_rett`). *Razón:* el estudio entrega las dos y ninguna es "
      "«la» principal por sí sola; las conclusiones no cambian entre ellas. *Coste:* ninguno en el pipeline —los "
      "doce documentos ya existen—: es decidir cuál se envía y cuál queda como sensibilidad.")
    A("* **Regla PIE 2022**: 42.940 (suma Apuntes 60 = total SINACES − escuelas especiales) frente a 42.945 "
      "impreso. *Razón:* la fuente se contradice consigo misma en 5 casos. *Coste:* si se cambia, reejecutar el "
      "módulo de educación y reconstruir.")
    A("* **Ponderadores JUNAEB**: EXP_REG (2024) y EXP (2025); 2023 sin ponderador; 1.º medio 2024 «no estimable». "
      "*Razón:* la fuente no publica el mismo ponderador todos los años. *Coste:* confirmar; ya está implementado "
      "y declarado.")
    A("* **Ética.** *Razón:* el texto asume datos públicos desidentificados sin aprobación de comité. *Coste:* una "
      "confirmación institucional.")
    A("* **Declaración de IA**: herramienta, versión y alcance de la supervisión. *Coste:* un párrafo y una "
      "reconstrucción.")
    A("* **Data sharing**: URL/DOI del repositorio de código y de las tablas derivadas. *Razón:* hoy sólo se citan "
      "las fuentes oficiales de los microdatos. *Coste:* publicar el repositorio y una reconstrucción.")
    A("* **Research in context**: confirmar las cadenas de búsqueda y su fecha (2026-09-04) contra "
      "`references_verification.csv`. *Coste:* una revisión.")
    A("* **Formularios ICMJE** de conflicto de intereses. *Coste:* trámite, fuera del pipeline.")
    A("")
    A("**3 · Lo demás que queda abierto, y no bloquea**, por orden de coste, con su razón y con el punto de la "
      "tabla al lado:")
    A("")
    DECIDIR = {
        "caption_tail_pages": (
            f"* **Ratificar las {n_tail_only} páginas de sola cola de leyenda** ({N.get('caption_tail_pages')}). "
            f"*Razón:* es el precio medido de la regla que cerró las {_m('colas_sin_rotulo', prev)} colas "
            f"huérfanas, y la alternativa está medida y es peor. *Coste:* cero si se ratifica; una reconstrucción "
            f"si se decide volver a tocar el suelo de la leyenda."),
        "hyphen_range_count": (
            f"* **Corregir la cifra declarada de rangos con guion** ({N.get('hyphen_range_count')}). *Razón:* el "
            f"instrumento cuenta las formas pegadas y no las que llevan espacios, de modo que declara 18 por "
            f"documento largo donde la página imprime 267 —ninguno de ellos un intervalo de lectura—. *Coste:* "
            f"minutos, sin reconstruir nada."),
        "rem20_area_names": (
            f"* **El nombre completo de las diez áreas funcionales REM-20** ({N.get('rem20_area_names')}). "
            f"*Razón:* la lámina las recorta por política declarada y su tabla compañera no las imprime. *Coste:* "
            f"una columna en la tabla, más una reconstrucción."),
        "supp_methods_numbering": (
            f"* **Renumerar los encabezados de métodos suplementarios a M1–M5** "
            f"({N.get('supp_methods_numbering')}). *Razón:* S1.–S5. colisiona con las láminas y tablas S1–S5, "
            f"aunque hoy ninguna cita los use. *Coste:* minutos, más una reconstrucción."),
        "spanish_verbatim_in_english": (
            f"* **Glosar `ESPECIALIDAD_MEDICA` en la Tabla S109** ({N.get('spanish_verbatim_in_english')}). "
            f"*Razón:* es verbatim declarado, pero sin glosa. *Coste:* una nota, más una reconstrucción."),
        "appendix_reference_numbering": (
            f"* **Numerar de corrido las referencias del apéndice suelto, o avisar en su nota** "
            f"({N.get('appendix_reference_numbering')}). *Razón:* cada archivo es autónomo por decisión de la "
            f"fase 4c. *Coste:* una frase, o rehacer la numeración de los cuatro apéndices."),
        "map_panel_letter": (
            f"* **Ratificar el anclaje de la letra de panel en los mapas** ({N.get('map_panel_letter')}) y **las "
            f"dos debilidades declaradas de la Figura 1** ({N.get('figure1_weaknesses')}). *Razón:* son "
            f"decisiones ya tomadas. *Coste:* cero."),
        "figure1_weaknesses": None,          # se nombra en la línea anterior
        "tooling_debt": (
            f"* **Centralizar el formateador de porcentaje y decidir el sitio de los cuatro comandos de "
            f"`tools/`** ({N.get('tooling_debt')}). *Razón:* nueve copias de la misma regla, y una batería que no "
            f"mide sobre láminas redibujadas porque cuesta ≈ 50 min por pasada. *Coste:* una tarde de refactor "
            f"con su reejecución de láminas."),
        "layout_checker_gap": (
            f"* **Tapar el hueco del verificador de composición** ({N.get('layout_checker_gap')}) y **cerrar la "
            f"irreproducibilidad de `figE26b`** ({N.get('fige26b')}). *Razón:* las dos curas del primero tocan el "
            f"motor que dibuja las {_m('construcciones_comprobadas')} láminas y pueden encender defectos en "
            f"láminas hoy limpias; el segundo no cambia nada impreso. *Coste:* una ronda propia, con reejecución "
            f"de los nueve módulos de lámina (≈ 50 min) y relectura a tamaño de impresión."),
        "fige26b": None,                     # se nombra en la línea anterior
        "journal_typography": (
            f"* **La pasada de maqueta de la revista** ({N.get('journal_typography')}). *Razón:* es trabajo de la "
            f"versión de envío, no de la de trabajo; la norma de 180 mm a página completa es la que el autor "
            f"pidió para leer. *Coste:* una ronda con redibujo de las {_m('construcciones_comprobadas')} láminas "
            f"y reconstrucción."),
        "white_foot_pages": (
            f"* **Aceptar el papel al pie de las páginas que abren una sección apaisada** "
            f"({N.get('white_foot_pages')}). *Razón:* un cambio de orientación obliga a empezar página y la "
            f"alternativa medida sale peor. *Coste:* cero si se acepta."),
        "panel65": None,                     # va en la lista 1
    }
    for p in abiertos:
        linea = DECIDIR.get(p["key"], f"* **{p.get('es', p['key'])}** ({N[p['key']]}).")
        if linea:
            A(linea)
    A("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=VARIANTS)
    ap.add_argument("--langs", nargs="+", default=list(LANGS), choices=LANGS)
    ap.add_argument("--skip-pdf", action="store_true", help="no convertir a PDF ni generar miniaturas")
    ap.add_argument("--skip-thumbs", action="store_true", help="convertir a PDF pero sin miniaturas")
    ap.add_argument("--no-memo", action="store_true", help="no reescribir memo_es.md")
    ap.add_argument("--supp-dpi", type=int, default=SUPP_DPI_DEFAULT,
                    help="resolución a la que se incrustan las láminas SUPLEMENTARIAS (0 = sin remuestrear); "
                         "las figuras del artículo y los PNG del disco se quedan a 600 ppp")
    args = ap.parse_args(argv)
    supp_dpi = args.supp_dpi or None

    t0 = time.time()
    MANU.mkdir(parents=True, exist_ok=True)
    REVIEW.mkdir(parents=True, exist_ok=True)
    authors, affiliations = load_paper_authors()
    log(f"autores de paper/prose.py: {[a[0] for a in authors]}")
    eq_paths = EQ.ensure_rendered()
    log(f"ecuaciones de la metodología extendida: {len(EQ.NUMBER)} numeradas, "
        f"{sum(len(v) for v in eq_paths.values())} PNG en {EQ.EQ_DIR}")
    # perfil de LibreOffice en una ruta sin espacios (una URI file:// con espacios hace abortar a soffice)
    profile = Path(tempfile.gettempdir()) / "study_lo_profile"
    report = dict(date=dt.datetime.now().isoformat(timespec="seconds"), soffice=SOFFICE if not args.skip_pdf else None,
                  thumbnail_dpi=THUMB_DPI, supp_dpi=supp_dpi, article_dpi=600, documents={})
    for variant in args.variants:
        for lang in args.langs:
            key = f"{variant}_{lang}"
            t1 = time.time()
            pair = build_pair(variant, lang, authors, affiliations, supp_dpi=supp_dpi)
            log(f"{key}: manuscrito {pair['manuscript']['size_mb']} MB, apéndice {pair['supplement']['size_mb']} MB, "
                f"artículo {pair['article']['size_mb']} MB ({time.time() - t1:.0f} s)")
            pl = pair["manuscript"]["plates"]
            bajo_suelo = pl.get("captions_below_floor") or []
            log(f"  láminas a página completa: {pl.get('n')} a {pl.get('width_mm_median')} mm, "
                f"{pl.get('natural')} con la leyenda entera en su página y {pl.get('caption_spill')} con la "
                f"leyenda continuada; leyendas {pl.get('caption_pt_min')}–{pl.get('caption_pt_max')} pt "
                f"(suelo {pl.get('caption_pt_floor')} pt; {len(bajo_suelo)} por debajo, para que la cola no "
                f"se quede sola: {', '.join(bajo_suelo) or 'ninguna'}), "
                f"entradillas {pl.get('lead_pt_min')}–{pl.get('lead_pt_max')} pt en {pl.get('with_lead_in')} "
                f"láminas; {pl.get('plates_opening_own_page')} abren página por sí solas y "
                f"{pl.get('caption_split')} llevan la cola de su leyenda al cuerpo del texto)")
            for part in ("manuscript", "supplement", "article"):
                fuera = pair[part]["plates"].get("captions_below_strand") or []
                if fuera:     # nunca debe ocurrir: 6,5 pt es el último escalón de la escala
                    raise RuntimeError(f"leyendas por debajo de {DB.PLATE_CAP_STRAND_PT} pt en "
                                       f"{Path(pair[part]['path']).name}: {', '.join(fuera)}")
            for part in ("manuscript", "supplement", "article"):
                docx = Path(pair[part]["path"])
                pair[part]["review"] = render_review(docx, not args.skip_pdf,
                                                     not (args.skip_pdf or args.skip_thumbs), profile, lang,
                                                     plates=pair[part]["builder"].get("full_page_plates"))
                rev = pair[part]["review"]
                if rev:
                    lay = rev.get("layout") or {}
                    trozos = [f"{n} {r.get('tail_pages')} colas / {r.get('sparse_pages')} flojas / "
                              f"{r.get('near_empty_pages')} casi vacías de {r.get('pages')}"
                              for n, r in (lay.get("regions") or {}).items() if r]
                    li = lay.get("lead_in") or {}
                    if li:
                        trozos.append(f"entradillas fuera de la página de su lámina: {li['lead_off_plate_page']}"
                                      f"/{li['plates']}")
                    cs = lay.get("caption_spill") or {}
                    if cs:
                        trozos.append(f"leyendas continuadas {cs['spilled']}/{cs['plates']}, "
                                      f"colas SIN rótulo {cs['unmarked_spills']}")
                    trozos.append(f"página más corta {lay.get('min_chars')} caracteres "
                                  f"(palabras unidas por un espacio) / {lay.get('min_chars_nonws')} "
                                  f"sin contar blancos")
                    extra = ("; " + "; ".join(trozos)) if trozos else ""
                    log(f"  {docx.name}: {rev.get('pages')} páginas PDF ({rev.get('pdf_seconds')} s){extra}")
            report["documents"][key] = pair
    if supp_dpi and EMBED_CACHE.is_dir() and set(args.variants) == set(VARIANTS) and set(args.langs) == set(LANGS):
        vivos = {p for p in EMBED_CACHE.glob("*.png") if p.stat().st_mtime >= t0 - 5}
        borradas = prune_embed_cache(vivos)
        log(f"caché de incrustación: {len(vivos)} copias en uso, {borradas} obsoletas borradas")
    report["seconds"] = round(time.time() - t0)
    REPORT_PATH.write_text(json.dumps(report, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    log(f"informe: {REPORT_PATH}")
    if not args.no_memo:
        log(f"memo: {write_memo(report)}")
    # resumen
    print("\ndocumento | páginas | tablas | láminas | refs | palabras (resumen/núcleo/opcional)")
    for key, pair in report["documents"].items():
        for part in ("manuscript", "supplement", "article"):
            d = pair[part]
            wc = d.get("word_counts")
            words = f"{wc['summary']}/{wc['core_body']}/{wc['opt_body']}" if wc else "—"
            print(f"{Path(d['path']).name} | {d.get('review', {}).get('pages', '—')} | {d['builder']['tables']} | "
                  f"{d['builder']['figures']} | {d['builder']['references']} | {words}")
    log(f"terminado en {report['seconds']} s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
