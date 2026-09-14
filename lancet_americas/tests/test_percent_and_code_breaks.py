# -*- coding: utf-8 -*-
"""Ninguna cifra pierde su unidad ni su etiqueta al maquetarse (los dos defectos bloqueantes del cierre).

Son hermanos del defecto F4-1 —un trozo que el lector lee como UNA cosa y que el maquetador partió en dos
líneas— y los dos se le escapaban a la prueba que ya existía (`test_table_numbers_unbroken`), porque ninguno
de los dos trozos era «un número» para el guardián de entonces.

  P1. LA CIFRA DETRÁS DE UNA ETIQUETA. La columna de códigos observados del diccionario JUNAEB imprimía
      «blank=184963»: doce caracteres sin un solo punto de corte. En la Tabla S43 —dieciséis columnas— Word
      partía por donde le tocaba y dejaba «blank=18496» con un «3» suelto debajo, que se lee como 18.496: un
      orden de magnitud. El español no lo sufría («en blanco=184963» ya traía un blanco donde cortar), de modo
      que los dos idiomas imprimían valores distintos, contra la regla del estudio.
      DOS arreglos, porque el defecto tenía dos causas encadenadas: al IMPRIMIR se separa el signo igual con
      blancos (`09b_tables_supplementary._data_states`), y el GUARDIÁN aprende a ver la cifra que viaja detrás
      de una etiqueta (`docx_builder._NUM_ETIQUETA_RE`), de modo que la clase queda cerrada aunque la celda
      volviera a escribirse pegada: medido sobre la Tabla S43 real, el guardián solo —sin tocar la celda— ya
      imprime la cifra entera.

  P2. LA UNIDAD SEPARADA DE SU CIFRA. El español escribe «26 (1,1 %)» con blanco entre la cifra y el signo, y
      en las columnas de 1 a 2 cm de las tablas suplementarias el maquetador imprimía «26 (1,1» arriba y «%)»
      abajo. Medido sobre los doce documentos del 2026-09-08: 1.286 y 1.291 signos huérfanos por documento
      largo español, en 35 páginas, y 28 en cada documento largo INGLÉS.
      También DOS causas. La primera, el blanco: se compone DURO (`docx_builder.pct_indivisible`), donde pasa
      todo lo que se imprime. La segunda —la que el inglés dejaba a la vista, porque ahí la celda dice «14.0%»
      SIN blanco y aun así se partía— es que el ancho del trozo se medía con la tabla de la PROSA, que mete
      toda la puntuación en 0,34 em cuando Times New Roman traza el signo de porcentaje a 0,833: la columna se
      concedía más estrecha que lo que había que meter en ella y el maquetador partía igual. Los trozos
      indivisibles se miden ahora con el avance real de la fuente (`docx_builder._ancho_numero`).

La prueba vigila las TRES puntas, como la de los números:

  1. las HERRAMIENTAS —el espacio duro, el guardián de la etiqueta y la regla con la que se mide un trozo
     indivisible—, cada una con su control negativo para que no puedan quedarse mudas;
  2. la GARANTÍA del constructor sobre la geometría real de las dos tablas que sufrían el defecto, incluida la
     Tabla S43 con la celda SIN arreglar;
  3. los DOCUMENTOS construidos, con la comprobación que vive al lado de la de los números
     (`docx_builder.revisar_pdf`, que busca una línea que empieza por el signo o una cifra cuya unidad se fue a
     la línea siguiente) y con `docx_builder.revisar_documento` sobre la rejilla. Esta última punta se salta
     mientras los archivos de `manuscript/` sean ANTERIORES a `docx_builder.py`.
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

import docx_builder as DB  # noqa: E402

#: The built documents live in two folders since 2026-09-10 (manuscript/04_submission_lancet_americas for
#: the journal package, manuscript/02_others for the full corpus). A non-recursive glob of manuscript/ went
#: silently blind when they moved, so these guards walk BOTH folders and say how many files they read.
MANUSCRIPT = LA / "manuscript"
#: Since 2026-09-14 each version keeps its built documents in a `documents/` subfolder (the builders
#: still write to the folder root), so both places are walked.
BUILT_DIRS = [p for d in (MANUSCRIPT / "04_submission_lancet_americas", MANUSCRIPT / "02_others")
              for p in (d, d / "documents")]
CHECK_OFF = os.environ.get("LANCET_NUM_CHECK", "").lower() in ("off", "0", "no")

#: El avance REAL de Times New Roman (unidades/em = 2048) de los caracteres de «14.0%», en em. Es la vara
#: contra la que se comprueba que la medida de un trozo indivisible no se queda corta.
_TNR_14_0_PCT_EM = 0.5 * 3 + 0.25 + 0.833


# ---------------------------------------------------------------------------
# El detector del PDF para el «etiqueta=cifra» partido dentro de la cifra
# ---------------------------------------------------------------------------
#: Arriba el trozo entero, abajo sólo dígitos, en columnas que se solapan. El del porcentaje vive en
#: `docx_builder.unidades_partidas`, que es la comprobación que se pasa sobre los documentos publicados.
_LABEL_RE = re.compile(r"^[^\W\d_][\w\s]*=\d+$", re.UNICODE)


def _tokens(linea: str):
    return [(m.start(), m.end(), m.group(0)) for m in re.finditer(r"\S+", linea)]


def codigos_partidos(texto: str) -> list[dict]:
    """«etiqueta=cifra» partida entre dos renglones dentro de sus dígitos.

    El discriminante no es la posición del token en su renglón —en la tabla que destapó el defecto la etiqueta
    llevaba tres celdas más a su derecha—, sino si la cifra CONTINÚA en el mismo renglón. El envío a la revista
    escribe los miles con un espacio fino, así que «records=932 839» sale del extractor como dos tokens
    contiguos del mismo renglón: la cifra sigue ahí y no hay corte. Si en cambio nada la continúa a su derecha
    y justo debajo, alineado con ella, hay un grupo de dígitos suelto, el número sí se partió."""
    lineas = texto.split("\n")
    fuera = []
    for i in range(len(lineas) - 1):
        arriba, abajo = _tokens(lineas[i]), _tokens(lineas[i + 1])
        for j, (a0, a1, w1) in enumerate(arriba):
            if not _LABEL_RE.match(w1):
                continue
            sigue = arriba[j + 1] if j + 1 < len(arriba) else None
            if sigue and sigue[0] - a1 <= 2 and re.fullmatch(r"\d{3}[;,]?", sigue[2]):
                continue                      # la cifra continúa en el mismo renglón (separador de miles)
            for b0, b1, w2 in abajo:
                if re.fullmatch(r"\d{1,4}[;,]?", w2) and min(a1, b1) - max(a0, b0) > 0:
                    fuera.append(dict(line=i + 1, head=w1, tail=w2))
    return fuera


def _pdftotext(path: Path) -> str | None:
    try:
        r = subprocess.run(["pdftotext", "-layout", str(path), "-"], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return r.stdout if r.returncode == 0 else None


def _fresco(path: Path) -> bool:
    return path.stat().st_mtime > Path(DB.__file__).stat().st_mtime


# ---------------------------------------------------------------------------
# Las tablas con la geometría de cada defecto
# ---------------------------------------------------------------------------
def _tabla_porcentajes() -> pd.DataFrame:
    """La Tabla de codiagnósticos CIE-10: ocho columnas, glosa larga y celdas «n (p %)» de 1 a 2 cm."""
    cats = ["F39 — Otros trastornos mentales", "Q85", "F06 — Otros trastornos mentales debidos a lesión cerebral",
            "Z62 — Problemas relacionados con la crianza", "K52 — Otras gastroenteritis y colitis no infecciosas"]
    datos = {"Categoría CIE-10 (3 caracteres)": cats}
    for y in range(2019, 2025):
        datos[str(y)] = ["8 (0,3 %)", "26 (1,1 %)", "19 (0,8 %)", "25 (1,0 %)", "11 (0,5 %)"]
    datos["Total 2019–2024"] = ["176", "174", "173", "163", "157"]
    return pd.DataFrame(datos)


def _tabla_codigos(pegado: bool) -> pd.DataFrame:
    """El diccionario JUNAEB: once columnas, dos de ellas con la redacción entera del cuestionario.

    `pegado` escribe la celda como la imprimía la ronda que falló —«blank=184963», sin punto de corte—; con
    `False`, como la escribe hoy el módulo 09b."""
    wording = ("[Trastornos del espectro autista (TEA)] 14. Si respondió Sí en la pregunta anterior, indique la "
               "enfermedad o condición de salud que presenta (puede marcar más de una)")
    filtro = ("El/la estudiante, ¿ha sido diagnosticado/a por un médico con alguna enfermedad o condición de salud "
              "que requiera terapia, tratamiento médico o medicamento por un periodo prolongado de tiempo?")
    codigos = ["blank=184963", "blank=173910; Yes=11053", "blank=175595; Yes=9368", "blank=168637; Yes=16326"]
    if not pegado:
        codigos = [re.sub(r"\s*=\s*(?=\d)", " = ", c) for c in codigos]
    return pd.DataFrame({
        "Year": ["2024"] * 4,
        "Level": ["Grade 9 (1º medio)"] * 4,
        "Files": ["eve_2024_1ero_medio_desidentificado.csv · cp1252 · códigos eve 2024 1 medio.xlsx · "
                  "ENCUESTA 1º MEDIO 2024.pdf"] * 4,
        "ASD variable": ["D15_11"] * 4,
        "ASD item wording": [wording] * 4,
        "Observed ASD codes": codigos,
        "Filter variable": ["D14"] * 4,
        "Filter wording": [filtro] * 4,
        "Auxiliary variables": ["EXP_REG · SEXO · DS_GRADO"] * 4,
        "Other categories": ["16"] * 4,
        "Estimability": ["not estimable"] * 4,
    })


class HerramientasTest(unittest.TestCase):

    def test_el_espacio_duro_entra_en_el_trozo_indivisible(self):
        """«1,1 %» se mide entero; con el espacio normal se medía sólo «1,1», que es de donde venía el corte."""
        blando, duro = "26 (1,1 %)", "26 (1,1 %)"
        self.assertEqual(DB.pct_indivisible(blando), duro)
        self.assertEqual(DB.pct_indivisible(duro), duro, "la conversión tiene que ser idempotente")
        self.assertEqual(DB.numeros_de(duro), ["26", "(1,1 %)"])
        # CONTROL NEGATIVO: con el espacio que PARTE, el trozo que Word tiene que imprimir de una pieza no
        # se ve entero y la columna se medía sobre «(1,1», que es exactamente por donde se partía.
        self.assertEqual(DB.numeros_de(blando), ["26", "(1,1"])
        self.assertGreater(DB._ancho_numero("(1,1 %)", 7.0), DB._ancho_numero("(1,1", 7.0))

    def test_el_porcentaje_ingles_y_la_prosa_no_se_tocan(self):
        """El inglés lo escribe pegado y ahí no hay blanco que endurecer; «95% CI» y «in %,» se quedan igual."""
        for texto in ("41.4 (38.4 to 44.6)", "95% CI", "in %, for each series", "2.6%", "%", "14.0%"):
            self.assertEqual(DB.pct_indivisible(texto), texto)
        # …y aun sin blanco se partía, porque el ANCHO del trozo se medía corto: ése es el otro arreglo.
        self.assertEqual(DB.numeros_de("14.0%"), ["14.0%"])

    def test_un_trozo_indivisible_se_mide_con_el_avance_real_de_la_fuente(self):
        """El signo de porcentaje mide 0,833 em en Times New Roman, no 0,34: medirlo corto partía la celda."""
        real_cm = _TNR_14_0_PCT_EM * 7.0 / 28.3465
        self.assertGreaterEqual(DB._ancho_numero("14.0%", 7.0), real_cm,
                                "la medida de un trozo indivisible no puede quedarse por debajo de la fuente")
        # CONTROL NEGATIVO: la regla de la PROSA sí se queda corta, y de ahí venían los 28 signos huérfanos
        # por documento largo inglés. Esa regla no se toca: mide renglones, no trozos indivisibles.
        self.assertLess(DB._ancho_texto("14.0%", 7.0), real_cm)
        self.assertAlmostEqual(DB._ANCHO_NUM["%"], 0.833, places=3)
        self.assertAlmostEqual(DB._ANCHO_CAR["%"], 0.34, places=3)

    def test_el_guardian_ve_la_cifra_que_viaja_detras_de_una_etiqueta(self):
        """«blank=184963» no tiene un solo punto de corte: o cabe entero, o Word parte dentro de la cifra."""
        self.assertEqual(DB.numeros_de("blank=184963"), ["blank=184963"])
        self.assertEqual(DB.numeros_de("blanco=173910; Sí=11053"), ["blanco=173910;", "Sí=11053"])
        # con la celda ya arreglada por 09b sobra la etiqueta: queda el número, y ocupa bastante menos
        self.assertEqual(DB.numeros_de("blank = 184963"), ["184963"])
        self.assertGreater(DB._ancho_numero("blank=184963", 6.0), DB._ancho_numero("184963", 6.0))
        # CONTROL NEGATIVO: un identificador con cifras NO es un número y tiene que poder partirse, que es lo
        # que hace falta para que quepan las tablas de procedencia. Sin esto, la URL de un microdato pediría
        # nueve centímetros de columna.
        for texto in ("F84.2", "D15_11", "GRD_PUBLICO_2019.csv", "1b86155938fd", "doi:10.1093", "EPSG:3857;",
                      "eve_2024_1ero_medio_desidentificado.csv",
                      "EV_2019_JUNAEB_1ero_basico_desidentificada.csv?generation=1762186542578959"):
            with self.subTest(texto=texto):
                self.assertEqual(DB.numeros_de(texto), [])

    def test_los_detectores_del_pdf_tienen_dientes(self):
        """Ven las dos caras del corte y no confunden la prosa correcta, dos celdas vecinas ni una cabecera."""
        roto = (" Q85            26 (1,1     11 (0,7     43 (0,7 %)      174\n"
                "                  %)          %)\n")
        self.assertEqual([x["head"] for x in DB.unidades_partidas(roto)], ["(1,1", "(0,7"])
        renglon = ("de los episodios, frente a 12,4\n"
                   "% en 2019, con un intervalo de\n")
        self.assertEqual([(x["head"], x["caso"]) for x in DB.unidades_partidas(renglon)], [("12,4", "linea")])
        prosa = ("2019 a 8.818 (812,1) en 2024 (CPA 35,6 %, IC 95 % 29,7 a 41,9; 32,6–\n"
                 "62,9 % entre especificaciones); el 95,5 % llevaba F84 solo como secundario\n")
        self.assertEqual(DB.unidades_partidas(prosa), [])
        # el folio de una página sobre la cabecera «% (IC 95 %)» de la siguiente NO es un signo huérfano
        folio = ("                                        208\n"
                 " Encuesta   Dominio     Subgrupo    n    Casos   % (IC 95 %)   Total\n")
        self.assertEqual(DB.unidades_partidas(folio), [])
        partido = (" 2024   Grade 9   [Trastornos    blank=18496    D14    16    not estimable\n"
                   "                  del espectro        3\n")
        self.assertEqual([x["head"] for x in codigos_partidos(partido)], ["blank=18496"])
        vecinas = " 2024   86   3,053\n 2025   76   3,034\n"
        self.assertEqual(codigos_partidos(vecinas), [])
        self.assertEqual(DB.unidades_partidas(vecinas), [])


class ConstructorTest(unittest.TestCase):

    def test_la_tabla_de_codiagnosticos_no_deja_un_signo_solo(self):
        """Ocho columnas y celdas «n (p %)»: la geometría exacta del defecto, ahogada a mano."""
        df = _tabla_porcentajes()
        doc = DB.nuevo_doc()
        tbl = DB.insertar_tabla(doc, df)
        self.assertIn(" ", tbl.rows[1].cells[1].text, "la celda no se escribió con el espacio duro")
        DB._aplicar_anchos(tbl, [5.0] + [1.2] * 6 + [1.4])       # columnas estrechas: el caso que fallaba
        self.assertEqual(DB.numeros_partidos(tbl), [])

    def test_el_diccionario_junaeb_no_parte_la_frecuencia(self):
        """Once columnas con dos redacciones enteras: la geometría de la Tabla S43, con la celda arreglada."""
        tbl = DB.insertar_tabla(DB.nuevo_doc(), _tabla_codigos(pegado=False))
        self.assertEqual(DB.numeros_partidos(tbl), [])

    def test_el_guardian_solo_ya_salva_la_frecuencia_pegada_a_su_etiqueta(self):
        """La misma tabla con la celda SIN arreglar: el guardián le concede la columna y la cifra sale entera.

        Es lo que cierra la CLASE y no sólo la celda que se vio en el papel: si mañana otro generador vuelve a
        escribir «etiqueta=cifra» sin blanco, el número sigue sin partirse."""
        tbl = DB.insertar_tabla(DB.nuevo_doc(), _tabla_codigos(pegado=True))
        self.assertIn("blank=184963", tbl.rows[1].cells[5].text)
        self.assertEqual(DB.numeros_partidos(tbl), [])


class DocumentosTest(unittest.TestCase):

    @unittest.skipIf(CHECK_OFF, "LANCET_NUM_CHECK=off")
    def test_ningun_pdf_deja_una_unidad_ni_un_codigo_partido(self):
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
                uni = DB.unidades_partidas(texto)
                self.assertEqual(uni, [], f"{path.name}: {len(uni)} unidades separadas de su cifra, "
                                          f"p. ej. {uni[0] if uni else ''}")
                cod = codigos_partidos(texto)
                self.assertEqual(cod, [], f"{path.name}: {len(cod)} códigos partidos dentro de su cifra, "
                                          f"p. ej. {cod[0] if cod else ''}")
        if not revisados:
            self.skipTest("los PDF son anteriores a docx_builder.py: falta reconstruirlos")


if __name__ == "__main__":
    unittest.main()
