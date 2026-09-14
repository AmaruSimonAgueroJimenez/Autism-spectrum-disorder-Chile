# -*- coding: utf-8 -*-
"""config.py — rutas, años, variantes de definición y códigos del estudio multisistema (Lancet Regional Health – Americas).

Todo script del pipeline importa este módulo. Las rutas de datos respetan
`ASESORIAS_DATA_ROOT` y `AUTISM_DATA_ROOT`; nunca se copian bases grandes al repositorio.

Variantes de definición (el usuario pidió dos versiones completas del análisis):
  * `con_rett`: familia F84 completa. GRD: cualquier código F84.x (incluye F84.2, síndrome de Rett).
                REM A05/P6: todas las categorías de trastornos generalizados del desarrollo, incluidas las
                filas de síndrome de Rett (05990024/05990029, P6241030/P6241080).
  * `sin_rett`: familia F84 sin síndrome de Rett. GRD: F84.x excepto F84.2. REM A05/P6: mismas categorías
                sin las filas de Rett.
En ambas variantes se presentan además, como series prespecificadas idénticas, el autismo estricto de
REM (05990022 / P6241010 / P6241060) y F84 en posición principal (GRD).

Idiomas: `es` y `en`. Cada salida (tabla, figura, manuscrito) se genera por variante e idioma.
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
HERE = Path(__file__).resolve().parent
OUT = HERE / "outputs"
TIDY = OUT / "tidy"
CONTROLS = OUT / "controls"
MANUSCRIPT = HERE / "manuscript"
#: The manuscript folder holds two different products and they are kept apart:
#:   SUBMISSION  the journal package built for The Lancet Regional Health - Americas (one case
#:               definition, journal format) — the documents that are actually sent;
#:   CORPUS      the full bilingual two-variant corpus the study produced, kept as the working record.
SUBMISSION = MANUSCRIPT / "04_submission_lancet_americas"
CORPUS = MANUSCRIPT / "02_others"
for _d in (TIDY, CONTROLS, MANUSCRIPT, SUBMISSION, CORPUS):
    _d.mkdir(parents=True, exist_ok=True)

DATA_ROOT = Path(os.environ.get("ASESORIAS_DATA_ROOT", "/Volumes/Datos/Asesorias_Data"))
AUTISM_ROOT = Path(os.environ.get("AUTISM_DATA_ROOT", str(DATA_ROOT / "Autism")))

PATHS = {
    "grd": DATA_ROOT / "GRD",                                   # GRD_PUBLICO_{year}.csv, sep="|"
    "grd_metadata": DATA_ROOT / "GRD" / "metadata",
    "rem_a": DATA_ROOT / "REM" / "SerieA",                      # SerieA_{year}.csv, sep=";"
    "rem_a_dicts": DATA_ROOT / "REM" / "SerieA" / "metadata" / "diccionarios",
    "rem_p": DATA_ROOT / "REM" / "SerieP",                      # SerieP_{year}.csv, sep=";"
    "rem_p_dicts": DATA_ROOT / "REM" / "SerieP" / "diccionarios",
    "deis_egresos": DATA_ROOT / "DEIS" / "Egresos",             # {year}.csv
    "fonasa": DATA_ROOT / "FONASA",                             # Resultados_YYYY12.rar/.zip (agregados), APS/, microdata/
    "fonasa_aps": DATA_ROOT / "FONASA" / "APS",                 # Inscritos_APS_YYYY12.csv
    "isapre": AUTISM_ROOT / "Cobertura" / "ISAPRE",             # isapre_beneficiarios_comuna_{year}.xls(x)
    "rem20": AUTISM_ROOT / "DEIS" / "REM20",                    # indicadores_rem20.csv, diccionario_rem20.xlsx
    "establecimientos": AUTISM_ROOT / "DEIS" / "Establecimientos",
    "ine": AUTISM_ROOT / "Poblacion" / "INE",                   # proyecciones_comuna_edad_sexo_2002_2035_base_2017.csv, Censo_2024/, Base_2024/
    "endide": AUTISM_ROOT / "Encuestas" / "ENDIDE_2022",
    "encavi": AUTISM_ROOT / "Encuestas" / "ENCAVI_2023_2024",
    "casen": AUTISM_ROOT / "Encuestas" / "CASEN_2024",
    "mineduc": AUTISM_ROOT / "Educacion" / "MINEDUC",
    "junaeb": AUTISM_ROOT / "Educacion" / "JUNAEB" / "EVE",     # microdata/{year}/*.csv, metadata/
    "sae": AUTISM_ROOT / "Territorio" / "SAE_2024",
    "download_manifest": AUTISM_ROOT / "metadata" / "download_manifest.csv",
    "repo_population_parquet": REPO / "data" / "censo_proyecciones_ano_edad_genero.parquet",
    "repo_shapes_comunas": REPO / "data" / "comunas.shp",
    "repo_shapes_regiones": REPO / "data" / "Regional.shp",
    "rem_pathway_codes": REPO / "scripts" / "downloads" / "rem_pathway_codes.csv",
}

YEARS_GRD = list(range(2019, 2025))
YEARS_REM = list(range(2019, 2026))
YEARS_STOCK = list(range(2019, 2026))
PANDEMIC_YEARS = [2020, 2021]
LAW_YEAR = 2023  # Ley 21.545, publicada el 10 de marzo de 2023: contexto, no intervención causal.

LANGUAGES = ["es", "en"]

# --- GRD: familia F84 -------------------------------------------------------------------------
F84_SUBCODES = ["F84", "F840", "F841", "F842", "F843", "F844", "F845", "F848", "F849"]
RETT_GRD = {"F842"}

# --- REM: códigos de la ruta administrativa (ver scripts/downloads/rem_pathway_codes.csv) -------
A05_ENTRY = {"autism": "05990022", "asperger": "05990023", "rett": "05990024", "disintegrative": "05990025", "pdd_nos": "05990026"}
A05_EXIT = {"autism": "05990027", "asperger": "05990028", "rett": "05990029", "disintegrative": "05990030", "pdd_nos": "05990031"}
A05_BROAD_PRE2021 = {"entry": "06902600", "exit": "05225000"}
P6_PRIMARY = {"autism": "P6241010", "asperger": "P6241020", "rett": "P6241030", "disintegrative": "P6241040", "pdd_nos": "P6241050"}
P6_SPECIALTY = {"autism": "P6241060", "asperger": "P6241070", "rett": "P6241080", "disintegrative": "P6241090", "pdd_nos": "P6241100"}
P6_BROAD_PRE2021 = {"primary": "P6223000", "specialty": "P6223380"}
P2_TEA = "P2500500"
P2_NANEAS_TOTAL = "P2501878"
A27 = {"counselling": "29101566", "assisted_referral": "29101574"}
A28 = {"primary": "29101629", "hospital": "29101651"}
A03_LEGACY = {"control_18m": "03500404", "language_social_alteration": "03500405", "mchat_done": "03500406", "mchat_altered": "03500407"}
A03_2023_2024 = {"suspected_other": "09600212", "low": "09600213", "medium": "09600214", "high": "09600215", "high_referred": "09600216",
                 "second_part_medium": "09600217", "second_no_referral": "09600218", "second_referral": "09600219"}
A03_2024_31_59 = {"evaluated": "03700104", "suspected_elsewhere": "03700105", "alert_yes": "03700106", "alert_no": "03700107", "referral_yes": "03700108", "referral_no": "03700109"}
A03_2025 = {"motive_eedp": "03710013", "motive_risk": "03710014", "motive_both": "03710015", "low": "03710016", "medium_no_referral": "03710017",
            "medium_referral": "03710018", "high_referral": "03710019", "susp_30_59_no_referral": "03710020", "susp_30_59_referral": "03710021"}

VARIANTS = {
    "con_rett": {
        "label": {"es": "F84 completo (incluye síndrome de Rett)", "en": "Full F84 family (including Rett syndrome)"},
        "short": {"es": "con Rett", "en": "with Rett"},
        "grd_subcodes": F84_SUBCODES,
        "a05_entry": list(A05_ENTRY.values()),
        "a05_exit": list(A05_EXIT.values()),
        "p6_primary": list(P6_PRIMARY.values()),
        "p6_specialty": list(P6_SPECIALTY.values()),
    },
    "sin_rett": {
        "label": {"es": "F84 sin síndrome de Rett", "en": "F84 family excluding Rett syndrome"},
        "short": {"es": "sin Rett", "en": "without Rett"},
        "grd_subcodes": [c for c in F84_SUBCODES if c not in RETT_GRD],
        "a05_entry": [v for k, v in A05_ENTRY.items() if k != "rett"],
        "a05_exit": [v for k, v in A05_EXIT.items() if k != "rett"],
        "p6_primary": [v for k, v in P6_PRIMARY.items() if k != "rett"],
        "p6_specialty": [v for k, v in P6_SPECIALTY.items() if k != "rett"],
    },
}
STRICT = {"a05_entry": A05_ENTRY["autism"], "a05_exit": A05_EXIT["autism"], "p6_primary": P6_PRIMARY["autism"], "p6_specialty": P6_SPECIALTY["autism"]}

# --- Controles de reproducción (valores esperados del prompt; se comparan en outputs/controls/) --
CONTROLS = {
    "grd_f84_any": {2019: 2385, 2020: 1633, 2021: 2399, 2022: 3912, 2023: 6473, 2024: 8818},
    "grd_f84_any_panel65": {2019: 2385, 2020: 1633, 2021: 2399, 2022: 3912, 2023: 6421, 2024: 8557},
    "grd_f84_any_strict_hospitalisation": {2019: 1960, 2020: 1550, 2021: 2217, 2022: 3561, 2023: 5797, 2024: 7500},
    "grd_f84_principal": {2019: 241, 2020: 163, 2021: 189, 2022: 304, 2023: 366, 2024: 401},
    "grd_records_total": {2019: 1151475, 2020: 781912, 2021: 816909, 2022: 932839, 2023: 1039587, 2024: 1085813},
    "grd_hospitals_observed": {2019: 65, 2020: 65, 2021: 65, 2022: 65, 2023: 68, 2024: 72},
    "grd_coding_depth_all_mean": {2019: 4.39, 2024: 5.78},
    "grd_coding_depth_f84_mean": {2019: 5.00, 2024: 6.04},
    "grd_f84_secondary_only_share_2024": 0.955,
    "grd_cma": {2019: 168, 2020: 83, 2021: 182, 2022: 351, 2023: 631, 2024: 1113},
    "grd_persons_within_year_f84_any": {2019: 1983, 2020: 1338, 2021: 1979, 2022: 3265, 2023: 5268, 2024: 7214},
    "a05_autism_entries": {2021: 2085, 2022: 4640, 2023: 8049, 2024: 11842, 2025: 13155},
    "a05_autism_exits": {2021: 494, 2022: 831, 2023: 1814, 2024: 3315, 2025: 3367},
    "a27_counselling": {2023: 2380, 2024: 3874, 2025: 3026},
    "a27_assisted_referral": {2023: 672, 2024: 1068, 2025: 878},
    "a28_primary": {2023: 3962, 2024: 7033, 2025: 15859},
    "a28_hospital": {2023: 731, 2024: 1045, 2025: 1740},
    "p2_tea_december": {2019: 1854, 2020: 1919, 2021: 3853, 2022: 7923, 2023: 13190, 2024: 21737, 2025: 29974},
    "p2_establishments_december": {2019: 460, 2020: 400, 2021: 640, 2022: 897, 2023: 1012, 2024: 1218, 2025: 1325},
    "p2_naneas_total_december": {2023: 59907, 2024: 77081, 2025: 100789},
    "p6_primary_december": {2019: 5520, 2020: 5185, 2021: 2257, 2022: 5042, 2023: 9717, 2024: 15934, 2025: 21843},
    "p6_specialty_december": {2019: 6624, 2020: 6905, 2021: 3562, 2022: 4684, 2023: 7982, 2024: 8835, 2025: 12645},
    "a03_legacy_mchat_done": {2019: 2613, 2020: 816, 2021: 1833, 2022: 3455},
    "a03_legacy_mchat_altered": {2019: 1640, 2020: 288, 2021: 879, 2022: 1535},
    "a03_2023_low_medium_high": {2023: (14083, 3642, 1907), 2024: (18142, 4698, 2234)},
    "fonasa_beneficiaries_december": {2019: 14841577, 2020: 15142528, 2021: 15233814, 2022: 15613584, 2023: 16229898, 2024: 16752189, 2025: 17132611},
    "aps_enrolled_december": {2019: 13777051, 2020: 13885509, 2021: 14100841, 2022: 14522464, 2023: 15051673, 2024: 15353689, 2025: 15791862},
    "aps_centres": {2019: 1890, 2020: 1956, 2021: 1984, 2022: 2026, 2023: 2057, 2024: 2078, 2025: 2091},
    "isapre_beneficiaries_december": {2019: 3431126, 2020: 3339226, 2021: 3330254, 2022: 3151885, 2023: 2788257, 2024: 2630026, 2025: 2517305},
    "ine_population_national": {2019: 19107216, 2025: 20206953},
    "rem20_panel_188_retention": {2019: 0.9976, 2025: 0.9816},
    "aps_panel_1871_retention": {2019: 0.9987, 2025: 0.9754},
    "pie_tea_strict": {2019: 11877, 2020: 13613, 2021: 18801, 2022: 28845, 2023: 47551},
    "pie_tea_asperger": {2019: 9135, 2020: 9977, 2021: 12081, 2022: 14095, 2023: 16091},
    "pie_harmonised": {2019: 21012, 2020: 23590, 2021: 30882, 2022: 42940, 2023: 63642, 2024: 86475, 2025: 106786},
    "pie_special_schools": {2024: 2505, 2025: 2626},
    "endide_unweighted": {"adults": 72, "children": 163, "children_confirmed": 139},
    "encavi_unweighted": {"positive": 80, "n": 16590},
    "junaeb_unweighted_2024": {"parvularia": 17641, "basico1": 10245, "basico5": 7468},
    "junaeb_unweighted_2025": {"parvularia": 18785, "basico1": 12536, "basico5": 9887, "medio1": 9164},
}

# Comunas no continentales (código único territorial) excluidas de contigüidad.
NON_CONTINENTAL = {5201, 5104, 12202, 12201}
# Alias de nombres de comuna (INE frente a DEIS/GRD); nunca hacer fuzzy matching silencioso.
COMUNA_ALIASES = {"AISEN": "AYSEN", "COIHAIQUE": "COYHAIQUE", "CABO DE HORNOS (EX-NAVARINO)": "CABO DE HORNOS", "CON CON": "CONCON"}
