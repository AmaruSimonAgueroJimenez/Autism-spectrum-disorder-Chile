#!/usr/bin/env python3
"""Descarga/audita GRD, DEIS, REM y metadatos hospitalarios oficiales."""
from downloads.download_chile_sources import main


if __name__ == "__main__":
    raise SystemExit(main(default_profile="hospital"))

