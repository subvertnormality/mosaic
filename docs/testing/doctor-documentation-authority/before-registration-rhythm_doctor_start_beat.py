"""Public Manual Start Beat regression (authorized functionality).

Characterisation: user-authorized full Manual alignment functionality,
2026-10-03; supplements README.md#rhythm-doctor. Real application input only.
Full apply/reanalysis requires real-time public PCM; draft-only UI may use an
independently qualified genuine candidate saved project in either UI lane.
"""
import json

from contract.rhythm_doctor_options import _select, _turn, _key, _qualify_fixture

CITATION = 'characterisation: authorized Manual Start Beat functionality; README.md#rhythm-doctor'


def regular_grid(envelope, bpm=120, origin=0):
    """Independent fixed-120 manual grid oracle, never production Bank code."""
    assert envelope['status'] == 'COMPLETED' and envelope['command'] == 'ANALYSE'
    assert type(envelope['frames']) is int and envelope['frames'] > 0
    assert envelope['sample_rate'] == 48000
    analysis = envelope['analysis']
    assert analysis['tempo_mode'] == 'manual' and analysis['bpm'] == bpm
    assert analysis['origin_sample'] == origin
    assert analysis['phrase_start_sample'] == origin
    period = 48000 * 60 / bpm
    assert period.is_integer(), 'This regression uses an exact integer sample period'
    phase = origin % int(period)
    wanted = list(range(phase, envelope['frames'], int(period)))
    assert analysis['beat_positions'] == wanted, 'Manual beat grid must span the whole actual capture, including before the chosen origin'
    assert len(wanted) > 1
    return wanted


def correction(previous, current, origin):
    """Bind reanalysis to the original actual WAV and unchanged candidates."""
    regular_grid(current, 120, origin)
    assert current['analysis_revision'] == previous['analysis_revision'] + 1
    for key in ('wav_sha256', 'frames', 'sample_rate', 'project_id', 'generation'):
        assert current[key] == previous[key], ('Actual recording identity changed', key)
    assert current['job_id'] != previous['job_id']
    assert current['analysis']['candidates'] == previous['analysis']['candidates'], 'Candidate absolute sample positions or values changed'
    assert current['analysis']['detector'] == previous['analysis']['detector']
    return current


def _checkpoint(c, ident, route, label=None, value=None):
    from manual_capture import frame
    expected = dict(route=route, label=label, value=value)
    receipt = dict(kind='doctor-start-beat-checkpoint', id=ident,
                   citation=CITATION, expected=expected, passed=False)
    c.results.append(receipt)
    frames = getattr(c, 'doctor_option_frames', [])
    frames.append(dict(id=ident, expect=expected,
                       output=frame(c, 'DOCTOR-START-BEAT', ident)))
    c.doctor_option_frames = frames
    # Capture actual native pixels even when old source still displays 1.
    c.ui.expect_rhythm_doctor_screen(route, label, value)
    receipt['passed'] = True


def _await(c, previous, origin):
    from frame_oracle import live_header_matches
    c.ui.expect_rhythm_doctor_header('R04')
    title, layout = c.ui._rhythm_doctor_screen('R05')
    c.wait(lambda state: live_header_matches(state, title, 'CH01', layout), timeout=180)
    c.ui.expect_rhythm_doctor_header('R05')
    envelopes = [json.loads(path.read_text()) for path in
                 (c.data_directory / 'rhythm-doctor-analysis-runtime/results').glob('*.json')]
    completed = [value for value in envelopes
                 if value.get('status') == 'COMPLETED'
                 and value.get('analysis_revision') == previous['analysis_revision'] + 1
                 and value.get('wav_sha256') == previous['wav_sha256']]
    assert len(completed) == 1, 'Need one exact next completed analysis of the retained actual WAV'
    return correction(previous, completed[0], origin)


def next_beat_apply_restore(c):
    """After retained_alignment(c,120), before READY fixture acquisition."""
    assert c.clock_mode == 'real-time', 'Public PCM/reanalysis is real-time only'
    original = c.doctor_ready_analysis
    assert original['analysis']['bpm'] == 120 and original['analysis']['origin_sample'] == 0
    c.ui.expect_rhythm_doctor_header('R05')
    _select(c, 'R05', 'Alignment')
    _key(c, 'apply_correction')
    _select(c, 'R06', 'Start beat')
    _checkpoint(c, 'start-beat-original1', 'R06', 'Start beat', '1')
    _turn(c, 3, 1)
    # Formal old-app regression fails HERE: singleton [0] leaves visible 1.
    _checkpoint(c, 'start-beat-next2', 'R06', 'Start beat', '2')
    regular_grid(original, 120, 0)
    _key(c, 'apply_correction')
    advanced = _await(c, original, 24000)
    c.doctor_ready_analysis = advanced
    _checkpoint(c, 'start-beat-next-ready', 'R05')

    _select(c, 'R05', 'Alignment')
    _key(c, 'apply_correction')
    _select(c, 'R06', 'Start beat')
    c.ui.expect_rhythm_doctor_screen('R06', 'Start beat', '2')
    _turn(c, 3, -1)
    _checkpoint(c, 'start-beat-restore1', 'R06', 'Start beat', '1')
    _key(c, 'apply_correction')
    restored = _await(c, advanced, 0)
    c.doctor_ready_analysis = restored
    _checkpoint(c, 'start-beat-restored-ready', 'R05')
    c.results.append(dict(kind='doctor-manual-start-beat', passed=True,
                          citation=CITATION, original=original,
                          advanced=advanced, restored=restored,
                          captured_sha256=original['wav_sha256'],
                          origins=[0, 24000, 0], bpm=120,
                          candidate_absolute_positions_unchanged=True,
                          controlled_time=dict(applicable=False, reason=
                            'Public ADC/softcut and retained PCM backend require real-time audio; draft-only UI is separately applicable.')))


def draft_next_cancel(c, fixture):
    """Prepared R05 genuine CANDIDATE saved-bank UI characterisation only.

    An old singleton-bank fixture is not a same-fixture C-backend regression.
    Caller qualifies before Driver startup. No correction is dispatched here.
    """
    _qualify_fixture(fixture)
    assert fixture['bank_bpm'] == 120 and fixture['beat_count'] > 1
    c.ui.expect_rhythm_doctor_header('R05')
    _select(c, 'R05', 'Alignment'); _key(c, 'apply_correction')
    _select(c, 'R06', 'Start beat')
    _checkpoint(c, 'start-beat-draft-original1', 'R06', 'Start beat', '1')
    _turn(c, 3, 1)
    _checkpoint(c, 'start-beat-draft-next2', 'R06', 'Start beat', '2')
    _key(c, 'discard_draft')
    c.ui.expect_rhythm_doctor_header('R05')
    _select(c, 'R05', 'Alignment'); _key(c, 'apply_correction')
    _select(c, 'R06', 'Start beat')
    _checkpoint(c, 'start-beat-draft-cancelled1', 'R06', 'Start beat', '1')
    _key(c, 'discard_draft')
    c.results.append(dict(kind='doctor-manual-start-beat-draft', passed=True,
                          citation=CITATION, same_fixture_backend_regression=False,
                          successful_reanalysis_claim=False))

