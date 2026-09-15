"""The drawing code shown on the results page must still be the code the modules run.

`docs/version_10_panels.qmd` carries a copy of the plotting code of `docs/study/figuras_principales.py`
and `figuras_suplementarias.py`, so that each figure on the page is drawn by the code printed with it
rather than linked from a folder. The modules stay in place for rebuilding the 600 dpi plates outside
the site, which leaves two copies of the same code. These tests are what stops them drifting: they fail
if the page no longer matches the modules, and the fix is to regenerate the page.

    python scripts/build_version_pages.py
"""
from pathlib import Path
import ast
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "version_10_panels.qmd"
STUDY = ROOT / "docs" / "study"
BUILDER = ROOT / "scripts" / "build_version_pages.py"
GENERATED = ["1", "2", "3", "4", "S2", "S3", "S4", "S5", "S7", "S8", "S9"]


def page_chunks():
    """The Python of every ```{python} chunk in the page, keyed by its label."""
    out = {}
    for block in re.findall(r"```\{python\}\n(.*?)```", PAGE.read_text(encoding="utf-8"), re.S):
        label = re.search(r"#\|\s*label:\s*(\S+)", block)
        if label:
            out[label.group(1)] = block
    return out


def module_figure_source(module, fig_id):
    """The source of `figN` as the module defines it."""
    src = (STUDY / module).read_text(encoding="utf-8")
    for node in ast.parse(src).body:
        if isinstance(node, ast.FunctionDef) and node.name == f"fig{fig_id}":
            return ast.get_source_segment(src, node)
    raise AssertionError(f"fig{fig_id} not found in {module}")


def normalise(source):
    """Compare the code itself, ignoring the one line the page has to change to show the figure."""
    source = re.sub(r"save\(fig, ('Figure_[^']+'), lang(?:, close=False)?\)", r"save(fig, \1, lang)", source)
    source = re.sub(r"\n\s*return fig\b", "", source)
    return [line.rstrip() for line in source.strip().splitlines()]


class PageCarriesTheDrawingCode(unittest.TestCase):
    def test_every_generated_figure_has_its_code_on_the_page(self):
        chunks = page_chunks()
        for fig_id in GENERATED:
            with self.subTest(figure=fig_id):
                self.assertIn(f"figura-{fig_id.lower()}", chunks,
                              f"the page has no chunk drawing figure {fig_id}")
                self.assertIn(f"def fig{fig_id}(lang):", chunks[f"figura-{fig_id.lower()}"],
                              f"the chunk for figure {fig_id} does not define its drawing function")

    def test_the_code_on_the_page_matches_the_module(self):
        chunks = page_chunks()
        for fig_id in GENERATED:
            module = "figuras_principales.py" if fig_id in ("1", "2", "3", "4") else "figuras_suplementarias.py"
            with self.subTest(figure=fig_id):
                chunk = chunks[f"figura-{fig_id.lower()}"]
                start = chunk.index(f"def fig{fig_id}(lang):")
                end = chunk.index("\nplt.close(", start)
                self.assertEqual(normalise(chunk[start:end]), normalise(module_figure_source(module, fig_id)),
                                 f"figure {fig_id} differs between the page and {module}; "
                                 f"run python scripts/build_version_pages.py")

    def test_no_figure_is_shown_from_a_stored_file_unless_it_is_inherited(self):
        """Only S1 and S6 may come from a folder: nothing in the repository draws them."""
        shown = set(re.findall(r"figure_md\(\s*[\"'](S?\d+)[\"']", PAGE.read_text(encoding="utf-8")))
        shown |= set(re.findall(r'for fid in \("(S\d+)", "(S\d+)"\)', PAGE.read_text(encoding="utf-8"))[0]
                     if re.search(r'for fid in \("S\d+", "S\d+"\)', PAGE.read_text(encoding="utf-8")) else [])
        self.assertTrue(shown <= {"S1", "S6"},
                        f"these figures are shown from a stored file but the repository can draw them: {sorted(shown - {'S1', 'S6'})}")

    def test_the_page_is_what_the_builder_writes(self):
        result = subprocess.run([sys.executable, str(BUILDER), "--check"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
