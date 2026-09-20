#!/usr/bin/env python3
"""Fetch the server's model weights, verifying what arrives.

Two of the three models fetch themselves from durable, versioned homes the
first time they are used: Demucs and Beat This! both publish weights their own
libraries download and cache. Neither needs anything here.

LarsNet does not. Its checkpoints are published as a 562 MB zip on Google
Drive and nowhere else, which is neither durable nor verifiable: the link can
change, the file can be replaced, and a quota-limited HTML error page
downloads with a 200 status and looks like a file. So this fetches from a
CONFIGURABLE source, defaults to the official one, and refuses anything whose
digest does not match what the operator expects.

Point --url at your own mirror to make this reproducible. The checkpoints are
CC BY-NC 4.0, so you may keep a private copy for non-commercial use but should
read that licence before redistributing them or building a product on them.
"""
from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path
from urllib.request import urlopen

# The official Google Drive id, as published in the LarsNet README.
LARSNET_DRIVE_ID = "1U8-5924B1ii1cjv9p0MTPzayb00P4qoL"
STEMS = ("kick", "snare", "toms", "hihat", "cymbals")


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, target: Path) -> None:
    if "drive.google.com" in url or url == LARSNET_DRIVE_ID:
        try:
            import gdown
        except ImportError:
            raise SystemExit(
                "Google Drive downloads need gdown (pip install gdown), or pass\n"
                "--url pointing at a mirror this script can fetch directly.")
        gdown.download(id=LARSNET_DRIVE_ID if url == LARSNET_DRIVE_ID else None,
                       url=None if url == LARSNET_DRIVE_ID else url,
                       output=str(target), quiet=False)
        return
    with urlopen(url, timeout=600) as response, target.open("wb") as out:
        shutil.copyfileobj(response, out)


def installed(root: Path) -> list[str]:
    """Which stem checkpoints are present under a LarsNet checkout."""
    found = []
    for stem in STEMS:
        if list((root / "pretrained_larsnet_models" / stem).glob("*.pth")):
            found.append(stem)
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--larsnet-root", type=Path, required=True,
                        help="a checkout of github.com/polimi-ispl/larsnet")
    parser.add_argument("--url", default=LARSNET_DRIVE_ID,
                        help="where to fetch the checkpoint zip; default is the official "
                             "Google Drive id. Point this at your own mirror for a "
                             "reproducible install.")
    parser.add_argument("--sha256", default=None,
                        help="expected digest of the zip. Without it the download is "
                             "reported but not verified.")
    parser.add_argument("--check", action="store_true",
                        help="report what is installed and exit")
    args = parser.parse_args(argv)

    root = args.larsnet_root
    if not (root / "config.yaml").is_file():
        print("not a LarsNet checkout: %s" % root, file=sys.stderr)
        return 2

    present = installed(root)
    if args.check:
        print("larsnet stems installed: %s" % (", ".join(present) if present else "none"))
        return 0 if len(present) == len(STEMS) else 1
    if len(present) == len(STEMS):
        print("all five stem checkpoints already present")
        return 0

    archive = root / "larsnet_models.zip"
    if not archive.is_file():
        print("fetching checkpoints from %s" % args.url)
        download(args.url, archive)
    if not archive.is_file() or archive.stat().st_size < 1 << 20:
        print("download did not produce a usable file; Google Drive quota pages arrive\n"
              "with a 200 status and look like a download", file=sys.stderr)
        return 1

    found = digest(archive)
    if args.sha256 and found.lower() != args.sha256.lower():
        print("digest mismatch:\n  expected %s\n  got      %s" % (args.sha256, found), file=sys.stderr)
        return 1
    print("archive sha256: %s" % found)
    if not args.sha256:
        print("  (pass --sha256 with this value to pin the download next time)")

    try:
        with zipfile.ZipFile(archive) as bundle:
            # Refuse paths that would escape the checkout.
            for name in bundle.namelist():
                target = (root / name).resolve()
                if root.resolve() not in target.parents and target != root.resolve():
                    print("archive contains an unsafe path: %s" % name, file=sys.stderr)
                    return 1
            bundle.extractall(root)
    except zipfile.BadZipFile:
        print("downloaded file is not a zip; the source may have returned an error page",
              file=sys.stderr)
        return 1

    present = installed(root)
    missing = [stem for stem in STEMS if stem not in present]
    if missing:
        print("still missing after extraction: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    print("installed all five stem checkpoints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
