#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""05_education.py — Triangulación educativa: PIE/SINACES (MINEDUC) y JUNAEB EVE 2019–2025.

Produce, bajo `study/outputs/`:
  tidy/pie_series.csv                 una fila por (año, serie) extraída de los tres informes MINEDUC, con archivo, página,
                                      leyenda de tabla/gráfico, definición y nota (incluye la regla explícita para 2022).
  tidy/junaeb_tea_year_level.csv      conteos no ponderados y proporciones ponderadas (EE, IC 95 %) del diagnóstico médico
                                      prolongado de TEA reportado por cuidadores, por año × nivel (× sexo).
  tidy/junaeb_items_dictionary.csv    variables, wording, códigos observados, ponderador y diseño por año × nivel.
  tidy/education_summary_year.csv     resumen anual PIE + JUNAEB (unidades explícitas en los nombres de columna).
  controls/05_education_controls.csv  esperado vs observado para cada control de reproducción.
  education_pdf_text/*.txt            texto de los PDF (pdftotext -layout) usado para la extracción, con fines de trazabilidad.

Principios aplicados (../analysis_plan.md y DATA_REVIEW.md):
  * PIE/SINACES son registros administrativos escolares (subvención, cupos); no son prevalencia.
  * PIE TEA estricto, TEA-Asperger y armonizado (TEA + TEA-Asperger) se mantienen como series separadas.
  * Discrepancia 2022: SINACES imprime 42.945 en PIE, pero su total 45.014 − 2.074 (escuelas especiales) = 42.940 = suma
    Apuntes 60 (28.845 + 14.095). Regla adoptada: la serie armonizada usa la suma de categorías de Apuntes 60 para
    2019–2023 (fuente primaria desagregada, coherente con el total SINACES) y SINACES para 2024–2025; el valor impreso
    42.945 se conserva como serie alternativa etiquetada.
  * JUNAEB: wording del cuestionario/diccionario anual; ponderador `EXP_REG` (2024) / `EXP` (2025); 2023 tiene ítem TEA
    pero no ponderador (solo conteos y proporciones no ponderadas, marcadas); 2019–2022 no tienen categoría TEA en el ítem
    de enfermedad crónica (no estimable); 1º medio 2024 tiene la variable TEA completamente vacía → «no estimable», no cero.
  * Los diccionarios JUNAEB no definen estratos ni conglomerados: el EE ponderado usa linealización de Taylor tratando a cada
    estudiante como unidad independiente (ignora el conglomerado escolar; los archivos 2024–2025 no traen identificador RBD).
  * Las series educativas no dependen de la familia F84/Rett: son idénticas en las variantes `con_rett` y `sin_rett`.

Ejecución: `python3 study/pipeline/05_education.py [--skip-junaeb] [--junaeb-years 2023 2024 2025]`
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import time
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config as CFG  # noqa: E402
import common as C  # noqa: E402

MODULE = "05_education"
SCRIPT = "study/pipeline/05_education.py"
PDF_TEXT_DIR = CFG.OUT / "education_pdf_text"
MINEDUC = CFG.PATHS["mineduc"]
JUNAEB = CFG.PATHS["junaeb"]

PDFS = {
    "apuntes60": "APUNTES_60_2024_tendencia_PIE_2019_2023.pdf",
    "apuntes59": "APUNTES_59_2024_PIE_sexo_2023.pdf",
    "sinaces": "Reporte_Ley_21545_SINACES_2022_2025.pdf",
}

# Valores transcritos de los PDF que se usan solo como controles de la extracción (no como datos).
PUBLISHED_CHECKS = {
    "apuntes60_pie_total": {2019: 385995, 2020: 343059, 2021: 396765, 2022: 438760, 2023: 473006},   # Apuntes 60 p.2 (prosa) y Tablas 2–6
    "sinaces_pie_printed": {2022: 42945, 2023: 63642, 2024: 86475, 2025: 106786},                   # SINACES Tabla 1 p.8
    "sinaces_total_printed": {2022: 45014, 2023: 65940, 2024: 88980, 2025: 109412},
    "sinaces_2022_total_minus_special": 42940,
    "sinaces_2022_discrepancy_cases": 5,
    "apuntes59_tea_strict_female_male": (9461, 38090),                                                # Apuntes 59 Tabla 2 p.5
    "apuntes59_tea_asperger_female_male": (2872, 13219),
    "junaeb_weighted_pct_2024": {"parvularia": 6.74, "basico1": 6.60, "basico5": 4.49},               # DATA_REVIEW.md (preliminar)
    "junaeb_weighted_pct_2025": {"parvularia": 7.69, "basico1": 8.35, "basico5": 5.71, "medio1": 5.03},
}

LEVELS = {
    "parvularia": {"label_es": "Educación parvularia (prekínder/kínder)", "label_en": "Pre-school (pre-kindergarten/kindergarten)",
                   "file_pattern": r"parvularia", "dict_pattern": r"parvularia", "quest_pattern": r"parvularia"},
    "basico1": {"label_es": "1º básico", "label_en": "Grade 1 (1º básico)",
                "file_pattern": r"(?<!\d)1(?:ero|ro|o)?[_ ]?basico", "dict_pattern": r"(?:(?<!\d)1|primero)\s*basico", "quest_pattern": r"(?<!\d)1(?:ro|o)?\s*basico"},
    "basico5": {"label_es": "5º básico", "label_en": "Grade 5 (5º básico)",
                "file_pattern": r"(?<!\d)5(?:to|o)?[_ ]?basico", "dict_pattern": r"(?:(?<!\d)5|quinto)\s*basico", "quest_pattern": r"(?<!\d)5(?:to|o)?\s*basico"},
    "medio1": {"label_es": "1º medio", "label_en": "Grade 9 (1º medio)",
               "file_pattern": r"(?<!\d)1(?:ero|ro|o)?[_ ]?medio", "dict_pattern": r"(?:(?<!\d)1|primero)\s*medio", "quest_pattern": r"(?<!\d)1(?:ro|o)?\s*medio"},
}
LEVEL_ORDER = list(LEVELS)

# Variables por año × nivel (nombres verificados en las cabeceras; la búsqueda es insensible a mayúsculas).
_LEGACY = {"parvularia": dict(filter="diag_enfermedad_cron", tea=None, weight=None, cat_regex=r"^diag(?:nostico)?_"),
           "basico1": dict(filter="diag_enfermed_cronic", tea=None, weight=None, cat_regex=r"^diag(?:nostico)?_"),
           "basico5": dict(filter="diag_enfermedad_cron", tea=None, weight=None, cat_regex=r"^diag(?:nostico)?_"),
           "medio1": dict(filter="diag_enfermedcronica", tea=None, weight=None, cat_regex=r"^diag(?:nostico)?_")}
JUNAEB_VARS = {
    2019: _LEGACY, 2020: _LEGACY, 2021: _LEGACY, 2022: _LEGACY,
    2023: {"parvularia": dict(filter="DIAGNOSTICO_MEDICO", tea="T_E_A", weight=None, cat_block_until=r"CARIES"),
           "basico1": dict(filter="DIAGNOSTICO_ENFERMEDAD", tea="TRASTORNO_ESPECTRO_AUTISTA", weight=None, cat_block_until=r"CARIES"),
           "basico5": dict(filter="DIAGNOSTICO_MEDICO", tea="DIAGNOSTICO_TEA", weight=None, cat_block_until=r"CARIES"),
           "medio1": dict(filter="DIAGNOSTICO_MEDICO_CONDICION_SALUD", tea="TRASTORNO_ESPECTRO_AUTISTA", weight=None, cat_block_until=r"CARIES")},
    2024: {"parvularia": dict(filter="C29", tea="C30_11", weight="EXP_REG", cat_regex=r"^C30_\d+$"),
           "basico1": dict(filter="D14", tea="D15_11", weight="EXP_REG", cat_regex=r"^D15_\d+$"),
           "basico5": dict(filter="D14", tea="D15_11", weight="EXP_REG", cat_regex=r"^D15_\d+$"),
           "medio1": dict(filter="D14", tea="D15_11", weight="EXP_REG", cat_regex=r"^D15_\d+$")},
    2025: {lvl: dict(filter="D13", tea="D14_11", weight="EXP", cat_regex=r"^D14_\d+$") for lvl in LEVEL_ORDER},
}
YEARS_JUNAEB = sorted(JUNAEB_VARS)

YES = {"sí", "si", "1", "1.0", "y", "yes", "s"}
NO = {"no", "2", "2.0", "n"}
DONT_KNOW = {"no sabe", "88", "88.0", "3", "3.0", "9", "ns", "nosabe", "no sabe / no desea responder"}
TEA_POSITIVE = {"sí", "si", "1", "1.0", "y", "x", "seleccionado", "true"}
TEA_NEGATIVE = {"0", "0.0", "no", "2", "2.0", "no seleccionado", "false"}
SEX_MAP = {"m": "male", "masculino": "male", "hombre": "male", "1": "male",
           "f": "female", "femenino": "female", "mujer": "female", "2": "female"}
SMALL_CELL = 5


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------
def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


def norm_name(s: str) -> str:
    """Minúsculas sin acentos ni ordinales (º → o) para emparejar nombres de archivo."""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    return s.lower()


def to_int(tok: str) -> int:
    return int(tok.replace(".", ""))


def to_pct(tok: str) -> float:
    return float(tok.replace(".", "").replace(",", "."))


INT_TOKEN = re.compile(r"(?<![\d.,])(\d{1,3}(?:\.\d{3})+|\d+)(?![\d.,%])")
PCT_TOKEN = re.compile(r"(\d+(?:,\d+)?)\s*%")


def ints_after_label(page: str, label_regex: str, n: int) -> tuple[list[int], str]:
    """Primera línea de la página que comienza con la etiqueta; devuelve los primeros `n` enteros que la siguen y la línea."""
    pat = re.compile(r"^\s*" + label_regex + r"(?![\w\-])(.*)$")
    for line in page.splitlines():
        m = pat.match(line)
        if m:
            toks = INT_TOKEN.findall(m.group(1))
            if len(toks) >= n:
                return [to_int(t) for t in toks[:n]], line.strip()
    raise LookupError(f"No se encontró la fila '{label_regex}' con {n} enteros")


def find_page(pages: list[str], needle: str) -> tuple[int, str]:
    for i, p in enumerate(pages, 1):
        if needle in p:
            return i, p
    raise LookupError(f"No se encontró la página con '{needle}'")


def caption_line(page: str, prefix: str) -> str:
    for line in page.splitlines():
        if prefix in line:
            return re.sub(r"\s+", " ", line.strip())
    return prefix


def pdf_text(pdf: Path, layout: bool = True) -> str:
    if shutil.which("pdftotext") is None:
        raise RuntimeError("pdftotext (poppler) no está disponible en PATH; es necesario para extraer los informes MINEDUC.")
    PDF_TEXT_DIR.mkdir(parents=True, exist_ok=True)
    out = PDF_TEXT_DIR / f"{pdf.stem}{'_layout' if layout else '_raw'}.txt"
    tmp = out.with_suffix(".tmp")
    cmd = ["pdftotext"] + (["-layout"] if layout else []) + [str(pdf), str(tmp)]
    subprocess.run(cmd, check=True, stderr=subprocess.DEVNULL)
    os.replace(tmp, out)
    return out.read_text(encoding="utf-8", errors="replace")


def detect_encoding(path: Path, nbytes: int = 4_000_000) -> str:
    with open(path, "rb") as fh:
        raw = fh.read(nbytes)
    try:
        raw.decode("utf-8")
        return "utf-8"
    except UnicodeDecodeError:
        return "cp1252"


def status_of(expected, observed, tol_rel: float = 0.005, tol_abs: float = 0.0) -> tuple[str, float, float]:
    if isinstance(expected, str) or isinstance(observed, str):
        ok = str(expected) == str(observed)
        return ("ok" if ok else "differs"), np.nan, np.nan
    if observed is None or (isinstance(observed, float) and np.isnan(observed)):
        return "differs", np.nan, np.nan
    diff = float(observed) - float(expected)
    rel = diff / float(expected) if float(expected) != 0 else (0.0 if diff == 0 else np.inf)
    ok = diff == 0 or abs(diff) <= tol_abs or abs(rel) <= tol_rel
    return ("ok" if ok else "differs"), diff, rel


class Controls:
    def __init__(self):
        self.rows = []

    def add(self, name, key, expected, observed, note="", tol_rel=0.005, tol_abs=0.0):
        st, diff, rel = status_of(expected, observed, tol_rel, tol_abs)
        self.rows.append(dict(name=name, key=str(key), expected=expected, observed=observed, abs_diff=diff, rel_diff=rel, status=st, note=note))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff", "status", "note"])


# ---------------------------------------------------------------------------
# 1. PIE / SINACES
# ---------------------------------------------------------------------------
def extract_pie(ctl: Controls) -> pd.DataFrame:
    rows = []
    sha = {}
    texts = {}
    for key, name in PDFS.items():
        pdf = MINEDUC / name
        if not pdf.is_file():
            raise FileNotFoundError(pdf)
        sha[key] = C.sha256_file(pdf)
        t0 = time.perf_counter()
        texts[key] = pdf_text(pdf, layout=True).split("\f")
        log(f"pdftotext -layout {name}: {len(texts[key])} páginas, {time.perf_counter() - t0:.1f} s")

    def add(year, series, value, unit, key, page, caption, definition, note="", derived=False):
        rows.append(dict(year=year, series=series, value=value, unit=unit, source_file=PDFS[key], source_sha256=sha[key], pdf_page=page,
                         table_or_figure_caption=caption, definition=definition, note=note, derived=derived, script=SCRIPT))

    # --- Apuntes 60, Tabla 6 (p. 11): tipo de integración 2019–2023 ----------------------------------------------------
    pg, page = find_page(texts["apuntes60"], "Tabla 6. Cantidad de estudiantes en el PIE según tipo de integración")
    pg_t6 = pg
    cap6 = caption_line(page, "Tabla 6.")
    yrs = [int(y) for y in re.search(r"2019\s+2020\s+2021\s+2022\s+2023", page).group(0).split()]
    strict, l1 = ints_after_label(page, r"Trastorno del Espectro Autista \(P\)", 5)
    asperger, l2 = ints_after_label(page, r"Trastorno del Espectro Autista - Asperger \(P\)", 5)
    total6, l3 = ints_after_label(page, r"Total", 5)
    for y, v in zip(yrs, strict):
        add(y, "pie_tea_strict", v, "students", "apuntes60", pg, cap6,
            "Estudiantes matriculados en PIE con NEE permanente 'Trastorno del Espectro Autista (P)' (establecimientos funcionando)",
            "Registro administrativo para subvención; no incluye a todo el estudiantado autista (nota SINACES p.8)")
    for y, v in zip(yrs, asperger):
        add(y, "pie_tea_asperger", v, "students", "apuntes60", pg, cap6,
            "Estudiantes matriculados en PIE con NEE permanente 'Trastorno del Espectro Autista - Asperger (P)'",
            "Categoría histórica mantenida por MINEDUC pese a DSM-5/CIE-11 (nota 2, p.11)")
    for y, v in zip(yrs, total6):
        add(y, "pie_total_enrolment", v, "students", "apuntes60", pg, cap6, "Total de estudiantes integrados/as en el PIE (todas las NEE)",
            "Denominador para expresar TEA como proporción de la matrícula PIE; coincide con Tablas 2–5 y prosa p.2")
    for y, s, a in zip(yrs, strict, asperger):
        add(y, "pie_harmonised_apuntes60", s + a, "students", "apuntes60", pg, cap6,
            "Suma TEA (P) + TEA-Asperger (P) calculada a partir de Tabla 6", "Serie armonizada derivada; 2022 = 42.940", derived=True)
    for y, s, a, t in zip(yrs, strict, asperger, total6):
        add(y, "pie_tea_strict_share_of_pie_pct", round(100 * s / t, 3), "percent of PIE students", "apuntes60", pg, cap6,
            "100 × TEA (P) / total PIE", "Calculado; comparar con Gráfico 3 p.10", derived=True)
        add(y, "pie_harmonised_share_of_pie_pct", round(100 * (s + a) / t, 3), "percent of PIE students", "apuntes60", pg, cap6,
            "100 × (TEA + TEA-Asperger) / total PIE", "Calculado", derived=True)
    for y, v in zip(yrs, strict):
        ctl.add("pie_tea_strict", y, CFG.CONTROLS["pie_tea_strict"][y], v, f"Apuntes 60 Tabla 6 p.{pg}: {re.sub(r'\s+', ' ', l1)[:80]}")
    for y, v in zip(yrs, asperger):
        ctl.add("pie_tea_asperger", y, CFG.CONTROLS["pie_tea_asperger"][y], v, f"Apuntes 60 Tabla 6 p.{pg}")
    for y, v in zip(yrs, total6):
        ctl.add("pie_total_enrolment_apuntes60", y, PUBLISHED_CHECKS["apuntes60_pie_total"][y], v, "Total Tabla 6 vs prosa p.2/Tablas 2–5 (transcrito)")

    # --- Apuntes 60, Gráfico 3 (p. 10): porcentajes publicados por tipo de integración (control de la extracción) ------
    try:
        pg3, page3 = find_page(texts["apuntes60"], "Gráfico 3. Tipo de integración")
        cap3 = caption_line(page3, "Gráfico 3.")
        legend = re.search(r"2023\s+2022\s+2021\s+2020\s+2019", page3)
        lines = page3.splitlines()
        for label, series in [("Trastorno del Espectro Autista (P)", "pie_tea_strict_share_of_pie_pct"),
                              ("Trastorno del Espectro Autista - Asperger (P)", "pie_tea_asperger_share_of_pie_pct")]:
            idx = [i for i, ln in enumerate(lines) if label in ln and (("Asperger" in ln) == ("Asperger" in label))]
            if not idx or legend is None:
                log(f"Gráfico 3: etiqueta '{label}' o leyenda de años no localizada; se omite")
                continue
            i = idx[0]
            block = lines[i - 2:i + 3]
            pcts = [PCT_TOKEN.search(ln) for ln in block]
            if len(block) != 5 or any(p is None for p in pcts):
                log(f"Gráfico 3: no se pudo leer el bloque de '{label}'; se omite (no se inventa)")
                continue
            for y, m in zip([2023, 2022, 2021, 2020, 2019], pcts):
                add(y, series + "_published", to_pct(m.group(1)), "percent of PIE students", "apuntes60", pg3, cap3,
                    f"Porcentaje publicado de '{label}' sobre el total PIE", "Valor redondeado a 0,1 pp en el gráfico")
                if series == "pie_tea_strict_share_of_pie_pct":
                    comp = 100 * strict[yrs.index(y)] / total6[yrs.index(y)]
                else:
                    comp = 100 * asperger[yrs.index(y)] / total6[yrs.index(y)]
                ctl.add(series + "_vs_published", y, to_pct(m.group(1)), round(comp, 3), "Publicado (Gráfico 3, redondeado a 0,1 pp) vs calculado Tabla 6", tol_abs=0.05)
    except LookupError as exc:
        log(f"Gráfico 3 no localizado: {exc}")

    # --- Apuntes 59, Tabla 2 (p. 5): tipo de integración × género 2023 ------------------------------------------------
    pg, page = find_page(texts["apuntes59"], "Tabla 2. Cantidad de estudiantes en el PIE según tipo de integración y género")
    cap = caption_line(page, "Tabla 2.")
    assert re.search(r"Femenino\s+Masculino", page), "Apuntes 59 Tabla 2: orden de columnas no verificado"
    rx = r"^\s*{label}\s+(\d{{1,3}}(?:\.\d{{3}})*)\s+(\d+(?:,\d+)?)%\s+(\d{{1,3}}(?:\.\d{{3}})*)\s+(\d+(?:,\d+)?)%"
    sex_rows = {}
    for label, series in [(r"Trastorno del Espectro Autista \(P\)", "pie_tea_strict"), (r"Trastorno del Espectro Autista - Asperger \(P\)", "pie_tea_asperger"), (r"Total", "pie_total_enrolment")]:
        m = None
        for line in page.splitlines():
            m = re.match(rx.format(label=label), line)
            if m:
                break
        if m is None:
            raise LookupError(f"Apuntes 59 Tabla 2: fila '{label}' no encontrada")
        f, fp, mm, mp = to_int(m.group(1)), to_pct(m.group(2)), to_int(m.group(3)), to_pct(m.group(4))
        sex_rows[series] = (f, mm)
        add(2023, series + "_female", f, "students", "apuntes59", pg, cap, f"{series} 2023, género femenino", f"Publicado {fp}% del tipo de integración; solo estudiantes con información de género")
        add(2023, series + "_male", mm, "students", "apuntes59", pg, cap, f"{series} 2023, género masculino", f"Publicado {mp}% del tipo de integración; solo estudiantes con información de género")
        add(2023, series + "_female_share_pct", round(100 * f / (f + mm), 2), "percent", "apuntes59", pg, cap, "100 × femenino / (femenino + masculino)", f"Publicado {fp}%", derived=True)
    ctl.add("apuntes59_tea_strict_sex_sum_equals_apuntes60", 2023, CFG.CONTROLS["pie_tea_strict"][2023], sum(sex_rows["pie_tea_strict"]), "Femenino + masculino Tabla 2 Apuntes 59 vs Tabla 6 Apuntes 60")
    ctl.add("apuntes59_tea_asperger_sex_sum_equals_apuntes60", 2023, CFG.CONTROLS["pie_tea_asperger"][2023], sum(sex_rows["pie_tea_asperger"]), "Femenino + masculino Tabla 2 Apuntes 59 vs Tabla 6 Apuntes 60")
    ctl.add("apuntes59_tea_strict_female", 2023, PUBLISHED_CHECKS["apuntes59_tea_strict_female_male"][0], sex_rows["pie_tea_strict"][0], "Transcrito Apuntes 59 p.5")
    ctl.add("apuntes59_tea_strict_male", 2023, PUBLISHED_CHECKS["apuntes59_tea_strict_female_male"][1], sex_rows["pie_tea_strict"][1], "Transcrito Apuntes 59 p.5")
    m = re.search(r"representa el (\d+,\d)% de la matrícula\s+total de estudiantes en establecimientos con aporte estatal", " ".join(texts["apuntes59"][0].split()))
    if m:
        add(2023, "pie_share_of_state_funded_enrolment_published_pct", to_pct(m.group(1)), "percent of enrolment in state-funded establishments", "apuntes59", 1,
            "Principales hallazgos (p.1)", "Porcentaje publicado: total PIE / matrícula total en establecimientos con aporte estatal", "Denominador no publicado en el informe; solo valor redondeado")

    # --- SINACES, Tabla 1 (p. 8) y Tabla 2 (p. 9) -----------------------------------------------------------------------
    pg, page = find_page(texts["sinaces"], "Tabla 1. Estudiantes autistas en el sistema educativo")
    cap1 = caption_line(page, "Tabla 1.")
    yrs_s = [int(y) for y in re.search(r"Año\s+(2022)\s+(2023)\s+(2024)\s+(2025)", page).groups()]
    pie_s, _ = ints_after_label(page, r"PIE", 4)
    tot_s, _ = ints_after_label(page, r"Total", 4)
    lines = page.splitlines()
    i0 = next(i for i, ln in enumerate(lines) if "Escuela Especial de" in ln)
    i1 = next(i for i, ln in enumerate(lines) if i > i0 and ln.strip().startswith("Autismo"))
    special = None
    for ln in lines[i0 + 1:i1]:
        toks = INT_TOKEN.findall(ln)
        if len(toks) >= 4:
            special = [to_int(t) for t in toks[:4]]
            break
    if special is None:
        raise LookupError("SINACES Tabla 1: fila 'Escuela Especial de Autismo' no encontrada")
    for y, v in zip(yrs_s, pie_s):
        add(y, "pie_harmonised_sinaces", v, "students", "sinaces", pg, cap1, "Estudiantes autistas en PIE (TEA + TEA-Asperger, según Centro de Estudios MINEDUC)",
            "2022 impreso 42.945; 45.014 − 2.074 = 42.940 (= Apuntes 60). Ver regla 2022 en la serie pie_harmonised")
    for y, v in zip(yrs_s, special):
        add(y, "special_schools_autism", v, "students", "sinaces", pg, cap1, "Estudiantes matriculados en Escuelas Especiales de Autismo",
            "Excluye escuelas especiales de otro tipo y establecimientos regulares sin PIE (nota 3, p.8)")
    for y, v in zip(yrs_s, tot_s):
        add(y, "sinaces_total_autistic_students", v, "students", "sinaces", pg, cap1, "Total = Escuela Especial de Autismo + PIE", "")
        add(y, "sinaces_total_minus_special", v - special[yrs_s.index(y)], "students", "sinaces", pg, cap1, "Total − Escuela Especial de Autismo (derivado)",
            "2022: 42.940 ≠ 42.945 impreso en PIE (discrepancia de 5 casos)", derived=True)
    for y, v in zip(yrs_s, pie_s):
        ctl.add("sinaces_pie_printed", y, PUBLISHED_CHECKS["sinaces_pie_printed"][y], v, f"SINACES Tabla 1 p.{pg}")
        ctl.add("sinaces_total_printed", y, PUBLISHED_CHECKS["sinaces_total_printed"][y], tot_s[yrs_s.index(y)], f"SINACES Tabla 1 p.{pg}")
    ctl.add("sinaces_2022_total_minus_special", 2022, PUBLISHED_CHECKS["sinaces_2022_total_minus_special"], tot_s[0] - special[0], "45.014 − 2.074; coincide con Apuntes 60 (28.845 + 14.095)")
    ctl.add("sinaces_2022_discrepancy_cases", 2022, PUBLISHED_CHECKS["sinaces_2022_discrepancy_cases"], pie_s[0] - (tot_s[0] - special[0]), "PIE impreso − (Total − especiales)")
    ctl.add("sinaces_2023_equals_apuntes60_sum", 2023, strict[yrs.index(2023)] + asperger[yrs.index(2023)], pie_s[yrs_s.index(2023)], "63.642 en ambas fuentes")
    for y, v in zip(yrs_s, special):
        if y in CFG.CONTROLS["pie_special_schools"]:
            ctl.add("pie_special_schools", y, CFG.CONTROLS["pie_special_schools"][y], v, f"SINACES Tabla 1 p.{pg}")

    pg2, page2 = find_page(texts["sinaces"], "Tabla 2. Estudiantes autistas postulados al PIE")
    cap2 = caption_line(page2, "Tabla 2.")
    rx2 = re.compile(r"^\s*(202\d)\s+(\d{1,3}(?:\.\d{3})*)\s+(\d{1,3}(?:\.\d{3})*)\s+(\d+(?:,\d+)?)%\s+(\d{1,3}(?:\.\d{3})*)\s+(\d{1,3}(?:\.\d{3})*)\s*$")
    t2 = {}
    for ln in page2.splitlines():
        m = rx2.match(ln)
        if m:
            t2[int(m.group(1))] = dict(applicants=to_int(m.group(2)), tea=to_int(m.group(3)), pct=to_pct(m.group(4)), regular=to_int(m.group(5)), exceptional=to_int(m.group(6)))
    if sorted(t2) != yrs_s:
        raise LookupError(f"SINACES Tabla 2: años leídos {sorted(t2)}")
    for y, d in sorted(t2.items()):
        add(y, "pie_total_applicants_sinaces", d["applicants"], "students", "sinaces", pg2, cap2, "Total de postulantes al PIE (todas las NEE)",
            "Definición 'postulantes' (SINACES) ≠ 'matriculados/integrados' (Apuntes 60); 2022: 438.783 vs 438.760")
        add(y, "pie_tea_applicants_sinaces", d["tea"], "students", "sinaces", pg2, cap2, "Postulantes autistas al PIE", "Coincide con la fila PIE de Tabla 1 (incluye 42.945 en 2022)")
        add(y, "pie_tea_share_of_applicants_published_pct", d["pct"], "percent of PIE applicants", "sinaces", pg2, cap2, "% publicado: postulantes autistas / total postulantes", "")
        add(y, "pie_tea_share_of_applicants_pct", round(100 * d["tea"] / d["applicants"], 3), "percent of PIE applicants", "sinaces", pg2, cap2, "100 × postulantes autistas / total postulantes (calculado)", "", derived=True)
        add(y, "pie_tea_regular_entry", d["regular"], "students", "sinaces", pg2, cap2, "Postulantes autistas por ingreso regular (cupos Decreto 170)", "")
        add(y, "pie_tea_exceptional_entry", d["exceptional"], "students", "sinaces", pg2, cap2, "Postulantes autistas por ingreso excepcional (autorización Seremi)", "Indicador de presión sobre cupos, no prevalencia")
        ctl.add("sinaces_tabla2_regular_plus_exceptional", y, d["tea"], d["regular"] + d["exceptional"], "Consistencia interna Tabla 2")
        ctl.add("sinaces_tabla2_pct_vs_computed", y, d["pct"], round(100 * d["tea"] / d["applicants"], 3), "Publicado (0,1 pp) vs calculado", tol_abs=0.05)

    # --- Serie armonizada adoptada 2019–2025 con la regla 2022 ----------------------------------------------------------
    rule = ("Regla 2022: se adopta la suma de categorías de Apuntes 60 (28.845 + 14.095 = 42.940), fuente primaria desagregada y coherente con "
            "SINACES Tabla 1 (45.014 − 2.074 = 42.940); el 42.945 impreso por SINACES se conserva en pie_harmonised_sinaces. Diferencia: 5 estudiantes (0,01 %).")
    for y, s, a in zip(yrs, strict, asperger):
        add(y, "pie_harmonised", s + a, "students", "apuntes60", pg_t6, cap6,
            "TEA (P) + TEA-Asperger (P), Apuntes 60 Tabla 6", rule if y == 2022 else "2019–2023 desde Apuntes 60", derived=True)
    for y, v in zip(yrs_s, pie_s):
        if y >= 2024:
            add(y, "pie_harmonised", v, "students", "sinaces", pg, cap1, "Estudiantes autistas en PIE (SINACES Tabla 1; TEA + TEA-Asperger)", "2024–2025 solo disponibles en SINACES", derived=False)
    for y in CFG.CONTROLS["pie_harmonised"]:
        obs = next(r["value"] for r in rows if r["series"] == "pie_harmonised" and r["year"] == y)
        ctl.add("pie_harmonised", y, CFG.CONTROLS["pie_harmonised"][y], obs, "Serie adoptada (regla 2022 = Apuntes 60)")

    df = pd.DataFrame(rows)
    df["pdf_page_note"] = "pdf_page = página física (1-based) del PDF; coincide con la paginación impresa en los tres informes"
    df = df.sort_values(["series", "year"]).reset_index(drop=True)
    return df


# ---------------------------------------------------------------------------
# 2. JUNAEB EVE
# ---------------------------------------------------------------------------
def junaeb_files() -> dict[tuple[int, str], Path]:
    out = {}
    for year in YEARS_JUNAEB:
        d = JUNAEB / "microdata" / str(year)
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.csv")):
            nm = norm_name(f.name)
            for lvl, spec in LEVELS.items():
                if re.search(spec["file_pattern"], nm):
                    if (year, lvl) in out:
                        raise ValueError(f"Dos archivos para {year}/{lvl}: {out[(year, lvl)].name}, {f.name}")
                    out[(year, lvl)] = f
    return out


def load_dictionary(year: int, level: str) -> tuple[dict, dict, str]:
    """Devuelve (etiquetas {VAR: label}, etiquetas de valor {VAR: {code: label}}, nombre de archivo) o vacíos."""
    d = JUNAEB / "metadata" / "Diccionarios" / str(year)
    if not d.is_dir():
        return {}, {}, ""
    cands = [f for f in d.glob("*.xlsx") if re.search(LEVELS[level]["dict_pattern"], norm_name(f.name))]
    if not cands:
        return {}, {}, ""
    f = cands[0]
    labels, values = {}, {}
    xl = pd.ExcelFile(f)
    strip = re.compile(r"^[A-Z]_(?:\d+_)+(?=[A-Z])")
    if year == 2021:
        desc = xl.parse("describe", header=None, dtype=str)
        for _, r in desc.iterrows():
            var = str(r[0]).strip() if pd.notna(r[0]) else ""
            if not var or var.lower().startswith("variable"):
                continue
            labels[strip.sub("", var).upper()] = str(r[3]).strip() if pd.notna(r[3]) else ""
        ll = xl.parse("label list", header=None, dtype=str)
        cur = None
        for _, r in ll.iterrows():
            if pd.notna(r[0]) and str(r[0]).strip() and not str(r[0]).strip().lower().startswith("variable"):
                cur = strip.sub("", str(r[0]).strip()).upper()
            if cur and pd.notna(r[1]):
                m = re.match(r"^\s*(\S+)\s+(.*)$", str(r[1]))
                if m:
                    values.setdefault(cur, {})[m.group(1)] = m.group(2).strip()
    else:
        sh = xl.parse(xl.sheet_names[0], header=None, dtype=str)
        cur = None
        for _, r in sh.iterrows():
            var = str(r[0]).strip() if pd.notna(r[0]) else ""
            if var and not var.lower().startswith("variable"):
                cur = var.upper()
                labels[cur] = str(r[1]).strip() if pd.notna(r[1]) else ""
            if year == 2025 and cur and sh.shape[1] >= 5 and pd.notna(r[3]):
                values.setdefault(cur, {})[str(r[3]).strip()] = str(r[4]).strip() if pd.notna(r[4]) else ""
    return labels, values, f.name


def questionnaire_text(year: int, level: str) -> tuple[str, str]:
    d = JUNAEB / "metadata" / "Cuestionarios" / str(year)
    if not d.is_dir():
        return "", ""
    cands = [f for f in d.glob("*.pdf") if re.search(LEVELS[level]["quest_pattern"], norm_name(f.name))]
    if not cands:
        return "", ""
    f = cands[0]
    txt = subprocess.run(["pdftotext", str(f), "-"], capture_output=True, text=True, check=True, errors="replace").stdout
    return re.sub(r"\s+", " ", txt), f.name


FILTER_RX = re.compile(r"((?:El/la|El /la)\s*(?:estudiante|niño/a|niño /a|niño/niña)\s*,?\s*¿ha sido diagnosticado/a por un médico con alguna [^?]{0,260}?tiempo\s*\?)", re.I)
TEA_LABEL_RX = re.compile(r"(Trastornos?\s+del\s+espec\w*\s+autista(?:\s*\(TEA\))?)", re.I)
STEM_RX = re.compile(r"(1[34]\.\s*(?:Si respondió S[íi] en la pregunta anterior[^.]*\.|Marque con una equis \(X\) la alternativa que corresponda\.|Especifique todas las alternativas que correspondan[.:]))", re.I)


_MANIFEST_SHA: dict[str, str] | None = None


def manifest_sha(path: Path) -> str:
    """SHA-256 registrado en el manifiesto de descarga (evita rehacer el hash de 9,6 GB); vacío si no está."""
    global _MANIFEST_SHA
    if _MANIFEST_SHA is None:
        _MANIFEST_SHA = {}
        mf = CFG.PATHS["download_manifest"]
        if mf.is_file():
            m = pd.read_csv(mf, dtype=str)
            if {"relative_path", "sha256"} <= set(m.columns):
                _MANIFEST_SHA = dict(zip(m.relative_path, m.sha256))
    try:
        rel = str(path.relative_to(CFG.AUTISM_ROOT))
    except ValueError:
        rel = path.name
    return _MANIFEST_SHA.get(rel, "")


def resolve(header: list[str], name: str | None) -> str | None:
    if name is None:
        return None
    up = {h.upper(): h for h in header}
    return up.get(name.upper())


def category_columns(spec: dict, header: list[str], filter_col: str) -> list[str]:
    if "cat_regex" in spec:
        rx = re.compile(spec["cat_regex"], re.I)
        return [h for h in header if rx.search(h) and h != filter_col]
    i0 = header.index(filter_col) + 1
    out = []
    for h in header[i0:]:
        if re.search(spec["cat_block_until"], h, re.I):
            break
        out.append(h)
    return out


#: Estados del dato tal como se imprimen al lector. «<NA>» es el marcador de pandas, no un código del
#: cuestionario: impreso tal cual en la tabla del diccionario JUNAEB se lee como un valor del archivo.
MISSING_LABEL = "sin dato"
BLANK_LABEL = "en blanco"


def codes_string(s: pd.Series, top: int = 6) -> str:
    """Códigos observados de una variable con su frecuencia, con los estados del dato con nombre."""
    vc = s.fillna(MISSING_LABEL).replace(r"^\s*$", BLANK_LABEL, regex=True).value_counts(dropna=False)
    return "; ".join(f"{k}={v}" for k, v in vc.head(top).items())


def weighted_block(df: pd.DataFrame, domain: pd.Series | None) -> dict:
    r = C.survey_proportion(df, "tea01", "w", None, None, domain=domain)
    return dict(proportion_weighted_pct=100 * r["proportion"], se_pct=100 * r["se"], lo_pct=100 * r["lo"], hi_pct=100 * r["hi"],
                weighted_tea_total=r["weighted_total"], weighted_population=r["weighted_population"], n_domain=r["n_domain"], n_cases=r["n_cases"])


def process_junaeb(year: int, level: str, path: Path, spec: dict) -> tuple[list[dict], list[dict]]:
    t0 = time.perf_counter()
    enc = detect_encoding(path)
    header = pd.read_csv(path, sep=";", nrows=0, encoding=enc, encoding_errors="replace").columns.tolist()
    fcol, tcol, wcol = resolve(header, spec["filter"]), resolve(header, spec["tea"]), resolve(header, spec["weight"])
    scol, gcol = resolve(header, "SEXO"), resolve(header, "DS_GRADO")
    if fcol is None:
        raise KeyError(f"{path.name}: falta la variable filtro {spec['filter']}")
    if spec["tea"] and tcol is None:
        raise KeyError(f"{path.name}: falta la variable TEA {spec['tea']}")
    if spec["weight"] and wcol is None:
        raise KeyError(f"{path.name}: falta el ponderador {spec['weight']}")
    cats = category_columns(spec, header, fcol)
    usecols = [c for c in [fcol, tcol, wcol, scol, gcol] if c] + [c for c in cats if c not in (fcol, tcol)]
    df = pd.read_csv(path, sep=";", usecols=usecols, dtype=str, encoding=enc, encoding_errors="replace")
    n_rows = len(df)

    labels, vlabels, dict_file = load_dictionary(year, level)
    qtext, quest_file = questionnaire_text(year, level)
    m = FILTER_RX.search(qtext)
    filter_wording = m.group(1) if m else labels.get(fcol.upper(), fcol)
    stem = STEM_RX.search(qtext)
    tea_label = TEA_LABEL_RX.search(qtext)
    if tcol:
        tea_wording = labels.get(tcol.upper()) or " ".join(x for x in [tea_label.group(1) if tea_label else f"[{tcol}]", stem.group(1) if stem else ""] if x)
    else:
        tea_wording = "ABSENT: el ítem de enfermedad/condición crónica no incluye una categoría de trastorno del espectro autista"

    f = df[fcol].fillna("").astype(str).str.strip().str.lower()
    f_yes, f_no, f_dk, f_blank = f.isin(YES), f.isin(NO), f.isin(DONT_KNOW), f.eq("")
    f_unmapped = sorted(set(f[~(f_yes | f_no | f_dk | f_blank)].unique()))
    sex = df[scol].fillna("").astype(str).str.strip().str.lower().map(SEX_MAP).fillna("other") if scol else pd.Series("unknown", index=df.index)
    grades = codes_string(df[gcol], 6) if gcol else ""

    items = []
    common_item = dict(year=year, level=level, source_file=path.name, encoding=enc, dictionary_file=dict_file, questionnaire_file=quest_file)
    items.append(dict(common_item, variable=fcol, role="filter_prolonged_medical_diagnosis", wording=filter_wording, value_codes_observed=codes_string(df[fcol]),
                      value_labels=str(vlabels.get(fcol.upper(), "")), note="Pregunta filtro; las categorías solo se marcan si la respuesta es Sí"))
    if tcol:
        items.append(dict(common_item, variable=tcol, role="tea_category", wording=tea_wording, value_codes_observed=codes_string(df[tcol]), value_labels=str(vlabels.get(tcol.upper(), "")),
                          note="Positivo = " + "/".join(sorted(TEA_POSITIVE & set(df[tcol].fillna("").str.strip().str.lower().unique())) or ["(ninguno observado)"])))
    else:
        items.append(dict(common_item, variable="ABSENT", role="tea_category", wording=tea_wording, value_codes_observed="", value_labels="",
                          note="Sin categoría TEA en " + str(year) + "; categorías disponibles: " + ", ".join(cats)))
    items.append(dict(common_item, variable=wcol or "ABSENT", role="expansion_weight", wording=labels.get(wcol.upper(), "") if wcol else "No se publica factor de expansión para este año",
                      value_codes_observed=(f"min={pd.to_numeric(df[wcol].str.replace(',', '.', regex=False), errors='coerce').min():.4f}; max={pd.to_numeric(df[wcol].str.replace(',', '.', regex=False), errors='coerce').max():.4f}" if wcol else ""),
                      value_labels="", note="Diccionario sin variables de estrato ni conglomerado; sin identificador de establecimiento (RBD) en 2024–2025" if wcol else ""))
    if scol:
        items.append(dict(common_item, variable=scol, role="sex", wording=labels.get(scol.upper(), "Sexo del estudiante"), value_codes_observed=codes_string(df[scol]), value_labels=str(vlabels.get(scol.upper(), "")), note=""))
    if gcol:
        items.append(dict(common_item, variable=gcol, role="grade", wording=labels.get(gcol.upper(), "Grado"), value_codes_observed=grades, value_labels="", note="Grados presentes en el archivo"))
    for c in cats:
        if c == tcol:
            continue
        items.append(dict(common_item, variable=c, role="other_category", wording=labels.get(c.upper(), c), value_codes_observed=codes_string(df[c], 4), value_labels=str(vlabels.get(c.upper(), "")), note=""))

    base = dict(year=year, level=level, level_label_es=LEVELS[level]["label_es"], level_label_en=LEVELS[level]["label_en"], grades_in_file=grades,
                source_file=str(path.relative_to(JUNAEB)), file_size_bytes=path.stat().st_size, file_sha256_manifest=manifest_sha(path), encoding=enc,
                item_variable=tcol or "ABSENT", item_wording=tea_wording, filter_variable=fcol, filter_wording=filter_wording, weight_variable=wcol or "ABSENT",
                design_note=("EE por linealización de Taylor con estudiantes como unidades independientes (sin estratos/PSU en el diccionario; ignora el conglomerado escolar); "
                             "IC 95 % logit; ponderador " + wcol) if wcol else "Sin ponderador publicado: proporciones no ponderadas con IC de Wilson; no son estimaciones nacionales",
                n_rows=n_rows, n_filter_yes=int(f_yes.sum()), n_filter_no=int(f_no.sum()), n_filter_dontknow=int(f_dk.sum()), n_missing_item=int(f_blank.sum()),
                filter_unmapped_codes=";".join(f_unmapped), runtime_seconds=np.nan)
    recs = []

    def empty_record(sex_label, n, note, estimable):
        r = dict(base, sex=sex_label, n_students=int(n), n_weight_missing=np.nan, n_tea_unweighted=np.nan, proportion_unweighted_pct=np.nan, lo_unweighted_pct=np.nan, hi_unweighted_pct=np.nan,
                 proportion_weighted_pct=np.nan, se_pct=np.nan, lo_pct=np.nan, hi_pct=np.nan, weighted_tea_total=np.nan, weighted_population=np.nan,
                 n_answered=np.nan, proportion_weighted_answered_pct=np.nan, se_answered_pct=np.nan, lo_answered_pct=np.nan, hi_answered_pct=np.nan,
                 share_tea_among_diagnosed_pct=np.nan, estimable=estimable, note=note)
        return r

    if tcol is None:
        recs.append(empty_record("all", n_rows, f"No estimable: el cuestionario {year} no incluye categoría TEA (categorías: {', '.join(cats)}). Se informa el filtro de diagnóstico prolongado solo como contexto.", "no"))
    else:
        t = df[tcol].fillna("").astype(str).str.strip().str.lower()
        pos, neg, blank = t.isin(TEA_POSITIVE), t.isin(TEA_NEGATIVE), t.eq("")
        t_unmapped = sorted(set(t[~(pos | neg | blank)].unique()))
        if t_unmapped:
            raise ValueError(f"{path.name}: códigos TEA no mapeados {t_unmapped}")
        if blank.all():
            # El ponderador sí existe en el archivo: se informa cuántas filas carecen de él (dato conocido, no se deja como NaN).
            n_w_missing = int(pd.to_numeric(df[wcol].str.replace(",", ".", regex=False), errors="coerce").isna().sum()) if wcol else np.nan
            note = (f"No estimable: la variable {tcol} está completamente vacía en el archivo publicado ({n_rows:,} filas), aunque {int(f_yes.sum()):,} cuidadores "
                    "respondieron Sí al filtro. No debe leerse como cero."
                    + (f" Ponderador {wcol} ausente en {n_w_missing:,} filas." if wcol else ""))
            r_all = empty_record("all", n_rows, note, "no")
            r_all["n_weight_missing"] = n_w_missing
            recs.append(r_all)
            for sx in ("female", "male"):
                r_sx = empty_record(sx, int((sex == sx).sum()), note, "no")
                r_sx["n_weight_missing"] = n_w_missing
                recs.append(r_sx)
        else:
            df["tea01"] = pos.astype(int)
            if wcol:
                df["w"] = pd.to_numeric(df[wcol].str.replace(",", ".", regex=False), errors="coerce")
                n_w_missing = int(df["w"].isna().sum())
                dw = df.loc[df["w"].notna()].copy()
                answered = (f_yes | f_no).loc[dw.index]
                sex_w = sex.loc[dw.index]
            else:
                n_w_missing = np.nan
                dw = df
                answered = f_yes | f_no
                sex_w = sex
            doms = [("all", None), ("female", sex_w == "female"), ("male", sex_w == "male")]
            other_n = int((sex_w == "other").sum())
            if other_n >= SMALL_CELL:
                doms.append(("other", sex_w == "other"))
            for sx, dom in doms:
                mask = pd.Series(True, index=dw.index) if dom is None else dom
                n = int(mask.sum())
                k = int(dw.loc[mask, "tea01"].sum())
                p, lo, hi = C.wilson(k, n) if n else (np.nan, np.nan, np.nan)
                rec = empty_record(sx, n, "", "yes" if wcol else "unweighted_only")
                rec.update(n_weight_missing=n_w_missing, n_tea_unweighted=k, proportion_unweighted_pct=100 * p, lo_unweighted_pct=100 * lo, hi_unweighted_pct=100 * hi)
                ky = int(dw.loc[mask & f_yes.loc[dw.index], "tea01"].sum())
                ny = int((mask & f_yes.loc[dw.index]).sum())
                rec["share_tea_among_diagnosed_pct"] = 100 * ky / ny if ny else np.nan
                if wcol:
                    wb = weighted_block(dw, dom)
                    rec.update(proportion_weighted_pct=wb["proportion_weighted_pct"], se_pct=wb["se_pct"], lo_pct=wb["lo_pct"], hi_pct=wb["hi_pct"],
                               weighted_tea_total=wb["weighted_tea_total"], weighted_population=wb["weighted_population"])
                    dom_a = answered if dom is None else (dom & answered)
                    wa = weighted_block(dw, dom_a)
                    rec.update(n_answered=int(dom_a.sum()), proportion_weighted_answered_pct=wa["proportion_weighted_pct"], se_answered_pct=wa["se_pct"], lo_answered_pct=wa["lo_pct"], hi_answered_pct=wa["hi_pct"])
                    rec["note"] = ("Proporción ponderada de estudiantes cuyo cuidador reporta diagnóstico médico prolongado de TEA sobre todos los estudiantes con ponderador "
                                   "(No/No sabe/sin respuesta al filtro = no reportado). Sensibilidad *_answered: denominador restringido a filtro Sí/No. "
                                   "Cohorte escolar seleccionada y reporte de cuidadores; no prevalencia nacional.")
                else:
                    rec["note"] = ("Ítem TEA disponible pero sin factor de expansión publicado para 2023: solo conteos y proporción no ponderada (IC Wilson); "
                                   "no es estimación nacional ni comparable directamente con 2024–2025.")
                if sx != "all":
                    rec["note"] += f" Sexo: {sx}." + (f" Categorías de sexo con n<{SMALL_CELL} ('other', n={other_n}) suprimidas." if 0 < other_n < SMALL_CELL and sx == "male" else "")
                recs.append(rec)
    dt = time.perf_counter() - t0
    for r in recs:
        r["runtime_seconds"] = round(dt, 1)
    log(f"JUNAEB {year} {level:10s} {path.name}: {n_rows:,} filas, enc={enc}, TEA={'ABSENT' if not tcol else tcol}, w={wcol or 'ABSENT'}, {dt:.1f} s")
    return recs, items


# ---------------------------------------------------------------------------
# 3. Resumen anual
# ---------------------------------------------------------------------------
def build_summary(pie: pd.DataFrame, jun: pd.DataFrame) -> pd.DataFrame:
    years = sorted(set(pie.year.astype(int)) | set(jun.year.astype(int)) if len(jun) else set(pie.year.astype(int)))
    out = []
    for y in years:
        p = pie[pie.year == y].set_index("series")["value"]
        row = dict(year=y)
        for series, col in [("pie_tea_strict", "pie_tea_strict_n"), ("pie_tea_asperger", "pie_tea_asperger_n"), ("pie_harmonised", "pie_harmonised_n"),
                            ("pie_harmonised_sinaces", "pie_harmonised_sinaces_n"), ("special_schools_autism", "special_schools_autism_n"),
                            ("pie_total_enrolment", "pie_total_enrolment_apuntes60_n"), ("pie_total_applicants_sinaces", "pie_total_applicants_sinaces_n"),
                            ("pie_tea_strict_share_of_pie_pct", "pie_tea_strict_share_of_pie_pct"), ("pie_harmonised_share_of_pie_pct", "pie_harmonised_share_of_pie_pct"),
                            ("pie_tea_share_of_applicants_pct", "pie_harmonised_share_of_applicants_sinaces_pct"), ("pie_tea_exceptional_entry", "pie_tea_exceptional_entry_n")]:
            row[col] = p.get(series, np.nan)
        src = pie[(pie.year == y) & (pie.series == "pie_harmonised")]
        row["pie_harmonised_source"] = src.source_file.iloc[0] if len(src) else ""
        for lvl in LEVEL_ORDER:
            j = jun[(jun.year == y) & (jun.level == lvl) & (jun.sex == "all")]
            if len(j):
                j = j.iloc[0]
                row[f"junaeb_{lvl}_n_students"] = j["n_students"]
                row[f"junaeb_{lvl}_tea_n"] = j["n_tea_unweighted"]
                row[f"junaeb_{lvl}_pct_weighted"] = j["proportion_weighted_pct"]
                row[f"junaeb_{lvl}_pct_weighted_lo"] = j["lo_pct"]
                row[f"junaeb_{lvl}_pct_weighted_hi"] = j["hi_pct"]
                row[f"junaeb_{lvl}_pct_unweighted"] = j["proportion_unweighted_pct"]
                row[f"junaeb_{lvl}_estimable"] = j["estimable"]
            else:
                for suf in ["n_students", "tea_n", "pct_weighted", "pct_weighted_lo", "pct_weighted_hi", "pct_unweighted"]:
                    row[f"junaeb_{lvl}_{suf}"] = np.nan
                row[f"junaeb_{lvl}_estimable"] = "not_run"
        out.append(row)
    df = pd.DataFrame(out)
    df["variant_note"] = "Series educativas idénticas en con_rett y sin_rett (no dependen de F84.2)"
    df["unit_note"] = "_n = estudiantes (stock escolar anual); _pct = porcentaje; JUNAEB = reporte de cuidadores en cohortes escolares seleccionadas"
    return df


# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-junaeb", action="store_true", help="solo PIE/SINACES (rápido)")
    ap.add_argument("--junaeb-years", type=int, nargs="*", default=YEARS_JUNAEB)
    args = ap.parse_args(argv)
    t_start = time.perf_counter()
    ctl = Controls()

    pie = extract_pie(ctl)
    C.atomic_write_csv(pie, CFG.TIDY / "pie_series.csv")
    log(f"pie_series.csv: {len(pie)} filas")

    jun_rows, item_rows = [], []
    if not args.skip_junaeb:
        files = junaeb_files()
        expected = {(y, l) for y in args.junaeb_years for l in LEVEL_ORDER}
        missing = sorted(expected - set(files))
        if missing:
            log(f"ADVERTENCIA: faltan archivos JUNAEB para {missing}")
        for (year, level), path in sorted(files.items(), key=lambda kv: (kv[0][0], LEVEL_ORDER.index(kv[0][1]))):
            if year not in args.junaeb_years:
                continue
            recs, items = process_junaeb(year, level, path, JUNAEB_VARS[year][level])
            jun_rows += recs
            item_rows += items
    jun = pd.DataFrame(jun_rows)
    items = pd.DataFrame(item_rows)
    if len(jun):
        jun["sex_order"] = jun.sex.map({"all": 0, "female": 1, "male": 2, "other": 3})
        jun["level_order"] = jun.level.map(LEVEL_ORDER.index)
        jun = jun.sort_values(["year", "level_order", "sex_order"]).drop(columns=["sex_order", "level_order"]).reset_index(drop=True)
        jun["script"] = SCRIPT
        C.atomic_write_csv(jun, CFG.TIDY / "junaeb_tea_year_level.csv")
        items["script"] = SCRIPT
        C.atomic_write_csv(items, CFG.TIDY / "junaeb_items_dictionary.csv")
        log(f"junaeb_tea_year_level.csv: {len(jun)} filas; junaeb_items_dictionary.csv: {len(items)} filas")
        # Controles JUNAEB
        for y, key in [(2024, "junaeb_unweighted_2024"), (2025, "junaeb_unweighted_2025")]:
            for lvl, exp in CFG.CONTROLS[key].items():
                j = jun[(jun.year == y) & (jun.level == lvl) & (jun.sex == "all")]
                ctl.add(key, lvl, exp, int(j.n_tea_unweighted.iloc[0]) if len(j) and pd.notna(j.n_tea_unweighted.iloc[0]) else np.nan, "Conteo no ponderado de TEA reportado")
        for y, key in [(2024, "junaeb_weighted_pct_2024"), (2025, "junaeb_weighted_pct_2025")]:
            for lvl, exp in PUBLISHED_CHECKS[key].items():
                j = jun[(jun.year == y) & (jun.level == lvl) & (jun.sex == "all")]
                obs = round(float(j.proportion_weighted_pct.iloc[0]), 2) if len(j) and pd.notna(j.proportion_weighted_pct.iloc[0]) else np.nan
                ctl.add(key, lvl, exp, obs, "Proporción ponderada (todos los estudiantes con ponderador), redondeada a 2 decimales; preliminar DATA_REVIEW.md", tol_abs=0.005)
        j = jun[(jun.year == 2024) & (jun.level == "medio1") & (jun.sex == "all")]
        ctl.add("junaeb_2024_medio1_not_estimable", "medio1", "no", j.estimable.iloc[0] if len(j) else "missing", "Variable D15_11 vacía: no estimable, no cero")
        for y in (2019, 2020, 2021, 2022):
            for lvl in LEVEL_ORDER:
                j = jun[(jun.year == y) & (jun.level == lvl) & (jun.sex == "all")]
                if len(j):
                    ctl.add("junaeb_no_tea_item_pre2023", f"{y}_{lvl}", "no", j.estimable.iloc[0], "Sin categoría TEA en el cuestionario")
    summary = build_summary(pie, jun if len(jun) else pd.DataFrame(columns=["year", "level", "sex"]))
    C.atomic_write_csv(summary, CFG.TIDY / "education_summary_year.csv")
    controls = ctl.frame()
    C.atomic_write_csv(controls, CFG.OUT / "controls" / f"{MODULE}_controls.csv")
    n_diff = int((controls.status != "ok").sum())
    log(f"controles: {len(controls)} ({n_diff} difieren)")
    if n_diff:
        print(controls[controls.status != "ok"].to_string(index=False))
    log(f"runtime total: {time.perf_counter() - t_start:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
