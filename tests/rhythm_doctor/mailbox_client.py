"""Client half of the Rhythm Doctor file mailbox, for suites that drive a worker.

This mirrors lib/rhythm_doctor/file_mailbox.lua so the IPC tests exercise the
carrier the device actually uses.  See that module for why norns cannot hold a
socket: matron embeds Lua 5.3 with no FFI.
"""
from __future__ import annotations

import os
from pathlib import Path
import time


class MailboxClient:
    def __init__(self, root, outbound="c2w", inbound="w2c", limit=8192, claim=True):
        self.root = Path(root)
        self.outbound, self.inbound, self.limit = self.root / outbound, self.root / inbound, limit
        self.send_sequence = self.receive_sequence = 1
        if claim:
            os.replace(self.root / "claim", self.root / "claimed")
        self.heartbeat()

    def _name(self, directory: Path, sequence: int, suffix: str = "") -> Path:
        return directory / f"{sequence:09d}.msg{suffix}"

    def heartbeat(self) -> None:
        (self.root / "alive").write_bytes(b"1")

    def send(self, payload: bytes) -> None:
        partial = self._name(self.outbound, self.send_sequence, ".part")
        partial.write_bytes(payload)
        os.replace(partial, self._name(self.outbound, self.send_sequence))
        self.send_sequence += 1

    def poll(self):
        path = self._name(self.inbound, self.receive_sequence)
        try:
            payload = path.read_bytes()
        except FileNotFoundError:
            return None
        path.unlink(missing_ok=True)
        self.receive_sequence += 1
        return payload

    def receive(self, timeout: float = 3.0) -> bytes:
        deadline = time.monotonic() + timeout
        while True:
            payload = self.poll()
            if payload is not None:
                return payload
            if time.monotonic() >= deadline:
                raise TimeoutError("no mailbox record within %.1fs" % timeout)
            self.heartbeat()
            time.sleep(.005)

    def peer_present(self) -> bool:
        return (self.root / "up").exists()

    def close(self) -> None:
        """Symmetry with the socket peer it replaces; the worker owns the files."""
