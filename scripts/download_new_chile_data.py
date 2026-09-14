#!/usr/bin/env python3
"""Descarga las fuentes chilenas de contexto para la revisión del manuscrito."""
from downloads.download_chile_sources import main


if __name__ == "__main__":
    raise SystemExit(main(default_profile="context"))

