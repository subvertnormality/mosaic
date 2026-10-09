"""Staged Doctor canonical options recipes; UNRUN and not registered.

README.md "Rhythm Doctor" is the assertion contract. The READY caller must
prepare Driver(project_seed=...) from a genuinely public-ADC captured and
application-saved project, plus independently derived fixture expectations.
No bank assignment, injection, private evaluator or native session launch here.
Actual successful reanalysis/input routing remains real-time audio acceptance.
"""
import hashlib
import json
import re
from pathlib import Path

from frame_oracle import live_header_matches, selected_field_matches

CONTRACT = 'README.md#rhythm-doctor'
CITATION = 'manual:rhythm-doctor'
STEP_CELLS = [((s - 1) % 16 + 1, (s - 1) // 16 + 4) for s in range(1, 65)]


def _record(c, name, **values):
    row = dict(kind='doctor-options', check=name,
               contract=CONTRACT, citation=CITATION, **values)
    case_id = getattr(c, 'doctor_options_case_id', None)
    if case_id is not None:
        row['case_id'] = case_id
    c.results.append(row)


def _native_witness(c):
    """Bind one actual stored observation to the executed public input prefix.

    observation_index is zero-based; recipe_index is the executed-prefix length
    (the next input index), not the last input index. Wait pruning preserves
    every observation stored before that wait begins.
    """
    state = c.snapshot()
    return dict(observation_index=len(c.observations) - 1,
                recipe_index=len(c.recipe),
                state_sha256=hashlib.sha256(json.dumps(
                    state, sort_keys=True, separators=(',', ':'),
                    ensure_ascii=True).encode('utf-8')).hexdigest(),
                frame_sha256=state['frame']['sha256'])


def _turn(c, encoder, steps):
    # Independent action schema bounds raw delta to integer[-127,127].
    # At default sensitivity, a logical step is two raw detents. Chunk63
    # keeps each event inside that bound without losing the exact total.
    if type(steps) is not int:
        raise TypeError('Doctor logical encoder steps must be an integer')
    if type(encoder) is not int or encoder not in (2, 3):
        raise ValueError('Doctor field encoder must be 2 or 3')
    method = (c.ui.rhythm_doctor_setup_field if encoder == 2
              else c.ui.adjust_rhythm_doctor_setup_value)
    remaining = abs(steps)
    direction = 1 if steps > 0 else -1
    while remaining:
        chunk = min(63, remaining)
        # Pace both sides of each public native edge to avoid acceleration.
        c.elapse(.06)
        method(direction * chunk * 2)
        c.elapse(.1)
        remaining -= chunk


def _key(c, action):
    c.ui.rhythm_doctor_key_edge(action, True)
    try:
        c.elapse(.04)
    finally:
        c.ui.rhythm_doctor_key_edge(action, False)
    c.elapse(.12)


def _select(c, route, label, count=5):
    # Observe the public framebuffer, rather than reading a private field index.
    title, layout = c.ui._rhythm_doctor_screen(route)
    for _ in range(count):
        state = c.snapshot()
        if (live_header_matches(state, title, 'CH01', layout)
                and selected_field_matches(state, layout, label, art=True)):
            return
        _turn(c, 2, 1)
    c.ui.expect_rhythm_doctor_screen(route, label)


def _field(c, route, label, value):
    text = str(int(value)) if isinstance(value, (int, float)) and int(value) == value else str(value)
    c.ui.expect_rhythm_doctor_screen(route, label, text)
    _record(c, 'field', route=route, label=label, value=text)


def _mask(c, steps, preview=False):
    wanted = frozenset(steps)
    def matches(state):
        levels = [state['grid'][(y - 1) * 16 + x - 1] for x, y in STEP_CELLS]
        actual = frozenset(i + 1 for i, v in enumerate(levels)
                           if v in ((12, 15) if preview else (15,)))
        return actual == wanted
    c.wait(matches)
    _record(c, 'exact-grid-mask', steps=sorted(wanted), preview=preview)


def setup_options(c):
    """Fresh empty stopped app; caller owns Driver setup and teardown.

    Both UI timing lanes apply. This proves field semantics, not backend BPM
    or L/R consumption; the authorized audio functionality needs separate reds.
    """
    ui = c.ui
    ui.tap_control('pattern_editor')
    ui.select_rhythm_doctor_algorithm('rhythm_doctor')
    ui.expect_rhythm_doctor_header('R01')
    _turn(c, 2, 1)  # Opens draft through public E2.
    _select(c, 'R01', 'Tempo', 3)
    _field(c, 'R01', 'Tempo', 'AUTO')
    _turn(c, 3, 1)
    _field(c, 'R01', 'Tempo', 'MANUAL')
    _turn(c, 3, 1)
    _field(c, 'R01', 'Tempo', 'AUTO')
    _select(c, 'R01', 'Manual BPM', 3)
    _field(c, 'R01', 'Manual BPM', 120)
    _turn(c, 3, -100)
    _field(c, 'R01', 'Manual BPM', 40)
    _turn(c, 3, -1)
    _field(c, 'R01', 'Manual BPM', 40)
    _turn(c, 3, 201)
    _field(c, 'R01', 'Manual BPM', 240)
    _turn(c, 3, 1)
    _field(c, 'R01', 'Manual BPM', 240)
    _select(c, 'R01', 'Input', 3)
    _field(c, 'R01', 'Input', 'STEREO')
    _turn(c, 3, 1); _field(c, 'R01', 'Input', 'L')
    _turn(c, 3, 1); _field(c, 'R01', 'Input', 'R')
    _turn(c, 3, 1); _field(c, 'R01', 'Input', 'STEREO')
    _turn(c, 3, 2); _field(c, 'R01', 'Input', 'R')
    _key(c, 'discard_draft')
    _turn(c, 2, 1)
    for label, value in (('Tempo', 'AUTO'), ('Manual BPM', 120), ('Input', 'STEREO')):
        _select(c, 'R01', label, 3)
        _field(c, 'R01', label, value)
    _select(c, 'R01', 'Tempo', 3); _turn(c, 3, 1)
    _select(c, 'R01', 'Manual BPM', 3); _turn(c, 3, 7)
    _select(c, 'R01', 'Input', 3); _turn(c, 3, 2)
    _key(c, 'apply_correction')
    _turn(c, 2, 1)
    for label, value in (('Tempo', 'MANUAL'), ('Manual BPM', 127), ('Input', 'R')):
        _select(c, 'R01', label, 3)
        _field(c, 'R01', label, value)
    # Dirty draft is dropped by transport start; edits/Record remain gated.
    _turn(c, 3, 1)
    ui.play()
    try:
        _turn(c, 2, 1); _turn(c, 3, 1)
        ui.expect_rhythm_doctor_header('R11')
        ui.rhythm_doctor_capture_edge(True)
        try:
            c.elapse(.08)
        finally:
            ui.rhythm_doctor_capture_edge(False)
        ui.expect_rhythm_doctor_header('R11')
    finally:
        ui.stop()
    _turn(c, 2, 1)
    _select(c, 'R01', 'Input', 3)
    _field(c, 'R01', 'Input', 'R')
    _key(c, 'discard_draft')
    _record(c, 'setup-complete', backend_bpm_input_claim=False)


def _qualify_fixture(fixture):
    """Require hash-bound acquisition, actual saved project and geometry receipt.

    The root Driver wrapper MUST call this before starting Driver(project_seed).
    ready_options calls it again to detect changed fixture files after startup.
    This validates independently exported receipt identities; it does not derive
    masks or geometry through production Bank code.
    """
    path = Path(fixture['acquisition_report'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == fixture['acquisition_report_sha256']
    report = json.loads(path.read_text())
    assert report['passed']
    assert report['publication_kind'] in ('doctor-native-audio', 'doctor-options-qualification')
    if report['publication_kind'] == 'doctor-options-qualification':
        results = json.loads((path.parent / report['results']).read_text())
        captures = [r for r in results if r.get('kind') == 'doctor-backend-options' and r.get('passed')]
        assert len(captures) == 1, 'No actual public ADC acquisition result'
        assert report['cleanup_failure'] is None
    assert report['clock_mode'] == 'real-time'
    assert not (path.parent / 'diagnostic-only.json').exists()
    assert fixture['project_seed_origin'] == 'application-autosave-after-public-adc'
    seed = Path(fixture['project_seed'])
    saved = Path(fixture['saved_project'])
    assert saved.resolve() == (seed / 'autosave.ptn').resolve(), 'Saved file is not seed autosave'
    paths = sorted(seed.rglob('*'))
    assert seed.is_dir() and not any(p.is_symlink() for p in paths), 'Invalid seed directory'
    seed_map = {str(p.relative_to(seed)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    assert seed_map == fixture['project_seed_files'], 'Seed files changed or extras appeared'
    assert 'autosave.ptn' in seed_map
    assert all(name == 'autosave.ptn' or name.startswith('config/') for name in seed_map), 'Seed carries runtime/audio extras'
    saved_sha = hashlib.sha256(saved.read_bytes()).hexdigest()
    assert saved_sha == fixture['saved_project_sha256'], 'Saved project changed'
    receipt_path = Path(fixture['geometry_receipt'])
    assert hashlib.sha256(receipt_path.read_bytes()).hexdigest() == fixture['geometry_receipt_sha256']
    receipt = json.loads(receipt_path.read_text())
    assert receipt['passed'] is True
    assert receipt['kind'] == 'doctor-saved-project-geometry'
    assert receipt['saved_project_sha256'] == saved_sha
    assert receipt['project_seed_files'] == seed_map
    assert receipt['acquisition_report_sha256'] == fixture['acquisition_report_sha256']
    assert receipt['project_seed_origin'] == fixture['project_seed_origin']
    for key in ('bank_bpm', 'window_max', 'beat_count'):
        assert receipt['geometry'][key] == fixture[key], ('Geometry mismatch', key)
    # Expected musical masks/MIDI come from separately preserved public
    # observations; they must be bound by this same immutable receipt.
    for key in ('masks_by_sensitivity', 'midi_expected'):
        assert receipt['observations'][key] == fixture[key], ('Observation mismatch', key)
    assert fixture['window_max'] >= 16
    assert fixture['beat_count'] > 1
    assert len(set(fixture['masks_by_sensitivity']['0.5'])) < 64
    assert fixture['retained_audio'] is False, 'Reload refusal fixture must have no retained take'
    # Parent fixture exporter supplies exact masks, bank geometry and MIDI.
    for key in ('bank_bpm', 'masks_by_sensitivity', 'midi_expected',
                'window_max', 'beat_count'):
        assert key in fixture, key


def _destination(c, number):
    """G20 selects destination on P01; its explicit task reopens the Doctor."""
    c.ui.tap_control('pattern_select', number)
    c.ui.wait_for_header('trigger_editor', pattern=number, channel=1)
    from manual_capture import frame
    ident = 'p%02d-%03d' % (number, len(c.results))
    output = frame(c, 'DOCTOR-READY-DESTINATION', ident)
    # The Rhythm Doctor row is conditional on algorithm 5 for the selected
    # pattern. Choose it through the public grid control after pattern change,
    # then use the named task handoff whether the chooser landed on P01 or a
    # remembered Doctor subpage.
    c.ui.select_rhythm_doctor_algorithm('rhythm_doctor')
    c.ui.open_task('Trig', 'rhythm_doctor')
    window_title, window_layout = c.ui._rhythm_doctor_screen('R05')
    paint_title, paint_layout = c.ui._rhythm_doctor_screen('R08')
    c.wait(lambda state:
           live_header_matches(state, window_title, 'CH01', window_layout)
           or live_header_matches(state, paint_title, 'CH01', paint_layout))
    state = c.snapshot()
    if live_header_matches(state, paint_title, 'CH01', paint_layout):
        # A changed destination must invalidate and visibly disarm Paint before
        # the named task opens. If Paint remains selected, fail closed; K2 is
        # not a Paint-page back control.
        _mask(c, [], preview=True)
        c.wait(lambda current:
               live_header_matches(current, window_title, 'CH01', window_layout))
    c.ui.expect_rhythm_doctor_header('R05')
    c.results.append(dict(kind='doctor-ready-destination', id=ident,
                          pattern=number, route='P01', passed=True,
                          contract=CONTRACT,
                          citation='characterisation: docs/ui-reimplementation/spec.json G20 destination route',
                          output=output))


def _toggle_destination_steps(c, steps, pattern):
    """G21 does not invalidate the R05 held-step return; release restores it."""
    steps = list(steps)
    c.ui.expect_rhythm_doctor_header('R05')
    for step in steps:
        c.ui.tap_control('step', step)
    if not steps:
        return
    # Every step tap includes hold.begin -> G21(P01) -> hold.end. G21's
    # invalidates_return=false preserves the original R05 return frame.
    c.ui.expect_rhythm_doctor_header('R05')
    from manual_capture import frame
    ident = 'steps-p%02d-%03d' % (pattern, len(c.results))
    c.results.append(dict(kind='doctor-ready-step-edit', id=ident,
                          pattern=pattern, steps=steps, route='R05', passed=True,
                          contract=CONTRACT,
                          citation='characterisation: spec input_algebra hold.begin/hold.end restores R05 after G21 invalidates_return=false',
                          output=frame(c, 'DOCTOR-READY-STEP-EDIT', ident)))


def _position(cell):
    return '%d.%d.%d' % (cell // 16 + 1, cell % 16 // 4 + 1, cell % 4 + 1)


def _saved_phrase_cell(fixture):
    # Inert saved graph read, bound by _qualify_fixture's exact file SHA.
    chunks = re.split(r'-- Table: \{(\d+)\}', Path(fixture['saved_project']).read_text())
    tables = {int(chunks[i]): chunks[i + 1] for i in range(1, len(chunks), 2)}
    def ref(body, key):
        found = re.search(r'\["' + key + r'"\]\s*=\s*\{(\d+)\}', body)
        assert found, key
        return int(found.group(1))
    envelope = tables[ref(tables[2], 'rhythm_doctor')]
    bank = tables[ref(envelope, 'bank')]
    found = re.search(r'\["phrase_start_cell"\]\s*=\s*(\d+)', bank)
    assert found, 'Genuine saved bank lacks phrase marker'
    return min(fixture['window_max'], int(found.group(1)))


def _browse(c, direction, target, tooltip, held=False):
    if held:
        # lib/m_grid.lua long_press uses clock.sleep(1), in both UI lanes.
        with c.ui.hold_control('phrase_' + direction):
            c.elapse(1.2)
    else:
        c.ui.tap_rhythm_doctor_phrase_button(direction)
    c.ui.expect_rhythm_doctor_tooltip(tooltip)
    _select(c, 'R05', 'Window step')
    _field(c, 'R05', 'Window step', target + 1)
    _record(c, 'browse-gesture', direction=direction, held=held,
            window_start=target, tooltip=tooltip)


def _driver_midi_pairs(events):
    """Convert JSON [port, bytes] rows to Driver's tuple-pair API unchanged."""
    if not isinstance(events, (list, tuple)):
        raise ValueError('Expected a MIDI event sequence')
    pairs = []
    for event in events:
        if not isinstance(event, (list, tuple)) or len(event) != 2:
            raise ValueError('Expected each MIDI event to be a [port, bytes] pair')
        pairs.append((event[0], event[1]))
    return pairs


def _ready_playback(c, fixture, ident):
    """Keep Driver's exact phrase oracle and bind its native packet interval."""
    before = c.snapshot()['midi_count']
    attacks = c.playback(_driver_midi_pairs(fixture['midi_expected']), cycles=2,
                         timeout=fixture.get('playback_timeout', 15))
    state = c.snapshot()
    assert state['midi_capture']['outstanding'] == []
    # G38 retains workspace; after clear the owner is EMPTY, otherwise READY.
    c.ui.expect_rhythm_doctor_header('R01' if ident == 'clear-keeps-pattern' else 'R05')
    assert all(before < item['index'] <= state['midi_count'] for item in attacks)
    c.results.append(dict(kind='doctor-ready-playback', id=ident,
                          contract=CONTRACT, citation=CONTRACT, passed=True,
                          midi_start_index=before,
                          midi_end_index=state['midi_count'],
                          attacks=attacks, expectedphrase=fixture['midi_expected'],
                          complete_cycles=2, outstanding_notes=[]))


def ready_options(c, fixture):
    """Prepared genuine project_seed Driver; unrun staged acceptance.

    Expected masks describe window_start=0, BD, sensitivities 0/0.5/1.
    Destination patterns 3 and 4 must start empty in the saved fixture.
    Pattern 1 may contain the acquisition workflow's painted gates.
    Expected MIDI list is exact [port, bytes] per painted step; caller sets
    output and a fast enough channel clock to capture two cycles.
    """
    _qualify_fixture(fixture)
    ui = c.ui
    # Saved page selection may already be Trig; start from public Channel
    # before entering Pattern so the global button cannot cycle to Note.
    ui.tap_control('channel_editor')
    ui.tap_control('pattern_editor')
    ui.select_rhythm_doctor_algorithm('rhythm_doctor')
    # Keep normal 1->5 entry; a restored 5->5 selection intentionally does
    # nothing, so use its public Pattern task to reopen the READY screen.
    title, layout = ui._rhythm_doctor_screen('R05')
    if not live_header_matches(c.snapshot(), title, 'CH01', layout):
        ui.open_task('Trig', 'rhythm_doctor')
    ui.expect_rhythm_doctor_header('R05')
    ui.select_rhythm_doctor_lane('BD')
    _destination(c, 3)
    _mask(c, [])
    ui.expect_rhythm_doctor_header('R05')
    # Occupied-bank Record owns its held release. Premature K3 cannot clear.
    ui.rhythm_doctor_capture_edge(True)
    try:
        c.elapse(.08)
        ui.expect_rhythm_doctor_header('R10')
        _key(c, 'apply_correction')
        ui.expect_rhythm_doctor_header('R10')
    finally:
        ui.rhythm_doctor_capture_edge(False)
    _key(c, 'discard_draft')
    ui.expect_rhythm_doctor_header('R05')
    _record(c, 'held-record-modal-cancel', bank_retained=True)
    _select(c, 'R05', 'Window bar')
    _turn(c, 3, -100)
    _field(c, 'R05', 'Window bar', 1)
    _turn(c, 3, 1); _field(c, 'R05', 'Window bar', 2)
    _turn(c, 3, 100)
    _field(c, 'R05', 'Window bar', fixture['window_max'] // 16 + 1)
    _select(c, 'R05', 'Window step')
    _field(c, 'R05', 'Window step', fixture['window_max'] + 1)
    _turn(c, 3, 1)
    _field(c, 'R05', 'Window step', fixture['window_max'] + 1)
    _turn(c, 3, -fixture['window_max'] - 1)
    _field(c, 'R05', 'Window step', 1)
    _turn(c, 3, 1); _field(c, 'R05', 'Window step', 2)
    _turn(c, 3, -1); _field(c, 'R05', 'Window step', 1)

    # Browse without preview: taps1cell, holds64cells, no wrapping at either end.
    assert fixture['window_max'] >= 64, 'Fixture must expose a whole phrase page'
    _browse(c, 'left', 0, 'Start of recording')
    _browse(c, 'right', 1, 'Step right ' + _position(1))
    _browse(c, 'left', 0, 'Step left ' + _position(0))
    current = 0
    while current < fixture['window_max']:
        current = min(fixture['window_max'], current + 64)
        _browse(c, 'right', current, 'Next phrase ' + _position(current), held=True)
    _browse(c, 'right', current, 'End of recording', held=True)
    _browse(c, 'right', current, 'End of recording')
    while current > 0:
        current = max(0, current - 64)
        _browse(c, 'left', current, 'Previous phrase ' + _position(current), held=True)
    _browse(c, 'left', 0, 'Start of recording', held=True)
    phrase = _saved_phrase_cell(fixture)
    _browse(c, 'centre', phrase, ('Phrase start ' + _position(phrase)) if phrase else 'At phrase start')
    _browse(c, 'centre', phrase, 'At phrase start')
    # Return to the independently observed mask fixture's window before painting.
    _turn(c, 3, -fixture['window_max'] - 1)
    _field(c, 'R05', 'Window step', 1)

    _select(c, 'R05', 'Sensitivity')
    _turn(c, 3, -30); _field(c, 'R05', 'Sensitivity', '0')
    ui.tap_control('paint'); _mask(c, fixture['masks_by_sensitivity']['0'], True)
    ui.tap_control('cancel'); _mask(c, [])
    _select(c, 'R05', 'Sensitivity')
    _turn(c, 3, 30); _field(c, 'R05', 'Sensitivity', '1')
    ui.tap_control('paint'); _mask(c, fixture['masks_by_sensitivity']['1'], True)
    ui.tap_control('cancel'); _mask(c, [])
    _select(c, 'R05', 'Sensitivity')
    _turn(c, 3, -10); _field(c, 'R05', 'Sensitivity', '0.5')
    lane = frozenset(fixture['masks_by_sensitivity']['0.5'])
    assert lane, 'Fixture needs audible BD gates at sensitivity 0.5'
    # Category cycling and lane-local sensitivity; kick-only PCM does not prove
    # snare/cymbal detection quality or fabricate gates in those lanes.
    ui.select_rhythm_doctor_lane('SD')
    ui.expect_rhythm_doctor_lanes({'BD': 'blink_low', 'SD': 'selected', 'CYM': 'blink_low'})
    _select(c, 'R05', 'Sensitivity')
    _turn(c, 3, -30); _field(c, 'R05', 'Sensitivity', '0')
    _turn(c, 3, 30); _field(c, 'R05', 'Sensitivity', '1')
    ui.select_rhythm_doctor_lane('CYM')
    ui.expect_rhythm_doctor_lanes({'BD': 'blink_low', 'SD': 'blink_low', 'CYM': 'selected'})
    ui.select_rhythm_doctor_lane('BD')
    ui.expect_rhythm_doctor_lanes({'BD': 'selected', 'SD': 'blink_low', 'CYM': 'blink_low'})
    _select(c, 'R05', 'Sensitivity'); _field(c, 'R05', 'Sensitivity', '0.5')
    ui.tap_control('paint'); _mask(c, lane, True)
    ui.tap_control('cancel'); _mask(c, [])
    ui.select_rhythm_doctor_lane('SD')
    _select(c, 'R05', 'Sensitivity'); _field(c, 'R05', 'Sensitivity', '1')
    ui.select_rhythm_doctor_lane('BD')
    _select(c, 'R05', 'Sensitivity'); _field(c, 'R05', 'Sensitivity', '0.5')
    _record(c, 'lane-sensitivity-isolation', selected_lane='BD', bd_sensitivity=0.5,
            sd_sensitivity=1, detector_quality_claim=False)

    _select(c, 'R05', 'Paint policy')
    for value in ('TOGGLE', 'ADD', 'REPLACE', 'TOGGLE'):
        _field(c, 'R05', 'Paint policy', value)
        _turn(c, 3, 1)
    # Cursor now ADD. Cancelled preview must preserve empty destination.
    ui.tap_control('paint'); _mask(c, lane, True)
    ui.tap_control('cancel'); _mask(c, [])
    # Destination change cancels stale preview, and cannot paint pattern 3.
    ui.tap_control('paint')
    _destination(c, 4)
    _mask(c, [])
    ui.tap_control('paint'); _mask(c, lane, True)
    ui.tap_control('paint'); _mask(c, lane)
    _destination(c, 3); _mask(c, [])

    # Each policy gets a fresh grid-entered baseline: one overlapping hit,
    # one hit outside the lane. This distinguishes union/replacement/toggle.
    overlap = min(lane)
    outside = next(s for s in range(1, 65) if s not in lane)
    baseline = frozenset((overlap, outside))
    current = frozenset()
    for policy, expected in (
            ('TOGGLE', baseline ^ lane),
            ('ADD', baseline | lane),
            ('REPLACE', lane)):
        _toggle_destination_steps(c, sorted(current ^ baseline), 3)
        _mask(c, baseline)
        _select(c, 'R05', 'Paint policy')
        for _ in range(3):
            state = c.snapshot()
            _, layout = ui._rhythm_doctor_screen('R05')
            if selected_field_matches(state, layout, 'Paint policy', policy, art=True):
                break
            _turn(c, 3, 1)
        _field(c, 'R05', 'Paint policy', policy)
        ui.tap_control('paint'); _mask(c, baseline ^ lane, True)
        # Existing+preview overlap blinks dark (0/3); source-only 12/15,
        # baseline-only15. This is grid rendering characterisation.
        ui.tap_control('paint'); _mask(c, expected)
        current = expected
    # Exact MIDI phrase supplements the visible Replace mask.
    _ready_playback(c, fixture, 'replace-policy')

    # Reloaded audio is absent: K3 half/double refuse but retain edited draft.
    _select(c, 'R05', 'Alignment'); _key(c, 'apply_correction')
    _field(c, 'R06', 'Half tempo', fixture['bank_bpm'])
    _key(c, 'apply_correction')
    ui.expect_rhythm_doctor_screen('R07', 'Refused', 'CAPTURE AUDIO UNAVAILABLE')
    _turn(c, 2, 1)
    half = max(40, int(fixture['bank_bpm']) // 2)
    _field(c, 'R06', 'Double tempo', half)
    _key(c, 'apply_correction')
    ui.expect_rhythm_doctor_screen('R07', 'Refused', 'CAPTURE AUDIO UNAVAILABLE')
    _turn(c, 2, 1)
    _select(c, 'R06', 'Exact BPM')
    _turn(c, 3, -240); _field(c, 'R06', 'Exact BPM', 40)
    _turn(c, 3, 201); _field(c, 'R06', 'Exact BPM', 240)
    _select(c, 'R06', 'Start beat')
    _turn(c, 3, -fixture['beat_count']); _field(c, 'R06', 'Start beat', 1)
    _turn(c, 3, fixture['beat_count']); _field(c, 'R06', 'Start beat', fixture['beat_count'])
    _select(c, 'R06', 'Fine start')
    _field(c, 'R06', 'Fine start', '0ms')
    _turn(c, 3, -1); _field(c, 'R06', 'Fine start', '-1ms')
    _turn(c, 3, 2); _field(c, 'R06', 'Fine start', '1ms')
    _key(c, 'discard_draft')
    ui.expect_rhythm_doctor_header('R05')
    _mask(c, lane)
    # K2 did not alter bank tempo: a fresh draft starts from original BPM.
    _select(c, 'R05', 'Alignment'); _turn(c, 3, 1)
    _field(c, 'R06', 'Half tempo', fixture['bank_bpm'])
    _key(c, 'discard_draft')
    # While playing, READY edits work, Alignment/Record remain stopped-only.
    witnesses = dict(pre_play=_native_witness(c))
    ui.play()
    try:
        _select(c, 'R05', 'Alignment'); _turn(c, 3, 1)
        ui.expect_rhythm_doctor_header('R05')
        # Record's running-transport refusal is silent. It must not open a
        # clear question or claim the held release; the READY row stays put.
        ui.rhythm_doctor_capture_edge(True)
        try:
            c.elapse(.08)
            ui.expect_rhythm_doctor_header('R05')
            _field(c, 'R05', 'Alignment', 'OPEN >')
            witnesses['held_record'] = _native_witness(c)
        finally:
            ui.rhythm_doctor_capture_edge(False)
        ui.expect_rhythm_doctor_header('R05')
        _field(c, 'R05', 'Alignment', 'OPEN >')
        witnesses['released_record'] = _native_witness(c)
        ui.select_rhythm_doctor_lane('SD')
        ui.expect_rhythm_doctor_lanes({'BD': 'blink_low', 'SD': 'selected',
                                      'CYM': 'blink_low'})
        ui.select_rhythm_doctor_lane('BD')
    finally:
        ui.stop()
    c.wait(lambda state: state['midi_capture']['outstanding'] == [])
    _mask(c, lane)
    witnesses['post_stop_mask'] = _native_witness(c)
    _select(c, 'R05', 'Alignment'); _turn(c, 3, 1)
    _field(c, 'R06', 'Half tempo', fixture['bank_bpm'])
    witnesses['stopped_bpm'] = _native_witness(c)
    _key(c, 'discard_draft')
    ui.expect_rhythm_doctor_header('R05')
    witnesses['end'] = _native_witness(c)
    _record(c, 'playing-record-refused', route='R05', released=True,
            bank_bpm=fixture['bank_bpm'], steps=sorted(lane), witnesses=witnesses)
    # Armed Replace preview survives transport start and commits while playing.
    _select(c, 'R05', 'Paint policy')
    _field(c, 'R05', 'Paint policy', 'REPLACE')
    ui.tap_control('paint')
    _mask(c, [], True)  # All source gates overlap existing destination gates.
    ui.play()
    try:
        ui.tap_control('paint')
    finally:
        ui.stop()
    _mask(c, lane)
    _ready_playback(c, fixture, 'live-preview-commit')
    # Confirm clear only after release. Painted gates/MIDI must survive.
    ui.rhythm_doctor_capture_edge(True)
    try:
        c.elapse(.08)
        ui.expect_rhythm_doctor_header('R10')
    finally:
        ui.rhythm_doctor_capture_edge(False)
    _key(c, 'apply_correction')
    ui.expect_rhythm_doctor_header('R01')
    _mask(c, lane)
    _ready_playback(c, fixture, 'clear-keeps-pattern')
    _record(c, 'clear-keeps-painted-pattern', bank_cleared=True)
    _record(c, 'ready-options-complete', fixture_report=str(fixture['acquisition_report']),
            successful_reanalysis_claim=False, staged_unrun=True)



def run_doctor_setup_options(c):
    """Registry owner for the existing Rhythm Doctor setup scenario."""
    c.doctor_options_case_id='M-DOCTOR-SETUP-001'
    setup_options(c)
