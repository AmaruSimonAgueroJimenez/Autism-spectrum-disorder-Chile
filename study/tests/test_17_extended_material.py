"""Pruebas del módulo 17 (material extendido dentro del manuscrito).

Verifican, en los dos idiomas y las dos variantes:

  * que ninguna cita de figura o tabla del ARTÍCULO se escriba fuera del registro: cada aparición de
    «Figure N»/«Figura N» o «Table N»/«Tabla N» en el texto del artículo corresponde una a una con una
    cadena producida por `R.mfig()` / `R.mtab()`;
  * que todo número citado exista (dentro del rango de MAIN_FIGURES / MAIN_TABLES y de
    SUPP_FIGURES / SUPP_TABLES) y que el archivo del ítem exista en el disco;
  * que toda figura y toda tabla del artículo se cite al menos una vez;
  * que el orden de primera cita sea 1, 2, 3, … para las figuras y para las tablas;
  * que la parte suplementaria esté dentro del archivo del manuscrito, después de las Referencias, con la
    metodología extendida (todas las ecuaciones numeradas y citadas), las láminas y las tablas;
  * que la numeración suplementaria del manuscrito y la del apéndice separado sean idénticas.

Las leyendas de láminas y las notas de tablas provienen de los módulos que las producen (captions.json /
titles.json) y no del texto de `prose_*`; de ellas solo se exige que cualquier «Figure N» que contengan
apunte a un número que existe.
"""
from pathlib import Path
import re
import sys
import unittest

LA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LA))
import config as CFG  # noqa: E402

HAS_OUTPUTS = all((CFG.OUT / f"values_{v}.json").is_file() for v in ("con_rett", "sin_rett")) and \
    all((CFG.OUT / v / lang / sub / "captions.json").is_file()
        for v in ("con_rett", "sin_rett") for lang in ("en", "es") for sub in ("figures", "extra/figures"))

VARIANTS = ("con_rett", "sin_rett")

# Citas a tablas de documentos externos (informes del MINEDUC) que no son ítems de este artículo.
EXTERNAL = ["(Table 6, p. 11)", "(Tabla 6, p. 11)"]


def _texts(blocks):
    """Texto de los bloques escritos por prose_* (párrafos, viñetas y panel), sin las citas externas."""
    out = []
    for kind, payload in blocks:
        if kind in ("p", "small"):
            out.append(str(payload))
        elif kind == "bullets":
            out += [str(i) for i in payload]
        elif kind == "panel":
            out += [str(t) for _, t in payload["items"]]
    joined = "\n".join(out)
    for phrase in EXTERNAL:
        joined = joined.replace(phrase, "")
    return joined


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las láminas/tablas por variante e idioma")
class ExtendedMaterialTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import prose_en as E
        import prose_es as S
        import supplementary_material as SM
        cls.mods = {"en": E, "es": S}
        cls.SM = SM
        cls.docs = {}
        for lang, P in cls.mods.items():
            for variant in VARIANTS:
                V = P.load_values(variant)
                cls.docs[(lang, variant)] = P._assemble(variant, V)

    # -- el artículo -----------------------------------------------------------------
    def test_no_main_citation_written_outside_the_registry(self):
        for (lang, variant), (art, _, _, R) in self.docs.items():
            P = self.mods[lang]
            pattern = re.compile(rf"\b({R.FIG_WORD}|{R.TAB_WORD})\s+(\d+)")
            found = [f"{m.group(1)} {m.group(2)}" for m in pattern.finditer(_texts(art))]
            self.assertEqual(sorted(found), sorted(R.main_citations[:R.article_citations]),
                             f"{lang}/{variant}: citas de ítems del artículo escritas fuera del registro")
            for label in found:
                word, number = label.split()
                limit = len(P.MAIN_FIGURES) if word == R.FIG_WORD else len(P.MAIN_TABLES)
                self.assertTrue(1 <= int(number) <= limit, f"{lang}/{variant}: {label} no existe")

    def test_every_main_item_is_cited_and_first_citation_order_is_ascending(self):
        for (lang, variant), (art, _, _, R) in self.docs.items():
            P = self.mods[lang]
            self.assertEqual(R.main_figs[:len(P.MAIN_FIGURES)], P.MAIN_FIGURES,
                             f"{lang}/{variant}: el orden de primera cita de las figuras no es 1, 2, 3, …")
            self.assertEqual(R.main_tabs[:len(P.MAIN_TABLES)], P.MAIN_TABLES,
                             f"{lang}/{variant}: el orden de primera cita de las tablas no es 1, 2, 3, …")
            self.assertEqual(set(P.MAIN_FIGURES) - set(R.main_figs), set(), f"{lang}/{variant}: figura no citada")
            self.assertEqual(set(P.MAIN_TABLES) - set(R.main_tabs), set(), f"{lang}/{variant}: tabla no citada")
            # los bloques insertados en el artículo llevan exactamente esos rótulos
            fig_labels = [p["label"] for k, p in art if k == "figure"]
            tab_labels = [p["label"] for k, p in art if k == "table"]
            self.assertEqual(sorted(fig_labels), sorted(f"{R.FIG_WORD} {i}" for i in range(1, len(P.MAIN_FIGURES) + 1)))
            self.assertEqual(sorted(tab_labels), sorted(f"{R.TAB_WORD} {i}" for i in range(1, len(P.MAIN_TABLES) + 1)))

    def test_workflow_plate_is_figure_1_and_source_table_is_table_s1(self):
        for (lang, variant), (art, _, _, R) in self.docs.items():
            P = self.mods[lang]
            self.assertEqual(P.MAIN_FIGURES[0], "fig1_dataflow", lang)
            self.assertNotIn("T1_sources", P.MAIN_TABLES, lang)
            self.assertEqual(P.SUPP_TABLES[0], "T1_sources", lang)
            self.assertEqual(P.SUPP_TABLES[1], "T_dataflow_counts", lang)
            # la lámina de flujo se inserta antes de la lámina de fuentes y cobertura
            figure_keys = [Path(p["path"]).stem for k, p in art if k == "figure"]
            self.assertLess(figure_keys.index("fig1_dataflow"), figure_keys.index("fig1_sources_coverage"), lang)
            self.assertIn(f"{R.TAB_WORD} S1", _texts(art), f"{lang}/{variant}: el artículo no cita la Tabla S1")

    # -- ítems suplementarios --------------------------------------------------------
    def test_supplementary_numbers_cited_exist_and_are_unique(self):
        for (lang, variant), (art, main, supp, R) in self.docs.items():
            P = self.mods[lang]
            pattern = re.compile(rf"\b({R.FIG_WORD}|{R.TAB_WORD})\s+S(\d+)")
            for word, number in pattern.findall(_texts(art) + "\n" + _texts(main)):
                limit = len(P.SUPP_FIGURES) if word == R.FIG_WORD else len(P.SUPP_TABLES)
                self.assertTrue(1 <= int(number) <= limit, f"{lang}/{variant}: {word} S{number} no existe")
            labels = [p["label"] for k, p in supp if k in ("figure", "table")]
            self.assertEqual(len(labels), len(set(labels)), f"{lang}/{variant}: rótulo suplementario repetido")
            self.assertEqual(len(labels), len(P.SUPP_FIGURES) + len(P.SUPP_TABLES), f"{lang}/{variant}")

    def test_every_supplementary_item_file_exists(self):
        for (lang, variant), (_, _, supp, _) in self.docs.items():
            for kind, payload in supp:
                if kind == "figure":
                    self.assertTrue(Path(payload["path"]).is_file(), f"{lang}/{variant}: {payload['label']}")
                    self.assertIn(f"/{lang}/", str(payload["path"]), payload["label"])
                elif kind == "table":
                    self.assertGreater(len(payload["df"]), 0, f"{lang}/{variant}: {payload['label']} sin filas")

    def test_manuscript_and_appendix_share_the_registry(self):
        for variant in VARIANTS:
            en = self.mods["en"].supplementary_map(variant, None)
            es = self.mods["es"].supplementary_map(variant, None)
            self.assertEqual(list(en["figures"]), list(es["figures"]))
            self.assertEqual(list(en["tables"]), list(es["tables"]))
            for key, label in en["figures"].items():
                self.assertEqual(es["figures"][key], label.replace("Figure", "Figura"))
            for key, label in en["tables"].items():
                self.assertEqual(es["tables"][key], label.replace("Table", "Tabla"))
            # los rótulos del apéndice separado coinciden con los del manuscrito
            for lang in ("en", "es"):
                _, main, supp, _ = self.docs[(lang, variant)]
                in_main = {(p["label"], p.get("title") or p.get("caption")) for k, p in main if k in ("figure", "table")}
                in_supp = {(p["label"], p.get("title") or p.get("caption")) for k, p in supp if k in ("figure", "table")}
                self.assertTrue(in_supp <= in_main, f"{lang}/{variant}: el apéndice tiene ítems que el manuscrito no")

    # -- la parte suplementaria dentro del manuscrito ---------------------------------
    def test_supplementary_part_follows_the_references(self):
        import equations as EQ
        for (lang, variant), (art, main, _, _) in self.docs.items():
            P = self.mods[lang]
            self.assertEqual(main[:len(art)], art, f"{lang}/{variant}: el artículo cambió")
            part = main[len(art):]
            kinds = [k for k, _ in part]
            self.assertEqual(kinds[:2], ["pagebreak", "h1"], f"{lang}/{variant}")
            self.assertEqual(part[1][1], P.SUPP_PART_H1, f"{lang}/{variant}")
            self.assertEqual(art[-1][0], "refs", f"{lang}/{variant}: el artículo no termina en Referencias")
            n_eq = sum(1 for k, _ in part if k == "eq")
            self.assertEqual(n_eq, len(EQ.NUMBER), f"{lang}/{variant}: faltan ecuaciones")
            # cada ecuación aparece una sola vez y la serie cubre 1..N sin huecos (el orden de impresión sigue al
            # estimador que la aplica, no al número, y por eso solo se exige el conjunto)
            numbers = [payload[1] for k, payload in part if k == "eq"]
            self.assertEqual(len(set(numbers)), len(numbers), f"{lang}/{variant}: ecuación repetida")
            self.assertEqual(sorted(numbers), list(range(1, n_eq + 1)), f"{lang}/{variant}")
            # cada ecuación se cita en el encabezado del estimador que la aplica
            headings = " ".join(str(p) for k, p in part if k == "h3")
            for number in numbers:
                self.assertRegex(headings, rf"\b{number}\b", f"{lang}/{variant}: ecuación {number} sin citar")

    def test_supplementary_note_and_index_state_the_rules(self):
        for (lang, variant), (art, main, _, _) in self.docs.items():
            note = str(main[len(art) + 2][1])
            index = str(main[len(art) + 3][1])
            keys = (["administrative recognition", "never prevalence", "not linked at the person level", "21.545"]
                    if lang == "en" else
                    ["reconocimiento administrativo", "nunca prevalencia", "no se enlazan a nivel de persona", "21.545"])
            for phrase in keys:
                self.assertIn(phrase, note, f"{lang}/{variant}: la nota no dice «{phrase}»")
            for phrase in (["S1", "S2"] if lang == "en" else ["S1", "S2"]):
                self.assertIn(phrase, index, f"{lang}/{variant}")

    def test_inventory_matches_the_registry(self):
        rows = self.SM.inventory()
        figs = [r for r in rows if r["kind"] == "figure"]
        tabs = [r for r in rows if r["kind"] == "table"]
        self.assertEqual([r["key"] for r in figs], self.SM.FIGURE_ORDER)
        self.assertEqual([r["key"] for r in tabs], self.SM.TABLE_ORDER)
        self.assertEqual(len(set(self.SM.FIGURE_ORDER)), len(self.SM.FIGURE_ORDER))
        self.assertEqual(len(set(self.SM.TABLE_ORDER)), len(self.SM.TABLE_ORDER))
        self.assertEqual(sorted(self.SM.FIGURE_INTRO), sorted(self.SM.FIGURE_ORDER))
        for key in self.SM.METHODS_TABLES:
            self.assertIn(key, self.SM.TABLE_ORDER)


if __name__ == "__main__":
    unittest.main()
