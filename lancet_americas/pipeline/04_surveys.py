#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""04_surveys.py — Benchmarks poblacionales con diseño complejo: ENDIDE 2022 y ENCAVI 2023–2024.

Estima con linealización de Taylor (`common.survey_proportion`; los dominios conservan todas las unidades del
diseño) la proporción, el error estándar, el IC 95 % (logit, t con gl = UPM − estratos), el total ponderado y el
n/casos no ponderados de:

  * ENDIDE 2022, personas adultas (18 años o más): autismo reportado (`c26_33`).
  * ENDIDE 2022, niños, niñas y adolescentes (NNA, 2–17 años; informa el/la responsable principal): autismo
    reportado (`n29_19`) y confirmación por un médico (`n29a_19`), esta última como dominio de los NNA con autismo
    reportado y como proporción de todos los NNA.
  * ENCAVI 2023–2024, personas de 15 años o más: diagnóstico de trastorno del espectro autista (`p4_6_1_h`).

Desagregación por sexo y grupo de edad amplio con DEFF y bandera «imprecise» (< 30 casos no ponderados). Nunca se
desagrega a comuna. Las encuestas no se enlazan con los registros administrativos: son benchmarks de orden de
magnitud de autorreporte/reporte de cuidadores, no prevalencia validada ni validación uno a uno de códigos.
Los ítems de autismo son idénticos en las variantes `con_rett` y `sin_rett` (el reporte no separa Rett).

Ejecución desde la raíz del repositorio:
    python3 lancet_americas/pipeline/04_surveys.py [--skip-design-check] [--mc-replicates 400] [--tmpdir DIR]

Salidas (escritura atómica):
    lancet_americas/outputs/tidy/survey_estimates.csv
    lancet_americas/outputs/tidy/survey_items_dictionary.csv
    lancet_americas/outputs/tidy/survey_design_check.csv
    lancet_americas/outputs/controls/04_surveys_controls.csv
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import config as CFG  # noqa: E402
import common as C  # noqa: E402

MODULE = "04_surveys"
SCRIPT = "lancet_americas/pipeline/04_surveys.py"
MIN_CASES = 30          # umbral de casos no ponderados para la bandera «imprecise»
RATE_TOL = 0.005        # tolerancia relativa para controles de tasas/proporciones
SIM_TOL = 0.10          # tolerancia relativa para las razones de EE de la simulación

ENDIDE_DIR = CFG.PATHS["endide"]
ENDIDE_ZIP = ENDIDE_DIR / "endide_2022_adultos_cuidadores_nna.dta.zip"
ENDIDE_DOCS = "libro_codigos_endide_2022.pdf; metodologia_diseno_muestral_endide_2022.pdf"
ENCAVI_DIR = CFG.PATHS["encavi"]
ENCAVI_DTA = ENCAVI_DIR / "ENCAVI_2023_2024.dta"
ENCAVI_DOCS = "manual_base_ENCAVI_2023_2024.pdf; cuestionario_ENCAVI_2023_2024.pdf"

# Diseño declarado en los archivos públicos (ENDIDE: libro de códigos, IDs 10–12; ENCAVI: manual, svyset).
ENDIDE_DESIGN = dict(weight="fexp", strata="estrato", psu="cod_upm")
ENCAVI_DESIGN = dict(weight="w_personas_cal", strata="varstrat", psu="varunit")

# Wording exacto (etiquetas del libro de códigos ENDIDE y cuestionario/manual ENCAVI).
W_ENDIDE_ADULT = "Enfermedad o condición de salud: Autismo (Trastorno del espectro autista)"
W_ENDIDE_NNA = "Enfermedad o condición de salud: Autismo (Trastorno del espectro Autista)"
W_ENDIDE_NNA_CONF = "¿Le ha dicho un médico que tiene…? Autismo (Trastorno del espectro Autista)"
W_ENDIDE_NNA_MED = "¿Ha recibido medicamento para...? Autismo (Trastorno del espectro Autista)"
W_ENDIDE_NNA_OTH = "¿Ha recibido otro tratam. para...? Autismo (Trastorno del espectro Autista)"
W_ENCAVI_DX = ("4.6 Actualmente, ¿Ud. ha sido diagnosticado con alguno de los siguientes problemas, condición de salud o "
               "enfermedades? — Trastorno del espectro autista (nota al encuestador: diagnóstico médico tradicional)")
W_ENCAVI_TX = "4.6 ¿Y para cuál de ellos ha recibido o está en tratamiento médico? — Trastorno del espectro autista"

ENDIDE_ADULT_AGE = [(18, 29, "18-29"), (30, 44, "30-44"), (45, 59, "45-59"), (60, 200, "60+")]
ENDIDE_NNA_AGE = [(2, 5, "2-5"), (6, 11, "6-11"), (12, 17, "12-17")]
ENCAVI_AGE5 = {1: "15-19", 2: "20-29", 3: "30-49", 4: "50-64", 5: "65+"}
SEX = {1: "Hombre", 2: "Mujer"}


def log(msg: str) -> None:
    print(f"[{MODULE}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Carga de microdatos (nunca se copian a la carpeta del repositorio)
# ---------------------------------------------------------------------------
def load_endide(tmp_root: str | None) -> pd.DataFrame:
    """Descomprime el ZIP oficial en un directorio temporal, lee solo las columnas necesarias y devuelve las
    personas seleccionadas (confirma_seleccionado == 1, folio y fexp no perdidos)."""
    cols = ["id_vivienda", "id_hogar", "folio", "confirma_seleccionado", "region", "zona", "estrato", "cod_upm", "fexp",
            "sexo", "edad", "forma_ent_adulto_inicio", "forma_ent_nna_rp_inicio", "rp2",
            "c26_33", "n29_19", "n29a_19", "n29b_19", "n29c_19"]
    with tempfile.TemporaryDirectory(prefix="endide_", dir=tmp_root) as td:
        with zipfile.ZipFile(ENDIDE_ZIP) as zf:
            members = [m for m in zf.namelist() if m.lower().endswith(".dta")]
            if len(members) != 1:
                raise RuntimeError(f"Se esperaba un único .dta dentro de {ENDIDE_ZIP.name}; hay {members}")
            zf.extract(members[0], td)
            dta = Path(td) / members[0]
        log(f"ENDIDE .dta extraído a temporal: {dta.name} ({dta.stat().st_size / 1e6:.1f} MB)")
        df = pd.read_stata(dta, columns=cols, convert_categoricals=False, convert_missing=False, preserve_dtypes=True)
    log(f"ENDIDE filas (roster completo): {len(df):,}")
    sel = df.loc[df.confirma_seleccionado == 1].copy()
    if sel.fexp.isna().any() or sel.folio.isna().any():
        raise RuntimeError("ENDIDE: personas seleccionadas con fexp o folio perdidos")
    # Universos: cuestionario adulto (18+) y cuestionario NNA (2–17, responde el/la responsable principal).
    sel["adult"] = ((sel.edad >= 18) & sel.c26_33.notna()).astype(int)
    sel["nna"] = ((sel.edad <= 17) & sel.n29_19.notna()).astype(int)
    bad = sel.loc[(sel.edad >= 18) & sel.c26_33.isna()].shape[0] + sel.loc[(sel.edad <= 17) & sel.n29_19.isna()].shape[0]
    if bad:
        log(f"AVISO ENDIDE: {bad} personas seleccionadas sin respuesta al ítem de su módulo")
    sel["y_adult_autism"] = sel.c26_33.fillna(0).astype(float)
    sel["y_nna_autism"] = sel.n29_19.fillna(0).astype(float)
    sel["nna_autism"] = ((sel.nna == 1) & (sel.n29_19 == 1)).astype(int)
    sel["nna_autism_conf_valid"] = ((sel.nna_autism == 1) & sel.n29a_19.isin([1, 2])).astype(int)
    sel["y_nna_confirmed"] = ((sel.nna_autism == 1) & (sel.n29a_19 == 1)).astype(float)
    sel["nna_med_valid"] = ((sel.nna_autism == 1) & sel.n29b_19.isin([1, 2])).astype(int)
    sel["y_nna_medication"] = ((sel.nna_autism == 1) & (sel.n29b_19 == 1)).astype(float)
    sel["nna_oth_valid"] = ((sel.nna_autism == 1) & sel.n29c_19.isin([1, 2])).astype(int)
    sel["y_nna_other_treatment"] = ((sel.nna_autism == 1) & (sel.n29c_19 == 1)).astype(float)
    sel["sex_label"] = sel.sexo.map(SEX)
    sel["age_group_adult"] = pd.Series(np.nan, index=sel.index, dtype="object")
    for lo, hi, lab in ENDIDE_ADULT_AGE:
        sel.loc[(sel.adult == 1) & sel.edad.between(lo, hi), "age_group_adult"] = lab
    sel["age_group_nna"] = pd.Series(np.nan, index=sel.index, dtype="object")
    for lo, hi, lab in ENDIDE_NNA_AGE:
        sel.loc[(sel.nna == 1) & sel.edad.between(lo, hi), "age_group_nna"] = lab
    log(f"ENDIDE seleccionados: {len(sel):,}; adultos {int(sel.adult.sum()):,}; NNA {int(sel.nna.sum()):,}; "
        f"estratos {sel.estrato.nunique()}; UPM {sel.cod_upm.nunique():,}; suma fexp {sel.fexp.sum():,.0f}")
    return sel.reset_index(drop=True)


def load_encavi() -> pd.DataFrame:
    cols = ["folio_encuesta", "region", "area", "sexo", "edad", "edad5", "w_personas_cal", "varunit", "varstrat",
            "p4_6_1_h", "p4_6_2_h"]
    df = pd.read_stata(ENCAVI_DTA, columns=cols, convert_categoricals=False, convert_missing=False, preserve_dtypes=True)
    if df.w_personas_cal.isna().any() or df.varunit.isna().any() or df.varstrat.isna().any():
        raise RuntimeError("ENCAVI: ponderador o variables de diseño perdidas")
    df["dx_valid"] = df.p4_6_1_h.isin([1, 2]).astype(int)          # 8 = No sabe, 9 = No responde → perdidos
    df["y_autism_dx"] = (df.p4_6_1_h == 1).astype(float)
    df["dx_positive"] = (df.p4_6_1_h == 1).astype(int)
    df["tx_valid"] = ((df.p4_6_1_h == 1) & df.p4_6_2_h.isin([1, 2])).astype(int)
    df["y_autism_tx"] = ((df.p4_6_1_h == 1) & (df.p4_6_2_h == 1)).astype(float)
    df["all_15plus"] = 1
    df["sex_label"] = df.sexo.map(SEX)
    df["age_group"] = df.edad5.map(ENCAVI_AGE5)
    log(f"ENCAVI personas 15+: {len(df):,}; estratos {df.varstrat.nunique()}; UPM {df.varunit.nunique()}; "
        f"suma ponderador {df.w_personas_cal.sum():,.0f}")
    return df


# ---------------------------------------------------------------------------
# Estimación
# ---------------------------------------------------------------------------
def estimate(df: pd.DataFrame, y: str, dom: pd.Series, design: dict, **meta) -> dict:
    """Envoltura de common.survey_proportion que añade DEFF, EE relativo y bandera de precisión."""
    r = C.survey_proportion(df, y, design["weight"], design["strata"], design["psu"], domain=dom)
    n, k, p, se = r["n_domain"], r["n_cases"], r["proportion"], r["se"]
    srs_var = p * (1 - p) / n if (n > 0 and 0 < p < 1) else np.nan
    deff = se ** 2 / srs_var if (srs_var and srs_var > 0) else np.nan
    rse = se / p if p > 0 else np.nan
    flag = "imprecise" if k < MIN_CASES else "adequate"
    note = (f"DEFF = {deff:.2f} (varianza de diseño / varianza MAS con el mismo n no ponderado y p del dominio); "
            f"EE relativo = {100 * rse:.1f} %; "
            + ("imprecise: menos de 30 casos no ponderados, usar solo como orden de magnitud"
               if flag == "imprecise" else "adecuado según el umbral de 30 casos no ponderados")
            + ("; EE relativo > 30 %" if (rse == rse and rse > 0.30) else ""))
    row = dict(meta)
    row.update(dict(weight_var=design["weight"], strata_var=design["strata"], psu_var=design["psu"],
                    n=n, cases=k, proportion=p, proportion_unit="proportion (0-1) of persons in domain",
                    se=se, lo=r["lo"], hi=r["hi"], ci_method="logit, t with df = PSU - strata (Taylor linearisation)",
                    weighted_total=r["weighted_total"], weighted_population=r["weighted_population"],
                    weighted_unit="persons (survey expansion weights)", deff=deff, rse=rse, df=r["df"],
                    n_psu=r["n_psu"], n_strata=r["n_strata"], precision_flag=flag, deff_note=note))
    return row


def endide_rows(sel: pd.DataFrame) -> list[dict]:
    rows = []
    src = dict(survey="ENDIDE 2022", survey_year=2022, variant="both", source_file=ENDIDE_ZIP.name,
               source_sha256=C.sha256_file(ENDIDE_ZIP), source_documents=ENDIDE_DOCS, script=SCRIPT,
               variant_note="Idéntico en con_rett y sin_rett: el reporte de autismo no separa el síndrome de Rett")
    d = ENDIDE_DESIGN
    adult_def = "Personas seleccionadas de 18 años o más con cuestionario adulto (c26_33 no perdido); autorreporte o con ayuda/por tercero (forma_ent_adulto_inicio)"
    nna_def = "Personas seleccionadas de 2 a 17 años con cuestionario NNA respondido por el/la responsable principal (n29_19 no perdido)"

    # --- Adultos: autismo reportado
    base = dict(src, module="Adultos (18+)", item_variable="c26_33", item_wording=W_ENDIDE_ADULT,
                positive_definition="c26_33 == 1 (Sí); 0 = No; sin códigos perdidos", estimate_type="primary")
    rows.append(estimate(sel, "y_adult_autism", sel.adult, d, domain="ENDIDE adultos 18+: autismo reportado",
                         domain_definition=adult_def, subgroup_type="total", subgroup="total", **base))
    for code, lab in SEX.items():
        dom = ((sel.adult == 1) & (sel.sexo == code)).astype(int)
        rows.append(estimate(sel, "y_adult_autism", dom, d, domain="ENDIDE adultos 18+: autismo reportado",
                             domain_definition=adult_def + f"; sexo = {lab}", subgroup_type="sex", subgroup=lab, **base))
    for _, _, lab in ENDIDE_ADULT_AGE:
        dom = ((sel.adult == 1) & (sel.age_group_adult == lab)).astype(int)
        rows.append(estimate(sel, "y_adult_autism", dom, d, domain="ENDIDE adultos 18+: autismo reportado",
                             domain_definition=adult_def + f"; edad {lab}", subgroup_type="age_group", subgroup=lab, **base))

    # --- NNA: autismo reportado
    base = dict(src, module="NNA (2-17), responsable principal", item_variable="n29_19", item_wording=W_ENDIDE_NNA,
                positive_definition="n29_19 == 1 (Sí); 0 = No; sin códigos perdidos", estimate_type="primary")
    rows.append(estimate(sel, "y_nna_autism", sel.nna, d, domain="ENDIDE NNA 2-17: autismo reportado",
                         domain_definition=nna_def, subgroup_type="total", subgroup="total", **base))
    for code, lab in SEX.items():
        dom = ((sel.nna == 1) & (sel.sexo == code)).astype(int)
        rows.append(estimate(sel, "y_nna_autism", dom, d, domain="ENDIDE NNA 2-17: autismo reportado",
                             domain_definition=nna_def + f"; sexo = {lab}", subgroup_type="sex", subgroup=lab, **base))
    for _, _, lab in ENDIDE_NNA_AGE:
        dom = ((sel.nna == 1) & (sel.age_group_nna == lab)).astype(int)
        rows.append(estimate(sel, "y_nna_autism", dom, d, domain="ENDIDE NNA 2-17: autismo reportado",
                             domain_definition=nna_def + f"; edad {lab}", subgroup_type="age_group", subgroup=lab, **base))

    # --- NNA: confirmación médica, dominio = NNA con autismo reportado (respuestas válidas) — primario
    conf_def = "NNA con autismo reportado (n29_19 == 1) y respuesta válida en n29a_19 (1 Sí / 2 No); -99 No responde excluido"
    base = dict(src, module="NNA (2-17), responsable principal", item_variable="n29a_19", item_wording=W_ENDIDE_NNA_CONF,
                positive_definition="n29a_19 == 1 (Sí); 2 = No; -99 = No responde (perdido); ítem aplicado solo si n29_19 == 1",
                estimate_type="primary")
    rows.append(estimate(sel, "y_nna_confirmed", sel.nna_autism_conf_valid, d,
                         domain="ENDIDE NNA con autismo reportado: confirmado por un médico",
                         domain_definition=conf_def, subgroup_type="total", subgroup="total", **base))
    for code, lab in SEX.items():
        dom = ((sel.nna_autism_conf_valid == 1) & (sel.sexo == code)).astype(int)
        rows.append(estimate(sel, "y_nna_confirmed", dom, d, domain="ENDIDE NNA con autismo reportado: confirmado por un médico",
                             domain_definition=conf_def + f"; sexo = {lab}", subgroup_type="sex", subgroup=lab, **base))
    # Sensibilidad: No responde tratado como no confirmado (denominador = los 163 NNA con autismo reportado)
    rows.append(estimate(sel, "y_nna_confirmed", sel.nna_autism, d,
                         domain="ENDIDE NNA con autismo reportado: confirmado por un médico (sensibilidad: No responde = no confirmado)",
                         domain_definition="NNA con autismo reportado (n29_19 == 1), todos; -99 No responde contado como no confirmado",
                         subgroup_type="total", subgroup="total", **dict(base, estimate_type="sensitivity")))
    # Confirmado como proporción de todos los NNA
    share_def = nna_def + "; numerador = n29_19 == 1 y n29a_19 == 1"
    base2 = dict(base, estimate_type="primary")
    rows.append(estimate(sel, "y_nna_confirmed", sel.nna, d, domain="ENDIDE NNA 2-17: autismo reportado y confirmado por un médico",
                         domain_definition=share_def, subgroup_type="total", subgroup="total", **base2))
    for code, lab in SEX.items():
        dom = ((sel.nna == 1) & (sel.sexo == code)).astype(int)
        rows.append(estimate(sel, "y_nna_confirmed", dom, d, domain="ENDIDE NNA 2-17: autismo reportado y confirmado por un médico",
                             domain_definition=share_def + f"; sexo = {lab}", subgroup_type="sex", subgroup=lab, **base2))
    for _, _, lab in ENDIDE_NNA_AGE:
        dom = ((sel.nna == 1) & (sel.age_group_nna == lab)).astype(int)
        rows.append(estimate(sel, "y_nna_confirmed", dom, d, domain="ENDIDE NNA 2-17: autismo reportado y confirmado por un médico",
                             domain_definition=share_def + f"; edad {lab}", subgroup_type="age_group", subgroup=lab, **base2))

    # --- NNA: medicamento y otro tratamiento (secundarios, dominio = NNA con autismo reportado y respuesta válida)
    rows.append(estimate(sel, "y_nna_medication", sel.nna_med_valid, d, domain="ENDIDE NNA con autismo reportado: ha recibido medicamento",
                         domain_definition="NNA con autismo reportado (n29_19 == 1) y respuesta válida en n29b_19; -99 excluido",
                         subgroup_type="total", subgroup="total",
                         **dict(src, module="NNA (2-17), responsable principal", item_variable="n29b_19", item_wording=W_ENDIDE_NNA_MED,
                                positive_definition="n29b_19 == 1 (Sí); 2 = No; -99 = No responde (perdido)", estimate_type="secondary")))
    rows.append(estimate(sel, "y_nna_other_treatment", sel.nna_oth_valid, d, domain="ENDIDE NNA con autismo reportado: ha recibido otro tratamiento",
                         domain_definition="NNA con autismo reportado (n29_19 == 1) y respuesta válida en n29c_19; -99 excluido",
                         subgroup_type="total", subgroup="total",
                         **dict(src, module="NNA (2-17), responsable principal", item_variable="n29c_19", item_wording=W_ENDIDE_NNA_OTH,
                                positive_definition="n29c_19 == 1 (Sí); 2 = No; -99 = No responde (perdido)", estimate_type="secondary")))
    return rows


def encavi_rows(df: pd.DataFrame) -> list[dict]:
    rows = []
    src = dict(survey="ENCAVI 2023-2024", survey_year="2023-2024", variant="both", source_file=ENCAVI_DTA.name,
               source_sha256=C.sha256_file(ENCAVI_DTA), source_documents=ENCAVI_DOCS, script=SCRIPT,
               variant_note="Idéntico en con_rett y sin_rett: el ítem de diagnóstico no separa el síndrome de Rett")
    d = ENCAVI_DESIGN
    valid_def = "Personas de 15 años o más con respuesta válida en p4_6_1_h (1 Sí / 2 No); 8 No sabe y 9 No responde excluidos"
    base = dict(src, module="Personas 15+ (módulo 4, salud)", item_variable="p4_6_1_h", item_wording=W_ENCAVI_DX,
                positive_definition="p4_6_1_h == 1 (Sí); 2 = No; 8 = No sabe y 9 = No responde (perdidos)", estimate_type="primary")
    rows.append(estimate(df, "y_autism_dx", df.dx_valid, d, domain="ENCAVI 15+: diagnóstico de trastorno del espectro autista",
                         domain_definition=valid_def, subgroup_type="total", subgroup="total", **base))
    for code, lab in SEX.items():
        dom = ((df.dx_valid == 1) & (df.sexo == code)).astype(int)
        rows.append(estimate(df, "y_autism_dx", dom, d, domain="ENCAVI 15+: diagnóstico de trastorno del espectro autista",
                             domain_definition=valid_def + f"; sexo = {lab}", subgroup_type="sex", subgroup=lab, **base))
    for code, lab in ENCAVI_AGE5.items():
        dom = ((df.dx_valid == 1) & (df.edad5 == code)).astype(int)
        rows.append(estimate(df, "y_autism_dx", dom, d, domain="ENCAVI 15+: diagnóstico de trastorno del espectro autista",
                             domain_definition=valid_def + f"; edad5 = {lab}", subgroup_type="age_group", subgroup=lab, **base))
    # Sensibilidad: No sabe / No responde contados como no diagnosticados (reproduce el cálculo preliminar sobre las 16.590 personas)
    rows.append(estimate(df, "y_autism_dx", df.all_15plus, d,
                         domain="ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)",
                         domain_definition="Todas las personas de 15 años o más de la base (16.590); 8/9 contados como no diagnosticados",
                         subgroup_type="total", subgroup="total", **dict(base, estimate_type="sensitivity")))
    # Secundario: en tratamiento médico entre los diagnosticados
    rows.append(estimate(df, "y_autism_tx", df.tx_valid, d, domain="ENCAVI 15+ con diagnóstico de TEA: ha recibido o está en tratamiento médico",
                         domain_definition="Personas 15+ con p4_6_1_h == 1 y respuesta válida en p4_6_2_h (1/2); 9 No responde excluido",
                         subgroup_type="total", subgroup="total",
                         **dict(src, module="Personas 15+ (módulo 4, salud)", item_variable="p4_6_2_h", item_wording=W_ENCAVI_TX,
                                positive_definition="p4_6_2_h == 1 (Sí); 2 = No; 8/9 perdidos; ítem aplicado solo si p4_6_1_h == 1",
                                estimate_type="secondary")))
    return rows


# ---------------------------------------------------------------------------
# Verificación de common.survey_proportion con una población simulada
# ---------------------------------------------------------------------------
def rao_wu_bootstrap_se(s: pd.DataFrame, y: str, dom: np.ndarray, B: int, rng: np.random.Generator) -> float:
    """Bootstrap reescalado de Rao–Wu sobre UPM (m_h = n_h − 1) para el estimador de razón del dominio."""
    t = (s.assign(_num=s["w"] * s[y] * dom, _den=s["w"] * dom)
         .groupby(["strata", "psu"])[["_num", "_den"]].sum().reset_index())
    num_b = np.zeros(B)
    den_b = np.zeros(B)
    for _, g in t.groupby("strata"):
        n_h = len(g)
        counts = rng.multinomial(n_h - 1, np.full(n_h, 1.0 / n_h), size=B)
        mult = counts * (n_h / (n_h - 1))
        num_b += mult @ g["_num"].to_numpy()
        den_b += mult @ g["_den"].to_numpy()
    return float(np.std(num_b / den_b, ddof=1))


def design_check(R: int = 400, B: int = 500, seed: int = 20260904) -> list[dict]:
    """Población finita estratificada (3 estratos) con conglomerados (UPM) de tamaño variable e ICC positiva.
    Muestra bietápica: MAS sin reemplazo de n_h UPM por estrato y de m unidades por UPM; ponderador = inverso de la
    probabilidad de inclusión. Compara la linealización de Taylor (common.survey_proportion) con la proporción
    ponderada ingenua (punto), con el bootstrap de Rao–Wu sobre UPM y con el EE empírico Monte Carlo (R muestras)."""
    rng = np.random.default_rng(seed)
    spec = {1: (400, 0.03), 2: (300, 0.06), 3: (200, 0.02)}   # estrato: (N_h UPM, proporción base)
    n_psu = 20
    m_units = 10
    frames = []
    for h, (N, base) in spec.items():
        sizes = rng.integers(20, 61, size=N)
        eff = rng.normal(0.0, 0.7, size=N)
        for i in range(N):
            p_i = 1 / (1 + np.exp(-(np.log(base / (1 - base)) + eff[i])))
            frames.append(pd.DataFrame({"strata": h, "psu": h * 100000 + i, "M": int(sizes[i]),
                                        "y": (rng.random(sizes[i]) < p_i).astype(float),
                                        "child": (rng.random(sizes[i]) < 0.25).astype(float)}))
    pop = pd.concat(frames, ignore_index=True)
    p_true = float(pop.y.mean())
    p_child = float(pop.loc[pop.child == 1, "y"].mean())
    psu_by_stratum = {h: pop.loc[pop.strata == h, "psu"].unique() for h in spec}

    def draw() -> pd.DataFrame:
        parts = []
        for h, (N, _) in spec.items():
            chosen = rng.choice(psu_by_stratum[h], size=n_psu, replace=False)
            sub = pop.loc[pop.psu.isin(chosen)].copy()
            sub["_k"] = rng.random(len(sub))
            sub = sub.sort_values(["psu", "_k"])
            sub["_r"] = sub.groupby("psu").cumcount()
            sub = sub.loc[sub._r < m_units].copy()
            m_i = sub.groupby("psu").y.transform("size")
            sub["w"] = (N / n_psu) * (sub.M / m_i)
            parts.append(sub.drop(columns=["_k", "_r"]))
        return pd.concat(parts, ignore_index=True)

    rec = []
    for r in range(R):
        s = draw()
        a = C.survey_proportion(s, "y", "w", "strata", "psu")
        dom = s.child.to_numpy()
        c = C.survey_proportion(s, "y", "w", "strata", "psu", domain=s.child)
        sub = s.loc[s.child == 1]
        c_sub = C.survey_proportion(sub, "y", "w", "strata", "psu")
        naive_all = float((s.w * s.y).sum() / s.w.sum())
        naive_child = float((sub.w * sub.y).sum() / sub.w.sum())
        rec.append(dict(p_all=a["proportion"], se_all=a["se"], lo_all=a["lo"], hi_all=a["hi"],
                        p_child=c["proportion"], se_child=c["se"], lo_child=c["lo"], hi_child=c["hi"],
                        se_child_subset=c_sub["se"], naive_all=naive_all, naive_child=naive_child,
                        boot_all=rao_wu_bootstrap_se(s, "y", np.ones(len(s)), B, rng),
                        boot_child=rao_wu_bootstrap_se(s, "y", dom, B, rng),
                        n=len(s), n_child=int(s.child.sum()), cases_child=int(sub.y.sum())))
    m = pd.DataFrame(rec)
    out = []

    def add(check, quantity, value, reference, note):
        out.append(dict(check=check, design="3 estratos; 400/300/200 UPM (20–60 unidades, ICC>0); muestra 20 UPM por estrato × 10 unidades; "
                                            f"MAS sin reemplazo en ambas etapas; R = {R} muestras Monte Carlo; B = {B} réplicas bootstrap; semilla {seed}",
                        quantity=quantity, value=float(value), reference=float(reference) if reference is not None else np.nan,
                        ratio=(float(value) / float(reference) if reference not in (None, 0) else np.nan), note=note))

    add("point_estimate", "max |Taylor − ponderada ingenua| (población completa)", (m.p_all - m.naive_all).abs().max(), 0.0,
        "El estimador de razón de Taylor debe coincidir exactamente con la proporción ponderada ingenua")
    add("point_estimate", "max |Taylor dominio − ponderada ingenua del subconjunto|", (m.p_child - m.naive_child).abs().max(), 0.0, "Idem para el dominio")
    add("bias", "media de p̂ (población completa)", m.p_all.mean(), p_true, "Referencia: proporción verdadera de la población finita")
    add("bias", "media de p̂ (dominio)", m.p_child.mean(), p_child, "Referencia: proporción verdadera del dominio")
    add("se_taylor_vs_mc", "media EE Taylor (población completa)", m.se_all.mean(), m.p_all.std(ddof=1),
        "Referencia: desviación estándar Monte Carlo de p̂ entre muestras (EE empírico). Fracción de muestreo de UPM 5–10 %: la aproximación con reemplazo sobreestima levemente")
    add("se_taylor_vs_mc", "media EE Taylor (dominio, todas las unidades conservadas)", m.se_child.mean(), m.p_child.std(ddof=1),
        "Referencia: EE empírico Monte Carlo del dominio")
    add("se_bootstrap_vs_mc", "media EE bootstrap Rao–Wu (población completa)", m.boot_all.mean(), m.p_all.std(ddof=1), "Referencia: EE empírico Monte Carlo")
    add("se_bootstrap_vs_mc", "media EE bootstrap Rao–Wu (dominio)", m.boot_child.mean(), m.p_child.std(ddof=1), "Referencia: EE empírico Monte Carlo del dominio")
    add("se_taylor_vs_bootstrap", "media EE Taylor / media EE bootstrap (población completa)", m.se_all.mean(), m.boot_all.mean(), "Dos estimadores de varianza del mismo diseño")
    add("se_taylor_vs_bootstrap", "media EE Taylor / media EE bootstrap (dominio)", m.se_child.mean(), m.boot_child.mean(), "Dos estimadores de varianza del mismo diseño")
    add("domain_vs_subset", "media EE dominio (todas las unidades) / media EE subconjunto (unidades fuera del dominio eliminadas)",
        m.se_child.mean(), m.se_child_subset.mean(),
        "El enfoque de subconjunto ignora la aleatoriedad del tamaño del dominio por UPM; aquí ambas coinciden en la práctica porque ninguna UPM pierde todas sus unidades")
    add("ci_coverage", "cobertura empírica del IC 95 % logit (población completa)", ((m.lo_all <= p_true) & (m.hi_all >= p_true)).mean(), 0.95, "Proporción de muestras cuyo IC contiene el valor verdadero")
    add("ci_coverage", "cobertura empírica del IC 95 % logit (dominio)", ((m.lo_child <= p_child) & (m.hi_child >= p_child)).mean(), 0.95, "Idem para el dominio")
    add("sample", "n medio por muestra", m.n.mean(), None, f"casos medios en el dominio: {m.cases_child.mean():.1f}; n medio del dominio: {m.n_child.mean():.1f}")
    return out


# ---------------------------------------------------------------------------
# Diccionario de ítems y variables de diseño
# ---------------------------------------------------------------------------
def items_dictionary() -> pd.DataFrame:
    e = "ENDIDE 2022"
    v = "ENCAVI 2023-2024"
    ed = "libro_codigos_endide_2022.pdf (junio 2023)"
    em = "metodologia_diseno_muestral_endide_2022.pdf"
    vm = "manual_base_ENCAVI_2023_2024.pdf"
    vq = "cuestionario_ENCAVI_2023_2024.pdf (sección 4.6)"
    rows = [
        dict(survey=e, module="Adultos (18+)", variable="c26_33", variable_label=W_ENDIDE_ADULT,
             question_wording="Batería c26 «Enfermedad o condición de salud» (lista de condiciones; el cuestionario no está en el archivo local, se usa la etiqueta del libro de códigos)",
             respondent="Persona seleccionada de 18+ (por sí misma, con ayuda o por un tercero según forma_ent_adulto_inicio)",
             universe="Personas seleccionadas de 18 años o más (n = 30.010)", response_codes="0 No; 1 Sí", missing_codes="ninguno (sin códigos perdidos; NaN = fuera del universo)",
             treatment_in_analysis="Numerador = 1; dominio = adultos con ítem no perdido", role="ítem principal adultos", source_document=ed),
        dict(survey=e, module="NNA (2-17)", variable="n29_19", variable_label=W_ENDIDE_NNA,
             question_wording="Batería n29 «Enfermedad o condición de salud» del cuestionario NNA (responsable principal)",
             respondent="Responsable principal del NNA (madre 77 %, rp2)", universe="Personas seleccionadas de 2 a 17 años (n = 5.526)",
             response_codes="0 No; 1 Sí", missing_codes="ninguno (NaN = fuera del universo)",
             treatment_in_analysis="Numerador = 1; dominio = NNA con ítem no perdido", role="ítem principal NNA", source_document=ed),
        dict(survey=e, module="NNA (2-17)", variable="n29a_19", variable_label=W_ENDIDE_NNA_CONF,
             question_wording="¿Le ha dicho un médico que tiene…? (confirmación profesional, aplicada solo si n29_19 = 1)",
             respondent="Responsable principal del NNA", universe="NNA con autismo reportado (n29_19 = 1; n = 163)",
             response_codes="1 Sí; 2 No", missing_codes="-99 No responde (10 casos); NaN = no aplica (n29_19 ≠ 1)",
             treatment_in_analysis="Primario: dominio = respuestas válidas (153); sensibilidad: -99 contado como no confirmado (163); también como proporción de todos los NNA",
             role="confirmación profesional NNA", source_document=ed),
        dict(survey=e, module="NNA (2-17)", variable="n29b_19", variable_label=W_ENDIDE_NNA_MED,
             question_wording="¿Ha recibido medicamento para...? (aplicada solo si n29_19 = 1)", respondent="Responsable principal del NNA",
             universe="NNA con autismo reportado (n = 163)", response_codes="1 Sí; 2 No", missing_codes="-99 No responde (10); NaN = no aplica",
             treatment_in_analysis="Secundario; dominio = respuestas válidas", role="tratamiento NNA", source_document=ed),
        dict(survey=e, module="NNA (2-17)", variable="n29c_19", variable_label=W_ENDIDE_NNA_OTH,
             question_wording="¿Ha recibido otro tratamiento para...? (aplicada solo si n29_19 = 1)", respondent="Responsable principal del NNA",
             universe="NNA con autismo reportado (n = 163)", response_codes="1 Sí; 2 No", missing_codes="-99 No responde (10); NaN = no aplica",
             treatment_in_analysis="Secundario; dominio = respuestas válidas", role="tratamiento NNA", source_document=ed),
        dict(survey=e, module="Adultos (18+)", variable="(no existe)", variable_label="Confirmación profesional de autismo en adultos",
             question_wording="La batería c26 no tiene ítem «¿Le ha dicho un médico…?»; solo c27 (medicamentos habituales) para el conjunto de condiciones",
             respondent="—", universe="—", response_codes="—", missing_codes="—",
             treatment_in_analysis="No estimable: no se informa confirmación profesional para adultos", role="nota", source_document=ed),
        dict(survey=e, module="Diseño", variable="fexp", variable_label="Factor de expansión personas seleccionadas en la muestra",
             question_wording="—", respondent="—", universe="Personas seleccionadas (n = 35.536); rango 24–15.246; suma 19.348.925",
             response_codes="numérico", missing_codes="NaN para personas del roster no seleccionadas",
             treatment_in_analysis="Ponderador (pw) en todas las estimaciones; producto de los factores de primera fase (precontacto Casen en Pandemia 2020) y segunda fase, ajustado por no elegibilidad, no respuesta y calibrado/suavizado",
             role="ponderador", source_document=f"{ed}; {em} sección 4"),
        dict(survey=e, module="Diseño", variable="estrato", variable_label="Estrato", question_wording="—", respondent="—",
             universe="Personas seleccionadas; 32 valores = región × zona (urbano/rural)", response_codes="1–32", missing_codes="ninguno",
             treatment_in_analysis="Estrato de varianza. El documento metodológico describe 96 estratos explícitos de segunda fase (tramo de edad × región × zona) que no se publican como variable; se usan los 32 pseudo-estratos publicados",
             role="estrato", source_document=f"{ed}; {em} sección 3.1"),
        dict(survey=e, module="Diseño", variable="cod_upm", variable_label="Unidad primaria de muestreo", question_wording="—", respondent="—",
             universe="Personas seleccionadas; 8.477 UPM (manzanas/secciones del marco Casen en Pandemia 2020); mínimo 8 UPM por estrato",
             response_codes="identificador", missing_codes="ninguno",
             treatment_in_analysis="Conglomerado de varianza (aproximación de conglomerado final con reemplazo); captura la correlación entre personas de una misma vivienda/UPM",
             role="conglomerado", source_document=f"{ed}; {em} sección 4.1"),
        dict(survey=e, module="Diseño", variable="sexo / edad", variable_label="¿Es [NOMBRE] hombre o mujer? / ¿Qué edad tiene [NOMBRE]?", question_wording="—",
             respondent="Informante del hogar", universe="Roster", response_codes="sexo 1 Hombre 2 Mujer; edad 0–106 (seleccionados 2–104)", missing_codes="ninguno",
             treatment_in_analysis="Dominios por sexo; grupos de edad 18-29/30-44/45-59/60+ (adultos) y 2-5/6-11/12-17 (NNA)", role="desagregación", source_document=ed),
        dict(survey=v, module="Personas 15+ (módulo 4)", variable="p4_6_1_h", variable_label="(Trastorno del espectro autista) ¿Ud. ha sido diagnosticado con alguno de los siguientes problemas, condición de salud o enfermedades?",
             question_wording=W_ENCAVI_DX, respondent="Persona seleccionada de 15+ (entrevista personal CAPI)",
             universe="Todas las personas de la base (n = 16.590)", response_codes="1 Sí; 2 No", missing_codes="8 No sabe (101); 9 No responde (5) — NO LEER",
             treatment_in_analysis="Primario: dominio = respuestas válidas (16.484); sensibilidad: 8/9 contados como no diagnosticados (16.590)",
             role="ítem principal ENCAVI", source_document=f"{vm}; {vq}"),
        dict(survey=v, module="Personas 15+ (módulo 4)", variable="p4_6_2_h", variable_label="(Trastorno del espectro autista) ¿Y para cuál de ellos ha recibido o está en tratamiento médico?",
             question_wording=W_ENCAVI_TX, respondent="Persona seleccionada de 15+", universe="Personas con p4_6_1_h = 1 (n = 80)",
             response_codes="1 Sí; 2 No", missing_codes="8 No sabe; 9 No responde (1); NaN = no aplica",
             treatment_in_analysis="Secundario; dominio = respuestas válidas (79)", role="tratamiento ENCAVI", source_document=f"{vm}; {vq}"),
        dict(survey=v, module="Diseño", variable="w_personas_cal", variable_label="Ponderador personas calibrado 4 márgenes (sexo_edad, sexo_educ, región, macro_área)",
             question_wording="—", respondent="—", universe="Todas las personas (n = 16.590); rango 13,1–7.672,2; suma 16.238.022 (población 15+ Censo 2017)",
             response_codes="numérico", missing_codes="ninguno", treatment_in_analysis="Ponderador (pw)", role="ponderador", source_document=f"{vm} (ID 436; svyset)"),
        dict(survey=v, module="Diseño", variable="varstrat", variable_label="Variable pseudo-estrato", question_wording="—", respondent="—",
             universe="96 pseudo-estratos; mínimo 2 UPM por estrato (sin unidades únicas)", response_codes="identificador", missing_codes="ninguno",
             treatment_in_analysis="Estrato de varianza (svyset varunit [pw = w_personas_cal], strata(varstrat) singleunit(certainty))", role="estrato", source_document=f"{vm} (ID 438)"),
        dict(survey=v, module="Diseño", variable="varunit", variable_label="Variable pseudo-conglomerado", question_wording="—", respondent="—",
             universe="350 pseudo-conglomerados", response_codes="identificador", missing_codes="ninguno",
             treatment_in_analysis="Conglomerado de varianza (conglomerado final con reemplazo)", role="conglomerado", source_document=f"{vm} (ID 437)"),
        dict(survey=v, module="Diseño", variable="sexo / edad / edad5", variable_label="Sexo del seleccionado/a; Edad del seleccionado/a; Tramos etarios",
             question_wording="—", respondent="—", universe="Todas las personas", response_codes="sexo 1 Hombre 2 Mujer; edad5 1 15-19, 2 20-29, 3 30-49, 4 50-64, 5 65+",
             missing_codes="ninguno", treatment_in_analysis="Dominios por sexo y tramo etario edad5", role="desagregación", source_document=vm),
    ]
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Controles
# ---------------------------------------------------------------------------
def control(name, key, expected, observed, kind="count", note="", tol=RATE_TOL) -> dict:
    exp = float(expected)
    obs = float(observed)
    ad = obs - exp
    rd = ad / exp if exp != 0 else (0.0 if ad == 0 else np.inf)
    if kind == "count":
        ok = abs(ad) < 0.5
    elif kind == "rate":
        ok = abs(rd) <= tol
    elif kind == "absolute":
        ok = abs(ad) <= tol
    else:
        raise ValueError(kind)
    return dict(name=name, key=key, expected=exp, observed=obs, abs_diff=ad, rel_diff=rd, status="ok" if ok else "differs", note=note)


def build_controls(est: pd.DataFrame, sel: pd.DataFrame, enc: pd.DataFrame, checks: list[dict]) -> pd.DataFrame:
    def pick(domain, subgroup="total", estimate_type=None):
        q = est[(est.domain == domain) & (est.subgroup == subgroup)]
        if estimate_type:
            q = q[q.estimate_type == estimate_type]
        if len(q) != 1:
            raise RuntimeError(f"Control ambiguo o ausente: {domain} / {subgroup} / {estimate_type}")
        return q.iloc[0]

    ad = pick("ENDIDE adultos 18+: autismo reportado")
    nn = pick("ENDIDE NNA 2-17: autismo reportado")
    cf = pick("ENDIDE NNA con autismo reportado: confirmado por un médico", estimate_type="primary")
    cf_all = pick("ENDIDE NNA 2-17: autismo reportado y confirmado por un médico")
    ev = pick("ENCAVI 15+: diagnóstico de trastorno del espectro autista", estimate_type="primary")
    es = pick("ENCAVI 15+: diagnóstico de trastorno del espectro autista (sensibilidad: No sabe/No responde = no diagnosticado)")
    cu = CFG.CONTROLS
    rows = [
        control("endide_unweighted", "adults", cu["endide_unweighted"]["adults"], ad.cases, note="c26_33 == 1 entre personas seleccionadas de 18+"),
        control("endide_unweighted", "children", cu["endide_unweighted"]["children"], nn.cases, note="n29_19 == 1 entre personas seleccionadas de 2–17"),
        control("endide_unweighted", "children_confirmed", cu["endide_unweighted"]["children_confirmed"], cf.cases, note="n29a_19 == 1 (Sí) entre NNA con autismo reportado"),
        control("endide_codebook", "selected_persons", 35536, len(sel), note="Libro de códigos ID 7 (folio) y ID 6 (confirma_seleccionado = 1)"),
        control("endide_codebook", "adult_item_n", 29938 + 72, ad.n, note="Libro de códigos ID 190: 29.938 No + 72 Sí"),
        control("endide_codebook", "nna_item_n", 5363 + 163, nn.n, note="Libro de códigos ID 917: 5.363 No + 163 Sí"),
        control("endide_codebook", "n29a_19_valid_n", 139 + 14, cf.n, note="Libro de códigos ID 958: 139 Sí + 14 No; 10 No responde excluidos del dominio primario"),
        control("endide_codebook", "n29a_19_no_response", 10, int((sel.n29a_19 == -99).sum()), note="Libro de códigos ID 958: -99 No responde = 10"),
        control("encavi_unweighted", "positive", cu["encavi_unweighted"]["positive"], ev.cases, note="p4_6_1_h == 1"),
        control("encavi_unweighted", "n", cu["encavi_unweighted"]["n"], len(enc), note="Filas de la base (manual: 16.590 casos); dominio primario con respuesta válida = %d" % ev.n),
        control("encavi_manual", "weighted_population_15plus", 16238022, enc.w_personas_cal.sum(), kind="rate",
                note="Manual: los factores representan a 16.238.022 personas de 15+ (Censo 2017); suma de w_personas_cal"),
        control("preliminary_weighted", "endide_adults", 0.0029, ad.proportion, kind="rate",
                note="DATA_REVIEW: 0,29 % (redondeado a dos decimales porcentuales); recalculado con diseño complejo; el punto no cambia con el diseño, solo el EE/IC"),
        control("preliminary_weighted", "endide_children", 0.0286, nn.proportion, kind="rate",
                note="DATA_REVIEW: 2,86 %; recalculado 2,867 % — diferencia de redondeo"),
        control("preliminary_weighted", "encavi_15plus_sensitivity_dk_as_no", 0.0071, es.proportion, kind="rate",
                note="DATA_REVIEW: 0,71 %; reproducido exactamente cuando No sabe/No responde (106) se cuentan como no diagnosticados (denominador 16.590)"),
        control("preliminary_weighted", "encavi_15plus_primary_valid_only", 0.0071, ev.proportion, kind="rate",
                note="Estimación primaria (respuestas válidas, n = 16.484) frente al 0,71 % preliminar; dentro de la tolerancia del 0,5 % relativo"),
        control("preliminary_weighted_total", "encavi_persons", 114817, ev.weighted_total, kind="rate",
                note="DATA_REVIEW: ~114.817 personas; total ponderado idéntico en primario y sensibilidad (numerador sin cambios)"),
        control("endide_unweighted", "children_confirmed_numerator_share_all_nna", 139, cf_all.cases, note="139 confirmados como proporción de todos los NNA (5.526); DATA_REVIEW no publicó porcentaje"),
    ]
    chk = pd.DataFrame(checks)

    def cval(check, contains):
        q = chk[(chk.check == check) & chk.quantity.str.contains(contains, regex=False)]
        return q.iloc[0]

    r = cval("point_estimate", "población completa")
    rows.append(control("design_check", "taylor_equals_naive_weighted_max_abs_diff", 0.0, r.value, kind="absolute", tol=1e-12, note="Simulación: el punto de Taylor coincide con la proporción ponderada ingenua"))
    r = cval("se_taylor_vs_mc", "población completa")
    rows.append(control("design_check", "taylor_se_over_mc_se_all", 1.0, r.ratio, kind="rate", tol=SIM_TOL, note=f"Simulación: media EE Taylor / EE empírico Monte Carlo; tolerancia ±{100 * SIM_TOL:.0f} %"))
    r = cval("se_taylor_vs_mc", "dominio")
    rows.append(control("design_check", "taylor_se_over_mc_se_domain", 1.0, r.ratio, kind="rate", tol=SIM_TOL, note=f"Simulación (dominio): tolerancia ±{100 * SIM_TOL:.0f} %"))
    r = cval("se_bootstrap_vs_mc", "población completa")
    rows.append(control("design_check", "bootstrap_se_over_mc_se_all", 1.0, r.ratio, kind="rate", tol=SIM_TOL, note=f"Simulación: bootstrap Rao–Wu / EE empírico; tolerancia ±{100 * SIM_TOL:.0f} %"))
    r = cval("se_taylor_vs_bootstrap", "dominio")
    rows.append(control("design_check", "taylor_se_over_bootstrap_se_domain", 1.0, r.ratio, kind="rate", tol=SIM_TOL, note=f"Simulación (dominio): Taylor / bootstrap; tolerancia ±{100 * SIM_TOL:.0f} %"))
    r = cval("ci_coverage", "población completa")
    rows.append(control("design_check", "ci95_logit_coverage_all", 0.95, r.value, kind="absolute", tol=0.03, note="Simulación: cobertura empírica del IC 95 % logit; tolerancia ±0,03"))
    r = cval("ci_coverage", "dominio")
    rows.append(control("design_check", "ci95_logit_coverage_domain", 0.95, r.value, kind="absolute", tol=0.03, note="Simulación (dominio): tolerancia ±0,03"))
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-design-check", action="store_true", help="omite la simulación de verificación de common.survey_proportion")
    ap.add_argument("--mc-replicates", type=int, default=400, help="muestras Monte Carlo de la simulación (por defecto 400)")
    ap.add_argument("--bootstrap-replicates", type=int, default=500, help="réplicas bootstrap Rao–Wu por muestra (por defecto 500)")
    ap.add_argument("--tmpdir", default=os.environ.get("LANCET_TMPDIR"), help="directorio para la extracción temporal del ZIP ENDIDE (por defecto el temporal del sistema)")
    args = ap.parse_args(argv)
    t0 = time.time()
    for p in (ENDIDE_ZIP, ENCAVI_DTA):
        if not p.is_file():
            raise FileNotFoundError(p)

    sel = load_endide(args.tmpdir)
    enc = load_encavi()
    rows = endide_rows(sel) + encavi_rows(enc)
    est = pd.DataFrame(rows)
    cols = ["survey", "survey_year", "variant", "module", "domain", "domain_definition", "subgroup_type", "subgroup", "estimate_type",
            "item_variable", "item_wording", "positive_definition", "weight_var", "strata_var", "psu_var",
            "n", "cases", "proportion", "proportion_unit", "se", "lo", "hi", "ci_method", "weighted_total", "weighted_population", "weighted_unit",
            "deff", "rse", "df", "n_psu", "n_strata", "precision_flag", "deff_note", "variant_note",
            "source_file", "source_sha256", "source_documents", "script"]
    est = est[cols]
    C.atomic_write_csv(est, CFG.TIDY / "survey_estimates.csv")
    log(f"survey_estimates.csv: {len(est)} filas")
    for _, r in est[est.subgroup == "total"].iterrows():
        log(f"  {r.domain} [{r.estimate_type}]: n={r.n:,} casos={r.cases} p={100 * r.proportion:.3f} % "
            f"(IC95 {100 * r.lo:.3f}–{100 * r.hi:.3f}) EE={100 * r.se:.3f} pp total={r.weighted_total:,.0f} DEFF={r.deff:.2f} {r.precision_flag}")

    items = items_dictionary()
    C.atomic_write_csv(items, CFG.TIDY / "survey_items_dictionary.csv")
    log(f"survey_items_dictionary.csv: {len(items)} filas")

    if args.skip_design_check:
        checks = []
        log("simulación de verificación omitida (--skip-design-check)")
    else:
        t1 = time.time()
        checks = design_check(R=args.mc_replicates, B=args.bootstrap_replicates)
        C.atomic_write_csv(pd.DataFrame(checks), CFG.TIDY / "survey_design_check.csv")
        log(f"survey_design_check.csv: {len(checks)} filas ({time.time() - t1:.1f} s)")
        for c in checks:
            log(f"  {c['check']}: {c['quantity']} = {c['value']:.5f}" + (f" (ref {c['reference']:.5f}, razón {c['ratio']:.3f})" if c['ratio'] == c['ratio'] else ""))

    if checks:
        ctr = build_controls(est, sel, enc, checks)
    else:
        ctr = build_controls(est, sel, enc, design_check(R=60, B=200))
    C.atomic_write_csv(ctr, CFG.OUT / "controls" / f"{MODULE}_controls.csv")
    n_diff = int((ctr.status == "differs").sum())
    log(f"{MODULE}_controls.csv: {len(ctr)} controles, {n_diff} con diferencias")
    for _, r in ctr.iterrows():
        log(f"  [{r.status}] {r['name']}/{r.key}: esperado {r.expected:g}, observado {r.observed:g}")
    log(f"tiempo total {time.time() - t0:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
