"""Find an identical-input cache or one explicitly pinned prior CI recording.

Selection is not audio acceptance: the caller must run the unchanged full
audio and native-session audits before reuse, and the build repeats adoption.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.request


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_pin(pin):
    require(pin.get('schema_version') == 1, 'Unsupported audio bundle pin')
    for key in ('run_id', 'run_attempt'):
        require(type(pin.get(key)) is int and pin[key] > 0, 'Invalid ' + key)
    require(re.fullmatch('[0-9a-f]{40}', pin.get('head_sha', '')), 'Invalid source pin')
    for key in ('archive_sha256', 'tar_sha256', 'report_sha256'):
        require(re.fullmatch('[0-9a-f]{64}', pin.get(key, '')), 'Invalid ' + key)
    name = pin.get('artifact_name', '')
    require(name == 'manual-audio-' + str(pin['run_id']) or
            re.fullmatch('manual-audio-src-[0-9a-f]{40}', name), 'Invalid artifact pin')


def find_bundle(repository, identity, pin, api):
    require(re.fullmatch('[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository), 'Invalid repository')
    require(re.fullmatch('[0-9a-f]{40}', identity), 'Invalid audio identity')
    base = '/repos/' + repository + '/actions'
    name = 'manual-audio-src-' + identity
    exact = api(base + '/artifacts?per_page=20&name=' + name).get('artifacts', [])
    for artifact in exact:
        if artifact.get('name') == name and not artifact.get('expired') and artifact.get('workflow_run', {}).get('id'):
            return dict(run_id=artifact['workflow_run']['id'], artifact_name=name, pinned=False)
    if pin is None:
        return None
    validate_pin(pin)
    run_url = base + '/runs/' + str(pin['run_id'])
    artifacts = api(run_url + '/artifacts?per_page=100').get('artifacts', [])
    matches = [a for a in artifacts if a.get('name') == pin['artifact_name'] and not a.get('expired')]
    if not matches:
        return None
    require(len(matches) == 1, 'Ambiguous pinned audio artifact')
    require(matches[0].get('digest') == 'sha256:' + pin['archive_sha256'], 'Pinned archive digest changed')
    run = api(run_url)
    require(run.get('head_sha') == pin['head_sha'] and run.get('run_attempt') == pin['run_attempt'], 'Pinned producer source or attempt changed')
    require(run.get('event') == 'pull_request' and run.get('path') == '.github/workflows/manual-build.yml', 'Pinned recording has a different workflow')
    require(all(run.get(key, {}).get('full_name') == repository for key in ('repository', 'head_repository')), 'Pinned recording comes from a different repository')
    jobs = api(run_url + '/attempts/' + str(pin['run_attempt']) + '/jobs?per_page=100').get('jobs', [])
    audio = [j for j in jobs if j.get('name') == 'Record manual audio assets']
    require(len(audio) == 1 and audio[0].get('conclusion') == 'success', 'Pinned recording job did not succeed')
    return dict(run_id=pin['run_id'], artifact_name=pin['artifact_name'], pinned=True)


def verify_bundle(bundle, pin):
    validate_pin(pin)
    root = Path(bundle)
    require((root / 'report.sha256').read_text().strip() == pin['report_sha256'], 'Pinned report digest changed')
    digest = hashlib.sha256()
    with (root / 'audio.tar').open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(chunk)
    require(digest.hexdigest() == pin['tar_sha256'], 'Pinned audio evidence bytes changed')


def qualify_audio(audio_audit, session_audit):
    """A changed recording input requires fresh assets; corruption stays fatal."""
    source_mismatches = ('stale audio authoring', 'Audio schema identity',
                         'Audio harness identity', 'Audio setups identity',
                         'Stale native audio capture source', 'Stale native Mosaic source:')
    try:
        audio = audio_audit()
        sessions = session_audit()
    except ValueError as error:
        if str(error).startswith(source_mismatches):
            return dict(reusable=False, reason=str(error))
        raise
    require(audio.get('passed') is True and sessions.get('passed') is True, 'Incomplete stored-audio qualification')
    return dict(reusable=True, audio=audio, sessions=sessions)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('find', 'verify-bundle'))
    parser.add_argument('--pin', type=Path, required=True)
    parser.add_argument('--repository')
    parser.add_argument('--identity')
    parser.add_argument('--bundle', type=Path)
    options = parser.parse_args()
    pin = json.loads(options.pin.read_text()) if options.pin.is_file() else None
    if options.command == 'verify-bundle':
        require(pin is not None and options.bundle is not None, 'Bundle verification requires a pin and bundle')
        verify_bundle(options.bundle, pin)
        return
    def api(path):
        request = urllib.request.Request('https://api.github.com' + path, headers={
            'Authorization': 'Bearer ' + os.environ['GITHUB_TOKEN'],
            'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    result = find_bundle(options.repository, options.identity, pin, api)
    print('run_id=' + (str(result['run_id']) if result else ''))
    print('artifact_name=' + (result['artifact_name'] if result else ''))
    print('pinned=' + ('true' if result and result['pinned'] else 'false'))


if __name__ == '__main__':
    main()
