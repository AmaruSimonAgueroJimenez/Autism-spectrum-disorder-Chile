# -*- coding: utf-8 -*-
"""plate_text_audit.py — mide el TEXTO QUE LA LÁMINA DIBUJA, no el que el PDF deja extraer.

Por qué existe. Un rótulo de lámina viaja al documento dentro de un mapa de bits: `pdftotext` no lo ve.
Medir la tipografía de las láminas sobre el texto extraído del PDF da siempre «cero defectos», que es
exactamente lo que dejó pasar la ronda anterior. Este arnés se engancha a la función que guarda la lámina
y, con la composición YA CONGELADA (después de `plate_fit`, `plate_resolve` y de la colocación de leyendas
y rótulos), recorre cada objeto `Text` de la figura —marcas de eje mayores y menores incluidas— y lo
contrasta contra dos reglas del estudio:

  A. VENTANA DE AÑOS con guion ASCII donde el corpus imprime raya corta («2019-2021» → «2019–2021»).
  B. PORCENTAJE con el espaciado del OTRO idioma («12.3 %» en inglés, «12,3%» en español).

No corrige nada y no cambia ninguna cifra: escribe un JSON con un hallazgo por rótulo, para poder poner
el ANTES y el DESPUÉS sobre el mismo instrumento y el mismo objeto.

    python lancet_americas/tools/plate_text_audit.py --module 15b --out audit.json
    python lancet_americas/tools/plate_text_audit.py --module 13 --variants con_rett --langs en
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent
REPO = PKG.parent
for p in (str(REPO), str(PKG)):
    if p not in sys.path:
        sys.path.insert(0, p)

#: Ventana de dos años de cuatro cifras unida por guion ASCII. El negativo delante de una cifra suelta, la
#: fecha ISO y los identificadores («REM-20») quedan fuera a propósito: no son ventanas de años.
YEAR_SPAN_HYPHEN = re.compile(r"(?<!\d)((?:19|20)\d{2})-((?:19|20)\d{2})(?!\d)")
#: Porcentaje a la española: cifra, espacio (normal o duro) y signo. Es lo correcto en español y un defecto
#: en inglés, que lo escribe pegado.
PCT_SPACED = re.compile(r"\d[   ]+%")
#: Porcentaje a la inglesa: cifra y signo pegados. Lo contrario.
PCT_TIGHT = re.compile(r"\d%")


def _texts(fig):
    """Todo `Text` que la figura imprime, con el sitio donde está, para poder señalarlo en el papel."""
    out = []

    def add(where, artist):
        if artist is None or not getattr(artist, "get_visible", lambda: True)():
            return
        s = artist.get_text()
        if s and s.strip():
            out.append((where, s))

    for t in fig.texts:
        add("figura", t)
    axes = list(fig.axes)
    i = 0
    while i < len(axes):
        axes.extend(a for a in getattr(axes[i], "child_axes", []) if a not in axes)
        i += 1
    for k, ax in enumerate(axes):
        letter = getattr(getattr(ax, "_panel_letter", None), "get_text", lambda: None)()
        who = letter or f"#{k}"
        if getattr(ax, "axison", True):
            for nom, axis in (("x", ax.xaxis), ("y", ax.yaxis)):
                if not axis.get_visible():
                    continue
                # Marcas MAYORES y MENORES: una ventana de años puede estar en cualquiera de las dos.
                for t in axis.get_ticklabels(which="both"):
                    add(f"{who} marca {nom}", t)
                add(f"{who} rótulo eje {nom}", axis.label)
        add(f"{who} título", ax.title)
        for t in ax.texts:
            add(f"{who} texto", t)
        lg = ax.get_legend()
        if lg is not None and lg.get_visible():
            for t in lg.get_texts():
                add(f"{who} leyenda", t)
            add(f"{who} título de leyenda", lg.get_title())
    return out


def audit_figure(fig, name: str, lang: str) -> list[dict]:
    """Hallazgos de una lámina ya compuesta. Sin efectos: no toca la figura."""
    faults = []
    for where, s in _texts(fig):
        # El modo matemático compone el guion como MENOS a la altura del eje matemático: no es el trazo
        # que se persigue y matplotlib fabrica esas marcas para todo el eje logarítmico, dentro y fuera
        # de la ventana dibujada.
        if "$" in s:
            continue
        for m in YEAR_SPAN_HYPHEN.finditer(s):
            faults.append(dict(plate=name, lang=lang, rule="year_span_hyphen", where=where,
                               text=s, token=m.group(0)))
        bad_pct = PCT_SPACED if lang == "en" else PCT_TIGHT
        for m in bad_pct.finditer(s):
            faults.append(dict(plate=name, lang=lang, rule="pct_spacing", where=where,
                               text=s, token=m.group(0)))
    return faults


def _load(path: Path):
    spec = importlib.util.spec_from_file_location(path.stem.replace(".", "_"), path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--module", required=True, choices=["13", "15b"])
    ap.add_argument("--variants", nargs="+")
    ap.add_argument("--langs", nargs="+")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    found: list[dict] = []
    seen: list[str] = []

    if args.module == "13":
        path = PKG / "pipeline" / "13_extra_figures_hospital.py"
        mod = _load(path)
        original = mod.save_plate

        def wrapped(fig, p):
            out = original(fig, p)
            name = Path(p).stem
            lang = getattr(fig, "_lancet_lang", "es")
            seen.append(f"{name}|{lang}")
            found.extend(audit_figure(fig, name, lang))
            return out

        mod.save_plate = wrapped
    else:
        path = PKG / "pipeline" / "15b_spatial_correlation.py"
        mod = _load(path)
        original = mod._save

        def wrapped(fig, fdir, name, plt, lang):
            out = original(fig, fdir, name, plt, lang)
            seen.append(f"{name}|{lang}")
            found.extend(audit_figure(fig, name, lang))
            return out

        mod._save = wrapped

    argv = [str(path)]
    if args.variants:
        argv += ["--variants", *args.variants]
    if args.langs:
        argv += ["--langs", *args.langs]
    sys.argv = argv
    code = mod.main()

    report = dict(module=args.module, plates_seen=len(seen), plates=sorted(set(seen)),
                  n_faults=len(found), by_rule={}, faults=found)
    for f in found:
        report["by_rule"][f["rule"]] = report["by_rule"].get(f["rule"], 0) + 1
    text = json.dumps(report, ensure_ascii=False, indent=1)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    print(f"[audit {args.module}] láminas medidas: {len(seen)}; hallazgos: {len(found)} {report['by_rule']}")
    for f in found[:40]:
        print(f"  {f['plate']} [{f['lang']}] {f['where']}: «{f['token']}» en «{f['text'][:70]}»")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
