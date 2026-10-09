"""Acquire a genuine saved READY fixture inside an existing public ADC session.

API: acquire(c), then finalize(out, report_path) AFTER the passing acquisition
report exists. No session startup, bank injection, private Lua input, Bank-model
recomputation or automatic publication. Only application autosave.ptn/config are
copied to the seed. Full captured/analysis evidence stays in the parent run.
"""
import hashlib
import json
import math
import re
import shutil
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'application-autosave-after-public-adc'
sys.path.insert(0, str(ROOT / 'tests/behaviour'))


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def seed_files(directory):
    directory = Path(directory)
    assert directory.is_dir()
    paths = sorted(directory.rglob('*'))
    assert not any(path.is_symlink() for path in paths), 'Seed cannot contain symlinks'
    files = {str(path.relative_to(directory)): digest(path) for path in paths if path.is_file()}
    assert 'autosave.ptn' in files
    assert all(name == 'autosave.ptn' or name.startswith('config/') for name in files), 'Seed has retained runtime/audio or extra files'
    return files


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n')


def saved_geometry(path):
    """Read the inert tabutil table graph; never execute its Lua source.

    Only scalar/reference fields needed for geometry are accepted. No Bank or
    Persistence code is called, and no saved field is modified.
    """
    text = Path(path).read_text()
    chunks = re.split(r'-- Table: \{(\d+)\}', text)
    assert len(chunks) > 2, 'Not a norns tabutil table graph'
    tables = {int(chunks[i]): chunks[i + 1] for i in range(1, len(chunks), 2)}
    def reference(body, key):
        found = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*\{(\d+)\}', body)
        assert found, 'Missing saved reference ' + key
        return int(found.group(1))
    def number(body, key):
        found = re.search(r'\["' + re.escape(key) + r'"\]\s*=\s*([-+0-9.eE]+)', body)
        assert found, 'Missing saved scalar ' + key
        value = float(found.group(1))
        assert math.isfinite(value), key
        return int(value) if value.is_integer() else value
    program = tables[2]
    envelope = tables[reference(program, 'rhythm_doctor')]
    assert number(envelope, 'version') == 1
    bank = tables[reference(envelope, 'bank')]
    source = tables[reference(bank, 'source')]
    beats = tables[reference(source, 'beat_positions')]
    # Table arrays emitted by tabutil contain one scalar per line.
    beat_values = re.findall(r'^\s*([-+0-9.eE]+)\s*,\s*$', beats, re.M)
    assert beat_values, 'Saved bank has no actual detector beat grid'
    geometry = {k: number(bank, k) for k in (
        'bpm', 'timeline_cells', 'sample_rate', 'capture_start_sample',
        'capture_end_sample', 'origin_sample', 'samples_per_cell', 'window_start')}
    assert geometry['timeline_cells'] >= 64
    assert geometry['sample_rate'] == 48000
    geometry.update(bank_bpm=geometry.pop('bpm'),
                    window_max=geometry['timeline_cells'] - 64,
                    beat_count=len(beat_values))
    return geometry


def _active(state):
    return [i + 1 for i, level in enumerate(state['grid'][48:112])
            if level in (12, 15)]


def _notes(state, after):
    return [item for item in state['midi'] if item['index'] > after
            and 144 <= item['bytes'][0] <= 159 and item['bytes'][2] > 0]


def _phrase(notes, hit_count):
    assert hit_count > 0 and len(notes) >= hit_count * 2 + 1
    sequence = [[item['port'], item['bytes']] for item in notes]
    expected = sequence[:hit_count]
    assert sequence == [expected[i % hit_count] for i in range(len(sequence))], 'Native phrase did not repeat exactly'
    assert all(port == 1 for port, _ in sequence), 'Wrong output port'
    return expected


def acquire(c):
    """Run after a successful capture_option(c, ...) in its still-live session."""
    from contract.rhythm_doctor_options import _select, _turn, _field, _mask, _key, _destination, _toggle_destination_steps
    from manual_capture import frame
    assert c.clock_mode == 'real-time'
    evidence = [r for r in c.results if r.get('kind') == 'doctor-backend-options' and r.get('passed')]
    assert len(evidence) == 1, 'Need one original actual public ADC acquisition'
    backend = evidence[0]
    envelope = getattr(c, 'doctor_ready_analysis', None)
    analysis = envelope['analysis'] if envelope else backend['analysis']
    out = c.out / 'ready-fixture'
    out.mkdir(exist_ok=False)
    observations = []
    def observe(name, **expected):
        observations.append(dict(id=name, expected=expected,
                                 output=frame(c, 'DOCTOR-READY-FIXTURE', name)))
    ui = c.ui
    # Initial capture may end on Channel Editor; retained reanalysis ends WINDOW.
    from frame_oracle import live_header_matches
    title, layout = ui._rhythm_doctor_screen('R05')
    if not live_header_matches(c.snapshot(), title, 'CH01', layout):
        ui.tap_control('pattern_editor')
        ui.wait_for_header('trigger_editor', pattern=1, channel=1)
        # Algorithm 5 is already selected; 5->5 is deliberately inert.
        ui.open_task('Trig', 'rhythm_doctor')
    ui.expect_rhythm_doctor_header('R05')
    ui.select_rhythm_doctor_lane('BD')
    _destination(c, 3)
    _mask(c, [])
    _destination(c, 4)
    _mask(c, [])
    _destination(c, 3)
    _select(c, 'R05', 'Window step')
    _turn(c, 3, -1000)
    _field(c, 'R05', 'Window step', 1)
    observe('window-low', window_start=0)
    _turn(c, 3, 1000)
    # Read exact bound from saved geometry later; capture a public rendering now.
    bound_frame = frame(c, 'DOCTOR-READY-FIXTURE', 'window-high')
    _turn(c, 3, -1000)
    _field(c, 'R05', 'Window step', 1)
    masks = {}
    for threshold, change in (('0', -30), ('0.5', 10), ('1', 10)):
        _select(c, 'R05', 'Sensitivity')
        _turn(c, 3, change)
        _field(c, 'R05', 'Sensitivity', threshold)
        ui.tap_control('paint')
        ui.expect_rhythm_doctor_header('R08')
        state = c.snapshot()
        masks[threshold] = _active(state)
        observe('preview-' + threshold, sensitivity=threshold, steps=masks[threshold])
        ui.tap_control('cancel')
        _mask(c, [])
    _select(c, 'R05', 'Sensitivity')
    _turn(c, 3, -10)
    _field(c, 'R05', 'Sensitivity', '0.5')
    _select(c, 'R05', 'Paint policy')
    _field(c, 'R05', 'Paint policy', 'TOGGLE')
    _turn(c, 3, 2)
    _field(c, 'R05', 'Paint policy', 'REPLACE')
    ui.tap_control('paint'); _mask(c, masks['0.5'], True)
    ui.tap_control('paint'); _mask(c, masks['0.5'])
    observe('paint-p3', steps=masks['0.5'])

    # Capture proved P1 assigned. Public row2 channel buttons route only P3.
    ui.tap_control('channel_editor')
    ui.tap_control('pattern_slot', 1)
    ui.tap_control('pattern_slot', 3)
    ui.set_range(1, 64)
    before = c.snapshot()['midi_count']
    ui.play()
    try:
        state = c.wait(lambda state: len(_notes(state, before)) >= len(masks['0.5']) * 2 + 1,
                       timeout=40)
        notes = _notes(state, before)
        phrase = _phrase(notes, len(masks['0.5']))
        # A complete repeated 64-step phrase, not the first two seconds.
        observe('full64-midi', steps=masks['0.5'], notes=notes, expected=phrase,
                midi_start_index=before, midi_end_index=state['midi_count'])
    finally:
        ui.stop()
    drained = c.wait(lambda state: state['midi_capture']['outstanding'] == [])
    packets = [item for item in drained['midi'] if item['index'] > before]
    closing = notes[-1]
    # Preserve the original closing attack and its actual native release after
    # public Stop. Do not treat an open closing attack as complete evidence.
    def releases(item):
        data = item['bytes']
        attack = closing['bytes']
        return (item['index'] > closing['index']
                and item['port'] == closing['port']
                and len(data) >= 3
                and data[0] % 16 == attack[0] % 16
                and data[1] == attack[1]
                and (128 <= data[0] <= 143
                     or (144 <= data[0] <= 159 and data[2] == 0)))
    closing_releases = [item for item in packets if releases(item)]
    assert closing_releases, 'Closing full64 attack has no actual native release'
    release_endpoint = dict(midi_start_index=before,
                            midi_end_index=drained['midi_count'],
                            closing_attack_index=closing['index'],
                            closing_attack=closing,
                            closing_releases=closing_releases,
                            packets=packets, outstanding_notes=[])
    observe('full64-midi-release', **release_endpoint)
    c.results.append(dict(kind='doctor-ready-fixture-playback-release', passed=True,
                          contract='README.md#rhythm-doctor', **release_endpoint))
    # Keep only P3 routed in saved config, then clear its fixture destination.
    ui.tap_control('pattern_editor')
    ui.wait_for_header('trigger_editor', pattern=3, channel=1)
    ui.open_task('Trig', 'rhythm_doctor')
    ui.expect_rhythm_doctor_header('R05')
    _destination(c, 3)
    _toggle_destination_steps(c, masks['0.5'], 3)
    _mask(c, [])
    _destination(c, 4); _mask(c, [])
    _destination(c, 3)
    observe('blank-destinations', patterns=[3, 4])
    # Autosave is an application timer. Do not ask it to serialize private state.
    c.elapse(30); c.elapse(30); c.elapse(2)
    saved = c.data_directory / 'autosave.ptn'
    c.wait(lambda _: saved.is_file(), timeout=5)
    geometry = saved_geometry(saved)
    assert geometry['bank_bpm'] == analysis['bpm']
    assert geometry['origin_sample'] == analysis['origin_sample']
    assert geometry['beat_count'] == len(analysis['beat_positions'])
    assert geometry['window_start'] == 0
    # Independently bind public high-bound rendering to the persisted scalar.
    from frame_oracle import selected_field_matches, live_header_matches
    title, layout = ui._rhythm_doctor_screen('R05')
    # Revisit bound publicly; no private state/evaluation.
    _select(c, 'R05', 'Window step')
    _turn(c, 3, 1000)
    _field(c, 'R05', 'Window step', geometry['window_max'] + 1)
    observe('window-high-confirmed', window_max=geometry['window_max'])
    _turn(c, 3, -1000)
    # Original autosave already has this same zero window/empty destination.
    seed = out / 'project-seed'
    seed.mkdir()
    shutil.copyfile(saved, seed / 'autosave.ptn')
    config = c.data_directory / 'config'
    if config.is_dir():
        shutil.copytree(config, seed / 'config')
    observations_value = dict(masks_by_sensitivity=masks, midi_expected=phrase)
    draft = dict(kind='doctor-ready-fixture-acquisition', passed=True,
                 project_seed_origin=ORIGIN, retained_audio=False,
                 saved_project=str(seed / 'autosave.ptn'),
                 saved_project_sha256=digest(seed / 'autosave.ptn'),
                 geometry=geometry, observations=observations_value,
                 captured_sha256=backend['captured_sha256'],
                 playback_release=release_endpoint,
                 original_bound_frame=bound_frame, frames=observations,
                 project_seed=str(seed), project_seed_files=seed_files(seed),
                 recipe_sha256=digest(__file__))
    write(out / 'acquisition.json', draft)
    c.results.append(dict(kind='doctor-ready-fixture-acquisition', passed=True,
                          receipt=str(out / 'acquisition.json'),
                          receipt_sha256=digest(out / 'acquisition.json'),
                          saved_project_sha256=draft['saved_project_sha256'],
                          contract='README.md#rhythm-doctor'))
    return draft


def finalize(out, report_path):
    """Bind the acquired fixture only after parent report and cleanup pass."""
    out, report_path = Path(out), Path(report_path)
    if not (out / 'acquisition.json').is_file():
        out = out / 'ready-fixture'
    report = json.loads(report_path.read_text())
    assert report['passed'] is True and report['clock_mode'] == 'real-time'
    assert report['publication_kind'] == 'doctor-options-qualification'
    assert report['cleanup_failure'] is None and not report['complete_regression_run']
    draft_path = out / 'acquisition.json'
    draft = json.loads(draft_path.read_text())
    assert draft['passed'] is True and draft['project_seed_origin'] == ORIGIN
    saved = Path(draft['saved_project'])
    assert digest(saved) == draft['saved_project_sha256']
    assert saved.resolve() == (Path(draft['project_seed']) / 'autosave.ptn').resolve()
    assert seed_files(draft['project_seed']) == draft['project_seed_files']
    results = json.loads((report_path.parent / report['results']).read_text())
    witnessed = [r for r in results if r.get('kind') == 'doctor-ready-fixture-acquisition']
    assert len(witnessed) == 1
    assert witnessed[0]['receipt_sha256'] == digest(draft_path)
    receipt = dict(kind='doctor-saved-project-geometry', passed=True,
                   project_seed_origin=ORIGIN,
                   saved_project_sha256=digest(saved),
                   acquisition_report_sha256=digest(report_path),
                   acquisition_receipt_sha256=digest(draft_path),
                   geometry=draft['geometry'], observations=draft['observations'],
                   project_seed_files=draft['project_seed_files'],
                   playback_release=draft['playback_release'],
                   recipe_sha256=draft['recipe_sha256'])
    receipt_path = out / 'geometry-receipt.json'
    write(receipt_path, receipt)
    geometry = draft['geometry']
    fixture = dict(project_seed=draft['project_seed'],
                   project_seed_files=draft['project_seed_files'],
                   saved_project=str(saved), saved_project_sha256=digest(saved),
                   acquisition_report=str(report_path),
                   acquisition_report_sha256=digest(report_path),
                   geometry_receipt=str(receipt_path),
                   geometry_receipt_sha256=digest(receipt_path),
                   project_seed_origin=ORIGIN, retained_audio=False,
                   bank_bpm=geometry['bank_bpm'], window_max=geometry['window_max'],
                   beat_count=geometry['beat_count'],
                   masks_by_sensitivity=draft['observations']['masks_by_sensitivity'],
                   midi_expected=draft['observations']['midi_expected'],
                   playback_timeout=40)
    from contract.rhythm_doctor_options import _qualify_fixture
    _qualify_fixture(fixture)
    write(out / 'fixture.json', fixture)
    return fixture


def guard_test_suite():
    """Durable pure fixture-protocol characterisations; no native session."""
    import tempfile
    import unittest
    class Tests(unittest.TestCase):
        def test_saved_graph_geometry(self):
            text = '''return {
-- Table: {1}
{}
-- Table: {2}
{["rhythm_doctor"]={3},}
-- Table: {3}
{["version"]=1,["bank"]={4},}
-- Table: {4}
{["bpm"]=100,["timeline_cells"]=166,["sample_rate"]=48000,
["capture_start_sample"]=0,["capture_end_sample"]=1200000,
["origin_sample"]=0,["samples_per_cell"]=7200,["window_start"]=0,["source"]={5},}
-- Table: {5}
{["beat_positions"]={6},}
-- Table: {6}
{
0,
28800,
57600,
},
}'''
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'autosave.ptn'; path.write_text(text)
                geometry = saved_geometry(path)
                self.assertEqual((geometry['window_max'], geometry['beat_count']), (102, 3))
                self.assertEqual(geometry['bank_bpm'], 100)
        def test_missing_bank_rejected(self):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'autosave.ptn'
                path.write_text('return { -- Table: {1}\n{} -- Table: {2}\n{} }')
                with self.assertRaises(AssertionError): saved_geometry(path)
        def test_phrase_requires_complete_repeat(self):
            notes = [dict(port=1, bytes=[144, 60, v]) for v in (80, 90, 80, 90, 80)]
            self.assertEqual(_phrase(notes, 2), [[1, [144, 60, 80]], [1, [144, 60, 90]]])
            notes[-1]['bytes'][2] = 70
            with self.assertRaises(AssertionError): _phrase(notes, 2)
        def test_seed_rejects_extra_audio_and_tracks_config_mutation(self):
            with tempfile.TemporaryDirectory() as directory:
                seed = Path(directory)
                (seed / 'autosave.ptn').write_text('actual-saved-project')
                (seed / 'config').mkdir()
                config = seed / 'config/device.json'; config.write_text('{}')
                initial = seed_files(seed)
                config.write_text('{\"changed\":true}')
                self.assertNotEqual(seed_files(seed), initial)
                (seed / 'capture.wav').write_bytes(b'audio')
                with self.assertRaises(AssertionError): seed_files(seed)
        def test_partial_phrase_rejected(self):
            with self.assertRaises(AssertionError): _phrase([dict(port=1, bytes=[144,60,80])], 2)
    return unittest.defaultTestLoader.loadTestsFromTestCase(Tests)


def self_test():
    import unittest
    return unittest.TextTestRunner().run(guard_test_suite()).wasSuccessful()


if __name__ == '__main__':
    if sys.argv[1:] != ['--self-test']:
        raise SystemExit('Use acquire(c) inside the parent live acquisition; or --self-test for pure guards')
    raise SystemExit(0 if self_test() else 1)

