# -*- coding: utf-8 -*-
"""prose_es.py — Manuscrito y apéndice suplementario en español (versión de trabajo del artículo para
la revista de destino; la revista publica en inglés, véase prose_en.py).

API pública
-----------
    manuscript(variant, V) -> lista de bloques de docx_builder (documento principal, español)
    supplement(variant, V) -> lista de bloques de docx_builder (apéndice suplementario, español)
    load_values(variant)   -> dict V leído de outputs/values_<variant>.json (reexportado de prose_en)
    word_counts(blocks)    -> dict con recuentos de palabras (resumen, panel, cuerpo núcleo sin '[OPT] ', ...)
    citation_keys(blocks, include_opt=False) -> lista ordenada de claves [@clave] distintas (reexportada de prose_en)
    supplementary_map(variant, V) -> {'figures': {stem: 'Figura Sn'}, 'tables': {stem: 'Tabla Sn'}}
    strip_opt(blocks)      -> bloques sin los párrafos opcionales (reexportada de prose_en)
    build_all(out_dir)     -> construye manuscrito y suplemento de ambas variantes

Convenciones
------------
* Traducción fiel de prose_en.py, párrafo por párrafo: mismas claves de V, mismos párrafos '[OPT] ', mismas claves de
  citación [@clave] en el mismo orden y mismas llamadas R.fig()/R.tab() en el mismo orden, de modo que la numeración
  suplementaria (Figura S1, S2, …; Tabla S1, S2, …) es idéntica a la del documento en inglés.
* Ninguna cifra literal: todo número procede de V y se formatea con common.fmt_number(x, dec, 'es') (coma decimal,
  punto de miles) y common.fmt_ci(lo, hi, dec, 'es') («a» entre límites). Porcentajes con espacio duro antes de «%»
  («12,5 %») e «IC 95 %», como en las leyendas de outputs/<variant>/es. Los únicos números literales son los de la
  literatura citada (787 %, 60 %, uno de cada 31, 0,3 %/0,9 %), códigos y años.
* Reglas de lenguaje: «episodios GRD con F84 documentado» (nunca «hospitalizaciones por autismo»); ruta administrativa
  agregada (sin cascada ni trayectorias individuales ni cocientes de conversión); stocks y flujos separados; lugar de
  atención frente a residencia; panel fijo de 65 hospitales frente al observado; personas únicas solo dentro de cada
  año; encuestas con diseño complejo; Ley 21.545 (marzo de 2023) como contexto coincidente, nunca como intervención.
* Las leyendas de láminas provienen de outputs/<variant>/es/figures/captions.json y los títulos/notas de tablas de
  outputs/<variant>/es/tables/titles.json (claves = nombres de archivo); los números provisionales de esos títulos
  («Figura S4.», «Tabla ST7.», «Tabla 8 (versión breve).», «Tabla F3 (datos).») se eliminan y se sustituyen por el
  rótulo secuencial. Las láminas PNG usadas son las de la carpeta es/.
* Los nombres propios de instrumentos y fuentes no se traducen (M-CHAT-R/F, GRD, REM, FONASA, ISAPRE, DEIS, INE, APS,
  NANEAS, PIE, JUNAEB, ENDIDE, ENCAVI, SINACES, MINEDUC).
* Las listas de archivos (MAIN_FIGURES, MAIN_TABLES, SUPP_FIGURES, SUPP_TABLES) se importan de prose_en para que la
  resolución de colisiones de numeración tenga una sola fuente de verdad.

Uso: `python prose_es.py [--out DIR]` construye ambas variantes (manuscrito + suplemento) e imprime los recuentos.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import fmt_ci, fmt_number  # noqa: E402
import controls_registry as CR  # noqa: E402  (ámbitos con nombre de los controles: una sola fuente para cada total)
import supplementary_material as SM  # noqa: E402  (inventario y constructor compartidos de la parte suplementaria)
from prose_en import (MAIN_FIGURES, MAIN_TABLES, SUPP_FIGURES, SUPP_TABLES, YEARS_A05, YEARS_A27,  # noqa: E402
                      YEARS_GRD, YEARS_REM, AUTHOR, AUTHOR_EMAIL, BIB, OPT, OUT, citation_keys, load_values,
                      panel_suffix, strip_opt, table_note)

LANG = "es"
NBSP = " "
CI95 = f"IC 95{NBSP}%"

TITLE = ("Reconocimiento administrativo del autismo en los sistemas de salud y educación de Chile, 2019–2025: "
         "un estudio nacional de vigilancia multifuente")
RUNNING_TITLE = "Reconocimiento administrativo del autismo en Chile, 2019–2025"
SUPP_PART_H1 = "Material suplementario"        # encabezado de la parte suplementaria dentro del manuscrito
SUPP_REFS_H1 = "Referencias suplementarias"
AFFILIATION = "[Afiliación institucional por completar por el autor antes del envío]"

VARIANT_LABEL = {
    "con_rett": "familia F84 completa (F84.0–F84.9, incluido el síndrome de Rett, F84.2)",
    "sin_rett": "familia F84 sin síndrome de Rett (F84.2 excluido)",
}
VARIANT_SHORT = {"con_rett": "con Rett", "sin_rett": "sin Rett"}

# ---------------------------------------------------------------------------
# Formato (español)
# ---------------------------------------------------------------------------
def n0(x):
    return fmt_number(x, 0, LANG)

def n1(x):
    return fmt_number(x, 1, LANG)

def n2(x):
    return fmt_number(x, 2, LANG)

def ci(lo, hi, dec=1):
    return fmt_ci(lo, hi, dec, LANG)

def pct(x, dec=1):
    return f"{fmt_number(x, dec, LANG)}{NBSP}%"

def ppct(x, dec=1):
    """Proporción en [0, 1] formateada como porcentaje."""
    return pct(100.0 * x, dec) if x is not None else "—"

def lst(items):
    items = [str(i) for i in items]
    if len(items) <= 1:
        return "".join(items)
    return ", ".join(items[:-1]) + " y " + items[-1]

def millions(x, dec=1):
    return f"{fmt_number(x / 1e6, dec, LANG)} millones"

#: Glosa española de las etiquetas con que values_*.json nombra los códigos REM de A27 y A28. El inglés las
#: imprime con `prose_en.codes()`; sin esta glosa el documento en español imprimía «counselling=29101566,
#: assisted_referral=29101574», es decir, el volcado crudo del archivo de valores, con etiqueta inglesa y signo
#: de igual. Una etiqueta nueva sin glosa falla aquí en vez de colarse sin traducir.
CODE_LABEL_ES = {"counselling": "consejería", "assisted_referral": "referencia asistida",
                 "primary": "nivel primario", "hospital": "nivel hospitalario"}

def codes(s) -> str:
    """Listas de códigos de values_*.json como prosa española (equivalente de `prose_en.codes`): las familias
    unidas por «+» llevan espacios (para que la línea pueda cortarse) y los pares «etiqueta=código» se traducen
    y se leen «etiqueta código y etiqueta código»."""
    s = str(s)
    if "=" in s:
        parts = []
        for pair in s.split(","):
            label, _, code = pair.strip().partition("=")
            label = label.strip()
            if label not in CODE_LABEL_ES:
                raise KeyError(f"falta la glosa española de la etiqueta de código '{label}'")
            parts.append(f"{CODE_LABEL_ES[label]} {code.strip()}")
        return lst(parts)
    return s.replace("+", " + ")

_SMALL = {0: "cero", 1: "un", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho",
          9: "nueve", 10: "diez"}

def nw(x, fem=False):
    """Números de uno a diez en palabras (estilo de la revista); mayores en cifras. `fem` da «una» para 1."""
    try:
        xi = int(x)
    except (TypeError, ValueError):
        return n0(x)
    if xi == x and xi in _SMALL:
        return "una" if (xi == 1 and fem) else _SMALL[xi]
    return n0(x)

class _V:
    """Accesor estricto sobre el diccionario plano de valores: una clave ausente lanza error (nunca un blanco)."""

    def __init__(self, V: dict, variant: str):
        self.V = V
        self.variant = variant

    def __call__(self, key: str):
        if key not in self.V:
            raise KeyError(f"values_{self.variant}.json carece de la clave '{key}' citada por prose_es.py")
        return self.V[key]

    def series(self, tmpl: str, years, dec=0):
        return lst(fmt_number(self(tmpl.format(y=y)), dec, LANG) for y in years)

    def apc(self, alias: str, dec=1):
        return f"{fmt_number(self(alias), dec, LANG)}{NBSP}% ({CI95} {ci(self(alias + '_lo'), self(alias + '_hi'), dec)})"

    def apc_disp(self, alias: str, dec=1):
        return f"{self.apc(alias, dec)}; dispersión {n1(self(alias + '_disp'))}"

    def rate(self, prefix: str, year, dec=1):
        return (f"{fmt_number(self(f'{prefix}_rate_{year}'), dec, LANG)} ({CI95} "
                f"{ci(self(f'{prefix}_rate_lo_{year}'), self(f'{prefix}_rate_hi_{year}'), dec)})")

    def est_ci(self, base: str, dec=1, suffix_lo="_lo", suffix_hi="_hi"):
        return f"{fmt_number(self(base), dec, LANG)} ({CI95} {ci(self(base + suffix_lo), self(base + suffix_hi), dec)})"

    def est_ci_y(self, prefix: str, year, dec=1):
        """Estimación con IC cuyas claves llevan el año al final: <prefix>_<y>, <prefix>_lo_<y>, <prefix>_hi_<y>."""
        return (f"{fmt_number(self(f'{prefix}_{year}'), dec, LANG)} ({CI95} "
                f"{ci(self(f'{prefix}_lo_{year}'), self(f'{prefix}_hi_{year}'), dec)})")

    def svy(self, base: str, dec=2):
        return f"{pct(self(base + '_pct'), dec)} ({CI95} {ci(self(base + '_lo_pct'), self(base + '_hi_pct'), dec)})"

# ---------------------------------------------------------------------------
# Registro de numeración suplementaria y ensamblador
# ---------------------------------------------------------------------------
_PREFIX_RE = re.compile(r"^(Figure|Figura|Table|Tabla|Plate|L\u00e1mina)\s+[A-Za-z]{0,3}\d+[a-zA-Z]?\s*"
                       r"(\([^)]*\)\s*)?[.:]?\s*")

def _strip_prefix(title: str) -> str:
    return _PREFIX_RE.sub("", title or "").strip()

class _Registry:
    """Registro de numeración compartido (versión española del de prose_en).

    Los ítems suplementarios se numeran por su posición en SUPP_FIGURES / SUPP_TABLES, que es el orden en que la
    parte suplementaria los imprime, de modo que el manuscrito y el apéndice separado siempre coinciden. Los ítems
    del artículo se numeran por su posición en MAIN_FIGURES / MAIN_TABLES y solo pueden citarse con mfig()/mtab():
    ninguna cita de figura o tabla del artículo puede escribirse como literal en prose_es.py.
    """

    FIG_WORD, TAB_WORD = "Figura", "Tabla"

    def __init__(self, variant: str):
        self.variant = variant
        self.figs: list[str] = []
        self.tabs: list[str] = []
        self.main_figs: list[str] = []
        self.main_tabs: list[str] = []
        self.main_citations: list[str] = []
        self.article_citations = 0   # citations produced before the article was closed
        fdir = OUT / variant / LANG / "figures"
        tdir = OUT / variant / LANG / "tables"
        xfdir = OUT / variant / LANG / "extra" / "figures"
        xtdir = OUT / variant / LANG / "extra" / "tables"
        self.fdir, self.tdir, self.xfdir, self.xtdir = fdir, tdir, xfdir, xtdir
        with open(fdir / "captions.json", encoding="utf-8") as fh:
            base_captions = json.load(fh)
        with open(xfdir / "captions.json", encoding="utf-8") as fh:
            extra_captions = json.load(fh)
        with open(tdir / "titles.json", encoding="utf-8") as fh:
            base_titles = json.load(fh)
        with open(xtdir / "titles.json", encoding="utf-8") as fh:
            extra_titles = json.load(fh)
        clash = (set(base_captions) & set(extra_captions)) | (set(base_titles) & set(extra_titles))
        if clash:
            raise RuntimeError(f"nombres de archivo usados por las carpetas principal y extra: {sorted(clash)}")
        self.captions = {**extra_captions, **base_captions}
        self.titles = {**extra_titles, **base_titles}
        self._fig_dir = {k: xfdir for k in extra_captions} | {k: fdir for k in base_captions}
        self._tab_dir = {k: xtdir for k in extra_titles} | {k: tdir for k in base_titles}

    def fig(self, key: str) -> str:
        if key not in SUPP_FIGURES:
            raise KeyError(f"'{key}' no está en SUPP_FIGURES")
        if key not in self.figs:
            self.figs.append(key)
        return f"{self.FIG_WORD} S{SUPP_FIGURES.index(key) + 1}"

    def tab(self, key: str) -> str:
        if key not in SUPP_TABLES:
            raise KeyError(f"'{key}' no está en SUPP_TABLES")
        if key not in self.tabs:
            self.tabs.append(key)
        return f"{self.TAB_WORD} S{SUPP_TABLES.index(key) + 1}"

    def mfig(self, key: str) -> str:
        if key not in MAIN_FIGURES:
            raise KeyError(f"'{key}' no está en MAIN_FIGURES")
        if key not in self.main_figs:
            self.main_figs.append(key)
        label = f"{self.FIG_WORD} {MAIN_FIGURES.index(key) + 1}"
        self.main_citations.append(label)
        return label

    def mtab(self, key: str) -> str:
        if key not in MAIN_TABLES:
            raise KeyError(f"'{key}' no está en MAIN_TABLES")
        if key not in self.main_tabs:
            self.main_tabs.append(key)
        label = f"{self.TAB_WORD} {MAIN_TABLES.index(key) + 1}"
        self.main_citations.append(label)
        return label

    # -- citas de panel (minúscula, resueltas contra la leyenda de la propia lámina) ------------
    def _panels(self, key: str, panels: str) -> str:
        return panel_suffix(self.captions[key].get("caption", ""), panels, key)

    def figp(self, key: str, panels: str) -> str:
        """«Figura S12c»: cita de una lámina suplementaria con sus letras de panel."""
        return f"{self.fig(key)}{self._panels(key, panels)}"

    def mfigp(self, key: str, panels: str) -> str:
        """«Figura 3c», «Figura 5d–e»: cita de una lámina del artículo con sus letras de panel.

        Las letras se resuelven con `prose_en.panel_suffix`, contra la leyenda de la lámina EN ESTE IDIOMA, de
        modo que la cita y la lámina no pueden divergir ni entre sí ni entre los dos documentos."""
        return f"{self.mfig(key)}{self._panels(key, panels)}"

    def fig_path(self, key: str) -> Path:
        return self._fig_dir[key] / f"{key}.png"

    def tab_path(self, key: str) -> Path:
        return self._tab_dir[key] / f"{key}.csv"

    def nrows(self, key: str) -> int:
        """Filas de datos de una tabla suplementaria (cifra trazable a ese archivo de salida)."""
        return len(pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False))

    def figure_block(self, key: str, label: str):
        meta = self.captions[key]
        caption = f"{_strip_prefix(meta.get('title', ''))}. {meta.get('caption', '')}".strip()
        return ("figure", dict(path=self.fig_path(key), caption=caption, label=label))

    def table_block(self, key: str, label: str):
        meta = self.titles[key]
        df = pd.read_csv(self.tab_path(key), dtype=str, keep_default_na=False)
        return ("table", dict(df=df, title=_strip_prefix(meta.get("title", "")),
                              note=table_note(key, meta.get("note", ""), df, LANG), label=label))

class _Doc:
    def __init__(self):
        self.blocks: list = []

    def add(self, kind, payload):
        self.blocks.append((kind, payload))

    def h1(self, t):
        self.add("h1", t)

    def h2(self, t):
        self.add("h2", t)

    def h3(self, t):
        self.add("h3", t)

    def p(self, t, opt=False):
        self.add("p", (OPT + t) if opt else t)

    def bullets(self, items):
        self.add("bullets", list(items))

# ---------------------------------------------------------------------------
# Manuscrito
# ---------------------------------------------------------------------------
def _assemble(variant: str, V: dict):
    if variant not in VARIANT_LABEL:
        raise ValueError(f"variante desconocida '{variant}'")
    k = _V(V, variant)
    R = _Registry(variant)
    other = "sin_rett" if variant == "con_rett" else "con_rett"
    vlabel, olabel = VARIANT_LABEL[variant], VARIANT_LABEL[other]
    doc = _Doc()

    # ---------------- Portada ----------------
    doc.add("title", TITLE)
    doc.add("subtitle", f"Variante de análisis: {vlabel}. Título corto: {RUNNING_TITLE}.")
    doc.add("authors", dict(authors=[(AUTHOR, "1")], affiliations=[("1", AFFILIATION)],
                            lines=[f"Correspondencia: {AUTHOR}, {AUTHOR_EMAIL}",
                                   "Tipo de artículo: Artículo (investigación original). Guías de reporte: STROBE y RECORD.",
                                   "Versión en español de trabajo para el equipo autor; la revista publica en inglés "
                                   "(prose_en.py). Los recuentos de palabras, las claves de citación y la numeración de "
                                   "láminas y tablas se informan con prose_es.word_counts()."]))

    # ---------------- Resumen ----------------
    doc.h1("Resumen")
    doc.p("**Antecedentes** Los diagnósticos registrados de autismo han aumentado con fuerza en países de altos "
          "ingresos, pero la evidencia multifuente latinoamericana es escasa. Describimos cómo cambió el "
          "reconocimiento administrativo del autismo en los sistemas públicos de salud y educación de Chile en "
          "2019–2025 y su robustez frente a cobertura, codificación y definiciones.")
    doc.p("**Métodos** Estudio nacional de datos rutinarios no enlazados: episodios de grupos relacionados por el "
          "diagnóstico (GRD) y egresos DEIS (2019–2024), seis módulos REM (2019–2025), denominadores de aseguramiento, "
          "atención primaria y población, dos encuestas con diseño complejo y registros escolares. Estimamos tasas por "
          "100.000 episodios y por población, tasas estandarizadas OMS y cambios porcentuales anuales (CPA) "
          "cuasi-Poisson con sensibilidades.")
    doc.p(f"**Resultados** Los episodios GRD con F84 documentado aumentaron de {n0(k('grd_f84_any_n_2019'))} "
          f"({n1(k('grd_f84_any_rate_2019'))} por 100.000 episodios) en 2019 a {n0(k('grd_f84_any_n_2024'))} "
          f"({n1(k('grd_f84_any_rate_2024'))}) en 2024 (CPA {n1(k('apc_grd_any_obs'))}{NBSP}%, {CI95} "
          f"{ci(k('apc_grd_any_obs_lo'), k('apc_grd_any_obs_hi'))}; {n1(k('apc_grd_any_sensitivity_min'))}–"
          f"{n1(k('apc_grd_any_sensitivity_max'))}{NBSP}% entre especificaciones); el "
          f"{pct(k('grd_f84_secondary_only_share_2024_pct'))} llevaba F84 solo como secundario y la profundidad "
          f"diagnóstica media subió de {n2(k('grd_coding_depth_all_mean_2019'))} a "
          f"{n2(k('grd_coding_depth_all_mean_2024'))}. Los ingresos a salud mental por autismo estricto pasaron de "
          f"{n0(k('a05_autism_entries_2021'))} (2021) a {n0(k('a05_autism_entries_2025'))} (2025), los niños bajo "
          f"control de {n0(k('p2_tea_dec_2019'))} a {n0(k('p2_tea_dec_2025'))} y los estudiantes en integración "
          f"escolar de {n0(k('pie_harmonised_2019'))} a {n0(k('pie_harmonised_2025'))}. Las encuestas reportaron "
          f"autismo en el {pct(k('svy_endide_children_reported_total_pct'), 2)} de los niños de 2 a 17 años y en el "
          f"{pct(k('svy_endide_adults_reported_total_pct'), 2)}–{pct(k('svy_encavi_15plus_diagnosed_total_pct'), 2)} "
          f"de adultos y adolescentes mayores.")
    doc.p("**Interpretación** Sistemas independientes de salud y educación registraron una expansión de varias veces "
          "del reconocimiento administrativo del autismo, coincidente con la recuperación pospandemia, la expansión "
          "del reporte, los cambios de códigos, la codificación más profunda y, desde 2023, la Ley 21.545. Reporte y "
          "codificación explican parte del cambio; la contribución epidemiológica no puede separarse. Capacidad "
          "asistencial y vigilancia deben seguir este ritmo.")
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
         "basada en tamizaje y a una estimación basada en registros escolares. Ningún estudio ha examinado cómo varios "
         "sistemas administrativos no enlazados de un país latinoamericano registraron el autismo en el mismo período, "
         "ni ha cuantificado cuánto del cambio registrado sobrevive al ajuste por cobertura del reporte, profundidad de "
         "codificación y quiebres de definición."),
        ("Valor añadido de este estudio",
         "Usando todas las fuentes rutinarias públicas de Chile que contienen un código o ítem de autismo (episodios GRD "
         "hospitalarios, egresos DEIS, seis módulos REM, denominadores de aseguramiento, atención primaria y población, "
         "dos encuestas nacionales y registros escolares), con procedencia congelada y controles de reproducción "
         "preespecificados, mostramos que el reconocimiento administrativo del autismo aumentó varias veces entre 2019 y "
         "2025 en los sistemas hospitalario, ambulatorio y educativo; que los aumentos convergen en tiempo y dirección "
         "pese a unidades, coberturas y definiciones distintas; y que la profundidad de codificación, la expansión del "
         "reporte y los cambios de definición explican parte, pero no todo, del cambio registrado. Separamos stocks de "
         "flujos, lugar de atención de residencia y eras de definición entre sí, e informamos el número de "
         "establecimientos reportantes junto a cada conteo."),
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
    doc.p("Se estima que el autismo afecta a cerca del 1 % de la población mundial [@zeidan2022; @santomauro2025], y los "
          "diagnósticos registrados han aumentado de forma pronunciada en las últimas dos décadas en todos los países con "
          "registros poblacionales. Los estudios basados en registros del Reino Unido, Dinamarca y Suecia atribuyen la "
          "mayor parte de ese aumento a cambios en los criterios diagnósticos, a la inclusión de contactos ambulatorios, "
          "a la concienciación y a la capacidad de los servicios más que a un cambio del fenotipo subyacente "
          "[@russell2022; @hansen2015; @lundstrom2015], y la red de vigilancia multifuente de Estados Unidos sigue "
          "documentando una prevalencia identificada creciente con registros enlazados de salud y educación [@shaw2025]. "
          "La Comisión Lancet sobre autismo llamó a contar con sistemas nacionales de datos capaces de monitorear la "
          "identificación, las necesidades y los servicios [@lord2022].")
    doc.p("América Latina aporta poco a esta evidencia. Existen estimaciones poblacionales de prevalencia para pocos "
          "países [@paula2011; @fombonne2016], las encuestas a cuidadores documentan largos retrasos diagnósticos y "
          "barreras de acceso [@montielnava2024], y los registros rutinarios rara vez se han analizado. Chile tiene un "
          "sistema de salud segmentado en el que el asegurador público FONASA cubre a la mayoría de la población y las "
          "aseguradoras privadas ISAPRE a una minoría decreciente [@becerril2011]; cuenta con una estimación urbana de "
          "prevalencia basada en tamizaje y confirmación clínica [@yanez2021], una estimación basada en registros "
          "escolares del autismo y de las necesidades educativas especiales no cubiertas [@romanurrestarazu2025] y guías "
          "clínicas de detección precoz en atención primaria desde 2011 [@minsal2011]. La Ley 21.545, vigente desde marzo "
          "de 2023, estableció derechos de inclusión, atención integral y protección para las personas autistas y creó "
          "deberes de reporte para los sectores de salud y educación [@ley21545; @irarrazaval2023].")
    doc.p("Los sistemas públicos de salud y educación de Chile producen varios conjuntos de datos rutinarios que registran "
          "el autismo: episodios hospitalarios de grupos relacionados por el diagnóstico (GRD), egresos hospitalarios "
          "(DEIS), resúmenes estadísticos mensuales (REM) que cubren detección, consejería, ingresos a programas, "
          "población bajo control y rehabilitación, los registros del Programa de Integración Escolar (PIE) y una "
          "encuesta a cuidadores de cohortes escolares completas. Difieren en unidad de observación, cobertura, "
          "definiciones y reglas de reporte, no están enlazados por persona y fueron diseñados para el pago y la gestión, "
          "no para la vigilancia. Los conteos derivados de ellos miden reconocimiento administrativo, es decir, el "
          "registro de un código de autismo en un contacto con un servicio, no la prevalencia ni la incidencia del "
          "autismo.")
    doc.p("Nos preguntamos cómo cambiaron el reconocimiento administrativo del autismo y la demanda registrada de "
          "servicios entre 2019 y 2025 en los sistemas públicos de salud y educación de Chile, y cuánto del cambio es "
          "robusto a variaciones de cobertura, intensidad de codificación y definiciones. La contribución es "
          "descriptiva: mostrar si sistemas independientes convergen, cuantificar las amenazas a la comparabilidad y "
          "traducir los hallazgos en necesidades de vigilancia y de capacidad asistencial para Chile y la región. La Ley "
          "21.545 se trata como contexto de política que coincide con la recuperación pospandemia, la expansión del "
          "reporte, los cambios de códigos y la codificación más profunda; no se estima ningún efecto de la ley.")

    # ---------------- Métodos ----------------
    doc.h1("Métodos")
    doc.h2("Diseño del estudio y contexto")
    doc.p(f"Este es un estudio descriptivo nacional multifuente de datos recolectados rutinariamente, reportado según la "
          f"declaración STROBE y su extensión RECORD [@vonelm2007; "
          f"@benchimol2015], con resultados desagregados por sexo siguiendo las guías SAGER [@heidari2016]. El contexto "
          f"es Chile (población residente proyectada de {millions(k('ine_pop_total_2019'))} en 2019 y "
          f"{millions(k('ine_pop_total_2025'))} en 2025), cuya red pública comprende los hospitales del Sistema Nacional "
          f"de Servicios de Salud (SNSS) y una atención primaria (APS) mayoritariamente municipal. El período de estudio "
          f"es 2019–2025; las fuentes hospitalarias terminan en 2024. Se analizaron dos variantes completas de "
          f"definición, que se entregan como documentos separados; este documento presenta la {vlabel}. El plan de "
          f"análisis (apéndice) se preespecificó antes de explorar cualquier asociación, y cada desviación, supuesto y "
          f"discrepancia se registra en una bitácora de decisiones.")
    doc.h2("Fuentes de datos y unidades de observación")
    doc.p(f"La {R.tab('T1_sources')} y la {R.mfig('fig1_dataflow')} describen las fuentes, sus unidades de "
          f"observación, cobertura, quiebres de "
          f"definición. La atención hospitalaria se midió con los archivos "
          f"GRD públicos publicados por FONASA, en los que la unidad es un episodio (hospitalización o cirugía mayor "
          f"ambulatoria, CMA; otras modalidades existen solo en 2019) con hasta {n0(k('grd_diagnosis_positions'))} "
          f"diagnósticos codificados, de los hospitales del SNSS que operan el sistema IR-GRD, usado desde 2020 como "
          f"mecanismo de pago [@cid2024]. El panel observado comprendió "
          f"{k.series('grd_hospitals_observed_{y}', YEARS_GRD)} hospitales en 2019–2024; los "
          f"{n0(k('grd_fixed_panel_n'))} hospitales presentes en todos los años forman el panel fijo usado como "
          f"sensibilidad, y los {n0(k('grd_hospitals_ever_observed_n'))} hospitales alguna vez observados nunca se "
          f"tratan como panel fijo. El identificador de persona cambia de formato entre 2020 y 2021, por lo que las "
          f"personas únicas se cuentan solo dentro de cada año. Los egresos hospitalarios DEIS de todos los "
          f"establecimientos (públicos y privados) se usaron como comprobación externa; DEIS publica solo el diagnóstico "
          f"principal (su segundo campo es la causa externa), de modo que la única comparación homóloga es F84 como "
          f"diagnóstico principal en ambas fuentes.")
    doc.p(f"La actividad ambulatoria se midió con los resúmenes estadísticos mensuales REM, cuya unidad es una fila "
          f"establecimiento × mes × código. Los módulos de la Serie A son flujos: A03 (tamizaje del desarrollo en "
          f"atención primaria), A27 (consejería y referencia asistida en el contexto del M-CHAT-R/F, desde 2023, que "
          f"cuenta intervenciones y no personas), A05 (ingresos y egresos de programas de salud mental) y A28 (ingresos a "
          f"rehabilitación, desde 2023). Los módulos de la Serie P son stocks semestrales de personas bajo control: P2 "
          f"(niños, niñas y adolescentes con necesidades especiales de atención en salud, NANEAS, con autismo) y P6 "
          f"(programas de salud mental en atención primaria y especialidad). Diciembre es el corte principal y junio una "
          f"sensibilidad; los semestres nunca se suman. Los {n0(k('rem_pathway_codes_n'))} códigos de la ruta se "
          f"verificaron contra el diccionario oficial de cada año ({R.tab('ST2_rem_code_dictionary')}); las eras de "
          f"definición ({R.tab('S_definition_breaks')}) se presentan en facetas separadas y ninguna serie cruza un "
          f"quiebre. Los establecimientos que reportan cada código y año ({R.tab('ST3_rem_reporting_establishments')}) "
          f"acompañan a cada conteo.")
    doc.p("Los benchmarks poblacionales provinieron de dos encuestas con diseño muestral complejo: la Encuesta Nacional "
          "de Discapacidad y Dependencia 2022 (ENDIDE; autismo reportado para adultos de 18 años o más y, por el cuidador "
          "principal, para niños de 2 a 17 años, con un ítem de confirmación médica para niños) y la Encuesta Nacional de "
          "Calidad de Vida y Salud 2023–24 (ENCAVI; diagnóstico declarado de trastorno del espectro autista a los 15 años "
          "o más). El reconocimiento educativo provino de los informes del Ministerio de Educación sobre el PIE (stock "
          "escolar anual de estudiantes autistas registrados, 2019–2025) y del informe de seguimiento de la Ley 21.545, "
          "y de los microdatos de la Encuesta de Vulnerabilidad Estudiantil de JUNAEB (reporte del cuidador de un "
          "trastorno del espectro autista diagnosticado por médico en las cohortes de educación parvularia, 1.º básico, "
          "5.º básico y 1.º medio; el ítem existe desde 2023 y los factores de expansión desde 2024).")
    doc.p(f"Fuentes oficiales: archivos GRD [@fonasa_grd], egresos DEIS [@deis_egresos], REM series A y P [@minsal_rem], "
          f"actividad hospitalaria REM-20 [@deis_rem20], proyecciones INE y Censo 2024 [@ine2019; @ine_base2024; "
          f"@ine_censo2024], beneficiarios FONASA e inscritos APS [@fonasa_beneficiarios; @fonasa_aps], beneficiarios "
          f"ISAPRE [@supersalud_isapre], ENDIDE [@endide2022], ENCAVI [@encavi2023], informes MINEDUC "
          f"[@mineduc_apuntes60; @mineduc_sinaces2026] y microdatos JUNAEB [@junaeb_eve]; todos son públicos. La "
          f"procedencia se congeló antes del análisis: {n0(k('prov_artefacts_n'))} artefactos fuente "
          f"({n1(k('prov_gb_total'))} GB) se resumieron con SHA-256 y se documentaron con unidad, período, cobertura, "
          f"geografía, columnas, carácter de stock o flujo, quiebres de definición y restricciones de enlace "
          f"({R.tab('ST7_provenance')}); los manifiestos concordaron con los archivos en disco "
          f"({R.tab('ST7b_manifest_checks')}). Los datos fuente nunca se copiaron al repositorio ni se sobrescribieron.",
          opt=True)
    doc.h2("Definiciones de caso y variantes de definición")
    doc.p(f"En el GRD, un episodio con F84 documentado es aquel en que cualquier código CIE-10 de la familia F84 aparece "
          f"en cualquiera de las {n0(k('grd_diagnosis_positions'))} posiciones diagnósticas; F84 principal (primera "
          f"posición) es una serie separada y más específica, y también se informan los episodios que llevan F84 solo en "
          f"posición secundaria. Las dos variantes difieren solo en el síndrome de Rett: la {vlabel} frente a la "
          f"{olabel}; F84.0 (autismo infantil) por sí solo se informa como serie estricta idéntica en ambas variantes "
          f"({R.fig('figS1_grd_variants')}, {R.fig('figS2_grd_subcodes')}, {R.tab('ST10_grd_f84_subcodes')}). En REM, el "
          f"autismo estricto es el código {k('strict_autism_code_a05_entry')} (ingresos) y "
          f"{k('strict_autism_code_a05_exit')} (egresos) en A05 y los códigos {k('strict_autism_code_p6_primary')} "
          f"(atención primaria) y {k('strict_autism_code_p6_specialty')} (especialidad) en P6, todos disponibles desde "
          f"2021 e idénticos en ambas variantes; la familia de trastornos generalizados del desarrollo (TGD) de la "
          f"variante añade el síndrome de Asperger, el trastorno desintegrativo infantil, el TGD no especificado y, solo "
          f"en la variante con Rett, el síndrome de Rett. Los códigos de TGD amplio de 2019–2020, en los que el síndrome "
          f"de Rett es inseparable, se muestran solo como sensibilidad rotulada. P2 (código {k('p2_tea_code')}), A03, A27 "
          f"y A28 no dependen de la variante. A03 tiene cuatro eras no comparables: 2019–2022 (M-CHAT realizado y "
          f"alterado solo entre niños con alteración del lenguaje o del área social en el control de los 18 meses, que no "
          f"es cobertura ni positividad), 2023–2024 (categorías de riesgo del M-CHAT-R/F y referencia), 2024 (niños de "
          f"31 a 59 meses) y el rediseño de 2025.")
    doc.p("En educación, el trastorno del espectro autista (TEA) estricto, el TEA-Asperger y su suma armonizada se "
          "mantienen como series PIE separadas; la discrepancia de 2022 entre los dos informes ministeriales se resuelve "
          "con una regla explícita (Resultados). En JUNAEB, el estimando es la proporción ponderada de estudiantes "
          "encuestados cuyo cuidador reporta un TEA diagnosticado por médico que requiere tratamiento prolongado; los "
          "niveles y años sin ítem o sin ponderador se informan como no estimables, nunca como cero. En las encuestas, "
          "los ítems son autismo reportado (ENDIDE) y diagnóstico declarado (ENCAVI); ninguno equivale a un código "
          "administrativo ni a prevalencia clínica.", opt=True)
    doc.h2("Denominadores y capas de cobertura")
    doc.p("Cuatro capas de denominador responden preguntas distintas y nunca se intercambiaron: proyecciones INE basadas "
          "en el Censo 2017 al 30 de junio (población residente territorial; la base 2024 y el Censo 2024 empadronado solo "
          "como sensibilidades, nunca fusionados dentro de una serie); stocks de beneficiarios FONASA e ISAPRE a "
          "diciembre (cobertura de aseguramiento); inscritos APS validados a diciembre (cobertura operativa por centro, "
          "lugar de atención); y egresos y días-cama REM-20 (actividad y capacidad, nunca una población cubierta). El "
          "estimando GRD primario es la tasa por 100.000 episodios GRD del mismo año, panel y modalidad, que describe la "
          "composición de la actividad hospitalaria; las tasas por 100.000 residentes INE son una lectura complementaria "
          "en la que el numerador se localiza por lugar de atención en la red pública y el denominador por residencia. "
          "Los conteos REM se acompañan del número de establecimientos reportantes, de tasas por establecimiento "
          "reportante y de un panel estable de establecimientos que reportan el código en todos los años de su era. Un "
          "cuadro de equivalencias comunal entre los códigos INE y DEIS usó solo nombres normalizados exactos y alias "
          "explícitos, sin "
          "emparejamiento difuso.")
    doc.h2("Análisis estadístico")
    doc.p(f"Las tasas por 100.000 episodios, egresos o residentes llevan límites exactos de Poisson al 95{NBSP}% con el "
          f"denominador tratado como fijo (para un subconjunto de su propio denominador son marginalmente conservadores "
          f"respecto de los límites binomiales). Las tasas por población se estandarizaron directamente a la población "
          f"estándar mundial de la OMS [@ahmad2001] con intervalos gamma de Fay–Feuer [@fay1997]. Las tendencias anuales "
          f"se resumieron con modelos log-lineales cuasi-Poisson [@wedderburn1974] con el logaritmo del denominador como "
          f"offset (episodios GRD, egresos DEIS, población INE, establecimientos reportantes o total NANEAS según el "
          f"estimando; sin offset para los stocks), de los que el cambio porcentual anual (CPA) es 100·(exp(β) − 1) con "
          f"{CI95} de Wald; la dispersión de Pearson se informa para cada modelo y la autocorrelación residual se "
          f"comprobó con el estadístico de Durbin–Watson, una prueba débil con tres a siete puntos anuales. Los modelos "
          f"hospital-año del GRD añadieron efectos fijos de hospital con tendencia común (errores estándar agrupados por "
          f"hospital como sensibilidad) y, por separado, un intercepto aleatorio Poisson por hospital (aproximación de "
          f"Laplace); los efectos de hospital se expresan como razones de tasas frente a la media geométrica de los "
          f"hospitales. Las covariables preespecificadas fueron la profundidad diagnóstica media (número de diagnósticos "
          f"codificados por episodio) y un indicador de la disrupción del reporte de 2020–2021, que describe el período "
          f"pandémico y no tiene significado causal. Los CPA ajustados por edad provinieron de celdas grupo de edad × año "
          f"con efectos fijos de edad y offset poblacional, en total y por sexo.")
    doc.p(f"Las proporciones de las encuestas se estimaron con los ponderadores, estratos y unidades primarias de muestreo "
          f"publicados de cada encuesta como estimadores de razón por dominio que conservan todas las unidades del "
          f"diseño, con errores estándar linealizados de Taylor [@wolter2007], {CI95} logit sobre t con grados de "
          f"libertad iguales a unidades primarias de muestreo menos estratos, efectos de diseño y errores estándar "
          f"relativos; los dominios con menos de 30 casos no ponderados se marcan como imprecisos y aquellos con error "
          f"estándar relativo superior al 30{NBSP}% se suprimen. Las proporciones JUNAEB usaron el factor de expansión "
          f"anual; como los archivos desidentificados no traen identificador de escuela, sus errores estándar ignoran el "
          f"conglomerado escolar y son probablemente demasiado estrechos. La convergencia entre sistemas se describe con "
          f"índices (primer año común 2021 = 100) que nunca se leen como niveles comparables. Los análisis se ejecutaron "
          f"en Python 3.14 con pandas, NumPy, SciPy y statsmodels; el pipeline, las tablas tidy y una tabla plana de cada "
          f"cantidad citada ({n0(k('models_n_variant'))} especificaciones de modelo convergidas por variante) se "
          f"comparten (Declaración de disponibilidad de datos). Las filas REM en cero, vacías y ausentes son estados "
          f"distintos (una fila ausente es «no reportado» y nunca se imputa), 2020 nunca se interpoló, las celdas con "
          f"menos de cinco eventos se suprimen en las tablas territoriales y no se ajustó ningún modelo causal de la Ley "
          f"21.545.")
    doc.p(f"Las sensibilidades preespecificadas fueron: panel hospitalario fijo frente a observado; toda modalidad frente "
          f"a hospitalización estricta con CMA informada por separado; cualquier posición frente a F84 principal; ajuste "
          f"por profundidad diagnóstica y estratificación por banda de profundidad; el indicador de disrupción 2020–2021 "
          f"y una ventana 2021–2024; la unidad de análisis (nacional, hospital-año, edad × año); las dos variantes F84 y "
          f"la serie solo F84.0; stocks de diciembre frente a junio; todos los establecimientos reportantes frente al "
          f"panel estable y tasas por establecimiento reportante; INE base 2017 frente a base 2024 y Censo 2024; y las "
          f"tres series PIE. Las filas REM en cero, vacías y ausentes son estados distintos: un establecimiento con fila "
          f"cuenta como reportante aunque el valor sea cero o vacío, y una fila ausente es «no reportado» y nunca se "
          f"imputa; 2020 nunca se interpoló. Las celdas con menos de cinco eventos se suprimen en las tablas "
          f"territoriales y los dominios de encuesta con menos de 30 casos se marcan. No se ajustó ningún modelo de "
          f"series de tiempo interrumpidas ni otro modelo causal de la Ley 21.545, porque la ley coincide con la "
          f"recuperación pospandemia, la expansión del reporte, los cambios de códigos y la codificación más profunda, y "
          f"ninguna especificación puede identificar su efecto.", opt=True)
    doc.h2("Controles de reproducibilidad")
    # Mismo rótulo de ámbito que el inglés: forma breve CR.label() en el texto núcleo, frase completa CR.phrase()
    # en el suplemento. Las dos versiones llevan exactamente las mismas cifras.
    doc.p(f"Antes de modelar, {n0(k('controls_families_prespecified_n'))} familias de control preespecificadas (totales "
          f"hospitalarios y REM, denominadores, conteos de casos de las encuestas y stocks educativos del protocolo) se "
          f"reprodujeron a partir de los archivos fuente; las coincidencias exigieron igualdad exacta para los conteos y "
          f"una diferencia relativa de 0,5{NBSP}% o menos para medias y proporciones, y cada diferencia se explicó antes "
          f"de usar el valor. Las {n0(k('t8_rows'))} filas indicador-año resultantes {CR.label(CR.ANALYSIS_PLAN, LANG)} "
          f"se resumen por familia en los Resultados, incluidas filas de comprobación rotuladas "
          # La cita debe resolver al ÁMBITO del plan de análisis: la tabla de las 205 filas indicador-año, no
          # la Figura S15 ni su Tabla S50, que cuentan los controles numéricos POR MÓDULO del pipeline
          # completo y nunca se suman con estas filas. El resumen por familia se nombra con palabras («en los
          # Resultados») y no con una cita: su tabla principal se cita por primera vez en los Resultados, y el
          # orden de primera cita de las tablas principales tiene que ser 1, 2, 3, …
          f"({R.tab('T8_controls')}).")
    doc.h2("Papel de la fuente de financiamiento")
    doc.p("No hubo fuente de financiamiento para este estudio. El autor tuvo acceso completo a todos los datos y la "
          "responsabilidad final de la decisión de enviar el manuscrito a publicación.")
    doc.h2("Ética")
    doc.p("El estudio usó únicamente datos administrativos públicos, desidentificados, agregados o seudonimizados, y "
          "microdatos públicos de encuestas; no se contactó a ninguna persona ni se intentó enlace alguno a nivel de "
          "persona. Según la normativa chilena, estos análisis secundarios de datos públicos no requieren aprobación de "
          "un comité de ética; el equipo autor debe confirmar esta afirmación, u obtener una exención, antes del envío.")
    doc.h2("Uso de inteligencia artificial en el proceso de investigación")
    doc.p("Se usaron asistentes de programación basados en grandes modelos de lenguaje (Claude Code, Anthropic, modelo "
          "Claude Fable 5.1; OpenAI Codex en Visual Studio Code) bajo la dirección del autor para escribir y depurar el "
          "pipeline de análisis y borradores de este texto; el autor especificó cada análisis, ejecutó y revisó todo el "
          "código y verificó cada cifra informada contra los archivos de salida (véase la declaración sobre IA).")

    # ---------------- Resultados ----------------
    doc.h1("Resultados")
    doc.h2("Fuentes y cobertura")
    doc.p(f"La {R.mfig('fig1_sources_coverage')} y la {R.tab('T1_sources')} resumen las fuentes, y la "
          f"{R.mfig('fig1_dataflow')} responde, fuente por fuente, qué es una fila (un registro, que "
          f"puede repetir a una persona, o una persona), cuántas filas entran y superan la selección de autismo, y "
          f"qué se cuenta contra qué denominador, sin enlace individual entre sistemas. Los "
          f"archivos GRD contenían {n0(k('grd_records_total_2019'))} "
          f"episodios en 2019 y {n0(k('grd_records_total_2024'))} en 2024 de "
          f"{k.series('grd_hospitals_observed_{y}', YEARS_GRD)} hospitales; el panel fijo de "
          f"{n0(k('grd_fixed_panel_n'))} hospitales concentró el {ppct(k('grd_records_fixed65_share_2024'))} de los "
          f"episodios de 2024, tras la incorporación de {nw(k('grd_hospitals_added_2023_n'))} hospitales en 2023 y "
          f"{nw(k('grd_hospitals_added_2024_only_n'))} más en 2024 ({R.tab('ST1_grd_hospital_panel')}). La profundidad "
          f"diagnóstica media de todos los episodios subió de {n2(k('grd_coding_depth_all_mean_2019'))} a "
          f"{n2(k('grd_coding_depth_all_mean_2024'))} diagnósticos por episodio y, entre los episodios con F84, de "
          f"{n2(k('grd_coding_depth_f84_mean_2019'))} a {n2(k('grd_coding_depth_f84_mean_2024'))}. En REM, los "
          f"establecimientos que reportaron ingresos por autismo estricto fueron "
          f"{k.series('a05_autism_entries_estab_{y}', YEARS_A05)} en 2021–2025 (una caída de "
          f"{n0(abs(k('a05_autism_entries_estab_change_2025_2024')))} en 2025, cuando el archivo puede estar aún "
          f"incompleto) y los que reportaron el stock P2 de autismo en diciembre fueron "
          f"{k.series('p2_tea_dec_estab_{y}', YEARS_REM)} en 2019–2025. El corte P2 de junio de 2020 cayó al "
          f"{ppct(k('p2_jun_dec_ratio_2020'))} del stock de diciembre porque pocos establecimientos reportaron durante la "
          f"pandemia ({R.fig('figS5_rem_june_december')}). La población empadronada en el Censo 2024 fue el "
          f"{ppct(k('ine_ratio_censo2024_base2017_2024'))} de la proyección base 2017 usada como denominador; FONASA "
          f"cubría al {pct(k('share_fonasa_ine_pct_2019'))} de los residentes en 2019 y al "
          f"{pct(k('share_fonasa_ine_pct_2025'))} en 2025, mientras ISAPRE cayó del {pct(k('share_isapre_ine_pct_2019'))} "
          f"al {pct(k('share_isapre_ine_pct_2025'))}, y los paneles continuos de APS y REM-20 retuvieron al menos el "
          f"{pct(min(k('aps_panel_retention_pct_2025'), k('rem20_panel_retention_pct_2025')))} de sus totales de 2025.")

    doc.add("_figure", "fig1_dataflow")
    doc.add("_figure", "fig1_sources_coverage")

    doc.h2("Núcleo hospitalario: episodios GRD con F84 documentado")
    doc.p(f"Los episodios con F84 documentado en cualquier posición fueron {k.series('grd_f84_any_n_{y}', YEARS_GRD)} en "
          f"2019–2024, es decir, {k.rate('grd_f84_any', 2019)} por 100.000 episodios GRD en 2019 y "
          f"{k.rate('grd_f84_any', 2024)} en 2024, una razón de {n2(k('grd_f84_any_rate_ratio_2024_2019'))} "
          f"({R.mtab('T2_grd_core')}, {R.mfig('fig2_grd_core')}). En el panel fijo de {n0(k('grd_fixed_panel_n'))} hospitales el conteo de 2024 fue "
          f"{n0(k('grd_f84_any_fixed65_n_2024'))} ({n1(k('grd_f84_any_fixed65_rate_2024'))} por 100.000), de modo que "
          f"los hospitales incorporados en 2023–2024 contribuyeron poco a la tasa. Los episodios de hospitalización "
          f"estricta con F84 fueron {n0(k('grd_f84_any_hosp_n_2024'))} en 2024 "
          f"({n0(k('grd_f84_any_hosp_fixed65_n_2024'))} en el panel fijo), y los episodios de CMA con F84 aumentaron de "
          f"{n0(k('grd_f84_any_cma_n_2019'))} a {n0(k('grd_f84_any_cma_n_2024'))}. Los episodios con F84 "
          f"principal fueron menos y crecieron más lentamente: {k.series('grd_f84_principal_n_{y}', YEARS_GRD)}, "
          f"de {k.rate('grd_f84_principal', 2019)} a {k.rate('grd_f84_principal', 2024)} por 100.000 episodios; en 2024, "
          f"el {pct(k('grd_f84_secondary_only_share_2024_pct'))} de los episodios con F84 lo llevaba solo como "
          f"diagnóstico secundario. La serie solo F84.0, idéntica en ambas variantes, alcanzó "
          f"{n0(k('grd_f840_strict_any_n_2024'))} episodios en 2024; la variante alternativa, {olabel}, contó "
          f"{n0(k('grd_f84_any_n_other_variant_2024'))} episodios con F84 en cualquier posición en 2024, una diferencia "
          f"de {n0(k('grd_f84_any_n_rett_only_difference_2024'))} episodios con F84.2 y ningún otro código F84.")
    doc.p(f"El aumento no fue solo un subproducto de la codificación más profunda: dentro de cada banda de profundidad "
          f"diagnóstica la tasa de F84 aumentó entre 2019 y 2024 por un factor de "
          f"{n1(k('grd_depth_bin_3_rate_ratio_2024_2019'))} (tres diagnósticos), "
          f"{n1(k('grd_depth_bin_4_rate_ratio_2024_2019'))} (cuatro), {n1(k('grd_depth_bin_5_rate_ratio_2024_2019'))} "
          f"(cinco), {n1(k('grd_depth_bin_6_7_rate_ratio_2024_2019'))} (seis a siete), "
          f"{n1(k('grd_depth_bin_8_10_rate_ratio_2024_2019'))} (ocho a diez) y "
          f"{n1(k('grd_depth_bin_11plus_rate_ratio_2024_2019'))} (11 o más), mientras la proporción de episodios con "
          f"ocho o más diagnósticos subió del {ppct(k('grd_depth_share_records_8plus_2019'))} al "
          f"{ppct(k('grd_depth_share_records_8plus_2024'))} ({R.mfigp('fig2_grd_core', 'c')}). Las personas únicas dentro de cada año "
          f"(identificadores válidos solo dentro del año) fueron {k.series('grd_f84_any_persons_{y}', YEARS_GRD)}, con "
          f"{n2(k('grd_episodes_per_person_any_2024'))} episodios por persona en 2024 "
          f"({R.tab('ST8_grd_identifier_audit')}).")
    doc.p(f"En 2024 la tasa más alta por 100.000 episodios se observó en el grupo de "
          f"{str(k('grd_f84_any_peak_age_group_2024')).replace('-', '–')} años, el "
          f"{ppct(k('grd_f84_any_share_age_0_9_2024'))} de los episodios con F84 correspondió a niños de 0 a 9 años y el "
          f"{ppct(k('grd_f84_any_share_age_20plus_2024'))} a personas de 20 años o más; la razón hombres:mujeres de los "
          f"episodios cayó de {n2(k('grd_f84_any_mf_ratio_n_2019'))} en 2019 a {n2(k('grd_f84_any_mf_ratio_n_2024'))} en "
          f"2024 ({R.tab('ST9_grd_age_sex')}). Por 100.000 residentes INE, los episodios con F84 aumentaron de "
          f"{n1(k('grd_pop_any_total_crude_2019'))} (tasa bruta) y {k.est_ci_y('grd_pop_any_total_asr', 2019)} "
          f"(estandarizada OMS) en 2019 a {n1(k('grd_pop_any_total_crude_2024'))} y "
          f"{k.est_ci_y('grd_pop_any_total_asr', 2024)} en 2024; las tasas estandarizadas de 2024 fueron "
          f"{n1(k('grd_pop_any_male_asr_2024'))} en hombres y {n1(k('grd_pop_any_female_asr_2024'))} en mujeres (razón "
          f"{n2(k('grd_pop_any_asr_mf_ratio_2024'))}; {R.tab('S_grd_population_rates')}).")
    doc.p(f"Los hospitales fueron heterogéneos: en 2024 la tasa varió de {n1(k('grd_hosp2024_rate_min'))} a "
          f"{n0(k('grd_hosp2024_rate_max'))} por 100.000 episodios (razón {n1(k('grd_hosp2024_rate_ratio_max_min'))}; "
          f"mediana {n1(k('grd_hosp2024_rate_median'))}, rango intercuartílico {n1(k('grd_hosp2024_rate_q1'))}–"
          f"{n1(k('grd_hosp2024_rate_q3'))}), con los valores más altos en hospitales pediátricos como el "
          f"{k('grd_hosp2024_top1_name')} ({n0(k('grd_hosp2024_top1_n_f84'))} de {n0(k('grd_hosp2024_top1_episodes'))} "
          f"episodios). En el modelo de efectos fijos de hospital, {n0(k('grd_hosp_rr_fixed_effects_none_n_above1'))} "
          f"hospitales tuvieron una razón de tasas superior a uno y {n0(k('grd_hosp_rr_fixed_effects_none_n_below1'))} "
          f"inferior a uno, y la desviación estándar del intercepto aleatorio fue {n2(k('apc_grd_hospital_ri_re_sd'))} "
          f"en escala logarítmica ({R.fig('figS3_grd_hospital_effects')}, {R.tab('S_hospital_rates_2024')}); los mapas "
          f"regionales por residencia y por lugar de atención son ecológicos y no corrigen las derivaciones "
          f"interregionales ({R.fig('figS9_regional_maps')}, {R.tab('S9_regional_rates')}).", opt=True)
    doc.p(f"Los egresos DEIS con F84 como diagnóstico principal en todos los establecimientos aumentaron de "
          f"{n0(k('deis_f84_principal_n_2019'))} ({k.rate('deis_f84_principal', 2019)} por 100.000 egresos) en 2019 a "
          f"{n0(k('deis_f84_principal_n_2024'))} ({k.rate('deis_f84_principal', 2024)}) en 2024, el "
          f"{ppct(k('deis_f84_principal_snss_share_2024'))} de ellos en establecimientos del SNSS; la razón entre los "
          f"conteos DEIS y GRD de F84 principal fue {n2(k('deis_vs_grd_ratio_f84_principal_2024'))} en 2024, una "
          f"comparación de cobertura entre registros no enlazados y no una probabilidad ("
          f"{R.tab('ST11a_deis_annual')}, {R.tab('ST11b_deis_vs_grd')}, {R.fig('figS14_deis_sex_age')}, "
          f"{R.tab('S14_deis_sex_age')}).", opt=True)
    doc.add("_table", "T2_grd_core")
    doc.add("_figure", "fig2_grd_core")

    doc.h2("Ruta administrativa agregada en atención primaria y especialidad")
    doc.p(f"La {R.mtab('T3_rem_pathway')} y la {R.mfig('fig3_rem_pathway')} presentan los módulos REM por era con sus "
          f"establecimientos reportantes; los paneles "
          f"son indicadores agregados de sistemas no enlazados, de modo que ningún cociente entre ellos representa una "
          f"probabilidad individual. Los códigos de detección y referencia en atención primaria se redefinieron en 2023, "
          f"2024 y 2025, por lo que A03 y A27 se muestran por era sin serie continua: la clasificación M-CHAT-R/F de "
          f"2023–2024 registró {n0(k('a03_2023_high_2023'))} y {n0(k('a03_2023_high_2024'))} niños en alto riesgo, y las "
          f"referencias asistidas (A27) fueron {k.series('a27_assisted_referral_{y}', YEARS_A27)} intervenciones en "
          f"2023–2025.")
    doc.p(f"En la era A03 legada, el tamizaje M-CHAT entre niños con alteración del lenguaje o del área social se registró "
          f"{k.series('a03_legacy_mchat_done_{y}', [2019, 2020, 2021, 2022])} veces en 2019–2022 y resultó alterado en "
          f"{k.series('a03_legacy_mchat_altered_{y}', [2019, 2020, 2021, 2022])} de ellas; en la era 2023–2024, la "
          f"clasificación de riesgo M-CHAT-R/F registró {n0(k('a03_2023_risk_total_2023'))} y "
          f"{n0(k('a03_2023_risk_total_2024'))} resultados ({n0(k('a03_2023_high_2023'))} y "
          f"{n0(k('a03_2023_high_2024'))} en alto riesgo), {n0(k('a03_2024_31_59_evaluated_2024'))} niños de 31 a 59 "
          f"meses fueron evaluados en 2024 y el rediseño de 2025 registró {n0(k('a03_2025_risk_total_2025'))} resultados "
          f"de riesgo. Las intervenciones de consejería A27 fueron {k.series('a27_counselling_{y}', YEARS_A27)} y las "
          f"referencias asistidas {k.series('a27_assisted_referral_{y}', YEARS_A27)} en 2023–2025.", opt=True)
    doc.p(f"Los ingresos por autismo estricto a programas de salud mental (A05) aumentaron de "
          f"{n0(k('a05_autism_entries_2021'))} en 2021 a {n0(k('a05_autism_entries_2025'))} en 2025 "
          f"({n0(k('a05_autism_entries_total_2021_2025'))} ingresos en cinco años; "
          f"{k.series('a05_autism_entries_{y}', YEARS_A05)}), los egresos de programa de {n0(k('a05_autism_exits_2021'))} "
          f"a {n0(k('a05_autism_exits_2025'))}, y los ingresos de la familia TGD de la variante de "
          f"{n0(k('a05_family_entries_2021'))} a {n0(k('a05_family_entries_2025'))}. En el panel estable de "
          f"{n0(k('a05_autism_entries_stable_panel_n'))} establecimientos que reportaron el código todos los años, los "
          f"ingresos por autismo estricto aumentaron de {n0(k('a05_autism_entries_stable_total_2021'))} a "
          f"{n0(k('a05_autism_entries_stable_total_2025'))} ({R.fig('figS6_rem_stable_panel')}, "
          f"{R.tab('S6_stable_panel')}). Por 100.000 residentes, los ingresos por autismo estricto aumentaron de "
          f"{n1(k('a05_autism_pop_total_crude_2021'))} (tasa bruta) y {k.est_ci_y('a05_autism_pop_total_asr', 2021)} "
          f"(estandarizada OMS) en 2021 a {n1(k('a05_autism_pop_total_crude_2025'))} y "
          f"{k.est_ci_y('a05_autism_pop_total_asr', 2025)} en 2025, con una razón hombres:mujeres de tasas "
          f"estandarizadas de {n2(k('a05_autism_pop_asr_mf_ratio_2025'))} en 2025 y el "
          f"{ppct(k('a05_autism_entries_share_age_0_9_2025'))} de los ingresos en niños de 0 a 9 años "
          f"({R.fig('figS7_rem_education_models')}, {R.fig('figS8_a05_age_sex')}, "
          f"{R.tab('S_a05_standardised_rates')}, {R.tab('ST13_a05_age_sex')}).")
    doc.p(f"El stock de diciembre de niños, niñas y adolescentes con autismo bajo control en el programa NANEAS (P2) "
          f"aumentó de {n0(k('p2_tea_dec_2019'))} en 2019 a {n0(k('p2_tea_dec_2025'))} en 2025 "
          f"({k.series('p2_tea_dec_{y}', YEARS_REM)}; razón {n1(k('p2_tea_dec_ratio_2025_2019'))}), mientras los "
          f"establecimientos reportantes aumentaron de {n0(k('p2_tea_dec_estab_2019'))} a "
          f"{n0(k('p2_tea_dec_estab_2025'))}; el stock de junio de 2025 fue {n0(k('p2_tea_jun_2025'))}. La población "
          f"NANEAS total, reportada desde diciembre de 2023, fue {k.series('p2_naneas_dec_{y}', [2023, 2024, 2025])}, "
          f"de modo que el autismo representó el {pct(k('p2_tea_share_of_naneas_dec_pct_2023'))} de los NANEAS bajo "
          f"control en 2023 y el {pct(k('p2_tea_share_of_naneas_dec_pct_2025'))} en 2025 "
          f"({R.tab('ST14_p2_p6_june_december')}, {R.tab('S5_june_december')}). En P6, el stock de diciembre bajo "
          f"control por autismo estricto aumentó de {n0(k('p6_primary_autism_dec_2021'))} a "
          f"{n0(k('p6_primary_autism_dec_2025'))} en atención primaria y de {n0(k('p6_specialty_autism_dec_2021'))} a "
          f"{n0(k('p6_specialty_autism_dec_2025'))} en especialidad (2021–2025); los stocks de TGD amplio de 2019–2020 "
          f"({n0(k('p6_primary_broad_dec_2019'))} y {n0(k('p6_primary_broad_dec_2020'))} en atención primaria; "
          f"{n0(k('p6_specialty_broad_dec_2019'))} y {n0(k('p6_specialty_broad_dec_2020'))} en especialidad) pertenecen "
          f"a otra definición y no se unen a ellos. Los ingresos a rehabilitación por autismo (A28), reportados desde "
          f"2023, fueron {k.series('a28_primary_{y}', YEARS_A27)} en el nivel primario (un aumento de "
          f"{n1(k('a28_primary_ratio_2025_2023'))} veces en dos años) y {k.series('a28_hospital_{y}', YEARS_A27)} en el "
          f"nivel hospitalario. El reporte mensual muestra que la caída de abril a septiembre de 2020 fue de "
          f"establecimientos reportantes y no de personas ({R.fig('figS13_rem_seasonality')}, "
          f"{R.tab('S13_rem_seasonality')}); los valores graficados en la {R.mfig('fig3_rem_pathway')} se listan en "
          f"{R.tab('F3_rem_pathway_data')}.")
    doc.add("_table", "T3_rem_pathway")
    doc.add("_figure", "fig3_rem_pathway")

    doc.h2("Capas de cobertura y denominadores")
    doc.p(f"La población residente INE creció de {millions(k('ine_pop_total_2019'), 2)} a "
          f"{millions(k('ine_pop_total_2025'), 2)}; la población empadronada del Censo 2024 "
          f"({n0(k('censo2024_enumerated'))}) fue el {ppct(k('ine_ratio_censo2024_base2017_2024'))} de la proyección base "
          f"2017 para 2024, de modo que cualquier tasa poblacional sería cerca de un "
          f"{pct(100 * (1 / k('ine_ratio_censo2024_base2017_2024') - 1), 1)} más alta con el denominador censal "
          f"({R.fig('figS10_denominators')}, {R.tab('S10_denominator_sensitivity')}). Los beneficiarios FONASA "
          f"aumentaron de {millions(k('fonasa_beneficiaries_2019'), 2)} ({pct(k('share_fonasa_ine_pct_2019'))} de la "
          f"población INE) a {millions(k('fonasa_beneficiaries_2025'), 2)} ({pct(k('share_fonasa_ine_pct_2025'))}), "
          f"mientras los beneficiarios ISAPRE cayeron de {millions(k('isapre_beneficiaries_2019'), 2)} "
          f"({pct(k('share_isapre_ine_pct_2019'))}) a {millions(k('isapre_beneficiaries_2025'), 2)} "
          f"({pct(k('share_isapre_ine_pct_2025'))}); su suma alcanzó el {pct(k('share_fonasa_plus_isapre_ine_pct_2025'))} "
          f"de la proyección en 2025, cifra que no es una tasa de aseguramiento porque mezcla stocks de diciembre con "
          f"una proyección a junio y omite otros regímenes ({R.mtab('T4_denominators_coverage')}, {R.fig('figS11_coverage_age_sex')}). Los inscritos "
          f"APS crecieron de {millions(k('aps_enrolled_2019'), 2)} en {n0(k('aps_centres_2019'))} centros a "
          f"{millions(k('aps_enrolled_2025'), 2)} en {n0(k('aps_centres_2025'))} centros, y el panel continuo de "
          f"{n0(k('aps_panel_n'))} centros retuvo entre el {pct(k('aps_panel_retention_pct_2019'))} y el "
          f"{pct(k('aps_panel_retention_pct_2025'))} de los inscritos; el panel REM-20 de {n0(k('rem20_panel_n'))} "
          f"establecimientos con 12 meses reportados todos los años retuvo entre el "
          f"{pct(k('rem20_panel_retention_pct_2019'))} y el {pct(k('rem20_panel_retention_pct_2025'))} de los egresos. "
          f"Los {n0(k('t8_differs'))} controles de reproducción que difieren se refieren a la definición de panel de la "
          f"hospitalización estricta, a identificadores de persona de relleno y a filas fuente repetidas, y se listan junto "
          f"con los controles de reproducción más abajo.", opt=True)
    doc.add("_table", "T4_denominators_coverage")

    doc.h2("Benchmarks poblacionales")
    doc.p(f"Con el diseño complejo, ENDIDE 2022 estimó autismo reportado en el {k.svy('svy_endide_adults_reported_total')} "
          f"de los adultos de 18 años o más (n = {n0(k('svy_endide_adults_reported_total_n'))}; "
          f"{n0(k('svy_endide_adults_reported_total_cases'))} casos; cerca de "
          f"{n0(k('svy_endide_adults_reported_total_weighted_total'))} personas) y en el "
          f"{k.svy('svy_endide_children_reported_total')} de los niños, niñas y adolescentes de 2 a 17 años (n = "
          f"{n0(k('svy_endide_children_reported_total_n'))}; {n0(k('svy_endide_children_reported_total_cases'))} casos; "
          f"cerca de {n0(k('svy_endide_children_reported_total_weighted_total'))} personas), de los cuales el "
          f"{k.svy('svy_endide_children_confirmed_among_reported_total', 1)} tenía diagnóstico confirmado por médico, lo "
          f"que da un {k.svy('svy_endide_children_reported_confirmed_total')} de todos los niños con autismo reportado y "
          f"confirmado. El autismo reportado fue del {pct(k('svy_endide_children_reported_male_pct'), 2)} en niños y "
          f"del {pct(k('svy_endide_children_reported_female_pct'), 2)} en niñas. ENCAVI 2023–24 estimó un diagnóstico "
          f"declarado de trastorno del espectro autista en el {k.svy('svy_encavi_15plus_diagnosed_total')} de las "
          f"personas de 15 años o más (n = {n0(k('svy_encavi_15plus_diagnosed_total_n'))}; "
          f"{n0(k('svy_encavi_15plus_diagnosed_total_cases'))} casos; efecto de diseño "
          f"{n2(k('svy_encavi_15plus_diagnosed_total_deff'))}). La mayoría de los dominios por sexo y edad son "
          f"imprecisos y se informan solo como órdenes de magnitud ({R.mtab('T5_survey_benchmarks')}, "
          f"{R.mfigp('fig4_triangulation', 'c')}, {R.tab('ST5_survey_items')}). "
          f"Estos benchmarks son autorreportados o reportados por el cuidador y no constituyen una validación de los "
          f"códigos administrativos.")
    doc.add("_table", "T5_survey_benchmarks")

    doc.h2("Triangulación educativa")
    doc.p(f"Los estudiantes autistas registrados en el PIE aumentaron de {n0(k('pie_tea_strict_2019'))} (TEA estricto) y "
          f"{n0(k('pie_tea_asperger_2019'))} (TEA-Asperger) en 2019 a {n0(k('pie_tea_strict_2023'))} y "
          f"{n0(k('pie_tea_asperger_2023'))} en 2023, cuando el TEA estricto representó el "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2023'))} de todos los estudiantes PIE frente al "
          f"{pct(k('pie_tea_strict_share_of_pie_pct_2019'))} en 2019; la serie armonizada TEA + Asperger fue "
          f"{k.series('pie_harmonised_{y}', YEARS_REM)} en 2019–2025 (razón {n2(k('pie_harmonised_ratio_2025_2019'))}), "
          f"con 2024–2025 provenientes del informe de seguimiento de la Ley 21.545. Para 2022 ese informe imprime "
          f"{n0(k('pie_2022_sinaces_printed'))}, mientras que su total de estudiantes autistas menos las escuelas "
          f"especiales ({n0(k('sinaces_total_autistic_students_2022'))} − {n0(k('special_schools_autism_2022'))} = "
          f"{n0(k('pie_2022_sinaces_total_minus_special'))}) coincide con la serie ministerial; la diferencia de "
          f"{nw(k('pie_2022_discrepancy_cases'))} estudiantes se resolvió a favor de la fuente desagregada. Los "
          f"estudiantes autistas en escuelas especiales fueron "
          f"{k.series('special_schools_autism_{y}', [2022, 2023, 2024, 2025])} y el total de estudiantes autistas "
          f"registrados {n0(k('sinaces_total_autistic_students_2022'))} en 2022 y "
          f"{n0(k('sinaces_total_autistic_students_2025'))} en 2025 ({R.mtab('T6_education')}, "
          f"{R.mfigp('fig4_triangulation', 'a')}).")
    doc.p(f"En la encuesta a cuidadores de cohortes completas de JUNAEB, el porcentaje ponderado de estudiantes con "
          f"diagnóstico médico reportado de TEA fue del {pct(k('junaeb_parvularia_all_pct_weighted_2024'), 2)} en "
          f"educación parvularia, del {pct(k('junaeb_basico1_all_pct_weighted_2024'), 2)} en 1.º básico y del "
          f"{pct(k('junaeb_basico5_all_pct_weighted_2024'), 2)} en 5.º básico en 2024 (1.º medio no estimable porque el "
          f"ítem está vacío en el archivo publicado), y del {pct(k('junaeb_parvularia_all_pct_weighted_2025'), 2)}, "
          f"{pct(k('junaeb_basico1_all_pct_weighted_2025'), 2)}, {pct(k('junaeb_basico5_all_pct_weighted_2025'), 2)} y "
          f"{pct(k('junaeb_medio1_all_pct_weighted_2025'), 2)} en 2025, con razones hombres:mujeres entre "
          f"{n1(k('junaeb_medio1_mf_ratio_2025'))} (1.º medio) y {n1(k('junaeb_basico1_mf_ratio_2025'))} (1.º básico) "
          f"({R.fig('figS12_junaeb_sex_level')}, {R.tab('S12_junaeb_sex_level')}, {R.tab('ST6_junaeb_items')}). Los "
          f"cuestionarios de 2019–2022 no tenían ítem de TEA y 2023 no tiene ponderador publicado, por lo que no puede "
          f"estimarse ninguna tendencia JUNAEB anterior a 2024; estas proporciones describen cohortes escolares "
          f"seleccionadas y el reporte de los cuidadores, no prevalencia nacional.")
    doc.add("_table", "T6_education")
    doc.add("_figure", "fig4_triangulation")

    doc.h2("Convergencia entre sistemas y sensibilidad de las tendencias")
    doc.p(f"Con índice 2021 = 100, la tasa GRD de episodios con F84 se situó en {n0(k('conv_grd_any_rate_index2021_2024'))} "
          f"en 2024, la tasa DEIS de F84 principal en {n0(k('conv_deis_principal_rate_index2021_2024'))}, los ingresos "
          f"A05 por autismo estricto en {n0(k('conv_a05_strict_entries_index2021_2025'))} en 2025, el stock P2 de "
          f"diciembre en {n0(k('conv_p2_december_stock_index2021_2025'))}, el stock P6 de atención primaria en "
          f"{n0(k('conv_p6_primary_strict_stock_index2021_2025'))} y el PIE armonizado en "
          f"{n0(k('conv_pie_harmonised_index2021_2025'))} ({R.mfigp('fig4_triangulation', 'd-e')}, {R.tab('S_convergence_index')}, "
          f"{R.tab('F4_triangulation_series')}); los índices comparten dirección y tiempo, con los aumentos más "
          f"pronunciados en 2022–2024, pero no unidades, denominadores ni definiciones.")
    doc.p(f"La {R.mtab('T7_models')} presenta los modelos preespecificados. El CPA de los episodios GRD con F84 por 100.000 episodios "
          f"fue {k.apc('apc_grd_any_obs')} en el panel observado (dispersión de Pearson "
          f"{n1(k('apc_grd_any_obs_disp'))}) y {k.apc('apc_grd_any_fixed65')} en el panel fijo; el ajuste por "
          f"profundidad diagnóstica media lo elevó a {k.apc('apc_grd_any_obs_depth')}, el indicador de disrupción "
          f"2020–2021 lo redujo a {k.apc('apc_grd_any_obs_disruption')}, la ventana 2021–2024 dio "
          f"{k.apc('apc_grd_any_obs_2021_2024')} y la hospitalización estricta {k.apc('apc_grd_any_hosp')}; en las "
          f"{n0(k('apc_grd_any_sensitivity_n_specs'))} especificaciones el CPA varió entre "
          f"{n1(k('apc_grd_any_sensitivity_min'))}{NBSP}% y {n1(k('apc_grd_any_sensitivity_max'))}{NBSP}%. F84 principal "
          f"creció al {n1(k('apc_grd_principal_obs'))}{NBSP}% ({CI95} "
          f"{ci(k('apc_grd_principal_obs_lo'), k('apc_grd_principal_obs_hi'))}; "
          f"{n1(k('apc_grd_principal_sensitivity_min'))}–{n1(k('apc_grd_principal_sensitivity_max'))}{NBSP}% entre "
          f"especificaciones). Los modelos hospital-año con efectos fijos de hospital dieron "
          f"{n1(k('apc_grd_hospital_fe'))}{NBSP}% ({CI95} agrupado por hospital "
          f"{ci(k('apc_grd_hospital_fe_cluster_lo'), k('apc_grd_hospital_fe_cluster_hi'))}) y el modelo de intercepto "
          f"aleatorio {n1(k('apc_grd_hospital_ri'))}{NBSP}%; cada diagnóstico codificado adicional por episodio se asoció "
          f"con una razón de tasas de {n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} dentro de los "
          f"hospitales. Por 100.000 residentes el CPA ajustado por edad fue {k.apc('apc_grd_pop_any_total_ageadj')}, "
          f"mayor en mujeres ({n1(k('apc_grd_pop_any_female_ageadj'))}{NBSP}%) que en hombres "
          f"({n1(k('apc_grd_pop_any_male_ageadj'))}{NBSP}%). Los egresos DEIS con F84 principal crecieron al "
          f"{n1(k('apc_deis_principal'))}{NBSP}% ({CI95} {ci(k('apc_deis_principal_lo'), k('apc_deis_principal_hi'))}; "
          f"{R.mfigp('fig4_triangulation', 'f')}, {R.fig('figS4_models_cpa')}, {R.tab('T7_models_cpa_full')}). En REM y "
          f"educación, el CPA fue del "
          f"{n1(k('apc_a05_autism_estab'))}{NBSP}% por establecimiento reportante para los ingresos por autismo estricto "
          f"({n1(k('apc_a05_autism_pop'))}{NBSP}% por residente), del {n1(k('apc_p2_dec_estab'))}{NBSP}% por "
          f"establecimiento para el stock P2 de diciembre ({n1(k('apc_p2_dec'))}{NBSP}% como conteo), del "
          f"{n1(k('apc_p6_primary_autism_estab'))}{NBSP}% por establecimiento para el stock P6 de atención primaria y de "
          f"{k.apc('apc_pie_harmonised')} para el stock PIE armonizado.")
    doc.p(f"Los ingresos A05 por autismo estricto crecieron al {k.apc('apc_a05_autism_pop')} por 100.000 residentes "
          f"(dispersión {n1(k('apc_a05_autism_pop_disp'))}), {k.apc('apc_a05_autism_estab')} por establecimiento "
          f"reportante, {k.apc('apc_a05_autism_stable_pop')} en el panel estable y "
          f"{k.apc('apc_a05_autism_ageadj_total')} tras el ajuste por edad "
          f"({n1(k('apc_a05_autism_ageadj_female'))}{NBSP}% en mujeres, {n1(k('apc_a05_autism_ageadj_male'))}{NBSP}% en "
          f"hombres). El stock P2 de diciembre creció al {k.apc('apc_p2_dec')} como conteo, {k.apc('apc_p2_dec_estab')} "
          f"por establecimiento reportante, {k.apc('apc_p2_dec_stable')} en el panel estable de "
          f"{n0(k('p2_tea_dec_stable_panel_n'))} establecimientos y {k.apc('apc_p2_dec_naneas_offset')} por 100 NANEAS "
          f"bajo control (2023–2025). Los stocks P6 de autismo estricto crecieron al {k.apc('apc_p6_primary_autism')} en "
          f"atención primaria ({n1(k('apc_p6_primary_autism_estab'))}{NBSP}% por establecimiento) y "
          f"{k.apc('apc_p6_specialty_autism')} en especialidad ({n1(k('apc_p6_specialty_autism_estab'))}{NBSP}% por "
          f"establecimiento). El stock PIE armonizado creció al {n1(k('apc_pie_harmonised'))}{NBSP}% ({CI95} "
          f"{ci(k('apc_pie_harmonised_lo'), k('apc_pie_harmonised_hi'))}; 2019–2025; "
          f"{n1(k('apc_pie_harmonised_2019_2023'))}{NBSP}% para la serie ministerial sola), con el TEA estricto al "
          f"{n1(k('apc_pie_tea_strict'))}{NBSP}% y el TEA-Asperger al {n1(k('apc_pie_tea_asperger'))}{NBSP}% en "
          f"2019–2023. La dispersión fue grande en los modelos de conteo de flujos y stocks, y ninguna especificación "
          f"estima un efecto de la Ley 21.545.", opt=True)
    doc.p(f"Los {n0(k('t8_rows'))} controles de reproducción {CR.label(CR.ANALYSIS_PLAN, LANG)} ({n0(k('t8_ok'))} "
          f"coinciden, {n0(k('t8_differs'))} difieren, todas documentadas) se listan por familia en la "
          f"{R.mtab('T8_controls_compact')} ({R.tab('T8_controls')}).")
    doc.add("_table", "T7_models")
    doc.add("_table", "T8_controls_compact")

    # ---------------- Discusión ----------------
    junaeb_levels = ("parvularia", "basico1", "basico5", "medio1")
    junaeb_2025 = [k(f"junaeb_{lvl}_all_pct_weighted_2025") for lvl in junaeb_levels]
    junaeb_min, junaeb_max = min(junaeb_2025), max(junaeb_2025)
    junaeb_mf = [k(f"junaeb_{lvl}_mf_ratio_2025") for lvl in junaeb_levels]
    junaeb_mf_min, junaeb_mf_max = min(junaeb_mf), max(junaeb_mf)
    doc.h1("Discusión")
    doc.p(f"En los sistemas públicos hospitalario, de atención primaria, de especialidad y educativo de Chile, el "
          f"reconocimiento administrativo del autismo se expandió varias veces entre 2019 y 2025: "
          f"{n1(k('grd_f84_any_rate_ratio_2024_2019'))} veces en la tasa de episodios GRD con F84 documentado, "
          f"{n1(k('a05_autism_entries_ratio_2025_2021'))} veces en los ingresos a programas por autismo estricto en "
          f"cuatro años, {n1(k('p2_tea_dec_ratio_2025_2019'))} veces en el stock de diciembre de niños con autismo bajo "
          f"control y {n1(k('pie_harmonised_ratio_2025_2019'))} veces en los estudiantes autistas registrados, con un "
          f"valle o meseta en 2020 y los aumentos más pronunciados en 2022–2024. Los aumentos sobreviven a la "
          f"restricción a un panel hospitalario fijo y a paneles estables de establecimientos, a la estratificación por "
          f"profundidad diagnóstica y al ajuste por la disrupción pandémica, aunque su magnitud cambia: el CPA del GRD "
          f"abarca del {n1(k('apc_grd_any_sensitivity_min'))} al {n1(k('apc_grd_any_sensitivity_max'))}{NBSP}% entre "
          f"especificaciones, los ingresos A05 crecen al {n1(k('apc_a05_autism_estab'))}{NBSP}% por establecimiento "
          f"reportante frente al {n1(k('apc_a05_autism_pop'))}{NBSP}% por residente, y el stock P2 al "
          f"{n1(k('apc_p2_dec_estab'))}{NBSP}% por establecimiento frente al {n1(k('apc_p2_dec'))}{NBSP}% como conteo.")
    doc.p(f"Deben separarse tres constructos. El reconocimiento administrativo es el registro de un código; la demanda "
          f"registrada es el volumen de contactos que lo llevan; la epidemiología subyacente es la ocurrencia del autismo "
          f"en la población. Nuestros datos miden los dos primeros. En el GRD, el "
          f"{pct(k('grd_f84_secondary_only_share_2024_pct'))} de los episodios con F84 en 2024 lo llevaba como "
          f"diagnóstico secundario y F84 principal creció al {n1(k('apc_grd_principal_obs'))}{NBSP}% frente al "
          f"{n1(k('apc_grd_any_obs'))}{NBSP}% para cualquier posición, de modo que la mayor parte de la señal "
          f"hospitalaria es la documentación del autismo en episodios ingresados por otras razones; se sabe que el "
          f"número de diagnósticos codificados por episodio cambia lo que capturan los datos administrativos "
          f"[@iezzoni1992], y la profundidad media aumentó un "
          f"{pct(100 * (k('grd_coding_depth_all_mean_ratio_2024_2019') - 1), 0)} en el período. Sin embargo, la tasa "
          f"aumentó dentro de cada banda de profundidad diagnóstica y cada diagnóstico adicional explicó solo una razón "
          f"de tasas de {n2(k('apc_grd_hospital_fe_depth_depth_rr_per_diagnosis'))} dentro de los hospitales, de modo "
          f"que la codificación más profunda da cuenta de parte del cambio y no de su totalidad. En REM, la brecha entre "
          f"el crecimiento por establecimiento y el crecimiento por residente cuantifica la contribución de la expansión "
          f"del reporte, y los stocks bajo control acumulan personas en el tiempo por construcción. La profundidad de "
          f"codificación, la expansión del reporte, los cambios de definición y la intensidad diagnóstica varían entre "
          f"lugares y son en sí mismos determinantes de las tasas registradas [@song2010]; el rango de "
          f"{n0(k('grd_hosp2024_rate_ratio_max_min'))} veces entre hospitales en 2024 refleja tanto la composición de "
          f"casos (los hospitales pediátricos encabezan) como la práctica.")
    doc.p(f"La convergencia entre sistemas independientes es informativa aunque los sistemas no midan lo mismo. Los "
          f"episodios hospitalarios, los ingresos a programas, los stocks bajo control y los registros escolares "
          f"comparten tiempo y dirección, una concentración en la primera infancia "
          f"({ppct(k('grd_f84_any_share_age_0_9_2024'))} de los episodios GRD y "
          f"{ppct(k('a05_autism_entries_share_age_0_9_2025'))} de los ingresos A05 en niños de 0 a 9 años) y una razón "
          f"hombres:mujeres decreciente (de {n1(k('grd_f84_any_mf_ratio_n_2019'))} a "
          f"{n1(k('grd_f84_any_mf_ratio_n_2024'))} en los episodios GRD; {n1(k('a05_autism_pop_asr_mf_ratio_2025'))} en "
          f"los ingresos A05 estandarizados; {n1(junaeb_mf_min)}–{n1(junaeb_mf_max)} en las cohortes JUNAEB), con "
          f"crecimiento más rápido en mujeres en los modelos ajustados por edad. Una razón que se aproxima a 2:1 está por "
          f"debajo del 3:1 de la detección activa y del 4:1 de las muestras pasivas [@loomes2017] y es consistente con un "
          f"reconocimiento creciente del autismo en niñas y mujeres, aunque los datos administrativos no pueden mostrar "
          f"si refleja un subreconocimiento previo o una población que cambia.")
    doc.p(f"La razón de sexos decreciente también está documentada en cohortes de nacimiento prospectivas, en las que la "
          f"razón hombre-mujer de la incidencia de autismo ha disminuido con el tiempo, y se ha vinculado al fenotipo "
          f"autista femenino y al camuflaje [@fyfe2026; @lai2020; @hull2020]; el benchmark de encuesta en niños chilenos "
          f"({n1(k('svy_endide_children_reported_male_pct') / k('svy_endide_children_reported_female_pct'))}:1 en "
          f"ENDIDE) está más cerca de los valores de detección pasiva que de los flujos administrativos de 2024–2025.",
          opt=True)
    doc.p(f"Internacionalmente, el patrón se asemeja a lo que los registros mostraron en décadas anteriores en otros "
          f"lugares. En la atención primaria del Reino Unido, los diagnósticos registrados de autismo aumentaron un "
          f"787{NBSP}% entre 1998 y 2018, con mayor pendiente en adultos y mujeres [@russell2022]; en Dinamarca, el "
          f"60{NBSP}% del aumento de la prevalencia fue atribuible a cambios en los criterios diagnósticos y a la "
          f"inclusión de contactos ambulatorios [@hansen2015]; en Suecia, los diagnósticos registrados aumentaron de "
          f"forma pronunciada en diez años mientras el fenotipo poblacional se mantuvo estable [@lundstrom2015]; y en "
          f"Estados Unidos, la vigilancia multifuente de niños de ocho años alcanzó uno de cada 31 niños en 2022, con "
          f"diferencias persistentes entre sitios en la identificación más que en la ocurrencia [@shaw2025]. Los cambios "
          f"anuales chilenos del {n0(k('apc_grd_any_sensitivity_min'))}–{n0(k('apc_grd_any_sensitivity_max'))}{NBSP}% en "
          f"episodios hospitalarios y del {n0(k('apc_a05_autism_estab'))}–{n0(k('apc_a05_autism_pop'))}{NBSP}% en "
          f"ingresos a programas están muy por encima de las tasas de largo plazo de esos países, que es lo que cabe "
          f"esperar de un sistema que se pone al día desde un nivel bajo de reconocimiento; los benchmarks de encuesta "
          f"del {pct(k('svy_endide_children_reported_confirmed_total_pct'), 1)}–"
          f"{pct(k('svy_endide_children_reported_total_pct'), 1)} en niños son del orden de la prevalencia identificada "
          f"en países de ingresos altos, mientras que los flujos y stocks administrativos permanecen muy por debajo de lo "
          f"que esos benchmarks implican.")
    doc.p(f"En América Latina, encuestas poblacionales en Brasil y México estimaron prevalencias de aproximadamente "
          f"0,3{NBSP}% y 0,9{NBSP}% [@paula2011; @fombonne2016], y un estudio de seis países que incluyó a Chile "
          f"documentó el diagnóstico tardío y el papel de la cobertura pública [@montielnava2024]. El sistema chileno "
          f"está segmentado por asegurador y por prestador: la red pública que observamos atiende a los residentes "
          f"asegurados por FONASA ({pct(k('share_fonasa_ine_pct_2025'), 0)} de la población en 2025), pero la atención "
          f"comprada de forma privada, la atención en redes ISAPRE y la de las fuerzas armadas son invisibles para el GRD "
          f"y el REM, y los cuidadores chilenos reportan que el acceso al diagnóstico y a los servicios difiere según el "
          f"seguro y la región [@garcia2022]. El reconocimiento administrativo depende, por tanto, de la oferta: crece "
          f"donde existen hospitales pediátricos, equipos de salud mental y programas de tamizaje, y la geografía del "
          f"lugar de atención difiere de la geografía de la residencia.")
    doc.p("La segmentación del aseguramiento de salud chileno entre FONASA e ISAPRE, y sus consecuencias para el acceso y "
          "el desempeño hospitalario, se han analizado en otros trabajos [@romanurrestarazu2018; @cid2016]; la política "
          "de desarrollo infantil temprano ha expandido el tamizaje del desarrollo en atención primaria, pero con brechas "
          "en el seguimiento de los niños con discapacidades del desarrollo [@breinbauer2022], y los datos REM ya se han "
          "usado para describir la caída y la recuperación de los controles de salud infantil en torno a la pandemia "
          "[@acevedo2025].", opt=True)
    doc.p(f"Las implicancias son prácticas. Cada etapa de la ruta pública está bajo presión: los códigos de tamizaje y "
          f"referencia se han rediseñado tres veces desde 2023, los ingresos a programas por autismo estricto alcanzaron "
          f"{n0(k('a05_autism_entries_2025'))} en 2025, los stocks bajo control en atención primaria se multiplicaron por "
          f"{n1(k('p6_primary_autism_dec_ratio_2025_2021'))} en cuatro años, los ingresos a rehabilitación de nivel "
          f"primario aumentaron {n1(k('a28_primary_ratio_2025_2023'))} veces en dos años, y los estudiantes autistas "
          f"representan el {pct(k('pie_tea_strict_share_of_pie_pct_2023'))} de los registros PIE (2023) y el "
          f"{pct(junaeb_min)}–{pct(junaeb_max)} de las cohortes escolares encuestadas en 2025. La capacidad diagnóstica, "
          f"el seguimiento en atención primaria, la rehabilitación y la integración escolar deben planificarse para una "
          f"demanda que sigue en aumento, y el monitoreo exigido por la Ley 21.545 debería construirse sobre indicadores "
          f"que informen el número de establecimientos reportantes, la era de definición y la regla de codificación "
          f"junto a cada conteo, y avanzar hacia el enlace a nivel de persona con los debidos resguardos, de modo que el "
          f"reconocimiento pueda distinguirse de los recontactos y de la acumulación de los stocks.")
    doc.p(f"Este estudio tiene limitaciones. La pandemia de COVID-19 deprimió la actividad y el reporte en 2020–2021 y su "
          f"recuperación se superpone con todos los cambios posteriores, de modo que el indicador de disrupción los "
          f"describe más que corregirlos. Los quiebres taxonómicos (TGD amplio a categorías en 2021; cuatro eras de A03; "
          f"el ítem JUNAEB desde 2023) truncan las series, y el archivo REM de 2025 puede estar incompleto "
          f"({n0(k('a05_autism_entries_estab_2025'))} establecimientos frente a {n0(k('a05_autism_entries_estab_2024'))} "
          f"en 2024). La cobertura y los paneles cambiaron: el GRD incorporó siete hospitales, los establecimientos "
          f"reportantes REM se multiplicaron, y los paneles estables son sensibilidades conservadoras y no series "
          f"representativas. Los numeradores se localizan por lugar de atención y los denominadores por residencia, de "
          f"modo que las tasas poblacionales son lecturas complementarias y las comparaciones regionales son ecológicas. "
          f"La profundidad de codificación aumentó y no puede ajustarse por completo. Las fuentes no están enlazadas por "
          f"persona, por lo que no puede estimarse ninguna trayectoria, cascada ni cociente de conversión, y las "
          f"personas son únicas solo dentro de un año. El reconocimiento depende del acceso a la red pública, lo que "
          f"introduce selección por seguro, región y edad. Ningún código se validó contra una evaluación clínica, y las "
          f"encuestas, con pocos casos y distinta formulación, son benchmarks y no validación. Las series son cortas "
          f"(tres a siete puntos), de modo que los modelos de tendencia son descriptivos y la dispersión es grande; las "
          f"varianzas de las encuestas son aproximadas (seudoestratos en ENDIDE; JUNAEB sin conglomerados).")
    doc.p(f"Sus fortalezas son la cobertura nacional de todas las fuentes públicas con un código o ítem de autismo, la "
          f"procedencia congelada con hashes SHA-256, {n0(k('t8_rows'))} controles de reproducción preespecificados "
          f"{CR.phrase(CR.ANALYSIS_PLAN, LANG)} con cada diferencia explicada, un plan de análisis preespecificado con "
          f"dos variantes completas de definición y un "
          f"conjunto exhaustivo de sensibilidades, intervalos exactos y basados en el diseño en todo el texto, y una "
          f"separación estricta de stocks y flujos, de lugar de atención y residencia, de eras de definición y de las "
          f"cuatro capas de denominador, sin ninguna afirmación de enlace individual.", opt=True)
    doc.p("No podemos separar la contribución de un cambio genuino en la ocurrencia del autismo de las contribuciones de "
          "la concienciación, la búsqueda de atención, la oferta de servicios, la cobertura, la profundidad de "
          "codificación y las definiciones. La convergencia observada establece que el reconocimiento y la demanda "
          "registrada aumentaron en todos los sistemas; no establece que el autismo se haya vuelto más frecuente, y la "
          "coincidencia de la Ley 21.545 con los demás cambios impide cualquier atribución a la ley.")
    doc.h1("Conclusión")
    doc.p("Entre 2019 y 2025, los sistemas públicos de salud y educación de Chile registraron una expansión de varias "
          "veces del reconocimiento administrativo del autismo que converge en tiempo y dirección entre registros "
          "hospitalarios, de atención primaria, de especialidad, de rehabilitación y escolares no enlazados, y que se "
          "explica en parte, pero no en su totalidad, por la expansión del reporte, la profundidad de codificación y los "
          "cambios de definición. Para Chile y para otros sistemas segmentados de América Latina, estos conteos son una "
          "medida de la demanda que los servicios y la vigilancia deben planificar, no una medida de prevalencia.")

    # ---------------- Declaraciones ----------------
    doc.h1("Contribuciones")
    doc.p(f"{AUTHOR} concibió el estudio, escribió el plan de análisis, obtuvo y curó los datos, escribió el pipeline de "
          f"análisis, verificó los controles de reproducción, produjo las láminas y las tablas, interpretó los resultados "
          f"y escribió el manuscrito. La revista exige que más de un autor haya accedido directamente a los datos "
          f"subyacentes y los haya verificado: antes del envío debe incorporarse un segundo autor que acceda de forma "
          f"independiente a los archivos fuente listados en la tabla de procedencia, reejecute el pipeline y verifique "
          f"los valores informados en el texto y en la {R.mtab('T8_controls_compact')}. Todos los autores tendrán acceso completo a todos los "
          f"datos y aceptan la responsabilidad de la decisión de enviar el manuscrito a publicación.")
    doc.h1("Declaración de intereses")
    doc.p("El autor declara no tener conflictos de interés. [Cada autor completará el formulario de declaración del ICMJE "
          "en el envío.]")
    doc.h1("Declaración de disponibilidad de datos")
    doc.p(f"Todos los datos fuente son públicos (la {R.tab('T1_sources')}, junto con la tabla de procedencia, lista "
          f"proveedores, archivos, "
          f"versiones y hashes SHA-256). Las tablas tidy derivadas ({n0(k('n_tables_supp_files_es'))} archivos de tablas "
          f"suplementarias y {n0(k('n_tables_main_es'))} de tablas principales por variante e idioma), la tabla plana de "
          f"cada cantidad citada en el texto, las salidas de los modelos, el plan de análisis, la bitácora de decisiones, "
          f"la lista de verificación de reporte y el pipeline completo en Python que reproduce cada lámina y tabla a "
          f"partir de los archivos fuente se depositarán en un repositorio público con identificador persistente (URL y "
          f"DOI por insertar en la aceptación) y están disponibles desde ahora a través del autor de correspondencia; el "
          f"acceso es abierto bajo una licencia permisiva, sin restricciones, desde la fecha de publicación. No se "
          f"redistribuyen datos a nivel de persona: los microdatos GRD, REM, DEIS, de encuestas y JUNAEB deben obtenerse "
          f"de los portales oficiales citados.")
    doc.h1("Financiamiento")
    doc.p("Ninguno.")
    doc.h1("Agradecimientos")
    doc.p("Agradecemos al Departamento de Estadísticas e Información de Salud (DEIS) del Ministerio de Salud, a FONASA, a "
          "la Superintendencia de Salud, al Instituto Nacional de Estadísticas, al Ministerio de Educación, a JUNAEB y al "
          "Ministerio de Desarrollo Social y Familia por publicar los datos usados en este estudio.")
    doc.h1("Declaración sobre el uso de inteligencia artificial")
    doc.p("De acuerdo con la política de la revista, el autor declara que en este trabajo se usaron asistentes basados en "
          "grandes modelos de lenguaje: Claude Code (Anthropic; modelo Claude Fable 5.1, claude-fable-5-1) y OpenAI Codex "
          "(extensión de Visual Studio Code; versión por confirmar por el autor). Propósito y alcance: escritura y "
          "depuración del pipeline de análisis en Python, de los scripts de láminas y tablas y del constructor de "
          "documentos; redacción y edición de este manuscrito, su resumen, el panel «Investigación en contexto» y el "
          "apéndice suplementario a partir de las salidas calculadas; y verificación de los metadatos bibliográficos "
          "contra PubMed, Crossref y páginas oficiales. Supervisión: el autor especificó cada análisis y regla, revisó y "
          "ejecutó todo el código, verificó cada cifra informada contra los archivos de salida y los controles de "
          "reproducción, comprobó cada referencia contra su fuente y editó el texto final; las herramientas no generaron "
          "ni alteraron datos, imágenes ni referencias, y no son autoras. Los prompts están disponibles a solicitud.")
    doc.add("refs", None)

    article_blocks = _expand(doc.blocks, R)
    R.article_citations = len(R.main_citations)

    # ---------------- Parte suplementaria (compartida por el manuscrito y el apéndice separado) ----------------
    supp = _Doc()
    supp.h1("Métodos suplementarios")
    supp.h2("S1. Fuentes, códigos y eras de definición")
    supp.p(f"El estudio usa la {vlabel}; el documento alternativo usa la {olabel}. Subcódigos GRD de esta variante: "
           f"{k('variant_grd_subcodes')}. Códigos REM de autismo estricto: {k('strict_autism_code_a05_entry')} (ingresos "
           f"A05), {k('strict_autism_code_a05_exit')} (egresos A05), {k('strict_autism_code_p6_primary')} (P6 atención "
           f"primaria) y {k('strict_autism_code_p6_specialty')} (P6 especialidad); familia TGD de la variante: ingresos "
           f"A05 {codes(k('a05_family_codes_entry'))}, egresos A05 {codes(k('a05_family_codes_exit'))}, P6 atención primaria "
           f"{codes(k('p6_family_codes_primary'))}, P6 especialidad {codes(k('p6_family_codes_specialty'))}; P2 autismo "
           f"{k('p2_tea_code')} y total NANEAS {k('p2_naneas_total_code')} (desde diciembre de 2023); A27 "
           f"{codes(k('a27_codes'))}; A28 {codes(k('a28_codes'))}. Los {n0(k('rem_pathway_codes_n'))} códigos se comprobaron contra el "
           f"diccionario oficial de cada año ({R.tab('ST2_rem_code_dictionary')}); los quiebres de definición, panel y "
           f"esquema por fuente se listan en {R.tab('S_definition_breaks')}; los establecimientos reportantes por código "
           f"y año en {R.tab('ST3_rem_reporting_establishments')}; el panel hospitalario en "
           f"{R.tab('ST1_grd_hospital_panel')}; la auditoría del identificador GRD en "
           f"{R.tab('ST8_grd_identifier_audit')}; los subcódigos F84 por posición en {R.tab('ST10_grd_f84_subcodes')}; y "
           f"la procedencia completa en {R.tab('ST7_provenance')} y {R.tab('ST7b_manifest_checks')} [@fonasa_grd; "
           f"@deis_egresos; @minsal_rem; @deis_rem20; @ine2019; @ine_base2024; @ine_censo2024; @fonasa_beneficiarios; "
           f"@fonasa_aps; @supersalud_isapre; @endide2022; @encavi2023; @mineduc_apuntes59; @mineduc_apuntes60; "
           f"@mineduc_sinaces2026; @junaeb_eve; @who_icd10; @deis_establecimientos].")
    supp.p("Eras A03 (nunca unidas): 2019–2022 códigos legados 03500406 (M-CHAT realizado) y 03500407 (M-CHAT alterado), "
           "restringidos a niños con alteración del lenguaje o del área social en el control de los 18 meses; 2023–2024 "
           "familia 09600212–09600219 (M-CHAT-R/F parte 1 por riesgo bajo, medio y alto; alto riesgo referido; parte 2 "
           "con y sin referencia); 2024 códigos 03700104–03700109 (niños de 31 a 59 meses: evaluados, sospecha en otro "
           "lugar, señales de alerta, referencia); rediseño 2025 03710013–03710021 (motivos a los 16–30 meses, resultado "
           "de riesgo y necesidad de referencia, sospecha a los 30–59 meses). A05 2019–2020 TGD amplio (06902600 "
           "ingresos, 05225000 egresos) y P6 2019–2020 TGD amplio (P6223000 atención primaria, P6223380 especialidad) "
           "contienen el síndrome de Rett de forma inseparable y se muestran solo como sensibilidades rotuladas. A27 "
           "cuenta intervenciones, no personas. Los stocks (P2, P6) son valores de diciembre con junio como sensibilidad "
           "y nunca se suman; el total NANEAS no se reporta en junio de 2023 (sin filas, no cero).")
    supp.h2("S2. Estimandos, denominadores y modelos")
    supp.p(f"Estimando hospitalario primario: episodios con F84 documentado (cualquiera de las "
           f"{n0(k('grd_diagnosis_positions'))} posiciones diagnósticas) por 100.000 episodios GRD del mismo año, panel y "
           f"modalidad, con límites exactos de Poisson; F84 principal, hospitalización estricta, CMA, panel fijo de "
           f"{n0(k('grd_fixed_panel_n'))} hospitales, estratos de profundidad diagnóstica, personas dentro del año y "
           f"tasas poblacionales INE por edad y sexo (estándar mundial OMS, intervalos de Fay–Feuer [@ahmad2001; "
           f"@fay1997]) como sensibilidades. Familia de tendencia: regresión log-lineal cuasi-Poisson [@wedderburn1974; "
           f"@mccullagh1989] del conteo sobre el año calendario con el logaritmo del denominador como offset; CPA = "
           f"100·(exp(β) − 1) con {CI95} de Wald [@clegg2009]; dispersión de Pearson; Durbin–Watson sobre los residuos "
           f"de devianza. Modelos hospital-año: efectos fijos de hospital con tendencia común y offset log(episodios del "
           f"hospital-año) (errores estándar agrupados por hospital como sensibilidad), efectos de hospital expresados "
           f"como razones de tasas frente a la media geométrica; intercepto aleatorio Poisson por hospital ajustado por "
           f"aproximación de Laplace con el offset añadido al predictor lineal (Bayes variacional como alternativa), "
           f"informado como sensibilidad porque ignora la sobredispersión. Covariables: profundidad diagnóstica media "
           f"(hospital-año o nacional) y el indicador de disrupción del reporte 2020–2021; ventanas 2019–2024 y "
           f"2021–2024. CPA ajustados por edad: celdas grupo de edad × año con efectos fijos de edad y offset "
           f"log(población). Los mapas comunales sí se calcularon: la razón comunal se estandariza indirectamente por "
           f"edad y sexo dentro del propio país y se suaviza con el estimador bayesiano empírico global de Marshall "
           f"[@breslow1987; @marshall1991], y el análisis territorial añade la I de Moran global y bivariada, LISA y "
           f"Gi* de Getis–Ord con umbral de Benjamini–Hochberg, las descomposiciones de Lorenz/Gini y de Theil, la "
           f"estabilidad de rangos y la asociación con la privación de área pequeña "
           f"({SM._range([R.fig('E40_maps_grd_smoothed_ratio'), R.fig('E49_regional_summary')])}, "
           f"{SM._range([R.tab('E40_grd_smoothed_ratio_comuna'), R.tab('E51_lisa_significant_comunas')])}), con supresión de "
           f"toda celda territorial menor que cinco; los mapas regionales de la {R.fig('figS9_regional_maps')} son "
           f"tasas brutas por residencia (GRD) y por lugar de atención (A05). El conjunto completo de {n0(k('models_n_variant'))} especificaciones convergidas por variante está "
           f"en {R.tab('T7_models_cpa_full')} y se resume en {R.fig('figS4_models_cpa')}; los efectos de hospital en "
           f"{R.fig('figS3_grd_hospital_effects')} y {R.tab('S_hospital_rates_2024')}; las tasas poblacionales en "
           f"{R.tab('S_grd_population_rates')} y {R.tab('S_a05_standardised_rates')}; los índices en "
           f"{R.tab('S_convergence_index')}.")
    supp.p(f"Capas de denominador: proyecciones INE base 2017 al 30 de junio por comuna, sexo y edad simple (primaria); "
           f"INE base 2024 (30 de junio y 1 de enero) y la población empadronada del Censo 2024 como sensibilidades "
           f"({R.fig('figS10_denominators')}, {R.tab('S10_denominator_sensitivity')}); stocks FONASA e ISAPRE de "
           f"diciembre e inscritos APS con sus cambios de esquema y reglas de armonización "
           f"({R.tab('ST12a_fonasa_schema')}, {R.tab('ST12b_isapre_rules')}, {R.tab('ST12c_aps_panel')}, "
           f"{R.fig('figS11_coverage_age_sex')}, {R.tab('S11_coverage_age_sex')}); cuadro de equivalencias comunal por nombre "
           f"normalizado exacto y alias explícitos ({R.tab('ST4a_comuna_crosswalk_summary')}, "
           f"{R.tab('ST4b_comuna_unmatched')}). Las tasas regionales ({R.fig('figS9_regional_maps')}, "
           f"{R.tab('S9_regional_rates')}) son ecológicas y no corrigen los flujos interregionales. Sensibilidad "
           f"semestral REM y paneles estables: {R.fig('figS5_rem_june_december')}, {R.tab('S5_june_december')}, "
           f"{R.tab('ST14_p2_p6_june_december')}, {R.fig('figS6_rem_stable_panel')}, {R.tab('S6_stable_panel')}; "
           f"estacionalidad mensual: {R.fig('figS13_rem_seasonality')}, {R.tab('S13_rem_seasonality')}; A05 por edad y "
           f"sexo: {R.fig('figS8_a05_age_sex')}, {R.tab('S8_a05_age_sex')}, {R.tab('ST13_a05_age_sex')}; DEIS: "
           f"{R.tab('ST11a_deis_annual')}, {R.tab('ST11b_deis_vs_grd')}, {R.fig('figS14_deis_sex_age')}, "
           f"{R.tab('S14_deis_sex_age')}; variantes GRD, subcódigos y tablas edad–sexo: {R.fig('figS1_grd_variants')}, "
           f"{R.fig('figS2_grd_subcodes')}, {R.tab('ST9_grd_age_sex')}.")
    supp.h2("S3. Encuestas")
    supp.p(f"ENDIDE 2022: ponderador fexp, {n0(k('svy_endide_adults_reported_total_n_strata'))} seudoestratos publicados "
           f"(región × zona) y {n0(k('svy_endide_adults_reported_total_n_psu'))} conglomerados de primera etapa "
           f"(cod_upm); los 96 estratos de segunda fase del diseño no se publican, por lo que se usa la aproximación de "
           f"conglomerado último con reemplazo, probablemente algo conservadora; adultos: ítem c26_33 (n = "
           f"{n0(k('svy_endide_adults_reported_total_n'))}); niños, niñas y adolescentes de 2 a 17 años: ítem n29_19 "
           f"respondido por el cuidador principal (n = {n0(k('svy_endide_children_reported_total_n'))}), confirmación "
           f"médica n29a_19 entre quienes tienen autismo reportado y respuesta válida (n = "
           f"{n0(k('svy_endide_children_confirmed_among_reported_total_n'))}). ENCAVI 2023–24: ponderador "
           f"w_personas_cal, estratos varstrat, conglomerados varunit, ítem p4_6_1_h (diagnóstico declarado) entre "
           f"personas de 15 años o más con respuesta válida (n = {n0(k('svy_encavi_15plus_diagnosed_total_n'))}; una "
           f"sensibilidad trata «no sabe/no responde» como no diagnosticado, n = "
           f"{n0(k('svy_encavi_15plus_diagnosed_sens_total_n'))}). Estimadores de razón por dominio con linealización de "
           f"Taylor [@wolter2007; @lumley2004], intervalos logit sobre t, efectos de diseño y errores estándar "
           f"relativos; ítems y formulación en {R.tab('ST5_survey_items')}. Las encuestas difieren en año, edades, "
           f"respondente y formulación y son benchmarks de autismo reportado, no prevalencia ni validación de códigos; "
           f"no se desagrega por región ni por comuna.")
    supp.h2("S4. Educación")
    supp.p(f"Series PIE: TEA estricto y TEA-Asperger 2019–2023 de MINEDUC Apuntes 60 (Tabla 6, p. 11) y Apuntes 59 "
           f"(desagregación por sexo); TEA + Asperger armonizado 2019–2023 de Apuntes 60 y 2024–2025 del informe de "
           f"seguimiento de la Ley 21.545 (Tablas 1–2, pp. 8–9), que también entrega los estudiantes autistas en escuelas "
           f"especiales y el total de estudiantes autistas registrados; la regla de 2022 adopta "
           f"{n0(k('pie_2022_apuntes60_sum'))} (suma de Apuntes 60, igual al total del informe menos escuelas "
           f"especiales) sobre el {n0(k('pie_2022_sinaces_printed'))} impreso. Microdatos de la Encuesta de "
           f"Vulnerabilidad Estudiantil de JUNAEB 2019–2025 (28 archivos desidentificados por año y nivel): el ítem TEA "
           f"existe desde 2023, ponderadores EXP_REG (2024) y EXP (2025); 2023 solo sin ponderar; 1.º medio en 2024 tiene "
           f"la variable TEA completamente vacía (no estimable, no cero); formulación, filtro y ponderador por año y "
           f"nivel en {R.tab('ST6_junaeb_items')}, estimaciones por sexo y nivel en {R.fig('figS12_junaeb_sex_level')} y "
           f"{R.tab('S12_junaeb_sex_level')}; las series graficadas en la {R.mfig('fig4_triangulation')} se listan en "
           f"{R.tab('F4_triangulation_series')} y los valores de la {R.mfig('fig3_rem_pathway')} en "
           f"{R.tab('F3_rem_pathway_data')}.")
    supp.h2("S5. Controles de reproducción")
    supp.p(f"Los controles de reproducción se cuentan en dos ámbitos con nombre que miden cosas distintas y nunca se "
           f"suman entre sí. Primero, {CR.phrase(CR.ANALYSIS_PLAN, LANG)}: las "
           f"{n0(k('controls_families_prespecified_n'))} familias de control preespecificadas, más las filas de "
           f"comprobación rotuladas, dan {n0(k('t8_rows'))} controles indicador-año "
           f"({n0(R.nrows('T8_controls_compact'))} filas en la {R.mtab('T8_controls_compact')}: una por familia de "
           f"control, una por fila de comprobación rotulada y una por control del módulo rotulado) reproducidos "
           f"desde los archivos fuente, de los cuales "
           f"{n0(k('t8_ok'))} coinciden y {n0(k('t8_differs'))} difieren, siendo cada diferencia una convención "
           f"documentada de panel, identificador o filas duplicadas (tabla completa en {R.tab('T8_controls')}; "
           f"dispersión de todos los {n0(R.nrows('S15_controls_scatter'))} controles numéricos de los módulos en "
           f"{R.fig('figS15_controls')} y {R.tab('S15_controls_scatter')}). Segundo, {CR.phrase(CR.PIPELINE, LANG)}: "
           f"{n0(k('controls_csv_rows'))} comprobaciones, de las cuales {n0(k('controls_csv_ok'))} reproducen, "
           f"{n0(k('controls_csv_info'))} son informativas (una cifra sin valor esperado externo) y "
           f"{n0(k('controls_csv_differs'))} llevan una diferencia documentada. Ese total lo escribe el pipeline en "
           f"controls_summary.csv y se informa aquí y en la metodología extendida; no lo imprime la lámina de flujo de "
           f"datos ({R.mfig('fig1_dataflow')}), cuya tabla de recuentos ({R.tab('T_dataflow_counts')}) lista los "
           f"recuentos de la propia lámina y no los controles de reproducción. Ningún control se completó por "
           f"plausibilidad; los valores que no se reproducen se marcan y no se citan.")

    # Metodología extendida (módulo 12, todas las fórmulas), láminas agrupadas por tema y tablas suplementarias.
    supp.blocks += SM.material_blocks(LANG, variant, V, R)
    supp.add("refs", dict(title=SUPP_REFS_H1, **{"continue": True}))
    note, index = SM.part_texts(LANG, R)
    note_standalone, _ = SM.part_texts(LANG, R, standalone=True)

    # El manuscrito lleva la misma parte suplementaria después de sus Referencias, en el mismo archivo.
    manuscript_blocks = (article_blocks + [("pagebreak", None), ("h1", SUPP_PART_H1), ("p", note), ("p", index)]
                         + supp.blocks)

    # El apéndice separado la repite con su propia portada, de modo que ambos comparten el registro de numeración.
    appendix = _Doc()
    appendix.add("title", "Apéndice suplementario")
    appendix.add("subtitle", f"{TITLE}. Variante de análisis: {vlabel}.")
    appendix.add("authors", dict(authors=[(AUTHOR, "1")], affiliations=[("1", AFFILIATION)],
                                 lines=[f"Correspondencia: {AUTHOR}, {AUTHOR_EMAIL}"]))
    appendix.h1("Contenido")
    appendix.p(note_standalone)
    appendix.p(index)
    appendix.blocks += supp.blocks
    return article_blocks, manuscript_blocks, appendix.blocks, R

def _expand(blocks, R: _Registry):
    """Sustituye los marcadores '_figure'/'_table' del documento principal por bloques reales de lámina/tabla."""
    out = []
    for kind, payload in blocks:
        if kind == "_figure":
            n = MAIN_FIGURES.index(payload) + 1
            out.append(_main_figure(R, payload, n))
        elif kind == "_table":
            n = MAIN_TABLES.index(payload) + 1
            out.append(_main_table(R, payload, n))
        else:
            out.append((kind, payload))
    return out

def _main_figure(R: _Registry, key: str, n: int):
    meta = R.captions[key]
    caption = f"{_strip_prefix(meta.get('title', ''))}. {meta.get('caption', '')}".strip()
    return ("figure", dict(path=R.fig_path(key), caption=caption, label=f"Figura {n}"))

def _main_table(R: _Registry, key: str, n: int):
    meta = R.titles[key]
    df = pd.read_csv(R.tab_path(key), dtype=str, keep_default_na=False)
    return ("table", dict(df=df, title=_strip_prefix(meta.get("title", "")),
                          note=table_note(key, meta.get("note", ""), df, LANG), label=f"Tabla {n}"))

# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------
def article(variant: str, V: dict) -> list:
    """Bloques solo del artículo (portada a Referencias), sin la parte suplementaria."""
    art, _, _, _ = _assemble(variant, V)
    return art

def manuscript(variant: str, V: dict) -> list:
    """Bloques del archivo del manuscrito (español): el artículo seguido de la parte suplementaria en el mismo archivo."""
    _, main, _, _ = _assemble(variant, V)
    return main

def supplement(variant: str, V: dict) -> list:
    """Bloques del apéndice suplementario separado (español), numerados de forma consistente con manuscript()."""
    _, _, supp, _ = _assemble(variant, V)
    return supp

def supplementary_map(variant: str, V: dict) -> dict:
    """Mapa de nombres de archivo a rótulos suplementarios finales ({'figures': {stem: 'Figura Sn'}, 'tables': {...}})."""
    return dict(figures={key: f"Figura S{i}" for i, key in enumerate(SUPP_FIGURES, 1)},
                tables={key: f"Tabla S{i}" for i, key in enumerate(SUPP_TABLES, 1)})

def main_map(variant: str, V: dict) -> dict:
    """Mapa de nombres de archivo a rótulos del artículo ({'figures': {stem: 'Figura n'}, 'tables': {...}})."""
    return dict(figures={key: f"Figura {i}" for i, key in enumerate(MAIN_FIGURES, 1)},
                tables={key: f"Tabla {i}" for i, key in enumerate(MAIN_TABLES, 1)})

def supplementary_part(variant: str, V: dict) -> list:
    """Bloques solo de la parte suplementaria (encabezado, nota, índice, metodología extendida, láminas y tablas)."""
    art, main, _, _ = _assemble(variant, V)
    return main[len(art):]

def main_citations(variant: str, V: dict) -> list:
    """Cadenas de cita de figuras/tablas del artículo producidas por el registro, en el orden en que se produjeron."""
    _, _, _, R = _assemble(variant, V)
    return list(R.main_citations)

_BODY_SECTIONS = ("Introducción", "Métodos", "Resultados", "Discusión", "Conclusión")
_DECL_SECTIONS = ("Contribuciones", "Declaración de intereses", "Declaración de disponibilidad de datos",
                  "Financiamiento", "Agradecimientos", "Declaración sobre el uso de inteligencia artificial")

def _wc(text: str) -> int:
    """Palabras sin marcadores de cita; el espacio duro de «12,5 %» e «IC 95 %» no separa palabras."""
    text = re.sub(r"\[@[^\]]+\]", "", str(text)).replace(NBSP, "")
    return len(text.split())

def word_counts(blocks: list) -> dict:
    """Recuentos: resumen, panel, cuerpo núcleo (Introducción–Conclusión sin '[OPT] '), cuerpo opcional, declaraciones."""
    counts = dict(summary=0, panel=0, core_body=0, opt_body=0, declarations=0, opt_paragraphs=0, tables=0, figures=0)
    section = None
    for kind, payload in blocks:
        if kind == "h1":
            section = payload
        elif kind == "panel":
            counts["panel"] += sum(_wc(t) for _, t in payload["items"])
        elif kind == "table":
            counts["tables"] += 1
        elif kind == "figure":
            counts["figures"] += 1
        elif kind in ("p", "bullets"):
            texts = payload if kind == "bullets" else [payload]
            for t in texts:
                w = _wc(t.replace("**", ""))
                if section == "Resumen":
                    counts["summary"] += w
                elif section in _BODY_SECTIONS:
                    if str(t).startswith(OPT):
                        counts["opt_body"] += _wc(t[len(OPT):])
                        counts["opt_paragraphs"] += 1
                    else:
                        counts["core_body"] += w
                elif section in _DECL_SECTIONS:
                    counts["declarations"] += w
    return counts

def build_all(out_dir: Path, variants=("con_rett", "sin_rett")) -> dict:
    """Construye manuscrito y suplemento DOCX por variante; devuelve los recuentos por variante."""
    from docx_builder import build_document
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for variant in variants:
        V = load_values(variant)
        art, main, supp, R = _assemble(variant, V)
        r_main = build_document(main, LANG, out_dir / f"manuscript_es_{variant}.docx", bib_path=BIB)
        r_supp = build_document(supp, LANG, out_dir / f"supplement_es_{variant}.docx", bib_path=BIB)
        report[variant] = dict(manuscript=r_main, supplement=r_supp, word_counts=word_counts(art),
                               core_citation_keys=len(citation_keys(art)), all_citation_keys=len(citation_keys(art, True)),
                               supp_figures=len(SUPP_FIGURES), supp_tables=len(SUPP_TABLES))
    return report

if __name__ == "__main__":
    import argparse
    import tempfile

    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="directorio de salida (por defecto: temporal)")
    args = ap.parse_args()
    if args.out:
        rep = build_all(Path(args.out))
    else:
        with tempfile.TemporaryDirectory() as tmp:
            rep = build_all(Path(tmp))
    print(json.dumps(rep, indent=1, ensure_ascii=False, default=str))
