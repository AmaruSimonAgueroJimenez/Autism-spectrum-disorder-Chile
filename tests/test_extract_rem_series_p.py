import argparse
import csv
import hashlib
import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile


REPO_ROOT = Path(__file__).resolve().parents[1]
DOWNLOAD_DIR = REPO_ROOT / "scripts" / "downloads"
sys.path.insert(0, str(DOWNLOAD_DIR))

from extract_rem_series_p import (  # noqa: E402
    DESTINATION_ROOT_ENV,
    MANIFEST_FIELDS,
    MANIFEST_NAME,
    SOURCE_ROOT_ENV,
    build_parser,
    main,
    parse_years,
    process_year,
    sha256_file,
)


def valid_series(year: int, value: str = "1") -> bytes:
    header = (
        "Mes;IdServicio;Ano;IdEstablecimiento;CodigoPrestacion;"
        "IdRegion;IdComuna\n"
    )
    row = f"12;1;{year};100;P2500500;13;13101\n"
    if value != "1":
        row = f"12;1;{year};100;P2500500;13;{value}\n"
    return (header + row).encode("utf-8")


def workbook_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", "<Types/>")
        workbook.writestr("xl/workbook.xml", "<workbook/>")
    return buffer.getvalue()


def make_rem_zip(
    source_root: Path,
    year: int,
    *,
    series_name: str | None = None,
    series_content: bytes | None = None,
    dictionary_name: str | None = None,
    extra_members: dict[str, bytes] | None = None,
) -> Path:
    source_root.mkdir(parents=True, exist_ok=True)
    archive_path = source_root / f"SERIE_REM_{year}.zip"
    if series_name is None:
        series_name = f"Datos/SerieP{year}.csv"
    if series_content is None:
        series_content = valid_series(year)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(series_name, series_content)
        if dictionary_name:
            archive.writestr(dictionary_name, workbook_bytes())
        for name, content in (extra_members or {}).items():
            archive.writestr(name, content)
    return archive_path


class ExtractRemSeriesPTests(unittest.TestCase):
    def test_extracts_series_and_dictionary_with_canonical_paths(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zips"
            destination = root / "series_p"
            make_rem_zip(
                source,
                2024,
                series_name="Datos/SerieP2024.csv",
                dictionary_name="Diccionarios/DICCIONARIO CODIGOS SP_24_V1.1.xlsm",
            )

            rows = process_year(2024, source, destination)

            series_path = destination / "SerieP_2024.csv"
            dictionary_path = (
                destination
                / "diccionarios"
                / "2024"
                / "DICCIONARIO CODIGOS SP_24_V1.1.xlsm"
            )
            self.assertEqual(series_path.read_bytes(), valid_series(2024))
            self.assertEqual(dictionary_path.read_bytes(), workbook_bytes())
            self.assertEqual({row["artifact_type"] for row in rows}, {"serie_p", "diccionario_sp"})
            series_row = next(row for row in rows if row["artifact_type"] == "serie_p")
            self.assertEqual(series_row["sha256"], sha256_file(series_path))
            self.assertEqual(series_row["destination"], "SerieP_2024.csv")
            self.assertFalse(list(destination.rglob("*.part")))

    def test_accepts_historical_series_name_variants(self):
        variants = {
            2019: "SerieP_2019.txt",
            2022: "SerieP.txt",
            2023: "Datos/SerieP2023.txt",
            2024: "Datos/SP_2024.csv",
        }
        for year, member_name in variants.items():
            with self.subTest(year=year), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "zips"
                destination = root / "out"
                make_rem_zip(source, year, series_name=member_name)
                process_year(year, source, destination)
                self.assertEqual(
                    (destination / f"SerieP_{year}.csv").read_bytes(),
                    valid_series(year),
                )

    def test_rejects_any_path_traversal_before_writing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zips"
            destination = root / "out"
            make_rem_zip(
                source,
                2024,
                extra_members={"../escape.txt": b"malicioso"},
            )
            with self.assertRaisesRegex(ValueError, "Ruta insegura"):
                process_year(2024, source, destination)
            self.assertFalse(destination.exists())
            self.assertFalse((root / "escape.txt").exists())

    def test_rejects_empty_invalid_or_wrong_year_series(self):
        cases = {
            "empty": b"",
            "invalid_header": b"foo,bar\n1,2\n",
            "wrong_year": valid_series(2023),
            "header_only": (
                b"Mes;IdServicio;Ano;IdEstablecimiento;CodigoPrestacion;"
                b"IdRegion;IdComuna\n"
            ),
        }
        for label, content in cases.items():
            with self.subTest(case=label), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / "zips"
                destination = root / "out"
                make_rem_zip(source, 2024, series_content=content)
                with self.assertRaises(ValueError):
                    process_year(2024, source, destination)
                self.assertFalse(destination.exists())

    def test_different_destination_requires_refresh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zips"
            destination = root / "out"
            make_rem_zip(source, 2024)
            process_year(2024, source, destination)
            series_path = destination / "SerieP_2024.csv"
            series_path.write_bytes(b"contenido local distinto")

            with self.assertRaisesRegex(FileExistsError, "--refresh"):
                process_year(2024, source, destination)
            self.assertEqual(series_path.read_bytes(), b"contenido local distinto")

            rows = process_year(2024, source, destination, refresh=True)
            self.assertEqual(series_path.read_bytes(), valid_series(2024))
            self.assertEqual(rows[0]["status"], "actualizado")

    def test_identical_destination_is_not_rewritten(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zips"
            destination = root / "out"
            make_rem_zip(source, 2024)
            process_year(2024, source, destination)
            series_path = destination / "SerieP_2024.csv"
            before = series_path.stat().st_mtime_ns
            rows = process_year(2024, source, destination)
            self.assertEqual(series_path.stat().st_mtime_ns, before)
            self.assertEqual(rows[0]["status"], "verificado_existente")

    def test_dry_run_does_not_create_destination(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zips"
            destination = root / "out"
            make_rem_zip(source, 2024)
            rows = process_year(2024, source, destination, dry_run=True)
            self.assertEqual(rows, [])
            self.assertFalse(destination.exists())

    def test_cli_writes_atomic_deduplicated_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zips"
            destination = root / "out"
            make_rem_zip(
                source,
                2024,
                dictionary_name="Diccionarios/DICCIONARIO CODIGOS SP_24.xlsx",
            )
            arguments = [
                "--source-root",
                str(source),
                "--destination-root",
                str(destination),
                "--years",
                "2024",
            ]
            self.assertEqual(main(arguments), 0)
            self.assertEqual(main(arguments), 0)

            manifest = destination / MANIFEST_NAME
            with manifest.open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle)
                rows = list(reader)
                self.assertEqual(reader.fieldnames, MANIFEST_FIELDS)
            self.assertEqual(len(rows), 2)
            self.assertEqual({row["status"] for row in rows}, {"verificado_existente"})
            self.assertTrue(all(len(row["sha256"]) == 64 for row in rows))
            self.assertFalse(list(destination.glob(f".{MANIFEST_NAME}.*.part")))

    def test_year_parser_supports_lists_and_ranges(self):
        self.assertEqual(parse_years(["2019-2021", "2023,2021"]), [2019, 2020, 2021, 2023])
        with self.assertRaisesRegex(ValueError, "invertido"):
            parse_years(["2024-2022"])
        with self.assertRaisesRegex(ValueError, "inválido"):
            parse_years(["202x"])

    def test_environment_roots_are_used_as_parser_defaults(self):
        with patch.dict(
            os.environ,
            {
                SOURCE_ROOT_ENV: "/tmp/rem-zips-test",
                DESTINATION_ROOT_ENV: "/tmp/rem-series-p-test",
            },
        ):
            args = build_parser().parse_args([])
        self.assertEqual(args.source_root, Path("/tmp/rem-zips-test"))
        self.assertEqual(args.destination_root, Path("/tmp/rem-series-p-test"))

    def test_run_reports_missing_year_without_manifest(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "zips"
            destination = root / "out"
            source.mkdir()
            args = argparse.Namespace(
                source_root=source,
                destination_root=destination,
                years=["2024"],
                refresh=False,
                dry_run=False,
            )
            from extract_rem_series_p import run

            self.assertEqual(run(args), 1)
            self.assertFalse((destination / MANIFEST_NAME).exists())


if __name__ == "__main__":
    unittest.main()
