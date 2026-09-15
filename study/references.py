# -*- coding: utf-8 -*-
"""references.py — bibliografía en estilo Vancouver a partir de study/references.bib.

El texto del manuscrito cita con marcadores `[@clave]` o `[@clave1; @clave2]`.
`Citations` asigna números por orden de primera aparición, sustituye cada marcador
por «(n)», «(n,m)» o «(n-m)» y produce la lista final formateada.

Procedencia: este archivo vivía en `paper/references.py`, que nunca estuvo versionado en git y
desapareció al borrarse esa carpeta, dejando sin importar a `docx_builder.py` y a ocho pruebas.
Se recuperó desde la única copia superviviente, en una carpeta de versión no versionada, con dos
cambios deliberados: el docstring y la constante BIB, que ahora apunta a `study/references.bib`
(122 entradas) en vez de a `docs/references.bib`, que es la bibliografía distinta del sitio Quarto.
"""
from __future__ import annotations

import re
from pathlib import Path

BIB = Path(__file__).resolve().parent / "references.bib"      # study/references.bib, 122 entries

ACCENTS = {
    r"{\'a}": "á", r"{\'e}": "é", r"{\'i}": "í", r"{\'o}": "ó", r"{\'u}": "ú", r"{\'\i}": "í",
    r"{\'A}": "Á", r"{\'E}": "É", r"{\'I}": "Í", r"{\'O}": "Ó", r"{\'U}": "Ú",
    r"{\~n}": "ñ", r"{\~N}": "Ñ", r"{\c{c}}": "ç", r"{\"u}": "ü", r"{\"o}": "ö", r"{\"a}": "ä",
    r"\'a": "á", r"\'e": "é", r"\'i": "í", r"\'o": "ó", r"\'u": "ú", r"\~n": "ñ", r"\c{c}": "ç",
    "--": "-", r"\&": "&", r"\#": "#",
}


def _clean(value: str) -> str:
    for k, v in ACCENTS.items():
        value = value.replace(k, v)
    value = re.sub(r"\{\\'\\i\}", "í", value)
    value = value.replace("{", "").replace("}", "")
    return " ".join(value.split())


def _fields(body: str) -> dict:
    """Campos `clave = {valor}` con llaves anidadas de cualquier profundidad."""
    fields, i, n = {}, 0, len(body)
    while i < n:
        m = re.compile(r"(\w+)\s*=\s*\{").search(body, i)
        if not m:
            break
        depth, j = 1, m.end()
        while j < n and depth:
            depth += {"{": 1, "}": -1}.get(body[j], 0)
            j += 1
        fields[m.group(1).lower()] = body[m.end():j - 1].strip()
        i = j
    return fields


def parse_bib(path: Path = BIB) -> dict:
    text = path.read_text(encoding="utf-8")
    entries = {}
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, flags=re.S):
        kind, key, body = m.group(1).lower(), m.group(2).strip(), m.group(3)
        fields = _fields(body)
        fields["_kind"] = kind
        entries[key] = fields
    return entries


def _author_list(raw: str, limit: int = 6) -> str:
    raw = raw.strip()
    parts = [p.strip() for p in re.split(r"\s+and\s+", raw)]
    names, others = [], False
    for p in parts:
        if p.lower() == "others":
            others = True
            continue
        if p.startswith("{") and p.endswith("}"):
            names.append(_clean(p))
            continue
        if "," in p:
            last, first = [x.strip() for x in p.split(",", 1)]
        else:
            tokens = p.split()
            last, first = tokens[-1], " ".join(tokens[:-1])
        initials = "".join(_clean(t)[0] for t in re.split(r"[\s\-]+", first) if t)
        names.append(f"{_clean(last)} {initials}".strip())
    if len(names) > limit:
        names = names[:limit]
        others = True
    out = ", ".join(names)
    if others:
        out += ", et al"
    return out


def format_vancouver(entry: dict) -> str:
    kind = entry["_kind"]
    authors = _author_list(entry.get("author") or entry.get("editor") or "")
    if not entry.get("author") and entry.get("editor"):
        authors += ", editores"
    title = _clean(entry.get("title", ""))
    year = entry.get("year", "")
    doi = entry.get("doi")
    url = entry.get("url")
    if kind == "article":
        journal = _clean(entry.get("journal", ""))
        vol = entry.get("volume", "")
        num = entry.get("number")
        pages = _clean(entry.get("pages", ""))
        ref = f"{authors}. {title}. {journal}. {year}"
        if vol:
            ref += f";{vol}"
            if num:
                ref += f"({num})"
        if pages:
            ref += f":{pages}"
        ref += "."
    elif kind == "book":
        publisher = _clean(entry.get("publisher", ""))
        address = _clean(entry.get("address", ""))
        ref = f"{authors}. {title}. " + (f"{address}: " if address else "") + f"{publisher}; {year}."
    elif kind == "incollection":
        editors = _author_list(entry.get("editor", ""))
        booktitle = _clean(entry.get("booktitle", ""))
        publisher = _clean(entry.get("publisher", ""))
        pages = _clean(entry.get("pages", ""))
        ref = f"{authors}. {title}. En: {editors}, editores. {booktitle}. {publisher}; {year}." + (f" p. {pages}." if pages else "")
    elif kind == "techreport":
        institution = _clean(entry.get("institution", ""))
        number = _clean(entry.get("number", ""))
        ref = f"{authors}. {title}. {institution}; {year}." + (f" ({number})." if number else "")
    else:
        how = _clean(entry.get("howpublished", ""))
        ref = f"{authors}. {title}. " + (f"{how}; " if how else "") + f"{year}."
    if doi:
        ref += f" doi:{_clean(doi)}"
    elif url:
        ref += f" Disponible en: {url}"
    return ref


MARKER = re.compile(r"\[(@[^\]]+)\]")


class Citations:
    def __init__(self, entries: dict | None = None):
        self.entries = entries or parse_bib()
        self.order: list[str] = []

    def number(self, key: str) -> int:
        if key not in self.entries:
            raise KeyError(f"Clave bibliográfica desconocida: {key}")
        if key not in self.order:
            self.order.append(key)
        return self.order.index(key) + 1

    def _format_numbers(self, numbers: list[int]) -> str:
        numbers = sorted(set(numbers))
        groups, start, prev = [], numbers[0], numbers[0]
        for n in numbers[1:]:
            if n == prev + 1:
                prev = n
                continue
            groups.append((start, prev))
            start = prev = n
        groups.append((start, prev))
        parts = [f"{a}" if a == b else (f"{a},{b}" if b == a + 1 else f"{a}-{b}") for a, b in groups]
        return "(" + ",".join(parts) + ")"

    def resolve(self, text: str) -> str:
        """Sustituye los marcadores [@a; @b] por números Vancouver en orden de aparición."""
        def repl(m):
            keys = [k.strip().lstrip("@") for k in m.group(1).split(";")]
            return self._format_numbers([self.number(k) for k in keys])
        return MARKER.sub(repl, text)

    def reference_list(self) -> list[str]:
        return [format_vancouver(self.entries[k]) for k in self.order]


if __name__ == "__main__":
    c = Citations()
    print(len(c.entries), "entradas")
    sample = "Texto [@zeidan2022] y [@loomes2017; @fyfe2026; @zeidan2022] y [@ley21545]."
    print(c.resolve(sample))
    for i, r in enumerate(c.reference_list(), 1):
        print(i, r)
    print("--- todas:")
    for k, e in c.entries.items():
        print(" ", format_vancouver(e))
