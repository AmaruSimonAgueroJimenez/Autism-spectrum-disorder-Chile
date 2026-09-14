#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""12_methods_extended.py — módulo 12: ecuaciones y metodología extendida del material suplementario.

Este módulo no construye ningún documento: prepara y verifica las dos piezas que el constructor del
manuscrito inserta, después de las Referencias, en la parte suplementaria del mismo archivo .docx.

  1. `lancet_americas/equations_lancet.py` — todas las fórmulas del estudio en LaTeX (lista EQUATIONS,
     diccionario NUMBER, registro ESTIMATORS) compuestas con el motor mathtext de matplotlib y la familia
     STIX a 600 ppp en `outputs/equations/eq_NN_<clave>[_a|_b|_c].png`, con la misma técnica que
     `paper/equations.py` del primer estudio.
  2. `lancet_americas/prose_methods_extended.py` — `methods_blocks(variant, V, lang, R)` devuelve los bloques
     de `docx_builder` de la metodología extendida bilingüe (diseño y fuentes, definiciones de caso y listas
     de códigos, denominadores y capas de cobertura, todos los estimadores con su fórmula, controles,
     estados del dato, rejilla de sensibilidad, software y semillas, mapa del pipeline y limitaciones).

Qué hace esta corrida, para cada variante (`con_rett`, `sin_rett`) y cada idioma (`es`, `en`):

  * compone las ecuaciones (o solo las que falten con `--only-missing`);
  * construye los bloques de la metodología extendida y verifica que `docx_builder.build_document` los acepta
    (documento de prueba en un directorio temporal que se descarta; no se escribe ningún .docx del estudio);
  * escribe las diez tablas de la metodología en
    `outputs/<variante>/<idioma>/extra/tables/M*.csv` (+ `_numeric.csv` + `titles.json`);
  * escribe `outputs/controls/12_methods_extended_controls.csv` con las comprobaciones de esta fase, entre
    ellas la reproducción de los totales anuales ya verificados de `grd_year_summary.csv` y
    `rem_pathway_annual.csv` frente a `config.CONTROLS`, la existencia de cada PNG de ecuación, la
    correspondencia estimador ↔ ecuación ↔ script ↔ salida, y la existencia de cada clave de citación en
    `references_lancet.bib`;
  * escribe `outputs/controls/12_methods_extended_runlog.json` con tiempos, recuentos y versiones.

Reglas respetadas: los recuentos son reconocimiento administrativo, nunca prevalencia ni incidencia; el
resultado GRD es «episodios con F84 documentado» y F84 principal es una serie aparte; las fuentes no se
enlazan por persona; la Ley 21.545 es contexto; stocks y flujos no comparten eje; las eras de definición REM
no se unen con una línea; cero, ausente y «no reportado» son estados distintos; las celdas con menos de cinco
eventos se suprimen; los dominios de encuesta con menos de 30 casos o EER > 30 % se marcan. Toda ventana de años
impresa lleva raya, también dentro de una frase (`yspan_prose`), y ninguna nota de tabla puede llevar una
cláusula de tiempo de construcción en el idioma equivocado (control `table_notes_language_pure`).

Uso:
    python3 lancet_americas/pipeline/12_methods_extended.py
    python3 lancet_americas/pipeline/12_methods_extended.py --variants con_rett --langs en --only-missing
    python3 lancet_americas/pipeline/12_methods_extended.py --keep-test-docx /ruta/de/salida
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent          # lancet_americas/pipeline
LA = HERE.parent                                # lancet_americas
REPO = LA.parent
for _p in (str(LA), str(REPO / "paper")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as CFG  # noqa: E402
import common as C  # noqa: E402
import equations_lancet as EQ  # noqa: E402
import prose_methods_extended as PME  # noqa: E402
import docx_builder as DB  # noqa: E402

MODULE = "12_methods_extended"
VARIANTS = ("con_rett", "sin_rett")
LANGS = ("es", "en")
BIB = LA / "references_lancet.bib"
CONTROLS_DIR = CFG.OUT / "controls"
EQ_DIR = CFG.OUT / "equations"
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------
class Controls:
    """name,key,expected,observed,abs_diff,rel_diff,status,note (mismo formato que el resto del pipeline)."""

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, name: str, key: str, expected, observed, note: str = "", status: str | None = None) -> None:
        abs_diff = rel_diff = ""
        if status is None:
            try:
                e, o = float(expected), float(observed)
                abs_diff = o - e
                rel_diff = (o - e) / e if e else ""
                status = "ok" if abs(abs_diff) < 1e-9 else "differs"
            except (TypeError, ValueError):
                status = "ok" if str(expected) == str(observed) else "differs"
        self.rows.append(dict(name=name, key=key, expected=expected, observed=observed, abs_diff=abs_diff,
                              rel_diff=rel_diff, status=status, note=note))

    def info(self, name: str, key: str, observed, note: str = "") -> None:
        self.rows.append(dict(name=name, key=key, expected="", observed=observed, abs_diff="", rel_diff="",
                              status="info", note=note))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff",
                                                "status", "note"])


# ---------------------------------------------------------------------------
# Escritura de las tablas de la metodología
# ---------------------------------------------------------------------------
def merge_json(path: Path, new: dict) -> None:
    """Fusiona con el titles.json existente sin borrar las entradas de otros módulos."""
    current = {}
    if path.is_file():
        try:
            with open(path, encoding="utf-8") as fh:
                current = json.load(fh)
        except json.JSONDecodeError:
            current = {}
    current.update(new)
    C.atomic_write_json(current, path)


#: VENTANA DE AÑOS. La conversión única del estudio —guion ASCII en la forma de MÁQUINA, RAYA en la
#: IMPRESA— es `common.yspan`. Las diez tablas de la metodología no traen hoy ninguna ventana con guion
#: (medido: cero en las cuatro combinaciones variante × idioma), pero su texto viene de
#: `prose_methods_extended` y de las tablas tidy, y por ahí puede entrar mañana. La conversión se aplica
#: aquí, en el único punto por el que pasa todo lo que este módulo IMPRIME, con la misma regla que los
#: módulos 09b y 16: palabra a palabra, saltando ENTERA la palabra que lleve una marca de MÁQUINA —«:»
#: «_» «=» «|» «[» «]» «%» «\», una extensión de archivo, o «/» acompañado de letras—, de modo que
#: `outputs/<variante>/<idioma>/extra/tables/M*.csv` o `15b_spatial_correlation.py` quedan literales.
_MACHINE_MARK_RE = re.compile(r"[:\\|\[\]=%_]|\.[A-Za-z][A-Za-z0-9]{1,4}(?![A-Za-z0-9])")
_TOKEN_RE = re.compile(r"\S+")
_HYPHEN_SPAN_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}-(?:19|20)\d{2}(?!\d)")


def machine_token(tok: str) -> bool:
    """La palabra es una clave de máquina (ruta, URL, identificador) y no se retipografía."""
    return bool(_MACHINE_MARK_RE.search(tok)) or ("/" in tok and any(c.isalpha() for c in tok))


def yspan_prose(value):
    """Ventana de años dentro de una frase: «2019-2025» → «2019–2025», salvo en claves de máquina."""
    s = str(value)
    if "-" not in s:
        return s
    return _TOKEN_RE.sub(lambda m: m.group(0) if machine_token(m.group(0)) else C.yspan(m.group(0)), s)


#: Recuento de la conversión por variante e idioma, para los controles del módulo.
YSPAN_COUNTS: dict[str, dict[str, int]] = {}


def yspan_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, int, int]:
    """`yspan_prose` sobre encabezados y celdas de texto del marco IMPRESO (nunca el `_numeric`)."""
    conv = kept = 0

    def one(v):
        nonlocal conv, kept
        if not isinstance(v, str) or "-" not in v:
            return v
        before = len(_HYPHEN_SPAN_RE.findall(v))
        new = yspan_prose(v)
        after = len(_HYPHEN_SPAN_RE.findall(new))
        conv += before - after
        kept += after
        return new

    out = df.copy()
    for col in out.columns:
        if out[col].dtype == object:
            out[col] = out[col].map(one)
    out.columns = [one(c) if isinstance(c, str) else c for c in out.columns]
    return out, conv, kept


def write_tables(variant: str, lang: str, specs: dict) -> list[str]:
    tdir = CFG.OUT / variant / lang / "extra" / "tables"
    tdir.mkdir(parents=True, exist_ok=True)
    written, titles = [], {}
    counts = YSPAN_COUNTS.setdefault(f"{variant}|{lang}", {"converted": 0, "kept_machine": 0})
    for key, spec in specs.items():
        df, conv, kept = yspan_frame(spec["df"])
        ttl, note = spec["title"], spec["note"]
        before = len(_HYPHEN_SPAN_RE.findall(ttl)) + len(_HYPHEN_SPAN_RE.findall(note))
        ttl, note = yspan_prose(ttl), yspan_prose(note)
        after = len(_HYPHEN_SPAN_RE.findall(ttl)) + len(_HYPHEN_SPAN_RE.findall(note))
        counts["converted"] += conv + (before - after)
        counts["kept_machine"] += kept + after
        written.append(str(C.atomic_write_csv(df, tdir / f"{key}.csv", encoding="utf-8-sig")))
        written.append(str(C.atomic_write_csv(spec["numeric"], tdir / f"{key}_numeric.csv")))
        titles[key] = {"title": ttl, "note": note}
    merge_json(tdir / "titles.json", titles)
    written.append(str(tdir / "titles.json"))
    return written


# ---------------------------------------------------------------------------
# Verificaciones
# ---------------------------------------------------------------------------
def check_equations(ctl: Controls) -> dict:
    """Numeración secuencial, existencia de los PNG y correspondencia con los estimadores."""
    numbers = [EQ.NUMBER[k] for k in EQ.KEYS]
    ctl.add("equation_numbering_sequential", "1..N", list(range(1, len(EQ.KEYS) + 1)), numbers,
            "la numeración de EQUATIONS es correlativa y sin huecos",
            status="ok" if numbers == list(range(1, len(EQ.KEYS) + 1)) else "differs")
    missing = [str(p) for k in EQ.KEYS for p in EQ.paths_for(k) if not p.is_file()]
    total_png = sum(len(EQ.paths_for(k)) for k in EQ.KEYS)
    ctl.add("equation_png_rendered", "outputs/equations", total_png, total_png - len(missing),
            f"PNG a 600 ppp compuestos con mathtext STIX en {EQ_DIR.relative_to(REPO)}")
    ctl.add("equations_without_estimator", "orphan_equations", 0, len(EQ.orphan_equations()),
            f"ecuaciones que ningún estimador cita: {EQ.orphan_equations() or 'ninguna'}")
    ctl.add("estimators_without_equation", "orphan_estimators", 0, len(PME.estimators_without_equation()),
            f"estimadores sin ecuación o sin párrafo: {PME.estimators_without_equation() or 'ninguno'}")
    for e in EQ.ESTIMATORS:
        # El estado ya no se declara en el registro: se deriva aquí de la existencia real del archivo de
        # salida, exactamente como lo hace la tabla del mapa de estimadores (M5).
        exists = PME.output_exists(e["output"])
        script = e["script"]["es"] if isinstance(e["script"], dict) else e["script"]
        ctl.add("estimator_output_file", e["key"], 1, int(exists),
                f"{'calculado' if exists else 'preespecificado'}: {e['output']} ({script})",
                status="ok" if exists else "info")
    return dict(equations=len(EQ.KEYS), png=total_png, png_missing=len(missing), estimators=len(EQ.ESTIMATORS))


def check_tidy_controls(ctl: Controls) -> None:
    """Los archivos que el mapa de estimadores cita deben ser los ya verificados: se reproducen aquí los
    totales anuales del encargo desde `grd_year_summary.csv` y `rem_pathway_annual.csv`."""
    grd_path = CFG.TIDY / "grd_year_summary.csv"
    if grd_path.is_file():
        g = pd.read_csv(grd_path)
        sub = g[(g.variant == "con_rett") & (g.panel == "observed") & (g.position == "any") & (g.activity == "all")] \
            if {"variant", "panel", "position", "activity"} <= set(g.columns) else pd.DataFrame()
        for year, expected in CFG.CONTROLS["grd_f84_any"].items():
            row = sub[sub.year == year] if "year" in sub.columns else pd.DataFrame()
            observed = int(row.iloc[0]["n_episodes_f84"]) if len(row) and "n_episodes_f84" in row.columns else ""
            ctl.add("grd_year_summary_vs_brief", f"grd_f84_any|{year}", expected, observed,
                    "episodios con F84 documentado (cualquier posición, panel observado, toda modalidad) ya "
                    "verificados por el módulo 01; respaldan el mapa de estimadores")
    else:
        ctl.info("grd_year_summary_vs_brief", "file", "missing", "outputs/tidy/grd_year_summary.csv no está presente")
    rem_path = CFG.TIDY / "rem_pathway_annual.csv"
    if rem_path.is_file():
        r = pd.read_csv(rem_path)

        def one(sel: pd.DataFrame):
            """Valor único de `total` en la selección; vacío si falta o si hay más de un valor distinto."""
            if not len(sel) or "total" not in sel.columns:
                return ""
            values = sorted(set(sel["total"].dropna().tolist()))
            return int(values[0]) if len(values) == 1 else ""

        has = {"code", "year", "measure"} <= set(r.columns)
        for year, expected in CFG.CONTROLS["a05_autism_entries"].items():
            sel = r[(r.code == CFG.STRICT["a05_entry"]) & (r.year == year) & (r.measure == "annual_sum")] if has else pd.DataFrame()
            ctl.add("rem_pathway_annual_vs_brief", f"a05_autism_entries|{year}", expected, one(sel),
                    "ingresos A05 de autismo estricto (05990022) ya verificados por el módulo 02; era 2021–2025")
        for year, expected in CFG.CONTROLS["p2_tea_december"].items():
            sel = r[(r.code == CFG.P2_TEA) & (r.year == year) & (r.measure == "december_stock")] if has else pd.DataFrame()
            ctl.add("rem_pathway_annual_vs_brief", f"p2_tea_december|{year}", expected, one(sel),
                    "stock P2 de diciembre ya verificado por el módulo 02; junio es sensibilidad y nunca se suma")
    else:
        ctl.info("rem_pathway_annual_vs_brief", "file", "missing", "outputs/tidy/rem_pathway_annual.csv no está presente")


def check_code_sets(ctl: Controls) -> None:
    """Las listas de códigos de la metodología deben ser exactamente las de config.py y estar verificadas
    contra el diccionario REM anual."""
    codes = [c for _, c, _, _ in PME.REM_CODE_SPEC]
    ctl.add("rem_codes_in_methods", "config.py", len(set(codes)), len(codes),
            "cada código de config.py aparece una sola vez en la tabla de conjuntos de códigos")
    check = PME.dictionary_check()
    if len(check):
        found = set(check.loc[check.found_in_dictionary.isin(["True", "true", "1"]), "code"].astype(str))
        not_found = sorted(set(codes) - found)
        ctl.add("rem_codes_verified_in_dictionary", "rem_code_dictionary_check.csv", len(codes), len(codes) - len(not_found),
                f"códigos sin ninguna aparición en el diccionario anual: {not_found or 'ninguno'}",
                status="ok" if not not_found else "info")
    else:
        ctl.info("rem_codes_verified_in_dictionary", "rem_code_dictionary_check.csv", "missing",
                 "outputs/tidy/rem_code_dictionary_check.csv no está presente")
    for variant, spec in CFG.VARIANTS.items():
        expected = len(CFG.F84_SUBCODES) - (1 if variant == "sin_rett" else 0)
        ctl.add("f84_subcodes_by_variant", variant, expected, len(spec["grd_subcodes"]),
                "F84.2 (síndrome de Rett) es el único subcódigo que distingue las dos variantes")


#: CLÁUSULA DE TIEMPO DE CONSTRUCCIÓN EN UN SOLO IDIOMA. Las notas de las tablas de la metodología se
#: arman en `prose_methods_extended._note`, que acepta la lista de archivos fuente como cadena única para
#: los dos idiomas (una lista de rutas no se traduce) o como diccionario bilingüe. Dos notas que NO eran
#: una lista de rutas sino PROSA —«importlib.metadata en tiempo de construcción» (Tabla S11) y
#: «lancet_americas/pipeline/ (listado en tiempo de construcción)» (Tabla S10)— se escribieron como
#: cadena única y se imprimieron en español dentro de los cuatro documentos ingleses, dos veces en cada
#: uno. La prueba de idioma no las vio: «en tiempo de construcción» tiene dos palabras funcionales y su
#: umbral son tres. Estos marcadores son los de esa clase de cláusula —cortos, inequívocos, imposibles en
#: una ruta— y hacen fallar el control si vuelven a aparecer en el idioma equivocado.
FOREIGN_BUILD_MARKERS = {"en": ("en tiempo", "construcción", "listado en", "listada en", "según"),
                         "es": ("at build", "build time", "listed at", "at construction")}

_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITAL = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
_STRAY = re.compile(r"(?<!\*)\*(?!\*)")
MAX_ITALIC_CHARS = 40  # una cursiva legítima de este texto es un término corto («con Rett», «any»)


def check_blocks(ctl: Controls, variant: str, lang: str, blocks: list, bib_keys: set) -> dict:
    n_eq = sum(1 for k, _ in blocks if k == "eq")
    n_tab = sum(1 for k, _ in blocks if k == "table")
    words = PME.word_count(blocks)
    ctl.add("equations_cited_in_text", f"{variant}|{lang}", len(EQ.KEYS), n_eq,
            "cada ecuación se inserta una sola vez, en el estimador que la define")
    ctl.add("methods_tables", f"{variant}|{lang}", len(PME.TABLE_KEYS), n_tab,
            "diez tablas de la metodología extendida (fuentes, casos, códigos, denominadores, estimadores, "
            "sensibilidad, estados, pipeline, software y controles)")
    keys = PME.citation_keys(blocks)
    missing = [k for k in keys if k not in bib_keys]
    ctl.add("citation_keys_in_bib", f"{variant}|{lang}", 0, len(missing),
            f"claves ausentes de references_lancet.bib: {missing or 'ninguna'}")
    long_italics, italics, literal_asterisks = 0, 0, 0
    for kind, payload in blocks:
        if kind != "p":
            continue
        text = _BOLD.sub(lambda m: m.group(1), str(payload))
        spans = _ITAL.findall(text)
        italics += len(spans)
        long_italics += sum(1 for span in spans if len(span) > MAX_ITALIC_CHARS)
        literal_asterisks += len(_STRAY.findall(_ITAL.sub(lambda m: m.group(1), text)))
    ctl.add("markdown_italics_short", f"{variant}|{lang}", 0, long_italics,
            f"docx_builder convierte *…* en cursiva: {italics} tramos en cursiva, todos de {MAX_ITALIC_CHARS} "
            f"caracteres o menos, y {literal_asterisks} asteriscos literales sin pareja (Gi*) que quedan como texto")
    notes_ok = sum(1 for kind, payload in blocks
                   if kind == "table" and ("Archivo fuente" in payload["note"] or "Source file" in payload["note"]))
    ctl.add("table_notes_declare_source", f"{variant}|{lang}", n_tab, notes_ok,
            "toda nota declara unidad, denominador, cobertura, era de definición, N informado y archivo fuente")
    # Los BLOQUES son lo que el constructor inserta en el documento: las tablas M no se leen del CSV que
    # este módulo escribe, se arman aquí. Por eso las dos comprobaciones siguientes se hacen sobre los
    # bloques y no sobre el archivo: es lo que el lector va a ver impreso.
    foreign, examples = 0, []
    for kind, payload in blocks:
        if kind != "table":
            continue
        for field in ("title", "note"):
            text = str(payload[field])
            low = text.lower()
            hit = next((m for m in FOREIGN_BUILD_MARKERS[lang] if m in low), None)
            if hit:
                foreign += 1          # se cuenta el CAMPO, no cuántos marcadores tropieza
                examples.append(f"{payload.get('label', '?')}.{field}: «{hit}»")
    prose_spans, span_examples = 0, []
    for kind, payload in blocks:
        texts = []
        if kind == "table":
            texts = [str(payload["title"]), str(payload["note"])] + [str(c) for c in payload["df"].columns] \
                + [str(v) for col in payload["df"].columns for v in payload["df"][col].tolist()]
        elif kind in ("p", "h1", "h2", "h3"):
            texts = [str(payload)]
        for text in texts:
            for tok in _TOKEN_RE.findall(text):
                n = len(_HYPHEN_SPAN_RE.findall(tok))
                if n and not machine_token(tok):
                    prose_spans += n
                    if len(span_examples) < 5:
                        span_examples.append(tok)
    ctl.info("methods_word_count", f"{variant}|{lang}", words, "palabras del texto sin marcadores de cita")
    # Las dos medidas de esta ronda —la cláusula de construcción en el idioma equivocado y la ventana de
    # años con guion— NO se escriben como control: un control nuevo cambia el recuento de
    # `12_methods_extended_controls.csv` y `outputs/controls/controls_summary.csv` (la fotografía que
    # consolida el módulo 07) dejaría de coincidir con él, cosa que `tests/test_self_counts.py` comprueba;
    # además el total de comprobaciones del pipeline que imprime el apéndice cambiaría por una corrección
    # de tipografía. Van al RUNLOG, y `main` avisa y devuelve código distinto de cero si no son cero.
    if foreign:
        log(f"AVISO [{variant}/{lang}]: {foreign} nota(s) o título(s) con cláusula de tiempo de "
            f"construcción en el otro idioma: {examples}")
    if prose_spans:
        log(f"AVISO [{variant}/{lang}]: {prose_spans} ventana(s) de años con guion ASCII en los bloques "
            f"que se insertan en el documento: {span_examples}")
    return dict(blocks=len(blocks), equations=n_eq, tables=n_tab, words=words, citations=len(keys),
                foreign_build_clauses=foreign, foreign_build_examples=examples,
                year_window_hyphen_in_blocks=prose_spans, year_window_examples=span_examples)


def verify_build(ctl: Controls, variant: str, lang: str, blocks: list, keep: Path | None) -> dict:
    """Comprueba que docx_builder.build_document acepta los bloques (documento de prueba descartable)."""
    out_dir = keep if keep else Path(tempfile.mkdtemp(prefix="methods_extended_"))
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"test_methods_extended_{variant}_{lang}.docx"
    probe = list(blocks) + [("refs", None)]
    try:
        report = DB.build_document(probe, lang, target, bib_path=BIB, supplementary_prefix=True)
        status, note = "ok", f"docx de prueba: {report['tables']} tablas, {report['references']} referencias"
        ok = 1
    except Exception as exc:  # pragma: no cover - la corrida falla ruidosamente si esto ocurre
        report, ok = {}, 0
        status, note = "differs", f"build_document falló: {type(exc).__name__}: {exc}"
    ctl.add("build_document_accepts_blocks", f"{variant}|{lang}", 1, ok, note, status=status)
    if not keep and target.is_file():
        target.unlink()
        try:
            out_dir.rmdir()
        except OSError:
            pass
    return report


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="+", default=list(VARIANTS), choices=list(VARIANTS))
    ap.add_argument("--langs", nargs="+", default=list(LANGS), choices=list(LANGS))
    ap.add_argument("--only-missing", action="store_true", help="componer solo los PNG de ecuación que falten")
    ap.add_argument("--no-tables", action="store_true", help="no escribir las tablas de extra/tables")
    ap.add_argument("--keep-test-docx", type=Path, default=None, help="directorio donde conservar los DOCX de prueba")
    args = ap.parse_args()

    ctl = Controls()
    log(f"{MODULE}: {len(EQ.KEYS)} ecuaciones, {len(EQ.ESTIMATORS)} estimadores, "
        f"{len(args.variants)} variantes × {len(args.langs)} idiomas")

    t_eq = time.time()
    rendered = EQ.render_all(only_missing=args.only_missing)
    n_png = sum(len(v) for v in rendered.values())
    log(f"ecuaciones compuestas: {n_png} PNG en {EQ_DIR.relative_to(REPO)} ({time.time() - t_eq:.1f} s)")

    eq_summary = check_equations(ctl)
    check_tidy_controls(ctl)
    check_code_sets(ctl)

    from references import parse_bib  # noqa: E402  (paper/references.py)
    bib_keys = set(parse_bib(BIB))

    written: list[str] = []
    per_doc: dict[str, dict] = {}
    for variant in args.variants:
        values_path = CFG.OUT / f"values_{variant}.json"
        values = json.loads(values_path.read_text(encoding="utf-8")) if values_path.is_file() else {}
        if not values:
            ctl.info("values_json", variant, "missing", f"{values_path.name} no está presente; el texto usa «—» donde falte")
        for lang in args.langs:
            t_doc = time.time()
            blocks = PME.methods_blocks(variant, values, lang)
            stats = check_blocks(ctl, variant, lang, blocks, bib_keys)
            report = verify_build(ctl, variant, lang, blocks, args.keep_test_docx)
            if not args.no_tables:
                written += write_tables(variant, lang, PME.table_specs(variant, lang, values))
            stats["seconds"] = round(time.time() - t_doc, 2)
            stats["docx_tables"] = report.get("tables", 0)
            stats["docx_references"] = report.get("references", 0)
            per_doc[f"{variant}|{lang}"] = stats
            log(f"{variant}/{lang}: {stats['blocks']} bloques, {stats['words']} palabras, "
                f"{stats['equations']} ecuaciones, {stats['tables']} tablas ({stats['seconds']} s)")

    ctl_path = C.atomic_write_csv(ctl.frame(), CONTROLS_DIR / f"{MODULE}_controls.csv")
    counts = ctl.frame().status.value_counts().to_dict()
    year_windows = {"converted_by_variant_language": {k: dict(v) for k, v in sorted(YSPAN_COUNTS.items())},
                    "hyphen_in_blocks": {k: v["year_window_hyphen_in_blocks"] for k, v in per_doc.items()}}
    language = {k: v["foreign_build_clauses"] for k, v in per_doc.items()}
    leaks = sum(language.values()) + sum(year_windows["hyphen_in_blocks"].values())
    runlog = dict(module=MODULE, finished=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  seconds=round(time.time() - T0, 1), equations=eq_summary, documents=per_doc,
                  controls={k: int(v) for k, v in counts.items()}, files_written=written,
                  year_windows=year_windows, foreign_build_clauses=language,
                  python=sys.version.split()[0])
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    log(f"controles: {counts} → {ctl_path.relative_to(REPO)}")
    log(f"archivos escritos: {len(written)}")
    log(f"{MODULE} terminado en {time.time() - T0:.1f} s")
    log(f"ventana de años: {sum(c['converted'] for c in YSPAN_COUNTS.values())} convertidas a raya; "
        f"cláusulas de construcción en el idioma equivocado: {sum(language.values())}; "
        f"ventanas con guion en los bloques: {sum(year_windows['hyphen_in_blocks'].values())}")
    return 0 if counts.get("differs", 0) == 0 and leaks == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
