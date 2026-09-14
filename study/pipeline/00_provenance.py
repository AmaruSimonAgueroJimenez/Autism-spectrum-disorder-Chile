#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""00_provenance.py — freeze the provenance of every source artefact used by the multisource study.

Produces `study/data_provenance.csv` (one row per artefact, SHA-256 streamed in 1 MiB blocks with
`common.sha256_file`) plus a copy in `outputs/tidy/`, a per-artefact manifest reconciliation table, a summary by
source and a controls table (`outputs/controls/00_provenance_controls.csv`).

Descriptive columns are transcribed from `scripts/downloads/DATA_REVIEW.md`, `scripts/downloads/source_registry.csv`,
`scripts/downloads/rem_pathway_codes.csv` and `study/config.py`; nothing is invented. They are written HERE in
English, and English is the canonical form of the frozen artefact: the Spanish reading of every one of them lives in
`labels.PROVENANCE_TEXT` and is applied when the supplementary table is printed (`labels.provenance_text`), so the CSV
and its SHA-256 never change with the language of the document. A new descriptive value added here without its Spanish
gloss makes `tests/test_language_purity.py::ProvenanceTextTest` fail, which is the reminder to declare it. Dates are reused from
the manifests that list each file (Autism/metadata/download_manifest.csv, FONASA/metadata/source_manifest.csv,
REM/SerieP/manifest_extract_rem_series_p.csv, REM/SerieA/metadata/canonical_manifest.csv, DEIS/Egresos/metadata/
canonical_manifest.csv and GRD/metadata/SOURCES_MANIFEST.md); a SHA mismatch against any manifest is a finding.

Run from the repository root:  python3 study/pipeline/00_provenance.py [--use-cache] [--limit N]
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parents[1]  # study/
sys.path.insert(0, str(HERE))
import config as CFG  # noqa: E402
import common as M  # noqa: E402

MODULE = "00_provenance"
DATA_ROOT = CFG.DATA_ROOT
AUTISM_ROOT = CFG.AUTISM_ROOT
REPO = CFG.REPO
# config.CONTROLS is the dict of expected values (it shadows the directory Path defined earlier in config.py)
CONTROLS_DIR = CFG.OUT / "controls"
CONTROLS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_PATH = CFG.OUT / ".cache" / "provenance_sha256_cache.json"

REQUIRED_COLUMNS = ["source_id", "file", "relative_path", "bytes", "sha256", "downloaded_or_version_date",
                    "observation_unit", "period", "population_covered", "geography", "codes_columns_used",
                    "stock_or_flow", "possible_denominator", "definition_breaks", "linkage_restrictions", "use_rule"]
EXTRA_COLUMNS = ["root", "artefact_role", "provider", "source_container", "manifest_source", "manifest_sha256",
                 "sha256_matches_manifest", "manifest_bytes", "bytes_match_manifest", "file_mtime_utc", "landing_url"]


def years(a: int, b: int) -> list[int]:
    return list(range(a, b + 1))


# ---------------------------------------------------------------------------
# Descriptive metadata by source (DATA_REVIEW.md, source_registry.csv, rem_pathway_codes.csv, config.py)
# ---------------------------------------------------------------------------
REM_A03_CODES = ("A03 legacy 2019-2022: 03500404, 03500405, 03500406, 03500407; 2023-2024: 09600212-09600219; "
                 "2024 only (31-59 months): 03700104-03700109; 2025 redesign: 03710013-03710021")
REM_A05_CODES = ("A05 2019-2020 broad PDD: 06902600 (entry), 05225000 (exit); 2021-2025: entries 05990022 autism, "
                 "05990023 Asperger, 05990024 Rett, 05990025 disintegrative, 05990026 PDD-NOS; exits 05990027-05990031")
REM_A27_A28_CODES = "A27 2023-2025: 29101566 counselling, 29101574 assisted referral; A28 2023-2025: 29101629 primary, 29101651 hospital"
REM_P_CODES = ("P2500500 (P2 autism NANEAS under control), P2501878 (total NANEAS, from Dec 2023); P6 2019-2020 broad PDD "
               "P6223000 (primary) / P6223380 (specialty); P6 2021-2025 primary P6241010-P6241050, specialty P6241060-P6241100")

SOURCES = {
    "grd_publico": dict(
        provider="FONASA", landing_url="https://public.tableau.com/views/PropuestaTableroGRD/PropuestaTableroGRD?:showVizHome=no",
        observation_unit="GRD episode (one row per financed/coded hospital episode: hospitalisation or major ambulatory surgery)",
        population_covered="Episodes of public hospitals reporting to the FONASA GRD dataset; observed panel of 65 hospitals in 2019-2022, 68 in 2023 and 72 in 2024 (not a fixed panel of 72)",
        geography="Hospital of care (COD_HOSPITAL, SERVICIO_SALUD); patient's reported COMUNA/PROVINCIA of residence (place of care and residence must not be mixed)",
        codes_columns_used="sep='|'; DIAGNOSTICO1..DIAGNOSTICO35 (ICD-10; F84 family per config.F84_SUBCODES, F84.2 Rett excluded in variant sin_rett), TIPO_ACTIVIDAD, COD_HOSPITAL, SEXO, FECHA_NACIMIENTO, FECHA_INGRESO, FECHAALTA, COMUNA, PREVISION; identifier CIP_ENCRIPTADO (2019-2023) / ID_BENEFICIARIO (2024)",
        stock_or_flow="flow (episodes discharged in the year)",
        possible_denominator="All GRD episodes of the same year and hospital panel (per 100,000 episodes); INE base-2017 population by age and sex for complementary population rates",
        definition_breaks="Encrypted identifier changes format between 2020 and 2021 (zero overlap); hospital panel 65/65/65/65/68/72; mean coding depth rises from 4.39 (2019) to 5.78 (2024) diagnoses per episode; 2019 contains day-hospital and emergency activity categories absent from 2020; GRD_PUBLICO_2022.csv omits one malformed source row (932,839 vs 932,840 records; see GRD/metadata/SOURCES_MANIFEST.md)",
        linkage_restrictions="Unique persons only within each year; never deduplicate across 2020/2021; no person-level linkage to REM, DEIS, FONASA, surveys or education",
        use_rule="Primary hospital estimand: GRD episodes with documented F84 in any diagnosis position per 100,000 GRD episodes; F84 principal, strict hospitalisation vs major ambulatory surgery, fixed panel of 65 hospitals and coding-depth stratification are mandatory sensitivities; never label as 'hospitalisations for autism', prevalence or incidence; reproduce config.CONTROLS['grd_*'] before modelling",
    ),
    "grd_dictionaries": dict(
        provider="FONASA", landing_url="https://public.tableau.com/views/PropuestaTableroGRD/PropuestaTableroGRD?:showVizHome=no",
        observation_unit="Code dictionary / master table (ICD-10, ICD-9-CM procedures, GRD master tables)",
        population_covered="not applicable (metadata)", geography="not applicable",
        codes_columns_used="ICD-10 F84 family labels; TIPO_ACTIVIDAD and hospital master tables",
        stock_or_flow="not applicable (dictionary)", possible_denominator="not applicable",
        definition_breaks="Verify the version applicable to each GRD year (source_registry.csv)",
        linkage_restrictions="not applicable", use_rule="Interpretation of GRD codes and categories only; never a data input",
    ),
    "rem_serie_a": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://deis.minsal.cl/#datosabiertos",
        observation_unit="Establishment x month x REM code row (Col01..Col50 cells of Serie A monthly statistical register)",
        population_covered="Activity reported by public-network establishments (primary care and specialty) to DEIS; the reporting panel varies by year and code and must be reported alongside counts",
        geography="Establishment of care (IdEstablecimiento, IdServicio, IdRegion, IdComuna of the establishment); never residence",
        codes_columns_used="sep=';'; keys Mes, IdServicio, Ano, IdEstablecimiento, CodigoPrestacion, IdRegion, IdComuna; values Col01..Col50 read as text (empty cell != 0). " + REM_A03_CODES + ". " + REM_A05_CODES + ". " + REM_A27_A28_CODES + ". Annual totals: sum of months of Col01+Col02 (A03) or Col01 (A05/A27/A28); A05 age-sex in Col04..Col37",
        stock_or_flow="flow (monthly activity: screenings, interventions, programme entries/exits)",
        possible_denominator="INE base-2017 population by age/sex (A05); number of reporting establishments and stable panel; APS enrolment as operational coverage; no ratios between stages of non-linkable sources",
        definition_breaks="A03: legacy subgroup codes 2019-2022 (children with language/social alteration), new M-CHAT-R/F family 2023, 31-59-month codes added 2024, full redesign 2025; A05: broad PDD only in 2019-2020, strict autism and disaggregated categories from 2021; A27 TEA-specific codes only from 2023 (earlier assisted-referral codes concern alcohol/drugs); A28 autism rehabilitation from 2023; 2020 reporting disruption (pandemic); SerieA_2025.csv keeps one incomplete trailing row from the source publication",
        linkage_restrictions="Aggregate rows without persons; A27 counts interventions not children; no linkage between A03, A27, A05, A28, P2/P6 or GRD",
        use_rule="Build tidy establishment x month x code tables keeping zero, empty and 'no row reported' as distinct states; facet by definition era; report reporting establishments; confirm every code against the annual Serie A dictionary; treat 2020 as a reporting-disruption year without interpolation; reproduce config.CONTROLS a05/a27/a28/a03 totals",
    ),
    "rem_serie_a_dictionary": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://deis.minsal.cl/#datosabiertos",
        observation_unit="Annual Serie A code dictionary (one sheet per REM section: A03, A05, A27, A28, ...)",
        population_covered="not applicable (metadata)", geography="not applicable",
        codes_columns_used="Sheets A03, A05, A27, A28: code (8 digits), label, section header, COL01..COLnn mapping (sex and age headers)",
        stock_or_flow="not applicable (dictionary)", possible_denominator="not applicable",
        definition_breaks="File naming changes in 2023 (DICCIONARIO CODIGOS SA_yy); code families change as listed for rem_serie_a",
        linkage_restrictions="not applicable", use_rule="Confirm every code and column position of scripts/downloads/rem_pathway_codes.csv for the given year before extraction (scripts/audit_rem.py pattern)",
    ),
    "rem_serie_p": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://deis.minsal.cl/#datosabiertos",
        observation_unit="Establishment x semester (Mes=06 or 12) x REM code row (Serie P population under control)",
        population_covered="People under control in public-network establishments reporting P2 (NANEAS) and P6 (mental health) at June and December; reporting establishments vary (P2 December: 460, 400, 640, 897, 1,012, 1,218, 1,325 in 2019-2025)",
        geography="Establishment of care (IdEstablecimiento, IdServicio, IdRegion, IdComuna of the establishment); never residence",
        codes_columns_used="sep=';'; same layout as Serie A (Mes, IdServicio, Ano, IdEstablecimiento, CodigoPrestacion, IdRegion, IdComuna, Col01..Col50 as text). " + REM_P_CODES + ". Primary value: Col01 at Mes=12",
        stock_or_flow="stock (semiannual population under control)",
        possible_denominator="P2501878 total NANEAS under control only from December 2023; number of reporting establishments; INE population as territorial context",
        definition_breaks="P6 changes from broad PDD (2019-2020) to autism and disaggregated categories (2021); P2501878 exists only from December 2023; June 2020 P2 records only 172 persons in 28 establishments (pandemic reporting collapse); files extracted from the official SERIE_REM_{year}.zip (member names vary by year)",
        linkage_restrictions="Aggregate stocks without persons; not linkable to A05 entries, GRD or education",
        use_rule="December (Mes=12) is the primary series and June the sensitivity; never sum semesters nor average them; always report reporting establishments; reproduce config.CONTROLS p2_*/p6_* December totals",
    ),
    "rem_serie_p_dictionary": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://deis.minsal.cl/#datosabiertos",
        observation_unit="Annual Serie P code dictionary (sheets P2, P6, ...)",
        population_covered="not applicable (metadata)", geography="not applicable",
        codes_columns_used="Sheets P2 and P6: code, label, section, COL01..COLnn (sex/age headers)",
        stock_or_flow="not applicable (dictionary)", possible_denominator="not applicable",
        definition_breaks="Taxonomic break of P6 in 2021; P2501878 added in 2023",
        linkage_restrictions="not applicable", use_rule="Confirm P2/P6 codes and column meaning for each year before extraction",
    ),
    "deis_egresos": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://deis.minsal.cl/#datosabiertos",
        observation_unit="Hospital discharge (egreso) reported to DEIS, one row per discharge",
        population_covered="All discharges from public and private establishments reported to DEIS (broader than the GRD public panel)",
        geography="Residence comuna/region of the patient (COMUNA_RESIDENCIA, 5-digit DEIS code with leading zero) and establishment sector (PERTENENCIA_ESTABLECIMIENTO_SALUD)",
        codes_columns_used="sep=';'; DIAG1, DIAG2 (ICD-10; F84 only in principal or one secondary position), ANO_EGRESO, GRUPO_EDAD, SEXO, COMUNA_RESIDENCIA, REGION_RESIDENCIA, PREVISION, DIAS_ESTADA, CONDICION_EGRESO",
        stock_or_flow="flow (discharges in the year)",
        possible_denominator="All DEIS discharges of the same year; INE population",
        definition_breaks="Only two diagnosis fields (cannot reproduce 'F84 in any of 35 positions'); column set changes across years (2019 header PERTENENCIA_ESTABLECIMIENTO_SALU with ETNIA, INTERV_Q, PROCED; 2024 header PERTENENCIA_ESTABLECIMIENTO_SALUD without them); 2012 and 2021 have an official 15-column variant kept apart",
        linkage_restrictions="No identifier; no linkage to GRD episodes or persons",
        use_rule="External check of the F84-principal/DIAG1-DIAG2 series and of national discharge volumes only; not a substitute for GRD; never combine numerators from GRD with denominators from DEIS",
    ),
    "deis_egresos_dictionary": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://deis.minsal.cl/#datosabiertos",
        observation_unit="Variable dictionary of the DEIS discharge database",
        population_covered="not applicable (metadata)", geography="not applicable", codes_columns_used="Variable names, categories and age groups of DEIS discharges",
        stock_or_flow="not applicable (dictionary)", possible_denominator="not applicable", definition_breaks="Check variant schemas (2012, 2021, 2024)",
        linkage_restrictions="not applicable", use_rule="Interpretation only",
    ),
    "fonasa_aggregates": dict(
        provider="Fondo Nacional de Salud (FONASA)", landing_url="https://datosabiertos.fonasa.cl/dimensiones-beneficiarios/",
        observation_unit="Aggregated cell of FONASA beneficiaries at December (dimension combination x count)",
        population_covered="FONASA beneficiaries at 31 December (national totals 14,841,577 in 2019 to 17,132,611 in 2025)",
        geography="Mixed: comuna of the APS enrolment centre for enrolled persons and domicile for non-enrolled; the variable INSCRITO_APS that separates the mixture disappears from 2023; never treat as homogeneous residence",
        codes_columns_used="Archive member CSV (bsdtar -xf; rar for 2018-2021, zip for 2022-2025). 2018-2020: MES_INFORMACION, TITULAR_CARGA, TRAMO, SEXO, EDAD_TRAMO, NACIONALIDAD, TIPO_ASEGURADO, DIRECCION_ZONAL, SERVICIO_SALUD, REGION, COMUNA, INSCRITO_APS, CUENTA_BENEFICIARIOS; 2021-2022 drop TIPO_ASEGURADO; 2023: TRAMO_FONASA and no INSCRITO_APS/DIRECCION_ZONAL; 2024-2025: REGION, COMUNA, SEXO, EDAD_TRAMO, NACIONALIDAD, TITULAR_CARGA, TRAMO, BENEFICIARIOS",
        stock_or_flow="stock (December snapshot)",
        possible_denominator="Public insurance coverage denominator by comuna, age group and sex (insurance layer, distinct from INE, APS and REM-20)",
        definition_breaks="Schema changes in 2021, 2023, 2024 and 2025; count column renamed CUENTA_BENEFICIARIOS -> BENEFICIARIOS in 2024; 2018-2020 contain repeated rows that are additive fragments of an unexposed dimension; encoding Latin-1 in 2018-2024 members and UTF-8 in the 2025 member; age groups change (e.g. 30 a 39 in 2023)",
        linkage_restrictions="Aggregate; no persons; not linkable to REM or GRD",
        use_rule="Never apply drop_duplicates(): sum all rows; harmonise schema explicitly keeping original columns; use as insurance-coverage layer only; reproduce config.CONTROLS fonasa_beneficiaries_december",
    ),
    "fonasa_dictionary": dict(
        provider="Fondo Nacional de Salud (FONASA)", landing_url="https://datosabiertos.fonasa.cl/dimensiones-beneficiarios/",
        observation_unit="Variable dictionary of FONASA beneficiary publications", population_covered="not applicable (metadata)", geography="not applicable",
        codes_columns_used="Variable definitions (TRAMO, TITULAR_CARGA, EDAD_TRAMO, INSCRITO_APS, ...)", stock_or_flow="not applicable (dictionary)",
        possible_denominator="not applicable", definition_breaks="Confirm version applicable to each year", linkage_restrictions="not applicable", use_rule="Interpretation only",
    ),
    "fonasa_aps": dict(
        provider="FONASA", landing_url="https://public.tableau.com/views/ReporteInscritosCentrosAPS/ReporteAPS?:showVizHome=no",
        observation_unit="Aggregated cell: APS centre x FONASA tramo x age group x sex x TOTAL_INSCRITOS at 31 December",
        population_covered="Persons enrolled in primary-care centres (13,777,051 in 2019 to 15,791,862 in 2025; centres 1,890 to 2,091)",
        geography="Comuna of the APS centre (COD_CENTRO), never residence",
        codes_columns_used="sep=','; PERIODO, SERVICIO_SALUD, REGIÓN, COMUNA, COD_CENTRO, NOMBRE_CENTRO, NOMBRE_DEPENDENCIA/DEPENDENCIA_ADMINISTRATIVA, TRAMO/TRAMO_FONASA, EDAD_TRAMO, SEXO, TOTAL_INSCRITOS",
        stock_or_flow="stock (December snapshot)",
        possible_denominator="Operational coverage per centre (offset for REM primary-care indicators); continuous panel of 1,871 centre codes retains 99.87% of 2019 and 97.54% of 2025 totals",
        definition_breaks="2024: variable names change (NOMBRE_DEPENDENCIA -> DEPENDENCIA_ADMINISTRATIVA, TRAMO -> TRAMO_FONASA) and age groups change; encoding Latin-1 in 2019-2023 and UTF-8 in 2024-2025; centre code 200261 appears reused and 200474 corrected geographically; tramo X and missing tramos must not be mixed without definition",
        linkage_restrictions="Aggregate; no persons",
        use_rule="Use as operational-coverage layer; restrict to tramos A-D when comparing with FONASA 'enrolled' totals (difference < 0.2% in 2019-2022); keep original columns; reproduce config.CONTROLS aps_enrolled_december and aps_centres",
    ),
    "isapre_communal": dict(
        provider="Superintendencia de Salud", landing_url="https://www.superdesalud.gob.cl/tax-biblioteca-digital/estadisticas-3724/estadisticas-por-tema-3741/cartera-de-beneficiarios-3742/",
        observation_unit="Aggregated ISAPRE beneficiaries (cotizantes and cargas) by comuna, age and sex at December",
        population_covered="ISAPRE beneficiaries (3,431,126 in 2019 to 2,517,305 in 2025)",
        geography="Administrative comuna of the beneficiary (as published by the Superintendencia)",
        codes_columns_used="Workbook sheets: 2019-2020 (.xls) Cotizantes, Cargas, Beneficiarios, sex-specific sheets and 'Nonatos o sin Clasificar'; 2021-2025 (.xlsx) Cotizantes, Cargas, sex/SI sheets, Total Cotizantes, Total Cargas",
        stock_or_flow="stock (December snapshot)",
        possible_denominator="Private insurance coverage layer; FONASA + ISAPRE equals 95.63% (2019) and 97.24% (2025) of INE projection (not a non-insurance rate)",
        definition_breaks="Format changes .xls -> .xlsx and single ages -> five-year groups in 2021; separate sheet for unborn/unclassified in 2019-2020; sheets by sex and 'Total' are duplicated views",
        linkage_restrictions="Aggregate; no persons",
        use_rule="Total = cotizantes + cargas (from 2021); never add sex sheets to the Total sheet; reproduce config.CONTROLS isapre_beneficiaries_december",
    ),
    "ine_population_base2017": dict(
        provider="Instituto Nacional de Estadísticas (INE)", landing_url="https://www.ine.gob.cl/estadisticas-por-tema/demografia-y-poblacion/estimaciones-y-proyecciones-de-poblacion",
        observation_unit="Population estimate/projection cell: comuna x sex x single age (or x urban/rural area x age group) x year",
        population_covered="Resident population of Chile, 346 comunas, 2002-2035 (national 19,107,216 in 2019 to 20,206,953 in 2025)",
        geography="Residence comuna (4-digit INE code without leading zero; DEIS uses 5 digits with leading zero); name aliases Aisén/Aysén, Coihaique/Coyhaique, Cabo de Hornos (Ex-Navarino)/Cabo de Hornos",
        codes_columns_used="Region, Nombre Region, Provincia, Nombre Provincia, Comuna, Nombre Comuna, Sexo (1=Hombre 2=Mujer), Edad (80 = open 80+), Poblacion 2002..Poblacion 2035 (sep=','); area file adds Area (1=Urbano 2=Rural) and Grupo edad (sep=';')",
        stock_or_flow="stock (mid-year population)",
        possible_denominator="Territorial population denominator for rates per 100,000 inhabitants and WHO direct standardisation",
        definition_breaks="Base Censo 2017; not to be combined with Censo 2024 / base-2024 figures without an explicit flag",
        linkage_restrictions="Territorial; not users of a specific provider",
        use_rule="Primary population denominator for 2019-2024/25 series; build an auditable comuna crosswalk by code (no silent fuzzy matching); reproduce config.CONTROLS ine_population_national",
    ),
    "ine_censo2024": dict(
        provider="Instituto Nacional de Estadísticas (INE)", landing_url="https://censo2024.ine.gob.cl/estadisticas/",
        observation_unit="Census tabulation: comuna x sex x five-year age group (D1) or disability tabulation (P1)",
        population_covered="Population enumerated in Censo 2024", geography="Comuna of enumeration (census geography)",
        codes_columns_used="Workbook sheets 1-4 of D1 (comuna, sex, five-year age); P1 disability tables",
        stock_or_flow="stock (census night 2024)",
        possible_denominator="Observed 2024 denominator and bridge between census bases (sensitivity)",
        definition_breaks="Different base from the 2017 projections; P1 is disability context, not autism-specific",
        linkage_restrictions="Territorial", use_rule="Sensitivity/bridge only; never mix with base-2017 projections without an explicit flag",
    ),
    "ine_base2024_national": dict(
        provider="Instituto Nacional de Estadísticas (INE)", landing_url="https://www.ine.gob.cl/estadisticas-por-tema/demografia-y-poblacion/estimaciones-y-proyecciones-de-poblacion",
        observation_unit="National population estimate/projection by sex and age, 1992-2070, base Censo 2024",
        population_covered="Resident population of Chile (national level only)", geography="National",
        codes_columns_used="Sheet BBDD_EEPP-2024_0101 (year, sex, age, population)",
        stock_or_flow="stock", possible_denominator="National sensitivity denominator",
        definition_breaks="No comuna disaggregation equivalent to the base-2017 series", linkage_restrictions="not applicable",
        use_rule="National sensitivity and census-base bridge only; flag explicitly when used",
    ),
    "deis_rem20": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://datos.gob.cl/dataset/indicadores-hospitalarios-rem20",
        observation_unit="Establishment x functional area x month (REM-20 hospitalisation process indicators; 167,405 rows, 2014-July 2026, 208 establishments, 29 functional areas)",
        population_covered="Public hospitals reporting REM-20 bed-day and discharge indicators",
        geography="Establishment (CODIGO_ESTABLECIMIENTO, COD_SSS), never residence",
        codes_columns_used="sep=';'; PERIODO, CODIGO_ESTABLECIMIENTO, ESTABLECIMIENTO, COD_AREA_FUNCIONAL, AREA_FUNCIONAL, MES, DIAS_CAMAS_OCUPADAS, DIAS_CAMAS_DISPONIBLES, DIAS_ESTADA, NUMERO_EGRESOS, EGRESOS_FALLECIDOS, INDICE_OCUPACIONAL, PROMEDIO_CAMAS_DISPONIBLE",
        stock_or_flow="activity/capacity (monthly discharges and bed-days; beds are capacity)",
        possible_denominator="Hospital activity/capacity intensity; not a covered population. Panel of 188 establishments with 12 months in every year 2019-2025 retains 99.76% of 2019 and 98.16% of 2025 discharges",
        definition_breaks="Continuously updated mutable dataset (download dated 2026-09-04); no diagnoses or persons",
        linkage_restrictions="Establishment codes link to DEIS catalogue; no persons; compatibility with GRD hospital codes must be verified",
        use_rule="Capacity/activity layer and continuous-panel sensitivity only; never use as covered population; reproduce config.CONTROLS rem20_panel_188_retention",
    ),
    "deis_establishments": dict(
        provider="DEIS, Ministerio de Salud", landing_url="https://datos.gob.cl/dataset/establecimientos-de-salud-vigentes",
        observation_unit="Health establishment (current catalogue; 5,717 records including closed establishments)",
        population_covered="not applicable (supply catalogue)", geography="Comuna and coordinates of the establishment (ComunaCodigo, Latitud, Longitud)",
        codes_columns_used="sep=';'; EstablecimientoCodigo, EstablecimientoCodigoAntiguo, RegionCodigo, ServicioDeSaludCodigo, TipoEstablecimientoGlosa, NivelAtencionEstabglosa, ComunaCodigo, EstadoFuncionamiento, FechaInicioFuncionamientoEstab, FechaCierre",
        stock_or_flow="not applicable (catalogue)", possible_denominator="not applicable",
        definition_breaks="Mutable current catalogue (portal version establecimientos_20260901.csv), not an annual series; many historical dates missing",
        linkage_restrictions="Links all REM-20 codes; historical reporting panel must be derived from observed REM/GRD reporting, not from this file",
        use_rule="Geography and type of supply for establishment codes only; never reconstruct an annual catalogue from it",
    ),
    "endide_2022": dict(
        provider="Ministerio de Desarrollo Social y Familia", landing_url="https://observatorio.ministeriodesarrollosocial.gob.cl/endide-2022",
        observation_unit="Surveyed person (adults, caregivers and children/adolescents), complex sample design",
        population_covered="Household population of Chile, 2022 (national and regional representativeness); unweighted autism reports: 72 adults, 163 children/adolescents, 139 with professional confirmation",
        geography="National and regional; never disaggregate to comuna",
        codes_columns_used="Stata .dta inside the zip (member '230630_Base de datos ENDIDE 2022_adultos cuidadores y NNA.dta.dta'); autism question, professional-confirmation item, weight, stratum and PSU variables as declared in libro_codigos_endide_2022.pdf (declared in module 07, not hard-coded here)",
        stock_or_flow="cross-sectional survey (population benchmark)",
        possible_denominator="Weighted survey population of each domain (adults; children/adolescents)",
        definition_breaks="Self/caregiver report; not equivalent to an administrative F84 code",
        linkage_restrictions="No linkage to registers; benchmark of order of magnitude only",
        use_rule="Estimate proportion, weighted total, SE and 95% CI with weights, strata and clusters (Taylor linearisation); avoid domains with insufficient effective size; preliminary 0.29%/2.86% must be recomputed",
    ),
    "encavi_2023_2024": dict(
        provider="Ministerio de Salud", landing_url="https://datos.gob.cl/dataset/encavi-2023-24",
        observation_unit="Surveyed person aged 15 years or more (16,590 respondents), complex sample design",
        population_covered="Population aged 15+ of Chile, 2023-2024; 80 unweighted positive autism-diagnosis responses",
        geography="National and regional; never comuna",
        codes_columns_used="Stata .dta (resource 20250808_ENCAVI_data.dta); autism diagnosis item, weight, stratum and PSU per manual_base_ENCAVI_2023_2024.pdf (declared in module 07)",
        stock_or_flow="cross-sectional survey (population benchmark)",
        possible_denominator="Weighted population aged 15+",
        definition_breaks="Reported diagnosis; not clinically equivalent to administrative F84",
        linkage_restrictions="No linkage to registers",
        use_rule="Complex-design estimation with 95% CI; preliminary 0.71% (about 114,817 persons) must be recomputed before use",
    ),
    "casen_2024": dict(
        provider="Ministerio de Desarrollo Social y Familia", landing_url="https://observatorio.ministeriodesarrollosocial.gob.cl/encuesta-casen-2024",
        observation_unit="Surveyed person/household (CASEN 2024), complex sample design",
        population_covered="Household population of Chile, 2024 (national and regional representativeness)",
        geography="National/regional; the provincia/comuna complement does not confer comuna representativeness",
        codes_columns_used="Stata .dta (pandas.read_stata); insurance/prevision and poverty variables and design variables per Libro_de_codigos_Casen_2024.xlsx (context only)",
        stock_or_flow="cross-sectional survey (context)",
        possible_denominator="Weighted population by insurance scheme (context for public/private coverage)",
        definition_breaks="Not an autism source; 2024 only",
        linkage_restrictions="No linkage to registers; comuna identifier does not give comuna representativeness",
        use_rule="Context on public insurance use and poverty only; never comuna-level estimates",
    ),
    "casen_2024_metadata": dict(
        provider="Ministerio de Desarrollo Social y Familia", landing_url="https://observatorio.ministeriodesarrollosocial.gob.cl/encuesta-casen-2024",
        observation_unit="Documentation and territorial complement of CASEN 2024 (codebooks, questionnaire, sampling design, usage note, provincia/comuna .dta)",
        population_covered="not applicable (metadata)", geography="not applicable", codes_columns_used="Codebooks define weights, strata and PSU; the provincia/comuna complement links by household/person identifiers per its codebook",
        stock_or_flow="not applicable (documentation)", possible_denominator="not applicable", definition_breaks="not applicable",
        linkage_restrictions="Comuna complement must be linked per codebook; no comuna representativeness", use_rule="Interpretation and design declaration only",
    ),
    "mineduc_pie_reports": dict(
        provider="Ministerio de Educación (Centro de Estudios / SINACES)", landing_url="https://bibliotecadigital.mineduc.cl/",
        observation_unit="Published aggregate tables of students in Programas de Integración Escolar (PIE) by diagnosis",
        population_covered="Students registered in PIE (registration for subsidy/quotas; MINEDUC warns it does not include all autistic students); PIE TEA strict 2019-2023: 11,877; 13,613; 18,801; 28,845; 47,551. TEA-Asperger: 9,135; 9,977; 12,081; 14,095; 16,091. SINACES harmonised 2024-2025: 86,475; 106,786 (special schools 2,505; 2,626)",
        geography="National (and sector where published)",
        codes_columns_used="Tables transcribed from PDFs (Apuntes 59, Apuntes 60, Reporte Ley 21.545 SINACES 2022-2025); categories TEA, TEA-Asperger, special schools",
        stock_or_flow="stock (school-year registration)",
        possible_denominator="Total enrolment in the same PIE/school universe when published",
        definition_breaks="TEA strict vs TEA-Asperger vs harmonised TEA + TEA-Asperger require separate rules; 2022 discrepancy: SINACES report writes 42,945 while 45,014 minus 2,074 special-school students gives 42,940 (Apuntes 60); rule must be explicit",
        linkage_restrictions="Aggregates, no microdata; not linkable to health registers",
        use_rule="Keep TEA strict, TEA-Asperger, harmonised and SINACES series separate; record the five-case discrepancy; interpret as school recognition/demand, never prevalence",
    ),
    "junaeb_eve_microdata": dict(
        provider="Junta Nacional de Auxilio Escolar y Becas (JUNAEB)", landing_url="https://bibliotecadatos.sead.junaeb.cl/",
        observation_unit="De-identified student record of the Encuesta de Vulnerabilidad Estudiantil (EVE), one file per level (parvularia, 1º básico, 5º básico, 1º medio) and year",
        population_covered="Students in selected school cohorts answering the caregiver questionnaire (coverage is selective, not all Chilean students); unweighted TEA 2024: 17,641 / 10,245 / 7,468 (parvularia / 1º básico / 5º básico); 2025: 18,785 / 12,536 / 9,887 / 9,164 (incl. 1º medio)",
        geography="Establishment and comuna of the school (JUNAEB_4_Q1_COMUNA etc.), not residence",
        codes_columns_used="sep=';' CSV; expansion weight EXP (column EXP_REG in the 2024 files, EXP in the 2025 files); the 2019-2023 files carry no expansion-weight column (header scan in module 00: no EXP/ponderador/factor variable), so those years can only be reported unweighted and flagged as such; TEA/autism item defined by the annual questionnaire and dictionary (prolonged medical diagnosis category TEA in 2024-2025); column names lower-case in 2019 and upper-case from 2020",
        stock_or_flow="cross-sectional school survey (caregiver report)",
        possible_denominator="Weighted students of the same level and year",
        definition_breaks="Question wording and codes change by year (dictionaries only for 2019, 2021, 2024, 2025); 2022 files are ANSI/Windows-1252 encoded; 2024 1º medio TEA variable is completely empty (report 'not estimable', never zero)",
        linkage_restrictions="No linkage to PIE, health registers or other years",
        use_rule="Use annual wording and weight EXP; report weighted proportions with CI; never national prevalence nor a series directly comparable with PIE; reproduce config.CONTROLS junaeb_unweighted_2024/2025",
    ),
    "junaeb_eve_metadata": dict(
        provider="Junta Nacional de Auxilio Escolar y Becas (JUNAEB)", landing_url="https://bibliotecadatos.sead.junaeb.cl/",
        observation_unit="EVE questionnaire (PDF) or code dictionary (xlsx) per level and year",
        population_covered="not applicable (metadata)", geography="not applicable",
        codes_columns_used="Question wording and codes of the autism/TEA item and of the expansion weight per year",
        stock_or_flow="not applicable (documentation)", possible_denominator="not applicable",
        definition_breaks="Questionnaires exist for 2019-2025; dictionaries only for 2019, 2021, 2024 and 2025",
        linkage_restrictions="not applicable", use_rule="Cite the exact annual wording before using any EVE variable",
    ),
    "sae_poverty_2024": dict(
        provider="Ministerio de Desarrollo Social y Familia", landing_url="https://observatorio.ministeriodesarrollosocial.gob.cl/pobreza-comunal-2024",
        observation_unit="Small-area estimate (SAE) of income and multidimensional poverty per comuna with confidence interval",
        population_covered="345 comunas, 2024", geography="Comuna (residence)",
        codes_columns_used="Sheet 'Sheet1' of each workbook: comuna code, estimate, lower/upper bounds",
        stock_or_flow="stock (2024 estimate)", possible_denominator="not applicable (covariate)",
        definition_breaks="Estimation uncertainty; 2024 only", linkage_restrictions="Ecological covariate; ecological fallacy",
        use_rule="Prespecified territorial deprivation covariate with its uncertainty; no ecological searches with many covariates",
    ),
    "repo_population_parquet": dict(
        provider="Repository derivative of INE base-2017 projections", landing_url="https://www.ine.gob.cl/estadisticas-por-tema/demografia-y-poblacion/estimaciones-y-proyecciones-de-poblacion",
        observation_unit="Long-format population cell: cut_comuna x edad x género x año (1,905,768 rows)",
        population_covered="Resident population 2002-2035 (INE base 2017), reshaped by the repository", geography="Comuna (cut_comuna, 4-digit INE code) and region",
        codes_columns_used="cut_region, region, cut_provincia, provincia, cut_comuna, comuna, edad, año, población, género",
        stock_or_flow="stock", possible_denominator="Population denominator (same as INE base 2017)",
        definition_breaks="Derived file: must be verified against Poblacion/INE/proyecciones_comuna_edad_sexo_2002_2035_base_2017.csv before use",
        linkage_restrictions="Territorial", use_rule="Use only after reconciliation with the INE source file; git-ignored local file (date = mtime)",
    ),
    "repo_shapes": dict(
        provider="Repository cartography (INE/BCN comuna and region polygons)", landing_url="https://www.ine.gob.cl/herramientas/portal-de-mapas/geodatos-abiertos",
        observation_unit="Polygon feature: comuna (346 features) or region (17 features), EPSG:3857; shapefile components (.shp geometry, .dbf attributes, .shx index, .prj CRS, .cpg encoding)",
        population_covered="not applicable (cartography)", geography="Comuna (cod_comuna) / region (codregion)",
        codes_columns_used="comunas: objectid, cod_comuna, codregion, Region, Comuna, Provincia, geometry; Regional: codregion, Region, geometry",
        stock_or_flow="not applicable", possible_denominator="not applicable",
        definition_breaks="Vintage of the layer must be confirmed against the comuna crosswalk (346 comunas)", linkage_restrictions="Join by code only; no fuzzy name matching",
        use_rule="Maps in supplement only; join by cod_comuna after crosswalk; git-ignored local files (date = mtime)",
    ),
    "rem_pathway_codes": dict(
        provider="Repository (scripts/downloads/rem_pathway_codes.csv, verified against annual REM dictionaries)", landing_url="https://deis.minsal.cl/#datosabiertos",
        observation_unit="Code map row: module x year range x code x domain x unit x aggregation rule x comparability warning (57 rows)",
        population_covered="not applicable (code map)", geography="not applicable",
        codes_columns_used="module, year_start, year_end, code, domain, setting, indicator, unit, aggregation_rule, comparability_warning",
        stock_or_flow="not applicable", possible_denominator="not applicable",
        definition_breaks="Encodes the A03/A05/A27/A28/P2/P6 definition breaks listed in DATA_REVIEW.md",
        linkage_restrictions="not applicable", use_rule="Initial map; each code must be re-confirmed against the annual dictionary in every run",
    ),
}


# ---------------------------------------------------------------------------
# Artefact enumeration
# ---------------------------------------------------------------------------
def _rel(path: Path) -> tuple[str, str]:
    """(root label, relative path) for a path under the data root or the repository."""
    try:
        return "ASESORIAS_DATA_ROOT", str(path.resolve().relative_to(DATA_ROOT.resolve()))
    except ValueError:
        pass
    try:
        return "REPO", str(path.resolve().relative_to(REPO.resolve()))
    except ValueError:
        return "ABSOLUTE", str(path)


def _dict_sa(year: int) -> Path | None:
    d = CFG.PATHS["rem_a_dicts"] / str(year)
    cands = [p for p in d.glob("*") if p.name.startswith(("SA_", "DICCIONARIO CODIGOS SA_"))]
    return cands[0] if len(cands) == 1 else None


def _dict_sp(year: int) -> Path | None:
    d = CFG.PATHS["rem_p_dicts"] / str(year)
    cands = [p for p in d.glob("*.xls*") if not p.name.startswith(".")]
    return cands[0] if len(cands) == 1 else None


def build_artefacts() -> list[dict]:
    """Explicit list of every source artefact (never globs over unknown directories except documented metadata trees)."""
    A: list[dict] = []

    def add(source_id, path: Path, role="data", period="", container="", **over):
        A.append(dict(source_id=source_id, path=Path(path), artefact_role=role, period=period, source_container=container, **over))

    # GRD core and its official dictionaries
    for y in CFG.YEARS_GRD:
        add("grd_publico", CFG.PATHS["grd"] / f"GRD_PUBLICO_{y}.csv", period=str(y))
    for name in ["CIE-10.xlsx", "CIE-9_MC.xlsx", "tablas_maestras_bases_GRD.xlsx"]:
        add("grd_dictionaries", CFG.PATHS["grd_metadata"] / "official" / name, role="dictionary", period="versions published with GRD 2019-2024")
    add("grd_dictionaries", CFG.PATHS["grd_metadata"] / "códigos grd.xlsx", role="dictionary", period="local codebook used by scripts/grd_epidemiology.py")
    # REM Serie A + dictionaries
    for y in CFG.YEARS_REM:
        add("rem_serie_a", CFG.PATHS["rem_a"] / f"SerieA_{y}.csv", period=str(y))
        p = _dict_sa(y)
        add("rem_serie_a_dictionary", p if p else CFG.PATHS["rem_a_dicts"] / str(y) / "MISSING_SA_DICTIONARY", role="dictionary", period=str(y))
    # REM Serie P + dictionaries
    for y in CFG.YEARS_REM:
        add("rem_serie_p", CFG.PATHS["rem_p"] / f"SerieP_{y}.csv", period=str(y))
        p = _dict_sp(y)
        add("rem_serie_p_dictionary", p if p else CFG.PATHS["rem_p_dicts"] / str(y) / "MISSING_SP_DICTIONARY", role="dictionary", period=str(y))
    # DEIS discharges
    for y in CFG.YEARS_GRD:
        add("deis_egresos", CFG.PATHS["deis_egresos"] / f"{y}.csv", period=str(y))
    add("deis_egresos_dictionary", CFG.PATHS["deis_egresos"] / "metadata" / "Diccionario BD egresos hospitalario.xlsx", role="dictionary", period="2001-2024")
    # FONASA aggregates, dictionary, APS
    ext = {2018: "rar", 2019: "rar", 2020: "rar", 2021: "rar", 2022: "zip", 2023: "zip", 2024: "zip", 2025: "zip"}
    for y in years(2018, 2025):
        add("fonasa_aggregates", CFG.PATHS["fonasa"] / f"Resultados_{y}12.{ext[y]}", period=f"December {y}", container="archive member listed at run time")
    add("fonasa_dictionary", CFG.PATHS["fonasa"] / "Diccionario_beneficiarios.xlsx", role="dictionary", period="current")
    for y in years(2019, 2025):
        add("fonasa_aps", CFG.PATHS["fonasa_aps"] / f"Inscritos_APS_{y}12.csv", period=f"31 December {y}")
    # ISAPRE
    for y in years(2019, 2025):
        add("isapre_communal", CFG.PATHS["isapre"] / f"isapre_beneficiarios_comuna_{y}.{'xls' if y <= 2020 else 'xlsx'}", period=f"December {y}")
    # INE
    add("ine_population_base2017", CFG.PATHS["ine"] / "proyecciones_comuna_edad_sexo_2002_2035_base_2017.csv", period="2002-2035 (base Censo 2017)")
    add("ine_population_base2017", CFG.PATHS["ine"] / "proyecciones_comuna_area_urbana_rural_2002_2035_base_2017.csv", period="2002-2035 (base Censo 2017)")
    add("ine_censo2024", CFG.PATHS["ine"] / "Censo_2024" / "D1_poblacion_comuna_sexo_edad_quinquenal.xlsx", period="Censo 2024")
    add("ine_censo2024", CFG.PATHS["ine"] / "Censo_2024" / "P1_Discapacidad.xlsx", period="Censo 2024", role="context")
    add("ine_base2024_national", CFG.PATHS["ine"] / "Base_2024" / "estimaciones_proyecciones_nacionales_1992_2070_base_2024.xlsx", period="1992-2070 (base Censo 2024)")
    # DEIS REM-20 and establishments
    add("deis_rem20", CFG.PATHS["rem20"] / "indicadores_rem20.csv", period="2014-07/2026 (continuous update)")
    add("deis_rem20", CFG.PATHS["rem20"] / "diccionario_rem20.xlsx", role="dictionary", period="current")
    add("deis_establishments", CFG.PATHS["establecimientos"] / "establecimientos_salud_vigentes.csv", period="current catalogue (portal file establecimientos_20260901.csv)")
    add("deis_establishments", CFG.PATHS["establecimientos"] / "diccionario_establecimientos.pdf", role="dictionary", period="current")
    # Surveys
    add("endide_2022", CFG.PATHS["endide"] / "endide_2022_adultos_cuidadores_nna.dta.zip", period="2022", container="230630_Base de datos ENDIDE 2022_adultos cuidadores y NNA.dta.dta")
    add("endide_2022", CFG.PATHS["endide"] / "libro_codigos_endide_2022.pdf", role="documentation", period="2022")
    add("endide_2022", CFG.PATHS["endide"] / "metodologia_diseno_muestral_endide_2022.pdf", role="documentation", period="2022")
    add("encavi_2023_2024", CFG.PATHS["encavi"] / "ENCAVI_2023_2024.dta", period="2023-2024")
    add("encavi_2023_2024", CFG.PATHS["encavi"] / "cuestionario_ENCAVI_2023_2024.pdf", role="documentation", period="2023-2024")
    add("encavi_2023_2024", CFG.PATHS["encavi"] / "manual_base_ENCAVI_2023_2024.pdf", role="documentation", period="2023-2024")
    add("casen_2024", CFG.PATHS["casen"] / "casen_2024.dta", period="2024")
    for name in ["casen_2024_provincia_comuna.dta", "Libro_de_codigos_Casen_2024.xlsx", "Libro_de_codigos_Casen_2024_prov_comuna.xlsx",
                 "Cuestionario_Casen_2024.pdf", "Diseno_Muestral_Casen_2024.pdf", "Ficha_tecnica_Casen_2024.pdf",
                 "Informe_metodologico_casen_2024.pdf", "Nota_uso_bases_de_datos_Casen_2024.pdf"]:
        add("casen_2024_metadata", CFG.PATHS["casen"] / "metadata" / name, role="documentation", period="2024")
    # Education
    add("mineduc_pie_reports", CFG.PATHS["mineduc"] / "APUNTES_59_2024_PIE_sexo_2023.pdf", period="2023 (PIE by sex)")
    add("mineduc_pie_reports", CFG.PATHS["mineduc"] / "APUNTES_60_2024_tendencia_PIE_2019_2023.pdf", period="2019-2023 (PIE trend)")
    add("mineduc_pie_reports", CFG.PATHS["mineduc"] / "Reporte_Ley_21545_SINACES_2022_2025.pdf", period="2022-2025 (SINACES report)")
    micro = CFG.PATHS["junaeb"] / "microdata"
    for y in years(2019, 2025):
        for p in sorted((micro / str(y)).glob("*.csv")):
            add("junaeb_eve_microdata", p, period=str(y))
    meta = CFG.PATHS["junaeb"] / "metadata"
    for p in sorted(meta.glob("Cuestionarios/*/*.pdf")) + sorted(meta.glob("Diccionarios/*/*.xlsx")):
        add("junaeb_eve_metadata", p, role="documentation", period=p.parent.name)
    for name in ["SAE_ingresos_2024.xlsx", "SAE_multidimensional_2024.xlsx"]:
        add("sae_poverty_2024", CFG.PATHS["sae"] / name, period="2024")
    add("sae_poverty_2024", CFG.PATHS["sae"] / "metodologia_estimaciones_SAE_2024.pdf", role="documentation", period="2024")
    # Repository artefacts
    add("repo_population_parquet", CFG.PATHS["repo_population_parquet"], period="2002-2035")
    for stem in ["comunas", "Regional"]:
        for comp in [".shp", ".dbf", ".shx", ".prj"]:
            add("repo_shapes", REPO / "data" / f"{stem}{comp}", period="current layer")
        cpg = next(iter(sorted((REPO / "data").glob(f"{stem}.[cC][pP][gG]"))), None)
        if cpg is not None:
            add("repo_shapes", cpg, period="current layer")
    add("rem_pathway_codes", CFG.PATHS["rem_pathway_codes"], role="code map", period="2019-2025")
    return A


EXPECTED_UNLISTED = 21  # artefacts that no manifest lists: 7 local SA dictionaries, códigos grd.xlsx, DEIS egresos dictionary, 12 repository files
EXPECTED_COUNTS = {  # artefacts enumerated by the study brief (module 00 task)
    "grd_publico": 6, "grd_dictionaries": 4, "rem_serie_a": 7, "rem_serie_a_dictionary": 7, "rem_serie_p": 7, "rem_serie_p_dictionary": 7,
    "deis_egresos": 6, "deis_egresos_dictionary": 1, "fonasa_aggregates": 8, "fonasa_dictionary": 1, "fonasa_aps": 7, "isapre_communal": 7,
    "ine_population_base2017": 2, "ine_censo2024": 2, "ine_base2024_national": 1, "deis_rem20": 2, "deis_establishments": 2,
    "endide_2022": 3, "encavi_2023_2024": 3, "casen_2024": 1, "casen_2024_metadata": 8, "mineduc_pie_reports": 3,
    "junaeb_eve_microdata": 28, "junaeb_eve_metadata": 44, "sae_poverty_2024": 3, "repo_population_parquet": 1, "repo_shapes": 10, "rem_pathway_codes": 1,
}


# ---------------------------------------------------------------------------
# Manifests
# ---------------------------------------------------------------------------
def load_manifests() -> tuple[dict[Path, list[dict]], dict]:
    """Map resolved path -> list of manifest entries {manifest, sha256, bytes, date, note}. Also returns manifest stats."""
    entries: dict[Path, list[dict]] = {}
    stats: dict = {}

    def put(path: Path, **e):
        entries.setdefault(path.resolve(), []).append(e)

    # 1. Autism/metadata/download_manifest.csv (storage project -> AUTISM_ROOT; shared -> DATA_ROOT). Last row per path wins.
    dm = CFG.PATHS["download_manifest"]
    if dm.is_file():
        df = pd.read_csv(dm, dtype=str).fillna("")
        stats["download_manifest_rows"] = len(df)
        stats["download_manifest_unique_paths"] = df[["storage", "relative_path"]].drop_duplicates().shape[0]
        last = df.groupby(["storage", "relative_path"], sort=False).tail(1)
        for r in last.itertuples(index=False):
            base = AUTISM_ROOT if r.storage == "project" else DATA_ROOT
            put(base / r.relative_path, manifest="Autism/metadata/download_manifest.csv", sha256=r.sha256, bytes=int(r.bytes) if r.bytes else None,
                date=r.downloaded_at_utc[:10], date_label="download_manifest.csv downloaded_at_utc", note=f"status={r.status}; source_url={r.source_url}")
    # 2. FONASA/metadata/source_manifest.csv
    fm = CFG.PATHS["fonasa"] / "metadata" / "source_manifest.csv"
    if fm.is_file():
        df = pd.read_csv(fm, dtype=str)
        stats["fonasa_source_manifest_rows"] = len(df)
        for r in df.itertuples(index=False):
            put(CFG.PATHS["fonasa"] / r.relative_path, manifest="FONASA/metadata/source_manifest.csv", sha256=r.sha256, bytes=int(r.size_bytes), date="", note="no date in manifest (consolidated 2026-09-02 per data-root README)")
    # 3. REM/SerieP/manifest_extract_rem_series_p.csv
    pm = CFG.PATHS["rem_p"] / "manifest_extract_rem_series_p.csv"
    if pm.is_file():
        df = pd.read_csv(pm, dtype=str)
        stats["seriep_manifest_rows"] = len(df)
        for r in df.itertuples(index=False):
            put(CFG.PATHS["rem_p"] / r.destination, manifest="REM/SerieP/manifest_extract_rem_series_p.csv", sha256=r.sha256, bytes=int(r.bytes),
                date=r.processed_at_utc[:10], date_label="manifest_extract_rem_series_p.csv processed_at_utc", note=f"status={r.status}; source_zip={Path(r.source_zip).name}; member={r.source_member}")
    # 4. REM/SerieA/metadata/canonical_manifest.csv (+ .rem_manifest.json for normalisation date)
    am = CFG.PATHS["rem_a"] / "metadata" / "canonical_manifest.csv"
    norm_dates = {}
    rj = CFG.PATHS["rem_a"] / ".rem_manifest.json"
    if rj.is_file():
        try:
            norm_dates = {k: v.get("normalizado_en", "")[:10] for k, v in json.load(open(rj, encoding="utf-8")).items()}
        except Exception:  # noqa: BLE001
            norm_dates = {}
    if am.is_file():
        df = pd.read_csv(am, dtype=str)
        stats["seriea_canonical_manifest_rows"] = len(df)
        for r in df.itertuples(index=False):
            put(CFG.PATHS["rem_a"] / r.file, manifest="REM/SerieA/metadata/canonical_manifest.csv", sha256=r.sha256, bytes=int(r.size_bytes),
                date=norm_dates.get(r.file, ""), date_label="REM/SerieA/.rem_manifest.json normalizado_en", note="date = normalisation date in REM/SerieA/.rem_manifest.json" if norm_dates.get(r.file) else "no date in manifest")
    # 5. DEIS/Egresos/metadata/canonical_manifest.csv
    em = CFG.PATHS["deis_egresos"] / "metadata" / "canonical_manifest.csv"
    if em.is_file():
        df = pd.read_csv(em, dtype=str)
        stats["egresos_canonical_manifest_rows"] = len(df)
        for r in df.itertuples(index=False):
            put(CFG.PATHS["deis_egresos"] / r.file, manifest="DEIS/Egresos/metadata/canonical_manifest.csv", sha256=r.sha256, bytes=int(r.size_bytes), date="", note="no date in manifest")
    # 6. GRD/metadata/SOURCES_MANIFEST.md (markdown table of canonical files)
    gm = CFG.PATHS["grd_metadata"] / "SOURCES_MANIFEST.md"
    if gm.is_file():
        text = gm.read_text(encoding="utf-8")
        m = re.search(r"Fecha de consolidaci[oó]n:\s*(\d{4}-\d{2}-\d{2})", text)
        cdate = m.group(1) if m else ""
        n = 0
        for row in re.finditer(r"^\|\s*`(GRD_PUBLICO_\d{4}\.csv)`\s*\|\s*([\d,]+)\s*\|\s*`([0-9a-f]{64})`\s*\|", text, flags=re.M):
            put(CFG.PATHS["grd"] / row.group(1), manifest="GRD/metadata/SOURCES_MANIFEST.md", sha256=row.group(3), bytes=None, date=cdate, date_label="SOURCES_MANIFEST.md consolidation date",
                note=f"canonical records={row.group(2)}; date = consolidation date of the manifest")
            n += 1
        stats["grd_sources_manifest_rows"] = n
    return entries, stats


# ---------------------------------------------------------------------------
# Hashing with progress (common.sha256_file streams 1 MiB blocks)
# ---------------------------------------------------------------------------
def load_cache() -> dict:
    if CACHE_PATH.is_file():
        try:
            return json.load(open(CACHE_PATH, encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def hash_all(arts: list[dict], use_cache: bool) -> None:
    cache = load_cache() if use_cache else {}
    present = [a for a in arts if a["path"].is_file()]
    total = sum(a["path"].stat().st_size for a in present)
    done = 0
    t0 = time.time()
    print(f"[{MODULE}] hashing {len(present)} files, {total / 1e9:.2f} GB (cache={'on' if use_cache else 'off'})", flush=True)
    for i, a in enumerate(present, 1):
        p = a["path"]
        st = p.stat()
        key = f"{p.resolve()}|{st.st_size}|{st.st_mtime_ns}"
        t1 = time.time()
        if use_cache and key in cache:
            a["sha256"], how = cache[key], "cache"
        else:
            a["sha256"], how = M.sha256_file(p), "sha256"
            cache[key] = a["sha256"]
        done += st.st_size
        dt = max(time.time() - t1, 1e-9)
        rate = st.st_size / dt / 1e6 if how == "sha256" else float("nan")
        print(f"  [{i:3d}/{len(present)}] {done / total * 100:5.1f}% {st.st_size / 1e6:9.1f} MB {how:6s} {rate:7.0f} MB/s  {p.name}  ({time.time() - t0:.0f}s)", flush=True)
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    M.atomic_write_json(cache, CACHE_PATH)


def archive_member(path: Path) -> str:
    """Member names of a rar/zip archive via bsdtar -tf (cheap; no extraction)."""
    import subprocess
    try:
        out = subprocess.run(["bsdtar", "-tf", str(path)], capture_output=True, text=True, timeout=120, check=True).stdout
        return "; ".join(l.strip() for l in out.splitlines() if l.strip())
    except Exception as exc:  # noqa: BLE001
        return f"bsdtar unavailable: {exc}"


def junaeb_weight_columns(arts: list[dict]) -> dict[str, str]:
    """Expansion-weight column present in each JUNAEB EVE microdata file (header line only; files are ';'-separated).

    Returns {file name: column name or 'none'}. Matches EXP, EXP_REG or any header containing PONDERADOR/FACTOR_EXP/FEXP
    (case-insensitive); nothing else is read, so 2022 Windows-1252 files are decoded as latin-1 without loss for this purpose.
    """
    out: dict[str, str] = {}
    pat = re.compile(r"^(EXP(_REG)?|.*PONDERADOR.*|.*FACTOR_?EXP.*|.*FEXP.*)$", re.I)
    for a in arts:
        if a["source_id"] != "junaeb_eve_microdata" or not a["path"].is_file():
            continue
        with open(a["path"], "rb") as fh:
            header = fh.readline().decode("latin-1").strip().lstrip("\ufeff")
        cols = [c.strip().strip('"') for c in header.split(";")]
        hits = [c for c in cols if pat.match(c)]
        out[a["path"].name] = hits[0] if hits else "none"
    return out


# ---------------------------------------------------------------------------
# Assemble rows and controls
# ---------------------------------------------------------------------------
def assemble(arts: list[dict], manifests: dict[Path, list[dict]]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows, checks = [], []
    for a in arts:
        p: Path = a["path"]
        desc = SOURCES[a["source_id"]]
        root, rel = _rel(p)
        exists = p.is_file()
        st = p.stat() if exists else None
        mtime = datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).strftime("%Y-%m-%d") if st else ""
        ents = manifests.get(p.resolve(), []) if exists else []
        m_names = "; ".join(e["manifest"] for e in ents)
        m_sha = "; ".join(sorted({e["sha256"] for e in ents}))
        m_bytes = "; ".join(sorted({str(e["bytes"]) for e in ents if e.get("bytes") is not None}))
        sha_ok = "not_listed" if not ents else str(all(e["sha256"] == a.get("sha256") for e in ents))
        b_ok = "not_listed" if not any(e.get("bytes") is not None for e in ents) else str(all(e["bytes"] == st.st_size for e in ents if e.get("bytes") is not None))
        dated = sorted((e for e in ents if e.get("date")), key=lambda e: e["date"])
        if dated:
            latest = dated[-1]
            date = f"{latest['date']} ({latest.get('date_label', latest['manifest'].split('/')[-1])})"
            if mtime and mtime != latest["date"]:
                date += f"; file mtime {mtime}"
        elif exists:
            date = f"{mtime} (file mtime; not dated in any manifest)"
        else:
            date = "MISSING"
        container = a.get("source_container", "")
        if exists and p.suffix.lower() in {".rar", ".zip"} and a["source_id"] in {"fonasa_aggregates", "endide_2022"}:
            container = archive_member(p)
        notes = " | ".join(e.get("note", "") for e in ents if e.get("note"))
        if a["source_id"] == "rem_serie_p" and notes:
            container = notes
        rows.append({
            "source_id": a["source_id"], "file": p.name, "relative_path": rel, "bytes": st.st_size if st else None, "sha256": a.get("sha256", ""),
            "downloaded_or_version_date": date, "observation_unit": desc["observation_unit"], "period": a["period"],
            "population_covered": desc["population_covered"], "geography": desc["geography"], "codes_columns_used": desc["codes_columns_used"],
            "stock_or_flow": desc["stock_or_flow"], "possible_denominator": desc["possible_denominator"], "definition_breaks": desc["definition_breaks"],
            "linkage_restrictions": desc["linkage_restrictions"], "use_rule": desc["use_rule"],
            "root": root, "artefact_role": a["artefact_role"], "provider": desc["provider"], "source_container": container,
            "manifest_source": m_names, "manifest_sha256": m_sha, "sha256_matches_manifest": sha_ok, "manifest_bytes": m_bytes,
            "bytes_match_manifest": b_ok, "file_mtime_utc": mtime, "landing_url": desc["landing_url"],
        })
        for e in ents:
            checks.append({"source_id": a["source_id"], "file": p.name, "relative_path": rel, "manifest": e["manifest"], "manifest_sha256": e["sha256"],
                           "observed_sha256": a.get("sha256", ""), "sha256_match": e["sha256"] == a.get("sha256"), "manifest_bytes": e.get("bytes"),
                           "observed_bytes": st.st_size if st else None, "bytes_match": (e.get("bytes") == st.st_size) if e.get("bytes") is not None and st else None,
                           "manifest_date": e.get("date", ""), "manifest_note": e.get("note", "")})
        if exists and not ents:
            checks.append({"source_id": a["source_id"], "file": p.name, "relative_path": rel, "manifest": "", "manifest_sha256": "", "observed_sha256": a.get("sha256", ""),
                           "sha256_match": None, "manifest_bytes": None, "observed_bytes": st.st_size, "bytes_match": None, "manifest_date": "", "manifest_note": "not listed in any manifest"})
    prov = pd.DataFrame(rows)[REQUIRED_COLUMNS + EXTRA_COLUMNS]
    return prov, pd.DataFrame(checks)


def control_row(name, key, expected, observed, note="", tol=0.0):
    try:
        e, o = float(expected), float(observed)
        diff = o - e
        rel = diff / e if e else (0.0 if diff == 0 else float("inf"))
        status = "ok" if (diff == 0 or abs(rel) <= tol) else "differs"
    except (TypeError, ValueError):
        diff, rel = None, None
        status = "ok" if str(expected) == str(observed) else "differs"
    return dict(name=name, key=key, expected=expected, observed=observed, abs_diff=diff, rel_diff=rel, status=status, note=note)


def controls(prov: pd.DataFrame, checks: pd.DataFrame, stats: dict, arts: list[dict]) -> pd.DataFrame:
    C = []
    present = prov[prov.bytes.notna()]
    counts = present.groupby("source_id").size()
    for sid, exp in EXPECTED_COUNTS.items():
        C.append(control_row("artefact_count_by_source", sid, exp, int(counts.get(sid, 0)), "expected = artefacts enumerated in the module brief"))
    C.append(control_row("artefact_count_total", "all", sum(EXPECTED_COUNTS.values()), int(len(present))))
    C.append(control_row("artefacts_missing_on_disk", "all", 0, int(prov.bytes.isna().sum()), "; ".join(prov.loc[prov.bytes.isna(), "relative_path"])))
    # Bytes: expected from manifests where the file is listed (else on-disk size); observed from stat.
    def exp_bytes(r):
        if r["manifest_bytes"] and r["manifest_bytes"] not in ("", "None"):
            vals = {int(v) for v in str(r["manifest_bytes"]).split("; ")}
            return min(vals) if len(vals) == 1 else None
        return r["bytes"]
    eb = present.apply(exp_bytes, axis=1)
    for sid, grp in present.groupby("source_id"):
        e = eb.loc[grp.index]
        C.append(control_row("bytes_by_source", sid, int(e.sum()) if e.notna().all() else "conflicting manifests", int(grp.bytes.sum()),
                             "expected = manifest bytes where listed, on-disk bytes otherwise"))
    C.append(control_row("bytes_total", "all", int(eb.sum()) if eb.notna().all() else "conflicting manifests", int(present.bytes.sum()), "expected = manifest bytes where listed, on-disk bytes otherwise"))
    C.append(control_row("bytes_total_gb", "all", round(int(eb.sum()) / 1e9, 3) if eb.notna().all() else "not applicable", round(int(present.bytes.sum()) / 1e9, 3)))
    # Manifest agreement
    listed = checks[checks.manifest != ""]
    n_listed_files = listed[["relative_path"]].drop_duplicates().shape[0]
    C.append(control_row("manifest_listed_artefacts", "all", sum(EXPECTED_COUNTS.values()) - EXPECTED_UNLISTED, n_listed_files, "artefacts listed in at least one manifest"))
    C.append(control_row("manifest_unlisted_artefacts", "all", EXPECTED_UNLISTED, int((present.sha256_matches_manifest == "not_listed").sum()),
                         "by design: local REM Serie A dictionaries (7), GRD and DEIS local codebooks (2), repository files (12); observed = " + "; ".join(sorted(set(present.loc[present.sha256_matches_manifest == "not_listed", "source_id"])))))
    C.append(control_row("manifest_sha256_agreement_rate", "all", 1.0, round(float(listed.sha256_match.mean()), 6) if len(listed) else "not applicable", f"{int(listed.sha256_match.sum())}/{len(listed)} manifest entries agree"))
    C.append(control_row("manifest_sha256_mismatches", "all", 0, int((~listed.sha256_match.astype(bool)).sum()), "; ".join(listed.loc[~listed.sha256_match.astype(bool), "relative_path"])))
    lb = listed[listed.bytes_match.notna()]
    C.append(control_row("manifest_bytes_agreement_rate", "all", 1.0, round(float(lb.bytes_match.astype(bool).mean()), 6) if len(lb) else "not applicable", f"{int(lb.bytes_match.astype(bool).sum())}/{len(lb)} entries with bytes agree"))
    for mname, grp in listed.groupby("manifest"):
        C.append(control_row("manifest_sha256_agreement_rate_by_manifest", mname, 1.0, round(float(grp.sha256_match.mean()), 6), f"{int(grp.sha256_match.sum())}/{len(grp)}"))
    # Manifest sizes documented in DATA_REVIEW.md / data-root README
    C.append(control_row("download_manifest_rows", "Autism/metadata/download_manifest.csv", 143, stats.get("download_manifest_rows"), "DATA_REVIEW.md: 143 artefactos adquiridos"))
    C.append(control_row("seriep_manifest_rows", "REM/SerieP/manifest_extract_rem_series_p.csv", 14, stats.get("seriep_manifest_rows"), "DATA_REVIEW.md: 14 artefactos (7 CSV + 7 diccionarios)"))
    C.append(control_row("fonasa_source_manifest_rows", "FONASA/metadata/source_manifest.csv", 7, stats.get("fonasa_source_manifest_rows"), "data-root README: siete archivos preservados"))
    C.append(control_row("grd_sources_manifest_rows", "GRD/metadata/SOURCES_MANIFEST.md", 6, stats.get("grd_sources_manifest_rows"), "canonical SHA table parsed from markdown"))
    # Byte totals documented in DATA_REVIEW.md
    j = present[present.source_id == "junaeb_eve_microdata"]
    C.append(control_row("junaeb_microdata_files", "2019-2025", 28, int(len(j)), "DATA_REVIEW.md"))
    C.append(control_row("junaeb_microdata_bytes", "2019-2025", 9_625_722_727, int(j.bytes.sum()), "DATA_REVIEW.md: 9.625.722.727 bytes"))
    # Expansion-weight column per JUNAEB year: DATA_REVIEW.md documents weighted (EXP) results only for 2024-2025; the 2019-2023
    # files carry no weight column, so the provenance row must not suggest one exists (header scan, no data read).
    wcols = junaeb_weight_columns(arts)
    exp_w = {2019: "none", 2020: "none", 2021: "none", 2022: "none", 2023: "none", 2024: "EXP_REG", 2025: "EXP"}
    for y, exp in exp_w.items():
        obs = sorted({v for k, v in wcols.items() if str(y) in k}) or ["no file"]
        C.append(control_row("junaeb_weight_column", str(y), exp, "; ".join(obs),
                             "DATA_REVIEW.md: ponderador EXP in 2024-2025 (EXP_REG in the 2024 headers); 2019-2023 headers have no EXP/ponderador/factor column"))
    c = present[(present.source_id == "casen_2024")]
    C.append(control_row("casen_2024_bytes", "casen_2024.dta", 1_608_073_353, int(c.bytes.sum()), "source_catalog.json / DATA_REVIEW.md"))
    # Official REM containers referenced by the Serie P manifest must exist (traceability of the extraction)
    zips = [CFG.PATHS["rem_a"] / "sources" / "official_zips" / f"SERIE_REM_{y}.zip" for y in CFG.YEARS_REM]
    C.append(control_row("rem_official_zips_present", "SERIE_REM_2019..2025.zip", len(zips), sum(z.is_file() for z in zips), "containers of Serie P extraction (not analysed directly)"))
    # GRD 2022 canonical record count documented (932,839) is checked in module 01; here only the manifest note is carried.
    df = pd.DataFrame(C)
    def _int_if_integral(v):
        return int(v) if isinstance(v, (int, float)) and not isinstance(v, bool) and pd.notna(v) and float(v).is_integer() else v
    for col in ("expected", "observed", "abs_diff"):
        df[col] = pd.Series([_int_if_integral(v) for v in df[col]], index=df.index, dtype=object)
    return df


def summary_by_source(prov: pd.DataFrame) -> pd.DataFrame:
    present = prov[prov.bytes.notna()].copy()
    g = present.groupby("source_id").agg(n_artefacts=("file", "size"), bytes_total=("bytes", "sum"), n_listed_in_manifest=("sha256_matches_manifest", lambda s: int((s != "not_listed").sum())),
                                          n_sha_match=("sha256_matches_manifest", lambda s: int((s == "True").sum())), n_sha_mismatch=("sha256_matches_manifest", lambda s: int((s == "False").sum())),
                                          stock_or_flow=("stock_or_flow", "first"), provider=("provider", "first")).reset_index()
    g["gb"] = (g.bytes_total / 1e9).round(3)
    g["unit_bytes"] = "bytes"
    order = list(EXPECTED_COUNTS)
    g["order"] = g.source_id.map({s: i for i, s in enumerate(order)})
    return g.sort_values("order").drop(columns="order")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--use-cache", action="store_true", help="reuse SHA-256 from outputs/.cache when path, size and mtime are unchanged (development only)")
    ap.add_argument("--limit", type=int, default=None, help="hash only the first N artefacts (smoke test)")
    args = ap.parse_args(argv)
    t0 = time.time()
    if not DATA_ROOT.is_dir():
        print(f"[{MODULE}] data root not mounted: {DATA_ROOT}", file=sys.stderr)
        return 2
    arts = build_artefacts()
    if args.limit:
        arts = arts[: args.limit]
    manifests, stats = load_manifests()
    print(f"[{MODULE}] manifests: {stats}", flush=True)
    hash_all(arts, use_cache=args.use_cache)
    prov, checks = assemble(arts, manifests)
    ctrl = controls(prov, checks, stats, arts)
    summ = summary_by_source(prov)
    out_main = HERE / "data_provenance.csv"
    M.atomic_write_csv(prov, out_main)
    M.atomic_write_csv(prov, CFG.TIDY / "data_provenance.csv")
    M.atomic_write_csv(checks, CFG.TIDY / "provenance_manifest_checks.csv")
    M.atomic_write_csv(summ, CFG.TIDY / "provenance_summary_by_source.csv")
    M.atomic_write_csv(ctrl, CONTROLS_DIR / f"{MODULE}_controls.csv")
    runtime = time.time() - t0
    n_diff = int((ctrl.status == "differs").sum())
    print(f"\n[{MODULE}] {len(prov)} artefacts, {prov.bytes.sum() / 1e9:.2f} GB; controls: {int((ctrl.status == 'ok').sum())} ok, {n_diff} differ; runtime {runtime:.1f}s")
    if n_diff:
        print(ctrl[ctrl.status == "differs"].to_string(index=False))
    print(f"[{MODULE}] wrote {out_main}, {CFG.TIDY / 'data_provenance.csv'}, {CONTROLS_DIR / (MODULE + '_controls.csv')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
