"""Probe (suspected-defects S24): turning a mask back to X ("off") on the Masks page.

S24: the mask handlers store "off" as -1, never nil (`v == -1 and nil or v` always yields v).
Human decision 2026-09-11: probe first; off, then save/reload and undo. X means no mask lock:
README 597 "The default mask value will apply to all steps that don't have a specific mask lock
set", and without a channel mask the pattern values play (README 570: masks override pattern
values). Channel 1 plays C D E F at velocities 127/117/107/97 on steps 1-4.

Stages (each turned back to X must play as if never set):
  A  channel velocity mask 50, then back to X;
  B  held step 2 trig mask N (step silent), then back to X;
  C  held step 3 velocity lock 50, then back to X.
Then an autosave restart must play the same phrase (save/reload), and one Memory-page step back
is recorded as an observation (characterisation, not asserted). Every stage is observed
before any assertion so one run reports them all.
"""
BASELINE = [(60, 127), (62, 117), (64, 107), (65, 97)]


def heard(c, label, expected):
    """One cycle of note-ons (pitch, velocity) as heard, without asserting."""
    controlled = c.clock_mode == 'controlled-experimental'
    field = 'logical_ns' if controlled else 'monotonic_ns'
    before = c.snapshot()['midi_count']; c.tap(1, 8); c.elapse(2 * 4 / 6 + .2)
    state = c.snapshot(); c.tap(1, 8); c.wait(lambda s: not s['midi_capture']['outstanding'])
    ons = [m for m in state['midi'] if m['index'] > before and m['bytes'][0] == 144 and m['bytes'][2] > 0]
    cycle = [(m['bytes'][1], m['bytes'][2]) for m in ons if ons and (m[field] - ons[0][field]) / 1e9 < 4 / 6 - .05]
    c.results.append(dict(kind='mask-off-probe', stage=label, expected=expected, heard=cycle))
    return (label, expected, cycle)


def hold_turn(c, step, turns):
    c.action(type='grid', x=step, y=4, state=1)
    try: c.enc(3, turns)
    finally: c.action(type='grid', x=step, y=4, state=0)
    c.elapse(.3)


def mask_off_probe(c):
    from driver import Driver
    rows = []
    c.configure(); c.enc(1, -4); c.enc(2, 1)                     # Masks page, Vel selector
    c.enc(3, 51); rows.append(heard(c, 'A channel velocity 50', [(n, 50) for n, _ in BASELINE]))
    c.enc(3, -51); rows.append(heard(c, 'A channel velocity back to X', BASELINE))
    c.enc(2, -2)                                                 # Trig selector
    hold_turn(c, 2, 1); rows.append(heard(c, 'B step 2 trig N', [BASELINE[0]] + BASELINE[2:]))
    hold_turn(c, 2, -1); rows.append(heard(c, 'B step 2 trig back to X', BASELINE))
    c.enc(2, 2)                                                  # Vel selector
    hold_turn(c, 3, 51); rows.append(heard(c, 'C step 3 velocity 50', BASELINE[:2] + [(64, 50), BASELINE[3]]))
    hold_turn(c, 3, -51); rows.append(heard(c, 'C step 3 velocity back to X', BASELINE))
    final = rows[-1][2]
    marks = {p.name: p.stat().st_mtime_ns for p in c.data_directory.glob('autosave.*')}
    for _ in range(3): c.elapse(21)
    c.wait(lambda _: all((c.data_directory/n).is_file() and (c.data_directory/n).stat().st_mtime_ns != marks.get(n)
                         for n in ('autosave.ptn', 'autosave.pset')))
    c.finish()
    out = c.out/'restarted'; out.mkdir()
    d = Driver(out, project_seed=c.data_directory, **c.launch_options)
    try:
        rows.append(heard(d, 'after autosave restart (same as before restart)', final))
        d.tap(3, 8); d.enc(1, -5); d.enc(1, 2); d.screen_header('Ch. 1 Memory')
        d.enc(3, -1); undo = heard(d, 'Memory one step back (observation)', None)
    except Exception:
        try: d.finish()
        except Exception: pass
        raise
    d.finish()
    c.results.append(dict(kind='mask-off-probe-undo-observation', heard=undo[2]))
    wrong = [(label, dict(expected=expected, heard=cycle)) for label, expected, cycle in rows if cycle != expected]
    assert not wrong, ('Mask turned back to X does not play as unset', wrong)
    c.results.append(dict(kind='mask-off-probe-summary', passed=True))
