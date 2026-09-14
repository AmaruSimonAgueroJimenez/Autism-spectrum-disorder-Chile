# -*- coding: utf-8 -*-
"""common.py — utilidades compartidas del pipeline Lancet: escritura atómica, hashes, lectura por trozos,
estadística (IC exactos, Wilson, Fay–Feuer, cuasi-Poisson, Taylor para encuestas), formato bilingüe y estilo de láminas.

Reutiliza `scripts/epi_helpers.py` del repositorio para la estandarización directa (OMS) y sus intervalos.
"""
from __future__ import annotations

import re
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from epi_helpers import (AGE_GROUPS, WHO_STANDARD, REGION_NAMES, REGION_ORDER, annual_percent_change,  # noqa: E402,F401
                         crude_rate, direct_standardization, empirical_bayes_ratio, expected_counts,
                         poisson_limits, rate_ratio, standardized_ratio, summarise_rates)
import config as CFG  # noqa: E402


# ---------------------------------------------------------------------------
# Procedencia y escritura atómica
# ---------------------------------------------------------------------------
def sha256_file(path: Path, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while chunk := fh.read(block):
            h.update(chunk)
    return h.hexdigest()


def atomic_write_csv(df: pd.DataFrame, path: Path, **kwargs) -> Path:
    """Escribe el CSV en un archivo temporal del mismo directorio y lo renombra (nunca sobreescribe a medias).

    Si el destino es una TABLA QUE SE IMPRIME (`is_printed_table`), el marco pasa antes por la regla de la
    raya del intervalo —una copia, nunca el marco del módulo— y lo convertido queda anotado en el libro
    mayor `range_dash_ledger()`. El hermano `_numeric.csv`, los tidy y los controles no pasan por ahí."""
    path = Path(path)
    if is_printed_table(path):
        df, _rd_conv, _rd_kept = range_dash_frame(df)
        _RANGE_DASH_LEDGER[str(path)] = (_rd_conv, _rd_kept)
    # Modo revista (LANCET_PLATE_JOURNAL): el corpus no recibe escrituras; la identidad cuando está apagado.
    path = journal_redirect(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        df.to_csv(tmp, index=False, **kwargs)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def atomic_write_json(obj, path: Path) -> Path:
    """Escritura atómica del JSON.

    Si el destino es el JSON de TÍTULOS o de LEYENDAS de una variante e idioma (`is_printed_labels`),
    todas sus cadenas pasan antes por la regla de la raya del intervalo: ese archivo es texto que el
    documento imprime, igual que una celda. Un runlog, un manifiesto o un `values_*.json` no pasan."""
    path = Path(path)
    if is_printed_labels(path):
        obj = range_dash_tree(obj)
    # Modo revista (LANCET_PLATE_JOURNAL): el corpus no recibe escrituras; la identidad cuando está apagado.
    # El captions.json de la carpeta de la revista se fusiona con el existente y lleva los títulos de
    # panel retirados de la lámina al principio de cada «(a) …» de la leyenda.
    dest = journal_redirect(path)
    if dest != path and dest.name == "captions.json":
        obj = _journal_captions_merge(obj, path, dest)
    path = dest
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.stem}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, ensure_ascii=False, indent=1, default=_json_default)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, Path):
        return str(o)
    return str(o)


def read_tidy(name: str, **kwargs) -> pd.DataFrame:
    path = CFG.TIDY / (name if name.endswith(".csv") else f"{name}.csv")
    if not path.is_file():
        raise FileNotFoundError(f"Falta {path}; ejecute el paso del pipeline que lo produce.")
    return pd.read_csv(path, **kwargs)


# ---------------------------------------------------------------------------
# Lectura de fuentes grandes
# ---------------------------------------------------------------------------
def iter_rem_series(path: Path, codes: set[str] | None, usecols: list[str] | None = None, chunksize: int = 2_000_000):
    """Itera SerieA/SerieP (sep=';') filtrando por códigos; conserva Col01..Col50 como texto para distinguir vacío de cero."""
    cols = usecols or ["Mes", "IdServicio", "Ano", "IdEstablecimiento", "CodigoPrestacion", "IdRegion", "IdComuna"] + [f"Col{i:02d}" for i in range(1, 51)]
    for chunk in pd.read_csv(path, sep=";", usecols=cols, dtype=str, chunksize=chunksize, encoding="utf-8", encoding_errors="replace"):
        if codes is not None:
            chunk = chunk.loc[chunk.CodigoPrestacion.isin(codes)]
        if len(chunk):
            yield chunk


GRD_DIAG_COLS = [f"DIAGNOSTICO{i}" for i in range(1, 36)]


def iter_grd(path: Path, usecols: list[str], chunksize: int = 200_000):
    """Itera un GRD anual (sep='|')."""
    header = pd.read_csv(path, sep="|", nrows=0).columns.tolist()
    present = [c for c in usecols if c in header]
    for chunk in pd.read_csv(path, sep="|", usecols=present, dtype="string", chunksize=chunksize, encoding="utf-8", encoding_errors="replace"):
        yield chunk


def normalize_code(value) -> str:
    return "" if pd.isna(value) else str(value).replace(".", "").replace(" ", "").strip().upper()


# ---------------------------------------------------------------------------
# Estadística
# ---------------------------------------------------------------------------
def wilson(k, n, alpha=0.05):
    if n == 0:
        return np.nan, np.nan, np.nan
    z = stats.norm.ppf(1 - alpha / 2)
    p = k / n
    den = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return p, max(0.0, centre - half), min(1.0, centre + half)


def rate_per(count, denominator, per=100_000, alpha=0.05):
    """Tasa por `per` con límites exactos de Poisson (count entero) y denominador fijo."""
    lo, hi = poisson_limits([count], alpha)
    return per * count / denominator, per * lo[0] / denominator, per * hi[0] / denominator


def quasi_poisson_trend(years, counts, offsets, covariates: pd.DataFrame | None = None, alpha=0.05) -> dict:
    """CPA cuasi-Poisson con offset log(denominador) y covariables opcionales; devuelve coeficientes, IC y dispersión."""
    import statsmodels.api as sm
    y = np.asarray(counts, dtype=float)
    t = np.asarray(years, dtype=float) - float(np.min(years))
    X = pd.DataFrame({"const": 1.0, "t": t})
    if covariates is not None:
        X = pd.concat([X.reset_index(drop=True), covariates.reset_index(drop=True)], axis=1)
    model = sm.GLM(y, X, family=sm.families.Poisson(), offset=np.log(np.asarray(offsets, dtype=float)))
    fit = model.fit(scale="X2") if len(y) > X.shape[1] else model.fit()
    beta, se = float(fit.params["t"]), float(fit.bse["t"])
    z = stats.norm.ppf(1 - alpha / 2)
    return dict(apc=100 * (np.exp(beta) - 1), apc_lo=100 * (np.exp(beta - z * se) - 1), apc_hi=100 * (np.exp(beta + z * se) - 1),
                p_value=float(fit.pvalues["t"]), dispersion=float(fit.scale), n=len(y), params=fit.params.to_dict(), bse=fit.bse.to_dict())


def survey_proportion(df: pd.DataFrame, y: str, weight: str, strata: str | None, psu: str | None, domain: pd.Series | None = None, alpha=0.05) -> dict:
    """Proporción ponderada de una variable 0/1 con error estándar por linealización de Taylor (diseño estratificado por conglomerados).

    Dominios: se mantienen todas las unidades y se pone a cero la contribución fuera del dominio (estimador de razón).
    Devuelve proporción, EE, IC 95 % (logit), total ponderado, n no ponderado del dominio y casos, y grados de libertad (PSU − estratos).
    """
    d = df.copy()
    w = d[weight].astype(float)
    ind = d[y].astype(float)
    dom = np.ones(len(d)) if domain is None else domain.astype(float).values
    num = w * ind * dom
    den = w * dom
    p = num.sum() / den.sum()
    # Variable linealizada del estimador de razón.
    u = (num - p * den) / den.sum()
    d["_u"] = u.values
    d["_strata"] = d[strata] if strata else 0
    d["_psu"] = d[psu] if psu else np.arange(len(d))
    var = 0.0
    n_psu = 0
    n_strata = 0
    for _, s in d.groupby("_strata"):
        totals = s.groupby("_psu")["_u"].sum()
        k = len(totals)
        n_psu += k
        n_strata += 1
        if k > 1:
            var += k / (k - 1) * ((totals - totals.mean()) ** 2).sum()
    se = float(np.sqrt(var))
    dfree = max(n_psu - n_strata, 1)
    tcrit = stats.t.ppf(1 - alpha / 2, dfree)
    if 0 < p < 1 and se > 0:
        logit = np.log(p / (1 - p))
        se_logit = se / (p * (1 - p))
        lo, hi = 1 / (1 + np.exp(-(logit - tcrit * se_logit))), 1 / (1 + np.exp(-(logit + tcrit * se_logit)))
    else:
        lo, hi = np.nan, np.nan
    return dict(proportion=float(p), se=se, lo=float(lo), hi=float(hi), weighted_total=float(num.sum()), weighted_population=float(den.sum()),
                n_domain=int(dom.sum()), n_cases=int((ind * dom).sum()), df=int(dfree), n_psu=int(n_psu), n_strata=int(n_strata))


# ---------------------------------------------------------------------------
# Formato bilingüe
# ---------------------------------------------------------------------------
#: EL SIGNO NEGATIVO DEL ESTUDIO (fase 4g, tarea G2). Dos trazos distintos hacían el mismo oficio a
#: cuarenta páginas de distancia: la Figura S3 (c) imprimía «ρ = -0,06» con el GUION ASCII (U+002D, el que
#: devolvía este formateador) y la S51, del mismo suplemento, «−0,10» con el MENOS TIPOGRÁFICO (U+2212),
#: porque el módulo 15b era el único que convertía. El guion mide 2,9 pt a 8 pt de cuerpo y se dibuja a la
#: altura de la x; el menos mide 6,8 pt y se dibuja sobre el eje matemático, a la misma altura que la barra
#: del «+» y del «=». Puestos uno al lado del otro en la misma tabla, el lector lee dos signos.
#:
#: LA REGLA, y vale para todo el estudio:
#:
#:   * TEXTO PARA EL LECTOR —prosa, celdas de tabla, títulos, leyendas, rótulos y marcas de eje— lleva el
#:     MENOS TIPOGRÁFICO. Es lo que `fmt_number` devuelve por omisión, de modo que `fmt_ci`, `fmt_p` y los
#:     ciento dos sitios que llaman al formateador fuera de las pruebas lo heredan sin tocar una línea: la
#:     regla se aplica UNA vez, aquí, y no se repite (ni se olvida) módulo a módulo. Coincide además con
#:     lo que matplotlib ya hace solo en las marcas de eje SIN formateador propio (`axes.unicode_minus`):
#:     por eso los ejes salían bien y las celdas no, y por eso un `FuncFormatter` sobre `fmt_number`
#:     deshacía, hasta aquí, el comportamiento por omisión de la propia biblioteca.
#:   * IDENTIFICADORES DE MÁQUINA —nombres de archivo, claves, columnas, códigos, rutas— y VALORES QUE UN
#:     PROGRAMA VUELVE A LEER —los `*_numeric.csv`, los tidy de `outputs/tidy/`, los controles— llevan el
#:     GUION ASCII. Esos no pasan por `fmt_number`: se escriben con el número crudo (`atomic_write_csv`
#:     sobre el marco sin formatear), y por eso el cambio no los toca. Cuando alguna vez haga falta pedir
#:     la forma ASCII desde código que sí formatea, están `fmt_number(..., ascii_minus=True)` y
#:     `to_ascii_minus(s)` para volver atrás.
#:
#: La conversión sustituye SOLO el signo de apertura, nunca un guion interior: el separador de millares es
#: «.» o «,» y jamás un guion, pero un `-inf` o un texto que se colara quedan intactos porque se exige que
#: tras el signo venga una cifra. Es idempotente: `_typographic_minus` del módulo 15b, que envuelve esta
#: función, ya no encuentra guion que cambiar y se queda en no-op.
MINUS_SIGN = "\u2212"    # U+2212 MINUS SIGN — el signo negativo del texto impreso
ASCII_HYPHEN = "\u002d"  # U+002D HYPHEN-MINUS — el de los identificadores y los archivos de máquina


def to_ascii_minus(s: str) -> str:
    """El camino de vuelta: menos tipográfico → guion ASCII, para lo que una máquina tenga que releer."""
    return str(s).replace(MINUS_SIGN, ASCII_HYPHEN)


def fmt_number(x, dec=0, lang="es", *, ascii_minus=False):
    """Número en la convención del idioma; el negativo lleva el MENOS TIPOGRÁFICO (ver la regla arriba).

    `ascii_minus=True` devuelve el guion ASCII, para lo que un programa vuelva a leer.
    """
    if x is None or (isinstance(x, float) and np.isnan(x)) or (not isinstance(x, str) and pd.isna(x)):
        return "—" if lang == "es" else "—"
    s = f"{x:,.{dec}f}"
    if lang == "es":
        s = s.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    if not ascii_minus and s[:1] == ASCII_HYPHEN and s[1:2].isdigit():
        s = MINUS_SIGN + s[1:]
    return s


#: VENTANA DE AÑOS: el guion ASCII es la forma de MÁQUINA («2019-2021»), la que viaja por las tablas tidy,
#: por las claves de `comparison`/`years` y por los nombres de archivo; la RAYA CORTA (U+2013) es la forma
#: IMPRESA, que es la que usa el resto del corpus en prosa, leyendas y ejes. `yspan` convierte de la primera
#: a la segunda AL ROTULAR, y sólo ahí: nunca se escribe en el tidy, porque un lector de máquina que parte
#: por «-» dejaría de reconocer la clave. Toca únicamente el guion que separa DOS AÑOS DE CUATRO CIFRAS,
#: de modo que un identificador («REM-20», «knn-4», «F84-2019»), una fecha ISO o un menos delante de una
#: cifra suelta quedan intactos. Es idempotente: sobre un texto que ya lleva la raya no cambia nada.
EN_DASH = "\u2013"       # U+2013 EN DASH — la raya de los intervalos impresos
_YSPAN_RE = re.compile(r"(?<!\d)((?:19|20)\d{2})-((?:19|20)\d{2})(?!\d)")


def yspan(s) -> str:
    """Ventana de años en forma impresa: «2019-2021» → «2019–2021». Sólo para rotular (ver la regla arriba)."""
    return _YSPAN_RE.sub(rf"\1{EN_DASH}\2", str(s))


# ---------------------------------------------------------------------------
# LA RAYA DEL INTERVALO: UNA SOLA REGLA PARA TODO EL CORPUS (fase 4j, tarea J2)
# ---------------------------------------------------------------------------
#: EL MISMO INTERVALO NUMÉRICO SE IMPRIMÍA CON DOS TRAZOS. La lectura independiente de la compilación del
#: 2026-09-08 encontró «0-4» y «0–4» en la misma página, y a veces en la misma lámina y en la misma fila de
#: la misma tabla: 448 intervalos con guion frente a 774 con raya en nueve láminas publicadas, y 982 celdas
#: con guion frente a 402 con raya en veinte tablas por documento largo (la Tabla S110 imprimía «Documented
#: F84 · 0-4» en la columna de indicador y «2 (0–6)» en la celda de al lado). La causa era estructural: la
#: regla estaba escrita CINCO veces —una copia de `dash_label`/`dash_intervals` en `08a`, `08b`, `08c`, `14`
#: y `15b`— y por tanto NO estaba escrita en los cuatro módulos de lámina que faltaban (`06`, `08d`, `13`,
#: `15`) ni en ninguna ruta de tabla, donde sólo se convertía la ventana de años (`yspan`) y no la banda de
#: edad, el tramo ni el decil.
#:
#: LA REGLA, escrita UNA vez y aquí, con TRES trazos y CUATRO categorías:
#:
#:   1. INTERVALO QUE UN LECTOR LEE  →  RAYA CORTA U+2013. Todo lo que separa dos cifras y se imprime:
#:      «0–4», «6–7», «31–59 meses», «2019–2024», «P25–P75» ya escrito con raya, «1,5–2,5», «2–5/6–11/12–17».
#:   2. IDENTIFICADOR DE MÁQUINA  →  GUION ASCII, el que trae de nacimiento. Nombre de archivo, ruta, URL,
#:      clave de diccionario, columna, «slug» de modelo o código: todo lo que alguien vuelve a leer, a
#:      cruzar o a partir por «-». Se reconoce por la MARCA que lleva dentro —«:» «_» «=» «|» «[» «]» «%»
#:      «\», una extensión de archivo, o «/» acompañado de letras—, que es el mismo criterio con el que los
#:      módulos 09b y 16 venían eximiendo la ventana de años, y no por una lista de columnas que envejece.
#:   3. NÚMERO NEGATIVO  →  MENOS TIPOGRÁFICO U+2212. No lo toca esta regla: lo pone `fmt_number`, y por eso
#:      un menos delante de una cifra suelta nunca es un guion cuando llega hasta aquí.
#:   4. LO QUE NO ES UN INTERVALO AUNQUE UNA CIFRA TOQUE EL GUION POR LOS DOS LADOS  →  GUION ASCII:
#:      * la FECHA, completa («2026-09-04») o de año-mes («2014-07/2026»): ahí el guion es el separador de
#:        una fecha ISO, no dos extremos;
#:      * el CÓDIGO con prefijo alfabético pegado («F84-2019», «A03-2024»): une un código a un año;
#:      * la CADENA de TRES O MÁS números («65-65-65-65-68-72», los seis tamaños anuales del panel
#:        observado): es una enumeración, no un intervalo de dos extremos. El corpus escribe ese mismo
#:        hecho como «65, 65, 65, 65, 68 y 72 hospitales» en la nota de los modelos, y así queda ahora
#:        también en el único rótulo que lo abreviaba (`16::PANEL_LABEL`).
#:
#: DÓNDE SE APLICA, y por qué ahí. En los DOS sitios por los que pasa TODO lo que el lector lee, de modo que
#: ningún módulo tiene que acordarse de llamarla y ninguno puede saltársela:
#:   * LÁMINA: `plate_range_dash`, enganchada al principio de `plate_fit` y de `plate_resolve` (los nueve
#:     módulos de lámina llaman al menos a uno de los dos justo antes de guardar) y de `save_fig`. Se aplica
#:     ANTES del reparto: el motor mide entonces el texto DEFINITIVO, y una marca que crece 1,5 pt al pasar
#:     de guion a raya no se sale de su columna después de medida.
#:   * TABLA IMPRESA: `range_dash_frame`, enganchada a `atomic_write_csv` cuando el destino es una tabla que
#:     se imprime —`outputs/<variante>/<idioma>/tables/…csv` y `.../extra/tables/…csv`—, y `range_dash_tree`
#:     enganchada a `atomic_write_json` cuando el destino es el `titles.json` o el `captions.json` de una
#:     variante e idioma, que es texto impreso igual que una celda. El hermano `_numeric.csv`, los
#:     `outputs/tidy/`, los `outputs/controls/`, los runlogs y los `values_*.json` NO pasan por la regla:
#:     son justamente los que una máquina vuelve a leer.
#: La conversión NUNCA toca el DATO: en este estudio la banda de edad y el tramo son A LA VEZ la clave con
#: la que se busca («reindex(bins)», «groupby("age_group")», «set_index("depth_bin")») y el rótulo que se
#: dibuja. Por eso se hace sobre el TEXTO YA COMPUESTO de la lámina y sobre una COPIA del marco al
#: escribirlo, y el marco que el módulo sigue usando queda intacto. Es idempotente: sobre un texto que ya
#: lleva la raya no cambia nada, de modo que las cinco copias que ya convertían siguen siendo correctas y
#: esta regla no encuentra nada que hacer detrás de ellas.
_RANGE_TOKEN_RE = re.compile(r"\S+")
#: Marca de MÁQUINA dentro de una palabra (categoría 2). Igual a la que ya usaban 09b y 16.
_RANGE_MACHINE_MARK_RE = re.compile(r"[:\\|\[\]=%_]|\.[A-Za-z][A-Za-z0-9]{1,4}(?![A-Za-z0-9])")
#: FECHA ISO completa o año-mes (categoría 4a).
_RANGE_DATE_RE = re.compile(r"(?<!\d)(?:19|20)\d{2}-(?:0[1-9]|1[0-2])(?:-(?:0[1-9]|[12]\d|3[01]))?(?!\d)")
#: CÓDIGO con prefijo alfabético pegado al primer número (categoría 4b).
_RANGE_CODE_RE = re.compile(r"[^\W\d_]\d+(?:-\d+)+", re.UNICODE)
#: CADENA de tres o más números unidos por guion (categoría 4c).
_RANGE_CHAIN_RE = re.compile(r"(?<![\d.,])\d+(?:[.,]\d+)?(?:-\d+(?:[.,]\d+)?){2,}(?![\d.,])")
#: El guion que separa DOS CIFRAS, que es el único que esta regla convierte.
_RANGE_HYPHEN_RE = re.compile(r"(?<=\d)-(?=\d)")
#: La raya ya puesta, sólo para MEDIR.
_RANGE_DASH_RE = re.compile(r"(?<=\d)–(?=\d)")
#: Columna de TRANSCRIPCIÓN LITERAL: su propio encabezado declara la transcripción. Mismo criterio con el
#: que `tests/test_language_purity.py` exime una columna de la prueba de idioma. Retocar la tipografía de
#: una cita rompe la cita, de modo que esas columnas conservan el guion que publica la fuente.
_RANGE_VERBATIM_HEADER_RE = re.compile(r"\(textual\)|verbatim", re.IGNORECASE)
#: Clave con la que un marco puede declarar sus propias columnas exentas (`df.attrs`).
RANGE_DASH_EXEMPT = "range_dash_exempt"


#: PUNTUACIÓN QUE ENVUELVE A LA PALABRA y no forma parte de ella. Se quita ANTES de preguntar si la
#: palabra es una clave de máquina, porque si no el signo de la FRASE decide la tipografía del NÚMERO:
#: «2020-2021:» —una entradilla de leyenda, con sus dos puntos de frase— caía en la categoría de máquina
#: por culpa de esos dos puntos y se quedaba con el guion, mientras «2020–2021» a dos centímetros llevaba
#: la raya. Los corchetes y las barras que SÍ son marca de máquina van siempre acompañados de otra dentro
#: de la palabra (`EF6_readmission[con_rett|2019-2020]` conserva `_`, `[` y `|` después de pelarla).
_RANGE_WRAP_OPEN = "(«\u201c\u2018\"'¡¿[{"
_RANGE_WRAP_CLOSE = ".,;:!?)»\u201d\u2019\"']}"


def is_machine_token(tok) -> bool:
    """La palabra es una clave de máquina (ruta, URL, identificador) y no se retipografía (categoría 2)."""
    tok = str(tok).lstrip(_RANGE_WRAP_OPEN).rstrip(_RANGE_WRAP_CLOSE)
    return bool(_RANGE_MACHINE_MARK_RE.search(tok)) or ("/" in tok and any(c.isalpha() for c in tok))


def _range_protected(tok: str) -> list[tuple[int, int]]:
    """Tramos del token en los que el guion NO separa dos extremos (categoría 4)."""
    spans: list[tuple[int, int]] = []
    for rx in (_RANGE_DATE_RE, _RANGE_CODE_RE, _RANGE_CHAIN_RE):
        spans += [m.span() for m in rx.finditer(tok)]
    return spans


def _range_token(tok: str) -> tuple[str, int]:
    """Devuelve el token con la raya puesta y cuántos guiones de intervalo tenía."""
    if "-" not in tok or is_machine_token(tok):
        return tok, 0
    spans = _range_protected(tok)
    out, n, last = [], 0, len(tok) - 1
    for i, ch in enumerate(tok):
        if (ch == "-" and 0 < i < last and tok[i - 1].isdigit() and tok[i + 1].isdigit()
                and not any(a <= i < b for a, b in spans)):
            out.append(EN_DASH)
            n += 1
        else:
            out.append(ch)
    return "".join(out), n


def range_dash(s) -> str:
    """LA REGLA: el intervalo numérico que un lector lee lleva raya corta. «0-4» → «0–4».

    Idempotente, palabra a palabra, y ciega para las cuatro categorías que conservan el guion."""
    s = str(s)
    return s if "-" not in s else _RANGE_TOKEN_RE.sub(lambda m: _range_token(m.group(0))[0], s)


def count_hyphen_ranges(s) -> int:
    """EL INSTRUMENTO: intervalos DE LECTURA que la cadena todavía escribe con guion (0 = cumple)."""
    s = str(s)
    return 0 if "-" not in s else sum(_range_token(m.group(0))[1] for m in _RANGE_TOKEN_RE.finditer(s))


def count_dash_ranges(s) -> int:
    """El otro lado del instrumento: intervalos ya escritos con raya."""
    return len(_RANGE_DASH_RE.findall(str(s)))


def count_kept_hyphens(s) -> int:
    """Guiones entre dos cifras que la regla CONSERVA a propósito (categorías 2 y 4)."""
    s = str(s)
    return len(_RANGE_HYPHEN_RE.findall(s)) - count_hyphen_ranges(s)


def range_dash_verbatim_header(header) -> bool:
    """El encabezado declara una TRANSCRIPCIÓN LITERAL y su columna no se retipografía."""
    return isinstance(header, str) and bool(_RANGE_VERBATIM_HEADER_RE.search(header))


def range_dash_frame(df, exempt_headers=()) -> tuple:
    """La regla sobre el marco IMPRESO: encabezados y celdas de texto, sobre una COPIA.

    Devuelve `(marco, convertidos, conservados)`: intervalos que pasaron a raya y guiones entre cifras que
    quedan a propósito (claves de máquina, fechas, códigos, cadenas y columnas de transcripción literal)."""
    exempt = frozenset(h for h in exempt_headers if isinstance(h, str))
    exempt |= frozenset(h for h in df.attrs.get(RANGE_DASH_EXEMPT, ()) if isinstance(h, str))
    conv = kept = 0

    def skipped(header) -> bool:
        return isinstance(header, str) and (header in exempt or range_dash_verbatim_header(header))

    def one(v):
        nonlocal conv, kept
        if not isinstance(v, str) or "-" not in v:
            return v
        n = count_hyphen_ranges(v)
        kept += count_kept_hyphens(v)
        if not n:
            return v
        conv += n
        return range_dash(v)

    def counted(v):
        nonlocal kept
        if isinstance(v, str) and "-" in v:
            kept += len(_RANGE_HYPHEN_RE.findall(v))
        return v

    out = df.copy()
    # Se recorre POR POSICIÓN, no por nombre: una tabla puede repetir un encabezado (la serie anual con
    # dos columnas «2019»), y `out[nombre]` devolvería entonces un marco y no una columna.
    for i in range(out.shape[1]):
        col = out.columns[i]
        if out.dtypes.iloc[i] != object:
            continue
        out.isetitem(i, out.iloc[:, i].map(counted if skipped(col) else one))
    out.columns = [c if skipped(c) else (one(c) if isinstance(c, str) else c) for c in out.columns]
    return out, conv, kept


#: Cuánto convirtió la regla al escribir cada tabla impresa, para que el módulo lo lleve a su runlog y para
#: poder poner el ANTES y el DESPUÉS sobre el mismo instrumento.
_RANGE_DASH_LEDGER: dict[str, tuple[int, int]] = {}


def range_dash_ledger() -> dict:
    """`{ruta: (convertidos, conservados)}` de las tablas impresas escritas en esta ejecución."""
    return dict(_RANGE_DASH_LEDGER)


def range_dash_totals() -> tuple[int, int]:
    """Totales del libro mayor: intervalos convertidos y guiones conservados a propósito."""
    return (sum(v[0] for v in _RANGE_DASH_LEDGER.values()),
            sum(v[1] for v in _RANGE_DASH_LEDGER.values()))


def is_printed_table(path) -> bool:
    """El archivo es una TABLA QUE SE IMPRIME: `<variante>/<idioma>/tables` o `.../extra/tables`, sin
    el sufijo `_numeric`. Los `outputs/tidy/`, los `outputs/controls/` y el hermano numérico quedan fuera
    porque son justamente lo que una máquina vuelve a leer."""
    path = Path(path)
    if path.suffix.lower() != ".csv" or path.stem.endswith("_numeric"):
        return False
    parts = path.parts[:-1]
    if not parts or parts[-1] != "tables":
        return False
    parts = parts[:-1]
    if parts and parts[-1] == "extra":
        parts = parts[:-1]
    return (len(parts) >= 2 and parts[-1] in tuple(CFG.LANGUAGES) and parts[-2] in tuple(CFG.VARIANTS))


def is_printed_labels(path) -> bool:
    """El archivo es el JSON de TÍTULOS o de LEYENDAS que el documento imprime: `titles.json` o
    `captions.json` bajo `outputs/<variante>/<idioma>/…`. Runlogs, manifiestos y `values_*.json` no."""
    path = Path(path)
    if path.name not in ("titles.json", "captions.json"):
        return False
    parts = path.parts[:-1]
    return any(parts[i] in tuple(CFG.VARIANTS) and parts[i + 1] in tuple(CFG.LANGUAGES)
               for i in range(len(parts) - 1))


def range_dash_tree(obj):
    """La regla sobre todas las cadenas de un árbol JSON (claves incluidas), sin tocar la estructura."""
    if isinstance(obj, str):
        return range_dash(obj)
    if isinstance(obj, dict):
        return {(range_dash(k) if isinstance(k, str) else k): range_dash_tree(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [range_dash_tree(v) for v in obj]
    if isinstance(obj, tuple):
        return tuple(range_dash_tree(v) for v in obj)
    return obj


_PLATE_PCT_RE = _re_pct = __import__("re").compile(r"(?<=\d)[ \t\u2009\u202f]+(?=%)")


def plate_pct_bind(fig) -> int:
    """El signo de porcentaje queda atado a su cifra en TODO texto que la lámina dibuja.

    Es la misma regla que el documento aplica a su prosa y a sus tablas, y hace falta aquí por la misma
    razón: matplotlib parte un rótulo largo por el espacio, y un rótulo de eje como «% del riesgo alto con
    derivación (IC 95 %)» se imprimía con «(IC 95» al final de un renglón y «% de Wilson)» abriendo el
    siguiente. Sólo se tocan los textos que el módulo escribe —no las marcas de eje, que son un único
    testigo y no se parten—, y el modo matemático se salta."""
    from matplotlib.text import Text
    ticks = set()
    axes, i = list(fig.axes), 0
    while i < len(axes):
        axes.extend(a for a in getattr(axes[i], "child_axes", []) if a not in axes)
        i += 1
    for ax in axes:
        for axis in (ax.xaxis, ax.yaxis):
            try:
                ticks.update(id(t) for t in axis.get_ticklabels(which="both"))
            except (AttributeError, ValueError, RuntimeError, TypeError):
                continue
    bound = 0
    for art in fig.findobj(Text):
        if id(art) in ticks:
            continue
        try:
            if not art.get_visible():
                continue
            s = art.get_text()
        except (AttributeError, ValueError, RuntimeError, TypeError):
            continue
        if not s or "$" in s:
            continue
        new = _PLATE_PCT_RE.sub("\u00a0", s)
        if new != s:
            art.set_text(new)
            bound += 1
    return bound


def plate_range_dash(fig) -> int:
    """LA REGLA sobre TODO el texto que la lámina dibuja. Devuelve cuántos intervalos convirtió.

    El eje se toca ENVOLVIENDO su formateador y no reescribiendo una lista de rótulos: `set_ticklabels` no
    guarda los rótulos categóricos en un `FixedFormatter`, sino en un `FuncFormatter` construido sobre un
    diccionario posición → texto, de modo que no hay lista que reescribir. Se envuelve SÓLO el eje en el que
    algún rótulo cambia —es decir, un eje categórico—, y así el formateador de idioma de los ejes numéricos
    queda intacto. Los encartes (`inset_axes`) no están en `fig.axes`: se recorren sus `child_axes`, o sus
    marcas se quedarían fuera. Todo lo demás —títulos de panel y de lámina, rótulos de eje, entradas y
    títulos de leyenda, notas, anotaciones y textos de figura— se recorre con `findobj`, que es lo único que
    no deja fuera un artista nuevo el día que un módulo añada uno. El modo matemático (`$…$`) se salta: ahí
    el guion ya se compone como menos a la altura del eje matemático."""
    from matplotlib.text import Text
    from matplotlib.ticker import FuncFormatter
    # Se dibuja SÓLO si hace falta. Las marcas de eje no existen como texto hasta el primer dibujado, pero
    # un `draw()` de más sobre una figura ya al día vuelve a resolver `constrained_layout` y mueve leyendas
    # que el módulo ya había colocado: con la regla enganchada al motor, ese dibujado de cortesía cambiaba
    # láminas en las que no había ni un guion que convertir.
    if getattr(fig, "stale", True):
        try:
            fig.canvas.draw()
        except Exception:  # noqa: BLE001 - una figura sin lienzo no impide aplicar la regla al resto
            pass
    changed = 0
    axes, i = list(fig.axes), 0
    while i < len(axes):
        axes.extend(a for a in getattr(axes[i], "child_axes", []) if a not in axes)
        i += 1
    ticks: set[int] = set()
    for ax in axes:
        for axis in (ax.xaxis, ax.yaxis):
            try:
                labels = list(axis.get_ticklabels(which="both"))
            except (AttributeError, ValueError, RuntimeError, TypeError):
                continue
            ticks.update(id(t) for t in labels)
            n = sum(count_hyphen_ranges(t.get_text()) for t in labels if "$" not in t.get_text())
            if not n:
                continue
            for get, put in ((axis.get_major_formatter, axis.set_major_formatter),
                             (axis.get_minor_formatter, axis.set_minor_formatter)):
                try:
                    old = get()
                except (AttributeError, ValueError, RuntimeError, TypeError):
                    continue
                if old is None or getattr(old, "_range_dash_wrapped", False):
                    continue
                new = FuncFormatter(lambda v, p, _f=old: range_dash(_f(v, p)))
                new._range_dash_wrapped = True
                put(new)
            changed += n
    for art in fig.findobj(Text):
        if id(art) in ticks:
            continue
        try:
            if not art.get_visible():
                continue
            s = art.get_text()
        except (AttributeError, ValueError, RuntimeError, TypeError):
            continue
        if not s or "$" in s:
            continue
        n = count_hyphen_ranges(s)
        if n:
            art.set_text(range_dash(s))
            changed += n
    if changed:
        try:
            fig.canvas.draw()
        except Exception:  # noqa: BLE001
            pass
    return changed


def fmt_ci(lo, hi, dec=1, lang="es"):
    sep = " a " if lang == "es" else " to "
    return f"{fmt_number(lo, dec, lang)}{sep}{fmt_number(hi, dec, lang)}"


def fmt_p(p, lang="es"):
    if p is None or (isinstance(p, float) and np.isnan(p)):
        return "n/d" if lang == "es" else "n/a"
    if p < 0.001:
        return "< 0,001" if lang == "es" else "< 0.001"
    return fmt_number(p, 3, lang)


# ---------------------------------------------------------------------------
# LA GLOSA DEL PANEL FIJO DE 65 HOSPITALES (fase 4k, tarea K1)
# ---------------------------------------------------------------------------
#: EL MISMO PANEL SE DEFINÍA DE DOS MANERAS. La lectura independiente de la compilación del 2026-09-08
#: encontró las dos definiciones a una página de distancia —apéndice inglés p. 361 (Tabla S62) «present in
#: 2019–2022» contra p. 362 (Tabla S64) «present in every year 2019–2024»— y otra vez dentro del artículo
#: (p. 18 contra p. 49). Contadas sobre el DOCX de la compilación: 37 apariciones del enunciado viejo
#: contra 16 del nuevo por manuscrito largo, 35 contra 15 por apéndice suelto y 2 contra 1 por artículo.
#:
#: EL HECHO ESTÁ ESTABLECIDO Y NO SE VUELVE A DERIVAR (outputs/tidy/grd_hospital_year.csv, verificado en
#: las tres variantes): los hospitales que reportan son 65, 65, 65, 65, 68 y 72 en 2019 a 2024; el conjunto
#: presente en LOS SEIS años tiene exactamente 65 miembros; el conjunto presente en 2019–2022 tiene
#: exactamente 65 miembros; y LOS DOS CONJUNTOS SON EL MISMO, sin un solo hospital de los cuatro primeros
#: años que falte después. Los dos enunciados describen, pues, los mismos hospitales. No hay nada que
#: decidir sobre el fondo y sí sobre la redacción: «presentes en 2019–2022» deja al lector preguntándose si
#: esos hospitales reportaron también en 2023 y en 2024, y el otro no.
#:
#: LA GLOSA DEL ESTUDIO, escrita UNA vez y aquí:
#:
#:     «hospitales que reportan en todos los años 2019–2024» / «hospitals reporting in every year 2019–2024»
#:
#: y de aquí la leen TODOS los módulos que la imprimen —09a (Tablas 1 y 2), 09b (ST1), 11 (E1–E12), 13
#: (EF1–EF10), 16 (E60–E68), 06 (S3) y 07 (tabla de controles del artículo)—, de modo que ninguno vuelve a
#: escribir su propia versión y arreglarla en uno no puede dejarla rota en otro.
#:
#: LO QUE NO ES LA GLOSA, Y NO SE TOCA. La REGLA DE CONSTRUCCIÓN —«intersección de los COD_HOSPITAL
#: presentes en 2019, 2020, 2021 y 2022, verificada como subconjunto de 2023 y de 2024»— nombra 2019–2022
#: con toda exactitud, porque describe CÓMO se obtiene el conjunto y no QUIÉNES lo forman. Vive en
#: `01_grd_core.py` (donde se calcula) y aquí como forma `construction`, y las dos frases se imprimen
#: juntas en la forma `full`: la que dice quiénes son primero, la que dice cómo se obtuvieron después.
#: El panel OBSERVADO —«65 (2019–2022), 68 (2023) y 72 (2024)»— tampoco es esta glosa: enumera cuántos
#: hospitales reporta cada año y es exacto tal cual.
FIXED_PANEL_N = 65

#: Las siete formas en que el corpus necesita decir la misma cosa. Se piden por nombre, nunca se copian.
_FIXED_PANEL_FORMS = {
    "clause": {"es": "que reportan en todos los años 2019–2024",
               "en": "reporting in every year 2019–2024"},
    "membership": {"es": "hospitales que reportan en todos los años 2019–2024",
                   "en": "hospitals reporting in every year 2019–2024"},
    "construction": {"es": "que se obtienen como la intersección de 2019, 2020, 2021 y 2022 y se verifican "
                           "como subconjunto de 2023 y de 2024",
                     "en": "obtained as the intersection of 2019, 2020, 2021 and 2022 and verified as a "
                           "subset of 2023 and of 2024"},
}


def fixed_panel_gloss(lang: str, form: str = "membership", n: int = FIXED_PANEL_N) -> str:
    """La glosa ÚNICA del panel fijo, en la forma que pide quien la imprime.

    `clause`        «que reportan en todos los años 2019–2024» — se pega detrás de un sustantivo ya dicho.
    `membership`    «hospitales que reportan en todos los años 2019–2024» — la glosa desnuda.
    `paren`         «(que reportan en todos los años 2019–2024)» — detrás de «panel fijo de 65».
    `named`         «panel fijo de 65 hospitales que reportan en todos los años 2019–2024».
    `definition`    «panel fijo de 65 = hospitales que reportan en todos los años 2019–2024».
    `construction`  la REGLA DE CONSTRUCCIÓN sola (nombra 2019–2022 con exactitud; no es la glosa).
    `full`          la glosa y, detrás, la regla de construcción.
    """
    if lang not in ("es", "en"):
        raise KeyError(f"idioma desconocido: {lang!r}")
    clause = _FIXED_PANEL_FORMS["clause"][lang]
    member = _FIXED_PANEL_FORMS["membership"][lang]
    build = _FIXED_PANEL_FORMS["construction"][lang]
    if form in ("clause", "membership", "construction"):
        return _FIXED_PANEL_FORMS[form][lang]
    if form == "paren":
        return f"({clause})"
    if form == "named":
        return (f"panel fijo de {n} {member}" if lang == "es" else f"fixed panel of {n} {member}")
    if form == "definition":
        return (f"panel fijo de {n} = {member}" if lang == "es" else f"fixed panel of {n} = {member}")
    if form == "full":
        return f"{member}, {build}" if lang == "es" else f"{member}, {build}"
    raise KeyError(f"forma desconocida de la glosa del panel fijo: {form!r}")


#: EL DETECTOR con el que se prueba que las dos glosas no vuelven a convivir (tests/test_fixed_panel_gloss.py).
#: Busca hacia ADELANTE desde cada mención del panel fijo, dentro de la misma frase, el verbo de PERTENENCIA
#: —presente/presentes, present, que reportan, reporting, report— y la ventana de años que lo acompaña, y
#: devuelve esa ventana. Mira sólo hacia adelante y sólo hasta el primer punto, punto y coma o barra
#: vertical, de modo que la enumeración del panel OBSERVADO que suele ir delante («65 (2019–2022), 68
#: (2023) y 72 (2024); panel fijo de 65 = …») no se le cuela, y la regla de construcción que va detrás de la
#: glosa tampoco, porque la ventana que encuentra primero es la de la glosa.
_FIXED_PANEL_MENTION = re.compile(r"panel fijo|fixed[\s -]panel", re.IGNORECASE)
_FIXED_PANEL_WINDOW = re.compile(
    r"(?:presentes?|present|que\s+reportan|reportan|reporting|report)\s+"
    r"(?:in\s+every\s+year\s+|en\s+todos\s+los\s+a[nñ]os\s+|en\s+|in\s+)"
    r"(\d{4}\s*[–-]\s*\d{4}|\d{4}(?:\s*,\s*\d{4})+\s*(?:y|and)\s*\d{4})", re.IGNORECASE)
#: La APOSICIÓN sin verbo, que dice lo mismo en tres palabras: «panel fijo 2019–2022», «the 2019–2022 fixed
#: panel». La ventana ha de tocar la mención —delante o detrás— sin nada en medio, para que la enumeración
#: del panel observado que va unida por «y»/«and» no se cuente como glosa.
_FIXED_PANEL_APPOS_AFTER = re.compile(r"^\s*(?:de\s+\d+\s+)?(\d{4}\s*[–-]\s*\d{4})\b")
_FIXED_PANEL_APPOS_BEFORE = re.compile(r"(\d{4}\s*[–-]\s*\d{4})\s+$")


def fixed_panel_membership_windows(text) -> list[str]:
    """Las ventanas de años con las que un texto dice QUIÉNES forman el panel fijo.

    Devuelve una lista de cadenas «AAAA–AAAA» normalizadas con raya corta, una por enunciado encontrado.
    Un texto que no habla del panel fijo devuelve la lista vacía."""
    if not isinstance(text, str) or not text:
        return []
    out = []
    for m in _FIXED_PANEL_MENTION.finditer(text):
        tail = text[m.end():]
        cut = min((i for i in (tail.find("."), tail.find(";"), tail.find("|"), tail.find("\n")) if i >= 0),
                  default=len(tail))
        for w in _FIXED_PANEL_WINDOW.finditer(tail[:cut]):
            years = re.findall(r"\d{4}", w.group(1))
            out.append(f"{years[0]}–{years[-1]}")
        for rx, where in ((_FIXED_PANEL_APPOS_AFTER, tail[:cut]), (_FIXED_PANEL_APPOS_BEFORE, text[:m.start()])):
            a = rx.search(where)
            if a:
                years = re.findall(r"\d{4}", a.group(1))
                out.append(f"{years[0]}–{years[-1]}")
    return out


# ---------------------------------------------------------------------------
# Nota de la tabla de controles en versión breve (una sola fuente para las TRES puntas)
# ---------------------------------------------------------------------------
#: La tabla de controles se imprime en dos tamaños —la larga, una fila por control indicador-año, y la
#: breve, una fila por familia— y comparte una sola nota. Contar «las filas de la tabla» en esa nota
#: compartida escribía en la breve el recuento de la larga. La cláusula se reconstruye AQUÍ, desde el
#: archivo que se está imprimiendo, y de aquí la leen las tres puntas que la necesitan: el módulo que
#: escribe titles.json (07_controls), y prose_en/prose_es al imprimir la tabla. Cuando las tres llaman a
#: la misma función, arreglarlo en una no puede dejarlo roto en otra —que es lo que pasó en la ronda 1,
#: cuando la cláusula quedó corregida al imprimir y la frase de cabecera guardada siguió diciendo lo
#: contrario dos oraciones más arriba.
#: La cláusula de filas tiene DOS formas y las dos se reconocen: la antigua y breve que escribía el módulo
#: («Rows: 205 (191 match, 14 differ, all explained).», contada sobre la tabla LARGA y heredada por la
#: breve) y la corregida, que separa las tres clases de fila y cierra nombrando la tabla completa. Que la
#: expresión reconozca la antigua es lo que permite a `prose_*.table_note` rescatar una nota vieja; que
#: reconozca la corregida es lo que hace que ese rescate sea un no-op cuando el módulo ya la escribió bien.
_CONTROLS_ROWS_ENDER = {"en": r"(?:\([^)]*\)\.|[^\n]*?\blists one per year\.)",
                        "es": r"(?:\([^)]*\)\.|[^\n]*?\blista uno por año\.)"}
CONTROLS_ROWS_CLAUSE_RE = {"en": re.compile(r"Rows:\s*(\d[\d,]*)\s*" + _CONTROLS_ROWS_ENDER["en"]),
                           "es": re.compile(r"Filas:\s*(\d[\d.]*)\s*" + _CONTROLS_ROWS_ENDER["es"])}
_CONTROLS_STATUS_FRACTION_RE = re.compile(r"\s*(\d+)\s*/\s*(\d+)")

#: Las dos etiquetas que puede llevar una fila de la tabla breve en su columna de indicador
#: (07_controls::LABELS). La que no lleva ninguna viene de una familia de control preespecificada. Son
#: TRES clases, no dos.
CONTROLS_ROW_CLASS_LABELS = {"check": ("(check row)", "(fila de comprobación)"),
                             "module": ("(module control;", "(control del módulo;")}


def controls_compact_counts(df) -> dict:
    """Lee la columna de estado de la tabla breve de controles («6/6 …», «4/6 …; …») y devuelve lo que hay:
    familias impresas, familias con todos sus años coincidentes, controles indicador-año que resumen y
    cuántos de ellos coinciden. Cada número de la cláusula es así rastreable hasta el archivo impreso.

    Separa además las filas en las TRES clases que el propio archivo rotula —familia de control,
    «(fila de comprobación)» y «(control del módulo; …)»—, de modo que la taxonomía de la nota se lee de
    la tabla en vez de afirmarse."""
    fractions = [_CONTROLS_STATUS_FRACTION_RE.match(str(v)) for v in df[df.columns[6]]]
    if not fractions or not all(fractions):
        raise ValueError("T8_controls_compact: the status column no longer reads 'matched/total'")
    matched = sum(int(m.group(1)) for m in fractions)
    total = sum(int(m.group(2)) for m in fractions)
    full = sum(1 for m in fractions if m.group(1) == m.group(2))
    indicator = [str(v) for v in df[df.columns[1]]]
    check = sum(1 for v in indicator if any(t in v for t in CONTROLS_ROW_CLASS_LABELS["check"]))
    module = sum(1 for v in indicator if any(t in v for t in CONTROLS_ROW_CLASS_LABELS["module"]))
    return dict(rows=len(df), full=full, partial=len(df) - full, controls=total, matched=matched,
                differ=total - matched, check=check, module=module,
                family=len(df) - check - module)


def controls_family_row_counts() -> list[int]:
    """Cuántas FILAS imprime en la tabla breve cada familia preespecificada de `config.CONTROLS`.

    Casi todas imprimen una. La que guarda una TUPLA por año imprime una fila por elemento de la tupla:
    la clasificación de riesgo del A03 2023–2024 guarda `(bajo, medio, alto)` y por eso imprime tres, una
    por banda. De aquí sale —contada, no afirmada— la diferencia entre las familias preespecificadas y las
    filas de familia que el lector cuenta en la tabla."""
    filas = []
    for valor in CFG.CONTROLS.values():
        anchos = {len(v) for v in valor.values() if isinstance(v, tuple)} if isinstance(valor, dict) else set()
        filas.append(max(anchos) if anchos else 1)
    return filas


def controls_compact_clause(df, lang: str) -> str:
    """La cláusula «Filas: …» / «Rows: …» de la nota de la tabla breve, contada sobre ESA tabla.

    LA CUENTA TIENE QUE CUADRAR A LA VISTA (defecto F4-2 de la fase 4f). La misma nota decía, tres
    oraciones antes, que el protocolo tiene 40 familias de control, y aquí contaba 42 filas «una por
    familia de control»: dos números que no pueden ser los dos ciertos si cada familia imprime una fila.
    Lo son porque una familia —la clasificación de riesgo del A03 2023–2024— imprime TRES filas, una por
    banda, y 39 + 3 = 42. La cláusula lo dice ahora con esas palabras y deja las tres sumas escritas
    (48 = 42 + 2 + 4, 42 + 6 = 48, 191 + 14 = 205), de modo que el lector puede comprobarlas sin salir de
    la nota. Las familias se cuentan de `config.CONTROLS` y las filas de la tabla impresa: si un día
    dejaran de cuadrar, la redacción cae sola en la forma general y no afirma un reparto que no existe."""
    c = controls_compact_counts(df)
    f = lambda x: fmt_number(x, 0, lang)  # noqa: E731
    por_familia = controls_family_row_counts()
    n_fam = len(por_familia)
    varias = [x for x in por_familia if x > 1]
    # ¿La tabla impresa se explica exactamente por el reparto de config.CONTROLS?
    cuadra = sum(por_familia) == c["family"] and len(varias) == 1
    if lang == "es":
        if cuadra:
            origen = (f"Las {f(n_fam)} familias de control preespecificadas imprimen {f(c['family'])} filas, "
                      f"porque {f(n_fam - 1)} de ellas imprimen una fila cada una y una imprime tres, una por "
                      f"banda de riesgo ({f(n_fam - 1)} + {f(varias[0])} = {f(c['family'])}); las "
                      f"{f(c['check'] + c['module'])} filas restantes no son familias de control: ")
        elif c["family"] == n_fam:
            origen = (f"Las {f(n_fam)} familias de control preespecificadas imprimen una fila cada una; las "
                      f"{f(c['check'] + c['module'])} filas restantes no son familias de control: ")
        else:
            origen = (f"Las {f(n_fam)} familias de control preespecificadas imprimen {f(c['family'])} filas, "
                      f"porque algunas imprimen una fila por banda en vez de una sola; las "
                      f"{f(c['check'] + c['module'])} filas restantes no son familias de control: ")
        return (f"Filas: {f(c['rows'])} = {f(c['family'])} + {f(c['check'])} + {f(c['module'])}. {origen}"
                f"{f(c['check'])} están rotuladas «fila de comprobación» y {f(c['module'])} «control del "
                f"módulo» (el valor esperado no está en el protocolo). Por resultado, de las {f(c['rows'])} "
                f"filas {f(c['full'])} tienen todos sus años coincidentes y {f(c['partial'])} al menos una "
                f"diferencia documentada ({f(c['full'])} + {f(c['partial'])} = {f(c['rows'])}); en conjunto "
                f"resumen {f(c['controls'])} controles indicador-año, de los cuales {f(c['matched'])} coinciden y "
                f"{f(c['differ'])} difieren ({f(c['matched'])} + {f(c['differ'])} = {f(c['controls'])}), todos "
                f"explicados, y que la tabla completa de controles lista uno por año.")
    if cuadra:
        origen = (f"The {f(n_fam)} pre-specified control families print {f(c['family'])} rows, because "
                  f"{f(n_fam - 1)} of them print one row each and one prints three, one per risk band "
                  f"({f(n_fam - 1)} + {f(varias[0])} = {f(c['family'])}); the remaining "
                  f"{f(c['check'] + c['module'])} rows are not control families: ")
    elif c["family"] == n_fam:
        origen = (f"The {f(n_fam)} pre-specified control families print one row each; the remaining "
                  f"{f(c['check'] + c['module'])} rows are not control families: ")
    else:
        origen = (f"The {f(n_fam)} pre-specified control families print {f(c['family'])} rows, because some "
                  f"print one row per band instead of a single row; the remaining "
                  f"{f(c['check'] + c['module'])} rows are not control families: ")
    return (f"Rows: {f(c['rows'])} = {f(c['family'])} + {f(c['check'])} + {f(c['module'])}. {origen}"
            f"{f(c['check'])} are labelled 'check row' and {f(c['module'])} 'module control' (the expected "
            f"value is not in the protocol). By result, of the {f(c['rows'])} rows {f(c['full'])} have every "
            f"year matching and {f(c['partial'])} at least one documented difference "
            f"({f(c['full'])} + {f(c['partial'])} = {f(c['rows'])}); together they summarise "
            f"{f(c['controls'])} indicator-year controls, of which {f(c['matched'])} match and "
            f"{f(c['differ'])} differ ({f(c['matched'])} + {f(c['differ'])} = {f(c['controls'])}), all "
            f"explained, and which the full controls table lists one per year.")


def controls_compact_lead(lang: str) -> str:
    """Frase de cabecera de la nota de la tabla breve.

    NO puede decir «una fila por familia de control»: seis de las 48 filas no son familias, y la propia
    nota lo dice dos oraciones más abajo. Remite al recuento del final, que es el que cuenta las tres
    clases sobre el archivo impreso."""
    if lang == "es":
        return ("Las filas son de tres clases, contadas al final de esta nota; los valores por año se "
                "listan en orden cronológico separados por «/». ")
    return ("Rows are of three classes, counted at the end of this note; yearly values are listed "
            "chronologically separated by '/'. ")


#: Lo que la cabecera de esa nota NO puede afirmar cuando la tabla lleva filas que no son familias de
#: control. Guarda del defecto IC-3: la frase «una fila por familia de control» como afirmación absoluta.
CONTROLS_LEAD_FORBIDDEN = {"en": ("one row per control family",),
                           "es": ("una fila por familia de control",)}


# ---------------------------------------------------------------------------
# Estilo de láminas (idéntico al manuscrito paper/)
# ---------------------------------------------------------------------------
OKABE = ["#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00", "#56B4E9", "#F0E442", "#000000"]
RED, BLUE, GREY = "#c0392b", "#2471a3", "#7f8c8d"


def style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns
    sns.set_theme(style="whitegrid", context="paper")
    plt.rcParams.update({
        "figure.dpi": 100, "savefig.dpi": 600, "savefig.facecolor": "white", "figure.facecolor": "white",
        "font.family": "DejaVu Sans", "font.size": 10.5,
        "axes.titlesize": 12.5, "axes.titleweight": "bold", "axes.labelsize": 11,
        "xtick.labelsize": 9.5, "ytick.labelsize": 9.5, "legend.fontsize": 8.5, "legend.frameon": False,
        "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True, "grid.alpha": .35,
        "axes.edgecolor": "#333333", "axes.linewidth": .9,
    })
    return plt, sns


def letter(ax, ch, dx=-0.09, dy=1.12):
    ax.text(dx, dy, ch, transform=ax.transAxes, fontsize=18, fontweight="bold", va="top", ha="right", family="DejaVu Sans")


def shade_years(ax, years, color="grey", alpha=0.12):
    for x in years:
        ax.axvspan(x - 0.5, x + 0.5, color=color, alpha=alpha, zorder=0)


# ---------------------------------------------------------------------------
# Norma de lámina vertical (180 × 245 mm, 3 filas × 2 columnas, 1:1 a 600 ppp)
# ---------------------------------------------------------------------------
# Estas tres utilidades resuelven el defecto que más veces se repetía en las láminas: el título de panel
# se ancla al borde izquierdo de SUS EJES, que en una celda estrecha empieza muy a la derecha cuando las
# etiquetas del eje Y son largas, de modo que el título se sale de la celda y se corta contra el borde
# del lienzo. Ancladas a la CELDA de la rejilla —cuya geometría es fija— las tres columnas de títulos
# quedan alineadas y ningún título invade la celda vecina ni se pierde contra el margen.
PLATE_CELL_MARGIN = 2.0 / 180.0        # margen izquierdo de la celda, en fracción de figura (2 mm)
_PLATE_MEASURE_FIG = None


def plate_text_width_pt(s: str, fontsize: float = 9.0, weight: str = "bold") -> float:
    """Ancho tipográfico real de una cadena, en puntos, medido con la fuente con la que se dibujará."""
    global _PLATE_MEASURE_FIG
    import matplotlib.pyplot as plt
    from matplotlib.font_manager import FontProperties
    if _PLATE_MEASURE_FIG is None:
        _PLATE_MEASURE_FIG = plt.figure(figsize=(1, 1))
    fig = _PLATE_MEASURE_FIG
    w, _h, _d = fig.canvas.get_renderer().get_text_width_height_descent(
        str(s), FontProperties(size=fontsize, weight=weight), False)
    return w * 72.0 / fig.dpi


def plate_wrap(text: str, max_pt: float, fontsize: float = 9.0, weight: str = "bold") -> str:
    """Ajuste de línea por ancho MEDIDO, no por número de caracteres.

    El español es ~15 % más largo que el inglés y las palabras del registro son largas: contar caracteres
    deja títulos que se salen de la celda en un idioma y cortos en el otro."""
    words, lines, cur = str(text).split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if cur and plate_text_width_pt(trial, fontsize, weight) > max_pt:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return "\n".join(lines) if lines else str(text)


def plate_annotate_no_overlap(ax, xs, ys, labels, fontsize=6.2, color="#222222", state=None, bbox=None) -> list:
    """Rotula puntos dispersos evitando que un rótulo caiga sobre otro ya colocado.

    Para cada punto se prueban desplazamientos candidatos (en puntos tipográficos) y se elige el primero cuyo
    rectángulo estimado no se solape con los rótulos ya dibujados ni salga del área de ejes; si ninguno queda libre
    se usa el de menor solapamiento, con una línea guía hasta su punto. Ningún rótulo se omite.
    """
    fig = ax.figure
    fig.canvas.draw()                       # fija la geometría antes de medir en coordenadas de pantalla
    scale = fig.dpi / 72.0
    ext = ax.get_window_extent()
    x0, x1, y0, y1 = ext.x0, ext.x1, ext.y0, ext.y1
    candidates = [(4, 3), (-4, 3), (4, -9), (-4, -9), (4, 11), (-4, 11), (4, -17), (-4, -17),
                  (0, 15), (0, -23), (14, 19), (-14, 19), (14, -27), (-14, -27), (26, 5), (-26, 5)]
    # `state` permite encadenar varias llamadas sobre el mismo panel (una por serie, con su color): los
    # rótulos de la segunda serie esquivan también los que ya colocó la primera.
    placed: list = [] if state is None else state
    order = np.argsort(-np.asarray(ys, dtype=float))
    for i in order:
        txt = str(labels[i])
        if not txt:
            continue
        px, py = ax.transData.transform((float(xs[i]), float(ys[i])))
        # el ancho de un dígito de DejaVu Sans es ~0,64 em: con 0,58 el rectángulo estimado se quedaba corto
        # y dos rótulos contiguos («1.854» y «1.919») se daban por separados y se imprimían pegados
        w = 0.64 * fontsize * len(txt) * scale + 2.0 * scale
        hgt = 1.35 * fontsize * scale
        best, best_cost = None, np.inf
        for dx, dy in candidates:
            axr = px + dx * scale
            bx0, bx1 = (axr, axr + w) if dx >= 0 else (axr - w, axr)
            ayr = py + dy * scale
            by0, by1 = (ayr, ayr + hgt) if dy >= 0 else (ayr - hgt, ayr)
            out = (max(0.0, x0 - bx0) + max(0.0, bx1 - x1) + max(0.0, y0 - by0) + max(0.0, by1 - y1)) * 1e3
            over = sum(max(0.0, min(bx1, q[2]) - max(bx0, q[0])) * max(0.0, min(by1, q[3]) - max(by0, q[1]))
                       for q in placed)
            cost = out + over
            if cost < best_cost:
                best, best_cost = (dx, dy, bx0, by0, bx1, by1), cost
            if cost == 0:
                break
        dx, dy, bx0, by0, bx1, by1 = best
        far = abs(dx) > 10 or abs(dy) > 17
        ann = ax.annotate(txt, (float(xs[i]), float(ys[i])), fontsize=fontsize, color=color,
                          xytext=(dx, dy), textcoords="offset points", zorder=6,
                          ha="left" if dx >= 0 else "right", va="bottom" if dy >= 0 else "top",
                          bbox=bbox,
                          arrowprops=dict(arrowstyle="-", lw=0.5, color="#999999",
                                          shrinkA=0.0, shrinkB=2.0) if far else None)
        # Este colocador ya resolvió el solape Y dibujó la línea guía cuando el rótulo quedó lejos de su
        # punto. Si el motor general lo volviera a mover, el rótulo se alejaría del punto SIN línea y el
        # lector dejaría de saber a qué marcador pertenece; se marca para que el motor no lo toque.
        ann.set_gid(PLATE_KEEP)
        placed.append((bx0, by0, bx1, by1))
    return placed


# Rutas de archivo fuera de la leyenda del lector -----------------------------------------------------
# La leyenda de una lámina la lee quien lee el artículo, no quien reproduce el pipeline: la frase «Fuente:
# outputs/tidy/….csv» no le dice nada y ocupa dos líneas. La procedencia de cada lámina sigue publicada, y
# con más detalle, en el mapa del pipeline y en el inventario de activos del material suplementario.
_SOURCE_PATH_SENTENCE = re.compile(
    r"(?:Source files|Source|Archivos fuente|Fuentes|Fuente)\s*:"
    r"[^.]*(?:\.(?:csv|shp|dbf|pdf|xlsx|xls|json|md|py|zip|txt)\b[^.]*)*\.\s*")


def strip_source_paths(text: str) -> str:
    """Quita de una leyenda la frase «Fuente/Source: <rutas>.» dejando el resto intacto."""
    return _SOURCE_PATH_SENTENCE.sub("", str(text)).replace("  ", " ").strip()


def strip_caption_paths(captions: dict) -> dict:
    """Aplica `strip_source_paths` al campo `caption` de un diccionario {clave: {title, caption}}."""
    out = {}
    for key, meta in captions.items():
        if isinstance(meta, dict) and "caption" in meta:
            meta = dict(meta)
            meta["caption"] = strip_source_paths(meta["caption"])
        out[key] = meta
    return out


def _plate_cell_bounds(fig, spec) -> tuple:
    """Bordes izquierdo y derecho, en fracción de figura, de la celda de rejilla que ocupa `spec`."""
    gs = spec.get_gridspec()
    parent = getattr(gs, "_subplot_spec", None)
    x0, x1 = _plate_cell_bounds(fig, parent) if parent is not None else (0.0, 1.0)
    n = gs.ncols
    return (x0 + (x1 - x0) * spec.colspan.start / n, x0 + (x1 - x0) * spec.colspan.stop / n)


PLATE_NOTE_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.92, pad=1.4)


def plate_frame_notes(fig, max_frac: float = 1.0) -> None:
    """Da recuadro blanco translúcido a las notas del panel y las pliega al ancho de sus ejes.

    Dos defectos se repetían en casi todas las láminas: una nota escrita en coordenadas del eje se imprimía
    ENCIMA de las barras o de la serie (sin fondo, el texto y el dato se confunden), y una nota más ancha que
    su panel se cortaba contra el borde del lienzo, porque el texto no se recorta ni se pliega solo. Aquí se
    resuelven los dos a la vez, justo antes de guardar: el recuadro deja ver el dato bajo la nota y el
    plegado por ancho medido la mantiene dentro de su celda.

    Los rótulos dibujados en coordenadas de DATO (los valores sobre un punto, el texto de una celda de mapa
    de calor) se dejan intactos: su sitio lo fija el dato, no el panel.
    """
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for ax in fig.axes:
        try:
            w_ax = ax.get_window_extent().width
        except (AttributeError, ValueError):
            continue
        if w_ax <= 0:
            continue
        for t in list(ax.texts):
            if t.get_transform() is ax.transData:
                continue
            texto = t.get_text()
            if not str(texto).strip():
                continue
            if t.get_bbox_patch() is None:
                t.set_bbox(dict(PLATE_NOTE_BBOX))
            try:
                ancho = t.get_window_extent(r).width
            except (AttributeError, ValueError):
                continue
            if ancho > w_ax * max_frac:
                objetivo = w_ax * max_frac * 72.0 / fig.dpi
                t.set_text("\n".join(plate_wrap(line, objetivo, t.get_size(), "normal")
                                     for line in str(texto).split("\n")))


def plate_align_titles(fig, margin: float = PLATE_CELL_MARGIN) -> None:
    """Ancla el título de cada panel al borde izquierdo de SU celda y congela la composición.

    Debe llamarse justo antes de guardar: deja el motor de composición en «none» para que el dibujo del
    archivo no vuelva a mover los ejes bajo unos títulos ya anclados."""
    fig.canvas.draw()
    fig.set_layout_engine("none")
    fig.canvas.draw()
    for ax in fig.axes:
        spec = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
        pos = ax.get_position()
        if spec is None or pos.width <= 0 or pos.height <= 0:
            continue
        t = next((c for c in (getattr(ax, "_left_title", None), ax.title) if c is not None and c.get_text()), None)
        if t is None:
            continue
        x_cell = (_plate_cell_bounds(fig, spec)[0] + margin - pos.x0) / pos.width
        t.set_ha("left")
        t.set_x(x_cell)


# ===========================================================================
# Modo revista de láminas (LANCET_PLATE_JOURNAL)
# ---------------------------------------------------------------------------
# APAGADO POR OMISIÓN: sin la variable de entorno nada de esta sección se ejecuta y cada módulo
# reconstruye el corpus byte a byte (`journal_redirect` es la identidad, `journal_plate_export` devuelve
# la misma ruta y no toca la figura).
#
# Encendido (`LANCET_PLATE_JOURNAL=1`, o el nombre de la variante que se envía; por omisión `sin_rett`),
# la MISMA lámina se guarda en la forma que pide la revista (Lancet Regional Health – Americas):
#   · solo la letra minúscula del panel, «(a)», y ningún título dentro del gráfico: el título de cada
#     panel pasa a la leyenda (captions.json y panel_titles.json de la carpeta de la revista);
#   · sin distintivo de variante en la lámina (la variante se declara en la leyenda);
#   · en inglés, la convención numérica de la revista en el propio dibujo: punto decimal a media altura
#     («23·4») y «100 000» en vez de «100,000» (los códigos, fechas, DOI y versiones quedan protegidos);
#   · mismo lienzo de 180 × 245 mm a 600 ppp (la revista pide 300 ppp y 107 mm como mínimo) y las mismas
#     proyecciones de área fiel de los mapas.
# En este modo el CORPUS NO RECIBE NINGUNA ESCRITURA: las láminas de la variante que se envía van a
# <variante>/<idioma>/journal/figures/, los registros de control a controls/journal/, y todo lo demás
# (tablas, tidy, láminas de la otra variante) a un borrador fuera de outputs/ (`journal_scratch_dir`).
# El registro de láminas (`supplementary_material._plate_stems`) mira solo figures/ y extra/figures/, de
# modo que la carpeta de la revista le es invisible.
# ===========================================================================
PLATE_JOURNAL_ENV = "LANCET_PLATE_JOURNAL"
PLATE_JOURNAL_DEFAULT_VARIANT = "sin_rett"
PLATE_JOURNAL_SUBDIR = "journal"
JOURNAL_MID_DOT = "·"          # U+00B7 MIDDLE DOT — el punto decimal a media altura de la revista
JOURNAL_THIN_SPACE = " "       # U+202F NARROW NO-BREAK SPACE — «100 000»
_JOURNAL_PANELS: dict = {}          # (variante, idioma) -> {lámina: registro de títulos retirados}
_JOURNAL_LETTER_RE = re.compile(r"^\(([a-f])\)(?:\s+(.*))?$", re.S)
_JOURNAL_BARE_LETTER_RE = re.compile(r"^\(?([a-f])\)?$")
_JOURNAL_STAMP_RE = re.compile(
    r"^(?:F84 )?(?:with|without|sin|con) Rett$|^Full F84 \(with Rett\)$|^F84 completo \(con Rett\)$")


def plate_journal_mode() -> bool:
    """¿Está encendido el modo revista? Solo lo enciende la variable de entorno LANCET_PLATE_JOURNAL."""
    v = str(os.environ.get(PLATE_JOURNAL_ENV, "")).strip().lower()
    return v not in ("", "0", "off", "false", "no")


def plate_journal_variant() -> str:
    """Variante que se envía a la revista: el valor de la variable si nombra una variante, si no `sin_rett`."""
    v = str(os.environ.get(PLATE_JOURNAL_ENV, "")).strip()
    return v if v in tuple(CFG.VARIANTS) else PLATE_JOURNAL_DEFAULT_VARIANT


def journal_scratch_dir() -> Path:
    """Borrador FUERA de outputs/ para lo que un módulo escribe en modo revista y no es una lámina de la
    variante enviada ni un registro de control (tablas, tidy, láminas de la otra variante)."""
    return Path(tempfile.gettempdir()) / "lancet_americas_journal_scratch"


def journal_redirect(path) -> Path:
    """Ruta de escritura en modo revista; la identidad cuando el modo está apagado.

        outputs/<v>/<lang>/figures/…         -> outputs/<v>/<lang>/journal/figures/…   (v = variante enviada)
        outputs/<v>/<lang>/extra/figures/…   -> outputs/<v>/<lang>/journal/figures/…   (v = variante enviada)
        outputs/controls/<x>                 -> outputs/controls/journal/<x>
        cualquier otra ruta bajo outputs/    -> journal_scratch_dir()/<ruta relativa>
    Una ruta ya redirigida o fuera de outputs/ vuelve tal cual."""
    path = Path(path)
    if not plate_journal_mode():
        return path
    try:
        rel = path.resolve().relative_to(Path(CFG.OUT).resolve())
    except (ValueError, OSError):
        return path
    parts = rel.parts
    if not parts:
        return path
    variants, langs = tuple(CFG.VARIANTS), tuple(CFG.LANGUAGES)
    if parts[0] in variants and len(parts) >= 3 and parts[1] in langs:
        if parts[2] == PLATE_JOURNAL_SUBDIR:
            return path
        tail = None
        if parts[2] == "figures":
            tail = parts[3:]
        elif parts[2:4] == ("extra", "figures"):
            tail = parts[4:]
        if tail is not None and parts[0] == plate_journal_variant():
            return Path(CFG.OUT) / parts[0] / parts[1] / PLATE_JOURNAL_SUBDIR / "figures" / Path(*tail)
        return journal_scratch_dir() / rel
    if parts[0] == "controls":
        if len(parts) >= 2 and parts[1] == PLATE_JOURNAL_SUBDIR:
            return path
        return Path(CFG.OUT) / "controls" / PLATE_JOURNAL_SUBDIR / Path(*parts[1:])
    return journal_scratch_dir() / rel


def _journal_path_parts(path) -> tuple:
    """(variante, idioma, nombre sin extensión) leídos de la ruta de una lámina; None donde no se reconoce."""
    path = Path(path)
    parts = path.parts
    variants, langs = tuple(CFG.VARIANTS), tuple(CFG.LANGUAGES)
    for i in range(len(parts) - 1):
        if parts[i] in variants and parts[i + 1] in langs:
            return parts[i], parts[i + 1], path.stem
    return None, None, path.stem


def _journal_is_stamp(s: str) -> bool:
    """¿Es el texto, entero, un distintivo de variante («without Rett», «F84 sin Rett»…)?"""
    s = " ".join(str(s).split())
    if not s:
        return False
    if _JOURNAL_STAMP_RE.match(s):
        return True
    for v in CFG.VARIANTS.values():
        for key in ("short", "label"):
            if s in {" ".join(str(x).split()) for x in (v.get(key) or {}).values()}:
                return True
    return False


def _journal_letter_annotation(ax):
    """Letra de panel dibujada como texto suelto (módulos 13/14: `ax._panel_letter`; 08b: `C.letter`)."""
    lt = getattr(ax, "_panel_letter", None)
    cands = [lt] if lt is not None else list(ax.texts)
    for t in cands:
        if t is None or not t.get_visible():
            continue
        m = _JOURNAL_BARE_LETTER_RE.match(str(t.get_text()).strip())
        if m and (lt is not None or str(t.get_fontweight()) in ("bold", "heavy", "700", "800", "900")):
            return m.group(1)
    return None


#: Títulos de ENCARTE que la revista no admite dentro del gráfico y cuya leyenda ya nombra («(c) … inset: mean
#: depth of all episodes and of episodes with F84 by year»): se retiran en modo revista (lectores, segunda ronda).
JOURNAL_TITLES_TO_LEGEND = {"Mean depth", "Profundidad media"}


def journal_strip_titles(fig) -> dict:
    """Modo revista: deja en cada panel SOLO su letra y retira los títulos y el distintivo de variante.

    Devuelve {letra: título retirado} y lo deja en `fig._journal_panels` para la leyenda. Idempotente.
      · «(a) Título…» (06/08a/08b/08c/15/15b)  -> «(a)»;
      · título sin letra en un panel cuya letra es un texto suelto (13/14) -> un espacio (se conserva la
        altura de línea a la que está anclada la letra);
      · un título sin letra en unos ejes sin letra (rótulo de faceta, franja o encarte) SE CONSERVA y se
        anota en `fig._journal_kept_titles` para la auditoría;
      · `fig._suptitle` y los textos iguales a un distintivo de variante se retiran."""
    if getattr(fig, "_journal_panels", None) is None:
        fig._journal_panels = {}
        fig._journal_kept_titles = []
        fig._journal_removed = []
    panels = fig._journal_panels
    for ax in _pl_all_axes(fig):
        if not ax.get_visible():
            continue
        letter_ann = _journal_letter_annotation(ax)
        for t in (getattr(ax, "_left_title", None), ax.title, getattr(ax, "_right_title", None)):
            if t is None:
                continue
            text = str(t.get_text())
            if not text.strip():
                continue
            m = _JOURNAL_LETTER_RE.match(text.strip())
            if m:
                rest = " ".join((m.group(2) or "").split())
                if rest or m.group(1) not in panels:
                    panels[m.group(1)] = rest
                t.set_text(f"({m.group(1)})")
            elif letter_ann is not None:
                panels[letter_ann] = " ".join(text.split())
                # el título queda INVISIBLE, no vacío: la letra de panel de los módulos 13/14 se ancla midiendo la
                # caja del título (`anchor_panel_letters`), y con un blanco en su lugar caía sobre la marca «100»
                # del eje Y (lectores, segunda ronda: Figura S17). La caja se conserva y la letra queda donde
                # estaba en el corpus; el texto no llega al PNG.
                t.set_alpha(0.0)
            else:
                kept = " ".join(text.split())
                if kept in JOURNAL_TITLES_TO_LEGEND:
                    # un título de encarte cuyo contenido ya dice la leyenda («inset: mean depth…»): se retira
                    t.set_text("")
                    fig._journal_removed.append(kept)
                    continue
                # rótulo de faceta o de franja: se conserva, pero en peso normal, para que no se lea como título
                t.set_fontweight("normal")
                if kept not in fig._journal_kept_titles:
                    fig._journal_kept_titles.append(kept)
        for t in list(ax.texts):
            if t.get_visible() and _journal_is_stamp(t.get_text()):
                t.set_visible(False)
                fig._journal_removed.append(" ".join(str(t.get_text()).split()))
    for t in list(fig.texts):
        if t.get_visible() and _journal_is_stamp(t.get_text()):
            t.set_visible(False)
            fig._journal_removed.append(" ".join(str(t.get_text()).split()))
    st = getattr(fig, "_suptitle", None)
    if st is not None and str(st.get_text()).strip():
        fig._journal_removed.append(" ".join(str(st.get_text()).split()))
        st.set_text("")
    return panels


# Convención numérica de la revista en el DIBUJO (solo inglés): «23·4», «2334», «13 155», «100 000».
# Se protegen los códigos y todo lo que una máquina vuelve a leer: CIE-10 («F84.0», «J18.9»), códigos REM
# de ocho cifras, «P6…», «Law 21.545», versiones «1.2.3», DOI, URL, fechas ISO, nombres de archivo,
# claves «a:b:c», SHA-256 y el texto matemático de matplotlib («$…$», donde viven las potencias de diez).
_JOURNAL_PROTECT_RE = re.compile(
    r"https?://\S+|doi:\S+|\bSHA-256\b|\b\d{4}-\d{2}-\d{2}\b|\S+\.(?:csv|json|py|png|pdf|md|docx)\b"
    r"|\b[A-Z]\d{2}(?:\.\d{1,2})?\b|\b\d{8}\b|\bP6\d{6}\b|(?:Law|Ley) 21\.545|\bv?\d+(?:\.\d+){2,}\b|\bv\d+\.\d+\b"
    r"|\b[a-z_]+:[a-z_]+(?::[A-Za-z0-9_-]+)+\b|\$[^$]*\$")
_JOURNAL_THOUSANDS_RE = re.compile(r"(?<![\d.,])\d{1,3}(?:,\d{3})+(?![\d,])")
_JOURNAL_DECIMAL_RE = re.compile(r"(?<=\d)\.(?=\d)")


def journal_artwork_text(s):
    """Texto de lámina en inglés con la convención numérica de la revista; los códigos no se tocan."""
    if s is None:
        return s
    s = str(s)
    if not any(ch.isdigit() for ch in s):
        return s
    keep = []

    def _mask(m):
        keep.append(m.group(0))
        return f"\x00{len(keep) - 1}\x00"

    def _thousands(m):
        tok = m.group(0)
        digits = tok.replace(",", "")
        return digits if len(digits) == 4 else JOURNAL_THIN_SPACE.join(tok.split(","))

    masked = _JOURNAL_PROTECT_RE.sub(_mask, s)
    masked = _JOURNAL_THOUSANDS_RE.sub(_thousands, masked)
    masked = _JOURNAL_DECIMAL_RE.sub(JOURNAL_MID_DOT, masked)
    return re.sub(r"\x00(\d+)\x00", lambda m: keep[int(m.group(1))], masked)


_JOURNAL_FORMATTER_CLASS = None


def _journal_tick_formatter_class():
    """Formateador de marcas que envuelve al del eje y pasa su salida por `journal_artwork_text`.

    Las marcas se vuelven a escribir en cada dibujo a partir del formateador: cambiar el texto de los
    artistas no bastaría. Delegar (y no sustituir) conserva el formateador del idioma que instaló el módulo."""
    global _JOURNAL_FORMATTER_CLASS
    if _JOURNAL_FORMATTER_CLASS is not None:
        return _JOURNAL_FORMATTER_CLASS
    from matplotlib.ticker import Formatter

    class JournalTickFormatter(Formatter):
        def __init__(self, inner):
            super().__init__()
            self.inner = inner

        def set_axis(self, axis):
            super().set_axis(axis)
            self.inner.set_axis(axis)

        def set_locs(self, locs):
            super().set_locs(locs)
            self.inner.set_locs(locs)

        def __call__(self, x, pos=None):
            return journal_artwork_text(self.inner(x, pos))

        def format_ticks(self, values):
            return [journal_artwork_text(s) for s in self.inner.format_ticks(values)]

        def get_offset(self):
            return journal_artwork_text(self.inner.get_offset())

        def format_data(self, value):
            return self.inner.format_data(value)

        def format_data_short(self, value):
            return self.inner.format_data_short(value)

        def fix_minus(self, s):
            return self.inner.fix_minus(s)

    _JOURNAL_FORMATTER_CLASS = JournalTickFormatter
    return JournalTickFormatter


#: Etiquetas internas de variante que una lámina inglesa no debe imprimir con su nombre de código: el
#: lector de la revista no sabe qué es «con_rett − sin_rett» (Figura S2e). Solo en modo revista e inglés.
_JOURNAL_LABEL_SUBS = (("con_rett − sin_rett", "full F84 − F84 without Rett"),
                       ("con_rett", "full F84 (with Rett)"), ("sin_rett", "F84 without Rett"))


def journal_label_text(s):
    """Texto de lámina en inglés sin los nombres de código de las variantes (véase _JOURNAL_LABEL_SUBS)."""
    if s is None:
        return s
    s = str(s)
    for old, new in _JOURNAL_LABEL_SUBS:
        if old in s:
            s = s.replace(old, new)
    return s


def journal_number_pass(fig) -> int:
    """Aplica la convención numérica de la revista a TODO el texto de la lámina (marcas incluidas), y
    sustituye los nombres de código de las variantes por su etiqueta legible (`journal_label_text`).

    Devuelve cuántos artistas de texto cambiaron. Solo se llama para el inglés."""
    import matplotlib.text as mtext
    Fmt = _journal_tick_formatter_class()
    for ax in _pl_all_axes(fig):
        for axis in (ax.xaxis, ax.yaxis):
            for which in ("major", "minor"):
                f = getattr(axis, f"get_{which}_formatter")()
                if f is not None and not isinstance(f, Fmt):
                    getattr(axis, f"set_{which}_formatter")(Fmt(f))
    n = 0
    for t in fig.findobj(mtext.Text):
        s = t.get_text()
        if not s:
            continue
        new = journal_label_text(journal_artwork_text(s))
        if new != s:
            t.set_text(new)
            n += 1
    return n


#: Fondo blanco sin borde bajo una leyenda o una nota de panel (modo revista): la misma caja que
#: `PLATE_NOTE_BBOX` usa para las notas del corpus.
_JOURNAL_BACK_BBOX = dict(facecolor="white", edgecolor="none", alpha=0.85, pad=0.9)


def _journal_context_lines(ax) -> list:
    """Líneas de CONTEXTO del panel: las dibujadas en coordenadas mixtas y no continuas (la línea punteada de la
    Ley 21.545, las líneas de referencia). Lo que va en coordenadas de dato es dato, no contexto."""
    out = []
    for ln in ax.lines:
        if not ln.get_visible() or ln.get_transform() is ax.transData:
            continue
        if str(ln.get_linestyle()) in ("-", "solid", "None", "none", ""):
            continue
        out.append(ln)
    return out


def journal_back_legends_and_notes(fig) -> int:
    """Modo revista: fondo blanco sin borde bajo cada leyenda SIN marco y bajo la nota de panel (coordenadas
    de eje, sin recuadro) que cae sobre una línea de contexto y sobre ningún dato.

    Con los marcos apagados del corpus (`legend.frameon: False`), la línea punteada de la Ley 21.545 cruzaba
    el texto de la leyenda en la Figura 4 (d, f) y en varias láminas suplementarias; la caja blanca la deja
    detrás sin dibujar un borde. Una nota que también cae sobre un DATO no se cubre: taparlo sería peor que
    la línea de contexto, y el verificador de composición lo marcaría. Devuelve cuántos artistas cambiaron."""
    r = _pl_renderer(fig)
    n = 0

    def _back(lg):
        nonlocal n
        if lg is None or not lg.get_visible() or lg.get_frame_on():
            return
        lg.set_frame_on(True)
        fr = lg.get_frame()
        fr.set_facecolor("white")
        fr.set_edgecolor("none")
        fr.set_alpha(_JOURNAL_BACK_BBOX["alpha"])
        lg.set_zorder(max(6, lg.get_zorder()))
        n += 1

    for ax in _pl_all_axes(fig):
        if not ax.get_visible():
            continue
        _back(ax.get_legend())
        ctx = [b for b in (_pl_extent(ln, r) for ln in _journal_context_lines(ax)) if b is not None]
        if not ctx:
            continue
        data = [b for b in (_pl_extent(a, r) for a in _pl_data_artists(ax)) if b is not None]
        for t in ax.texts:
            if not t.get_visible() or not str(t.get_text()).strip() or _pl_boxed(t) or _pl_in_data_coords(t, ax):
                continue
            b = _pl_extent(t, r)
            if b is None or not any(b.overlaps(c) for c in ctx) or any(b.overlaps(d) for d in data):
                continue
            t.set_bbox(dict(_JOURNAL_BACK_BBOX))
            n += 1
    for lg in getattr(fig, "legends", []):
        _back(lg)
    return n


def journal_plate_export(fig, path, lang: str | None = None) -> Path:
    """Punto de salida de una lámina en modo revista; la identidad (sin tocar nada) cuando está apagado.

    Se llama justo antes del `savefig` definitivo de cada módulo (o dentro de `save_fig`): retira los
    títulos (idempotente tras `plate_resolve`), aplica en inglés la convención numérica, vuelve a pasar el
    verificador de composición sobre el estado que se guarda (LANCET_PLATE_CHECK), anota los títulos
    retirados en `panel_titles.json` junto a la lámina y devuelve la ruta redirigida donde escribirla."""
    path = Path(path)
    if not plate_journal_mode():
        return path
    variant, path_lang, stem = _journal_path_parts(path)
    lang = (lang or path_lang or getattr(fig, "_plate_lang", None) or getattr(fig, "_lancet_lang", None)
            or "es")
    panels = journal_strip_titles(fig)
    dest = journal_redirect(path)
    if variant is not None and variant != plate_journal_variant():
        return dest                      # borrador: la variante que no se envía no se verifica ni se anota
    if lang == "en":
        journal_number_pass(fig)
    backed = journal_back_legends_and_notes(fig)
    fig.canvas.draw()
    fig._plate_checked = False
    _plate_autocheck(fig, dest.name)
    rec = dict(variant=variant, lang=lang, file=str(dest), number_pass=(lang == "en"),
               panels=dict(panels), kept_titles=list(getattr(fig, "_journal_kept_titles", [])),
               removed=list(getattr(fig, "_journal_removed", [])), backed_legends_notes=int(backed))
    _JOURNAL_PANELS.setdefault((variant, lang), {})[stem] = rec
    reg_path = dest.parent / "panel_titles.json"
    try:
        reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.is_file() else {}
    except (OSError, ValueError):
        reg = {}
    reg[stem] = rec
    atomic_write_json(dict(sorted(reg.items())), reg_path)
    return dest


_JOURNAL_CAPTION_MARK_RE = re.compile(r"(?:^|(?<=[.;:!?] ))\(([a-f](?:\s*[,–-]\s*[a-f])*)\)\s+")


def _journal_letters(spec: str) -> list:
    spec = spec.replace(" ", "")
    out = []
    for part in spec.split(","):
        m = re.match(r"^([a-f])[–-]([a-f])$", part)
        if m:
            out.extend(chr(c) for c in range(ord(m.group(1)), ord(m.group(2)) + 1))
        elif part:
            out.append(part)
    return out


def journal_caption_text(caption, panels: dict) -> str:
    """Leyenda de la revista: cada «(a) …» empieza por el título que el panel llevaba impreso.

        «(a) Episodes with F84 …»  ->  «(a) Rate per 100,000 episodes. Episodes with F84 …»
    Un marcador agrupado, «(a, b)» o «(a–c)», lleva los títulos de sus paneles separados por «; ».
    Los números del título son los que la lámina imprimía (calculados por el módulo), nunca tecleados."""
    def _sub(m):
        titles = [str(panels.get(letter_, "")).strip() for letter_ in _journal_letters(m.group(1))]
        titles = [t.rstrip(".:;, ") for t in titles if t]
        if not titles:
            return m.group(0)
        return f"({m.group(1)}) " + "; ".join(titles) + ". "
    return _JOURNAL_CAPTION_MARK_RE.sub(_sub, str(caption))


def journal_caption_entry(entry: dict, rec: dict) -> dict:
    """Entrada de captions.json de la carpeta de la revista: mismo esquema {title, caption} más `panels`."""
    panels = dict(rec.get("panels") or {})
    out = dict(entry)
    out["caption"] = journal_caption_text(entry.get("caption", ""), panels)
    out["panels"] = panels
    return out


def _journal_captions_merge(obj, original, dest) -> dict:
    """captions.json en modo revista: se FUSIONA con el de la carpeta de la revista y solo entran las
    láminas que este proceso dibujó en modo revista, con sus títulos de panel pasados a la leyenda."""
    variant, lang, _ = _journal_path_parts(original)
    reg = _JOURNAL_PANELS.get((variant, lang), {})
    try:
        existing = json.loads(Path(dest).read_text(encoding="utf-8")) if Path(dest).is_file() else {}
    except (OSError, ValueError):
        existing = {}
    out = dict(existing) if isinstance(existing, dict) else {}
    for key, entry in (obj or {}).items():
        if key in reg and isinstance(entry, dict):
            out[key] = journal_caption_entry(entry, reg[key])
    return dict(sorted(out.items()))


def save_fig(fig, path: Path, dpi=600):
    path = Path(path)
    # Última red de la regla de la raya: una figura que no pasa por el motor (08d) llega igual con la
    # raya puesta. Idempotente detrás de `plate_fit`/`plate_resolve`.
    plate_range_dash(fig)
    plate_pct_bind(fig)
    # Modo revista (LANCET_PLATE_JOURNAL): títulos fuera, convención numérica, verificación y ruta de la
    # revista; devuelve la misma ruta y no toca la figura cuando el modo está apagado.
    path = journal_plate_export(fig, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Puerta del verificador de composición (apagada salvo que se pida): ninguna lámina se guarda sin
    # comprobarse cuando LANCET_PLATE_CHECK está en «report» o en «strict».
    _plate_autocheck(fig, path.name)
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    return path


# ===========================================================================
# Motor de descongestión de láminas
# ---------------------------------------------------------------------------
# Los verificadores devolvieron ~40 defectos de la misma familia: un rótulo impreso sobre otro, una leyenda
# encima de las barras, una nota cortada por el borde de la celda, marcas de eje que se pisan. Todos nacen
# de lo mismo: el texto se coloca en una coordenada fija SIN MEDIR lo que ya hay dibujado. Corregirlos uno a
# uno en cada panel deja el defecto latente en el panel siguiente; aquí se mide y se resuelve una sola vez,
# justo antes de guardar, para todas las láminas de las nueve producciones.
#
# El motor tiene dos mitades, porque la composición se congela a mitad del guardado:
#   plate_fit(fig)      — ANTES de congelar: marcas de eje que se pisan, rótulos de eje más largos que su
#                         panel, leyendas más anchas que su celda o encima de los datos.
#   plate_resolve(fig)  — DESPUÉS de congelar: colisiones entre rótulos, notas sobre los datos, texto de
#                         celda de mapa de calor más ancho que su celda, y lo que sobresalga de la celda.
# Ningún cuerpo baja de 6 pt: cuando reducir no basta, el motor pliega, desplaza o adelgaza, nunca encoge
# por debajo del mínimo de la norma.
# ===========================================================================
PLATE_FS_FLOOR = 6.0
PLATE_KEEP = "plate-keep"          # gid que exime a un artista del motor (posición deliberada e inamovible)


def _pl_bbox(x0, y0, x1, y1):
    from matplotlib.transforms import Bbox
    return Bbox.from_extents(x0, y0, x1, y1)


def _pl_over(a, b) -> float:
    """Área de solape de dos rectángulos de pantalla (0 si no se tocan)."""
    return (max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0)) * max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0)))


def _pl_out(box, bound) -> float:
    """Cuánto sobresale un rectángulo de su región permitida, en píxeles lineales."""
    return (max(0.0, bound.x0 - box.x0) + max(0.0, box.x1 - bound.x1)
            + max(0.0, bound.y0 - box.y0) + max(0.0, box.y1 - bound.y1))


def _pl_extent(artist, r):
    try:
        b = artist.get_window_extent(r)
    except (AttributeError, ValueError, RuntimeError, TypeError):
        return None
    if not np.isfinite([b.x0, b.y0, b.x1, b.y1]).all() or b.width <= 0 or b.height <= 0:
        return None
    return b


def plate_cell_box(fig, ax, topmost: bool = False):
    """Rectángulo de PANTALLA de la celda de rejilla del panel: el territorio que le pertenece.

    Nada de un panel debe salir de su celda: fuera de ella o se pierde contra el borde del lienzo o se
    imprime sobre el panel vecino (los dos defectos que los verificadores vieron en S45, S46 y S3)."""
    spec = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
    if spec is None:
        return fig.bbox
    if topmost:
        # El TÍTULO de panel pertenece a la celda de la lámina, no a la subcelda: en un mapa de tres
        # franjas la subcelda es un tercio de la celda y plegar el título a ese ancho lo parte en seis
        # líneas que aplastan el mapa.
        try:
            spec = spec.get_topmost_subplotspec()
        except (AttributeError, ValueError):
            pass
    def bounds(sp):
        gs = sp.get_gridspec()
        parent = getattr(gs, "_subplot_spec", None)
        x0, x1, y0, y1 = bounds(parent) if parent is not None else (0.0, 1.0, 0.0, 1.0)
        nc, nr = gs.ncols, gs.nrows
        return (x0 + (x1 - x0) * sp.colspan.start / nc, x0 + (x1 - x0) * sp.colspan.stop / nc,
                y1 - (y1 - y0) * sp.rowspan.stop / nr, y1 - (y1 - y0) * sp.rowspan.start / nr)
    cx0, cx1, cy0, cy1 = bounds(spec)
    W, H = fig.bbox.width, fig.bbox.height
    return _pl_bbox(cx0 * W, cy0 * H, cx1 * W, cy1 * H)


# ---------------------------------------------------------------------------
# Ocupación: dónde hay tinta de datos dentro de un panel
# ---------------------------------------------------------------------------
def _pl_ink(ax, r, nx: int = 56, ny: int = 40):
    """Rejilla de ocupación del área de ejes: cuenta la tinta de datos celda a celda.

    Sirve para decidir dónde cabe una leyenda o una nota sin taparlos. Se muestrean los vértices de las
    líneas (densificando cada segmento, o una recta larga solo marcaría sus extremos), los rectángulos de
    las barras, los desplazamientos de las colecciones y el recuadro de las imágenes."""
    ext = _pl_extent(ax, r) or ax.bbox
    occ = np.zeros((ny, nx), dtype=float)
    if ext.width <= 0 or ext.height <= 0:
        return occ, ext

    def mark_box(b, w=1.0):
        if b is None or b.width <= 0:
            return
        i0 = int(np.floor((b.x0 - ext.x0) / ext.width * nx)); i1 = int(np.ceil((b.x1 - ext.x0) / ext.width * nx))
        j0 = int(np.floor((b.y0 - ext.y0) / ext.height * ny)); j1 = int(np.ceil((b.y1 - ext.y0) / ext.height * ny))
        i0, i1 = max(0, i0), min(nx, i1); j0, j1 = max(0, j0), min(ny, j1)
        if i1 > i0 and j1 > j0:
            occ[j0:j1, i0:i1] += w

    def mark_pts(pts, w=1.0):
        pts = np.asarray(pts, dtype=float)
        if pts.ndim != 2 or pts.shape[0] == 0:
            return
        pts = pts[np.isfinite(pts).all(axis=1)]
        if not len(pts):
            return
        i = np.clip(((pts[:, 0] - ext.x0) / ext.width * nx).astype(int), 0, nx - 1)
        j = np.clip(((pts[:, 1] - ext.y0) / ext.height * ny).astype(int), 0, ny - 1)
        np.add.at(occ, (j, i), w)

    for ln in ax.lines:
        try:
            pts = ln.get_transform().transform(ln.get_xydata())
        except (ValueError, TypeError, AttributeError):
            continue
        pts = np.asarray(pts, dtype=float)
        if pts.ndim != 2 or len(pts) == 0:
            continue
        if len(pts) > 1:
            t = np.linspace(0.0, 1.0, 16)[:, None, None]
            dense = (pts[None, :-1, :] * (1 - t) + pts[None, 1:, :] * t).reshape(-1, 2)
            mark_pts(dense)
        else:
            mark_pts(pts)
    for p in ax.patches:
        mark_box(_pl_extent(p, r))
    for c in ax.collections:
        try:
            off = np.asarray(c.get_offset_transform().transform(c.get_offsets()), dtype=float)
        except (ValueError, TypeError, AttributeError):
            off = np.empty((0, 2))
        if off.ndim == 2 and len(off):
            mark_pts(off)
        else:
            mark_box(_pl_extent(c, r))
    for im in ax.images:
        mark_box(_pl_extent(im, r))
    return occ, ext


def _pl_axes_groups(fig) -> list:
    """Agrupa los ejes que ocupan el MISMO rectángulo (twinx/twiny).

    Un eje gemelo es un objeto Axes distinto pero dibuja en el mismo sitio: los porcentajes de retención del
    eje derecho y los «n=» del eje izquierdo se imprimían unos sobre otros porque cada eje se descongestionaba
    por separado y ninguno veía los rótulos del otro. Aquí se tratan como un solo panel."""
    groups: dict = {}
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        pos = ax.get_position()
        key = (round(pos.x0, 4), round(pos.y0, 4), round(pos.x1, 4), round(pos.y1, 4))
        groups.setdefault(key, []).append(ax)
    return list(groups.values())


def _pl_group_ink(axes, r):
    """Tinta acumulada de un grupo de ejes gemelos, sobre la rejilla del primero."""
    occ, ext = _pl_ink(axes[0], r)
    for ax in axes[1:]:
        o2, _ = _pl_ink(ax, r)
        if o2.shape == occ.shape:
            occ = occ + o2
    return occ, ext


def _pl_ink_cost(occ, ext, box) -> float:
    """Tinta de datos bajo un rectángulo candidato, normalizada por su área en celdas de la rejilla."""
    ny, nx = occ.shape
    if ext.width <= 0 or ext.height <= 0:
        return 0.0
    i0 = int(np.floor((box.x0 - ext.x0) / ext.width * nx)); i1 = int(np.ceil((box.x1 - ext.x0) / ext.width * nx))
    j0 = int(np.floor((box.y0 - ext.y0) / ext.height * ny)); j1 = int(np.ceil((box.y1 - ext.y0) / ext.height * ny))
    i0, i1 = max(0, i0), min(nx, i1); j0, j1 = max(0, j0), min(ny, j1)
    if i1 <= i0 or j1 <= j0:
        return 0.0
    return float(occ[j0:j1, i0:i1].sum())


# ---------------------------------------------------------------------------
# plate_fit: marcas de eje, rótulos de eje y leyendas (antes de congelar la composición)
# ---------------------------------------------------------------------------
def _pl_axis_labels(axis):
    return [t for t in axis.get_ticklabels() if t.get_visible() and str(t.get_text()).strip()]


def _pl_pairs_overlap(boxes, gap: float = 1.0) -> bool:
    for a, b in zip(boxes[:-1], boxes[1:]):
        if a is None or b is None:
            continue
        if _pl_over(_pl_bbox(a.x0 - gap, a.y0 - gap, a.x1 + gap, a.y1 + gap), b) > 0:
            return True
    return False


def _pl_fix_ticklabels(ax, r, horizontal: bool) -> None:
    """Evita que dos marcas de eje contiguas se impriman una sobre otra.

    Se prueba, por este orden: reducir el cuerpo hasta el mínimo de la norma (6 pt); girar a 90° las marcas
    del eje X (una etiqueta vertical ocupa su ALTO, no su ancho, y doce categorías caben donde antes se
    pisaban); y, solo si ninguna de las dos basta, plegar la etiqueta en dos líneas. Nunca se oculta una
    marca: la categoría que desaparece del eje desaparece del resultado."""
    axis = ax.xaxis if horizontal else ax.yaxis
    labs = _pl_axis_labels(axis)
    if len(labs) < 2:
        return
    labs.sort(key=lambda t: t.get_window_extent(r).x0 if horizontal else t.get_window_extent(r).y0)

    def boxes():
        return [_pl_extent(t, r) for t in labs]

    if not _pl_pairs_overlap(boxes()):
        return
    for fs in (7.0, 6.5, PLATE_FS_FLOOR):
        if min(t.get_size() for t in labs) <= fs:
            continue
        for t in labs:
            t.set_size(min(t.get_size(), fs))
        if not _pl_pairs_overlap(boxes()):
            return
    if horizontal and max(abs(t.get_rotation() % 180) for t in labs) < 60:
        for t in labs:
            t.set_rotation(90); t.set_ha("center"); t.set_va("top")
        if not _pl_pairs_overlap(boxes()):
            return
    # último recurso: plegar en dos líneas, que reduce a la mitad el lado que estorba
    for t in labs:
        txt = str(t.get_text())
        if "\n" in txt or " " not in txt:
            continue
        parts = txt.split()
        mid = max(1, len(parts) // 2)
        t.set_text("\n".join([" ".join(parts[:mid]), " ".join(parts[mid:])]))


def _pl_fit_ytick_width(ax, fig, r) -> None:
    """Impide que las marcas del eje Y se salgan de la celda e invadan el panel de la izquierda.

    Es el defecto de S45/S46 panel (f): «San Carlos (201)», «Chillán (681)» empezaban a la izquierda del
    borde de la celda y se leían dentro del panel vecino. Se pliega por ancho medido y, si aún no cabe, se
    reduce el cuerpo hasta 6 pt."""
    labs = _pl_axis_labels(ax.yaxis)
    if not labs:
        return
    cell = plate_cell_box(fig, ax)
    axb = _pl_extent(ax, r)
    if axb is None:
        return
    room_px = max(12.0, axb.x0 - cell.x0 - 3.0)
    room_pt = room_px * 72.0 / fig.dpi
    # Plegar en dos líneas solo si el paso entre filas admite dos líneas: en un «forest» de quince
    # especificaciones el plegado cambiaba un rótulo asomado por dos rótulos impresos uno sobre otro, que es
    # peor. Cuando no cabe la segunda línea se reduce el cuerpo y se deja el rótulo en una sola.
    pitch = axb.height / max(1, len(labs))
    for t in labs:
        b = _pl_extent(t, r)
        if b is None or b.width <= room_px:
            continue
        txt = str(t.get_text())
        if " " in txt and "\n" not in txt and pitch > 2.5 * t.get_size() * fig.dpi / 72.0:
            t.set_text(plate_wrap(txt, room_pt, t.get_size(), "normal"))
        b = _pl_extent(t, r)
        while b is not None and b.width > room_px and t.get_size() > PLATE_FS_FLOOR:
            t.set_size(max(PLATE_FS_FLOOR, t.get_size() - 0.5))
            b = _pl_extent(t, r)
    # Un eje con marcas de tres cuerpos distintos se lee como un error de composición: la que más se ha
    # tenido que reducir fija el cuerpo de todas.
    sizes = [t.get_size() for t in labs]
    if sizes and max(sizes) - min(sizes) > 1e-6:
        for t in labs:
            t.set_size(min(sizes))


def _pl_fit_xlabel(ax, fig, r) -> None:
    """Rótulos de eje que caben en su celda.

    Dos defectos recurrentes: el rótulo del eje X más ancho que la celda, cortado contra el borde del lienzo
    («…hospital episode» sin su «(log)»), y el rótulo girado del eje Y más alto que el panel, cuyo remate
    atravesaba el título y la letra del panel. Se pliega por ancho medido y, si sigue sin caber, se reduce
    hasta 6 pt."""
    cell = plate_cell_box(fig, ax)
    axb = _pl_extent(ax, r)
    if axb is None:
        return
    xl = ax.xaxis.label
    if str(xl.get_text()).strip():
        # El rótulo del eje X se centra en los EJES, no en la celda. Cuando las marcas del eje Y son largas
        # los ejes empiezan muy a la derecha y un rótulo centrado en ellos se sale por el borde derecho de la
        # celda: el ancho útil es el doble de la distancia menor del centro de los ejes a los bordes de la
        # celda, no el ancho de la celda. Con este cálculo dejaron de perderse los remates «(log)» y «2017)».
        centre = 0.5 * (axb.x0 + axb.x1)
        room_px = max(60.0, 2.0 * min(centre - cell.x0, cell.x1 - centre) - 6.0)
        room_pt = room_px * 72.0 / fig.dpi
        b = _pl_extent(xl, r)
        if b is not None and b.width > room_px:
            xl.set_text("\n".join(plate_wrap(line, room_pt, xl.get_size(), "normal")
                                  for line in str(xl.get_text()).split("\n")))
            b = _pl_extent(xl, r)
            while b is not None and b.width > room_px and xl.get_size() > PLATE_FS_FLOOR:
                xl.set_size(max(PLATE_FS_FLOOR, xl.get_size() - 0.5))
                b = _pl_extent(xl, r)


def _pl_fit_ylabel(ax, fig, r) -> None:
    """Rótulo girado del eje Y que cabe en el alto del panel."""
    cell = plate_cell_box(fig, ax)
    axb = _pl_extent(ax, r)
    if axb is None:
        return
    yl = ax.yaxis.label
    if str(yl.get_text()).strip():
        b = _pl_extent(yl, r)
        room = axb.height - 2.0
        if b is not None and b.height > room:
            # Primero se reduce el cuerpo: plegar el rótulo GIRADO del eje Y añade una línea a su IZQUIERDA,
            # y si no hay sitio esa línea se pierde contra el borde del lienzo —«…ratio (log» sin su
            # «escala)»—. Solo se pliega cuando el hueco a la izquierda del panel da para otra línea, y si
            # el resultado se sale de la celda se vuelve a la línea única.
            while b is not None and b.height > room and yl.get_size() > PLATE_FS_FLOOR:
                yl.set_size(max(PLATE_FS_FLOOR, yl.get_size() - 0.5))
                b = _pl_extent(yl, r)
            if b is not None and b.height > room:
                original = str(yl.get_text())
                room_pt = max(48.0, room * 72.0 / fig.dpi)
                yl.set_text("\n".join(plate_wrap(line, room_pt, yl.get_size(), "normal")
                                      for line in original.split("\n")))
                nb = _pl_extent(yl, r)
                if nb is None or nb.x0 < cell.x0 + 1.0:
                    yl.set_text(original)


_PL_LOCS = ("upper left", "upper right", "lower left", "lower right",
            "upper center", "lower center", "center left", "center right", "center")


def _pl_loc_box(loc: str, ext, w: float, h: float, pad: float):
    if "left" in loc:
        x0 = ext.x0 + pad
    elif "right" in loc:
        x0 = ext.x1 - pad - w
    else:
        x0 = ext.x0 + (ext.width - w) / 2.0
    if "upper" in loc:
        y0 = ext.y1 - pad - h
    elif "lower" in loc:
        y0 = ext.y0 + pad
    else:
        y0 = ext.y0 + (ext.height - h) / 2.0
    return _pl_bbox(x0, y0, x0 + w, y0 + h)


def _pl_fit_legend(ax, fig, r) -> None:
    """Leyenda dentro de su panel, entera y sobre el hueco más vacío.

    Tres defectos a la vez: la leyenda a dos columnas más ancha que el panel, cuya columna derecha se cortaba
    a media palabra («Entries: strict a…»); la leyenda dibujada encima de las barras o de la serie; y la
    leyenda que tapaba el principio de una nota. Se recompone a una columna cuando no cabe, se pliega el
    texto de cada entrada por ancho medido y se ancla en el cuadrante con menos tinta."""
    lg = ax.get_legend()
    if lg is None or not lg.get_visible() or lg.get_gid() == PLATE_KEEP:
        return
    axb = _pl_extent(ax, r)
    if axb is None:
        return
    b = _pl_extent(lg, r)
    if b is None:
        return
    if b.x1 < axb.x0 + 1 or b.x0 > axb.x1 - 1 or b.y1 < axb.y0 + 1 or b.y0 > axb.y1 - 1:
        return                                   # leyenda deliberadamente fuera del área de ejes
    # una leyenda con anclaje propio (`bbox_to_anchor`) se corrige de ancho pero no se reubica: su sitio lo
    # fija el autor respecto de un punto del panel, y moverla rompería esa referencia.
    anc = lg.get_bbox_to_anchor()
    own_anchor = anc is not None and max(abs(anc.x0 - axb.x0), abs(anc.x1 - axb.x1),
                                         abs(anc.y0 - axb.y0), abs(anc.y1 - axb.y1)) > 2.0
    handles = list(getattr(lg, "legend_handles", getattr(lg, "legendHandles", [])))
    labels = [t.get_text() for t in lg.get_texts()]
    fs = lg.get_texts()[0].get_size() if lg.get_texts() else PLATE_FS_FLOOR
    ncol = getattr(lg, "_ncols", 1)
    max_w = axb.width * 0.99
    # 1) a una columna si a dos no cabe entera en el panel
    if b.width > max_w and ncol > 1 and handles:
        lg = _pl_relegend(ax, lg, handles, labels, ncol=1)
        b = _pl_extent(lg, r)
    # 2) plegar el texto de las entradas y, si hace falta, reducir hasta 6 pt
    guard = 0
    while b is not None and b.width > max_w and guard < 6:
        guard += 1
        room_pt = max(40.0, (max_w - 22.0) * 72.0 / fig.dpi)
        changed = False
        for t in lg.get_texts():
            s = str(t.get_text())
            w = plate_wrap(s, room_pt, t.get_size(), "normal")
            if w != s:
                t.set_text(w); changed = True
        b = _pl_extent(lg, r)
        if b is not None and b.width > max_w and fs > PLATE_FS_FLOOR:
            fs = max(PLATE_FS_FLOOR, fs - 0.4)
            for t in lg.get_texts():
                t.set_size(fs)
            if lg.get_title() is not None:
                lg.get_title().set_size(fs)
            b = _pl_extent(lg, r); changed = True
        if not changed:
            break
    # 3) forma y sitio: se prueba el número de columnas Y el anclaje, y gana el par que menos tinta tapa
    if b is None or own_anchor:
        return
    # El estado ya ajustado por los pasos 1 y 2 es el punto de partida: leer aquí el número de columnas y
    # los textos YA PLEGADOS es lo que impide que la recomposición final deshaga el ajuste y devuelva la
    # leyenda a dos columnas con las etiquetas sin plegar —que es como la columna derecha volvía a cortarse.
    ncol = getattr(lg, "_ncols", 1)
    labels = [t.get_text() for t in lg.get_texts()]
    handles = list(getattr(lg, "legend_handles", [])) or handles
    siblings = next((g for g in _pl_axes_groups(ax.figure) if ax in g), [ax])
    occ, ext = _pl_group_ink(siblings, r)
    pad = 0.012 * min(axb.width, axb.height) + 2.0
    others = [q for q in (_pl_extent(t, r) for a in siblings for t in a.texts if t.get_visible()) if q is not None]

    def score(box):
        # Los rótulos del panel pesan de verdad en la elección: con un peso simbólico la leyenda se sentaba
        # sobre la marca de la pandemia o sobre la de la Ley y era el rótulo, no la leyenda, el que tenía que
        # huir —y acababa contra el título. Y una leyenda no puede salirse del panel: centrada, una más ancha
        # que el eje asomaba por la izquierda y tapaba el rótulo del eje Y.
        return (_pl_ink_cost(occ, ext, box) + 0.02 * sum(_pl_over(box, q) for q in others)
                + 60.0 * _pl_out(box, axb))

    def best_loc(box_w, box_h):
        out = (None, np.inf)
        for loc in _PL_LOCS:
            c = score(_pl_loc_box(loc, axb, box_w, box_h, pad))
            if c < out[1] - 1e-9:
                out = (loc, c)
        return out

    # Coste de donde YA está: una leyenda que su autor colocó en una banda que reservó para ella no se
    # mueve por una mejora marginal del recuento de tinta. Sin esta histéresis, la leyenda de S45 (f) se
    # iba de la banda libre de la derecha —reservada ampliando el eje— a la esquina superior, donde tapaba
    # las dos primeras filas.
    here = score(b)
    best, best_cost = best_loc(b.width, b.height)
    # Una leyenda de dieciséis entradas en una columna es una tira que cruza el panel entero, y en dos
    # columnas es un bloque que tapa un cuarto del área de datos. Con varias formas a prueba, el motor elige
    # la que cabe en el hueco que de verdad hay: ancha y baja cuando el hueco está abajo, alta y estrecha
    # cuando está al costado.
    if len(labels) > 5 and handles:
        # `ax.legend(...)` SUSTITUYE la leyenda del panel: probar una forma ya la deja puesta. Por eso se
        # prueban todas, se anota la mejor y se vuelve a componer al final con la ganadora; descartar una
        # forma con un `continue` dejaba en el panel la última probada —una leyenda a tres columnas más
        # ancha que el eje, que se salía por la izquierda y tapaba el rótulo del eje Y.
        best_ncol, best_shape_cost = ncol, np.inf
        for nc in (1, 2, 3):
            if nc == ncol:
                continue
            cand_lg = _pl_relegend(ax, lg, handles, labels, ncol=nc)
            cb = _pl_extent(cand_lg, r)
            if cb is None or cb.width > max_w:
                continue
            loc_, cost_ = best_loc(cb.width, cb.height)
            if cost_ < best_shape_cost - 1e-9:
                best_shape_cost, best_ncol = cost_, nc
        use = best_ncol if (best_ncol != ncol and best_shape_cost < 0.7 * min(here, best_cost)) else ncol
        # Se recompone SIEMPRE con la forma elegida: `ax.legend(...)` sustituye la leyenda del panel, de
        # modo que probar una forma ya la deja puesta y salir del bucle sin recomponer dejaba en el panel
        # la última probada.
        lg = _pl_relegend(ax, lg, handles, labels, ncol=use)
        nb = _pl_extent(lg, r)
        if nb is not None:
            best, best_cost = best_loc(nb.width, nb.height)
    if best is not None and best_cost < 0.7 * here:
        try:
            lg.set_loc(best)
        except (AttributeError, ValueError):
            pass


def _pl_relegend(ax, lg, handles, labels, ncol: int):
    """Recompone una leyenda con otro número de columnas conservando su aspecto."""
    fs = lg.get_texts()[0].get_size() if lg.get_texts() else PLATE_FS_FLOOR
    title = lg.get_title().get_text() if lg.get_title() is not None else None
    frame = lg.get_frame()
    kw = dict(loc="upper left", fontsize=fs, ncol=ncol, frameon=lg.get_frame_on(),
              framealpha=frame.get_alpha() if frame is not None else 0.85,
              edgecolor="none", facecolor="white", borderpad=0.25,
              handlelength=1.4, handletextpad=0.5, labelspacing=0.28, columnspacing=0.8)
    if title:
        kw["title"] = title
        kw["title_fontsize"] = fs
    new = ax.legend(handles, labels, **kw)
    new.set_zorder(max(6, lg.get_zorder()))
    new.set_in_layout(False)
    return new


def plate_fit(fig) -> None:
    """Primera mitad del motor: se llama ANTES de congelar la composición."""
    fig.canvas.draw()
    # La raya del intervalo va antes de MEDIR y después del dibujado que el motor ya hacía: el motor mide
    # así el texto definitivo —una marca crece ~1,5 pt al pasar de guion a raya— sin que la regla añada un
    # dibujado propio a la lámina que no tiene nada que convertir (regla en J2, arriba).
    plate_range_dash(fig)
    plate_pct_bind(fig)
    r = fig.canvas.get_renderer()
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        try:
            _pl_fix_ticklabels(ax, r, horizontal=True)
            _pl_fix_ticklabels(ax, r, horizontal=False)
            _pl_fit_ytick_width(ax, fig, r)
            # El rótulo del eje X se pliega AQUÍ, con el reparto vivo: plegado después de congelarlo, la
            # línea que gana no tiene sitio reservado, se sale de la celda y la guarda de recorte lo
            # empujaba hacia arriba, sobre las propias marcas del eje.
            _pl_fit_xlabel(ax, fig, r)
        except (ValueError, AttributeError, RuntimeError, TypeError, IndexError):
            continue


# ---------------------------------------------------------------------------
# plate_resolve: colisiones de rótulos, notas sobre los datos y recortes (composición ya congelada)
# ---------------------------------------------------------------------------
def _pl_nudge(t, dx: float, dy: float, fig) -> bool:
    """Desplaza un texto dx, dy PUNTOS sin tocar su sistema de coordenadas.

    Un rótulo de valor vive en coordenadas de dato, una nota en coordenadas de eje y la marca de la Ley en
    una mezcla de las dos: recalcular la posición en cada sistema sería tres códigos distintos y frágiles.
    Componer la transformación con una traslación en puntos vale para los tres."""
    from matplotlib.text import Annotation
    from matplotlib.transforms import ScaledTranslation
    if dx == 0 and dy == 0:
        return True
    if isinstance(t, Annotation):
        if t.anncoords != "offset points":
            return False
        x, y = t.xyann
        t.xyann = (x + dx, y + dy)
        return True
    base = getattr(t, "_pl_base_tr", None)
    if base is None:
        base = t.get_transform()
        t._pl_base_tr = base
    ox, oy = getattr(t, "_pl_off", (0.0, 0.0))
    ox, oy = ox + dx, oy + dy
    t._pl_off = (ox, oy)
    t.set_transform(base + ScaledTranslation(ox / 72.0, oy / 72.0, fig.dpi_scale_trans))
    return True


def _pl_free_axes(t, ax) -> str:
    """Direcciones en que un texto puede moverse sin mentir sobre a qué dato se refiere."""
    tr = t.get_transform()
    if tr is ax.transAxes:
        return "xy"
    try:
        if tr is ax.get_xaxis_transform():
            return "y"          # la x la fija el dato (la línea de la Ley, el año)
        if tr is ax.get_yaxis_transform():
            return "x"
    except (AttributeError, ValueError):
        pass
    return "xy"


def _pl_data_pitch(ax, fig) -> tuple:
    """Media distancia, en puntos, entre categorías contiguas de cada eje.

    Un rótulo escrito en coordenadas de dato no puede alejarse más que eso de su dato: pasado ese punto el
    lector lo atribuye a la fila o a la columna vecina, que es el defecto que los verificadores describieron
    en la Figura 5 («no se sabe a qué fila pertenece cada número»)."""
    out = []
    for axis, span in ((ax.xaxis, ax.bbox.width), (ax.yaxis, ax.bbox.height)):
        try:
            lo, hi = min(axis.get_view_interval()), max(axis.get_view_interval())
            locs = [q for q in axis.get_ticklocs() if lo <= q <= hi]
            labels = [str(t.get_text()) for t in axis.get_ticklabels() if str(t.get_text()).strip()]
        except (AttributeError, ValueError):
            locs, labels = [], []
        # El límite solo se aplica a un eje CATEGÓRICO —regiones, especificaciones, grupos de edad—, donde
        # la fila vecina es otra categoría y mover el rótulo cambia a qué se refiere. En un eje continuo la
        # marca es una graduación, no una categoría: allí el rótulo puede correrse lo que haga falta, y sin
        # esta distinción dos valores contiguos se quedaban pegados por no poder apartarse.
        def _numeric(txt: str) -> bool:
            q = txt.replace("\u2212", "-").replace("\u2013", "-").replace(" ", "").replace("\u00a0", "")
            q = q.replace("%", "").replace(",", "").replace(".", "").replace("'", "").lstrip("-+")
            return q.isdigit()
        categorical = bool(labels) and sum(_numeric(t) for t in labels) < 0.6 * len(labels)
        out.append(0.5 * span / max(1, len(locs) - 1) * 72.0 / fig.dpi
                   if (categorical and len(locs) >= 3) else np.inf)
    return tuple(out)


def _pl_candidates(t, ax, w_pt: float, h_pt: float):
    """Desplazamientos candidatos, del menor al mayor: se mueve lo mínimo que resuelve la colisión."""
    free = _pl_free_axes(t, ax)
    rot = abs(float(t.get_rotation())) % 180.0
    dy = h_pt + 1.2
    dx = w_pt * 0.60 + 1.2
    ys = [0.0, dy, -dy, 2 * dy, -2 * dy, 3 * dy, -3 * dy, 4 * dy, -4 * dy]
    xs = [0.0, dx, -dx, 2 * dx, -2 * dx]
    if 60 <= rot <= 120:                 # rótulo girado: separarlo a lo largo de su propia lectura
        ys = [0.0, dy * 0.45, -dy * 0.45, dy * 0.9, -dy * 0.9, dy * 1.4, -dy * 1.4, dy * 2.0, -dy * 2.0]
        xs = [0.0, w_pt + 1.5, -(w_pt + 1.5), 2 * (w_pt + 1.5), -2 * (w_pt + 1.5)]
    if free == "y":
        cand = [(0.0, v) for v in ys]
    elif free == "x":
        cand = [(u, 0.0) for u in xs]
    else:
        cand = [(u, v) for v in ys for u in xs]
    if t.get_transform() is ax.transData:
        px, py = _pl_data_pitch(ax, ax.figure)
        cand = [(u, v) for u, v in cand if abs(u) <= px and abs(v) <= py]
        if not cand:
            cand = [(0.0, 0.0)]
    return sorted(cand, key=lambda p: abs(p[0]) + 1.35 * abs(p[1]))


def _pl_relocate_notes(axes, fig, r, occ, ext, obstacles) -> list:
    """Lleva cada nota de panel al hueco más vacío de su panel.

    «La nota impresa sobre los datos» es el segundo defecto más repetido del informe (S33, S36, S37, S42,
    S43, S44, S11…): la nota se ancla a una fracción fija del eje y cae sobre la serie que describe. Aquí se
    prueban nueve anclajes y se elige el que menos tinta tapa. Solo se mueven las notas escritas en
    coordenadas de EJE y dentro del panel: las que cuelgan bajo el eje, y las que se refieren a un dato
    concreto, se quedan donde su autor las puso."""
    ax = axes[0]
    axb = _pl_extent(ax, r)
    placed = list(obstacles)
    if axb is None:
        return placed
    notes = []
    for a in axes:
      for t in a.texts:
        if not t.get_visible() or not str(t.get_text()).strip() or t.get_gid() == PLATE_KEEP:
            continue
        if t.get_transform() is not a.transAxes:
            continue
        if len(" ".join(str(t.get_text()).split())) < 22:
            continue                # rótulo corto: señala un dato concreto, no es una nota de panel
        x, y = t.get_position()
        if not (0.0 <= float(x) <= 1.0 and 0.0 <= float(y) <= 1.0):
            continue               # anclada fuera del panel a propósito
        b = _pl_extent(t, r)
        if b is None:
            continue
        notes.append((t, b))
    notes.sort(key=lambda p: -p[1].width * p[1].height)
    pad = 0.012 * min(axb.width, axb.height) + 2.0
    # Los rótulos de valor cuentan como obstáculo al elegir el hueco de la nota: es mejor que la nota busque
    # sitio a que quince «n=» tengan que apartarse de ella.
    ids = {id(t) for t, _ in notes}
    others = [q for q in (_pl_extent(t, r) for a in axes for t in a.texts
                          if t.get_visible() and id(t) not in ids and str(t.get_text()).strip())
              if q is not None]
    for t, b in notes:
        best, best_cost = None, np.inf
        for loc in _PL_LOCS:
            cand = _pl_loc_box(loc, axb, b.width, b.height, pad)
            # La leyenda y el título son obstáculos DUROS para una nota: una nota bajo la leyenda pierde sus
            # primeras palabras («…isodes without a recorded weight») y el lector no puede recuperarlas.
            cost = (_pl_ink_cost(occ, ext, cand) + 0.5 * sum(_pl_over(cand, q) for q in placed)
                    + 0.20 * sum(_pl_over(cand, q) for q in others))
            if cost < best_cost - 1e-9:
                best, best_cost = (loc, cand), cost
        if best is None:
            continue
        loc, cand = best
        if _pl_over(cand, b) / max(1.0, b.width * b.height) > 0.92:
            t._pl_settled = True
            placed.append(b)
            continue                     # ya estaba en el mejor sitio
        dx = (cand.x0 - b.x0) * 72.0 / fig.dpi
        dy = (cand.y0 - b.y0) * 72.0 / fig.dpi
        if _pl_nudge(t, dx, dy, fig):
            t._pl_settled = True
            placed.append(cand)
        else:
            placed.append(b)
    return placed


def _pl_marker_area_under(box, marks) -> float:
    """Área (px²) de los DISCOS de marcador que quedan bajo `box`, sumada y vectorizada.

    Aproxima cada disco por su cuadrado envolvente: es el coste de una colocación, no una medida que se
    publique, y basta para que separar dos rótulos no consista en dejar uno encima de una chincheta."""
    if marks is None or not len(marks):
        return 0.0
    rad = _pl_marker_radii(marks)
    ix = np.clip(np.minimum(box.x1, marks[:, 0] + rad) - np.maximum(box.x0, marks[:, 0] - rad), 0.0, None)
    iy = np.clip(np.minimum(box.y1, marks[:, 1] + rad) - np.maximum(box.y0, marks[:, 1] - rad), 0.0, None)
    return float(np.sum(ix * iy))


def _pl_resolve_texts(axes, fig, r, obstacles) -> None:
    """Separa los rótulos que se imprimen unos sobre otros, moviendo lo mínimo.

    Se colocan de mayor a menor: el bloque grande ancla y los rótulos pequeños esquivan. Cada uno se prueba
    en los desplazamientos candidatos de su clase y se queda en el primero libre; si ninguno lo está, en el
    de menor solape. Ningún rótulo se borra: el número que desaparece de la lámina desaparece del artículo."""
    ax = axes[0]
    cell = plate_cell_box(fig, ax)
    axb = _pl_extent(ax, r) or cell
    bound = _pl_bbox(min(cell.x0, axb.x0) + 1.0, min(cell.y0, axb.y0) + 1.0,
                     max(cell.x1, axb.x1) - 1.0, max(cell.y1, axb.y1) - 1.0)
    # Las marcas y los rótulos de eje son obstáculos, no candidatos: empujar un «n=1.854» bajo el eje lo
    # imprime sobre el año al que se refiere, que es cambiar una colisión por otra.
    furniture = []
    for a in axes:
        for art in (list(a.xaxis.get_ticklabels()) + list(a.yaxis.get_ticklabels())
                    + [a.xaxis.label, a.yaxis.label]):
            if art is not None and art.get_visible() and str(art.get_text()).strip():
                q = _pl_extent(art, r)
                if q is not None:
                    furniture.append(q)
    marks, _bars = _pl_markers_and_bars(axes, r)
    items, placed_notes = [], []
    for a in axes:
      for t in a.texts:
        if not t.get_visible() or not str(t.get_text()).strip() or t.get_gid() == PLATE_KEEP:
            continue
        b = _pl_extent(t, r)
        if b is None:
            continue
        if getattr(t, "_pl_settled", False):
            placed_notes.append(b)      # ya la colocó la pasada de notas: es obstáculo, no candidata
            continue
        items.append((t, a, b))
    if len(items) < 2 and not obstacles:
        return
    items.sort(key=lambda p: -p[2].width * p[2].height)
    placed = [q for q in obstacles if not any(_pl_over(q, n) > 0.9 * min(q.width * q.height, n.width * n.height)
                                              for n in placed_notes)] + placed_notes + furniture
    s = fig.dpi / 72.0
    for t, own, b in items:
        w_pt, h_pt = b.width * 72.0 / fig.dpi, b.height * 72.0 / fig.dpi
        inside = _pl_over(b, axb) > 0.7 * b.width * b.height
        # Los solapes se miden en ÁREA y lo que sobresale, en longitud: comparar los dos números sin más
        # hacía preferible salirse del panel (ocho píxeles de desborde) a taparse con una leyenda
        # (cuatrocientos ochenta píxeles cuadrados), y el rótulo acababa impreso sobre el título. Multiplicar
        # el desborde por el tamaño del rótulo pone las dos cosas en la misma unidad.
        span = b.width + b.height
        def cost_of(dx, dy):
            nb = _pl_bbox(b.x0 + dx * s, b.y0 + dy * s, b.x1 + dx * s, b.y1 + dy * s)
            # Los MARCADORES también son obstáculos aquí. `plate_value_label` colocaba el rótulo fuera de
            # las chinchetas y esta pasada, que solo miraba textos, lo devolvía encima de una: es lo que
            # dejaba a la S12 (f) con un marcador del que asomaba un quince por ciento.
            c = (sum(_pl_over(nb, q) for q in placed) + _pl_marker_area_under(nb, marks)
                 + 30.0 * _pl_out(nb, bound) * span
                 + 0.4 * (abs(dx) + abs(dy)) * s)
            if inside:
                c += 3.0 * _pl_out(nb, axb) * span   # lo que nació dentro del panel se queda dentro
            return c, nb
        best, best_cost, best_box = (0.0, 0.0), np.inf, b
        for dx, dy in _pl_candidates(t, own, w_pt, h_pt):
            c, nb = cost_of(dx, dy)
            if c < best_cost - 1e-9:
                best, best_cost, best_box = (dx, dy), c, nb
            if best_cost <= 1e-9:
                break
        # Válvula de seguridad para las notas de contexto (la marca de la Ley, la banda de la disrupción):
        # su x la fija el dato, pero si toda la columna está ocupada —lo que pasaba cuando el rótulo girado
        # «definition break» llenaba la franja— vale más correrla un poco en x que imprimirla encima.
        if best_cost > 4.0 * s and t.get_transform() is not own.transData:
            for dx in (w_pt * 0.7, -w_pt * 0.7, w_pt * 1.3, -w_pt * 1.3):
                for dy in (0.0, h_pt + 1.2, -(h_pt + 1.2), 2 * (h_pt + 1.2), -2 * (h_pt + 1.2)):
                    c, nb = cost_of(dx, dy)
                    if c < best_cost - 1e-9:
                        best, best_cost, best_box = (dx, dy), c, nb
        dx, dy = best
        if (dx or dy) and _pl_nudge(t, dx, dy, fig):
            b = best_box
        placed.append(b)


def _pl_fit_cell_text(ax, fig, r) -> None:
    """Ajusta el cuerpo del texto de una celda de mapa de calor al ancho de SU celda.

    Con tres dígitos y una celda estrecha los valores se tocaban de borde a borde y no se sabía dónde acaba
    uno («-0.14-0.41»). Se reduce hasta 6 pt, que es el mínimo de la norma; por debajo no se baja."""
    from matplotlib.collections import QuadMesh
    meshes = [c for c in ax.collections if isinstance(c, QuadMesh)] + list(ax.images)
    if not meshes:
        return
    axb = _pl_extent(ax, r)
    if axb is None:
        return
    ncols = 0
    for m in meshes:
        arr = getattr(m, "get_array", lambda: None)()
        if arr is not None and getattr(arr, "shape", None):
            shape = arr.shape
            if len(shape) >= 2:
                ncols = max(ncols, int(shape[1]))
    if ncols <= 0:
        try:
            ncols = max(1, len(ax.get_xticks()))
        except (AttributeError, ValueError):
            return
    room = axb.width / ncols * 0.82
    for t in ax.texts:
        if t.get_transform() is not ax.transData or t.get_gid() == PLATE_KEEP:
            continue
        b = _pl_extent(t, r)
        while b is not None and b.width > room and t.get_size() > PLATE_FS_FLOOR:
            t.set_size(max(PLATE_FS_FLOOR, t.get_size() - 0.3))
            b = _pl_extent(t, r)
        # El valor de una celda de mapa de calor SOLO significa algo dentro de su celda: apartarlo para
        # resolver una colisión lo pondría en la celda vecina y cambiaría el dato que dice.
        t.set_gid(PLATE_KEEP)


def _pl_pin_shape_labels(ax, fig, r) -> None:
    """Fija el rótulo escrito DENTRO de una figura (celda de rejilla, segmento de barra) a esa figura.

    Un mapa de calor dibujado a mano con rectángulos —no con `pcolormesh`— no lo reconoce el ajuste de celda,
    y sus cifras quedaban a merced de la pasada de colisiones: en la Figura 2 (a) las cifras de la fila
    inferior acabaron impresas sobre la barra de color, a dos filas de la celda que describían. La regla es
    la misma que para una celda de mapa de calor: si el rótulo está escrito dentro de una figura, esa figura
    dice a qué se refiere y moverlo lo haría mentir. Se ajusta el cuerpo al ancho de la figura (nunca por
    debajo de 6 pt) y se marca para que nadie lo mueva.
    """
    patches = [(q, _pl_extent(q, r)) for q in ax.patches]
    patches = [(q, b) for q, b in patches if b is not None and b.width > 1.0 and b.height > 1.0]
    if not patches:
        return
    for t in ax.texts:
        if (t.get_gid() == PLATE_KEEP or getattr(t, "_pl_escaped", False)
                or t.get_transform() is not ax.transData or not str(t.get_text()).strip()):
            continue
        b = _pl_extent(t, r)
        if b is None:
            continue
        cx, cy = 0.5 * (b.x0 + b.x1), 0.5 * (b.y0 + b.y1)
        host = next((q for _p, q in patches if q.x0 <= cx <= q.x1 and q.y0 <= cy <= q.y1), None)
        if host is None:
            continue
        room = host.width * 0.94
        while b is not None and b.width > room and t.get_size() > PLATE_FS_FLOOR:
            t.set_size(max(PLATE_FS_FLOOR, t.get_size() - 0.3))
            b = _pl_extent(t, r)
        t.set_gid(PLATE_KEEP)


def _pl_clip_guard(fig, r) -> None:
    """Nada sale de su celda: lo que sobresale se devuelve dentro.

    Cubre los recortes que el informe señaló contra el borde del lienzo (un total troceado por el borde
    superior, una nota cortada a media palabra) y los que se producían contra el panel vecino."""
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        cell = plate_cell_box(fig, ax)
        bound = _pl_bbox(max(cell.x0 + 1.0, 1.0), max(cell.y0 + 1.0, 1.0),
                         min(cell.x1 - 1.0, fig.bbox.x1 - 1.0), min(cell.y1 - 1.0, fig.bbox.y1 - 1.0))
        for t in list(ax.texts) + [ax.xaxis.label, ax.yaxis.label]:
            if t is None or not t.get_visible() or not str(t.get_text()).strip() or t.get_gid() == PLATE_KEEP:
                continue
            b = _pl_extent(t, r)
            if b is None or _pl_out(b, bound) <= 0.5:
                continue
            guard = 0
            while b is not None and b.width > bound.width and t.get_size() > PLATE_FS_FLOOR and guard < 8:
                guard += 1
                t.set_size(max(PLATE_FS_FLOOR, t.get_size() - 0.4))
                b = _pl_extent(t, r)
            if b is None:
                continue
            dx = max(0.0, bound.x0 - b.x0) - max(0.0, b.x1 - bound.x1)
            dy = max(0.0, bound.y0 - b.y0) - max(0.0, b.y1 - bound.y1)
            if t is ax.xaxis.label or t is ax.yaxis.label:
                dy = 0.0        # subirlo lo imprimiría sobre las marcas que rotula
            if dx or dy:
                _pl_nudge(t, dx * 72.0 / fig.dpi, dy * 72.0 / fig.dpi, fig)


def _pl_title_fit(fig, r) -> None:
    """Repliega el título de panel que se sale de su celda por la derecha.

    El título se ancla al borde izquierdo de su celda y se pliega al ancho que en ese momento se creía
    disponible; cuando ese cálculo se queda corto por unos pocos puntos, la última palabra invade la celda
    vecina y se lee pegada al título del panel de al lado («…Smoothed ratiob REM P2 December…»). Aquí se
    mide el título YA DIBUJADO contra el borde real de su celda y se repliega si hace falta. El cuerpo no
    se toca: la norma fija el título de panel en 9 pt en negrita."""
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        t = next((c for c in (getattr(ax, "_left_title", None), ax.title) if c is not None and c.get_text()), None)
        if t is None or t.get_gid() == PLATE_KEEP:
            continue
        cell = plate_cell_box(fig, ax, topmost=True)
        # Canalón de 4 mm entre columnas: pegado al borde de su celda, el título de la izquierda se lee
        # como una sola palabra con el de la derecha («…Smoothed ratiob REM P2 December…») aunque
        # técnicamente no lo invada.
        gutter = fig.bbox.width * 4.0 / 180.0
        limit = min(cell.x1 - gutter, fig.bbox.x1 - 3.0)
        b = _pl_extent(t, r)
        if b is None or b.x1 <= limit:
            continue
        room_pt = max(70.0, (limit - b.x0) * 72.0 / fig.dpi)
        texto = " ".join(str(t.get_text()).split())
        t.set_text(plate_wrap(texto, room_pt, t.get_size(), "bold"))


def _pl_title_headroom(fig, r) -> None:
    """Baja el panel cuando su título, plegado en más líneas de las previstas, se sale del lienzo.

    Es el defecto de S35 en inglés: el título del panel (b) se plegaba a dos líneas DESPUÉS de repartir el
    lienzo, así que la primera línea —y con ella la letra del panel— quedaba cortada por el borde superior.
    Como el plegado depende del idioma, la comprobación tiene que hacerse sobre el título ya plegado y en
    cada idioma, nunca sobre el número de caracteres."""
    top = fig.bbox.y1 - 1.0
    for ax in fig.axes:
        if not ax.get_visible():
            continue
        t = next((c for c in (getattr(ax, "_left_title", None), ax.title) if c is not None and c.get_text()), None)
        if t is None:
            continue
        b = _pl_extent(t, r)
        if b is None or b.y1 <= top:
            continue
        over = (b.y1 - top) / fig.bbox.height
        pos = ax.get_position()
        new_h = pos.height - over
        if new_h > 0.02:
            ax.set_position([pos.x0, pos.y0, pos.width, new_h])


def _pl_lift_texts(fig) -> None:
    """Ningún rótulo se dibuja por debajo del dato que rotula."""
    for ax in fig.axes:
        for t in ax.texts:
            if t.get_zorder() < 5.0:
                t.set_zorder(5.0)


def _pl_backing(fig, r) -> None:
    """Recuadro blanco translúcido al rótulo oscuro que cae sobre la tinta del dato.

    Un «n=68» gris sobre la banda de confianza gris, o un valor sobre su propio marcador, se lee mal aunque
    esté por encima: el problema es de contraste, no de orden de dibujo. El recuadro se pone solo cuando hay
    tinta debajo y solo si el texto es oscuro: un rótulo blanco escrito dentro de una barra de color perdería
    su fondo y con él la legibilidad."""
    from matplotlib.colors import to_rgb
    for group in _pl_axes_groups(fig):
        occ, ext = _pl_group_ink(group, r)
        for ax in group:
            for t in ax.texts:
                if not t.get_visible() or not str(t.get_text()).strip() or t.get_bbox_patch() is not None:
                    continue
                try:
                    red, green, blue = to_rgb(t.get_color())
                except (ValueError, TypeError):
                    continue
                if 0.299 * red + 0.587 * green + 0.114 * blue > 0.92:
                    continue                     # rótulo blanco: su fondo es la barra en la que está escrito
                b = _pl_extent(t, r)
                if b is None:
                    continue
                area = max(1.0, (b.width / ext.width * occ.shape[1]) * (b.height / ext.height * occ.shape[0]))
                if _pl_ink_cost(occ, ext, b) / area > 0.25:
                    t.set_bbox(dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9))


def _pl_white_labels(fig, r) -> None:
    """Rescata el rótulo blanco escrito dentro de un segmento más delgado que él.

    En una barra apilada el valor se escribe en blanco DENTRO de su segmento. Cuando el segmento mide menos
    que el texto —«1.907 · 9,7 %» dentro de una franja de dos milímetros— la mitad del rótulo cae sobre el
    fondo blanco de la lámina y desaparece. Aquí se detecta el caso por medida, se pasa el rótulo a tinta
    oscura sobre recuadro claro y se deja que la pasada de colisiones lo lleve fuera del segmento.
    """
    from matplotlib.colors import to_rgb
    for ax in fig.axes:
        patches = [(p_, _pl_extent(p_, r)) for p_ in ax.patches]
        patches = [(p_, b) for p_, b in patches if b is not None]
        if not patches:
            continue
        for t in ax.texts:
            if not t.get_visible() or not str(t.get_text()).strip() or t.get_gid() == PLATE_KEEP:
                continue
            try:
                red, green, blue = to_rgb(t.get_color())
            except (ValueError, TypeError):
                continue
            if 0.299 * red + 0.587 * green + 0.114 * blue < 0.92:
                continue                                   # no es un rótulo blanco sobre color
            b = _pl_extent(t, r)
            if b is None:
                continue
            cx, cy = 0.5 * (b.x0 + b.x1), 0.5 * (b.y0 + b.y1)
            host = next((q for _p, q in patches if q.x0 <= cx <= q.x1 and q.y0 <= cy <= q.y1), None)
            if host is None:
                continue
            if host.height >= b.height * 1.1 and host.width >= b.width * 1.02:
                continue                                   # cabe: se queda donde está
            t.set_color("#222222")
            t.set_bbox(dict(facecolor="white", edgecolor="none", alpha=0.85, pad=0.9))
            t._pl_escaped = True        # este SÍ tiene que poder salir de su segmento


def plate_resolve(fig) -> None:
    """Segunda mitad del motor: se llama DESPUÉS de congelar la composición y justo antes de guardar."""
    _pl_lift_texts(fig)
    fig.canvas.draw()
    # Misma regla, segunda pasada: el módulo 13 no llama a `plate_fit`, y entre las dos mitades puede
    # nacer texto nuevo. Es idempotente y no dibuja si no cambia nada, de modo que detrás de la primera
    # pasada no deja rastro.
    plate_range_dash(fig)
    plate_pct_bind(fig)
    r = fig.canvas.get_renderer()
    _pl_white_labels(fig, r)
    # Modo revista (LANCET_PLATE_JOURNAL, apagado por omisión): los títulos de panel se reducen a la letra
    # ANTES de medir títulos y cabeceras, de modo que el reparto y el verificador ven la lámina que se guarda.
    if plate_journal_mode():
        journal_strip_titles(fig)
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
    # Los rótulos de eje se miden aquí, con la composición ya congelada: medidos antes, el motor de
    # reparto todavía movía los ejes y un rótulo que en el reparto provisional no cabía se plegaba en dos
    # líneas que, en la geometría definitiva, sobraban («…ratio (log» con su «escala)» perdida arriba).
    for ax in fig.axes:
        if ax.get_visible():
            try:
                _pl_fit_ylabel(ax, fig, r)
            except (ValueError, AttributeError, RuntimeError, TypeError, IndexError):
                continue
    _pl_title_fit(fig, r)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    _pl_title_headroom(fig, r)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    for group in _pl_axes_groups(fig):
        try:
            for ax in group:
                _pl_fit_cell_text(ax, fig, r)
                _pl_pin_shape_labels(ax, fig, r)
                # La leyenda se mide con la composición YA congelada. Medida antes, el reparto todavía
                # movía los ejes: una leyenda que en la geometría provisional cabía a dos columnas se
                # quedaba a dos columnas cuando el panel definitivo era más estrecho, y su columna derecha
                # se cortaba a media palabra («Entries: strict a…»), que es el defecto que el informe
                # señaló en la Figura 4 (d).
                _pl_fit_legend(ax, fig, r)
            obstacles = []
            for ax in group:
                lg = ax.get_legend()
                if lg is not None and lg.get_visible():
                    b = _pl_extent(lg, r)
                    if b is not None:
                        obstacles.append(b)
                t = next((c for c in (getattr(ax, "_left_title", None), ax.title)
                          if c is not None and c.get_text()), None)
                if t is not None:
                    b = _pl_extent(t, r)
                    if b is not None:
                        obstacles.append(b)
            occ, ext = _pl_group_ink(group, r)
            obstacles = _pl_relocate_notes(group, fig, r, occ, ext, obstacles)
            _pl_resolve_texts(group, fig, r, obstacles)
        except (ValueError, AttributeError, RuntimeError, TypeError, IndexError):
            continue
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    _pl_backing(fig, r)
    _pl_clip_guard(fig, r)
    # Puerta del verificador: TODA lámina del estudio pasa por aquí (los nueve módulos llaman a
    # `plate_resolve` justo antes de guardar), de modo que encender LANCET_PLATE_CHECK comprueba la
    # producción entera sin tocar ni un módulo. Apagada por omisión: no altera la reconstrucción.
    _plate_autocheck(fig)


# ===========================================================================
# Verificador de composición de lámina
# ---------------------------------------------------------------------------
# El motor de descongestión (arriba) MUEVE lo que se pisa; este verificador COMPRUEBA que ya no se pisa
# nada, sobre el renderizador real y con la lámina terminada. Treinta y tres de las cincuenta y nueve
# láminas llegaron a los verificadores humanos con un rótulo impreso sobre otro: leer cada página a tamaño
# de impresión no escala y el defecto vuelve en cuanto cambia un dato. `check_layout` mide lo mismo que
# leería un humano —cajas de texto, leyendas, marcadores, barras de error— y devuelve la lista de defectos;
# `assert_layout_clean` la convierte en un fallo ruidoso del módulo que dibuja la lámina.
#
# Familias de defecto (una constante por familia, tal como aparecen en el informe de verificación):
#   TEXT OVER TEXT                          dos textos cualesquiera que se solapan
#   TEXT OUTSIDE THE CANVAS                 texto que no cabe entero en el lienzo (títulos cortados en español)
#   AXIS TITLE OVER TICK LABELS             rótulo de eje (o del eje gemelo) sobre su propia columna de marcas
#   LEGEND OR ANNOTATION OVER DATA          leyenda o nota con recuadro encima de la tinta de datos
#   VALUE LABEL OVER ITS OWN MARKER OR ERROR BAR
#   VALUE LABEL MASKING ITS OWN BAR         recuadro del rótulo que tapa la longitud de la barra que rotula
#   NEIGHBOURING PANEL TITLES WITHOUT A GUTTER
#                                           dos títulos que no se solapan pero se leen como una sola frase
#   REPEATED TICK LABELS                    dos marcas NUMÉRICAS distintas del mismo eje con el mismo rótulo
#   PANEL COUNT                             lámina que no es de 3 × 2, o con más de seis paneles
# ===========================================================================
PLATE_STD_GRID = (3, 2)                 # filas × columnas de la norma
PLATE_MAX_PANELS = 6

TEXT_OVER_TEXT = "TEXT OVER TEXT"
TEXT_OUTSIDE_CANVAS = "TEXT OUTSIDE THE CANVAS"
AXIS_TITLE_OVER_TICKS = "AXIS TITLE OVER TICK LABELS"
LEGEND_OVER_DATA = "LEGEND OR ANNOTATION OVER DATA"
VALUE_LABEL_OVER_DATUM = "VALUE LABEL OVER ITS OWN MARKER OR ERROR BAR"
#: Los dos puntos ciegos que la fase 4e encontró LEYENDO la página, no midiéndola. El primero es el que
#: imprimió la Figura S37 (e) con la categoría MAYOR más corta que la segunda: el rótulo de la barra más
#: larga no cabía a su derecha, la pasada de colisiones lo devolvía sobre su propia barra y `_pl_backing`
#: le pintaba detrás un recuadro blanco translúcido que borraba la mitad de la barra. La familia
#: VALUE LABEL OVER ITS OWN MARKER OR ERROR BAR no lo veía porque mide marcadores y bigotes, no parches.
#: El segundo es el que imprimió la Figura S45 con «… 2019-2024 — Smoothed(b) GRD persons/year …»: los dos
#: títulos vecinos NO se solapan —el hueco es positivo, de 1,4 pt— y por eso TEXT OVER TEXT, que mide
#: solapes con 0,5 pt de tolerancia, los daba por buenos; lo que faltaba era exigir un hueco MÍNIMO.
BAR_MASKED_BY_LABEL = "VALUE LABEL MASKING ITS OWN BAR"
TITLES_WITHOUT_GUTTER = "NEIGHBOURING PANEL TITLES WITHOUT A GUTTER"
REPEATED_TICK_LABELS = "REPEATED TICK LABELS"
PANEL_COUNT = "PANEL COUNT"
PLATE_PROBLEM_KINDS = (TEXT_OVER_TEXT, TEXT_OUTSIDE_CANVAS, AXIS_TITLE_OVER_TICKS,
                       LEGEND_OVER_DATA, VALUE_LABEL_OVER_DATUM, BAR_MASKED_BY_LABEL,
                       TITLES_WITHOUT_GUTTER, REPEATED_TICK_LABELS, PANEL_COUNT)

#: Sentinela: «usa la rejilla declarada en la figura, y si no la hay, la de la norma».
_PL_GRID_AUTO = object()


class PlateProblem:
    """Un defecto de composición: qué familia, en qué panel, entre qué artistas y cuánto se solapan.

    `overlap_pt` es la PENETRACIÓN en puntos tipográficos —el lado menor del rectángulo de intersección—,
    que es la magnitud que se lee en la página: 0,5 pt es el roce de dos cajas que se tocan, 4 pt es un
    rótulo impreso encima de otro. Para «fuera del lienzo» es cuánto sobresale; para «leyenda sobre datos»
    la fracción tapada viaja en `detail` y en `fraction`.
    """
    __slots__ = ("kind", "axes", "artists", "overlap_pt", "detail", "objects", "fraction")

    def __init__(self, kind, axes, artists, overlap_pt=0.0, detail="", objects=(), fraction=None):
        self.kind = str(kind)
        self.axes = str(axes)
        self.artists = tuple(str(a) for a in artists)
        self.overlap_pt = float(overlap_pt)
        self.detail = str(detail)
        self.objects = tuple(objects)
        self.fraction = fraction

    def __str__(self):
        s = f"{self.kind} — {self.axes}: " + " × ".join(self.artists)
        if self.overlap_pt:
            s += f" — overlap {self.overlap_pt:.2f} pt"
        if self.fraction is not None:
            s += f" — {100.0 * self.fraction:.0f}% of the data element covered"
        if self.detail:
            s += f" ({self.detail})"
        return s

    __repr__ = __str__

    def as_dict(self) -> dict:
        return dict(kind=self.kind, axes=self.axes, artists=list(self.artists),
                    overlap_pt=round(self.overlap_pt, 3), fraction=self.fraction, detail=self.detail)


class PlateLayoutError(AssertionError):
    """Lámina con defectos de composición: lleva la lista completa, no solo el primero."""

    def __init__(self, name, problems):
        self.name = str(name)
        self.problems = list(problems)
        lines = [f"{self.name}: {len(self.problems)} layout problem(s) — the plate would print illegible"]
        lines += [f"  {i:>2}. {p}" for i, p in enumerate(self.problems, 1)]
        super().__init__("\n".join(lines))


# ---------------------------------------------------------------------------
# Utilidades del verificador
# ---------------------------------------------------------------------------
def _pl_renderer(fig, draw: bool = True):
    """Renderizador REAL de la figura (el mismo con el que se guardará), dibujando si hace falta."""
    if draw:
        fig.canvas.draw()
    try:
        return fig.canvas.get_renderer()
    except AttributeError:
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        FigureCanvasAgg(fig)
        fig.canvas.draw()
        return fig.canvas.get_renderer()


def _pl_pt(fig, px: float) -> float:
    return float(px) * 72.0 / fig.dpi


def _pl_inter(a, b) -> tuple:
    """Ancho y alto del rectángulo de intersección (0, 0 si no se tocan)."""
    return (max(0.0, min(a.x1, b.x1) - max(a.x0, b.x0)),
            max(0.0, min(a.y1, b.y1) - max(a.y0, b.y0)))


def _pl_is_colorbar(ax) -> bool:
    return getattr(ax, "_colorbar", None) is not None or getattr(ax, "_colorbar_info", None) is not None


def _pl_inset_ids(fig) -> set:
    """Ejes ENCARTADOS (`ax.inset_axes`): son hijos de un panel, no paneles de la rejilla."""
    out = set()
    for ax in _pl_all_axes(fig):
        for ch in (getattr(ax, "child_axes", None) or []):
            out.add(id(ch))
    return out


def _pl_all_axes(fig) -> list:
    """Todos los ejes dibujados, incluidos los encartados (que NO están en `fig.axes`)."""
    out, queue = [], list(fig.axes)
    seen = set()
    while queue:
        ax = queue.pop(0)
        if id(ax) in seen:
            continue
        seen.add(id(ax))
        out.append(ax)
        queue.extend(getattr(ax, "child_axes", None) or [])
    return out


def _pl_cell_key(ax):
    """Celda de la lámina a la que pertenece un panel: (fila, columna) de la rejilla de primer nivel."""
    sp = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
    if sp is None:
        pos = ax.get_position()
        return (round(1.0 - pos.y1, 3), round(pos.x0, 3), None, None)
    try:
        top = sp.get_topmost_subplotspec()
    except (AttributeError, ValueError):
        top = sp
    return (top.rowspan.start, top.colspan.start, top.rowspan.stop, top.colspan.stop)


def _pl_name_map(fig) -> dict:
    """Nombre legible de cada eje: «panel (a)», «panel (b) [twin]», «panel (c) [colour bar]», «[inset]».

    El verificador tiene que decir DÓNDE está el defecto con el mismo vocabulario que usa la leyenda de la
    figura: el autor lee «panel (f)» y sabe qué mirar."""
    insets = _pl_inset_ids(fig)
    everything = _pl_all_axes(fig)
    cells, roles = {}, {}
    for ax in everything:
        if _pl_is_colorbar(ax):
            roles[id(ax)] = "colour bar"
        elif id(ax) in insets:
            roles[id(ax)] = "inset"
        else:
            roles[id(ax)] = ""
    # Las celdas se numeran en orden de lectura sobre los paneles de verdad (ni barras de color ni encartes).
    keys = []
    for ax in everything:
        if roles[id(ax)]:
            continue
        k = _pl_cell_key(ax)
        cells[id(ax)] = k
        if k not in keys:
            keys.append(k)
    keys.sort(key=lambda k: (k[0], k[1]))
    letters = {k: chr(ord("a") + i) if i < 26 else f"#{i + 1}" for i, k in enumerate(keys)}
    # una barra de color o un encarte heredan la letra del panel que los contiene
    def owner_letter(ax) -> str:
        k = _pl_cell_key(ax)
        if k in letters:
            return letters[k]
        pos = ax.get_position()
        cx, cy = pos.x0 + pos.width / 2.0, pos.y0 + pos.height / 2.0
        # Una barra de color o un encarte heredan la letra del panel que los contiene y, si el reparto los
        # ha sacado fuera de él (constrained_layout aparta la barra al margen), la del panel más cercano.
        best, best_d = None, np.inf
        for other in everything:
            if roles[id(other)] or other is ax:
                continue
            q = other.get_position()
            if q.x0 - 0.02 <= cx <= q.x1 + 0.02 and q.y0 - 0.02 <= cy <= q.y1 + 0.02:
                return letters.get(_pl_cell_key(other), "?")
            d = abs(q.x0 + q.width / 2.0 - cx) + abs(q.y0 + q.height / 2.0 - cy)
            if d < best_d:
                best, best_d = other, d
        return letters.get(_pl_cell_key(best), "?") if best is not None else "?"

    seen_pos: dict = {}
    names = {}
    for ax in everything:
        role = roles[id(ax)]
        letter_ = letters.get(cells.get(id(ax)), None) or owner_letter(ax)
        tag = ""
        if role:
            tag = f" [{role}]"
        else:
            pos = ax.get_position()
            key = (round(pos.x0, 4), round(pos.y0, 4), round(pos.x1, 4), round(pos.y1, 4))
            if key in seen_pos:
                tag = " [twin]"
            else:
                seen_pos[key] = ax
        names[id(ax)] = f"panel ({letter_}){tag}"
    return names


def _pl_ink_box(t, b, dpi: float = 100.0):
    """Caja de TINTA aproximada de un texto: la de composición menos el aire de la línea tipográfica.

    La caja que devuelve matplotlib incluye el ascendente y el descendente de la fuente, de modo que dos
    textos separados por un pelo se «solapan» un punto sin que sus trazos se toquen. Denunciar eso manda a
    los autores a perseguir fantasmas; recortar el aire deja pasar el roce y sigue viendo el defecto real."""
    lines = max(1, str(t.get_text()).count("\n") + 1)
    dy = min(0.13 * b.height / lines, 1.6 * dpi / 72.0) if b.height > 0 else 0.0
    dx = min(0.06 * b.width, 0.6 * dpi / 72.0) if b.width > 0 else 0.0
    if abs(float(t.get_rotation()) % 180.0 - 90.0) < 30.0:      # rótulo girado: el aire está en la x
        dx, dy = dy, dx
    return _pl_bbox(b.x0 + dx, b.y0 + dy, b.x1 - dx, b.y1 - dy)


def _pl_shorten(s, n: int = 46) -> str:
    s = " ".join(str(s).split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _pl_desc(art, role: str = "") -> str:
    """Descripción corta de un artista, con su texto o su etiqueta de leyenda."""
    from matplotlib.legend import Legend
    from matplotlib.lines import Line2D
    from matplotlib.patches import Rectangle
    from matplotlib.text import Text
    from matplotlib.container import ErrorbarContainer
    if isinstance(art, Legend):
        return f"legend ({len(art.get_texts())} entries)"
    if isinstance(art, ErrorbarContainer):
        lab = _pl_shorten(str(art.get_label() or ""), 24)
        return f"error bars '{lab}'" if lab and not lab.startswith("_") else "error bars"
    if isinstance(art, Text):
        return f"{role or 'text'} '{_pl_shorten(art.get_text())}'"
    label = str(getattr(art, "get_label", lambda: "")() or "")
    label = "" if label.startswith("_") else f" '{_pl_shorten(label, 24)}'"
    if isinstance(art, Line2D):
        return f"line{label}"
    if isinstance(art, Rectangle):
        return f"bar{label}"
    return f"{type(art).__name__}{label}"


def _pl_text_items(fig, r, names) -> list:
    """Inventario de TODO el texto dibujado: marcas, rótulos de eje, títulos, notas, leyendas y texto de figura.

    Cada entrada trae el artista, su eje, el nombre del panel, el papel que cumple y su caja de pantalla."""
    items = []

    def add(t, ax, role):
        if t is None or not t.get_visible():
            return
        if not str(t.get_text()).strip():
            return
        try:
            if float(t.get_alpha() if t.get_alpha() is not None else 1.0) < 0.05:
                return
        except (TypeError, ValueError):
            pass
        b = _pl_extent(t, r)
        if b is None:
            return
        items.append(dict(t=t, ax=ax, axes=names.get(id(ax), "figure") if ax is not None else "figure",
                          role=role, box=b, ink=_pl_ink_box(t, b, fig.dpi)))

    for ax in _pl_all_axes(fig):
        if not ax.get_visible():
            continue
        for cand, role in ((getattr(ax, "_left_title", None), "panel title"),
                           (ax.title, "panel title"),
                           (getattr(ax, "_right_title", None), "panel title")):
            add(cand, ax, role)
        # `set_axis_off()` —los mapas de la Figura S9, el lienzo del diagrama— no dibuja NINGUNA marca ni
        # rótulo de eje, aunque cada artista siga diciendo que es visible: contarlos denunciaba veinte
        # recortes falsos por lámina de mapas («1.750.000» cortado por la izquierda) que no se imprimen.
        if getattr(ax, "axison", True):
            if ax.xaxis.get_visible():
                add(ax.xaxis.label, ax, "x-axis title")
            if ax.yaxis.get_visible():
                add(ax.yaxis.label, ax, "y-axis title")
            for axis, role in ((ax.xaxis, "x tick label"), (ax.yaxis, "y tick label")):
                for lab in _pl_tick_texts(axis):
                    add(lab, ax, role)
                try:
                    add(axis.get_offset_text(), ax, "axis offset")
                except AttributeError:
                    pass
        for t in ax.texts:
            add(t, ax, "annotation" if type(t).__name__ == "Annotation" else "panel text")
        lg = ax.get_legend()
        if lg is not None and lg.get_visible():
            for t in lg.get_texts():
                add(t, ax, "legend entry")
            if lg.get_title() is not None:
                add(lg.get_title(), ax, "legend title")
    for t in fig.texts:
        add(t, None, "figure text")
    if getattr(fig, "_suptitle", None) is not None:
        add(fig._suptitle, None, "figure title")
    for lg in getattr(fig, "legends", []):
        if lg.get_visible():
            for t in lg.get_texts():
                add(t, None, "figure legend entry")
    return items


def _pl_tick_texts(axis) -> list:
    """Rótulos de marca REALMENTE dibujados: los de las marcas dentro del intervalo visible del eje.

    Un eje entero invisible no dibuja nada: `twinx()` apaga el eje X del gemelo, y sus rótulos siguen
    diciendo que son visibles aunque no se impriman. Contarlos denunciaba siete choques falsos por panel
    («2019» sobre «2019») en toda lámina con eje gemelo."""
    out = []
    if not axis.get_visible():
        return out
    try:
        lo, hi = sorted(axis.get_view_interval())
    except (AttributeError, ValueError, TypeError):
        lo, hi = -np.inf, np.inf
    span = (hi - lo) if np.isfinite(hi - lo) else 0.0
    slack = 1e-7 * max(1.0, abs(span))
    try:
        ticks = list(axis.get_major_ticks()) + list(axis.get_minor_ticks())
    except (AttributeError, ValueError, RuntimeError):
        return out
    for tick in ticks:
        try:
            loc = tick.get_loc()
        except (AttributeError, ValueError, TypeError):
            loc = None
        if loc is not None and np.isfinite(loc) and not (lo - slack <= loc <= hi + slack):
            continue
        for lab in (getattr(tick, "label1", None), getattr(tick, "label2", None)):
            if lab is not None and lab.get_visible() and str(lab.get_text()).strip():
                out.append(lab)
    return out


def _pl_axis_owner(item) -> str:
    """Devuelve 'x' o 'y' si el texto pertenece a un eje concreto (rótulo o marca), o '' si no."""
    role = item["role"]
    if role in ("x-axis title", "x tick label"):
        return "x"
    if role in ("y-axis title", "y tick label"):
        return "y"
    return ""


# ---------------------------------------------------------------------------
# Tinta de datos: qué fracción de un elemento tapa un rectángulo
# ---------------------------------------------------------------------------
def _pl_data_artists(ax) -> list:
    """Artistas que llevan DATO en este panel, en coordenadas de dato.

    Se excluye deliberadamente lo que está dibujado en coordenadas mixtas —la línea de la Ley, la banda de
    la pandemia, las líneas de referencia—: son contexto, y una leyenda sobre ellas no oculta ningún dato."""
    from matplotlib.collections import Collection
    out = []
    for ln in ax.lines:
        if not ln.get_visible():
            continue
        if ln.get_transform() is not ax.transData:
            continue
        try:
            if len(ln.get_xydata()) == 0:
                continue
        except (ValueError, TypeError):
            continue
        out.append(ln)
    for p in ax.patches:
        if not p.get_visible():
            continue
        try:
            if p.get_data_transform() is not ax.transData:
                continue
        except (AttributeError, ValueError):
            continue
        out.append(p)
    for c in ax.collections:
        if not c.get_visible():
            continue
        try:
            tr_ok = (c.get_offset_transform() is ax.transData) or (c.get_transform() is ax.transData)
        except (AttributeError, ValueError):
            tr_ok = False
        if isinstance(c, Collection) and tr_ok:
            out.append(c)
    for im in ax.images:
        if im.get_visible():
            out.append(im)
    return out


def _pl_line_points(ln, dense: int = 24):
    """Puntos de pantalla de una línea, densificando cada segmento (una recta larga solo tiene dos vértices)."""
    try:
        pts = np.asarray(ln.get_transform().transform(ln.get_xydata()), dtype=float)
    except (ValueError, TypeError, AttributeError):
        return np.empty((0, 2))
    pts = pts[np.isfinite(pts).all(axis=1)] if pts.ndim == 2 and len(pts) else np.empty((0, 2))
    if len(pts) < 2:
        return pts
    t = np.linspace(0.0, 1.0, dense)[:, None, None]
    return (pts[None, :-1, :] * (1 - t) + pts[None, 1:, :] * t).reshape(-1, 2)


def _pl_inside(pts, box) -> float:
    if not len(pts):
        return 0.0
    inside = ((pts[:, 0] >= box.x0) & (pts[:, 0] <= box.x1)
              & (pts[:, 1] >= box.y0) & (pts[:, 1] <= box.y1))
    return float(inside.mean())


def _pl_cover_frac(box, art, r) -> float:
    """Fracción del elemento de datos que queda BAJO el rectángulo (0 = no lo toca, 1 = lo tapa entero)."""
    from matplotlib.collections import Collection, LineCollection
    from matplotlib.container import ErrorbarContainer
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    if isinstance(art, ErrorbarContainer):
        return max([_pl_cover_frac(box, c, r) for c in _pl_container_parts(art)] or [0.0])
    if isinstance(art, Line2D):
        return _pl_inside(_pl_line_points(art), box)
    if isinstance(art, LineCollection):
        pts = []
        try:
            tr = art.get_transform()
            for seg in art.get_segments():
                seg = np.asarray(seg, dtype=float)
                if len(seg) >= 2:
                    q = np.asarray(tr.transform(seg), dtype=float)
                    t = np.linspace(0.0, 1.0, 12)[:, None, None]
                    pts.append((q[None, :-1, :] * (1 - t) + q[None, 1:, :] * t).reshape(-1, 2))
        except (ValueError, TypeError, AttributeError):
            pts = []
        return _pl_inside(np.vstack(pts) if pts else np.empty((0, 2)), box)
    if isinstance(art, Collection):
        try:
            off = np.asarray(art.get_offset_transform().transform(art.get_offsets()), dtype=float)
        except (ValueError, TypeError, AttributeError):
            off = np.empty((0, 2))
        if off.ndim == 2 and len(off):
            return _pl_inside(off, box)
    b = _pl_extent(art, r)
    if b is None or b.width <= 0 or b.height <= 0:
        return 0.0
    iw, ih = _pl_inter(box, b)
    if isinstance(art, Patch) and (b.width <= 1.5 or b.height <= 1.5):
        return 1.0 if iw > 0 and ih > 0 else 0.0
    return float(iw * ih) / float(b.width * b.height)


def _pl_container_parts(cont) -> list:
    parts = []
    lines = getattr(cont, "lines", ())
    for piece in lines:
        if piece is None:
            continue
        if isinstance(piece, (tuple, list)):
            parts.extend([q for q in piece if q is not None])
        else:
            parts.append(piece)
    return parts


def _pl_boxed(t) -> bool:
    """Un texto con recuadro: tapa lo que hay debajo aunque el recuadro sea translúcido."""
    patch = t.get_bbox_patch()
    if patch is None:
        return False
    try:
        return float(patch.get_alpha() if patch.get_alpha() is not None else 1.0) > 0.05
    except (TypeError, ValueError):
        return True


# ---------------------------------------------------------------------------
# Las seis comprobaciones
# ---------------------------------------------------------------------------
def _ck_texts(fig, r, items, tol_px, names) -> list:
    """TEXT OVER TEXT, AXIS TITLE OVER TICK LABELS y TEXT OUTSIDE THE CANVAS."""
    out = []
    canvas = fig.bbox
    for it in items:
        b = it["ink"]
        over = _pl_out(b, canvas)
        if over > tol_px:
            sides = []
            if b.x0 < canvas.x0 - tol_px:
                sides.append("left")
            if b.x1 > canvas.x1 + tol_px:
                sides.append("right")
            if b.y0 < canvas.y0 - tol_px:
                sides.append("bottom")
            if b.y1 > canvas.y1 + tol_px:
                sides.append("top")
            out.append(PlateProblem(TEXT_OUTSIDE_CANVAS, it["axes"], [_pl_desc(it["t"], it["role"])],
                                    _pl_pt(fig, over), detail="clipped at the " + "/".join(sides or ["edge"]),
                                    objects=[it["t"]]))
    n = len(items)
    for i in range(n):
        a = items[i]
        for j in range(i + 1, n):
            b = items[j]
            if a["t"] is b["t"]:
                continue
            iw, ih = _pl_inter(a["ink"], b["ink"])
            if iw <= tol_px or ih <= tol_px:
                continue
            pen = _pl_pt(fig, min(iw, ih))
            kind, axes = TEXT_OVER_TEXT, a["axes"] if a["axes"] == b["axes"] else f"{a['axes']} / {b['axes']}"
            if a["ax"] is not None and a["ax"] is b["ax"]:
                roles = {a["role"], b["role"]}
                for side in ("x", "y"):
                    if roles == {f"{side}-axis title", f"{side} tick label"}:
                        kind = AXIS_TITLE_OVER_TICKS
            out.append(PlateProblem(kind, axes,
                                    [_pl_desc(a["t"], a["role"]), _pl_desc(b["t"], b["role"])],
                                    pen, objects=[a["t"], b["t"]]))
    return out


def _pl_check_groups(fig) -> list:
    """Grupos de ejes que comparten rectángulo (gemelos) más cada encarte como grupo propio."""
    groups = _pl_axes_groups(fig)
    known = {id(a) for g in groups for a in g}
    for ax in _pl_all_axes(fig):
        if id(ax) not in known and ax.get_visible():
            groups.append([ax])
    return groups


def _ck_boxes_over_data(fig, r, names, data_frac, tol_px) -> list:
    """LEGEND OR ANNOTATION OVER DATA."""
    out = []
    for group in _pl_check_groups(fig):
        data = [(ax, art) for ax in group for art in _pl_data_artists(ax)]
        if not data:
            continue
        covers = []
        for ax in group:
            lg = ax.get_legend()
            if lg is not None and lg.get_visible():
                b = _pl_extent(lg, r)
                if b is not None:
                    covers.append((ax, lg, b, "legend"))
            for t in ax.texts:
                if not t.get_visible() or not str(t.get_text()).strip() or t.get_gid() == PLATE_KEEP:
                    continue
                if not (_pl_boxed(t) or type(t).__name__ == "Annotation"):
                    continue
                # Un rótulo anclado a un DATO (el nombre de una región dentro de su polígono, el valor
                # dentro de su barra, la cifra de una celda de mapa de calor) está encima de la tinta por
                # definición y ahí es donde tiene que estar: lo que se persigue aquí es la NOTA de panel
                # —escrita en coordenadas de eje— que cae sobre la serie que describe.
                if _pl_in_data_coords(t, ax):
                    continue
                b = _pl_extent(t, r)
                if b is not None:
                    covers.append((ax, t, b, "boxed note"))
        for ax, cov, box, role in covers:
            for own, art in data:
                if art is cov:
                    continue
                frac = _pl_cover_frac(box, art, r)
                if frac <= data_frac:
                    continue
                ab = _pl_extent(art, r)
                iw, ih = _pl_inter(box, ab) if ab is not None else (0.0, 0.0)
                out.append(PlateProblem(LEGEND_OVER_DATA, names.get(id(ax), "figure"),
                                        [_pl_desc(cov, role), _pl_desc(art)],
                                        _pl_pt(fig, min(iw, ih)), fraction=frac, objects=[cov, art]))
    return out


def _pl_markers_and_bars(group, r) -> tuple:
    """Marcadores y barras de error de un grupo de ejes, en coordenadas de pantalla.

    Los marcadores vuelven como una matriz de TRES columnas: x, y y el RADIO del disco en píxeles. El
    radio importa: un marcador no es un punto, y preguntar sólo por su centro deja que un rótulo tape
    media chincheta sin coste alguno —era el defecto de la S12 (f), con un disco del que sólo asomaba
    un quince por ciento—. Con el radio, la prueba de pertenencia se hace contra el disco entero.
    """
    from matplotlib.collections import LineCollection
    from matplotlib.container import ErrorbarContainer
    px = float(getattr(getattr(group[0], "figure", None), "dpi", 100.0)) / 72.0 if len(group) else 1.0
    marks, bars = [], []

    def add(pts, radius_pt):
        pts = np.asarray(pts, dtype=float)
        if pts.ndim != 2 or not len(pts):
            return
        pts = pts[np.isfinite(pts).all(axis=1)]
        if not len(pts):
            return
        rad = np.full((len(pts), 1), max(0.0, float(radius_pt)) * px)
        marks.append(np.hstack([pts[:, :2], rad]))

    for ax in group:
        for cont in getattr(ax, "containers", []):
            if not isinstance(cont, ErrorbarContainer):
                continue
            for piece in _pl_container_parts(cont):
                if isinstance(piece, LineCollection):
                    try:
                        tr = piece.get_transform()
                        for seg in piece.get_segments():
                            seg = np.asarray(seg, dtype=float)
                            if len(seg) >= 2:
                                bars.append(np.asarray(tr.transform(seg), dtype=float))
                    except (ValueError, TypeError, AttributeError):
                        continue
        for ln in ax.lines:
            if not ln.get_visible() or ln.get_transform() is not ax.transData:
                continue
            marker = ln.get_marker()
            if marker in (None, "", " ", "None"):
                continue
            try:
                pts = np.asarray(ln.get_transform().transform(ln.get_xydata()), dtype=float)
            except (ValueError, TypeError, AttributeError):
                continue
            try:
                rad_pt = 0.5 * float(ln.get_markersize())      # markersize es el DIÁMETRO, en puntos
            except (TypeError, ValueError):
                rad_pt = 0.0
            add(pts, rad_pt)
        for c in ax.collections:
            try:
                off = np.asarray(c.get_offset_transform().transform(c.get_offsets()), dtype=float)
            except (ValueError, TypeError, AttributeError):
                continue
            try:
                sizes = np.asarray(c.get_sizes(), dtype=float)   # s de scatter: ÁREA en puntos²
                s = float(np.nanmax(sizes)) if sizes.size else 0.0
                rad_pt = 0.5 * float(np.sqrt(max(0.0, s)))
            except (TypeError, ValueError, AttributeError):
                rad_pt = 0.0
            add(off, rad_pt)
    m = np.vstack(marks) if marks else np.empty((0, 3))
    return m, bars


def _pl_marker_radii(marks):
    """Radios (px) de la matriz de marcadores; cero si viene sin la tercera columna."""
    if marks is None or not len(marks):
        return np.zeros(0)
    return marks[:, 2] if marks.shape[1] > 2 else np.zeros(len(marks))


#: Fracción del DISCO de un marcador que un rótulo de valor puede tapar sin que se denuncie. Un marcador
#: no es un punto: preguntar sólo por su centro dejaba tapar media chincheta sin coste (el defecto de la
#: S12 (f), con un disco del que asomaba un quince por ciento), pero inflar la caja el radio entero
#: denunciaba el roce de una décima de punto en catorce láminas que se leen perfectamente. Lo que se mide
#: es cuánto del disco queda cubierto, y un dieciseisavo es el umbral: por debajo, el marcador se ve.
PLATE_MARKER_COVER = 1.0 / 16.0

def _pl_disc_samples(n_rings: int = 4, n_ang: int = 16):
    """Muestreo del disco unidad con puntos de IGUAL ÁREA (anillos en sqrt((k+½)/n)).

    Sirve para estimar qué fracción de un marcador cubre una caja de texto sin integrar analíticamente
    el área de una intersección círculo-rectángulo, que no tiene forma cerrada corta."""
    pts = []
    for k in range(n_rings):
        rr = float(np.sqrt((k + 0.5) / n_rings))
        for j in range(n_ang):
            a = 2.0 * np.pi * (j + 0.5 * (k % 2)) / n_ang
            pts.append((rr * np.cos(a), rr * np.sin(a)))
    return np.asarray(pts, dtype=float)


_PL_DISC = _pl_disc_samples()


def _pl_marker_cover(box, marks):
    """Fracción del disco de cada marcador cubierta por `box` (0 fuera, 1 tapado entero).

    Devuelve `(idx, frac)` sólo de los marcadores que TOCAN la caja: los demás no se muestrean."""
    if marks is None or not len(marks):
        return np.zeros(0, dtype=int), np.zeros(0)
    rad = _pl_marker_radii(marks)
    near = ((marks[:, 0] >= box.x0 - rad) & (marks[:, 0] <= box.x1 + rad)
            & (marks[:, 1] >= box.y0 - rad) & (marks[:, 1] <= box.y1 + rad))
    idx = np.flatnonzero(near)
    if not len(idx):
        return idx, np.zeros(0)
    fracs = np.empty(len(idx))
    for i, j in enumerate(idx):
        r = float(rad[j])
        if r <= 0.0:
            fracs[i] = 1.0                       # sin radio conocido: el centro dentro es tapado entero
            continue
        pts = _PL_DISC * r + marks[j, :2]
        inside = ((pts[:, 0] >= box.x0) & (pts[:, 0] <= box.x1)
                  & (pts[:, 1] >= box.y0) & (pts[:, 1] <= box.y1))
        fracs[i] = float(inside.mean())
    return idx, fracs


def _ck_value_labels(fig, r, names, tol_px) -> list:
    """VALUE LABEL OVER ITS OWN MARKER OR ERROR BAR."""
    out = []
    for group in _pl_check_groups(fig):
        marks, bars = _pl_markers_and_bars(group, r)
        if not len(marks) and not bars:
            continue
        for ax in group:
            for t in ax.texts:
                if not t.get_visible() or not str(t.get_text()).strip() or t.get_gid() == PLATE_KEEP:
                    continue
                if not _pl_in_data_coords(t, ax):
                    continue
                b = _pl_extent(t, r)
                if b is None:
                    continue
                inner = _pl_bbox(b.x0 + tol_px, b.y0 + tol_px, b.x1 - tol_px, b.y1 - tol_px)
                if inner.width <= 0 or inner.height <= 0:
                    continue
                hit = None
                if len(marks):
                    # El marcador es un DISCO, no un punto: se mide qué FRACCIÓN del disco tapa la caja.
                    # Preguntar sólo por el centro dejaba tapar media chincheta sin coste (S12 (f));
                    # inflar la caja el radio entero denunciaba el roce de una décima de punto. El umbral
                    # es `PLATE_MARKER_COVER`: por debajo, el marcador se sigue viendo.
                    idx, cover = _pl_marker_cover(inner, marks)
                    bad = np.flatnonzero(cover > PLATE_MARKER_COVER)
                    if len(bad):
                        worst = int(np.argmax(cover[bad]))
                        j = int(idx[bad[worst]])
                        p, rp = marks[j], float(_pl_marker_radii(marks)[j])
                        depth = min(p[0] - (inner.x0 - rp), (inner.x1 + rp) - p[0],
                                    p[1] - (inner.y0 - rp), (inner.y1 + rp) - p[1])
                        hit = ("its own marker", depth, int(len(bad)), float(cover[bad][worst]))
                if hit is None:
                    for seg in bars:
                        q = np.linspace(0.0, 1.0, 24)[:, None]
                        pts = seg[0][None, :] * (1 - q) + seg[-1][None, :] * q
                        inside = ((pts[:, 0] >= inner.x0) & (pts[:, 0] <= inner.x1)
                                  & (pts[:, 1] >= inner.y0) & (pts[:, 1] <= inner.y1))
                        if inside.any():
                            hit = ("an error bar", float(inside.mean() * min(inner.width, inner.height)), 1,
                                   None)
                            break
                if hit is None:
                    continue
                what, depth, count, frac = hit
                out.append(PlateProblem(VALUE_LABEL_OVER_DATUM, names.get(id(ax), "figure"),
                                        [_pl_desc(t, "value label"), what],
                                        _pl_pt(fig, max(depth, 0.0)),
                                        detail=f"{count} datum/data under the label", objects=[t],
                                        fraction=frac))
    return out


def _pl_in_data_coords(t, ax) -> bool:
    """¿El texto está anclado a un DATO? (rótulo de valor) — frente a coordenadas de eje (nota de panel)."""
    from matplotlib.text import Annotation
    if isinstance(t, Annotation):
        xc = t.xycoords if isinstance(t.xycoords, str) else None
        return xc in (None, "data") or t.xycoords is ax.transData
    tr = getattr(t, "_pl_base_tr", None) or t.get_transform()
    return tr is ax.transData


#: Fracción de la LONGITUD de una barra que puede quedar bajo el recuadro de un rótulo antes de que la
#: barra se lea más corta de lo que es. En la S37 (e) el recuadro tapaba el 50 % de la barra mayor y la
#: imprimía por debajo de la segunda; por debajo de este umbral el recuadro se nota pero no falsea nada.
PLATE_BAR_MASK = 0.20

#: …y sólo cuenta si el recuadro cruza la barra DE LADO A LADO. Sin esta segunda condición la familia
#: denunciaba la Figura 4 (c), donde los rótulos van girados 90° al costado de cada barra y su recuadro
#: muerde uno o dos píxeles del borde: medido sobre el PNG a 600 ppp, entre el 1 % y el 10 % de la tinta
#: de cada barra y NI UNA sola fila de la barra tapada de lado a lado, es decir, ninguna barra acortada.
#: Un recuadro que no cruza la barra deja su silueta entera y no puede hacerla leer más corta.
PLATE_BAR_MASK_ACROSS = 0.5

#: …y sólo si lo que la barra PIERDE se puede ver. La familia denuncia que una barra se imprima más corta
#: de lo que vale, y una merma de menos de milímetro y medio no se mide a ojo en la página: el recuadro se
#: nota, la longitud no cambia de lectura. Con un umbral sólo relativo la familia denunciaba el rótulo
#: «202» de la Figura S15 (c) —segmento rojo de 1,7 pt del que el recuadro cubre 1,38, el 81 % de una
#: barra que no llega a los dos puntos, y que además se imprime en color PURO— y los rótulos «−9», «−5» y
#: «−11» de la Figura S44 (a), que pierden 2,3 pt cada uno. Los tres defectos REALES de esta fase pierden
#: 46 pt (S37 e), 21 pt (Figura 4 c) y 8 pt (S29 e): el umbral los separa sin rozarlos.
PLATE_BAR_MASK_MIN_PT = 4.0

#: Hueco mínimo, en puntos, entre los títulos de dos paneles VECINOS. Menos que esto y el lector no ve
#: dónde acaba uno y empieza el otro: el espacio de palabra DENTRO de un título de 9 pt mide 4,3 pt, de
#: modo que un hueco de 1,4 pt entre dos títulos es menos de un tercio de la separación entre sus palabras.
PLATE_TITLE_GUTTER_PT = 6.0


def _pl_bar_patches(ax, r) -> list:
    """Los rectángulos de `ax` que son BARRAS, con la dirección en la que cada una crece.

    Una barra arranca de una base común: todas las de un panel comparten su `x` de origen (horizontales,
    `barh`) o su `y` de origen (verticales, `bar`). Un mapa de calor dibujado con rectángulos no comparte
    ninguna de las dos —cada celda tiene origen propio en las dos direcciones—, así que este filtro lo
    deja fuera, y con él los recuadros de contraste que la norma acepta sobre las matrices."""
    from matplotlib.patches import Rectangle
    rects = [p_ for p_ in ax.patches
             if type(p_) is Rectangle and p_.get_visible()
             and float(p_.get_width() or 0.0) and float(p_.get_height() or 0.0)]
    if len(rects) < 2:
        return []
    xs = [round(float(p_.get_x()), 9) for p_ in rects]
    ys = [round(float(p_.get_y()), 9) for p_ in rects]
    share_x = max(xs.count(v) for v in set(xs)) / len(rects)
    share_y = max(ys.count(v) for v in set(ys)) / len(rects)
    if max(share_x, share_y) < 0.6:
        return []
    horizontal = share_x >= share_y          # todas arrancan en la misma x: la barra crece a lo ancho
    out = []
    for p_ in rects:
        b = _pl_extent(p_, r)
        if b is not None and b.width > 0 and b.height > 0:
            out.append((p_, b, horizontal))
    return out


def _ck_bar_masks(fig, r, names) -> list:
    """VALUE LABEL MASKING ITS OWN BAR.

    Sólo cuenta el rótulo que pinta RECUADRO —el rescate de `_pl_backing`, o uno puesto a mano—: un rótulo
    escrito sin recuadro dentro de su barra no borra nada. Lo que se mide es cuánto de la LONGITUD de la
    barra queda debajo del recuadro CUANDO el recuadro la cruza de lado a lado, que es lo que el lector
    pierde: media barra tapada de borde a borde por un rectángulo blanco es media barra que no está
    impresa, y la categoría mayor puede acabar leyéndose como la menor. Un recuadro que sólo muerde el
    canto de la barra —el rótulo girado 90° al costado— no le quita longitud y no se denuncia."""
    from matplotlib.colors import to_rgba
    out = []
    for ax in _pl_all_axes(fig):
        if not ax.get_visible():
            continue
        bars = _pl_bar_patches(ax, r)
        if not bars:
            continue
        for t in ax.texts:
            if not t.get_visible() or not str(t.get_text()).strip():
                continue
            if not _pl_in_data_coords(t, ax):
                continue
            patch = t.get_bbox_patch()
            if patch is None or not patch.get_visible():
                continue                     # sin recuadro no hay máscara: el rótulo no borra la barra
            try:
                if to_rgba(patch.get_facecolor())[3] < 0.05:
                    continue                 # recuadro transparente: tampoco borra
            except (ValueError, TypeError):
                pass
            box = _pl_extent(patch, r) or _pl_extent(t, r)
            if box is None:
                continue
            worst = None
            for p_, b, horizontal in bars:
                x0, y0 = max(box.x0, b.x0), max(box.y0, b.y0)
                x1, y1 = min(box.x1, b.x1), min(box.y1, b.y1)
                if x1 <= x0 or y1 <= y0:
                    continue
                span = b.width if horizontal else b.height          # a lo LARGO de la barra
                thick = b.height if horizontal else b.width         # de lado a lado
                across = ((y1 - y0) if horizontal else (x1 - x0)) / max(thick, 1e-9)
                if across < PLATE_BAR_MASK_ACROSS:
                    continue                 # el recuadro roza el borde: la silueta de la barra sigue entera
                covered = (x1 - x0) if horizontal else (y1 - y0)
                if _pl_pt(fig, covered) < PLATE_BAR_MASK_MIN_PT:
                    continue                 # la merma no llega a milímetro y medio: no se ve
                frac = covered / max(span, 1e-9)
                if worst is None or frac > worst[0]:
                    worst = (frac, covered)
            if worst is None or worst[0] <= PLATE_BAR_MASK:
                continue
            out.append(PlateProblem(BAR_MASKED_BY_LABEL, names.get(id(ax), "figure"),
                                    [_pl_desc(t, "value label"), "the backing box over its own bar"],
                                    _pl_pt(fig, worst[1]),
                                    detail=f"{100.0 * worst[0]:.0f}% of the bar's length is hidden by the box",
                                    objects=[t], fraction=worst[0]))
    return out


def _ck_title_gutter(fig, items, min_pt: float) -> list:
    """NEIGHBOURING PANEL TITLES WITHOUT A GUTTER.

    Dos títulos que comparten renglón y NO se solapan pueden seguir siendo ilegibles: si el hueco entre
    ellos es menor que el espacio que separa las palabras dentro de cada uno, el lector no ve el corte y
    lee las dos frases como una. El solape ya lo denuncia TEXT OVER TEXT; aquí se exige el hueco."""
    titles = [it for it in items if it["role"] == "panel title" and it["ax"] is not None]
    min_px = float(min_pt) * fig.dpi / 72.0
    out = []
    for i, a in enumerate(titles):
        for b in titles[i + 1:]:
            if a["ax"] is b["ax"]:
                continue
            ba, bb = a["box"], b["box"]
            if min(ba.y1, bb.y1) - max(ba.y0, bb.y0) <= 0:
                continue                     # no comparten renglón: no se leen seguidos
            left, right = (a, b) if ba.x0 <= bb.x0 else (b, a)
            gap = right["box"].x0 - left["box"].x1
            if gap < 0 or gap >= min_px:     # negativo = solape, y de eso ya avisa TEXT OVER TEXT
                continue
            out.append(PlateProblem(TITLES_WITHOUT_GUTTER, f"{left['axes']} / {right['axes']}",
                                    [_pl_desc(left["t"], "panel title"), _pl_desc(right["t"], "panel title")],
                                    _pl_pt(fig, min_px - gap),
                                    detail=f"{_pl_pt(fig, gap):.2f} pt between the two titles; "
                                           f"the plate asks for {min_pt:.0f} pt",
                                    objects=[left["t"], right["t"]]))
    return out


#: Un rótulo de marca que es UN NÚMERO: cifras con los separadores de los dos idiomas, signo opcional
#: (incluido el menos tipográfico) y un % o un ‰ opcional al final. Sólo se comprueban los rótulos
#: numéricos: en un eje CATEGÓRICO dos etiquetas iguales pueden ser dos categorías distintas legítimas,
#: mientras que dos posiciones numéricas distintas con el mismo número son siempre ilegibles.
_PL_NUMERIC_TICK = re.compile(r"^[\s+\-\u2212]*\d[\d\s.,\u00a0\u202f\u2009]*(?:\s*[%‰])?$")


def _ck_tick_labels(fig, names) -> list:
    """REPEATED TICK LABELS: dos marcas numéricas distintas del mismo eje escritas con el mismo número.

    Es lo que produce un formateador que congela sus decimales antes de que el reparto se asiente: el
    localizador vuelve a marcar de 0,5 en 0,5, el formateador sigue escribiendo con cero decimales y el
    eje imprime «1 2 2 2 3 4 4 4 5». Ninguna posición se puede leer, y ninguna de las otras familias lo
    ve, porque las cajas no se tocan y el texto no sale del lienzo.
    """
    out = []
    for ax in fig.axes:
        if not ax.get_visible() or not getattr(ax, "axison", True):
            continue
        for which, axis in (("x axis", ax.xaxis), ("y axis", ax.yaxis)):
            if not axis.get_visible():
                continue
            try:
                lo, hi = sorted(axis.get_view_interval())
                locs = [float(t) for t in axis.get_majorticklocs()]
                labs = list(axis.get_majorticklabels())
            except (AttributeError, TypeError, ValueError):
                continue
            if len(labs) != len(locs):
                continue
            span = (hi - lo) if np.isfinite(hi - lo) else 0.0
            slack = 1e-7 * max(1.0, abs(span))
            drawn = []
            for loc, lab in zip(locs, labs):
                if not np.isfinite(loc) or not (lo - slack <= loc <= hi + slack):
                    continue
                if lab is None or not lab.get_visible():
                    continue
                txt = " ".join(str(lab.get_text()).split())
                if not txt or not _PL_NUMERIC_TICK.match(txt):
                    continue
                drawn.append((float(loc), txt))
            drawn.sort(key=lambda t: t[0])
            # Sólo cuentan las marcas CONSECUTIVAS. Un eje espejado —la pirámide de población de la S11,
            # con hombres a la izquierda y mujeres a la derecha— rotula a propósito −500 y 500 como «500»,
            # y esas dos posiciones están en extremos opuestos del eje: nadie las confunde. Lo ilegible es
            # que dos marcas VECINAS lleven el mismo número, que es exactamente lo que produce un
            # formateador con los decimales congelados.
            runs = {}
            for (x0, t0), (x1, t1) in zip(drawn, drawn[1:]):
                if t0 == t1 and abs(x1 - x0) > slack:
                    runs.setdefault(t0, set()).update((round(x0, 9), round(x1, 9)))
            for txt, at in sorted(runs.items()):
                uniq = sorted(at)
                out.append(PlateProblem(REPEATED_TICK_LABELS, names.get(id(ax), "figure"),
                                        [f"{which} tick '{txt}'", f"{len(uniq)} adjacent positions"],
                                        0.0,
                                        detail="the same number at " + ", ".join(f"{v:g}" for v in uniq)))
    return out


def _ck_panels(fig, names, grid) -> list:
    """PANEL COUNT: la lámina es de tres filas por dos columnas y no lleva más de seis paneles."""
    if grid is None:
        return []
    insets = _pl_inset_ids(fig)
    seen, panels, floating = {}, [], []
    for ax in fig.axes:
        if not ax.get_visible() or _pl_is_colorbar(ax) or id(ax) in insets:
            continue
        pos = ax.get_position()
        key = (round(pos.x0, 4), round(pos.y0, 4), round(pos.x1, 4), round(pos.y1, 4))
        if key in seen:
            continue                     # eje gemelo: es el mismo panel
        seen[key] = ax
        sp = ax.get_subplotspec() if hasattr(ax, "get_subplotspec") else None
        (panels if sp is not None else floating).append((ax, sp))
    if not panels:
        # Una lámina de diagrama (la Figura 1 del flujo de datos) es un solo lienzo dibujado a mano: no
        # tiene rejilla y no se le puede exigir 3 × 2.
        if len(floating) <= 1:
            return []
        return [PlateProblem(PANEL_COUNT, "plate", [f"{len(floating)} free-floating axes"], 0.0,
                             detail="no grid: the plate standard is three rows by two columns")]
    out, shapes, cells = [], set(), set()
    for ax, sp in panels:
        try:
            top = sp.get_topmost_subplotspec()
            gs = top.get_gridspec()
            shapes.add((gs.nrows, gs.ncols))
            cells.add((top.rowspan.start, top.rowspan.stop, top.colspan.start, top.colspan.stop))
        except (AttributeError, ValueError):
            continue
    want = tuple(grid)
    for shape in sorted(shapes):
        if shape != want:
            out.append(PlateProblem(PANEL_COUNT, "plate", [f"grid {shape[0]}×{shape[1]}"], 0.0,
                                    detail=f"the plate standard is {want[0]} rows × {want[1]} columns"))
    if len(cells) > PLATE_MAX_PANELS:
        out.append(PlateProblem(PANEL_COUNT, "plate", [f"{len(cells)} panels"], 0.0,
                                detail=f"a plate carries at most {PLATE_MAX_PANELS} panels"))
    if floating:
        out.append(PlateProblem(PANEL_COUNT, "plate", [f"{len(floating)} axes outside the grid"], 0.0,
                                detail="every panel belongs to a cell of the 3 × 2 grid"))
    return out


def check_layout(fig, *, tol_pt: float = 0.5, data_frac: float = 0.03, panels: bool = True,
                 grid=_PL_GRID_AUTO, gutter_pt: float = PLATE_TITLE_GUTTER_PT) -> list:
    """Comprueba la composición de una lámina YA DIBUJADA, sobre su renderizador real.

    Devuelve la lista de `PlateProblem` (vacía si la lámina está limpia). No modifica la figura.

        problemas = C.check_layout(fig)              # después de C.plate_resolve(fig)
        for p in problemas: print(p)

    `tol_pt` es la tolerancia de roce en puntos: dos cajas que se tocan por menos de eso no se denuncian.
    `data_frac` es la fracción mínima de un elemento de datos tapada por una leyenda o una nota para
    considerarlo un defecto (0,03 = 3 %). `grid` fija la rejilla esperada; `None` desactiva la comprobación
    de paneles para una lámina de diagrama, y por omisión se usa la declarada con `plate_declare` o la de
    la norma (3 × 2). `gutter_pt` es el hueco mínimo exigido entre los títulos de dos paneles vecinos.
    """
    r = _pl_renderer(fig)
    tol_px = float(tol_pt) * fig.dpi / 72.0
    names = _pl_name_map(fig)
    items = _pl_text_items(fig, r, names)
    problems = _ck_texts(fig, r, items, tol_px, names)
    problems += _ck_boxes_over_data(fig, r, names, data_frac, tol_px)
    problems += _ck_value_labels(fig, r, names, tol_px)
    problems += _ck_bar_masks(fig, r, names)
    problems += _ck_title_gutter(fig, items, gutter_pt)
    problems += _ck_tick_labels(fig, names)
    if panels:
        want = getattr(fig, "_plate_grid", PLATE_STD_GRID) if grid is _PL_GRID_AUTO else grid
        problems += _ck_panels(fig, names, want)
    order = {k: i for i, k in enumerate(PLATE_PROBLEM_KINDS)}
    problems.sort(key=lambda p: (order.get(p.kind, 99), -p.overlap_pt))
    return problems


def assert_layout_clean(fig, name, **kw) -> list:
    """Falla —ruidosamente y con la lista COMPLETA— si la lámina tiene algún defecto de composición.

        C.assert_layout_clean(fig, "figS9_regional_maps.png")

    Acepta los mismos parámetros que `check_layout`. Devuelve la lista vacía cuando la lámina está limpia,
    de modo que se puede encadenar."""
    problems = check_layout(fig, **kw)
    if problems:
        raise PlateLayoutError(name, problems)
    return problems


def plate_declare(fig, name: str | None = None, grid=_PL_GRID_AUTO) -> None:
    """Declara el nombre de la lámina y su rejilla para el verificador.

    `grid=None` exime a la lámina de la comprobación de paneles (solo para un diagrama de lienzo único,
    como la Figura 1 del flujo de datos)."""
    if name is not None:
        fig._plate_name = str(name)
    if grid is not _PL_GRID_AUTO:
        fig._plate_grid = None if grid is None else tuple(grid)


# ---------------------------------------------------------------------------
# Puerta automática: comprobar TODAS las láminas que construye un módulo
# ---------------------------------------------------------------------------
#: Modo del verificador automático. Se lee de la variable de entorno LANCET_PLATE_CHECK
#: («off» —por omisión—, «report» para acumular y avisar, «strict» para fallar en la primera lámina mala)
#: o se fija con `plate_check_enable`.
PLATE_CHECK_ENV = "LANCET_PLATE_CHECK"
_PLATE_CHECK = {"mode": None, "kw": {}, "found": [], "checked": []}


def plate_check_enable(mode: str = "strict", **kw) -> None:
    """Enciende el verificador automático para TODAS las láminas que se guarden después.

        C.plate_check_enable("strict")   # el módulo falla en la primera lámina con defectos
        C.plate_check_enable("report")   # las acumula y las resume al final (plate_check_summary)

    Equivale a exportar LANCET_PLATE_CHECK=strict|report antes de ejecutar el módulo."""
    mode = str(mode).lower()
    if mode not in ("off", "report", "strict"):
        raise ValueError("mode debe ser 'off', 'report' o 'strict'")
    _PLATE_CHECK["mode"] = mode
    _PLATE_CHECK["kw"] = dict(kw)


def plate_check_mode() -> str:
    if _PLATE_CHECK["mode"] is not None:
        return _PLATE_CHECK["mode"]
    return str(os.environ.get(PLATE_CHECK_ENV, "off")).strip().lower() or "off"


def plate_check_reset() -> None:
    _PLATE_CHECK["found"] = []
    _PLATE_CHECK["checked"] = []


def plate_check_records() -> list:
    """Lista de (nombre, problemas) acumulada en modo «report»."""
    return list(_PLATE_CHECK["found"])


def plate_check_summary() -> str:
    """Resumen legible de lo acumulado: qué láminas se comprobaron y qué defectos quedaron."""
    lines = [f"plate layout check: {len(_PLATE_CHECK['checked'])} plate(s) checked, "
             f"{len(_PLATE_CHECK['found'])} with problems"]
    for name, problems in _PLATE_CHECK["found"]:
        lines.append(f"{name}: {len(problems)} problem(s)")
        lines += [f"    {p}" for p in problems]
    return "\n".join(lines)


def plate_check_write(path) -> Path:
    """Vuelca lo acumulado a un archivo de texto (para adjuntarlo al informe de la fase)."""
    path = journal_redirect(Path(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(plate_check_summary() + "\n", encoding="utf-8")
    return path


def _pl_guess_name(fig) -> str:
    """Nombre de la lámina para el informe: el declarado, el rótulo de la figura o el archivo de destino."""
    name = getattr(fig, "_plate_name", None)
    if name:
        return str(name)
    label = str(fig.get_label() or "")
    if label:
        return label
    import inspect
    frame = inspect.currentframe()
    try:
        for _ in range(8):
            frame = frame.f_back
            if frame is None:
                break
            for key in ("path", "out_path", "target", "dest", "png"):
                val = frame.f_locals.get(key)
                if isinstance(val, (str, Path)) and str(val).lower().endswith(".png"):
                    return Path(val).name
    finally:
        del frame
    return f"figure#{id(fig):x}"


def plate_check(fig, name: str | None = None, **kw) -> list:
    """Comprueba la lámina SEGÚN EL MODO ACTIVO: silencioso, acumulando avisos o fallando.

    Es lo que llama el guardado de láminas; un módulo no necesita invocarlo a mano."""
    mode = plate_check_mode()
    if mode == "off":
        return []
    name = name or _pl_guess_name(fig)
    kw = {**_PLATE_CHECK["kw"], **kw}
    problems = check_layout(fig, **kw)
    _PLATE_CHECK["checked"].append(name)
    if problems:
        _PLATE_CHECK["found"].append((name, problems))
        if mode == "strict":
            raise PlateLayoutError(name, problems)
        sys.stderr.write(f"[plate-check] {name}: {len(problems)} layout problem(s)\n")
        for p in problems:
            sys.stderr.write(f"[plate-check]     {p}\n")
    return problems


def _plate_autocheck(fig, name: str | None = None) -> None:
    """Puerta que atraviesan TODAS las láminas: se llama al final de `plate_resolve` y de `save_fig`."""
    if plate_check_mode() == "off":
        return
    if getattr(fig, "_plate_checked", False):
        return
    fig._plate_checked = True
    plate_check(fig, name)


# ---------------------------------------------------------------------------
# Ayudas de colocación: para que los paneles se arreglen en la CAUSA, no en el síntoma
# ---------------------------------------------------------------------------
def plate_ylabel(ax, text: str, *, right: bool = False, above: bool = False, gap_pt: float = 2.0,
                 fontsize: float | None = None, **kw):
    """Rótulo del eje Y que NUNCA cae sobre sus propias marcas.

    Dos modos:
      * por omisión, se mide la columna de marcas del eje ya dibujada y se fija `labelpad` a partir de esa
        anchura, devolviendo además el rótulo a su colocación automática (un desplazamiento heredado de la
        guarda de recorte es la causa habitual del defecto);
      * `above=True` lo saca de la vertical y lo escribe como UNA LÍNEA HORIZONTAL corta sobre el panel,
        empujando el título de panel lo justo para que quepan los dos. Es lo que hace falta cuando la
        columna de marcas es tan ancha que no queda sitio a la izquierda.

    `right=True` para el eje gemelo de la derecha. Respeta la norma: cuerpo mínimo 6 pt y título «(a) …»."""
    fig = ax.figure
    axis = ax.yaxis
    fs = float(fontsize) if fontsize is not None else float(axis.label.get_size())
    fs = max(PLATE_FS_FLOOR, fs)
    r = _pl_renderer(fig)
    if above:
        axis.set_label_text("")
        old = getattr(ax, "_pl_above_label", None)
        if old is not None:
            try:
                old.remove()
            except (ValueError, NotImplementedError):
                pass
        t = ax.text(1.0 if right else 0.0, 1.0, str(text), transform=ax.transAxes, fontsize=fs,
                    ha="right" if right else "left", va="bottom", **kw)
        ax._pl_above_label = t
        h_pt = _pl_pt(fig, (_pl_extent(t, r) or fig.bbox).height)
        _pl_push_title(ax, h_pt + gap_pt)
        return t
    axis.set_label_position("right" if right else "left")
    axis.set_label_text(str(text), fontsize=fs, **kw)
    try:
        axis._autolabelpos = True           # deshace un `set_label_coords` previo
    except AttributeError:
        pass
    base = getattr(axis.label, "_pl_base_tr", None)
    if base is not None:                    # deshace un empujón del motor de descongestión
        axis.label.set_transform(base)
        axis.label._pl_off = (0.0, 0.0)
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    width_px = 0.0
    for lab in _pl_tick_texts(axis):
        b = _pl_extent(lab, r)
        if b is not None:
            width_px = max(width_px, b.width)
    ticks = axis.get_major_ticks()
    tick_pt = 0.0
    if ticks:
        try:
            tick_pt = float(ticks[0].get_pad()) + float(ticks[0].get_tick_padding() or 0.0)
        except (AttributeError, TypeError, ValueError):
            tick_pt = float(ticks[0].get_pad() or 0.0)
    axis.labelpad = max(1.0, gap_pt)
    # matplotlib coloca el rótulo a `labelpad` del borde de las MARCAS: con la colocación automática
    # restaurada basta el hueco, pero si el panel las dibuja por dentro (`tick_params(pad=-…)`) hay que
    # sumar el ancho medido para que el rótulo no las invada.
    if tick_pt < 0:
        axis.labelpad = max(1.0, gap_pt + _pl_pt(fig, width_px) - tick_pt)
    fig.canvas.draw()
    return axis.label


def _pl_push_title(ax, extra_pt: float) -> None:
    """Sube el título de panel `extra_pt` puntos conservando su cuerpo, su peso, su alineación y su x."""
    import matplotlib.pyplot as plt
    title = next((c for c in (getattr(ax, "_left_title", None), ax.title, getattr(ax, "_right_title", None))
                  if c is not None and c.get_text()), None)
    pad = float(getattr(ax, "_pl_title_pad", plt.rcParams.get("axes.titlepad", 6.0)))
    new = pad + float(extra_pt)
    ax._pl_title_pad = new
    if title is None:
        return
    loc = "center"
    if title is getattr(ax, "_left_title", None):
        loc = "left"
    elif title is getattr(ax, "_right_title", None):
        loc = "right"
    ax.set_title(title.get_text(), loc=loc, pad=new, fontsize=title.get_size(),
                 fontweight=title.get_fontweight(), color=title.get_color(),
                 x=title.get_position()[0])


def plate_place_legend(ax, legend=None, *, outside_below: bool = True, prefer=(), pad_frac: float = 0.012,
                       free_tol: float = 0.0):
    """Coloca la leyenda en la primera posición estándar que NO tape ningún dato.

    Prueba las nueve posiciones de matplotlib (`upper left`… `center`) y, si ninguna deja los datos a la
    vista, la saca DEBAJO del panel, bajo las marcas del eje X. Devuelve la posición elegida
    (`'upper left'`, …, o `'outside below'`). El orden se puede sesgar con `prefer=('lower right', …)`."""
    fig = ax.figure
    lg = legend if legend is not None else ax.get_legend()
    if lg is None:
        return None
    r = _pl_renderer(fig)
    axb = _pl_extent(ax, r)
    b = _pl_extent(lg, r)
    if axb is None or b is None:
        return None
    group = next((g for g in _pl_axes_groups(fig) if ax in g), [ax])
    occ, ext = _pl_group_ink(group, r)
    pad = pad_frac * min(axb.width, axb.height) + 2.0
    order = [loc for loc in prefer if loc in _PL_LOCS] + [loc for loc in _PL_LOCS if loc not in prefer]
    best, best_cost = None, np.inf
    for loc in order:
        box = _pl_loc_box(loc, axb, b.width, b.height, pad)
        cost = _pl_ink_cost(occ, ext, box) + 60.0 * _pl_out(box, axb)
        if cost <= free_tol:
            lg.set_loc(loc)
            lg.set_in_layout(False)
            return loc
        if cost < best_cost:
            best, best_cost = loc, cost
    def keep_inside():
        lg.set_loc(best)
        lg.set_in_layout(False)
        return best

    if not outside_below:
        return keep_inside()
    # Nada libre dentro: se baja al pie del panel, bajo las marcas del eje X, con sitio RESERVADO. Y se
    # comprueba midiendo: una leyenda de siete entradas en una columna mide 57 pt y, colgada bajo un panel
    # de la fila inferior, se pierde por el borde del lienzo —peor defecto que el que venía a resolver—.
    handles = list(getattr(lg, "legend_handles", getattr(lg, "legendHandles", [])))
    labels = [t.get_text() for t in lg.get_texts()]
    cell = plate_cell_box(fig, ax)
    pos0 = ax.get_position().frozen()
    best_shape = None
    for ncol in (3, 2, 1):
        if not handles:
            break
        cand = _pl_relegend(ax, lg, handles, labels, ncol=ncol)
        cb = _pl_extent(cand, r)
        if cb is not None and cb.width <= min(axb.width, cell.width) * 1.02:
            best_shape, lg = ncol, cand
            break
    if best_shape is None and handles:
        lg = _pl_relegend(ax, lg, handles, labels, ncol=1)
    try:
        xb = ax.xaxis.get_tightbbox(r)
    except (AttributeError, ValueError, TypeError):
        xb = None
    bottom = xb.y0 if xb is not None else axb.y0
    y = (bottom - axb.y0) / axb.height - 0.015
    lg.set_loc("upper center")
    lg.set_bbox_to_anchor((0.5, y), transform=ax.transAxes)
    lg.set_in_layout(False)
    b = _pl_extent(lg, r)
    drop = (b.height / fig.bbox.height + 0.006) if b is not None else 0.0
    if 0 < drop < pos0.height * 0.5:
        ax.set_position([pos0.x0, pos0.y0 + drop, pos0.width, pos0.height - drop])
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        b = _pl_extent(lg, r)
    room = _pl_bbox(min(cell.x0, fig.bbox.x0) + 1.0, max(cell.y0, fig.bbox.y0) + 1.0,
                    max(cell.x1, fig.bbox.x1) - 1.0, min(cell.y1, fig.bbox.y1) - 1.0)
    if b is None or _pl_out(b, room) > 1.0:
        ax.set_position(pos0)                      # no cabe abajo: se vuelve a la menos mala de dentro
        lg.set_bbox_to_anchor(None)
        if handles:
            lg = _pl_relegend(ax, lg, handles, labels, ncol=getattr(lg, "_ncols", 1))
        fig.canvas.draw()
        return keep_inside()
    return "outside below"


#: Letras de panel de la norma, en el orden en que se leen.
PLATE_PANEL_LETTERS = "abcdef"


def plate_panel_letter(ch) -> str:
    """La letra de panel tal como se IMPRIME en la lámina: minúscula y entre paréntesis, «(a)».

    UNA sola convención para las 59 láminas. Las 58 leyendas con paneles escriben «(a)…(f)», y las
    láminas de 06/08a/08b/08c ya imprimían «(a)»; las de 13/14/15/15b imprimían «a» a secas, de modo que
    el artículo publicaba dos convenciones y la leyenda no casaba con su propia lámina. Acepta un índice
    entero (0 → «(a)»), la letra suelta o la letra ya entre paréntesis, y siempre devuelve «(x)».
    """
    if isinstance(ch, (int, np.integer)) and not isinstance(ch, bool):
        s = PLATE_PANEL_LETTERS[int(ch)] if 0 <= int(ch) < len(PLATE_PANEL_LETTERS) else str(int(ch))
    else:
        s = str(ch).strip()
    s = s.lower()
    if s.startswith("(") and s.endswith(")"):
        return s
    return f"({s})"


def plate_value_label(ax, x, y, text, *, err=None, fontsize: float | None = None, color: str = "#222222",
                      step_pt: float = 3.0, max_steps: int = 4, prefer=None, **kw):
    """Escribe un rótulo de valor SEPARADO de su marcador y de su barra de error.

    Prueba desplazamientos crecientes (arriba, abajo, derecha, izquierda y diagonales) y se queda en el
    primero que no cae sobre ningún marcador del panel, sobre la barra de error del propio dato
    (`err=(lo, hi)` en unidades de dato, o el `ErrorbarContainer`) ni sobre otro rótulo ya colocado.
    Devuelve la anotación."""
    fig = ax.figure
    fs = max(PLATE_FS_FLOOR, float(fontsize) if fontsize is not None else PLATE_FS_FLOOR + 0.3)
    ann = ax.annotate(str(text), xy=(x, y), xycoords="data", textcoords="offset points",
                      xytext=(0.0, step_pt), fontsize=fs, color=color,
                      ha=kw.pop("ha", "center"), va=kw.pop("va", "bottom"), zorder=6, **kw)
    r = _pl_renderer(fig)
    group = next((g for g in _pl_axes_groups(fig) if ax in g), [ax])
    marks, bars = _pl_markers_and_bars(group, r)
    if err is not None:
        bars = list(bars)
        if hasattr(err, "lines"):                    # un ErrorbarContainer entero
            from matplotlib.collections import LineCollection
            for piece in _pl_container_parts(err):
                if isinstance(piece, LineCollection):
                    try:
                        tr = piece.get_transform()
                        bars += [np.asarray(tr.transform(np.asarray(seg, dtype=float)), dtype=float)
                                 for seg in piece.get_segments() if len(seg) >= 2]
                    except (ValueError, TypeError, AttributeError):
                        pass
        else:
            try:
                lo, hi = err                          # (lo, hi) en unidades de dato
                p0, p1 = ax.transData.transform([[x, lo], [x, hi]])
                bars.append(np.vstack([p0, p1]))
            except (TypeError, ValueError, IndexError):
                pass
    placed = getattr(ax, "_pl_value_boxes", [])
    b = _pl_extent(ann, r)
    if b is None:
        return ann
    w_pt, h_pt = _pl_pt(fig, b.width), _pl_pt(fig, b.height)
    dirs = prefer or ((0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, 1), (1, -1), (-1, -1))
    # El primer paso tiene que sacar la caja del DISCO del marcador, no de su centro: con el radio fuera
    # de la cuenta, el desplazamiento mínimo dejaba el borde del rótulo dentro de la chincheta y el
    # buscador se quedaba ahí porque ningún centro caía dentro de la caja (el defecto de la S12 (f)).
    rad_pt = _pl_pt(fig, float(np.max(_pl_marker_radii(marks)))) if len(marks) else 0.0
    best, best_cost = (0.0, step_pt + rad_pt), np.inf
    for k in range(1, max_steps + 1):
        for ux, uy in dirs:
            dx = ux * (w_pt * 0.55 + step_pt + rad_pt) * k
            dy = uy * (h_pt * 0.75 + step_pt + rad_pt) * k
            ann.xyann = (dx, dy)
            nb = _pl_extent(ann, r)
            if nb is None:
                continue
            cost = 0.0
            if len(marks):
                # Misma medida que el verificador, pero GRADUADA: el coste es la fracción de disco tapada,
                # de modo que la búsqueda prefiere la posición que menos marcador tapa en vez de detenerse
                # en la primera que no pisa ningún centro —que era la que dejaba medio marcador cubierto—.
                _idx, cover = _pl_marker_cover(nb, marks)
                cost += 40.0 * float(np.sum(cover[cover > PLATE_MARKER_COVER])) if len(cover) else 0.0
                cost += 4.0 * float(np.sum(cover)) if len(cover) else 0.0
            for seg in bars:
                q = np.linspace(0.0, 1.0, 24)[:, None]
                pts = seg[0][None, :] * (1 - q) + seg[-1][None, :] * q
                inside = ((pts[:, 0] >= nb.x0) & (pts[:, 0] <= nb.x1)
                          & (pts[:, 1] >= nb.y0) & (pts[:, 1] <= nb.y1))
                cost += 40.0 * float(inside.sum())
            cost += sum(_pl_over(nb, q) for q in placed) / 100.0
            cost += 0.02 * (abs(dx) + abs(dy))
            axb = _pl_extent(ax, r)
            if axb is not None:
                cost += 5.0 * _pl_out(nb, axb)
            if cost < best_cost - 1e-9:
                best, best_cost = (dx, dy), cost
            if best_cost <= 1e-9:
                break
        if best_cost <= 1e-9:
            break
    ann.xyann = best
    nb = _pl_extent(ann, r)
    if nb is not None:
        ax._pl_value_boxes = list(placed) + [nb]
    return ann


#: Abreviaturas de los rótulos largos que se repiten en los ejes categóricos del estudio. El nombre
#: completo vuelve SIEMPRE en la tabla acompañante: la lámina abrevia, no oculta.
PLATE_LABEL_GLOSSARY = {
    "Arica y Parinacota": "Arica y P.", "Antofagasta": "Antofag.", "Metropolitana": "Metropol.",
    "Región Metropolitana": "Metropol.", "Metropolitan Region": "Metropol.", "Valparaíso": "Valparaíso",
    "La Araucanía": "Araucanía", "Magallanes": "Magallanes", "Libertador General Bernardo O'Higgins": "O'Higgins",
    "O'Higgins": "O'Higgins", "Aysén del General Carlos Ibáñez del Campo": "Aysén", "Aysén": "Aysén",
    "Magallanes y de la Antártica Chilena": "Magallanes", "Tarapacá": "Tarapacá", "Atacama": "Atacama",
    "Coquimbo": "Coquimbo", "Maule": "Maule", "Ñuble": "Ñuble", "Biobío": "Biobío", "Los Ríos": "Los Ríos",
    "Los Lagos": "Los Lagos",
}


def plate_thin_category_ticks(ax, *, axis: str = "y", glossary=None, rotate: bool = True,
                              fontsize_floor: float = PLATE_FS_FLOOR, keep_every: int | None = None) -> dict:
    """Adelgaza un eje CATEGÓRICO con muchos nombres largos hasta que ninguno se imprima sobre otro.

    Por este orden: reducir el cuerpo hasta el mínimo de la norma (6 pt) → abreviar por el glosario →
    girar (solo en el eje X) → dejar una marca de cada `k` (con `k` el menor que resuelve el choque).
    Nunca borra información sin decirlo: devuelve `{'mode', 'fontsize', 'shown', 'hidden', 'abbreviated'}`
    y el llamante escribe en la tabla acompañante los nombres que la lámina no imprime.

    Es el defecto de la Figura S9 (a)-(c): dieciséis nombres de región impresos de tres en tres."""
    fig = ax.figure
    r = _pl_renderer(fig)
    horizontal = str(axis).lower().startswith("x")
    axis_obj = ax.xaxis if horizontal else ax.yaxis
    labs = _pl_tick_texts(axis_obj)
    report = {"mode": "unchanged", "fontsize": None, "shown": [str(t.get_text()) for t in labs],
              "hidden": [], "abbreviated": {}}
    if len(labs) < 2:
        return report

    def boxes():
        return [_pl_extent(t, r) for t in labs]

    def clash() -> bool:
        bs = sorted([b for b in boxes() if b is not None],
                    key=lambda b: b.x0 if horizontal else b.y0)
        return _pl_pairs_overlap(bs, gap=0.5)

    if not clash():
        return report
    for fs in (7.5, 7.0, 6.5, fontsize_floor):
        if min(t.get_size() for t in labs) <= fs:
            continue
        for t in labs:
            t.set_size(min(t.get_size(), fs))
        report.update(mode="shrunk", fontsize=fs)
        if not clash():
            return report
    gl = PLATE_LABEL_GLOSSARY if glossary is None else glossary
    look = gl if callable(gl) else (lambda s: gl.get(s, s))
    changed = {}
    for t in labs:
        s = str(t.get_text())
        short = str(look(s) or s)
        if short != s:
            t.set_text(short)
            changed[s] = short
    if changed:
        report.update(mode="abbreviated", abbreviated=changed,
                      shown=[str(t.get_text()) for t in labs])
        if not clash():
            return report
    if horizontal and rotate and max(abs(t.get_rotation() % 180) for t in labs) < 60:
        for t in labs:
            t.set_rotation(90)
            t.set_ha("center")
            t.set_va("top")
        report.update(mode="rotated")
        if not clash():
            return report
    locs = list(axis_obj.get_ticklocs())
    texts = [str(t.get_text()) for t in labs]
    if len(locs) == len(texts):
        for k in ([keep_every] if keep_every else (2, 3, 4)):
            keep = [(loc, txt) for i, (loc, txt) in enumerate(zip(locs, texts)) if i % k == 0]
            axis_obj.set_ticks([q for q, _ in keep])
            axis_obj.set_ticklabels([s for _, s in keep])
            fig.canvas.draw()
            labs = _pl_tick_texts(axis_obj)
            for t in labs:
                t.set_size(min(fontsize_floor + 1.0, t.get_size()))
            if not clash():
                report.update(mode=f"every {k}th tick", shown=[s for _, s in keep],
                              hidden=[s for i, s in enumerate(texts) if i % k != 0])
                return report
        report.update(mode="every 4th tick", shown=[str(t.get_text()) for t in labs],
                      hidden=[s for s in texts if s not in {str(t.get_text()) for t in labs}])
    report["mode"] = report["mode"] if report["mode"] != "unchanged" else "unresolved"
    return report
