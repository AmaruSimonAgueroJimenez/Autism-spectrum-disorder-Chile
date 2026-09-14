# -*- coding: utf-8 -*-
"""controls_registry.py — fuente ÚNICA de los totales de control que los documentos citan sobre sí mismos.

Problema que resuelve (defecto 9 de la revisión página a página): el mismo estudio declaraba tres
totales de control distintos, sin rótulo que los distinguiera, en el mismo archivo:

  * la lámina de flujo de datos (Figura 1) y la Tabla S2 decían «1.280 comprobaciones en 13 módulos»,
    porque `controls_summary.csv` se había escrito en una corrida en la que solo existían los archivos
    de control de los módulos 00 a 09b;
  * la metodología extendida decía «5.835 comprobaciones» porque sumaba los 22 archivos
    `outputs/controls/*_controls.csv` presentes en el disco;
  * los métodos suplementarios breves decían «205 controles indicador-año».

Los tres son correctos, pero cuentan cosas distintas. Este módulo declara esos conjuntos como ÁMBITOS
con nombre, expone UNA función —`totals(scope)`— que devuelve sus totales y UNA función —`phrase(scope,
lang)`— que devuelve el ámbito escrito en palabras, de modo que ningún documento pueda imprimir un
total sin decir de qué habla.

Ámbitos
-------
  `pipeline`       todas las filas de todos los archivos `<módulo>_controls.csv` del pipeline
                   (módulos 00 a 17), consolidadas por el módulo 07 en `controls_summary.csv` con
                   `scope = "pipeline"`.
  `analysis_plan`  las filas indicador-año de la tabla de controles preespecificados del plan de
                   análisis (config.CONTROLS × año/clave, más las filas de comprobación y las
                   diferencias de los módulos que construyen los conjuntos analíticos, 00 a 09b),
                   consolidadas en el mismo archivo con `scope = "analysis_plan"`.

Un ámbito NO es un subconjunto del otro fila a fila: la tabla del plan de análisis reexpresa filas de
los módulos (una fila por indicador y año, con filas de comprobación añadidas), por lo que sus totales
no se suman a los del pipeline y nunca deben presentarse juntos sin su rótulo.

Uso:
    import controls_registry as CR
    t = CR.totals("pipeline")            # {'checks': 5835, 'ok': …, 'info': …, 'differs': …, 'files': 22, …}
    CR.phrase("pipeline", "en")          # 'across the 22 control files of the whole pipeline'
    CR.phrase("analysis_plan", "es")     # 'para los controles indicador-año del plan de análisis'

Este módulo no escribe nada: solo lee `outputs/controls/controls_summary.csv` (y, si ese archivo aún
no tiene columna `scope`, cae en las fuentes históricas para no romper una corrida a medio camino).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
CONTROLS_DIR = HERE / "outputs" / "controls"
SUMMARY_PATH = CONTROLS_DIR / "controls_summary.csv"
# Respaldo histórico del ámbito `analysis_plan` cuando controls_summary.csv todavía no lo trae.
PLAN_FALLBACK = HERE / "outputs" / "con_rett" / "en" / "tables" / "T8_controls_numeric.csv"

PIPELINE = "pipeline"
ANALYSIS_PLAN = "analysis_plan"

#: Módulos cuyas filas de control pueden entrar en la tabla del plan de análisis. Son los módulos que
#: construyen los conjuntos analíticos y las láminas y tablas del artículo; los módulos de material
#: extendido (11 a 17) se cuentan en el ámbito `pipeline` y no en el del plan.
PLAN_MODULES: list[str] = ["00_provenance", "01_grd_core", "01b_deis_egresos", "02_rem_pathway",
                           "03_denominators", "04_surveys", "05_education", "06_models",
                           "08b_figures_rem", "08c_figures_triangulation", "08d_figure_dataflow",
                           "09a_tables_main", "09b_tables_supplementary"]

SCOPES: dict[str, dict] = {
    PIPELINE: {
        # {n} = número de archivos `<módulo>_controls.csv` consolidados.
        "phrase": {"en": "across the {n} control files of the whole pipeline",
                   "es": "en los {n} archivos de control de todo el pipeline"},
        "short": {"en": "whole pipeline", "es": "todo el pipeline"},
        # forma breve, para cuando el rótulo va pegado al sustantivo que cuenta ("N checks of the whole pipeline")
        "label": {"en": "of the whole pipeline", "es": "de todo el pipeline"},
        "unit": {"en": "checks", "es": "comprobaciones"},
        "source": "outputs/controls/controls_summary.csv (scope=pipeline)",
    },
    ANALYSIS_PLAN: {
        "phrase": {"en": "for the indicator-year controls of the analysis plan",
                   "es": "para los controles indicador-año del plan de análisis"},
        "short": {"en": "analysis plan", "es": "plan de análisis"},
        "label": {"en": "of the analysis plan", "es": "del plan de análisis"},
        "unit": {"en": "controls", "es": "controles"},
        "source": "outputs/controls/controls_summary.csv (scope=analysis_plan)",
    },
}

_CACHE: dict[str, dict] = {}


def scopes() -> list[str]:
    """Nombres de ámbito válidos, en el orden en que se documentan."""
    return list(SCOPES)


def _read_summary(path: Path | None = None) -> pd.DataFrame:
    p = Path(path) if path is not None else SUMMARY_PATH
    if not p.is_file():
        raise FileNotFoundError(f"Falta {p}; ejecute study/pipeline/07_controls.py.")
    df = pd.read_csv(p, dtype=str, keep_default_na=False, encoding="utf-8")
    if "scope" not in df.columns:            # archivo anterior a la consolidación por ámbito
        df["scope"] = PIPELINE
    if "module" not in df.columns:
        df["module"] = ""
    if "status" not in df.columns:
        df["status"] = ""
    return df


def _counts(df: pd.DataFrame, scope: str, source: str) -> dict:
    st = df["status"].astype(str).str.strip().str.lower()
    known = {"ok", "info", "differs", "missing"}
    return dict(
        scope=scope,
        checks=int(len(df)),
        ok=int((st == "ok").sum()),
        info=int((st == "info").sum()),
        differs=int((st == "differs").sum()),
        missing=int((st == "missing").sum()),
        other=int((~st.isin(known)).sum()),
        modules=int(df["module"].astype(str).nunique()),
        files=int(df["module"].astype(str).nunique()),
        source=source,
        phrase_en=SCOPES[scope]["phrase"]["en"].format(n=int(df["module"].astype(str).nunique())),
        phrase_es=SCOPES[scope]["phrase"]["es"].format(n=int(df["module"].astype(str).nunique())),
    )


def totals(scope: str = PIPELINE, path: Path | None = None, refresh: bool = False) -> dict:
    """Totales del ámbito pedido: checks, ok, info, differs, missing, modules, files y su rótulo en palabras.

    En el ámbito `pipeline` un módulo equivale a un archivo `<módulo>_controls.csv`, de modo que
    `modules` y `files` coinciden por construcción. En `analysis_plan` `files` es el número de módulos
    que aportan filas al plan y solo se usa para trazabilidad, nunca se imprime.
    """
    if scope not in SCOPES:
        raise KeyError(f"ámbito de control desconocido: {scope!r}; válidos: {', '.join(SCOPES)}")
    if not refresh and scope in _CACHE and path is None:
        return dict(_CACHE[scope])
    df = _read_summary(path)
    sub = df.loc[df["scope"].astype(str) == scope]
    if sub.empty and scope == ANALYSIS_PLAN and PLAN_FALLBACK.is_file():
        # corrida a medio camino: el consolidado aún no trae el ámbito del plan
        sub = pd.read_csv(PLAN_FALLBACK, dtype=str, keep_default_na=False, encoding="utf-8")
        out = _counts(sub, scope, str(PLAN_FALLBACK.relative_to(HERE.parent)))
    else:
        out = _counts(sub, scope, SCOPES[scope]["source"])
    if path is None:
        _CACHE[scope] = dict(out)
    return out


def phrase(scope: str, lang: str, path: Path | None = None) -> str:
    """El ámbito escrito en palabras, con el número de archivos ya sustituido."""
    if scope not in SCOPES:
        raise KeyError(f"ámbito de control desconocido: {scope!r}; válidos: {', '.join(SCOPES)}")
    return totals(scope, path)[f"phrase_{lang}"]


def phrase_template(scope: str, lang: str, token: str = "{n}") -> str:
    """El ámbito en palabras dejando el número de archivos como marcador `token`.

    Lo usa la lámina de flujo de datos, donde toda cifra impresa debe salir de su propio registro de
    recuentos (`{e_controls_modules}`) y no puede escribirse en el texto.
    """
    if scope not in SCOPES:
        raise KeyError(f"ámbito de control desconocido: {scope!r}; válidos: {', '.join(SCOPES)}")
    return SCOPES[scope]["phrase"][lang].replace("{n}", token)


def short(scope: str, lang: str) -> str:
    """Nombre breve del ámbito, para encabezados de tabla y rótulos de columna."""
    return SCOPES[scope]["short"][lang]


def label(scope: str, lang: str) -> str:
    """Rótulo breve del ámbito pegado al sustantivo que se cuenta («N controls of the analysis plan»).

    Es la misma distinción que `phrase()`, en la forma corta que exige el texto núcleo del artículo, donde el
    límite de palabras de la revista no deja espacio para la frase completa. Nunca se imprime un total sin uno
    de los dos rótulos.
    """
    if scope not in SCOPES:
        raise KeyError(f"ámbito de control desconocido: {scope!r}; válidos: {', '.join(SCOPES)}")
    return SCOPES[scope]["label"][lang]


def all_totals(path: Path | None = None, refresh: bool = False) -> dict[str, dict]:
    return {s: totals(s, path, refresh) for s in SCOPES}


if __name__ == "__main__":  # diagnóstico
    for _s, _t in all_totals(refresh=True).items():
        print(f"{_s:14s} {_t['checks']:6d} checks | ok {_t['ok']:5d} | info {_t['info']:4d} | "
              f"differs {_t['differs']:3d} | modules {_t['modules']:3d}")
        print(f"               en: {_t['phrase_en']}")
        print(f"               es: {_t['phrase_es']}")
