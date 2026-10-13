"""Complete saved-project content oracle, independent of Lua serialization order."""
import hashlib
import subprocess
from pathlib import Path


def project_digest(path, source):
    """Characterisation: complete decoded content, independent of Lua table order."""
    canonical = subprocess.check_output([
        'lua5.3', str(Path(__file__).with_suffix('.lua')),
        source, str(path),
    ])
    return hashlib.sha256(canonical).hexdigest()
