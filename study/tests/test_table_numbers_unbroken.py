# -*- coding: utf-8 -*-
"""Ninguna línea de ninguna tabla puede terminar dentro de un número (defecto F4-1 de la fase 4f).

Word parte una palabra que no cabe en su celda por donde le toque, carácter a carácter: en las tablas
suplementarias de 14 a 21 columnas eso imprimía «1,085,8» en una línea y «13» en la siguiente. Se lee como
una errata, no como un salto de línea, y ocurría en los OCHO documentos largos y en ninguno de los cuatro
del artículo.

La prueba vigila las TRES puntas del arreglo:

  1. lo que ES un número y lo que no (`docx_builder.numeros_de`): «1.085.813», «(18,1» y «2019» se protegen;
     «F84.2», «GRD_PUBLICO_2019.csv» y un SHA-256 no son números y siguen pudiendo partirse, que es lo que
     hace falta para que quepan las tablas de procedencia;
  2. la GARANTÍA del constructor: llegue el reparto de anchos de donde llegue —incluido el reparto a
     prorrata que hace el posproceso apaisado de 10_manuscript cuando una tabla no cabe ni a 6 pt—,
     `docx_builder._aplicar_anchos` no deja salir una columna más estrecha que su número más largo mientras
     otra columna tenga texto que sí se pueda partir. Con un control negativo, para que la comprobación no
     pueda quedarse muda: los mismos anchos escritos SIN pasar por el arreglo sí parten números;
  3. los DOCUMENTOS construidos, medidos por dos caminos independientes: la rejilla del DOCX
     (`docx_builder.revisar_documento`) y el texto del PDF, donde se busca literalmente una línea que
     termina dentro de un número y sigue en la siguiente.

Las dos comprobaciones sobre los documentos se saltan mientras los archivos de `manuscript/` sean ANTERIORES
a `docx_builder.py`: los publicados el 2026-09-07 llevan el defecto por construcción y el arreglo no los
reescribe (de eso se encarga la reconstrucción). En cuanto se reconstruyen, la prueba se activa sola.
"""
from pathlib import Path
import os
import re
import subprocess
import sys
import unittest

LA = Path(__file__).resolve().parents[1]
if str(LA) not in sys.path:
    sys.path.insert(0, str(LA))

import pandas as pd  # noqa: E402
from docx.oxml.ns import qn  # noqa: E402

import docx_builder as DB  # noqa: E402

#: The built documents live in two folders since 2026-09-10 (manuscript/04_submission_study for
#: the journal package, manuscript/02_others for the full corpus). A non-recursive glob of manuscript/ went
#: silently blind when they moved, so these guards walk BOTH folders and say how many files they read.
MANUSCRIPT = LA / "manuscript"
#: Since 2026-09-14 each version keeps its built documents in a `documents/` subfolder (the builders
#: still write to the folder root), so both places are walked.
BUILT_DIRS = [p for d in (MANUSCRIPT / "04_submission_study", MANUSCRIPT / "02_others")
              for p in (d, d / "documents")]
LANDSCAPE_TEXT_WIDTH_CM = 29.7 - 2 * 2.5      # misma caja apaisada que pipeline/10_manuscript
CHECK_OFF = os.environ.get("NUM_CHECK", "").lower() in ("off", "0", "no")


# ---------------------------------------------------------------------------
# Un número partido, visto en el TEXTO del PDF
# ---------------------------------------------------------------------------
#: El separador de millares de cada idioma. Un número partido deja arriba un grupo incompleto («1,085,8»,
#: «580.74») y abajo la cola de ese grupo, sólo cifras y sin separador («13», «0»); juntos forman un número
#: bien agrupado que el fragmento de arriba NO es. Pedir las tres cosas a la vez —fragmento, cola y unión
#: válida, en columnas que se solapan— es lo que distingue un número roto de dos números de celdas vecinas
#: que se tocan en la vertical.
_SEP = {"en": ",", "es": "."}


def _regex_numero(sep: str):
    s = re.escape(sep)
    return (re.compile(rf"^\d{{1,3}}(?:{s}\d{{3}})+$"),                  # número completo con millares
            re.compile(rf"^\d{{1,3}}(?:{s}\d{{3}})*{s}\d{{1,2}}$"),      # fragmento: último grupo incompleto
            re.compile(r"^\d{1,3}$"))                                    # cola: cifras sin separador


def lineas_partidas_en_numero(texto: str, lang: str) -> list[dict]:
    """Toda línea del texto de un PDF que termina dentro de un número y continúa en la siguiente."""
    entero, fragmento, cola = _regex_numero(_SEP[lang])
    palabras = lambda linea: [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", linea)]  # noqa: E731
    lineas = texto.split("\n")
    fuera = []
    for i in range(len(lineas) - 1):
        arriba, abajo = palabras(lineas[i]), palabras(lineas[i + 1])
        for a0, a1, w1 in arriba:
            if not fragmento.match(w1):
                continue
            for b0, b1, w2 in abajo:
                if cola.match(w2) and min(a1, b1) - max(a0, b0) > 0 and entero.match(w1 + w2):
                    fuera.append(dict(line=i + 1, head=w1, tail=w2, number=w1 + w2))
    return fuera


def _pdftotext(path: Path) -> str | None:
    try:
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return r.stdout if r.returncode == 0 else None


def _fresco(path: Path) -> bool:
    """¿Se construyó el documento DESPUÉS del arreglo? Si no, lleva el defecto por construcción."""
    return path.stat().st_mtime > Path(DB.__file__).stat().st_mtime


# ---------------------------------------------------------------------------
# Una tabla que reproduce la geometría del defecto: 20 columnas, texto largo y cifras de siete dígitos
# ---------------------------------------------------------------------------
def _tabla_dura() -> pd.DataFrame:
    anios = [2019, 2020, 2021, 2022, 2023, 2024]
    grandes = ["1,667,180", "1,330,477", "1,467,062", "1,597,118", "1,612,267", "1,667,349"]
    otros = ["1,151,475", "781,912", "816,909", "932,839", "1,039,587", "1,085,813"]
    datos = {
        "Year": [str(a) for a in anios],
        "Series": ["Full F84 family (including Rett syndrome)"] * 6,
        "DEIS discharges (all establishments)": grandes,
        "GRD episodes (observed panel)": otros,
        "SNSS discharges": ["1,042,595", "816,463", "844,546", "909,774", "938,890", "993,807"],
    }
    for k in range(6):
        datos[f"Principal F84 per 100,000 discharges (exact 95% CI) {k}"] = [
            "20.2 (18.1 to 22.4)", "20.1 (17.7 to 22.6)", "21.1 (18.8 to 23.5)",
            "30.1 (27.4 to 32.9)", "37.2 (34.3 to 40.3)", "41.4 (38.4 to 44.6)"]
    for k in range(6):
        datos[f"Ratio principal F84 DEIS SNSS / GRD strict hospitalisation {k}"] = [
            "1.45", "1.70", "1.80", "1.71", "1.55", "1.54"]
    datos["Microdata file"] = [f"variants/detailed_age_15col/{a}.csv" for a in anios]
    datos["Age scheme"] = ["decadal", "decadal", "decadal", "decadal", "decadal", "five-year"]
    datos["Reproduction module"] = ["study/pipeline/01b_deis_egresos.py::canonical"] * 6
    return pd.DataFrame(datos)


def _rejilla_cm(tbl) -> list[float]:
    grid = tbl._tbl.find(qn("w:tblGrid"))
    return [int(gc.get(qn("w:w")) or 0) / 567.0 for gc in grid.findall(qn("w:gridCol"))]


def _escribir_rejilla(tbl, anchos_cm) -> None:
    """Escribe los anchos SIN pasar por `_aplicar_anchos`: el estado del que venía el defecto."""
    grid = tbl._tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), anchos_cm):
        gc.set(qn("w:w"), str(int(w * 567)))


class NumerosIndivisiblesTest(unittest.TestCase):

    def test_que_es_un_numero_y_que_no(self):
        """Se protege lo que el lector lee como una cifra; un identificador con dígitos sigue partiéndose."""
        for texto, esperado in [("1,085,813", ["1,085,813"]), ("1.085.813", ["1.085.813"]),
                                ("2019", ["2019"]), ("(18.1", ["(18.1"]), ("22,4)", ["22,4)"]),
                                ("2.6%", ["2.6%"]), ("100,000", ["100,000"]), ("0,001", ["0,001"]),
                                ("20.2 (18.1 to 22.4)", ["20.2", "(18.1", "22.4)"]),
                                ("2019–2024", ["2019", "2024"]),
                                ("F84.2", []), ("GRD_PUBLICO_2019.csv", []),
                                ("study/pipeline/06_models.py::x", []),
                                ("1b86155938fd", []), ("n_f84_ids_shared_with_previous_year", [])]:
            with self.subTest(texto=texto):
                self.assertEqual(DB.numeros_de(texto), esperado)

    def test_una_tabla_que_se_queda_vertical_no_parte_ningun_numero(self):
        """La tabla que cabe en la columna de texto se compone sin partir una cifra."""
        df = pd.DataFrame({
            "Year": ["2019", "2020", "2021", "2022", "2023", "2024"],
            "GRD episodes (observed panel)": ["1,151,475", "781,912", "816,909", "932,839",
                                              "1,039,587", "1,085,813"],
            "Episodes with documented F84": ["2,385", "1,633", "2,399", "3,912", "6,473", "8,818"],
            "Rate per 100,000 episodes (exact 95% CI)": ["20.7 (19.9 to 21.6)", "20.9 (19.9 to 21.9)",
                                                         "29.4 (28.2 to 30.6)", "41.9 (40.6 to 43.3)",
                                                         "62.3 (60.8 to 63.8)", "81.2 (79.5 to 83.0)"],
        })
        doc = DB.nuevo_doc()
        tbl = DB.insertar_tabla(doc, df)
        self.assertEqual(DB.numeros_partidos(tbl), [])

    def test_el_reparto_a_prorrata_del_posproceso_tampoco(self):
        """El caso que producía el defecto: la tabla no cabe ni apaisada y los anchos van a prorrata.

        Es la geometría real de las tablas S24, S25, S37 y S38: veinte columnas que ni a 6 pt caben en la
        caja apaisada de 24,7 cm, de modo que el posproceso de 10_manuscript reparte los anchos a prorrata
        y algunas columnas quedan por debajo de su cifra más larga. Con un CONTROL NEGATIVO delante: los
        mismos anchos escritos SIN pasar por `_aplicar_anchos` sí parten números, de modo que esta prueba
        no puede quedarse muda si el arreglo desapareciera."""
        df = _tabla_dura()
        cols = [str(c) for c in df.columns]
        textos = [[str(v) for v in df.iloc[:, j]] for j in range(len(cols))]
        doc = DB.nuevo_doc()
        tbl = DB.insertar_tabla(doc, df)
        pt = DB._cell_pt(tbl.rows[0].cells[0])
        minimos = [max([DB._ancho_texto(w, pt) for t in textos[j] for w in t.split()]
                       + [DB._ancho_texto(w, pt, bold=True) for w in cols[j].split()] or [0.0]) * 1.08 + 0.40
                   for j in range(len(cols))]
        total = sum(minimos)
        self.assertGreater(total, LANDSCAPE_TEXT_WIDTH_CM,
                           "la tabla de prueba ya cabe apaisada: no reproduce la geometría del defecto")
        prorrata = [LANDSCAPE_TEXT_WIDTH_CM * m / total for m in minimos]
        _escribir_rejilla(tbl, prorrata)                       # control negativo: sin el arreglo
        self.assertTrue(DB.numeros_partidos(tbl),
                        "el reparto a prorrata ya no parte números: revisar este control negativo")
        DB._aplicar_anchos(tbl, prorrata)                      # con el arreglo
        self.assertEqual(DB.numeros_partidos(tbl), [])
        self.assertAlmostEqual(sum(_rejilla_cm(tbl)), sum(prorrata), delta=0.05,
                               msg="el arreglo no puede ensanchar la tabla, sólo repartirla distinto")

    def test_los_dos_idiomas_se_protegen_igual(self):
        """El separador de millares cambia con el idioma y la regla no: 1,085,813 y 1.085.813 pesan igual."""
        for lang, num in (("en", "1,085,813"), ("es", "1.085.813")):
            with self.subTest(lang=lang):
                df = pd.DataFrame({"n": [num] * 4, "texto": ["hospitalisation " * 12] * 4,
                                   "otro": ["establecimientos " * 12] * 4})
                doc = DB.nuevo_doc()
                tbl = DB.insertar_tabla(doc, df)
                DB._aplicar_anchos(tbl, [0.8, 7.6, 7.6])       # la columna de la cifra, ahogada
                self.assertEqual(DB.numeros_partidos(tbl), [])

    def test_el_detector_del_pdf_reconoce_un_numero_partido(self):
        """El detector del PDF tiene dientes: ve el corte y no confunde dos celdas vecinas."""
        partido = " 2024   Full F84   1,667,349   993,807   690   41.4   1,085,8   72\n" \
                  "        family                                              13\n"
        self.assertEqual([x["number"] for x in lineas_partidas_en_numero(partido, "en")], ["1,085,813"])
        vecinas = " 2024   86   3,053\n 2025   76   3,034\n"
        self.assertEqual(lineas_partidas_en_numero(vecinas, "en"), [])
        es = " 2024   1.667.349   580.74\n         canonical       0\n"
        self.assertEqual([x["number"] for x in lineas_partidas_en_numero(es, "es")], ["580.740"])

    @unittest.skipIf(CHECK_OFF, "NUM_CHECK=off")
    def test_documentos_construidos_docx(self):
        """Ningún DOCX publicado deja una columna más estrecha que un número que imprime."""
        docs = sorted(p for d in BUILT_DIRS for p in d.glob("*.docx"))
        if not docs:
            self.skipTest("no hay documentos construidos en manuscript/")
        revisados = 0
        for path in docs:
            if not _fresco(path):
                continue
            revisados += 1
            with self.subTest(doc=path.name):
                fallos = DB.revisar_documento(path)
                self.assertEqual(fallos, [], f"{path.name}: {len(fallos)} números partibles, "
                                             f"p. ej. {fallos[0] if fallos else ''}")
        if not revisados:
            self.skipTest("los documentos son anteriores a docx_builder.py: falta reconstruirlos")

    @unittest.skipIf(CHECK_OFF, "NUM_CHECK=off")
    def test_documentos_construidos_pdf(self):
        """Ningún PDF publicado tiene una línea que termina dentro de un número."""
        pdfs = sorted(p for d in BUILT_DIRS for p in d.glob("*.pdf"))
        if not pdfs:
            self.skipTest("no hay PDF construidos en manuscript/")
        revisados = 0
        for path in pdfs:
            if not _fresco(path):
                continue
            texto = _pdftotext(path)
            if texto is None:
                self.skipTest("pdftotext no disponible")
            revisados += 1
            with self.subTest(doc=path.name):
                cortes = lineas_partidas_en_numero(texto, "es" if "_es." in path.name else "en")
                self.assertEqual(cortes, [], f"{path.name}: {len(cortes)} números partidos, "
                                             f"p. ej. {cortes[0] if cortes else ''}")
        if not revisados:
            self.skipTest("los PDF son anteriores a docx_builder.py: falta reconstruirlos")


if __name__ == "__main__":
    unittest.main()
