"""Independent fixed-tempo note plan; never infer tempo/phase from emissions."""
from fractions import Fraction


def preview_residual(period):
    return period + Fraction(1, 2) - (period + Fraction(49, 100)).__floor__()


def quantised_pulse(period, ordinal, preview_seed=Fraction(1, 2)):
    assert period >= 1 and type(ordinal) is int and ordinal >= 0
    # Pinned lattice preview/carry contract, independently checked against700
    # actual lattice positions. The constructor consumes one preview interval.
    bias = preview_seed - Fraction(1, 100)
    return ((ordinal + 1) * period + bias).__floor__() - (period + bias).__floor__()


def note_plan(period, origin, stop, pulse_rate=144, preview_seed=Fraction(1, 2)):
    assert isinstance(period, Fraction) and period >= 1
    assert all(type(x) is int for x in (origin, stop, pulse_rate))
    assert 0 <= origin < stop and pulse_rate > 0
    planned = []
    onsets = []
    velocities = (127, 117, 107, 97)
    for ordinal in range(100_000):
        pulse = quantised_pulse(period, ordinal, preview_seed)
        deadline = origin + round(Fraction(pulse * 1_000_000_000, pulse_rate))
        if deadline >= stop:
            break
        intent = origin + round(ordinal * period * 1_000_000_000 / pulse_rate)
        if ordinal:
            planned.append(dict(port=1, bytes=[128, 60, velocities[(ordinal-1) % 4]],
                                intent_ns=intent, deadline_ns=deadline))
        planned.append(dict(port=1, bytes=[144, 60, velocities[ordinal % 4]],
                            intent_ns=intent, deadline_ns=deadline))
        onsets.append(dict(ordinal=ordinal, pulse=pulse, intent_ns=intent, deadline_ns=deadline))
    else:
        raise AssertionError('Unbounded fractional timing plan')
    assert onsets
    return planned, onsets



def realtime_stop_prefix(events, period, origin, stop, applied, preview_seed):
    """Match an independently bounded canonical prefix at an asynchronous Stop.

    D20 already permits a50ms per-event maximum (p99 remains10ms and final20ms).
    This bound defines cancellation uncertainty; it does not loosen timing checks
    for emitted notes or fit the schedule to observed startup/phase.
    """
    bound=50_000_000
    planned,onsets=note_plan(period,origin,applied+bound+1,preview_seed=preview_seed)
    required=sum(n['deadline_ns']+bound<stop for n in onsets)
    # N onsets have exactly2*N-1 scheduled messages and one forced release.
    # Enumerate allowed lengths from canonical deadlines, not observed pitches.
    admissible=range(max(1,required),len(onsets)+1)
    assert len(events)%2==0 and len(events)//2 in admissible, (
        'Missing/extra note event outside Stop boundary',len(events),required,len(onsets))
    emitted=len(events)//2
    final=events[-1]
    assert origin<=events[0]['monotonic_ns']<=origin+bound,'Start latency outside D20 bound'
    assert all(e['monotonic_ns']<=final['monotonic_ns'] for e in events[:-1]),'Scheduled emission after forced release'
    return planned[:2*emitted-1],onsets[:emitted],dict(
        bound_ns=bound,required_onsets=required,emitted_onsets=emitted,
        maximum_admissible_onsets=len(onsets),boundary_ambiguous_onsets=len(onsets)-required,
        permitted_prefix_lengths=list(admissible))


def check_segment(events, period, origin, stop, applied, *, controlled, preview_seed=Fraction(1, 2)):
    from automation.scheduling_metrics import scheduling_metrics
    assert stop <= applied
    planned, onsets = note_plan(period, origin, stop, preview_seed=preview_seed)
    notes = [e for e in events if e['bytes'][0] & 240 in (128, 144)]
    boundary=None
    if controlled:
        assert len(notes) == len(planned) + 1, ('Missing/extra note event', len(notes), len(planned)+1)
    else:
        planned,onsets,boundary=realtime_stop_prefix(notes,period,origin,stop,applied,preview_seed)
    field = 'logical_ns' if controlled else 'monotonic_ns'
    scheduled = notes[:-1]
    if controlled:
        errors = []
        for expected, actual in zip(planned, scheduled):
            assert (actual['port'], actual['bytes']) == (expected['port'], expected['bytes']), 'MIDI data/order'
            error = actual[field] - expected['deadline_ns']
            assert abs(error) <= 2, ('Absolute controlled pulse deadline', error, expected, actual)
            errors.append(error)
        metrics = dict(count=len(errors), scheduling_errors_ns=errors,
                       maximum_absolute_error_ns=max(map(abs, errors)))
    else:
        metrics = scheduling_metrics(planned, scheduled)
        assert metrics['within_event_profile'], ('D20 event scheduling profile', metrics)
    final = notes[-1]
    assert final['port'] == 1 and final['bytes'][:2] == [128, 60], 'Wrong forced Stop release'
    assert final['bytes'][2] in (0, planned[-1]['bytes'][2]), 'Wrong Stop velocity'
    tolerance = 2 if controlled else 0
    assert stop-tolerance <= final[field] <= applied+tolerance, 'Forced release outside identified Stop callback'
    actual_onsets = scheduled[::2]
    window_errors = [float(Fraction(b[field]-a[field]) - Fraction(period.numerator*1_000_000_000, 144))
                     for a,b in zip(actual_onsets, actual_onsets[period.denominator:])]
    release_errors = [b[field]-a[field] for a,b in zip(scheduled[1::2], scheduled[2::2])]
    if controlled:
        assert all(abs(error)<=2 for error in window_errors), 'Controlled rational window changed'
        assert all(abs(error)<=2 for error in release_errors), 'Controlled release/retrigger phase changed'
    return dict(kind='fractional-clock-continuity', pulse_ratio=[period.numerator, period.denominator],
                preview_seed=[preview_seed.numerator, preview_seed.denominator],
                onsets=len(onsets), scheduled_note_events=len(planned), forced_stop_releases=1,
                origin_ns=origin, stop_ns=stop, stop_applied_ns=applied,
                deadline_domain='logical' if controlled else 'monotonic',
                maximum_quantisation_offset_ns=max(abs(p['deadline_ns']-p['intent_ns']) for p in planned),
                complete_ratio_windows=len(window_errors), maximum_window_residual_ns=max(map(abs,window_errors),default=0),
                release_order_checks=len(release_errors),
                metrics=metrics, realtime_stop_boundary=boundary, passed=True)


def reconcile_note_stream(events, segments, kind):
    """Every native note must belong to exactly one validated capture window.

    This fixture never plays during setup, between rates, or after final Stop.
    No setup or cleanup note exemption is therefore permitted.
    """
    assert kind in (3, 11) and segments
    previous = -1
    for segment in segments:
        after, cursor = segment['after'], segment['cursor']
        assert type(after) is int and type(cursor) is int
        assert previous <= after < cursor, 'Overlapping or invalid capture windows'
        previous = cursor
    count = 0
    for event in events:
        if event.get('kind') not in (3, 11):
            continue
        assert event['kind'] == kind, 'Mixed native clock domains'
        if event['bytes'][0] & 240 not in (128, 144):
            continue
        owners = sum(s['after'] < event['sequence'] <= s['cursor'] for s in segments)
        assert owners == 1, ('Note outside validated capture windows', event)
        count += 1
    assert count > 0, 'Empty native note population'
    return dict(kind='fractional-full-stream-accounting', note_events=count,
                capture_windows=len(segments), unaccounted_note_events=0, passed=True)
