"""Write the NMF drum dictionary as a plain binary the C backend can read.

The .npz is numpy's own container format, so the native backend cannot read it
without the dependency this whole exercise removes. The payload is identical:
this only changes the envelope, and test_nmf_template asserts the two agree.

Layout, little-endian throughout:
    magic   8 bytes  "RDTPL\0\0\1"
    bins    uint32
    lanes   uint32
    window  uint32
    hop     uint32
    names   lanes * 8 bytes, NUL-padded ASCII
    data    bins * lanes float32, column-major by lane
"""
import struct
import sys
from pathlib import Path

import numpy as np

MAGIC = b"RDTPL\0\0\1"
HERE = Path(__file__).resolve().parent
SOURCE = HERE / "data" / "nmf_drum_templates.npz"
TARGET = HERE / "data" / "nmf_drum_templates.bin"


def export(source=SOURCE, target=TARGET):
    with np.load(source, allow_pickle=False) as data:
        templates = np.asarray(data["templates"], dtype="<f4")
        lanes = [str(x) for x in data["lanes"]]
        window, hop = int(data["window_size"]), int(data["hop_size"])
    bins, columns = templates.shape
    if columns != len(lanes) or not np.isfinite(templates).all():
        raise ValueError("drum template dictionary is malformed")
    if any(len(name.encode()) > 8 for name in lanes):
        raise ValueError("lane names must fit in eight bytes")
    out = bytearray(MAGIC)
    out += struct.pack("<4I", bins, columns, window, hop)
    for name in lanes:
        out += name.encode().ljust(8, b"\0")
    # Column-major: every lane's spectrum is contiguous, which is the order the
    # native dictionary multiply walks.
    out += templates.T.tobytes(order="C")
    target.write_bytes(bytes(out))
    return dict(bins=bins, lanes=lanes, window=window, hop=hop, bytes=len(out))


if __name__ == "__main__":
    print(export())
