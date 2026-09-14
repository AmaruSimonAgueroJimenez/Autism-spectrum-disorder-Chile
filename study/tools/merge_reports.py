# -*- coding: utf-8 -*-
"""merge_reports.py — integra los informes estructurados de los agentes (JSON) en la documentación del proyecto.

    python study/tools/merge_reports.py reports_phase1.json

Escribe/actualiza: variables_dictionary.md (una sección por tabla tidy), outputs/controls/controls_summary.csv
(esperado frente a observado de todos los módulos) y añade filas a decision_log.md (decisiones e incidencias
reportadas por cada módulo), sin duplicar entradas ya presentes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]


def main(path: str) -> None:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    items = payload if isinstance(payload, list) else payload.get("results", payload)
    variables, controls, decisions, issues, verdicts = [], [], [], [], []
    for item in items:
        report = item.get("report", item)
        module = report.get("module", item.get("module", "?"))
        for v in report.get("variables", []):
            variables.append(dict(module=module, **v))
        for c in report.get("controls", []):
            controls.append(dict(module=module, **c))
        for d in report.get("decisions", []):
            decisions.append((module, d))
        for i in report.get("issues", []):
            issues.append((module, i))
        if item.get("verdict"):
            verdicts.append((module, item["verdict"]))
    # Diccionario de variables
    lines = ["# Diccionario de variables derivadas (tablas tidy de `outputs/tidy/`)", "",
             "Generado desde los informes de los módulos; cada tabla indica unidad, definición y módulo productor.", ""]
    df = pd.DataFrame(variables)
    if len(df):
        for table, g in df.groupby("table", sort=True):
            lines.append(f"## `{table}` (módulo {g.module.iloc[0]})")
            lines.append("")
            lines.append("| Variable | Definición | Unidad |")
            lines.append("|---|---|---|")
            for _, r in g.iterrows():
                lines.append(f"| `{r.variable}` | {str(r.definition).replace('|', '/')} | {str(r.get('unit', '') or '')} |")
            lines.append("")
    if len(df):
        (HERE / "variables_dictionary.md").write_text("\n".join(lines), encoding="utf-8")
    else:
        print("sin variables en los informes: se conserva variables_dictionary.md")
    # Controles
    if controls:
        cdf = pd.DataFrame(controls)
        (HERE / "outputs" / "controls").mkdir(parents=True, exist_ok=True)
        cdf.to_csv(HERE / "outputs" / "controls" / "controls_summary.csv", index=False)
        print(cdf.status.value_counts().to_string())
    # Registro de decisiones
    log_path = HERE / "decision_log.md"
    existing = log_path.read_text(encoding="utf-8") if log_path.is_file() else ""
    new_rows = []
    for module, text in decisions:
        row = f"| 2026-09-04 | {module} | {text.replace('|', '/')} |"
        if row not in existing:
            new_rows.append(row)
    for module, text in issues:
        row = f"| 2026-09-04 | {module} (incidencia) | {text.replace('|', '/')} |"
        if row not in existing:
            new_rows.append(row)
    for module, v in verdicts:
        for text in v.get("principle_violations", []) + v.get("output_problems", []):
            row = f"| 2026-09-04 | {module} (verificación) | {text.replace('|', '/')} |"
            if row not in existing:
                new_rows.append(row)
    if new_rows:
        log_path.write_text(existing.rstrip("\n") + "\n" + "\n".join(new_rows) + "\n", encoding="utf-8")
    print(f"variables: {len(variables)}; controles: {len(controls)}; filas nuevas en decision_log: {len(new_rows)}")


if __name__ == "__main__":
    main(sys.argv[1])
