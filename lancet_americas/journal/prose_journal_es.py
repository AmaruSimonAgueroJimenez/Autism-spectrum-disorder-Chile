# -*- coding: utf-8 -*-
"""prose_journal_es.py — versión española de trabajo del artículo enviado (sin_rett) a The Lancet Regional Health – Americas.

API pública
-----------
    article(V, plate_dir=None) -> lista de bloques de docx_builder con la MISMA estructura que prose_journal_en.article:
        portada, Resumen (cinco párrafos), panel «Investigación en contexto», Introducción … Conclusión, las
        declaraciones, ("refs", None), Tabla 1, Tabla 2, Figuras 1–4.

Convenciones
------------
* Traducción fiel de prose_journal_en.py, párrafo por párrafo: mismas claves de V en el mismo orden, mismas claves
  de citación [@clave] en el mismo orden y mismas llamadas R.fig()/R.tab() en el mismo orden, de modo que la
  numeración del apéndice es idéntica. Los recuentos de tablas depositadas usan las claves «_en» del archivo de
  valores en ambos idiomas (los valores «_es» son iguales; así la paridad numérica se garantiza por construcción).
* Ninguna cifra literal: todo número procede de V a través de prose_es (coma decimal, punto de miles, espacio
  duro antes de «%», «IC 95 %») o de una fila tidy mediante journal_config; los intervalos se imprimen «a–b».
* Las leyendas de las láminas del cuerpo y las notas de las dos tablas se ensamblan con fragmentos LITERALES de las
  leyendas y notas españolas del corpus (outputs/sin_rett/es), como en el inglés.
* El español es la versión de trabajo del equipo autor: conserva las convenciones numéricas del corpus (sin pase de
  número de la revista) y no se construye su suplemento (existe el corpus bilingüe completo).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(HERE), str(ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)
import common as C  # noqa: E402  (the single source of the fixed-panel gloss)
import controls_registry as CR  # noqa: E402
import journal_config as JC  # noqa: E402
import supplementary_material as SM  # noqa: E402
import prose_en as PE  # noqa: E402
import prose_es as PS  # noqa: E402
from prose_es import (AFFILIATION, CI95, NBSP, RUNNING_TITLE, TITLE, millions, n0, n1, n2, nw, pct, ppct)  # noqa: E402
from prose_en import AUTHOR, AUTHOR_EMAIL, YEARS_A05, YEARS_A27, YEARS_GRD, YEARS_REM  # noqa: E402
from prose_journal_en import M_TABLES, PLAN_DATE, assemble_fragments, territory_numbers  # noqa: E402
from prose_journal_en import (GRD_AGE_BANDS_0_9, GRD_AGE_BANDS_20PLUS, a05_age_0_9_count,  # noqa: E402
                              grd_age_count)
from prose_journal_en import _eq, _eqs  # noqa: E402

LANG = "es"
VARIANT = JC.VARIANT
VLABEL = "familia F84 sin síndrome de Rett (F84.2)"
PLAN_DATE_ES = "4 de septiembre de 2026"
assert PLAN_DATE == "4 September 2026"


def cir(lo, hi, dec=1) -> str:
    return f"{PE.fmt_number(lo, dec, LANG)}–{PE.fmt_number(hi, dec, LANG)}"


class _K:
    def __init__(self, V: dict):
        self.k = PS._V(V, VARIANT)

    def __call__(self, key):
        return self.k(key)

    def series(self, tmpl, years, dec=0):
        return self.k.series(tmpl, years, dec)

    def apc(self, alias, dec=1):
        return f"{PE.fmt_number(self(alias), dec, LANG)}{NBSP}% ({CI95} {cir(self(alias + '_lo'), self(alias + '_hi'), dec)})"

    def rate(self, prefix, year, dec=1):
        return (f"{PE.fmt_number(self(f'{prefix}_rate_{year}'), dec, LANG)} ({CI95} "
                f"{cir(self(f'{prefix}_rate_lo_{year}'), self(f'{prefix}_rate_hi_{year}'), dec)})")

    def est_y(self, prefix, year, dec=1):
        return (f"{PE.fmt_number(self(f'{prefix}_{year}'), dec, LANG)} ({CI95} "
                f"{cir(self(f'{prefix}_lo_{year}'), self(f'{prefix}_hi_{year}'), dec)})")

    def svy(self, base, dec=2):
        return f"{pct(self(base + '_pct'), dec)} ({CI95} {cir(self(base + '_lo_pct'), self(base + '_hi_pct'), dec)})"


# ---------------------------------------------------------------------------
# Leyendas y notas del cuerpo (fragmentos literales de las leyendas/notas españolas del corpus)
# ---------------------------------------------------------------------------
def _legend_parts(R: JC.JournalRegistry) -> dict:
    return {
        "fig1_dataflow": [
            "Ningún registro se enlaza entre sistemas: los seis carriles no comparten identificador; nada dibujado es "
            "una trayectoria ni una cascada, y una persona puede estar contada en más de un carril.",
            "Las personas se cuentan solo dentro de un año: el identificador del GRD cambia de formato entre 2020 y 2021.",
            "Los recuentos son reconocimiento administrativo, no prevalencia ni incidencia; en el GRD son «episodios "
            "con F84 documentado» y F84 principal es una serie aparte; stocks y flujos nunca comparten eje; cero, "
            "ausente y «sin reporte» son distintos; lugar de atención y residencia nunca se mezclan sin advertirlo;",
            "~las celdas territoriales con menos de cinco eventos se suprimen;",
            "y no se estima ningún efecto de la Ley 21.545 (marzo de 2023).",
            f"~Cada cifra impresa, con su unidad, origen y columna, y las convenciones de dibujo están en la "
            f"{R.tab('T_dataflow_counts')} del apéndice.",
        ],
        "fig2_grd_core": [
            "(a) Episodios con F84 en cualquier posición y con F84 principal por 100.000 episodios GRD del mismo panel "
            "y año", "~,", "panel anual observado (65, 65, 65, 65, 68 y 72 hospitales en 2019–2024", "~)",
            "y panel fijo de 65 hospitales.",
            "(b) Panel observado por modalidad: toda modalidad, hospitalización estricta y cirugía mayor ambulatoria "
            "(CMA), cualquier posición; la categoría «otra» está ausente de los archivos 2020–2024 (ausencia, no cero).",
            "(c) Tasa de F84 por 100.000 episodios dentro de cada estrato de profundidad diagnóstica (diagnósticos "
            "codificados por episodio) en 2019 y 2024 con IC exactos; recuadro: profundidad media de todos los "
            "episodios y de los episodios con F84 por año", "~(solo medias; no se dibuja dispersión).",
            "(d) Episodios con F84 (cualquier posición) por 100.000 habitantes INE (base 2017, nacional) por grupo de "
            "edad", "y sexo, 2019 frente a 2024", "~:",
            "el numerador se localiza por lugar de atención (hospitales públicos GRD) y el denominador por "
            "residencia, por lo que es una lectura complementaria y no una tasa de uso de una población definida.",
            "(e) Tasa de F84 por 100.000 episodios de cada hospital en 2024", "~,",
            "con IC exactos y tasa nacional (804); los cinco hospitales con la tasa más alta se numeran 1–5 y los "
            "tres con la más baja x, y y z",
            f"~(cada hospital en la {R.tab('S_hospital_rates_2024')} del apéndice).",
            "(f) Episodios con F84 y personas únicas dentro de cada año, en miles (sin deduplicación entre años: el "
            "identificador cambia de formato entre 2020 y 2021), episodios por persona",
            "y razón hombre:mujer de los episodios con IC 95 % (eje derecho).",
            "Banda gris: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto", "~.",
            "Los conteos son reconocimiento administrativo", "~(episodios con F84 documentado)",
            ", no prevalencia ni incidencia.",
        ],
        "fig3_rem_pathway": [
            "Todos los valores son conteos administrativos anuales de la red pública", "~;",
            "las fuentes no se enlazan por persona y ningún cociente entre paneles representa una probabilidad "
            "individual.", "~Ninguna serie cruza un quiebre.",
            "(a) A03 detección en APS, escala logarítmica, un punto por año", "~por era:",
            "2019–2022 M-CHAT realizado", "y alterado",
            "solo en niños/as con alteración de lenguaje o del área social en el control de 18 meses (no es "
            "cobertura ni positividad poblacional); 2023–2024 M-CHAT-R/F", "~categorías de riesgo y derivación.",
            "(b) A03 en las eras siguientes, misma lectura: 2024 códigos", "~para", "31–59 meses", "y 2025 rediseño",
            "~; no comparables entre sí.",
            "(c) A27 consejería", "y referencia asistida", "~, y", "A28 ingresos a rehabilitación por TEA en APS",
            "y hospitalaria",
            ", 2023–2025: intervenciones e ingresos, no personas", "~.",
            "(d) A05 ingresos y altas clínicas del programa de salud mental en un solo eje con el quiebre de "
            "definición marcado: TGD amplio 2019–2020", "y autismo estricto 2021–2025",
            "con la familia TGD de la variante", "como líneas claras; línea gris y eje derecho: establecimientos "
            "reportantes.",
            "(e) P2 población NANEAS con TEA bajo control",
            ": stock de diciembre (puntos llenos) y de junio (marcadores huecos, sensibilidad; los semestres nunca se "
            "suman); líneas grises y eje derecho: establecimientos con fila en diciembre y en junio; texto: TEA por "
            "100 NANEAS totales", "~.",
            "(f) P6 población bajo control en diciembre en un solo eje con el quiebre marcado: TGD amplio 2019–2020",
            "y autismo estricto 2021–2025", "~.",
            "Sombreado gris: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto, "
            "no como intervención", "~.",
            "Los conteos son reconocimiento administrativo, no prevalencia ni incidencia; stocks (e, f) y flujos (a, "
            "b, c, d) nunca comparten un eje.",
        ],
        "fig4_triangulation": [
            "(a) Estudiantes autistas en el Programa de Integración Escolar (PIE; stock escolar anual, matrícula "
            "nacional): TEA estricto y TEA-Asperger 2019–2023", ", serie armonizada TEA + Asperger 2019–2025", "~y",
            "el autismo en escuelas especiales 2022–2025.",
            "(b) JUNAEB (Encuesta de Vulnerabilidad): % de estudiantes con TEA reportado por cuidadores según nivel; "
            "2024", "y 2025", "con IC 95 %; 2023 sin ponderador publicado", "~;",
            "2019–2022 sin ítem TEA y 1º medio 2024 con variable vacía se marcan como «no estimable»",
            ", nunca como cero.",
            "(c) Proporciones ponderadas con diseño complejo",
            ": ENDIDE 2022 adultos 18+, NNA 2–17 con autismo reportado por el cuidador y reportado con confirmación "
            "médica, y ENCAVI 2023–2024 personas 15+ con diagnóstico de TEA", "~; estimaciones imprecisas en gris.",
            "(d) Índices (primer año común 2021 = 100; escala log)", "~:",
            "GRD F84 en cualquier posición por 100.000 episodios (panel observado), DEIS F84 principal por 100.000 "
            "egresos, ingresos A05 por autismo", ", stock P2 de diciembre", "y PIE armonizado", "~;",
            "son índices, no niveles comparables.",
            "(e) Cinco franjas apiladas, cada una con su propio eje vertical, por 100.000 habitantes INE",
            "~(residencia)",
            ": episodios GRD con F84 (variante), personas únicas dentro del año, ingresos A05 y stock P2 de diciembre "
            "(numeradores por lugar de atención, red pública; n = establecimientos reportantes) y PIE armonizado.",
            "Las barras rayadas son stocks y las llenas flujos, y nunca comparten un eje", "~.",
            "(f) F84 en posición principal: egresos DEIS (todos los establecimientos y subconjunto SNSS) por 100.000 "
            "egresos frente a episodios GRD", "~(n = hospitales)", "por 100.000 episodios, IC 95 % exacto de Poisson;",
            "~una comparación de cobertura entre dos registros del mismo evento, no una probabilidad.",
            "Sombreado: disrupción del reporte 2020–2021; línea punteada: Ley 21.545 (marzo 2023) como contexto, no "
            "como intervención", "~.",
            "Las fuentes no se enlazan por persona; los conteos son reconocimiento administrativo, no prevalencia ni "
            "incidencia.",
        ],
    }


def _table_note_parts(R: JC.JournalRegistry) -> dict:
    n_t2, n_t7, n_cpa = R.nrows("T2_grd_core"), R.nrows("T7_models"), R.nrows("T7_models_cpa_full")
    return {
        "T2_grd_core": [
            "Fuente: GRD público (FONASA) 2019–2024, módulo 01_grd_core (grd_year_summary.csv, grd_subcode_year.csv) "
            "y módulo 06_models (models_population_rates.csv).",
            "Unidad: episodio GRD (hospitalización o cirugía mayor ambulatoria); «F84 en cualquier posición» = "
            "episodios con F84 documentado", "~;", "F84 principal como serie separada.",
            "Denominador de las tasas: episodios GRD del mismo año, panel y modalidad, por 100.000, con IC 95 % "
            "exactos de Poisson.",
            "Cobertura: panel observado de 65/65/65/65/68/72 hospitales (2019–2024);",
            C.fixed_panel_gloss("es", "named") + ".",
            "Personas únicas solo dentro de cada año (el identificador cambia de formato entre 2020 y 2021; "
            "CIP_ENCRIPTADO 2019–2023, ID_BENEFICIARIO 2024); nunca se deduplica entre años.",
            "Tasas por 100.000 habitantes: numerador por lugar de atención (red pública) y denominador INE base 2017 "
            "al 30 de junio (residencia), lectura complementaria; tasa estandarizada OMS con IC de Fay–Feuer.",
            "La fila «solo F84.0» es idéntica en ambas variantes.",
            "Todos los conteos son reconocimiento administrativo, no prevalencia ni incidencia.",
            "La Ley 21.545 (marzo de 2023) es contexto de política, no una intervención con efecto causal identificable.",
            f"=La tabla completa ({n0(n_t2)} filas, con las tasas de la familia completa, los resúmenes de profundidad "
            f"diagnóstica y las tasas poblacionales de F84 principal) es la {R.tab('T2_grd_core')} del apéndice.",
        ],
        "T7_models": [
            f"=Veintinueve de las {n0(n_t7)} especificaciones preespecificadas de la {R.tab('T7_models')} del "
            f"apéndice; las {n0(n_cpa)} especificaciones convergidas están en la {R.tab('T7_models_cpa_full')} del "
            f"apéndice.",
            "Modelos log-lineales cuasi-Poisson (escala de Pearson) con el offset indicado; CPA = 100·(exp(β) − 1) "
            "con IC 95 % de Wald; dispersión = χ² de Pearson / gl.",
            "~Valores p de Wald con dos cifras significativas.",
            "GRD: episodios con F84 documentado por 100.000 episodios GRD del mismo panel y modalidad (panel observado "
            "65/65/65/65/68/72 hospitales; panel fijo 65); hospital-año con efectos fijos de hospital y offset "
            "log(episodios), EE agrupados por hospital e intercepto aleatorio Poisson como sensibilidad; por 100.000 "
            "habitantes con numerador por lugar de atención y denominador INE base 2017 (residencia).",
            "REM A05 2021–2025 (era de códigos de autismo; TGD amplio 2019–2020 no modelado; menos establecimientos "
            "reportan en 2025); P2 y P6 son stocks de diciembre (junio solo sensibilidad; nunca sumados); PIE "
            "armonizado = Apuntes 60 (2019–2023) y SINACES (2024–2025); DEIS solo F84 en DIAG1, comparable "
            "únicamente con GRD principal.",
            "El indicador 2020–2021 describe la disrupción del reporte y ninguna especificación estima un efecto "
            "causal de la Ley 21.545 (marzo de 2023).",
            "Todos los conteos son reconocimiento administrativo, no prevalencia ni incidencia.",
        ],
    }


def body_legend(R: JC.JournalRegistry, key: str) -> str:
    return assemble_fragments(R.caption_text(key), _legend_parts(R)[key], f"leyenda de {key}")


def body_note(R: JC.JournalRegistry, key: str) -> str:
    return assemble_fragments(R.note_text(key), _table_note_parts(R)[key], f"nota de {key}")


# ---------------------------------------------------------------------------
# El artículo
# ---------------------------------------------------------------------------
def article(V: dict, plate_dir: Path | None = None) -> list:
    k = _K(V)
    jn = lambda lvl, y: f"{n0(k(f'junaeb_{lvl}_all_tea_n_{y}'))}/{n0(k(f'junaeb_{lvl}_all_n_answered_{y}'))}"  # noqa: E731
    mill = lambda key: PE.fmt_number(k(key) / 1e6, 1, LANG)  # noqa: E731  («17,1 de 20,2 millones»)
    grd_0_9, grd_age_base = grd_age_count(GRD_AGE_BANDS_0_9, "grd_f84_any_share_age_0_9_2024", V)
    grd_20plus, _ = grd_age_count(GRD_AGE_BANDS_20PLUS, "grd_f84_any_share_age_20plus_2024", V)
    a05_0_9 = a05_age_0_9_count(V)
    R = JC.JournalRegistry(LANG, plate_dir=plate_dir)
    doc = PS._Doc()
    T = lambda key: R.tab(key)  # noqa: E731
    F = lambda key: R.fig(key)  # noqa: E731
    TR = lambda keys: R.tabs_range(keys)  # noqa: E731
    FR = lambda keys: R.figs_range(keys)  # noqa: E731

    # ---------------- Portada ----------------
    doc.add("title", TITLE)
    doc.add("authors", dict(authors=[(f"{AUTHOR} [grado académico preferido, uno solo: por completar por el autor]", "1")],
                            affiliations=[("1", f"{AFFILIATION} [dirección postal completa de la afiliación: por completar "
                                                f"por el autor]")],
                            lines=[f"Autor de correspondencia: {AUTHOR}; [dirección postal: por completar por el autor]; "
                                   f"{AUTHOR_EMAIL}; teléfono [por completar por el autor].",
                                   f"Título corto: {RUNNING_TITLE}.",
                                   "Tipo de artículo: Artículo (investigación original). Guías de reporte: STROBE "
                                   "(Strengthening the Reporting of Observational Studies in Epidemiology) y RECORD "
                                   "(REporting of studies Conducted using Observational Routinely-collected health Data). "
                                   "Versión española de trabajo del equipo autor; la revista publica en inglés.",
                                   "__COUNTS__"]))

    # ---------------- Resumen ----------------
    doc.h1("Resumen")
    doc.p("**Antecedentes** Los diagnósticos registrados de autismo han aumentado con fuerza en países de altos "
          "ingresos; la evidencia latinoamericana es escasa. Describimos cómo cambió el reconocimiento administrativo "
          "del autismo en los sistemas públicos de salud y educación de Chile en 2019–2025 y su robustez frente a "
          "cobertura, codificación y definiciones.")
    doc.p("**Métodos** Estudio nacional de datos rutinarios no enlazados: episodios de grupos relacionados por el "
          "diagnóstico (GRD) de hospitales públicos y egresos DEIS (2019–2024), seis módulos ambulatorios REM "
          "(2019–2025), denominadores poblacionales, dos encuestas con diseño complejo y registros escolares. "
          "Estimamos tasas por 100.000 episodios GRD y por residente, tasas estandarizadas OMS y cambios porcentuales "
          "anuales (CPA) cuasi-Poisson con sensibilidades preespecificadas.")
    doc.p(f"**Resultados** Los episodios GRD con F84 documentado aumentaron de {n0(k('grd_f84_any_n_2019'))} "
          f"({n1(k('grd_f84_any_rate_2019'))} por 100.000 episodios) en 2019 a {n0(k('grd_f84_any_n_2024'))} "
          f"({n1(k('grd_f84_any_rate_2024'))}) en 2024 (CPA {n1(k('apc_grd_any_obs'))}{NBSP}%, {CI95} "
          f"{cir(k('apc_grd_any_obs_lo'), k('apc_grd_any_obs_hi'))}; {n1(k('apc_grd_any_sensitivity_min'))}–"
          f"{n1(k('apc_grd_any_sensitivity_max'))}{NBSP}% entre especificaciones); el "
          f"{pct(k('grd_f84_secondary_only_share_2024_pct'))} ({n0(k('grd_f84_secondary_only_n_2024'))} episodios) "
          f"llevaba F84 solo como diagnóstico secundario. Los "
          f"ingresos a salud mental por autismo estricto pasaron de {n0(k('a05_autism_entries_2021'))} (2021) a "
          f"{n0(k('a05_autism_entries_2025'))} (2025), los niños con autismo bajo control de "
          f"{n0(k('p2_tea_dec_2019'))} a {n0(k('p2_tea_dec_2025'))} y los estudiantes autistas en integración "
          f"escolar de {n0(k('pie_harmonised_2019'))} a {n0(k('pie_harmonised_2025'))}. La razón hombres:mujeres de "
          f"los episodios hospitalarios cayó de {n2(k('grd_f84_any_mf_ratio_n_2019'))} a "
          f"{n2(k('grd_f84_any_mf_ratio_n_2024'))}. ENDIDE 2022 reportó autismo en el "
          f"{pct(k('svy_endide_children_reported_total_pct'), 2)} de los niños de 2 a 17 años "
          f"({n0(k('svy_endide_children_reported_total_cases'))}/{n0(k('svy_endide_children_reported_total_n'))}) y el "
          f"{pct(k('svy_endide_adults_reported_total_pct'), 2)} de los adultos "
          f"({n0(k('svy_endide_adults_reported_total_cases'))}/{n0(k('svy_endide_adults_reported_total_n'))}); "
          f"ENCAVI 2023–24 en el {pct(k('svy_encavi_15plus_diagnosed_total_pct'), 2)} de las personas de 15 años o más "
          f"({n0(k('svy_encavi_15plus_diagnosed_total_cases'))}/{n0(k('svy_encavi_15plus_diagnosed_total_n'))}).")
    doc.p("**Interpretación** Sistemas independientes de salud y educación registraron una expansión de varias veces "
          "del reconocimiento administrativo, junto con la recuperación pospandemia, la expansión del reporte, los "
          "cambios de códigos y, desde 2023, la Ley 21.545. Reporte y codificación explican parte; el cambio "
          "epidemiológico no puede separarse. Servicios y vigilancia deben seguir este ritmo.")
    doc.p("**Financiamiento** Ninguno.")

    # ---------------- Investigación en contexto ----------------
    doc.add("panel", dict(title="Investigación en contexto", items=[
        ("Evidencia previa a este estudio",
         "Buscamos en PubMed y Crossref el 4 de septiembre de 2026, sin restricciones de idioma ni de fecha, combinando "
         "los términos \"autism\", \"autism spectrum disorder\" o \"pervasive developmental disorder\" con "
         "\"administrative data\", \"register\", \"hospital discharge\", \"surveillance\", \"time trends\", "
         "\"prevalence\", \"Chile\" y \"Latin America\", y consultamos en la misma fecha los portales oficiales del "
         "Ministerio de Salud de Chile (DEIS), FONASA, la Superintendencia de Salud, el Instituto Nacional de "
         "Estadísticas, el Ministerio de Educación, JUNAEB, el Ministerio de Desarrollo Social y Familia y la Biblioteca "
         "del Congreso Nacional para obtener documentación de los datos, informes metodológicos y el texto de la Ley "
         "21.545; cada registro retenido se verificó contra sus metadatos en PubMed o Crossref o contra la página "
         "oficial. Los estudios basados en registros del Reino Unido, Dinamarca, Suecia y Estados Unidos muestran grandes "
         "aumentos de los diagnósticos registrados de autismo, atribuibles sobre todo a los criterios diagnósticos, al "
         "contacto con los servicios y a la concienciación más que a cambios del fenotipo subyacente. La evidencia "
         "latinoamericana se limita a unas pocas encuestas locales de prevalencia, a encuestas a cuidadores que "
         "documentan retraso diagnóstico y barreras de acceso y, para Chile, a una estimación urbana de prevalencia "
         "basada en tamizaje y a una estimación basada en registros escolares. La calidad de esa evidencia es desigual: "
         "los estudios de registros son cohortes nacionales con bajo riesgo de sesgo de selección cuyo desenlace, como el "
         "nuestro, es un código administrativo no validado; las estimaciones latinoamericanas provienen de tamizajes en "
         "una sola ciudad o de muestras de conveniencia con riesgo moderado a alto de sesgo de selección y de "
         "información; y la documentación oficial es descriptiva, sin que sea posible una evaluación del riesgo de "
         "sesgo. Ningún estudio ha examinado cómo varios "
         "sistemas administrativos no enlazados de un país latinoamericano registraron el autismo en el mismo período, "
         "ni ha cuantificado cuánto del cambio registrado sobrevive al ajuste por cobertura del reporte, profundidad de "
         "codificación y quiebres de definición."),
        ("Valor añadido de este estudio",
         "Usando todas las fuentes rutinarias públicas de Chile que contienen un código o ítem de autismo (episodios GRD "
         "hospitalarios, egresos DEIS, seis módulos REM, denominadores de aseguramiento, atención primaria y población, "
         "dos encuestas nacionales y registros escolares), con procedencia congelada y controles de reproducción "
         "preespecificados, mostramos que el reconocimiento administrativo del autismo aumentó varias veces entre 2019 y "
         "2025 en los sistemas hospitalario, ambulatorio, de rehabilitación y educativo; que los aumentos convergen en "
         "tiempo y dirección pese a unidades, coberturas y definiciones distintas; y que la profundidad de codificación, "
         "la expansión del reporte y los cambios de definición explican parte, pero no todo, del cambio registrado. "
         "Separamos stocks de flujos, lugar de atención de residencia y eras de definición entre sí, e informamos el "
         "número de establecimientos reportantes junto a cada conteo."),
        ("Implicancias de toda la evidencia disponible",
         "El reconocimiento administrativo es una medida accionable de la demanda de diagnóstico, atención y apoyo "
         "educativo aun cuando no pueda leerse como prevalencia. En Chile, y en otros sistemas segmentados de América "
         "Latina, la expansión observada implica necesidades crecientes de capacidad diagnóstica, seguimiento en atención "
         "primaria, rehabilitación e integración escolar, y de una vigilancia que registre explícitamente la cobertura y "
         "las reglas de codificación. Si el cambio refleja una necesidad no cubierta que se hace visible o una ocurrencia "
         "creciente del autismo no puede resolverse con registros no enlazados; se requieren enlace a nivel de persona, "
         "validación de los códigos y encuestas poblacionales repetidas."),
    ]))

    # ---------------- Introducción ----------------
    doc.h1("Introducción")
    doc.p("Se estima que el autismo afecta a cerca del 1 % de la población mundial [@zeidan2022], y los diagnósticos "
          "registrados han aumentado de forma pronunciada dondequiera que existen registros poblacionales. Los estudios "
          "basados en registros del Reino Unido, Dinamarca y Suecia atribuyen la mayor parte de ese aumento a cambios en "
          "los criterios diagnósticos, a la inclusión de contactos ambulatorios, a la concienciación y a la capacidad de "
          "los servicios más que a un cambio del fenotipo subyacente [@russell2022; @hansen2015; @lundstrom2015], y la "
          "red de vigilancia multifuente de Estados Unidos sigue documentando una prevalencia identificada creciente con "
          "registros enlazados de salud y educación [@shaw2025]. La Comisión Lancet sobre autismo llamó a contar con "
          "sistemas nacionales de datos capaces de monitorear la identificación, las necesidades y los servicios "
          "[@lord2022].")
    doc.p(f"América Latina aporta poco a esta evidencia: existen estimaciones poblacionales de prevalencia para pocos "
          f"países [@zeidan2022], las encuestas a cuidadores documentan largos retrasos diagnósticos y barreras de "
          f"acceso [@montielnava2024], y los registros rutinarios rara vez se han analizado. Chile tiene un sistema de salud "
          f"segmentado en el que el asegurador público FONASA cubría al {pct(k('share_fonasa_ine_pct_2025'))} de los "
          f"residentes en 2025 ({mill('fonasa_beneficiaries_2025')} de {mill('ine_pop_total_2025')} millones) y "
          f"las aseguradoras privadas ISAPRE a una minoría decreciente ({pct(k('share_isapre_ine_pct_2025'))}; "
          f"{millions(k('isapre_beneficiaries_2025'))}); cuenta con una estimación urbana de prevalencia [@yanez2021] y "
          f"una estimación basada en registros escolares [@romanurrestarazu2025]. La Ley 21.545, vigente desde marzo "
          f"de 2023, estableció derechos de "
          f"inclusión, atención y protección para las personas autistas y creó deberes de reporte para los sectores "
          f"de salud y educación [@ley21545].")
    doc.p("Los sistemas públicos de salud y educación de Chile producen varios conjuntos de datos rutinarios que "
          "registran el autismo: episodios hospitalarios de grupos relacionados por el diagnóstico (GRD), egresos "
          "hospitalarios (DEIS), resúmenes estadísticos mensuales (REM), los registros del Programa de Integración "
          "Escolar (PIE) y una encuesta a cuidadores de cohortes escolares completas. Difieren en unidad de "
          "observación, cobertura, definiciones y reglas de reporte, no están enlazados por persona y fueron diseñados "
          "para el pago y la gestión, no para la vigilancia. Los conteos derivados de ellos miden reconocimiento "
          "administrativo, el registro de un código de autismo en un contacto con un servicio, no la prevalencia ni la "
          "incidencia del autismo.")
    doc.p("Nos preguntamos cómo cambiaron el reconocimiento administrativo del autismo y la demanda registrada de "
          "servicios entre 2019 y 2025 en los sistemas públicos de salud y educación de Chile, y cuánto del cambio es "
          "robusto a variaciones de cobertura, intensidad de codificación y definiciones. La contribución es "
          "descriptiva: mostrar si sistemas independientes convergen, cuantificar las amenazas a la comparabilidad y "
          "traducir los hallazgos en necesidades de vigilancia y de capacidad asistencial. La Ley 21.545 se trata como "
          "contexto de política que coincide con la recuperación pospandemia, la expansión del reporte, los cambios de "
          "códigos y la codificación más profunda; no se estima ningún efecto de la ley.")

    # ---------------- Métodos ----------------
    doc.h1("Métodos")
    doc.h2("Diseño del estudio y contexto")
    doc.p(f"Este es un estudio descriptivo nacional multifuente de datos recolectados rutinariamente. La metodología "
          f"aplicada está en el apéndice (Parte A, {TR(M_TABLES)}); el estudio sigue la declaración STROBE y su "
          f"extensión RECORD [@vonelm2007; @benchimol2015] ({T('S_reporting_checklist')} del apéndice) e informa "
          f"resultados por sexo siguiendo las guías SAGER: el sexo es el que registra cada fuente o el declarado "
          f"a cada encuesta, ninguna fuente registra el sexo asignado al nacer ni el género, y no se analizó ninguna "
          f"variable de género; el plan de análisis preespecificado (versión 1.0, "
          f"{PLAN_DATE_ES}) se reproduce en el apéndice (Parte A, sección A9), con cada desviación en la bitácora de "
          f"decisiones. El contexto es Chile (población residente proyectada de {millions(k('ine_pop_total_2019'))} "
          f"en 2019 y {millions(k('ine_pop_total_2025'))} en 2025), cuya red pública comprende los hospitales del "
          f"SNSS y una atención primaria (APS) mayoritariamente municipal; las fuentes hospitalarias terminan en 2024.")
    doc.h2("Fuentes de datos y unidades de observación")
    doc.p(f"La {T('T1_sources')} del apéndice y la {R.mfig('fig1_dataflow')} describen las fuentes, unidades, "
          f"cobertura y quiebres de definición (recuentos de la {R.mfig('fig1_dataflow')}: {T('T_dataflow_counts')} "
          f"del apéndice). La atención hospitalaria se midió con los archivos GRD públicos, en los que la unidad es un "
          f"episodio (hospitalización o cirugía mayor ambulatoria, CMA) con hasta {n0(k('grd_diagnosis_positions'))} "
          f"diagnósticos codificados, de hospitales del SNSS. El panel observado comprendió "
          f"{k.series('grd_hospitals_observed_{y}', YEARS_GRD)} hospitales en 2019–2024; los "
          f"{n0(k('grd_fixed_panel_n'))} hospitales presentes en todos los años forman el panel fijo usado como "
          f"sensibilidad, y los {n0(k('grd_hospitals_ever_observed_n'))} alguna vez observados no son un panel "
          f"({T('ST1_grd_hospital_panel')} del apéndice). El identificador de persona cambia de formato entre 2020 y "
          f"2021, por lo que las personas únicas se cuentan solo dentro de cada año ({T('ST8_grd_identifier_audit')} "
          f"del apéndice). Los egresos DEIS de todos los establecimientos, que llevan solo el diagnóstico principal, "
          f"fueron una comprobación externa homóloga únicamente con F84 principal.")
    doc.p(f"La actividad ambulatoria se midió con los resúmenes estadísticos mensuales REM, cuya unidad es una fila "
          f"establecimiento × mes × código; la completitud del reporte por módulo y año (cero, ausente y sin reporte "
          f"como estados distintos) está en la {F('fig1_sources_coverage')} del apéndice. Los módulos de la Serie A "
          f"son flujos: A03 (tamizaje del desarrollo), A27 (consejería y referencia asistida, desde 2023; "
          f"intervenciones, no personas), A05 (ingresos y egresos de programas de salud mental) y A28 (ingresos a "
          f"rehabilitación, desde 2023). Los módulos de la Serie P son stocks semestrales de personas bajo control: P2 "
          f"(NANEAS con autismo) y P6 (programas de salud mental); diciembre es el corte principal y junio una "
          f"sensibilidad, nunca sumados. Los {n0(k('rem_pathway_codes_n'))} códigos de la ruta se verificaron contra "
          f"el diccionario oficial de cada año ({T('ST2_rem_code_dictionary')} del apéndice); ninguna serie cruza un "
          f"quiebre de definición ({T('S_definition_breaks')} del apéndice), y los establecimientos que reportan cada "
          f"código y año ({T('ST3_rem_reporting_establishments')} del apéndice) acompañan a cada conteo.")
    doc.p(f"Los benchmarks poblacionales provinieron de dos encuestas con diseño complejo: la Encuesta Nacional de "
          f"Discapacidad y Dependencia 2022 (ENDIDE; autismo reportado por adultos de 18 años o más y por cuidadores "
          f"de niños de 2 a 17 años, con un ítem de confirmación médica) y la Encuesta Nacional de Calidad de Vida y "
          f"Salud 2023–24 (ENCAVI; diagnóstico declarado a los 15 años o más). El autismo se identificó a partir de "
          f"los ítems de las encuestas tal como los reportó la persona o su cuidador; no se infirió ninguna "
          f"discapacidad a partir de un diagnóstico (formulación de los ítems: {T('ST5_survey_items')} del apéndice). "
          f"El reconocimiento educativo provino de los informes del Ministerio de Educación sobre el PIE (stock anual "
          f"de estudiantes autistas registrados, 2019–2025), del informe de seguimiento de la Ley 21.545 y de los "
          f"microdatos de la Encuesta de Vulnerabilidad Estudiantil de JUNAEB (diagnóstico médico de trastorno del "
          f"espectro autista reportado por el cuidador en las cohortes de educación parvularia, 1.º básico, 5.º básico "
          f"y 1.º medio; ítem desde 2023, ponderadores desde 2024; {T('ST6_junaeb_items')} del apéndice).")
    doc.p(f"Fuentes oficiales: archivos GRD [@fonasa_grd], egresos DEIS [@deis_egresos], REM [@minsal_rem], "
          f"proyecciones INE [@ine2019], beneficiarios FONASA [@fonasa_beneficiarios], ENDIDE 2022 [@endide2022], "
          f"ENCAVI 2023–24 [@encavi2023], registros PIE [@mineduc_apuntes60; @mineduc_sinaces2026] y JUNAEB "
          f"[@junaeb_eve]; las capas de sensibilidad (INE base 2024 y Censo 2024, inscritos APS, beneficiarios ISAPRE "
          f"y actividad hospitalaria REM-20) se citan en el apéndice. La procedencia se congeló antes del análisis: "
          f"{n0(k('prov_artefacts_n'))} artefactos fuente ({n1(k('prov_gb_total'))} GB) se resumieron (SHA-256) y "
          f"documentaron ({TR(['ST7_provenance', 'ST7b_manifest_checks'])} del apéndice); los datos fuente nunca se "
          f"copiaron ni sobrescribieron.")
    doc.h2("Definiciones de caso y variantes de definición")
    doc.p(f"En el GRD, un episodio con F84 documentado es aquel en que cualquier código CIE-10 de la familia F84 "
          f"aparece en cualquiera de las {n0(k('grd_diagnosis_positions'))} posiciones diagnósticas; F84 principal es "
          f"una serie separada y más específica, y también se informa el F84 solo secundario (subcódigos por posición: "
          f"{T('ST10_grd_f84_subcodes')} del apéndice). En todo este artículo la definición de caso es la familia F84 "
          f"sin síndrome de Rett (F84.2), porque F84.2 es un trastorno genético distinto que ya no se clasifica junto "
          f"al autismo; la familia F84 completa se analiza en paralelo y se compara serie por serie en la "
          f"{F('figE28_variant_sensitivity')} y la {T('E28_variant_sensitivity')} del apéndice (una diferencia de "
          f"{n0(k('grd_f84_any_n_rett_only_difference_2024'))} episodios en 2024), y F84.0 por sí solo es una serie "
          f"estricta que ambas definiciones comparten. En REM, el autismo estricto es "
          f"{k('strict_autism_code_a05_entry')}/{k('strict_autism_code_a05_exit')} en A05 (ingresos/egresos) y "
          f"{k('strict_autism_code_p6_primary')}/{k('strict_autism_code_p6_specialty')} en P6 (atención "
          f"primaria/especialidad), todos desde 2021; la familia de trastornos generalizados del desarrollo (TGD) de "
          f"la variante añade las demás categorías de TGD, y los códigos de TGD amplio de 2019–2020, de los que no "
          f"puede separarse F84.2, son solo una sensibilidad rotulada. P2 (código {k('p2_tea_code')}), A03, "
          f"A27 y A28 no dependen de la variante; A03 tiene cuatro eras no comparables. En educación, el trastorno del "
          f"espectro autista (TEA) estricto, el TEA-Asperger y su suma armonizada son series PIE separadas; el "
          f"estimando JUNAEB es la proporción ponderada de estudiantes encuestados con diagnóstico médico de TEA "
          f"reportado por el cuidador, y un nivel o año sin ítem o sin ponderador no es estimable, nunca cero.")
    doc.h2("Denominadores y capas de cobertura")
    doc.p(f"Cuatro capas de denominador responden preguntas distintas y nunca se intercambiaron "
          f"({T('T4_denominators_coverage')} del apéndice): proyecciones INE basadas en el Censo 2017 al 30 de junio "
          f"(población residente; la base 2024 y el Censo 2024 empadronado solo como sensibilidades, "
          f"{F('figS10_denominators')} y {T('S10_denominator_sensitivity')} del apéndice); stocks de beneficiarios "
          f"FONASA e ISAPRE a diciembre e inscritos APS validados (cobertura de aseguramiento y operativa; esquemas, "
          f"reglas de armonización, cuadro comunal de equivalencias por nombre exacto y cobertura por edad y sexo en "
          f"{TR(['ST12a_fonasa_schema', 'ST12b_isapre_rules', 'ST12c_aps_panel', 'ST4a_comuna_crosswalk_summary', 'ST4b_comuna_unmatched'])}, "
          f"{F('figS11_coverage_age_sex')} y {T('S11_coverage_age_sex')} del apéndice); y egresos y días-cama REM-20 "
          f"(nunca una población cubierta). El estimando GRD primario es la tasa por 100.000 episodios GRD del mismo "
          f"año, panel y modalidad; las tasas por 100.000 residentes INE son una lectura complementaria con el "
          f"numerador localizado por lugar de atención y el denominador por residencia. Los conteos REM llevan sus "
          f"establecimientos reportantes, tasas por establecimiento reportante y un panel estable de establecimientos "
          f"que reportan el código en todos los años de su era.")
    doc.h2("Análisis estadístico")
    doc.p(f"Los estimadores se definen en la Parte A del apéndice (números de ecuación a continuación). Las tasas por "
          f"100.000 episodios, egresos o residentes llevan límites exactos de Poisson al 95{NBSP}% (ecuación "
          f"{_eq('crude')}); las tasas por población se estandarizaron directamente a la población estándar mundial "
          f"de la OMS [@ahmad2001] con intervalos gamma de Fay–Feuer [@fay1997] (ecuaciones "
          f"{_eqs('age_specific', 'ff')}). Las tendencias anuales se resumieron con modelos log-lineales "
          f"cuasi-Poisson [@wedderburn1974] con el logaritmo del denominador del estimando como offset (ninguno para "
          f"los stocks), de los que el cambio porcentual anual (CPA) es 100·(exp(β) − 1) con {CI95} de Wald "
          f"(ecuaciones {_eqs('qpois', 'apc')}); la dispersión de Pearson se informa para cada modelo y la "
          f"autocorrelación residual se comprobó con el estadístico de Durbin–Watson (ecuación {_eq('dw')}), débil "
          f"con tres a siete puntos. Los modelos hospital-año del GRD añadieron efectos fijos de hospital con "
          f"tendencia común (errores estándar agrupados como sensibilidad; ecuación {_eq('fe')}) y, por separado, un "
          f"intercepto aleatorio Poisson por hospital (ecuación {_eq('ri')}). Las covariables fueron la profundidad "
          f"diagnóstica media (diagnósticos codificados por episodio) y un indicador de la disrupción del reporte de "
          f"2020–2021, que no tiene significado causal. Los CPA ajustados por edad provinieron de celdas grupo de edad "
          f"× año con efectos fijos de edad y offset poblacional, por sexo (diagnósticos: "
          f"{F('figE27_model_diagnostics')}, {T('E27_model_diagnostics')} del apéndice).")
    doc.p(f"Las proporciones de las encuestas se estimaron con los ponderadores, estratos y unidades primarias de "
          f"muestreo publicados como estimadores de razón por dominio con errores estándar linealizados de Taylor, "
          f"{CI95} logit sobre t, efectos de diseño y errores estándar relativos (ecuaciones "
          f"{_eqs('taylor', 'deff')}); los dominios con menos de 30 casos o con error estándar relativo superior al "
          f"30{NBSP}% se marcan. Las proporciones JUNAEB usaron el factor de expansión anual sin conglomerado escolar. "
          f"La convergencia se describe con índices (2021 = 100; ecuación {_eq('index_number')}) que nunca se leen "
          f"como niveles comparables. Las tasas comunales por residencia se estandarizaron indirectamente, se "
          f"suavizaron (Bayes empírico) y se describieron con la I de Moran, indicadores locales y Gi* de Getis–Ord "
          f"con control de Benjamini–Hochberg y con medidas de Lorenz, Gini y Theil, con supresión de las celdas con "
          f"menos de cinco eventos (ecuaciones {_eqs('expected', 'eb_prior')} y {_eqs('moran', 'suppression')}). Las "
          f"sensibilidades preespecificadas ({T('M6_sensitivity_grid')} del apéndice) fueron: panel hospitalario fijo "
          f"frente a observado, hospitalización estricta frente a toda modalidad, principal frente a cualquier "
          f"posición, solo F84.0, ajuste y estratificación por profundidad diagnóstica, el indicador de disrupción "
          f"2020–2021, la ventana 2021–2024, efectos fijos y aleatorios de hospital, paneles REM estables, offsets por "
          f"establecimiento, stocks de junio frente a diciembre, y los denominadores del Censo 2024 y de la base 2024. "
          f"Una fila REM ausente es «no reportado», distinto de cero, y nunca se imputa; 2020 nunca se interpoló; no se "
          f"ajustó ningún modelo causal de la Ley 21.545. Los análisis usaron Python 3.14; las "
          f"{n0(k('models_n_variant'))} especificaciones convergidas se comparten (Declaración de disponibilidad de "
          f"datos).")
    doc.h2("Controles de reproducibilidad")
    doc.p(f"Antes de modelar, {n0(k('controls_families_prespecified_n'))} familias de control preespecificadas se "
          f"reprodujeron a partir de los archivos fuente, exigiendo igualdad exacta para los conteos y una diferencia "
          f"relativa de 0,5{NBSP}% o menos para medias y proporciones; cada diferencia se explicó. Las "
          f"{n0(k('t8_rows'))} filas indicador-año resultantes {CR.label(CR.ANALYSIS_PLAN, LANG)} se resumen por "
          f"familia en las {TR(['T8_controls_compact', 'E79_reproduction_controls_by_family'])} del apéndice y se "
          f"grafican en la {F('figS15_controls')} del apéndice; ningún control se completó por plausibilidad.")
    doc.h2("Papel de la fuente de financiamiento")
    doc.p("No hubo fuente de financiamiento para este estudio. El autor de correspondencia tuvo acceso completo a todos "
          "los datos del estudio y la responsabilidad final de la decisión de enviar el manuscrito a publicación.")
    doc.h2("Ética")
    doc.p("El estudio usó únicamente datos administrativos públicos, desidentificados, agregados o seudonimizados, y "
          "microdatos públicos de encuestas; no se contactó a ninguna persona ni se intentó enlace alguno. Según la "
          "normativa chilena, estos análisis secundarios no requieren aprobación ética [por confirmar por el equipo "
          "autor antes del envío].")
    doc.h2("Uso de inteligencia artificial en el proceso de investigación")
    doc.p("Se usaron asistentes basados en grandes modelos de lenguaje (Claude Code, Anthropic, modelo Claude Fable "
          "5.1; OpenAI Codex) bajo la dirección del autor para escribir y depurar el pipeline y borradores de este "
          "texto; el autor especificó cada análisis, ejecutó y revisó todo el código y verificó cada cifra contra los "
          "archivos de salida (declaración sobre IA).")

    # ---------------- Resultados ----------------
    doc.h1("Resultados")
    doc.h2("Fuentes y cobertura")
    doc.p(f"La {R.mfig('fig1_dataflow')} muestra, para cada fuente, qué es una fila, cuántas filas superan la "
          f"selección de autismo y el denominador, sin enlace individual. Los archivos GRD contenían "
          f"{n0(k('grd_records_total_2019'))} episodios en 2019 y {n0(k('grd_records_total_2024'))} en 2024 de "
          f"{k.series('grd_hospitals_observed_{y}', YEARS_GRD)} hospitales; el panel fijo de "
          f"{n0(k('grd_fixed_panel_n'))} hospitales concentró {n0(k('grd_records_fixed65_2024'))} de los "
          f"{n0(k('grd_records_total_2024'))} episodios de 2024 ({ppct(k('grd_records_fixed65_share_2024'))}), tras la "
          f"incorporación de {nw(k('grd_hospitals_added_2023_n'))} hospitales en 2023 y "
          f"{nw(k('grd_hospitals_added_2024_only_n'))} más en 2024 ({T('ST1_grd_hospital_panel')} del apéndice). Los "
          f"establecimientos que reportaron ingresos A05 por autismo estricto fueron "
          f"{k.series('a05_autism_entries_estab_{y}', YEARS_A05)} en 2021–2025 ("
          f"{n0(abs(k('a05_autism_entries_estab_change_2025_2024')))} menos en 2025; archivo posiblemente "
          f"incompleto) y los que reportaron el stock P2 de diciembre "
          f"{k.series('p2_tea_dec_estab_{y}', YEARS_REM)} en 2019–2025. FONASA cubría al "
          f"{pct(k('share_fonasa_ine_pct_2019'))} de los residentes en 2019 ({mill('fonasa_beneficiaries_2019')} "
          f"de {mill('ine_pop_total_2019')} millones) y al {pct(k('share_fonasa_ine_pct_2025'))} en 2025 "
          f"({mill('fonasa_beneficiaries_2025')} de {mill('ine_pop_total_2025')} millones); la población "
          f"empadronada en el Censo 2024 fue el {ppct(k('ine_ratio_censo2024_base2017_2024'))} de la proyección base "
          f"2017 ({n0(k('censo2024_enumerated'))} de {n0(k('ine_pop_total_2024'))}).")

    doc.h2("Núcleo hospitalario: episodios GRD con F84 documentado")
    doc.p(f"Los episodios con F84 documentado en cualquier posición fueron {k.series('grd_f84_any_n_{y}', YEARS_GRD)} "
          f"en 2019–2024, es decir, {k.rate('grd_f84_any', 2019)} por 100.000 episodios GRD en 2019 y "
          f"{k.rate('grd_f84_any', 2024)} en 2024, una razón de {n2(k('grd_f84_any_rate_ratio_2024_2019'))} "
          f"({R.mtab('T2_grd_core')}, {R.mfig('fig2_grd_core')}; {F('figS2_grd_subcodes')}, "
          f"{TR(['E60_grd_annual_full', 'T2_grd_core'])} del apéndice). El conteo cayó con la actividad hospitalaria "
          f"en 2020 ({n0(k('grd_f84_any_n_2020'))} episodios) mientras la tasa no lo hizo "
          f"({n1(k('grd_f84_any_rate_2020'))}). En el panel fijo de {n0(k('grd_fixed_panel_n'))} hospitales el conteo "
          f"de 2024 fue {n0(k('grd_f84_any_fixed65_n_2024'))} ({n1(k('grd_f84_any_fixed65_rate_2024'))} por 100.000), "
          f"de modo que los hospitales incorporados contribuyeron poco. F84 principal fue más raro y creció más "
          f"lentamente: {k.series('grd_f84_principal_n_{y}', YEARS_GRD)}, de {k.rate('grd_f84_principal', 2019)} a "
          f"{k.rate('grd_f84_principal', 2024)} por 100.000 episodios; en 2024, "
          f"{n0(k('grd_f84_secondary_only_n_2024'))} de los {n0(k('grd_f84_any_n_2024'))} episodios con F84 "
          f"({pct(k('grd_f84_secondary_only_share_2024_pct'))}) lo llevaban solo como diagnóstico secundario. La serie solo F84.0 alcanzó {n0(k('grd_f840_strict_any_n_2024'))} episodios en "
          f"2024 (apéndice: {F('figE28_variant_sensitivity')}, {T('E28_variant_sensitivity')}).")
    doc.p(f"El aumento no fue solo codificación más profunda (profundidad media por año: recuadro de la "
          f"{R.mfigp('fig2_grd_core', 'c')}; no se calcula ninguna dispersión): dentro de cada estrato de tres o más "
          f"diagnósticos la tasa de F84 aumentó entre 2019 y 2024 "
          f"por un factor de {n1(k('grd_depth_bin_3_rate_ratio_2024_2019'))} (tres diagnósticos), "
          f"{n1(k('grd_depth_bin_4_rate_ratio_2024_2019'))} (cuatro), {n1(k('grd_depth_bin_5_rate_ratio_2024_2019'))} "
          f"(cinco), {n1(k('grd_depth_bin_6_7_rate_ratio_2024_2019'))} (seis a siete), "
          f"{n1(k('grd_depth_bin_8_10_rate_ratio_2024_2019'))} (ocho a diez) y "
          f"{n1(k('grd_depth_bin_11plus_rate_ratio_2024_2019'))} (11 o más), y en los estratos de uno y dos "
          f"diagnósticos de {n1(k('grd_depth_bin_1_rate_2019'))} a {n1(k('grd_depth_bin_1_rate_2024'))} y de "
          f"{n1(k('grd_depth_bin_2_rate_2019'))} a {n1(k('grd_depth_bin_2_rate_2024'))} por 100.000 "
          f"({R.mfigp('fig2_grd_core', 'c')}). Las personas únicas dentro de cada año fueron "
          f"{k.series('grd_f84_any_persons_{y}', YEARS_GRD)}, con {n2(k('grd_episodes_per_person_any_2024'))} "
          f"episodios por persona en 2024 ({F('EF6_readmission_multiplicity')}, "
          f"{T('EF6_readmission_multiplicity')} del apéndice).")
    doc.p(f"En 2024 la tasa más alta por 100.000 episodios se observó en el grupo de "
          f"{str(k('grd_f84_any_peak_age_group_2024')).replace('-', ' a ')} años, el "
          f"{n0(grd_0_9)} de los {n0(grd_age_base)} episodios con F84 y edad conocida "
          f"({ppct(k('grd_f84_any_share_age_0_9_2024'))}) correspondieron a niños de 0 a 9 años y {n0(grd_20plus)} "
          f"({ppct(k('grd_f84_any_share_age_20plus_2024'))}) a personas de 20 años o más; la razón hombres:mujeres "
          f"de los episodios cayó de {n2(k('grd_f84_any_mf_ratio_n_2019'))} en 2019 a "
          f"{n2(k('grd_f84_any_mf_ratio_n_2024'))} en 2024 ({T('ST9_grd_age_sex')} del apéndice). Por 100.000 "
          f"residentes INE, la tasa estandarizada OMS de episodios con F84 aumentó de "
          f"{k.est_y('grd_pop_any_total_asr', 2019)} en 2019 a {k.est_y('grd_pop_any_total_asr', 2024)} en 2024, "
          f"{n1(k('grd_pop_any_male_asr_2024'))} en hombres y {n1(k('grd_pop_any_female_asr_2024'))} en mujeres "
          f"(razón {n2(k('grd_pop_any_asr_mf_ratio_2024'))}; {T('S_grd_population_rates')} del apéndice; "
          f"{R.mfigp('fig2_grd_core', 'd')}).")
    doc.p(f"Los hospitales fueron heterogéneos: en 2024 la tasa varió de {n1(k('grd_hosp2024_rate_min'))} a "
          f"{n0(k('grd_hosp2024_rate_max'))} por 100.000 episodios (razón {n1(k('grd_hosp2024_rate_ratio_max_min'))}; "
          f"mediana {n1(k('grd_hosp2024_rate_median'))}, RIC {n1(k('grd_hosp2024_rate_q1'))}–"
          f"{n1(k('grd_hosp2024_rate_q3'))}), con los valores más altos en hospitales pediátricos "
          f"({R.mfigp('fig2_grd_core', 'e')}; {FR(['figS3_grd_hospital_effects', 'EF8_hospitals'])}, "
          f"{TR(['S_hospital_rates_2024', 'EF8_hospitals'])} del apéndice); "
          f"{n0(k('grd_hosp_rr_fixed_effects_none_n_above1'))} hospitales tuvieron una razón de tasas de efectos "
          f"fijos superior a uno y {n0(k('grd_hosp_rr_fixed_effects_none_n_below1'))} inferior a uno, y la desviación "
          f"estándar del intercepto aleatorio fue {n2(k('apc_grd_hospital_ri_re_sd'))} (diagnósticos principales de "
          f"los episodios con F84 secundario: {F('EF5_codiagnoses')}, "
          f"{TR(['EF5_codiagnoses', 'E8_grd_principal_when_secondary'])} del apéndice; gravedad y letalidad: "
          f"{T('EF4_severity_weight')} del apéndice). Los egresos DEIS con F84 "
          f"principal aumentaron de {n0(k('deis_f84_principal_n_2019'))} ({k.rate('deis_f84_principal', 2019)} por "
          f"100.000 egresos) en 2019 a {n0(k('deis_f84_principal_n_2024'))} ({k.rate('deis_f84_principal', 2024)}) "
          f"en 2024, {n0(k('deis_f84_principal_snss_2024'))} de ellos ({ppct(k('deis_f84_principal_snss_share_2024'))}) "
          f"en establecimientos del SNSS; la "
          f"razón entre los conteos DEIS y GRD de F84 principal fue {n2(k('deis_vs_grd_ratio_f84_principal_2024'))} "
          f"en 2024, una comparación de cobertura entre dos registros no enlazados del mismo evento y no una "
          f"probabilidad ({TR(['ST11a_deis_annual', 'ST11b_deis_vs_grd'])}, "
          f"{FR(['figS14_deis_sex_age', 'EF10_deis_detail'])}, {TR(['S14_deis_sex_age', 'EF10_deis_detail'])} del "
          f"apéndice).")

    doc.h2("Ruta administrativa agregada en atención primaria y especialidad")
    doc.p(f"La {R.mfig('fig3_rem_pathway')} presenta los módulos REM por era con sus establecimientos reportantes "
          f"({TR(['T3_rem_pathway', 'E69_rem_code_year_full'])} del apéndice); los paneles son indicadores agregados "
          f"de sistemas no enlazados, de modo que ningún cociente entre ellos representa una probabilidad individual. "
          f"Los códigos de detección y referencia se redefinieron en 2023, 2024 y 2025, por lo que A03 y A27 se "
          f"muestran por era sin serie continua: la clasificación M-CHAT-R/F de 2023–2024 registró "
          f"{n0(k('a03_2023_high_2023'))} y {n0(k('a03_2023_high_2024'))} niños en alto riesgo, y las referencias "
          f"asistidas (A27) fueron {k.series('a27_assisted_referral_{y}', YEARS_A27)} intervenciones en 2023–2025 "
          f"(riesgo y derivación por era: {FR(['E12_rem_a03_risk_referral', 'E11_rem_a03_codes_by_era'])}, "
          f"{TR(['E12_rem_a03_risk_referral', 'E11_rem_a03_codes_by_era'])} del apéndice).")
    doc.p(f"Los ingresos por autismo estricto a programas de salud mental (A05) aumentaron de "
          f"{n0(k('a05_autism_entries_2021'))} en 2021 a {n0(k('a05_autism_entries_2025'))} en 2025 "
          f"({k.series('a05_autism_entries_{y}', YEARS_A05)}), los egresos de programa de "
          f"{n0(k('a05_autism_exits_2021'))} a {n0(k('a05_autism_exits_2025'))} y los ingresos de la familia TGD de la "
          f"variante de {n0(k('a05_family_entries_2021'))} a {n0(k('a05_family_entries_2025'))}. En el panel estable "
          f"de {n0(k('a05_autism_entries_stable_panel_n'))} establecimientos, los ingresos aumentaron de "
          f"{n0(k('a05_autism_entries_stable_total_2021'))} a {n0(k('a05_autism_entries_stable_total_2025'))} "
          f"({FR(['figS6_rem_stable_panel', 'E17_rem_establishment_distribution'])}, "
          f"{TR(['S6_stable_panel', 'E17_rem_establishment_distribution'])} del apéndice). Por 100.000 residentes, la "
          f"tasa estandarizada OMS de ingresos aumentó de {k.est_y('a05_autism_pop_total_asr', 2021)} en 2021 a "
          f"{k.est_y('a05_autism_pop_total_asr', 2025)} en 2025 ({F('figS7_rem_education_models')}, "
          f"{T('S_a05_standardised_rates')} del apéndice), con una razón hombres:mujeres de tasas estandarizadas de "
          f"{n2(k('a05_autism_pop_asr_mf_ratio_2025'))} en 2025 y {n0(a05_0_9)} de los "
          f"{n0(k('a05_autism_entries_2025'))} ingresos ({ppct(k('a05_autism_entries_share_age_0_9_2025'))}) en niños "
          f"de 0 a 9 años "
          f"({F('figS8_a05_age_sex')}, {TR(['ST13_a05_age_sex', 'E14_rem_a05_age_sex'])} del apéndice; definiciones "
          f"comparadas en "
          f"{F('E19_rem_definition_era_sensitivity')}, {T('E19_rem_definition_era_sensitivity')} del apéndice).")
    doc.p(f"El stock de diciembre de niños con autismo bajo control en el programa NANEAS (P2) aumentó de "
          f"{n0(k('p2_tea_dec_2019'))} en 2019 a {n0(k('p2_tea_dec_2025'))} en 2025 "
          f"({k.series('p2_tea_dec_{y}', YEARS_REM)}; razón {n1(k('p2_tea_dec_ratio_2025_2019'))}), mientras los "
          f"establecimientos reportantes aumentaron de {n0(k('p2_tea_dec_estab_2019'))} a "
          f"{n0(k('p2_tea_dec_estab_2025'))}; el autismo representó el "
          f"{pct(k('p2_tea_share_of_naneas_dec_pct_2023'))} del stock NANEAS total en 2023 ({n0(k('p2_tea_dec_2023'))} "
          f"de {n0(k('p2_naneas_dec_2023'))}) y el {pct(k('p2_tea_share_of_naneas_dec_pct_2025'))} en 2025 "
          f"({n0(k('p2_tea_dec_2025'))} de {n0(k('p2_naneas_dec_2025'))}; {F('E15_rem_p2_p6_detail')}, "
          f"{T('E15_rem_p2_p6_detail')} del apéndice). El corte de junio de 2020 cayó al "
          f"{ppct(k('p2_jun_dec_ratio_2020'))} del stock de diciembre ({n0(k('p2_tea_jun_2020'))} frente a "
          f"{n0(k('p2_tea_dec_2020'))}) porque pocos establecimientos reportaron: las series mensuales muestran que "
          f"la caída de abril a septiembre de 2020 fue de establecimientos reportantes, no de personas ({FR(['figS5_rem_june_december', 'figS13_rem_seasonality'])}, "
          f"{TR(['ST14_p2_p6_june_december', 'S13_rem_seasonality'])} del apéndice; índice mensual GRD: "
          f"{T('E1_grd_seasonality')} del apéndice). En P6, el stock de diciembre bajo "
          f"control por autismo estricto aumentó de {n0(k('p6_primary_autism_dec_2021'))} a "
          f"{n0(k('p6_primary_autism_dec_2025'))} en atención primaria y de {n0(k('p6_specialty_autism_dec_2021'))} a "
          f"{n0(k('p6_specialty_autism_dec_2025'))} en especialidad (2021–2025). Los ingresos a rehabilitación por "
          f"autismo (A28), reportados desde 2023, fueron {k.series('a28_primary_{y}', YEARS_A27)} en el nivel primario "
          f"y {k.series('a28_hospital_{y}', YEARS_A27)} en el nivel hospitalario (capacidad REM-20, nunca un "
          f"denominador: {F('figE22_rem20_capacity')}, {T('E22_rem20_capacity')} del apéndice).")

    doc.h2("Benchmarks poblacionales")
    doc.p(f"ENDIDE 2022 estimó autismo reportado en el {k.svy('svy_endide_adults_reported_total')} de los adultos de "
          f"18 años o más ({n0(k('svy_endide_adults_reported_total_cases'))} casos) y en el "
          f"{k.svy('svy_endide_children_reported_total')} de los niños de 2 a 17 años "
          f"({n0(k('svy_endide_children_reported_total_cases'))} casos), de los cuales el "
          f"{k.svy('svy_endide_children_confirmed_among_reported_total', 1)} tenía diagnóstico confirmado por médico "
          f"({n0(k('svy_endide_children_confirmed_among_reported_total_cases'))} de "
          f"{n0(k('svy_endide_children_confirmed_among_reported_total_n'))}; "
          f"{k.svy('svy_endide_children_reported_confirmed_total')} de todos los niños); el autismo reportado fue del "
          f"{pct(k('svy_endide_children_reported_male_pct'), 2)} en niños ({n0(k('svy_endide_children_reported_male_cases'))} "
          f"casos entre {n0(k('svy_endide_children_reported_male_n'))} encuestados) y del "
          f"{pct(k('svy_endide_children_reported_female_pct'), 2)} en niñas "
          f"({n0(k('svy_endide_children_reported_female_cases'))} de {n0(k('svy_endide_children_reported_female_n'))}). "
          f"ENCAVI 2023–24 estimó un diagnóstico "
          f"declarado de trastorno del espectro autista en el {k.svy('svy_encavi_15plus_diagnosed_total')} a los 15 "
          f"años o más ({n0(k('svy_encavi_15plus_diagnosed_total_cases'))} casos; efecto de diseño "
          f"{n2(k('svy_encavi_15plus_diagnosed_total_deff'))}). La mayoría de los dominios por sexo y edad son "
          f"imprecisos ({R.mfigp('fig4_triangulation', 'c')}; "
          f"{T('T5_survey_benchmarks')}, {F('figE23_surveys_detail')}, {T('E23_surveys_detail')} del apéndice); estos "
          f"benchmarks son autorreportados o reportados por el cuidador, no una validación de los códigos.")

    doc.h2("Triangulación educativa")
    doc.p(f"Los estudiantes autistas registrados en el PIE aumentaron de {n0(k('pie_tea_strict_2019'))} (TEA estricto) "
          f"y {n0(k('pie_tea_asperger_2019'))} (TEA-Asperger) en 2019 a {n0(k('pie_tea_strict_2023'))} y "
          f"{n0(k('pie_tea_asperger_2023'))} en 2023, cuando el TEA estricto representó el "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2023'))} de todos los estudiantes PIE ({n0(k('pie_tea_strict_2023'))} "
          f"de {n0(k('pie_total_enrolment_2023'))}) frente al {pct(k('pie_tea_strict_share_of_pie_pct_2019'))} en 2019 "
          f"({n0(k('pie_tea_strict_2019'))} de {n0(k('pie_total_enrolment_2019'))}); la serie armonizada TEA + Asperger "
          f"fue "
          f"{k.series('pie_harmonised_{y}', YEARS_REM)} en 2019–2025 (razón {n2(k('pie_harmonised_ratio_2025_2019'))}), "
          f"con 2024–2025 provenientes del informe de seguimiento de la Ley 21.545 "
          f"({R.mfigp('fig4_triangulation', 'a')}; {T('T6_education')} del apéndice). Para 2022 ese informe imprime "
          f"{n0(k('pie_2022_sinaces_printed'))} mientras que su propio total menos las escuelas especiales da "
          f"{n0(k('pie_2022_sinaces_total_minus_special'))}, la cifra ministerial; la diferencia de "
          f"{nw(k('pie_2022_discrepancy_cases'))} estudiantes se resolvió a favor de la fuente desagregada. Incluidas "
          f"las escuelas especiales, los estudiantes autistas registrados fueron "
          f"{n0(k('sinaces_total_autistic_students_2022'))} en 2022 y "
          f"{n0(k('sinaces_total_autistic_students_2025'))} en 2025 ({F('figE24_education_detail')}, "
          f"{T('E24_education_detail')} del apéndice).")
    doc.p(f"En la encuesta a cuidadores de cohortes completas de JUNAEB, la proporción ponderada de estudiantes con "
          f"diagnóstico médico reportado de TEA fue del {pct(k('junaeb_parvularia_all_pct_weighted_2024'), 2)} en "
          f"educación parvularia ({jn('parvularia', 2024)} casos no ponderados/respondentes), del "
          f"{pct(k('junaeb_basico1_all_pct_weighted_2024'), 2)} en 1.º básico ({jn('basico1', 2024)}) y del "
          f"{pct(k('junaeb_basico5_all_pct_weighted_2024'), 2)} en 5.º básico ({jn('basico5', 2024)}) en 2024 (1.º "
          f"medio no estimable: ítem vacío), y del {pct(k('junaeb_parvularia_all_pct_weighted_2025'), 2)} "
          f"({jn('parvularia', 2025)}), {pct(k('junaeb_basico1_all_pct_weighted_2025'), 2)} ({jn('basico1', 2025)}), "
          f"{pct(k('junaeb_basico5_all_pct_weighted_2025'), 2)} ({jn('basico5', 2025)}) y "
          f"{pct(k('junaeb_medio1_all_pct_weighted_2025'), 2)} ({jn('medio1', 2025)}) en 2025, con razones "
          f"hombres:mujeres entre "
          f"{n1(k('junaeb_medio1_mf_ratio_2025'))} (1.º medio) y {n1(k('junaeb_basico1_mf_ratio_2025'))} (1.º básico) "
          f"({R.mfigp('fig4_triangulation', 'b')}; {F('figS12_junaeb_sex_level')}, {T('S12_junaeb_sex_level')} del "
          f"apéndice); no puede estimarse ninguna tendencia anterior a 2024, y son reportes de cuidadores en cohortes "
          f"seleccionadas, no prevalencia nacional.")

    doc.h2("Territorio")
    t = territory_numbers()
    doc.p(f"Las tasas comunales de episodios GRD por residencia (razones estandarizadas suavizadas por Bayes empírico) "
          f"mostraron agrupamiento espacial: la I de Moran global fue {n2(t['moran']['queen'])} (contigüidad reina; "
          f"p = {JC.format_p(t['moran_p'], LANG)} con {n0(t['moran_perm'])} permutaciones; "
          f"{n2(min(t['moran'].values()))}–{n2(max(t['moran'].values()))} entre cuatro matrices de pesos). Tras el "
          f"control de Benjamini–Hochberg, {nw(t['hh'])} comunas fueron alto–alto, {nw(t['ll'])} bajo–bajo y "
          f"{nw(t['lh'], fem=True)} bajo–alto, y el Gi* identificó {nw(t['hot'])} puntos calientes y {nw(t['cold'])} "
          f"fríos entre {n0(t['n_lisa'])} comunas continentales. La desigualdad cayó a medida que se extendió el "
          f"reconocimiento: el coeficiente de Gini entre comunas fue {n2(t['gini'][2019])} en 2019 y "
          f"{n2(t['gini'][2024])} en 2024, las comunas con al menos un episodio aumentaron de "
          f"{n0(t['with_events'][2019])} a {n0(t['with_events'][2024])} de {n0(t['n_comunas'])}, y la participación "
          f"del decil superior en los episodios cayó del {ppct(t['top_decile'][2019])} (de "
          f"{n0(t['total_count'][2019])} con comuna de residencia) al {ppct(t['top_decile'][2024])} (de "
          f"{n0(t['total_count'][2024])}). Los "
          f"rangos comunales de episodios GRD (residencia) e ingresos A05 (lugar de "
          f"atención) se correlacionaron débilmente (ρ de Spearman {n2(t['rho'])}, {CI95} "
          f"{cir(t['rho_lo'], t['rho_hi'], 2)}), una comparación territorial de dos sistemas no enlazados con "
          f"geografías distintas, no un enlace "
          f"({FR(['figS9_regional_maps', 'E40_maps_grd_smoothed_ratio', 'E42_lisa_gistar_maps', 'E47_lorenz_theil', 'E49_regional_summary', 'E46_sae_deprivation'])}, "
          f"{TR(['S9_regional_rates', 'E62_grd_region_population_rates', 'E13_rem_a05_regional', 'E40_grd_smoothed_ratio_comuna', 'E42_local_class_counts', 'E51_lisa_significant_comunas', 'E43_moran_sensitivity_main', 'E50_moran_gistar_all', 'E47_inequality_gini_theil', 'E49_regional_summary', 'E44_correlation_matrix_comuna', 'E45_bivariate_moran_pairs', 'E48_rank_stability', 'E46_sae_association', 'E41_rem_comuna_place_of_care'])} "
          f"del apéndice). Las series región × año (residencia para el GRD, establecimiento reportante para A05) nunca "
          f"se dividen una por otra, y la I de Moran bivariada de cada par de indicadores es una colocalización "
          f"espacial de sistemas no enlazados, no una dirección ni un enlace.")

    doc.h2("Convergencia entre sistemas y sensibilidad de las tendencias")
    doc.p(f"Con índice 2021 = 100, la tasa GRD de episodios con F84 se situó en "
          f"{n0(k('conv_grd_any_rate_index2021_2024'))} en 2024, la tasa DEIS de F84 principal en "
          f"{n0(k('conv_deis_principal_rate_index2021_2024'))}, los ingresos A05 por autismo estricto en "
          f"{n0(k('conv_a05_strict_entries_index2021_2025'))} en 2025, el stock P2 de diciembre en "
          f"{n0(k('conv_p2_december_stock_index2021_2025'))}, el stock P6 de atención primaria en "
          f"{n0(k('conv_p6_primary_strict_stock_index2021_2025'))} y el PIE armonizado en "
          f"{n0(k('conv_pie_harmonised_index2021_2025'))} ({R.mfigp('fig4_triangulation', 'd-e')}; "
          f"{TR(['S_convergence_index', 'F4_triangulation_series'])}, {F('figE26_cross_source')}, "
          f"{T('E26_cross_source')} del apéndice); los índices comparten dirección y tiempo (aumentos más pronunciados "
          f"en 2022–2024), pero no unidades, denominadores ni definiciones.")
    doc.p(f"La {R.mtab('T7_models')} presenta los modelos preespecificados. El CPA de los episodios GRD con F84 por "
          f"100.000 episodios fue {k.apc('apc_grd_any_obs')} en el panel observado y {k.apc('apc_grd_any_fixed65')} "
          f"en el panel fijo; el ajuste por profundidad diagnóstica media lo elevó a "
          f"{k.apc('apc_grd_any_obs_depth')}, el indicador de disrupción 2020–2021 lo redujo a "
          f"{k.apc('apc_grd_any_obs_disruption')}, la ventana 2021–2024 dio {k.apc('apc_grd_any_obs_2021_2024')} y "
          f"la hospitalización estricta {k.apc('apc_grd_any_hosp')} ({n1(k('apc_grd_any_sensitivity_min'))}–"
          f"{n1(k('apc_grd_any_sensitivity_max'))}{NBSP}% en las {n0(k('apc_grd_any_sensitivity_n_specs'))} "
          f"especificaciones). F84 principal creció al {k.apc('apc_grd_principal_obs')} "
          f"({n1(k('apc_grd_principal_sensitivity_min'))}–{n1(k('apc_grd_principal_sensitivity_max'))}{NBSP}% entre "
          f"especificaciones). Los modelos de efectos fijos de hospital dieron {n1(k('apc_grd_hospital_fe'))}{NBSP}% "
          f"({CI95} agrupado por hospital "
          f"{cir(k('apc_grd_hospital_fe_cluster_lo'), k('apc_grd_hospital_fe_cluster_hi'))}) y el modelo de "
          f"intercepto aleatorio {n1(k('apc_grd_hospital_ri'))}{NBSP}%; cada diagnóstico codificado adicional se "
          f"asoció con una razón de tasas de {n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} dentro de "
          f"los hospitales. Por 100.000 residentes el CPA ajustado por edad fue "
          f"{k.apc('apc_grd_pop_any_total_ageadj')}, mayor en mujeres ({n1(k('apc_grd_pop_any_female_ageadj'))}{NBSP}%) "
          f"que en hombres ({n1(k('apc_grd_pop_any_male_ageadj'))}{NBSP}%). Los egresos DEIS con F84 principal "
          f"crecieron al {k.apc('apc_deis_principal')} ({R.mfigp('fig4_triangulation', 'f')}; cada especificación "
          f"con su ajuste en la {F('figS4_models_cpa')} y las {TR(['T7_models', 'T7_models_cpa_full'])} del "
          f"apéndice).")
    doc.p(f"Los ingresos A05 por autismo estricto crecieron al {k.apc('apc_a05_autism_pop')} por 100.000 residentes, "
          f"{k.apc('apc_a05_autism_estab')} por establecimiento reportante, {k.apc('apc_a05_autism_stable_pop')} en "
          f"el panel estable y {k.apc('apc_a05_autism_ageadj_total')} tras el ajuste por edad "
          f"({n1(k('apc_a05_autism_ageadj_female'))}{NBSP}% en mujeres, {n1(k('apc_a05_autism_ageadj_male'))}{NBSP}% "
          f"en hombres); el stock P2 de diciembre al {k.apc('apc_p2_dec')} como conteo, {k.apc('apc_p2_dec_estab')} "
          f"por establecimiento reportante, {k.apc('apc_p2_dec_stable')} en el panel estable de "
          f"{n0(k('p2_tea_dec_stable_panel_n'))} establecimientos y {k.apc('apc_p2_dec_naneas_offset')} por 100 "
          f"NANEAS bajo control (2023–2025); el stock P6 de atención primaria al {k.apc('apc_p6_primary_autism')} "
          f"({n1(k('apc_p6_primary_autism_estab'))}{NBSP}% por establecimiento) y el PIE armonizado al "
          f"{k.apc('apc_pie_harmonised')}. La dispersión fue grande en los modelos de flujos y stocks, y ninguna "
          f"especificación estima un efecto de la Ley 21.545.")
    doc.p(f"Los {n0(k('t8_rows'))} controles de reproducción {CR.label(CR.ANALYSIS_PLAN, LANG)} ({n0(k('t8_ok'))} "
          f"coinciden, {n0(k('t8_differs'))} difieren, todas documentadas) se listan por familia en las "
          f"{TR(['T8_controls_compact', 'E79_reproduction_controls_by_family'])} del apéndice.")

    # ---------------- Discusión ----------------
    junaeb_levels = ("parvularia", "basico1", "basico5", "medio1")
    junaeb_2025 = [k(f"junaeb_{lvl}_all_pct_weighted_2025") for lvl in junaeb_levels]
    junaeb_min, junaeb_max = min(junaeb_2025), max(junaeb_2025)
    junaeb_mf = [k(f"junaeb_{lvl}_mf_ratio_2025") for lvl in junaeb_levels]
    junaeb_mf_min, junaeb_mf_max = min(junaeb_mf), max(junaeb_mf)
    endide_mf = k('svy_endide_children_reported_male_pct') / k('svy_endide_children_reported_female_pct')
    doc.h1("Discusión")
    doc.p(f"En los sistemas públicos hospitalario, de atención primaria, de especialidad y educativo de Chile, el "
          f"reconocimiento administrativo del autismo se expandió varias veces entre 2019 y 2025: "
          f"{n1(k('grd_f84_any_rate_ratio_2024_2019'))} veces en la tasa de episodios GRD con F84 documentado, "
          f"{n1(k('a05_autism_entries_ratio_2025_2021'))} veces en los ingresos a programas por autismo estricto en "
          f"cuatro años, {n1(k('p2_tea_dec_ratio_2025_2019'))} veces en el stock de diciembre de niños con autismo bajo "
          f"control y {n1(k('pie_harmonised_ratio_2025_2019'))} veces en los estudiantes autistas registrados; los "
          f"conteos hospitalarios cayeron con la actividad en 2020 mientras los stocks no, y los aumentos más "
          f"pronunciados llegaron en 2022–2024. Los aumentos sobreviven a todas las sensibilidades preespecificadas, "
          f"aunque su magnitud cambia: el CPA del GRD abarca del {n1(k('apc_grd_any_sensitivity_min'))} al "
          f"{n1(k('apc_grd_any_sensitivity_max'))}{NBSP}% entre especificaciones, los ingresos A05 crecen al "
          f"{n1(k('apc_a05_autism_estab'))}{NBSP}% por establecimiento reportante frente al "
          f"{n1(k('apc_a05_autism_pop'))}{NBSP}% por residente, y el stock P2 al {n1(k('apc_p2_dec_estab'))}{NBSP}% "
          f"por establecimiento frente al {n1(k('apc_p2_dec'))}{NBSP}% como conteo, una brecha que acota la "
          f"contribución de la expansión del reporte.")
    doc.p(f"Deben separarse tres constructos: el reconocimiento administrativo es el registro de un código; la demanda "
          f"registrada es el volumen de contactos que lo llevan; la epidemiología subyacente es la ocurrencia del "
          f"autismo en la población; nuestros datos miden los dos primeros. En el GRD, el "
          f"{pct(k('grd_f84_secondary_only_share_2024_pct'))} de los episodios con F84 en 2024 lo llevaba como "
          f"diagnóstico secundario y F84 principal creció al {n1(k('apc_grd_principal_obs'))}{NBSP}% frente al "
          f"{n1(k('apc_grd_any_obs'))}{NBSP}% para cualquier posición, de modo que la mayor parte de la señal "
          f"hospitalaria es la documentación del autismo en episodios ingresados por otras razones, y la profundidad "
          f"de codificación cambia lo que capturan los datos administrativos [@iezzoni1992]. Sin embargo, la tasa "
          f"aumentó dentro de cada estrato de profundidad diagnóstica de tres o más diagnósticos y cada diagnóstico "
          f"adicional explicó solo una razón de tasas de {n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} "
          f"dentro de los hospitales, de modo que la codificación más profunda da cuenta de parte del cambio y no de "
          f"su totalidad. En REM, la brecha entre el crecimiento por establecimiento y el crecimiento por residente "
          f"acota la contribución de la expansión del reporte, y los stocks bajo control acumulan personas por "
          f"construcción. Las prácticas de codificación y reporte son en sí mismas determinantes de las tasas "
          f"registradas [@song2010]; el rango de {n0(k('grd_hosp2024_rate_ratio_max_min'))} veces entre hospitales en "
          f"2024 refleja tanto la composición pediátrica de casos como la práctica.")
    doc.p(f"La convergencia entre sistemas independientes es informativa aunque midan cosas distintas: comparten "
          f"tiempo y dirección, una concentración en la primera infancia ({ppct(k('grd_f84_any_share_age_0_9_2024'))} "
          f"de los episodios GRD y {ppct(k('a05_autism_entries_share_age_0_9_2025'))} de los ingresos A05 en niños de "
          f"0 a 9 años) y una razón hombres:mujeres decreciente (de {n1(k('grd_f84_any_mf_ratio_n_2019'))} a "
          f"{n1(k('grd_f84_any_mf_ratio_n_2024'))} en los episodios GRD; {n1(k('a05_autism_pop_asr_mf_ratio_2025'))} "
          f"en los ingresos A05 estandarizados; {n1(junaeb_mf_min)}–{n1(junaeb_mf_max)} en las cohortes JUNAEB), con "
          f"crecimiento más rápido en mujeres en los modelos ajustados por edad ({F('figE26b_sex_ratio_multisource')}, "
          f"{T('E26b_sex_ratio_multisource')} del apéndice). Una razón que se aproxima a 2:1 está por debajo del 3:1 "
          f"de la detección activa y del 4:1 de las muestras pasivas [@loomes2017], y una razón decreciente se ha "
          f"documentado en una cohorte de nacimiento de base poblacional [@fyfe2026]; es consistente con "
          f"un reconocimiento creciente del autismo en niñas y mujeres, aunque los registros no enlazados no pueden "
          f"mostrar si refleja un subreconocimiento previo o una población que cambia; el benchmark ENDIDE en niños "
          f"chilenos ({n1(endide_mf)}:1) está más cerca de los valores de detección pasiva que de los flujos "
          f"administrativos de 2024–2025.")
    doc.p(f"Los registros de otros lugares mostraron antes el mismo patrón. En la atención primaria del Reino Unido, "
          f"los diagnósticos registrados de autismo aumentaron un 787{NBSP}% entre 1998 y 2018 [@russell2022]; en "
          f"Dinamarca, el 60{NBSP}% del aumento de la prevalencia fue atribuible a cambios en los criterios "
          f"diagnósticos y a la inclusión de contactos ambulatorios [@hansen2015]; en Suecia, los diagnósticos "
          f"registrados aumentaron de forma pronunciada en diez años mientras el fenotipo poblacional se mantuvo "
          f"estable [@lundstrom2015]; y en Estados Unidos, la vigilancia multifuente de niños de ocho años alcanzó "
          f"uno de cada 31 niños en 2022 [@shaw2025]. Los cambios anuales chilenos del "
          f"{n0(k('apc_grd_any_sensitivity_min'))}–{n0(k('apc_grd_any_sensitivity_max'))}{NBSP}% en episodios "
          f"hospitalarios y del {n0(k('apc_a05_autism_estab'))}–{n0(k('apc_a05_autism_pop'))}{NBSP}% en ingresos a "
          f"programas están muy por encima de las tasas de largo plazo de esos países; los benchmarks de encuesta del "
          f"{pct(k('svy_endide_children_reported_confirmed_total_pct'), 1)}–"
          f"{pct(k('svy_endide_children_reported_total_pct'), 1)} en niños son del orden de la prevalencia "
          f"identificada en países de ingresos altos, mientras que los flujos y stocks administrativos, que no son "
          f"prevalencia, permanecen muy por debajo del número de personas que esos benchmarks implican.")
    doc.p(f"En América Latina, un estudio de seis países que incluyó a Chile documentó el diagnóstico tardío y el papel "
          f"de la cobertura pública [@montielnava2024]. La red pública que observamos atiende a los residentes "
          f"asegurados por FONASA ({pct(k('share_fonasa_ine_pct_2025'), 0)} de la población en 2025); la atención "
          f"comprada de forma privada, las redes ISAPRE y las fuerzas armadas son invisibles para el GRD y el REM, y "
          f"los cuidadores chilenos reportan que el acceso al diagnóstico y a los servicios difiere según el seguro y "
          f"la región [@garcia2022]. El reconocimiento depende, por tanto, de la oferta, y la geografía del lugar de "
          f"atención difiere de la de la residencia.")
    doc.p(f"Las implicancias son prácticas. Cada etapa de la ruta pública está bajo presión: los ingresos a programas "
          f"por autismo estricto alcanzaron {n0(k('a05_autism_entries_2025'))} en 2025, los stocks bajo control en "
          f"atención primaria se multiplicaron por {n1(k('p6_primary_autism_dec_ratio_2025_2021'))} en cuatro años, "
          f"los ingresos a rehabilitación de nivel primario aumentaron {n1(k('a28_primary_ratio_2025_2023'))} veces en "
          f"dos años, y los estudiantes autistas representan el {pct(k('pie_tea_strict_share_of_pie_pct_2023'))} de "
          f"los registros PIE (2023) y el {pct(junaeb_min)}–{pct(junaeb_max)} de las cohortes escolares encuestadas "
          f"en 2025. Los servicios de diagnóstico, seguimiento, rehabilitación y escolares deben planificarse para "
          f"una demanda que sigue en aumento, y el monitoreo exigido por la Ley 21.545 debería informar el número de "
          f"establecimientos reportantes, la era de definición y la regla de codificación junto a cada conteo y "
          f"avanzar hacia el enlace a nivel de persona con los debidos resguardos, de modo que el reconocimiento "
          f"pueda distinguirse de los recontactos y de la acumulación de los stocks.")
    doc.p(f"Sus fortalezas (cobertura nacional de todas las fuentes públicas, procedencia congelada, controles y "
          f"sensibilidades preespecificados) no eliminan sus limitaciones. La pandemia de COVID-19 deprimió la "
          f"actividad y el reporte en 2020–2021 y su recuperación se superpone con todos los cambios posteriores; el "
          f"indicador de disrupción los describe más que corregirlos. Los quiebres taxonómicos (categorías de TGD en "
          f"2021, cuatro eras de A03, el ítem JUNAEB desde 2023) truncan las series, y el archivo REM de 2025 puede "
          f"estar incompleto ({n0(k('a05_autism_entries_estab_2025'))} establecimientos frente a "
          f"{n0(k('a05_autism_entries_estab_2024'))} en 2024). Los paneles cambiaron, y los paneles estables son "
          f"sensibilidades conservadoras y no series representativas. Los numeradores se localizan por lugar de "
          f"atención y los denominadores por residencia, de modo que las tasas poblacionales son lecturas "
          f"complementarias y las comparaciones regionales y comunales son ecológicas (residencia para el GRD, lugar "
          f"de atención para el REM). El sexo es el registrado administrativamente o el declarado a la encuesta, no el "
          f"sexo asignado al nacer ni la identidad de género, de modo que la razón hombres:mujeres decreciente describe "
          f"el registro y no puede darse ningún resultado por género. Las fuentes no están enlazadas por persona, por lo "
          f"que no puede estimarse "
          f"ninguna trayectoria, cascada ni cociente de conversión, y las personas son únicas solo dentro de un año. "
          f"Ningún código se validó clínicamente; las encuestas, con pocos casos y distinta formulación, son "
          f"benchmarks, no validación. Las series son cortas (tres a siete puntos), de modo que los modelos de "
          f"tendencia son descriptivos y la dispersión es grande.")
    doc.p("No podemos separar un cambio genuino en la ocurrencia del autismo de la concienciación, la búsqueda de "
          "atención, la oferta de servicios, la cobertura, la profundidad de codificación y las definiciones. La "
          "convergencia observada establece que el reconocimiento y la demanda registrada aumentaron en todos los "
          "sistemas; no establece que el autismo se haya vuelto más frecuente, y la coincidencia de la Ley 21.545 con "
          "los demás cambios impide cualquier atribución a la ley.")
    doc.h1("Conclusión")
    doc.p("Entre 2019 y 2025, los sistemas públicos de salud y educación de Chile registraron una expansión de varias "
          "veces del reconocimiento administrativo del autismo que converge en tiempo y dirección entre registros "
          "hospitalarios, de atención primaria, de especialidad, de rehabilitación y escolares no enlazados, y que se "
          "explica en parte, pero no en su totalidad, por la expansión del reporte, la profundidad de codificación y "
          "los cambios de definición. Para Chile y para otros sistemas segmentados de América Latina, estos conteos son "
          "una medida de la demanda que los servicios y la vigilancia deben planificar, no una medida de prevalencia.")

    # ---------------- Declaraciones ----------------
    doc.h1("Contribuciones")
    doc.p(f"{AUTHOR} concibió el estudio, escribió el plan de análisis, obtuvo y curó los datos, escribió el pipeline "
          f"de análisis, verificó los controles de reproducción, produjo las láminas y las tablas, interpretó los "
          f"resultados y escribió el manuscrito. [Segundo autor, por nombrar antes del envío] accedió de forma "
          f"independiente a los archivos fuente listados en la {T('ST7_provenance')} del apéndice, reejecutó el "
          f"pipeline y verificó los valores informados en el texto, en la {R.mtab('T2_grd_core')} y la "
          f"{R.mtab('T7_models')} y en el apéndice. {AUTHOR} y [segundo autor] accedieron directamente a los datos "
          f"subyacentes informados en el manuscrito y los verificaron. Todos los autores tuvieron acceso completo a "
          f"todos los datos y aceptan la responsabilidad de la decisión de enviar el manuscrito a publicación.")
    doc.h1("Declaración de intereses")
    doc.p("Los autores declaran no tener conflictos de interés. [Cada autor completará el formulario de declaración del "
          "ICMJE en el envío.]")
    doc.h1("Declaración de disponibilidad de datos")
    doc.p(f"Todos los datos fuente son públicos y se listan, con proveedores, archivos, versiones y hashes SHA-256, en la "
          f"{T('T1_sources')} y la {T('ST7_provenance')} del apéndice. Las tablas tidy derivadas (diccionario de datos: "
          f"{T('E80_tidy_data_dictionary')} del apéndice; {n0(k('n_tables_supp_files_en'))} archivos de tablas "
          f"suplementarias y {n0(k('n_tables_main_en'))} de tablas principales por variante e idioma), el material "
          f"extendido completo del corpus bilingüe ({n0(len(PE.MAIN_FIGURES) + len(SM.FIGURE_ORDER))} láminas y "
          f"{n0(len(PE.MAIN_TABLES) + len(SM.TABLE_ORDER))} tablas, de las cuales este artículo y su apéndice imprimen "
          f"{n0(len(JC.BODY_FIGURES) + len(JC.SUPP_FIGURES))} y "
          f"{n0(len(set(JC.BODY_TABLES) | set(JC.SUPP_TABLES) - JC.SYNTHETIC_TABLES))}; el resto se nombra en la parte B "
          f"del apéndice), la tabla plana de cada cantidad citada en el texto, las salidas de los modelos, el plan de análisis, la bitácora de "
          f"decisiones, la lista de verificación de reporte y el pipeline completo en Python que reproduce cada lámina "
          f"y tabla a partir de los archivos fuente se depositarán en un repositorio público con identificador "
          f"persistente [URL y DOI por insertar en la aceptación] y están disponibles desde ahora a través del autor "
          f"de correspondencia; el acceso es abierto bajo una licencia permisiva, sin restricciones ni solicitud, desde "
          f"la fecha de publicación. No se redistribuyen datos a nivel de persona: los microdatos GRD, REM, DEIS, de "
          f"encuestas y JUNAEB deben obtenerse de los portales oficiales citados.")
    doc.h1("Financiamiento")
    doc.p("Ninguno.")
    doc.h1("Agradecimientos")
    doc.p("Agradecemos al Departamento de Estadísticas e Información de Salud (DEIS) del Ministerio de Salud, a FONASA, a "
          "la Superintendencia de Salud, al Instituto Nacional de Estadísticas, al Ministerio de Educación, a JUNAEB y al "
          "Ministerio de Desarrollo Social y Familia por publicar los datos usados en este estudio.")
    doc.h1("Declaración sobre el uso de inteligencia artificial")
    doc.p("De acuerdo con la política de la revista, el autor declara que en este trabajo se usaron asistentes basados en "
          "grandes modelos de lenguaje: Claude Code (Anthropic; modelo Claude Fable 5.1, claude-fable-5-1) y OpenAI Codex "
          "(extensión de Visual Studio Code; [versión por confirmar por el autor]). Propósito y alcance: escritura y "
          "depuración del pipeline de análisis en Python, de los scripts de láminas y tablas y del constructor de "
          "documentos; redacción y edición de este manuscrito, su resumen, el panel «Investigación en contexto» y el "
          "apéndice suplementario a partir de las salidas calculadas; y verificación de los metadatos bibliográficos "
          "contra PubMed, Crossref y páginas oficiales. Supervisión: el autor especificó cada análisis y regla, revisó y "
          "ejecutó todo el código, verificó cada cifra informada contra los archivos de salida y los controles de "
          "reproducción, comprobó cada referencia contra su fuente y editó el texto final; las herramientas no generaron "
          "ni alteraron datos, imágenes ni referencias, y no son autoras. Los prompts están disponibles a solicitud.")
    doc.add("refs", None)

    # ---------------- Tablas y láminas, una por página ----------------
    for key in JC.BODY_TABLES:
        kind, payload = R.table_block(key, f"Tabla {JC.BODY_TABLES.index(key) + 1}", note=body_note(R, key))
        doc.add(kind, payload)
    for key in JC.BODY_FIGURES:
        heading = R.title_text(key)
        kind, payload = R.figure_block(key, f"Figura {JC.BODY_FIGURES.index(key) + 1}", body=True,
                                       caption=body_legend(R, key))
        payload["heading"] = heading
        doc.add(kind, payload)

    blocks = doc.blocks
    R.article_citations = len(R.main_citations)
    R.assert_monotone(complete=True)

    wc = PS.word_counts(blocks)
    n_refs = len(PE.citation_keys(blocks))
    counts = (f"Texto del manuscrito {n0(wc['core_body'])} palabras; Resumen {n0(wc['summary'])} palabras; "
              f"{n0(n_refs)} referencias; {nw(len(JC.BODY_TABLES))} tablas; {nw(len(JC.BODY_FIGURES))} láminas; "
              f"apéndice con {n0(len(JC.SUPP_FIGURES))} láminas y {n0(len(JC.SUPP_TABLES))} tablas.")
    for kind, payload in blocks:
        if kind == "authors":
            payload["lines"] = [counts if line == "__COUNTS__" else line for line in payload["lines"]]
    return blocks


if __name__ == "__main__":
    import json

    V = PE.load_values(VARIANT)
    blocks = article(V)
    print(json.dumps(dict(word_counts=PS.word_counts(blocks), sections=JC.budget_report(blocks, LANG),
                          citations=PE.citation_keys(blocks)), indent=1, ensure_ascii=False))
