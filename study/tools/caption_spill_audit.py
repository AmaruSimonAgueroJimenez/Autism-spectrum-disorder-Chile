# -*- coding: utf-8 -*-
"""caption_spill_audit.py — cuánta LEYENDA DE LÁMINA se imprime fuera de la página de su lámina, y si esa
cola lleva rótulo.

Por qué existe (tarea J1 de la fase 4j). El constructor rotula la cola de una leyenda partida
(«Figura N (continuación).»), pero hasta la fase 4j sólo lo hacía cuando detrás de la lámina se cerraba la
sección. En los demás casos la leyenda viajaba al DOCX como UN párrafo y era Word quien la partía, sin
poder poner rótulo: **100 colas sin rótulo** en los ocho documentos largos de la compilación del
2026-09-08, hasta el 88 % de una leyenda impresa en una página que no era la de su lámina. Ninguna medida
de página lo veía —esas páginas no están vacías ni dejan papel al pie, porque detrás de la cola va la
lámina siguiente—, y por eso el defecto pasó tres verificaciones.

Qué mide. Para cada leyenda del DOCX localiza la página impresa que lleva su rótulo, compara la leyenda
con lo que esa página imprime y cuenta lo que queda fuera; después mira si la página siguiente abre con el
rótulo de cola. No corrige nada y no toca ninguna cifra: escribe un JSON con una fila por leyenda, para
poner el ANTES y el DESPUÉS sobre el mismo instrumento y el mismo objeto.

Método. La comparación se hace sobre el flujo de caracteres SIN BLANCOS de cada página. Word parte
«quasi-Poisson» por su guion al final de un renglón y `pdftotext` devuelve dos palabras donde el documento
tiene una: una versión de este arnés que comparaba PALABRAS denunciaba 166 colas, 66 de ellas cortes de
renglón y no desbordamientos. Contar caracteres sin blancos quita ese falso positivo de raíz.

Este arnés lee el DOCX y el PDF desde fuera. La misma comprobación corre DENTRO de cada compilación
(`pipeline/10_manuscript.py`, `caption_spill_audit`, que se apoya en `caption_end` del informe del
constructor) y su resultado queda en `manuscript/build_report.json`
(`review.layout.caption_spill.unmarked_spills`, que tiene que ser 0).

    python study/tools/caption_spill_audit.py study/manuscript --out spill.json
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

FIG = {"en": "Figure", "es": "Figura"}
CONT = {"en": "continued", "es": "continuación"}
WS = re.compile(r"\s+")


def flat(s: str) -> str:
    """Flujo de caracteres sin blancos y en minúscula: inmune al punto donde cae el corte de renglón."""
    return WS.sub("", str(s)).lower()


def page_texts(pdf: Path) -> list[str]:
    out = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True,
                         check=True).stdout
    return out.split("\f")


def docx_captions(docx: Path, lang: str) -> list[dict]:
    """Las leyendas del documento, cada una ENTERA: la cabeza bajo la lámina más la cola rotulada, si la hay."""
    from docx import Document
    F, C = FIG[lang], CONT[lang]
    lab_re = re.compile(rf"^{F}\s+(S?\d+)\.\s")
    cont_re = re.compile(rf"^{F}\s+(S?\d+)\s+\({re.escape(C)}\)\.\s")
    caps: list[dict] = []
    by_label: dict[str, dict] = {}
    for p in Document(str(docx)).paragraphs:
        t = " ".join(p.text.split())
        m = cont_re.match(t)
        if m:
            d = by_label.get(f"{F} {m.group(1)}")
            if d is not None:
                d["full"] += " " + t[m.end():]
                d["split_in_docx"] = True
            continue
        m = lab_re.match(t)
        if m:
            lab = f"{F} {m.group(1)}"
            d = dict(label=lab, full=t[m.end():], split_in_docx=False)
            caps.append(d)
            by_label[lab] = d
    return caps


def audit(pdf: Path, docx: Path, lang: str) -> dict:
    F, C = FIG[lang], CONT[lang]
    pages = [flat(p) for p in page_texts(pdf)]
    rows = []
    for c in docx_captions(docx, lang):
        lab, cap = c["label"], flat(c["full"])
        needle = flat(lab + ".")
        pg = pos = None
        for i, t in enumerate(pages):
            # el rótulo SEGUIDO del comienzo de su leyenda: una frase del cuerpo que diga «Figura 3.» no cuenta
            j = t.find(needle + cap[:60])
            if j >= 0:
                pg, pos = i, j + len(needle)
                break
        if pg is None:
            rows.append(dict(label=lab, page=None, status="caption-not-found"))
            continue
        resto = pages[pg][pos:]
        k = 0
        while k < len(cap) and k < len(resto) and cap[k] == resto[k]:
            k += 1
        sobra = len(cap) - k
        marcada = pg + 1 < len(pages) and pages[pg + 1].startswith(flat(f"{lab} ({C})."))
        rows.append(dict(label=lab, page=pg + 1, chars_total=len(cap), chars_on_page=k,
                         chars_spilled=sobra, pct_spilled=round(100 * sobra / max(1, len(cap)), 1),
                         spilled=sobra > 0, marked=bool(marcada), split_in_docx=c["split_in_docx"],
                         unmarked_spill=bool(sobra > 0 and not marcada)))
    return dict(pdf=pdf.name, rows=rows, n_captions=len(rows),
                n_spill=sum(1 for r in rows if r.get("spilled")),
                n_marked=sum(1 for r in rows if r.get("marked")),
                n_unmarked=sum(1 for r in rows if r.get("unmarked_spill")),
                not_found=[r["label"] for r in rows if r.get("status")])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("build_dir", type=Path, help="directorio con los DOCX y sus PDF (p. ej. study/manuscript)")
    ap.add_argument("--out", type=Path, default=None, help="JSON con una fila por leyenda")
    ap.add_argument("--strict", action="store_true", help="devuelve 1 si queda alguna cola sin rótulo")
    args = ap.parse_args(argv)
    res, total = {}, 0
    for var in ("con_rett", "sin_rett"):
        for lang in ("en", "es"):
            for kind in ("manuscript", "supplement", "article"):
                pdf = args.build_dir / f"{kind}_{var}_{lang}.pdf"
                docx = args.build_dir / f"{kind}_{var}_{lang}.docx"
                if not (pdf.is_file() and docx.is_file()):
                    continue
                r = res[pdf.stem] = audit(pdf, docx, lang)
                total += r["n_unmarked"]
                print(f"{pdf.stem:32s} leyendas={r['n_captions']:3d} continuadas={r['n_spill']:3d} "
                      f"rotuladas={r['n_marked']:3d} SIN ROTULO={r['n_unmarked']:3d} "
                      f"no encontradas={len(r['not_found'])}")
    print("TOTAL DE COLAS SIN ROTULO:", total)
    if args.out:
        args.out.write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        print("informe:", args.out)
    return 1 if (args.strict and total) else 0


if __name__ == "__main__":
    raise SystemExit(main())
