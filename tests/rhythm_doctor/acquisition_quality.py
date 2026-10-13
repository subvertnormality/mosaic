"""Independent PLAN.md RD-02 acquisition metrics (outside current README).

Reference beat/downbeat times must come from frozen annotations, never detector
outputs. This scores metrics only, not corpus provenance or runtime behaviour.
"""
import bisect
import math

FIELDS = {
    "id", "eligible", "control", "reference_bpm", "reference_beats",
    "reference_downbeat", "captured_duration", "predicted_bpm", "predicted_origin",
    "predicted_region", "status", "predicted_bar_start", "timeout_seconds",
}


def number(value, name, positive=False, optional=False):
    if value is None and optional:
        return None
    if (type(value) not in (int, float) or not math.isfinite(value)
            or value < 0 or (positive and value == 0)):
        raise ValueError("invalid " + name)
    return float(value)


def validate(case):
    if not isinstance(case, dict) or set(case) != FIELDS:
        raise ValueError("invalid acquisition evidence schema")
    if not isinstance(case['id'], str) or not case['id']:
        raise ValueError('missing case identity')
    if type(case['eligible']) is not bool:
        raise ValueError('invalid eligibility')
    if case['control'] not in ('steady', 'silent', 'ambiguous', 'drifting'):
        raise ValueError('invalid control')
    if case['status'] not in ('accepted', 'uncertain', 'refused'):
        raise ValueError('invalid status')
    duration = number(case['captured_duration'], 'duration', positive=True)
    decision = number(case['timeout_seconds'], 'decision time', positive=True)
    if duration > 45 or decision > 45:
        raise ValueError('capture/decision exceeds 45 seconds')
    for field in ('reference_bpm', 'predicted_bpm'):
        number(case[field], field, positive=True, optional=True)
    for field in ('reference_downbeat', 'predicted_origin'):
        number(case[field], field, optional=True)
    bar = case['predicted_bar_start']
    if bar != 'START ASSUMED':
        number(bar, 'predicted bar start', optional=True)
    region = case['predicted_region']
    if region is not None:
        if not isinstance(region, list) or len(region) != 2:
            raise ValueError('invalid region')
        for value in region:
            number(value, 'region')
    beats = case['reference_beats']
    if not isinstance(beats, list):
        raise ValueError('missing reference beats')
    for beat in beats:
        if number(beat, 'reference beat') > duration:
            raise ValueError('reference beat outside capture')
    if any(a >= b for a, b in zip(beats, beats[1:])):
        raise ValueError('reference beats must be strictly increasing')
    if case['control'] == 'silent':
        if beats or case['reference_bpm'] is not None or case['reference_downbeat'] is not None:
            raise ValueError('silent reference contains musical beats')
    elif not beats or case['reference_bpm'] is None:
        raise ValueError('missing musical reference')
    if case['eligible'] and case['control'] != 'steady':
        raise ValueError('uncertainty control cannot be steady eligible')
    if case['control'] == 'steady' and not 40 <= case['reference_bpm'] <= 240:
        raise ValueError('reference BPM outside supported envelope')


def phase_error(beats, origin, end, bpm):
    """All predicted beats in the retained span, including a complete end beat."""
    count = math.floor((end - origin) * bpm / 60 + 1e-9) + 1
    if count < 1 or count > 181:
        return None
    maximum = 0.0
    for index in range(count):
        beat = origin + index * 60 / bpm
        nearest = bisect.bisect_left(beats, beat)
        candidates = beats[max(0, nearest - 1):nearest + 1]
        if not candidates:
            return None
        maximum = max(maximum, min(abs(beat - reference) for reference in candidates))
    return maximum


def evaluate(cases):
    cases = list(cases)
    seen, results = set(), []
    eligible = successes = octaves = bar_scored = bar_correct = 0
    controls_pass = True
    for case in cases:
        validate(case)
        if case['id'] in seen:
            raise ValueError('duplicate case identity')
        seen.add(case['id'])
        row = dict(id=case['id'], eligible=case['eligible'], ok=False)
        results.append(row)
        if case['control'] != 'steady':
            row['ok'] = case['status'] == 'uncertain'
            controls_pass = controls_pass and row['ok']
            continue
        if not case['eligible']:
            row['excluded'] = True
            continue
        eligible += 1
        if case['status'] != 'accepted':
            continue
        bpm, origin, region = (case[name] for name in
                               ('predicted_bpm', 'predicted_origin', 'predicted_region'))
        if bpm is None or origin is None or region is None:
            raise ValueError('accepted result is missing prediction')
        ratio = bpm / case['reference_bpm']
        octave = any(abs(ratio / multiple - 1) <= .02 for multiple in (.5, 2))
        octaves += int(octave)
        start, end = region
        valid_region = (40 <= bpm <= 240 and abs(start - origin) <= 1e-9
                        and 0 <= start < end <= min(case['captured_duration'], case['timeout_seconds'])
                        and end - start + 1e-9 >= 16 * 60 / bpm)
        phase = phase_error(case['reference_beats'], origin, end, bpm) if valid_region else None
        bar, downbeat = case['predicted_bar_start'], case['reference_downbeat']
        labelled = bar == 'START ASSUMED' or (bar is not None and downbeat is not None)
        if bar != 'START ASSUMED' and bar is not None and downbeat is not None:
            bar_scored += 1
            bar_correct += int(abs(bar - downbeat) <= .05 + 1e-12)
        row.update(phase_seconds=phase, octave_error=octave,
                   ok=bool(valid_region and phase is not None and phase <= .05 + 1e-12
                           and abs(ratio - 1) <= .02 + 1e-12 and not octave and labelled))
        successes += int(row['ok'])
    if not eligible:
        raise ValueError('no steady eligible clips')
    rate = successes / eligible
    return dict(eligible=eligible, passed=successes, success_rate=rate,
                octave_errors=octaves, uncertainty_controls_pass=controls_pass,
                gate_pass=rate >= .9 and controls_pass, results=results,
                bar_start=dict(scored=bar_scored, correct=bar_correct,
                               accuracy=bar_correct / bar_scored if bar_scored else None),
                complete_rd02_acceptance=False,
                scope='acquisition metrics only; provenance and runtime gates separate')
