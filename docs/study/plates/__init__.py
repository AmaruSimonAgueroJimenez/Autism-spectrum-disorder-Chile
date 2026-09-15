"""Redrawn corpus plates, one module per plate.

Each stored plate in `docs/study/corpus/figures/` was produced by `study/pipeline/`, which reads
microdata that is not in this repository. Where the plate's series survive in a published table, a
module here redraws it from that table so the chapter can show the code that made it. One module per
plate, so the modules never collide and each one can be verified on its own.

Every module exposes `draw()` returning a matplotlib figure, and `PLATE`, `SOURCES` and `NOTE`
describing what it reconstructs and from what. The corpus is English only, so nothing here is
bilingual: inventing a Spanish plate for an English original would misrepresent it.
"""
from importlib import import_module
from pathlib import Path

HERE = Path(__file__).resolve().parent


def available():
    """The plate ids this package can draw, in the corpus's own order."""
    return sorted(p.stem for p in HERE.glob("*.py") if p.stem != "__init__")


def load(plate_id):
    """Import one plate module by its corpus id."""
    return import_module(f"{__name__}.{plate_id}")


def draw(plate_id):
    """Draw one plate and hand back its figure."""
    return load(plate_id).draw()
