from contract.duration_assertions import assert_durations

def integral_clock_divisions(c,slow=False):
    from fractions import Fraction
    from midi_window import MidiWindow
    # Fixed public selector labels; expected seconds follow the musical ratio,
    # never Mosaic's clock or lattice implementation.
    labels=['x16','x12','x8','x6','x5.3','x5','x4','x3','x2.6','x2','x1.5','x1.3',
      '/1','/1.5','/2','/2.6','/3','/4','/5','/5.3','/6','/7','/8','/9','/10','/11','/12','/13','/14','/15','/16',
      '/17','/19','/21','/23','/24','/25','/27','/29','/32','/40','/48','/56','/64','/96','/101','/128']
    c.ui.configure();c.ui.channel_page('clock_mods','midi_config')
    selected=13;tested=[]
    for index,label in enumerate(labels,1):
        number=Fraction(label[1:]);factor=1/number if label[0]=='x' else number
        pulses=24*factor
        if pulses.denominator!=1 or (factor>16)!=slow:continue
        c.ui.turn(3,selected-index);c.ui.press_key(3);selected=index
        expected=[(1,[144,n,v]) for n,v in zip([60,62,64,65],[127,117,107,97])]
        capture=MidiWindow(c.snapshot()['midi_count']);c.ui.play();capture.extend(c.snapshot())
        remaining=float(8*factor/6)
        # Public controlled advances are bounded to60s. Small chunks retain
        # responsive clients and preserve that runtime limit in both lanes.
        while remaining>0:
            chunk=min(30,remaining);c.elapse(chunk);remaining-=chunk;capture.extend(c.snapshot())
        c.wait(lambda state:len(capture.extend(state).note_ons())>=9,timeout=3)
        notes=capture.note_ons()
        assert [(m['port'],m['bytes']) for m in notes]==[expected[i%4] for i in range(len(notes))],label
        c.ui.stop();c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(m[field]-notes[0][field])/1e9-float(i*factor/6) for i,m in enumerate(notes)]
        assert all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),(label,errors)
        assert_durations(c,notes,[float(factor)]*8,events=capture.events)
        c.results.append(dict(kind='clock-division-phrase',label=label,pulses=int(pulses),period_seconds=float(factor/6),complete_cycles=2,onsets=len(notes),max_phase_error_seconds=max(abs(x) for x in errors),passed=True));tested.append(label)
    assert len(tested)==(16 if slow else 24),tested


def integral_clock_divisions_slow(c):
    return integral_clock_divisions(c, slow=True)
