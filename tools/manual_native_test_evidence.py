"""Portable access to exact retained native evidence used by offline manual tests."""
from __future__ import annotations

import atexit
import hashlib
import json
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

_ARCHIVE_SHA256 = "af6954ce3c3ed861873e4e5b49b3ab5084c6f774ef7b529d00e0e8d3278526f0"
_MANIFEST_SHA256 = "418c58b57c7c56f5ca375997e552b1b032fb173c1b22c73516dbdbd02e21c7ef"
_ARCHIVE = Path(__file__).resolve().parents[1] / "test-fixtures/manual-retained-native-evidence-v1.tar.gz"


def _sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class PortableNativeEvidence:
    """Resolve only pinned absolute source paths to identical archived bytes."""

    def __init__(self):
        archive_bytes = _ARCHIVE.read_bytes()
        if _sha_bytes(archive_bytes) != _ARCHIVE_SHA256:
            raise ValueError("retained native fixture archive digest changed")
        self._temporary = tempfile.TemporaryDirectory(prefix="manual-native-evidence-")
        self.root = Path(self._temporary.name)
        with tarfile.open(_ARCHIVE, "r:gz") as archive:
            members = archive.getmembers()
            if any(not member.isfile() for member in members):
                raise ValueError("retained native fixture contains a non-file entry")
            names = {member.name for member in members}
            manifest_member = archive.extractfile("manifest.json")
            if manifest_member is None:
                raise ValueError("retained native fixture lacks its source manifest")
            manifest_bytes = manifest_member.read()
            if _sha_bytes(manifest_bytes) != _MANIFEST_SHA256:
                raise ValueError("retained native fixture manifest digest changed")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
            if manifest.get("schema") != "mosaic-retained-native-test-fixtures-v1":
                raise ValueError("unrecognized retained native fixture schema")
            expected = set(manifest.get("files", {})) | {"manifest.json"}
            if names != expected:
                raise ValueError("retained native fixture inventory differs from its manifest")
            self._sources = {}
            for source_path, record in manifest["runs"].items():
                relative = record["archive_path"]
                if not source_path.startswith("/home/andy/mosaic-manual-runs/") or relative != "runs/" + source_path[len("/home/andy/mosaic-manual-runs/"):]:
                    raise ValueError("retained native source path does not match archive location")
                self._sources[str(Path(source_path).resolve())] = relative
            for name, record in manifest["files"].items():
                path = PurePosixPath(name)
                if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
                    raise ValueError("unsafe retained native fixture path")
                member = archive.getmember(name)
                raw_stream = archive.extractfile(member)
                if raw_stream is None:
                    raise ValueError("retained native fixture entry is unreadable")
                raw = raw_stream.read()
                if len(raw) != record["bytes"] or _sha_bytes(raw) != record["sha256"]:
                    raise ValueError("retained native fixture file digest changed: " + name)
                target = self.root.joinpath(*path.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        self._closed = False
        atexit.register(self.close)

    def resolve(self, source_path):
        key = str(Path(source_path).resolve())
        relative = self._sources.get(key)
        if relative is None:
            raise ValueError("unregistered retained native source path: " + key)
        return self.root / relative

    def close(self):
        if not self._closed:
            self._temporary.cleanup()
            self._closed = True

