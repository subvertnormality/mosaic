"""Read immutable generated-reader source fixtures from the portable archive."""
from __future__ import annotations

import hashlib
import json
import os
import tarfile
from pathlib import Path

# Tests can run from an installed checkout while importing this helper from an
# external candidate tree. Use the checkout selected by the test environment
# so the shared, installed immutable fixture archive is reused.
ROOT = Path(os.environ.get("MOSAIC_PROJECT_ROOT", Path(__file__).resolve().parents[1])).resolve()
ARCHIVE = ROOT / "test-fixtures/reader-projection-portable-v1.tar.gz"
ARCHIVE_SHA256 = "d829656150148ded99e79727c937cb494be31a2abfaf11206ecb4d34b26dc099"
BOOK_SHA256 = "b4646a9f869c5c60ed47a14585d6cd3db516b6f882c575b0e82fe3a1790ccc78"

def load_pinned_projection_book():
    archive_bytes = ARCHIVE.read_bytes()
    if hashlib.sha256(archive_bytes).hexdigest() != ARCHIVE_SHA256:
        raise ValueError("portable reader projection fixture archive changed")
    with tarfile.open(ARCHIVE, "r:gz") as source:
        member = source.extractfile("inputs/manual/generated/book.json")
        if member is None:
            raise ValueError("portable reader projection book is missing")
        data = member.read()
    if hashlib.sha256(data).hexdigest() != BOOK_SHA256:
        raise ValueError("pinned historical reader projection book changed")
    return json.loads(data.decode("utf-8"))
