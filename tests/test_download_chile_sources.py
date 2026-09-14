import csv
import base64
import hashlib
import io
import json
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

from download_chile_sources import (  # noqa: E402
    Artifact,
    HTTPClient,
    Probe,
    _parse_content_range,
    _resume_identity,
    _resume_metadata_matches,
    _roots_from_args,
    _safe_join,
    audit_shared_data,
    load_catalog,
    resolve_source,
    select_sources,
    validate_file,
    verify_remote_checksum,
)


class FakeResponse:
    def __init__(self, body, *, status=200, headers=None, url="https://example.test/data"):
        self._body = io.BytesIO(body)
        self.status = status
        self.headers = headers or {}
        self._url = url

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self, size=-1):
        return self._body.read(size)

    def getcode(self):
        return self.status

    def geturl(self):
        return self._url


class ResumeClient(HTTPClient):
    def __init__(self, response, etag='"v1"'):
        super().__init__(retries=1)
        self.response = response
        self.etag = etag
        self.request_headers = None

    def probe(self, _url):
        return Probe(6, "https://example.test/data", self.etag, "")

    def open(self, _url, headers=None, timeout=120):
        self.request_headers = headers or {}
        return self.response


class DownloadCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = load_catalog(DOWNLOAD_DIR / "source_catalog.json")

    def test_registry_and_catalog_have_the_same_ids(self):
        catalog_ids = {source["id"] for source in self.catalog["sources"]}
        with (DOWNLOAD_DIR / "source_registry.csv").open(newline="", encoding="utf-8") as handle:
            registry_ids = {row["id"] for row in csv.DictReader(handle)}
        self.assertEqual(catalog_ids, registry_ids)

    def test_profiles_do_not_duplicate_sources(self):
        for profile in self.catalog["profiles"]:
            selected = select_sources(self.catalog, profile, None)
            ids = [source["id"] for source in selected]
            self.assertEqual(len(ids), len(set(ids)), profile)

    def test_annual_extension_and_year_filter(self):
        source = next(
            source for source in self.catalog["sources"] if source["id"] == "fonasa_aggregates"
        )
        artifacts = resolve_source(source, HTTPClient(retries=1), (2020, 2020))
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0].relative_path.name, "Resultados_202012.rar")
        self.assertIn("202012.rar", artifacts[0].url)

    def test_direct_grd_resources_keep_canonical_guard(self):
        source = next(
            source for source in self.catalog["sources"] if source["id"] == "grd_publico"
        )
        artifacts = resolve_source(source, HTTPClient(retries=1), (2024, 2024))
        self.assertEqual(len(artifacts), 1)
        self.assertEqual(artifacts[0].skip_if, Path("GRD/GRD_PUBLICO_2024.csv"))

    def test_safe_join_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(ValueError):
                _safe_join(root, "../outside.csv")

    def test_validation_rejects_html_and_accepts_zip(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bad = root / "error.csv"
            bad.write_bytes(b"<!doctype html><html>Error</html>")
            with self.assertRaises(ValueError):
                validate_file(bad)
            corrupt = root / "corrupt.zip.part"
            corrupt.write_bytes(b"not a zip")
            with self.assertRaises(ValueError):
                validate_file(corrupt, full_archive_check=True)
            good = root / "data.zip.part"
            with zipfile.ZipFile(good, "w") as archive:
                archive.writestr("data.csv", "a,b\n1,2\n")
            validate_file(good, full_archive_check=True)

    def test_remote_checksum_is_enforced(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "data.csv"
            path.write_bytes(b"abc")
            expected = hashlib.md5(b"abc").hexdigest()
            self.assertTrue(verify_remote_checksum(path, f"md5:{expected}"))
            with self.assertRaises(ValueError):
                verify_remote_checksum(path, "md5:" + "0" * 32)

    def test_content_range_requires_consistent_bounds(self):
        self.assertEqual(_parse_content_range("bytes 3-5/6"), (3, 5, 6))
        with self.assertRaises(OSError):
            _parse_content_range("bytes 3-6/6")
        with self.assertRaises(OSError):
            _parse_content_range("garbage")

    def test_resume_requires_same_strong_etag(self):
        artifact = Artifact("x", "p", "project", Path("x.csv"), "https://x", "", False)
        strong = _resume_identity(artifact, Probe(6, "https://x", '"v1"', "date"), 6)
        self.assertTrue(_resume_metadata_matches(dict(strong), strong))
        weak = _resume_identity(artifact, Probe(6, "https://x", 'W/"v1"', "date"), 6)
        self.assertFalse(_resume_metadata_matches(dict(weak), weak))

    def test_bad_range_never_concatenates_a_partial(self):
        response = FakeResponse(
            b"NEW", status=206, headers={"Content-Range": "bytes 0-2/6"}
        )
        client = ResumeClient(response)
        artifact = Artifact(
            "x", "p", "project", Path("data.csv"), "https://example.test/data", "", False
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "data.csv"
            partial = Path(str(destination) + ".part")
            metadata = Path(str(destination) + ".part.json")
            partial.write_bytes(b"OLD")
            identity = _resume_identity(artifact, client.probe(artifact.url), 6)
            metadata.write_text(json.dumps(identity), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                client.download(
                    artifact, destination, refresh=False, full_archive_check=False
                )
            self.assertFalse(destination.exists())
            self.assertFalse(partial.exists())
            self.assertFalse(metadata.exists())

    def test_server_ignoring_range_restarts_from_zero(self):
        response = FakeResponse(b"NEWNEW", status=200, headers={"Content-Length": "6"})
        client = ResumeClient(response)
        artifact = Artifact(
            "x", "p", "project", Path("data.csv"), "https://example.test/data", "", False
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "data.csv"
            partial = Path(str(destination) + ".part")
            metadata = Path(str(destination) + ".part.json")
            partial.write_bytes(b"OLD")
            identity = _resume_identity(artifact, client.probe(artifact.url), 6)
            metadata.write_text(json.dumps(identity), encoding="utf-8")
            client.download(artifact, destination, refresh=False, full_archive_check=False)
            self.assertEqual(destination.read_bytes(), b"NEWNEW")

    def test_resume_sends_strong_if_range_and_appends_exact_segment(self):
        response = FakeResponse(
            b"NEW",
            status=206,
            headers={"Content-Range": "bytes 3-5/6", "ETag": '"v1"'},
        )
        client = ResumeClient(response)
        artifact = Artifact(
            "x", "p", "project", Path("data.csv"), "https://example.test/data", "", False
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "data.csv"
            partial = Path(str(destination) + ".part")
            metadata = Path(str(destination) + ".part.json")
            partial.write_bytes(b"OLD")
            metadata.write_text(
                json.dumps(_resume_identity(artifact, client.probe(artifact.url), 6)),
                encoding="utf-8",
            )
            client.download(artifact, destination, refresh=False, full_archive_check=False)
            self.assertEqual(destination.read_bytes(), b"OLDNEW")
            self.assertEqual(client.request_headers["Range"], "bytes=3-")
            self.assertEqual(client.request_headers["If-Range"], '"v1"')

    def test_weak_or_malformed_etag_never_resumes(self):
        artifact = Artifact(
            "x", "p", "project", Path("data.csv"), "https://example.test/data", "", False
        )
        for etag in ['W/"v1"', "v1", ""]:
            with self.subTest(etag=etag), tempfile.TemporaryDirectory() as temporary:
                client = ResumeClient(FakeResponse(b"NEWNEW"), etag=etag)
                destination = Path(temporary) / "data.csv"
                partial = Path(str(destination) + ".part")
                metadata = Path(str(destination) + ".part.json")
                partial.write_bytes(b"OLD")
                metadata.write_text(
                    json.dumps(_resume_identity(artifact, client.probe(artifact.url), 6)),
                    encoding="utf-8",
                )
                client.download(
                    artifact, destination, refresh=False, full_archive_check=False
                )
                self.assertEqual(destination.read_bytes(), b"NEWNEW")
                self.assertNotIn("Range", client.request_headers)
                self.assertNotIn("If-Range", client.request_headers)

    def test_complete_bad_partial_redownloads_with_one_attempt(self):
        good = b"NEWNEW"
        response = FakeResponse(good)
        client = ResumeClient(response)
        artifact = Artifact(
            "x",
            "p",
            "project",
            Path("data.csv"),
            "https://example.test/data",
            "",
            False,
            remote_checksum="md5:" + hashlib.md5(good).hexdigest(),
        )
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "data.csv"
            partial = Path(str(destination) + ".part")
            metadata = Path(str(destination) + ".part.json")
            partial.write_bytes(b"BADBAD")
            metadata.write_text(
                json.dumps(_resume_identity(artifact, client.probe(artifact.url), 6)),
                encoding="utf-8",
            )
            client.download(artifact, destination, refresh=False, full_archive_check=False)
            self.assertEqual(destination.read_bytes(), good)

    def test_partial_response_etag_or_body_mismatch_is_discarded(self):
        cases = [
            ({"Content-Range": "bytes 3-5/6", "ETag": '"v2"'}, b"NEW"),
            ({"Content-Range": "bytes 3-5/6", "ETag": '"v1"'}, b"NE"),
            ({"Content-Range": "bytes 3-5/*", "ETag": '"v1"'}, b"NEW"),
        ]
        artifact = Artifact(
            "x", "p", "project", Path("data.csv"), "https://example.test/data", "", False
        )
        for headers, body in cases:
            with self.subTest(headers=headers), tempfile.TemporaryDirectory() as temporary:
                client = ResumeClient(FakeResponse(body, status=206, headers=headers))
                destination = Path(temporary) / "data.csv"
                partial = Path(str(destination) + ".part")
                metadata = Path(str(destination) + ".part.json")
                partial.write_bytes(b"OLD")
                metadata.write_text(
                    json.dumps(_resume_identity(artifact, client.probe(artifact.url), 6)),
                    encoding="utf-8",
                )
                with self.assertRaises(RuntimeError):
                    client.download(
                        artifact, destination, refresh=False, full_archive_check=False
                    )
                self.assertFalse(destination.exists())
                self.assertFalse(partial.exists())
                self.assertFalse(metadata.exists())

    def test_probe_rejects_partial_response_without_content_range(self):
        client = HTTPClient(retries=1)
        client.open = lambda *_args, **_kwargs: FakeResponse(
            b"x", status=206, headers={"Content-Length": "1"}
        )
        with self.assertRaises(RuntimeError):
            client.probe("https://example.test/data")

    def test_gcs_md5_and_generation_are_pinned(self):
        payload = b"abc"

        class GCSClient:
            def get_json(self, _url):
                return {
                    "items": [
                        {
                            "name": "root/2024/data.csv",
                            "size": str(len(payload)),
                            "etag": '"etag"',
                            "generation": "12345",
                            "updated": "2026-01-01T00:00:00Z",
                            "md5Hash": base64.b64encode(hashlib.md5(payload).digest()).decode(),
                        }
                    ]
                }

        source = {
            "id": "gcs_test",
            "provider": "test",
            "storage": "project",
            "destination": "data",
            "kind": "gcs",
            "large": False,
            "bucket": "bucket",
            "include_regex": r"^root/2024/.+\.csv$",
            "strip_prefix": "root/",
            "landing_url": "https://example.test",
        }
        artifacts = resolve_source(source, GCSClient(), None)
        self.assertEqual(len(artifacts), 1)
        self.assertIn("generation=12345", artifacts[0].url)
        self.assertEqual(
            artifacts[0].remote_checksum, "md5:" + hashlib.md5(payload).hexdigest()
        )

    def test_audit_reports_missing_required_file(self):
        miniature = {
            "audit_checks": [
                {"id": "x", "label": "X", "path": "missing.csv", "required": True}
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            self.assertEqual(audit_shared_data(miniature, Path(temporary), None), 1)

    def test_audit_glob_enforces_minimum_valid_files(self):
        miniature = {
            "audit_checks": [
                {
                    "id": "metadata",
                    "label": "Metadata",
                    "glob": "metadata/*/*.pdf",
                    "min_count": 2,
                    "required": True,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / "metadata" / "2025"
            folder.mkdir(parents=True)
            (folder / "one.pdf").write_bytes(b"%PDF-1.4\n")
            self.assertEqual(audit_shared_data(miniature, root, None), 1)
            (folder / "two.pdf").write_bytes(b"%PDF-1.4\n")
            self.assertEqual(audit_shared_data(miniature, root, None), 0)

    def test_audit_uses_project_root_for_project_artifacts(self):
        miniature = {
            "audit_checks": [
                {
                    "id": "project",
                    "label": "Project",
                    "storage": "project",
                    "path": "survey/data.dta",
                    "required": True,
                }
            ]
        }
        with tempfile.TemporaryDirectory() as shared, tempfile.TemporaryDirectory() as project:
            project_root = Path(project)
            destination = project_root / "survey" / "data.dta"
            destination.parent.mkdir()
            destination.write_bytes(b"valid-data")
            self.assertEqual(
                audit_shared_data(
                    miniature, Path(shared), None, project_root=project_root
                ),
                0,
            )

    def test_audit_filters_sources_and_rejects_empty_year_intersection(self):
        miniature = {
            "audit_checks": [
                {
                    "id": "x",
                    "source_id": "x_source",
                    "label": "X",
                    "template": "x_{year}.csv",
                    "year_start": 2019,
                    "year_end": 2020,
                    "required": True,
                },
                {
                    "id": "y",
                    "source_id": "y_source",
                    "label": "Y",
                    "path": "y.csv",
                    "required": True,
                },
            ]
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(
                audit_shared_data(miniature, root, (2019, 2019), {"x_source"}), 1
            )
            with self.assertRaises(ValueError):
                audit_shared_data(miniature, root, (2030, 2031), {"x_source"})

    def test_project_override_does_not_disable_default_volume_guard(self):
        args = type(
            "Args",
            (),
            {"data_root": None, "project_root": None},
        )()
        with patch.dict(
            os.environ,
            {"AUTISM_DATA_ROOT": "/tmp/autism-test"},
            clear=False,
        ):
            with patch.dict(os.environ, {"ASESORIAS_DATA_ROOT": ""}, clear=False):
                _, _, using_default_data_root = _roots_from_args(
                    args, {"project_subdirectory": "Autism"}
                )
        self.assertTrue(using_default_data_root)


if __name__ == "__main__":
    unittest.main()
