"""Run-time source and native installation identities for performance reports."""

import hashlib
import json
import re
import subprocess
import os
from pathlib import Path


def _sha256(path):
    try:
        with Path(path).open('rb') as stream:
            digest = hashlib.sha256()
            for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(chunk)
            return digest.hexdigest()
    except OSError as error:
        raise ValueError('unreadable provenance file: ' + str(path)) from error


def _hex(value, length):
    return isinstance(value, str) and re.fullmatch(r'[0-9a-f]{%d}' % length, value) is not None


def git_identity(root):
    """Record the exact commit and tracked/untracked source status at run time."""
    root = Path(root).resolve()
    revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root,
                                       text=True).strip()
    if not _hex(revision, 40):
        raise ValueError('invalid Git source revision: ' + revision)
    status = subprocess.check_output(
        ['git', 'status', '--porcelain', '--untracked-files=all'], cwd=root,
        text=True).splitlines()
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root,
                                      text=True).split('\0')
    untracked = subprocess.check_output(
        ['git', 'ls-files', '--others', '--exclude-standard', '-z'], cwd=root,
        text=True).split('\0')
    files = {}
    for name in sorted(set(tracked + untracked) - {''}):
        path = root / name
        if path.is_symlink():
            files[name] = hashlib.sha256(os.fsencode(os.readlink(path))).hexdigest()
        elif path.is_file():
            files[name] = _sha256(path)
        else:
            # Keep deleted tracked paths in the identity too.
            files[name] = None
    encoded = json.dumps(files, sort_keys=True, separators=(',', ':')).encode()
    return dict(revision=revision, status=status,
                files_sha256=hashlib.sha256(encoded).hexdigest(), file_count=len(files))


def installation_identity(path):
    """Hash an explicit install and verify every runtime file it declares."""
    path = Path(path).resolve()
    try:
        manifest = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise ValueError('unreadable installation manifest: ' + str(path)) from error
    if not isinstance(manifest, dict):
        raise ValueError('invalid installation manifest')
    for field, length in (('lock_sha256', 64), ('build_inputs_sha256', 64),
                          ('norns_revision', 40)):
        if not _hex(manifest.get(field), length):
            raise ValueError('missing installation identity: ' + field)
    source = Path(manifest.get('source', ''))
    if not source.is_absolute() or not source.is_dir():
        raise ValueError('missing native runtime source')
    binaries = manifest.get('binaries')
    interpreted = manifest.get('interpreted_files')
    if not isinstance(binaries, dict) or not binaries:
        raise ValueError('missing runtime binary inventory')
    if not isinstance(interpreted, dict) or not interpreted:
        raise ValueError('missing interpreted runtime inventory')
    for name, entry in binaries.items():
        if not isinstance(entry, dict) or not _hex(entry.get('sha256'), 64):
            raise ValueError('invalid binary runtime inventory: ' + str(name))
        target = Path(entry.get('path', ''))
        if not target.is_absolute() or _sha256(target) != entry['sha256']:
            raise ValueError('binary runtime file differs: ' + str(name))
    for relative, expected in interpreted.items():
        candidate = Path(relative)
        if candidate.is_absolute() or '..' in candidate.parts or not _hex(expected, 64):
            raise ValueError('invalid interpreted runtime inventory: ' + str(relative))
        target = (source / candidate).resolve()
        try:
            target.relative_to(source.resolve())
        except ValueError as error:
            raise ValueError('interpreted runtime path escapes source: ' + str(relative)) from error
        if _sha256(target) != expected:
            raise ValueError('interpreted runtime file differs: ' + str(relative))
    return dict(manifest_sha256=_sha256(path),
                lock_sha256=manifest['lock_sha256'],
                build_inputs_sha256=manifest['build_inputs_sha256'],
                norns_revision=manifest['norns_revision'],
                binary_count=len(binaries), interpreted_count=len(interpreted))
