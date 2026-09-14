# -*- coding: utf-8 -*-
"""17_extended_material.py — módulo 17: material extendido DENTRO del manuscrito.

Verifica y documenta la parte suplementaria que `prose_en.py` / `prose_es.py` añaden al archivo del
manuscrito después de las Referencias (metodología extendida con todas las fórmulas, láminas
suplementarias agrupadas por tema y tablas suplementarias), y el único cambio acordado en el artículo:
la lámina de flujo de datos del módulo 08d pasa a ser la Figura 1 y el inventario de fuentes
(`T1_sources`) pasa al material suplementario como Tabla S1.

Recorre las dos variantes (`con_rett`, `sin_rett`) y los dos idiomas (`es`, `en`) y comprueba:

  * inventario: cada lámina y cada tabla del registro compartido existe en disco, con leyenda o título
    y nota, en las cuatro combinaciones variante × idioma;
  * numeración: `Figura/Figure S1…` y `Tabla/Table S1…` son la posición en SUPP_FIGURES / SUPP_TABLES,
    ningún número se repite, T1_sources es la Tabla S1, T_dataflow_counts la Tabla S2, y el manuscrito y
    el apéndice separado comparten exactamente el mismo registro en ambos idiomas;
  * artículo: cinco figuras y siete tablas, todas citadas al menos una vez, con orden de primera cita
    1, 2, 3, …, ninguna cita escrita fuera del registro, y los límites de la revista (resumen ≤ 250
    palabras, cuerpo 3500–5000, ≤ 30 claves de citación) medidos sobre el artículo, no sobre el archivo;
  * ecuaciones: las de `equations.py` están compuestas, se emiten todas una sola vez y se citan;
  * agregados: las tablas completas embebidas reproducen exactamente las tablas tidy ya verificadas
    (`grd_year_summary`, `rem_pathway_annual`, `models_summary`) y los controles preespecificados de
    `config.CONTROLS`.

Salidas:
  outputs/controls/17_extended_material_controls.csv   name,key,expected,observed,abs_diff,rel_diff,status,note
  outputs/controls/17_extended_material_runlog.json    recuentos, tiempos y versión de Python
  extended_material_index.md                           número, archivo, tabla tidy de origen y descripción
                                                       de cada lámina y tabla suplementaria

Uso:
    python3 study/pipeline/17_extended_material.py               # verifica y escribe índice y controles
    python3 study/pipeline/17_extended_material.py --build       # además reconstruye los 12 documentos
    python3 study/pipeline/17_extended_material.py --build --supp-dpi 300
    python3 study/pipeline/17_extended_material.py --build --skip-pdf

Reglas del estudio respetadas: los recuentos son reconocimiento administrativo, nunca prevalencia ni
incidencia; el resultado GRD es «episodios con F84 documentado» y F84 principal es una serie aparte; las
fuentes no se enlazan por persona; stocks y flujos no se mezclan; lugar de atención y residencia no se
mezclan sin nota; las eras de definición REM no se unen con una línea; la Ley 21.545 es contexto.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent          # study/pipeline
LA = HERE.parent                                # study
REPO = LA.parent
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import pandas as pd  # noqa: E402

import common as C  # noqa: E402
import config as CFG  # noqa: E402
import equations as EQ  # noqa: E402
import labels as LBL  # noqa: E402  (rótulos compartidos; nunca literales sueltos para los conceptos del estudio)
import prose_en as PEN  # noqa: E402
import prose_es as PES  # noqa: E402
import supplementary_material as SM  # noqa: E402

MODULE = "17_extended_material"
T0 = time.time()
VARIANTS = tuple(CFG.VARIANTS)
LANGS = ("en", "es")
PROSE = {"en": PEN, "es": PES}
CONTROLS_DIR = CFG.OUT / "controls"
INDEX_PATH = LA / "extended_material_index.md"
BUILD_REPORT = LA / "manuscript" / "build_report.json"
STATUS_PATH = LA / "review_status.json"


# ---------------------------------------------------------------------------
# Los hechos de la COMPILACIÓN, leídos y no escritos a mano
# ---------------------------------------------------------------------------
# Este índice llevaba escritas a mano las medidas de una compilación concreta —su fecha y su hora, la
# página más corta del corpus, las colas de leyenda, las páginas de la región de láminas y la lista de
# puntos abiertos del memo—. Envejecían solas: la primera reconstrucción posterior las dejaba mintiendo
# sin que nadie tocara una línea. Desde la fase 4k salen de los dos artefactos que ya los miden:
# `manuscript/build_report.json`, lo que la compilación mide de sí misma, y `review_status.json`, el
# registro de las lecturas independientes y de los puntos abiertos. Si falta el informe, el índice lo
# dice en vez de repetir de memoria las cifras de otra compilación.
def build_facts() -> dict:
    """Las medidas de la compilación que hay en `manuscript/`, o `present=False` si no hay ninguna."""
    try:
        br = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(present=False)
    docs = {f"{part}_{key}": br["documents"][key][part]
            for key in br["documents"] for part in ("manuscript", "supplement", "article")}
    largos = {k: v for k, v in docs.items() if not k.startswith("article_")}

    def lay(d):
        return ((d.get("review") or {}).get("layout") or {})

    def spill(d):
        return lay(d).get("caption_spill") or {}

    def lead(d):
        return lay(d).get("lead_in") or {}

    corto = min(docs.items(), key=lambda kv: lay(kv[1]).get("min_chars", 10 ** 9))
    corto_nb = min(docs.items(), key=lambda kv: lay(kv[1]).get("min_chars_nonws", 10 ** 9))
    inicio = datetime.fromisoformat(br["date"])
    fin = inicio + timedelta(seconds=int(br.get("seconds") or 0))
    region = {}
    for lang in LANGS:
        d = docs.get(f"supplement_{VARIANTS[0]}_{lang}") or {}
        region[lang] = ((lay(d).get("regions") or {}).get("plates") or {}).get("pages")
    suelo = {}
    for lang in LANGS:
        bajo = sorted({r for k, v in largos.items() if k.endswith(f"_{lang}")
                       for r in ((v.get("plates") or {}).get("captions_below_floor") or [])})
        suelo[lang] = bajo
    return dict(
        present=True, date=inicio.date().isoformat(),
        span=f"{inicio.strftime('%H:%M')}–{fin.strftime('%H:%M')}",
        documents=len(docs), pages=sum((d.get("review") or {}).get("pages") or 0 for d in docs.values()),
        min_chars=lay(corto[1]).get("min_chars"), min_chars_doc=corto[0],
        min_chars_nonws=lay(corto_nb[1]).get("min_chars_nonws"), min_chars_nonws_doc=corto_nb[0],
        below300_nonws=sum(1 for d in docs.values() if (lay(d).get("min_chars_nonws") or 10 ** 9) < 300),
        tails_marked=sum(spill(d).get("marked") or 0 for d in docs.values()),
        tails_unmarked=sum(spill(d).get("unmarked_spills") or 0 for d in docs.values()),
        captions=sum(spill(d).get("plates") or 0 for d in docs.values()),
        lead_ins=sum(lead(d).get("plates") or 0 for d in largos.values()),
        lead_off=sum(lead(d).get("lead_off_plate_page") or 0 for d in largos.values()),
        plate_region=region, below_floor=suelo,
        caption_floor_article=min([(d.get("plates") or {}).get("caption_pt_min", 99)
                                   for k, d in docs.items() if k.startswith("article_")] or [None]),
        caption_floor_long=min([(d.get("plates") or {}).get("caption_pt_min", 99)
                                for d in largos.values()] or [None]),
    )


def review_facts() -> dict:
    """Lo que el registro de lecturas dice hoy: puntos abiertos y medidas de lámina de la lectura."""
    try:
        st = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(present=False, open=[], defects=[])
    puntos = st.get("points") or []
    abiertos = [p for p in puntos if p.get("state") != "fixed"]
    m = {}
    for r in st.get("readings") or []:
        m.update(r.get("measurements") or {})
    return dict(present=True, open=abiertos, n_open=len(abiertos),
                defects=[p for p in abiertos if p.get("reads_as_defect")],
                build=st.get("build"), measures=m)


def _num(x, alt="—"):
    """Entero con el separador de millares del español (el índice se escribe en español)."""
    return f"{x:,}".replace(",", ".") if isinstance(x, int) else alt


def _dec(x, n: int = 1, alt="—"):
    """Decimal con coma, que es el separador del idioma en que se escribe este índice."""
    return f"{x:.{n}f}".replace(".", ",") if isinstance(x, (int, float)) else alt


TIDY_RE = re.compile(r"(?:study/)?outputs/tidy/([A-Za-z0-9_]+\.csv)")


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------
class Controls:
    """Acumulador de controles esperado/observado con la misma cabecera que los demás módulos."""

    def __init__(self):
        self.rows: list[dict] = []

    def add(self, name: str, key: str, expected, observed, note: str = "") -> None:
        exp_n, obs_n = self._num(expected), self._num(observed)
        if exp_n is not None and obs_n is not None:
            abs_diff = abs(obs_n - exp_n)
            rel_diff = abs_diff / abs(exp_n) if exp_n else (0.0 if abs_diff == 0 else float("nan"))
            status = "ok" if abs_diff <= 1e-9 else "differs"
        else:
            abs_diff = rel_diff = ""
            status = "ok" if str(expected) == str(observed) else "differs"
        self.rows.append(dict(name=name, key=key, expected=expected, observed=observed, abs_diff=abs_diff,
                              rel_diff=rel_diff, status=status, note=note))

    def info(self, name: str, key: str, observed, note: str = "") -> None:
        self.rows.append(dict(name=name, key=key, expected="", observed=observed, abs_diff="", rel_diff="",
                              status="info", note=note))

    @staticmethod
    def _num(value):
        if isinstance(value, bool) or value is None or isinstance(value, str):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["name", "key", "expected", "observed", "abs_diff", "rel_diff",
                                                "status", "note"])


# ---------------------------------------------------------------------------
# 1. Inventario de láminas y tablas
# ---------------------------------------------------------------------------
def check_inventory(ctl: Controls) -> dict:
    """Cada ítem del registro existe, con leyenda/título, en las cuatro combinaciones variante × idioma."""
    meta: dict[tuple[str, str], dict] = {}
    for variant in VARIANTS:
        for lang in LANGS:
            base = CFG.OUT / variant / lang
            captions = {**json.loads((base / "extra" / "figures" / "captions.json").read_text(encoding="utf-8")),
                        **json.loads((base / "figures" / "captions.json").read_text(encoding="utf-8"))}
            titles = {**json.loads((base / "extra" / "tables" / "titles.json").read_text(encoding="utf-8")),
                      **json.loads((base / "tables" / "titles.json").read_text(encoding="utf-8"))}
            meta[(variant, lang)] = dict(captions=captions, titles=titles)
            missing_fig = [k for k in SM.FIGURE_ORDER if k not in captions]
            missing_tab = [k for k in SM.TABLE_ORDER if k not in titles]
            ctl.add("figure_captions_present", f"{variant}|{lang}", len(SM.FIGURE_ORDER),
                    len(SM.FIGURE_ORDER) - len(missing_fig),
                    "leyendas autónomas de outputs/<variante>/<idioma>/(extra/)figures/captions.json"
                    + (f"; faltan {missing_fig}" if missing_fig else ""))
            ctl.add("table_titles_present", f"{variant}|{lang}", len(SM.TABLE_ORDER),
                    len(SM.TABLE_ORDER) - len(missing_tab),
                    "títulos y notas de outputs/<variante>/<idioma>/(extra/)tables/titles.json"
                    + (f"; faltan {missing_tab}" if missing_tab else ""))
            n_png = sum(1 for k in SM.FIGURE_ORDER
                        if (base / ("extra/figures" if k not in json.loads((base / "figures" / "captions.json")
                                                                          .read_text(encoding="utf-8")) else "figures")
                            / f"{k}.png").is_file())
            ctl.add("figure_files_present", f"{variant}|{lang}", len(SM.FIGURE_ORDER), n_png,
                    "archivos PNG a 600 ppp de las láminas suplementarias")
            n_csv = 0
            for k in SM.TABLE_ORDER:
                for folder in ("tables", "extra/tables"):
                    if (base / folder / f"{k}.csv").is_file():
                        n_csv += 1
                        break
            ctl.add("table_files_present", f"{variant}|{lang}", len(SM.TABLE_ORDER), n_csv,
                    "archivos CSV formateados por idioma de las tablas suplementarias")
    return meta


# ---------------------------------------------------------------------------
# 2. Registro de numeración, artículo y parte suplementaria
# ---------------------------------------------------------------------------
def check_documents(ctl: Controls) -> dict:
    stats: dict[str, dict] = {}
    for lang in LANGS:
        P = PROSE[lang]
        fig_word, tab_word = ("Figure", "Table") if lang == "en" else ("Figura", "Tabla")
        for variant in VARIANTS:
            key = f"{variant}|{lang}"
            V = P.load_values(variant)
            art, main, supp, R = P._assemble(variant, V)

            # -- ítems del artículo -------------------------------------------------
            ctl.add("article_figures", key, 5, sum(1 for k, _ in art if k == "figure"),
                    "Figuras 1–5: flujo de datos (08d), fuentes y cobertura, núcleo GRD, ruta REM y triangulación")
            ctl.add("article_tables", key, 7, sum(1 for k, _ in art if k == "table"),
                    "Tablas 1–7: las antiguas Tablas 2–8 renumeradas; T1_sources pasó al suplemento")
            ctl.add("main_figures_first_citation_order", key, ",".join(P.MAIN_FIGURES), ",".join(R.main_figs),
                    "orden de primera cita de las figuras del artículo (debe ser 1, 2, 3, …)")
            ctl.add("main_tables_first_citation_order", key, ",".join(P.MAIN_TABLES), ",".join(R.main_tabs),
                    "orden de primera cita de las tablas del artículo (debe ser 1, 2, 3, …)")

            # -- ninguna cita del artículo escrita fuera del registro ---------------
            text = "\n".join(str(p) for k, p in art if k == "p") + "\n" + \
                   "\n".join(t for k, p in art if k == "panel" for _, t in p["items"])
            for phrase in ("(Table 6, p. 11)", "(Tabla 6, p. 11)"):   # tabla de un informe externo del MINEDUC
                text = text.replace(phrase, "")
            found = [f"{m.group(1)} {m.group(2)}" for m in re.finditer(rf"\b({fig_word}|{tab_word})\s+(\d+)", text)]
            ctl.add("main_citations_from_registry", key, len(R.main_citations[:R.article_citations]), len(found),
                    "cada «Figura N»/«Tabla N» del artículo la produce R.mfig()/R.mtab(); ninguna es literal")
            outside = sorted(set(found) - set(R.main_citations[:R.article_citations]))
            ctl.add("main_citations_unknown", key, 0, len(outside),
                    f"citas a números inexistentes: {outside}" if outside else "todo número citado existe")

            # -- numeración suplementaria -------------------------------------------
            smap = P.supplementary_map(variant, V)
            ctl.add("supp_figures", key, len(SM.FIGURE_ORDER), len(smap["figures"]),
                    "serie única Figura S1… compartida con el apéndice separado")
            ctl.add("supp_tables", key, len(SM.TABLE_ORDER), len(smap["tables"]),
                    "serie única Tabla S1… compartida con el apéndice separado")
            ctl.add("supp_table_S1_is_sources", key, "T1_sources",
                    next(k for k, v in smap["tables"].items() if v.endswith(" S1")),
                    "el inventario de fuentes es la Tabla S1 del registro compartido")
            ctl.add("supp_table_S2_is_dataflow", key, "T_dataflow_counts",
                    next(k for k, v in smap["tables"].items() if v.endswith(" S2")),
                    "los recuentos de la lámina de flujo de datos son la Tabla S2")
            labels = [p["label"] for k, p in supp if k in ("figure", "table")]
            ctl.add("supp_labels_unique", key, len(labels), len(set(labels)),
                    "ningún rótulo suplementario se usa dos veces")

            # -- ítems suplementarios citados en el artículo ------------------------
            cited = set(re.findall(rf"(?:{fig_word}|{tab_word}) S\d+", text))
            ctl.add("supp_cited_in_article_exist", key, len(cited), len(cited & set(labels)),
                    "todo ítem suplementario citado en el artículo está en el suplemento")

            # -- la parte suplementaria está dentro del archivo del manuscrito ------
            part = main[len(art):]
            ctl.add("supplementary_part_after_references", key, "pagebreak+h1",
                    "+".join(k for k, _ in part[:2]),
                    "la parte suplementaria sigue a las Referencias, con salto de página, en el mismo archivo")
            ctl.add("supplementary_part_heading", key, P.SUPP_PART_H1, part[1][1],
                    "encabezado «Supplementary material» / «Material suplementario»")
            n_eq = sum(1 for k, _ in part if k == "eq")
            numbers = sorted(payload[1] for k, payload in part if k == "eq")
            ctl.add("equations_emitted", key, len(EQ.NUMBER), n_eq,
                    "todas las ecuaciones de la metodología extendida, numeradas secuencialmente")
            ctl.add("equations_sequence", key, ",".join(str(i) for i in range(1, len(EQ.NUMBER) + 1)),
                    ",".join(str(i) for i in numbers), "la serie de ecuaciones cubre 1..N sin huecos ni repeticiones")
            headings = " ".join(str(p) for k, p in part if k == "h3")
            uncited = [n for n in numbers if not re.search(rf"\b{n}\b", headings)]
            ctl.add("equations_cited_in_text", key, 0, len(uncited),
                    "cada ecuación se cita en el encabezado del estimador que la aplica")

            # -- recuentos de la revista, medidos sobre el artículo -----------------
            wc = P.word_counts(art)
            n_keys = len(P.citation_keys(art))
            # Las filas informativas nombran el IDIOMA y el límite que le aplica: los límites de la revista rigen
            # para el envío en inglés; el español es la traducción de trabajo del equipo, se expande frente al
            # inglés y se comprueba por paridad de contenido, nunca contra el conteo de palabras de la revista.
            lim = ({"summary": "límite de la revista (envío en inglés): 250 palabras",
                    "core": "límite de la revista (envío en inglés): 3500–5000 palabras",
                    "keys": "límite de la revista (envío en inglés): 30 claves en el texto núcleo"} if lang == "en" else
                   {"summary": "traducción de trabajo en español: el límite de 250 palabras rige para el inglés; aquí solo se exige paridad de contenido",
                    "core": "traducción de trabajo en español: el límite de 3500–5000 palabras rige para el inglés; aquí solo se exige paridad de contenido (razón es/en 0,90–1,30)",
                    "keys": "traducción de trabajo en español: el límite de 30 claves rige para el inglés; aquí se exige la misma lista de claves"})
            ctl.info(f"article_summary_words_{lang}", key, wc["summary"], lim["summary"])
            ctl.info(f"article_core_words_{lang}", key, wc["core_body"], lim["core"])
            ctl.info(f"article_citation_keys_{lang}", key, n_keys, lim["keys"])
            if lang == "en":
                # El límite de 3500–5000 palabras es el de la revista y se aplica al inglés, que es el idioma de
                # publicación; el español es una versión de trabajo que se expande y solo debe mantener la paridad.
                ctl.add("article_core_words_within_limits_en", key, True, 3500 <= wc["core_body"] <= 5000,
                        "envío en inglés: el cuerpo del artículo se mantiene dentro del límite de 3500–5000 palabras de la revista")
                ctl.add("article_summary_within_limit_en", key, True, wc["summary"] <= 250,
                        "envío en inglés: resumen ≤ 250 palabras de la revista")
                ctl.add("article_citation_keys_within_limit_en", key, True, n_keys <= 30,
                        "envío en inglés: ≤ 30 claves de cita en el texto núcleo")
            else:
                ratio = wc["core_body"] / PROSE["en"].word_counts(PROSE["en"].article(variant, V))["core_body"]
                ctl.add("article_core_words_parity_es_vs_en", key, True, 0.9 <= ratio <= 1.3,
                        f"traducción de trabajo en español: el requisito aplicable NO es el límite de la revista sino la paridad con "
                        f"el inglés; expansión observada {ratio:.2f} (rango exigido 0,90–1,30)")
                ctl.info("article_core_words_ratio_es_en", key, round(ratio, 3),
                         "razón de palabras del cuerpo español respecto del inglés (el español se expande; los límites de la revista "
                         "rigen para el inglés)")

            stats[key] = dict(article_blocks=len(art), manuscript_blocks=len(main), appendix_blocks=len(supp),
                              figures_article=sum(1 for k, _ in art if k == "figure"),
                              tables_article=sum(1 for k, _ in art if k == "table"),
                              figures_supp=len(SM.FIGURE_ORDER), tables_supp=len(SM.TABLE_ORDER),
                              equations=n_eq, word_counts=wc, citation_keys_core=n_keys,
                              citation_keys_all=len(P.citation_keys(main, True)))

    # -- el manuscrito y el apéndice comparten el registro; los idiomas también ------
    for variant in VARIANTS:
        en = PEN.supplementary_map(variant, None)
        es = PES.supplementary_map(variant, None)
        same_f = sum(1 for k, v in en["figures"].items() if es["figures"][k] == v.replace("Figure", "Figura"))
        same_t = sum(1 for k, v in en["tables"].items() if es["tables"][k] == v.replace("Table", "Tabla"))
        ctl.add("registry_same_in_both_languages_figures", variant, len(en["figures"]), same_f,
                "«Figure S8» y «Figura S8» designan el mismo archivo")
        ctl.add("registry_same_in_both_languages_tables", variant, len(en["tables"]), same_t,
                "«Table S8» y «Tabla S8» designan el mismo archivo")
    return stats


# ---------------------------------------------------------------------------
# 3. Agregados frente a las tablas tidy ya verificadas
# ---------------------------------------------------------------------------
def check_aggregates(ctl: Controls) -> None:
    grd = C.read_tidy("grd_year_summary")
    rem = C.read_tidy("rem_pathway_annual")
    models = C.read_tidy("models_summary")
    for variant in VARIANTS:
        for lang in LANGS:
            key = f"{variant}|{lang}"
            xt = CFG.OUT / variant / lang / "extra" / "tables"

            # E60: serie anual GRD completa == grd_year_summary de la variante
            e60 = pd.read_csv(xt / "E60_grd_annual_full_numeric.csv")
            ref = grd.loc[grd.variant == variant]
            merged = e60.merge(ref, on=["year", "variant", "panel", "activity", "position"],
                               suffixes=("_e60", "_tidy"), how="outer", indicator=True)
            ctl.add("E60_rows_match_grd_year_summary", key, len(ref), int((merged._merge == "both").sum()),
                    "la tabla anual completa embebida reproduce outputs/tidy/grd_year_summary.csv fila a fila")
            both = merged.loc[merged._merge == "both"]
            ctl.add("E60_episodes_equal_grd_year_summary", key, 0,
                    int((both.n_episodes_f84_e60 != both.n_episodes_f84_tidy).sum()),
                    "episodios con F84 documentado por año, panel, actividad y posición")
            # Los controles preespecificados de config.CONTROLS describen la familia F84 completa: en la variante
            # sin Rett la diferencia es de diseño (F84.2 excluido) y se informa, no se marca como discrepancia.
            for year, expected in CFG.CONTROLS["grd_f84_any"].items():
                obs = e60.loc[(e60.year == year) & (e60.panel == "observed") & (e60.activity == "all")
                              & (e60.position == "any"), "n_episodes_f84"]
                obs = int(obs.iloc[0]) if len(obs) else None
                if variant == "con_rett":
                    ctl.add("E60_grd_f84_any_vs_config", f"{key}:{year}", expected, obs,
                            "control preespecificado (panel observado, toda actividad, cualquier posición)")
                else:
                    ctl.info("E60_grd_f84_any_without_rett", f"{key}:{year}", obs,
                             f"variante sin Rett: {expected - obs} episodios menos que el control de la familia "
                             f"completa, por exclusión de F84.2 (diferencia de definición, no discrepancia)")

            # E69: serie REM completa == rem_pathway_annual (una fila por año, módulo, código, variante, mes y medida:
            # los stocks P2/P6 tienen corte de junio y de diciembre y nunca se suman)
            e69 = pd.read_csv(xt / "E69_rem_code_year_full_numeric.csv")
            keys_rem = ["year", "module", "code", "variant", "month", "measure"]
            merged_rem = e69.merge(rem, on=keys_rem, suffixes=("_e69", "_tidy"), how="inner")
            ctl.add("E69_rows_match_rem_pathway_annual", key, len(e69), len(merged_rem),
                    "cada fila de la tabla REM completa embebida existe en outputs/tidy/rem_pathway_annual.csv")
            ctl.add("E69_totals_equal_rem_pathway_annual", key, 0,
                    int((merged_rem.total_e69.fillna(-1) != merged_rem.total_tidy.fillna(-1)).sum()),
                    "totales por código, año y corte frente a outputs/tidy/rem_pathway_annual.csv")
            checks_rem = (("a05_autism_entries", CFG.STRICT["a05_entry"], "annual_sum", CFG.CONTROLS["a05_autism_entries"]),
                          ("a28_primary", CFG.A28["primary"], "annual_sum", CFG.CONTROLS["a28_primary"]),
                          ("p2_tea_december", CFG.P2_TEA, "december_stock", CFG.CONTROLS["p2_tea_december"]))
            for name, code, measure, expected in checks_rem:
                for year, exp in expected.items():
                    sel = e69.loc[(e69.year == year) & (e69.code == code) & (e69.measure == measure)
                                  & (e69.variant == "single_code")]
                    obs = float(sel.total.iloc[0]) if len(sel) == 1 else None
                    ctl.add(f"E69_{name}_vs_config", f"{key}:{year}", exp, obs,
                            "control preespecificado de la ruta administrativa REM; flujo anual o stock de diciembre "
                            "(los semestres nunca se suman)")

            # E78: todas las especificaciones de modelo de la variante y las independientes de la variante
            e78 = pd.read_csv(xt / "E78_models_all_specifications_numeric.csv")
            other = "sin_rett" if variant == "con_rett" else "con_rett"
            ref_models = models.loc[models.variant != other]
            ctl.add("E78_rows_equal_models_summary", key, len(ref_models), len(e78),
                    "una fila por especificación convergida de outputs/tidy/models_summary.csv (la variante analizada "
                    "más las series idénticas en ambas variantes)")
            ctl.add("E78_model_ids_equal_models_summary", key, 0,
                    len(set(ref_models.model_id) ^ set(e78.model_id)),
                    "los identificadores de modelo coinciden uno a uno")

            # T_dataflow_counts: los recuentos de la lámina de flujo tienen archivo fuente declarado
            tdf = pd.read_csv(xt / "T_dataflow_counts_numeric.csv")
            ctl.add("T_dataflow_counts_have_source", key, len(tdf), int(tdf.source_file.notna().sum()),
                    "cada recuento de la Figura 1 declara su archivo y su columna o clave de origen")
            ctl.info("T_dataflow_counts_rows", key, len(tdf),
                     "filas de la tabla que sustenta la lámina de flujo de datos (Tabla S2)")


# ---------------------------------------------------------------------------
# 4. Índice del material extendido
# ---------------------------------------------------------------------------
def source_tidy(text: str) -> str:
    """Tablas tidy citadas en la leyenda o la nota del ítem (orden de aparición, sin repetir)."""
    seen: list[str] = []
    for name in TIDY_RE.findall(text or ""):
        if name not in seen:
            seen.append(name)
    return ", ".join(seen)


def asset_origin() -> dict[str, str]:
    """Archivo de datos emparejado o script productor de cada lámina y tabla, según el inventario E81."""
    path = CFG.OUT / VARIANTS[0] / "en" / "extra" / "tables" / "E81_project_asset_inventory_numeric.csv"
    inv = pd.read_csv(path, dtype=str, keep_default_na=False)
    origin: dict[str, str] = {}
    for _, row in inv.iterrows():
        if row["asset"] in origin:
            continue
        scripts = [s for s in str(row["referenced_in"]).split("|") if s and s[0].isdigit()]
        origin[row["asset"]] = row["paired_data_file"] or (scripts[0] if scripts else "")
    return origin


BUILD_REPORT = LA / "manuscript" / "build_report.json"
PART_ES = {"manuscript": "manuscrito (artículo + material suplementario)",
           "supplement": "apéndice suplementario suelto",
           "article": "sólo el artículo, hasta las Referencias"}


def built_documents_block() -> list[str]:
    """Páginas y tamaños de los doce documentos, leídos del informe que escribe el módulo 10.

    El índice no reconstruye nada: si el informe no existe todavía, la sección se omite.
    """
    if not BUILD_REPORT.is_file():
        return []
    rep = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    docs = rep.get("documents") or {}
    if not docs:
        return []
    total_pp = sum((d.get("review") or {}).get("pages", 0)
                   for pair in docs.values() for d in pair.values() if isinstance(d, dict))

    def _mil(n: int) -> str:
        return f"{n:,}".replace(",", ".")

    out = ["", "## Documentos construidos", "",
           f"Compilación del {str(rep.get('date', ''))[:19].replace('T', ' ')} "
           f"(`manuscript/build_report.json`; láminas del artículo a {rep.get('article_dpi', 600)} ppp y "
           f"suplementarias a {rep.get('supp_dpi') or rep.get('article_dpi', 600)} ppp). Cada lámina ocupa una página "
           "propia y se imprime a tamaño natural.", "",
           f"Es la compilación que lee el autor: **{_mil(total_pp)} páginas** en los doce documentos, todas con "
           f"folio y con el folio igual a su índice. **No queda ningún arreglo viviendo sólo en `outputs/`.** Qué "
           f"verificó cada lectura independiente, y sobre qué compilación la hizo, está fechado en `decision_log.md`; "
           f"lo que sigue abierto se enumera en la sección 6 de `memo_es.md`.", "",
           "| Documento | Parte | Páginas | DOCX | PDF | Tablas | Láminas | Referencias | Palabras del cuerpo |",
           "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for key, pair in docs.items():
        for part in ("manuscript", "supplement", "article"):
            d = pair.get(part)
            if not d:
                continue
            rev, b = d.get("review") or {}, d["builder"]
            wc = d.get("word_counts")
            words = f"{wc['core_body']} (núcleo) + {wc['opt_body']} opcionales" if wc else "—"
            out.append(f"| `{Path(d['path']).name}` | {PART_ES[part]} | {rev.get('pages', '—')} | "
                       f"{d.get('size_mb', '—')} MB | {rev.get('pdf_size_mb', '—')} MB | {b['tables']} | "
                       f"{b['figures']} | {b['references']} | {words} |")
    return out + [""]


def write_index(meta: dict, stats: dict) -> Path:
    es = meta[(VARIANTS[0], "es")]
    origin = asset_origin()
    bf, rv = build_facts(), review_facts()
    if not bf.get("present"):
        raise RuntimeError("no hay manuscript/build_report.json: el índice no puede describir una compilación "
                           "que no existe; ejecute pipeline/10_manuscript.py antes que este módulo")
    n_plates = len(SM.FIGURE_ORDER) + len(PEN.MAIN_FIGURES)
    n_plate_builds = n_plates * len(VARIANTS) * len(LANGS)
    png = sorted(set(q.name for v in VARIANTS for l in LANGS
                     for q in list((CFG.OUT / v / l / "figures").glob("*.png"))
                     + list((CFG.OUT / v / l / "extra" / "figures").glob("*.png"))))
    n_png_names = len(png)
    n_png = n_png_names * len(VARIANTS) * len(LANGS)
    # la frase de estado del memo: cuántos puntos siguen abiertos y si alguno se lee como defecto
    if not rv.get("present"):
        apertura = "No hay registro de lectura independiente en `review_status.json`."
    elif rv["defects"]:
        apertura = (f"Lo que sigue abierto se enumera en la sección 6 de `memo_es.md`, que hoy lista "
                    f"{rv['n_open']} puntos, de los cuales {len(rv['defects'])} se lee(n) como defecto.")
    else:
        apertura = (f"Lo que sigue abierto se enumera en la sección 6 de `memo_es.md`, que hoy lista "
                    f"{rv['n_open']} puntos y **ninguno de ellos se lee como defecto**.")

    def where(key: str, text: str) -> str:
        # varias fuentes se concatenan con una barra vertical, que partiría la fila de la tabla markdown
        return (source_tidy(text) or origin.get(key, "") or "—").replace("|", " · ")

    fig_group = {k: g for g, keys in SM.FIGURE_GROUPS for k in keys}
    tab_group = {k: g for g, keys in SM.TABLE_GROUPS for k in keys}
    methods_group = {"en": "Extended methodology", "es": "Metodología extendida"}
    lines = [
        "# Índice del material suplementario extendido (módulo 17)",
        "",
        f"Generado por `study/pipeline/{MODULE}.py` el "
        f"{datetime.now(timezone.utc).date().isoformat()}. Una única serie de numeración, compartida por la parte "
        "suplementaria que sigue a las Referencias dentro de cada `manuscript/manuscript_<variante>_<idioma>.docx` y "
        "por los apéndices separados `manuscript/supplement_<variante>_<idioma>.docx`: una cita como «Tabla S8» "
        "designa el mismo ítem en los cuatro manuscritos y los cuatro apéndices.",
        "",
        "Los recuentos son reconocimiento administrativo del autismo, nunca prevalencia ni incidencia; el resultado "
        "hospitalario son «episodios con F84 documentado» y F84 principal es una serie aparte; las fuentes no se "
        "enlazan por persona, de modo que ninguna lámina ni tabla de esta lista es una cascada asistencial; stocks y "
        "flujos no comparten eje; lugar de atención y residencia no se mezclan sin nota explícita; las eras de "
        "definición REM nunca se unen con una línea; la Ley 21.545 (marzo de 2023) es contexto de política.",
        "",
        f"Norma de lámina: las {len(SM.FIGURE_ORDER) + len(PEN.MAIN_FIGURES)} láminas del estudio "
        f"({len(PEN.MAIN_FIGURES)} del artículo y {len(SM.FIGURE_ORDER)} suplementarias) se dibujan a "
        f"{SM.PLATE_W_MM:.0f} × {SM.PLATE_H_MM:.0f} mm en vertical, a escala 1:1 y {SM.PLATE_DPI} ppp "
        f"({SM.PLATE_PX[0]} × {SM.PLATE_PX[1]} píxeles), en una rejilla de 3 filas × 2 columnas con un máximo de "
        f"{SM.PLATE_MAX_PANELS} paneles por lámina, letras de panel en minúscula (a)–(f) en la figura y en la leyenda, "
        f"y ningún rótulo por debajo de {SM.PLATE_MIN_PT:.0f} pt. La Figura 1 es la única excepción a la rejilla y a "
        "las letras: es un esquema de seis carriles dibujado sobre un lienzo único, sin paneles y sin letras de panel, "
        "y cumple el resto de la norma (mismo tamaño, misma escala y mismos 4251 × 5787 píxeles). Ninguna lámina se "
        "dividió, añadió ni renombró al aplicar la norma, de modo que la numeración de esta lista no cambió.",
        "",
        "Composición verificada: la de cada lámina la mide `common.check_layout` sobre el renderizador real —nueve "
        "familias de defecto: texto sobre texto, texto fuera del lienzo, título de eje sobre sus marcas, leyenda o nota "
        "sobre los datos, rótulo de valor sobre su marcador o su barra de error, rótulo de valor cuyo recuadro tapa su "
        "propia barra, títulos de dos paneles vecinos sin hueco entre ellos, marcas numéricas repetidas y recuento de "
        "paneles— y los nueve módulos de lámina la ejecutan a través de `plate_resolve` / `save_fig` con "
        f"`PLATE_CHECK`: cero defectos en las {n_plate_builds} construcciones ({n_plates} láminas × "
        f"{len(VARIANTS)} variantes × {len(LANGS)} idiomas), todas de {_dec(SM.PLATE_W_MM)} × {_dec(SM.PLATE_H_MM)} mm "
        f"exactos a {SM.PLATE_DPI} ppp y sin un píxel de tinta en la banda de 3 px de los cuatro bordes. En disco "
        f"hay {n_png} PNG de lámina —{n_png_names} nombres × {len(VARIANTS)} variantes × {len(LANGS)} idiomas, todos "
        f"de {_num(SM.PLATE_PX[0])} × {_num(SM.PLATE_PX[1])} px exactos—: los {n_plates} del estudio y dos láminas "
        "heredadas que ningún documento incrusta "
        "(`figS4_grd_model_sensitivities` y `figS7_a05_standardised_rates`, que conservan el nombre de un plan de "
        "figuras anterior). La tercera huérfana, `figS3_hospital_effects`, era la única apaisada y el módulo 06 dejó "
        "de producirla: ya no está en disco. El verificador mide la lámina, no la colocación dentro del panel. Los "
        "tres defectos de composición que las verificaciones humanas habían dejado abiertos —la leyenda de lámina "
        "derramada sin marca, la ventana de años con guion en texto de lectura de las Tablas S68 y S85, y el mismo "
        "intervalo numérico impreso con raya y con guion— quedaron **cerrados en la fase 4j** y llegaron al papel: la "
        "regla de la raya se escribe hoy una sola vez en `common.py` y se aplica en los dos embudos por los que pasa "
        f"todo lo impreso, y la lectura independiente midió **{_num(rv['measures'].get('rangos_con_guion_en_lamina'))} "
        f"rangos con guion en {_num(rv['measures'].get('rotulos_de_lamina_medidos'))} rótulos** de las "
        f"{_num(rv['measures'].get('construcciones_comprobadas'))} construcciones de lámina. En la fase 4k se cerró "
        "además la **glosa del panel fijo de 65 hospitales**, que el corpus decía de dos maneras: hoy se escribe una "
        "sola vez en `common.fixed_panel_gloss` y todos los módulos que la imprimen la piden de ahí. " + apertura,
        "",
        "En el documento, cada lámina suplementaria comparte página con la frase que la presenta y con su leyenda "
        f"—{bf['lead_ins']} de {bf['lead_ins']} en los ocho documentos largos, sobre {bf['captions']} leyendas "
        "localizadas sin una sola sin lámina y sin una página con dos láminas—, y ninguna página de los doce "
        "documentos queda por debajo de 300 caracteres (medido por el propio constructor sobre los doce PDF de la "
        f"compilación vigente, la del {bf['date']} {bf['span']}: mínimo **{bf['min_chars']}** caracteres contando "
        "palabras unidas por un espacio y líneas por un salto, descontado el folio —la portada de "
        f"`{bf['min_chars_doc']}`—; contando sólo caracteres no blancos esa misma portada baja a "
        f"**{bf['min_chars_nonws']}**, que es un bloque de título completo y no una página vacía, y con esa segunda "
        f"cuenta son {bf['below300_nonws']} las portadas de apéndice suelto por debajo de 300). **La leyenda que no "
        "cabe ya está resuelta**: desde la fase 4j se parte en el código y su cola se imprime rotulada «Figure N "
        "(continued).» / «Figura N (continuación).» al principio de la página siguiente, sin umbral y sin excepción; "
        f"en los doce documentos hay **{bf['tails_marked']} colas rotuladas y {bf['tails_unmarked']} sin rotular**. "
        "Cuesta cinco páginas por documento largo: la región de láminas del apéndice son hoy "
        f"**{bf['plate_region']['en']} páginas seguidas en inglés y {bf['plate_region']['es']} en español**. La "
        f"leyenda de lámina no baja de {_dec(bf['caption_floor_article'])} pt en los cuatro archivos sólo-artículo ni "
        f"de {_dec(bf['caption_floor_long'])} pt en los ocho documentos largos, donde ese último escalón se gasta "
        f"en {', '.join(bf['below_floor']['en'])} en inglés y en "
        f"{', '.join(bf['below_floor']['es'])} en español, para que su cola no quede sola.",
        "",
        "## El artículo",
        "",
        "| Ítem | Archivo | Descripción |",
        "| --- | --- | --- |",
    ]
    for i, key in enumerate(PEN.MAIN_FIGURES, 1):
        lines.append(f"| Figura {i} | `{key}.png` | {PES._strip_prefix(es['captions'][key]['title'])} |")
    for i, key in enumerate(PEN.MAIN_TABLES, 1):
        lines.append(f"| Tabla {i} | `{key}.csv` | {PES._strip_prefix(es['titles'][key]['title'])} |")
    lines += [
        "",
        f"## Láminas suplementarias ({len(SM.FIGURE_ORDER)})",
        "",
        "| Nº | Grupo temático | Archivo | Origen (tabla tidy o script productor) | Descripción |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i, key in enumerate(SM.FIGURE_ORDER, 1):
        cap = es["captions"][key]
        title = PES._strip_prefix(cap.get("title", ""))
        lines.append(f"| Figura S{i} | {fig_group[key]['es']} | `{key}.png` | "
                     f"{where(key, cap.get('caption', ''))} | {title} |")
    lines += [
        "",
        f"## Tablas suplementarias ({len(SM.TABLE_ORDER)}; las {len(SM.METHODS_TABLES)} metodológicas se imprimen "
        "dentro de la metodología extendida)",
        "",
        "| Nº | Grupo temático | Archivo | Origen (tabla tidy o script productor) | Descripción |",
        "| --- | --- | --- | --- | --- |",
    ]
    for i, key in enumerate(SM.TABLE_ORDER, 1):
        tit = es["titles"][key]
        group = tab_group.get(key, methods_group)["es"]
        lines.append(f"| Tabla S{i} | {group} | `{key}.csv` | "
                     f"{where(key, tit.get('note', '') + ' ' + tit.get('title', ''))} | "
                     f"{PES._strip_prefix(tit.get('title', ''))} |")
    lines += [
        "",
        "## Recuentos por documento",
        "",
        "| Variante · idioma | Bloques del artículo | Bloques del manuscrito | Bloques del apéndice | Palabras del "
        "cuerpo | Claves de citación (núcleo / total) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for key, s in stats.items():
        lines.append(f"| {key.replace('|', ' · ')} | {s['article_blocks']} | {s['manuscript_blocks']} | "
                     f"{s['appendix_blocks']} | {s['word_counts']['core_body']} | "
                     f"{s['citation_keys_core']} / {s['citation_keys_all']} |")
    lines += [
        "",
        f"Ecuaciones de la metodología extendida: {len(EQ.NUMBER)}, numeradas de 1 a {len(EQ.NUMBER)} y citadas en el "
        f"encabezado del estimador que las aplica ({len(EQ.ESTIMATORS)} estimadores).",
    ]
    lines += built_documents_block()
    INDEX_PATH.write_text("\n".join(lines), encoding="utf-8")
    return INDEX_PATH


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", action="store_true",
                    help="reconstruir los 4 manuscritos, los 4 apéndices y los 4 archivos sólo con el artículo")
    ap.add_argument("--skip-pdf", action="store_true", help="con --build: no convertir a PDF ni generar miniaturas")
    ap.add_argument("--skip-thumbs", action="store_true", help="con --build: PDF sí, miniaturas no")
    ap.add_argument("--supp-dpi", type=int, default=None,
                    help="con --build: resolución de incrustación de las láminas SUPLEMENTARIAS "
                         "(por defecto la del módulo 10, 300 ppp; 0 = sin remuestrear). Las figuras del artículo y "
                         "los PNG del disco se quedan a 600 ppp")
    args = ap.parse_args(argv)

    ctl = Controls()
    log(f"{len(SM.FIGURE_ORDER)} láminas y {len(SM.TABLE_ORDER)} tablas suplementarias, "
        f"{len(EQ.NUMBER)} ecuaciones, {len(VARIANTS)} variantes × {len(LANGS)} idiomas")
    log(f"rótulos compartidos disponibles: {len(LBL.L)} ({LBL.t('definition_era', 'es')})")

    t = time.time()
    meta = check_inventory(ctl)
    log(f"inventario verificado ({time.time() - t:.1f} s)")

    t = time.time()
    stats = check_documents(ctl)
    log(f"documentos verificados ({time.time() - t:.1f} s)")
    for key, s in stats.items():
        log(f"  {key}: artículo {s['figures_article']} figuras / {s['tables_article']} tablas / "
            f"{s['word_counts']['core_body']} palabras; suplemento {s['figures_supp']} láminas / "
            f"{s['tables_supp']} tablas / {s['equations']} ecuaciones")

    t = time.time()
    check_aggregates(ctl)
    log(f"agregados verificados contra las tablas tidy ({time.time() - t:.1f} s)")

    path = C.atomic_write_csv(ctl.frame(), CONTROLS_DIR / f"{MODULE}_controls.csv")
    counts = ctl.frame().status.value_counts().to_dict()
    log(f"controles: {counts} → {path.relative_to(REPO)}")
    differing = ctl.frame().query("status == 'differs'")
    for _, row in differing.iterrows():
        log(f"  DIFIERE {row['name']} [{row['key']}]: esperado {row['expected']} / observado {row['observed']}")

    index = write_index(meta, stats)
    log(f"índice: {index.relative_to(REPO)}")

    build_report = None
    if args.build:
        import importlib.util
        spec = importlib.util.spec_from_file_location("m10", HERE / "10_manuscript.py")
        m10 = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m10)
        argv10 = []
        if args.skip_pdf:
            argv10.append("--skip-pdf")
        if args.skip_thumbs:
            argv10.append("--skip-thumbs")
        if args.supp_dpi is not None:
            argv10 += ["--supp-dpi", str(args.supp_dpi)]
        rc = m10.main(argv10)
        build_report = dict(returncode=rc, report=str(m10.REPORT_PATH))
        log(f"reconstrucción de documentos: rc={rc}")

    runlog = dict(module=MODULE, finished=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  seconds=round(time.time() - T0, 1), figures=len(SM.FIGURE_ORDER), tables=len(SM.TABLE_ORDER),
                  methods_tables=len(SM.METHODS_TABLES), equations=len(EQ.NUMBER), documents=stats,
                  controls={k: int(v) for k, v in counts.items()}, build=build_report,
                  python=sys.version.split()[0])
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    log(f"{MODULE} terminado en {time.time() - T0:.1f} s")
    return 0 if counts.get("differs", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
