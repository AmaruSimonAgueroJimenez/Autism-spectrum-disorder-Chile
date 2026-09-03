"""Shared presentation helpers; analytical transformations live in the QMDs."""
from pathlib import Path
from html import escape
import numbers

import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import HTML, display

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output_files" / "consolidacion"
POSITION_LABELS = {
    "principal": "Principal",
    "solo_secundario": "Solo secundario",
    "principal_y_secundario": "Principal y secundario",
    "mixto_mismo_dia": "Posiciones mixtas el mismo día",
}
GROUP_LABELS = {
    "Animo_ansiedad_estres": "Ánimo, ansiedad y estrés",
    "Epilepsia": "Epilepsia",
    "Signos_desarrollo_habla": "Signos del desarrollo y del habla",
    "Lenguaje_aprendizaje_desarrollo": "Lenguaje, aprendizaje y desarrollo",
    "Conducta_emociones_infancia": "Conducta y emociones en la infancia",
    "Discapacidad_intelectual": "Discapacidad intelectual",
    "Hiperactividad_atencion": "Hiperactividad y atención",
    "Psicosis": "Psicosis",
    "Audicion": "Audición",
}
AGE_GROUPS = [f"{i}-{i + 4}" for i in range(0, 80, 5)] + ["80+"]
COLORS = ["#167482", "#405d99", "#b9783c", "#738779"]


def read_result(name: str) -> pd.DataFrame:
    path = OUTPUT / name
    if not path.is_file():
        raise FileNotFoundError(
            f"Falta {path.name}. Ejecute las extracciones indicadas en el README antes de renderizar."
        )
    return pd.read_csv(path, dtype={
        "code": str, "CodigoPrestacion": str, "IdRegion": str,
        "first_principal": str, "last_prior_principal": str,
    })


def number(value, decimals=0):
    if pd.isna(value):
        return "—"
    if isinstance(value, numbers.Number):
        return f"{value:,.{decimals}f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return str(value)


def show_table(frame: pd.DataFrame, caption: str, decimals=None):
    """Escaped, scrollable tables; column-specific precision keeps years integral."""
    decimals = decimals or {}
    formatters = {c: (lambda v, d=decimals.get(c, 0): number(v, d)) for c in frame.columns}
    for column in ["Año", "Año inicial", "Año final", "Mes"]:
        if column in frame.columns:
            formatters[column] = lambda v: "—" if pd.isna(v) else str(int(v))
    table = frame.to_html(index=False, escape=True, border=0, na_rep="—", formatters=formatters,
                          classes="table table-striped table-sm")
    caption_html = f"<caption>{escape(caption)}</caption>"
    table = table.replace("<thead>", caption_html + "<thead>", 1)
    display(HTML(f'<div class="analysis-table" role="region" aria-label="{escape(caption)}" tabindex="0">{table}</div>'))


def kpis(items):
    cards = "".join(f'<div class="metric"><strong>{escape(str(value))}</strong><span>{escape(label)}</span></div>'
                    for value, label in items)
    display(HTML(f'<div class="metrics">{cards}</div>'))


def plot_style():
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.titleweight": "bold", "figure.dpi": 130, "savefig.dpi": 170})


def share(numerator, denominator):
    return 100 * numerator / denominator if denominator else float("nan")
