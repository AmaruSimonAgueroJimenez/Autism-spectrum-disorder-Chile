#!/usr/bin/env python3
"""Extrae de forma reproducible la Serie P desde los ZIP anuales REM.

El portal DEIS distribuye todas las series REM dentro de un ZIP anual, pero el
nombre y la carpeta de la Serie P cambian según el año. Este programa localiza
la serie sin depender de una ruta fija, valida su esquema mínimo y la deja con
un nombre canónico. También conserva el diccionario SP cuando está disponible.

Por defecto lee desde::

    /Volumes/Datos/Asesorias_Data/REM/SerieA/sources/official_zips

y escribe en::

    /Volumes/Datos/Asesorias_Data/REM/SerieP

Las variables ``AUTISM_REM_ZIP_ROOT`` y ``AUTISM_REM_SERIEP_ROOT`` permiten
cambiar esas raíces sin modificar el código. Las opciones de línea de comandos
``--source-root`` y ``--destination-root`` tienen prioridad sobre el entorno.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import os
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Iterable, Iterator, Sequence
import unicodedata
import zipfile


DEFAULT_SOURCE_ROOT = Path(
    "/Volumes/Datos/Asesorias_Data/REM/SerieA/sources/official_zips"
)
DEFAULT_DESTINATION_ROOT = Path("/Volumes/Datos/Asesorias_Data/REM/SerieP")
SOURCE_ROOT_ENV = "AUTISM_REM_ZIP_ROOT"
DESTINATION_ROOT_ENV = "AUTISM_REM_SERIEP_ROOT"
MANIFEST_NAME = "manifest_extract_rem_series_p.csv"
MANIFEST_FIELDS = [
    "year",
    "artifact_type",
    "processed_at_utc",
    "status",
    "source_zip",
    "source_member",
    "destination",
    "bytes",
    "sha256",
]
REQUIRED_COLUMNS = {
    "mes",
    "idservicio",
    "ano",
    "idestablecimiento",
    "codigoprestacion",
    "idregion",
    "idcomuna",
}
SERIES_SUFFIXES = {".csv", ".txt"}
DICTIONARY_SUFFIXES = {".xls", ".xlsx", ".xlsm"}
COPY_BLOCK_SIZE = 1024 * 1024


@dataclass(frozen=True)
class ArtifactPlan:
    """Un miembro del ZIP y su destino canónico."""

    artifact_type: str
    member: zipfile.ZipInfo
    destination: Path


def _log(message: str = "") -> None:
    print(message, flush=True)


def sha256_file(path: Path) -> str:
    """Calcula SHA-256 por bloques, sin cargar el archivo completo en memoria."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(COPY_BLOCK_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def _normalise_token(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", ascii_text.lower())


def _safe_member_name(name: str) -> PurePosixPath:
    """Valida un nombre interno sin confiar en ``ZipFile.extract``."""
    if not name or "\x00" in name or "\\" in name:
        raise ValueError(f"Ruta insegura dentro del ZIP: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or re.match(r"^[A-Za-z]:", name):
        raise ValueError(f"Ruta insegura dentro del ZIP: {name!r}")
    return path


def _validate_archive_members(archive: zipfile.ZipFile) -> None:
    """Rechaza rutas peligrosas, duplicados y enlaces simbólicos."""
    seen: set[str] = set()
    for member in archive.infolist():
        safe = _safe_member_name(member.filename)
        canonical = safe.as_posix().rstrip("/")
        if canonical in seen:
            raise ValueError(f"Miembro duplicado dentro del ZIP: {member.filename}")
        seen.add(canonical)
        unix_mode = member.external_attr >> 16
        if unix_mode and stat.S_ISLNK(unix_mode):
            raise ValueError(f"Enlace simbólico no permitido dentro del ZIP: {member.filename}")


def _series_name_year(member: zipfile.ZipInfo) -> int | None:
    basename = PurePosixPath(member.filename).name
    if Path(basename).suffix.lower() not in SERIES_SUFFIXES:
        return None
    stem = _normalise_token(Path(basename).stem)
    match = re.fullmatch(r"(?:seriep|sp)(20\d{2})?", stem)
    if not match:
        return None
    return int(match.group(1)) if match.group(1) else 0


def _select_series_member(archive: zipfile.ZipFile, year: int) -> zipfile.ZipInfo:
    candidates: list[tuple[int, zipfile.ZipInfo]] = []
    wrong_years: list[str] = []
    for member in archive.infolist():
        if member.is_dir():
            continue
        embedded_year = _series_name_year(member)
        if embedded_year is None:
            continue
        if embedded_year not in {0, year}:
            wrong_years.append(member.filename)
            continue
        score = 10 if embedded_year == year else 0
        if PurePosixPath(member.filename).parent.name.lower() == "datos":
            score += 2
        if Path(member.filename).suffix.lower() == ".csv":
            score += 1
        candidates.append((score, member))
    if not candidates:
        detail = f"; candidatos de otro año: {', '.join(wrong_years)}" if wrong_years else ""
        raise ValueError(f"No se encontró la Serie P correspondiente a {year}{detail}")
    top_score = max(score for score, _ in candidates)
    selected = [member for score, member in candidates if score == top_score]
    if len(selected) != 1:
        names = ", ".join(member.filename for member in selected)
        raise ValueError(f"Serie P ambigua para {year}: {names}")
    member = selected[0]
    if member.file_size <= 0:
        raise ValueError(f"La Serie P está vacía dentro del ZIP: {member.filename}")
    if member.flag_bits & 0x1:
        raise ValueError(f"La Serie P está cifrada: {member.filename}")
    return member


def _dictionary_score(member: zipfile.ZipInfo, year: int) -> int | None:
    basename = PurePosixPath(member.filename).name
    if Path(basename).suffix.lower() not in DICTIONARY_SUFFIXES:
        return None
    tokens = [
        _normalise_token(token)
        for token in re.split(r"[^A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]+", Path(basename).stem)
        if token
    ]
    if "sp" not in tokens:
        return None
    normalised = _normalise_token(Path(basename).stem)
    if "diccionario" not in normalised and "codigo" not in normalised:
        if not normalised.startswith("sp"):
            return None
    score = 0
    if str(year) in tokens:
        score += 10
    if f"{year % 100:02d}" in tokens:
        score += 6
    if "diccionario" in normalised:
        score += 2
    if PurePosixPath(member.filename).parent.name.lower().startswith("diccionario"):
        score += 1
    return score


def _select_dictionary_member(
    archive: zipfile.ZipFile, year: int
) -> zipfile.ZipInfo | None:
    candidates = [
        (score, member)
        for member in archive.infolist()
        if not member.is_dir()
        for score in [_dictionary_score(member, year)]
        if score is not None
    ]
    if not candidates:
        return None
    top_score = max(score for score, _ in candidates)
    selected = [member for score, member in candidates if score == top_score]
    if len(selected) != 1:
        names = ", ".join(member.filename for member in selected)
        raise ValueError(f"Diccionario SP ambiguo para {year}: {names}")
    member = selected[0]
    if member.file_size <= 0:
        raise ValueError(f"El diccionario SP está vacío: {member.filename}")
    if member.flag_bits & 0x1:
        raise ValueError(f"El diccionario SP está cifrado: {member.filename}")
    return member


def _decode_sample(sample: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return sample.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("No fue posible decodificar la cabecera de la Serie P")


def _validate_series_sample(sample: bytes, year: int, label: str) -> None:
    if not sample:
        raise ValueError(f"Serie P vacía: {label}")
    text = _decode_sample(sample)
    reader = csv.reader(io.StringIO(text), delimiter=";")
    header = next(reader, None)
    if not header or len(header) < len(REQUIRED_COLUMNS):
        raise ValueError(f"Cabecera inválida en la Serie P: {label}")
    normalised_header = [_normalise_token(column) for column in header]
    missing = sorted(REQUIRED_COLUMNS.difference(normalised_header))
    if missing:
        raise ValueError(
            f"Cabecera inválida en la Serie P {label}; faltan: {', '.join(missing)}"
        )
    first_row = next((row for row in reader if row and any(cell.strip() for cell in row)), None)
    if first_row is None:
        raise ValueError(f"La Serie P no contiene filas de datos: {label}")
    if len(first_row) != len(header):
        raise ValueError(f"Primera fila inconsistente en la Serie P: {label}")
    year_index = normalised_header.index("ano")
    try:
        observed_year = int(first_row[year_index].strip())
    except (ValueError, IndexError) as exc:
        raise ValueError(f"Año inválido en la primera fila de la Serie P: {label}") from exc
    if observed_year != year:
        raise ValueError(
            f"El contenido de la Serie P declara {observed_year}, no {year}: {label}"
        )


def _read_member_sample(
    archive: zipfile.ZipFile, member: zipfile.ZipInfo, limit: int = 256 * 1024
) -> bytes:
    with archive.open(member, "r") as handle:
        return handle.read(limit)


def _validate_dictionary_sample(sample: bytes, suffix: str, label: str) -> None:
    if not sample:
        raise ValueError(f"Diccionario SP vacío: {label}")
    suffix = suffix.lower()
    if suffix in {".xlsx", ".xlsm"} and not sample.startswith(b"PK"):
        raise ValueError(f"Firma inválida en el diccionario SP: {label}")
    if suffix == ".xls" and not sample.startswith(bytes.fromhex("d0cf11e0")):
        raise ValueError(f"Firma inválida en el diccionario SP: {label}")


def _validate_dictionary_file(path: Path, expected_suffix: str, label: str) -> None:
    with path.open("rb") as handle:
        sample = handle.read(512)
    _validate_dictionary_sample(sample, expected_suffix, label)
    if expected_suffix.lower() in {".xlsx", ".xlsm"}:
        try:
            with zipfile.ZipFile(path) as workbook:
                bad_member = workbook.testzip()
        except zipfile.BadZipFile as exc:
            raise ValueError(f"Libro de diccionario SP corrupto: {label}") from exc
        if bad_member:
            raise ValueError(f"Libro de diccionario SP corrupto ({bad_member}): {label}")


def _validate_series_file(path: Path, year: int) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise ValueError(f"Serie P vacía: {path}")
    with path.open("rb") as handle:
        sample = handle.read(256 * 1024)
    _validate_series_sample(sample, year, path.name)


def _hash_member(archive: zipfile.ZipFile, member: zipfile.ZipInfo) -> str:
    digest = hashlib.sha256()
    try:
        with archive.open(member, "r") as source:
            for block in iter(lambda: source.read(COPY_BLOCK_SIZE), b""):
                digest.update(block)
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ValueError(f"No se pudo verificar {member.filename}: {exc}") from exc
    return digest.hexdigest()


def _extract_member_atomic(
    archive: zipfile.ZipFile,
    plan: ArtifactPlan,
    year: int,
) -> tuple[int, str]:
    destination = plan.destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    digest = hashlib.sha256()
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".part",
            delete=False,
        ) as target:
            temporary = Path(target.name)
            with archive.open(plan.member, "r") as source:
                while True:
                    block = source.read(COPY_BLOCK_SIZE)
                    if not block:
                        break
                    target.write(block)
                    digest.update(block)
            target.flush()
            os.fsync(target.fileno())
        if plan.artifact_type == "serie_p":
            _validate_series_file(temporary, year)
        else:
            _validate_dictionary_file(
                temporary, plan.destination.suffix, plan.destination.name
            )
        size = temporary.stat().st_size
        if size != plan.member.file_size:
            raise ValueError(
                f"Tamaño extraído inconsistente para {plan.member.filename}: "
                f"{size} != {plan.member.file_size}"
            )
        temporary.chmod(0o644)
        os.replace(temporary, destination)
        temporary = None
        _fsync_directory(destination.parent)
        return size, digest.hexdigest()
    except (OSError, RuntimeError, zipfile.BadZipFile) as exc:
        raise ValueError(f"No se pudo extraer {plan.member.filename}: {exc}") from exc
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)


def _preflight_existing(
    archive: zipfile.ZipFile,
    plans: Sequence[ArtifactPlan],
    refresh: bool,
) -> dict[Path, tuple[int, str, bool]]:
    """Verifica conflictos antes de escribir el primer artefacto del año."""
    result: dict[Path, tuple[int, str, bool]] = {}
    for plan in plans:
        destination = plan.destination
        if not destination.exists():
            continue
        if not destination.is_file():
            raise FileExistsError(f"El destino existe y no es un archivo: {destination}")
        source_hash = _hash_member(archive, plan.member)
        destination_hash = sha256_file(destination)
        is_same = source_hash == destination_hash
        if not is_same and not refresh:
            raise FileExistsError(
                f"El destino ya existe con contenido distinto: {destination}. "
                "Use --refresh para reemplazarlo."
            )
        result[destination] = (plan.member.file_size, source_hash, is_same)
    return result


def _manifest_row(
    *,
    year: int,
    plan: ArtifactPlan,
    source_zip: Path,
    status: str,
    size: int,
    sha256: str,
    destination_root: Path,
) -> dict[str, str]:
    return {
        "year": str(year),
        "artifact_type": plan.artifact_type,
        "processed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "source_zip": str(source_zip.resolve()),
        "source_member": plan.member.filename,
        "destination": plan.destination.relative_to(destination_root).as_posix(),
        "bytes": str(size),
        "sha256": sha256,
    }


def process_year(
    year: int,
    source_root: Path,
    destination_root: Path,
    *,
    refresh: bool = False,
    dry_run: bool = False,
) -> list[dict[str, str]]:
    """Valida y extrae un año. Retorna las filas nuevas del manifiesto."""
    source_zip = source_root / f"SERIE_REM_{year}.zip"
    if not source_zip.is_file():
        raise FileNotFoundError(f"No existe el ZIP anual: {source_zip}")
    try:
        archive_context = zipfile.ZipFile(source_zip)
    except zipfile.BadZipFile as exc:
        raise ValueError(f"ZIP anual corrupto: {source_zip}") from exc

    with archive_context as archive:
        _validate_archive_members(archive)
        series = _select_series_member(archive, year)
        _validate_series_sample(
            _read_member_sample(archive, series), year, series.filename
        )
        plans = [
            ArtifactPlan(
                "serie_p",
                series,
                destination_root / f"SerieP_{year}.csv",
            )
        ]
        dictionary = _select_dictionary_member(archive, year)
        if dictionary is not None:
            _validate_dictionary_sample(
                _read_member_sample(archive, dictionary, 512),
                Path(dictionary.filename).suffix,
                dictionary.filename,
            )
            dictionary_name = PurePosixPath(dictionary.filename).name
            plans.append(
                ArtifactPlan(
                    "diccionario_sp",
                    dictionary,
                    destination_root / "diccionarios" / str(year) / dictionary_name,
                )
            )

        existing = _preflight_existing(archive, plans, refresh)
        if dry_run:
            for plan in plans:
                state = existing.get(plan.destination)
                if state and state[2]:
                    action = "conservar (idéntico)"
                elif state:
                    action = "reemplazar"
                else:
                    action = "extraer"
                _log(f"  [simulación] {action}: {plan.destination}")
            if dictionary is None:
                _log(f"  [simulación] {year}: el ZIP no contiene diccionario SP")
            return []

        rows: list[dict[str, str]] = []
        for plan in plans:
            state = existing.get(plan.destination)
            if state and state[2]:
                size, digest, _ = state
                status = "verificado_existente"
            else:
                size, digest = _extract_member_atomic(archive, plan, year)
                status = "actualizado" if state else "extraído"
            rows.append(
                _manifest_row(
                    year=year,
                    plan=plan,
                    source_zip=source_zip,
                    status=status,
                    size=size,
                    sha256=digest,
                    destination_root=destination_root,
                )
            )
            _log(
                f"  {status.replace('_', ' ')}: {plan.destination} "
                f"({size:,} bytes; sha256 {digest[:12]}…)"
            )
        if dictionary is None:
            _log(f"  Aviso: el ZIP {year} no contiene diccionario SP")
        return rows


def _read_manifest(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    if not path.is_file():
        raise ValueError(f"La ruta del manifiesto no es un archivo: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != MANIFEST_FIELDS:
            raise ValueError(
                f"El manifiesto existente tiene un esquema incompatible: {path}"
            )
        return [dict(row) for row in reader]


def _merge_manifest_rows(
    existing: Iterable[dict[str, str]], updates: Iterable[dict[str, str]]
) -> list[dict[str, str]]:
    keyed: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in existing:
        keyed[(row["year"], row["artifact_type"], row["destination"])] = row
    for row in updates:
        keyed[(row["year"], row["artifact_type"], row["destination"])] = row
    return sorted(
        keyed.values(),
        key=lambda row: (int(row["year"]), row["artifact_type"], row["destination"]),
    )


def _write_manifest_atomic(path: Path, rows: Sequence[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            newline="",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".part",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows(rows)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        temporary = None
        _fsync_directory(path.parent)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def parse_years(values: Sequence[str]) -> list[int]:
    """Acepta años individuales, listas con coma y rangos inclusivos."""
    years: set[int] = set()
    for value in values:
        for token in value.split(","):
            token = token.strip()
            if not token:
                continue
            range_match = re.fullmatch(r"(\d{4})\s*-\s*(\d{4})", token)
            if range_match:
                first, last = map(int, range_match.groups())
                if first > last:
                    raise ValueError(f"Rango de años invertido: {token}")
                years.update(range(first, last + 1))
            elif re.fullmatch(r"\d{4}", token):
                years.add(int(token))
            else:
                raise ValueError(f"Año o rango inválido: {token!r}")
    if not years:
        raise ValueError("No se indicó ningún año válido")
    invalid = sorted(year for year in years if year < 1900 or year > 2100)
    if invalid:
        raise ValueError(f"Años fuera de rango: {', '.join(map(str, invalid))}")
    return sorted(years)


def discover_years(source_root: Path) -> list[int]:
    years = []
    for path in source_root.glob("SERIE_REM_*.zip"):
        match = re.fullmatch(r"SERIE_REM_(\d{4})\.zip", path.name)
        if match and path.is_file():
            years.append(int(match.group(1)))
    return sorted(set(years))


@contextmanager
def _run_lock(destination_root: Path) -> Iterator[None]:
    destination_root.mkdir(parents=True, exist_ok=True)
    lock_path = destination_root / ".extract_rem_series_p.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def build_parser() -> argparse.ArgumentParser:
    source_default = Path(os.environ.get(SOURCE_ROOT_ENV, DEFAULT_SOURCE_ROOT))
    destination_default = Path(
        os.environ.get(DESTINATION_ROOT_ENV, DEFAULT_DESTINATION_ROOT)
    )
    parser = argparse.ArgumentParser(
        description=(
            "Extrae y valida la Serie P (P2/P6) y el diccionario SP desde los "
            "ZIP anuales REM ya descargados."
        )
    )
    parser.add_argument(
        "--years",
        nargs="+",
        metavar="AÑO|INICIO-FIN",
        help=(
            "Años a procesar; admite espacios, comas y rangos (ej.: "
            "--years 2019-2025 o --years 2019,2021 2024). Si se omite, "
            "descubre todos los ZIP disponibles."
        ),
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=source_default,
        help=f"Carpeta de ZIP anuales (entorno: {SOURCE_ROOT_ENV}).",
    )
    parser.add_argument(
        "--destination-root",
        type=Path,
        default=destination_default,
        help=f"Carpeta canónica de Serie P (entorno: {DESTINATION_ROOT_ENV}).",
    )
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Permite reemplazar un destino cuyo contenido difiere del ZIP.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Valida y muestra las acciones sin escribir archivos ni manifiesto.",
    )
    return parser


def _resolved_root(path: Path) -> Path:
    return path.expanduser().resolve(strict=False)


def run(args: argparse.Namespace) -> int:
    source_root = _resolved_root(args.source_root)
    destination_root = _resolved_root(args.destination_root)
    if not source_root.is_dir():
        _log(f"Error: no existe la carpeta de ZIP REM: {source_root}")
        return 2
    try:
        years = parse_years(args.years) if args.years else discover_years(source_root)
    except ValueError as exc:
        _log(f"Error: {exc}")
        return 2
    if not years:
        _log(f"Error: no se encontraron ZIP SERIE_REM_<año>.zip en {source_root}")
        return 2

    _log(f"ZIP de origen: {source_root}")
    _log(f"Destino Serie P: {destination_root}")
    _log(f"Años: {', '.join(map(str, years))}")
    if args.dry_run:
        _log("Modo simulación: no se escribirá ningún archivo.")

    manifest_path = destination_root / MANIFEST_NAME
    updates: list[dict[str, str]] = []
    failures = 0

    def process_all(existing_rows: list[dict[str, str]]) -> None:
        nonlocal failures
        for year in years:
            _log(f"\nREM {year}")
            try:
                updates.extend(
                    process_year(
                        year,
                        source_root,
                        destination_root,
                        refresh=args.refresh,
                        dry_run=args.dry_run,
                    )
                )
            except (FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
                failures += 1
                _log(f"  Error: {exc}")
        if not args.dry_run and updates:
            merged = _merge_manifest_rows(existing_rows, updates)
            _write_manifest_atomic(manifest_path, merged)

    if args.dry_run:
        process_all([])
    else:
        try:
            with _run_lock(destination_root):
                existing_rows = _read_manifest(manifest_path)
                process_all(existing_rows)
        except (ValueError, OSError) as exc:
            _log(f"Error: {exc}")
            return 2

    _log(
        f"\nResultado: {len(updates)} artefactos registrados; "
        f"{failures} año(s) con error."
    )
    return 1 if failures else 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
