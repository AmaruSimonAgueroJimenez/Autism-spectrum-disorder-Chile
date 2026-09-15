"""The drawing code shown on the results page must still be the code the modules run.

`docs/results.qmd` carries a copy of the plotting code of `docs/study/figuras_principales.py`
and `figuras_suplementarias.py`, so that each figure on the page is drawn by the code printed with it
rather than linked from a folder. The modules stay in place for rebuilding the 600 dpi plates outside
the site, which leaves two copies of the same code. These tests are what stops them drifting: they fail
if the page no longer matches the modules, and the fix is to regenerate the page.

    python scripts/build_results_chapter.py
"""
from pathlib import Path
import ast
import re
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "results.qmd"
STUDY = ROOT / "docs" / "study"
BUILDER = ROOT / "scripts" / "build_results_chapter.py"
GENERATED = ["1", "2", "3", "4", "S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8", "S9"]


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
                                 f"run python scripts/build_results_chapter.py")

    def test_no_figure_is_shown_from_a_stored_file(self):
        """Every figure must be drawn by a chunk. Nothing on the page may come from a stored file."""
        shown = set(re.findall(r"figure_md\(\s*[\"'](S?\d+)[\"']", PAGE.read_text(encoding="utf-8")))
        shown |= set(re.findall(r'for fid in \("(S\d+)", "(S\d+)"\)', PAGE.read_text(encoding="utf-8"))[0]
                     if re.search(r'for fid in \("S\d+", "S\d+"\)', PAGE.read_text(encoding="utf-8")) else [])
        self.assertEqual(shown, set(),
                         f"these figures are shown from a stored file but the repository can draw them: {sorted(shown)}")

    def test_the_page_is_what_the_builder_writes(self):
        result = subprocess.run([sys.executable, str(BUILDER), "--check"], capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


class GeneratedPagesAreValidPython(unittest.TestCase):
    """Every generated page must parse before it is rendered.

    A template that loses one level of escaping writes a broken f-string into the page, and Quarto
    only reports it minutes into a render. Parsing the chunks here turns that into a one-second failure.
    """

    PAGES = ["results.qmd"]

    def test_every_chunk_parses(self):
        for name in self.PAGES:
            page = ROOT / "docs" / name
            with self.subTest(page=name):
                self.assertTrue(page.exists(), f"{name} is missing")
                blocks = re.findall(r"```\{python\}\n(.*?)```", page.read_text(encoding="utf-8"), re.S)
                self.assertTrue(blocks, f"{name} has no Python chunks")
                for i, block in enumerate(blocks, 1):
                    code = "\n".join(l for l in block.splitlines() if not l.startswith("#|"))
                    try:
                        ast.parse(code)
                    except SyntaxError as exc:
                        self.fail(f"{name} chunk {i} does not parse: {exc}")


if __name__ == "__main__":
    unittest.main()
