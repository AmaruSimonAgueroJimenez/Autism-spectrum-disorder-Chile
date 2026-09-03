"""Build a readable Quarto report from aggregate outputs (no raw data access)."""
from pathlib import Path
from datetime import date
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output_files/consolidacion"
DOCS = ROOT / "docs"
FIGS = DOCS / "figures/consolidacion"


def read(name):
    return pd.read_csv(OUT / name, dtype={"code": str, "CodigoPrestacion": str})


def table(df):
    def fmt(value):
        if pd.isna(value):
            return "—"
        if isinstance(value, float):
            return f"{value:,.1f}".replace(",", "_").replace(".", ",").replace("_", ".")
        return str(value).replace("|", "/").replace("\n", " ")
    return "\n".join(["| " + " | ".join(df.columns) + " |", "| " + " | ".join(["---"] * len(df.columns)) + " |"] +
                     ["| " + " | ".join(map(fmt, row)) + " |" for row in df.itertuples(index=False, name=None)])


def main():
    FIGS.mkdir(parents=True, exist_ok=True)
    summary = read("grd_cohort_summary.csv")
    positions = read("grd_first_position.csv")
    quality = read("grd_trajectory_quality.csv")
    linkage = read("grd_linkage_between_years.csv")
    rem = read("rem_annual_by_code.csv")
    rq = read("rem_quality.csv")
    core = summary.loc[summary.definition == "TEA_operacional"].copy()
    core["% con egreso previo"] = 100 * core.prior_hospitalization / core.patients
    core["% con grupo previo de interés"] = 100 * core.prior_candidate_group / core.patients
    selected = core[["era", "patients", "prior_hospitalization", "% con egreso previo", "prior_candidate_group", "% con grupo previo de interés", "age_median"]]
    selected = selected.rename(columns={"era": "Período", "patients": "Identificadores incluidos", "prior_hospitalization": "Con egreso previo",
                                        "prior_candidate_group": "Con grupo previo de interés", "age_median": "Edad mediana al registro"})
    p = positions.loc[positions.definition == "TEA_operacional"].copy()
    p["Porcentaje"] = 100*p.patients / p.groupby("era").patients.transform("sum")
    labels = {"principal": "Principal", "solo_secundario": "Solo secundario", "principal_y_secundario": "Principal y secundario", "mixto_mismo_dia": "Posiciones mixtas, mismo día"}
    p["Posición"] = p.index_role.map(labels)
    rem_autism = rem.loc[rem.code == "05990022"].copy()
    rem_autism["% mujeres"] = 100 * rem_autism.Col03 / rem_autism.Col01
    plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6), layout="constrained")
    axes[0].plot(rem_autism.year, rem_autism.Col01, "o-", color="#186d78", lw=2)
    axes[0].set(title="REM · Ingresos con código de autismo", xlabel="Año", ylabel="Registros A05 · 05990022")
    axes[0].set_xticks(rem_autism.year)
    current = p.loc[p.era == "2021-2024"].sort_values("patients")
    axes[1].barh(current["Posición"], current.Porcentaje, color="#435d94")
    axes[1].set(title="GRD · Primer registro observado de TEA", xlabel="Porcentaje de la cohorte 2021–2024", xlim=(0, 105))
    for i, (_, row) in enumerate(current.iterrows()):
        label = "<0,1%" if 0 < row.Porcentaje < .1 else f"{row.Porcentaje:.1f}%".replace(".", ",")
        axes[1].text(row.Porcentaje + 1, i, label, va="center", fontsize=10)
    fig.savefig(FIGS / "resumen.png", dpi=170, bbox_inches="tight")
    plt.close(fig)
    groups = read("grd_previous_groups.csv")
    groups = groups.loc[(groups.era == "2021-2024") & (groups.definition == "TEA_operacional") & (groups.window == "all") & (groups.position == "any")].copy()
    denominator = int(core.loc[core.era == "2021-2024", "patients"].iloc[0])
    prior_denominator = int(core.loc[core.era == "2021-2024", "prior_hospitalization"].iloc[0])
    groups["% cohorte"] = 100 * groups.patients / denominator
    groups["% con egreso previo"] = 100 * groups.patients / prior_denominator if prior_denominator else float("nan")
    groups["Grupo"] = groups.group.str.replace("_", " ")
    last = read("grd_last_prior_principal.csv")
    last = last.loc[(last.era == "2021-2024") & (last.definition == "TEA_operacional")].head(12)
    last["% con egreso previo"] = 100 * last.patients / prior_denominator if prior_denominator else float("nan")
    idx = read("grd_index_principal.csv")
    idx = idx.loc[(idx.era == "2021-2024") & (idx.definition == "TEA_operacional") & (idx.index_role == "solo_secundario")].head(12)
    transition = read("grd_principal_transitions.csv")
    transition = transition.loc[(transition.definition == "TEA_operacional") & (transition.index_role == "solo_secundario")].copy()
    transition["% a 365 días"] = 100 * transition.later_principal_365d / transition.eligible_followup_365d.replace(0, float("nan"))
    report = f'''---
title: "REM y GRD: consolidación y primeros resultados"
subtitle: "Autismo en Chile · auditoría y trayectorias hospitalarias observadas"
date: "{date.today().isoformat()}"
lang: es
format:
  html:
    toc: true
    toc-depth: 2
    embed-resources: true
    theme: cosmo
    code-fold: true
---

## Alcance y lectura

Se revisaron **{read("grd_source_inventory.csv").records.sum():,} registros GRD (2019–2024)** y **{rq.records.sum():,} filas REM (2017–2024)**. Este informe resume una extracción nueva; la [propuesta de análisis](propuesta-rem-grd.md) detalla el diseño y las ampliaciones pendientes.

**Resultado central:** GRD permite investigar diagnósticos hospitalarios anteriores al primer registro observado de autismo, separando posición principal y secundaria. No identifica por sí solo el primer diagnóstico clínico ni demuestra que los diagnósticos previos fueran diferenciales descartados.

Los resultados longitudinales son exploratorios: enlazan por identificador dentro de 2019–2020 o 2021–2024 y excluyen identificadores inconsistentes. No se cruzan ambos períodos. La cohorte principal usa **F84.0, F84.1, F84.5, F84.8 y F84.9** como definición operacional. La posición principal corresponde operacionalmente a `DIAGNOSTICO1`; la estabilidad del identificador y esta semántica requieren confirmación documental del productor.

![Dos resultados descriptivos de fuentes diferentes. REM cuenta ingresos al programa; GRD cuenta identificadores de la cohorte depurada.](figures/consolidacion/resumen.png)

## GRD: qué se puede enlazar

No se encontró ningún identificador compartido entre los bloques 2019–2020 y 2021–2024. Entre 2023 y 2024 sí existen coincidencias, pese al cambio de nombre del campo. La concordancia siguiente se calcula solo entre identificadores con nacimiento y sexo comparables y sin contradicciones internas de cada año; no certifica identidad.

{table(linkage[["year_a", "year_b", "shared_identifiers", "comparable_ids", "agreeing_birth_and_sex", "pct_agreement"]].rename(columns={"year_a":"Año inicial", "year_b":"Año final", "shared_identifiers":"ID compartidos", "comparable_ids":"Comparables", "agreeing_birth_and_sex":"Concordantes", "pct_agreement":"% concordancia"}))}

## GRD: cohorte y posición del primer registro

La fecha índice es el primer alta observada con la definición seleccionada. Un egreso previo debe finalizar antes del ingreso al episodio índice. No se imputan fechas. Un registro secundario puede corresponder a autismo conocido antes de esa hospitalización.

{table(selected)}

{table(p[["era", "Posición", "patients", "Porcentaje"]].rename(columns={"era":"Período", "patients":"Identificadores", "Porcentaje":"%"}))}

Los porcentajes describen una cohorte hospitalaria seleccionada, no a todas las personas autistas en Chile. La edad es la edad al ingreso del primer episodio observado, no la edad del diagnóstico clínico. Las personas sin egresos previos quedan incluidas en los denominadores y no se interpretan como personas sin antecedentes clínicos.

### Diagnósticos anteriores de interés, 2021–2024

Se cuenta una vez a cada identificador por grupo, en cualquier posición diagnóstica. Los grupos pueden coexistir y no son diferenciales clínicos confirmados. El denominador de toda la cohorte es **{denominator:,}**; el de quienes tienen un egreso previo es **{prior_denominator:,}**.

{table(groups[["Grupo", "patients", "% cohorte", "% con egreso previo"]].rename(columns={"patients":"Identificadores"}))}

### Último diagnóstico principal anterior, 2021–2024

Se presentan códigos CIE-10 normalizados sin punto. En empates de fecha se conservan los distintos códigos sin imponer un orden. Las tablas completas también incluyen el primer principal hospitalario observado, ventanas de 365/730 días y las secuencias agregadas.

{table(last[["code", "patients", "% con egreso previo"]].rename(columns={"code":"Código", "patients":"Identificadores"}))}

### Principal de la hospitalización cuando el TEA aparece solo como secundario

Esta tabla describe el motivo principal codificado en el episodio índice. No corresponde a un diagnóstico anterior al autismo.

{table(idx[["code", "patients"]].rename(columns={"code":"Código principal", "patients":"Identificadores"}))}

### De secundario a principal en una hospitalización posterior

La proporción a 365 días restringe el denominador a índices con al menos 365 días calendario hasta el cierre. No presupone seguimiento clínico continuo. Para la transición, el episodio posterior debe ingresar después del alta índice.

{table(transition[["era", "patients", "later_principal", "eligible_followup_365d", "later_principal_365d", "% a 365 días"]].rename(columns={"era":"Período", "patients":"Índice solo secundario", "later_principal":"Principal posterior", "eligible_followup_365d":"Con 365 días disponibles", "later_principal_365d":"Principal en 365 días"}))}

### Sensibilidad de la definición

`autismo_F840`: F84.0. `TEA_operacional`: F84.0/.1/.5/.8/.9. `F84_historico`: categoría F84 y sus subcategorías válidas, incluyendo Rett. Cada definición vuelve a calcular su propia primera fecha; no se suman sus cohortes. La clasificación distingue estas categorías. [CIE-10, NHS](https://classbrowser.nhs.uk/ICD-10-5TH-Edition/vol1/block-f80-f89.htm).

{table(summary[["era", "definition", "patients", "prior_hospitalization", "prior_candidate_group"]].rename(columns={"era":"Período", "definition":"Definición", "patients":"Incluidos", "prior_hospitalization":"Con egreso previo", "prior_candidate_group":"Con grupo previo de interés"}))}

### Oportunidad de observación

Los antecedentes solo pueden observarse dentro de cada bloque. Los conteos siguientes separan disponibilidad calendario de evidencia de un contacto hospitalario anterior. Las proporciones anteriores utilizan toda la cohorte; todavía no son los resultados de una cohorte restringida por 365/730 días.

{table(core[["era", "patients", "lookback_365d", "lookback_730d", "observed_prior_365d", "observed_prior_730d"]].rename(columns={"era":"Período", "patients":"Incluidos", "lookback_365d":"365 días calendario", "lookback_730d":"730 días calendario", "observed_prior_365d":"Contacto ≥365 días antes", "observed_prior_730d":"Contacto ≥730 días antes"}))}

### Calidad y exclusiones

El universo de esta tabla son los identificadores con F84 histórico antes de las exclusiones. Las causas pueden solaparse. Los registros sin identificador se cuantifican, pero no pueden entrar en una trayectoria. Las tablas anuales de posiciones se limitan a registros con identificador y deduplicación exacta; no son un censo de todas las hospitalizaciones F84.

{table(quality.rename(columns={"era":"Período", "raw_F84_identifiers":"ID F84 iniciales", "F84_records_missing_id":"Registros F84 sin ID", "history_records":"Registros recuperados", "exact_duplicate_rows_removed":"Duplicados retirados", "ids_inconsistent_or_missing_birth_sex":"ID inconsistentes/incompletos", "ids_ambiguous_encounter_key":"ID con episodio ambiguo", "history_records_invalid_dates":"Registros con fechas inválidas"}))}

## REM: extracción corregida

El catálogo anual se extrae de los diccionarios originales. Para A05, `Col01` es total, `Col02` hombres, `Col03` mujeres y `Col04–37` son 17 grupos de edad en pares por sexo. Para las secciones A03 revisadas, el total requiere **`Col01 + Col02`**. Las celdas faltantes se conservan como faltantes; no se convierten automáticamente a cero.

### Ingresos al programa con código de autismo

Estos son registros de ingresos A05, no incidencia de autismo ni personas únicas nacionales. Se muestra el período con código específico `05990022`; el TGD genérico de 2017–2020 se mantiene separado. Son sumas de valores observados: en 2024 una de las 5.020 filas de este código carece de total, por lo que 11.842 no acredita un total completo. No se imputó el valor faltante.

{table(rem_autism[["year", "Col01", "Col02", "Col03", "% mujeres", "reporting_establishments", "months"]].rename(columns={"year":"Año", "Col01":"Ingresos", "Col02":"Hombres", "Col03":"Mujeres", "reporting_establishments":"Establecimientos con registros", "months":"Meses presentes"}))}

### Controles de calidad REM

Se revisan claves repetidas, totales por sexo y por edad en filas con todas las celdas necesarias observadas. Un mes presente en el agregado no implica cobertura completa de todos los establecimientos. Las seis filas idénticas seleccionadas de 2024 se deduplicaron. Las discrepancias residuales se conservan y se informan; no se corrigieron las fuentes.

{table(rq[["year", "selected_records", "exact_duplicates_removed", "a05_rows_sex_comparable", "a05_rows_sex_mismatch", "a05_rows_age_comparable", "a05_rows_age_mismatch"]].rename(columns={"year":"Año", "selected_records":"Filas seleccionadas", "exact_duplicates_removed":"Duplicadas retiradas", "a05_rows_sex_comparable":"Comparables por sexo", "a05_rows_sex_mismatch":"Discrepancias por sexo", "a05_rows_age_comparable":"Comparables por edad", "a05_rows_age_mismatch":"Discrepancias por edad"}))}

### Extensión recomendada

Priorizar: (1) tendencias mensuales A05 por sexo/edad y establecimientos informantes; (2) indicadores de tamizaje con numerador y denominador de la misma etapa, distinguiendo 2019–2022 de 2023–2024; (3) ingresos a rehabilitación A28, diferenciando secciones. A28 no debe etiquetarse automáticamente como consultas. No hay enlace individual REM–GRD en estas bases.

No se calculan tasas de positividad ni incidencia a partir de fórmulas sin denominador validado. La [propuesta completa](propuesta-rem-grd.md) establece los modelos y los controles necesarios antes de extender a 2025–2026 o reutilizar las tasas geográficas históricas.

## Reproducibilidad

Las entradas son los CSV canónicos externos. Los resultados agregados están en `output_files/consolidacion/`. Se conserva el inventario de tamaño, fecha de modificación y número de registros, además del catálogo con archivo, hoja y fila de cada código REM. Los manifiestos fuente externos contienen los hashes de los canónicos. Ninguna tabla nueva exporta identificadores o historias individuales.

Los scripts de auditoría y extracción están en `scripts/`; las versiones utilizadas se registran en `requirements-analysis.txt`. El [README](../README.md) contiene los comandos de reproducción. Este documento fue generado con las tablas derivadas y no ejecuta de nuevo la lectura de microdatos. Los informes históricos se conservan, pero requieren la revisión metodológica descrita.
'''
    (DOCS / "consolidacion-rem-grd.qmd").write_text(report, encoding="utf-8")
    print("Informe y figura generados.")


if __name__ == "__main__":
    main()
