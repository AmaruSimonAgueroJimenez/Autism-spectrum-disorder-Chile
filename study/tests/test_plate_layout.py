# -*- coding: utf-8 -*-
"""Pruebas del verificador de composición de láminas (`common.check_layout`).

Treinta y tres de las cincuenta y nueve láminas llegaron a los verificadores humanos con un rótulo impreso
sobre otro. Leer cada página a tamaño de impresión no escala y el defecto vuelve en cuanto cambia un dato:
la comprobación tiene que vivir en el código que dibuja. Aquí se prueba, con láminas sintéticas construidas
a la norma (180 × 245 mm, 3 × 2, cuerpo base 8 pt, mínimo 6 pt, letras minúsculas), que:

  1. cada una de las nueve familias de defecto se DENUNCIA cuando existe;
  2. ninguna se denuncia cuando la lámina está limpia —incluidos los casos que antes daban falso positivo:
     ejes gemelos, barras de color, encartes, rótulos escritos dentro de su propia figura y el roce de un
     punto tipográfico que produce el aire de la fuente—;
  3. las ayudas de colocación (`plate_ylabel`, `plate_place_legend`, `plate_value_label`,
     `plate_thin_category_ticks`) convierten un defecto denunciado en una lámina limpia;
  4. la puerta automática (`PLATE_CHECK`) hace fallar el módulo que produzca una lámina mala, y
     todos los módulos que dibujan láminas pasan por ella.

Con PLATE_REAL=1 se añade la comprobación sobre una lámina REAL reconstruida por su módulo.
"""
from pathlib import Path
import os
import sys
import tempfile
import unittest

import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import common as C  # noqa: E402

MM = 1.0 / 25.4
PLATE_SIZE = (180 * MM, 245 * MM)          # la norma: 180 × 245 mm en vertical
FS_TITLE, FS_BASE, FS_TICK = 9.0, 8.0, 7.0


def kinds(problems) -> set:
    return {p.kind for p in problems}


def new_plate(n_panels: int = 6, rows: int = 3, cols: int = 2):
    """Lámina a la norma: 180 × 245 mm, rejilla 3 × 2, títulos «(a) Título» en minúscula."""
    fig = plt.figure(figsize=PLATE_SIZE, constrained_layout=True)
    gs = fig.add_gridspec(rows, cols)
    axes = [fig.add_subplot(gs[i // cols, i % cols]) for i in range(n_panels)]
    for i, ax in enumerate(axes):
        ax.set_title(f"{chr(97 + i)}  Panel {i + 1}", loc="left", fontsize=FS_TITLE, fontweight="bold")
        ax.tick_params(labelsize=FS_TICK)
    return fig, axes


def twin_with_title_over_its_ticks(ax):
    """Reproduce el defecto de doce paneles: el rótulo del eje derecho clavado sobre su columna de marcas.

    Se mide la columna de marcas ya dibujada y se ancla ahí el rótulo, que es lo que acaba ocurriendo cuando
    la guarda de recorte empuja el rótulo hacia dentro para que no se salga de la celda."""
    tw = ax.twinx()
    tw.plot(np.arange(2019, 2026), np.linspace(6, 19, 7), color="#D55E00")
    tw.tick_params(labelsize=FS_TICK)
    tw.set_ylabel("Unweighted autism cases (thousands)", fontsize=FS_BASE)
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    boxes = [t.get_window_extent(r) for t in C._pl_tick_texts(tw.yaxis)]
    x_disp = float(np.mean([0.5 * (b.x0 + b.x1) for b in boxes]))
    x_axes = float(tw.transAxes.inverted().transform([[x_disp, 0.0]])[0][0])
    tw.yaxis.set_label_coords(x_axes, 0.5)
    return tw


def clean_series(ax, n: int = 7):
    years = np.arange(2019, 2019 + n)
    ax.plot(years, np.linspace(10, 40, n), marker="o", markersize=3)
    ax.set_xlabel("Year", fontsize=FS_BASE)
    ax.set_ylabel("Episodes per 100 000", fontsize=FS_BASE)
    return years


class CheckerReportsEachFamilyTest(unittest.TestCase):
    """Cada familia del informe de verificación se denuncia cuando el defecto existe."""

    def tearDown(self):
        plt.close("all")

    def test_a_clean_plate_reports_nothing(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        self.assertEqual(C.check_layout(fig), [])

    def test_text_over_text(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        # dos rótulos de valor escritos en el mismo sitio: el segundo tapa al primero
        axes[0].text(0.5, 0.5, "n=1.854", transform=axes[0].transAxes, fontsize=FS_BASE)
        axes[0].text(0.5, 0.5, "n=2.011", transform=axes[0].transAxes, fontsize=FS_BASE)
        probs = [p for p in C.check_layout(fig) if p.kind == C.TEXT_OVER_TEXT]
        self.assertTrue(probs, "un rótulo impreso sobre otro tiene que denunciarse")
        self.assertIn("panel (a)", probs[0].axes)
        self.assertTrue(any("n=1.854" in a for a in probs[0].artists))
        self.assertGreater(probs[0].overlap_pt, 1.0)

    def test_text_outside_the_canvas(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        # un título español que no cabe: se sale por el borde derecho del lienzo
        axes[1].set_title("b  " + "Cobertura de la población bajo control en diciembre por región " * 2,
                          loc="left", fontsize=FS_TITLE, fontweight="bold")
        probs = [p for p in C.check_layout(fig) if p.kind == C.TEXT_OUTSIDE_CANVAS]
        self.assertTrue(probs)
        self.assertGreater(probs[0].overlap_pt, 5.0)
        self.assertIn("clipped", probs[0].detail)

    def test_axis_title_over_tick_labels(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[2]
        twin_with_title_over_its_ticks(ax)
        probs = [p for p in C.check_layout(fig) if p.kind == C.AXIS_TITLE_OVER_TICKS]
        self.assertTrue(probs, "el rótulo del eje derecho sobre sus propias marcas tiene que denunciarse")
        self.assertIn("twin", probs[0].axes)
        self.assertTrue(any("y-axis title" in a for a in probs[0].artists))

    def test_legend_over_data(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[3]
        ax.legend(ax.lines, ["GRD episodes"], loc="center", fontsize=FS_TICK)
        probs = [p for p in C.check_layout(fig) if p.kind == C.LEGEND_OVER_DATA]
        self.assertTrue(probs)
        self.assertTrue(any("legend" in a for a in probs[0].artists))
        self.assertIsNotNone(probs[0].fraction)
        self.assertGreater(probs[0].fraction, 0.03)

    def test_boxed_note_over_data(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[4]
        ax.text(0.5, 0.5, "Note: episodes without a recorded weight are counted in the denominator",
                transform=ax.transAxes, ha="center", va="center", fontsize=6.2,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.92))
        probs = [p for p in C.check_layout(fig) if p.kind == C.LEGEND_OVER_DATA]
        self.assertTrue(probs, "una nota con recuadro encima de la serie tiene que denunciarse")
        self.assertTrue(any("boxed note" in a for a in probs[0].artists))

    def test_value_label_over_its_own_marker(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[5]
        ax.text(2021, ax.lines[0].get_ydata()[2], "23,4", fontsize=6.2, ha="center", va="center")
        probs = [p for p in C.check_layout(fig) if p.kind == C.VALUE_LABEL_OVER_DATUM]
        self.assertTrue(probs)
        self.assertIn("its own marker", probs[0].artists[1])

    def test_value_label_half_over_its_own_marker(self):
        """El rótulo DESPLAZADO medio marcador: el centro queda fuera de la caja y el disco, tapado.

        Era el punto ciego de la S12 (f): tanto el colocador como el verificador preguntaban si el CENTRO
        del marcador caía dentro de la caja del rótulo. Un marcador es un disco, así que un rótulo podía
        tapar media chincheta sin coste alguno y sin que la medida dijera nada, mientras el ojo veía un
        punto negro del que sólo asomaba una astilla."""
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[3]
        ax.plot([2021], [25.0], marker="o", markersize=9, color="#111111", linestyle="none")
        fig.canvas.draw()
        r = C._pl_renderer(fig)
        # el rótulo se escribe desplazado medio marcador: su caja NO contiene el centro del disco
        rad_px = 0.5 * 9.0 * fig.dpi / 72.0
        x0, y0 = ax.transData.transform([[2021, 25.0]])[0]
        txt = ax.text(2021, 25.0, "25,0", fontsize=6.2, ha="left", va="center")
        txt.set_position(ax.transData.inverted().transform(
            [[x0 + 0.62 * rad_px, y0]])[0])
        fig.canvas.draw()
        r = C._pl_renderer(fig)
        b = C._pl_extent(txt, r)
        self.assertGreater(b.x0, x0, "el caso de prueba exige que el centro del marcador quede FUERA "
                                     "de la caja del rótulo")
        probs = [p for p in C.check_layout(fig) if p.kind == C.VALUE_LABEL_OVER_DATUM]
        self.assertTrue(probs, "un rótulo que tapa medio marcador tiene que denunciarse")
        self.assertIn("its own marker", probs[0].artists[1])

    def test_marker_radius_travels_with_the_marker(self):
        """La matriz de marcadores lleva el RADIO en su tercera columna, en píxeles."""
        fig, axes = new_plate()
        ax = axes[0]
        ax.plot([2019, 2020], [1.0, 2.0], marker="o", markersize=8, linestyle="none")
        ax.scatter([2019.5], [1.5], s=64.0)
        fig.canvas.draw()
        marks, _bars = C._pl_markers_and_bars([ax], C._pl_renderer(fig))
        self.assertEqual(marks.shape[1], 3)
        rad = C._pl_marker_radii(marks)
        px = fig.dpi / 72.0
        self.assertAlmostEqual(float(np.max(rad)), 4.0 * px, places=6)   # markersize 8 → radio 4 pt
        self.assertAlmostEqual(float(np.min(rad)), 4.0 * px, places=6)   # s = 64 pt² → radio 4 pt

    def test_value_label_over_its_error_bar(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[0]
        ax.errorbar([2020.5], [25.0], yerr=[[6.0], [6.0]], fmt="none", ecolor="#333333")
        ax.text(2020.5, 25.0, "25,0", fontsize=6.2, ha="center", va="center")
        probs = [p for p in C.check_layout(fig) if p.kind == C.VALUE_LABEL_OVER_DATUM]
        self.assertTrue(probs)

    def test_value_label_masking_its_own_bar(self):
        """Defecto VL3-1: el recuadro del rótulo borra media barra y la mayor se lee más corta que la segunda."""
        fig, axes = new_plate()
        ax = axes[0]
        # la geometría de la S37 (e): diez áreas funcionales, rótulo de dos líneas a 6,2 pt, que mide más
        # que el grosor de la barra y por tanto la cruza de lado a lado
        vals = [100.0, 60.0, 48.0, 34.0, 33.0, 30.0, 17.0, 17.0, 12.0, 9.0]
        ax.barh(range(len(vals)), vals, height=0.7)
        ax.set_xlim(0, 162)
        ax.set_yticklabels([])
        # el rótulo de la barra más larga, devuelto sobre su propia barra por la pasada de colisiones, con
        # el recuadro blanco translúcido que `_pl_backing` le pinta detrás
        ax.text(52.0, 0, "2.236 miles de días-cama\n265.452 egresos", fontsize=6.2, va="center", ha="left",
                linespacing=1.25, bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9))
        probs = [p for p in C.check_layout(fig) if p.kind == C.BAR_MASKED_BY_LABEL]
        self.assertTrue(probs, "un recuadro que tapa media barra tiene que denunciarse")
        self.assertIn("panel (a)", probs[0].axes)
        self.assertGreater(probs[0].fraction, 0.3)
        self.assertIn("hidden by the box", probs[0].detail)

    def test_neighbouring_panel_titles_without_a_gutter(self):
        """Defecto VL3-2: dos títulos que no se solapan pero se leen como una sola frase."""
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        axes[0].set_title("(a) GRD F84 episodes 2019-2024 — Smoothed ratio", loc="left",
                          fontsize=FS_TITLE, fontweight="bold")
        fig.canvas.draw()
        r = fig.canvas.get_renderer()
        end = axes[0]._left_title.get_window_extent(r).x1
        pos = axes[1].get_position()
        want = (end + 1.4 * fig.dpi / 72.0) / fig.bbox.width      # 1,4 pt después del título de (a)
        axes[1].set_title("(b) GRD persons/year 2019-2024", loc="left", fontsize=FS_TITLE,
                          fontweight="bold", x=(want - pos.x0) / pos.width)
        probs = [p for p in C.check_layout(fig) if p.kind == C.TITLES_WITHOUT_GUTTER]
        self.assertTrue(probs, "dos títulos vecinos a 1,4 pt tienen que denunciarse")
        self.assertTrue(any("GRD F84 episodes" in a for a in probs[0].artists))
        self.assertTrue(any("GRD persons/year" in a for a in probs[0].artists))
        self.assertIn("between the two titles", probs[0].detail)

    def test_repeated_tick_labels(self):
        """Marcas NUMÉRICAS repetidas: «1 2 2 2 3 4 4 4 5» en el eje x.

        Lo produce un formateador que congela sus decimales antes de que el reparto se asiente
        (`_localise_ticks` corría antes de `plate_fit` y de los dos `draw()`): el localizador vuelve a
        marcar de 0,5 en 0,5, el formateador sigue escribiendo con cero decimales y ninguna posición del
        eje se puede leer. Ninguna otra familia lo ve: las cajas no se tocan y nada sale del lienzo."""
        from matplotlib.ticker import FuncFormatter, MultipleLocator
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[1]
        ax.set_xlim(1.0, 5.0)
        ax.xaxis.set_major_locator(MultipleLocator(0.5))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: str(int(round(v)))))
        probs = [p for p in C.check_layout(fig) if p.kind == C.REPEATED_TICK_LABELS]
        self.assertTrue(probs, "un eje que imprime dos veces el mismo número tiene que denunciarse")
        self.assertTrue(any("x axis" in a for p in probs for a in p.artists))

    def test_mirrored_axis_labels_are_not_a_defect(self):
        """La pirámide de población rotula −500 y 500 como «500»: son los DOS EXTREMOS, no dos vecinas."""
        from matplotlib.ticker import FuncFormatter, MultipleLocator
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[4]
        ax.clear()
        ax.barh([0, 1, 2], [-400, -300, -200])
        ax.barh([0, 1, 2], [350, 280, 190])
        ax.set_xlim(-500, 500)
        ax.xaxis.set_major_locator(MultipleLocator(250))
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _p: str(int(abs(v)))))
        fig.canvas.draw()
        drawn = [t.get_text() for t in ax.xaxis.get_majorticklabels()]
        self.assertEqual(drawn.count("500"), 2, "el caso de prueba necesita el rótulo espejado")
        probs = [p for p in C.check_layout(fig) if p.kind == C.REPEATED_TICK_LABELS]
        self.assertEqual(probs, [])

    def test_repeated_category_ticks_are_not_a_defect(self):
        """En un eje CATEGÓRICO dos rótulos iguales pueden ser dos categorías legítimas: no se denuncian."""
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[2]
        ax.clear()
        ax.bar([0, 1, 2, 3], [3, 5, 2, 4])
        ax.set_xticks([0, 1, 2, 3])
        ax.set_xticklabels(["Maule", "Ñuble", "Maule", "Biobío"], fontsize=FS_TICK)
        probs = [p for p in C.check_layout(fig) if p.kind == C.REPEATED_TICK_LABELS]
        self.assertEqual(probs, [])

    def test_panel_count_wrong_grid(self):
        fig, axes = new_plate(n_panels=4, rows=2, cols=2)
        for ax in axes:
            clean_series(ax)
        probs = [p for p in C.check_layout(fig) if p.kind == C.PANEL_COUNT]
        self.assertTrue(probs)
        self.assertIn("2×2", probs[0].artists[0])

    def test_panel_count_too_many_panels(self):
        fig = plt.figure(figsize=PLATE_SIZE, constrained_layout=True)
        gs = fig.add_gridspec(3, 2)
        for i in range(6):
            sub = gs[i // 2, i % 2].subgridspec(2, 1) if i == 0 else None
            if sub is None:
                fig.add_subplot(gs[i // 2, i % 2])
            else:
                fig.add_subplot(sub[0]); fig.add_subplot(sub[1])
        probs = [p for p in C.check_layout(fig) if p.kind == C.PANEL_COUNT]
        # siete subceldas dentro de la rejilla 3 × 2: la rejilla es correcta y las celdas siguen siendo seis
        self.assertEqual(probs, [])

    def test_panel_count_accepts_full_width_rows_and_diagram_plates(self):
        fig = plt.figure(figsize=PLATE_SIZE, constrained_layout=True)
        gs = fig.add_gridspec(3, 2)
        for row in range(3):
            ax = fig.add_subplot(gs[row, :])
            clean_series(ax)
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.PANEL_COUNT], [])
        diagram = plt.figure(figsize=PLATE_SIZE)
        ax = diagram.add_axes([0.0, 0.0, 1.0, 1.0])
        ax.set_axis_off()
        ax.text(0.1, 0.5, "GRD 2019–2025", fontsize=FS_BASE)
        self.assertEqual([p for p in C.check_layout(diagram) if p.kind == C.PANEL_COUNT], [])

    def test_problem_records_axes_artists_and_overlap(self):
        fig, axes = new_plate()
        clean_series(axes[0])
        axes[0].text(0.5, 0.5, "AAAA", transform=axes[0].transAxes, fontsize=FS_BASE)
        axes[0].text(0.5, 0.5, "BBBB", transform=axes[0].transAxes, fontsize=FS_BASE)
        p = [q for q in C.check_layout(fig) if q.kind == C.TEXT_OVER_TEXT][0]
        self.assertEqual(p.as_dict()["kind"], C.TEXT_OVER_TEXT)
        self.assertEqual(len(p.artists), 2)
        self.assertEqual(len(p.objects), 2)
        self.assertIn("pt", str(p))


class CheckerStaysSilentOnLegitimateLayoutsTest(unittest.TestCase):
    """Lo que la norma permite no se denuncia: si el verificador cría ruido, nadie lo usa."""

    def tearDown(self):
        plt.close("all")

    def test_twin_colourbar_and_inset_plate_is_clean(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        tw = axes[0].twinx()                       # el eje X del gemelo está apagado: no duplica marcas
        tw.plot(np.arange(2019, 2026), np.linspace(1, 9, 7), color="#D55E00")
        tw.tick_params(labelsize=FS_TICK)
        tw.set_ylabel("%", fontsize=FS_BASE)
        im = axes[3].imshow(np.random.default_rng(3).random((4, 4)))
        cb = fig.colorbar(im, ax=axes[3])
        cb.ax.tick_params(labelsize=6.0)
        ins = axes[4].inset_axes([0.62, 0.62, 0.34, 0.34])
        ins.plot([1, 2, 3], [1, 2, 3])
        ins.tick_params(labelsize=6.0)
        problems = C.check_layout(fig)
        self.assertEqual(problems, [], f"falsos positivos: {problems}")

    def test_label_written_inside_its_own_shape_is_not_a_defect(self):
        """El nombre de una región dentro de su polígono, o el valor dentro de su barra, está donde debe."""
        fig, axes = new_plate()
        ax = axes[0]
        ax.bar([1, 2, 3], [10, 20, 30])
        for x, y in ((1, 10), (2, 20), (3, 30)):
            ax.text(x, y / 2, f"{y}", ha="center", va="center", fontsize=6.2, color="white",
                    bbox=dict(facecolor="none", edgecolor="none"))
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.LEGEND_OVER_DATA], [])

    def test_a_label_beyond_the_tip_of_its_bar_is_not_a_defect(self):
        """La corrección de VL3-1: una columna de rótulos a la derecha de la barra más larga no tapa nada."""
        fig, axes = new_plate()
        ax = axes[0]
        vals = [100.0, 60.0, 48.0, 34.0, 33.0, 30.0, 17.0, 17.0, 12.0, 9.0]
        ax.barh(range(len(vals)), vals, height=0.7)
        ax.set_xlim(0, 175)
        ax.set_yticklabels([])
        for y, v in enumerate(vals):
            ax.text(103.0, y, f"{v:.0f} miles de días-cama\n{v * 100:.0f} egresos", fontsize=6.2,
                    va="center", ha="left", linespacing=1.25,
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9))
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.BAR_MASKED_BY_LABEL], [])

    def test_a_rotated_label_that_only_bites_the_edge_of_its_bar_is_not_a_defect(self):
        """La Figura 4 (c): el rótulo va girado 90° al costado de la barra y su recuadro le muerde el canto.

        Medido en el PNG a 600 ppp, entre el 1 % y el 10 % de la tinta de cada barra queda pálida y NI UNA
        fila de la barra está tapada de lado a lado: la silueta sigue entera y ninguna barra se lee más
        corta. Denunciarlo era el falso positivo que la primera versión de la familia producía."""
        fig, axes = new_plate()
        ax = axes[0]
        ax.bar([0, 1, 2], [2380.0, 3874.0, 3026.0], width=0.22)
        ax.set_ylim(0, 33000)
        for x, v in ((0, 2380.0), (1, 3874.0), (2, 3026.0)):
            ax.text(x - 0.135, v * 1.02, f"{v:,.0f} · n=150", rotation=90, fontsize=6.2, ha="center",
                    va="bottom", bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9))
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.BAR_MASKED_BY_LABEL], [])

    def test_a_loss_of_less_than_a_millimetre_and_a_half_is_not_a_defect(self):
        """La Figura S44 (a): el recuadro del rótulo «−9» muerde 2,3 pt de la punta de una barra corta.

        Es lo que hace el rescate de contraste de `_pl_backing` en la punta de casi toda barra rotulada.
        La familia denuncia que una barra se lea MÁS CORTA de lo que vale, y una merma de menos de
        milímetro y medio no se mide a ojo en la página."""
        fig, axes = new_plate()
        ax = axes[0]
        vals = [2300.0, 1550.0, 2320.0, 3870.0, 6460.0, 8700.0, 150.0, 110.0, 90.0, 250.0, 260.0, 290.0]
        ax.bar(range(len(vals)), vals, width=0.38)
        ax.set_ylim(0, 10500)
        for i, v in enumerate(vals):
            ax.text(i, v * 1.01, f"−{i + 3}", fontsize=6.4, ha="center", va="bottom",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9))
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.BAR_MASKED_BY_LABEL], [])

    def test_a_bar_shorter_than_the_type_has_no_length_to_lose(self):
        """La Figura S15 (c): el segmento rojo del apilado mide 1,7 pt y el recuadro del total cubre 1,38.

        Es el 81 % de una barra que no llega a los dos puntos tipográficos: no hay longitud legible que
        acortar, y medido sobre el PNG el segmento se imprime en color puro. La familia denuncia que una
        barra se lea MÁS CORTA de lo que vale, no que una astilla quede debajo de un rótulo."""
        fig, axes = new_plate()
        ax = axes[0]
        y = list(range(9))
        ax.barh(y, [86, 79, 200, 81, 65, 24, 88, 57, 4], height=0.7, color="#009E73")
        ax.barh(y, [0, 7, 2, 0, 1, 0, 0, 0, 1], left=[86, 79, 200, 81, 65, 24, 88, 57, 4],
                height=0.7, color="#8b0000")
        ax.set_xlim(0, 228)
        ax.set_yticklabels([])
        for i, total in enumerate((86, 86, 202, 202, 66, 24, 88, 57, 12)):
            ax.text(total + 2.0, i, f"{total}", fontsize=6.4, va="center", ha="left",
                    bbox=dict(facecolor="white", edgecolor="none", alpha=0.78, pad=0.9))
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.BAR_MASKED_BY_LABEL], [])

    def test_a_boxed_label_on_a_heat_map_cell_is_not_a_bar(self):
        """Los recuadros de contraste de las matrices no son barras: cada celda tiene origen propio."""
        from matplotlib.patches import Rectangle
        fig, axes = new_plate()
        ax = axes[0]
        for i in range(4):
            for j in range(3):
                ax.add_patch(Rectangle((i, j), 1, 1, facecolor="#9ecae1", edgecolor="white"))
        ax.set_xlim(0, 4); ax.set_ylim(0, 3)
        ax.text(0.5, 0.5, "12,4", fontsize=6.2, ha="center", va="center",
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.85, pad=0.6))
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.BAR_MASKED_BY_LABEL], [])

    def test_a_one_point_typographic_touch_is_not_reported(self):
        """El aire de la fuente hace que dos cajas se rocen sin que los trazos se toquen."""
        fig, axes = new_plate()
        ax = axes[0]
        clean_series(ax)
        b = ax.transAxes.transform([[0.5, 0.5]])[0]
        t1 = ax.text(0.5, 0.5, "abc", transform=ax.transAxes, fontsize=FS_BASE, va="bottom", ha="left")
        fig.canvas.draw()
        h = t1.get_window_extent(fig.canvas.get_renderer()).height
        # el segundo, justo encima, rozando un punto tipográfico
        y2 = (b[1] + h - 1.0 * fig.dpi / 72.0)
        ax.text(*ax.transAxes.inverted().transform([[b[0], y2]])[0], "def", transform=ax.transAxes,
                fontsize=FS_BASE, va="bottom", ha="left")
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.TEXT_OVER_TEXT], [])

    def test_axes_with_the_axis_switched_off_report_no_tick_labels(self):
        """Un mapa (`set_axis_off`) no imprime marcas: contarlas denunciaba veinte recortes inexistentes."""
        fig, axes = new_plate()
        ax = axes[0]
        ax.plot([0, 2_000_000], [0, 2_000_000])
        ax.set_axis_off()
        problems = C.check_layout(fig)
        self.assertEqual([p for p in problems if p.kind == C.TEXT_OUTSIDE_CANVAS], [])
        self.assertFalse([p for p in problems if "tick label" in " ".join(p.artists)])

    def test_legend_outside_the_axes_over_nothing_is_clean(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[0]
        lg = ax.legend(ax.lines, ["GRD"], loc="upper left", fontsize=FS_TICK)
        lg.set_in_layout(False)
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.LEGEND_OVER_DATA], [])


class AssertLayoutCleanTest(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    def test_raises_with_the_whole_list(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        axes[0].text(0.5, 0.5, "uno", transform=axes[0].transAxes, fontsize=FS_BASE)
        axes[0].text(0.5, 0.5, "dos", transform=axes[0].transAxes, fontsize=FS_BASE)
        axes[1].legend(axes[1].lines, ["serie"], loc="center", fontsize=FS_TICK)
        with self.assertRaises(C.PlateLayoutError) as cm:
            C.assert_layout_clean(fig, "figS99_prueba.png")
        msg = str(cm.exception)
        self.assertIn("figS99_prueba.png", msg)
        self.assertGreaterEqual(len(cm.exception.problems), 2)
        self.assertEqual(msg.count("\n"), len(cm.exception.problems))   # una línea por defecto
        self.assertIn(C.TEXT_OVER_TEXT, msg)
        self.assertIn(C.LEGEND_OVER_DATA, msg)

    def test_returns_empty_list_when_clean(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        self.assertEqual(C.assert_layout_clean(fig, "limpia.png"), [])


class PlateCheckGateTest(unittest.TestCase):
    """La puerta automática: un módulo no puede producir una lámina mala sin enterarse."""

    def setUp(self):
        C.plate_check_enable("off")
        C.plate_check_reset()

    def tearDown(self):
        C.plate_check_enable("off")
        C.plate_check_reset()
        os.environ.pop(C.PLATE_CHECK_ENV, None)
        plt.close("all")

    def broken(self):
        """Una lámina que la puerta TIENE que denunciar, con un defecto que el motor no puede reparar.

        Antes eran sólo dos rótulos escritos uno sobre otro, y la prueba dependía en realidad de que
        `plate_resolve` NO consiguiera separarlos: en cuanto el motor mejoró —al enseñarle que un
        marcador es un disco y no un punto— la lámina salía limpia y la puerta, correctamente, no
        denunciaba nada; la prueba fallaba entonces sólo según qué otro módulo hubiera cambiado antes los
        rcParams de matplotlib. La rejilla EQUIVOCADA (2 × 2 en lugar de 3 × 2) no es reparable por
        ningún motor de colocación, de modo que la puerta se prueba contra la puerta y no contra la
        habilidad del motor. Se conservan además los dos rótulos superpuestos."""
        fig, axes = new_plate(n_panels=4, rows=2, cols=2)
        for ax in axes:
            clean_series(ax)
        axes[0].text(0.5, 0.5, "uno", transform=axes[0].transAxes, fontsize=FS_BASE)
        axes[0].text(0.5, 0.5, "dos", transform=axes[0].transAxes, fontsize=FS_BASE)
        return fig

    def test_off_by_default_does_not_touch_the_rebuild(self):
        fig = self.broken()
        C.plate_resolve(fig)                       # no levanta nada con la puerta apagada
        self.assertEqual(C.plate_check_records(), [])

    def test_strict_mode_makes_plate_resolve_fail_loudly(self):
        C.plate_check_enable("strict")
        with self.assertRaises(C.PlateLayoutError):
            C.plate_resolve(self.broken())

    def test_report_mode_accumulates_every_plate(self):
        C.plate_check_enable("report")
        C.plate_resolve(self.broken())
        C.plate_resolve(self.broken())
        self.assertEqual(len(C.plate_check_records()), 2)
        self.assertIn("2 plate(s) checked", C.plate_check_summary())
        with tempfile.TemporaryDirectory() as tmp:
            path = C.plate_check_write(Path(tmp) / "check.txt")
            self.assertIn("layout problem", path.read_text(encoding="utf-8") + " layout problem")

    def test_env_var_enables_the_gate_without_touching_a_module(self):
        os.environ[C.PLATE_CHECK_ENV] = "strict"
        C.plate_check_enable("off") if False else None
        C._PLATE_CHECK["mode"] = None              # que mande la variable de entorno
        self.assertEqual(C.plate_check_mode(), "strict")
        with self.assertRaises(C.PlateLayoutError):
            C.plate_resolve(self.broken())

    def test_save_fig_is_gated_too(self):
        C.plate_check_enable("strict")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(C.PlateLayoutError):
                C.save_fig(self.broken(), Path(tmp) / "figX.png")

    def test_declared_name_and_grid_are_honoured(self):
        C.plate_check_enable("report")
        fig = self.broken()
        C.plate_declare(fig, "figS99_declarada.png")
        C.plate_resolve(fig)
        self.assertEqual(C.plate_check_records()[0][0], "figS99_declarada.png")


class PlacementHelpersTest(unittest.TestCase):
    """Las ayudas existen para que los paneles se arreglen en la CAUSA: cada una borra su defecto."""

    def tearDown(self):
        plt.close("all")

    def test_plate_ylabel_clears_the_axis_title_over_its_ticks(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[2]
        tw = twin_with_title_over_its_ticks(ax)
        self.assertTrue([p for p in C.check_layout(fig) if p.kind == C.AXIS_TITLE_OVER_TICKS])
        C.plate_ylabel(tw, "Unweighted autism cases (thousands)", right=True, fontsize=FS_BASE)
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.AXIS_TITLE_OVER_TICKS], [])

    def test_plate_ylabel_above_writes_one_short_horizontal_line(self):
        fig, axes = new_plate()
        ax = axes[0]
        clean_series(ax)
        ax.set_yticks([10, 20, 30, 40])
        ax.set_yticklabels(["10 000", "20 000", "30 000", "40 000"], fontsize=FS_TICK)
        t = C.plate_ylabel(ax, "Episodes", above=True, fontsize=FS_BASE)
        self.assertEqual(ax.get_ylabel(), "")
        self.assertAlmostEqual(float(t.get_rotation()), 0.0)
        self.assertEqual([p for p in C.check_layout(fig)
                          if p.kind in (C.AXIS_TITLE_OVER_TICKS, C.TEXT_OVER_TEXT)], [])

    def test_plate_place_legend_finds_a_spot_that_covers_no_data(self):
        fig, axes = new_plate()
        for ax in axes:
            clean_series(ax)
        ax = axes[0]
        lg = ax.legend(ax.lines, ["GRD episodes"], loc="center", fontsize=FS_TICK)
        self.assertTrue([p for p in C.check_layout(fig) if p.kind == C.LEGEND_OVER_DATA])
        loc = C.plate_place_legend(ax)
        self.assertIn(loc, list(C._PL_LOCS) + ["outside below"])
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.LEGEND_OVER_DATA], [])

    def test_plate_place_legend_goes_below_when_nothing_inside_is_free(self):
        fig, axes = new_plate()
        ax = axes[0]
        rng = np.random.default_rng(11)
        for k in range(6):                                  # panel lleno de tinta de borde a borde
            ax.plot(np.arange(2019, 2026), rng.uniform(0, 100, 7), label=f"serie {k}")
        ax.set_ylim(0, 100)
        ax.legend(loc="center", fontsize=FS_TICK, ncol=2)
        loc = C.plate_place_legend(ax)
        self.assertEqual(loc, "outside below")

    def test_plate_value_label_clears_marker_and_error_bar(self):
        fig, axes = new_plate()
        ax = axes[0]
        xs = np.arange(2019, 2026)
        ys = np.linspace(10, 40, 7)
        ax.errorbar(xs, ys, yerr=np.full(7, 4.0), fmt="o", markersize=3, ecolor="#888888")
        for x, y in zip(xs, ys):
            C.plate_value_label(ax, x, y, f"{y:.0f}", err=(y - 4.0, y + 4.0), fontsize=6.2)
        problems = [p for p in C.check_layout(fig) if p.kind == C.VALUE_LABEL_OVER_DATUM]
        self.assertEqual(problems, [], f"rótulos sobre su marcador: {problems}")

    def test_plate_thin_category_ticks_resolves_long_region_names(self):
        """Las dieciséis regiones en el eje X de una celda de 90 mm: sin adelgazar se leen fundidas."""
        fig, axes = new_plate()
        ax = axes[0]
        from epi_helpers import REGION_NAMES, REGION_ORDER
        names = [REGION_NAMES[r] for r in REGION_ORDER]
        ax.bar(np.arange(len(names)), np.linspace(5, 60, len(names)))
        ax.set_xticks(np.arange(len(names)))
        ax.set_xticklabels(names, fontsize=FS_TICK)
        self.assertTrue([p for p in C.check_layout(fig) if p.kind == C.TEXT_OVER_TEXT])
        report = C.plate_thin_category_ticks(ax, axis="x")
        self.assertIn(report["mode"], ("shrunk", "abbreviated", "rotated", "every 2th tick",
                                       "every 3th tick", "every 4th tick"))
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.TEXT_OVER_TEXT], [])
        # nada desaparece en silencio: lo que la lámina no imprime vuelve en el informe
        self.assertEqual(len(report["shown"]) + len(report["hidden"]), len(names))

    def test_plate_thin_category_ticks_drops_to_every_kth_and_says_what_it_hid(self):
        """Cuarenta nombres largos en una celda de 90 × 80 mm: reducir no basta y hay que adelgazar."""
        fig, axes = new_plate()
        ax = axes[0]
        labels = [f"Servicio de salud de la provincia {i:02d}" for i in range(40)]
        ax.barh(np.arange(len(labels)), np.linspace(1, 40, len(labels)))
        ax.set_yticks(np.arange(len(labels)))
        ax.set_yticklabels(labels, fontsize=FS_TICK)
        self.assertTrue([p for p in C.check_layout(fig) if p.kind == C.TEXT_OVER_TEXT])
        report = C.plate_thin_category_ticks(ax, axis="y")
        self.assertTrue(report["mode"].startswith("every"), report["mode"])
        self.assertTrue(report["hidden"], "lo que la lámina no imprime tiene que salir en el informe")
        self.assertEqual([p for p in C.check_layout(fig) if p.kind == C.TEXT_OVER_TEXT], [])

    def test_plate_thin_category_ticks_never_goes_below_the_floor(self):
        fig, axes = new_plate()
        ax = axes[0]
        labels = [f"Servicio de salud número {i}" for i in range(18)]
        ax.barh(np.arange(len(labels)), np.arange(len(labels)) + 1.0)
        ax.set_yticks(np.arange(len(labels)))
        ax.set_yticklabels(labels, fontsize=9.0)
        C.plate_thin_category_ticks(ax, axis="y")
        fig.canvas.draw()
        sizes = [t.get_size() for t in C._pl_tick_texts(ax.yaxis)]
        self.assertTrue(all(s >= C.PLATE_FS_FLOOR - 1e-9 for s in sizes))


class EveryPlateModuleGoesThroughTheGateTest(unittest.TestCase):
    """La puerta solo sirve si TODAS las láminas pasan por ella: se comprueba módulo a módulo."""

    MODULES = ["06_models.py", "08a_figures_grd.py", "08b_figures_rem.py", "08c_figures_triangulation.py",
               "08d_figure_dataflow.py", "13_extra_figures_hospital.py", "14_extra_figures_rem.py",
               "15_extra_figures_context.py", "15b_spatial_correlation.py"]

    def test_every_figure_module_saves_through_plate_resolve_or_save_fig(self):
        root = Path(__file__).resolve().parents[1] / "pipeline"
        for name in self.MODULES:
            path = root / name
            self.assertTrue(path.is_file(), f"falta el módulo de láminas {name}")
            src = path.read_text(encoding="utf-8")
            self.assertTrue("C.plate_resolve(" in src or "C.save_fig(" in src,
                            f"{name} guarda láminas sin pasar por la puerta del verificador "
                            f"(C.plate_resolve o C.save_fig)")

    #: Los cuatro módulos que escribían la letra de panel a secas («a») frente a las 58 leyendas que la
    #: escriben entre paréntesis («(a)»). El artículo publicaba así DOS convenciones sobre 59 láminas.
    LETTER_MODULES = ["13_extra_figures_hospital.py", "14_extra_figures_rem.py",
                      "15_extra_figures_context.py", "15b_spatial_correlation.py"]

    def test_panel_letter_is_parenthesised_everywhere(self):
        """UNA convención: la letra de panel se imprime «(a)», y siempre por el mismo sitio."""
        self.assertEqual([C.plate_panel_letter(i) for i in range(6)],
                         ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)"])
        self.assertEqual(C.plate_panel_letter("A"), "(a)")
        self.assertEqual(C.plate_panel_letter("(b)"), "(b)")
        root = Path(__file__).resolve().parents[1] / "pipeline"
        for name in self.LETTER_MODULES:
            src = (root / name).read_text(encoding="utf-8")
            self.assertIn("C.plate_panel_letter(", src,
                          f"{name} escribe la letra de panel sin pasar por C.plate_panel_letter")
        # los módulos que ya la parentizaban en el título siguen haciéndolo
        for name in ("06_models.py", "08a_figures_grd.py", "08b_figures_rem.py",
                     "08c_figures_triangulation.py"):
            src = (root / name).read_text(encoding="utf-8")
            self.assertIn('f"({letter_}) {title}"', src,
                          f"{name} dejó de parentizar la letra de panel")


@unittest.skipUnless(os.environ.get("PLATE_REAL") == "1",
                     "reconstrucción de una lámina real: PLATE_REAL=1")
class RealPlateTest(unittest.TestCase):
    """Comprobación sobre una lámina REAL reconstruida por su módulo (lenta: fuera de la suite por omisión)."""

    def test_context_plate_e22_is_clean(self):
        import importlib.util
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "pipeline"))
        spec = importlib.util.spec_from_file_location("m15", root / "pipeline" / "15_extra_figures_context.py")
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        D = m.load()
        P = m.prepare(D, "con_rett")
        with tempfile.TemporaryDirectory() as tmp:
            for lang in ("en", "es"):
                fig_path = m.FIG_BUILDERS["E22"](P["E22"], lang, Path(tmp))
                self.assertTrue(Path(fig_path).is_file())
        self.assertEqual([r for r in C.plate_check_records() if r[1]], [])


if __name__ == "__main__":
    unittest.main()
