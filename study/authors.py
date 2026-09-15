# -*- coding: utf-8 -*-
"""Author metadata of the study, read by `pipeline/10_manuscript.py`.

Procedencia: estas dos constantes vivían en `paper/prose.py`, que nunca estuvo versionado en git y
desapareció al borrarse esa carpeta, dejando fallando tres pruebas de `test_10_manuscript.py`.
Aquí se versiona sólo la autoría, no la prosa: el texto del manuscrito no forma parte de este
repositorio, y `load_paper_authors` sólo lee estos dos nombres mediante `ast`, sin importar el módulo.
"""

AUTHORS = [
    ('Amaru Simón Agüero Jiménez', '1', 'amaruaguero2004@ug.uchile.cl'),
]

AFFILIATIONS = [
    ('1', '[Afiliación institucional por completar]'),
]
