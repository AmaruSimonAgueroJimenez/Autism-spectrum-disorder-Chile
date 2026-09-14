# -*- coding: utf-8 -*-
"""Guarda del INSTRUMENTO que mide el texto dibujado de las láminas (`tools/plate_text_audit.py`).

Por qué esta prueba existe. Los tres defectos que cerró la tarea G5 pasaron por tres verificaciones seguidas
porque nadie miraba el sitio donde vivían: el texto de un rótulo viaja al documento dentro de un mapa de
bits y `pdftotext` no lo ve, de modo que medir la tipografía de las láminas sobre el texto extraído del PDF
da siempre «cero defectos». El arnés de `plate_text_audit` mira el objeto `Text` de la figura ya compuesta,
que es lo que de verdad se imprime.

Un detector así sólo sirve si no puede quedarse mudo. Aquí se le dibuja una lámina con los defectos EXACTOS
que se cerraron —la leyenda de la S21 (c), los títulos de eje y las filas de la S53, los quintiles de la
S51 (d)— y se exige que los denuncie; y una lámina limpia, para que no denuncie lo que está bien. La suite
no puede permitirse dibujar las 244 láminas reales (son ~20 min por pasada), pero sí puede garantizar que
el instrumento con el que se miden sigue viendo.
"""
import sys
import unittest
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

LA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(LA / "tools"))
from plate_text_audit import audit_figure  # noqa: E402


class PlateTextAuditTest(unittest.TestCase):
    def tearDown(self):
        plt.close("all")

    @staticmethod
    def _defective():
        """Reproduce los rótulos tal como los dibujaban las tres láminas antes del arreglo."""
        fig, ax = plt.subplots(2, 2)
        ax[0, 0].bar([0, 1], [1, 2], label="2019-2020")
        ax[0, 0].bar([2, 3], [1, 2], label="2021-2024")
        ax[0, 0].legend(title="Identifier era")
        ax[0, 1].set_xlabel("Smoothed ratio (EB) 2019-2021")
        ax[0, 1].set_ylabel("Smoothed ratio (EB) 2022-2024")
        ax[1, 0].set_yticks([0, 1])
        ax[1, 0].set_yticklabels(["GRD F84 episodes (2019-2021 vs 2022-2025)",
                                  "REM A05 entries (2021-2022 vs 2023-2025)"])
        ax[1, 1].set_xticks(range(5))
        ax[1, 1].set_xticklabels([f"Q{i}\n{v} %" for i, v in
                                  enumerate(("10.1", "15.6", "18.1", "21.2", "26.9"), 1)])
        fig.canvas.draw()
        return fig

    @staticmethod
    def _clean():
        """La misma lámina ya arreglada: raya corta en la ventana, porcentaje pegado en inglés."""
        fig, ax = plt.subplots(2, 2)
        ax[0, 0].bar([0, 1], [1, 2], label="2019–2020")
        ax[0, 0].bar([2, 3], [1, 2], label="2021–2024")
        ax[0, 0].legend(title="Identifier era")
        ax[0, 1].set_xlabel("Smoothed ratio (EB) 2019–2021")
        ax[0, 1].set_ylabel("Smoothed ratio (EB) 2022–2024")
        ax[1, 0].set_yticks([0, 1])
        ax[1, 0].set_yticklabels(["GRD F84 episodes (2019–2021 vs 2022–2025)",
                                  "REM-20 discharges (2021–2022 vs 2023–2025)"])
        ax[1, 1].set_xticks(range(5))
        ax[1, 1].set_xticklabels([f"Q{i}\n{v}%" for i, v in
                                  enumerate(("10.1", "15.6", "18.1", "21.2", "26.9"), 1)])
        ax[1, 1].set_title("Pooled ratio by deprivation quintile (exact Poisson 95% CI)")
        fig.canvas.draw()
        return fig

    def test_sees_the_year_window_written_with_a_hyphen(self):
        faults = audit_figure(self._defective(), "SYNTH", "en")
        años = [f for f in faults if f["rule"] == "year_span_hyphen"]
        # 2 de la leyenda, 2 de los títulos de eje, 2 en cada uno de los dos rótulos de fila.
        self.assertEqual(len(años), 8, [f["token"] for f in años])
        self.assertIn("2019-2020", [f["token"] for f in años])

    def test_sees_the_spanish_percent_inside_an_english_plate(self):
        faults = audit_figure(self._defective(), "SYNTH", "en")
        pct = [f for f in faults if f["rule"] == "pct_spacing"]
        self.assertEqual(len(pct), 5, [f["text"] for f in pct])

    def test_the_percent_rule_follows_the_language(self):
        """El mismo rótulo «10.1 %» es DEFECTO en inglés y CORRECTO en español; y al revés."""
        fig = self._defective()
        self.assertEqual(len([f for f in audit_figure(fig, "S", "en") if f["rule"] == "pct_spacing"]), 5)
        self.assertEqual(len([f for f in audit_figure(fig, "S", "es") if f["rule"] == "pct_spacing"]), 0)

    def test_stays_quiet_on_a_clean_plate(self):
        """Control negativo: sobre la lámina arreglada no denuncia nada, ni el «REM-20» ni el «95% CI»."""
        self.assertEqual(audit_figure(self._clean(), "SYNTH", "en"), [])

    def test_ignores_mathtext_exponents(self):
        """El guion de un exponente en modo matemático es un MENOS a la altura del eje matemático."""
        fig, ax = plt.subplots()
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["$\\mathdefault{10^{-1}}$", "$\\mathdefault{10^{-2}}$"])
        fig.canvas.draw()
        self.assertEqual(audit_figure(fig, "SYNTH", "en"), [])


if __name__ == "__main__":
    unittest.main()
