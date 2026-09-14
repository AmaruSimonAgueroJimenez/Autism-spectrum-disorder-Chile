#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""15b_spatial_correlation.py — módulo 15b: análisis espacial y de correlación territorial completo
(serie de figuras E40–E49 y sus tablas) para el material suplementario del estudio multifuente
the target journal.

Todo lo que produce este módulo es **descriptivo y ecológico**. Los recuentos son reconocimiento
administrativo, nunca prevalencia ni incidencia; el resultado GRD es «episodios con F84 documentado»
(F84 principal es una serie aparte); las fuentes no se enlazan por persona, de modo que ninguna
correlación entre fuentes describe trayectorias individuales; la Ley 21.545 (marzo de 2023) es contexto
de política y nunca se le atribuye un efecto; los stocks (P2, P6, FONASA, APS, ISAPRE) y los flujos
(A05, GRD, REM-20) no comparten eje ni se suman; el cero, el vacío y «no reportado» son estados
distintos; las celdas con menos de cinco eventos se muestran como «<5» en las tablas territoriales.

Compatibilidad numerador/denominador (se rotula en cada mapa, tabla y correlación):
  * COMPATIBLE  — GRD: numerador por **comuna de residencia** del episodio y denominador INE por comuna de
                  residencia. La tasa poblacional y la razón estandarizada son interpretables como
                  reconocimiento administrativo de residentes.
  * NO COMPATIBLE — REM (A05, P2, P6), REM-20 y APS: el numerador se localiza en la comuna del
                  **establecimiento que reporta** (lugar de atención) y el denominador es población
                  residente. Las comunas sin establecimiento reportante producen ceros estructurales y las
                  comunas con hospitales o COSAM de referencia concentran atención de residentes de otras
                  comunas. Toda cifra derivada lleva la advertencia explícita.

Métodos preespecificados en `analysis_plan.md` (sección de análisis espacial del suplemento):

 (1) Indicadores comunales por variante y periodo, cada uno con su denominador propio
     (`outputs/tidy/spatial_comuna_indicators.csv`).
 (2) Estandarización indirecta por comuna: cuentas esperadas a partir de las tasas nacionales por edad,
     sexo y año de la **misma fuente**; razón estandarizada con límites exactos de Poisson; razón suavizada
     empírica de Bayes de Marshall con su peso de contracción, y la media y la varianza de la distribución
     previa (`outputs/tidy/spatial_comuna_standardised.csv`).
 (3) Autocorrelación espacial global: I de Moran con contigüidad reina estandarizada por filas, inferencia
     analítica y por 999 permutaciones con semilla fija, para la tasa cruda, la razón cruda y la razón
     suavizada, por variante y por fuente; sensibilidad con pesos de k vecinos más próximos (k = 4 y k = 8)
     y con pesos de distancia inversa; y lo mismo para las 16 regiones como escala más gruesa
     (`outputs/tidy/spatial_moran.csv`).
 (4) Indicadores locales: LISA con clasificación por cuadrante, p de permutación y umbral de
     Benjamini–Hochberg; Gi* de Getis–Ord con puntos calientes y fríos; mapas de ambos con el número de
     comunas en cada clase y una tabla con cada comuna significativa (`outputs/tidy/spatial_lisa.csv`).
 (5) Correlación territorial entre sistemas: rho de Spearman con intervalo de Fisher-z sobre comunas y
     sobre regiones para cada par de indicadores, matriz de correlación e I de Moran bivariada de cada par
     con inferencia por permutación (`outputs/tidy/spatial_correlations.csv`,
     `outputs/tidy/spatial_bivariate_moran.csv`).
 (6) Desigualdad de la distribución territorial: curva de Lorenz y Gini de episodios e ingresos frente a
     población, índice de Theil descompuesto dentro y entre regiones, y razón entre el decil superior y el
     inferior, por fuente y año (`outputs/tidy/spatial_inequality.csv`).
 (7) Estabilidad: Spearman entre los rangos comunales de años sucesivos y correlación entre la razón
     suavizada de 2019–2021 y la de 2022–2024 (`outputs/tidy/spatial_stability.csv`).
 (8) Sensibilidad: excluyendo comunas con menos de 5 eventos, excluyendo la Región Metropolitana,
     excluyendo las comunas no continentales y usando el denominador del Censo 2024 en lugar de la
     proyección base 2017 (filas `sensitivity` de `outputs/tidy/spatial_moran.csv`).

Entradas (todas ya verificadas por módulos anteriores; este módulo no reescribe ninguna):
  outputs/tidy/grd_territory.csv                episodios y personas dentro del año por comuna de RESIDENCIA (módulo 11)
  outputs/tidy/grd_hospital_year.csv            hospital (lugar de ATENCIÓN) → comuna vía catálogo DEIS
  outputs/tidy/rem_pathway_tidy.csv             filas REM con IdComuna del ESTABLECIMIENTO (5 dígitos)
  outputs/tidy/rem_establishment_year.csv       establecimientos reportantes por año y comuna
  outputs/tidy/rem_pathway_annual.csv           totales nacionales de control
  outputs/tidy/grd_year_summary.csv             totales nacionales de control
  outputs/tidy/deis_*.csv                       egresos DEIS (sin desglose comunal en la capa tidy: se documenta)
  outputs/tidy/ine_population_comuna_year_age_sex.csv   denominador poblacional base 2017
  outputs/tidy/ine_population_sensitivity.csv   denominador Censo 2024 (sensibilidad, nunca mezclado)
  outputs/tidy/comuna_crosswalk.csv             CUT ↔ código DEIS ↔ nombre INE (enlace auditable)
  outputs/tidy/comuna_unmatched.csv             nombres no enlazados documentados
  outputs/tidy/coverage_layers_year.csv         capas de cobertura nacionales
  outputs/tidy/aps_enrolment_comuna_year.csv    inscritos APS por comuna del CENTRO
  outputs/tidy/fonasa_beneficiaries_comuna_year.csv, isapre_beneficiaries_comuna_year.csv
  outputs/tidy/rem20_establishment_year.csv     egresos REM-20 (actividad/capacidad)
  outputs/tidy/education_summary_year.csv       PIE/JUNAEB: solo nacional (no hay desglose comunal aquí)
  /Volumes/Datos/.../Territorio/SAE_2024/SAE_multidimensional_2024.xlsx, SAE_ingresos_2024.xlsx
  /Volumes/Datos/.../Poblacion/INE/proyecciones_comuna_area_urbana_rural_2002_2035_base_2017.csv
  /Volumes/Datos/.../DEIS/Establecimientos/establecimientos_salud_vigentes.csv
  data/comunas.shp y data/Regional.shp (report_helpers.load_comunas / load_regions; EPSG:3857)

Salidas:
  outputs/tidy/spatial_*.csv                                   tablas tidy (escritura atómica)
  outputs/<variante>/<idioma>/extra/figures/E4*.png (+ captions.json)   láminas E40–E49 a 600 ppp
  outputs/<variante>/<idioma>/extra/tables/E4*.csv, E50*, E51* (+ _numeric.csv + titles.json)
  outputs/controls/15b_spatial_correlation_controls.csv        esperado frente a observado
  outputs/controls/15b_spatial_correlation_runlog.json         tiempos, versiones y semillas

Uso: python3 study/pipeline/15b_spatial_correlation.py
       [--variants con_rett sin_rett] [--langs es en] [--permutations 999] [--no-figures] [--no-tables]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import textwrap
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.ticker  # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

HERE = Path(__file__).resolve().parent
LA = HERE.parent
REPO = LA.parent
for _p in (str(LA), str(REPO / "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import config as CFG  # noqa: E402
import common as C  # noqa: E402
import labels as LB  # noqa: E402
from report_helpers import load_comunas, load_regions  # noqa: E402
from epi_helpers import REGION_NAMES, REGION_ORDER, poisson_limits, empirical_bayes_ratio, standardized_ratio  # noqa: E402

MODULE = "15b_spatial_correlation"
SCRIPT = str(Path(__file__).resolve().relative_to(REPO))
CONTROLS_DIR = CFG.OUT / "controls"
CONTROLS_DIR.mkdir(parents=True, exist_ok=True)
TIDY = CFG.TIDY

SEED = 20260905                 # semilla fija de todas las permutaciones (se registra en el runlog)
PERMUTATIONS = 999
ALPHA = 0.05
FDR_Q = 0.05                    # umbral de Benjamini–Hochberg de los indicadores locales
SUPPRESSION_THRESHOLD = 5       # celdas con menos de 5 eventos se muestran como «<5»
PER = 100_000
T0 = time.time()


def log(msg: str) -> None:
    print(f"[{time.time() - T0:7.1f}s] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Controles (mismo formato que el resto del pipeline)
# ---------------------------------------------------------------------------
class Controls:
    """name,key,expected,observed,abs_diff,rel_diff,status,note."""

    def __init__(self) -> None:
        self.rows: list[dict] = []

    def add(self, name: str, key: str, expected, observed, note: str = "", status: str | None = None,
            tol: float = 1e-9) -> None:
        abs_diff = rel_diff = ""
        if status is None:
            try:
                e, o = float(expected), float(observed)
                abs_diff = o - e
                rel_diff = (o - e) / e if e else ""
                status = "ok" if abs(abs_diff) <= tol else "differs"
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


CTL = Controls()

# ---------------------------------------------------------------------------
# Registro de indicadores comunales
# ---------------------------------------------------------------------------
YEARS_GRD = list(CFG.YEARS_GRD)                 # 2019–2024
YEARS_A05 = [2021, 2022, 2023, 2024, 2025]      # era de autismo estricto/desagregado
YEARS_P6 = [2021, 2022, 2023, 2024, 2025]       # era desagregada de P6 (nunca unida con 2019–2020)
YEARS_P2 = list(CFG.YEARS_STOCK)                # 2019–2025 (código único P2500500)
YEARS_COV = list(CFG.YEARS_STOCK)

# clave: (etiqueta es/en, fuente, años, geografía del numerador, compatibilidad con denominador residencial,
#         desglose edad-sexo disponible, stock/flujo, papel)
IND = {
    "grd_episodes": dict(
        source="GRD", years=YEARS_GRD, geo="residence", compatible=True, agesex=True, kind="flow", role="outcome",
        es="Episodios GRD con F84 documentado (cualquier posición)", en="GRD episodes with documented F84 (any position)",
        file="outputs/tidy/grd_territory.csv"),
    "grd_persons": dict(
        source="GRD", years=YEARS_GRD, geo="residence", compatible=True, agesex=False, kind="flow", role="outcome",
        es="Personas únicas dentro del año con F84 documentado (GRD)", en="Unique persons within year with documented F84 (GRD)",
        file="outputs/tidy/grd_territory.csv"),
    "grd_principal": dict(
        source="GRD", years=YEARS_GRD, geo="residence", compatible=True, agesex=True, kind="flow", role="outcome",
        es="Episodios GRD con F84 principal", en="GRD episodes with F84 as principal diagnosis",
        file="outputs/tidy/grd_territory.csv"),
    "a05_entries": dict(
        source="REM A05", years=YEARS_A05, geo="care", compatible=False, agesex=True, kind="flow", role="outcome",
        es="Ingresos a salud mental por familia TGD (REM A05, 2021–2025)", en="Mental-health entries for the PDD family (REM A05, 2021–2025)",
        file="outputs/tidy/rem_pathway_tidy.csv"),
    "p2_stock": dict(
        source="REM P2", years=YEARS_P2, geo="care", compatible=False, agesex=False, kind="stock", role="outcome",
        es="Población bajo control NANEAS con TEA en diciembre (REM P2)", en="December NANEAS population under control with ASD (REM P2)",
        file="outputs/tidy/rem_pathway_tidy.csv"),
    "p6_primary": dict(
        source="REM P6", years=YEARS_P6, geo="care", compatible=False, agesex=False, kind="stock", role="outcome",
        es="Población bajo control en APS por familia TGD en diciembre (REM P6, 2021–2025)", en="December primary-care population under control for the PDD family (REM P6, 2021–2025)",
        file="outputs/tidy/rem_pathway_tidy.csv"),
    "p6_specialty": dict(
        source="REM P6", years=YEARS_P6, geo="care", compatible=False, agesex=False, kind="stock", role="outcome",
        es="Población bajo control en especialidad por familia TGD en diciembre (REM P6, 2021–2025)", en="December specialty population under control for the PDD family (REM P6, 2021–2025)",
        file="outputs/tidy/rem_pathway_tidy.csv"),
    "aps_enrolled": dict(
        source="FONASA/APS", years=YEARS_COV, geo="care", compatible=False, agesex=False, kind="stock", role="coverage",
        es="Inscritos en APS en diciembre (cobertura operativa)", en="APS enrolment in December (operational coverage)",
        file="outputs/tidy/aps_enrolment_comuna_year.csv"),
    "fonasa_beneficiaries": dict(
        source="FONASA", years=YEARS_COV, geo="mixed", compatible=False, agesex=False, kind="stock", role="coverage",
        es="Beneficiarios FONASA en diciembre (aseguramiento)", en="FONASA beneficiaries in December (insurance coverage)",
        file="outputs/tidy/fonasa_beneficiaries_comuna_year.csv"),
    "rem20_discharges": dict(
        source="REM-20", years=YEARS_COV, geo="care", compatible=False, agesex=False, kind="activity", role="capacity",
        es="Egresos hospitalarios REM-20 (actividad/capacidad, no población cubierta)", en="REM-20 hospital discharges (activity/capacity, not covered population)",
        file="outputs/tidy/rem20_establishment_year.csv"),
}
CONTEXT = {
    "sae_multidimensional": dict(
        source="SAE 2024", geo="residence", kind="context", role="deprivation",
        es="Pobreza multidimensional comunal, % (SAE 2024)", en="Comuna multidimensional poverty, % (SAE 2024)",
        file="SAE_multidimensional_2024.xlsx"),
    "sae_income": dict(
        source="SAE 2024", geo="residence", kind="context", role="deprivation",
        es="Pobreza por ingresos comunal, % (SAE 2024)", en="Comuna income poverty, % (SAE 2024)",
        file="SAE_ingresos_2024.xlsx"),
    "urban_share": dict(
        source="INE", geo="residence", kind="context", role="urbanicity",
        es="Población urbana, % (proyección INE urbano-rural base 2017)", en="Urban population, % (INE urban–rural projection, base 2017)",
        file="proyecciones_comuna_area_urbana_rural_2002_2035_base_2017.csv"),
    "fonasa_share": dict(
        source="FONASA/INE", geo="mixed", kind="context", role="coverage",
        es="Beneficiarios FONASA sobre población INE, % (capas mezcladas)", en="FONASA beneficiaries over INE population, % (mixed layers)",
        file="outputs/tidy/fonasa_beneficiaries_comuna_year.csv"),
}
COUNT_INDICATORS = list(IND)
ALL_INDICATORS = COUNT_INDICATORS + list(CONTEXT)

# Periodos (los dos tramos nunca se unen con una línea cuando cambia la era de definición).
PERIODS = {
    "grd_episodes": {"full": YEARS_GRD, "early": [2019, 2020, 2021], "late": [2022, 2023, 2024]},
    "grd_persons": {"full": YEARS_GRD, "early": [2019, 2020, 2021], "late": [2022, 2023, 2024]},
    "grd_principal": {"full": YEARS_GRD, "early": [2019, 2020, 2021], "late": [2022, 2023, 2024]},
    "a05_entries": {"full": YEARS_A05, "early": [2021, 2022], "late": [2023, 2024, 2025]},
    "p2_stock": {"full": YEARS_P2, "early": [2019, 2020, 2021], "late": [2022, 2023, 2024, 2025]},
    "p6_primary": {"full": YEARS_P6, "early": [2021, 2022], "late": [2023, 2024, 2025]},
    "p6_specialty": {"full": YEARS_P6, "early": [2021, 2022], "late": [2023, 2024, 2025]},
    "aps_enrolled": {"full": YEARS_COV, "early": [2019, 2020, 2021], "late": [2022, 2023, 2024, 2025]},
    "fonasa_beneficiaries": {"full": YEARS_COV, "early": [2019, 2020, 2021], "late": [2022, 2023, 2024, 2025]},
    "rem20_discharges": {"full": YEARS_COV, "early": [2019, 2020, 2021], "late": [2022, 2023, 2024, 2025]},
}
MAIN = "grd_episodes"
LOCAL_INDICATORS = ["grd_episodes", "grd_persons", "a05_entries", "p2_stock"]

WARN_CARE = {
    "es": ("ADVERTENCIA de compatibilidad: el numerador se localiza en la comuna del ESTABLECIMIENTO que reporta "
           "(lugar de atención) y el denominador es población RESIDENTE del INE; las comunas sin establecimiento "
           "reportante producen ceros estructurales y las comunas con centros de referencia concentran atención de "
           "residentes de otras comunas. No es una tasa poblacional de la comuna."),
    "en": ("Compatibility WARNING: the numerator is located in the comuna of the REPORTING ESTABLISHMENT (place of "
           "care) while the denominator is INE RESIDENT population; comunas without a reporting establishment yield "
           "structural zeros and comunas with referral centres concentrate care of residents of other comunas. This "
           "is not a population rate of the comuna."),
}
WARN_ECOLOGICAL = {
    "es": ("Asociaciones ecológicas entre recuentos administrativos de fuentes que no se enlazan por persona: no se "
           "sigue ninguna inferencia individual, ninguna cascada asistencial y ningún efecto causal (tampoco de la "
           "Ley 21.545, que es contexto de política desde marzo de 2023)."),
    "en": ("Ecological associations between administrative counts from sources that are not person-linked: no "
           "individual-level inference, no care cascade and no causal effect follow (Law 21.545 is policy context "
           "from March 2023, not an intervention with an estimable effect)."),
}
NOT_PREVALENCE = {
    "es": ("Los recuentos son reconocimiento administrativo, nunca prevalencia ni incidencia; el resultado GRD es "
           "«episodios con F84 documentado» y F84 principal es una serie separada."),
    "en": ("Counts are administrative recognition, never prevalence or incidence; the GRD outcome is 'episodes with "
           "documented F84' and F84-principal is a separate series."),
}


# ---------------------------------------------------------------------------
# Geografía, cartografía y matrices de pesos
# ---------------------------------------------------------------------------
def load_crosswalk() -> pd.DataFrame:
    """Enlace CUT ↔ código DEIS ↔ nombre de comuna, con la ORTOGRAFÍA del nombre normalizada al imprimir.

    `comuna_crosswalk.csv` conserva el nombre tal como lo publica la fuente que lo enlazó, y esa fuente
    escribe «Los Angeles» y «Pitrufquen» sin su tilde: el panel (f) de las Figuras E40 y E41 imprimía
    «Los Angeles» en la misma columna que «Valparaíso», «Maipú», «Copiapó», «Chillán» y «Concepción».
    `labels.comuna_name` devuelve la ortografía oficial de las 81 comunas con diacrítico buscando por la
    forma plegada, de modo que la corrección no es un parche para dos nombres. Se normaliza SÓLO la
    columna que se imprime: `comuna_norm`, `aliases_norm`, el CUT y el código DEIS —que son las claves
    de cruce— se dejan exactamente como vienen."""
    cw = pd.read_csv(TIDY / "comuna_crosswalk.csv")
    cw["cut_comuna"] = cw.cut_comuna.astype(int)
    cw["deis_code"] = cw.deis_code.astype(str).str.zfill(5)
    cw["comuna_name_ine"] = cw.comuna_name_ine.map(LB.comuna_name)
    cw["region_name"] = cw.cut_region.map(REGION_NAMES).fillna(cw.region_short)
    return cw


# Proyección cónica de igual área para Chile (idéntica a 08c_figures_triangulation.load_regions_equal_area):
# las distancias entre centroides y las áreas se calculan en esta proyección, nunca en Web Mercator.
ALBERS = "+proj=aea +lat_1=-20 +lat_2=-52 +lat_0=-36 +lon_0=-71 +datum=WGS84 +units=m +no_defs"
CONTINENTAL_BOX = (-76.5, -56.6, -66.0, -17.3)
BANDS = [[15, 1, 2, 3, 4], [5, 13, 6, 7, 16, 8, 9, 14, 10], [11, 12]]


def _equal_area(shp, key: str, simplify: float):
    """Recorta a la caja continental, proyecta a la cónica de igual área y simplifica lo pedido."""
    from shapely.geometry import box
    shp = shp.to_crs(4326)
    try:
        shp["geometry"] = shp.geometry.make_valid()
    except AttributeError:
        shp["geometry"] = shp.geometry.buffer(0)
    shp["geometry"] = shp.geometry.intersection(box(*CONTINENTAL_BOX))
    shp = shp[~shp.geometry.is_empty].copy()
    shp = shp.to_crs(ALBERS)
    if simplify:
        shp["geometry"] = shp.geometry.simplify(simplify)
    shp[key] = shp[key].astype(int)
    return shp


def load_geography(cw: pd.DataFrame) -> dict:
    """Cartografía comunal y regional en proyección de igual área y las cuatro definiciones de pesos espaciales."""
    import libpysal

    raw = _equal_area(load_comunas(simplify=0.0), "cut_comuna", 0.0)      # topología intacta
    plot = raw.copy()                                                      # geometría ligera solo para dibujar
    plot["geometry"] = plot.geometry.simplify(500.0)
    regions_raw = _equal_area(load_regions(simplify=0.0), "cut_region", 0.0)
    regions = regions_raw.copy()
    regions["geometry"] = regions.geometry.simplify(800.0)
    region_of_comuna = dict(zip(cw.cut_comuna, cw.cut_region))
    for frame in (raw, plot):
        frame["cut_region"] = frame.cut_comuna.map(region_of_comuna)

    non_cont = sorted(CFG.NON_CONTINENTAL)
    contiguity = raw[~raw.cut_comuna.isin(non_cont)].sort_values("cut_comuna").reset_index(drop=True)
    order = contiguity.cut_comuna.tolist()

    wq = libpysal.weights.Queen.from_dataframe(contiguity, use_index=False)
    islands_idx = list(wq.islands)
    islands = [int(contiguity.cut_comuna.iloc[i]) for i in islands_idx]
    wk1 = libpysal.weights.KNN.from_dataframe(contiguity, k=1, use_index=False)
    queen = libpysal.weights.attach_islands(wq, wk1) if islands_idx else wq
    knn4 = libpysal.weights.KNN.from_dataframe(contiguity, k=4, use_index=False)
    knn8 = libpysal.weights.KNN.from_dataframe(contiguity, k=8, use_index=False)
    centroids = contiguity.copy()
    centroids["geometry"] = contiguity.geometry.centroid
    threshold = float(libpysal.weights.min_threshold_distance(np.c_[centroids.geometry.x, centroids.geometry.y]))
    idw = libpysal.weights.DistanceBand.from_dataframe(centroids, threshold=threshold, binary=False, alpha=-1.0,
                                                       use_index=False)
    weights = {"queen": queen, "knn4": knn4, "knn8": knn8, "idw": idw}
    for w in weights.values():
        w.transform = "r"

    region_shapes = regions_raw.sort_values("cut_region").reset_index(drop=True)
    wregion = libpysal.weights.Queen.from_dataframe(region_shapes, use_index=False)
    wregion.transform = "r"
    region_order = region_shapes.cut_region.astype(int).tolist()

    CTL.add("cartography_comunas_vs_crosswalk", "comunas.shp",
            len(cw) - len([c for c in cw.cut_comuna if c not in set(raw.cut_comuna)]), int(raw.cut_comuna.nunique()),
            "comunas del crosswalk representadas en la cartografía tras recortar a la caja continental "
            f"{CONTINENTAL_BOX}; las ausentes ({sorted(set(cw.cut_comuna) - set(raw.cut_comuna))}) se conservan en "
            "las tablas y se excluyen de los mapas y de la contigüidad")
    CTL.info("contiguity_units", "queen", len(order),
             f"comunas en la matriz de contigüidad tras excluir las no continentales {non_cont} "
             f"(se conservan en las tablas)")
    CTL.info("contiguity_islands_attached", "queen", json.dumps(islands),
             "comunas sin vecino reina (topología de archipiélago); se les adjunta su vecino más próximo (KNN-1) "
             "siguiendo libpysal.weights.attach_islands, y el resultado se documenta")
    CTL.info("contiguity_components", "queen", int(getattr(queen, "n_components", -1)),
             "componentes conexas del grafo reina tras adjuntar islas")
    CTL.info("idw_threshold_km", "idw", round(threshold / 1000, 1),
             "umbral mínimo que garantiza al menos un vecino a cada comuna; pesos = 1/distancia entre centroides")
    for name, w in weights.items():
        CTL.info("weights_mean_neighbours", name, round(float(np.mean(list(w.cardinalities.values()))), 2),
                 "número medio de vecinos, matriz estandarizada por filas")
    return dict(raw=raw, plot=plot, contiguity=contiguity, order=order, weights=weights,
                regions=regions, region_shapes=region_shapes, wregion=wregion, region_order=region_order,
                non_continental=non_cont, islands=islands, idw_threshold=threshold, crs=ALBERS,
                missing_from_map=sorted(set(cw.cut_comuna) - set(raw.cut_comuna)))


# ---------------------------------------------------------------------------
# Fuentes comunales
# ---------------------------------------------------------------------------
def comuna_counts_grd(variant: str) -> pd.DataFrame:
    """Episodios, personas dentro del año y F84 principal por comuna de RESIDENCIA (panel anual observado)."""
    terr = pd.read_csv(TIDY / "grd_territory.csv")
    sel = terr[(terr.level == "comuna") & (terr.panel == "observed") & (terr.match_method != "unmatched") &
               (terr.variant == variant)].copy()
    sel["cut_comuna"] = sel.cut_comuna.astype(int)
    out = []
    any_pos = sel[sel.position == "any"].groupby(["year", "cut_comuna"]).agg(
        count=("n_episodes", "sum"), persons=("n_persons_within_year", "sum")).reset_index()
    out.append(any_pos.assign(indicator="grd_episodes")[["year", "cut_comuna", "indicator", "count"]])
    out.append(any_pos.rename(columns={"persons": "count2"}).assign(indicator="grd_persons")
               .assign(count=lambda d: d.count2)[["year", "cut_comuna", "indicator", "count"]])
    principal = sel[sel.position == "principal"].groupby(["year", "cut_comuna"]).n_episodes.sum().reset_index()
    out.append(principal.rename(columns={"n_episodes": "count"}).assign(indicator="grd_principal")
               [["year", "cut_comuna", "indicator", "count"]])
    return pd.concat(out, ignore_index=True)


def comuna_counts_rem(variant: str, cw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """A05 (ingresos, era 2021–2025), P2 diciembre y P6 (APS y especialidad) de diciembre, era 2021–2025,
    por comuna del ESTABLECIMIENTO que reporta. Devuelve también el número de establecimientos reportantes."""
    rt = pd.read_csv(TIDY / "rem_pathway_tidy.csv", dtype=str, low_memory=False)
    rt["value"] = pd.to_numeric(rt.total_known, errors="coerce")
    rt["year"] = rt.year.astype(int)
    rt["month"] = pd.to_numeric(rt.month, errors="coerce")
    rt["code8"] = np.where(rt.series.eq("A"), rt.code.str.zfill(8), rt.code)
    deis2cut = dict(zip(cw.deis_code, cw.cut_comuna))
    rt["cut_comuna"] = rt.id_comuna_5d.astype(str).str.zfill(5).map(deis2cut)
    CTL.add("rem_comuna_link", "rem_pathway_tidy", 0, int(rt.cut_comuna.isna().sum()),
            "filas REM cuyo IdComuna de establecimiento (5 dígitos) no enlaza con comuna_crosswalk.csv")
    rt = rt.dropna(subset=["cut_comuna"]).copy()
    rt["cut_comuna"] = rt.cut_comuna.astype(int)

    spec = {
        "a05_entries": (set(CFG.VARIANTS[variant]["a05_entry"]), None, YEARS_A05),
        "p2_stock": ({CFG.P2_TEA}, 12, YEARS_P2),
        "p6_primary": (set(CFG.VARIANTS[variant]["p6_primary"]), 12, YEARS_P6),
        "p6_specialty": (set(CFG.VARIANTS[variant]["p6_specialty"]), 12, YEARS_P6),
    }
    counts, establishments = [], []
    for name, (codes, month, years) in spec.items():
        sub = rt[rt.code8.isin(codes) & rt.year.isin(years)]
        if month is not None:
            sub = sub[sub.month == month]
        agg = sub.groupby(["year", "cut_comuna"]).agg(count=("value", "sum")).reset_index()
        agg["indicator"] = name
        counts.append(agg[["year", "cut_comuna", "indicator", "count"]])
        est = (sub[sub.value.notna()].groupby(["year", "cut_comuna"]).IdEstablecimiento.nunique()
               .reset_index().rename(columns={"IdEstablecimiento": "n_establishments"}))
        est["indicator"] = name
        establishments.append(est)
    return pd.concat(counts, ignore_index=True), pd.concat(establishments, ignore_index=True)


def establishment_to_comuna(cw: pd.DataFrame) -> pd.Series:
    """Código DEIS del establecimiento → CUT de la comuna (catálogo oficial de establecimientos vigentes)."""
    path = CFG.PATHS["establecimientos"] / "establecimientos_salud_vigentes.csv"
    est = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8", encoding_errors="replace")
    est["code"] = pd.to_numeric(est.EstablecimientoCodigo, errors="coerce")
    deis2cut = dict(zip(cw.deis_code, cw.cut_comuna))
    est["cut"] = est.ComunaCodigo.astype(str).str.zfill(5).map(deis2cut)
    est = est.dropna(subset=["code", "cut"]).drop_duplicates("code")
    return pd.Series(est.cut.astype(int).values, index=est.code.astype(int).values)


def comuna_counts_coverage(cw: pd.DataFrame) -> pd.DataFrame:
    """Inscritos APS, beneficiarios FONASA y egresos REM-20 por comuna (capas de cobertura y capacidad)."""
    rows = []
    aps = pd.read_csv(TIDY / "aps_enrolment_comuna_year.csv")
    a = aps[(aps.match_method != "unmatched") & aps.cut_comuna.notna()]
    agg = a.groupby(["year", "cut_comuna"]).enrolled.sum().reset_index().rename(columns={"enrolled": "count"})
    agg["indicator"] = "aps_enrolled"
    rows.append(agg)
    fon = pd.read_csv(TIDY / "fonasa_beneficiaries_comuna_year.csv")
    f = fon[(fon.match_method != "unmatched") & fon.cut_comuna.notna() & fon.year.isin(YEARS_COV)]
    agg = f.groupby(["year", "cut_comuna"]).beneficiaries.sum().reset_index().rename(columns={"beneficiaries": "count"})
    agg["indicator"] = "fonasa_beneficiaries"
    rows.append(agg)
    emap = establishment_to_comuna(cw)
    r20 = pd.read_csv(TIDY / "rem20_establishment_year.csv")
    r20["cut_comuna"] = r20.codigo_establecimiento.map(emap)
    CTL.add("rem20_establishment_link", "establecimientos_salud_vigentes.csv", 0, int(r20.cut_comuna.isna().sum()),
            "establecimientos REM-20 sin comuna en el catálogo DEIS de establecimientos vigentes")
    agg = (r20.dropna(subset=["cut_comuna"]).groupby(["year", "cut_comuna"]).discharges.sum().reset_index()
           .rename(columns={"discharges": "count"}))
    agg["indicator"] = "rem20_discharges"
    rows.append(agg)
    out = pd.concat(rows, ignore_index=True)
    out["cut_comuna"] = out.cut_comuna.astype(int)
    return out[["year", "cut_comuna", "indicator", "count"]]


def load_population(base: str = "base2017") -> tuple[pd.DataFrame, pd.DataFrame]:
    """Población comunal por año, edad y sexo (base 2017) o del Censo 2024 (sensibilidad; nunca mezcladas)."""
    if base == "base2017":
        pop = pd.read_csv(TIDY / "ine_population_comuna_year_age_sex.csv")
        pop = pop[["year", "cut_comuna", "cut_region", "sex", "age_group", "population"]].copy()
    else:
        s = pd.read_csv(TIDY / "ine_population_sensitivity.csv")
        pop = s[(s.population_base == "censo2024") & (s.level == "comuna")][
            ["year", "cut_comuna", "cut_region", "sex", "age_group", "population"]].copy()
    pop["cut_comuna"] = pop.cut_comuna.astype(int)
    pop["cut_region"] = pop.cut_region.astype(int)
    total = pop.groupby(["year", "cut_comuna"]).population.sum().reset_index()
    return pop, total


def load_context(cw: pd.DataFrame, pop_total: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    """Privación SAE 2024, porcentaje urbano y participación FONASA: covariables de contexto por comuna."""
    def read_sae(path: Path, key: str) -> pd.DataFrame:
        d = pd.read_excel(path, sheet_name=0, skiprows=2)
        d = d.iloc[:, :10]
        d.columns = ["cut_comuna", "region_raw", "comuna_raw", "population_projection", "n_poor", "value",
                     "value_lo", "value_hi", "in_casen_sample", "sae_estimator"]
        d = d[pd.to_numeric(d.cut_comuna, errors="coerce").notna()].copy()
        d["cut_comuna"] = d.cut_comuna.astype(float).astype(int)
        for col in ("value", "value_lo", "value_hi"):
            d[col] = pd.to_numeric(d[col], errors="coerce") * 100.0
        d["indicator"] = key
        return d[["cut_comuna", "indicator", "value", "value_lo", "value_hi", "in_casen_sample", "sae_estimator"]]

    sae_m = read_sae(CFG.PATHS["sae"] / "SAE_multidimensional_2024.xlsx", "sae_multidimensional")
    sae_i = read_sae(CFG.PATHS["sae"] / "SAE_ingresos_2024.xlsx", "sae_income")
    CTL.info("sae_comunas", "SAE_2024", int(sae_m.cut_comuna.nunique()),
             "comunas con estimación SAE 2024 (la Antártica no tiene estimación); el archivo trae el punto y su intervalo")

    up = pd.read_csv(CFG.PATHS["ine"] / "proyecciones_comuna_area_urbana_rural_2002_2035_base_2017.csv",
                     sep=";", encoding="latin-1")
    up = up.rename(columns={"Comuna": "cut_comuna", "Area (1=Urbano 2=Rural)": "area"})
    wide = up.groupby(["cut_comuna", "area"])["Poblacion 2024"].sum().unstack(fill_value=0)
    urban = wide.get(1, pd.Series(0, index=wide.index)).astype(float)
    rural = wide.get(2, pd.Series(0, index=wide.index)).astype(float)
    urb = pd.DataFrame({"cut_comuna": wide.index.astype(int),
                        "value": np.where(urban + rural > 0, 100.0 * urban / (urban + rural), np.nan)})
    urb["indicator"] = "urban_share"
    urb["value_lo"] = np.nan
    urb["value_hi"] = np.nan

    ref_year = 2024
    fon = coverage[(coverage.indicator == "fonasa_beneficiaries") & (coverage.year == ref_year)]
    ine = pop_total[pop_total.year == ref_year]
    share = fon.merge(ine, on="cut_comuna", how="inner")
    share["value"] = 100.0 * share["count"] / share.population
    share["indicator"] = "fonasa_share"
    share["value_lo"] = np.nan
    share["value_hi"] = np.nan

    cols = ["cut_comuna", "indicator", "value", "value_lo", "value_hi"]
    out = pd.concat([sae_m[cols + ["in_casen_sample", "sae_estimator"]],
                     sae_i[cols + ["in_casen_sample", "sae_estimator"]],
                     urb[cols], share[cols]], ignore_index=True)
    out["reference_year"] = ref_year
    return out


# ---------------------------------------------------------------------------
# Tasas nacionales de referencia y estandarización indirecta
# ---------------------------------------------------------------------------
SEX_MAP = {"Hombres": "HOMBRE", "Mujeres": "MUJER", "HOMBRE": "HOMBRE", "MUJER": "MUJER"}


def national_age_sex_schedule(indicator: str, variant: str) -> pd.DataFrame | None:
    """Recuento nacional por año, sexo y grupo etario de la MISMA fuente (referencia de la estandarización)."""
    if indicator in ("grd_episodes", "grd_principal"):
        g = pd.read_csv(TIDY / "grd_age_sex_year.csv")
        position = "any" if indicator == "grd_episodes" else "principal"
        sel = g[(g.variant == variant) & (g.panel == "observed") & (g.position == position) &
                (g.activity == "all") & (g.sex.isin(SEX_MAP)) & (g.age_group != "unknown")]
        out = sel.groupby(["year", "sex", "age_group"]).n_f84.sum().reset_index().rename(columns={"n_f84": "count"})
        out["sex"] = out.sex.map(SEX_MAP)
        return out
    if indicator == "a05_entries":
        a = pd.read_csv(TIDY / "rem_a05_age_sex_annual.csv")
        sel = a[(a.variant == variant) & (a.flow == "entry") & (a.category == "pdd_family") &
                (a.age_group != "total") & a.year.isin(YEARS_A05)]
        out = sel.groupby(["year", "sex", "age_group"])["count"].sum().reset_index()
        out["sex"] = out.sex.map(SEX_MAP)
        return out
    return None


def indirect_standardise(counts: pd.DataFrame, indicator: str, variant: str, years: list[int],
                         pop_agesex: pd.DataFrame, pop_total: pd.DataFrame, base: str = "base2017") -> pd.DataFrame:
    """Estandarización indirecta interna por comuna acumulando los años del periodo.

    Cuando la fuente publica el desglose por edad y sexo, las tasas de referencia son las nacionales por
    edad, sexo y año de esa misma fuente; en caso contrario el esperado es proporcional a la población
    (estandarización solo por tamaño, declarada como tal). El esperado se reescala para que la suma
    nacional de esperados iguale la de observados (razón nacional = 1 por construcción); el factor de
    reescalado se informa. Límites exactos de Poisson para la razón cruda y suavizado empírico de Bayes de
    Marshall (media y varianza previas incluidas)."""
    sub = counts[(counts.indicator == indicator) & counts.year.isin(years)]
    observed = sub.groupby("cut_comuna")["count"].sum()
    py = pop_total[pop_total.year.isin(years)].groupby("cut_comuna").population.sum()
    universe = sorted(set(py.index))
    observed = observed.reindex(universe).fillna(0.0)
    py = py.reindex(universe)
    if "reported" in sub.columns:
        reported = sub.groupby("cut_comuna").reported.sum().reindex(universe).fillna(0).astype(int)
    else:
        reported = pd.Series(len(years), index=universe)

    schedule = national_age_sex_schedule(indicator, variant)
    if schedule is not None and not schedule.empty:
        nat_pop = pop_agesex[pop_agesex.year.isin(years)].groupby(["year", "sex", "age_group"]).population.sum()
        sch = schedule[schedule.year.isin(years)].set_index(["year", "sex", "age_group"])["count"]
        rate = (sch / nat_pop.reindex(sch.index)).rename("ref_rate").reset_index()
        cp = pop_agesex[pop_agesex.year.isin(years)].merge(rate, on=["year", "sex", "age_group"], how="left")
        cp["expected"] = cp.population * cp.ref_rate.fillna(0.0)
        expected = cp.groupby("cut_comuna").expected.sum().reindex(universe).fillna(0.0)
        method = "age-sex indirect (national age x sex x year rates of the same source)"
    else:
        nat = sub.groupby("year")["count"].sum()
        natpop = pop_total[pop_total.year.isin(years)].groupby("year").population.sum()
        crude = (nat / natpop.reindex(nat.index)).fillna(0.0)
        cp = pop_total[pop_total.year.isin(years)].copy()
        cp["expected"] = cp.population * cp.year.map(crude).fillna(0.0)
        expected = cp.groupby("cut_comuna").expected.sum().reindex(universe).fillna(0.0)
        method = "population-size indirect (no age-sex breakdown published for this indicator)"

    raw_sum = float(expected.sum())
    factor = float(observed.sum() / raw_sum) if raw_sum > 0 else np.nan
    expected_scaled = expected * (factor if np.isfinite(factor) else 1.0)

    sr = standardized_ratio(observed.values, expected_scaled.values)
    eb = empirical_bayes_ratio(observed.values, expected_scaled.values)
    out = pd.DataFrame({
        "cut_comuna": universe,
        "indicator": indicator,
        "variant": variant,
        "population_base": base,
        "observed": observed.values,
        "expected": expected_scaled.values,
        "expected_unscaled": expected.values,
        "expected_scaling_factor": factor,
        "person_years": py.values,
        "rate_per_100k": np.where(py.values > 0, PER * observed.values / py.values, np.nan),
        "standardisation": method,
        "years_in_period": len(years),
        "years_reported": reported.values,
    })
    lo, hi = poisson_limits(observed.values, ALPHA)
    out["rate_lo"] = np.where(py.values > 0, PER * lo / py.values, np.nan)
    out["rate_hi"] = np.where(py.values > 0, PER * hi / py.values, np.nan)
    out = pd.concat([out, sr, eb], axis=1)
    out["suppressed"] = out.observed < SUPPRESSION_THRESHOLD
    out["never_reported"] = out.years_reported == 0
    return out


# ---------------------------------------------------------------------------
# Estadística espacial
# ---------------------------------------------------------------------------
def _aligned(values: pd.Series, order: list[int]) -> np.ndarray:
    return values.reindex(order).astype(float).values


def moran_global(vals: np.ndarray, w, permutations: int = PERMUTATIONS) -> dict:
    """I de Moran con inferencia analítica (normalidad) y por permutaciones con semilla fija."""
    import esda
    finite = np.isfinite(vals)
    if finite.sum() < 10 or np.nanstd(vals) == 0:
        return dict(morans_i=np.nan, expected_i=np.nan, z_norm=np.nan, p_norm=np.nan, p_sim=np.nan,
                    sim_mean=np.nan, sim_sd=np.nan, n=int(finite.sum()), permutations=permutations, seed=SEED)
    x = np.where(finite, vals, np.nanmean(vals[finite]))
    np.random.seed(SEED)
    m = esda.Moran(x, w, permutations=permutations)
    return dict(morans_i=float(m.I), expected_i=float(m.EI), z_norm=float(m.z_norm), p_norm=float(m.p_norm),
                p_sim=float(m.p_sim), sim_mean=float(np.mean(m.sim)), sim_sd=float(np.std(m.sim)),
                n=int(finite.sum()), permutations=permutations, seed=SEED,
                n_imputed_to_mean=int((~finite).sum()))


def bh_threshold(pvals: np.ndarray, q: float = FDR_Q) -> tuple[np.ndarray, float]:
    """Benjamini–Hochberg: devuelve el vector de rechazos y el p crítico (0 si no hay ninguno)."""
    from statsmodels.stats.multitest import multipletests
    ok = np.isfinite(pvals)
    reject = np.zeros(len(pvals), dtype=bool)
    if ok.sum() == 0:
        return reject, 0.0
    rej, _, _, _ = multipletests(pvals[ok], alpha=q, method="fdr_bh")
    reject[np.where(ok)[0]] = rej
    crit = float(np.max(pvals[ok][rej])) if rej.any() else 0.0
    return reject, crit


LISA_LABEL = {1: "HH", 2: "LH", 3: "LL", 4: "HL"}


def lisa_local(vals: np.ndarray, w, ids: list[int], permutations: int = PERMUTATIONS) -> pd.DataFrame:
    """LISA con cuadrante, p de permutación y umbral de Benjamini–Hochberg."""
    import esda
    finite = np.isfinite(vals)
    x = np.where(finite, vals, np.nanmean(vals[finite])) if finite.any() else vals
    lm = esda.Moran_Local(x, w, permutations=permutations, seed=SEED)
    reject, crit = bh_threshold(np.asarray(lm.p_sim, dtype=float))
    z = (x - np.nanmean(x)) / np.nanstd(x)
    lag = np.asarray(w.sparse @ z).ravel()
    return pd.DataFrame({
        "cut_comuna": ids, "value": vals, "z_value": z, "spatial_lag_z": lag,
        "lisa_i": np.asarray(lm.Is, dtype=float), "lisa_z": np.asarray(lm.z_sim, dtype=float),
        "lisa_p_sim": np.asarray(lm.p_sim, dtype=float),
        "lisa_p_z_sim": np.asarray(getattr(lm, "p_z_sim", np.full(len(ids), np.nan)), dtype=float),
        "lisa_quadrant": [LISA_LABEL.get(int(q), "n/a") for q in lm.q],
        "lisa_bh_reject": reject, "lisa_bh_critical_p": crit,
        "lisa_class": np.where(reject, [LISA_LABEL.get(int(q), "n/a") for q in lm.q], "ns"),
    })


def gistar_local(vals: np.ndarray, w, ids: list[int], permutations: int = PERMUTATIONS) -> pd.DataFrame:
    """Gi* de Getis–Ord (incluye la propia unidad) con p de permutación y umbral de Benjamini–Hochberg."""
    import esda
    finite = np.isfinite(vals)
    x = np.where(finite, vals, np.nanmean(vals[finite])) if finite.any() else vals
    x = x - np.nanmin(x) + 1e-9 if np.nanmin(x) < 0 else x      # Gi* requiere valores no negativos
    g = esda.G_Local(x, w, permutations=permutations, star=True, seed=SEED)
    p = np.asarray(g.p_sim, dtype=float)
    reject, crit = bh_threshold(p)
    z = np.asarray(g.Zs, dtype=float)
    cls = np.where(reject & (z > 0), "hot", np.where(reject & (z < 0), "cold", "ns"))
    return pd.DataFrame({"cut_comuna": ids, "gi_z": z, "gi_p_sim": p,
                         "gi_p_z_sim": np.asarray(getattr(g, "p_z_sim", np.full(len(ids), np.nan)), dtype=float),
                         "gi_bh_reject": reject, "gi_bh_critical_p": crit, "gi_class": cls})


def moran_bivariate(x: np.ndarray, y: np.ndarray, w, permutations: int = PERMUTATIONS) -> dict:
    """I de Moran bivariada (x en la unidad, y en el rezago espacial) con inferencia por permutación."""
    import esda
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 10 or np.nanstd(x[ok]) == 0 or np.nanstd(y[ok]) == 0:
        return dict(bv_i=np.nan, bv_p_sim=np.nan, bv_z=np.nan, n=int(ok.sum()))
    xf = np.where(ok, x, np.nanmean(x[ok]))
    yf = np.where(ok, y, np.nanmean(y[ok]))
    np.random.seed(SEED)
    m = esda.Moran_BV(xf, yf, w, permutations=permutations)
    return dict(bv_i=float(m.I), bv_p_sim=float(m.p_sim), bv_z=float(m.z_sim), n=int(ok.sum()))


# ---------------------------------------------------------------------------
# Correlación, desigualdad y estabilidad
# ---------------------------------------------------------------------------
def spearman_ci(x: np.ndarray, y: np.ndarray, alpha: float = ALPHA) -> dict:
    """Rho de Spearman con intervalo de Fisher-z (error estándar de Bonett–Wright, sqrt(1.06/(n-3)))."""
    ok = np.isfinite(x) & np.isfinite(y)
    n = int(ok.sum())
    if n < 5 or np.nanstd(x[ok]) == 0 or np.nanstd(y[ok]) == 0:
        return dict(rho=np.nan, rho_lo=np.nan, rho_hi=np.nan, p_value=np.nan, n=n)
    rho, p = stats.spearmanr(x[ok], y[ok])
    if n > 3 and abs(rho) < 1:
        z = np.arctanh(rho)
        se = np.sqrt(1.06 / (n - 3))
        crit = stats.norm.ppf(1 - alpha / 2)
        lo, hi = np.tanh(z - crit * se), np.tanh(z + crit * se)
    else:
        lo = hi = np.nan
    return dict(rho=float(rho), rho_lo=float(lo), rho_hi=float(hi), p_value=float(p), n=n)


def lorenz_gini(counts: np.ndarray, population: np.ndarray) -> dict:
    """Curva de Lorenz de los eventos frente a la población (comunas ordenadas por tasa) y su índice de Gini."""
    ok = np.isfinite(counts) & np.isfinite(population) & (population > 0)
    c, p = counts[ok], population[ok]
    if c.sum() <= 0:
        return dict(gini=np.nan, x=np.array([0.0, 1.0]), y=np.array([0.0, 1.0]), n=int(ok.sum()),
                    top_decile_share=np.nan)
    rate = c / p
    order = np.argsort(rate, kind="mergesort")
    cp = np.cumsum(p[order]) / p.sum()
    cc = np.cumsum(c[order]) / c.sum()
    x = np.concatenate([[0.0], cp])
    y = np.concatenate([[0.0], cc])
    gini = 1.0 - np.sum((x[1:] - x[:-1]) * (y[1:] + y[:-1]))
    top = float(1.0 - np.interp(0.9, x, y))
    return dict(gini=float(gini), x=x, y=y, n=int(ok.sum()), top_decile_share=top)


def theil_decomposition(counts: np.ndarray, population: np.ndarray, region: np.ndarray) -> dict:
    """Índice de Theil de la distribución de eventos respecto de la población, descompuesto entre y dentro de regiones."""
    ok = np.isfinite(counts) & np.isfinite(population) & (population > 0) & (counts > 0)
    c, p, r = counts[ok], population[ok], region[ok]
    if c.sum() <= 0:
        return dict(theil=np.nan, between=np.nan, within=np.nan, between_share=np.nan, n=int(ok.sum()))
    s = c / c.sum()
    q = p / p.sum()
    theil = float(np.sum(s * np.log(s / q)))
    between = within = 0.0
    for reg in np.unique(r):
        m = r == reg
        S, Q = s[m].sum(), q[m].sum()
        if S <= 0 or Q <= 0:
            continue
        between += S * np.log(S / Q)
        si, qi = s[m] / S, q[m] / Q
        within += S * float(np.sum(si * np.log(si / qi)))
    return dict(theil=theil, between=float(between), within=float(within),
                between_share=float(between / theil) if theil else np.nan, n=int(ok.sum()))


def decile_ratio(counts: np.ndarray, population: np.ndarray) -> dict:
    """Razón entre la tasa del decil poblacional superior y la del inferior (comunas ordenadas por tasa)."""
    ok = np.isfinite(counts) & np.isfinite(population) & (population > 0)
    c, p = counts[ok], population[ok]
    if c.sum() <= 0:
        return dict(top_decile_rate=np.nan, bottom_decile_rate=np.nan, decile_ratio=np.nan)
    rate = c / p
    order = np.argsort(rate, kind="mergesort")
    c, p = c[order], p[order]
    cum = np.cumsum(p) / p.sum()
    bottom = cum <= 0.10
    top = cum > 0.90
    if bottom.sum() == 0:
        bottom = np.zeros(len(c), dtype=bool)
        bottom[0] = True
    if top.sum() == 0:
        top = np.zeros(len(c), dtype=bool)
        top[-1] = True
    br = c[bottom].sum() / p[bottom].sum() * PER
    tr = c[top].sum() / p[top].sum() * PER
    # Variante restringida a comunas con al menos un evento: el decil inferior de todo el país puede ser
    # íntegramente de comunas con cero eventos, y entonces la razón no es estimable.
    nz = c > 0
    ratio_nz = np.nan
    if nz.sum() >= 10:
        cn, pn = c[nz], p[nz]
        cumn = np.cumsum(pn) / pn.sum()
        bn, tn = cumn <= 0.10, cumn > 0.90
        if bn.sum() and tn.sum():
            brn = cn[bn].sum() / pn[bn].sum()
            trn = cn[tn].sum() / pn[tn].sum()
            ratio_nz = float(trn / brn) if brn > 0 else np.nan
    return dict(top_decile_rate=float(tr), bottom_decile_rate=float(br),
                decile_ratio=float(tr / br) if br > 0 else np.nan,
                decile_ratio_comunas_with_events=ratio_nz,
                n_comunas_with_events=int(nz.sum()))


# ---------------------------------------------------------------------------
# Análisis por variante
# ---------------------------------------------------------------------------
def analyse_variant(variant: str, geo: dict, base_data: dict, permutations: int) -> dict:
    """Ejecuta los ocho bloques del análisis espacial para una variante de definición."""
    import libpysal

    cw = base_data["crosswalk"]
    pop_agesex, pop_total = base_data["pop_agesex"], base_data["pop_total"]
    context = base_data["context"]
    order = geo["order"]
    weights = geo["weights"]
    region_of = dict(zip(cw.cut_comuna, cw.cut_region))

    t_v = time.time()
    grd = comuna_counts_grd(variant)
    rem, rem_est = comuna_counts_rem(variant, cw)
    observed_rows = pd.concat([grd, rem, base_data["coverage"]], ignore_index=True)
    observed_rows["reported"] = True

    # Panel comunal completo: cada indicador x año x comuna del universo poblacional. La ausencia de fila
    # en la fuente NO es lo mismo que un cero informado y se marca como tal:
    #   * GRD (residencia): la fuente cubre todo el país, la ausencia es un CERO ESTRUCTURAL (ningún residente
    #     de esa comuna tuvo un episodio con F84 documentado ese año);
    #   * REM, REM-20 y APS (lugar de atención): la ausencia significa que NINGÚN ESTABLECIMIENTO de esa comuna
    #     reportó el indicador; el valor se fija en cero para poder mapear y correlacionar, pero la columna
    #     `count_state` conserva la distinción y las notas la declaran.
    universe = sorted(pop_total.cut_comuna.unique())
    frames = []
    for name, spec in IND.items():
        grid = pd.MultiIndex.from_product([spec["years"], universe], names=["year", "cut_comuna"]).to_frame(index=False)
        grid["indicator"] = name
        frames.append(grid)
    counts = pd.concat(frames, ignore_index=True).merge(
        observed_rows, on=["year", "cut_comuna", "indicator"], how="left")
    counts["reported"] = counts.reported.fillna(False).astype(bool)
    counts["count"] = counts["count"].fillna(0.0)
    counts["variant"] = variant
    counts["cut_region"] = counts.cut_comuna.map(region_of)
    counts = counts.merge(pop_total, on=["year", "cut_comuna"], how="left")
    counts["rate_per_100k"] = np.where(counts.population > 0, PER * counts["count"] / counts.population, np.nan)
    counts["geography_numerator"] = counts.indicator.map({k: v["geo"] for k, v in IND.items()})
    counts["denominator_compatible"] = counts.indicator.map({k: v["compatible"] for k, v in IND.items()})
    counts["kind"] = counts.indicator.map({k: v["kind"] for k, v in IND.items()})
    counts["source"] = counts.indicator.map({k: v["source"] for k, v in IND.items()})
    counts["count_state"] = np.where(
        counts.reported, np.where(counts["count"] > 0, "reported_value", "reported_zero"),
        np.where(counts.geography_numerator == "residence", "structural_zero", "no_reporting_establishment"))
    counts["suppressed"] = counts["count"] < SUPPRESSION_THRESHOLD
    counts["variant_note"] = CFG.VARIANTS[variant]["label"]["en"]
    for name in IND:
        sel = counts[counts.indicator == name]
        CTL.info("comunas_with_report", f"{variant}|{name}",
                 int(sel[sel.reported].cut_comuna.nunique()),
                 f"comunas con al menos un año informado de {len(universe)} del universo poblacional; "
                 f"el resto se fija en cero y se marca en count_state")
    log(f"  {variant}: panel comunal {len(counts):,} filas ({time.time() - t_v:.1f} s)")

    # --- (2) estandarización indirecta por indicador y periodo -------------------------------------
    std_rows = []
    for ind, periods in PERIODS.items():
        for pname, years in periods.items():
            df = indirect_standardise(counts, ind, variant, years, pop_agesex, pop_total)
            df["period"] = pname
            df["years"] = f"{min(years)}-{max(years)}"
            df["cut_region"] = df.cut_comuna.map(region_of)
            std_rows.append(df)
    standardised = pd.concat(std_rows, ignore_index=True)
    log(f"  {variant}: estandarización indirecta lista ({time.time() - t_v:.1f} s)")

    full = standardised[standardised.period == "full"]
    value_frames: dict[str, pd.Series] = {}
    for ind in COUNT_INDICATORS:
        f = full[full.indicator == ind].set_index("cut_comuna")
        value_frames[f"{ind}|rate_per_100k"] = f.rate_per_100k
        value_frames[f"{ind}|sir"] = f.sir
        value_frames[f"{ind}|sir_eb"] = f.sir_eb
    ctx = context.pivot_table(index="cut_comuna", columns="indicator", values="value", aggfunc="first")
    for ind in CONTEXT:
        if ind in ctx.columns:
            value_frames[f"{ind}|value"] = ctx[ind]

    # --- (3) I de Moran global, sensibilidad de pesos y escala regional ----------------------------
    moran_rows = []

    def add_moran(scope, ind, value_type, weight, years_label, vals, w, subset_note=""):
        res = moran_global(vals, w, permutations)
        moran_rows.append(dict(variant=variant, scope=scope, indicator=ind, value_type=value_type,
                               weights=weight, years=years_label, subset=subset_note or "all comunas", **res))

    for key, series in value_frames.items():
        ind, value_type = key.split("|")
        vals = _aligned(series, order)
        for wname, w in weights.items():
            add_moran("comuna", ind, value_type, wname, "full period", vals, w)
    log(f"  {variant}: Moran global comunal ({len(moran_rows)} filas, {time.time() - t_v:.1f} s)")

    # Moran por año (indicadores locales) — la serie anual nunca une eras de definición distintas.
    for ind in LOCAL_INDICATORS:
        for year in PERIODS[ind]["full"]:
            df = indirect_standardise(counts, ind, variant, [year], pop_agesex, pop_total)
            vals = _aligned(df.set_index("cut_comuna").sir_eb, order)
            add_moran("comuna", ind, "sir_eb", "queen", str(year), vals, weights["queen"])

    # Sensibilidad: <5 eventos, sin Región Metropolitana, denominador Censo 2024.
    contiguity = geo["contiguity"]
    contiguity_all = geo["raw"]
    subsets = {}
    small = full[(full.indicator == MAIN) & (full.observed >= SUPPRESSION_THRESHOLD)].cut_comuna.tolist()
    subsets["comunas with >=5 events"] = sorted(set(small) & set(order))
    subsets["excluding Metropolitan Region (13)"] = [c for c in order if region_of.get(c) != 13]
    with_islands = sorted(set(order) | (set(contiguity_all.cut_comuna) & set(CFG.NON_CONTINENTAL)))
    if len(with_islands) > len(order):
        subsets["including non-continental comunas present in the cartography"] = with_islands
    for label, keep in subsets.items():
        pool = contiguity_all if "non-continental" in label else contiguity
        sub = pool[pool.cut_comuna.isin(keep)].sort_values("cut_comuna").reset_index(drop=True)
        wq = libpysal.weights.Queen.from_dataframe(sub, use_index=False)
        if wq.islands:
            wq = libpysal.weights.attach_islands(wq, libpysal.weights.KNN.from_dataframe(sub, k=1, use_index=False))
        wq.transform = "r"
        sorder = sub.cut_comuna.tolist()
        for value_type in ("rate_per_100k", "sir", "sir_eb"):
            vals = _aligned(value_frames[f"{MAIN}|{value_type}"], sorder)
            add_moran("comuna", MAIN, value_type, "queen", "full period", vals, wq, subset_note=label)
    # Denominador alternativo (Censo 2024): solo el año 2024, nunca mezclado con la base 2017.
    censo_total = base_data["pop_total_censo"]
    censo_agesex = base_data["pop_agesex_censo"]
    denominator_sensitivity = []
    if censo_total is not None and len(censo_total):
        for base_name, pas, ptot in (("base2017", pop_agesex, pop_total), ("censo2024", censo_agesex, censo_total)):
            df = indirect_standardise(counts, MAIN, variant, [2024], pas, ptot, base=base_name)
            denominator_sensitivity.append(df.assign(period="2024", years="2024"))
            for value_type in ("rate_per_100k", "sir", "sir_eb"):
                vals = _aligned(df.set_index("cut_comuna")[value_type], order)
                add_moran("comuna", MAIN, value_type, "queen", "2024", vals, weights["queen"],
                          subset_note=f"denominator {base_name}")

    # Escala regional (16 regiones, contigüidad reina).
    region_rows = []
    rorder = geo["region_order"]
    for ind in COUNT_INDICATORS:
        f = full[full.indicator == ind]
        agg = f.groupby("cut_region").agg(observed=("observed", "sum"), expected=("expected", "sum"),
                                          person_years=("person_years", "sum")).reset_index()
        agg["rate_per_100k"] = np.where(agg.person_years > 0, PER * agg.observed / agg.person_years, np.nan)
        lo, hi = poisson_limits(agg.observed.values, ALPHA)
        agg["rate_lo"] = PER * lo / agg.person_years
        agg["rate_hi"] = PER * hi / agg.person_years
        agg = pd.concat([agg, standardized_ratio(agg.observed.values, agg.expected.values)], axis=1)
        agg = pd.concat([agg, empirical_bayes_ratio(agg.observed.values, agg.expected.values)], axis=1)
        agg["indicator"] = ind
        agg["variant"] = variant
        agg["region_name"] = agg.cut_region.map(REGION_NAMES)
        region_rows.append(agg)
        for value_type in ("rate_per_100k", "sir", "sir_eb"):
            vals = _aligned(agg.set_index("cut_region")[value_type], rorder)
            add_moran("region", ind, value_type, "queen (16 regions)", "full period", vals, geo["wregion"])
    for ind in CONTEXT:
        if f"{ind}|value" not in value_frames:
            continue
        w_pop = pop_total[pop_total.year == 2024].set_index("cut_comuna").population
        v = value_frames[f"{ind}|value"]
        dfc = pd.DataFrame({"value": v, "population": w_pop.reindex(v.index)})
        dfc["cut_region"] = [region_of.get(c) for c in dfc.index]
        agg = dfc.dropna(subset=["value", "population"]).groupby("cut_region").apply(
            lambda d: np.average(d.value, weights=d.population)).rename("value").reset_index()
        vals = _aligned(agg.set_index("cut_region").value, rorder)
        add_moran("region", ind, "value", "queen (16 regions)", "2024", vals, geo["wregion"])
        region_rows.append(agg.assign(indicator=ind, variant=variant,
                                      region_name=agg.cut_region.map(REGION_NAMES)))
    regions = pd.concat(region_rows, ignore_index=True)
    moran = pd.DataFrame(moran_rows)
    log(f"  {variant}: Moran global total {len(moran)} filas ({time.time() - t_v:.1f} s)")

    # --- (4) LISA y Gi* ---------------------------------------------------------------------------
    local_rows = []
    for ind in LOCAL_INDICATORS:
        vals = _aligned(value_frames[f"{ind}|sir_eb"], order)
        lisa = lisa_local(vals, weights["queen"], order, permutations)
        gi = gistar_local(vals, weights["queen"], order, permutations)
        merged = lisa.merge(gi, on="cut_comuna")
        merged["indicator"] = ind
        merged["variant"] = variant
        merged["value_type"] = "sir_eb"
        merged["weights"] = "queen"
        local_rows.append(merged)
    local = pd.concat(local_rows, ignore_index=True)
    local["cut_region"] = local.cut_comuna.map(region_of)
    local = local.merge(full[full.indicator.isin(LOCAL_INDICATORS)][
        ["cut_comuna", "indicator", "observed", "expected", "person_years", "rate_per_100k", "sir", "sir_lo",
         "sir_hi", "sir_eb", "eb_weight", "suppressed"]], on=["cut_comuna", "indicator"], how="left")
    local = local.merge(cw[["cut_comuna", "comuna_name_ine", "region_name"]], on="cut_comuna", how="left")
    log(f"  {variant}: LISA y Gi* listos ({time.time() - t_v:.1f} s)")

    # --- (5) correlación territorial entre sistemas ------------------------------------------------
    pair_keys = [f"{i}|sir_eb" for i in COUNT_INDICATORS] + [f"{i}|value" for i in CONTEXT if f"{i}|value" in value_frames]
    region_value = {}
    for ind in COUNT_INDICATORS:
        sub = regions[(regions.indicator == ind) & regions.sir_eb.notna()] if "sir_eb" in regions else pd.DataFrame()
        if len(sub):
            region_value[ind] = sub.set_index("cut_region").sir_eb
    for ind in CONTEXT:
        sub = regions[(regions.indicator == ind)]
        if len(sub) and "value" in sub:
            region_value[ind] = sub.dropna(subset=["value"]).set_index("cut_region").value

    corr_rows, bv_rows = [], []
    for a in range(len(pair_keys)):
        for b in range(a + 1, len(pair_keys)):
            ka, kb = pair_keys[a], pair_keys[b]
            ia, ib = ka.split("|")[0], kb.split("|")[0]
            xa = _aligned(value_frames[ka], order)
            xb = _aligned(value_frames[kb], order)
            res = spearman_ci(xa, xb)
            corr_rows.append(dict(variant=variant, scope="comuna", indicator_x=ia, indicator_y=ib,
                                  value_type_x=ka.split("|")[1], value_type_y=kb.split("|")[1], **res))
            if ia in region_value and ib in region_value:
                ra = _aligned(region_value[ia], rorder)
                rb = _aligned(region_value[ib], rorder)
                rres = spearman_ci(ra, rb)
                corr_rows.append(dict(variant=variant, scope="region", indicator_x=ia, indicator_y=ib,
                                      value_type_x=ka.split("|")[1], value_type_y=kb.split("|")[1], **rres))
            bv = moran_bivariate(xa, xb, weights["queen"], permutations)
            bv_rows.append(dict(variant=variant, indicator_x=ia, indicator_y=ib, weights="queen",
                                spearman_rho=res["rho"], **bv))
    correlations = pd.DataFrame(corr_rows)
    bivariate = pd.DataFrame(bv_rows)
    log(f"  {variant}: {len(correlations)} correlaciones y {len(bivariate)} Moran bivariadas ({time.time() - t_v:.1f} s)")

    # --- (6) desigualdad territorial ---------------------------------------------------------------
    ineq_rows = []
    for ind in COUNT_INDICATORS:
        years = PERIODS[ind]["full"]
        for label, ysel in [(str(y), [y]) for y in years] + [(f"{min(years)}-{max(years)}", years)]:
            sub = counts[(counts.indicator == ind) & counts.year.isin(ysel)]
            agg = sub.groupby("cut_comuna").agg(count=("count", "sum"), population=("population", "sum"),
                                                years_reported=("reported", "sum")).reset_index()
            agg["cut_region"] = agg.cut_comuna.map(region_of)
            lz = lorenz_gini(agg["count"].values, agg.population.values)
            th = theil_decomposition(agg["count"].values, agg.population.values, agg.cut_region.values)
            dr = decile_ratio(agg["count"].values, agg.population.values)
            ineq_rows.append(dict(variant=variant, indicator=ind, years=label, n_comunas=lz["n"],
                                  total_count=float(agg["count"].sum()), gini=lz["gini"],
                                  top_decile_event_share=lz["top_decile_share"], theil=th["theil"],
                                  theil_between=th["between"], theil_within=th["within"],
                                  theil_between_share=th["between_share"], **dr,
                                  n_comunas_zero=int((agg["count"] <= 0).sum()),
                                  n_comunas_never_reported=int((agg.years_reported <= 0).sum()),
                                  geography_numerator=IND[ind]["geo"],
                                  denominator_compatible=IND[ind]["compatible"]))
    inequality = pd.DataFrame(ineq_rows)

    # --- (7) estabilidad ---------------------------------------------------------------------------
    stab_rows = []
    for ind in COUNT_INDICATORS:
        years = PERIODS[ind]["full"]
        wide = counts[counts.indicator == ind].pivot_table(index="cut_comuna", columns="year",
                                                           values="rate_per_100k", aggfunc="first")
        for y1, y2 in zip(years[:-1], years[1:]):
            if y1 in wide.columns and y2 in wide.columns:
                res = spearman_ci(wide[y1].reindex(order).values, wide[y2].reindex(order).values)
                stab_rows.append(dict(variant=variant, indicator=ind, comparison=f"{y1} vs {y2}",
                                      basis="rate per 100,000", **res))
        early = standardised[(standardised.indicator == ind) & (standardised.period == "early")].set_index("cut_comuna")
        late = standardised[(standardised.indicator == ind) & (standardised.period == "late")].set_index("cut_comuna")
        if len(early) and len(late):
            res = spearman_ci(_aligned(early.sir_eb, order), _aligned(late.sir_eb, order))
            stab_rows.append(dict(variant=variant, indicator=ind,
                                  comparison=f"{early.years.iloc[0]} vs {late.years.iloc[0]}",
                                  basis="empirical-Bayes smoothed standardised ratio", **res))
    stability = pd.DataFrame(stab_rows)
    log(f"  {variant}: desigualdad y estabilidad listas ({time.time() - t_v:.1f} s)")

    # Moran bivariada local de los dos pares más fuertes entre sistemas distintos (E45).
    import esda
    cross = _cross_system(bivariate)
    top_pairs = cross.reindex(cross.bv_i.abs().sort_values(ascending=False).index).head(2)
    bv_local = []
    for row in top_pairs.itertuples():
        xa = _aligned(value_frames[f"{row.indicator_x}|" + ("value" if row.indicator_x in CONTEXT else "sir_eb")], order)
        xb = _aligned(value_frames[f"{row.indicator_y}|" + ("value" if row.indicator_y in CONTEXT else "sir_eb")], order)
        ok = np.isfinite(xa) & np.isfinite(xb)
        xa = np.where(ok, xa, np.nanmean(xa[ok]))
        xb = np.where(ok, xb, np.nanmean(xb[ok]))
        lb = esda.Moran_Local_BV(xa, xb, weights["queen"], permutations=permutations, seed=SEED)
        rej, crit = bh_threshold(np.asarray(lb.p_sim, dtype=float))
        za = (xa - xa.mean()) / xa.std()
        zb = (xb - xb.mean()) / xb.std()
        bv_local.append(pd.DataFrame({
            "variant": variant, "indicator_x": row.indicator_x, "indicator_y": row.indicator_y,
            "cut_comuna": order, "x_z": za, "lag_y_z": np.asarray(weights["queen"].sparse @ zb).ravel(),
            "bv_local_i": np.asarray(lb.Is, dtype=float), "bv_local_p_sim": np.asarray(lb.p_sim, dtype=float),
            "bv_local_quadrant": [LISA_LABEL.get(int(q), "n/a") for q in lb.q],
            "bv_bh_reject": rej, "bv_bh_critical_p": crit,
            "bv_class": np.where(rej, [LISA_LABEL.get(int(q), "n/a") for q in lb.q], "ns"),
            "bv_i_global": row.bv_i, "bv_p_global": row.bv_p_sim}))
    bivariate_local = pd.concat(bv_local, ignore_index=True) if bv_local else pd.DataFrame()

    denominator = (pd.concat(denominator_sensitivity, ignore_index=True) if denominator_sensitivity
                   else pd.DataFrame())
    return dict(counts=counts, standardised=standardised, moran=moran, local=local, correlations=correlations,
                bivariate=bivariate, inequality=inequality, stability=stability, regions=regions,
                denominator=denominator, bivariate_local=bivariate_local, value_frames=value_frames,
                region_value=region_value, rem_establishments=rem_est, seconds=round(time.time() - t_v, 1))


# ---------------------------------------------------------------------------
# Rótulos bilingües de las láminas y las tablas
# ---------------------------------------------------------------------------
TR = {
    "comuna": ("Comuna", "Comuna"),
    "region": ("Región", "Region"),
    "smoothed_ratio": ("Razón estandarizada suavizada (Bayes empírico)", "Empirical-Bayes smoothed standardised ratio"),
    "crude_ratio": ("Razón estandarizada cruda", "Crude standardised ratio"),
    "rate": ("Tasa por 100.000 habitantes", "Rate per 100,000 population"),
    "expected": ("Casos esperados (estandarización indirecta)", "Expected counts (indirect standardisation)"),
    "observed": ("Observados", "Observed"),
    "shrink": ("Peso de contracción del suavizado", "Shrinkage weight of the smoother"),
    "morans_i": ("I de Moran", "Moran's I"),
    "lag": ("Rezago espacial (z)", "Spatial lag (z)"),
    "value_z": ("Valor estandarizado (z)", "Standardised value (z)"),
    "weights": ("Definición de pesos", "Weight definition"),
    "permutation": ("Distribución de referencia (999 permutaciones)", "Reference distribution (999 permutations)"),
    "lisa": ("LISA (cuadrante, BH q < 0,05)", "LISA (quadrant, BH q < 0.05)"),
    "gistar": ("Gi* de Getis–Ord (BH q < 0,05)", "Getis–Ord Gi* (BH q < 0.05)"),
    # Formas cortas para el interior de la lámina: el rótulo completo (con el umbral) va en la
    # leyenda de la lámina y en el panel de clave, no en cada título de panel de media página.
    "lisa_short": ("LISA", "LISA"),
    # Formas cortas de las magnitudes cartografiadas: el rótulo completo («razón estandarizada
    # suavizada por Bayes empírico») ocupaba tres renglones de título sobre un mapa de media página.
    "smoothed_ratio_short": ("Razón suavizada (BE)", "Smoothed ratio (EB)"),
    "rate_short": ("Tasa por 100.000", "Rate per 100,000"),
    "crude_ratio_short": ("Razón cruda", "Crude ratio"),
    "national_ref": ("referencia nacional = 1", "national reference = 1"),
    "gistar_short": ("Gi* de Getis–Ord", "Getis–Ord Gi*"),
    "n_comunas": ("Comunas", "Comunas"),
    "spearman": ("rho de Spearman", "Spearman's rho"),
    "bivariate": ("I de Moran bivariada", "Bivariate Moran's I"),
    "lorenz": ("Curva de Lorenz de eventos frente a población", "Lorenz curve of events against population"),
    "cum_pop": ("Proporción acumulada de población", "Cumulative share of population"),
    "cum_events": ("Proporción acumulada de eventos", "Cumulative share of events"),
    "gini": ("Índice de Gini", "Gini index"),
    "theil": ("Índice de Theil", "Theil index"),
    "between": ("Entre regiones", "Between regions"),
    "within": ("Dentro de las regiones", "Within regions"),
    "decile_ratio": ("Razón decil superior / decil inferior", "Top-decile / bottom-decile ratio"),
    "stability": ("Estabilidad del orden comunal", "Stability of the comuna ranking"),
    "early": ("Periodo temprano", "Early period"),
    "late": ("Periodo tardío", "Late period"),
    "sae_multi": ("Pobreza multidimensional comunal, % (SAE 2024)", "Comuna multidimensional poverty, % (SAE 2024)"),
    "sae_income": ("Pobreza por ingresos comunal, % (SAE 2024)", "Comuna income poverty, % (SAE 2024)"),
    "quintile": ("Quintil de privación", "Deprivation quintile"),
    "care_warning": ("Lugar de ATENCIÓN sobre denominador de RESIDENCIA", "Place of CARE over a RESIDENCE denominator"),
    "residence": ("Comuna de residencia", "Comuna of residence"),
    "care": ("Comuna del establecimiento", "Comuna of the establishment"),
    "no_report": ("Sin establecimiento reportante", "No reporting establishment"),
    "no_data": ("Sin dato", "No data"),
    "hot": ("Punto caliente", "Hot spot"),
    "cold": ("Punto frío", "Cold spot"),
    "ns": ("No significativo", "Not significant"),
    "national": ("Referencia nacional = 1", "National reference = 1"),
    "year": ("Año", "Year"),
    "reporting_comunas": ("Comunas con reporte", "Comunas with a report"),
    "n_events": ("Eventos", "Events"),
    "suppressed": ("<5 eventos (suprimido en tablas)", "<5 events (suppressed in tables)"),
    "indicator": ("Indicador", "Indicator"),
    "pair": ("Par de indicadores", "Indicator pair"),
    "ci95": ("IC 95\u00a0%", "95% CI"),   # espacio duro: el título nunca parte «95 %»
    "period": ("Periodo", "Period"),
}


def tr(key: str, lang: str) -> str:
    return TR[key][0 if lang == "es" else 1]


def ind_label(name: str, lang: str) -> str:
    spec = IND.get(name) or CONTEXT.get(name)
    return spec[lang]


def ind_short(name: str, lang: str) -> str:
    short = {
        "grd_episodes": ("GRD episodios F84", "GRD F84 episodes"),
        "grd_persons": ("GRD personas/año", "GRD persons/year"),
        "grd_principal": ("GRD F84 principal", "GRD F84 principal"),
        "a05_entries": ("REM A05 ingresos", "REM A05 entries"),
        "p2_stock": ("REM P2 diciembre", "REM P2 December"),
        "p6_primary": ("REM P6 APS", "REM P6 primary"),
        "p6_specialty": ("REM P6 especialidad", "REM P6 specialty"),
        "aps_enrolled": ("Inscritos APS", "APS enrolment"),
        "fonasa_beneficiaries": ("FONASA beneficiarios", "FONASA beneficiaries"),
        "rem20_discharges": ("REM-20 egresos", "REM-20 discharges"),
        "sae_multidimensional": ("SAE multidimensional", "SAE multidimensional"),
        "sae_income": ("SAE ingresos", "SAE income"),
        "urban_share": ("% urbano", "Urban %"),
        "fonasa_share": ("% FONASA/INE", "FONASA/INE %"),
    }
    return short.get(name, (name, name))[0 if lang == "es" else 1]


VALUE_TYPE_LABEL = {
    "rate_per_100k": ("Tasa por 100.000 habitantes", "Rate per 100,000 population"),
    "sir": ("Razón estandarizada cruda", "Crude standardised ratio"),
    "sir_eb": ("Razón estandarizada suavizada (Bayes empírico)", "Empirical-Bayes smoothed standardised ratio"),
    "value": ("Valor observado", "Observed value"),
}
SUBSET_LABEL = {
    "all comunas": ("todas las comunas", "all comunas"),
    "comunas with >=5 events": ("comunas con ≥5 eventos", "comunas with ≥5 events"),
    "excluding Metropolitan Region (13)": ("sin Región Metropolitana (13)", "excluding Metropolitan Region (13)"),
    "including non-continental comunas present in the cartography":
        ("incluye las comunas no continentales presentes en la cartografía",
         "including non-continental comunas present in the cartography"),
    "denominator base2017": ("denominador INE base 2017", "denominator INE base 2017"),
    "denominator censo2024": ("denominador Censo 2024", "denominator Census 2024"),
}
BASIS_LABEL = {
    "rate per 100,000": ("Tasa por 100.000 habitantes", "Rate per 100,000 population"),
    "empirical-Bayes smoothed standardised ratio":
        ("Razón estandarizada suavizada (Bayes empírico)", "Empirical-Bayes smoothed standardised ratio"),
}
def _pick(table: dict, key, lang: str) -> str:
    """Las etiquetas de categoría de las tablas se escriben en el idioma del archivo, nunca en clave interna."""
    pair = table.get(str(key))
    return str(key) if pair is None else pair[0 if lang == "es" else 1]


#: Forma corta del tipo de valor para los rótulos de eje del panel de media página.
VALUE_TYPE_SHORT = {
    "rate_per_100k": ("Tasa por 100.000", "Rate per 100,000"),
    "sir": ("Razón cruda", "Crude ratio"),
    "sir_eb": ("Razón suavizada (BE)", "Smoothed ratio (EB)"),
    "value": ("Valor observado", "Observed value"),
}


def vtype_short(value_type, lang: str) -> str:
    return _pick(VALUE_TYPE_SHORT, value_type, lang)


def vtype_label(value_type, lang: str) -> str:
    return _pick(VALUE_TYPE_LABEL, value_type, lang)


def subset_label(subset, lang: str) -> str:
    return _pick(SUBSET_LABEL, subset, lang)


#: La ventana de años se guarda con guion ASCII (clave de máquina; ver `common.yspan`) y se IMPRIME con
#: raya corta. `yspan` es esa conversión y vive en `common` porque el módulo 13 rotula la misma ventana en
#: la leyenda de su EF6: una sola definición para las dos láminas que la dibujan.
yspan = C.yspan


def years_label(years, lang: str) -> str:
    """Periodo tal como se IMPRIME en una tabla: «periodo completo»/«full period», o la ventana con raya."""
    return ("periodo completo" if lang == "es" else "full period") if str(years) == "full period" else yspan(years)


def scope_label(scope, lang: str) -> str:
    return tr("comuna", lang) if str(scope) == "comuna" else tr("region", lang)


#: Los valores de la columna `weights` viajan en inglés por el tidy (como todas las claves del estudio) y se
#: traducen al imprimir. Sin esta traducción las Tablas E43/E50 españolas imprimían «queen (16 regions)» en 34
#: filas mientras la prosa española dice «contigüidad reina» y el eje de la propia lámina (panel d de E44)
#: ya escribía «reina».
WEIGHTS_LABEL = {
    "queen": {"es": "reina", "en": "queen"},
    "queen (16 regions)": {"es": "reina (16 regiones)", "en": "queen (16 regions)"},
    "knn4": {"es": "knn4", "en": "knn4"},
    "knn8": {"es": "knn8", "en": "knn8"},
    "idw": {"es": "idw", "en": "idw"},
}


def weights_label(w, lang: str) -> str:
    """Definición de pesos en el idioma del documento («reina» / «queen»)."""
    key = str(w)
    lab = WEIGHTS_LABEL.get(key)
    return lab[lang] if lab else key


NE = {"es": "n/e", "en": "n/e"}

#: Signo NEGATIVO tipográfico (U+2212 MINUS SIGN) y raya de INTERVALO (U+2013 EN DASH). Son dos signos
#: distintos con dos oficios distintos y este módulo los escribía con el mismo trazo: `format` pone el
#: guion ASCII delante del negativo (2,9 pt de ancho a 8 pt) y `ci` separa el intervalo con la raya
#: (4,1 pt), de modo que una celda de la Tabla E46 se leía «rho = -0,10 (IC 95 % -0,21-0,00)» —tres trazos
#: casi iguales, ninguno separable del otro— y «-0,12 (-0,23–-0,02)» era ilegible. El menos tipográfico
#: mide 6,8 pt y se dibuja a la altura del eje matemático: el signo y el rango se distinguen a simple
#: vista. El choque es propio de este módulo porque es el único que separa el intervalo con RAYA (las
#: tablas de modelos lo separan con «a»/«to», donde el guion no compite con nada). Se aplica en `num`, que
#: es por donde pasa TODA cifra que este módulo imprime —láminas, ejes, títulos, leyendas y las doce tablas
#: E40–E51—, y en los dos idiomas por igual; las columnas `_numeric.csv`, que son para leer con una
#: máquina, conservan el número crudo.
MINUS, EN_DASH = "\u2212", "\u2013"


def _typographic_minus(s: str) -> str:
    """Cambia el guion ASCII del signo por el menos tipográfico. El separador de miles no lleva guion."""
    return s.replace("-", MINUS)


def num(x, dec=0, lang="es"):
    if x is None or (isinstance(x, str)) or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))) or pd.isna(x):
        return NE[lang] if not isinstance(x, str) else x
    return _typographic_minus(C.fmt_number(float(x), dec, lang))


def pct(x, lang="es", dec=1):
    return NE[lang] if x is None or pd.isna(x) else num(x, dec, lang) + (" %" if lang == "es" else "%")


#: Separador del intervalo cuando una de las cotas es NEGATIVA. La raya corta entre dos cifras positivas
#: («0,02–0,23») se lee sin esfuerzo; delante de un signo menos tipográfico no: «−0,21–0,00» pone un menos
#: (U+2212) y una raya (U+2013) a cuatro caracteres de distancia y el lector tiene que decidir cuál de los
#: dos separa y cuál es el signo. Medido sobre la lámina E46 del 2026-09-08: el menos ocupa 47 px y la raya
#: 29 px a 600 dpi —los dos glifos correctos, la raya NO era un guion (el guion mide 19–23 px)—, de modo que
#: lo que falla no es el carácter sino que haya dos rayas seguidas. Se usa entonces la conjunción con la que
#: el resto del corpus separa las cotas de un intervalo (`common.fmt_ci`: «19,9 a 21,6» / «19.9 to 21.6»),
#: y sólo en ese caso, para no alargar los rótulos de las láminas donde no hace falta.
_CI_WORD = {"es": " a ", "en": " to "}


def ci(lo, hi, dec=2, lang="es"):
    if lo is None or hi is None or pd.isna(lo) or pd.isna(hi):
        return NE[lang]
    sep = _CI_WORD[lang] if (float(lo) < 0 or float(hi) < 0) else EN_DASH
    return f"{num(lo, dec, lang)}{sep}{num(hi, dec, lang)}"


def fmt_p(p, lang="es"):
    return C.fmt_p(p, lang)


#: Cardinales en letra para las leyendas que cuentan indicadores. Se escriben en letra porque así lo pide
#: el estilo de la revista para las cifras pequeñas dentro de una frase; el NÚMERO nunca se teclea a mano,
#: se deriva de la lista que se está describiendo (ver `spelled`), que es lo que dejó a la leyenda de la
#: E44 prometiendo «trece indicadores» sobre una matriz de catorce.
SPELLED = {
    "es": {1: "un", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho",
           9: "nueve", 10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince",
           16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve", 20: "veinte"},
    "en": {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
           9: "nine", 10: "ten", 11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
           15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty"},
}


def spelled(n: int, lang: str = "es", upper: bool = False) -> str:
    """Cardinal en letra de `n` (1-20); fuera de ese rango, la cifra. `upper` para la versalita de la leyenda."""
    word = SPELLED[lang].get(int(n)) or C.fmt_number(int(n), 0, lang)
    return word.upper() if upper else word


# ---------------------------------------------------------------------------
# Cartografía de las láminas
# ---------------------------------------------------------------------------
def _abbrev(text, n: int = 26) -> str:
    """Recorta un rótulo de eje al ancho del panel de media página, marcando el recorte."""
    t = str(text)
    return t if len(t) <= n else t[: n - 1] + "…"


def _wrap(text: str, width: int = 52) -> str:
    """Los títulos de los mapas se reparten en varias líneas para que no se solapen entre paneles."""
    return "\n".join(textwrap.wrap(text, width) if "\n" not in text else
                     sum([textwrap.wrap(part, width) or [""] for part in text.split("\n")], []))


def chile_map(fig, slot, shapes, values: pd.Series, lang: str, title: str, cmap="YlGnBu", vmin=None, vmax=None,
              letter_=None, cbar_label="", center=None, log=False, missing_label=None, key="cut_comuna"):
    """Mapa comunal en tres franjas (norte, centro, sur) con la misma escala métrica y una barra de color común."""
    from matplotlib.colors import Normalize, TwoSlopeNorm, LogNorm
    from matplotlib import cm
    from matplotlib.patches import Patch
    sub = slot.subgridspec(2, 3, height_ratios=[1, 0.055], wspace=0.02, hspace=0.04)
    vals = values.reindex(shapes[key]).to_numpy(dtype=float)
    finite = vals[np.isfinite(vals)]
    if finite.size == 0:
        finite = np.array([0.0, 1.0])
    lo = float(np.nanquantile(finite, 0.02)) if vmin is None else vmin
    hi = float(np.nanquantile(finite, 0.98)) if vmax is None else vmax
    if hi <= lo:
        hi = lo + 1e-6
    if center is not None:
        spread = max(center - lo, hi - center, 1e-6)
        low = center - spread
        if float(np.nanmin(finite)) >= 0:
            low = max(low, 0.0)            # una razón nunca es negativa: la escala no baja de cero
        if low >= center:
            low = center - spread
        norm = TwoSlopeNorm(vcenter=center, vmin=low, vmax=center + spread)
    elif log:
        norm = LogNorm(vmin=max(lo, 1e-3), vmax=hi)
    else:
        norm = Normalize(vmin=lo, vmax=hi)
    mapper = cm.ScalarMappable(norm=norm, cmap=cmap)
    spans = []
    for band in BANDS:
        g = shapes[shapes.cut_region.isin(band)]
        b = g.total_bounds
        spans.append(b[3] - b[1])
    span = max(spans) * 1.04
    axes = []
    for k, band in enumerate(BANDS):
        ax = fig.add_subplot(sub[0, k])
        g = shapes[shapes.cut_region.isin(band)].copy()
        v = values.reindex(g[key]).to_numpy(dtype=float)
        cols = [mapper.to_rgba(x) if np.isfinite(x) else "#e9e9e9" for x in v]
        g.plot(color=cols, edgecolor="#666666", linewidth=0.18, ax=ax)
        b = g.total_bounds
        cy = (b[1] + b[3]) / 2
        cx = (b[0] + b[2]) / 2
        _map_frame(ax, cx, cy, span, (b[2] - b[0]) * 1.06)
        axes.append(ax)
    # El título va sobre la franja de la IZQUIERDA, alineado con el borde del panel: `_anchor_titles`
    # lo lleva después al borde de la columna, de modo que ocupa el ancho completo de la celda.
    _title(axes[0], title)
    cax = fig.add_subplot(sub[1, :])
    cb = fig.colorbar(mapper, cax=cax, orientation="horizontal")
    cb.set_label(cbar_label, fontsize=FS_MIN + 0.6)
    cb.ax.tick_params(labelsize=FS_MIN + 0.4)
    kax = None
    if missing_label:
        # La clave de «sin dato» NUNCA se dibuja sobre un mapa. Colgada de la franja sur —que es donde la
        # dejaron las dos rondas anteriores, primero al pie y después en el hueco «que menos tapa»— su
        # recuadro translúcido se imprimía sobre las comunas del norte de la franja central y su cuadro
        # gris sobre la costa: dentro de un eje de mapa no hay hueco que no sea territorio. Aquí la clave
        # baja a una FILA PROPIA del pie de la celda, debajo del rótulo de la barra de color, fuera de los
        # tres ejes de mapa. La fila se reserva en TODAS las celdas de mapa de la lámina (`_place_maps`),
        # tengan clave o no, para que los tres mapas sigan midiendo exactamente lo mismo.
        kax = fig.add_subplot(sub[1, 2])
        kax.set_axis_off()
        leg = kax.legend(handles=[Patch(facecolor="#e9e9e9", edgecolor="#666666", label=missing_label)],
                         loc="center", fontsize=FS_MIN + 0.2, frameon=False, borderpad=0.0,
                         borderaxespad=0.0, handlelength=1.5, handleheight=0.9, handletextpad=0.5)
        leg.set_in_layout(False)
    if letter_:
        _letter(axes[0], letter_)
    _register_map_cell(slot, axes, cax, "cbar", key=kax)
    return axes


CLASS_COLOURS = {"HH": "#c0392b", "LL": "#2471a3", "LH": "#8bb8d8", "HL": "#e59a8f",
                 "hot": "#c0392b", "cold": "#2471a3", "ns": "#f2f2f2"}
CLASS_LABEL = {
    "HH": ("Alto–Alto", "High–High"), "LL": ("Bajo–Bajo", "Low–Low"),
    "LH": ("Bajo–Alto", "Low–High"), "HL": ("Alto–Bajo", "High–Low"),
    "hot": ("Punto caliente", "Hot spot"), "cold": ("Punto frío", "Cold spot"),
    "ns": ("No significativo", "Not significant"),
}


def chile_map_classes(fig, slot, shapes, classes: pd.Series, lang: str, title: str, letter_=None, order=None,
                      legend: bool = True):
    """Mapa comunal categórico (LISA o Gi*) en tres franjas.

    Con `legend=False` el mapa ocupa la celda entera y la clave de clases —con su recuento— se imprime
    una sola vez en el panel de leyenda de la lámina: en una página vertical, repetir la leyenda bajo
    cada mapa robaba un 12 % del alto de cada mapa sin añadir información.
    """
    from matplotlib.patches import Patch
    sub = (slot.subgridspec(2, 3, height_ratios=[1, 0.055], wspace=0.02, hspace=0.04) if legend
           else slot.subgridspec(1, 3, wspace=0.02))
    axes = []
    spans = []
    for band in BANDS:
        b = shapes[shapes.cut_region.isin(band)].total_bounds
        spans.append(b[3] - b[1])
    span = max(spans) * 1.04
    for k, band in enumerate(BANDS):
        ax = fig.add_subplot(sub[0, k] if legend else sub[0, k])
        g = shapes[shapes.cut_region.isin(band)].copy()
        cls = classes.reindex(g.cut_comuna)
        cols = [CLASS_COLOURS.get(c, "#e9e9e9") for c in cls]
        g.plot(color=cols, edgecolor="#666666", linewidth=0.18, ax=ax)
        b = g.total_bounds
        cy = (b[1] + b[3]) / 2
        cx = (b[0] + b[2]) / 2
        _map_frame(ax, cx, cy, span, (b[2] - b[0]) * 1.06)
        axes.append(ax)
    _title(axes[0], title)
    if legend:
        counts = classes.value_counts()
        keys = order or [k for k in ["HH", "LL", "HL", "LH", "hot", "cold", "ns"] if k in counts.index]
        handles = [Patch(facecolor=CLASS_COLOURS.get(k, "#e9e9e9"), edgecolor="#666666",
                         label=f"{CLASS_LABEL[k][0 if lang == 'es' else 1]}: {num(counts.get(k, 0), 0, lang)}")
                   for k in keys]
        lax = fig.add_subplot(sub[1, :])
        lax.set_axis_off()
        lax.legend(handles=handles, loc="center", ncol=2, fontsize=FS_MIN, frameon=False,
                   columnspacing=1.0, handlelength=1.2, handletextpad=0.4)
    else:
        lax = None
    if letter_:
        _letter(axes[0], letter_)
    _register_map_cell(slot, axes, lax, "legend" if lax is not None else None)
    return axes


# ---------------------------------------------------------------------------
# Láminas E40–E49
# ---------------------------------------------------------------------------
OK = C.OKABE


def _sr(res, indicator, period="full", column="sir_eb") -> pd.Series:
    s = res["standardised"]
    sub = s[(s.indicator == indicator) & (s.period == period)]
    return sub.set_index("cut_comuna")[column]


# NORMA DE LÁMINA (fase 4c). Toda lámina multipanel se dibuja a tamaño final: lienzo vertical de
# 180 × 245 mm (7,09 × 9,65 pulgadas) a escala 1:1, rejilla de TRES FILAS POR DOS COLUMNAS, un máximo
# de seis paneles, letras de panel en minúscula (a…f) en la lámina y en la leyenda, tipografía base de
# 8 pt, título de panel de 9 pt en negrita, marcas de eje de 7 pt, leyenda de 7 pt, nada por debajo de
# 6 pt y 600 ppp. Antes las láminas se dibujaban con 432 mm de ancho y se encogían al insertarse
# (factor 0,41): esa es la causa de que los mapas y las matrices fueran apenas legibles.
PLATE_W_IN = 180 / 25.4                  # 7,09 pulgadas
PLATE_H_IN = 245 / 25.4                  # 9,65 pulgadas
PLATE_ROWS, PLATE_COLS = 3, 2
PLATE_MAX_PANELS = PLATE_ROWS * PLATE_COLS
PLATE_DPI = 600
FS_BASE, FS_TITLE, FS_TICK, FS_LEGEND = 8.0, 9.0, 7.0, 7.0
FS_MIN = 6.0
PANEL_LETTERS = "abcdef"
#: Ancho de línea del título de panel: 85 mm de panel a 9 pt en negrita ≈ 38 caracteres.
TITLE_WRAP = 38


def _plate_style():
    plt, _ = C.style()
    plt.rcParams.update({
        "font.size": FS_BASE, "axes.titlesize": FS_TITLE, "axes.titleweight": "bold",
        "axes.labelsize": FS_BASE, "xtick.labelsize": FS_TICK, "ytick.labelsize": FS_TICK,
        "legend.fontsize": FS_LEGEND, "figure.dpi": 100, "savefig.dpi": PLATE_DPI,
        # Toda leyenda de estas láminas se dibuja DENTRO del panel: sin recuadro se leía sobre las barras y
        # sobre los puntos. Con el recuadro blanco translúcido el dato sigue visible bajo ella.
        "legend.frameon": True, "legend.framealpha": 0.82, "legend.facecolor": "white",
        "legend.edgecolor": "none", "legend.borderpad": 0.25,
        "lines.linewidth": 1.3, "lines.markersize": 4.0, "axes.linewidth": 0.7,
        "xtick.major.size": 2.4, "ytick.major.size": 2.4, "xtick.major.pad": 1.8, "ytick.major.pad": 1.8,
        "axes.labelpad": 2.2, "axes.titlepad": 3.5,
    })
    return plt


def _plate(n_panels=PLATE_MAX_PANELS, note_lines=0):
    """Lámina vertical de 3 × 2 a escala 1:1.

    Devuelve ``(plt, fig, slots)`` con ``slots`` en orden de lectura: ``slots[0]`` es la celda del
    panel a y ``slots[5]`` la del f. Cada celda es un `SubplotSpec`, de modo que un panel corriente se
    crea con ``fig.add_subplot(slots[i])`` y un mapa de tres franjas con ``slots[i].subgridspec(...)``.
    """
    if n_panels > PLATE_MAX_PANELS:
        raise ValueError(f"una lámina no admite más de {PLATE_MAX_PANELS} paneles; pedidos {n_panels}")
    plt = _plate_style()
    fig = plt.figure(figsize=(PLATE_W_IN, PLATE_H_IN), constrained_layout=True)
    gs = fig.add_gridspec(PLATE_ROWS, PLATE_COLS)
    slots = [gs[i // PLATE_COLS, i % PLATE_COLS] for i in range(n_panels)]
    bottom = 0.0 if not note_lines else min(0.12, 0.0105 * note_lines + 0.005)
    fig.get_layout_engine().set(rect=(0.006, bottom + 0.004, 0.982, 0.982 - bottom),
                                w_pad=0.026, h_pad=0.022, wspace=0.050, hspace=0.060)
    return plt, fig, slots


#: Ancho útil del título dentro de una celda: media lámina menos 5 mm de margen y el hueco de la letra.
TITLE_W_PT = (PLATE_W_IN * 72.0) / PLATE_COLS - (5.0 / 25.4 * 72.0) - 12.0


#: Hueco mínimo, en puntos, entre el título de un panel y el del panel VECINO de la derecha. Sin él el
#: límite de plegado era el borde de la celda y el título de la columna izquierda podía terminar a 1,4 pt
#: del paréntesis que abre el de la derecha —un tercio del espacio de palabra que llevan dentro—, de modo
#: que las dos líneas se leían como una sola frase («… 2019–2024 — Smoothed(b) GRD persons/year …»).
#: 14 pt son más de tres espacios de palabra: el corte entre un título y el siguiente se ve.
TITLE_GUTTER_PT = 14.0


def _wrap_title(text, _legacy_width=None) -> str:
    """Envuelve un título al ancho MEDIDO de la celda, no a un número de caracteres.

    Contando caracteres, «Spearman's r», «(smoothed ratio)» y «between periods» quedaban en una línea más
    ancha que la celda y se imprimían cortados contra el borde del lienzo; el español, un 15 % más largo,
    lo hacía en más paneles todavía. El segundo argumento se acepta y se ignora: quedan llamadas heredadas
    que pasaban su propio ancho, calculado para el lienzo apaisado anterior."""
    return "\n".join(C.plate_wrap(part, TITLE_W_PT, FS_TITLE, "bold") for part in str(text).split("\n"))


def _title(ax, text, **kw):
    """Título de panel (9 pt negrita), envuelto al ancho del panel de media página."""
    kw.setdefault("fontsize", FS_TITLE)
    return ax.set_title(_wrap_title(text), **kw)


def _letter(ax, i):
    """Letra de panel EN MINÚSCULA y ENTRE PARÉNTESIS delante del título, alineado a la izquierda.

    El rótulo va dentro del título y no como texto fuera de los ejes: sin recorte «tight» un texto
    fuera de los ejes se pierde, y un título centrado más ancho que el panel se monta sobre la letra.
    """
    # Entre paréntesis, «(a)»: es la convención de las 58 leyendas con paneles y la que ya imprimían las
    # láminas de 06/08a/08b/08c. Con la letra a secas el artículo publicaba dos convenciones.
    ch = C.plate_panel_letter(PANEL_LETTERS[i] if isinstance(i, int) else i)
    txt = ax.get_title(loc="center")
    ax.set_title("", loc="center")
    # La letra se antepone a la PRIMERA línea del título ya envuelto: volver a envolver el texto
    # completo partía otra vez las líneas y producía títulos de tres y cuatro renglones.
    rows = str(txt).split("\n") if txt else [""]
    rows[0] = f"{ch} {rows[0]}".rstrip()
    ax.set_title("\n".join(rows), loc="left", fontsize=FS_TITLE, fontweight="bold", pad=3.5)


def _plate_note(fig, text, colour=None):
    """Nota al pie de la lámina, dentro del lienzo (sin recorte «tight» no hay margen que la rescate)."""
    fig.text(0.008, 0.004, text, fontsize=FS_MIN + 0.4, color=colour or "#555555", va="bottom",
             ha="left", linespacing=1.25)


#: Alto de la franja (metros) y centro de cada eje de mapa, para ajustar la ventana al recuadro final.
_MAP_FRAMES: dict[int, tuple[float, float, float]] = {}
#: Celdas de mapa (tres franjas + barra de color o clave) que se colocan a mano tras congelar el reparto.
_MAP_CELLS: list[dict] = []
#: Alto reservado bajo las franjas, en puntos: barra 5,5 pt + marcas 6,4 pt + rótulo 6,6 pt + holguras.
FOOT_CBAR_PT, FOOT_BAR_PT = 27.0, 5.5
#: Alto de la FILA DE CLAVE que va debajo del rótulo de la barra de color cuando el mapa tiene una clase
#: sin dato («Sin dato», «Sin establecimiento reportante»): una línea de 6,2 pt con su cuadro y sus
#: holguras. Se reserva en todas las celdas de mapa de la lámina, tengan clave o no, de modo que los
#: mapas de (a), (b) y (c) sigan midiendo lo mismo.
FOOT_KEY_PT = 11.0


def _register_map_cell(slot, axes, foot=None, kind=None, key=None) -> None:
    """Anota una celda de mapa y la SACA del reparto automático.

    `constrained_layout` no sabe repartir esta celda: la barra de color ocupa una fila de rejilla con una
    razón de alto de 0,055 mientras sus marcas y su rótulo piden cuatro veces más, el motor intenta
    compensar encogiendo las franjas, y cuando no lo consigue abandona el reparto con la advertencia
    «axes sizes collapsed to zero». El resultado eran mapas de 1,5 mm de ancho —las «astillas» del informe—
    y barras de color impresas sobre el título del panel de abajo. Fuera del reparto, la celda se coloca
    con geometría propia en `_place_maps` y el motor reparte el resto de la lámina sin verse arrastrado.
    """
    # Solo el PIE (barra de color o clave) sale del reparto: es su fila de rejilla enana —razón de alto
    # 0,055 frente a unas marcas y un rótulo que piden cuatro veces más— la que hacía colapsar el motor.
    # Las franjas siguen dentro del reparto: si salieran también, la celda dejaría de pedir sitio y las
    # filas de abajo se comerían la de arriba, con la barra de color de (a) cayendo sobre el título de (c).
    for art in (foot, key):
        if art is None:
            continue
        try:
            art.set_in_layout(False)
        except AttributeError:
            pass
    _MAP_CELLS.append(dict(slot=slot, axes=list(axes), foot=foot, kind=kind, key=key))


def _plate_rect(fig) -> tuple:
    """Rectángulo útil de la lámina (izquierda, abajo, ancho, alto) en fracción de figura."""
    try:
        rect = fig.get_layout_engine().get().get("rect")
        if rect and len(rect) == 4:
            return tuple(float(v) for v in rect)
    except (AttributeError, TypeError, ValueError):
        pass
    return (0.006, 0.004, 0.982, 0.982)


def _place_maps(fig) -> None:
    """Coloca cada celda de mapa dentro de SU celda de la rejilla, con el reparto ya congelado.

    Se reserva arriba el alto medido del título (que en español ocupa a menudo dos líneas) y abajo el de la
    barra de color o de la clave; lo que queda se reparte entre las tres franjas. Así ni la barra ni el
    título salen de la celda, que es lo que hacía que la barra de (a) se imprimiera sobre el título de (c).
    """
    if not _MAP_CELLS:
        return
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    H = fig.bbox.height
    left, bottom, width, height = _plate_rect(fig)
    cw, ch = width / PLATE_COLS, height / PLATE_ROWS
    # El margen inferior de una celda de mapa es mayor que el superior: bajo la barra de color van sus
    # marcas y su rótulo, y sin ese respiro el rótulo de la barra de (b) se imprimía sobre el título de (d).
    pad_x, pad_top, pad_bot = 2.0 / 180.0, 2.0 / 245.0, 5.0 / 245.0
    gap = 1.2 / 180.0
    # La fila de clave se reserva en TODAS las celdas de barra de color en cuanto UNA de ellas lleva
    # clave: si sólo la reservara la celda que la lleva, el mapa de (a) mediría 11 pt menos que los de
    # (b) y (c) —cada celda escala sus franjas al alto que le queda— y la lámina compararía tres mapas
    # dibujados a escalas distintas.
    key_row = (FOOT_KEY_PT / 72.0 / fig.get_size_inches()[1]
               if any(c["kind"] == "cbar" and c.get("key") is not None for c in _MAP_CELLS) else 0.0)
    for cell in _MAP_CELLS:
        spec = cell["slot"]
        col, row = int(spec.colspan.start), int(spec.rowspan.start)
        x0 = left + col * cw + pad_x
        x1 = left + (col + 1) * cw - pad_x
        y1 = bottom + height - row * ch - pad_top
        y0 = bottom + height - (row + 1) * ch + pad_bot
        # La rejilla NO se reparte en tercios iguales: `constrained_layout` da a cada fila el alto que su
        # contenido pide, de modo que la fila de los mapas —que pide poco— cede sitio a las de abajo. Tomar
        # la banda ideal de un tercio ponía la barra de color de (a) sobre el título de (c), que en la
        # geometría real empieza más arriba. La banda vertical se lee del reparto ya hecho.
        placed = [a.get_position() for a in cell["axes"]]
        from_layout = bool(placed) and (max(q.y1 for q in placed) - min(q.y0 for q in placed)) > 0.04
        head = cell["axes"][0]
        t = next((c for c in (getattr(head, "_left_title", None), head.title)
                  if c is not None and c.get_text()), None)
        if from_layout:
            # El reparto ya descontó el título: la banda que devuelve empieza justo debajo.
            y1 = max(q.y1 for q in placed)
            y0 = min(q.y0 for q in placed)
            th = 0.002
        else:
            th = 0.0
            if t is not None:
                th = t.get_window_extent(r).height / H + 0.004
        foot = cell["foot"]
        if foot is None:
            fh = 0.0
        elif cell["kind"] == "cbar":
            fh = FOOT_CBAR_PT / 72.0 / fig.get_size_inches()[1] + key_row
        else:
            lg = next((c for c in foot.get_children() if c.__class__.__name__ == "Legend"), None)
            fh = ((lg.get_window_extent(r).height / H + 0.006) if lg is not None
                  else 20.0 / 72.0 / fig.get_size_inches()[1])
        top, bot = y1 - th, y0 + fh
        n = len(cell["axes"])
        h = max(0.02, top - bot)
        # Cada franja recibe el ancho que su geografía necesita a la escala vertical común, no un tercio
        # fijo de la celda: con tercios iguales el norte y el centro —estrechos— dejaban dos tercios de su
        # recuadro en blanco y el país se leía como una astilla en medio de un rectángulo vacío.
        w_in, h_in = fig.get_size_inches()
        frames = [_MAP_FRAMES.get(id(ax)) for ax in cell["axes"]]
        span_m = max((f[2] for f in frames if f), default=0.0)
        dws = [f[3] if f and len(f) > 3 and f[3] > 0 else span_m * 0.34 for f in frames]
        avail = (x1 - x0 - (n - 1) * gap) * w_in
        if span_m > 0 and sum(dws) > 0:
            scale = (h * h_in) / span_m                     # pulgadas por metro
            widths = [d * scale for d in dws]
            if sum(widths) > avail:                          # no cabe a lo ancho: se reduce la escala
                k = avail / sum(widths)
                widths = [q * k for q in widths]
                h = h * k
            widths = [q / w_in for q in widths]
        else:
            widths = [(x1 - x0 - (n - 1) * gap) / n] * n
        x = x0 + max(0.0, (x1 - x0 - sum(widths) - (n - 1) * gap)) / 2.0
        for k, ax in enumerate(cell["axes"]):
            ax.set_position([x, bot, widths[k], h])
            x += widths[k] + gap
        if foot is None:
            continue
        if cell["kind"] == "cbar":
            bar = FOOT_BAR_PT / 72.0 / fig.get_size_inches()[1]
            foot.set_position([x0 + 0.06 * (x1 - x0), y0 + fh - bar - 0.004, 0.88 * (x1 - x0), bar])
            kax = cell.get("key")
            if kax is not None:
                # Franja propia al pie de la celda, bajo el rótulo de la barra: fuera de los tres ejes
                # de mapa y fuera de la barra de color, de modo que la clave no pisa ni territorio ni
                # cifras. La barra de color y sus marcas ocupan los FOOT_CBAR_PT de arriba.
                kax.set_position([x0, y0, x1 - x0, max(0.006, key_row - 0.0015)])
        else:
            foot.set_position([x0, y0, x1 - x0, max(0.012, fh - 0.004)])


def _map_frame(ax, cx: float, cy: float, span: float, dw: float = 0.0) -> None:
    """Prepara un eje de mapa: sin marcas, sin proporción fija y con su ventana anotada.

    La proporción se impone DESPUÉS del reparto (`_fit_maps`): con `set_aspect("equal")` matplotlib
    encogía el recuadro hasta que el mapa medía menos de la mitad de la celda, y las tres franjas de
    una misma lámina acababan con tamaños distintos según el largo del título de cada panel.
    """
    ax.set_aspect("auto")
    ax.set_axis_off()
    ax.set_ylim(cy - span / 2, cy + span / 2)
    ax.set_xlim(cx - span * 0.34 / 2, cx + span * 0.34 / 2)
    _MAP_FRAMES[id(ax)] = (cx, cy, span, dw)


def _fit_maps(fig) -> None:
    """Ajusta la ventana de cada mapa a su recuadro ya repartido, SIN deformar la geografía.

    La escala vertical la fija el alto del recuadro (igual para las tres franjas de la lámina) y la
    ventana horizontal se abre lo que haga falta para que un metro mida lo mismo en los dos ejes.
    """
    if not _MAP_FRAMES:
        return
    w_in, h_in = fig.get_size_inches()
    for ax in fig.axes:
        frame = _MAP_FRAMES.get(id(ax))
        if frame is None:
            continue
        cx, cy, span = frame[0], frame[1], frame[2]
        pos = ax.get_position()
        box_w = max(pos.width * w_in, 1e-6)
        box_h = max(pos.height * h_in, 1e-6)
        ax.set_ylim(cy - span / 2, cy + span / 2)
        x_range = span * box_w / box_h
        ax.set_xlim(cx - x_range / 2, cx + x_range / 2)


def _plate_column(ax, pos) -> int:
    """Columna de la rejilla a la que pertenece un panel.

    Se lee del `SubplotSpec` de más alto nivel, que para una franja de mapa devuelve la celda de la
    lámina y no la subcelda: con el umbral sobre la posición, la primera franja del mapa de la derecha
    caía en la columna izquierda y su título se dibujaba encima del título del panel vecino.
    """
    try:
        top = ax.get_subplotspec().get_topmost_subplotspec()
        return int(top.colspan.start) % PLATE_COLS
    except (AttributeError, ValueError, TypeError):
        return 0 if pos.x0 + pos.width / 2 < 0.5 else 1


def _anchor_titles(fig) -> None:
    """Alinea el título de cada panel con el borde izquierdo visible de su COLUMNA.

    `loc="left"` alinea con el borde de los ejes, no con el del panel: con rótulos de eje largos el
    título arrancaba muy a la derecha y se salía del lienzo. Se resuelve el reparto, se congela y se
    recolocan los títulos.
    """
    fig.canvas.draw()
    fig.set_layout_engine("none")
    r = fig.canvas.get_renderer()
    width = fig.bbox.width
    edges = []
    for ax in fig.axes:
        if not ax.get_title(loc="left"):
            continue
        pos = ax.get_position()
        left = pos.x0
        if ax.axison:                       # un mapa con el eje apagado no tiene marcas que sangrar
            try:
                left = min(left, ax.yaxis.get_tightbbox(r).x0 / width)
            except (AttributeError, ValueError, TypeError):
                pass
        edges.append((ax, pos, max(left, 0.006)))
    columns: dict[int, float] = {}
    keys = {}
    for ax, pos, left in edges:
        key = _plate_column(ax, pos)
        keys[id(ax)] = key
        columns[key] = min(columns.get(key, left), left)
    for ax, pos, left in edges:
        key = keys[id(ax)]
        x0 = columns[key]
        # El título arranca en x0, que no es el borde de la celda sino el borde VISIBLE de la columna: el
        # ancho que le queda hasta el borde derecho de su celda es lo que hay, y a ese ancho se pliega. Sin
        # este segundo plegado los títulos largos se cortaban contra el borde del lienzo («Spearman's r»,
        # «(smoothed rati», «between peri»).
        # El borde derecho útil no es el de la CELDA sino donde ARRANCA el título del panel vecino, que
        # puede empezar a la izquierda de ese borde; y hasta él hay que dejar un hueco visible.
        right = columns.get(key + 1)
        gutter = TITLE_GUTTER_PT if right is not None else 4.0
        if right is None:
            right = (key + 1) / PLATE_COLS
        disponible = max(60.0, (right - x0) * width * 72.0 / fig.dpi - gutter)
        texto = " ".join(ax.get_title(loc="left").split())
        ax.set_title(C.plate_wrap(texto, disponible, FS_TITLE, "bold"), loc="left", fontsize=FS_TITLE,
                     fontweight="bold", pad=3.5, x=(x0 - pos.x0) / pos.width)


# ---------------------------------------------------------------------------
# LA RAYA DEL INTERVALO IMPRESO (fase 4i, tarea H3; unificada en la fase 4j, tarea J2)
# ---------------------------------------------------------------------------
#: UN INTERVALO NUMÉRICO QUE EL LECTOR LEE SE SEPARA CON RAYA CORTA (U+2013), NUNCA CON GUION; el guion
#: ASCII queda para lo que una máquina vuelve a leer (las claves `age_group`, `depth_bin`, `years` y
#: `age_band_10` de las tablas tidy, los nombres de archivo y los códigos), y el menos tipográfico para el
#: número negativo.
#:
#: LA REGLA YA NO VIVE AQUÍ. Hasta la fase 4i estaba copiada, palabra por palabra, en CINCO módulos —`08a`,
#: `08b`, `08c`, `14` y `15b`— y por eso NO estaba en los otros cuatro que dibujan láminas (`06`, `08d`,
#: `13`, `15`): 448 intervalos con guion frente a 774 con raya en nueve láminas publicadas. Está escrita una
#: sola vez en `common` (`C.range_dash` y `C.plate_range_dash`), con sus cuatro categorías y sus tres
#: trazos, y `common` la aplica sola al principio de `plate_fit` y de `plate_resolve`, por los que pasan
#: TODAS las láminas del estudio. Estas dos funciones se conservan porque el módulo las nombra en su
#: guardado y porque dejan EXPLÍCITO el momento en que se aplica: antes del reparto, para que el motor mida
#: el texto definitivo y una marca que crece 1,5 pt al cambiar de trazo no se salga de su columna.
def dash_label(s: str) -> str:
    """«0-4» → «0–4». Delega en la regla única del estudio (`common.range_dash`)."""
    return C.range_dash(s)


def dash_intervals(fig) -> int:
    """Pasa la regla por todo el texto que la lámina dibuja. Delega en `common.plate_range_dash`.

    Devuelve cuántos rótulos cambió: 0 en una lámina que ya cumple, de modo que sirve de medida."""
    return C.plate_range_dash(fig)


def _save(fig, fdir: Path, name: str, plt, lang: str) -> str:
    """Guarda a 600 ppp SIN recorte «tight»: el archivo mide exactamente 180 × 245 mm.

    Las anotaciones dentro de un panel se excluyen del reparto: `constrained_layout` las suma al
    recuadro del panel y con una nota larga concluye que el panel mide cero y abandona el reparto.

    Con el reparto ya congelado se resuelve todo lo que depende de la geometría FINAL: las marcas
    numéricas en la convención del idioma, la celda de cada matriz, la posición de cada leyenda, los
    rótulos de punta de barra, los rótulos de valor y los bloques del panel de clave. Decidirlo antes de
    congelar era la causa de las leyendas sobre los datos: la columna de la rejilla la fija el panel de
    rótulos más largos y el panel cambia de tamaño después de dibujarse.
    """
    _localise_ticks(fig, lang)
    for ax in fig.axes:
        for txt in ax.texts:
            txt.set_in_layout(False)
    # Motor de descongestión (common.py): mide lo dibujado y resuelve colisiones, recortes y leyendas.
    # `plate_fit` actúa con la composición todavía viva (marcas de eje, rótulos de eje, leyendas);
    # `plate_resolve`, ya congelada, separa los rótulos que se pisan y devuelve dentro lo que se sale.
    # La regla de la raya se aplica ANTES del reparto: el motor mide el texto definitivo y una
    # marca que crece 1,5 pt al cambiar de trazo no se sale de su columna después de medida.
    dash_intervals(fig)
    C.plate_fit(fig)
    fig.canvas.draw()
    fig.set_layout_engine("none")
    fig.canvas.draw()
    _place_maps(fig)
    _place_heat(fig)
    _anchor_titles(fig)
    _place_legends(fig)
    _fit_tip_labels(fig)
    _place_values(fig)
    _place_key_blocks(fig)
    C.plate_frame_notes(fig)
    _fit_maps(fig)
    C.plate_resolve(fig)
    path = Path(fdir) / f"{name}.png"
    # Modo revista (PLATE_JOURNAL, apagado por omisión): títulos fuera, convención numérica y ruta
    # de la revista; con el modo apagado devuelve la misma ruta y no toca la figura.
    path = C.journal_plate_export(fig, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=PLATE_DPI, facecolor="white")
    plt.close(fig)
    _MAP_FRAMES.clear()
    _MAP_CELLS.clear()
    for registry in (_LEGENDS, _TIPS, _VALUES, _KEYS, _HEAT_CELLS):
        registry.clear()
    return str(path)


def _spear_text(rho: dict, lang: str) -> str:
    return (f"{tr('spearman', lang)} = {num(rho['rho'], 2, lang)} "
            f"({tr('ci95', lang)} {ci(rho['rho_lo'], rho['rho_hi'], 2, lang)}; n = {num(rho['n'], 0, lang)})")


LAW_X = CFG.LAW_YEAR - 0.30      # marzo de 2023 sobre un eje de años centrados
#: Marca dentro del panel; el texto completo («marzo de 2023, contexto de política») va en la leyenda.
LAW_TEXT = ("Ley 21.545 (2023)", "Law 21.545 (2023)")


def law_marker(ax, lang: str, band: float = 0.16) -> None:
    """Marcador vertical de contexto de la Ley 21.545: nunca una intervención con efecto estimable.

    El rótulo se escribe EN HORIZONTAL dentro de una banda RESERVADA sobre los datos (se amplía el
    límite superior del eje) y sin recuadro. Escrito en vertical dentro del panel y con caja blanca
    translúcida se imprimía sobre las mismas series que venía a fechar —hasta el 7 % de una línea en los
    paneles anuales de E43, E47 y E48— y la caja tapaba el trozo que cruzaba.
    """
    lo, hi = ax.get_xlim()
    if not (lo - 0.5 <= LAW_X <= hi + 0.5):
        return
    ax.axvline(LAW_X, color="#333333", ls=":", lw=1.1, zorder=0)
    y0, y1 = ax.get_ylim()
    if ax.get_yscale() == "log" and y0 > 0 and y1 > y0:
        ax.set_ylim(y0, y1 * (y1 / y0) ** band)
    elif y1 > y0:
        ax.set_ylim(y0, y1 + (y1 - y0) * band)
    # El rótulo se ancla al lado de la línea donde queda más sitio: así no se sale del panel ni en el
    # eje 2019–2024 (la marca cae a la derecha) ni en el 2019–2025 (cae en el centro).
    right = (hi - LAW_X) >= (LAW_X - lo)
    txt = LAW_TEXT[0 if lang == "es" else 1]
    ax.text(LAW_X, 0.995, (" " + txt) if right else (txt + " "), transform=ax.get_xaxis_transform(),
            fontsize=FS_MIN, color="#333333", va="top", ha="left" if right else "right", zorder=6)


# ---------------------------------------------------------------------------
# Colocación MEDIDA sobre la lámina ya congelada
# ---------------------------------------------------------------------------
# Todo lo que sólo se puede colocar bien con el reparto ya congelado se anota aquí y se resuelve en
# `_save`: antes de congelar, la geometría del panel todavía cambia —la columna de la rejilla la fija el
# panel de rótulos más largos— y una leyenda «que no tapa nada» acaba encima de la serie más alta.
_LEGENDS: list[dict] = []
_TIPS: list[dict] = []
_VALUES: list[dict] = []
_KEYS: list[dict] = []
_HEAT_CELLS: list[dict] = []


def _legend(ax, *args, prefer=(), **kw):
    """Leyenda colocada donde NO tapa ningún dato (`common.plate_place_legend`, ya congelada la lámina)."""
    kw.setdefault("fontsize", FS_LEGEND)
    kw.setdefault("framealpha", 0.92)
    lg = ax.legend(*args, **kw)
    if lg is not None:
        _LEGENDS.append(dict(ax=ax, legend=lg, prefer=tuple(prefer)))
    return lg


def _place_legends(fig) -> None:
    for item in _LEGENDS:
        if item["ax"].figure is fig:
            C.plate_place_legend(item["ax"], item["legend"], prefer=item["prefer"])


def _tip_label(ax, value, pos, text, fontsize=None, color="#333333", pad_pt=2.6):
    """Rótulo pegado a la PUNTA de su barra, por fuera, con el eje ensanchado después hasta que quepa.

    Anclado al borde del panel —que es como se escribía el valor p en E45-c, E43-e y E49-e— el rótulo se
    imprime sobre el extremo de las barras largas y deja un hueco absurdo junto a las cortas.

    Va marcado con `PLATE_KEEP`: su sitio es DELIBERADO y `_fit_tip_labels` ya garantiza que cabe dentro
    del panel. Sin esa marca, el motor lo trataba como un rótulo suelto: `plate_frame_notes` le pintaba
    detrás un recuadro blanco de rescate y la pasada de colisiones lo devolvía hacia dentro, con lo que el
    recuadro acababa sobre la PUNTA de la barra que rotula. En la E45 (c) —que ordena los pares por su I
    bivariada— eso borraba entre el 20 % y el 30 % de las SEIS barras más largas: las de arriba se
    imprimían más cortas de lo que valen y el orden que el panel dibuja dejaba de leerse. Fuera del motor,
    el rótulo se queda donde se puso, en blanco limpio a la derecha de la punta, y no tapa nada."""
    v = float(value)
    ann = ax.annotate(str(text), xy=(v, pos), xycoords="data", textcoords="offset points",
                      xytext=(pad_pt if v >= 0 else -pad_pt, 0), va="center",
                      ha="left" if v >= 0 else "right", color=color, zorder=6, gid=C.PLATE_KEEP,
                      fontsize=max(FS_MIN, FS_MIN + 0.2 if fontsize is None else fontsize))
    _TIPS.append(dict(ax=ax, ann=ann))
    return ann


def _fit_tip_labels(fig) -> None:
    """Ensancha el eje X hasta que ningún rótulo de punta de barra se salga de su panel."""
    groups: dict[int, tuple] = {}
    for item in _TIPS:
        if item["ax"].figure is fig:
            groups.setdefault(id(item["ax"]), (item["ax"], []))[1].append(item["ann"])
    for ax, anns in groups.values():
        for _ in range(6):
            fig.canvas.draw()
            r = fig.canvas.get_renderer()
            box = ax.get_window_extent()
            over_lo = over_hi = 0.0
            for ann in anns:
                b = ann.get_window_extent(r)
                over_lo = max(over_lo, box.x0 - b.x0)
                over_hi = max(over_hi, b.x1 - box.x1)
            if over_lo <= 0.5 and over_hi <= 0.5:
                break
            lo, hi = ax.get_xlim()
            per_px = (hi - lo) / max(box.width, 1.0)
            d_lo = (over_lo + 2.0) * per_px if over_lo > 0.5 else 0.0
            d_hi = (over_hi + 2.0) * per_px if over_hi > 0.5 else 0.0
            if abs(lo + hi) < 1e-9 * max(abs(hi), 1.0):     # eje simétrico: el cero sigue en el centro
                d_lo = d_hi = max(d_lo, d_hi)
            ax.set_xlim(lo - d_lo, hi + d_hi)


def _value_label(ax, x, y, text, **kw):
    """Rótulo de valor separado de su marcador (se resuelve en `_save`, ya congelada la lámina).

    `leader=True` añade una línea fina de guía cuando el colocador ha tenido que alejar el rótulo de su
    punto: en una nube de dieciséis regiones el nombre acaba a veces más cerca del marcador de otra."""
    _VALUES.append(dict(ax=ax, x=float(x), y=float(y), text=str(text), kw=kw))


def _leader_line(ax, ann, x, y, near_pt: float = 3.5) -> None:
    """Une el rótulo con SU punto cuando queda lejos de él.

    Es el defecto del panel (f) de la E49: los nombres se apartan hasta encontrar hueco y el lector ya no
    puede emparejarlos («Metropolitana» y «Atacama» sin ningún punto al lado, «Tarapacá» y «Coquimbo»
    pegados letra con letra, «Los Lagos» sobre el marcador de otra región). La guía va por debajo del
    rótulo y se detiene antes del disco, de modo que no tapa ni el nombre ni el dato."""
    try:
        dx, dy = ann.xyann
    except (AttributeError, TypeError, ValueError):
        return
    if float(np.hypot(float(dx), float(dy))) < near_pt:
        return
    ax.annotate("", xy=(x, y), xycoords="data", xytext=(float(dx), float(dy)), textcoords="offset points",
                arrowprops=dict(arrowstyle="-", lw=0.5, color="#9a9a9a", shrinkA=1.0, shrinkB=4.0),
                zorder=5, annotation_clip=False)


def _place_values(fig) -> None:
    for item in _VALUES:
        if item["ax"].figure is not fig:
            continue
        kw = dict(item["kw"])
        leader = bool(kw.pop("leader", False))
        ann = C.plate_value_label(item["ax"], item["x"], item["y"], item["text"], **kw)
        if leader:
            # El colocador ya midió el hueco y la guía se dibuja hacia ESE sitio: si la pasada de
            # colisiones vuelve a mover el rótulo, la guía queda apuntando al vacío. Se marca como
            # colocado a conciencia, igual que hacen las otras láminas del estudio con sus rótulos medidos.
            ann.set_gid(C.PLATE_KEEP)
            _leader_line(item["ax"], ann, item["x"], item["y"])


def _key_blocks(ax, legend, blocks) -> None:
    """Bloques de texto de un panel de clave, que se colocan BAJO la leyenda ya medida."""
    _KEYS.append(dict(ax=ax, legend=legend, blocks=list(blocks)))


def _place_key_blocks(fig) -> None:
    """Coloca los bloques del panel de clave uno bajo otro, midiendo la leyenda y cada bloque.

    Con las alturas escritas a mano (0,62 y 0,24) la leyenda española —más larga y por tanto más alta—
    caía sobre el primer bloque: el título «Clase local» se imprimía sobre la advertencia ⚠.
    """
    for item in _KEYS:
        ax = item["ax"]
        if ax.figure is not fig:
            continue
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        box = ax.get_window_extent()
        y = 1.0
        lg = item["legend"]
        if lg is not None:
            y = (lg.get_window_extent(r).y0 - box.y0) / max(box.height, 1.0) - 0.045
        for text, colour, size in item["blocks"]:
            t = ax.text(0.0, y, text, transform=ax.transAxes, fontsize=size, va="top", ha="left",
                        linespacing=1.35, color=colour)
            t.set_in_layout(False)
            # Posición deliberada: el motor de descongestión busca «el hueco más vacío del panel» y en un
            # panel de clave —sin datos— eso significa barajar los tres bloques y subir la advertencia ⚠
            # sobre el título de la leyenda. Aquí el orden de lectura es la información.
            t.set_gid(C.PLATE_KEEP)
            fig.canvas.draw()
            h = t.get_window_extent(fig.canvas.get_renderer()).height / max(box.height, 1.0)
            y -= h + 0.035


def _place_heat(fig) -> None:
    """Da a cada matriz el ancho ÚTIL de su celda y decide, MIDIENDO, si el coeficiente cabe.

    `constrained_layout` reparte por columnas de la rejilla: el borde izquierdo de la matriz lo fijaba el
    panel de la misma columna con los rótulos de eje más largos, de modo que la matriz quedaba encajonada
    en 43 mm y la celda en 5,37 mm —justo lo que mide «-0,10» a 6 pt—, y los coeficientes negativos
    contiguos se imprimían sin separación («-0,10-0,08-0,07», «-0,42-0,77»). Aquí la celda de la matriz
    se coloca con geometría propia, con su barra de color a la derecha, y el coeficiente se degrada por
    escalones —dos decimales, un decimal, sólo color— antes que imprimirse pegado al de al lado.
    """
    if not _HEAT_CELLS:
        return
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    W = fig.bbox.width
    w_in, h_in = fig.get_size_inches()
    left, bottom, width, height = _plate_rect(fig)
    cw = width / PLATE_COLS
    pad, gap = 2.0 / 180.0, 1.6 / 180.0
    for cell in _HEAT_CELLS:
        ax, cb = cell["ax"], cell["cbar"]
        if ax.figure is not fig:
            continue
        col = int(cell["slot"].colspan.start)
        x0c, x1c = left + col * cw + pad, left + (col + 1) * cw - pad
        try:
            wy = ax.yaxis.get_tightbbox(r).width / W
        except (AttributeError, ValueError, TypeError):
            wy = 0.0
        wc = 0.0
        if cb is not None:
            try:
                tb = cb.ax.get_tightbbox(r)
                wc = (tb.x1 - tb.x0) / W + gap
            except (AttributeError, ValueError, TypeError):
                wc = 14.0 / 180.0
        pos = ax.get_position(original=True)
        x0 = x0c + wy + gap
        avail_w = max(0.02, (x1c - wc) - x0) * w_in
        side = min(avail_w, pos.height * h_in)          # la matriz sigue siendo cuadrada
        w_f, h_f = side / w_in, side / h_in
        ax.set_position([x0, pos.y1 - h_f, w_f, h_f])
        if cb is not None:
            bar = 2.0 / 180.0
            hh = h_f * 0.74
            cb.ax.set_position([x0 + w_f + gap, pos.y1 - h_f + (h_f - hh) / 2, bar, hh])
        fig.canvas.draw()
        _fit_heat_values(fig, cell, side * 25.4 / max(cell["n"], 1))


def _fit_heat_values(fig, cell, cell_mm: float, gap_mm: float = 0.9) -> str:
    """Degrada el coeficiente de la matriz hasta que dos celdas contiguas no se toquen.

    Nunca baja del cuerpo mínimo de la norma (6 pt) ni imprime un número pegado al de al lado: lo que la
    lámina deja de imprimir está íntegro en la tabla acompañante (matriz completa de los catorce
    indicadores, en las dos escalas y con IC, p y n).
    """
    labels = cell["labels"]
    if not labels or cell_mm <= 0:
        return "none"

    def widest() -> float:
        r = fig.canvas.get_renderer()
        return max(((C._pl_extent(t, r) or fig.bbox).width for t, _v in labels), default=0.0) * 25.4 / fig.dpi

    if widest() + gap_mm <= cell_mm:
        return "2 decimals"
    for t, v in labels:
        t.set_text(num(v, 1, cell["lang"]))
    fig.canvas.draw()
    if widest() + gap_mm <= cell_mm:
        return "1 decimal"
    for t, _v in labels:
        t.set_visible(False)
    return "colour only"


class _LocaleLogFormatter(matplotlib.ticker.Formatter):
    """Escribe la marca de un eje logarítmico en la convención del idioma SIN decidir cuáles llevan rótulo.

    Esa decisión es del formateador de matplotlib (deja en blanco las marcas que no toca rotular), y aquí
    sólo se cambia cómo se escribe el número que él sí rotula: 10.000 en español, 10,000 en inglés, nunca
    10000 ni notación científica.
    """

    def __init__(self, inner, lang: str):
        super().__init__()
        self.inner, self.lang = inner, lang

    def set_axis(self, axis):
        super().set_axis(axis)
        try:
            self.inner.set_axis(axis)
        except AttributeError:
            pass

    def set_locs(self, locs):
        try:
            self.inner.set_locs(locs)
        except (AttributeError, TypeError):
            pass

    def __call__(self, x, pos=None):
        try:
            raw = self.inner(x, pos)
        except (ValueError, TypeError, AttributeError):
            raw = ""
        if not str(raw).strip() or x is None or not np.isfinite(x) or x <= 0:
            return raw
        dec = 0 if x >= 1 else min(4, max(1, int(np.ceil(-np.log10(x)))))
        return num(x, dec, self.lang)


class _LocaleLinFormatter(matplotlib.ticker.Formatter):
    """Marca de un eje lineal en la convención del idioma, con los decimales resueltos AL ESCRIBIR.

    El número de decimales lo piden las marcas del eje EN CONJUNTO —si alguna cae en 0,5 el eje entero se
    escribe con un decimal—, y por eso no puede congelarse cuando se instala el formateador:
    `_localise_ticks` corre antes de `C.plate_fit` y de los dos `draw()` que congelan el reparto, y al
    redimensionarse el panel el localizador vuelve a marcar de 0,5 en 0,5. Con los decimales congelados a
    cero, el eje x de la S45 (f) imprimía «1 2 2 2 3 4 4 4 5» y el de la S46 (e) «0 0 1 1 2 2 2 3 4 4»:
    marcas REPETIDAS, ninguna posición legible. Aquí se miran las marcas vigentes en cada llamada.
    """

    def __init__(self, axis, lang: str):
        super().__init__()
        self.axis, self.lang = axis, lang

    def _decimals(self) -> int:
        try:
            lo, hi = sorted(self.axis.get_view_interval())
            ticks = [float(t) for t in self.axis.get_majorticklocs() if lo - 1e-9 <= t <= hi + 1e-9]
        except (AttributeError, TypeError, ValueError):
            ticks = []
        if not ticks:
            return 0
        for d in range(4):
            if all(abs(t * 10 ** d - round(t * 10 ** d)) < 1e-6 for t in ticks):
                return d
        return 3

    def __call__(self, v, pos=None):
        if v is None or not np.isfinite(v):
            return ""
        dec = self._decimals()
        if dec == 0 and abs(v) < 10000:
            # Los años nunca llevan separador de miles; el signo, cuando lo hay (retardo espacial, z de
            # Moran), es el menos tipográfico como en el resto del módulo.
            return _typographic_minus(str(int(round(v))))
        return num(v, dec, self.lang)


def _localise_ticks(fig, lang: str) -> None:
    """Marcas numéricas con la convención del idioma: 20.000 en español, 20,000 en inglés; nunca 20000.

    Los años (enteros por debajo de 10.000) se dejan sin separador. Los ejes categóricos —que llevan
    rótulos fijos— y los que ya tienen formateador propio no se tocan.
    """
    from matplotlib.ticker import ScalarFormatter, NullFormatter
    for ax in fig.axes:
        if not ax.axison:
            continue
        for axis, scale in ((ax.xaxis, ax.get_xscale()), (ax.yaxis, ax.get_yscale())):
            if not axis.get_visible():
                continue
            if not isinstance(axis.get_major_formatter(), ScalarFormatter) and scale != "log":
                continue
            if scale == "log":
                # Se ENVUELVE el formateador logarítmico en vez de sustituirlo: quién lleva rótulo y quién
                # no lo decide matplotlib (en un eje que no llega a cubrir una década los rótulos van en las
                # marcas menores), y sustituirlo dejaba el eje de tasas del panel f de E49 sin una sola cifra.
                for kind in ("major", "minor"):
                    inner = (axis.get_major_formatter() if kind == "major" else axis.get_minor_formatter())
                    if isinstance(inner, (NullFormatter, _LocaleLogFormatter)):
                        continue
                    wrapped = _LocaleLogFormatter(inner, lang)
                    if kind == "major":
                        axis.set_major_formatter(wrapped)
                    else:
                        axis.set_minor_formatter(wrapped)
                continue
            lo, hi = sorted(axis.get_view_interval())
            ticks = [t for t in axis.get_majorticklocs() if lo - 1e-9 <= t <= hi + 1e-9]
            if not ticks:
                continue
            axis.set_major_formatter(_LocaleLinFormatter(axis, lang))


def fig_E40(res, geo, variant, lang, fdir) -> str:
    """Mapas comunales de la razón suavizada de episodios y personas GRD (residencia)."""
    plt, fig, S = _plate()
    shapes = geo["plot"]
    vlab = CFG.VARIANTS[variant]["short"][lang]
    eb_e, eb_p = _sr(res, "grd_episodes"), _sr(res, "grd_persons")
    cbar_ratio = f"{tr('smoothed_ratio_short', lang)}; {tr('national_ref', lang)}"
    chile_map(fig, S[0], shapes, eb_e, lang,
              f"{ind_short('grd_episodes', lang)} 2019–2024 — {tr('smoothed_ratio_short', lang)} ({vlab})",
              cmap="RdBu_r", center=1.0, cbar_label=cbar_ratio,
              missing_label=tr("no_data", lang), letter_="A")
    chile_map(fig, S[1], shapes, eb_p, lang,
              f"{ind_short('grd_persons', lang)} 2019–2024 — {tr('smoothed_ratio_short', lang)} ({vlab})",
              cmap="RdBu_r", center=1.0, cbar_label=cbar_ratio, letter_="B")
    rate = _sr(res, "grd_episodes", column="rate_per_100k")
    chile_map(fig, S[2], shapes, rate, lang,
              f"{ind_short('grd_episodes', lang)} — {tr('rate_short', lang)} 2019–2024",
              cmap="YlGnBu", cbar_label=tr("rate_short", lang), letter_="C")
    d = fig.add_subplot(S[3])
    f = res["standardised"]
    f = f[(f.indicator == "grd_episodes") & (f.period == "full")]
    d.scatter(f.expected, f.eb_weight, s=18, color=OK[0], edgecolor="white", linewidth=0.3, zorder=3)
    d.axhline(1.0, color="#444444", ls=":", lw=1)
    d.set_xscale("log")
    d.set_ylim(0, 1.05)
    d.set_xlabel(tr("expected", lang))
    d.set_ylabel(_wrap(tr("shrink", lang), 34))
    d.text(0.02, 0.05, ("Peso 0 = la razón se contrae por completo a la referencia nacional;\n"
                        "peso 1 = la razón cruda se conserva" if lang == "es" else
                        "Weight 0 = the ratio is shrunk entirely to the national reference;\n"
                        "weight 1 = the crude ratio is preserved"),
           transform=d.transAxes, fontsize=7.2, va="bottom", color="#444444")
    _title(d, f"{tr('shrink', lang)}: "
              f"{'media previa' if lang == 'es' else 'prior mean'} = {num(f.prior_mean.iloc[0], 2, lang)}, "
              f"{'varianza previa' if lang == 'es' else 'prior variance'} = {num(f.prior_variance.iloc[0], 3, lang)}")
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    bins = np.linspace(0, max(3.0, float(np.nanquantile(f.sir.replace([np.inf], np.nan).dropna(), 0.99))), 30)
    e.hist(f.sir.replace([np.inf], np.nan).dropna(), bins=bins, color="#bdbdbd", label=tr("crude_ratio", lang))
    e.hist(f.sir_eb.dropna(), bins=bins, color=OK[0], alpha=0.75, label=tr("smoothed_ratio", lang))
    e.axvline(1.0, color="#444444", ls="--", lw=1)
    e.set_xlabel(_wrap(f"{tr('crude_ratio_short', lang)} / {tr('smoothed_ratio_short', lang)}", 40))
    e.set_ylabel(tr("n_comunas", lang))
    _title(e, "Distribución de las razones comunales" if lang == "es"
           else "Distribution of the comuna ratios")
    e_lo, e_hi = e.get_ylim()
    e.set_ylim(e_lo, e_hi * 1.34)                   # banda libre sobre los histogramas para la leyenda
    _legend(e, prefer=("upper right", "upper left"))
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    top = f.sort_values("sir_eb", ascending=False).head(18).iloc[::-1]
    names = res["local"][["cut_comuna", "comuna_name_ine"]].drop_duplicates().set_index("cut_comuna").comuna_name_ine
    ypos = np.arange(len(top))
    g.errorbar(top.sir, ypos, xerr=[top.sir - top.sir_lo, top.sir_hi - top.sir], fmt="o", color="#7f8c8d",
               ms=4, lw=1, label=f"{tr('crude_ratio', lang)} ({tr('ci95', lang)})")
    g.scatter(top.sir_eb, ypos, color=OK[1], s=30, zorder=4, label=tr("smoothed_ratio", lang))
    g.set_yticks(ypos)
    g.set_yticklabels([f"{names.get(c, c)} ({num(o, 0, lang)})" for c, o in zip(top.cut_comuna, top.observed)],
                      fontsize=7.4)
    g.axvline(1.0, color="#444444", ls="--", lw=1)
    g.set_xlabel(_wrap(f"{tr('crude_ratio_short', lang)} / {tr('smoothed_ratio_short', lang)}", 40))
    g.set_title(_wrap_title("18 comunas con mayor razón suavizada (observados entre paréntesis)" if lang == "es"
                      else "18 comunas with the highest smoothed ratio (observed in brackets)"))
    g_lo, g_hi = g.get_xlim()
    g.set_xlim(g_lo, g_hi + 0.46 * (g_hi - g_lo))   # banda libre a la derecha para la leyenda
    _legend(g, fontsize=FS_MIN + 0.4, framealpha=0.95, prefer=("lower right", "upper right"))
    _letter(g, 5)
    return _save(fig, fdir, "E40_maps_grd_smoothed_ratio", plt, lang)


def fig_E41(res, geo, variant, lang, fdir) -> str:
    """Mapas comunales de REM A05 y P2 con la advertencia de lugar de atención."""
    plt, fig, S = _plate()
    shapes = geo["plot"]
    vlab = CFG.VARIANTS[variant]["short"][lang]
    warn = f"⚠ {tr('care_warning', lang)}"
    chile_map(fig, S[0], shapes, _sr(res, "a05_entries"), lang,
              f"{ind_short('a05_entries', lang)} 2021–2025 — {tr('smoothed_ratio_short', lang)} ({vlab}) ⚠",
              cmap="RdBu_r", center=1.0, cbar_label=tr("smoothed_ratio_short", lang),
              missing_label=tr("no_report", lang), letter_="A")
    chile_map(fig, S[1], shapes, _sr(res, "p2_stock"), lang,
              f"{ind_short('p2_stock', lang)} 2019–2025 — {tr('smoothed_ratio_short', lang)} ⚠",
              cmap="RdBu_r", center=1.0, cbar_label=tr("smoothed_ratio_short", lang), letter_="B")
    chile_map(fig, S[2], shapes, _sr(res, "a05_entries", column="rate_per_100k"), lang,
              f"{ind_short('a05_entries', lang)} — {tr('rate_short', lang)} ⚠",
              cmap="YlOrRd", cbar_label=tr("rate_short", lang), letter_="C")

    d = fig.add_subplot(S[3])
    est = res["rem_establishments"]
    last = est[(est.indicator == "a05_entries")].year.max()
    e_last = est[(est.indicator == "a05_entries") & (est.year == last)].set_index("cut_comuna").n_establishments
    counts = res["counts"]
    n_rep = counts[(counts.indicator == "a05_entries") & counts.reported].groupby("year").cut_comuna.nunique()
    d.bar(n_rep.index.astype(str), n_rep.values, color=OK[1])
    for x, v in zip(range(len(n_rep)), n_rep.values):
        d.text(x, v, num(v, 0, lang), ha="center", va="bottom", fontsize=7.5)
    d.set_xlabel(tr("year", lang))
    d.set_ylabel(tr("reporting_comunas", lang))
    d.set_title(_wrap_title("Comunas con al menos un establecimiento que reporta A05" if lang == "es"
                      else "Comunas with at least one establishment reporting A05"))
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    both = pd.DataFrame({"a05": _sr(res, "a05_entries"), "p2": _sr(res, "p2_stock")}).dropna()
    e.scatter(both.a05, both.p2, s=18, color=OK[2], alpha=0.8, edgecolor="white", linewidth=0.3)
    rho = spearman_ci(both.a05.values, both.p2.values)
    e.set_xlabel(_wrap(f"{ind_short('a05_entries', lang)} — {tr('smoothed_ratio_short', lang)}", 34))
    e.set_ylabel(_wrap(f"{ind_short('p2_stock', lang)} — {tr('smoothed_ratio_short', lang)}", 30))
    e.set_title(_wrap_title(_spear_text(rho, lang)))
    e.axhline(1, color="#999999", ls=":", lw=0.9)
    e.axvline(1, color="#999999", ls=":", lw=0.9)
    e.text(0.98, 0.02, _wrap(warn, 34), transform=e.transAxes, ha="right", va="bottom",
           fontsize=FS_MIN, color="#8b0000", linespacing=1.25)
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    ypos = np.arange(len(e_last.sort_values().tail(18)))
    top = e_last.sort_values().tail(18)
    names = res["local"][["cut_comuna", "comuna_name_ine"]].drop_duplicates().set_index("cut_comuna").comuna_name_ine
    g.barh(ypos, top.values, color=OK[4])
    g.set_yticks(ypos)
    g.set_yticklabels([names.get(c, c) for c in top.index], fontsize=7.4)
    g.set_xlabel("Establecimientos que reportan A05" if lang == "es" else "Establishments reporting A05")
    g.set_title(_wrap_title(("Comunas con más establecimientos reportantes de A05" if lang == "es"
                       else "Comunas with the most establishments reporting A05") + f" ({last})"))
    _letter(g, 5)
    return _save(fig, fdir, "E41_maps_rem_place_of_care", plt, lang)


def fig_E42(res, geo, variant, lang, fdir) -> str:
    """LISA y Gi* del indicador principal y del indicador REM, con el recuento de clases.

    REDISEÑO (fase 4c). La versión anterior apilaba tres mapas —cada uno con sus tres franjas y su
    propia leyenda— en una fila de una lámina apaisada que después se encogía: nueve mapas de 20 mm de
    ancho, ilegibles. Ahora cada mapa ocupa un panel entero de la página vertical (a, b, c) y no lleva
    leyenda propia; la clave de clases, con el recuento de cada mapa, se imprime una sola vez en el
    panel f. Los dos recuentos por clase que antes ocupaban dos paneles en escala logarítmica —donde la
    barra de «no significativo» aplastaba a las demás— se funden en el panel d, que muestra sólo las
    clases significativas en escala lineal; el recuento de «no significativo» queda en el panel f y en
    la tabla acompañante.
    """
    plt, fig, S = _plate()
    shapes = geo["plot"]
    L = res["local"]
    es = lang == "es"

    def cls(ind, col):
        return L[L.indicator == ind].set_index("cut_comuna")[col]

    maps = [(0, "grd_episodes", "lisa_class", f"{tr('lisa_short', lang)} — {ind_short('grd_episodes', lang)}"),
            (1, "grd_episodes", "gi_class", f"{tr('gistar_short', lang)} — {ind_short('grd_episodes', lang)}"),
            (2, "a05_entries", "lisa_class",
             f"{tr('lisa_short', lang)} — {ind_short('a05_entries', lang)} ⚠")]
    for slot, ind, col, title in maps:
        chile_map_classes(fig, S[slot], shapes, cls(ind, col), lang, title,
                          letter_=PANEL_LETTERS[slot], legend=False)

    # --- d: comunas por clase significativa, LISA y Gi*, escala lineal --------------------------
    d = fig.add_subplot(S[3])
    inds = LOCAL_INDICATORS
    sig_cls = [("lisa_class", "HH"), ("lisa_class", "LL"), ("lisa_class", "HL"), ("lisa_class", "LH"),
               ("gi_class", "hot"), ("gi_class", "cold")]
    width = 0.82 / len(sig_cls)
    x = np.arange(len(inds))
    for k, (col, cl) in enumerate(sig_cls):
        vals = [int((L[L.indicator == i][col] == cl).sum()) for i in inds]
        prefix = tr("lisa_short", lang) if col == "lisa_class" else tr("gistar_short", lang)
        d.bar(x + k * width, vals, width=width, color=CLASS_COLOURS[cl], edgecolor="#555555", linewidth=0.3,
              label=f"{prefix} {CLASS_LABEL[cl][0 if es else 1]}")
        for xi, v in zip(x + k * width, vals):
            if v:
                d.text(xi, v, num(v, 0, lang), ha="center", va="bottom", fontsize=FS_MIN)
    d.set_xticks(x + 0.41 - width / 2)
    d.set_xticklabels([_wrap(ind_short(i, lang), 12) for i in inds], fontsize=FS_MIN + 0.4)
    d.set_ylabel(tr("n_comunas", lang))
    d_lo, d_hi = d.get_ylim()
    d.set_ylim(0, d_hi * 1.42)                      # banda libre para la leyenda de seis clases
    d.legend(fontsize=FS_MIN, ncol=2, loc="upper right", framealpha=0.95)
    _title(d, ("Comunas por clase significativa (BH q < 0,05); «no significativo» no se dibuja"
               if es else "Comunas per significant class (BH q < 0.05); 'not significant' is not drawn"))
    _letter(d, 3)

    # --- e: región de las comunas LISA significativas del indicador principal -------------------
    e = fig.add_subplot(S[4])
    order_cls = ["HH", "LL", "HL", "LH"]
    sig = L[(L.indicator == "grd_episodes") & (L.lisa_class != "ns")]
    if len(sig):
        tab = sig.groupby(["region_name", "lisa_class"]).size().unstack(fill_value=0)
        bottom = np.zeros(len(tab))
        for cl in [c for c in order_cls if c in tab.columns]:
            e.barh(np.arange(len(tab)), tab[cl].values, left=bottom, color=CLASS_COLOURS[cl],
                   label=CLASS_LABEL[cl][0 if es else 1], edgecolor="#555555", linewidth=0.3)
            bottom = bottom + tab[cl].values
        e.set_yticks(np.arange(len(tab)))
        e.set_yticklabels([_abbrev(str(i), 18) for i in tab.index], fontsize=FS_MIN + 0.4)
        e.set_xlim(0, float(bottom.max()) * 1.55)   # banda libre a la derecha para la leyenda
        e.legend(fontsize=FS_MIN, loc="lower right", framealpha=0.95)
    else:
        e.text(0.5, 0.5, ("Ninguna comuna alcanza el umbral de Benjamini–Hochberg" if es
                          else "No comuna reaches the Benjamini–Hochberg threshold"),
               transform=e.transAxes, ha="center", va="center", fontsize=FS_BASE)
        e.set_yticks([])
    e.set_xlabel(tr("n_comunas", lang))
    _title(e, ("Región de las comunas LISA significativas (GRD)" if es
               else "Region of the LISA-significant comunas (GRD)"))
    _letter(e, 4)

    # --- f: clave de clases, recuentos por mapa y advertencias ----------------------------------
    from matplotlib.patches import Patch
    g = fig.add_subplot(S[5])
    g.set_axis_off()
    key_order = ["HH", "LL", "HL", "LH", "hot", "cold", "ns"]
    handles = [Patch(facecolor=CLASS_COLOURS[k], edgecolor="#666666",
                     label=CLASS_LABEL[k][0 if es else 1]) for k in key_order]
    key_legend = g.legend(handles=handles, loc="upper left", bbox_to_anchor=(0.0, 1.0), ncol=2,
                          fontsize=FS_MIN + 0.6, frameon=False,
                          title=("Clase local" if es else "Local class"), title_fontsize=FS_MIN + 0.8,
                          alignment="left")
    rows = []
    for slot, ind, col, title in maps:
        counts = L[L.indicator == ind][col].value_counts()
        parts = ", ".join(f"{CLASS_LABEL[k][0 if es else 1]} {num(counts.get(k, 0), 0, lang)}"
                          for k in key_order if k in counts.index)
        # La referencia cruzada dentro del bloque de clave lleva la MISMA letra que el panel al que
        # remite: «(a)», no «a)».
        rows.append(f"{C.plate_panel_letter(PANEL_LETTERS[slot])} {title.replace(' ⚠', '')}: {parts}")
    body = "\n".join(_wrap(r, 52) for r in rows)
    # Los bloques se colocan BAJO la leyenda ya medida (`_place_key_blocks`): con alturas escritas a mano
    # la leyenda española —más larga y más alta— caía sobre la advertencia ⚠.
    blocks = [(body, "#333333", FS_MIN + 0.4),
              (_wrap(f"⚠ {tr('care_warning', lang)}", 52), "#8b0000", FS_MIN + 0.4),
              (_wrap(("Sólo se colorean las comunas que superan el umbral de Benjamini–Hochberg "
                      f"(q = {num(FDR_Q, 2, lang)}); las demás son «no significativo», nunca ausencia de dato."
                      if es else
                      "Only comunas passing the Benjamini–Hochberg threshold "
                      f"(q = {FDR_Q}) are coloured; the rest are 'not significant', never missing data."), 52),
               "#555555", FS_MIN + 0.4)]
    _key_blocks(g, key_legend, blocks)
    _title(g, "Clave de clases y recuentos" if es else "Class key and counts")
    _letter(g, 5)
    return _save(fig, fdir, "E42_lisa_gistar_maps", plt, lang)


def fig_E43(res, geo, variant, lang, fdir) -> str:
    """Diagramas de Moran y sensibilidad de la I a la definición de pesos."""
    plt, fig, S = _plate()
    L = res["local"]
    M = res["moran"]

    def scatter(ax, ind, letter_):
        sub = L[L.indicator == ind]
        row = M[(M.scope == "comuna") & (M.indicator == ind) & (M.value_type == "sir_eb") &
                (M.weights == "queen") & (M.years == "full period") & (M.subset == "all comunas")]
        ax.scatter(sub.z_value, sub.spatial_lag_z, s=16, color=OK[0], alpha=0.75, edgecolor="white", linewidth=0.3)
        b = np.polyfit(sub.z_value, sub.spatial_lag_z, 1)
        xs = np.linspace(sub.z_value.min(), sub.z_value.max(), 20)
        ax.plot(xs, np.polyval(b, xs), color="#c0392b", lw=1.6)
        ax.axhline(0, color="#999999", lw=0.8)
        ax.axvline(0, color="#999999", lw=0.8)
        ax.set_xlabel(tr("value_z", lang))
        ax.set_ylabel(tr("lag", lang))
        i_val = row.morans_i.iloc[0] if len(row) else np.nan
        p_val = row.p_sim.iloc[0] if len(row) else np.nan
        ax.set_title(_wrap_title(f"{ind_short(ind, lang)} — {tr('morans_i', lang)} = {num(i_val, 3, lang)}, "
                           f"p ({PERMUTATIONS}) = {fmt_p(p_val, lang)}"))
        _letter(ax, letter_)

    scatter(fig.add_subplot(S[0]), "grd_episodes", "A")
    scatter(fig.add_subplot(S[1]), "a05_entries", "B")

    c = fig.add_subplot(S[2])
    row = M[(M.scope == "comuna") & (M.indicator == MAIN) & (M.value_type == "sir_eb") & (M.weights == "queen") &
            (M.years == "full period") & (M.subset == "all comunas")].iloc[0]
    xs = np.linspace(row.sim_mean - 4 * row.sim_sd, max(row.sim_mean + 4 * row.sim_sd, row.morans_i * 1.1), 200)
    c.plot(xs, stats.norm.pdf(xs, row.sim_mean, row.sim_sd), color=OK[0], lw=1.6,
           label=tr("permutation", lang))
    c.fill_between(xs, stats.norm.pdf(xs, row.sim_mean, row.sim_sd), color=OK[0], alpha=0.18)
    c.axvline(row.morans_i, color="#c0392b", lw=2, label=f"{tr('morans_i', lang)} = {num(row.morans_i, 3, lang)}")
    c.axvline(row.expected_i, color="#444444", ls="--", lw=1, label=f"E[I] = {num(row.expected_i, 3, lang)}")
    c.set_xlabel(tr("morans_i", lang))
    c.set_ylabel("Densidad" if lang == "es" else "Density")
    c.set_title(_wrap_title(f"{ind_short(MAIN, lang)}: p ({PERMUTATIONS}) = {fmt_p(row.p_sim, lang)}; "
                      f"p {'analítico' if lang == 'es' else 'analytic'} = {fmt_p(row.p_norm, lang)}", 48),
                fontsize=9.2)
    _legend(c, fontsize=7.4, prefer=("upper left", "upper right"))
    _letter(c, 2)

    d = fig.add_subplot(S[3])
    wnames = ["queen", "knn4", "knn8", "idw"]
    types = ["rate_per_100k", "sir", "sir_eb"]
    tlab = {"rate_per_100k": tr("rate_short", lang), "sir": tr("crude_ratio_short", lang),
            "sir_eb": tr("smoothed_ratio_short", lang)}
    top_bar = 0.0
    for k, vt in enumerate(types):
        vals = [float(M[(M.scope == "comuna") & (M.indicator == MAIN) & (M.value_type == vt) & (M.weights == w) &
                        (M.years == "full period") & (M.subset == "all comunas")].morans_i.iloc[0]) for w in wnames]
        top_bar = max(top_bar, max(vals))
        d.bar(np.arange(len(wnames)) + k * 0.26, vals, width=0.26, color=OK[k], label=tlab[vt])
    d.set_ylim(0, top_bar * 1.45)          # banda superior libre: la leyenda nunca tapa la barra más alta
    d.set_xticks(np.arange(len(wnames)) + 0.26)
    d.set_xticklabels([weights_label(w, lang) for w in wnames], fontsize=8)
    d.set_ylabel(tr("morans_i", lang))
    d.set_xlabel(tr("weights", lang))
    d.set_title(_wrap_title("Sensibilidad de la I de Moran a los pesos (GRD episodios)" if lang == "es"
                      else "Sensitivity of Moran's I to the weight definition (GRD episodes)"))
    _legend(d, fontsize=FS_MIN + 0.4, framealpha=0.95, prefer=("upper right", "upper left"))
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    sub = M[(M.scope == "comuna") & (M.value_type == "sir_eb") & (M.weights == "queen") &
            (M.years == "full period") & (M.subset == "all comunas") & M.indicator.isin(COUNT_INDICATORS)]
    sub = sub.sort_values("morans_i")
    colours = [OK[0] if IND[i]["geo"] == "residence" else OK[1] for i in sub.indicator]
    e.barh(np.arange(len(sub)), sub.morans_i, color=colours)
    e.set_yticks(np.arange(len(sub)))
    e.set_yticklabels([f"{ind_short(i, lang)}{'' if IND[i]['geo'] == 'residence' else ' ⚠'}" for i in sub.indicator],
                      fontsize=7.6)
    for y, (i_val, p_val) in enumerate(zip(sub.morans_i, sub.p_sim)):
        _tip_label(e, i_val, y, f"p = {fmt_p(p_val, lang)}", fontsize=6.8)
    e.set_xlabel(tr("morans_i", lang))
    e.set_title(_wrap_title("I de Moran por indicador (razón suavizada, contigüidad reina); ⚠ = lugar de atención"
                      if lang == "es" else
                      "Moran's I by indicator (smoothed ratio, queen contiguity); ⚠ = place of care"))
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    for k, ind in enumerate(LOCAL_INDICATORS):
        # Solo el subconjunto base: las filas de sensibilidad de denominador (base 2017 frente a Censo 2024)
        # duplicarían 2024 y unirían con una línea dos bases de población que nunca se mezclan.
        sub = M[(M.scope == "comuna") & (M.indicator == ind) & (M.value_type == "sir_eb") &
                (M.weights == "queen") & (M.subset == "all comunas") & M.years.str.fullmatch(r"\d{4}")]
        if not len(sub):
            continue
        sub = sub.sort_values("years")
        g.plot(sub.years.astype(int), sub.morans_i, "o-", color=OK[k], label=ind_short(ind, lang), lw=1.6, ms=5)
    C.shade_years(g, CFG.PANDEMIC_YEARS)
    law_marker(g, lang)
    g.axhline(0, color="#444444", ls="--", lw=0.9)
    g.set_xlabel(tr("year", lang))
    g.set_ylabel(tr("morans_i", lang))
    g.set_title(_wrap_title("I de Moran anual de la razón suavizada (sombreado: 2020–2021)" if lang == "es"
                      else "Annual Moran's I of the smoothed ratio (shaded: 2020–2021)"))
    _legend(g, fontsize=7.4, framealpha=0.92, prefer=("lower right", "lower left"))
    _letter(g, 5)
    return _save(fig, fdir, "E43_moran_scatter_weights", plt, lang)


SOURCE_OF = {}
ROLE_OF = {}


def _init_pair_maps():
    SOURCE_OF.update({k: v["source"] for k, v in IND.items()})
    SOURCE_OF.update({k: v["source"] for k, v in CONTEXT.items()})
    ROLE_OF.update({k: v["role"] for k, v in IND.items()})
    ROLE_OF.update({k: v["role"] for k, v in CONTEXT.items()})


_init_pair_maps()


def _cross_system(frame: pd.DataFrame) -> pd.DataFrame:
    """Pares informativos: fuentes distintas y al menos un indicador de resultado (nunca cobertura-cobertura,
    cuya correlación es estructural porque ambos son esencialmente tamaño de población)."""
    keep = [(SOURCE_OF.get(a) != SOURCE_OF.get(b)) and
            (ROLE_OF.get(a) == "outcome" or ROLE_OF.get(b) == "outcome")
            for a, b in zip(frame.indicator_x, frame.indicator_y)]
    return frame[keep]


def _corr_matrix(corr: pd.DataFrame, scope: str, keys: list[str]) -> pd.DataFrame:
    m = pd.DataFrame(np.nan, index=keys, columns=keys, dtype=float)
    sub = corr[corr.scope == scope]
    for r in sub.itertuples():
        if r.indicator_x in m.index and r.indicator_y in m.columns:
            m.loc[r.indicator_x, r.indicator_y] = r.rho
            m.loc[r.indicator_y, r.indicator_x] = r.rho
    np.fill_diagonal(m.values, 1.0)
    return m


#: Ocho indicadores en la matriz de la lámina, uno por sistema y capa: los otros seis son redundantes
#: (personas GRD y episodios GRD correlacionan 0,95; APS, FONASA y FONASA/INE son esencialmente tamaño
#: de población y correlacionan entre sí por encima de 0,95) y con catorce indicadores la celda medía
#: menos de 7 mm, con el coeficiente y las marcas rotadas ilegibles. La MATRIZ COMPLETA de los catorce
#: indicadores, en las dos escalas, se imprime en la tabla acompañante.
MATRIX_INDICATORS = ["grd_episodes", "grd_principal", "a05_entries", "p2_stock", "p6_primary",
                     "rem20_discharges", "sae_multidimensional", "urban_share"]
#: Rótulo mínimo para los ejes de la matriz y para los pares del panel f.
IND_TINY = {
    "grd_episodes": ("GRD F84", "GRD F84"),
    "grd_persons": ("GRD pers.", "GRD pers."),
    "grd_principal": ("GRD princ.", "GRD princ."),
    "a05_entries": ("A05", "A05"),
    "p2_stock": ("P2 dic.", "P2 Dec."),
    "p6_primary": ("P6 APS", "P6 prim."),
    "p6_specialty": ("P6 esp.", "P6 spec."),
    "aps_enrolled": ("APS", "APS"),
    "fonasa_beneficiaries": ("FONASA", "FONASA"),
    "rem20_discharges": ("REM-20", "REM-20"),
    "sae_multidimensional": ("SAE mult.", "SAE mult."),
    "sae_income": ("SAE ingr.", "SAE inc."),
    "urban_share": ("% urbano", "Urban %"),
    "fonasa_share": ("% FONASA", "FONASA %"),
}


def ind_tiny(name: str, lang: str) -> str:
    return IND_TINY.get(name, (name, name))[0 if lang == "es" else 1]


def _heat(fig, slot, mat, lang, title, letter_):
    """Matriz de rho de Spearman con su barra de color, colocada y MEDIDA en `_place_heat`.

    El ancho de celda no se estima con una fórmula sobre el ancho de la página —la estimación daba 8 mm
    donde la celda real medía 5,37 mm, porque el borde izquierdo del panel lo fija el panel de la misma
    columna con los rótulos más largos—: se mide sobre la lámina ya congelada y el coeficiente se degrada
    por escalones (dos decimales → un decimal → sólo color) antes que imprimirse pegado al de la celda
    contigua. La matriz completa de los catorce indicadores está siempre en la tabla acompañante.
    """
    ax = fig.add_subplot(slot)
    im = ax.imshow(mat.values, cmap="RdBu_r", vmin=-1, vmax=1)
    n = len(mat)
    ax.set_xticks(np.arange(n))
    ax.set_yticks(np.arange(n))
    ax.set_xticklabels([ind_tiny(i, lang) for i in mat.index], rotation=55, ha="right",
                       fontsize=FS_MIN + 0.4)
    ax.set_yticklabels([ind_tiny(i, lang) for i in mat.index], fontsize=FS_MIN + 0.4)
    labels = []
    for i in range(n):
        for j in range(n):
            if i == j:
                continue              # la diagonal vale 1 por construcción y sólo roba espacio
            v = mat.values[i, j]
            if np.isfinite(v):
                labels.append((ax.text(j, i, num(v, 2, lang), ha="center", va="center", fontsize=FS_MIN,
                                       color="white" if abs(v) > 0.55 else "#222222"), float(v)))
    # Barra de color estrecha: con la fracción por defecto (0,15 del ancho) la celda de la matriz bajaba
    # todavía más y el coeficiente dejaba de imprimirse.
    cb = fig.colorbar(im, ax=ax, shrink=0.70, pad=0.02, fraction=0.05, aspect=22)
    cb.set_label(tr("spearman", lang), fontsize=FS_MIN + 0.6)
    cb.ax.tick_params(labelsize=FS_MIN + 0.2)
    _title(ax, title)
    ax.grid(False)
    _letter(ax, letter_)
    _HEAT_CELLS.append(dict(slot=slot, ax=ax, cbar=cb, labels=labels, n=n, lang=lang))
    return ax


def fig_E44(res, geo, variant, lang, fdir) -> str:
    """Matriz de correlación entre fuentes sobre comunas y sobre regiones.

    REDISEÑO (fase 4c). Las dos matrices llevaban catorce indicadores con el rótulo completo rotado y el
    coeficiente a 5,4 pt sobre un lienzo que después se encogía: ilegibles. Ahora cada matriz muestra
    OCHO indicadores —uno por sistema y capa— con rótulo mínimo, el coeficiente impreso sólo si la
    celda lo admite, y las dos escalas separadas en los paneles a (comuna) y b (región). La matriz
    completa de los catorce indicadores, en las dos escalas y con IC, p y n, está en la tabla acompañante.
    """
    plt, fig, S = _plate()
    es = lang == "es"
    keys = [k for k in MATRIX_INDICATORS]
    mc = _corr_matrix(res["correlations"], "comuna", keys)
    mr = _corr_matrix(res["correlations"], "region", keys)
    _heat(fig, S[0], mc, lang, f"{tr('comuna', lang)}s (n = {len(geo['order'])})", 0)
    _heat(fig, S[1], mr, lang, ("Regiones (n = 16)" if es else "Regions (n = 16)"), 1)

    c = fig.add_subplot(S[2])
    sub = res["correlations"]
    sub = sub[(sub.scope == "comuna") & ((sub.indicator_x == MAIN) | (sub.indicator_y == MAIN))].copy()
    sub["other"] = np.where(sub.indicator_x == MAIN, sub.indicator_y, sub.indicator_x)
    sub = sub.sort_values("rho")
    ypos = np.arange(len(sub))
    c.errorbar(sub.rho, ypos, xerr=[sub.rho - sub.rho_lo, sub.rho_hi - sub.rho], fmt="o", color=OK[0],
               ms=3.2, lw=1.0)
    c.axvline(0, color="#444444", ls="--", lw=0.9)
    c.set_yticks(ypos)
    c.set_yticklabels([f"{ind_short(o, lang)}{'' if (IND.get(o) or CONTEXT[o])['geo'] == 'residence' else ' ⚠'}"
                       for o in sub.other], fontsize=FS_MIN + 0.4)
    c.set_xlabel(f"{tr('spearman', lang)} ({tr('ci95', lang)} Fisher-z)")
    _title(c, ("Correlación con GRD episodios (razón suavizada)" if es
               else "Correlation with GRD episodes (smoothed ratio)"))
    _letter(c, 2)

    d = fig.add_subplot(S[3])
    merged = res["correlations"].pivot_table(index=["indicator_x", "indicator_y"], columns="scope",
                                             values="rho").dropna()
    d.scatter(merged["comuna"], merged["region"], s=14, color=OK[2], alpha=0.8, edgecolor="white",
              linewidth=0.3)
    d.plot([-1, 1], [-1, 1], color="#444444", ls="--", lw=0.9)
    d.set_xlim(-1, 1)
    d.set_ylim(-1, 1)
    d.set_xlabel(f"{tr('spearman', lang)} — {tr('comuna', lang)}")
    d.set_ylabel(f"{tr('spearman', lang)} — {tr('region', lang)}")
    rho = spearman_ci(merged["comuna"].values, merged["region"].values)
    _title(d, ("Escala comunal frente a escala regional" if es
               else "Comuna scale versus region scale") + f"; {_spear_text(rho, lang)}")
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    cross = _cross_system(res["correlations"][res["correlations"].scope == "comuna"])
    best = cross.reindex(cross.rho.abs().sort_values(ascending=False).index).iloc[0]
    vx = res["value_frames"][f"{best.indicator_x}|{best.value_type_x}"]
    vy = res["value_frames"][f"{best.indicator_y}|{best.value_type_y}"]
    both = pd.DataFrame({"x": vx, "y": vy}).dropna()
    e.scatter(both.x, both.y, s=14, color=OK[1], alpha=0.8, edgecolor="white", linewidth=0.3)
    e.set_xlabel(_wrap(f"{ind_short(best.indicator_x, lang)} — {vtype_short(best.value_type_x, lang)}", 34))
    e.set_ylabel(_wrap(f"{ind_short(best.indicator_y, lang)} — {vtype_short(best.value_type_y, lang)}", 30))
    _title(e, ("Par más fuerte entre sistemas distintos" if es
               else "Strongest pair between different systems")
           + f": {_spear_text(dict(rho=best.rho, rho_lo=best.rho_lo, rho_hi=best.rho_hi, n=best.n), lang)}")
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    n_pairs = 10                      # diez pares: con catorce el rótulo del par no cabía en el panel
    top = cross.reindex(cross.rho.abs().sort_values().index).tail(n_pairs)
    ypos = np.arange(len(top))
    g.errorbar(top.rho, ypos, xerr=[top.rho - top.rho_lo, top.rho_hi - top.rho], fmt="o", color=OK[3],
               ms=3.2, lw=1.0)
    g.axvline(0, color="#444444", ls="--", lw=0.9)
    g.set_yticks(ypos)
    g.set_yticklabels([f"{ind_tiny(x, lang)} – {ind_tiny(y, lang)}"
                       for x, y in zip(top.indicator_x, top.indicator_y)], fontsize=FS_MIN + 0.4)
    g.set_xlabel(f"{tr('spearman', lang)} ({tr('ci95', lang)})")
    _title(g, (f"Los {n_pairs} pares más fuertes entre sistemas distintos (al menos un indicador de resultado)"
               if es else
               f"The {n_pairs} strongest cross-system pairs (at least one outcome indicator)"))
    _letter(g, 5)
    return _save(fig, fdir, "E44_correlation_matrix", plt, lang)


def fig_E45(res, geo, variant, lang, fdir) -> str:
    """Moran bivariada: mapas locales y ordenación de todos los pares."""
    plt, fig, S = _plate()
    shapes = geo["plot"]
    bl = res["bivariate_local"]
    pairs = bl[["indicator_x", "indicator_y"]].drop_duplicates().values.tolist() if len(bl) else []
    for k, (ix, iy) in enumerate(pairs[:2]):
        sub = bl[(bl.indicator_x == ix) & (bl.indicator_y == iy)]
        chile_map_classes(fig, S[k], shapes, sub.set_index("cut_comuna").bv_class, lang,
                          f"{ind_tiny(ix, lang)} → {ind_tiny(iy, lang)}\n"
                          f"I = {num(sub.bv_i_global.iloc[0], 3, lang)}, "
                          f"p = {fmt_p(sub.bv_p_global.iloc[0], lang)}", letter_="AB"[k])
    c = fig.add_subplot(S[2])
    B = _cross_system(res["bivariate"].copy())
    B = B.reindex(B.bv_i.abs().sort_values().index).tail(16)
    ypos = np.arange(len(B))
    c.barh(ypos, B.bv_i, color=[OK[0] if v > 0 else OK[1] for v in B.bv_i])
    c.set_yticks(ypos)
    c.set_yticklabels([f"{ind_tiny(a, lang)} → {ind_tiny(b, lang)}"
                       for a, b in zip(B.indicator_x, B.indicator_y)], fontsize=FS_MIN + 0.4)
    # El valor p se anclaba al BORDE del panel, del lado opuesto al signo de la barra: en las seis barras
    # más largas se imprimía sobre el extremo de la propia barra («p = 0,001» sobre la barra) y en las
    # cortas quedaba a media panel de distancia. Ahora va pegado a la PUNTA de su barra, por fuera, y el
    # eje se ensancha después (`_fit_tip_labels`) hasta que el rótulo más largo cabe dentro del panel.
    lim = float(np.nanmax(np.abs(B.bv_i))) * 1.28
    c.set_xlim(-lim, lim)
    for y, (v, p) in enumerate(zip(B.bv_i, B.bv_p_sim)):
        _tip_label(c, v, y, f"p = {fmt_p(p, lang)}", fontsize=FS_MIN + 0.2)
    c.axvline(0, color="#444444", lw=0.9)
    c.set_xlabel(tr("bivariate", lang))
    c.set_title(_wrap_title("I bivariada de los 16 pares más fuertes entre sistemas" if lang == "es"
                      else "Bivariate I of the 16 strongest cross-system pairs"))
    _letter(c, 2)

    for k, (ix, iy) in enumerate(pairs[:2]):
        ax = fig.add_subplot(S[3 + k])
        sub = bl[(bl.indicator_x == ix) & (bl.indicator_y == iy)]
        ax.scatter(sub.x_z, sub.lag_y_z, s=16, color=OK[2], alpha=0.8, edgecolor="white", linewidth=0.3)
        b = np.polyfit(sub.x_z, sub.lag_y_z, 1)
        xs = np.linspace(sub.x_z.min(), sub.x_z.max(), 20)
        ax.plot(xs, np.polyval(b, xs), color="#c0392b", lw=1.6)
        ax.axhline(0, color="#999999", lw=0.8)
        ax.axvline(0, color="#999999", lw=0.8)
        ax.set_xlabel(f"{ind_tiny(ix, lang)} (z)")
        ax.set_ylabel(_wrap(f"{tr('lag', lang)}: {ind_tiny(iy, lang)}", 28))
        _title(ax, f"{tr('bivariate', lang)} = {num(sub.bv_i_global.iloc[0], 3, lang)}")
        _letter(ax, 3 + k)

    g = fig.add_subplot(S[5])
    if len(bl):
        tab = bl.groupby(["indicator_x", "indicator_y", "bv_class"]).size().unstack(fill_value=0)
        labels = [f"{ind_tiny(a, lang)}\n→ {ind_tiny(b, lang)}" for a, b in tab.index]
        bottom = np.zeros(len(tab))
        for cl in [c for c in ["HH", "LL", "HL", "LH"] if c in tab.columns]:
            g.bar(np.arange(len(tab)), tab[cl].values, bottom=bottom, color=CLASS_COLOURS[cl],
                  label=CLASS_LABEL[cl][0 if lang == "es" else 1], edgecolor="#555555", linewidth=0.3)
            bottom = bottom + tab[cl].values
        g.set_xticks(np.arange(len(tab)))
        g.set_xticklabels(labels, fontsize=FS_MIN + 0.4)
        if bottom.max() > 0:
            g.set_ylim(0, float(bottom.max()) * 1.32)   # banda libre sobre las barras para la leyenda
        _legend(g, fontsize=7, framealpha=0.92, prefer=("upper right", "upper left"))
    g.set_ylabel(f"{tr('n_comunas', lang)} ({len(geo['order'])} " +
                 ("en total" if lang == "es" else "in total") + ")")
    g.set_title(_wrap_title("Comunas por clase bivariada local significativa (BH q < 0,05)" if lang == "es"
                      else "Comunas per significant local bivariate class (BH q < 0.05)"))
    _letter(g, 5)
    return _save(fig, fdir, "E45_bivariate_moran", plt, lang)


def fig_E46(res, geo, variant, lang, fdir) -> str:
    """Asociación con la privación comunal estimada por SAE 2024."""
    plt, fig, S = _plate()
    shapes = geo["plot"]
    ctx = res["value_frames"]
    sae_m = ctx.get("sae_multidimensional|value")
    sae_i = ctx.get("sae_income|value")
    reg = res["counts"][["cut_comuna", "cut_region"]].drop_duplicates().set_index("cut_comuna").cut_region

    def scat(ax, y_ind, x_series, xlabel, letter_, title):
        y = _sr(res, y_ind)
        both = pd.DataFrame({"x": x_series, "y": y, "r": reg}).dropna()
        zones = [("Norte" if lang == "es" else "North", BANDS[0]),
                 ("Centro-sur" if lang == "es" else "Centre-south", BANDS[1]),
                 ("Austral" if lang == "es" else "Far south", BANDS[2])]
        for k, (zname, band) in enumerate(zones):
            sel = both[both.r.isin(band)]
            if len(sel):
                ax.scatter(sel.x, sel.y, s=18, color=OK[k], alpha=0.85, edgecolor="white", linewidth=0.25,
                           label=zname)
        _legend(ax, fontsize=7, title=("Macrozona" if lang == "es" else "Macro-zone"), title_fontsize=7,
                prefer=("upper right", "lower right", "upper left"))
        b = np.polyfit(both.x, both.y, 1)
        xs = np.linspace(both.x.min(), both.x.max(), 20)
        ax.plot(xs, np.polyval(b, xs), color="#c0392b", lw=1.6)
        rho = spearman_ci(both.x.values, both.y.values)
        ax.axhline(1, color="#999999", ls=":", lw=0.9)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(_wrap(f"{ind_short(y_ind, lang)} — {tr('smoothed_ratio_short', lang)}", 30))
        ax.set_title(_wrap_title(f"{title}; {_spear_text(rho, lang)}"))
        _letter(ax, letter_)
        return rho

    scat(fig.add_subplot(S[0]), "grd_episodes", sae_m, tr("sae_multi", lang), "A",
         ind_short("grd_episodes", lang))
    scat(fig.add_subplot(S[1]), "grd_episodes", sae_i, tr("sae_income", lang), "B",
         ind_short("grd_episodes", lang))
    chile_map(fig, S[2], shapes, sae_m, lang, tr("sae_multi", lang), cmap="PuBuGn",
              cbar_label=tr("sae_multi", lang), letter_="C")

    d = fig.add_subplot(S[3])
    y = _sr(res, "grd_episodes")
    std = res["standardised"]
    f = std[(std.indicator == "grd_episodes") & (std.period == "full")].set_index("cut_comuna")
    q = pd.qcut(sae_m.reindex(f.index), 5, labels=False)
    rows = []
    for k in range(5):
        m = q == k
        obs, exp = f.observed[m].sum(), f.expected[m].sum()
        lo, hi = poisson_limits([obs], ALPHA)
        rows.append((k + 1, obs / exp if exp else np.nan, lo[0] / exp if exp else np.nan,
                     hi[0] / exp if exp else np.nan, int(m.sum()), float(sae_m.reindex(f.index)[m].mean())))
    qd = pd.DataFrame(rows, columns=["q", "sir", "lo", "hi", "n", "mean_sae"])
    d.bar(qd.q, qd.sir, color=OK[0], yerr=[qd.sir - qd.lo, qd.hi - qd.sir], capsize=3)
    d.axhline(1, color="#444444", ls="--", lw=1)
    d.set_xticks(qd.q)
    # El sufijo del porcentaje lo pone `pct`, que mira el idioma: «10,1 %» en español y «10.1%» en inglés.
    # Escrito a mano, este rótulo imprimía el espacio castellano también dentro de la lámina inglesa, que en
    # la misma cara escribe «95% CI» pegado.
    d.set_xticklabels([f"Q{int(k)}\n{pct(m, lang, 1)}" for k, m in zip(qd.q, qd.mean_sae)], fontsize=7.6)
    d.set_xlabel(_wrap(f"{tr('quintile', lang)} ({tr('sae_multi', lang)})", 40))
    d.set_ylabel(tr("crude_ratio", lang))
    d.set_title(_wrap_title("Razón agregada por quintil de privación (IC 95 % exacto de Poisson)" if lang == "es"
                      else "Pooled ratio by deprivation quintile (exact Poisson 95% CI)"))
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    rows = []
    for ind in COUNT_INDICATORS:
        for ctx_key, lab in (("sae_multidimensional", tr("sae_multi", lang)), ("sae_income", tr("sae_income", lang))):
            sub = res["correlations"]
            sel = sub[(sub.scope == "comuna") &
                      (((sub.indicator_x == ind) & (sub.indicator_y == ctx_key)) |
                       ((sub.indicator_y == ind) & (sub.indicator_x == ctx_key)))]
            if len(sel):
                rows.append((ind, ctx_key, float(sel.rho.iloc[0]), float(sel.rho_lo.iloc[0]), float(sel.rho_hi.iloc[0])))
    fr = pd.DataFrame(rows, columns=["ind", "ctx", "rho", "lo", "hi"])
    for k, ctx_key in enumerate(["sae_multidimensional", "sae_income"]):
        s = fr[fr.ctx == ctx_key]
        ypos = np.arange(len(s)) + k * 0.32
        # Rótulo CORTO en la leyenda: con el nombre completo («Pobreza multidimensional comunal, %
        # (SAE 2024)») la leyenda medía dos líneas de ancho de panel, tapaba entera la fila de REM-20
        # egresos —estimación e intervalo— y se cortaba contra el borde derecho. El nombre completo está
        # en el rótulo del eje X de los paneles (a) y (b) y en la leyenda de la lámina.
        e.errorbar(s.rho, ypos, xerr=[s.rho - s.lo, s.hi - s.rho], fmt="o", color=OK[k], ms=4, lw=1.1,
                   label=ind_short("sae_multidimensional", lang) if k == 0 else ind_short("sae_income", lang))
    n_rows = len(fr[fr.ctx == "sae_multidimensional"])
    e.set_yticks(np.arange(n_rows) + 0.16)
    e.set_yticklabels([ind_short(i, lang) for i in fr[fr.ctx == "sae_multidimensional"].ind], fontsize=7.4)
    e.axvline(0, color="#444444", ls="--", lw=0.9)
    e.set_ylim(-0.7, n_rows - 1 + 0.32 + 0.7)   # una fila de respiro; la leyenda la coloca `_place_legends`
    e.set_xlabel(f"{tr('spearman', lang)} ({tr('ci95', lang)})")
    e.set_title(_wrap_title("Correlación de cada indicador con la privación SAE" if lang == "es"
                      else "Correlation of each indicator with SAE deprivation"))
    _legend(e, fontsize=7.2, framealpha=0.92, prefer=("upper right", "upper left"))
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    scat(g, "grd_episodes", ctx.get("urban_share|value"),
         ("Población urbana, %" if lang == "es" else "Urban population, %"), "F",
         ("Urbanidad" if lang == "es" else "Urbanicity"))
    return _save(fig, fdir, "E46_sae_deprivation", plt, lang)


def fig_E47(res, geo, variant, lang, fdir) -> str:
    """Curvas de Lorenz, Gini, descomposición de Theil y razón de deciles."""
    plt, fig, S = _plate()
    counts = res["counts"]
    region_of = counts[["cut_comuna", "cut_region"]].drop_duplicates().set_index("cut_comuna").cut_region

    def lorenz_panel(ax, ind, letter_):
        years = PERIODS[ind]["full"]
        for k, y in enumerate(years):
            sub = counts[(counts.indicator == ind) & (counts.year == y)]
            lz = lorenz_gini(sub["count"].values, sub.population.values)
            ax.plot(lz["x"], lz["y"], color=OK[k % len(OK)], lw=1.5,
                    label=f"{y} (G = {num(lz['gini'], 3, lang)})")
        ax.plot([0, 1], [0, 1], color="#444444", ls="--", lw=1)
        ax.set_xlabel(tr("cum_pop", lang))
        ax.set_ylabel(tr("cum_events", lang))
        ax.set_title(_wrap_title(f"{tr('lorenz', lang)} — {ind_short(ind, lang)}"))
        _legend(ax, fontsize=6.8, prefer=("upper left", "lower right"))
        _letter(ax, letter_)

    lorenz_panel(fig.add_subplot(S[0]), "grd_episodes", "A")
    lorenz_panel(fig.add_subplot(S[1]), "a05_entries", "B")

    c = fig.add_subplot(S[2])
    I = res["inequality"]
    for k, ind in enumerate(["grd_episodes", "grd_persons", "a05_entries", "p2_stock", "p6_primary"]):
        sub = I[(I.indicator == ind) & I.years.str.fullmatch(r"\d{4}")].sort_values("years")
        c.plot(sub.years.astype(int), sub.gini, "o-", color=OK[k], lw=1.5, ms=5,
               label=f"{ind_short(ind, lang)}{'' if IND[ind]['geo'] == 'residence' else ' ⚠'}")
    C.shade_years(c, CFG.PANDEMIC_YEARS)
    law_marker(c, lang)
    c.set_xlabel(tr("year", lang))
    c.set_ylabel(tr("gini", lang))
    c.set_title(_wrap_title("Gini de la distribución territorial por fuente y año" if lang == "es"
                      else "Gini of the territorial distribution by source and year"))
    _legend(c, fontsize=7, prefer=("lower left", "upper left", "lower right"))
    _letter(c, 2)

    d = fig.add_subplot(S[3])
    sub = I[(I.indicator == "grd_episodes") & I.years.str.fullmatch(r"\d{4}")].sort_values("years")
    x = np.arange(len(sub))
    d.bar(x, sub.theil_between, color=OK[0], label=tr("between", lang))
    d.bar(x, sub.theil_within, bottom=sub.theil_between, color=OK[4], label=tr("within", lang))
    d.set_xticks(x)
    d.set_xticklabels(sub.years, fontsize=8)
    d.set_ylabel(tr("theil", lang))
    d.set_title(_wrap_title("Theil de GRD episodios: entre y dentro de regiones" if lang == "es"
                      else "Theil of GRD episodes: between and within regions"))
    _legend(d, fontsize=7.4, prefer=("upper right", "upper left"))
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    sub = I[(I.indicator == "a05_entries") & I.years.str.fullmatch(r"\d{4}")].sort_values("years")
    x = np.arange(len(sub))
    e.bar(x, sub.theil_between, color=OK[0], label=tr("between", lang))
    e.bar(x, sub.theil_within, bottom=sub.theil_between, color=OK[4], label=tr("within", lang))
    e.set_xticks(x)
    e.set_xticklabels(sub.years, fontsize=8)
    e.set_ylabel(tr("theil", lang))
    e.set_title(_wrap_title("Theil de REM A05 (⚠ lugar de atención)" if lang == "es"
                      else "Theil of REM A05 (⚠ place of care)"))
    _legend(e, fontsize=7.4, prefer=("upper right", "upper left"))
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    for k, ind in enumerate(["grd_episodes", "a05_entries", "p2_stock"]):
        sub = I[(I.indicator == ind) & I.years.str.fullmatch(r"\d{4}")].sort_values("years")
        g.plot(sub.years.astype(int), sub.decile_ratio_comunas_with_events, "o-", color=OK[k], lw=1.5, ms=5,
               label=ind_short(ind, lang))
    g.set_yscale("log")
    g.set_xlabel(tr("year", lang))
    g.set_ylabel(tr("decile_ratio", lang))
    C.shade_years(g, CFG.PANDEMIC_YEARS)
    law_marker(g, lang)
    g.set_title(_wrap_title("Razón de deciles (solo comunas con al menos un evento)" if lang == "es"
                      else "Decile ratio (comunas with at least one event only)"))
    _legend(g, fontsize=7.4, prefer=("lower left", "upper left"))
    _letter(g, 5)
    return _save(fig, fdir, "E47_lorenz_theil", plt, lang)


def fig_E48(res, geo, variant, lang, fdir) -> str:
    """Estabilidad del orden comunal entre años y entre los dos periodos."""
    plt, fig, S = _plate()
    STAB = res["stability"]
    a = fig.add_subplot(S[0])
    for k, ind in enumerate(["grd_episodes", "grd_persons", "a05_entries", "p2_stock", "p6_primary"]):
        sub = STAB[(STAB.indicator == ind) & (STAB.basis == "rate per 100,000")]
        if not len(sub):
            continue
        x = [int(c.split(" vs ")[1]) for c in sub.comparison]
        a.plot(x, sub.rho, "o-", color=OK[k], lw=1.5, ms=5,
               label=f"{ind_short(ind, lang)}{'' if IND[ind]['geo'] == 'residence' else ' ⚠'}")
    a.set_xlabel(tr("year", lang))
    a.set_ylabel(tr("spearman", lang))
    a.set_ylim(0, 1)
    a.set_title(_wrap_title("Correlación de rangos comunales entre años sucesivos" if lang == "es"
                      else "Spearman between comuna ranks in successive years"))
    _legend(a, fontsize=7, prefer=("lower left", "lower right"))
    _letter(a, 0)

    def early_late(ax, ind, letter_):
        e = res["standardised"]
        early = e[(e.indicator == ind) & (e.period == "early")].set_index("cut_comuna")
        late = e[(e.indicator == ind) & (e.period == "late")].set_index("cut_comuna")
        both = pd.DataFrame({"e": early.sir_eb, "l": late.sir_eb}).dropna()
        ax.scatter(both.e, both.l, s=18, color=OK[1], alpha=0.8, edgecolor="white", linewidth=0.3)
        lim = [0, max(both.e.max(), both.l.max()) * 1.05]
        ax.plot(lim, lim, color="#444444", ls="--", lw=1)
        rho = spearman_ci(both.e.values, both.l.values)
        # Se reparte en dos líneas: el rótulo completo en español desborda el borde derecho de la lámina.
        ax.set_xlabel(_wrap(f"{tr('smoothed_ratio_short', lang)} {yspan(early.years.iloc[0])}", 30))
        ax.set_ylabel(_wrap(f"{tr('smoothed_ratio_short', lang)} {yspan(late.years.iloc[0])}", 30))
        ax.set_title(_wrap_title(f"{ind_short(ind, lang)}; {_spear_text(rho, lang)}"))
        _letter(ax, letter_)

    early_late(fig.add_subplot(S[1]), "grd_episodes", "B")
    early_late(fig.add_subplot(S[2]), "a05_entries", "C")

    d = fig.add_subplot(S[3])
    M = res["moran"]
    for k, ind in enumerate(LOCAL_INDICATORS):
        # Igual que en E43-F: las filas de sensibilidad de denominador quedan fuera de la serie anual.
        sub = M[(M.scope == "comuna") & (M.indicator == ind) & (M.value_type == "sir_eb") &
                (M.weights == "queen") & (M.subset == "all comunas") &
                M.years.str.fullmatch(r"\d{4}")].sort_values("years")
        if len(sub):
            d.plot(sub.years.astype(int), sub.morans_i, "o-", color=OK[k], lw=1.5, ms=5,
                   label=ind_short(ind, lang))
    C.shade_years(d, CFG.PANDEMIC_YEARS)
    law_marker(d, lang)
    d.set_xlabel(tr("year", lang))
    d.set_ylabel(tr("morans_i", lang))
    d.set_title(_wrap_title("I de Moran anual (razón suavizada)" if lang == "es"
                      else "Annual Moran's I (smoothed ratio)"))
    _legend(d, fontsize=7, framealpha=0.92, prefer=("lower right", "lower left"))
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    sub = STAB[STAB.basis.str.contains("Bayes")].sort_values("rho")
    ypos = np.arange(len(sub))
    e.errorbar(sub.rho, ypos, xerr=[sub.rho - sub.rho_lo, sub.rho_hi - sub.rho], fmt="o", color=OK[0], ms=4, lw=1.2)
    e.set_yticks(ypos)
    e.set_yticklabels([f"{ind_short(i, lang)} ({yspan(c)})" for i, c in zip(sub.indicator, sub.comparison)],
                      fontsize=6.8)
    e.set_xlabel(f"{tr('spearman', lang)} ({tr('ci95', lang)})")
    e.set_xlim(0, 1)
    e.set_title(_wrap_title("Estabilidad entre periodos por fuente" if lang == "es"
                      else "Between-period stability by source"))
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    st = res["standardised"]
    early = st[(st.indicator == "grd_episodes") & (st.period == "early")].set_index("cut_comuna")
    late = st[(st.indicator == "grd_episodes") & (st.period == "late")].set_index("cut_comuna")
    both = pd.DataFrame({"e": early.sir_eb, "l": late.sir_eb}).dropna()
    shift = (both.l.rank() - both.e.rank()).abs()
    g.hist(shift, bins=25, color=OK[2])
    g.axvline(shift.median(), color="#c0392b", lw=1.6,
              label=("mediana" if lang == "es" else "median") + f" = {num(shift.median(), 0, lang)}")
    g.set_xlabel(("Cambio absoluto de rango comunal" if lang == "es" else "Absolute change in comuna rank"))
    g.set_ylabel(tr("n_comunas", lang))
    g.set_title(_wrap_title("Desplazamiento de rangos entre periodos (GRD episodios)" if lang == "es"
                      else "Rank displacement between periods (GRD episodes)"))
    _legend(g, fontsize=7.4, prefer=("upper right", "center right"))
    _letter(g, 5)
    return _save(fig, fdir, "E48_rank_stability", plt, lang)


def fig_E49(res, geo, variant, lang, fdir) -> str:
    """Resumen a escala regional: tasas, razones e intervalos."""
    plt, fig, S = _plate()
    R = res["regions"]
    rshapes = geo["regions"]
    grd = R[(R.indicator == "grd_episodes")].set_index("cut_region")
    a05 = R[(R.indicator == "a05_entries")].set_index("cut_region")
    chile_map(fig, S[0], rshapes, grd.sir_eb, lang,
              f"{ind_short('grd_episodes', lang)} — {tr('smoothed_ratio_short', lang)} ({tr('region', lang)})",
              cmap="RdBu_r", center=1.0, cbar_label=tr("smoothed_ratio_short", lang), key="cut_region",
              letter_="A")
    chile_map(fig, S[1], rshapes, a05.sir_eb, lang,
              f"{ind_short('a05_entries', lang)} — {tr('smoothed_ratio_short', lang)} ⚠",
              cmap="RdBu_r", center=1.0, cbar_label=tr("smoothed_ratio_short", lang), key="cut_region",
              letter_="B")
    c = fig.add_subplot(S[2])
    g = grd.reindex(REGION_ORDER).dropna(subset=["rate_per_100k"])
    ypos = np.arange(len(g))[::-1]
    c.errorbar(g.rate_per_100k, ypos, xerr=[g.rate_per_100k - g.rate_lo, g.rate_hi - g.rate_per_100k],
               fmt="o", color=OK[0], ms=4.5, lw=1.2)
    c.set_yticks(ypos)
    c.set_yticklabels([f"{REGION_NAMES.get(r, r)} ({num(o, 0, lang)})" for r, o in zip(g.index, g.observed)],
                      fontsize=7.4)
    c.set_xlabel(f"{tr('rate', lang)} ({tr('ci95', lang)})")
    c.set_title(_wrap_title("Tasa regional de episodios GRD con F84, 2019–2024 (observados)" if lang == "es"
                      else "Regional rate of GRD episodes with F84, 2019–2024 (observed)"))
    _letter(c, 2)

    d = fig.add_subplot(S[3])
    a = a05.reindex(REGION_ORDER).dropna(subset=["rate_per_100k"])
    ypos = np.arange(len(a))[::-1]
    d.errorbar(a.rate_per_100k, ypos, xerr=[a.rate_per_100k - a.rate_lo, a.rate_hi - a.rate_per_100k],
               fmt="o", color=OK[1], ms=4.5, lw=1.2)
    d.set_yticks(ypos)
    d.set_yticklabels([f"{REGION_NAMES.get(r, r)} ({num(o, 0, lang)})" for r, o in zip(a.index, a.observed)],
                      fontsize=7.4)
    d.set_xlabel(f"{tr('rate', lang)} ({tr('ci95', lang)})")
    d.set_title(_wrap_title("Tasa regional de ingresos A05, 2021–2025 ⚠ lugar de atención" if lang == "es"
                      else "Regional rate of A05 entries, 2021–2025 ⚠ place of care"))
    _letter(d, 3)

    e = fig.add_subplot(S[4])
    M = res["moran"]
    sub = M[(M.scope == "region") & (M.value_type.isin(["sir_eb", "value"]))].copy()
    sub = sub.sort_values("morans_i")
    e.barh(np.arange(len(sub)), sub.morans_i, color=[OK[0] if v > 0 else OK[1] for v in sub.morans_i])
    e.set_yticks(np.arange(len(sub)))
    e.set_yticklabels([ind_short(i, lang) for i in sub.indicator], fontsize=7)
    for y, (v, p) in enumerate(zip(sub.morans_i, sub.p_sim)):
        _tip_label(e, v, y, f"p = {fmt_p(p, lang)}", fontsize=6.4)
    e.axvline(0, color="#444444", lw=0.9)
    e.set_xlabel(f"{tr('morans_i', lang)} ({tr('region', lang)}, n = 16)")
    e.set_title(_wrap_title("I de Moran a escala regional" if lang == "es" else "Moran's I at the regional scale", 46),
                fontsize=9.2)
    _letter(e, 4)

    g = fig.add_subplot(S[5])
    both = pd.DataFrame({"grd": grd.rate_per_100k, "a05": a05.rate_per_100k}).dropna()
    # El marcador se dibuja POR ENCIMA del recuadro translúcido que el motor pone bajo un rótulo cercano:
    # con el marcador debajo, media circunferencia de Magallanes, Coquimbo y Los Ríos quedaba borrada por
    # el fondo del nombre de la región vecina. El disco también se reduce: dieciséis discos de 3 mm en un
    # panel de media página no dejaban sitio para separar los nombres de los puntos.
    g.scatter(both.a05, both.grd, s=38, color=OK[2], edgecolor="white", linewidth=0.4, zorder=7)
    rho = spearman_ci(both.a05.values, both.grd.values)
    g.set_xscale("log")
    g.set_yscale("log")
    # El nombre de cada región se separa de SU marcador y de los nombres ya colocados sobre la lámina
    # ya congelada (`common.plate_value_label`): con los cuatro desplazamientos fijos que se usaban
    # antes, «O'Higgins», «Arica y Parinacota» y «Magallanes» se imprimían encima de su propio punto.
    for r, row in both.sort_values("grd", ascending=False).iterrows():
        # Paso de separación 5,5 pt: con el de omisión (3 pt) el borde del rótulo llegaba al disco del
        # marcador y el recuadro translúcido que el motor le pone encima le borraba media circunferencia.
        _value_label(g, row.a05, row.grd, REGION_NAMES.get(r, str(r)), fontsize=6.8, step_pt=5.5, leader=True)
    g.set_xlabel(_wrap(f"{ind_short('a05_entries', lang)} — {tr('rate_short', lang)}", 34))
    g.set_ylabel(_wrap(f"{ind_short('grd_episodes', lang)} — {tr('rate_short', lang)}", 30))
    g.margins(0.16)
    g.set_title(_wrap_title(_spear_text(rho, lang)))
    g.text(0.02, 0.98, _wrap(f"⚠ {tr('care_warning', lang)}", 32), transform=g.transAxes, ha="left",
           va="top", fontsize=FS_MIN, color="#8b0000", linespacing=1.25)
    _letter(g, 5)
    return _save(fig, fdir, "E49_regional_summary", plt, lang)


FIGURES = {
    "E40_maps_grd_smoothed_ratio": fig_E40,
    "E41_maps_rem_place_of_care": fig_E41,
    "E42_lisa_gistar_maps": fig_E42,
    "E43_moran_scatter_weights": fig_E43,
    "E44_correlation_matrix": fig_E44,
    "E45_bivariate_moran": fig_E45,
    "E46_sae_deprivation": fig_E46,
    "E47_lorenz_theil": fig_E47,
    "E48_rank_stability": fig_E48,
    "E49_regional_summary": fig_E49,
}


# ---------------------------------------------------------------------------
# Leyendas de las láminas (autónomas, bilingües)
# ---------------------------------------------------------------------------
def _sources_note(lang: str) -> str:
    return ("Archivos fuente: outputs/tidy/grd_territory.csv (GRD, comuna de residencia), "
            "outputs/tidy/rem_pathway_tidy.csv (REM A05/P2/P6, comuna del establecimiento), "
            "outputs/tidy/aps_enrolment_comuna_year.csv, outputs/tidy/fonasa_beneficiaries_comuna_year.csv, "
            "outputs/tidy/rem20_establishment_year.csv, outputs/tidy/ine_population_comuna_year_age_sex.csv "
            "(denominador INE base 2017, 30 de junio), SAE_multidimensional_2024.xlsx y SAE_ingresos_2024.xlsx, "
            "proyecciones_comuna_area_urbana_rural_2002_2035_base_2017.csv, data/comunas.shp y data/Regional.shp."
            if lang == "es" else
            "Source files: outputs/tidy/grd_territory.csv (GRD, comuna of residence), "
            "outputs/tidy/rem_pathway_tidy.csv (REM A05/P2/P6, comuna of the establishment), "
            "outputs/tidy/aps_enrolment_comuna_year.csv, outputs/tidy/fonasa_beneficiaries_comuna_year.csv, "
            "outputs/tidy/rem20_establishment_year.csv, outputs/tidy/ine_population_comuna_year_age_sex.csv "
            "(INE base-2017 denominator, 30 June), SAE_multidimensional_2024.xlsx and SAE_ingresos_2024.xlsx, "
            "proyecciones_comuna_area_urbana_rural_2002_2035_base_2017.csv, data/comunas.shp and data/Regional.shp.")


def _methods_note(lang: str, geo: dict) -> str:
    isl = ", ".join(str(i) for i in geo["islands"])
    if lang == "es":
        return (f"Estandarización indirecta interna (razón nacional = 1 por construcción) con las tasas nacionales por "
                f"edad, sexo y año de la misma fuente cuando la fuente publica el desglose; límites exactos de Poisson "
                f"para la razón cruda y suavizado empírico de Bayes de Marshall. Contigüidad reina estandarizada por "
                f"filas sobre {len(geo['order'])} comunas (las no continentales {sorted(geo['non_continental'])} se "
                f"excluyen del grafo y se conservan en las tablas; las comunas sin vecino reina —{isl}— se enlazan a su "
                f"vecino más próximo). Inferencia por {PERMUTATIONS} permutaciones con semilla {SEED} y también "
                f"analítica; los indicadores locales usan el umbral de Benjamini–Hochberg con q = {num(FDR_Q, 2, lang)}. "
                f"Celdas con menos de {SUPPRESSION_THRESHOLD} eventos suprimidas en las tablas territoriales.")
    return (f"Internal indirect standardisation (national ratio = 1 by construction) using the national age-, sex- and "
            f"year-specific rates of the same source where the source publishes the breakdown; exact Poisson limits for "
            f"the crude ratio and Marshall's empirical-Bayes smoother. Row-standardised queen contiguity over "
            f"{len(geo['order'])} comunas (the non-continental ones {sorted(geo['non_continental'])} are excluded from "
            f"the graph and kept in the tables; comunas with no queen neighbour —{isl}— are linked to their nearest "
            f"neighbour). Inference from {PERMUTATIONS} permutations with seed {SEED} and analytically; local "
            f"indicators use the Benjamini–Hochberg threshold at q = {FDR_Q}. Cells with fewer than "
            f"{SUPPRESSION_THRESHOLD} events are suppressed in territorial tables.")


#: Paneles cuyo NUMERADOR se localiza en la comuna del establecimiento que reporta (lugar de atención).
#: La advertencia de compatibilidad se pega sólo a las leyendas que tienen alguno, y nombra cuáles son.
#: Pegada sin condición a las diez leyendas, la Figura E40 declaraba en (c) que numerador y denominador
#: son COMPATIBLES —GRD por comuna de residencia, que es justo lo que ese panel cartografía— y cerraba
#: avisando de que el numerador se localiza en el establecimiento que reporta: dos afirmaciones
#: contrarias sobre el mismo panel, en la misma leyenda.
CARE_PANELS = {
    "E40_maps_grd_smoothed_ratio": (),                       # los seis paneles son GRD por RESIDENCIA
    "E41_maps_rem_place_of_care": ("a", "b", "c", "d", "e", "f"),
    "E42_lisa_gistar_maps": ("c", "d", "f"),                 # (a, b, e) son GRD por residencia
    "E43_moran_scatter_weights": ("b", "e", "f"),            # (a, c, d) son GRD por residencia
    "E44_correlation_matrix": ("a", "b", "c", "d", "e", "f"),
    "E45_bivariate_moran": ("a", "b", "c", "d", "e", "f"),
    "E46_sae_deprivation": ("e",),                           # (a–d, f) son GRD y contexto por residencia
    "E47_lorenz_theil": ("b", "c", "e", "f"),                # (a, d) son GRD por residencia
    "E48_rank_stability": ("a", "c", "d", "e"),              # (b, f) son GRD por residencia
    "E49_regional_summary": ("b", "d", "e", "f"),            # (a, c) son GRD por residencia
}


def _panel_list(letters, lang: str) -> str:
    """«a los paneles (b), (c) y (f)» / «to panels (b), (c) and (f)», con la convención de la lámina.

    Devuelve el complemento entero, con su preposición, para que el español contraiga («al panel (e)»)."""
    items = [f"({c})" for c in letters]
    if not items:
        return ""
    if len(items) >= PLATE_MAX_PANELS:
        return "a todos los paneles de esta lámina" if lang == "es" else "to every panel of this plate"
    if len(items) == 1:
        return (f"al panel {items[0]}" if lang == "es" else f"to panel {items[0]}")
    joined = ", ".join(items[:-1]) + (" y " if lang == "es" else " and ") + items[-1]
    return (f"a los paneles {joined}" if lang == "es" else f"to panels {joined}")


def _care_note(fig_key: str, lang: str) -> str:
    """Advertencia de compatibilidad numerador/denominador, ATADA a los paneles que la necesitan."""
    where = _panel_list(CARE_PANELS.get(fig_key, ()), lang)
    if not where:
        return ""
    return (f"La advertencia de compatibilidad se aplica {where}: {WARN_CARE[lang]}" if lang == "es"
            else f"The compatibility warning applies {where}: {WARN_CARE[lang]}")


def _grd_f84_total(variant: str, default: int) -> int:
    """Total de episodios con F84 documentado 2019–2024 de la variante, leído de la tabla tidy del módulo 01.

    Es la misma cifra que imprimen la Figura 1 y su tabla de recuentos; se lee para poder declarar en la
    leyenda cuántos episodios quedan fuera del análisis territorial por no tener comuna enlazable."""
    try:
        ys = C.read_tidy("grd_year_summary")
        sel = ys[(ys.variant == variant) & (ys.panel == "observed") & (ys.activity == "all") & (ys.position == "any")]
        return int(sel.n_episodes_f84.sum())
    except Exception:
        return int(default)


def captions(res, geo, variant, lang) -> dict:
    """Leyendas autónomas: unidad, denominador, cobertura, era de definición, N reportante y archivo fuente."""
    v = CFG.VARIANTS[variant]["label"][lang]
    M = res["moran"]
    row = M[(M.scope == "comuna") & (M.indicator == MAIN) & (M.value_type == "sir_eb") & (M.weights == "queen") &
            (M.years == "full period") & (M.subset == "all comunas")].iloc[0]
    counts = res["counts"]
    n_grd = int(counts[(counts.indicator == "grd_episodes")]["count"].sum())
    # Los episodios del análisis territorial son los que llevan una comuna de residencia enlazable al
    # padrón: dos de los 25.620 episodios con F84 documentado de 2019–2024 no la llevan y quedan fuera.
    # Sin decirlo, la lámina y las tablas imprimen 25.618 y la Figura 1 y su tabla de recuentos 25.620,
    # y las dos cifras del mismo hecho se leen como una contradicción.
    n_grd_total = _grd_f84_total(variant, n_grd)
    n_grd_lost = max(0, n_grd_total - n_grd)
    lost_txt = ("" if not n_grd_lost else
                (f" de los {num(n_grd_total, 0, lang)} episodios con F84 documentado del período; los {n_grd_lost} restantes "
                 f"no llevan una comuna de residencia enlazable al padrón y quedan fuera del análisis territorial"
                 if lang == "es" else
                 f" of the {num(n_grd_total, 0, lang)} episodes with documented F84 in the period; the remaining {n_grd_lost} "
                 f"carry no comuna of residence that links to the register and are outside the territorial analysis"))
    n_a05 = int(counts[(counts.indicator == "a05_entries")]["count"].sum())
    n_p2 = int(counts[(counts.indicator == "p2_stock") & (counts.year == max(YEARS_P2))]["count"].sum())
    a05_comunas = int(counts[(counts.indicator == "a05_entries") & counts.reported].cut_comuna.nunique())
    head = f"{NOT_PREVALENCE[lang]} {WARN_ECOLOGICAL[lang]}"
    tail = f"{_methods_note(lang, geo)} {_sources_note(lang)}"

    def common_for(fig_key: str) -> str:
        """Cierre de la leyenda: la advertencia de lugar de atención sólo si algún panel la necesita."""
        care = _care_note(fig_key, lang)
        return f"{head} {care} {tail}" if care else f"{head} {tail}"

    es = lang == "es"
    out = {}

    common = common_for("E40_maps_grd_smoothed_ratio")
    out["E40_maps_grd_smoothed_ratio"] = dict(
        title=(f"Distribución territorial del reconocimiento hospitalario del autismo por comuna de residencia, "
               f"Chile 2019–2024 — {v}" if es else
               f"Territorial distribution of hospital recognition of autism by comuna of residence, Chile 2019–2024 "
               f"— {v}"),
        caption=((f"(a, b) Razón estandarizada suavizada (Bayes empírico de Marshall) de los episodios GRD con F84 "
                  f"documentado y de las personas únicas dentro del año, comuna de residencia, acumulado 2019–2024 "
                  f"(n = {num(n_grd, 0, lang)} episodios{lost_txt}); la escala está centrada en 1, la referencia nacional. (c) Tasa cruda por "
                  f"100.000 habitantes-año (denominador INE base 2017 por comuna de residencia; numerador y denominador "
                  f"COMPATIBLES). (d) Contracción del suavizado frente a los casos esperados. (e) Distribución de las "
                  f"razones cruda y suavizada. (f) Dieciocho comunas con la razón suavizada más alta, con la razón "
                  f"cruda y su IC 95 % exacto de Poisson y los episodios observados entre paréntesis. Panel anual "
                  f"observado del GRD (65, 65, 65, 65, 68 y 72 hospitales en 2019–2024). " + common)
                 if es else
                 (f"(a, b) Empirical-Bayes (Marshall) smoothed standardised ratio of GRD episodes with documented F84 "
                  f"and of unique persons within year, by comuna of residence, pooled 2019–2024 (n = {num(n_grd, 0, lang)} "
                  f"episodes{lost_txt}); the scale is centred on 1, the national reference. (c) Crude rate per 100,000 "
                  f"person-years (INE base-2017 denominator by comuna of residence; numerator and denominator are "
                  f"COMPATIBLE). (d) Shrinkage of the smoother against expected counts. (e) Distribution of the crude "
                  f"and smoothed ratios. (f) Eighteen comunas with the highest smoothed ratio, with the crude ratio and "
                  f"its exact Poisson 95% CI and the observed episodes in brackets. Observed annual GRD panel (65, 65, "
                  f"65, 65, 68 and 72 hospitals in 2019–2024). " + common)))

    common = common_for("E41_maps_rem_place_of_care")
    out["E41_maps_rem_place_of_care"] = dict(
        title=(f"Distribución territorial de los indicadores REM de autismo por comuna del establecimiento, "
               f"Chile 2019–2025 — {v}" if es else
               f"Territorial distribution of the REM autism indicators by comuna of the establishment, Chile 2019–2025 "
               f"— {v}"),
        caption=((f"(a) Ingresos A05 por la familia TGD, era de definición 2021–2025 (n = {num(n_a05, 0, lang)} "
                  f"ingresos; {a05_comunas} comunas con al menos un año informado). (b) Población bajo control NANEAS "
                  f"con TEA en diciembre, código único P2500500, 2019–2025 (stock; {num(n_p2, 0, lang)} personas en "
                  f"{max(YEARS_P2)}). (c) Tasa cruda A05 por 100.000 habitantes-año. (d) Comunas con al menos un "
                  f"establecimiento que reporta A05, por año. (e) Razón suavizada A05 frente a P2. (f) Comunas con más "
                  f"establecimientos reportantes. Los stocks (P2) y los flujos (A05) nunca comparten eje ni se suman. "
                  + common)
                 if es else
                 (f"(a) A05 entries for the PDD family, definition era 2021–2025 (n = {num(n_a05, 0, lang)} entries; "
                  f"{a05_comunas} comunas with at "
                  f"least one reported year). (b) December NANEAS population under control with ASD, single code "
                  f"P2500500, 2019–2025 (stock; {num(n_p2, 0, lang)} persons in {max(YEARS_P2)}). (c) Crude A05 rate per 100,000 "
                  f"person-years. (d) Comunas with at least one establishment reporting A05, by year. (e) A05 smoothed "
                  f"ratio against P2. (f) Comunas with the most reporting establishments. Stocks (P2) and flows (A05) "
                  f"never share an axis and are never summed. " + common)))

    lisa_counts = res["local"][res["local"].indicator == MAIN].lisa_class.value_counts().to_dict()
    gi_counts = res["local"][res["local"].indicator == MAIN].gi_class.value_counts().to_dict()
    common = common_for("E42_lisa_gistar_maps")
    out["E42_lisa_gistar_maps"] = dict(
        title=(f"Agrupamientos locales del reconocimiento administrativo del autismo: LISA y Gi*, Chile — {v}" if es
               else f"Local clusters of administrative recognition of autism: LISA and Gi*, Chile — {v}"),
        caption=((f"(a, b) LISA y Gi* de Getis–Ord de la razón suavizada de los episodios GRD con F84 documentado "
                  f"(comuna de residencia): {lisa_counts.get('HH', 0)} comunas alto–alto, {lisa_counts.get('LL', 0)} "
                  f"bajo–bajo, {lisa_counts.get('HL', 0)} alto–bajo y {lisa_counts.get('LH', 0)} bajo–alto en el LISA; "
                  f"{gi_counts.get('hot', 0)} puntos calientes y {gi_counts.get('cold', 0)} fríos en el Gi*. "
                  f"(c) LISA de los ingresos A05, marcado ⚠. (d) Comunas por clase significativa e indicador, en "
                  f"escala lineal; el recuento de "
                  f"«no significativo» está en el panel f y en la tabla acompañante. (e) Región de las comunas LISA "
                  f"significativas del indicador principal. (f) Clave de clases, recuentos de cada mapa y umbral. "
                  f"Solo se colorean las comunas que superan el umbral de Benjamini–Hochberg "
                  f"(q = {num(FDR_Q, 2, lang)}); las demás quedan como «no significativo», nunca como ausencia de dato. " + common)
                 if es else
                 (f"(a, b) LISA and Getis–Ord Gi* of the smoothed ratio of GRD episodes with documented F84 (comuna of "
                  f"residence): {lisa_counts.get('HH', 0)} high–high, {lisa_counts.get('LL', 0)} low–low, "
                  f"{lisa_counts.get('HL', 0)} high–low and {lisa_counts.get('LH', 0)} low–high comunas in the LISA; "
                  f"{gi_counts.get('hot', 0)} hot and {gi_counts.get('cold', 0)} cold spots in the Gi*. (c) LISA of A05 "
                  f"entries, marked ⚠. (d) Comunas per "
                  f"significant class and indicator on a linear scale; the 'not significant' count is in panel f and in "
                  f"the companion table. (e) Region of the LISA-significant comunas of the main indicator. (f) Class "
                  f"key, per-map counts and threshold. Only comunas passing the Benjamini–Hochberg threshold "
                  f"(q = {FDR_Q}) are coloured; the rest are 'not significant', never missing data. " + common)))

    common = common_for("E43_moran_scatter_weights")
    out["E43_moran_scatter_weights"] = dict(
        title=(f"Autocorrelación espacial global y su sensibilidad a la definición de pesos, Chile — {v}" if es else
               f"Global spatial autocorrelation and its sensitivity to the weight definition, Chile — {v}"),
        caption=((f"(a, b) Diagramas de Moran de la razón suavizada (valor estandarizado frente a su rezago espacial) "
                  f"con contigüidad reina. (c) Distribución de referencia de {PERMUTATIONS} permutaciones con semilla "
                  f"{SEED} para los episodios GRD: I = {num(row.morans_i, 3, lang)}, p de permutación = "
                  f"{fmt_p(row.p_sim, lang)}, p analítico = {fmt_p(row.p_norm, lang)}, E[I] = "
                  f"{num(row.expected_i, 3, lang)}. (d) I de Moran con contigüidad reina, k = 4, k = 8 y distancia "
                  f"inversa, para la tasa, la razón cruda y la razón suavizada. (e) I por indicador; ⚠ marca los "
                  f"indicadores cuyo numerador es el lugar de atención. (f) I anual de la razón suavizada; el sombreado "
                  f"marca 2020–2021 como disrupción del reporte, no como efecto. " + common)
                 if es else
                 (f"(a, b) Moran scatterplots of the smoothed ratio (standardised value against its spatial lag) with "
                  f"queen contiguity. (c) Reference distribution of {PERMUTATIONS} permutations with seed {SEED} for "
                  f"GRD episodes: I = {num(row.morans_i, 3, lang)}, permutation p = {fmt_p(row.p_sim, lang)}, analytic "
                  f"p = {fmt_p(row.p_norm, lang)}, E[I] = {num(row.expected_i, 3, lang)}. (d) Moran's I with queen "
                  f"contiguity, k = 4, k = 8 and inverse-distance weights, for the rate, the crude ratio and the "
                  f"smoothed ratio. (e) I by indicator; ⚠ marks indicators whose numerator is the place of care. "
                  f"(f) Annual I of the smoothed ratio; shading marks 2020–2021 as reporting disruption, not as an "
                  f"effect. " + common)))

    common = common_for("E44_correlation_matrix")
    out["E44_correlation_matrix"] = dict(
        title=(f"Correlación territorial entre los sistemas administrativos, comunas y regiones — {v}" if es else
               f"Territorial correlation between the administrative systems, comunas and regions — {v}"),
        caption=((f"(a, b) Matriz de rho de Spearman entre las razones suavizadas sobre comunas y sobre regiones, con "
                  f"{spelled(len(MATRIX_INDICATORS), lang, upper=True)} indicadores —uno por sistema y capa— para que "
                  f"el coeficiente sea legible; la matriz completa de los {spelled(len(ALL_INDICATORS), lang)} "
                  f"indicadores, en las dos escalas y con IC, p y n, está en la tabla acompañante. "
                  f"(c) Correlación de cada indicador con los episodios "
                  f"GRD, con IC 95 % de Fisher-z. (d) Comparación de la correlación en las dos escalas: las "
                  f"correlaciones regionales son sistemáticamente distintas, lo que ilustra el problema de la unidad "
                  f"areal modificable. (e) Par más fuerte entre sistemas distintos. (f) Diez pares más fuertes entre "
                  f"sistemas distintos. " + common)
                 if es else
                 (f"(a, b) Matrix of Spearman's rho between the smoothed ratios over comunas and over regions, with "
                  f"{spelled(len(MATRIX_INDICATORS), lang, upper=True)} indicators — one per system and layer — so "
                  f"that the coefficient is legible; the complete matrix of the "
                  f"{spelled(len(ALL_INDICATORS), lang)} indicators, at both scales and with CI, p and n, is in the "
                  f"companion table. "
                  f"(c) Correlation of each indicator with GRD episodes, "
                  f"with Fisher-z 95% CI. (d) Comparison of the correlation at the two scales: regional correlations "
                  f"differ systematically, illustrating the modifiable areal unit problem. (e) Strongest pair between "
                  f"different systems. (f) Ten strongest cross-system pairs. " + common)))

    bl = res["bivariate_local"]
    # La leyenda promete DOS pares y nombraba uno solo: `bl.iloc[0]` es la primera FILA de la tabla —una
    # comuna del primer par—, no el par. El panel (b) dibuja un segundo par real (con_rett: GRD personas →
    # A05; sin_rett: GRD F84 → P6 APS) que la leyenda no identificaba. Aquí se nombran los dos, en el mismo
    # orden y con la misma selección que hace `fig_E45` al dibujarlos.
    pair_txt = ""
    if len(bl):
        parts = []
        for letter_, (ix, iy) in zip("ab", bl[["indicator_x", "indicator_y"]].drop_duplicates().values.tolist()[:2]):
            sub = bl[(bl.indicator_x == ix) & (bl.indicator_y == iy)]
            parts.append(f"{letter_}: {ind_short(ix, lang)} → {ind_short(iy, lang)} "
                         f"(I = {num(sub.bv_i_global.iloc[0], 3, lang)}, p = {fmt_p(sub.bv_p_global.iloc[0], lang)})")
        pair_txt = "; ".join(parts)
    common = common_for("E45_bivariate_moran")
    out["E45_bivariate_moran"] = dict(
        title=(f"Correlación espacial cruzada entre sistemas: I de Moran bivariada — {v}" if es else
               f"Spatial cross-correlation between systems: bivariate Moran's I — {v}"),
        caption=((f"(a, b) Clasificación local bivariada de los dos pares con mayor |I| entre sistemas distintos "
                  f"({pair_txt}); el valor de la comuna se compara con el rezago espacial del segundo indicador. "
                  f"(c) I bivariada de los dieciséis pares más fuertes con su p de permutación. (d, e) Diagramas "
                  f"bivariados. (f) Comunas por clase local bivariada tras el umbral de Benjamini–Hochberg. La I "
                  f"bivariada es asimétrica: describe la asociación del indicador de la comuna con el entorno del otro "
                  f"indicador, y el orden del par importa. " + common)
                 if es else
                 (f"(a, b) Local bivariate classification of the two cross-system pairs with the largest |I| "
                  f"({pair_txt}); the comuna's value is compared with the spatial lag of the second indicator. "
                  f"(c) Bivariate I of the sixteen strongest pairs with their permutation p. (d, e) Bivariate "
                  f"scatterplots. (f) Comunas per local bivariate class after the Benjamini–Hochberg threshold. "
                  f"Bivariate I is asymmetric: it describes the association of the comuna's indicator with the "
                  f"neighbourhood of the other indicator, and the order of the pair matters. " + common)))

    common = common_for("E46_sae_deprivation")
    out["E46_sae_deprivation"] = dict(
        title=(f"Reconocimiento administrativo del autismo y privación comunal estimada por áreas pequeñas (SAE 2024) "
               f"— {v}" if es else
               f"Administrative recognition of autism and comuna deprivation estimated for small areas (SAE 2024) "
               f"— {v}"),
        caption=((f"(a, b) Razón suavizada de los episodios GRD frente a la pobreza multidimensional y a la pobreza por "
                  f"ingresos comunal (estimaciones SAE 2024 del Ministerio de Desarrollo Social, con su intervalo "
                  f"propio, que no se propaga aquí), coloreadas por región. (c) Mapa de la pobreza multidimensional. "
                  f"(d) Razón agregada por quintil de privación con IC 95 % exacto de Poisson sobre los observados y "
                  f"esperados del quintil. (e) Correlación de cada indicador con las dos medidas de privación. "
                  f"(f) Asociación con el porcentaje de población urbana (proyección INE urbano-rural base 2017). "
                  f"La privación es una covariable de contexto, no un factor de riesgo individual estimado. " + common)
                 if es else
                 (f"(a, b) Smoothed ratio of GRD episodes against comuna multidimensional and income poverty (SAE 2024 "
                  f"estimates of the Ministry of Social Development, with their own interval, which is not propagated "
                  f"here), coloured by region. (c) Map of multidimensional poverty. (d) Pooled ratio by deprivation "
                  f"quintile with exact Poisson 95% CI on the quintile's observed and expected counts. (e) Correlation "
                  f"of each indicator with the two deprivation measures. (f) Association with the urban share of the "
                  f"population (INE base-2017 urban–rural projection). Deprivation is a context covariate, not an "
                  f"estimated individual risk factor. " + common)))

    I = res["inequality"]
    g19 = I[(I.indicator == "grd_episodes") & (I.years == "2019")].gini
    g24 = I[(I.indicator == "grd_episodes") & (I.years == "2024")].gini
    common = common_for("E47_lorenz_theil")
    out["E47_lorenz_theil"] = dict(
        title=(f"Desigualdad territorial de la distribución del reconocimiento administrativo — {v}" if es else
               f"Territorial inequality of the distribution of administrative recognition — {v}"),
        caption=((f"(a, b) Curvas de Lorenz de los eventos frente a la población, con las comunas ordenadas por su tasa "
                  f"(Gini entre paréntesis); el Gini de los episodios GRD pasa de "
                  f"{num(float(g19.iloc[0]) if len(g19) else np.nan, 3, lang)} en 2019 a "
                  f"{num(float(g24.iloc[0]) if len(g24) else np.nan, 3, lang)} en 2024. (c) Gini por fuente y año. "
                  f"(d, e) Índice de Theil descompuesto entre regiones y dentro de las regiones. (f) Razón entre la "
                  f"tasa del decil poblacional superior y la del inferior, calculada solo sobre comunas con al menos un "
                  f"evento porque el decil inferior nacional puede ser íntegramente de comunas con cero. ⚠ marca los "
                  f"indicadores a los que se aplica la advertencia de compatibilidad del final. " + common)
                 if es else
                 (f"(a, b) Lorenz curves of events against population, with comunas ordered by their rate (Gini in "
                  f"brackets); the Gini of GRD episodes moves from "
                  f"{num(float(g19.iloc[0]) if len(g19) else np.nan, 3, lang)} in 2019 to "
                  f"{num(float(g24.iloc[0]) if len(g24) else np.nan, 3, lang)} in 2024. (c) Gini by source and year. "
                  f"(d, e) Theil index decomposed between and within regions. (f) Ratio between the rate of the top and "
                  f"bottom population deciles, computed only over comunas with at least one event because the national "
                  f"bottom decile can consist entirely of comunas with zero. ⚠ marks the indicators to which the "
                  f"compatibility warning at the end applies. " + common)))

    common = common_for("E48_rank_stability")
    out["E48_rank_stability"] = dict(
        title=(f"Estabilidad temporal de la distribución territorial — {v}" if es else
               f"Temporal stability of the territorial distribution — {v}"),
        caption=((f"(a) Rho de Spearman entre los rangos comunales de años sucesivos, por fuente. (b, c) Razón suavizada "
                  f"del periodo temprano frente al tardío, con la correlación y su IC 95 % de Fisher-z; las eras de "
                  f"definición no se cruzan (A05 solo 2021–2025). (d) I de Moran anual. (e) Estabilidad entre periodos "
                  f"por fuente. (f) Distribución del cambio absoluto de rango comunal entre los dos periodos del "
                  f"indicador principal. " + common)
                 if es else
                 (f"(a) Spearman's rho between comuna ranks in successive years, by source. (b, c) Smoothed ratio of "
                  f"the early against the late period, with the correlation and its Fisher-z 95% CI; definition eras "
                  f"are never crossed (A05 covers 2021–2025 only). (d) Annual Moran's I. (e) Between-period stability "
                  f"by source. (f) Distribution of the absolute change in comuna rank between the two periods of the "
                  f"main indicator. " + common)))

    common = common_for("E49_regional_summary")
    out["E49_regional_summary"] = dict(
        title=(f"Resumen a escala regional: tasas, razones estandarizadas e intervalos — {v}" if es else
               f"Regional-scale summary: rates, standardised ratios and intervals — {v}"),
        caption=((f"(a, b) Razón suavizada por región para los episodios GRD (residencia) y los ingresos A05 (⚠ lugar de "
                  f"atención). (c, d) Tasa regional por 100.000 habitantes-año con IC 95 % exacto de Poisson y los "
                  f"eventos observados entre paréntesis. (e) I de Moran a escala regional (16 unidades; la inferencia "
                  f"con n = 16 es poco potente y se informa como tal). (f) Comparación regional entre las dos fuentes "
                  f"en escala logarítmica; nunca se calcula un cociente entre ellas. " + common)
                 if es else
                 (f"(a, b) Smoothed ratio by region for GRD episodes (residence) and A05 entries (⚠ place of care). "
                  f"(c, d) Regional rate per 100,000 person-years with exact Poisson 95% CI and the observed events in "
                  f"brackets. (e) Moran's I at the regional scale (16 units; inference with n = 16 has little power and "
                  f"is reported as such). (f) Regional comparison of the two sources on a log scale; no ratio between "
                  f"them is ever computed. " + common)))
    return out


# ---------------------------------------------------------------------------
# Tablas formateadas del suplemento (extra/tables)
# ---------------------------------------------------------------------------
def merge_json(path: Path, new: dict) -> None:
    """Fusiona con el JSON existente sin borrar las entradas de otros módulos."""
    current: dict = {}
    if path.is_file():
        try:
            current = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            current = {}
    if not isinstance(current, dict):
        current = {}
    current.update(new)
    C.atomic_write_json(current, path)


def out_dir(variant: str, lang: str, kind: str) -> Path:
    p = CFG.OUT / variant / lang / "extra" / kind
    p.mkdir(parents=True, exist_ok=True)
    return p


def _count_display(n, lang):
    """Supresión de celdas territoriales con menos de 5 eventos."""
    if n is None or pd.isna(n):
        return NE[lang]
    return "<5" if 0 < float(n) < SUPPRESSION_THRESHOLD else num(n, 0, lang)


def build_tables(res, geo, base, variant, lang) -> tuple[list[str], dict]:
    """Doce tablas (E40–E51) formateadas por idioma más su compañera numérica."""
    tdir = out_dir(variant, lang, "tables")
    written: list[str] = []
    titles: dict = {}
    v = CFG.VARIANTS[variant]["label"][lang]
    note_common = (f"{NOT_PREVALENCE[lang]} {WARN_ECOLOGICAL[lang]} {WARN_CARE[lang]} "
                   f"{_methods_note(lang, geo)} {_sources_note(lang)}")
    #: Una tabla cuyo numerador está TODO por comuna de residencia declara su denominador COMPATIBLE; pegarle
    #: además la advertencia de lugar de atención hacía que la misma nota se contradijera (leído en la Tabla S92
    #: de los ocho documentos largos). La advertencia va sólo donde hay algún numerador localizado por atención.
    note_residence = (f"{NOT_PREVALENCE[lang]} {WARN_ECOLOGICAL[lang]} "
                      f"{_methods_note(lang, geo)} {_sources_note(lang)}")
    cw = base["crosswalk"].set_index("cut_comuna")
    es = lang == "es"

    def add(name, formatted, numeric, title, note):
        written.append(str(C.atomic_write_csv(formatted, tdir / f"{name}.csv", encoding="utf-8-sig")))
        written.append(str(C.atomic_write_csv(numeric, tdir / f"{name}_numeric.csv")))
        titles[name] = {"title": title, "note": note}

    def comuna_cols(df):
        return pd.DataFrame({
            tr("comuna", lang): [cw.comuna_name_ine.get(c, str(c)) for c in df.cut_comuna],
            "CUT": df.cut_comuna.astype(int).astype(str),
            tr("region", lang): [REGION_NAMES.get(cw.cut_region.get(c), "") for c in df.cut_comuna],
        })

    # --- E40 ------------------------------------------------------------------------------------
    std = res["standardised"]
    f = std[(std.indicator == "grd_episodes") & (std.period == "full")].sort_values("sir_eb", ascending=False)
    p = std[(std.indicator == "grd_persons") & (std.period == "full")].set_index("cut_comuna")
    fmt = comuna_cols(f)
    fmt[("Episodios observados" if es else "Observed episodes")] = [_count_display(x, lang) for x in f.observed]
    fmt[("Esperados" if es else "Expected")] = [num(x, 1, lang) for x in f.expected]
    fmt[("Habitantes-año" if es else "Person-years")] = [num(x, 0, lang) for x in f.person_years]
    fmt[tr("rate", lang)] = [f"{num(r, 1, lang)} ({ci(lo, hi, 1, lang)})"
                             for r, lo, hi in zip(f.rate_per_100k, f.rate_lo, f.rate_hi)]
    fmt[tr("crude_ratio", lang)] = [f"{num(r, 2, lang)} ({ci(lo, hi, 2, lang)})"
                                    for r, lo, hi in zip(f.sir, f.sir_lo, f.sir_hi)]
    fmt[tr("smoothed_ratio", lang)] = [num(x, 2, lang) for x in f.sir_eb]
    fmt[tr("shrink", lang)] = [num(x, 2, lang) for x in f.eb_weight]
    fmt[("Personas GRD (razón suavizada)" if es else "GRD persons (smoothed ratio)")] = [
        num(p.sir_eb.get(c), 2, lang) for c in f.cut_comuna]
    add("E40_grd_smoothed_ratio_comuna", fmt, f,
        (f"Episodios GRD con F84 documentado por comuna de residencia: observados, esperados, tasa y razones "
         f"estandarizadas, Chile 2019–2024 — {v}" if es else
         f"GRD episodes with documented F84 by comuna of residence: observed, expected, rate and standardised ratios, "
         f"Chile 2019–2024 — {v}"),
        ((f"Unidad: episodios GRD con F84 documentado en cualquier posición, acumulados 2019–2024, panel anual "
          f"observado. Denominador: habitantes-año de la proyección INE base 2017 por comuna de RESIDENCIA "
          f"(COMPATIBLE con el numerador). Cobertura: {len(f)} comunas del universo poblacional. Era de definición: "
          f"CIE-10 F84 en DIAGNOSTICO1..35. N reportante: {num(int(f.observed.sum()), 0, lang)} episodios. " + note_residence)
         if es else
         (f"Unit: GRD episodes with documented F84 in any position, pooled 2019–2024, observed annual panel. "
          f"Denominator: person-years of the INE base-2017 projection by comuna of RESIDENCE (COMPATIBLE with the "
          f"numerator). Coverage: {len(f)} comunas of the population universe. Definition era: ICD-10 F84 in "
          f"DIAGNOSTICO1..35. Reporting N: {num(int(f.observed.sum()), 0, lang)} episodes. " + note_residence)))

    # --- E41 ------------------------------------------------------------------------------------
    a = std[(std.indicator == "a05_entries") & (std.period == "full")].set_index("cut_comuna")
    p2 = std[(std.indicator == "p2_stock") & (std.period == "full")].set_index("cut_comuna")
    p6 = std[(std.indicator == "p6_primary") & (std.period == "full")].set_index("cut_comuna")
    est = res["rem_establishments"]
    est_last = est[(est.indicator == "a05_entries") & (est.year == est[est.indicator == "a05_entries"].year.max())]
    est_last = est_last.set_index("cut_comuna").n_establishments
    order_c = a.sort_values("sir_eb", ascending=False).index
    fmt = comuna_cols(pd.DataFrame({"cut_comuna": order_c}))
    fmt[("A05 ingresos" if es else "A05 entries")] = [_count_display(a.observed.get(c), lang) for c in order_c]
    fmt[("A05 razón suavizada" if es else "A05 smoothed ratio")] = [num(a.sir_eb.get(c), 2, lang) for c in order_c]
    fmt[("Establecimientos A05" if es else "A05 establishments")] = [num(est_last.get(c, 0), 0, lang) for c in order_c]
    fmt[("P2 diciembre" if es else "P2 December")] = [_count_display(p2.observed.get(c), lang) for c in order_c]
    fmt[("P2 razón suavizada" if es else "P2 smoothed ratio")] = [num(p2.sir_eb.get(c), 2, lang) for c in order_c]
    fmt[("P6 APS" if es else "P6 primary")] = [_count_display(p6.observed.get(c), lang) for c in order_c]
    fmt[("P6 razón suavizada" if es else "P6 smoothed ratio")] = [num(p6.sir_eb.get(c), 2, lang) for c in order_c]
    fmt[("Estado del dato A05" if es else "A05 data state")] = [
        (tr("no_report", lang) if a.never_reported.get(c, True) else ("informado" if es else "reported"))
        for c in order_c]
    numeric = std[std.indicator.isin(["a05_entries", "p2_stock", "p6_primary", "p6_specialty"]) &
                  (std.period == "full")]
    add("E41_rem_comuna_place_of_care", fmt, numeric,
        (f"Indicadores REM de autismo por comuna del establecimiento: A05, P2 y P6, Chile 2019–2025 — {v}" if es else
         f"REM autism indicators by comuna of the establishment: A05, P2 and P6, Chile 2019–2025 — {v}"),
        ((f"Unidad: ingresos A05 (flujo, era 2021–2025), personas bajo control P2 y P6 "
          f"en diciembre (stock; junio es sensibilidad y nunca se suma). Denominador: habitantes-año INE base 2017 de "
          f"la comuna, NO COMPATIBLE con el numerador. Cobertura: {int((~a.never_reported).sum())} comunas con al menos "
          f"un año informado de A05. Eras de definición: A05 autismo/TGD desagregado desde 2021 (el TGD amplio "
          f"2019–2020 no se une con esta serie); P2500500 es código único 2019–2025; P6 desagregado desde 2021. "
          f"N reportante: {num(int(a.observed.sum()), 0, lang)} ingresos A05 y {num(int(p2.observed.sum()), 0, lang)} personas-año P2. "
          + note_common)
         if es else
         (f"Unit: A05 entries (flow, era 2021–2025), P2 and P6 December population under "
          f"control (stock; June is a sensitivity and is never summed). Denominator: INE base-2017 person-years of the "
          f"comuna, NOT COMPATIBLE with the numerator. Coverage: {int((~a.never_reported).sum())} comunas with at least "
          f"one reported A05 year. Definition eras: disaggregated A05 autism/PDD from 2021 (the 2019–2020 broad PDD "
          f"series is never joined to it); P2500500 is a single code 2019–2025; P6 disaggregated from 2021. Reporting "
          f"N: {num(int(a.observed.sum()), 0, lang)} A05 entries and {num(int(p2.observed.sum()), 0, lang)} P2 person-years. " + note_common)))

    # --- E42 ------------------------------------------------------------------------------------
    L = res["local"]
    rows = []
    for ind in LOCAL_INDICATORS:
        s = L[L.indicator == ind]
        rows.append({
            tr("indicator", lang): ind_short(ind, lang) + ("" if IND[ind]["geo"] == "residence" else " ⚠"),
            "LISA HH": num(int((s.lisa_class == "HH").sum()), 0, lang),
            "LISA LL": num(int((s.lisa_class == "LL").sum()), 0, lang),
            "LISA HL": num(int((s.lisa_class == "HL").sum()), 0, lang),
            "LISA LH": num(int((s.lisa_class == "LH").sum()), 0, lang),
            ("LISA no significativo" if es else "LISA not significant"): num(int((s.lisa_class == "ns").sum()), 0, lang),
            ("LISA p crítico BH" if es else "LISA BH critical p"): num(float(s.lisa_bh_critical_p.iloc[0]), 4, lang),
            ("Gi* calientes" if es else "Gi* hot"): num(int((s.gi_class == "hot").sum()), 0, lang),
            ("Gi* fríos" if es else "Gi* cold"): num(int((s.gi_class == "cold").sum()), 0, lang),
            ("Gi* p crítico BH" if es else "Gi* BH critical p"): num(float(s.gi_bh_critical_p.iloc[0]), 4, lang),
        })
    add("E42_local_class_counts", pd.DataFrame(rows), L,
        (f"Comunas por clase de los indicadores locales (LISA y Gi*) y umbral de Benjamini–Hochberg — {v}" if es else
         f"Comunas per class of the local indicators (LISA and Gi*) and Benjamini–Hochberg threshold — {v}"),
        ((f"Unidad: comunas clasificadas por el LISA (cuadrante alto–alto, bajo–bajo, alto–bajo, bajo–alto) y por el "
          f"Gi* de Getis–Ord (punto caliente o frío) de la razón estandarizada suavizada. Denominador: "
          f"{len(geo['order'])} comunas del grafo de contigüidad. Cobertura: {', '.join(ind_short(i, lang) for i in LOCAL_INDICATORS)}. "
          f"N reportante: cada indicador declara su propio N en E40 y E41. " + note_common)
         if es else
         (f"Unit: comunas classified by the LISA (high–high, low–low, high–low, low–high quadrant) and by the Getis–Ord "
          f"Gi* (hot or cold spot) of the smoothed standardised ratio. Denominator: {len(geo['order'])} comunas of the "
          f"contiguity graph. Coverage: {', '.join(ind_short(i, lang) for i in LOCAL_INDICATORS)}. Reporting N: each "
          f"indicator declares its own N in E40 and E41. " + note_common)))

    # --- E43 ------------------------------------------------------------------------------------
    M = res["moran"]
    sub = M[(M.scope == "comuna") & (M.indicator == MAIN)].copy()
    fmt = pd.DataFrame({
        tr("weights", lang): [weights_label(x, lang) for x in sub.weights],
        ("Tipo de valor" if es else "Value type"): [vtype_label(x, lang) for x in sub.value_type],
        tr("period", lang): [years_label(x, lang) for x in sub.years],
        ("Subconjunto" if es else "Subset"): [subset_label(x, lang) for x in sub.subset],
        "n": [num(x, 0, lang) for x in sub.n],
        tr("morans_i", lang): [num(x, 4, lang) for x in sub.morans_i],
        "E[I]": [num(x, 4, lang) for x in sub.expected_i],
        "z": [num(x, 2, lang) for x in sub.z_norm],
        ("p analítico" if es else "Analytic p"): [fmt_p(x, lang) for x in sub.p_norm],
        (f"p ({PERMUTATIONS} permutaciones)" if es else f"p ({PERMUTATIONS} permutations)"):
            [fmt_p(x, lang) for x in sub.p_sim],
    })
    add("E43_moran_sensitivity_main", fmt, sub,
        (f"I de Moran del indicador principal: definición de pesos, tipo de valor, periodo y análisis de sensibilidad "
         f"— {v}" if es else
         f"Moran's I of the main indicator: weight definition, value type, period and sensitivity analyses — {v}"),
        ((f"Unidad: I de Moran global de los episodios GRD con F84 documentado por comuna de residencia. Denominador: "
          f"habitantes-año INE base 2017. Cobertura: {len(geo['order'])} comunas en el grafo base; los subconjuntos "
          f"«≥5 eventos» y «sin Región Metropolitana» reconstruyen la contigüidad sobre las comunas que quedan, y las "
          f"filas «denominador censo2024» comparan la base 2017 con el Censo 2024 solo en 2024 (las bases nunca se "
          f"mezclan). Semilla {SEED}. " + note_common)
         if es else
         (f"Unit: global Moran's I of GRD episodes with documented F84 by comuna of residence. Denominator: INE "
          f"base-2017 person-years. Coverage: {len(geo['order'])} comunas in the base graph; the '>=5 events' and "
          f"'excluding Metropolitan Region' subsets rebuild contiguity over the remaining comunas, and the "
          f"'denominator censo2024' rows compare base 2017 with Census 2024 in 2024 only (the bases are never mixed). "
          f"Seed {SEED}. " + note_common)))

    # --- E44 ------------------------------------------------------------------------------------
    # La lámina muestra ocho indicadores por matriz para que el coeficiente sea legible; esta tabla
    # imprime la MATRIZ COMPLETA de los catorce indicadores en las DOS escalas, una debajo de la otra.
    keys = COUNT_INDICATORS + list(CONTEXT)
    blocks = []
    for scope in ("comuna", "region"):
        m = _corr_matrix(res["correlations"], scope, keys)
        block = pd.DataFrame({("Escala" if es else "Scale"): [scope_label(scope, lang)] * len(m),
                              tr("indicator", lang): [ind_short(i, lang) for i in m.index]})
        for col in m.columns:
            block[ind_short(col, lang)] = [num(x, 2, lang) for x in m[col]]
        blocks.append(block)
    fmt = pd.concat(blocks, ignore_index=True)
    add("E44_correlation_matrix_comuna", fmt, res["correlations"],
        (f"Matriz de rho de Spearman entre indicadores territoriales, comunas y regiones — {v}" if es else
         f"Matrix of Spearman's rho between territorial indicators, comunas and regions — {v}"),
        ((f"Unidad: rho de Spearman entre las razones estandarizadas suavizadas de cada indicador (y los porcentajes de "
          f"contexto SAE, urbano y FONASA/INE) sobre las {len(geo['order'])} comunas del grafo. La compañera numérica "
          f"trae cada par con su IC 95 % de Fisher-z, su p y su n, en las dos escalas (comuna y región). "
          f"Advertencia: los indicadores REM, REM-20 y APS localizan el numerador en el lugar de atención. DEIS no "
          f"aparece porque la capa tidy de egresos DEIS no publica la comuna. " + note_common)
         if es else
         (f"Unit: Spearman's rho between the smoothed standardised ratios of each indicator (and the SAE, urban and "
          f"FONASA/INE context percentages) over the {len(geo['order'])} comunas of the graph. The numeric companion "
          f"carries every pair with its Fisher-z 95% CI, p and n, at both scales (comuna and region). Warning: the REM, "
          f"REM-20 and APS indicators locate the numerator at the place of care. DEIS does not appear because the tidy "
          f"DEIS discharge layer publishes no comuna. " + note_common)))

    # --- E45 ------------------------------------------------------------------------------------
    B = res["bivariate"].copy()
    B = B.reindex(B.bv_i.abs().sort_values(ascending=False).index)
    fmt = pd.DataFrame({
        tr("pair", lang): [f"{ind_short(a, lang)} → {ind_short(b, lang)}"
                           for a, b in zip(B.indicator_x, B.indicator_y)],
        tr("bivariate", lang): [num(x, 3, lang) for x in B.bv_i],
        "z": [num(x, 2, lang) for x in B.bv_z],
        (f"p ({PERMUTATIONS} permutaciones)" if es else f"p ({PERMUTATIONS} permutations)"):
            [fmt_p(x, lang) for x in B.bv_p_sim],
        tr("spearman", lang): [num(x, 2, lang) for x in B.spearman_rho],
        "n": [num(x, 0, lang) for x in B.n],
    })
    add("E45_bivariate_moran_pairs", fmt, res["bivariate_local"] if len(res["bivariate_local"]) else B,
        (f"I de Moran bivariada de cada par de indicadores territoriales — {v}" if es else
         f"Bivariate Moran's I of every pair of territorial indicators — {v}"),
        ((f"Unidad: I de Moran bivariada (valor del primer indicador frente al rezago espacial del segundo) con "
          f"contigüidad reina estandarizada por filas e inferencia por {PERMUTATIONS} permutaciones con semilla {SEED}. "
          f"La medida es asimétrica y no implica dirección causal. La compañera numérica contiene la clasificación "
          f"local bivariada comuna a comuna de los dos pares más fuertes entre sistemas distintos. " + note_common)
         if es else
         (f"Unit: bivariate Moran's I (value of the first indicator against the spatial lag of the second) with "
          f"row-standardised queen contiguity and inference from {PERMUTATIONS} permutations with seed {SEED}. The "
          f"measure is asymmetric and implies no causal direction. The numeric companion contains the comuna-level "
          f"local bivariate classification of the two strongest cross-system pairs. " + note_common)))

    # --- E46 ------------------------------------------------------------------------------------
    rows = []
    corr = res["correlations"]
    for ind in COUNT_INDICATORS:
        r = {tr("indicator", lang): ind_short(ind, lang) + ("" if IND[ind]["geo"] == "residence" else " ⚠")}
        for ctx_key, lab in (("sae_multidimensional", tr("sae_multi", lang)),
                             ("sae_income", tr("sae_income", lang)),
                             ("urban_share", "es" == lang and "Población urbana, %" or "Urban population, %")):
            sel = corr[(corr.scope == "comuna") &
                       (((corr.indicator_x == ind) & (corr.indicator_y == ctx_key)) |
                        ((corr.indicator_y == ind) & (corr.indicator_x == ctx_key)))]
            r[lab] = (f"{num(sel.rho.iloc[0], 2, lang)} ({ci(sel.rho_lo.iloc[0], sel.rho_hi.iloc[0], 2, lang)})"
                      if len(sel) else NE[lang])
        rows.append(r)
    ctx_wide = base["context"].pivot_table(index="cut_comuna", columns="indicator",
                                           values=["value", "value_lo", "value_hi"], aggfunc="first")
    ctx_wide.columns = [f"{b}_{a}" for a, b in ctx_wide.columns]
    ratios = std[std.period == "full"].pivot_table(index="cut_comuna", columns="indicator", values="sir_eb")
    ratios.columns = [f"{c}_sir_eb" for c in ratios.columns]
    e46_numeric = ctx_wide.join(ratios, how="outer").reset_index()
    e46_numeric["variant"] = variant
    add("E46_sae_association", pd.DataFrame(rows), e46_numeric,
        (f"Asociación ecológica de cada indicador territorial con la privación comunal SAE 2024 y la urbanidad — {v}"
         if es else
         f"Ecological association of each territorial indicator with SAE 2024 comuna deprivation and urbanicity — {v}"),
        ((f"Unidad: rho de Spearman con IC 95 % de Fisher-z entre la razón estandarizada suavizada de cada indicador y "
          f"el porcentaje comunal de pobreza multidimensional, pobreza por ingresos (estimaciones SAE 2024 con su "
          f"propio intervalo, que no se propaga) y población urbana (proyección INE urbano-rural base 2017). "
          f"Cobertura: {len(geo['order'])} comunas. Son asociaciones ecológicas: la privación es contexto, no un "
          f"factor de riesgo individual. " + note_common)
         if es else
         (f"Unit: Spearman's rho with Fisher-z 95% CI between the smoothed standardised ratio of each indicator and the "
          f"comuna percentage of multidimensional poverty, income poverty (SAE 2024 estimates with their own interval, "
          f"which is not propagated) and urban population (INE base-2017 urban–rural projection). Coverage: "
          f"{len(geo['order'])} comunas. These are ecological associations: deprivation is context, not an individual "
          f"risk factor. " + note_common)))

    # --- E47 ------------------------------------------------------------------------------------
    I = res["inequality"]
    fmt = pd.DataFrame({
        tr("indicator", lang): [ind_short(i, lang) + ("" if IND[i]["geo"] == "residence" else " ⚠")
                                for i in I.indicator],
        tr("period", lang): [years_label(x, lang) for x in I.years],
        tr("n_events", lang): [num(x, 0, lang) for x in I.total_count],
        ("Comunas con cero" if es else "Comunas with zero"): [num(x, 0, lang) for x in I.n_comunas_zero],
        ("Comunas sin reporte" if es else "Comunas with no report"): [num(x, 0, lang) for x in I.n_comunas_never_reported],
        tr("gini", lang): [num(x, 3, lang) for x in I.gini],
        ("Eventos en el decil superior, %" if es else "Events in the top decile, %"):
            [pct(100 * x, lang) for x in I.top_decile_event_share],
        tr("theil", lang): [num(x, 3, lang) for x in I.theil],
        tr("between", lang): [num(x, 3, lang) for x in I.theil_between],
        tr("within", lang): [num(x, 3, lang) for x in I.theil_within],
        ("Entre regiones, %" if es else "Between regions, %"): [pct(100 * x, lang) for x in I.theil_between_share],
        tr("decile_ratio", lang): [num(x, 1, lang) for x in I.decile_ratio_comunas_with_events],
    })
    add("E47_inequality_gini_theil", fmt, I,
        (f"Desigualdad territorial: Gini, índice de Theil descompuesto y razón de deciles, por fuente y año — {v}"
         if es else
         f"Territorial inequality: Gini, decomposed Theil index and decile ratio, by source and year — {v}"),
        ((f"Unidad: distribución de los eventos de cada fuente entre las {len(base['pop_total'].cut_comuna.unique())} "
          f"comunas del universo poblacional, con la población INE base 2017 como referencia. El Gini y el Theil "
          f"incluyen las comunas con cero; la razón de deciles se calcula solo sobre las comunas con al menos un evento "
          f"porque el decil inferior nacional puede ser íntegramente de comunas con cero. Las columnas «comunas con "
          f"cero» y «comunas sin reporte» separan el cero informado de la ausencia de establecimiento reportante. "
          + note_common)
         if es else
         (f"Unit: distribution of each source's events across the {len(base['pop_total'].cut_comuna.unique())} comunas "
          f"of the population universe, with the INE base-2017 population as the reference. Gini and Theil include "
          f"comunas with zero; the decile ratio is computed only over comunas with at least one event because the "
          f"national bottom decile can consist entirely of comunas with zero. The 'comunas with zero' and 'comunas with "
          f"no report' columns separate a reported zero from the absence of a reporting establishment. " + note_common)))

    # --- E48 ------------------------------------------------------------------------------------
    S = res["stability"]
    fmt = pd.DataFrame({
        tr("indicator", lang): [ind_short(i, lang) + ("" if IND[i]["geo"] == "residence" else " ⚠")
                                for i in S.indicator],
        ("Comparación" if es else "Comparison"): [yspan(x) for x in S.comparison],
        ("Base" if es else "Basis"): [_pick(BASIS_LABEL, x, lang) for x in S.basis],
        tr("spearman", lang): [f"{num(r, 3, lang)} ({ci(lo, hi, 3, lang)})"
                               for r, lo, hi in zip(S.rho, S.rho_lo, S.rho_hi)],
        "p": [fmt_p(x, lang) for x in S.p_value],
        "n": [num(x, 0, lang) for x in S.n],
    })
    add("E48_rank_stability", fmt, S,
        (f"Estabilidad del orden territorial entre años y entre periodos — {v}" if es else
         f"Stability of the territorial ranking between years and between periods — {v}"),
        ((f"Unidad: rho de Spearman con IC 95 % de Fisher-z entre las tasas comunales por 100.000 habitantes de años "
          f"sucesivos y entre las razones suavizadas del periodo temprano y del tardío de cada fuente. Las eras de "
          f"definición nunca se cruzan: A05 y P6 comparan 2021–2022 con 2023–2025, GRD compara 2019–2021 con "
          f"2022–2024. Cobertura: {len(geo['order'])} comunas. " + note_common)
         if es else
         (f"Unit: Spearman's rho with Fisher-z 95% CI between the comuna rates per 100,000 of successive years and "
          f"between the smoothed ratios of the early and late periods of each source. Definition eras are never "
          f"crossed: A05 and P6 compare 2021–2022 with 2023–2025, GRD compares 2019–2021 with 2022–2024. Coverage: "
          f"{len(geo['order'])} comunas. " + note_common)))

    # --- E49 ------------------------------------------------------------------------------------
    R = res["regions"]
    sub = R[R.indicator.isin(["grd_episodes", "grd_persons", "a05_entries", "p2_stock"])].copy()
    sub = sub.dropna(subset=["observed"])
    fmt = pd.DataFrame({
        tr("region", lang): [REGION_NAMES.get(int(r), str(r)) for r in sub.cut_region],
        tr("indicator", lang): [ind_short(i, lang) + ("" if IND[i]["geo"] == "residence" else " ⚠")
                                for i in sub.indicator],
        tr("observed", lang): [num(x, 0, lang) for x in sub.observed],
        tr("expected", lang): [num(x, 1, lang) for x in sub.expected],
        tr("rate", lang): [f"{num(r, 1, lang)} ({ci(lo, hi, 1, lang)})"
                           for r, lo, hi in zip(sub.rate_per_100k, sub.rate_lo, sub.rate_hi)],
        tr("crude_ratio", lang): [f"{num(r, 2, lang)} ({ci(lo, hi, 2, lang)})"
                                  for r, lo, hi in zip(sub.sir, sub.sir_lo, sub.sir_hi)],
        tr("smoothed_ratio", lang): [num(x, 2, lang) for x in sub.sir_eb],
    })
    add("E49_regional_summary", fmt, R,
        (f"Resumen regional: observados, esperados, tasas y razones estandarizadas con intervalos — {v}" if es else
         f"Regional summary: observed, expected, rates and standardised ratios with intervals — {v}"),
        ((f"Unidad: las mismas fuentes agregadas a las 16 regiones. Denominador: habitantes-año INE base 2017 de la "
          f"región. Cobertura: GRD 2019–2024 (residencia), A05 2021–2025 y P2 2019–2025 (⚠ comuna del establecimiento). "
          f"Nunca se calcula un cociente entre fuentes no enlazables. " + note_common)
         if es else
         (f"Unit: the same sources aggregated to the 16 regions. Denominator: INE base-2017 person-years of the region. "
          f"Coverage: GRD 2019–2024 (residence), A05 2021–2025 and P2 2019–2025 (⚠ comuna of the establishment). No "
          f"ratio is ever computed between sources that cannot be linked. " + note_common)))

    # --- E50 ------------------------------------------------------------------------------------
    allm = M.copy()
    fmt = pd.DataFrame({
        ("Escala" if es else "Scale"): [scope_label(x, lang) for x in allm.scope],
        tr("indicator", lang): [ind_short(i, lang) for i in allm.indicator],
        ("Tipo de valor" if es else "Value type"): [vtype_label(x, lang) for x in allm.value_type],
        tr("weights", lang): [weights_label(x, lang) for x in allm.weights],
        tr("period", lang): [years_label(x, lang) for x in allm.years],
        ("Subconjunto" if es else "Subset"): [subset_label(x, lang) for x in allm.subset],
        "n": [num(x, 0, lang) for x in allm.n],
        tr("morans_i", lang): [num(x, 4, lang) for x in allm.morans_i],
        "E[I]": [num(x, 4, lang) for x in allm.expected_i],
        "z": [num(x, 2, lang) for x in allm.z_norm],
        ("p analítico" if es else "Analytic p"): [fmt_p(x, lang) for x in allm.p_norm],
        (f"p ({PERMUTATIONS} perm.)" if es else f"p ({PERMUTATIONS} perm.)"): [fmt_p(x, lang) for x in allm.p_sim],
    })
    gi = res["local"].groupby("indicator").agg(gi_hot=("gi_class", lambda s: int((s == "hot").sum())),
                                               gi_cold=("gi_class", lambda s: int((s == "cold").sum()))).reset_index()
    add("E50_moran_gistar_all", fmt, allm.merge(gi, on="indicator", how="left"),
        (f"Todas las estadísticas de autocorrelación espacial calculadas: I de Moran global y clases del Gi* — {v}"
         if es else
         f"Every spatial-autocorrelation statistic computed: global Moran's I and Gi* classes — {v}"),
        ((f"Unidad: una fila por escala (comuna o región), indicador, tipo de valor, definición de pesos, periodo y "
          f"subconjunto de sensibilidad. Inferencia analítica bajo normalidad y por {PERMUTATIONS} permutaciones con "
          f"semilla {SEED}. La compañera numérica añade el número de puntos calientes y fríos del Gi*. " + note_common)
         if es else
         (f"Unit: one row per scale (comuna or region), indicator, value type, weight definition, period and "
          f"sensitivity subset. Inference analytically under normality and from {PERMUTATIONS} permutations with seed "
          f"{SEED}. The numeric companion adds the number of Gi* hot and cold spots. " + note_common)))

    # --- E51 ------------------------------------------------------------------------------------
    sig = res["local"][(res["local"].lisa_class != "ns") | (res["local"].gi_class != "ns")].copy()
    sig = sig.sort_values(["indicator", "lisa_p_sim"])
    fmt = pd.DataFrame({
        tr("indicator", lang): [ind_short(i, lang) + ("" if IND[i]["geo"] == "residence" else " ⚠")
                                for i in sig.indicator],
        tr("comuna", lang): sig.comuna_name_ine,
        "CUT": sig.cut_comuna.astype(int).astype(str),
        tr("region", lang): sig.region_name,
        tr("observed", lang): [_count_display(x, lang) for x in sig.observed],
        tr("expected", lang): [num(x, 1, lang) for x in sig.expected],
        tr("crude_ratio", lang): [f"{num(r, 2, lang)} ({ci(lo, hi, 2, lang)})"
                                  for r, lo, hi in zip(sig.sir, sig.sir_lo, sig.sir_hi)],
        tr("smoothed_ratio", lang): [num(x, 2, lang) for x in sig.sir_eb],
        "LISA": [_pick(CLASS_LABEL, x, lang) for x in sig.lisa_class],
        ("LISA p" if es else "LISA p"): [fmt_p(x, lang) for x in sig.lisa_p_sim],
        "Gi*": [_pick(CLASS_LABEL, x, lang) for x in sig.gi_class],
        "Gi* z": [num(x, 2, lang) for x in sig.gi_z],
        ("Gi* p" if es else "Gi* p"): [fmt_p(x, lang) for x in sig.gi_p_sim],
    })
    add("E51_lisa_significant_comunas", fmt, sig,
        (f"Comunas con agrupamiento local significativo (LISA o Gi*, Benjamini–Hochberg q < {num(FDR_Q, 2, lang)}) — {v}" if es else
         f"Comunas with a significant local cluster (LISA or Gi*, Benjamini–Hochberg q < {FDR_Q}) — {v}"),
        ((f"Unidad: una fila por comuna e indicador con clase local significativa tras el control de la tasa de "
          f"falsos descubrimientos. Se listan los observados (suprimidos como «<5» cuando corresponde), los esperados "
          f"de la estandarización indirecta, la razón cruda con IC 95 % exacto de Poisson, la razón suavizada, el "
          f"cuadrante LISA y la clase Gi* con sus p de permutación. Cobertura: {len(geo['order'])} comunas del grafo. "
          + note_common)
         if es else
         (f"Unit: one row per comuna and indicator with a significant local class after false-discovery-rate control. "
          f"Observed counts (suppressed as '<5' where applicable), expected counts from the indirect standardisation, "
          f"the crude ratio with exact Poisson 95% CI, the smoothed ratio, the LISA quadrant and the Gi* class with "
          f"their permutation p are listed. Coverage: {len(geo['order'])} comunas of the graph. " + note_common)))

    merge_json(tdir / "titles.json", titles)
    written.append(str(tdir / "titles.json"))
    return written, titles


# ---------------------------------------------------------------------------
# Controles de reproducción
# ---------------------------------------------------------------------------
def run_controls(res: dict, variant: str, geo: dict, base: dict) -> None:
    """Los agregados comunales deben reproducir los totales nacionales ya verificados."""
    counts = res["counts"]
    cw = base["crosswalk"]

    # 1. GRD: la suma comunal debe igualar grd_year_summary (salvo los episodios sin comuna enlazable).
    gy = pd.read_csv(TIDY / "grd_year_summary.csv")
    gy = gy[(gy.variant == variant) & (gy.panel == "observed") & (gy.activity == "all")]
    terr = pd.read_csv(TIDY / "grd_territory.csv")
    unmatched = terr[(terr.level == "comuna") & (terr.panel == "observed") & (terr.variant == variant) &
                     (terr.match_method == "unmatched")]
    for position, indicator in (("any", "grd_episodes"), ("principal", "grd_principal")):
        for year in YEARS_GRD:
            expected = float(gy[(gy.position == position) & (gy.year == year)].n_episodes_f84.iloc[0])
            observed = float(counts[(counts.indicator == indicator) & (counts.year == year)]["count"].sum())
            unm = float(unmatched[(unmatched.position == position) & (unmatched.year == year)].n_episodes.sum())
            CTL.add(f"grd_comuna_sum_vs_national_{position}", f"{variant}|{year}", expected - unm, observed,
                    f"suma comunal + {unm:.0f} episodios de comunas no enlazables = total nacional de "
                    f"grd_year_summary.csv ({expected:.0f})")

    # 2. REM: la suma comunal debe igualar rem_pathway_annual y config.CONTROLS.
    ra = pd.read_csv(TIDY / "rem_pathway_annual.csv")
    a05 = ra[(ra.module == "A05") & (ra.variant == variant) & ra.indicator.str.contains("ingresos")]
    for row in a05.itertuples():
        observed = float(counts[(counts.indicator == "a05_entries") & (counts.year == row.year)]["count"].sum())
        CTL.add("a05_comuna_sum_vs_national", f"{variant}|{row.year}", float(row.total), observed,
                "suma por comuna del establecimiento = total anual de rem_pathway_annual.csv", tol=1e-6)
    for year, expected in CFG.CONTROLS["p2_tea_december"].items():
        observed = float(counts[(counts.indicator == "p2_stock") & (counts.year == year)]["count"].sum())
        CTL.add("p2_comuna_sum_vs_config", f"{variant}|{year}", float(expected), observed,
                "stock de diciembre por comuna del establecimiento = config.CONTROLS['p2_tea_december']", tol=1e-6)
    p6 = ra[(ra.module == "P6") & (ra.variant == variant) & (ra.month.astype(str).str.zfill(2) == "12")]
    p6_sets = {"p6_primary": set(CFG.VARIANTS[variant]["p6_primary"]),
               "p6_specialty": set(CFG.VARIANTS[variant]["p6_specialty"])}
    for row in p6.itertuples():
        codes = set(str(row.code).split("+"))
        ind = next((k for k, v in p6_sets.items() if codes == v), None)
        if ind is None or row.year not in YEARS_P6:
            continue
        observed = float(counts[(counts.indicator == ind) & (counts.year == row.year)]["count"].sum())
        CTL.add("p6_comuna_sum_vs_national", f"{variant}|{ind}|{row.year}", float(row.total), observed,
                "stock de diciembre por comuna del establecimiento = total de rem_pathway_annual.csv", tol=1e-6)

    # 3b. Enlace de nombres de comuna: coincidencias frente al crosswalk y nombres no enlazados documentados.
    matched_names = terr[(terr.level == "comuna") & (terr.match_method.isin(["exact", "alias"]))].comuna_norm.nunique()
    unmatched_names = sorted(terr[(terr.level == "comuna") &
                                  (terr.match_method == "unmatched")].comuna_norm.unique())
    CTL.add("grd_comuna_names_matched", variant, len(cw), matched_names,
            f"nombres distintos de comuna de residencia del GRD enlazados por código o alias auditable frente a las "
            f"{len(cw)} comunas del crosswalk; nombres no enlazados: {unmatched_names} "
            f"(nunca se asignan por similitud)",
            status="ok" if matched_names <= len(cw) else "differs")
    CTL.info("grd_comuna_names_unmatched", variant, json.dumps(unmatched_names),
             "nombres de comuna del GRD sin enlace en comuna_crosswalk.csv; sus episodios quedan fuera de los mapas "
             "y se descuentan de los controles de suma")

    # 3. Cobertura y capacidad.
    cov = pd.read_csv(TIDY / "coverage_layers_year.csv")
    for year in YEARS_COV:
        row = cov[cov.year == year]
        if not len(row):
            continue
        observed = float(counts[(counts.indicator == "aps_enrolled") & (counts.year == year)]["count"].sum())
        CTL.add("aps_comuna_sum_vs_national", f"{variant}|{year}", float(row.aps_enrolled_dec.iloc[0]), observed,
                "inscritos APS por comuna del centro = total nacional de coverage_layers_year.csv", tol=1e-6)
        observed = float(counts[(counts.indicator == "rem20_discharges") & (counts.year == year)]["count"].sum())
        CTL.add("rem20_comuna_sum_vs_national", f"{variant}|{year}", float(row.rem20_discharges_all.iloc[0]),
                observed, "egresos REM-20 por comuna del establecimiento = total de coverage_layers_year.csv",
                tol=1e-6)
        observed = float(counts[(counts.indicator == "fonasa_beneficiaries") & (counts.year == year)]["count"].sum())
        national = float(row.fonasa_beneficiaries_dec.iloc[0])
        CTL.add("fonasa_comuna_sum_vs_national", f"{variant}|{year}", national, observed,
                "la suma comunal es menor que el total nacional por las filas sin comuna enlazable "
                "(DESCONOCIDA y equivalentes, documentadas en comuna_unmatched.csv)",
                status="ok" if observed <= national else "differs")

    # 4. Enlace territorial: comunas con coincidencia frente al crosswalk.
    unm_names = pd.read_csv(TIDY / "comuna_unmatched.csv")
    CTL.add("comunas_in_universe", variant, len(cw), int(counts.cut_comuna.nunique()),
            f"el panel comunal cubre las {len(cw)} comunas del crosswalk auditable; los nombres no enlazados "
            f"({len(unm_names)} filas de comuna_unmatched.csv) nunca se asignan por similitud")
    CTL.add("comunas_in_contiguity_graph", variant, len(cw) - len(geo["missing_from_map"]) - 1,
            len(geo["order"]),
            f"comunas del crosswalk menos las ausentes de la cartografía {geo['missing_from_map']} y menos "
            f"Cabo de Hornos (12201), no continental")

    # 5. Estandarización: la razón nacional debe ser 1 por construcción.
    std = res["standardised"]
    for ind in COUNT_INDICATORS:
        f = std[(std.indicator == ind) & (std.period == "full")]
        CTL.add("national_ratio_equals_one", f"{variant}|{ind}", 1.0,
                float(f.observed.sum() / f.expected.sum()) if f.expected.sum() else np.nan,
                "estandarización indirecta interna: la suma de esperados se reescala a la de observados",
                tol=1e-6)
        CTL.info("expected_scaling_factor", f"{variant}|{ind}", round(float(f.expected_scaling_factor.iloc[0]), 6),
                 "factor de reescalado del esperado antes de la razón (1 = la referencia nacional ya cuadra)")

    # 6. La I de Moran del indicador principal se informa siempre con su p de permutación.
    M = res["moran"]
    row = M[(M.scope == "comuna") & (M.indicator == MAIN) & (M.value_type == "sir_eb") & (M.weights == "queen") &
            (M.years == "full period") & (M.subset == "all comunas")]
    CTL.add("main_moran_reported_with_permutation_p", variant, 1, int(len(row) == 1 and np.isfinite(row.p_sim.iloc[0])),
            f"I de Moran de la razón suavizada de {MAIN} = {float(row.morans_i.iloc[0]):.4f} con "
            f"p de permutación = {float(row.p_sim.iloc[0]):.4f} ({PERMUTATIONS} permutaciones, semilla {SEED})")
    CTL.info("main_moran_value", variant, round(float(row.morans_i.iloc[0]), 4),
             f"E[I] = {float(row.expected_i.iloc[0]):.4f}; z = {float(row.z_norm.iloc[0]):.2f}; "
             f"p analítico = {float(row.p_norm.iloc[0]):.3g}")

    # 7. Recuentos de las clases locales y de los pares evaluados.
    L = res["local"]
    CTL.info("lisa_significant_comunas", f"{variant}|{MAIN}", int((L[L.indicator == MAIN].lisa_class != "ns").sum()),
             f"comunas con clase LISA significativa tras Benjamini–Hochberg (q = {FDR_Q})")
    CTL.info("gistar_significant_comunas", f"{variant}|{MAIN}", int((L[L.indicator == MAIN].gi_class != "ns").sum()),
             "comunas con Gi* significativo tras Benjamini–Hochberg")
    CTL.info("correlation_pairs", variant, int((res["correlations"].scope == "comuna").sum()),
             "pares de indicadores con rho de Spearman e IC de Fisher-z a escala comunal")
    CTL.info("bivariate_pairs", variant, len(res["bivariate"]),
             "pares con I de Moran bivariada e inferencia por permutación")

    # 8. DEIS: no hay desglose comunal en la capa tidy.
    CTL.info("deis_comuna_available", variant, "no",
             "ninguna tabla outputs/tidy/deis_*.csv publica la comuna del egreso; los egresos DEIS quedan fuera de "
             "la matriz de correlación comunal y se declara en las notas")
    CTL.info("education_comuna_available", variant, "no",
             "outputs/tidy/education_summary_year.csv es nacional: el PIE no tiene desglose comunal en esta capa")


# ---------------------------------------------------------------------------
# Principal
# ---------------------------------------------------------------------------
def main() -> int:
    global PERMUTATIONS
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--variants", nargs="+", default=list(CFG.VARIANTS), choices=list(CFG.VARIANTS))
    ap.add_argument("--langs", nargs="+", default=list(CFG.LANGUAGES), choices=list(CFG.LANGUAGES))
    ap.add_argument("--permutations", type=int, default=PERMUTATIONS)
    ap.add_argument("--no-figures", action="store_true")
    ap.add_argument("--no-tables", action="store_true")
    args = ap.parse_args()
    PERMUTATIONS = args.permutations

    log(f"{MODULE}: {len(args.variants)} variantes × {len(args.langs)} idiomas; "
        f"{args.permutations} permutaciones, semilla {SEED}")

    cw = load_crosswalk()
    geo = load_geography(cw)
    pop_agesex, pop_total = load_population("base2017")
    pop_agesex_censo, pop_total_censo = load_population("censo2024")
    coverage = comuna_counts_coverage(cw)
    context = load_context(cw, pop_total, coverage)
    base = dict(crosswalk=cw, pop_agesex=pop_agesex, pop_total=pop_total, pop_agesex_censo=pop_agesex_censo,
                pop_total_censo=pop_total_censo, coverage=coverage, context=context)
    log(f"entradas listas: {len(pop_total.cut_comuna.unique())} comunas, "
        f"{len(geo['order'])} en el grafo de contigüidad")

    written: list[str] = []
    tidy: dict[str, list[pd.DataFrame]] = {k: [] for k in
                                           ["spatial_comuna_indicators", "spatial_comuna_standardised", "spatial_moran",
                                            "spatial_lisa", "spatial_correlations", "spatial_bivariate_moran",
                                            "spatial_bivariate_local", "spatial_inequality", "spatial_stability",
                                            "spatial_region_summary", "spatial_denominator_sensitivity"]}
    per_variant: dict[str, dict] = {}
    figures_written: dict[str, int] = {}

    for variant in args.variants:
        log(f"variante {variant}")
        res = analyse_variant(variant, geo, base, args.permutations)
        run_controls(res, variant, geo, base)
        tidy["spatial_comuna_indicators"].append(res["counts"])
        tidy["spatial_comuna_standardised"].append(res["standardised"])
        tidy["spatial_moran"].append(res["moran"])
        tidy["spatial_lisa"].append(res["local"])
        tidy["spatial_correlations"].append(res["correlations"])
        tidy["spatial_bivariate_moran"].append(res["bivariate"])
        if len(res["bivariate_local"]):
            tidy["spatial_bivariate_local"].append(res["bivariate_local"])
        tidy["spatial_inequality"].append(res["inequality"])
        tidy["spatial_stability"].append(res["stability"])
        tidy["spatial_region_summary"].append(res["regions"])
        if len(res["denominator"]):
            tidy["spatial_denominator_sensitivity"].append(res["denominator"])
        per_variant[variant] = dict(seconds=res["seconds"], comunas=int(res["counts"].cut_comuna.nunique()),
                                    moran_rows=len(res["moran"]), local_rows=len(res["local"]),
                                    correlation_rows=len(res["correlations"]))

        for lang in args.langs:
            t_l = time.time()
            if not args.no_figures:
                fdir = out_dir(variant, lang, "figures")
                caps = captions(res, geo, variant, lang)
                paths = {}
                for name, fn in FIGURES.items():
                    paths[name] = fn(res, geo, variant, lang, fdir)
                    written.append(paths[name])
                merge_json(fdir / "captions.json", C.strip_caption_paths(caps))
                written.append(str(fdir / "captions.json"))
                figures_written[f"{variant}/{lang}"] = len(paths)
            if not args.no_tables:
                paths, titles = build_tables(res, geo, base, variant, lang)
                written += paths
            log(f"  {variant}/{lang}: láminas y tablas listas ({time.time() - t_l:.1f} s)")

    for name, frames in tidy.items():
        if not frames:
            continue
        df = pd.concat(frames, ignore_index=True)
        df["script"] = SCRIPT
        written.append(str(C.atomic_write_csv(df, TIDY / f"{name}.csv")))
        log(f"tidy {name}.csv: {len(df):,} filas")

    ctx = base["context"].copy()
    ctx["script"] = SCRIPT
    ctx["unit"] = ("percentage of the comuna population; SAE 2024 small-area estimates carry their own lower and "
                   "upper limit, which is reported and never propagated into the correlations")
    written.append(str(C.atomic_write_csv(ctx, TIDY / "spatial_context_comuna.csv")))
    log(f"tidy spatial_context_comuna.csv: {len(ctx):,} filas")

    dictionary = pd.DataFrame([
        dict(table="spatial_comuna_indicators", unit="comuna × year × indicator: count, population, rate per 100,000",
             geography="mixed: residence for GRD, establishment for REM/REM-20/APS (column geography_numerator)",
             denominator="INE base 2017 (30 June) comuna population", definition_era="see column indicator",
             note="count_state separates reported_value, reported_zero, structural_zero and no_reporting_establishment"),
        dict(table="spatial_comuna_standardised", unit="comuna × indicator × period: observed, expected, ratios",
             geography="as above", denominator="person-years of the period",
             definition_era="GRD 2019–2024; A05 and P6 2021–2025; P2 2019–2025; coverage 2019–2025",
             note="internal indirect standardisation; exact Poisson limits; Marshall empirical-Bayes with prior mean and variance"),
        dict(table="spatial_moran", unit="one row per scale × indicator × value type × weights × period × subset",
             geography="comuna and region", denominator="n/a",
             definition_era="n/a", note=f"analytic and {PERMUTATIONS}-permutation inference, seed {SEED}"),
        dict(table="spatial_lisa", unit="comuna × indicator: LISA quadrant, Gi* class and their p-values",
             geography="comuna", denominator="n/a", definition_era="n/a",
             note=f"Benjamini–Hochberg at q = {FDR_Q}; p_sim and p_z_sim both reported"),
        dict(table="spatial_correlations", unit="indicator pair × scale: Spearman rho with Fisher-z interval",
             geography="comuna and region", denominator="n/a", definition_era="n/a",
             note="ecological associations between administrative counts; no individual inference"),
        dict(table="spatial_bivariate_moran", unit="indicator pair: bivariate Moran's I",
             geography="comuna", denominator="n/a", definition_era="n/a",
             note="asymmetric measure; permutation inference"),
        dict(table="spatial_bivariate_local", unit="comuna × pair: local bivariate class",
             geography="comuna", denominator="n/a", definition_era="n/a", note="two strongest cross-system pairs"),
        dict(table="spatial_inequality", unit="indicator × year: Gini, Theil (between/within) and decile ratio",
             geography="comuna", denominator="INE base 2017 population", definition_era="see indicator",
             note="comunas with zero are kept; the decile ratio is also reported over comunas with events only"),
        dict(table="spatial_stability", unit="indicator × comparison: Spearman rho with Fisher-z interval",
             geography="comuna", denominator="n/a", definition_era="eras are never crossed",
             note="successive years on rates; early versus late period on the smoothed ratio"),
        dict(table="spatial_region_summary", unit="region × indicator: observed, expected, rate and ratios",
             geography="region", denominator="INE base 2017 person-years", definition_era="see indicator",
             note="16 regions; no ratio between unlinked sources"),
        dict(table="spatial_context_comuna", unit="comuna × context indicator: percentage with its own interval",
             geography="residence (SAE and INE) or mixed (FONASA share)", denominator="see unit",
             definition_era="SAE 2024; INE urban–rural projection base 2017; FONASA December 2024",
             note="the SAE interval is reported verbatim and never propagated into the correlations"),
        dict(table="spatial_denominator_sensitivity", unit="comuna: 2024 standardisation under two population bases",
             geography="comuna", denominator="INE base 2017 versus Census 2024", definition_era="2024 only",
             note="the bases are never merged; the census is an enumeration, not a mid-year projection"),
    ])
    dictionary["variants"] = ", ".join(args.variants)
    dictionary["script"] = SCRIPT
    written.append(str(C.atomic_write_csv(dictionary, TIDY / "spatial_dictionary.csv")))

    ctl_frame = CTL.frame()
    ctl_path = C.atomic_write_csv(ctl_frame, CONTROLS_DIR / f"{MODULE}_controls.csv")
    counts_status = ctl_frame.status.value_counts().to_dict()
    import esda as _esda
    import libpysal as _libpysal
    runlog = dict(module=MODULE, script=SCRIPT,
                  finished=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  seconds_total=round(time.time() - T0, 1), seed=SEED, permutations=args.permutations,
                  fdr_q=FDR_Q, suppression_threshold=SUPPRESSION_THRESHOLD,
                  crs=geo["crs"], comunas_in_graph=len(geo["order"]),
                  islands_attached=geo["islands"], idw_threshold_m=geo["idw_threshold"],
                  variants=per_variant, figures=figures_written,
                  controls={k: int(v) for k, v in counts_status.items()},
                  files_written=len(written),
                  python=sys.version.split()[0], pandas=pd.__version__, numpy=np.__version__,
                  esda=_esda.__version__, libpysal=_libpysal.__version__)
    C.atomic_write_json(runlog, CONTROLS_DIR / f"{MODULE}_runlog.json")
    log(f"controles: {counts_status} → {ctl_path.relative_to(REPO)}")
    log(f"archivos escritos: {len(written)}")
    log(f"{MODULE} terminado en {time.time() - T0:.1f} s")
    return 0 if counts_status.get("differs", 0) == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
