#!/usr/bin/env python3
"""Descarga reproducible de fuentes oficiales chilenas para el estudio de autismo.

Los datos grandes se guardan en el almacén externo compartido y nunca en Git.
El catálogo declarativo vive junto a este archivo en ``source_catalog.json``.
"""
from __future__ import annotations

import argparse
import base64
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
import fcntl
import hashlib
from html import unescape
import http.cookiejar
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sys
import time
from typing import Any, Iterable
import urllib.error
import urllib.parse
import urllib.request
import zipfile


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_CATALOG = SCRIPT_DIR / "source_catalog.json"
DEFAULT_DATA_ROOT = Path("/Volumes/Datos/Asesorias_Data")
DEFAULT_VOLUME = Path("/Volumes/Datos")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140 Safari/537.36"
)
MANIFEST_FIELDS = [
    "catalog_date",
    "dataset_id",
    "provider",
    "downloaded_at_utc",
    "status",
    "storage",
    "relative_path",
    "bytes",
    "sha256",
    "source_url",
    "resolved_url",
    "landing_url",
    "remote_size",
    "remote_etag",
    "remote_last_modified",
    "remote_checksum",
]


@dataclass(frozen=True)
class Artifact:
    dataset_id: str
    provider: str
    storage: str
    relative_path: Path
    url: str
    landing_url: str
    large: bool
    year: int | None = None
    skip_if: Path | None = None
    remote_size: int | None = None
    remote_etag: str = ""
    remote_last_modified: str = ""
    remote_checksum: str = ""


@dataclass(frozen=True)
class Probe:
    size: int | None
    resolved_url: str
    etag: str
    last_modified: str


def _log(message: str = "") -> None:
    print(message, flush=True)


def _human_size(value: int | None) -> str:
    if value is None:
        return "tamaño desconocido"
    number = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if number < 1024 or unit == "TiB":
            return f"{number:.0f} {unit}" if unit == "B" else f"{number:.1f} {unit}"
        number /= 1024
    return f"{number:.1f} TiB"


def _normalise_url(url: str) -> str:
    """Codifica Unicode sin volver a codificar escapes existentes."""
    return urllib.parse.quote(url, safe=":/?&=%#;,+@[]!")


def _safe_relative_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Ruta insegura en el catálogo: {value!s}")
    return path


def _safe_join(root: Path, relative: str | Path) -> Path:
    relative_path = _safe_relative_path(relative)
    root_resolved = root.expanduser().resolve()
    candidate = (root_resolved / relative_path).resolve(strict=False)
    try:
        candidate.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"El destino sale de la raíz autorizada: {relative_path}") from exc
    return candidate


def load_catalog(path: Path = DEFAULT_CATALOG) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        catalog = json.load(handle)
    if catalog.get("schema_version") != 1:
        raise ValueError("Versión de catálogo no compatible")
    sources = catalog.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("El catálogo no contiene fuentes")
    ids = [source.get("id") for source in sources]
    if any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("Todas las fuentes necesitan un id")
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    if duplicates:
        raise ValueError(f"Ids duplicados: {', '.join(duplicates)}")
    valid_kinds = {"annual", "direct", "ckan", "gcs", "existing", "manual", "restricted"}
    valid_access = {"automatic", "existing_only", "manual", "restricted"}
    for source in sources:
        if source.get("kind") not in valid_kinds:
            raise ValueError(f"Tipo inválido en {source['id']}: {source.get('kind')}")
        if source.get("access") not in valid_access:
            raise ValueError(f"Acceso inválido en {source['id']}: {source.get('access')}")
        if source.get("storage") not in {"shared", "project"}:
            raise ValueError(f"Almacenamiento inválido en {source['id']}")
        _safe_relative_path(source["destination"])
        if source.get("access") == "automatic":
            for url in _catalog_urls(source):
                if not url.startswith("https://"):
                    raise ValueError(f"La fuente {source['id']} no usa HTTPS: {url}")
    return catalog


def _catalog_urls(source: dict[str, Any]) -> Iterable[str]:
    if source.get("url_template"):
        yield str(source["url_template"])
    for resource in source.get("resources", []):
        if resource.get("url"):
            yield str(resource["url"])


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_file(
    path: Path,
    full_archive_check: bool = False,
    *,
    expected_name: str | None = None,
) -> None:
    """Detecta páginas de error y contenedores corruptos antes del reemplazo."""
    if not path.is_file():
        raise FileNotFoundError("no existe")
    if path.stat().st_size == 0:
        raise ValueError("archivo vacío")
    with path.open("rb") as handle:
        head = handle.read(512)
    low = head.lstrip().lower()
    if low.startswith((b"<!doctype html", b"<html", b"<?xml")):
        raise ValueError("el servidor devolvió HTML/XML en vez del archivo")

    # Las descargas se validan mientras aún llevan el sufijo temporal ``.part``.
    # ``expected_name`` impide que ese detalle desactive los controles de formato.
    name = (expected_name or path.name).lower()
    if expected_name is None and name.endswith(".part"):
        name = name[: -len(".part")]
    if name.endswith(".pdf") and not head.startswith(b"%PDF"):
        raise ValueError("firma PDF inválida")
    if name.endswith(".rar") and not head.startswith(b"Rar!"):
        raise ValueError("firma RAR inválida")
    if name.endswith(".xls") and not head.startswith(bytes.fromhex("d0cf11e0")):
        raise ValueError("firma XLS inválida")
    if name.endswith((".zip", ".xlsx")):
        if not head.startswith(b"PK"):
            raise ValueError("firma ZIP/XLSX inválida")
        with zipfile.ZipFile(path) as archive:
            members = archive.infolist()
            if not members:
                raise ValueError("contenedor ZIP vacío")
            if full_archive_check:
                bad = archive.testzip()
                if bad:
                    raise ValueError(f"CRC inválido en {bad}")


def verify_remote_checksum(path: Path, checksum: str) -> bool:
    """Verifica checksums remotos inequívocos; retorna False si no se reconoce."""
    value = checksum.strip()
    if not value:
        return False
    algorithm = ""
    expected = ""
    if ":" in value:
        prefix, candidate = value.split(":", 1)
        if prefix.lower() in {"md5", "sha256"}:
            algorithm, expected = prefix.lower(), candidate.strip().lower()
        elif prefix.lower() == "md5-base64":
            algorithm = "md5"
            try:
                expected = base64.b64decode(candidate).hex()
            except Exception as exc:
                raise ValueError("checksum MD5 base64 inválido") from exc
        else:
            return False
    elif re.fullmatch(r"[0-9a-fA-F]{32}", value):
        algorithm, expected = "md5", value.lower()
    elif re.fullmatch(r"[0-9a-fA-F]{64}", value):
        algorithm, expected = "sha256", value.lower()
    else:
        return False
    if not re.fullmatch(r"[0-9a-f]+", expected):
        raise ValueError(f"checksum {algorithm} remoto inválido")
    digest = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    if digest.hexdigest().lower() != expected:
        raise ValueError(f"checksum {algorithm} no coincide con la fuente")
    return True


class RangeResponseError(IOError):
    """El servidor respondió un rango distinto del solicitado."""


class IntegrityError(IOError):
    """El archivo completo no coincide con su formato o checksum esperado."""


def _parse_content_range(value: str) -> tuple[int, int, int | None]:
    match = re.fullmatch(r"bytes\s+(\d+)-(\d+)/(\d+|\*)", value.strip(), re.IGNORECASE)
    if not match:
        raise RangeResponseError(f"Content-Range inválido: {value!r}")
    start, end = int(match.group(1)), int(match.group(2))
    if end < start:
        raise RangeResponseError(f"Content-Range invertido: {value!r}")
    total = None if match.group(3) == "*" else int(match.group(3))
    if total is not None and end >= total:
        raise RangeResponseError(f"Content-Range excede el tamaño: {value!r}")
    return start, end, total


def _resume_identity(artifact: Artifact, probe: Probe, expected: int) -> dict[str, Any]:
    return {
        "source_url": artifact.url,
        "expected_bytes": expected,
        "etag": probe.etag,
        "last_modified": probe.last_modified,
    }


def _strong_etag(value: str) -> str:
    """Retorna un entity-tag fuerte y bien formado, o cadena vacía."""
    candidate = value.strip()
    if candidate.startswith("W/"):
        return ""
    if not re.fullmatch(r'"[\x21\x23-\x7e\x80-\uffff]*"', candidate):
        return ""
    return candidate


def _resume_metadata_matches(saved: dict[str, Any], current: dict[str, Any]) -> bool:
    if saved.get("source_url") != current.get("source_url"):
        return False
    if int(saved.get("expected_bytes") or -1) != int(current.get("expected_bytes") or -1):
        return False
    # If-Range solo admite un entity-tag fuerte. Un ETag W/ o una fecha no
    # bastan para combinar bytes de dos solicitudes con seguridad.
    etag = _strong_etag(str(current.get("etag") or ""))
    return bool(etag and saved.get("etag") == etag)


def _validate_complete_artifact(
    path: Path,
    artifact: Artifact,
    destination: Path,
    *,
    full_archive_check: bool,
) -> None:
    try:
        validate_file(
            path,
            full_archive_check=full_archive_check,
            expected_name=destination.name,
        )
        verify_remote_checksum(path, artifact.remote_checksum)
    except Exception as exc:
        raise IntegrityError(str(exc)) from exc


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    temporary = Path(str(path) + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    os.replace(temporary, path)


def _acquire_run_lock(path: Path):
    """Serializa descargadores que comparten destinos y manifiesto."""
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a+", encoding="utf-8")
    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
    handle.seek(0)
    handle.truncate()
    handle.write(
        json.dumps(
            {"pid": os.getpid(), "started_at_utc": datetime.now(timezone.utc).isoformat()}
        )
    )
    handle.flush()
    return handle


def _release_run_lock(handle) -> None:
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


class HTTPClient:
    def __init__(self, retries: int = 4) -> None:
        self.retries = retries
        jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self._fonasa_primed = False

    def _prime_fonasa(self) -> None:
        if self._fonasa_primed:
            return
        self._fonasa_primed = True
        request = urllib.request.Request(
            "https://datosabiertos.fonasa.cl/dimensiones-beneficiarios/",
            headers={"User-Agent": USER_AGENT, "Accept-Language": "es-CL,es;q=0.9"},
        )
        try:
            with self.opener.open(request, timeout=45) as response:
                response.read(1)
        except Exception:
            # La descarga posterior conserva su propio diagnóstico y reintentos.
            pass

    def open(self, url: str, headers: dict[str, str] | None = None, timeout: int = 120):
        if "fonasa.cl/assets/" in url:
            self._prime_fonasa()
        merged = {
            "User-Agent": USER_AGENT,
            "Accept": "*/*",
            "Accept-Encoding": "identity",
            "Accept-Language": "es-CL,es;q=0.9,en;q=0.7",
        }
        if "fonasa.cl/assets/" in url:
            merged["Referer"] = "https://datosabiertos.fonasa.cl/dimensiones-beneficiarios/"
        if headers:
            merged.update(headers)
        request = urllib.request.Request(_normalise_url(url), headers=merged)
        return self.opener.open(request, timeout=timeout)

    def get_json(self, url: str) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with self.open(url, timeout=60) as response:
                    return json.load(response)
            except Exception as exc:  # red remota: se informa tras agotar reintentos
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 20))
        raise RuntimeError(f"No se pudo leer {url}: {last_error}")

    def probe(self, url: str) -> Probe:
        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            try:
                with self.open(url, headers={"Range": "bytes=0-0"}, timeout=60) as response:
                    response.read(1)
                    headers = response.headers
                    resolved_url = response.geturl()
                    if urllib.parse.urlsplit(resolved_url).scheme.lower() != "https":
                        raise RuntimeError(f"redirección no segura: {resolved_url}")
                    status = getattr(response, "status", response.getcode())
                    content_range = headers.get("Content-Range", "")
                    size: int | None = None
                    if status == 206:
                        start, _, total = _parse_content_range(content_range)
                        if start != 0 or total is None:
                            raise RangeResponseError(
                                f"sondeo remoto no comenzó en cero: {content_range!r}"
                            )
                        size = total
                    elif status == 200 and headers.get("Content-Length", "").isdigit():
                        size = int(headers["Content-Length"])
                    elif status != 200:
                        raise IOError(f"respuesta HTTP inesperada al sondear: {status}")
                    return Probe(
                        size=size,
                        resolved_url=resolved_url,
                        etag=headers.get("ETag", ""),
                        last_modified=headers.get("Last-Modified", ""),
                    )
            except Exception as exc:
                last_error = exc
                if attempt < self.retries:
                    time.sleep(min(2**attempt, 20))
        raise RuntimeError(f"No se pudo consultar {url}: {last_error}")

    def download(
        self,
        artifact: Artifact,
        destination: Path,
        *,
        refresh: bool,
        full_archive_check: bool,
    ) -> tuple[Probe, str]:
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = Path(str(destination) + ".part")
        partial_metadata = Path(str(destination) + ".part.json")
        if refresh:
            partial.unlink(missing_ok=True)
            partial_metadata.unlink(missing_ok=True)

        probe = self.probe(artifact.url)
        expected = artifact.remote_size or probe.size
        if artifact.remote_size and probe.size and artifact.remote_size != probe.size:
            raise RuntimeError(
                "el tamaño del catálogo remoto no coincide con el servidor "
                f"({_human_size(artifact.remote_size)} vs {_human_size(probe.size)})"
            )
        if expected is None:
            raise RuntimeError("el servidor no informa tamaño; no es posible validar integridad")

        identity = _resume_identity(artifact, probe, expected)
        if partial.exists():
            try:
                saved_identity = json.loads(partial_metadata.read_text(encoding="utf-8"))
            except Exception:
                saved_identity = {}
            if not _resume_metadata_matches(saved_identity, identity):
                partial.unlink(missing_ok=True)
                partial_metadata.unlink(missing_ok=True)
        elif partial_metadata.exists():
            partial_metadata.unlink()

        free = shutil.disk_usage(destination.parent).free
        remaining = max(0, expected - (partial.stat().st_size if partial.exists() else 0))
        if free < remaining + max(100 * 1024 * 1024, int(expected * 0.05)):
            raise OSError(
                f"espacio insuficiente: se necesitan al menos {_human_size(remaining)}, "
                f"hay {_human_size(free)} libres"
            )
        if partial.exists() and partial.stat().st_size > expected:
            partial.unlink()
            partial_metadata.unlink(missing_ok=True)

        last_error: Exception | None = None
        for attempt in range(1, self.retries + 1):
            offset = partial.stat().st_size if partial.exists() else 0
            if not partial_metadata.exists():
                _write_json_atomic(partial_metadata, identity)
            if offset == expected:
                try:
                    _validate_complete_artifact(
                        partial,
                        artifact,
                        destination,
                        full_archive_check=full_archive_check,
                    )
                    digest = sha256_file(partial)
                    os.replace(partial, destination)
                    partial_metadata.unlink(missing_ok=True)
                    return probe, digest
                except Exception as exc:
                    last_error = exc
                    partial.unlink(missing_ok=True)
                    partial_metadata.unlink(missing_ok=True)
                    offset = 0
                    _write_json_atomic(partial_metadata, identity)
            strong_etag = _strong_etag(probe.etag)
            if offset and not strong_etag:
                partial.unlink(missing_ok=True)
                partial_metadata.unlink(missing_ok=True)
                offset = 0
                _write_json_atomic(partial_metadata, identity)
            headers: dict[str, str] = {}
            if offset:
                headers["Range"] = f"bytes={offset}-"
                headers["If-Range"] = strong_etag
            try:
                with self.open(artifact.url, headers=headers, timeout=300) as response:
                    status = getattr(response, "status", response.getcode())
                    if status not in {200, 206}:
                        raise IOError(f"respuesta HTTP inesperada: {status}")
                    response_bytes: int | None = None
                    if status == 206:
                        if "Range" not in headers:
                            raise RangeResponseError("el servidor envió 206 sin haberse solicitado Range")
                        range_start, range_end, range_total = _parse_content_range(
                            response.headers.get("Content-Range", "")
                        )
                        if range_start != offset:
                            raise RangeResponseError(
                                f"el servidor inició en {range_start}, se solicitó {offset}"
                            )
                        if range_total is None or range_total != expected:
                            raise RangeResponseError(
                                f"el servidor informó {_human_size(range_total)}, "
                                f"se esperaban {_human_size(expected)}"
                            )
                        response_etag = response.headers.get("ETag", "")
                        if response_etag and response_etag != strong_etag:
                            raise RangeResponseError(
                                "el ETag de la respuesta parcial no coincide con If-Range"
                            )
                        response_bytes = range_end - range_start + 1
                    append = bool(offset and status == 206)
                    mode = "ab" if append else "wb"
                    if offset and not append:
                        offset = 0
                        probe = Probe(
                            size=expected,
                            resolved_url=response.geturl(),
                            etag=response.headers.get("ETag", "") or probe.etag,
                            last_modified=response.headers.get("Last-Modified", "")
                            or probe.last_modified,
                        )
                    total_written = offset
                    written_this_response = 0
                    next_report = total_written + 256 * 1024 * 1024
                    with partial.open(mode) as handle:
                        while True:
                            block = response.read(1024 * 1024)
                            if not block:
                                break
                            handle.write(block)
                            total_written += len(block)
                            written_this_response += len(block)
                            if total_written >= next_report:
                                _log(
                                    f"      {_human_size(total_written)}"
                                    + (f" / {_human_size(expected)}" if expected else "")
                                )
                                next_report += 256 * 1024 * 1024
                    if response_bytes is not None and written_this_response != response_bytes:
                        raise RangeResponseError(
                            "el cuerpo HTTP no coincide con Content-Range: "
                            f"{written_this_response} vs {response_bytes} bytes"
                        )
                if partial.stat().st_size != expected:
                    raise IOError(
                        f"descarga incompleta: {_human_size(partial.stat().st_size)} "
                        f"de {_human_size(expected)}"
                    )
                _validate_complete_artifact(
                    partial,
                    artifact,
                    destination,
                    full_archive_check=full_archive_check,
                )
                digest = sha256_file(partial)
                os.replace(partial, destination)
                partial_metadata.unlink(missing_ok=True)
                return probe, digest
            except Exception as exc:
                last_error = exc
                if isinstance(exc, (RangeResponseError, IntegrityError)) or (
                    isinstance(exc, urllib.error.HTTPError) and exc.code == 416
                ):
                    partial.unlink(missing_ok=True)
                    partial_metadata.unlink(missing_ok=True)
                if attempt < self.retries:
                    _log(f"      reintento {attempt}/{self.retries}: {str(exc)[:120]}")
                    time.sleep(min(2**attempt, 20))
        raise RuntimeError(f"descarga fallida tras {self.retries} intentos: {last_error}")


class Manifest:
    def __init__(self, path: Path, catalog_date: str) -> None:
        self.path = path
        self.catalog_date = catalog_date

    def append(
        self,
        artifact: Artifact,
        destination: Path,
        storage_root: Path,
        *,
        status: str,
        digest: str,
        probe: Probe | None,
    ) -> None:
        relative = destination.relative_to(storage_root).as_posix()
        rows: list[dict[str, str]] = []
        if self.path.is_file():
            with self.path.open(newline="", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
        if any(
            row.get("dataset_id") == artifact.dataset_id
            and row.get("storage") == artifact.storage
            and row.get("relative_path") == relative
            and row.get("sha256") == digest
            for row in rows
        ):
            return
        row = {
            "catalog_date": self.catalog_date,
            "dataset_id": artifact.dataset_id,
            "provider": artifact.provider,
            "downloaded_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "storage": artifact.storage,
            "relative_path": relative,
            "bytes": str(destination.stat().st_size),
            "sha256": digest,
            "source_url": artifact.url,
            "resolved_url": probe.resolved_url if probe else artifact.url,
            "landing_url": artifact.landing_url,
            "remote_size": str((artifact.remote_size or (probe.size if probe else None)) or ""),
            "remote_etag": artifact.remote_etag or (probe.etag if probe else ""),
            "remote_last_modified": artifact.remote_last_modified or (
                probe.last_modified if probe else ""
            ),
            "remote_checksum": artifact.remote_checksum,
        }
        rows.append(row)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = Path(str(self.path) + ".tmp")
        with temporary.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=MANIFEST_FIELDS)
            writer.writeheader()
            writer.writerows({field: item.get(field, "") for field in MANIFEST_FIELDS} for item in rows)
        os.replace(temporary, self.path)


def _year_range(source: dict[str, Any], selected_years: tuple[int, int] | None) -> list[int]:
    years = list(range(int(source["year_start"]), int(source["year_end"]) + 1))
    if selected_years:
        years = [year for year in years if selected_years[0] <= year <= selected_years[1]]
    return years


def _artifact_from_resource(
    source: dict[str, Any], resource: dict[str, Any], relative_path: Path
) -> Artifact:
    url = str(resource["url"])
    if urllib.parse.urlsplit(url).scheme.lower() != "https":
        raise ValueError(f"La fuente dinámica {source['id']} no usa HTTPS: {url}")
    size_value = resource.get("size")
    try:
        size = int(size_value) if size_value not in (None, "") else None
    except (TypeError, ValueError):
        size = None
    return Artifact(
        dataset_id=source["id"],
        provider=source["provider"],
        storage=source["storage"],
        relative_path=relative_path,
        url=url,
        landing_url=source.get("landing_url", ""),
        large=bool(source.get("large")),
        year=int(resource["year"]) if resource.get("year") is not None else None,
        skip_if=(
            _safe_relative_path(resource["skip_if"])
            if resource.get("skip_if")
            else None
        ),
        remote_size=size,
        remote_etag=str(resource.get("etag") or ""),
        remote_last_modified=str(resource.get("last_modified") or ""),
        remote_checksum=str(resource.get("checksum") or resource.get("hash") or ""),
    )


def resolve_source(
    source: dict[str, Any],
    client: HTTPClient,
    selected_years: tuple[int, int] | None,
) -> list[Artifact]:
    destination = _safe_relative_path(source["destination"])
    kind = source["kind"]
    artifacts: list[Artifact] = []

    if kind == "annual":
        extension_map = source.get("extension_by_year", {})
        for year in _year_range(source, selected_years):
            extension = extension_map.get(str(year), "zip")
            values = {"year": year, "ext": extension}
            filename = source["filename_template"].format(**values)
            relative = destination / _safe_relative_path(filename)
            skip_if = None
            if source.get("skip_if_template"):
                skip_if = _safe_relative_path(source["skip_if_template"].format(**values))
            artifacts.append(
                Artifact(
                    dataset_id=source["id"],
                    provider=source["provider"],
                    storage=source["storage"],
                    relative_path=relative,
                    url=source["url_template"].format(**values),
                    landing_url=source.get("landing_url", ""),
                    large=bool(source.get("large")),
                    year=year,
                    skip_if=skip_if,
                )
            )
        return artifacts

    if kind == "direct":
        for resource in source.get("resources", []):
            year = resource.get("year")
            if selected_years and year is not None and not (
                selected_years[0] <= int(year) <= selected_years[1]
            ):
                continue
            filename = _safe_relative_path(resource["filename"])
            artifacts.append(_artifact_from_resource(source, resource, destination / filename))
        return artifacts

    if kind == "ckan":
        dataset_id = urllib.parse.quote(str(source["ckan_id"]), safe="")
        api = f"https://datos.gob.cl/api/3/action/package_show?id={dataset_id}"
        payload = client.get_json(api)
        if not payload.get("success"):
            raise RuntimeError(f"CKAN no pudo resolver {source['ckan_id']}")
        resources = payload["result"].get("resources", [])
        for selector in source.get("resource_selectors", []):
            pattern = re.compile(selector["name_regex"], re.IGNORECASE)
            matches = [item for item in resources if pattern.search(str(item.get("name", "")))]
            if len(matches) != 1:
                raise RuntimeError(
                    f"{source['id']}: selector {selector['name_regex']!r} encontró {len(matches)} recursos"
                )
            item = matches[0]
            resource = {
                "url": item["url"],
                "filename": selector["filename"],
                "size": item.get("size"),
                "last_modified": item.get("last_modified") or item.get("created"),
                "hash": item.get("hash"),
            }
            artifacts.append(
                _artifact_from_resource(
                    source, resource, destination / _safe_relative_path(selector["filename"])
                )
            )
        return artifacts

    if kind == "gcs":
        bucket = str(source["bucket"])
        api = f"https://storage.googleapis.com/storage/v1/b/{urllib.parse.quote(bucket)}/o"
        items: list[dict[str, Any]] = []
        page_token = ""
        while True:
            query = {"maxResults": "1000"}
            if page_token:
                query["pageToken"] = page_token
            payload = client.get_json(api + "?" + urllib.parse.urlencode(query))
            items.extend(payload.get("items", []))
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token:
                break
        pattern = re.compile(source["include_regex"], re.IGNORECASE)
        prefix = str(source.get("strip_prefix") or "")
        for item in items:
            name = str(item.get("name") or "")
            if not pattern.search(name) or int(item.get("size") or 0) == 0:
                continue
            year_match = re.search(r"/(20\d{2})/", "/" + name)
            year = int(year_match.group(1)) if year_match else None
            if selected_years and year is not None and not (
                selected_years[0] <= year <= selected_years[1]
            ):
                continue
            stripped = name[len(prefix) :] if prefix and name.startswith(prefix) else name
            object_path = PurePosixPath(stripped)
            if object_path.is_absolute() or ".." in object_path.parts:
                raise ValueError(f"Objeto GCS inseguro: {name}")
            relative = destination.joinpath(*object_path.parts)
            checksum = ""
            if item.get("md5Hash"):
                try:
                    decoded_md5 = base64.b64decode(item["md5Hash"], validate=True)
                    if len(decoded_md5) != 16:
                        raise ValueError("longitud MD5 distinta de 16 bytes")
                    checksum = "md5:" + decoded_md5.hex()
                except Exception:
                    raise ValueError(f"{source['id']}: md5Hash GCS inválido para {name}")
            object_url = (
                f"https://storage.googleapis.com/{bucket}/"
                + urllib.parse.quote(name, safe="/")
            )
            if item.get("generation"):
                object_url += "?" + urllib.parse.urlencode({"generation": item["generation"]})
            resource = {
                "url": object_url,
                "filename": object_path.name,
                "year": year,
                "size": item.get("size"),
                "etag": item.get("etag"),
                "last_modified": item.get("updated"),
                # Objetos compuestos pueden carecer de MD5. En ese caso no se
                # etiqueta CRC32C como verificado si no hay implementación local.
                "checksum": checksum,
            }
            artifacts.append(_artifact_from_resource(source, resource, relative))
        return sorted(artifacts, key=lambda artifact: artifact.relative_path.as_posix())

    return artifacts


def select_sources(
    catalog: dict[str, Any], profile: str, dataset_ids: list[str] | None
) -> list[dict[str, Any]]:
    sources = catalog["sources"]
    by_id = {source["id"]: source for source in sources}
    if dataset_ids:
        unknown = [item for item in dataset_ids if item not in by_id]
        if unknown:
            raise ValueError(f"Fuentes desconocidas: {', '.join(unknown)}")
        return [by_id[item] for item in dataset_ids]
    groups = set(catalog["profiles"][profile])
    return [source for source in sources if groups.intersection(source.get("groups", []))]


def list_sources(sources: list[dict[str, Any]]) -> None:
    for source in sources:
        size_flag = " · GRANDE" if source.get("large") else ""
        groups = ",".join(source.get("groups", []))
        _log(
            f"{source['id']:<30} {source['access']:<13} [{groups}]{size_flag}\n"
            f"  {source['label']} · {source.get('coverage', 'sin cobertura declarada')}"
        )


def audit_shared_data(
    catalog: dict[str, Any],
    data_root: Path,
    selected_years: tuple[int, int] | None,
    source_ids: set[str] | None = None,
    project_root: Path | None = None,
) -> int:
    # Normalise aliases such as macOS' /var -> /private/var before comparing paths.
    data_root = data_root.expanduser().resolve()
    project_root = (project_root or data_root).expanduser().resolve()
    missing_required = 0
    applicable = 0
    _log(f"Auditoría local: {data_root}")
    for check in catalog.get("audit_checks", []):
        if source_ids is not None and check.get("source_id") not in source_ids:
            continue
        audit_root = project_root if check.get("storage") == "project" else data_root
        paths: list[Path] = []
        glob_minimum: int | None = None
        if check.get("glob"):
            relative_pattern = _safe_relative_path(check["glob"])
            glob_minimum = int(check.get("min_count", 1))
            if glob_minimum < 1:
                raise ValueError(f"min_count inválido en la auditoría {check['id']}")
            for candidate in audit_root.glob(relative_pattern.as_posix()):
                resolved = candidate.resolve(strict=False)
                try:
                    resolved.relative_to(audit_root)
                except ValueError as exc:
                    raise ValueError(
                        f"La auditoría {check['id']} encontró una ruta fuera de la raíz"
                    ) from exc
                if candidate.is_file():
                    paths.append(candidate)
        elif check.get("path"):
            paths.append(_safe_join(audit_root, check["path"]))
        else:
            extension_map = check.get("extension_by_year", {})
            for year in range(int(check["year_start"]), int(check["year_end"]) + 1):
                if selected_years and not (selected_years[0] <= year <= selected_years[1]):
                    continue
                extension = extension_map.get(str(year), "")
                paths.append(
                    _safe_join(audit_root, check["template"].format(year=year, ext=extension))
                )
        if not paths and glob_minimum is None:
            continue
        applicable += 1
        found: list[Path] = []
        invalid: dict[Path, str] = {}
        for path in paths:
            try:
                validate_file(path)
                found.append(path)
            except Exception as exc:
                invalid[path] = str(exc)
        absent = [path for path in paths if path not in found]
        glob_deficit = (
            max(0, glob_minimum - len(found)) if glob_minimum is not None else 0
        )
        total_bytes = sum(path.stat().st_size for path in found)
        marker = "✓" if not absent and not glob_deficit else "✗"
        if glob_minimum is None:
            _log(
                f"  {marker} {check['label']}: {len(found)}/{len(paths)} archivo(s), "
                f"{_human_size(total_bytes)}"
            )
        else:
            _log(
                f"  {marker} {check['label']}: {len(found)} archivo(s) válido(s), "
                f"mínimo esperado={glob_minimum}, {_human_size(total_bytes)}"
            )
        for path in absent[:5]:
            detail = invalid.get(path, "no existe")
            _log(f"      falta/inválido: {path.relative_to(audit_root)} ({detail})")
        if len(absent) > 5:
            _log(f"      … y {len(absent) - 5} más")
        if check.get("required"):
            if glob_minimum is None:
                missing_required += len(absent)
            else:
                missing_required += glob_deficit
    if not applicable:
        raise ValueError("la selección y el rango de años no contienen auditorías aplicables")
    return missing_required


def _roots_from_args(args: argparse.Namespace, catalog: dict[str, Any]) -> tuple[Path, Path, bool]:
    env_data = os.environ.get("ASESORIAS_DATA_ROOT")
    env_project = os.environ.get("AUTISM_DATA_ROOT")
    data_root = Path(args.data_root or env_data or DEFAULT_DATA_ROOT).expanduser().resolve()
    project_root = Path(
        args.project_root or env_project or data_root / catalog["project_subdirectory"]
    ).expanduser().resolve()
    using_default_data_root = not (args.data_root or env_data)
    return data_root, project_root, using_default_data_root


def _ensure_write_roots(data_root: Path, project_root: Path, using_default: bool) -> None:
    if using_default and not os.path.ismount(DEFAULT_VOLUME):
        raise RuntimeError(
            f"El volumen {DEFAULT_VOLUME} no está montado. Conéctelo o defina "
            "ASESORIAS_DATA_ROOT."
        )
    if not data_root.is_dir():
        raise RuntimeError(f"No existe el almacén compartido: {data_root}")
    project_root.mkdir(parents=True, exist_ok=True)


def _artifact_paths(
    artifact: Artifact, data_root: Path, project_root: Path
) -> tuple[Path, Path, Path | None]:
    storage_root = data_root if artifact.storage == "shared" else project_root
    destination = _safe_join(storage_root, artifact.relative_path)
    skip = _safe_join(data_root, artifact.skip_if) if artifact.skip_if else None
    return storage_root, destination, skip


def build_parser(default_profile: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile",
        choices=["hospital", "context", "core", "all"],
        default=default_profile,
        help=f"conjunto de fuentes (predeterminado: {default_profile})",
    )
    parser.add_argument("--dataset", nargs="+", help="id(s) exactos; reemplaza --profile")
    parser.add_argument("--years", nargs=2, type=int, metavar=("DESDE", "HASTA"))
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--list", action="store_true", help="muestra el catálogo sin usar la red")
    mode.add_argument(
        "--audit",
        action="store_true",
        help="verifica las bases compartidas y específicas del proyecto",
    )
    mode.add_argument("--dry-run", action="store_true", help="resuelve y consulta sin escribir")
    parser.add_argument("--include-large", action="store_true", help="autoriza archivos de varios GB")
    parser.add_argument(
        "--retain-sources",
        action="store_true",
        help="baja ZIP oficiales de DEIS/REM aunque exista el canónico compartido",
    )
    parser.add_argument("--refresh", action="store_true", help="vuelve a descargar destinos existentes")
    parser.add_argument(
        "--full-archive-check",
        action="store_true",
        help="descomprime para verificar CRC de todos los miembros ZIP/XLSX",
    )
    parser.add_argument("--retries", type=int, default=4, choices=range(1, 9))
    parser.add_argument("--data-root", help="raíz compartida; reemplaza ASESORIAS_DATA_ROOT")
    parser.add_argument("--project-root", help="raíz específica; reemplaza AUTISM_DATA_ROOT")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    return parser


def main(argv: list[str] | None = None, *, default_profile: str = "core") -> int:
    parser = build_parser(default_profile)
    args = parser.parse_args(argv)
    if args.years and args.years[0] > args.years[1]:
        parser.error("--years DESDE no puede ser mayor que HASTA")
    selected_years = tuple(args.years) if args.years else None
    try:
        catalog = load_catalog(args.catalog)
        sources = select_sources(catalog, args.profile, args.dataset)
        data_root, project_root, using_default = _roots_from_args(args, catalog)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))

    if args.list:
        list_sources(sources)
        return 0
    if args.audit:
        try:
            missing = audit_shared_data(
                catalog,
                data_root,
                selected_years,
                {source["id"] for source in sources},
                project_root,
            )
        except ValueError as exc:
            parser.error(str(exc))
        return 1 if missing else 0

    _log(f"Almacén compartido: {data_root}")
    _log(f"Datos específicos de autismo: {project_root}")
    if not args.dry_run:
        try:
            _ensure_write_roots(data_root, project_root, using_default)
        except RuntimeError as exc:
            parser.error(str(exc))

    run_lock = None
    if not args.dry_run:
        run_lock = _acquire_run_lock(data_root / "metadata" / ".autism_download.lock")

    client = HTTPClient(retries=args.retries)
    manifest = Manifest(
        project_root / "metadata" / "download_manifest.csv", catalog["catalog_date"]
    )
    counts = {"downloaded": 0, "present": 0, "canonical": 0, "large": 0, "manual": 0, "failed": 0}

    for source in sources:
        _log(f"\n=== {source['id']}: {source['label']} ===")
        if source["access"] != "automatic":
            counts["manual"] += 1
            if source["access"] == "existing_only":
                _log("  Solo auditoría local: no hay URL pública reproducible documentada.")
            elif source["access"] == "restricted":
                _log("  Acceso restringido: requiere autorización o convenio; no se intenta descargar.")
            else:
                _log(f"  Selección manual requerida: {source.get('landing_url', '')}")
            _log(f"  Nota: {source.get('notes', '')}")
            continue

        if source.get("large") and not args.include_large and source["kind"] == "gcs":
            counts["large"] += 1
            _log("  Omitida: colección de varios GB; use --include-large.")
            continue
        try:
            artifacts = resolve_source(source, client, selected_years)
        except Exception as exc:
            counts["failed"] += 1
            _log(f"  ✗ no se pudo resolver el catálogo remoto: {exc}")
            continue
        if not artifacts:
            counts["failed"] += 1
            _log("  ✗ el catálogo no produjo archivos")
            continue

        for artifact in artifacts:
            storage_root, destination, skip_if = _artifact_paths(
                artifact, data_root, project_root
            )
            label = destination.name + (f" [{artifact.year}]" if artifact.year else "")
            if skip_if and skip_if.is_file() and not args.retain_sources:
                try:
                    validate_file(skip_if)
                except Exception as exc:
                    counts["failed"] += 1
                    _log(
                        f"  ✗ {label}: canónico compartido inválido ({exc}); "
                        "revíselo antes de adquirir la fuente"
                    )
                    continue
                counts["canonical"] += 1
                _log(f"  ✓ {label}: canónico compartido válido; no se duplica")
                continue
            if artifact.large and not args.include_large:
                counts["large"] += 1
                suffix = "; ya existe pero no se recorrió" if destination.is_file() else ""
                _log(f"  ↷ {label}: omitido por tamaño{suffix}; use --include-large")
                continue
            refresh = bool(args.refresh or source.get("mutable"))
            if destination.is_file() and not refresh:
                try:
                    validate_file(destination, full_archive_check=False)
                    verify_remote_checksum(destination, artifact.remote_checksum)
                    digest = sha256_file(destination)
                    counts["present"] += 1
                    _log(f"  ✓ {label}: ya existe ({_human_size(destination.stat().st_size)})")
                    if not args.dry_run:
                        manifest.append(
                            artifact,
                            destination,
                            storage_root,
                            status="adopted",
                            digest=digest,
                            probe=None,
                        )
                except Exception as exc:
                    counts["failed"] += 1
                    _log(f"  ✗ {label}: archivo existente inválido ({exc}); use --refresh")
                continue
            if args.dry_run:
                try:
                    probe = client.probe(artifact.url)
                    remote_size = artifact.remote_size or probe.size
                    _log(f"  → {label}: disponible, {_human_size(remote_size)}")
                except Exception as exc:
                    counts["failed"] += 1
                    _log(f"  ✗ {label}: {exc}")
                continue

            _log(f"  ↓ {label}")
            try:
                probe, digest = client.download(
                    artifact,
                    destination,
                    refresh=refresh,
                    full_archive_check=args.full_archive_check,
                )
                counts["downloaded"] += 1
                _log(
                    f"    ✓ {_human_size(destination.stat().st_size)} · sha256 {digest[:12]}…"
                )
                manifest.append(
                    artifact,
                    destination,
                    storage_root,
                    status="downloaded",
                    digest=digest,
                    probe=probe,
                )
            except Exception as exc:
                counts["failed"] += 1
                _log(f"    ✗ {exc}")

    _log("\n=== Resumen ===")
    _log(
        f"descargados={counts['downloaded']} · existentes={counts['present']} · "
        f"canónicos reutilizados={counts['canonical']} · grandes omitidos={counts['large']} · "
        f"manuales/restringidos={counts['manual']} · fallos={counts['failed']}"
    )
    if not args.dry_run and (counts["downloaded"] or counts["present"]):
        _log(f"Manifiesto: {manifest.path}")
    if run_lock is not None:
        _release_run_lock(run_lock)
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
