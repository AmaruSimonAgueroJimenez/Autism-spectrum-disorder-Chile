"""Pruebas de pipeline/10_manuscript.py: transformaciones de bloques, localización de referencias, ecuaciones de la
metodología extendida, posproceso del DOCX (numeración de páginas y secciones apaisadas) y hoja de contacto.
No convierte a PDF."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

LA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LA))
import config as CFG  # noqa: E402

spec = importlib.util.spec_from_file_location("m10", LA / "pipeline" / "10_manuscript.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

HAS_OUTPUTS = all((CFG.OUT / f"values_{v}.json").is_file() for v in ("con_rett", "sin_rett")) and \
    (CFG.OUT / "con_rett" / "en" / "figures" / "captions.json").is_file()


class UnitTest(unittest.TestCase):
    def test_strip_opt_with_index(self):
        blocks = [("h1", "Methods"), ("h2", "Statistical analysis"), ("p", "Core paragraph [@zeidan2022]."),
                  ("p", M.OPT + "Optional paragraph with **bold** and a citation [@zeidan2022] here."),
                  ("h1", "Discussion"), ("p", M.OPT + "Second optional paragraph.")]
        out, index = M.strip_opt_with_index(blocks, "en")
        self.assertEqual(len(index), 2)
        self.assertFalse(any(str(p).startswith(M.OPT) for k, p in out if k == "p"))
        self.assertEqual(index[0]["section"], "Methods")
        self.assertEqual(index[0]["subsection"], "Statistical analysis")
        self.assertIsNone(index[1]["subsection"])
        self.assertNotIn("[@", index[0]["excerpt"])
        self.assertNotIn("**", index[0]["excerpt"])
        self.assertEqual(out[3][1], "Optional paragraph with **bold** and a citation [@zeidan2022] here.")
        idx_blocks = M.optional_index_blocks(index, "en", 4000)
        self.assertEqual([k for k, _ in idx_blocks], ["pagebreak", "h1", "p", "bullets"])
        self.assertEqual(idx_blocks[1][1], "Optional material index")
        self.assertEqual(len(idx_blocks[3][1]), 2)

    def test_localise_reference(self):
        ref = "Autor A. Título. En: Editor B, editores. Libro. Editorial; 2020. Disponible en: https://x"
        en = M.localise_reference(ref, "en")
        self.assertIn(" In: ", en)
        self.assertIn(", editors.", en)
        self.assertIn("Available from:", en)
        self.assertNotIn("Disponible", en)
        self.assertEqual(M.localise_reference(ref, "es"), ref)

    def test_equations_are_numbered_and_rendered(self):
        """Las ecuaciones del documento son las de equations: numeración 1..N sin huecos, todas compuestas y
        todas asignadas a un estimador (la sección S6 con las 17 ecuaciones de paper/equations.py fue sustituida por
        la metodología extendida, que las contiene todas)."""
        numbers = sorted(M.EQ.NUMBER.values())
        self.assertEqual(numbers, list(range(1, len(numbers) + 1)))
        self.assertGreaterEqual(len(numbers), 17)
        self.assertEqual(M.EQ.orphan_equations(), [])
        self.assertEqual(M.EQ.orphan_estimators(), [])
        rendered = M.EQ.ensure_rendered()
        self.assertEqual(set(rendered), set(M.EQ.NUMBER))
        for key, paths in rendered.items():
            for path in paths:
                self.assertTrue(Path(path).is_file(), f"{key}: {path}")

    def test_paper_authors(self):
        authors, affiliations = M.load_paper_authors()
        self.assertTrue(authors and affiliations)
        self.assertEqual(len(authors[0]), 3)
        payload = M.authors_payload("en", M.prose_en, authors, affiliations, ["x"])
        self.assertTrue(payload["affiliations"][0][1].startswith("["))
        self.assertIn("affiliation", payload["affiliations"][0][1].lower())

    def test_min_widths_and_contact_sheet(self):
        cols = ["Source", "Explanation"]
        textos = [["GRD", "REM"], ["a very long explanation with words", "short"]]
        mins = M._min_widths_cm(cols, textos, 8.0)
        self.assertEqual(len(mins), 2)
        self.assertGreater(mins[1], mins[0])
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            pages = []
            for i in range(3):
                p = Path(tmp) / f"page-{i + 1:02d}.png"
                Image.new("RGB", (372, 526), "white").save(p)
                pages.append(p)
            out = M.contact_sheet(pages, Path(tmp) / "sheet.png", cols=2, thumb_w=100)
            with Image.open(out) as im:
                self.assertEqual(im.width, 6 + 2 * 106)
                self.assertGreater(im.height, 2 * 141)


class FullPagePlateTest(unittest.TestCase):
    """Colocación a página completa de las láminas verticales (180 × 245 mm) y sus cortes de sección.

    Lo que se comprueba es el CONTRATO de la colocación, no un número mágico: con una leyenda corta la
    lámina se imprime a sus 180 mm; con una leyenda larga se ajusta pero nunca por debajo del ancho de la
    columna de texto del cuerpo; entradilla, imagen y leyenda caben en una sola página siempre que el
    modo no sea `spill`; una lámina apaisada heredada sigue en el flujo del texto; y dos láminas
    consecutivas comparten una sola sección para que entre ellas no aparezca una página en blanco."""

    @staticmethod
    def _png(tmp, w, h, name="plate.png"):
        from PIL import Image
        path = Path(tmp) / name
        Image.new("RGB", (w, h), "white").save(path)
        return path

    def _fig(self, path, caption, label):
        return ("figure", dict(path=str(path), caption=caption, label=label))

    def test_short_caption_prints_the_plate_at_its_natural_180_mm(self):
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            lay = DB.plate_layout(self._png(tmp, 4251, 5787), "One short sentence about the plate.", "Figure S1")
            self.assertEqual(lay["mode"], "natural")
            self.assertAlmostEqual(lay["width_cm"], DB.PLATE_NATURAL_W_CM, places=6)
            self.assertLessEqual(lay["height_cm"], DB.PLATE_TEXT_H_CM)

    def test_a_long_caption_never_shrinks_the_plate(self):
        """La lámina se imprime SIEMPRE a 180 mm: lo que cede ante una leyenda larga es la LEYENDA.

        Antes la lámina se encogía hasta el ancho de la columna de texto (160 mm) y sus anotaciones de 6 pt
        se imprimían a 5,3 pt, por debajo del mínimo de la revista. Ahora se compone la leyenda al mayor
        cuerpo que quepa (9 → 7 pt) y, si ninguno cabe entero, se compone al SUELO de la escala y continúa
        en la página siguiente: la leyenda se parte, no se encoge por debajo de los 7 pt."""
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            justa = DB.plate_layout(png, "Panel a shows the annual series. " * 66, "Figure S2")
            enorme = DB.plate_layout(png, "Panel a shows the annual series. " * 200, "Figure S3")
            mayor = DB.plate_layout(png, "Panel a shows the annual series. " * 400, "Figure S4")
            for lay in (justa, enorme, mayor):
                self.assertAlmostEqual(lay["width_cm"], DB.PLATE_NATURAL_W_CM, places=6)
            # una leyenda larga que todavía cabe: se compone al suelo, pero entera y en su página
            self.assertEqual(justa["mode"], "natural")
            self.assertEqual(justa["caption_pt"], DB.PLATE_CAP_PT[-1])
            # una que no cabe a ningún cuerpo: al suelo y con cola
            for lay in (enorme, mayor):
                self.assertEqual(lay["caption_pt"], DB.PLATE_CAP_FALLBACK_PT,
                                 "la leyenda que va a partirse se compone al suelo, no más pequeña")
                self.assertEqual(lay["mode"], "spill")
                self.assertGreater(lay["spill_cm"], 0.0)
            self.assertGreater(mayor["spill_cm"], enorme["spill_cm"])
            self.assertEqual(DB.PLATE_CAP_FALLBACK_PT, min(DB.PLATE_CAP_PT),
                             "la leyenda que se parte se compone al suelo de la escala")
            self.assertGreaterEqual(DB.PLATE_MIN_W_CM, DB.PLATE_NATURAL_W_CM,
                                    "el suelo de ancho no puede ser menor que el ancho natural de la lámina")

    def test_no_caption_is_ever_composed_below_seven_points(self):
        """El SUELO tipográfico de la leyenda es 7 pt (fase 4e, tarea Y2).

        Seis leyendas de los doce documentos se imprimían a 6,0 pt —la Figura 3 de los cuatro documentos en
        español y la Figura S54 de los dos con_rett en español— porque el builder tenía un escalón más de
        escala para meter entera una leyenda que se quedaba a una línea de caber. Seis puntos es el tamaño
        de las anotaciones dibujadas DENTRO de la lámina, no el de un párrafo de catorce líneas. Ahora la
        leyenda que no cabe se PARTE al suelo de 7 pt y la cola pasa a la página siguiente acompañada. El
        único escalón por debajo, `PLATE_CAP_STRAND_PT` (6,5 pt), existe sólo para la cola que se quedaría
        sola en una página, y nunca se baja de ahí."""
        import docx_builder as DB
        self.assertEqual(min(DB.PLATE_CAP_PT), 7.0, "el suelo de la escala de leyenda es 7 pt")
        for nombre in ("PLATE_CAP_MIN_PT", "PLATE_CAP_STANDALONE_PT", "PLATE_CAP_FALLBACK_PT"):
            self.assertEqual(getattr(DB, nombre), 7.0, f"{nombre} tiene que ser el suelo de 7 pt")
        self.assertEqual(DB.PLATE_CAP_STRAND_PT, 6.5,
                         "el único escalón bajo el suelo salva una página, no aprieta un párrafo")
        self.assertFalse(hasattr(DB, "PLATE_CAP_TIGHT_PT"), "el escalón de 6,0 pt ya no existe")
        self.assertGreaterEqual(DB.PLATE_LEAD_PT[-1], DB.PLATE_CAP_STRAND_PT,
                                "la entradilla nunca se compone menor que la leyenda")
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            # una tanda de leyendas de todos los largos: ninguna baja del suelo salvo para salvar una página
            blocks = [("h1", "Supplementary figures")]
            for n in range(1, 15):
                blocks.append(("p", f"Figure S{n} gives the annual series of the hospital lane by region."))
                blocks.append(self._fig(png, "Panel (a) gives the annual series. " * (4 * n), f"Figure S{n}"))
            blocks.append(("p", "The supplementary tables follow, with the same numbering."))
            plan = DB.plan_full_page_plates(blocks, "en", True)
            self.assertEqual(len(plan), 14)
            for v in plan.values():
                self.assertGreaterEqual(v["layout"]["caption_pt"], DB.PLATE_CAP_STRAND_PT,
                                        f"{v['label']} se compuso por debajo de 6,5 pt")
            cuerpos = {v["layout"]["caption_pt"] for v in plan.values()}
            self.assertTrue(cuerpos <= set(DB.PLATE_CAP_PT) | {DB.PLATE_CAP_STRAND_PT},
                            f"cuerpos fuera de la escala: {sorted(cuerpos)}")

    def test_a_caption_below_the_floor_has_to_save_a_page_from_carrying_only_a_tail(self):
        """El escalón de 6,5 pt sólo se gasta donde SALVA una página, y se comprueba que la salva.

        Dentro de una tanda la cola de una leyenda cae sobre la página de la lámina siguiente; cuando crece
        tanto que esa lámina ya no cabe en ella, la página se queda con la cola y nada más. Medio punto menos
        de leyenda devuelve el presupuesto justo para que la lámina siguiente entre: ése es el único caso en
        que se baja del suelo, y sólo si de verdad lo devuelve.

        Lo que se exige es que el medio punto COMPRE algo —que haya menos páginas de cola sola con el escalón
        que sin él— y que se gaste sólo donde compra. NO se exige que las quite todas, y desde la fase 4j se
        mide por qué: con la leyenda partida en el código, la cola es un párrafo con su rótulo y su altura se
        compone, no se estima por diferencia de renglones. Ocho leyendas seguidas de trece líneas piden más
        renglones de los que una caja de 28,68 cm deja bajo una lámina de 245 mm, y ninguna composición
        legítima —el suelo de 7,0 pt, la lámina a 180 mm y la leyenda entera— los crea. La versión anterior
        de esta guardia exigía cero páginas de cola sola y pasaba porque la cuenta de la cola se quedaba
        corta: descontaba renglones sin componer el rótulo «Figure SN (continued). » que los empuja."""
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            lead = "Figure S{n} contrasts the two case-definition variants in the hospital series by region."
            caption = "Panel (a) gives the annual series with its exact interval and its denominator. " * 27
            blocks = [("h1", "Supplementary figures")]
            for n in range(1, 9):
                blocks.append(("p", lead.format(n=n)))
                blocks.append(self._fig(png, caption, f"Figure S{n}"))
            plan = DB.plan_full_page_plates(blocks, "en", True)
            orden = [plan[i] for i in sorted(plan)]
            bajo = [v for v in orden if v["layout"]["caption_pt"] < DB.PLATE_CAP_MIN_PT]
            self.assertTrue(bajo, "el caso de prueba tiene que ejercitar el escalón de 6,5 pt")
            for v in bajo:
                self.assertEqual(v["layout"]["caption_pt"], DB.PLATE_CAP_STRAND_PT)
                siguiente = orden[orden.index(v) + 1]
                self.assertFalse(siguiente["own_page"],
                                 f"{v['label']} se compuso a 6,5 pt sin salvar la página de "
                                 f"{siguiente['label']}")
            # y sin el escalón —el suelo aplicado a rajatabla— hay MÁS páginas que se quedan con la cola
            # sola: es lo que prueba que el medio punto compra algo y no se gasta por gusto
            suelo = DB.PLATE_CAP_STRAND_PT
            try:
                DB.PLATE_CAP_STRAND_PT = DB.PLATE_CAP_MIN_PT
                sin_escalon = DB.plan_full_page_plates(blocks, "en", True)
            finally:
                DB.PLATE_CAP_STRAND_PT = suelo
            con, sin = (sum(1 for v in orden if v["own_page"]),
                        sum(1 for v in sin_escalon.values() if v["own_page"]))
            self.assertTrue(sin, "sin el escalón tiene que aparecer la página que lleva sólo la cola")
            self.assertLess(con, sin, "con el escalón tiene que haber MENOS páginas de cola sola que sin él")

    def test_a_caption_with_nothing_behind_it_does_not_send_its_tail_to_an_empty_page(self):
        """La otra mitad de la norma: la cola cae ACOMPAÑADA, y si no puede, la leyenda no se parte.

        Detrás de una lámina que cierra sección, la cola se imprime en el cuerpo del texto y la sigue lo que
        venía detrás de la lámina —un título y sus párrafos—, de modo que la página se llena. Cuando no viene
        NADA detrás, esa página llevaría la cola y 26 cm de papel en blanco: ahí, y sólo ahí, la leyenda baja
        al escalón de 6,5 pt para entrar entera. Si ni a 6,5 entra, se parte igual: encogerla más no salva la
        página. En los doce documentos del estudio el caso no se da —detrás de cada lámina que cierra sección
        hay entre 6 y 189 bloques—, y la guardia existe para el día que un cambio de prosa lo cambie."""
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            lead = "Figure S9 summarises the annual series of the region."
            caption = "Panel (a) gives the annual series with its exact interval. " * 36
            sola = DB.plan_full_page_plates(
                [("p", lead), self._fig(png, caption, "Figure S9")], "en", True)
            acompanada = DB.plan_full_page_plates(
                [("p", lead), self._fig(png, caption, "Figure S9"),
                 ("p", "The text continues here with a full paragraph that fills the page.")], "en", True)
            v_sola, v_acomp = list(sola.values())[0], list(acompanada.values())[0]
            self.assertTrue(v_sola["close_section"] and v_acomp["close_section"])
            # con texto detrás: al suelo y partida, que es la norma
            self.assertEqual(v_acomp["layout"]["caption_pt"], DB.PLATE_CAP_MIN_PT)
            self.assertEqual(v_acomp["layout"]["mode"], "spill")
            self.assertTrue(v_acomp["split_caption"])
            # sin nada detrás: entera al escalón de 6,5, porque la cola se quedaría sola
            self.assertEqual(v_sola["layout"]["caption_pt"], DB.PLATE_CAP_STRAND_PT)
            self.assertEqual(v_sola["layout"]["mode"], "natural")
            self.assertFalse(v_sola["split_caption"])
            # y una leyenda a la que 6,5 tampoco le basta se parte igual, sin bajar más
            enorme = "Panel (a) gives the annual series with its exact interval. " * 60
            v = list(DB.plan_full_page_plates(
                [("p", lead), self._fig(png, enorme, "Figure S9")], "en", True).values())[0]
            self.assertEqual(v["layout"]["caption_pt"], DB.PLATE_CAP_MIN_PT)
            self.assertTrue(v["split_caption"])

    def test_lead_in_image_and_caption_fit_a_single_page(self):
        import docx_builder as DB
        lead = ("Figure S4 compares the June and December cuts of the REM stocks, which are never summed. "
                "The unit is the person in the stock at the date and there is no denominator.")
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            for n in (10, 25, 40):
                caption = "(a) The fixed panel of 65 hospitals. " * n
                lay = DB.plate_layout(png, caption, "Figure S4", lead)
                if lay["mode"] == "spill":
                    continue
                alto = (lay["lead_cm"] + lay["height_cm"] + DB.PLATE_GAP_CM
                        + DB._text_cm("Figure S4. " + caption, lay["caption_pt"], DB.PLATE_TEXT_W_CM,
                                      line=1.0, space_before=3))
                self.assertLessEqual(alto, DB.PLATE_TEXT_H_CM, f"{n} repeticiones no caben en la página")

    def test_a_legacy_landscape_plate_stays_in_the_flow(self):
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(DB.is_full_page_plate(self._png(tmp, 4251, 5787, "vertical.png")))
            self.assertFalse(DB.is_full_page_plate(self._png(tmp, 10269, 6544, "apaisada.png")))
            blocks = [("p", "Lead."), self._fig(self._png(tmp, 10269, 6544, "b.png"), "Caption.", "Figure S1")]
            self.assertEqual(DB.plan_full_page_plates(blocks, "en", True), {})

    def test_consecutive_plates_share_one_section_and_carry_their_lead_in(self):
        """Cada lámina viaja con SU frase de presentación y la tanda comparte una sola sección.

        La frase de presentación ya no se queda nunca en el texto: componerla a 12 pt con interlineado 1,5
        la dejaba fuera de la página de su lámina y el documento imprimía 43 páginas con dos líneas y nada
        más. Ahora se compone al cuerpo que quepa (12 → 7,5 pt) y entra siempre. Dentro de la tanda no se
        fuerza el salto de página: la entradilla lleva keepNext y arrastra su lámina."""
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            blocks = [("h2", "Core supplementary figures"),
                      ("p", "Figure S1 contrasts the two case-definition variants."),
                      self._fig(png, "Short caption.", "Figure S1"),
                      ("p", "Figure S2 decomposes the F84 family into subcodes."),
                      self._fig(png, "Short caption.", "Figure S2"),
                      ("h2", "Supplementary tables")]
            plan = DB.plan_full_page_plates(blocks, "en", True)
            primero, segundo = sorted(plan)
            for k in (primero, segundo):
                self.assertEqual(plan[k]["lead_index"], k - 1, "la entradilla viaja con su lámina")
                self.assertGreater(plan[k]["layout"]["lead_cm"], 0.0)
                self.assertGreaterEqual(plan[k]["layout"]["lead_pt"], plan[k]["layout"]["caption_pt"],
                                        "la entradilla nunca se compone menor que la leyenda")
                self.assertFalse(plan[k]["page_break"], "dentro de la tanda no se fuerza el salto")
            self.assertEqual(plan[primero]["start_index"], primero - 2)   # el título entra con la lámina
            self.assertTrue(plan[primero]["open_section"])
            self.assertFalse(plan[primero]["close_section"])
            self.assertFalse(plan[segundo]["open_section"])
            self.assertTrue(plan[segundo]["close_section"])
            self.assertTrue(plan[primero]["lead_keep"], "sin cola delante, la entradilla se pega a su lámina")

    def test_every_plate_keeps_its_lead_in_even_behind_a_caption_tail(self):
        """La entradilla viaja con SU lámina, con cola de leyenda delante o sin ella.

        La regla anterior soltaba el keepNext cuando la página traía la cola de la leyenda anterior, para
        que la frase se quedara con esa cola en vez de dejarla sola. Impreso, eso dejaba la frase de
        presentación de 6 a 12 de las 54 láminas en la página ANTERIOR a su lámina, que es justamente lo
        que una frase de presentación no puede hacer. Ahora se pega siempre; el papel en blanco se ataca en
        el presupuesto de la página, no soltando la frase."""
        import docx_builder as DB
        caption = ("Panel (a) gives the annual series with its exact interval and panel (b) the same series "
                   "for the restricted definition; the unit is the episode and the denominator the episodes "
                   "of the same year. ") * 8
        lead = ("Figure S{n} contrasts the two case-definition variants in the hospital series. The unit is "
                "the GRD episode and the denominator the GRD episodes of the same year, panel and activity.")
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            blocks = [("h1", "Supplementary figures")]
            for n in range(1, 13):
                blocks.append(("p", lead.format(n=n)))
                blocks.append(self._fig(png, caption, f"Figure S{n}"))
            plan = DB.plan_full_page_plates(blocks, "en", True)
            self.assertEqual(len(plan), 12)
            for i, v in sorted(plan.items()):
                self.assertEqual(v["lead_index"], i - 1, f"{v['label']} dejó fuera su frase de presentación")
                self.assertGreater(v["layout"]["lead_cm"], 0.0, f"{v['label']} no reserva sitio para ella")
                self.assertTrue(v["lead_keep"], f"{v['label']} soltó su frase de presentación")
            self.assertTrue(any(v["layout"]["spill_cm"] > 0 for v in plan.values()),
                            "el caso de prueba tiene que ejercitar la cola de la leyenda")

    def test_a_spilling_caption_is_split_where_the_page_ends(self):
        """La leyenda que no cabe se parte por la línea exacta que cabe bajo la lámina.

        Es lo que permite que la cola no se quede sola cuando detrás de ella se cierra la sección: la
        cabeza se imprime con la imagen y la cola pasa al cuerpo del texto."""
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            caption = "Panel (a) gives the annual series with its exact interval. " * 60
            lay = DB.plate_layout(png, caption, "Figure 3")
            self.assertEqual(lay["mode"], "spill")
            self.assertGreater(lay["caption_lines_total"], lay["caption_lines_page"])
            cabeza, cola = DB.split_caption_lines("Figure 3. ", caption, lay["caption_pt"],
                                                  lay["caption_lines_page"])
            self.assertTrue(cabeza and cola)
            self.assertEqual(DB._wrapped_lines("Figure 3. " + cabeza, lay["caption_pt"], DB.PLATE_TEXT_W_CM),
                             lay["caption_lines_page"])
            self.assertEqual((cabeza + " " + cola).split(), caption.split(),
                             "partir la leyenda no puede perder ni repetir una palabra")

    def test_the_article_figure_prints_its_caption_tail_in_the_body_section(self):
        """El defecto del ARTÍCULO: la cola de la leyenda se quedaba sola con 28 cm de papel en blanco.

        Con la sección de lámina cerrada justo detrás de la leyenda, la cola no puede fluir hacia ninguna
        lámina siguiente. Se parte en el código y la cola se imprime DESPUÉS del corte de sección, en el
        cuerpo del texto, donde la sigue el párrafo siguiente."""
        from docx import Document
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            caption = "Panel (a) gives the annual series with its exact interval. " * 60
            blocks = [("p", "Figure 3 gives the annual series of the hospital lane."),
                      self._fig(png, caption, "Figure 3"),
                      ("p", "The discussion continues here with a full paragraph of running text.")]
            out = Path(tmp) / "art.docx"
            r = DB.build_document(blocks, "en", out)
            self.assertTrue(r["full_page_plates"][0]["caption_split"])
            textos = [p.text for p in Document(str(out)).paragraphs if p.text.strip()]
            cont = [t for t in textos if t.startswith("Figure 3 (continued).")]
            self.assertEqual(len(cont), 1, "la cola tiene que imprimirse rotulada, una sola vez")
            self.assertLess(textos.index(cont[0]), textos.index(textos[-1]),
                            "la cola va ANTES del párrafo siguiente, que es el que llena la página")
            cabeza = [t for t in textos if t.startswith("Figure 3.") and "(continued)" not in t][0]
            impresa = (cabeza[len("Figure 3. "):] + " " + cont[0][len("Figure 3 (continued). "):]).split()
            self.assertEqual(impresa, caption.split(),
                             "entre la cabeza y la cola tiene que estar la leyenda entera, sin repetir nada")

    def test_a_plate_always_prints_at_least_the_opening_of_its_legend(self):
        """Bajo la lámina se imprime SIEMPRE leyenda, no sólo el rótulo.

        El presupuesto de la página descuenta la cola de la leyenda anterior, que es una predicción; cuando
        no llega, la cuenta dejaba cero líneas y la lámina se imprimía con «Figura S54.» y nada debajo: una
        figura sin pie. `PLATE_CAP_MIN_LINES` es el suelo, y `split_caption_lines` nunca recibe cero."""
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            caption = "Panel (a) gives the annual series with its exact interval. " * 14
            lead = ("Figure S54 summarises the same territorial analysis at regional scale, where the counts "
                    "are larger and the intervals narrower. The unit is the region.")
            # presupuesto exiguo: la página llega con 2,9 cm de cola de la leyenda anterior encima
            lay = DB.plate_layout(png, caption, "Figure S54", lead, budget_cm=DB.PLATE_TEXT_H_CM - 2.9)
            self.assertEqual(lay["mode"], "spill")
            self.assertGreaterEqual(lay["caption_lines_page"], DB.PLATE_CAP_MIN_LINES,
                                    "una lámina no puede quedarse sin ninguna línea de leyenda")
            cabeza, cola = DB.split_caption_lines("Figure S54. ", caption, lay["caption_pt"],
                                                  lay["caption_lines_page"])
            self.assertTrue(cabeza, "el rótulo no puede imprimirse solo bajo la lámina")
            self.assertTrue(cola)
            self.assertEqual((cabeza + " " + cola).split(), caption.split())

    def test_a_caption_that_overflows_a_whole_page_is_split_and_labelled_without_a_section_break(self):
        """La Figura 1 del artículo: 37–39 líneas de leyenda que no caben ni con la página entera.

        Detrás de ella NO se cierra la sección (la Figura 2 va inmediatamente después), de modo que la cola
        no pasaba por `split_caption_lines` y Word la partía donde quería: la página siguiente abría a media
        frase y sin rótulo, mientras las Figuras 2, 4 y 5 del mismo artículo sí lo llevaban. Ahora se parte
        en el código y la cola se imprime rotulada al principio de su página."""
        from docx import Document
        from docx.oxml.ns import qn
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            larga = "Panel (a) gives the annual series with its exact interval. " * 130
            corta = "Panel (a) gives the annual series. " * 4
            blocks = [self._fig(png, larga, "Figure 1"), self._fig(png, corta, "Figure 2"),
                      ("p", "The results continue here with a full paragraph of running text.")]
            plan = DB.plan_full_page_plates(blocks, "en")
            primera = plan[0]
            self.assertFalse(primera["close_section"], "la Figura 2 va detrás: la sección no se cierra")
            self.assertGreater(primera["structural_spill_cm"], DB.PLATE_SPILL_LABEL_CM)
            self.assertTrue(primera["split_caption"], "una leyenda que desborda la página entera se parte")
            self.assertEqual(primera["layout"]["caption_pt"], DB.PLATE_CAP_FALLBACK_PT,
                             "la cola cae sobre la página de la lámina siguiente: se compone al menor cuerpo")
            out = Path(tmp) / "art.docx"
            r = DB.build_document(blocks, "en", out)
            self.assertTrue(r["full_page_plates"][0]["caption_split"])
            doc = Document(str(out))
            cont = [p for p in doc.paragraphs if p.text.startswith("Figure 1 (continued).")]
            self.assertEqual(len(cont), 1, "la cola de la Figura 1 tiene que ir rotulada")
            ppr = cont[0]._p.find(qn("w:pPr"))
            saltos = cont[0]._p.findall(".//" + qn("w:br"))
            self.assertTrue(ppr.find(qn("w:pageBreakBefore")) is not None or
                            any(b.get(qn("w:type")) == "page" for b in saltos),
                            "sin corte de sección detrás, el salto de página lo pone la cola")
            cabeza = [p.text for p in doc.paragraphs
                      if p.text.startswith("Figure 1.") and "(continued)" not in p.text][0]
            impresa = (cabeza[len("Figure 1. "):] + " "
                       + cont[0].text[len("Figure 1 (continued). "):]).split()
            self.assertEqual(impresa, larga.split(), "la leyenda entera, sin perder ni repetir una palabra")
            # una leyenda que sí cabe en su página no se parte ni se rotula
            self.assertFalse(plan[1]["split_caption"])

    def test_every_caption_that_does_not_fit_is_split_and_labelled(self):
        """La regla de J1: dentro de una tanda, la cola de TODA leyenda que no cabe va rotulada.

        Antes se rotulaba sólo cuando detrás de la lámina se cerraba la sección o cuando la leyenda
        desbordaba la página entera; dentro de una tanda la leyenda viajaba como un párrafo y era Word quien
        la partía, sin poder poner rótulo. Sobre los doce PDF del 2026-09-08 eso dejaba 100 colas sin dueño
        visible. Se comprueba lo que el lector ve: cada cola lleva su rótulo, empieza página, y la leyenda
        impresa —cabeza más cola— es la leyenda entera, sin perder ni repetir una palabra."""
        from docx import Document
        from docx.oxml.ns import qn
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            lead = "Figure S{n} maps the comuna-level indicator and its spatial lag."
            caption = ("(a) Local classification of the indicator with its permutation p; the compatibility "
                       "warning applies to every panel of this plate. " * 14)
            blocks = [("h1", "Supplementary figures")]
            for n in range(1, 7):
                blocks.append(("p", lead.format(n=n)))
                blocks.append(self._fig(png, caption, f"Figure S{n}"))
            plan = DB.plan_full_page_plates(blocks, "en", True)
            derraman = [v for v in plan.values() if v["layout"]["mode"] == "spill"]
            self.assertTrue(derraman, "el caso de prueba tiene que producir leyendas que no caben")
            self.assertTrue(all(v["split_caption"] for v in derraman),
                            "toda leyenda que no cabe se parte en el código y su cola va rotulada")
            out = Path(tmp) / "supp.docx"
            r = DB.build_document(blocks, "en", out)
            doc = Document(str(out))
            textos = [p.text for p in doc.paragraphs]
            for pl in r["full_page_plates"]:
                if pl["mode"] != "spill":
                    continue
                lab = pl["label"]
                self.assertTrue(pl["caption_split"], f"{lab}: la leyenda que no cabe tiene que partirse")
                cont = [t for t in textos if t.startswith(f"{lab} (continued).")]
                self.assertEqual(len(cont), 1, f"{lab}: la cola tiene que ir rotulada una vez")
                cabeza = [t for t in textos if t.startswith(f"{lab}.") and "(continued)" not in t][0]
                impresa = (cabeza[len(f"{lab}. "):] + " " + cont[0][len(f"{lab} (continued). "):]).split()
                self.assertEqual(impresa, caption.split(),
                                 f"{lab}: la leyenda entera, sin perder ni repetir una palabra")
                par = next(p for p in doc.paragraphs if p.text.startswith(f"{lab} (continued)."))
                ppr = par._p.find(qn("w:pPr"))
                saltos = par._p.findall(".//" + qn("w:br"))
                anterior = par._p.getprevious()
                previo_sect = (anterior is not None and anterior.tag == qn("w:p") and
                               anterior.find(qn("w:pPr")) is not None and
                               anterior.find(qn("w:pPr")).find(qn("w:sectPr")) is not None)
                self.assertTrue((ppr is not None and ppr.find(qn("w:pageBreakBefore")) is not None) or
                                any(b.get(qn("w:type")) == "page" for b in saltos) or previo_sect,
                                f"{lab}: la cola abre página, para que el rótulo no caiga a media página")

    def test_the_caption_is_never_cut_between_a_number_and_its_percent_sign(self):
        """El corte de la leyenda no cae en un espacio duro: el «%» no abre página separado de su cifra.

        `str.split()` parte también por U+00A0, que es justo el blanco que el corpus escribe entre la cifra
        y su signo (`pct_indivisible`). Mientras se partían cinco leyendas por documento el riesgo era
        pequeño; partiendo las 260 de los doce documentos, el corte acaba cayendo ahí."""
        import docx_builder as DB
        texto = DB.pct_indivisible("Panel (a) shows 12,5 % of episodes and panel (b) shows 3,1 % more "
                                   "of them in the same year.")
        self.assertIn("\u00a0", texto, "el caso de prueba tiene que llevar espacio duro")
        for n in range(1, 8):
            cabeza, cola = DB.split_caption_lines("Figure S1. ", texto, 7.0, n, ancho_cm=3.0)
            self.assertFalse(cola.lstrip().startswith("%"),
                             f"con {n} línea(s) el signo de porcentaje abre la cola sin su cifra")
            self.assertFalse(cabeza.rstrip().endswith("12,5") or cabeza.rstrip().endswith("3,1"),
                             f"con {n} línea(s) la cabeza termina en la cifra y deja el signo fuera")
            if cabeza and cola:
                self.assertEqual((cabeza + " " + cola).split(), texto.split(),
                                 "el corte no puede perder ni repetir una palabra")

    def test_the_caption_spill_audit_sees_a_tail_that_lost_its_label(self):
        """Control positivo de la guardia de J1: se le da el defecto exacto y tiene que denunciarlo.

        Una guardia que no se prueba contra el defecto que persigue puede estar muda y nadie lo nota: fue lo
        que pasó con las tres verificaciones que dieron estas colas por buenas. Se le dan las dos páginas tal
        como salieron impresas —la de la lámina, que termina a media leyenda, y la siguiente, que abre con el
        resto— y se exige que cuente uno; con el rótulo puesto, cero."""
        plates = [dict(label="Figure S41", caption_head="Comparison across administrative systems",
                       caption_end="pandemic reporting disruption.")]
        pagina = dict(text="Figure S41 places every system side by side.\nFigure S41. Comparison across "
                           "administrative systems: index, raw value and population rate, with their "
                           "denominators. UNITS DIFFER: episodes, discharges and students are not")
        sin_rotulo = [pagina, dict(text="interchangeable. Counts are administrative recognition, never "
                                        "prevalence or incidence. 2020-2021: pandemic reporting "
                                        "disruption.")]
        out = M.caption_spill_audit(sin_rotulo, plates, "en")
        self.assertEqual(out["spilled"], 1)
        self.assertEqual(out["unmarked_spills"], 1)
        self.assertEqual(out["unmarked_at"][0]["label"], "Figure S41")
        con_rotulo = [pagina, dict(text="Figure S41 (continued). interchangeable. Counts are administrative "
                                        "recognition, never prevalence or incidence. 2020-2021: pandemic "
                                        "reporting disruption.")]
        self.assertEqual(M.caption_spill_audit(con_rotulo, plates, "en")["unmarked_spills"], 0)
        self.assertEqual(M.caption_spill_audit(con_rotulo, plates, "en")["marked"], 1)
        # y la leyenda que TERMINA en la página de su lámina no cuenta como desbordamiento, aunque la cola
        # de la leyenda ANTERIOR —que acaba con las mismas palabras de norma— esté impresa encima de ella
        entera = [dict(text="Figure S40 (continued). ... 2020-2021: pandemic reporting disruption.\n"
                            "Figure S41 places every system side by side.\nFigure S41. Comparison across "
                            "administrative systems and their denominators. 2020-2021: pandemic reporting "
                            "disruption.")]
        self.assertEqual(M.caption_spill_audit(entera, plates, "en")["spilled"], 0)

    def test_the_caption_audit_reads_the_legend_under_the_plate(self):
        """La guardia de V9, leída del PDF: el rótulo solo bajo la lámina es una figura sin leyenda."""
        plates = [dict(label="Figura S54", caption_head="Resumen a escala regional: tasas, razones")]
        solo_rotulo = [dict(text="La Figura S54 resume el mismo análisis territorial.\nFigura S54."),
                       dict(text="Figura S54 (continuación). Resumen a escala regional: tasas, razones…")]
        out = M.caption_audit(solo_rotulo, plates)
        self.assertEqual(out["caption_off_plate_page"], 1)
        self.assertEqual(out["caption_off_at"][0]["label"], "Figura S54")
        con_leyenda = [dict(text="La Figura S54 resume el análisis.\nFigura S54. Resumen a escala "
                                 "regional: tasas, razones estandarizadas e intervalos.")]
        self.assertEqual(M.caption_audit(con_leyenda, plates)["caption_off_plate_page"], 0)
        self.assertEqual(M.caption_audit(con_leyenda, plates)["caption_not_found"], [])

    def test_the_heading_that_announces_a_wide_table_travels_with_it(self):
        """V12: el subtítulo no puede quedarse como última línea de la página vertical anterior.

        Cuando delante del rótulo de una tabla ancha está la COLA de la leyenda de una lámina, absorber
        toda la cabecera en la sección apaisada dejaba esa página con la cola y nada más. La regla que lo
        evitaba no absorbía NADA, y entonces el subtítulo que anuncia la tabla —«Sources and data
        workflow»— se imprimía solo al pie de la página vertical, con 18 cm en blanco detrás y la Tabla S1
        abriendo ya apaisada. Se absorbe lo justo: el subtítulo viaja con su tabla y el título de sección
        con su párrafo de entrada se quedan llenando la página de la cola."""
        from docx import Document
        from docx.oxml.ns import qn
        import pandas as pd
        import docx_builder as DB
        ancha = pd.DataFrame({f"Establecimiento_reportante_{j}": [
            f"IdEstablecimiento_columna_larguisima_{j}_{k}" for k in range(3)] for j in range(1, 9)})
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            blocks = [self._fig(png, "Panel (a) gives the annual series. " * 120, "Figure S54"),
                      ("h1", "Supplementary tables"),
                      ("p", "The tables below keep the sequential numbering of the shared registry and "
                            "carry the title and the note of their output file."),
                      ("h2", "Sources and data workflow"),
                      ("table", dict(df=ancha, title="Data sources, unit of observation and coverage",
                                     note="Note. Counts are administrative recognition.", label="Table S1"))]
            out = Path(tmp) / "supp.docx"
            DB.build_document(blocks, "en", out)
            post = M.postprocess_docx(out, "en")
            self.assertGreaterEqual(len(post["landscape_tables"]), 1, "la tabla de prueba tiene que rotarse")
            doc = Document(str(out))

            def texto(el):
                return "".join(t.text or "" for t in el.iter(qn("w:t"))).strip()

            def lleva_sect(el):
                ppr = el.find(qn("w:pPr")) if el is not None and el.tag == qn("w:p") else None
                return ppr is not None and ppr.find(qn("w:sectPr")) is not None

            cuerpo = list(doc.element.body)
            sub = next(el for el in cuerpo if el.tag == qn("w:p") and texto(el) == "Sources and data workflow")
            cont = next(el for el in cuerpo if el.tag == qn("w:p")
                        and texto(el).startswith("Figure S54 (continued)."))
            titulo = next(el for el in cuerpo if el.tag == qn("w:p") and texto(el) == "Supplementary tables")
            self.assertTrue(lleva_sect(sub.getprevious()),
                            "el corte a la sección apaisada va justo delante del subtítulo, que viaja con "
                            "su tabla y no se queda huérfano al pie de la página vertical")
            self.assertLess(cuerpo.index(cont), cuerpo.index(titulo))
            self.assertLess(cuerpo.index(titulo), cuerpo.index(sub.getprevious()),
                            "el título de sección y su párrafo de entrada se quedan con la cola, que así "
                            "no ocupa sola su página")

    def test_the_document_opens_one_section_per_run_of_plates(self):
        from docx import Document
        from docx.oxml.ns import qn
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            blocks = [("h1", "Supplementary figures")]
            for i in (1, 2, 3):
                blocks.append(("p", f"Figure S{i} shows the annual series."))
                blocks.append(self._fig(png, "Short caption.", f"Figure S{i}"))
            blocks.append(("p", "Closing paragraph."))
            out = Path(tmp) / "plates.docx"
            r = DB.build_document(blocks, "en", out)
            self.assertEqual(len(r["full_page_plates"]), 3)
            doc = Document(str(out))
            sects = doc.element.body.findall(".//" + qn("w:sectPr"))
            self.assertEqual(len(sects), 3)                     # apertura, cierre y el sectPr final
            anchos = {s.find(qn("w:pgMar")).get(qn("w:left")) for s in sects}
            self.assertIn(str(int(DB.PLATE_MARGIN_CM["left"] * 567)), anchos)

    def test_the_audit_sees_a_page_that_is_full_of_characters_and_empty_of_paper(self):
        """La medida que faltaba: ALTURA OCUPADA, no sólo caracteres.

        Once líneas de leyenda a 7 pt meten dos mil caracteres en 3 cm de papel y dejan 26 cm en blanco.
        El umbral de caracteres no la veía: era la razón de que 2–3 páginas por documento pasaran la
        auditoría estando al 12 % de ocupación."""
        cola = dict(height_cm=29.7, lines=11, chars=2026, top_cm=0.45, end_cm=3.47, gap_cm=26.23,
                    text="…multiplicity.", first="(c) Crude A05 rate per 100,000 person-years.", last="…")
        llena = dict(height_cm=29.7, lines=40, chars=4000, top_cm=2.5, end_cm=27.2, gap_cm=2.5,
                     text="x", first="x", last="x")
        fin = dict(height_cm=29.7, lines=6, chars=480, top_cm=2.5, end_cm=6.1, gap_cm=23.6,
                   text="y", first="Convergence across systems and sensitivity of the trends", last="y")
        stats = M._region_stats([llena, cola, fin, llena], 0, 3, 3)
        self.assertEqual(stats["near_empty_pages"], 0, "el umbral de caracteres no ve esta página")
        self.assertEqual(stats["sparse_pages"], 2, "la altura ocupada sí las ve")
        self.assertEqual(stats["tail_pages"], 1, "sólo una ABRE a media frase: la otra cierra su sección")
        self.assertEqual(stats["sparse_at"][0]["page"], 2)
        self.assertTrue(stats["sparse_at"][0]["tail"])
        self.assertFalse(stats["sparse_at"][1]["tail"])
        self.assertGreaterEqual(stats["max_gap_cm"], M.SPARSE_GAP_CM)
        # la última página del documento no cuenta: termina donde termina el texto
        self.assertEqual(M._region_stats([llena, cola], 0, 1, 1)["sparse_pages"], 0)
        # Y las dos medidas se cuentan POR SEPARADO. Una página de lámina con 231 caracteres —la entradilla
        # y el rótulo «Figura S54.», sin una sola línea de leyenda— no deja papel en blanco al pie, porque
        # los 245 mm de imagen lo ocupan: exigirle las dos cosas a la vez hacía invisible el único caso que
        # apareció impreso. El recuento de caracteres, solo, la ve; la altura ocupada, sola, no.
        lamina = dict(height_cm=29.7, lines=3, chars=231, top_cm=0.30, end_cm=25.94, gap_cm=3.76,
                      text="z", first="La Figura S54 resume el mismo análisis territorial", last="z")
        conteo = M._region_stats([llena, lamina, llena, llena], 0, 3, 3)
        self.assertEqual(conteo["near_empty_pages"], 1, "una lámina sin una línea de leyenda es texto vacío")
        self.assertEqual(conteo["near_empty_at"], [2])
        self.assertEqual(conteo["sparse_pages"], 0, "y no deja papel en blanco: la imagen lo ocupa")
        # una lámina con su leyenda entera debajo pasa de los dos mil caracteres y no es ninguna de las dos
        con_leyenda = dict(lamina, chars=2410, lines=14)
        self.assertEqual(M._region_stats([llena, con_leyenda, llena, llena], 0, 3, 3)["near_empty_pages"], 0)

    def test_the_lead_in_guard_reads_the_printed_page_and_not_the_model(self):
        """La guardia de la entradilla se lee del PDF: el modelo se equivocaba por defecto en 2–7 láminas."""
        pagina_ok = dict(text="Figure S8 distributes the A05 entries by age and sex.\nFigure S8. REM A05 entries…")
        pagina_previa = dict(text="Figure S9 gives the same for the June cut.")
        pagina_sola = dict(text="Figure S9. REM P2 stocks in June and December…")
        plates = [dict(label="Figure S8", lead_head="Figure S8 distributes the A05 entries"),
                  dict(label="Figure S9", lead_head="Figure S9 gives the same for")]
        out = M.lead_in_audit([pagina_ok, pagina_previa, pagina_sola], "en", plates)
        self.assertEqual(out["plates"], 2)
        self.assertEqual(out["lead_off_plate_page"], 1)
        self.assertEqual(out["lead_off_at"][0]["label"], "Figure S9")
        self.assertEqual(out["caption_not_found"], [])

    @unittest.skipUnless(CFG.CORPUS.joinpath("build_report.json").is_file(),
                         "no hay build_report.json: los documentos no se han construido en esta copia")
    def test_the_built_pdfs_keep_every_lead_in_on_the_page_of_its_plate(self):
        """La guardia de la entradilla, leída del PDF CONSTRUIDO y no del modelo.

        `plan_full_page_plates` es una estimación y Word es exacto: la versión anterior de esta guardia
        preguntaba al modelo (`lead_index`, `lead_keep`) y decía 3–5 entradillas fuera de su página donde
        el PDF impreso tenía 6–12. Ahora se lee lo impreso, que es lo que lee quien revisa."""
        import json
        rep = json.loads(CFG.CORPUS.joinpath("build_report.json").read_text(encoding="utf-8"))
        visto = 0
        for key, pair in rep.get("documents", {}).items():
            for part in ("manuscript", "supplement", "article"):
                lay = ((pair.get(part) or {}).get("review") or {}).get("layout") or {}
                li = lay.get("lead_in") or {}
                if not li.get("plates"):
                    continue
                visto += 1
                self.assertEqual(li["lead_off_plate_page"], 0,
                                 f"{key}/{part}: entradillas impresas fuera de la página de su lámina: "
                                 f"{li.get('lead_off_at')}")
                self.assertEqual(li.get("caption_not_found"), [],
                                 f"{key}/{part}: leyendas que la auditoría no encontró en el PDF")
                caps = lay.get("captions") or {}
                if caps.get("plates"):
                    self.assertEqual(caps["caption_off_plate_page"], 0,
                                     f"{key}/{part}: láminas impresas sin una línea de leyenda debajo "
                                     f"{caps.get('caption_off_at')}")
                    self.assertEqual(caps.get("caption_not_found"), [],
                                     f"{key}/{part}: rótulos de lámina que la auditoría no encontró")
                plates = (lay.get("regions") or {}).get("plates") or {}
                if plates:
                    self.assertEqual(plates["near_empty_pages"], 0,
                                     f"{key}/{part}: páginas casi vacías en la región de láminas "
                                     f"{plates.get('near_empty_at')}")
        self.assertGreaterEqual(visto, 1, "el informe no trae ninguna auditoría de entradillas")

    def test_drop_empty_sections_removes_the_blank_page(self):
        from docx import Document
        from docx.oxml.ns import qn
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            doc = DB.nuevo_doc()
            DB.parrafo(doc, "Texto.")
            DB._sectpr_paragraph(doc, DB.PLATE_MARGIN_CM)
            DB._sectpr_paragraph(doc, DB.BODY_MARGIN_CM)        # sección vacía entre ambos
            DB.parrafo(doc, "Más texto.")
            out = Path(tmp) / "s.docx"
            doc.save(str(out))
            doc = Document(str(out))
            self.assertEqual(M.drop_empty_sections(doc), 1)
            self.assertEqual(M.drop_empty_sections(doc), 0)

    def test_embed_copy_downsamples_the_copy_and_leaves_the_original_at_600_dpi(self):
        from PIL import Image
        import docx_builder as DB
        with tempfile.TemporaryDirectory() as tmp:
            png = self._png(tmp, 4251, 5787)
            antes = png.stat().st_size
            cache = Path(tmp) / "cache"
            copia = DB.embed_copy(png, 18.0, 300, cache)
            self.assertNotEqual(Path(copia), png)
            with Image.open(copia) as im:
                self.assertEqual(im.width, round(18.0 / 2.54 * 300))
            with Image.open(png) as im:
                self.assertEqual(im.size, (4251, 5787))
            self.assertEqual(png.stat().st_size, antes)
            self.assertEqual(Path(DB.embed_copy(png, 18.0, None, cache)), png)


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las láminas/tablas por variante")
class ArticleOnlyTest(unittest.TestCase):
    """El archivo sólo con el artículo termina en las Referencias y lo declara en su portada."""

    def test_article_blocks_end_at_the_references(self):
        P = M.prose_en
        art = P.article("con_rett", P.load_values("con_rett"))
        self.assertEqual(art[-1][0], "refs")
        self.assertEqual(sum(1 for k, _ in art if k == "refs"), 1)
        self.assertEqual(sum(1 for k, _ in art if k == "figure"), len(P.MAIN_FIGURES))
        self.assertEqual(sum(1 for k, _ in art if k == "table"), len(P.MAIN_TABLES))

    def test_the_title_page_says_where_the_supplementary_part_is(self):
        P = M.prose_en
        V = P.load_values("con_rett")
        art = P.article("con_rett", V)
        wc = P.word_counts(art)
        authors, affiliations = M.load_paper_authors()
        counts = dict(summary=wc["summary"], panel=wc["panel"], core=wc["core_body"], n_opt=wc["opt_paragraphs"],
                      opt=wc["opt_body"], decl=wc["declarations"], refs_core=1, refs_all=1, tables=wc["tables"],
                      figures=wc["figures"], sfig=len(P.SUPP_FIGURES), stab=len(P.SUPP_TABLES), neq=len(M.EQ.NUMBER))
        solo = M.title_page(list(art), "en", "con_rett", P, authors, affiliations, counts, article_only=True)
        combinado = M.title_page(list(art), "en", "con_rett", P, authors, affiliations, counts)
        lineas, combi = solo[2][1]["lines"], combinado[2][1]["lines"]
        self.assertEqual(len(lineas), len(combi))
        self.assertTrue(any("This file ends at the References" in ln for ln in lineas))
        # ni el índice de material opcional ni la parte suplementaria están en este archivo: no se anuncian
        self.assertFalse(any("Optional material index" in ln for ln in lineas))
        self.assertFalse(any("in this same file" in ln for ln in lineas))
        self.assertTrue(any("Optional material index" in ln for ln in combi))
        self.assertTrue(any("in this same file" in ln for ln in combi))


@unittest.skipUnless(HAS_OUTPUTS, "requiere outputs/values_*.json y las láminas/tablas por variante")
class BuildTest(unittest.TestCase):
    def test_docx_build_and_postprocess(self):
        """Construye un manuscrito sin láminas pesadas (título, resumen y las 8 tablas) y verifica el posproceso."""
        from docx import Document
        from docx.oxml.ns import qn
        from docx_builder import build_document
        P = M.prose_en
        V = P.load_values("con_rett")
        art = P.article("con_rett", V)
        wc = P.word_counts(art)
        stripped, index = M.strip_opt_with_index(art, "en")
        self.assertEqual(len(index), wc["opt_paragraphs"])
        self.assertEqual(sum(e["words"] for e in index), wc["opt_body"])
        authors, affiliations = M.load_paper_authors()
        counts = dict(summary=wc["summary"], panel=wc["panel"], core=wc["core_body"], n_opt=wc["opt_paragraphs"],
                      opt=wc["opt_body"], decl=wc["declarations"], refs_core=1, refs_all=1, tables=wc["tables"],
                      figures=wc["figures"], sfig=len(P.SUPP_FIGURES), stab=len(P.SUPP_TABLES),
                      neq=len(M.EQ.NUMBER))
        stripped = M.title_page(stripped, "en", "con_rett", P, authors, affiliations, counts)
        self.assertEqual(stripped[2][0], "authors")
        self.assertTrue(any("Word counts" in line for line in stripped[2][1]["lines"]))
        light = [(k, p) for k, p in stripped if k != "figure"] + M.optional_index_blocks(index, "en", wc["core_body"])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "m.docx"
            with M.localised_references("en"):
                r = build_document(light, "en", out, bib_path=P.BIB)
            self.assertEqual(r["tables"], 7)
            post = M.postprocess_docx(out, "en")
            self.assertGreaterEqual(len(post["landscape_tables"]), 1)
            doc = Document(str(out))
            texts = [p.text for p in doc.paragraphs]
            self.assertIn("Optional material index", texts)
            self.assertFalse(any(t.startswith(M.OPT) for t in texts))
            self.assertFalse(any("Disponible en:" in t for t in texts))
            sects = doc.element.body.findall(".//" + qn("w:sectPr"))
            self.assertGreater(len(sects), 1)
            self.assertTrue(any(s.find(qn("w:pgSz")) is not None and s.find(qn("w:pgSz")).get(qn("w:orient")) == "landscape"
                                for s in sects))
            # EL FOLIO, EN TODAS LAS SECCIONES. Word hereda el pie sólo hacia ADELANTE: una sección sin
            # `w:footerReference` propia toma el de la anterior, nunca el de la siguiente. Mientras el pie
            # se escribía en `sections[0]` ANTES de que `landscape_wide_tables` partiera el documento, cada
            # sección nueva se intercalaba por delante y dejaba sin folio todo lo anterior —171 páginas de
            # los cuatro apéndices sueltos, de la portada a la Tabla S12 apaisada—. Comprobar sólo la
            # sección 0 no veía nada: la sección 0 era justamente la única numerada.
            self.assertGreater(len(doc.sections), 1)
            for i, section in enumerate(doc.sections):
                with self.subTest(section=i):
                    self.assertTrue(section.footer.paragraphs[0]._p.findall(qn("w:fldSimple")),
                                    f"la sección {i} de {len(doc.sections)} se imprime sin folio")
            self.assertEqual(post["sections_numbered"], len(doc.sections))

    @staticmethod
    def _split_sections_in_front(doc, idxs):
        """Abre secciones nuevas POR DELANTE, como hace `landscape_wide_tables` con cada tabla ancha."""
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        body = doc.element.body
        for i in idxs:
            par = body.findall(qn("w:p"))[i]
            ppr = par.find(qn("w:pPr"))
            if ppr is None:
                ppr = OxmlElement("w:pPr")
                par.insert(0, ppr)
            ppr.append(OxmlElement("w:sectPr"))

    def test_folio_survives_sections_opened_after_it(self):
        """Reproduce el apéndice suelto: UNA sección, el pie escrito, y luego el corte en tablas anchas.

        Escrito ANTES del corte, el pie se quedaba en la ÚNICA sección que había, que tras el corte pasa a
        ser la ÚLTIMA: como Word hereda el pie sólo hacia adelante, todo lo anterior salía sin folio —eran
        171 páginas en los cuatro apéndices sueltos, de la portada a la Tabla S12—. La comprobación mide lo
        que Word ve: se guarda el documento, se vuelve a abrir y se cuenta el `w:footerReference` de cada
        sección, no el objeto que python-docx resuelve por herencia.
        """
        import io
        from docx import Document as Doc
        from docx.oxml.ns import qn

        def folios(document):
            buf = io.BytesIO()
            document.save(buf)
            buf.seek(0)
            reread = Doc(buf)
            return [bool(sec.footer.paragraphs[0]._p.findall(qn("w:fldSimple"))) for sec in reread.sections]

        # ORDEN ANTIGUO —numerar y DESPUÉS cortar—: así se veía el defecto.
        antiguo = Doc()
        for i in range(6):
            antiguo.add_paragraph(f"parrafo {i}")
        M.add_page_numbers(antiguo)
        self._split_sections_in_front(antiguo, (1, 2, 3))
        self.assertFalse(all(folios(antiguo)), "el orden antiguo debería dejar secciones sin folio")

        # ORDEN NUEVO —cortar y numerar al final, que es lo que hace `postprocess_docx`—.
        nuevo = Doc()
        for i in range(6):
            nuevo.add_paragraph(f"parrafo {i}")
        self._split_sections_in_front(nuevo, (1, 2, 3))
        self.assertEqual(len(nuevo.sections), 4)
        self.assertEqual(M.add_page_numbers(nuevo), 4)
        self.assertTrue(all(folios(nuevo)), "toda sección tiene que imprimir su folio")
        # Idempotente: una segunda pasada no añade un segundo campo PAGE a ninguna sección.
        self.assertEqual(M.add_page_numbers(nuevo), 4)
        for i, section in enumerate(nuevo.sections):
            with self.subTest(section=i):
                self.assertEqual(len(section.footer.paragraphs[0]._p.findall(qn("w:fldSimple"))), 1)

    def test_postprocess_numbers_pages_after_it_has_cut_the_sections(self):
        """La guarda del ORDEN: el folio es la última operación del posproceso.

        Es la causa raíz y no se ve en el resultado de un documento que ya abría secciones propias antes de
        su primera tabla ancha (los cuatro manuscritos, que nunca perdieron el folio). Se vigila el orden.
        """
        from docx import Document
        llamadas = []
        originales = {k: getattr(M, k) for k in ("add_page_numbers", "landscape_wide_tables", "drop_empty_sections")}

        def espia(nombre):
            def envuelto(*a, **k):
                llamadas.append(nombre)
                return originales[nombre](*a, **k)
            return envuelto

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "m.docx"
            doc = Document()
            doc.add_paragraph("texto")
            doc.save(str(out))
            try:
                for nombre in originales:
                    setattr(M, nombre, espia(nombre))
                M.postprocess_docx(out, "en")
            finally:
                for nombre, fn in originales.items():
                    setattr(M, nombre, fn)
        self.assertEqual(llamadas[-1], "add_page_numbers",
                         f"el folio tiene que escribirse al final; orden observado: {llamadas}")
        self.assertLess(llamadas.index("landscape_wide_tables"), llamadas.index("add_page_numbers"))
        self.assertLess(llamadas.index("drop_empty_sections"), llamadas.index("add_page_numbers"))


if __name__ == "__main__":
    unittest.main()
