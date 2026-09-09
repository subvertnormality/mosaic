from shuffle_matrix import shuffle_matrix
from random_note_domains import random_note_domains
from scale_slot_matrix import scale_slot_matrix
from pitch_lock_isolation import pitch_lock_isolation
from project_dialog_lifecycle import project_dialog_while_playing
from persisted_ranges import saved_range_compatibility
from persisted_ranges import rejected_manual_range
from persisted_ranges import rejected_saved_range
from range_rejection import queued_global_length_transitions
from range_rejection import accepted_live_range_transitions
from range_rejection import offset_range_rates,offset_scale_range_clipping
from range_rejection import offset_range_clipping
from range_rejection import global_range_clipping
from range_rejection import rejected_range_channel_isolation
from range_rejection import rejected_range_while_playing
from range_rejection import rejected_range
from mask_gestures import multiheld_keyboard
from mask_gestures import held_keyboard_chord
from mask_gestures import trig_gesture_all_steps
from mask_quantisation import mask_full_chord_inheritance
from mask_quantisation import mask_full_quantisation
from mask_quantisation import mask_scale_snap
from mask_clearing import mask_clear_recorded_chord
from mask_clearing import mask_clear_last_steps
from mask_clearing import mask_clear_combined_chords
from mask_clearing import mask_clear_attributes
from numeric_merging import fractional_length_mask_merge
from numeric_merging import numeric_length_merge
from numeric_merging import velocity_zero_boundary
from numeric_merging import lydian_octave_boundary
from numeric_merging import numeric_velocity_merge
from numeric_merging import merge_rounding
from numeric_merging import merge_mode_cycle
from numeric_merging import numeric_note_merge
from recording_lifetimes import recording_ten_slots
from recording_lifetimes import recording_stop_safety
from trig_parameter_interactions import sparse_editor_domain
from trig_parameter_interactions import cc_encoder_domain
from recording_lifetimes import recording_lifetime,recording_nrpn
from patch_params import patch_sparse_slide
from patch_params import patch_ten_slot_slides
from patch_params import patch_channel_clear_isolation
from patch_params import patch_clear_mask_boundary
from patch_params import patch_slide_live_destination
from patch_params import patch_slide_trigless
from patch_params import patch_slide_song_cutoff
from patch_params import patch_slide_live_division
from patch_params import patch_slide_timing
from patch_params import patch_adjacent_locks
from patch_params import patch_lock_precedence
from patch_params import patch_sparse_range
from patch_params import patch_restart
from patch_params import patch_nrpn_bytes
from patch_params import patch_muted_recall
"""Mosaic-owned physical-input regressions; independent literal musical oracles."""
from driver import REPO,Driver,digest

def four_notes(c):
    c.configure()
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    c.tap(5,8);c.tap(5,8);c.tap(4,3)
    c.led_values([(4,3)],[12])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(67,97)]])
    # Selected pattern's top LED deliberately alternates 3-1 / 3+1.
    # Observe both states, then compare the same visible phase in both clocks.
    # Do not mask this LED or weaken the full-grid admission comparison.
    c.led_values([(1,1)],[4]);c.led_values([(1,1)],[2])
    c.results.append(dict(kind='selected-pattern-blink-cycle',levels=[4,2],passed=True))

def next_trig_cutoff(c):
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(5,4);c.tap(5,8);c.tap(5,3);c.tap(3,8);c.tap(5,8)
    c.hold_tap((1,4),(4,4));c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,15,2,15])
    notes=c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(67,100)]],timeout=6)
    assert_durations(c,notes,[2,1,1]*2)

def assert_durations(c,notes,lengths,events=None):
    assert lengths and len(notes)>=len(lengths),'Missing duration observations'
    state=c.snapshot();rows=[]
    events=state['midi'] if events is None else events
    for note,length in zip(notes,lengths):
        off=next(m for m in events if m['index']>note['index'] and m['port']==note['port'] and m['bytes']==[128+(note['bytes'][0]&15),note['bytes'][1],note['bytes'][2]])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        actual=(off[field]-note[field])/1e9
        rows.append(dict(pitch=note['bytes'][1],expected_seconds=length/6,actual_seconds=actual,error_ms=1000*(actual-length/6)))
    c.results.append(dict(kind='duration',rows=rows))
    # Two nanoseconds cover native integer deadline rounding; no wall jitter in D.
    tolerance_ms=.000002 if c.clock_mode=='controlled-experimental' else 10
    assert all(abs(row['error_ms'])<=tolerance_ms for row in rows),rows

def restore_length(c):
    # The source length must survive temporary interruption by an inserted trig.
    next_trig_cutoff(c)
    c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,5,5,15])
    notes=c.playback([(1,[144,60,127]),(1,[144,67,100])],timeout=6)
    assert_durations(c,notes,[4,1]*2)
    # Reinsert the collision: the same authored length must shorten again.
    c.tap(3,4)
    c.led_values([(x,4) for x in range(1,6)],[15,5,15,2,15])
    notes=c.playback([(1,[144,60,127]),(1,[144,64,107]),(1,[144,67,100])],timeout=6)
    assert_durations(c,notes,[2,1,1]*2)

def wrapped_length(c,same_pitch=False):
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(15,7);c.hold_tap((15,7),(2,4))
    c.led_values([(15,7),(16,7),(1,4),(2,4)],[15,5,15,2])
    if not same_pitch:
        c.tap(5,8);c.tap(12,8);c.tap(15,3)
        c.led_values([(15,3)],[12])
    notes=c.playback([(1,[144,60,127]),(1,[144,60 if same_pitch else 67,100])],timeout=38)
    assert_durations(c,notes,[1,2]*2)
    if not same_pitch:
        # Page49-64's empty selected-pattern top cell has base brightness1,
        # with the same +/-1 selection animation as the authored-note page.
        c.led_values([(1,1)],[0]);c.led_values([(1,1)],[2])
        c.results.append(dict(kind='selected-pattern-blink-cycle',levels=[0,2],passed=True))


def pattern_duration_domain(c,lengths=range(1,65),channel_end=64):
    # The documented finite duration domain is1..64 sixteenth-note steps.
    # Author each duration using grid gestures; observe every cell and MIDI off.
    c.configure();c.hold_tap((1,4),((channel_end-1)%16+1,(channel_end-1)//16+4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for length in lengths:
        if length>1:c.hold_tap(cells[0],cells[length-1])
        c.led_values(cells,[15 if step==1 else 5 if step<=length else 2 for step in range(1,65)])
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        def recorded(state):return [m for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes'][0] in (128,144)]
        # Native capture retains all events; fewer snapshots cannot hide an
        # early release because the emission-time and order assertions follow.
        c.elapse(max(0,length/6-.12))
        state=c.wait(lambda state:any(m['bytes']==[128,60,127] for m in recorded(state)),timeout=13)
        emitted=recorded(state)
        assert emitted[0]['bytes']==[144,60,127],emitted
        release=next(m for m in emitted if m['bytes'][0]==128)
        assert release['bytes']==[128,60,127]
        elapsed=(release[field]-emitted[0][field])/1e9
        assert abs(elapsed-length/6)<=tolerance,dict(length=length,actual=elapsed,expected=length/6)
        # At the full64-step boundary another onset may follow the completed
        # note before Stop arrives. Its ordering and cleanup are still required.
        assert [m['bytes'] for m in emitted[:2]]==[[144,60,127],[128,60,127]],emitted
        assert all(m['bytes'] in ([144,60,127],[128,60,127]) for m in emitted)
        c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
        c.results.append(dict(kind='pattern-duration-domain',steps=length,expected_seconds=length/6,actual_seconds=elapsed,first_on=emitted[0],first_off=release))


def pattern_duration_controls(c):
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(5,4);c.tap(5,8);c.tap(5,3);c.tap(3,8);c.tap(5,8)
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    def phrase(length):
        c.led_values(cells,[15 if step in (1,5) else 5 if 1<step<=length else 2 for step in range(1,65)])
        notes=c.playback([(1,[144,60,127]),(1,[144,67,100])],cycles=2)
        assert_durations(c,notes,[length,1]*2)
    def long_hold(cell):
        c.action(type='grid',x=cell[0],y=cell[1],state=1)
        try:c.elapse(1.1)
        finally:c.action(type='grid',x=cell[0],y=cell[1],state=0)
        c.elapse(.06)
    phrase(1);c.hold_tap((1,4),(3,4));phrase(3)
    long_hold((1,4));phrase(1)
    # Empty sources must neither create a trigger nor leave hidden length data
    # that changes the existing phrase. Test both the combo and lone hold.
    c.hold_tap((2,4),(4,4));phrase(1)
    long_hold((2,4));phrase(1)
    c.hold_tap((1,4),(4,4));phrase(4)

def live_pattern_duration(c):
    c.configure();c.hold_tap((1,4),(8,4));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.hold_tap((1,4),(4,4))
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    def onsets(state):return [m for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127]]
    state=c.wait(lambda state:len(onsets(state))>=1)
    first=onsets(state)[0]
    c.hold_tap((1,4),(2,4))
    now=c.logical_ns if c.clock_mode=='controlled-experimental' else c.snapshot()['diagnostics']['monotonic_ns']
    assert now<first[field]+round(2e9/6),'Shortening gesture missed the pending note window'
    state=c.wait(lambda state:len(onsets(state))>=2)
    second=onsets(state)[1]
    c.hold_tap((1,4),(4,4))
    now=c.logical_ns if c.clock_mode=='controlled-experimental' else c.snapshot()['diagnostics']['monotonic_ns']
    assert now<second[field]+round(2e9/6),'Extension gesture missed the pending note window'
    state=c.wait(lambda state:len(onsets(state))>=3)
    third=onsets(state)[2]
    c.wait(lambda state:any(m['index']>third['index'] and m['bytes']==[128,60,127] for m in state['midi']))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    state=c.snapshot()
    actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    expected=[(1,[144,60,127]),(1,[128,60,127])]*3
    assert actual==expected,dict(expected=expected,actual=actual)
    c.results.append(dict(kind='live-duration-exact-midi',expected=expected,actual=actual))
    # Editing the stored duration affects later onsets. Each already-emitted
    # note retains its scheduled release; neither edit retroactively cuts it.
    assert_durations(c,[first,second,third],[4,2,4])
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert all(abs((b[field]-a[field])/1e9-8/6)<=tolerance for a,b in ((first,second),(second,third)))
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    c.led_values(cells,[15 if step==1 else 5 if step<=4 else 2 for step in range(1,65)])
    notes=c.playback([(1,[144,60,127])],cycles=2)
    assert_durations(c,notes,[4,4])


def euclidean_workflow(c):
    # Migrated from emulator tests/mosaic_euclidean.py; independent3-in-8 table.
    baseline=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    c.configure();c.hold_tap((1,4),(8,4))
    c.tap(5,8);c.tap(5,8)
    for x,y in [(5,3),(6,2),(7,1),(8,6)]:c.tap(x,y)
    c.tap(3,8);c.tap(5,8) # trig editor
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='eight-step-loop-baseline',passed=True))
    c.tap(14,2) # Euclidean
    c.tap(2,2) # broad fader minimum: one pulse
    for _ in range(2):c.tap(10,2)
    c.tap(2,3)
    for _ in range(7):c.tap(10,3)
    c.tap(16,8)
    # The manual distinguishes dim overlaps and bright newly proposed steps.
    # Verify both blink phases and all64 cells against fixed authored/candidate
    # sets; no application rhythm calculation supplies the expected positions.
    cells=[((step-1)%16+1,(step-1)//16+4) for step in range(1,65)]
    original={1,2,3,4}
    proposed={step for step in range(1,65) if (step-1)%8+1 in (1,4,7)}
    for overlap,new in ((0,15),(3,12)):
        c.led_values(cells,[overlap if step in original and step in proposed else new if step in proposed else 15 if step in original else 2 for step in range(1,65)])
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='preview-does-not-paint',passed=True))
    c.tap(14,8);c.led_values([(x,4) for x in range(1,9)],[15]*4+[2]*4)
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='cancel-retains-pattern',passed=True))
    c.tap(16,8);c.tap(12,8) # shift right: {2,5,8}
    c.led_values([(2,4),(5,4),(8,4)],[0,15,15]);c.tap(16,8)
    shifted={step for step in range(1,65) if (step-1)%8+1 in (2,5,8)}
    painted=original.symmetric_difference(shifted)
    c.led_values(cells,[15 if step in painted else 2 for step in range(1,65)])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(65,97),(67,100),(62,100)]])
    c.results.append(dict(kind='workflow-check',name='shifted-paint-xor',passed=True))
    c.tap(16,8);c.led_values([(2,4),(5,4),(8,4)],[15,0,0]);c.tap(16,8)
    c.playback(baseline);c.results.append(dict(kind='workflow-check',name='repaint-restores-original',passed=True))
    c.tap(16,8);c.tap(10,8) # left: back to {1,4,7}
    c.led_values([(1,4),(4,4),(7,4)],[0,0,15]);c.tap(12,8);c.tap(11,8)
    c.led_values([(1,4),(4,4),(7,4)],[0,0,15]);c.tap(16,8)
    c.playback([(1,[144,n,v]) for n,v in [(62,117),(64,107),(71,100)]])
    c.results.append(dict(kind='workflow-check',name='left-and-center-reset',passed=True))
    c.tap(16,8);c.led_values([(1,4),(4,4),(7,4)],[15,15,0]);c.tap(16,8);c.playback(baseline)
    c.tap(9,2) # fill32, exceeding length8: every step selected
    c.tap(16,8);c.led_values([(1,4),(4,4),(5,4),(16,7)],[0,0,15,15]);c.tap(16,8)
    c.led_values([(x,y) for y in range(4,8) for x in range(1,17)],[2]*4+[15]*60)
    c.playback([(1,[144,n,100]) for n in [67,69,71,62]]);c.results.append(dict(kind='workflow-check',name='dense-fill-boundary',passed=True))

# Independent literal 3/3/2 segment tables; no application algorithm import.
TRESILLO_STEPS={8:[3,6],16:[3,9,15],24:[3,12,21],32:[3,15,27],
      40:[3,18,33],48:[3,16,21,34,39],56:[3,16,24,37,45],
      64:[3,16,27,40,51,64]}

def tresillo_setup(c):
    c.configure();c.tap(5,8)
    for x in range(1,5):c.tap(x,4)
    c.tap(5,8)
    for x in range(1,17):
        c.action(type='key',n=1,state=1);c.elapse(.3)
        c.tap(x,7-((x-1)%6));c.action(type='key',n=1,state=0)
    c.tap(3,8);c.tap(5,8);c.tap(13,2);c.tap(12,3)
    c.tap(2,2);c.tap(10,2);c.tap(2,3);c.tap(10,3)
    c.enc(1,1);c.enc(3,-8)
    from frame_oracle import header,matches
    expected=header('Trig editor options',selected=2,tabs=2)
    c.wait(lambda state:matches(state,expected))
    c.results.append(dict(kind='screen-header',expected='Trig editor options',selected=2,tabs=2,matched=True))

def tresillo_rhythm(c,length,steps):
    c.tap(3,8);c.hold_tap((1,4),((length-1)%16+1,4+(length-1)//16));c.tap(5,8)
    c.tap(16,8)
    first=((steps[0]-1)%16+1,4+(steps[0]-1)//16)
    c.led_values([first],[15]);c.tap(16,8)
    cells=[(x,y) for y in range(4,8) for x in range(1,17)]
    c.led_values(cells,[15 if i%length+1 in steps else 2 for i in range(64)])
    pitches=[60,62,64,65,67,69]
    velocities=[127,117,107,97]+[100]*60
    expected=[(1,[144,pitches[((s-1)%16)%6],velocities[s-1]]) for s in steps]
    notes=c.playback(expected,cycles=2,timeout=4,settle_seconds=length/3-.1)
    # Literal candidate positions imply audible inter-onset spacing at90 BPM.
    # Include the wraparound gap; pitch order alone cannot prove the rhythm.
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    rows=[]
    for i,(left,right) in enumerate(zip(notes,notes[1:])):
        gap=(steps[(i+1)%len(steps)]-steps[i%len(steps)])%length
        if gap==0:gap=length
        actual=(right[field]-left[field])/1e9
        rows.append(dict(from_step=steps[i%len(steps)],to_step=steps[(i+1)%len(steps)],expected_seconds=gap/6,actual_seconds=actual))
    c.results.append(dict(kind='tresillo-timing',length=length,steps=steps,rows=rows))
    assert len(rows)>=2*len(steps) and all(abs(x['actual_seconds']-x['expected_seconds'])<=tolerance for x in rows),rows
    c.tap(16,8);c.led_values([first],[0]);c.tap(16,8);c.led_values(cells,[2]*64)

def tresillo_multipliers(c):
    tresillo_setup(c);c.results.append(dict(kind='workflow-check',name='tresillo-input-setup',passed=True))
    for i,(length,steps) in enumerate(TRESILLO_STEPS.items()):
        if i:c.enc(3,1)
        tresillo_rhythm(c,length,steps);c.results.append(dict(kind='workflow-check',name='multiplier-'+str(length),passed=True))

def tresillo_drum_boundary(c):
    tresillo_setup(c);c.tap(13,3);c.enc(3,7)
    tresillo_rhythm(c,64,list(range(1,65,8)));c.results.append(dict(kind='workflow-check',name='drum-bank-64-step-tresillo',passed=True))



def rhythm_bank_workflow(c):
    # Literal decoded bank entries, independent of drum_ops implementation.
    # Pattern2 covers all five drum banks including the empty fifth bank.
    oracle={'drum_pattern_2':{'1':[3,16],'2':[1,9],'3':[5,13],
      '4':[1,3,5,7,9,11,13,15],'5':[]},
      'numeric_prime_1_factor_1':{'1':[5,13],'2':[1],'3':[9],'4':[1,5,9,13]}}
    def silence(c):
        before=c.snapshot()['midi_count'];c.tap(1,8)
        c.elapse(16/6*2+.1);c.tap(1,8)
        state=c.snapshot()
        emitted=[m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        assert emitted==[] and state['midi_capture']['outstanding']==[],emitted
        c.results.append(dict(kind='silence',complete_cycles=2,emitted=emitted))
    c.configure();c.hold_tap((1,4),(16,4))
    c.tap(5,8)
    for x in range(1,5):c.tap(x,4) # empty pattern, retain routing
    c.tap(5,8)
    for x in range(1,17):c.tap(x,7-((x-1)%7))
    c.tap(3,8);c.tap(5,8)
    cells=[(x,y) for y in range(4,8) for x in range(1,17)]
    c.led_values(cells,[2]*64);silence(c);c.results.append(dict(kind='workflow-check',name='empty-pattern',passed=True))
    def paint(steps):
        c.tap(16,8)
        # Nonempty previews flash coherently. Empty banks have no step flashes.
        if steps:c.led_values([((steps[0]-1)%16+1,4)],[15])
        else:c.led_values([(14,8)],[15])
        c.tap(16,8)
        c.led_values(cells,[15 if i%16+1 in steps else 2 for i in range(64)])
        if steps:
            pitches=[60,62,64,65,67,69,71]
            velocities=[127,117,107,97]+[100]*12
            c.playback([(1,[144,pitches[(s-1)%7],velocities[s-1]]) for s in steps],cycles=2,timeout=4,settle_seconds=16/3-.1)
        else:silence(c)
        c.tap(16,8)
        if steps:c.led_values([((steps[0]-1)%16+1,4)],[0])
        else:c.led_values([(14,8)],[15])
        c.tap(16,8);c.led_values(cells,[2]*64)
    c.tap(12,2);c.tap(2,2);c.tap(10,2) # drum pattern2
    for bank in range(1,6):
        c.tap(11+bank,3);paint(oracle['drum_pattern_2'][str(bank)]);c.results.append(dict(kind='workflow-check',name='drum-bank-'+str(bank),passed=True))
    c.tap(15,2);c.tap(2,2);c.tap(2,3) # numeric prime1, factor1
    for bank in range(1,5):
        c.tap(11+bank,3);paint(oracle['numeric_prime_1_factor_1'][str(bank)]);c.results.append(dict(kind='workflow-check',name='numeric-mask-'+str(bank),passed=True))



# Ported editor-range fixture; literal pitches and velocities remain independent.
def editor_shift_tap(c,x,y):
    c.action(type='key',n=1,state=1);c.elapse(.3)
    try:c.tap(x,y)
    finally:c.action(type='key',n=1,state=0)

def editor_range_hold(c,x,y):
    c.action(type='grid',x=x,y=y,state=1)
    try:c.elapse(1.1)
    finally:c.action(type='grid',x=x,y=y,state=0)

def editor_note_ranges(c):
    c.configure();c.tap(5,8);c.tap(5,8)
    def choose(y,note):
        c.tap(4,y);c.led_values([(4,y)],[12]);c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107)]]+[(1,[144,note,97])])
    choose(1,71);c.results.append(dict(kind='workflow-check',name='initial-note-range',passed=True))
    c.tap(14,8);choose(1,72);c.results.append(dict(kind='workflow-check',name='first-up-step',passed=True))
    c.tap(14,8);choose(1,74);c.results.append(dict(kind='workflow-check',name='second-up-step',passed=True))
    c.tap(16,8);choose(1,72);c.results.append(dict(kind='workflow-check',name='first-down-step',passed=True))
    c.tap(16,8);choose(1,71);c.results.append(dict(kind='workflow-check',name='second-down-step',passed=True))
    editor_range_hold(c,14,8);choose(1,83);c.results.append(dict(kind='workflow-check',name='hold-to-highest-range',passed=True))
    c.tap(14,8);choose(1,83);c.results.append(dict(kind='workflow-check',name='highest-range-clamp',passed=True))
    editor_range_hold(c,16,8);choose(7,48);c.results.append(dict(kind='workflow-check',name='hold-to-lowest-range',passed=True))
    c.tap(16,8);choose(7,48);c.results.append(dict(kind='workflow-check',name='lowest-range-clamp',passed=True))
    c.tap(15,8);choose(4,65);c.results.append(dict(kind='workflow-check',name='center-restores-root-page',passed=True))

VELOCITIES=[127,117,107,97,87,78,68,58,48,39,29,19,9,0]

def editor_velocity_ranges(c):
    c.configure();c.tap(5,8);c.tap(5,8);c.tap(5,8)
    def choose(y,value):
        c.tap(4,y);c.led_values([(4,y)],[12])
        c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107)]]+([(1,[144,65,value])] if value else []))
    for y,value in enumerate(VELOCITIES[:7],1):choose(y,value);c.results.append(dict(kind='workflow-check',name='velocity-'+str(value),passed=True))
    c.tap(16,8);choose(1,117);c.results.append(dict(kind='workflow-check',name='first-velocity-range-step',passed=True))
    c.tap(16,8);choose(1,107);c.results.append(dict(kind='workflow-check',name='second-velocity-range-step',passed=True))
    c.tap(15,8);choose(1,117);c.results.append(dict(kind='workflow-check',name='velocity-range-step-back',passed=True))
    editor_range_hold(c,16,8)
    for y,value in enumerate(VELOCITIES[7:],1):choose(y,value);c.results.append(dict(kind='workflow-check',name='velocity-'+str(value),passed=True))
    c.tap(16,8);choose(7,0);c.results.append(dict(kind='workflow-check',name='lowest-velocity-range-clamp',passed=True))
    editor_range_hold(c,15,8);choose(1,127);c.results.append(dict(kind='workflow-check',name='hold-to-highest-velocity-range',passed=True))
    c.tap(15,8);choose(1,127);c.results.append(dict(kind='workflow-check',name='highest-velocity-range-clamp',passed=True))

def editor_step_groups(c):
    c.configure();c.tap(5,8)
    for y in range(5,8):
        for x in range(1,5):c.tap(x,y)
    c.tap(5,8)
    for x in range(1,5):editor_shift_tap(c,x,8-x)
    for group in range(4):
        c.tap(9+group,8);c.led_values([(x,8-x) for x in range(1,5)],[12]*4)
    c.results.append(dict(kind='workflow-check',name='shift-copies-notes-to-four-groups',passed=True))
    c.tap(5,8)
    for x in range(1,5):editor_shift_tap(c,x,2)
    for group in range(4):
        c.tap(9+group,8);c.led_values([(x,2) for x in range(1,5)],[12]*4)
    c.results.append(dict(kind='workflow-check',name='shift-copies-velocities-to-four-groups',passed=True))
    c.tap(3,8)
    for group in range(4):
        c.hold_tap((1,4+group),(4,4+group))
        c.playback([(1,[144,n,117]) for n in [60,62,64,65]])
        c.results.append(dict(kind='workflow-check',name='play-step-group-'+str(group+1),passed=True))



def note_pattern_selectors(c):
    # Author distinguishable single-note patterns through the normal editor.
    c.configure();pitches=[60,62,64,65,67,69,71];authored={}
    for slot in range(1,17):
        c.tap(5,8);c.tap(slot,1)
        if slot==1:
            for x in (2,3,4):c.tap(x,4)
        else:c.tap(1,4)
        c.tap(5,8);offset=(slot-1)%7;c.tap(1,7-offset)
        authored[slot]=pitches[offset];c.tap(3,8)
    assigned=1
    c.tap(5,8);c.tap(5,8)
    for pass_index,gesture in enumerate(('shift','hold'),1):
        for slot in range(1,17):
            if gesture=='shift':editor_shift_tap(c,slot,1)
            else:editor_range_hold(c,slot,1)
            offset=(slot-1+pass_index)%7
            assert authored[slot]!=pitches[offset]
            c.tap(1,7-offset);c.led_values([(1,7-offset)],[12])
            authored[slot]=pitches[offset];c.tap(3,8)
            if assigned!=slot:c.tap(assigned,2);c.tap(slot,2)
            assigned=slot;c.led_values([(slot,2)],[15])
            c.playback([(1,[144,authored[slot],127 if slot==1 else 100])],cycles=2,timeout=3,settle_seconds=4/3-.1)
            c.results.append(dict(kind='pattern-selector',gesture=gesture,slot=slot,pitch=authored[slot],passed=True))
            c.tap(5,8);c.tap(5,8)
    # Holding a top-row cell must not damage a previously edited pattern.
    # Revisit every assignment after the whole selector/edit history.
    c.tap(3,8)
    for slot in range(1,17):
        if assigned!=slot:c.tap(assigned,2);c.tap(slot,2)
        assigned=slot
        c.playback([(1,[144,authored[slot],127 if slot==1 else 100])],cycles=2,timeout=3,settle_seconds=4/3-.1)
        c.results.append(dict(kind='pattern-selector-retained',slot=slot,pitch=authored[slot],passed=True))


def editor_hold_boundaries(c):
    import time
    c.configure();c.tap(5,8);c.tap(5,8)
    before=.999999999 if c.clock_mode=='controlled-experimental' else .95
    after=1.000000001 if c.clock_mode=='controlled-experimental' else 1.05
    baseline=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107)]]
    def hold(x,seconds,expected_long,interrupt=False):
        logical_start=c.logical_ns;t0=time.monotonic_ns()
        c.action(type='grid',x=x,y=8,state=1);t1=time.monotonic_ns()
        if interrupt:
            c.elapse(.5);c.tap(4,3);c.elapse(.6)
        else:c.elapse(seconds)
        t2=time.monotonic_ns();logical_end=c.logical_ns
        c.action(type='grid',x=x,y=8,state=0);t3=time.monotonic_ns()
        lower=(t2-t1)/1e9;upper=(t3-t0)/1e9
        c.results.append(dict(kind='hold-input-bounds',x=x,interrupted=interrupt,
            expected_long=expected_long,logical_seconds=(logical_end-logical_start)/1e9,
            wall_lower_seconds=lower,wall_upper_seconds=upper))
        if c.clock_mode=='real-time' and not interrupt:
            assert lower>1 if expected_long else upper<1, 'Host input delivery crossed the intended one-second hold boundary'
        c.elapse(.06)
    for label,duration,pitch in [('before',before,72),('after',after,83),('cancelled',0,71)]:
        c.tap(15,8) # Return the displayed note range to the root page.
        hold(14,duration,label=='after',interrupt=label=='cancelled')
        c.tap(4,1);c.led_values([(4,1)],[12])
        c.playback(baseline+[(1,[144,pitch,97])],cycles=2,timeout=3,settle_seconds=4/3-.1)
        c.results.append(dict(kind='editor-hold-boundary',editor='note',boundary=label,pitch=pitch,passed=True))
    c.tap(5,8) # Velocity editor; the fourth note now remains B4.
    for label,duration,velocity in [('before',before,117),('after',after,58),('cancelled',0,127)]:
        editor_range_hold(c,15,8) # Highest velocity range, independent of old offset.
        hold(16,duration,label=='after',interrupt=label=='cancelled')
        c.tap(4,1);c.led_values([(4,1)],[12])
        c.playback(baseline+[(1,[144,71,velocity])],cycles=2,timeout=3,settle_seconds=4/3-.1)
        c.results.append(dict(kind='editor-hold-boundary',editor='velocity',boundary=label,velocity=velocity,passed=True))


def pattern_grid_viewer(c):
    import base64
    from frame_oracle import render
    # Independent layout contract:16x4 sequencer dots,7px spacing,35px font.
    # Levels come only from the authored phrase and declared channel range.
    def viewer(channel,levels,label):
        assert len(levels)==64
        dots=render([(-3+x*7,-2+y*7,levels[(y-4)*16+x-1],'.') for y in range(4,8) for x in range(1,17)],font_size=35,antialias=1)
        # Official norns core/script.lua resets screen.aa(0) on script load.
        title=render([(0,9,10,'Channel '+str(channel)+' grid viewer')],antialias=1)
        def matches(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return (all(actual[(y*128+x)*4+k]==dots[(y*128+x)*4+k] for y in range(20,57) for x in range(120) for k in range(3))
              and all(actual[(y*128+x)*4+k]==title[(y*128+x)*4+k] for y in range(2,11) for x in range(114) for k in range(3)))
        row=dict(kind='grid-viewer-frame',channel=channel,label=label,expected_levels=levels,passed=False)
        c.results.append(row);c.wait(matches);row['passed']=True
    baseline=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    viewer(1,[15]*4+[2]*60,'wide-range-positive-oracle')
    c.tap(3,8);c.hold_tap((1,4),(4,4));c.tap(5,8)
    viewer(1,[15]*4+[0]*60,'shortened-range-clears-outside')
    c.playback(baseline,cycles=2,timeout=3,settle_seconds=4/3-.1)
    for channel in range(2,17):
        c.enc(2,1);viewer(channel,[2]*64,'unassigned-channel')
    c.enc(2,1);viewer(16,[2]*64,'upper-channel-clamp')
    c.enc(2,-15);viewer(1,[15]*4+[0]*60,'return-to-short-channel')
    c.enc(2,-1);viewer(1,[15]*4+[0]*60,'lower-channel-clamp')
    # Note and velocity editors have separate viewer selections but share the
    # same drawing/cache component. Page changes must not leak the previous view.
    c.tap(5,8);viewer(1,[15]*4+[0]*60,'note-page-short-channel')
    c.enc(2,15);viewer(16,[2]*64,'note-page-channel16')
    c.tap(5,8);viewer(1,[15]*4+[0]*60,'velocity-page-short-channel')
    c.enc(2,15);viewer(16,[2]*64,'velocity-page-channel16')
    c.tap(5,8);viewer(1,[15]*4+[0]*60,'trig-page-retains-own-selection')
    c.tap(5,8);viewer(16,[2]*64,'note-page-retains-own-selection')
    c.tap(3,8);c.tap(5,8);viewer(1,[15]*4+[0]*60,'return-from-channel-page')
    # Viewer selection is independent of the channel's pattern data and route.
    c.led_values([((s-1)%16+1,(s-1)//16+4) for s in range(1,65)],[15]*4+[2]*60)
    c.playback(baseline,cycles=2,timeout=3,settle_seconds=4/3-.1)


def inactive_note_priority(c,source_slot=1):
    assert source_slot in (1,3)
    def silence(label):
        before=c.snapshot()['midi_count'];c.tap(1,8);c.elapse(1.5);c.tap(1,8)
        state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        assert not notes and not state['midi_capture']['outstanding'],notes
        c.results.append(dict(kind='inactive-note-silence',phase=label,seconds=1.5,passed=True))
    def phrase(pitch,velocity,label):
        c.playback([(1,[144,pitch,velocity])],cycles=2,timeout=3,settle_seconds=4/3-.1)
        c.results.append(dict(kind='inactive-note-priority',source_slot=source_slot,phase=label,pitch=pitch,velocity=velocity,passed=True))
    c.configure();c.tap(5,8)
    for x in range(1,5):c.tap(x,4)
    c.tap(source_slot,1);c.tap(5,8);c.tap(1,3) # G4 on an inactive step.
    c.led_values([(1,3)],[12]);c.tap(3,8)
    if source_slot!=1:c.tap(1,2);c.tap(source_slot,2)
    silence('authored-inactive-pattern')
    c.tap(5,8);c.tap(2,1);c.tap(1,4);c.tap(3,8)
    c.tap(source_slot,2);c.tap(2,2)
    phrase(60,100,'rhythm-pattern-alone')
    c.hold_tap((15,8),(source_slot,2))
    c.led_values([(source_slot,2),(2,2),(15,8)],[2,15,15])
    phrase(67,100,'unassigned-note-source')
    c.tap(source_slot,2);phrase(67,100,'assigned-inactive-note-source')
    c.tap(2,2);c.tap(5,8);c.tap(source_slot,1);c.tap(1,4);c.tap(3,8)
    phrase(67,127 if source_slot==1 else 100,'later-trig-uses-authored-note')
    c.tap(5,8);c.tap(1,4);c.tap(3,8);silence('trig-removed-note-retained')


def priority_field_isolation(c,field,source_slot):
    assert field in ('velocity','length') and source_slot in (1,3)
    c.configure();c.tap(5,8)
    for x in range(1,5):c.tap(x,4)
    c.tap(source_slot,1);c.tap(1,4);c.hold_tap((1,4),(3,4))
    c.led_values([(1,4),(2,4),(3,4)],[15,5,5])
    c.tap(5,8);c.tap(1,3) # Inactive source will hold G4, velocity107, length3.
    c.tap(5,8);c.tap(1,3);c.tap(3,8);c.tap(5,8);c.tap(1,4)
    c.led_values([(1,4),(2,4),(3,4)],[2,2,2])
    c.tap(2,1);c.tap(1,4);c.tap(3,8);c.tap(1,2);c.tap(2,2)
    base=c.playback([(1,[144,60,100])],cycles=2,timeout=3,settle_seconds=4/3-.1)
    assert_durations(c,base,[1,1])
    if field=='length':c.action(type='key',n=1,state=1);c.elapse(.3)
    try:c.hold_tap((16,8),(source_slot,2));c.led_values([(16,8)],[15])
    finally:
        if field=='length':c.action(type='key',n=1,state=0)
    velocity=107 if field=='velocity' else 100
    length=3 if field=='length' else 1
    notes=c.playback([(1,[144,60,velocity])],cycles=2,timeout=3,settle_seconds=4/3-.1)
    assert_durations(c,notes,[length,length])
    # The same physical button addresses velocity normally and length with K1.
    # Selecting one priority source must preserve the other merge mode.
    if field=='velocity':c.action(type='key',n=1,state=1);c.elapse(.3)
    try:c.led_values([(16,8)],[2])
    finally:
        if field=='velocity':c.action(type='key',n=1,state=0)
    c.results.append(dict(kind='priority-field-isolation',field=field,source_slot=source_slot,pitch=60,velocity=velocity,length_steps=length,passed=True))


def inactive_note_positions(c):
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in range(1,5):c.tap(x,4)
    c.tap(3,1);c.tap(5,8)
    pitches=[60,62,64,65,67,69,71]
    cells=[((s-1)%16+1,(s-1)//16+4) for s in range(1,65)]
    for page in range(4):
        c.tap(9+page,8)
        selections=[(x,7-((page*16+x-1)%7)) for x in range(1,17)]
        for cell in selections:c.tap(*cell)
        c.led_values(selections,[12]*16)
    c.tap(3,8);c.tap(1,2);c.tap(3,2)
    def silence(label):
        c.led_values(cells,[2]*64)
        before=c.snapshot()['midi_count'];c.tap(1,8);c.elapse(64/3+.1);c.tap(1,8)
        state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        assert not notes and not state['midi_capture']['outstanding'],notes
        c.results.append(dict(kind='inactive-position-silence',phase=label,steps=64,complete_cycles=2,passed=True))
    def phrase(label):
        expected=[(1,[144,pitches[(s-1)%7],100]) for s in range(1,65)]
        notes=c.playback(expected,cycles=2,timeout=4,settle_seconds=64/3-.1)
        assert_durations(c,notes,[1]*128)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(b[field]-a[field])/1e9-1/6 for a,b in zip(notes,notes[1:])]
        assert len(errors)>=128 and all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),errors
        c.results.append(dict(kind='inactive-position-playback',phase=label,steps=64,complete_cycles=2,max_spacing_error_seconds=max(abs(x) for x in errors),passed=True))
    silence('all64-authored-without-trigs')
    c.tap(5,8);c.tap(2,1)
    for cell in cells:c.tap(*cell)
    c.led_values(cells,[15]*64);c.tap(3,8);c.tap(3,2);c.tap(2,2)
    c.hold_tap((15,8),(3,2));c.led_values([(3,2),(2,2),(15,8)],[2,15,15])
    phrase('unassigned-priority-source-all64')
    c.tap(3,2);phrase('assigned-inactive-priority-source-all64')
    c.tap(2,2);c.tap(5,8);c.tap(3,1)
    for cell in cells:c.tap(*cell)
    c.led_values(cells,[15]*64);c.tap(3,8);phrase('all64-later-activated')
    c.tap(5,8)
    for cell in cells:c.tap(*cell)
    c.tap(3,8);silence('all64-trigs-removed-again')


def all_note_priorities(c):
    c.configure();c.tap(5,8)
    for x in range(1,5):c.tap(x,4)
    pitches=[60,62,64,65,67,69,71]
    # Two base-seven digits make a distinct musical fingerprint for each slot.
    for slot in range(1,17):
        c.tap(slot,1);c.tap(5,8)
        c.tap(1,7-(slot-1)%7);c.tap(2,7-(slot-1)//7)
        c.tap(3,8);c.tap(5,8)
    c.tap(2,1);c.tap(1,4);c.tap(2,4);c.tap(3,8)
    c.tap(1,2);c.tap(2,2);rhythm=2
    def play(slot,assigned):
        velocities=[127,117] if rhythm==1 else [100,100]
        expected=[(1,[144,pitches[(slot-1)%7],velocities[0]]),(1,[144,pitches[(slot-1)//7],velocities[1]])]
        notes=c.playback(expected,cycles=2,timeout=3,settle_seconds=4/3-.1)
        assert_durations(c,notes,[1]*4)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(b[field]-a[field])/1e9-([1,3][i%2]/6) for i,(a,b) in enumerate(zip(notes,notes[1:]))]
        assert len(errors)>=4 and all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),errors
        c.results.append(dict(kind='note-priority-slot',slot=slot,assigned=assigned,rhythm_slot=rhythm,expected=expected,max_spacing_error_seconds=max(abs(x) for x in errors),passed=True))
    for slot in range(1,17):
        wanted_rhythm=1 if slot==2 else 2
        if rhythm!=wanted_rhythm:
            c.led_values([(rhythm,2),(wanted_rhythm,2)],[15,2])
            c.tap(5,8);c.tap(rhythm,1);c.tap(1,4);c.tap(2,4)
            c.tap(wanted_rhythm,1);c.tap(1,4);c.tap(2,4);c.tap(3,8)
            c.led_values([(rhythm,2),(wanted_rhythm,2)],[15,2])
            c.tap(rhythm,2);c.led_values([(rhythm,2),(wanted_rhythm,2)],[2,2])
            c.tap(wanted_rhythm,2);c.led_values([(rhythm,2),(wanted_rhythm,2)],[2,15]);rhythm=wanted_rhythm
        c.hold_tap((15,8),(slot,2))
        c.led_values([(slot,2),(rhythm,2),(15,8)],[2,15,15]);play(slot,False)
        c.tap(slot,2);c.led_values([(slot,2),(rhythm,2)],[15,15]);play(slot,True)
        c.tap(slot,2)


def octave_phrase(c,octaves,phase):
    base=[60,62,64,65];velocities=[127,117,107,97]
    expected=[(1,[144,n+12*o,v]) for n,o,v in zip(base,octaves,velocities)]
    notes=c.playback(expected,cycles=2,timeout=3,settle_seconds=4/3-.1)
    assert_durations(c,notes,[1]*8)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    errors=[(b[field]-a[field])/1e9-1/6 for a,b in zip(notes,notes[1:])]
    assert len(errors)>=8 and all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),errors
    c.results.append(dict(kind='octave-phrase',phase=phase,octaves=octaves,passed=True))

def channel_octave_controls(c):
    c.configure()
    for octave in (-2,-1,0,1,2,0,0):
        c.tap(octave+10,8)
        c.led_values([(x,8) for x in range(8,13)],[15 if x==octave+10 else 2 for x in range(8,13)])
        octave_phrase(c,[octave]*4,'global-'+str(octave))
    c.tap(5,8);c.tap(3,8)
    c.led_values([(x,8) for x in range(8,13)],[2,2,15,2,2])
    octave_phrase(c,[0]*4,'center-retained-after-navigation')

def octave_lock_precedence(c):
    c.configure();c.enc(1,-3)
    def held_feedback(step,octave):
        c.action(type='grid',x=step,y=4,state=1)
        try:c.led_values([(x,8) for x in range(8,13)],[15 if x==octave+10 else 2 for x in range(8,13)])
        finally:c.action(type='grid',x=step,y=4,state=0)
    for global_octave in range(-2,3):
        c.tap(global_octave+10,8)
        for locked_octave in range(-2,3):
            c.hold_tap((2,4),(locked_octave+10,8));held_feedback(2,locked_octave)
            octave_phrase(c,[global_octave,locked_octave,global_octave,global_octave],'override-%s-%s'%(global_octave,locked_octave))
            c.action(type='grid',x=2,y=4,state=1)
            try:c.key(2)
            finally:c.action(type='grid',x=2,y=4,state=0)
            held_feedback(2,global_octave)
            octave_phrase(c,[global_octave]*4,'cleared-%s-%s'%(global_octave,locked_octave))
    c.tap(-2+10,8)
    # Repeating the same lock selector removes it, including explicit zero.
    for step in range(1,5):
        c.hold_tap((step,4),(10,8));held_feedback(step,0)
        expected=[-2]*4;expected[step-1]=0
        octave_phrase(c,expected,'zero-lock-step-'+str(step))
        c.hold_tap((step,4),(10,8));held_feedback(step,-2)
        octave_phrase(c,[-2]*4,'toggle-clear-step-'+str(step))


def octave_all_positions(c):
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    cells=[(i%16+1,i//16+4) for i in range(64)]
    for cell in cells[4:]:c.tap(*cell)
    c.tap(5,8)
    for page in range(4):
        c.tap(9+page,8)
        for x in range(1,17):c.tap(x,7)
    c.tap(3,8);c.enc(1,-3)
    octaves=[i%5-2 for i in range(64)]
    for cell,octave in zip(cells,octaves):c.hold_tap(cell,(10+octave,8))
    velocities=[127,117,107,97]+[100]*60
    def play(expected_octaves,phase):
        expected=[(1,[144,60+12*octave,velocity]) for octave,velocity in zip(expected_octaves,velocities)]
        notes=c.playback(expected,cycles=2,timeout=5,settle_seconds=64/3-.1)
        assert_durations(c,notes,[1]*128)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(b[field]-a[field])/1e9-1/6 for a,b in zip(notes,notes[1:])]
        assert len(errors)>=128 and all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),errors
        c.results.append(dict(kind='octave-position-playback',phase=phase,octaves=expected_octaves,passed=True))
    for global_octave in (-2,2):
        c.tap(10+global_octave,8)
        for cell,octave in zip(cells,octaves):
            c.action(type='grid',x=cell[0],y=cell[1],state=1)
            try:c.led_values([(x,8) for x in range(8,13)],[15 if x==10+octave else 2 for x in range(8,13)])
            finally:c.action(type='grid',x=cell[0],y=cell[1],state=0)
        play(octaves,'all64-override-global-'+str(global_octave))
    c.action(type='key',n=1,state=1)
    try:c.elapse(.3);c.key(2)
    finally:c.action(type='key',n=1,state=0)
    for cell in cells:
        c.action(type='grid',x=cell[0],y=cell[1],state=1)
        try:c.led_values([(x,8) for x in range(8,13)],[2,2,2,2,15])
        finally:c.action(type='grid',x=cell[0],y=cell[1],state=0)
    play([2]*64,'all64-cleared-to-global')


def integral_clock_divisions(c,slow=False):
    from fractions import Fraction
    from midi_window import MidiWindow
    from frame_oracle import header,matches
    # Fixed public selector labels; expected seconds follow the musical ratio,
    # never Mosaic's clock or lattice implementation.
    labels=['x16','x12','x8','x6','x5.3','x5','x4','x3','x2.6','x2','x1.5','x1.3',
      '/1','/1.5','/2','/2.6','/3','/4','/5','/5.3','/6','/7','/8','/9','/10','/11','/12','/13','/14','/15','/16',
      '/17','/19','/21','/23','/24','/25','/27','/29','/32','/40','/48','/56','/64','/96','/101','/128']
    c.configure();c.enc(1,-1);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
    selected=13;tested=[]
    for index,label in enumerate(labels,1):
        number=Fraction(label[1:]);factor=1/number if label[0]=='x' else number
        pulses=24*factor
        if pulses.denominator!=1 or (factor>16)!=slow:continue
        c.enc(3,selected-index);c.key(3);selected=index
        expected=[(1,[144,n,v]) for n,v in zip([60,62,64,65],[127,117,107,97])]
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8);capture.extend(c.snapshot())
        remaining=float(8*factor/6)
        # Public controlled advances are bounded to60s. Small chunks retain
        # responsive clients and preserve that runtime limit in both lanes.
        while remaining>0:
            chunk=min(30,remaining);c.elapse(chunk);remaining-=chunk;capture.extend(c.snapshot())
        c.wait(lambda state:len(capture.extend(state).note_ons())>=9,timeout=3)
        notes=capture.note_ons()
        assert [(m['port'],m['bytes']) for m in notes]==[expected[i%4] for i in range(len(notes))],label
        c.tap(1,8);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(m[field]-notes[0][field])/1e9-float(i*factor/6) for i,m in enumerate(notes)]
        assert all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),(label,errors)
        assert_durations(c,notes,[float(factor)]*8,events=capture.events)
        c.results.append(dict(kind='clock-division-phrase',label=label,pulses=int(pulses),period_seconds=float(factor/6),complete_cycles=2,onsets=len(notes),max_phase_error_seconds=max(abs(x) for x in errors),passed=True));tested.append(label)
    assert len(tested)==(16 if slow else 24),tested


def menu_option_row(c,label,value,top=22):
    import base64
    from frame_oracle import render
    # Native params draws the full name then the right-aligned value, without
    # clearing their overlap. Assert the composite row, including both glyphs.
    expected=render([(0,30,15,label),(None,30,15,value)])
    indices=[(y*128+x)*4+k for y in range(top,32) for x in range(128) for k in range(3)]
    def match(state):
        actual=base64.b64decode(state['frame']['pixels_base64'])
        return all(actual[i]==expected[i] for i in indices)
    c.wait(match);c.results.append(dict(kind='selected-menu-option-row',label=label,value=value,matched=True))

def set_mosaic_options(c,options):
    from frame_oracle import selected_line
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,value in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if value['id']=='mosaic')
    c.enc(2,position);c.key(3)
    for label,enabled in options:
        # The preceding Parameter locks separator draws its rule at y22.
        top=23 if label in ('Trigless locks','Snap note masks to scale') else 22
        c.enc(2,-60)
        for attempt in range(40):
            if selected_line(c.snapshot(),label,top=top):break
            c.enc(2,1)
        else:raise AssertionError('Required Mosaic option not reached: '+label)
        c.enc(3,3 if enabled else -3);menu_option_row(c,label,'On' if enabled else 'Off',top=top)
        c.results.append(dict(kind='mosaic-option-input',label=label,enabled=enabled))
    c.key(2);c.enc(2,-60);menu_label(c,'LEVELS >');c.key(2);c.key(1)

def repeated_pattern_reset_policy(c,verify_pending=False):
    from midi_window import MidiWindow
    c.configure();c.hold_tap((1,4),(3,4));c.enc(1,-1);c.enc(3,-11);c.key(3)
    for song_on,transition_reset,repeat_reset in ((True,False,False),(True,True,False),(True,False,True),(True,True,True),(False,True,True)):
        set_mosaic_options(c,[('Song mode',song_on),('Reset on song seq change',transition_reset),('Reset on pattern repeat',repeat_reset)])
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8);c.elapse(24);capture.extend(c.snapshot())
        c.tap(1,8);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        reset=song_on and repeat_reset
        expected=[]
        for tick in range(3457):
            origin=(tick//1536)*1536 if reset else 0
            if (tick-origin)%216==0:
                step=((tick-origin)//216)%3
                expected.append((tick,[144,[60,62,64][step],[127,117,107][step]]))
        notes=capture.note_ons()
        assert [(m['port'],m['bytes']) for m in notes]==[(1,event) for tick,event in expected],dict(reset=reset,actual=[m['bytes'] for m in notes],expected=expected)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(m[field]-notes[0][field])/1e9-tick/144 for m,(tick,event) in zip(notes,expected)]
        assert all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),errors
        if not reset or verify_pending:assert_durations(c,notes,[9]*(len(notes)-1),events=capture.events)
        if verify_pending:
            from note_accounting import note_pairs
            assert len(note_pairs(capture.events))==len(notes),'Incomplete reset release accounting'
        c.results.append(dict(kind='native-repeat-reset-policy',song_mode=song_on,transition_reset=transition_reset,repeat_reset=repeat_reset,onsets=len(notes),expected_pulse_offsets=[tick for tick,event in expected],max_phase_error_seconds=max(abs(x) for x in errors),passed=True))


def fractional_clock_continuity(c):
    from fractions import Fraction
    from midi_window import MidiWindow
    from fractional_deadlines import check_segment, reconcile_note_stream
    from automation.input_origin import verified_input_origin
    import json
    c.configure();c.tap(5,8);c.tap(5,8)
    for x in range(1,5):c.tap(x,7)
    c.tap(3,8);c.enc(1,-1)
    set_mosaic_options(c,[('Reset on song seq change',False),('Reset on pattern repeat',False)])
    ratios=[(1,'x16',Fraction(3,2)),(5,'x5.3',Fraction(240,53)),(6,'x5',Fraction(24,5)),(9,'x2.6',Fraction(120,13)),(12,'x1.3',Fraction(240,13)),(16,'/2.6',Fraction(312,5)),(20,'/5.3',Fraction(636,5))]
    selected=13;segments=[];trigger_action=dict(type='grid',x=1,y=8,state=0)
    for index,label,pulses in ratios:
        c.enc(3,selected-index);c.key(3);selected=index
        capture=MidiWindow(c.snapshot()['midi_count']);observation_start=len(c.observations)
        # Transport start reconstructs from final settings with one canonical preview.
        seed=Fraction(1,2)
        c.action(type='grid',x=1,y=8,state=1)
        logical_start=c.logical_ns;start_ack=c.action(**trigger_action)
        c.elapse(.06)
        for _ in range(90):
            c.elapse(.5);capture.extend(c.snapshot())
            if len(c.observations)>observation_start+2:del c.observations[observation_start+1:-1]
        c.action(type='grid',x=1,y=8,state=1)
        logical_stop=c.logical_ns;stop_ack=c.action(**trigger_action)
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        segments.append(dict(label=label,ratio=[pulses.numerator,pulses.denominator],preview_seed=[seed.numerator,seed.denominator],after=capture.after,cursor=capture.cursor,
            start_ack=start_ack,stop_ack=stop_ack,logical_start=logical_start,logical_stop=logical_stop,
            capture=capture.events))
    # Complete the public-client export before checking causal input records.
    # finish() is idempotent; the outer runner still propagates any assertion.
    c.finish()
    events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
    actions=[json.loads(line) for line in (c.out/'native/actions.jsonl').read_text().splitlines()]
    controlled=c.clock_mode=='controlled-experimental';kind=11 if controlled else 3
    (c.out/'fractional-clock-plans.json').write_text(json.dumps(dict(
        formula='floor((n+1)*P+seed-1/100)-floor(P+seed-1/100); seed=1/2 at canonical transport-start construction',pulse_rate=144,tempo=90,
        origin_rule='Identified backend grid RELEASE submission triggers short Play; controlled lane uses declared logical release input time',
        stop_rule='Identified grid RELEASE Stop submission and its native applied acknowledgement',segments=segments),indent=2)+'\n')
    def input_origin(ack):
        submissions=[e for e in events if e.get('kind')=='input' and e['sequence']==ack['native']['sequence']]
        assert len(submissions)==1
        return verified_input_origin(events,actions,session_id=c.runtime.id,action_id=ack['action_id'],
            expected_action=trigger_action,declared_origin_ns=submissions[0]['monotonic_ns'])
    try:
        c.results.append(reconcile_note_stream(events,segments,kind))
        for segment in segments:
            start_evidence=input_origin(segment['start_ack']);stop_evidence=input_origin(segment['stop_ack'])
            origin=segment['logical_start'] if controlled else start_evidence['origin_ns']
            stop=segment['logical_stop'] if controlled else stop_evidence['origin_ns']
            applied=stop if controlled else stop_evidence['applied_ns']
            captured=[e for e in events if e.get('kind')==kind and segment['after']<e['sequence']<=segment['cursor']]
            fields=('port','bytes','logical_ns' if controlled else 'monotonic_ns')
            assert [{k:e[k] for k in fields} for e in captured]==[{k:e[k] for k in fields} for e in segment['capture']], 'Public/native MIDI capture differs'
            report=check_segment(captured,Fraction(*segment['ratio']),origin,stop,applied,controlled=controlled,preview_seed=Fraction(*segment['preview_seed']))
            assert report['onsets']>=2*segment['ratio'][1]+1
            assert stop-origin>=45_000_000_000, 'Missing45-second timing population'
            report.update(label=segment['label'],global_boundaries_crossed=4,start_input=start_evidence,stop_input=stop_evidence)
            c.results.append(report)
    finally:
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def song_transition_reset_policy(c,verify_pending=False):
    from midi_window import MidiWindow
    c.configure();c.hold_tap((1,4),(3,4));c.enc(1,-1);c.enc(3,-11);c.key(3)
    c.tap(6,8);c.hold_tap((1,1),(2,1));c.led_values([(1,1),(2,1)],[15,7])
    c.tap(2,1);c.tap(3,8);c.tap(11,8);c.tap(6,8);c.tap(1,1)
    for transition_reset,repeat_reset in ((False,False),(True,False),(False,True),(True,True)):
        set_mosaic_options(c,[('Song mode',True),('Reset on song seq change',transition_reset),('Reset on pattern repeat',repeat_reset)])
        c.tap(1,1);c.led_values([(1,1),(2,1)],[15,7])
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
        c.elapse(10.8);capture.extend(c.snapshot());c.led_values([(1,1),(2,1)],[7,15])
        c.elapse(10.8);capture.extend(c.snapshot());c.led_values([(1,1),(2,1)],[15,7])
        c.elapse(1.4);capture.extend(c.snapshot());c.tap(1,8)
        c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        # Preserve the existing reset predicate, including repeat reset on a
        # changed-pattern boundary; candidate0026 does not redefine that option.
        reset=transition_reset or repeat_reset
        expected=[]
        for tick in range(3385):
            epoch=tick//1536;origin=epoch*1536 if reset else 0
            if (tick-origin)%216==0:
                step=((tick-origin)//216)%3;pitch=[60,62,64][step]+12*(epoch%2)
                expected.append((tick,[144,pitch,[127,117,107][step]]))
        notes=capture.note_ons()
        assert [(m['port'],m['bytes']) for m in notes]==[(1,event) for tick,event in expected],dict(reset=reset,actual=[m['bytes'] for m in notes],expected=expected)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(note[field]-notes[0][field])/1e9-tick/144 for note,(tick,event) in zip(notes,expected)]
        assert all(abs(x)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for x in errors),errors
        if not reset or verify_pending:assert_durations(c,notes,[9]*(len(notes)-1),events=capture.events)
        if verify_pending:
            from note_accounting import note_pairs
            assert len(note_pairs(capture.events))==len(notes),'Incomplete reset release accounting'
        c.results.append(dict(kind='native-song-transition-reset',transition_reset=transition_reset,repeat_reset=repeat_reset,onsets=len(notes),expected_pulse_offsets=[tick for tick,event in expected],max_phase_error_seconds=max(abs(x) for x in errors),passed=True))


def inactive_shuffle_transition(c,basis=False):
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    c.configure();c.tap(5,8);c.tap(5,8)
    for x in range(1,5):c.tap(x,7)
    c.tap(3,8);c.enc(1,-1);c.enc(3,12);c.key(3)
    set_mosaic_options(c,[('Reset on song seq change',False),('Reset on pattern repeat',False)])
    c.tap(6,8);c.hold_tap((1,1),(2,1));c.tap(2,1);c.tap(3,8)
    # Set either stored Smooth feel or7 basis in Shuffle mode, then return
    # to Swing. Each inactive field is tested independently at transitions.
    c.enc(2,1);c.enc(3,2);c.key(3)
    c.enc(2,2 if basis else 1);c.enc(3,2);c.key(3)
    c.enc(2,-2 if basis else -1);c.enc(3,-1);c.key(3)
    c.tap(11,8);c.tap(6,8);c.tap(1,1)
    capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
    for i in range(90):
        c.elapse(.5);capture.extend(c.snapshot())
        if i==22:c.led_values([(1,1),(2,1)],[7,15])
        if i==44:c.led_values([(1,1),(2,1)],[15,7])
    c.tap(1,8);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
    notes=capture.note_ons();pairs=note_pairs(capture.events)
    assert len(pairs)==len(notes) and len(notes)>4000
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    for i,note in enumerate(notes):
        epoch=(i//1024)%2
        assert note['port']==1 and note['bytes']==[144,60+12*epoch,[127,117,107,97][i%4]],(i,note)
    windows=[(b[field]-a[field])/1e9-3/144 for a,b in zip(notes,notes[2:])]
    assert max(abs(x) for x in windows)<=tolerance,('Inactive shuffle settings changed Swing timing',max(abs(x) for x in windows))
    phase=[(note[field]-notes[0][field])/1e9-i/96 for i,note in enumerate(notes)]
    assert max(abs(x) for x in phase)<=1/144+tolerance,('Cumulative phase',max(abs(x) for x in phase))
    c.results.append(dict(kind='inactive-shuffle-transitions',onsets=len(notes),release_pairs=len(pairs),windows=len(windows),max_window_error_seconds=max(abs(x) for x in windows),passed=True))


def length_mask_display(c,label):
    import base64
    from frame_oracle import render
    expected=render([(75,18,15,'Len'),(75,26,15,label)])
    indices=[(y*128+x)*4+k for y in range(11,29) for x in range(75,100) for k in range(3)]
    def matches(state):
        actual=base64.b64decode(state['frame']['pixels_base64'])
        return all(actual[i]==expected[i] for i in indices)
    c.wait(matches)
    c.results.append(dict(kind='length-mask-display',label=label,passed=True))

def length_mask_boundaries(c):
    c.configure();c.enc(1,-4);c.enc(2,2)
    length_mask_display(c,'X');c.enc(3,-3);length_mask_display(c,'X')
    c.enc(3,89);length_mask_display(c,'128')
    c.enc(3,3);length_mask_display(c,'128')
    c.enc(3,-12);length_mask_display(c,'64')
    c.enc(3,-59);length_mask_display(c,'2')
    c.enc(3,-10);length_mask_display(c,'1/2')
    c.enc(3,-8);length_mask_display(c,'X')


def pending_mask_lengths(c,long=False):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(3,4));c.enc(1,-1);c.enc(3,-11);c.key(3)
    c.enc(1,-3);c.enc(2,2);selected=0
    choices=[(89,'128',128,True)] if long else [(8,'1/2',.5,False),(8,'1/2',.5,True),(18,'2',2,False),(18,'2',2,True)]
    for index,label,length,reset in choices:
        c.enc(3,index-selected);selected=index;length_mask_display(c,label)
        set_mosaic_options(c,[('Reset on song seq change',False),('Reset on pattern repeat',reset)])
        length_mask_display(c,label)
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8)
        seconds=195 if long else 24
        remaining=seconds
        while remaining:
            chunk=min(30,remaining);c.elapse(chunk);capture.extend(c.snapshot());remaining-=chunk
        controlled=c.clock_mode=='controlled-experimental'
        lower=c.logical_ns if controlled else time.monotonic_ns()
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        upper=c.logical_ns if controlled else time.monotonic_ns()
        c.elapse(.06);c.wait(lambda state:capture.extend(state) and not state['midi_capture']['outstanding'])
        onsets=[]
        for tick in range(seconds*144+1):
            origin=(tick//1536)*1536 if reset else 0
            if (tick-origin)%216==0:
                step=((tick-origin)//216)%3
                onsets.append((tick,[60,62,64][step],[127,117,107][step]))
        field='logical_ns' if controlled else 'monotonic_ns';notes=capture.note_ons()
        assert notes,'Missing notes'
        rows=assert_schedule(capture.events,onsets,[216*length]*len(onsets),field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
        if long:assert sum(not row['truncated'] for row in rows)>=3,'Missing completed maximum-length notes'
        c.results.append(dict(kind='native-pending-mask-length',length=length,reset=reset,onsets=len(onsets),release_checks=len(rows),complete_releases=sum(not row['truncated'] for row in rows),stop_truncated_releases=sum(row['truncated'] for row in rows),passed=True))


def parameter_list_label(c,label,wait=True):
    import base64
    from frame_oracle import render
    expected=render([(35,35,5,label)])
    indices=[(y*128+x)*4+k for y in range(27,37) for x in range(35,128) for k in range(3)]
    def matches(state):
        actual=base64.b64decode(state['frame']['pixels_base64'])
        return all(actual[i]==expected[i] for i in indices)
    if wait:
        c.wait(matches);c.results.append(dict(kind='parameter-list-label',label=label,passed=True));return True
    return matches(c.snapshot())

def assign_trig_parameter(c,label):
    c.key(2);c.enc(3,-50)
    for attempt in range(50):
        if parameter_list_label(c,label,wait=False):break
        c.enc(3,1)
    else:raise AssertionError('Parameter unavailable through native UI: '+label)
    parameter_list_label(c,label);c.key(3);c.key(2)

def strum_reset_continuity(c):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(3,4));c.enc(1,-4);c.enc(2,3);c.enc(3,3)
    import base64
    from frame_oracle import render
    expected_chord=render([(0,40,15,'Chd1'),(0,48,15,'3rd')])
    indices=[(y*128+x)*4+k for y in range(33,50) for x in range(25) for k in range(3)]
    def third_selected(state):
        actual=base64.b64decode(state['frame']['pixels_base64'])
        return all(actual[i]==expected_chord[i] for i in indices)
    c.wait(third_selected);c.results.append(dict(kind='chord-mask-screen',label='3rd',passed=True))
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Strum');c.enc(3,8)
    for reset in (False,True):
        set_mosaic_options(c,[('Reset on song seq change',False),('Reset on pattern repeat',reset)])
        capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8);c.elapse(24);capture.extend(c.snapshot())
        controlled=c.clock_mode=='controlled-experimental'
        lower=c.logical_ns if controlled else time.monotonic_ns()
        c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
        upper=c.logical_ns if controlled else time.monotonic_ns()
        # A deferred strum beyond Stop must never sound.
        c.elapse(2);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
        expected=[]
        for tick in range(3457):
            origin=(tick//1536)*1536 if reset else 0
            if (tick-origin)%216==0:
                step=((tick-origin)//216)%3;velocity=[127,117,107][step]
                expected.append((tick,[60,62,64][step],velocity,216))
                if tick+108<=3456:expected.append((tick+108,[64,65,67][step],velocity,108))
        # Sort only the independently constructed musical table, never emissions.
        expected.sort(key=lambda row:row[0])
        field='logical_ns' if controlled else 'monotonic_ns';notes=capture.note_ons();assert notes
        rows=assert_schedule(capture.events,[row[:3] for row in expected],[row[3] for row in expected],field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
        c.results.append(dict(kind='native-strum-reset',reset=reset,onsets=len(expected),release_checks=len(rows),scope='Half-step third-degree strum retains the established one-step root gate through resets; no deferred onset after Stop',passed=True))


def arp_basic_timing(c,replacement=False,fractional_gate=False,reset=False,fast=False):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    if fast:assert c.clock_mode=='controlled-experimental','Exact one-pulse arp boundary fixture requires controlled time; real-time family acceptance uses separate scheduling metrics'
    c.configure();c.hold_tap((1,4),(3,4));c.tap(5,8)
    if not replacement:c.tap(2,4);c.tap(3,4)
    c.tap(3,8)
    c.enc(1,-4);c.enc(2,2);c.enc(3,15 if fractional_gate else 18);length_mask_display(c,'1.25' if fractional_gate else '2')
    if not (fast or reset):
        c.enc(2,1);c.enc(3,3)
        if fractional_gate:c.enc(2,1);c.enc(3,5)
    c.enc(1,3);c.enc(3,0 if fast else -11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,1 if fast else 8)
    if reset:set_mosaic_options(c,[('Reset on song seq change',False),('Reset on pattern repeat',True)])
    seconds=3 if fast else (24 if reset else 10)
    capture=MidiWindow(c.snapshot()['midi_count'])
    if fast:c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    else:c.tap(1,8)
    # Native rational deadlines round upward to nanoseconds. Include the
    # final planned pulse explicitly; its2ns musical error bound is unchanged.
    c.elapse(seconds+(1e-6 if fast else 0));capture.extend(c.snapshot())
    controlled=c.clock_mode=='controlled-experimental'
    lower=c.logical_ns if controlled else time.monotonic_ns()
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(2);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    expected=[];durations=[]
    gate=48 if fast else (270 if fractional_gate else 432)
    interval=1 if fast else 108
    spacing=72 if fast else (216 if replacement else 648)
    roots=[tick for tick in range(seconds*144+1) if (tick%1536 if reset else tick)%spacing==0]
    for position,root in enumerate(roots):
        step=(root//spacing)%3 if replacement else 0
        next_root=roots[position+1] if position+1<len(roots) else root+spacing
        end=min(root+gate,next_root)
        for offset in range(0,end-root,interval):
            if root+offset>seconds*144:continue
            slot=(offset//interval)%5
            if fast or reset:pitch=[60,62,64][step] # No-mask ratchet retains dense retrigger coverage.
            elif slot==0:pitch=[60,62,64][step]
            elif slot==1:pitch=[64,65,67][step]
            elif slot==2 and fractional_gate:pitch=[67,69,71][step]
            else:continue # Explicit trailing slot is a rest under the amended contract.
            expected.append((root+offset,pitch,[127,117,107][step]))
            durations.append(min(interval,root+gate-(root+offset)))
    field='logical_ns' if controlled else 'monotonic_ns';notes=capture.note_ons();assert notes
    rows=assert_schedule(capture.events,expected,durations,field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='native-arpeggio-half-step',replacement=replacement,fractional_gate=fractional_gate,reset=reset,fast=fast,onsets=len(expected),release_checks=len(rows),passed=True))


def parameter_division_bounds(c,parameter):
    import base64
    from frame_oracle import render
    def label(value):
        expected=render([(0,25,15,value)])
        indices=[(y*128+x)*4+k for y in range(19,27) for x in range(24) for k in range(3)]
        def matches(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[i]==expected[i] for i in indices)
        c.wait(matches);c.results.append(dict(kind='parameter-division-label',parameter=parameter,value=value,passed=True))
    c.configure();c.enc(1,-3);assign_trig_parameter(c,parameter)
    label('X');c.enc(3,-3);label('X')
    c.enc(3,1);label('1/24');c.enc(3,88);label('128')
    c.enc(3,3);label('128')
    c.enc(3,-1);label('120');c.enc(3,-88);label('X')


def spread_acceleration_contract(c,arp,acceleration,explicit_off=False):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    assert acceleration in range(-5,6)
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4);c.enc(2,2);c.enc(3,89);length_mask_display(c,'128')
    for turns in (3,5,6,8):c.enc(2,1);c.enc(3,turns)
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio' if arp else 'Chord Note Strum');c.enc(3,8)
    c.enc(2,1);assign_trig_parameter(c,'Chord Spread');c.enc(3,5)
    if acceleration or explicit_off:
        c.enc(2,1);assign_trig_parameter(c,'Chord Accel Mod');c.enc(3,2 if explicit_off else acceleration)
        if explicit_off:
            c.action(type='grid',x=1,y=4,state=1)
            try:c.enc(3,-2)
            finally:c.action(type='grid',x=1,y=4,state=0)
    capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8);c.elapse(18);capture.extend(c.snapshot())
    controlled=c.clock_mode=='controlled-experimental'
    lower=c.logical_ns if controlled else time.monotonic_ns()
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(2);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    # Codex-arbitrated new contract, not a fit to current implementation:
    # channel period216, d=1/2, s=1/4; gap_k=d+s*(1+(k-1)*a).
    pitches=(60,64,67,69,72);expected=[(0,60,127)];tick=0;ordinal=1
    while arp or ordinal<=4:
        gap=108+54*(1+(ordinal-1)*acceleration)
        if gap<=0:break
        tick+=gap
        if tick>2592:break
        expected.append((tick,pitches[ordinal%5],127));ordinal+=1
    field='logical_ns' if controlled else 'monotonic_ns';notes=capture.note_ons();assert notes
    # Strum durations deliberately exceed this observation; only their Stop
    # releases are claimed here. Arp duration is independently half a step.
    rows=assert_schedule(capture.events,expected,[108 if arp else 27648]*len(expected),field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='spread-acceleration-contract',arp=arp,acceleration=acceleration,default_off=acceleration==0 and not explicit_off,explicit_off=explicit_off,onsets=len(expected),release_checks=len(rows),decision='01a07f50-06ce-76f2-86f5-76414bd23074',compatibility_claim='New-contract conformance; historical behavior is preserved only where independently shown',passed=True))


def arp_empty_masks(c,muted=False):
    from note_accounting import note_pairs
    c.configure();c.enc(1,-3);assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,8)
    if muted:
        c.enc(2,1);assign_trig_parameter(c,'Mute Chord Root');c.enc(3,1)
        before=c.snapshot()['midi_count'];c.tap(1,8);c.elapse(.5)
        # Silence alone cannot pass: the native input loop and screen must
        # remain responsive while an all-empty muted arp is selected.
        c.enc(1,3);c.screen_header('Ch. 1 Device Config');c.tap(1,8);c.elapse(.25)
        state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and m['bytes'][0]&240==144 and m['bytes'][2]>0]
        assert not notes and not state['midi_capture']['outstanding'],'Muted empty arp emitted or retained a voice'
        c.results.append(dict(kind='empty-muted-arp-responsive-silence',passed=True));return
    before=c.snapshot()['midi_count']
    expected=[(1,[144,pitch,velocity]) for pitch,velocity in ((60,127),(62,117),(64,107),(65,97)) for _ in range(2)]
    notes=c.playback(expected,cycles=2,timeout=4,settle_seconds=1.25)
    assert_durations(c,notes,[.5]*16)
    events=[m for m in c.snapshot()['midi'] if m['index']>before]
    assert len(note_pairs(events))==len(notes),'No-mask ratchet release accounting failed'
    c.results.append(dict(kind='no-mask-ratchet-compatibility-control',onsets=len(notes),passed=True))

def arp_rest_slots(c,internal=False):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4);c.enc(2,2);c.enc(3,89);length_mask_display(c,'128')
    # Explicit Off values preserve real internal/trailing rest slots in the
    # baseline; this does not depend on Lua's length of a sparse table.
    for turns in (3,1,5 if internal else 1,1):c.enc(2,1);c.enc(3,turns)
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,8)
    capture=MidiWindow(c.snapshot()['midi_count']);c.tap(1,8);c.elapse(8);capture.extend(c.snapshot())
    controlled=c.clock_mode=='controlled-experimental';lower=c.logical_ns if controlled else time.monotonic_ns()
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(1);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    slots=(60,64,None,67 if internal else None,None)
    expected=[(ordinal*108,slots[ordinal%5],127) for ordinal in range(11) if slots[ordinal%5] is not None]
    field='logical_ns' if controlled else 'monotonic_ns';notes=capture.note_ons();assert notes
    rows=assert_schedule(capture.events,expected,[108]*len(expected),field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='arp-rest-slot-contract',internal=internal,onsets=len(expected),release_checks=len(rows),decision='01a07f50-06ce-76f2-86f5-76414bd23074',passed=True))


def fractional_spread_contract(c):
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    assert c.clock_mode=='controlled-experimental','Exact fractional pulse windows require controlled time until the D20 real-time deadline oracle is implemented'
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4);c.enc(2,2);c.enc(3,89);length_mask_display(c,'128')
    for turns in (3,5,6,8):c.enc(2,1);c.enc(3,turns)
    c.enc(1,3);c.enc(3,7);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,8)
    c.enc(2,1);assign_trig_parameter(c,'Chord Spread');c.enc(3,5)
    capture=MidiWindow(c.snapshot()['midi_count'])
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.elapse(1.500001);capture.extend(c.snapshot());lower=c.logical_ns
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns;c.elapse(.25);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    notes=capture.note_ons();assert len(notes)==61,('Fractional arp onset count',len(notes))
    origin=notes[0]['logical_ns'];pitches=(60,64,67,69,72)
    pulses=[(note['logical_ns']-origin)*144/1e9 for note in notes]
    for i,note in enumerate(notes):
        assert (note['port'],note['bytes'])==(1,[144,pitches[i%5],127]),('Fractional arp data',i,note)
        assert abs(pulses[i]-i*18/5)<=1.0000003,('Fractional arp phase',i,pulses[i])
        if i:assert min(abs(pulses[i]-pulses[i-1]-n) for n in (3,4))<=.0000003,('Fractional arp gap',i)
        if i>=5:assert abs(pulses[i]-pulses[i-5]-18)<=.0000003,('Fractional five-slot window',i)
    pairs=note_pairs(capture.events);assert len(pairs)==61
    for on,off in pairs:
        duration=(off['logical_ns']-on['logical_ns'])*144/1e9
        regular=abs(duration-12/5)<=1.0000003
        stopped=lower<=off['logical_ns']<=upper and off['bytes'][2] in (0,on['bytes'][2])
        assert regular or stopped,('Fractional arp duration',duration,on,off)
        assert off['bytes'][2]==on['bytes'][2] or stopped,'Fractional release velocity'
    c.results.append(dict(kind='fractional-spread-contract',parent_period='24/5 pulses',arp_interval='18/5 pulses',independent_windows=56,onsets=61,release_checks=61,decision='01a07f50-06ce-76f2-86f5-76414bd23074',passed=True))


def minimum_swung_gap_contract(c,swing):
    from midi_window import MidiWindow
    from note_accounting import note_pairs
    assert c.clock_mode=='controlled-experimental','Exact fractional pulse windows require controlled time until the D20 real-time deadline oracle is implemented'
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4);c.enc(2,2);c.enc(3,89);length_mask_display(c,'128')
    for turns in (3,5,6,8):c.enc(2,1);c.enc(3,turns)
    c.enc(1,3);c.enc(3,7);c.key(3)
    c.enc(2,1);c.enc(3,1);c.key(3)
    c.enc(2,1);c.enc(3,swing+51);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,8)
    c.enc(2,1);assign_trig_parameter(c,'Chord Spread');c.enc(3,1)
    c.enc(2,1);assign_trig_parameter(c,'Chord Accel Mod');c.enc(3,-4)
    capture=MidiWindow(c.snapshot()['midi_count'])
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.elapse(.5);capture.extend(c.snapshot())
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.elapse(.25);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    # Four positive spacing gaps; the fifth is negative and must not sound.
    expected=(0,1,4,5,6) if swing<0 else (0,4,5,6,7)
    notes=capture.note_ons();assert len(notes)==5,('Minimum swung gap lost/extra note',swing,len(notes))
    origin=notes[0]['logical_ns'];pitches=(60,64,67,69,72)
    for note,pulse,pitch in zip(notes,expected,pitches):
        assert (note['port'],note['bytes'])==(1,[144,pitch,127])
        assert abs((note['logical_ns']-origin)*144/1e9-pulse)<.0000003,('Minimum gap onset',swing,pulse,note)
    # Independently declared rounded parent cycles: x5, signed50 swing,
    # initial half-pulse carry. A half-step gate integrates across these cycles.
    periods=(2,8,2,7) if swing<0 else (7,3,7,2)
    pairs=note_pairs(capture.events);assert len(pairs)==5
    for (on,off),onset in zip(pairs,expected):
        start=0
        for n,period in enumerate(periods):
            if onset<start+period:break
            start+=period
        fraction=(onset-start)/period+.5
        if fraction<=1:ideal=start+fraction*period
        else:ideal=start+period+(fraction-1)*periods[n+1]
        actual=(off['logical_ns']-origin)*144/1e9
        assert abs(actual-ideal)<=1.0000003,('Half-step swung release',swing,onset,ideal,actual)
        assert off['bytes']==[128,on['bytes'][1],127]
    c.results.append(dict(kind='minimum-swung-gap',swing=swing,onsets=5,releases=5,passed=True))


def autosave_restart(c):
    c.configure()
    saved=c.data_directory/'autosave.ptn';pset=c.data_directory/'autosave.pset'
    assert not saved.exists() and not pset.exists(),'Fresh fixture unexpectedly contains autosave'
    c.elapse(59)
    assert not saved.exists(),'Autosave occurred before the documented60-second idle period'
    c.elapse(2)
    c.wait(lambda _:saved.is_file() and pset.is_file(),timeout=2)
    assert saved.stat().st_size>0 and pset.stat().st_size>0
    c.results.append(dict(kind='saved-project',files=[dict(name=p.name,sha256=digest(p)) for p in (saved,pset)]))
    c.finish()
    out=c.out/'reloaded';out.mkdir()
    loaded=Driver(out,project_seed=c.data_directory,**c.launch_options)
    try:
        # Read the restored pattern through the visible grid and complete MIDI
        # phrases. Do not re-create notes or inspect the serialized model.
        loaded.tap(3,8);loaded.tap(5,8)
        loaded.led_values([(x,4) for x in range(1,5)],[15,15,15,15])
        loaded.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    finally:loaded.finish()

def menu_label(c,text,x=0):
    from frame_oracle import selected_line
    c.wait(lambda s:selected_line(s,text,x));c.results.append(dict(kind='selected-menu-label',text=text))

def menu_value(c,text):
    from frame_oracle import selected_value
    c.wait(lambda s:selected_value(s,text));c.results.append(dict(kind='selected-menu-value',text=text))

def route_fixed_note(c,source_position,source_name):
    assert c.profile=='midi-modulation','This case requires actual matrix/toolkit mods'
    c.configure()
    c.key(1);c.enc(2,1);c.key(3);menu_label(c,'DEVICES > ')
    c.enc(2,2);menu_label(c,'MODS >');c.key(3);menu_label(c,'MATRIX >',4)
    c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['id']=='midi_device_params_group_channel_1')
    c.enc(2,position);c.key(3);menu_label(c,'Fixed Note')
    c.key(3);menu_label(c,'rhythm 1')
    c.enc(2,source_position);menu_label(c,source_name)
    c.enc(3,100);menu_value(c,'1.00')

def toolkit_parameter_group(c,name):
    c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['name']==name)
    c.enc(2,position);c.key(3)

def macro_route_clear(c):
    route_fixed_note(c,12,'macro 1')
    toolkit_parameter_group(c,'macro 1');menu_label(c,'active')
    c.enc(2,1);menu_label(c,'value');c.enc(3,100);c.key(1)
    c.playback([(1,[144,127,v]) for v in (127,117,107,97)])
    # Return to the retained Matrix source selection, then zero its depth.
    c.key(1);c.enc(1,-4);c.key(3);c.key(3);c.key(3)
    menu_label(c,'macro 1');c.key(3);menu_value(c,'-');c.key(1)
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))])

def held_macro_rebind(c):
    macro_route_clear(c)
    # The macro still holds1. Rebinding must apply it without touching the
    # source or waiting for another source event.
    c.key(1);menu_label(c,'macro 1');c.enc(3,100);menu_value(c,'1.00');c.key(1)
    c.playback([(1,[144,127,v]) for v in (127,117,107,97)])

def pulse_lfo(c):
    route_fixed_note(c,4,'lfo 1')
    toolkit_parameter_group(c,'lfo 1');menu_label(c,'clocked');c.key(3)
    c.enc(2,1);menu_label(c,'beats');c.enc(3,9)
    c.enc(2,2);menu_label(c,'shape');c.enc(3,2);c.key(1)
    # A4-beat pulse with50% width is high for8 sixteenth notes and low for8.
    # Place playback safely inside the high half using a verified native clock
    # read (not Mosaic state); E/R jitter and the24PPQN mod sample cannot cross
    # a half-cycle boundary at this1/8-beat offset.
    import math
    state=c.snapshot();beat=state['diagnostics']['beats']
    target=4*(math.floor(beat/4)+1)+.125
    c.elapse((target-beat)*2/3)
    expected=[]
    notes=[(60,127),(62,117),(64,107),(65,97)]
    for i in range(16):
        note,velocity=notes[i%4];expected.append((1,[144,127 if i<8 else note,velocity]))
    emitted=c.playback(expected,cycles=2,timeout=8)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    # Opening-pulse phase is separately exposed by M-LEN-001. Here check every
    # subsequent onset plus the full LFO period against90BPM, not merely ratios.
    anchor=emitted[1][field];rows=[]
    for i,event in enumerate(emitted[1:]):
        actual=(event[field]-anchor)/1e9;expected_seconds=i/6
        rows.append(dict(index=i+1,expected_seconds=expected_seconds,actual_seconds=actual))
    c.results.append(dict(kind='steady-lfo-timing',rows=rows,opening_phase_case='M-LEN-001'))
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert all(abs(row['actual_seconds']-row['expected_seconds'])<=tolerance for row in rows),rows

def phrase_timing(c):
    # Establish the edited 8-step phrase through the existing grid recipe, then
    # restart and measure every complete phrase against the fixed 90BPM oracle.
    next_trig_cutoff(c)
    notes=c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(67,100)]],cycles=20,timeout=32)
    assert_durations(c,notes,[2,1,1]*20)
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    anchor=notes[0][field];rows=[]
    for i,note in enumerate(notes[:61]):
        expected=(8*(i//3)+(0,2,4)[i%3])/6
        actual=(note[field]-anchor)/1e9
        rows.append(dict(index=i,expected_seconds=expected,actual_seconds=actual))
    c.results.append(dict(kind='twenty-phrase-onsets',rows=rows))
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert len(rows)==61 and all(abs(r['actual_seconds']-r['expected_seconds'])<=tolerance for r in rows),rows

def restart_phase_edges(c):
    import math
    next_trig_cutoff(c)
    for offset_ns in (-100,-1,0,1,100):
        beat=c.snapshot()['diagnostics']['beats']
        boundary=(math.ceil(beat*96)+96)/96
        c.elapse((boundary-beat)*2/3+offset_ns/1e9)
        observed=c.snapshot()['diagnostics']['beats']
        error_ns=(observed-boundary)*2/3*1e9
        c.results.append(dict(kind='restart-phase',requested_offset_ns=offset_ns,observed_offset_ns=error_ns,exact_phase=c.clock_mode=='controlled-experimental'))
        if c.clock_mode=='controlled-experimental':
            assert abs(error_ns-offset_ns)<=2,(offset_ns,error_ns)
        notes=c.playback([(1,[144,n,v]) for n,v in [(60,127),(64,107),(67,100)]],cycles=2,timeout=4)
        assert_durations(c,notes,[2,1,1]*2)

def midi_clock_transport(c):
    import time
    c.configure()
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    position=next(i for i,v in enumerate(roots) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source')
    menu_value(c,'internal');c.enc(3,1);menu_value(c,'midi')
    def inject(value,at=None):
        action=dict(type='midi',port=1,bytes=[value])
        if at is not None:action['at_monotonic_ns']=at
        c.action(**action)
    def pulses(count):
        start=time.monotonic_ns()
        for i in range(count):
            if c.clock_mode=='controlled-experimental':c.elapse(.025);inject(248)
            else:inject(248,start+(i+1)*25000000)
    # Replace the native estimator startup window with49 evenly spaced pulses.
    before=c.snapshot()['midi_count']
    first_play_pulse=None
    if c.clock_mode=='controlled-experimental':
        pulses(49)
        def new_notes():return [m for m in c.snapshot()['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
        assert not new_notes(),'Clock pulses alone started playback'
        inject(250);c.elapse(0)
        assert not new_notes(),'Transport started before the next MIDI clock pulse'
        pulses(60);inject(252)
    else:
        # One native queue avoids requiring every client roundtrip to finish
        # inside the25ms MIDI clock interval. Keep pulse spacing at100BPM.
        origin=time.monotonic_ns()+500000000
        packets=[(i*25000000,248) for i in range(1,50)]
        packets += [(1240000000,250)]
        packets += [(1250000000+i*25000000,248) for i in range(60)]
        packets += [(2735000000,252)]
        events=[dict(port=1,bytes=[value],at_monotonic_ns=origin+offset) for offset,value in packets]
        c.action(type='midi_schedule',schedule_id=1,events=events)
        state=c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
        delivered=state['midi_input_schedule']['delivered']
        first_play_pulse=delivered[50]['actual_monotonic_ns']
        c.results.append(dict(kind='native-midi-clock-stimulus',events=events,delivered=delivered))
    c.wait(lambda s:not s['midi_capture']['outstanding'])
    state=c.snapshot();notes=[m for m in state['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
    if first_play_pulse is not None:
        assert not [m for m in notes if m['monotonic_ns']<first_play_pulse],'Warmup/transport emitted notes before the first playback pulse'
    expected=[(60,127),(62,117),(64,107),(65,97)]
    assert len(notes)>=9,notes
    assert [(m['port'],m['bytes']) for m in notes]==[(1,[144,*expected[i%4]]) for i in range(len(notes))],notes
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    rows=[]
    for i,note in enumerate(notes[:9]):
        rows.append(dict(index=i,expected_seconds=i*.15,actual_seconds=(note[field]-notes[0][field])/1e9))
    c.results.append(dict(kind='midi-clock-onsets',rows=rows))
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    assert all(abs(r['actual_seconds']-r['expected_seconds'])<=tolerance for r in rows),rows
    durations=[]
    for note in notes[:8]:
        off=next(m for m in state['midi'] if m['index']>note['index'] and m['bytes']==[128,note['bytes'][1],note['bytes'][2]])
        durations.append((off[field]-note[field])/1e9)
    c.results.append(dict(kind='midi-clock-durations',expected_seconds=.15,actual_seconds=durations))
    assert all(abs(d-.15)<=tolerance for d in durations),durations
    c.enc(3,-1);menu_value(c,'internal')
    # Native clock.lua updates clock_tempo from the external source; returning
    # to internal uses that adopted tempo. Explicitly edit it back to90BPM.
    c.enc(2,1);menu_label(c,'tempo');menu_value(c,'100')
    c.enc(3,-10);menu_value(c,'90');c.key(1)
    internal=c.playback([(1,[144,n,v]) for n,v in expected])
    restored=[(m[field]-internal[0][field])/1e9 for m in internal[:9]]
    c.results.append(dict(kind='restored-internal-onsets',actual_seconds=restored))
    assert len(restored)==9 and all(abs(t-i/6)<=tolerance for i,t in enumerate(restored)),restored

def live_clock_handoff(c):
    import math,time
    next_trig_cutoff(c)
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');menu_value(c,'internal')
    pulse_cursor=0
    controlled=c.clock_mode=='controlled-experimental'
    domain='logical' if controlled else 'monotonic'
    origin=c.logical_ns if controlled else time.monotonic_ns()+500000000
    events=[dict(port=1,bytes=[248],**{'at_'+domain+'_ns':origin+(i+1)*25000000}) for i in range(83)]
    events.append(dict(port=1,bytes=[252],**{'at_'+domain+'_ns':origin+84*25000000}))
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    def pulses(count):
        nonlocal pulse_cursor
        pulse_cursor+=count
        if controlled:
            delta=origin+pulse_cursor*25000000-c.logical_ns
            assert delta>=0,'Control work crossed the requested observation deadline'
            c.elapse(delta/1e9)
            assert len(c.snapshot()['midi_input_schedule']['delivered'])>=pulse_cursor
        else:c.wait(lambda s:len(s['midi_input_schedule']['delivered'])>=pulse_cursor)
    pulses(49)
    before=c.snapshot();start_beat=before['diagnostics']['beats'];marker=before['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    pulses(4)
    pending=c.snapshot()
    assert pending['midi_capture']['outstanding'],'No pending note at source switch'
    elapsed_ticks=math.floor((pending['diagnostics']['beats']-start_beat)*96)
    assert 0<elapsed_ticks<48,elapsed_ticks
    switch_ack=c.action(type='enc',n=3,delta=2)
    handoff=c.snapshot();beat=handoff['diagnostics']['beats']
    if not controlled:
        # A pre-input snapshot can precede the audible onset by tens of ms.
        # Anchor to emitted MIDI and the runtime's applied control timestamp,
        # not HTTP receipt or a stale pre-grid observation.
        onset=next(m for m in pending['midi'] if m['index']>marker and m['bytes']==[144,60,127])
        applied=switch_ack['native']['monotonic_ns']
        start_beat=before['diagnostics']['beats']+(onset['monotonic_ns']-before['diagnostics']['monotonic_ns'])*1.5e-9
        elapsed_ticks=math.floor((applied-onset['monotonic_ns'])*144e-9)
        beat-=(handoff['diagnostics']['monotonic_ns']-applied)*(100/60)*1e-9
        assert 0<elapsed_ticks<48,elapsed_ticks
    quantum=1/96;phase=start_beat%quantum;epsilon=2**-23
    next_beat=math.ceil((beat+epsilon)/quantum)*quantum+phase-quantum
    while next_beat<beat+epsilon:next_beat+=quantum
    # One two-step note is48 ticks. Only its pending next wait is rephased;
    # remaining ticks proceed at100BPM (0.6 seconds per quarter note).
    remaining_seconds=(next_beat-beat)*.6+(48-elapsed_ticks-1)*.6/96
    origin_ns=c.logical_ns if controlled else applied
    expected_off_ns=origin_ns+remaining_seconds*1e9
    pulses(30);pulses(1)
    arrivals=c.snapshot()['midi_input_schedule']['delivered']
    errors=[e['actual_'+domain+'_ns']-e['intended_'+domain+'_ns'] for e in arrivals]
    c.results.append(dict(kind='continuous-midi-arrival-errors',time_domain=domain,errors_ns=errors))
    assert len(arrivals)==84 and all(0<=e<=(0 if controlled else 10000000) for e in errors),errors
    c.wait(lambda s:not s['midi_capture']['outstanding']);state=c.snapshot()
    notes=[m for m in state['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    assert [(m['port'],m['bytes']) for m in notes]==[(1,[144,60,127]),(1,[144,64,107]),(1,[144,67,100])],notes
    off=next(m for m in state['midi'] if m['index']>notes[0]['index'] and m['bytes']==[128,60,127])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    error_ns=off[field]-expected_off_ns
    c.results.append(dict(kind='pending-note-source-handoff',elapsed_ticks=elapsed_ticks,expected_off_ns=expected_off_ns,actual_off_ns=off[field],error_ns=error_ns))
    assert abs(error_ns)<=(2 if c.clock_mode=='controlled-experimental' else 10000000),c.results[-1]
    menu_value(c,'midi')
    reverse_live_clock_handoff(c)

def reverse_live_clock_handoff(c):
    import math,time
    # Establish100BPM on the internal reference while stopped, then return to
    # MIDI. This isolates phase/source transfer from internal24PPQN tempo
    # publication latency; pending tempo changes remain a separate edge case.
    c.enc(3,-1);menu_value(c,'internal');c.elapse(.1)
    c.enc(3,1);menu_value(c,'midi')
    controlled=c.clock_mode=='controlled-experimental'
    domain='logical' if controlled else 'monotonic'
    origin=c.logical_ns if controlled else time.monotonic_ns()+500000000
    events=[dict(port=1,bytes=[248],**{'at_'+domain+'_ns':origin+(i+1)*25000000}) for i in range(83)]
    events.append(dict(port=1,bytes=[252],**{'at_'+domain+'_ns':origin+84*25000000}))
    request=dict(type='midi_schedule',schedule_id=2,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    def until(pulse):
        if controlled:
            delta=origin+pulse*25000000-c.logical_ns
            assert delta>=0
            c.elapse(delta/1e9)
        else:c.wait(lambda s:len(s['midi_input_schedule']['delivered'])>=pulse)
    until(49)
    before=c.snapshot();start_beat=before['diagnostics']['beats'];marker=before['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    until(53);c.elapse(.001)  # Avoid observing exactly on a strict sync boundary.
    pending=c.snapshot();assert pending['midi_capture']['outstanding']
    elapsed_ticks=math.floor((pending['diagnostics']['beats']-start_beat)*96)
    assert 0<elapsed_ticks<48,elapsed_ticks
    switch_ack=c.action(type='enc',n=3,delta=-2)
    handoff=c.snapshot();beat=handoff['diagnostics']['beats']
    if not controlled:
        onset=next(m for m in pending['midi'] if m['index']>marker and m['bytes']==[144,60,127])
        applied=switch_ack['native']['monotonic_ns']
        start_beat=before['diagnostics']['beats']+(onset['monotonic_ns']-before['diagnostics']['monotonic_ns'])*(100/60)*1e-9
        elapsed_ticks=math.floor((applied-onset['monotonic_ns'])*160e-9)
        beat-=(handoff['diagnostics']['monotonic_ns']-applied)*(100/60)*1e-9
        assert 0<elapsed_ticks<48,elapsed_ticks
    assert abs(handoff['diagnostics']['tempo']-100)<1e-6,handoff['diagnostics']
    quantum=1/96;phase=start_beat%quantum;epsilon=2**-23
    next_beat=math.ceil((beat+epsilon)/quantum)*quantum+phase-quantum
    while next_beat<beat+epsilon:next_beat+=quantum
    remaining=(next_beat-beat)*.6+(48-elapsed_ticks-1)*.6/96
    expected_off=(c.logical_ns if controlled else applied)+remaining*1e9
    until(84)
    def onsets(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    # The scheduled MIDI Stop is no longer the selected transport. Internal
    # playback must continue into the next phrase until a physical grid Stop.
    c.wait(lambda state:len(onsets(state))>=4,timeout=2)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    state=c.snapshot();notes=onsets(state)
    assert [(m['port'],m['bytes']) for m in notes]==[(1,[144,60,127]),(1,[144,64,107]),(1,[144,67,100]),(1,[144,60,127])],notes
    off=next(m for m in state['midi'] if m['index']>notes[0]['index'] and m['bytes']==[128,60,127])
    field='logical_ns' if controlled else 'monotonic_ns';error=off[field]-expected_off
    c.results.append(dict(kind='pending-note-reverse-handoff',elapsed_ticks=elapsed_ticks,expected_off_ns=expected_off,actual_off_ns=off[field],error_ns=error))
    assert abs(error)<=(2 if controlled else 10000000),c.results[-1]
    arrivals=state['midi_input_schedule']['delivered']
    errors=[e['actual_'+domain+'_ns']-e['intended_'+domain+'_ns'] for e in arrivals]
    c.results.append(dict(kind='reverse-continuous-midi-arrival-errors',time_domain=domain,errors_ns=errors))
    assert len(arrivals)==84 and all(0<=e<=(0 if controlled else 10000000) for e in errors),errors
    menu_value(c,'internal')

def scale_edit_selection(c):
    from frame_oracle import header,matches
    def selected(slot,applied):
        expected=header('Scale slot '+str(slot)+' ',selected=1,tabs=3)
        c.wait(lambda state:matches(state,expected))
        c.results.append(dict(kind='scale-edit-header',slot=slot))
        levels=[15 if n==applied else 4 if n==slot else 2 for n in range(1,17)]
        c.led_values([(n,3) for n in range(1,17)],levels)
    def phrase(pitches):
        c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])])
    def shift_slot(slot):
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3)  # Native K1 hold threshold is250ms before script dispatch.
            c.tap(slot,3)
        finally:c.action(type='key',n=1,state=0)
    def long_slot(slot):
        c.action(type='grid',x=slot,y=3,state=1)
        try:c.elapse(1.1)
        finally:c.action(type='grid',x=slot,y=3,state=0)
        c.elapse(.06)
    c.configure();c.tap(4,8)
    selected(1,1)
    shift_slot(2);selected(2,1)
    # Root C -> D, saved through E2/E3/K3. Editing an unused scale must not
    # change playback: the applied C-major scale still governs these notes.
    c.enc(2,-1);c.enc(3,2);c.key(3)
    selected(2,1);phrase([60,62,64,65])
    c.tap(2,3);selected(2,2);phrase([62,64,66,67])
    # Long-selecting a different editor retains the D-major applied scale.
    long_slot(3);selected(3,2);phrase([62,64,66,67])
    # Saving an already applied scale does alter playback, even when selected
    # through the edit-only gesture. D -> E remains a major scale.
    shift_slot(2);selected(2,2)
    c.enc(3,2);c.key(3);phrase([64,66,68,69])
    # Select another editing slot, then long-press it again. Global off must
    # restore chromatic relative intervals and clear the editor indicator.
    long_slot(3);selected(3,2)
    long_slot(3);selected(0,0);phrase([60,61,62,63])
    # State can be re-entered following global off; stored scale edits persist.
    c.tap(2,3);selected(2,2);phrase([64,66,68,69])


def scale_lock_lifetime(c):
    from cases import menu_label,menu_value
    from frame_oracle import selected_line
    def phrase(pitches):
        c.playback([(1,[144,p,v]) for p,v in zip(pitches,[127,117,107,97])])
    def edit_slot(slot,semitones):
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3)  # Native K1 hold threshold is250ms before script dispatch.
            c.tap(slot,3)
        finally:c.action(type='key',n=1,state=0)
        c.enc(3,semitones);c.key(3)
    c.configure();c.tap(4,8);c.enc(2,-1)
    edit_slot(2,2);edit_slot(3,4)  # Unused D-major and E-major scales.
    # Global D lock at step1; channel E lock at step2. Four-step channel wraps
    # repeatedly inside the independent 64-step global scale track.
    c.hold_tap((1,4),(2,3));c.tap(3,8)
    c.hold_tap((2,4),(3,3))
    phrase([62,66,68,69])
    # Native menu navigation only; the diagnostic root names locate the group,
    # while rasterized labels and MIDI establish the user-perceived result.
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    roots=c.snapshot()['diagnostics']['parameter_roots']
    c.enc(2,next(i for i,v in enumerate(roots) if v['id']=='mosaic'))
    c.key(3)
    for _ in range(40):
        if selected_line(c.snapshot(),'Scales lock until ptn end'):break
        c.enc(2,1)
    else:raise AssertionError('Scale lifetime control absent from native menu')
    menu_label(c,'Scales lock until ptn end');menu_value(c,'On')
    c.enc(3,-1);menu_value(c,'Off');c.key(1)
    phrase([62,66,66,67])
    # Remove the channel lock by repeating its physical gesture. The global D
    # lock must still apply on every channel note with channel hold disabled.
    c.hold_tap((2,4),(3,3));phrase([62,64,66,67])
    # Remove global lock too: this restores the C-major default, proving the
    # preceding D phrase came from global persistence rather than stale state.
    c.tap(4,8);c.hold_tap((1,4),(2,3));c.tap(3,8)
    phrase([60,62,64,65])


def trig_merge_sets(c):
    c.configure()
    c.tap(5,8);c.tap(5,8);c.tap(4,3)  # Pattern1 fourth note F -> G.
    c.tap(5,8);c.tap(5,8)  # Back to trig editor.
    c.tap(2,1)
    for step in (2,4):c.tap(step,4)
    c.tap(3,8);c.tap(2,2)
    c.hold_tap((15,8),(1,2));c.hold_tap((16,8),(1,2))
    notes={1:(60,127),2:(62,117),3:(64,107),4:(67,97)}
    def phrase(steps):
        observed=c.playback([(1,[144,*notes[s]]) for s in steps])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[]
        for index,(a,b) in enumerate(zip(observed,observed[1:])):
            left=steps[index%len(steps)];right=steps[(index+1)%len(steps)]
            expected=((right-left)%4 or 4)/6
            errors.append((b[field]-a[field])/1e9-expected)
        c.results.append(dict(kind='merge-rest-spacing',steps=steps,errors_seconds=errors))
        assert errors and all(abs(e)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for e in errors),errors
    def mode(level,steps):
        c.led_values([(14,8)],[level]);phrase(steps)
    mode(2,[1,3])  # Exactly one contributing pattern.
    c.tap(14,8);mode(5,[2,4])  # Two contributors only.
    c.tap(14,8);mode(8,[1,2,3,4])  # Set union.
    # A third pattern overlapping step2 distinguishes exactly-one from odd
    # parity and proves Only accepts two or more contributors.
    c.tap(5,8);c.tap(3,1)
    for step in (2,3):c.tap(step,4)
    c.tap(3,8);c.tap(3,2)
    c.tap(14,8);mode(2,[1])
    c.tap(14,8);mode(5,[2,3,4])
    c.tap(14,8);mode(8,[1,2,3,4])
    # With one assigned pattern there are no overlaps. Only must be silent,
    # not keep a stale merged pattern after unassignment.
    c.tap(2,2);c.tap(3,2);c.tap(14,8);c.tap(14,8)
    c.led_values([(14,8)],[5]);before=c.snapshot()['midi_count']
    c.tap(1,8);c.elapse(1.5);c.tap(1,8)
    state=c.snapshot()
    emitted=[m for m in state['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
    assert not emitted,emitted
    assert not state['midi_capture']['outstanding']
    c.results.append(dict(kind='only-without-overlap-silent',seconds=1.5))


def all_pattern_slots(c):
    c.configure();c.tap(5,8)
    for x in range(1,5):c.tap(x,4)  # Clear only the fixture's initial trigs.
    pitches=[60,62,64,65,67,69,71]
    authored={};previous=1
    cells=[(x,y) for y in range(4,8) for x in range(1,17)]
    for slot in range(1,17):
        c.tap(slot,1)
        # An untouched slot must not inherit the previous slot's authored data.
        c.led_values(cells,[2]*64)
        x=1+(slot-1)%4
        active={(x,4),(slot,5),(17-slot,7)}
        for cell in sorted(active):c.tap(*cell)
        c.tap(5,8);c.tap(x,7-(slot-1)%7)
        c.tap(5,8);c.tap(5,8)
        expected=[15 if cell in active else 2 for cell in cells]
        c.led_values(cells,expected);authored[slot]=expected
        c.tap(3,8)
        if slot!=previous:
            c.tap(previous,2);c.tap(slot,2)
        c.led_values([(slot,2)],[15])
        # Four-step channel length excludes both deliberately authored outer
        # trigs. Exactly one pitched event per loop may reach the MIDI port.
        velocity=[127,117,107,97][x-1] if slot==1 else 100
        notes=c.playback([(1,[144,pitches[(slot-1)%7],velocity])])
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        errors=[(b[field]-a[field])/1e9-4/6 for a,b in zip(notes,notes[1:])]
        assert errors and all(abs(e)<=(2e-9 if c.clock_mode=='controlled-experimental' else .01) for e in errors),errors
        c.results.append(dict(kind='pattern-slot-playback',slot=slot,pitch=pitches[(slot-1)%7],spacing_errors_seconds=errors))
        previous=slot;c.tap(5,8)
    # Revisit every slot after all edits: editing slot16 must not overwrite
    # previous slots, even where pitches or active short-loop steps coincide.
    for slot in range(1,17):
        c.tap(slot,1);c.led_values(cells,authored[slot])


def scale_stop_indicator(c):
    c.configure();c.tap(4,8);c.tap(2,3)
    c.led_values([(2,3)],[15])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    # Stopping transport does not disable the applied scale. The bright
    # applied indicator must survive the playing-to-stopped transition.
    c.led_values([(2,3)],[15])
    # A held global step displays its own lock, not the stopped default.
    c.action(type='grid',x=2,y=4,state=1)
    try:
        c.tap(3,3);c.led_values([(2,3),(3,3)],[2,15])
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.led_values([(2,3),(3,3)],[15,2])

def channel_long_hold(c):
    c.configure()
    c.action(type='grid',x=2,y=4,state=1)
    try:c.elapse(1.1)
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.led_values([(x,4) for x in range(1,5)],[15,15,15,15])
    c.playback([(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]])
    c.action(type='grid',x=2,y=4,state=1)
    try:
        c.elapse(1.1);c.tap(4,4)
    finally:c.action(type='grid',x=2,y=4,state=0)
    c.led_values([(x,4) for x in range(1,5)],[0,15,15,15])
    notes=c.playback([(1,[144,n,v]) for n,v in [(62,117),(64,107),(65,97)]])
    field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
    tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
    c.results.append(dict(kind='range-loop-spacing',expected_seconds=1/6,actual_seconds=gaps))
    assert all(abs(gap-1/6)<=tolerance for gap in gaps),gaps

def adjacent_channel_ranges(c):
    # Fill every step through the pattern editor. The first four authored
    # pitches/velocities distinguish step addressing; later steps use C/100.
    c.configure();c.tap(5,8)
    cell=lambda step:((step-1)%16+1,(step-1)//16+4)
    for step in range(5,65):c.tap(*cell(step))
    c.tap(3,8)
    cells=[cell(step) for step in range(1,65)]
    values=[(60,127),(62,117),(64,107),(65,97)]+[(60,100)]*60
    # Every possible adjacent pair, including all row boundaries and step64.
    # Ascending ranges are documented; reversed endpoints remain a separate
    # failure-mode investigation, never silently normalized by this oracle.
    for start,end in [(s,s+1) for s in range(1,64)]+[(1,64)]:
        c.hold_tap(cell(start),cell(end))
        c.led_values(cells,[15 if start<=step<=end else 0 for step in range(1,65)])
        expected=[(1,[144,n,v]) for n,v in values[start-1:end]]
        notes=c.playback(expected,cycles=2,timeout=(end-start+1)/3+3)
        field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
        gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        c.results.append(dict(kind='adjacent-range',start=start,end=end,expected_gap_seconds=1/6,actual_gaps=gaps))
        assert all(abs(gap-1/6)<=tolerance for gap in gaps),dict(start=start,end=end,gaps=gaps)

def channel_mute_gestures(c):
    c.configure()
    phrase=[(1,[144,n,v]) for n,v in [(60,127),(62,117),(64,107),(65,97)]]
    def hold(seconds):
        c.action(type='grid',x=1,y=1,state=1)
        try:c.elapse(seconds)
        finally:c.action(type='grid',x=1,y=1,state=0)
    def shift_mute():
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3);c.tap(1,1)
        finally:c.action(type='key',n=1,state=0)
    def silence(seconds):
        before=c.snapshot()['midi_count'];c.elapse(seconds);state=c.snapshot()
        notes=[m for m in state['midi'] if m['index']>before and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        c.results.append(dict(kind='mute-silence',seconds=seconds,new_note_ons=notes))
        assert not notes,notes
        assert not state['midi_capture']['outstanding'],'Muted phrase retained active notes'
    hold(.8);c.led_values([(1,1)],[15]);c.playback(phrase)
    hold(1.1);c.led_values([(1,1)],[7])
    c.tap(1,8);silence(1.5);c.tap(1,8)
    shift_mute();c.led_values([(1,1)],[15]);c.playback(phrase)
    # Muting and unmuting during playback must leave transport running and
    # release existing notes; resumed pitches follow the unchanged phrase.
    c.tap(1,8)
    c.wait(lambda s:s['midi_capture']['outstanding']!=[])
    hold(1.1);c.led_values([(1,1)],[7]);silence(1.5)
    marker=c.snapshot()['midi_count'];shift_mute();c.led_values([(1,1)],[15])
    def emitted(s):
        return [m for m in s['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    state=c.wait(lambda s:len(emitted(s))>=9)
    actual=[(m['port'],m['bytes']) for m in emitted(state)]
    start=phrase.index(actual[0]);expected=[phrase[(start+i)%4] for i in range(len(actual))]
    assert actual==expected,dict(expected=expected,actual=actual)
    c.results.append(dict(kind='unmute-live-phrase',expected=expected,actual=actual))
    c.tap(1,8);c.wait(lambda s:not s['midi_capture']['outstanding'])

def channel_routing_isolation(c):
    c.configure()
    phrase=[(60,127),(62,117),(64,107),(65,97)]
    for channel in range(2,17):
        c.tap(channel,1)
        from frame_oracle import header,matches
        title='Ch. '+str(channel)+' Device Config';expected_header=header(title,selected=5)
        c.wait(lambda state:matches(state,expected_header))
        c.results.append(dict(kind='screen-header',expected=title,matched=True))
        c.enc(3,1) # none -> generic CC device
        c.enc(2,1);c.enc(3,channel-1) # distinct MIDI channel
        c.enc(2,1)
        if channel%2==0:c.enc(3,1) # second virtual port
        c.key(3);c.tap(1,2);c.hold_tap((1,4),(4,4))
        c.led_values([(channel,1),(1,2)],[15,15])
    def verify(active):
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        def ons(state):
            return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        if active:
            state=c.wait(lambda state:all(sum(m['bytes'][0]==143+ch for m in ons(state))>=9 for ch in active),timeout=5)
        else:
            c.elapse(1.5);state=c.snapshot()
        notes=ons(state)
        assert {m['bytes'][0]-143 for m in notes}==set(active),dict(active=active,actual=[m['bytes'] for m in notes])
        traces={}
        for ch in active:
            trace=[m for m in notes if m['bytes'][0]==143+ch]
            actual=[(m['port'],m['bytes']) for m in trace]
            expected=[(1 if ch%2 else 2,[143+ch,*phrase[i%4]]) for i in range(len(trace))]
            assert actual==expected,dict(channel=ch,expected=expected,actual=actual)
            field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
            times=[m[field] for m in trace];tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
            assert all(abs((b-a)/1e9-1/6)<=tolerance for a,b in zip(times,times[1:])),dict(channel=ch,times=times)
            traces[ch]=times
        # Equal-rate channels must stay aligned; retain within-channel order.
        if traces:
            firsts=[times[0] for times in traces.values()]
            tolerance_ns=2 if c.clock_mode=='controlled-experimental' else 10000000
            assert max(firsts)-min(firsts)<=tolerance_ns,firsts
        c.results.append(dict(kind='channel-routing-isolation',active_channels=active,note_on_count=len(notes),times_by_channel=traces))
        c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    def toggle(ch):
        c.action(type='key',n=1,state=1)
        try:
            c.elapse(.3);c.tap(ch,1)
        finally:c.action(type='key',n=1,state=0)
    verify(list(range(1,17)))
    for ch in range(1,17):
        toggle(ch);c.led_values([(ch,1)],[7 if ch==16 else 0]);verify(list(range(ch+1,17)))
    for ch in range(16,0,-1):
        toggle(ch);c.led_values([(ch,1)],[15 if ch==16 else 2]);verify(list(range(ch,17)))

def memory_navigation(c):
    from frame_oracle import render
    import base64
    c.configure();c.enc(1,-2);c.screen_header('Ch. 1 Memory')
    baseline=[(60,127),(62,117),(64,107),(65,97)]
    first=[(72,90),*baseline[1:]]
    both=[(72,90),(76,80),*baseline[2:]]
    branch=[(72,90),(62,117),(79,70),(65,97)]
    def counter(current,total):
        expected=render([(0,23,15,str(current)),(0,49,15,str(total))],font_size=10,antialias=1)
        indexes=[(y*128+x)*4+k for y in list(range(13,26))+list(range(39,52)) for x in range(16) for k in range(3)]
        def match(state):
            actual=base64.b64decode(state['frame']['pixels_base64'])
            return all(actual[i]==expected[i] for i in indexes)
        c.wait(match);c.results.append(dict(kind='memory-position',current=current,total=total,frame_matched=True))
    def phrase(values):c.playback([(1,[144,n,v]) for n,v in values],cycles=2)
    def record(step,note,velocity):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.action(type='midi',port=1,bytes=[144,note,velocity]);c.elapse(.05)
            c.action(type='midi',port=1,bytes=[128,note,0])
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1)
    counter(0,0);c.key(2);c.key(3);c.enc(3,-3);c.enc(3,3);counter(0,0);phrase(baseline)
    c.enc(1,-2);c.screen_header('Ch. 1 Note Masks');record(1,72,90);record(2,76,80)
    c.enc(1,2);counter(2,2);phrase(both)
    c.enc(3,-1);counter(1,2);phrase(first)
    c.enc(3,-1);counter(0,2);phrase(baseline)
    c.enc(3,-3);counter(0,2);phrase(baseline)
    c.enc(3,1);counter(1,2);phrase(first)
    c.enc(3,1);counter(2,2);phrase(both)
    c.enc(3,3);counter(2,2);phrase(both)
    c.key(2);counter(0,2);phrase(baseline)
    c.key(3);counter(2,2);phrase(both)
    c.enc(3,-1);counter(1,2)
    c.enc(1,-2);record(3,79,70);c.enc(1,2);counter(2,2);phrase(branch)
    c.key(3);counter(2,2);phrase(branch)
    c.key(2);counter(0,2);phrase(baseline)
    c.key(3);counter(2,2);phrase(branch)

def memory_channel_isolation(c):
    from frame_oracle import header,matches,render
    import base64
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.enc(1,-4)
    baseline=[(60,127),(62,117),(64,107),(65,97)]
    edited_one=[(72,90),*baseline[1:]]
    edited_two=[baseline[0],(79,80),*baseline[2:]]
    def record(step,note,velocity):
        c.action(type='grid',x=step,y=4,state=1)
        try:
            c.action(type='midi',port=1,bytes=[144,note,velocity]);c.elapse(.05)
            c.action(type='midi',port=1,bytes=[128,note,0])
        finally:c.action(type='grid',x=step,y=4,state=0)
        c.elapse(.1)
    def history(channel,current,total=1):
        expected=header('Ch. '+str(channel)+' Memory',selected=3)
        c.wait(lambda state:matches(state,expected))
        expected=render([(0,23,15,str(current)),(0,49,15,str(total))],font_size=10,antialias=1)
        indices=[(y*128+x)*4+k for y in list(range(13,26))+list(range(39,52)) for x in range(16) for k in range(3)]
        def match(state):
            pixels=base64.b64decode(state['frame']['pixels_base64'])
            return all(pixels[i]==expected[i] for i in indices)
        c.wait(match);c.results.append(dict(kind='channel-history-counter',channel=channel,current=current,total=total))
    def verify(one,two):
        marker=c.snapshot()['midi_count'];c.tap(1,8)
        def notes(state):return [m for m in state['midi'] if m['index']>marker and 144<=m['bytes'][0]<=159 and m['bytes'][2]>0]
        state=c.wait(lambda state:all(sum(m['bytes'][0]==status for m in notes(state))>=9 for status in (144,145)),timeout=5)
        observed=notes(state)
        assert {m['bytes'][0] for m in observed}=={144,145}
        for port,status,phrase in [(1,144,one),(2,145,two)]:
            actual=[(m['port'],m['bytes']) for m in observed if m['bytes'][0]==status]
            expected=[(port,[status,*phrase[i%4]]) for i in range(len(actual))]
            assert actual==expected,dict(channel=status-143,expected=expected,actual=actual)
            c.results.append(dict(kind='history-musical-isolation',channel=status-143,expected=expected,actual=actual))
        c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    record(2,79,80);c.tap(1,1);record(1,72,90);c.enc(1,2)
    history(1,1);verify(edited_one,edited_two)
    c.enc(3,-1);history(1,0);verify(baseline,edited_two)
    c.tap(2,1);history(2,1);c.key(2);history(2,0);verify(baseline,baseline)
    c.tap(1,1);history(1,0);c.key(3);history(1,1);verify(edited_one,baseline)
    c.tap(2,1);history(2,0);c.enc(3,1);history(2,1);verify(edited_one,edited_two)
    # Switching to an untouched channel and navigating its empty history must
    # not affect either audible channel or borrow their history counters.
    c.tap(3,1);history(3,0,0);c.key(2);c.key(3);c.enc(3,-2);c.enc(3,2);history(3,0,0);verify(edited_one,edited_two)
    c.tap(1,1);history(1,1);c.tap(2,1);history(2,1)

def live_record_placement(c,input_offsets=(1430000000,1730000000),expected_steps=(2,4),range_start=1,clock_delta=0,rate_factor=1,boundary_witness=False):
    import time
    c.configure()
    if boundary_witness:
        # An independent audible channel marks the active step through MIDI.
        # Same four-step range and clock; no application-state oracle.
        c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
        c.tap(1,2);c.hold_tap((1,4),(4,4))
        # Build a separate pattern; channel1's source will be cleared below.
        c.tap(5,8);c.tap(2,1)
        for x in range(1,5):c.tap(x,4)
        c.tap(5,8)
        for x,y in ((1,7),(2,6),(3,5),(4,4)):c.tap(x,y)
        c.tap(5,8)
        for x,y in ((1,1),(2,2),(3,3),(4,4)):c.tap(x,y)
        c.tap(3,8);c.tap(1,2);c.tap(2,2);c.tap(1,1)
    c.tap(5,8)
    if boundary_witness:c.tap(1,1)
    for x in range(1,5):c.tap(x,4)
    c.tap(3,8)
    cell=lambda step:((step-1)%16+1,(step-1)//16+4)
    if range_start!=1:c.hold_tap(cell(range_start),cell(range_start+3))
    cells=[cell(step) for step in range(1,65)]
    c.led_values(cells,[2 if range_start<=step<=range_start+3 else 0 for step in range(1,65)])
    if clock_delta:
        from frame_oracle import header,matches
        c.enc(1,-1);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
        c.enc(3,clock_delta);c.key(3)
    c.key(1);c.enc(1,4);c.key(3);menu_label(c,'LEVELS >')
    position=next(i for i,v in enumerate(c.snapshot()['diagnostics']['parameter_roots']) if v['name']=='CLOCK')
    c.enc(2,position);c.key(3);menu_label(c,'source');c.enc(3,1);menu_value(c,'midi');c.key(1)
    c.tap(2,8) # arm recording through the grid
    controlled=c.clock_mode=='controlled-experimental';domain='logical' if controlled else 'monotonic'
    origin=c.logical_ns+100000000 if controlled else time.monotonic_ns()+500000000
    # 24PPQN at100BPM:25ms pulses,150ms per sixteenth. FA follows49 warmup
    # pulses; pulse50 begins step1. Notes well inside steps2/4 isolate address
    # placement from the separate exact-boundary ordering campaign.
    packets=[(i*25000000,[248]) for i in range(1,113)]
    packets += [(1230000000,[250]),(input_offsets[0],[144,72,90]),(input_offsets[0]+20000000,[128,72,0]),(input_offsets[1],[144,79,80]),(input_offsets[1]+20000000,[128,79,0]),(2805000000,[252])]
    events=[dict(port=1,bytes=data,**{'at_'+domain+'_ns':origin+offset}) for offset,data in sorted(packets,key=lambda pair:pair[0])]
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+2820000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=5)
    state=c.snapshot();assert len(state['midi_input_schedule']['delivered'])==len(events)
    if boundary_witness:
        emitted=state['midi'];field='logical_ns' if controlled else 'monotonic_ns'
        arrivals=state['midi_input_schedule']['delivered']
        limit=0 if controlled else 10000000
        for sent,received in zip(events,arrivals):
            assert received['bytes']==sent['bytes'] and received['port']==sent['port']
            assert received['intended_'+domain+'_ns']==sent['at_'+domain+'_ns']
            assert 0<=received['actual_'+domain+'_ns']-received['intended_'+domain+'_ns']<=limit,received
        assert all(a['actual_'+domain+'_ns']<=b['actual_'+domain+'_ns'] for a,b in zip(arrivals,arrivals[1:]))
        witness=[m for m in emitted if m['port']==2 and m['bytes'][0]==145 and m['bytes'][2]>0]
        phrase=[(60,127),(62,117),(64,107),(65,97)]
        # FA at1.23s, first playback pulse at1.25s; stop at2.805s permits
        # exactly11 sixteenths at100BPM. Anchor to stimulus, not captured output.
        assert [m['bytes'] for m in witness]==[[145,*phrase[i%4]] for i in range(11)],witness
        for i,m in enumerate(witness):
            assert abs(m[field]-(origin+1250000000+i*150000000))<=(2 if controlled else 10000000),m
        evidence=[]
        for pitch,step in zip((72,79),expected_steps):
            active_pitch=phrase[step-1][0]
            preview=next(m for m in emitted if m['port']==1 and m['bytes'][:2]==[144,pitch])
            prior=[m for m in emitted if m['index']<preview['index'] and m['port']==2 and m['bytes'][0]==145 and m['bytes'][2]>0]
            following=[m for m in emitted if m['index']>preview['index'] and m['port']==2 and m['bytes'][0]==145 and m['bytes'][2]>0]
            assert prior and following,'Missing MIDI step witness'
            assert prior[-1]['bytes'][1]==active_pitch,dict(preview=preview,prior=prior[-1])
            assert following[0]['bytes'][1]==phrase[step%4][0]
            assert prior[-1][field]<=preview[field]<following[0][field]
            delivery=next(d for d in arrivals if d['bytes'][:2]==[144,pitch])
            assert 0<=preview[field]-delivery['actual_'+domain+'_ns']<=(0 if controlled else 10000000)
            if controlled and input_offsets==(1400000000,1700000000):
                assert following[0][field]-preview[field]==1
            evidence.append(dict(recorded_step=step,preview=preview,active_step_onset=prior[-1],next_step_onset=following[0],gap_to_next_ns=following[0][field]-preview[field]))
        c.results.append(dict(kind='boundary-active-step-midi-witness',events=evidence))
    c.wait(lambda state:not state['midi_capture']['outstanding']);c.tap(2,8)
    c.led_values(cells,[15 if step in expected_steps else (2 if range_start<=step<=range_start+3 else 0) for step in range(1,65)])
    c.results.append(dict(kind='recorded-step-placement',expected_steps=list(expected_steps),input_note_on_offsets_ns=list(input_offsets),clock_step_ns=round(150000000*rate_factor),channel_range=[range_start,range_start+3]))
    # Replay in normal internal clock after disarming; preview MIDI cannot
    # satisfy this oracle because playback takes a fresh capture marker.
    c.key(1);c.key(3);menu_label(c,'source');c.enc(3,-1);menu_value(c,'internal')
    c.enc(2,1);menu_label(c,'tempo');c.enc(3,-10);menu_value(c,'90');c.key(1)
    # Independent step positions define playback order, including wrap input.
    phrase=sorted(zip(expected_steps,[(1,[144,72,90]),(1,[144,79,80])]))
    if boundary_witness:
        c.tap(2,1);c.tap(2,2);c.tap(1,1)
    notes=c.playback([event for step,event in phrase],cycles=3)
    field='logical_ns' if controlled else 'monotonic_ns'
    gaps=[(b[field]-a[field])/1e9 for a,b in zip(notes,notes[1:])]
    expected_gaps=[((phrase[(i+1)%2][0]-phrase[i%2][0])%4)*rate_factor/6 for i in range(len(gaps))]
    tolerance=2e-9 if controlled else .01
    assert all(abs(gap-expected)<=tolerance for gap,expected in zip(gaps,expected_gaps)),dict(actual=gaps,expected=expected_gaps)
    c.results.append(dict(kind='recorded-replay-spacing',expected_seconds=expected_gaps,actual_seconds=gaps))

def recorded_note_channel_switch(c,hold_ns=500000000,expected_duration=.5,release_status=128,input_channel=1,disarm_while_held=False):
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.tap(1,1)
    c.tap(2,8);marker=c.snapshot()['midi_count'];c.tap(1,8)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    state=c.wait(lambda state:any(m['index']>marker and m['port']==1 and m['bytes']==[144,60,127] for m in state['midi']))
    anchor=next(m[field] for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127])
    # The next four-step loop starts2/3s after the observed first onset.
    # Enter50ms into step1; supply the requested hold with native deadlines.
    # Client snapshots/channel selection must not lengthen the keyboard hold.
    origin=anchor+666666667+50000000
    events=[dict(port=1,bytes=data,**{'at_'+field:origin+offset}) for offset,data in [(0,[143+input_channel,72,90]),(hold_ns,[release_status+input_channel-1,72,0])]]
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+100000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])>=1,timeout=2)
    c.tap(2,1)
    if disarm_while_held:c.tap(2,8)
    marker=c.snapshot()['midi_count']
    if controlled:c.elapse((origin+hold_ns+10000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==2,timeout=2)
    state=c.snapshot()
    c.results.append(dict(kind='scheduled-keyboard-hold',expected_ns=hold_ns,events=events,delivered=state['midi_input_schedule']['delivered']))
    releases=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=143 and m['bytes'][1]==72]
    c.results.append(dict(kind='held-input-release-route',expected=[(1,[128,72,0])],actual=releases))
    assert releases==[(1,[128,72,0])],releases
    if disarm_while_held:
        # New post-disarm notes may preview, but must not alter channel2 replay.
        c.action(type='midi',port=1,bytes=[144,79,80]);c.elapse(.03)
        c.action(type='midi',port=1,bytes=[128,79,0])
    c.tap(1,8)
    if not disarm_while_held:c.tap(2,8)
    c.wait(lambda state:not state['midi_capture']['outstanding'])
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0]
    state=c.wait(lambda state:all(sum(m['bytes'][0]==status for m in notes(state))>=13 for status in (144,145)),timeout=5)
    rows=notes(state);field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    for port,status,phrase,pitch,duration in [(1,144,[(72,90),(62,117),(64,107),(65,97)],72,expected_duration),(2,145,[(60,127),(62,117),(64,107),(65,97)],60,1/6)]:
        channel_notes=[m for m in rows if m['bytes'][0]==status]
        actual=[(m['port'],m['bytes']) for m in channel_notes];expected=[(port,[status,*phrase[i%4]]) for i in range(len(actual))]
        assert actual==expected,dict(expected=expected,actual=actual)
        durations=[]
        for note in [m for m in channel_notes if m['bytes'][1]==pitch][:3]:
            off=next(m for m in events if m['index']>note['index'] and m['port']==port and m['bytes'][:2]==[status-16,pitch])
            durations.append((off[field]-note[field])/1e9)
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        assert all(abs(value-duration)<=tolerance for value in durations),dict(channel=status-143,durations=durations,expected=duration)
        c.results.append(dict(kind='recording-origin-channel',channel=status-143,expected=expected,actual=actual,durations=durations,expected_duration=duration))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])

def live_playhead_feedback(c,clock_delta=0):
    import time
    c.configure()
    if clock_delta:
        from frame_oracle import header,matches
        c.enc(1,-1);c.wait(lambda state:matches(state,header('Ch. 1 Clocks',selected=4)))
        c.enc(3,clock_delta);c.key(3)
    marker=c.snapshot()['midi_count']
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    started=c.logical_ns if controlled else time.monotonic_ns()
    samples=[];settled=set();last_rows=[]
    # Grid redraw sleeps50ms. D permits only integer-nanosecond rounding;
    # R adds the existing10ms scheduler allowance, not a whole extra step.
    limit=50000002 if controlled else 60000000
    while (c.logical_ns if controlled else time.monotonic_ns())-started<3000000000:
        before=c.logical_ns if controlled else time.monotonic_ns()
        state=c.snapshot()
        after=c.logical_ns if controlled else time.monotonic_ns()
        rows=[m for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes'][0]==144 and m['bytes'][2]>0]
        if rows:
            expected=[[144,n,v] for n,v in [(60,127),(62,117),(64,107),(65,97)]]
            assert [m['bytes'] for m in rows]==[expected[i%4] for i in range(len(rows))]
            current=(len(rows)-1)%4+1;previous=(current-2)%4+1
            visible=[step for step in range(1,65) if state['grid'][48+step-1]==10]
            assert len(visible)<=1,visible
            age_low=before-rows[-1][field];age_high=after-rows[-1][field]
            if visible:assert visible[0] in (current,previous),dict(current=current,visible=visible)
            if age_low>limit:assert visible==[current],dict(current=current,visible=visible,age_low_ns=age_low,age_high_ns=age_high)
            if visible==[current]:settled.add(len(rows))
            samples.append(dict(note_ordinal=len(rows),current_step=current,visible=visible,age_lower_ns=age_low,age_upper_ns=age_high))
            last_rows=rows
            if len(rows)>=9 and 9 in settled:break
        c.elapse(.01 if controlled else .005)
    assert len(last_rows)>=9 and set(range(1,10))<=settled,dict(notes=len(last_rows),settled=sorted(settled))
    stale=[x for x in samples if x['visible']!=[x['current_step']]]
    c.results.append(dict(kind='live-playhead-latency',redraw_period_ns=50000000,maximum_allowed_stale_ns=limit,samples=samples,max_observed_stale_lower_ns=max([x['age_lower_ns'] for x in stale],default=0)))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    c.led_values([(x,4) for x in range(1,5)],[15]*4)

def keyboard_input_channels(c):
    import time
    c.configure();marker=c.snapshot()['midi_count']
    controlled=c.clock_mode=='controlled-experimental';field='logical_ns' if controlled else 'monotonic_ns'
    origin=c.logical_ns+100000000 if controlled else time.monotonic_ns()+500000000
    events=[];expected=[];ordinal=0
    for port in (1,2):
        for channel in range(1,17):
            for release in (128,144):
                note=60+(channel-1)%12;onset=origin+ordinal*60000000
                events += [dict(port=port,bytes=[143+channel,note,90],**{'at_'+field:onset}),dict(port=port,bytes=[release+channel-1,note,0],**{'at_'+field:onset+30000000})]
                expected += [(1,[144,note,90]),(1,[128,note,0])]
                ordinal+=1
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+ordinal*60000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=6)
    state=c.snapshot();assert len(state['midi_input_schedule']['delivered'])==128
    actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    assert actual==expected,dict(expected=expected,actual=actual)
    assert not state['midi_capture']['outstanding']
    c.results.append(dict(kind='keyboard-input-channel-matrix',input_ports=[1,2],input_channels=list(range(1,17)),release_status_types=[128,144],expected=expected,actual=actual))

def overlapping_keyboard_sources(c,second_port=2,second_channel=1):
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    for order in ((0,1),(1,0)):
        c.tap(1,1);marker=c.snapshot()['midi_count']
        c.action(type='midi',port=1,bytes=[144,72,90])
        c.tap(2,1);c.action(type='midi',port=second_port,bytes=[143+second_channel,72,80])
        inputs=[(1,1),(second_port,second_channel)]
        expected=[(1,[144,72,90]),(2,[145,72,80])]
        for owner in order:
            port,channel=inputs[owner]
            c.action(type='midi',port=port,bytes=[127+channel,72,0])
            expected.append((owner+1,[128+owner,72,0]))
            state=c.snapshot()
            actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
            assert actual==expected,dict(release_order=order,expected=expected,actual=actual)
        assert not state['midi_capture']['outstanding']
        c.results.append(dict(kind='overlapping-keyboard-source-isolation',input_sources=inputs,release_order=order,expected=expected,actual=actual))

def recorded_chord_release(c,release_order=(76,79,72),onset_offsets=(0,0,0),preview_release_ns=None,release_offsets=(300000000,400000000,500000000)):
    c.configure();c.tap(2,8)
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    state=c.wait(lambda state:any(m['index']>marker and m['port']==1 and m['bytes']==[144,60,127] for m in state['midi']))
    anchor=next(m[field] for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127])
    origin=anchor+666666667+50000000
    packets=[(offset,[144,pitch,90]) for offset,pitch in zip(onset_offsets,(72,76,79))]
    packets += [(offset,[128,pitch,0]) for offset,pitch in zip(release_offsets,release_order)]
    if preview_release_ns is not None:
        packets += [(100000000,[144,83,80]),(preview_release_ns,[128,83,0])]
    packets.sort(key=lambda item:item[0])
    events=[dict(port=1,bytes=data,**{'at_'+field:origin+offset}) for offset,data in packets]
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+(10000000 if preview_release_ns is not None else 100000000)-c.logical_ns)/1e9)
    else:c.wait(lambda state:sum(event['bytes'][0]==144 and event['bytes'][1] in (72,76,79) for event in state['midi_input_schedule']['delivered'])>=3,timeout=2)
    c.tap(2,8) # Disarm after all three chord presses; some voices may already be released.
    if controlled:c.elapse((origin+max(500000000,preview_release_ns or 0)+10000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=2)
    state=c.snapshot()
    c.results.append(dict(kind='scheduled-recorded-chord',release_order=release_order,events=events,delivered=state['midi_input_schedule']['delivered']))
    if preview_release_ns is not None:
        preview=[(m['port'],m['bytes']) for m in state['midi'] if m['bytes'][1:2]==[83] and m['bytes'][0] in (128,144)]
        expected_preview=[(1,[144,83,80]),(1,[128,83,0])]
        c.results.append(dict(kind='post-disarm-preview',expected=expected_preview,actual=preview))
        assert preview==expected_preview,dict(expected=expected_preview,actual=preview)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0]==144 and m['bytes'][2]>0]
    state=c.wait(lambda state:len(notes(state))>=19,timeout=5)
    rows=notes(state)
    phrase=[(72,90),(76,90),(79,90),(62,117),(64,107),(65,97)]
    expected=[(1,[144,*phrase[i%6]]) for i in range(len(rows))]
    actual=[(m['port'],m['bytes']) for m in rows]
    c.results.append(dict(kind='recorded-chord-replay',expected=expected,actual=actual))
    assert actual==expected,dict(expected=expected,actual=actual)
    durations=[]
    for note in [m for m in rows if m['bytes'][1] in (72,76,79)][:9]:
        off=next(m for m in state['midi'] if m['index']>note['index'] and m['port']==1 and m['bytes'][:2]==[128,note['bytes'][1]])
        durations.append((off[field]-note[field])/1e9)
    tolerance=2e-9 if controlled else .01
    c.results.append(dict(kind='recorded-chord-length',expected=.5,actual=durations,release_order=release_order))
    assert len(durations)==9 and all(abs(value-.5)<=tolerance for value in durations),dict(expected=.5,durations=durations,release_order=release_order)
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])

def recorded_input_sources(c,second_port=2,second_channel=1):
    hold_ns=500000000;expected_duration=.5;release_status=128;input_channel=1;disarm_while_held=False
    c.configure();c.tap(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.enc(2,1);c.enc(3,1);c.key(3)
    c.tap(1,2);c.hold_tap((1,4),(4,4));c.tap(1,1)
    c.tap(2,8);marker=c.snapshot()['midi_count'];c.tap(1,8)
    controlled=c.clock_mode=='controlled-experimental'
    field='logical_ns' if controlled else 'monotonic_ns'
    state=c.wait(lambda state:any(m['index']>marker and m['port']==1 and m['bytes']==[144,60,127] for m in state['midi']))
    anchor=next(m[field] for m in state['midi'] if m['index']>marker and m['port']==1 and m['bytes']==[144,60,127])
    # The next four-step loop starts2/3s after the observed first onset.
    # Enter20ms into step1, select channel2, then enter its note100ms later.
    # Client snapshots/channel selection must not lengthen the keyboard hold.
    origin=anchor+666666667+20000000
    events=[dict(port=1,bytes=data,**{'at_'+field:origin+offset}) for offset,data in [(0,[143+input_channel,72,90]),(hold_ns,[release_status+input_channel-1,72,0])]]
    events += [dict(port=second_port,bytes=data,**{'at_'+field:origin+offset}) for offset,data in [(100000000,[143+second_channel,72,80]),(600000000,[127+second_channel,72,0])]]
    events.sort(key=lambda event:event['at_'+field])
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+10000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])>=1,timeout=2)
    c.tap(2,1)
    if disarm_while_held:c.tap(2,8)
    marker=c.snapshot()['midi_count']
    if controlled:c.elapse((origin+610000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==4,timeout=2)
    state=c.snapshot()
    c.results.append(dict(kind='scheduled-keyboard-hold',expected_ns=hold_ns,events=events,delivered=state['midi_input_schedule']['delivered']))
    releases=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=143 and m['bytes'][1]==72]
    c.results.append(dict(kind='held-input-release-route',expected=[(1,[128,72,0]),(2,[129,72,0])],actual=releases))
    assert releases==[(1,[128,72,0]),(2,[129,72,0])],releases
    if disarm_while_held:
        # New post-disarm notes may preview, but must not alter channel2 replay.
        c.action(type='midi',port=1,bytes=[144,79,80]);c.elapse(.03)
        c.action(type='midi',port=1,bytes=[128,79,0])
    c.tap(1,8)
    if not disarm_while_held:c.tap(2,8)
    c.wait(lambda state:not state['midi_capture']['outstanding'])
    marker=c.snapshot()['midi_count'];c.tap(1,8)
    def notes(state):return [m for m in state['midi'] if m['index']>marker and m['bytes'][0] in (144,145) and m['bytes'][2]>0]
    state=c.wait(lambda state:all(sum(m['bytes'][0]==status for m in notes(state))>=13 for status in (144,145)),timeout=5)
    rows=notes(state);field='logical_ns' if c.clock_mode=='controlled-experimental' else 'monotonic_ns'
    for port,status,phrase,pitch,duration in [(1,144,[(72,90),(62,117),(64,107),(65,97)],72,expected_duration),(2,145,[(72,80),(62,117),(64,107),(65,97)],72,.5)]:
        channel_notes=[m for m in rows if m['bytes'][0]==status]
        actual=[(m['port'],m['bytes']) for m in channel_notes];expected=[(port,[status,*phrase[i%4]]) for i in range(len(actual))]
        assert actual==expected,dict(expected=expected,actual=actual)
        durations=[]
        for note in [m for m in channel_notes if m['bytes'][1]==pitch][:3]:
            off=next(m for m in events if m['index']>note['index'] and m['port']==port and m['bytes'][:2]==[status-16,pitch])
            durations.append((off[field]-note[field])/1e9)
        tolerance=2e-9 if c.clock_mode=='controlled-experimental' else .01
        assert all(abs(value-duration)<=tolerance for value in durations),dict(channel=status-143,durations=durations,expected=duration)
        c.results.append(dict(kind='recording-origin-channel',channel=status-143,expected=expected,actual=actual,durations=durations,expected_duration=duration))
    c.tap(1,8);c.wait(lambda state:not state['midi_capture']['outstanding'])

def keyboard_pitch_range(c):
    import time
    c.configure();marker=c.snapshot()['midi_count']
    controlled=c.clock_mode=='controlled-experimental';field='logical_ns' if controlled else 'monotonic_ns'
    origin=c.logical_ns+100000000 if controlled else time.monotonic_ns()+500000000
    events=[];expected=[];ordinal=0
    for note in range(128):
        for release,velocity in ((128,1),(144,127)):
            onset=origin+ordinal*30000000
            events += [dict(port=1,bytes=[144,note,velocity],**{'at_'+field:onset}),dict(port=1,bytes=[release,note,0],**{'at_'+field:onset+15000000})]
            expected += [(1,[144,note,velocity]),(1,[128,note,0])]
            ordinal+=1
    request=dict(type='midi_schedule',schedule_id=1,events=events)
    if controlled:request['time_domain']='logical'
    c.action(**request)
    if controlled:c.elapse((origin+ordinal*30000000-c.logical_ns)/1e9)
    else:c.wait(lambda state:len(state['midi_input_schedule']['delivered'])==len(events),timeout=12)
    state=c.snapshot();assert len(state['midi_input_schedule']['delivered'])==512
    actual=[(m['port'],m['bytes']) for m in state['midi'] if m['index']>marker and 128<=m['bytes'][0]<=159]
    assert actual==expected,dict(expected=expected,actual=actual)
    assert not state['midi_capture']['outstanding']
    c.results.append(dict(kind='keyboard-pitch-range',pitches=list(range(128)),velocities=[1,127],release_status_types=[128,144],expected=expected,actual=actual))


def muted_sparse_reverse_arp(c,shape):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4)
    c.enc(2,1);c.enc(3,51) # Unset -1 -> velocity50.
    c.enc(2,1);c.enc(3,89);length_mask_display(c,'128')
    c.enc(2,4);c.enc(3,8) # Only mask4 is populated: octave; others remain unset.
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,8)
    c.enc(2,1);assign_trig_parameter(c,'Chord Pattern');c.enc(3,shape)
    c.enc(2,1);assign_trig_parameter(c,'Mute Chord Root');c.enc(3,1)
    c.enc(2,1);assign_trig_parameter(c,'Chord Velocity Mod');c.enc(3,10)
    capture=MidiWindow(c.snapshot()['midi_count']);trigger=c.logical_ns;c.tap(1,8);c.elapse(8.5);capture.extend(c.snapshot())
    controlled=c.clock_mode=='controlled-experimental';lower=c.logical_ns if controlled else time.monotonic_ns()
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns if controlled else time.monotonic_ns()
    c.elapse(1);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    expected=[(0,72,50),(540,72,100),(1080,72,127)]
    field='logical_ns' if controlled else 'monotonic_ns';notes=capture.note_ons();assert notes
    if controlled:assert abs(notes[0]['logical_ns']-trigger)<=2,'Sparse reverse initial note missed trigger'
    rows=assert_schedule(capture.events,expected,[108]*3,field=field,origin=notes[0][field],stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='muted-sparse-reverse-arp',shape=shape,onsets=3,releases=len(rows),velocity_ordinals=[0,5,10],passed=True))


def arp_rest_live_scale(c,fully_masked=False):
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    assert c.clock_mode=='controlled-experimental','Absolute live-edit schedule requires controlled time until D20 mapping is admitted'
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4)
    if fully_masked:c.enc(3,61) # Explicit C4 mask, then use full scale processing.
    c.enc(2,1);c.enc(3,51);c.enc(2,1);c.enc(3,89);length_mask_display(c,'128')
    c.enc(2,1);c.enc(3,3);c.enc(2,2);c.enc(3,5)
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    values=[('Chord Note Arpeggio',8),('Chord Spread',5),('Chord Accel Mod',1),('Chord Velocity Mod',10),('Mute Chord Root',1)]
    if fully_masked:values.append(('Quantise Note Mask',2))
    for index,(label,value) in enumerate(values):
        if index:c.enc(2,1)
        assign_trig_parameter(c,label);c.enc(3,value)
    capture=MidiWindow(c.snapshot()['midi_count']);origin=c.logical_ns
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.elapse(2);capture.extend(c.snapshot())
    c.tap(4,8);c.enc(2,-1);c.enc(3,2);c.key(3) # Applied scale C-major -> D-major during a rest.
    assert (c.logical_ns-origin)/1e9<4.5,'Scale edit missed its declared rest window'
    c.elapse(14-(c.logical_ns-origin)/1e9);capture.extend(c.snapshot());lower=c.logical_ns
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns;c.elapse(1);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    expected=[(162,64,60),(648,69,80),(1782,66,110)]
    rows=assert_schedule(capture.events,expected,[108]*3,field='logical_ns',origin=origin,stop_bounds=(lower,upper),tolerance=2e-9)
    c.results.append(dict(kind='arp-rest-live-scale',fully_masked=fully_masked,onsets=3,releases=len(rows),ordinals=[1,3,6],passed=True))


def arp_empty_muted_replacement(c):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8);c.tap(4,4);c.tap(3,8)
    c.enc(1,-4);c.enc(2,2);c.enc(3,22);length_mask_display(c,'3')
    c.enc(2,1);c.enc(3,1) # Global chord1 Off; other masks unset.
    for x in (1,3):
        c.action(type='grid',x=x,y=4,state=1)
        try:c.enc(3,2) # Third only for the first and replacement trigger.
        finally:c.action(type='grid',x=x,y=4,state=0)
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio');c.enc(3,18) # Two-step notes/onsets.
    c.enc(2,1);assign_trig_parameter(c,'Mute Chord Root');c.enc(3,1)
    for x in (1,3):
        c.action(type='grid',x=x,y=4,state=1)
        try:c.enc(3,-1)
        finally:c.action(type='grid',x=x,y=4,state=0)
    capture=MidiWindow(c.snapshot()['midi_count']);trigger=c.logical_ns
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.elapse(6.75);capture.extend(c.snapshot())
    controlled=c.clock_mode=='controlled-experimental';lower=c.logical_ns if controlled else time.monotonic_ns()
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns if controlled else time.monotonic_ns();c.elapse(2);capture.extend(c.snapshot())
    c.wait(lambda state:not state['midi_capture']['outstanding'])
    # Empty-muted trigger at216 cancels the old onset due432, preserving
    # its root release432. Old gate648 cannot cut replacement root due864.
    # Replacement chord begins864 and is drained by Stop972 before gate1080.
    expected=[(0,60,127),(432,64,107),(864,67,107)]
    notes=capture.note_ons();assert notes;field='logical_ns' if controlled else 'monotonic_ns'
    origin=trigger if controlled else notes[0][field]
    rows=assert_schedule(capture.events,expected,[432,432,216],field=field,origin=origin,stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='empty-muted-replacement-release-ownership',onsets=3,releases=len(rows),empty_trigger_pulse=216,old_gate_pulse=648,passed=True))


def chord_dashboard_display(c, root_velocity):
    import base64
    from frame_oracle import render
    # Literal user-facing pitches/velocity for MIDI60 +64/67/69/72 (norns labels C3/E3/G3/A3/C4).
    # Only the three complete root value widgets are compared here. Chord-slot
    # persistence remains a separate dashboard coverage obligation.
    expected=render([(0,18,1,'Note'),(0,26,1,'C3'),
                     (25,18,1,'Vel'),(25,26,1,str(root_velocity)),
                     (50,18,1,'Len'),(50,26,1,'4.0')])
    indices=[(y*128+x)*4+k for y in range(11,29) for x in range(75) for k in range(3)]
    def matches(state):
        actual=base64.b64decode(state['frame']['pixels_base64'])
        return all(actual[i]==expected[i] for i in indices)
    c.wait(matches,timeout=.5)
    c.results.append(dict(kind='chord-root-dashboard',note='C3',velocity=root_velocity,length='4.0',
                          source='rendered framebuffer',passed=True))


def chord_shape_schedule(c,arp,shape,muted,mask_bits=15,velocity=50,modifier=10,extra=None,dashboard=False):
    import time
    from midi_window import MidiWindow
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4);c.enc(2,1);c.enc(3,velocity+1)
    c.enc(2,1);c.enc(3,26);length_mask_display(c,'4')
    for i,turns in enumerate((3,5,6,8)):
        c.enc(2,1)
        if mask_bits&(1<<i):c.enc(3,turns)
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio' if arp else 'Chord Note Strum');c.enc(3,0 if extra=='disabled' else 8)
    c.enc(2,1);assign_trig_parameter(c,'Chord Pattern');c.enc(3,shape)
    c.enc(2,1);assign_trig_parameter(c,'Mute Chord Root');c.enc(3,int(muted))
    c.enc(2,1);assign_trig_parameter(c,'Chord Velocity Mod');c.enc(3,modifier)
    if extra=='accelerating':
        c.enc(2,1);assign_trig_parameter(c,'Chord Spread');c.enc(3,5)
        c.enc(2,1);assign_trig_parameter(c,'Chord Accel Mod');c.enc(3,-1)
    if dashboard:c.enc(1,4) # Trig Locks to Note Dashboard, stopped.
    capture=MidiWindow(c.snapshot()['midi_count']);trigger=c.logical_ns
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    c.elapse(2.625 if extra=='early-stop' else 3.25);capture.extend(c.snapshot());controlled=c.clock_mode=='controlled-experimental'
    lower=c.logical_ns if controlled else time.monotonic_ns()
    c.action(type='grid',x=1,y=8,state=1);c.action(type='grid',x=1,y=8,state=0)
    upper=c.logical_ns if controlled else time.monotonic_ns();c.elapse(1);capture.extend(c.snapshot());c.wait(lambda state:not state['midi_capture']['outstanding'])
    order={1:(0,1,2,3,4),2:(4,3,2,1,0),3:(0,1,4,2,3),4:(4,1,3,2,0)}[shape]
    pitches=(60,64,67,69,72)
    expected=[(ordinal*108,pitches[slot],max(0,min(127,velocity+ordinal*modifier))) for ordinal,slot in enumerate(order) if (slot==0 and not muted) or (slot>0 and mask_bits&(1<<(slot-1)))]
    if extra=='disabled':expected=[(0,pitch,vel) for _,pitch,vel in expected]
    elif extra=='accelerating':
        ticks={0:0,108:162,216:270,324:324}
        expected=[(ticks[tick],pitch,vel) for tick,pitch,vel in expected if tick in ticks]
    elif extra=='early-stop':expected=[row for row in expected if row[0]<378]
    if arp and mask_bits==0:
        expected=[] if muted else [(i*108,60,max(0,min(127,velocity+i*modifier))) for i in range(5)] # Root-only ratchet, independent of shape.
    notes=capture.note_ons();assert notes or not expected
    field='logical_ns' if controlled else 'monotonic_ns'
    origin=trigger if controlled else (notes[0][field]-expected[0][0]/144*1e9 if notes else 0)
    if not expected:
        assert not [m for m in capture.events if m['bytes'][0]&240 in (128,144)],'Silent chord emitted MIDI notes/releases'
        rows=[]
    elif modifier<0:
        # Zero-velocity Note On is a wire-level Note Off; inspect the explicit
        # zero messages separately instead of pretending they opened voices.
        ons=[m for m in capture.events if m['bytes'][0]&240==144]
        offs=[m for m in capture.events if m['bytes'][0]&240==128]
        assert len(ons)==len(offs)==len(expected),'Velocity-bound MIDI count'
        tolerance=2e-9 if controlled else .01
        pending={}
        for event,(tick,pitch,vel) in zip(ons,expected):
            assert (event['port'],event['bytes'])==(1,[144,pitch,vel]),('Clamped velocity',event,pitch,vel)
            assert abs((event[field]-origin)/1e9-tick/144)<=tolerance
            pending[pitch]=vel
        for event in offs:
            pitch=event['bytes'][1];assert pitch in pending,'Duplicate or unrelated velocity release'
            assert event['port']==1 and event['bytes'][0]==128 and event['bytes'][2] in (0,pending.pop(pitch))
            assert lower-tolerance*1e9<=event[field]<=upper+tolerance*1e9,'Release outside Stop drain'
        assert not pending;rows=offs
    else:
        rows=assert_schedule(capture.events,expected,[108 if arp else 864]*len(expected),field=field,origin=origin,stop_bounds=(lower,upper),tolerance=2e-9 if controlled else .01)
    c.results.append(dict(kind='chord-shape-slots',arp=arp,shape=shape,muted=muted,mask_bits=mask_bits,onsets=len(expected),release_checks=len(rows),passed=True))

    if dashboard:chord_dashboard_display(c,max(0,min(127,velocity+(4*modifier if shape in (2,4) else 0))))

def navigation_matrix(c):
    # Independent six-page model: the pattern key cycles three editors.
    # Check each intermediate menu state and re-play the authored melody after
    # every source/destination pair so navigation cannot silently alter music.
    pages=('channel','scale','trig','note','velocity','song')
    pattern_pages=('trig','note','velocity')
    menus={'channel':[15,2,2,2], 'scale':[2,15,2,2],
           'trig':[2,2,5,2], 'note':[2,2,10,2],
           'velocity':[2,2,15,2], 'song':[2,2,2,15]}
    melody=[(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))]
    c.configure();current='channel';edges=[];presses=0
    def choose(target):
        nonlocal current, presses
        if target in pattern_pages:
            count=((pattern_pages.index(target)-pattern_pages.index(current))%3 or 3) if current in pattern_pages else pattern_pages.index(target)+1
            button=5
        else:
            count=1;button={'channel':3,'scale':4,'song':6}[target]
        for _ in range(count):
            c.tap(button,8);presses+=1
            if button==5:
                current=pattern_pages[(pattern_pages.index(current)+1)%3] if current in pattern_pages else 'trig'
            else:current={3:'channel',4:'scale',6:'song'}[button]
            c.led_values([(x,8) for x in (3,4,5,6)],menus[current])
        assert current==target
    for source in pages:
        for target in pages:
            choose(source);choose(target)
            notes=c.playback(melody,cycles=2)
            assert len(notes)>=9
            c.led_values([(x,8) for x in (3,4,5,6)],menus[target])
            edges.append([source,target])
    assert len(edges)==36 and len({tuple(edge) for edge in edges})==36
    c.results.append(dict(kind='navigation-matrix',source_destination_pairs=edges,
                          menu_presses=presses,melody_checks=36,passed=True))


def panic_hold(c, button, source, repeats=1):
    menus={'channel':[15,2,2,2], 'scale':[2,15,2,2],
           'trig':[2,2,5,2], 'note':[2,2,10,2],
           'velocity':[2,2,15,2], 'song':[2,2,2,15]}
    selected={'channel':3,'scale':4,'trig':5,'note':5,'velocity':5,'song':6}[source]
    c.tap(3,8)
    if source in ('trig','note','velocity'):
        for _ in range(('trig','note','velocity').index(source)+1):c.tap(5,8)
    elif source!='channel':c.tap(selected,8)
    menu=menus[source];c.led_values([(x,8) for x in (3,4,5,6)],menu)
    expected=[[128+channel,note,0] for note in range(128) for channel in range(16)] if button!=selected else []
    for repeat in range(repeats):
        after=c.snapshot()['midi_count'];start=len(c.observations)
        logical_start=c.logical_ns;press_ack=c.action(type='grid',x=button,y=8,state=1)
        c.elapse(.9);c.snapshot()
        # Live snapshots drive observation only; full exported MIDI is the oracle.
        for _ in range(10):
            c.elapse(.1);c.snapshot()
            if len(c.observations)>start+2:del c.observations[start+1:-1]
        c.action(type='grid',x=button,y=8,state=0);c.elapse(.06);cursor=c.snapshot()['midi_count']
        c.led_values([(x,8) for x in (3,4,5,6)],menu)
        if not hasattr(c,'panic_windows'):c.panic_windows=[]
        c.panic_windows.append(dict(type='panic',after=after,cursor=cursor,source=source,
                                   button=button,repeat=repeat,logical_start=logical_start,press_ack=press_ack))


def panic_navigation(c, button):
    c.configure();panic_hold(c,button,'song');finish_panic_trace(c)


def panic_hold_matrix(c):
    c.configure();pairs=[]
    for source in ('channel','scale','trig','note','velocity','song'):
        for button in (3,4,5,6):
            panic_hold(c,button,source,repeats=2)
            after=c.snapshot()['midi_count']
            c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
            c.panic_windows.append(dict(type='melody',after=after,cursor=c.snapshot()['midi_count']))
            pairs.append([source,button])
    assert len(pairs)==24
    finish_panic_trace(c,dict(kind='panic-hold-matrix',pairs=pairs,holds=48,melody_checks=24,passed=True))



def finish_panic_trace(c, summary=None):
    import json
    from automation.input_origin import verified_input_origin
    from panic_trace import verify_panic_trace
    c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        actions=[json.loads(line) for line in (c.out/'native/actions.jsonl').read_text().splitlines()]
        controlled=c.clock_mode=='controlled-experimental'
        for window in c.panic_windows:
            if window['type']!='panic':continue
            ack=window['press_ack']
            submitted=[e for e in events if e.get('kind')=='input' and e['sequence']==ack['native']['sequence']]
            assert len(submitted)==1
            evidence=verified_input_origin(events,actions,session_id=c.runtime.id,action_id=ack['action_id'],
                expected_action=dict(type='grid',x=window['button'],y=8,state=1),declared_origin_ns=submitted[0]['monotonic_ns'])
            window['input_origin']=evidence
            window['minimum_ns']=window['logical_start']+1_000_000_000-2 if controlled else evidence['origin_ns']+900_000_000
        (c.out/'panic-windows.json').write_text(json.dumps(c.panic_windows,indent=2)+'\n')
        verify_panic_trace(events,c.panic_windows,11 if controlled else 3,c.results)
        if summary:c.results.append(summary)
    finally:
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')

def panic_live_note_stop(c):
    import json
    c.configure();c.tap(5,8)
    for x in range(1,5):c.tap(x,4)
    c.tap(6,8);c.tap(1,8);c.elapse(.2)
    before=c.snapshot()['midi_count']
    c.action(type='grid',x=5,y=8,state=1)
    released=False;played=False
    try:
        c.wait(lambda s:any(e['index']>before and e['port']==1 and e['bytes']==[143,24,0] for e in s['midi']),timeout=2)
        c.action(type='grid',x=5,y=8,state=0);released=True
        c.action(type='midi',port=1,bytes=[144,24,100]);played=True
        c.wait(lambda s:any(e['index']>before and e['port']==3 and e['bytes']==[143,127,0] for e in s['midi']),timeout=2)
        c.elapse(.05);stop_before=c.snapshot()['midi_count']
        c.tap(1,8);c.elapse(.1);stop_after=c.snapshot()['midi_count']
    finally:
        if not released:c.action(type='grid',x=5,y=8,state=0)
        if played:c.action(type='midi',port=1,bytes=[128,24,0]);c.elapse(.1)
    c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        assert all(e['kind']==(11 if c.clock_mode=='controlled-experimental' else 3) for e in midi)
        notes=[e for e in midi if e['bytes'][0]&240 in (128,144)]
        ons=[e for e in notes if e['bytes'][0]&240==144 and e['bytes'][2]>0]
        assert len(ons)==1 and (ons[0]['port'],ons[0]['bytes'])==(1,[144,24,100]),'Quiet transport or live keyboard note differs'
        onset=ons[0]['sequence']
        sweep=[e for e in midi[before:stop_before] if e['bytes'][0]&240==128]
        expected=[[128+channel,note,0] for note in range(128) for channel in range(16)]
        assert len(sweep)==6144
        for port in (1,2,3):assert [e['bytes'] for e in sweep if e['port']==port]==expected
        prior=[e for e in sweep if e['port']==1 and e['bytes']==[128,24,0]]
        last=[e for e in sweep if e['port']==1 and e['bytes']==[143,127,0]]
        assert prior[0]['sequence']<onset<last[0]['sequence'],'Input missed the required in-flight overlap'
        stops=[e for e in midi[stop_before:stop_after] if e['bytes'][0]&240 in (128,144)]
        c.results.append(dict(kind='panic-live-note-stop',onset=onset,stop_before=stop_before,stop_after=stop_after,actual=[(e['port'],e['bytes']) for e in stops]))
        assert [(e['port'],e['bytes']) for e in stops]==[(1,[128,24,0])],'Stop failed to release the live note played behind the panic sweep'
        cleanup=[e for e in midi[stop_after:] if e['bytes'][0]&240 in (128,144)]
        assert [(e['port'],e['bytes']) for e in cleanup]==[(1,[128,24,0])],'Keyboard release cleanup differs'
        assert len(notes)==6147,'Unexpected note output outside the complete sweep/live/stop/release trace'
        c.results.append(dict(kind='panic-live-note-stop-complete',passed=True))
    finally:
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def panic_overlapping_holds(c, repeats):
    import json
    from panic_repeat_trace import verify_restarted_sweeps
    from panic_trace import verify_panic_trace
    c.configure();c.tap(6,8)
    before=c.snapshot()['midi_count'];held=[]
    try:
        for button in (3,4,5)[:repeats]:
            c.action(type='grid',x=button,y=8,state=1);held.append(button);c.elapse(.12)
        c.elapse(1.9)
    finally:
        for button in held:c.action(type='grid',x=button,y=8,state=0)
    c.elapse(.1);after=c.snapshot()['midi_count']
    c.led_values([(x,8) for x in (3,4,5,6)],[2,2,2,15])
    melody_before=c.snapshot()['midi_count']
    c.playback([(1,[144,n,v]) for n,v in ((60,127),(62,117),(64,107),(65,97))],cycles=2)
    melody_after=c.snapshot()['midi_count'];c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1))
        kind=11 if c.clock_mode=='controlled-experimental' else 3
        assert all(e['kind']==kind for e in midi)
        c.results.append(verify_restarted_sweeps(midi[before:after],repeats))
        # Reuse the independent melody oracle on a reindexed copy of that window.
        melody=[dict(e,sequence=i+1,index=i+1) for i,e in enumerate(midi[melody_before:melody_after])]
        verify_panic_trace(melody,[dict(type='melody',after=0,cursor=len(melody))],kind,c.results)
        outside=midi[:before]+midi[after:melody_before]+midi[melody_after:]
        assert not [e for e in outside if e['bytes'][0]&240 in (128,144)],'Notes outside panic/melody windows'
        c.results.append(dict(kind='panic-overlap-complete-stream',repeats=repeats,passed=True))
    finally:
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


def panic_pending_chord(c, arp, shape):
    import json
    from automation.input_origin import verified_input_origin
    from automation.scheduling_metrics import scheduling_metrics
    from note_schedule import assert_schedule
    c.configure();c.hold_tap((1,4),(16,7));c.tap(5,8)
    for x in (2,3,4):c.tap(x,4)
    c.tap(3,8);c.enc(1,-4);c.enc(2,1);c.enc(3,51)
    c.enc(2,1);c.enc(3,26);length_mask_display(c,'4')
    for turns in (3,5,6,8):c.enc(2,1);c.enc(3,turns)
    c.enc(1,3);c.enc(3,-11);c.key(3);c.enc(1,-2)
    assign_trig_parameter(c,'Chord Note Arpeggio' if arp else 'Chord Note Strum');c.enc(3,8)
    c.enc(2,1);assign_trig_parameter(c,'Chord Pattern');c.enc(3,shape)
    c.enc(2,1);assign_trig_parameter(c,'Chord Velocity Mod');c.enc(3,10)
    c.tap(6,8);logical_start=c.logical_ns
    c.action(type='grid',x=1,y=8,state=1);start_ack=c.action(type='grid',x=1,y=8,state=0)
    c.elapse(.1);panic_before=c.snapshot()['midi_count']
    c.action(type='grid',x=5,y=8,state=1)
    try:c.elapse(1.9)
    finally:c.action(type='grid',x=5,y=8,state=0)
    c.elapse(.06);panic_after=c.snapshot()['midi_count']
    c.led_values([(x,8) for x in (3,4,5,6)],[2,2,2,15])
    c.elapse(1.19);logical_stop=c.logical_ns
    c.action(type='grid',x=1,y=8,state=1);stop_ack=c.action(type='grid',x=1,y=8,state=0)
    c.elapse(1);c.snapshot();c.finish()
    try:
        events=[json.loads(line) for line in (c.out/'native/native-events.jsonl').read_text().splitlines()]
        actions=[json.loads(line) for line in (c.out/'native/actions.jsonl').read_text().splitlines()]
        def origin(ack):
            submitted=[e for e in events if e.get('kind')=='input' and e['sequence']==ack['native']['sequence']]
            assert len(submitted)==1
            return verified_input_origin(events,actions,session_id=c.runtime.id,action_id=ack['action_id'],expected_action=dict(type='grid',x=1,y=8,state=0),declared_origin_ns=submitted[0]['monotonic_ns'])
        start,stop=origin(start_ack),origin(stop_ack)
        controlled=c.clock_mode=='controlled-experimental';kind=11 if controlled else 3;field='logical_ns' if controlled else 'monotonic_ns'
        midi=[e for e in events if e.get('kind') in (3,11)]
        assert [e['sequence'] for e in midi]==list(range(1,len(midi)+1)) and all(e['kind']==kind for e in midi)
        sweep=[e for e in midi[panic_before:panic_after] if e['bytes'][0]&240==128 and e['bytes'][2]==0]
        expected_sweep=[[128+channel,note,0] for note in range(128) for channel in range(16)]
        assert len(sweep)==6144,'Incomplete panic during chord playback'
        for port in (1,2,3):assert [e['bytes'] for e in sweep if e['port']==port]==expected_sweep
        sweep_ids={e['sequence'] for e in sweep};musical=[e for e in midi if e['sequence'] not in sweep_ids]
        order=(0,1,2,3,4) if shape==1 else (4,3,2,1,0)
        pitches=(60,64,67,69,72)
        expected=[(ordinal*108,pitches[slot],50+ordinal*10) for ordinal,slot in enumerate(order)]
        onset_events=[e for e in musical if e['bytes'][0]&240==144 and e['bytes'][2]>0]
        assert len(onset_events)==5
        # Require active voices before the sweep and pending voices after it.
        assert onset_events[1][field]<min(e[field] for e in sweep)<onset_events[2][field]
        assert max(e[field] for e in sweep)<onset_events[3][field]
        initial=logical_start if controlled else start['origin_ns']
        bounds=(logical_stop,logical_stop) if controlled else (stop['origin_ns'],stop['applied_ns'])
        from panic_transport import verify_panic_transport
        start_bounds=(logical_start,logical_start) if controlled else (start['origin_ns'],start['applied_ns'])
        c.results.append(verify_panic_transport(midi,field=field,start_bounds=start_bounds,stop_bounds=bounds))
        rows=assert_schedule(musical,expected,[108 if arp else 864]*5,field=field,origin=initial,stop_bounds=bounds,tolerance=2e-9 if controlled else .01)
        metrics=None
        if not controlled:
            planned=[dict(port=1,bytes=[144,pitch,velocity],intent_ns=initial+ordinal*750_000_000,deadline_ns=initial+ordinal*750_000_000) for ordinal,(_,pitch,velocity) in enumerate(expected)]
            metrics=scheduling_metrics(planned,onset_events)
            assert metrics['within_event_profile'],('Pending chord onset scheduling',metrics)
        c.results.append(dict(kind='panic-pending-chord',arp=arp,shape=shape,sweep_events=len(sweep),onsets=5,releases=len(rows),start_origin=start,stop_origin=stop,metrics=metrics,passed=True))
    finally:
        (c.out/'results.json').write_text(json.dumps(c.results,indent=2)+'\n')


from panic_hotplug import panic_hotplug
from patch_params import patch_boundaries,patch_play_recall
from patch_matrix import patch_cc_matrix

from output_cases import jf_same_voice_overlap, jf_keyboard_ownership, jf_mono_phrase,doubledecker_audition

from patch_params import patch_nrpn_restart,patch_nrpn_boundary_matrix,patch_nrpn_slide,patch_configured_off_lock

from trig_parameter_interactions import fixed_note_domain,quantised_fixed_table,stock_pitch_lock_inheritance,competing_pitch_locks,probability_endpoint_locks,seeded_probability,probability_midi_locks,live_parameter_recording

from shuffle_inheritance import shuffle_type_inheritance,live_shuffle_type_inheritance

from shuffle_mixed_channels import mixed_shuffle_inheritance

from shuffle_field_inheritance import shuffle_field_inheritance

from song_length_domain import song_length_domain

from song_length_sparse import sparse_song_lengths

from song_repetitions import song_repetition_domain

from song_tempo import song_tempo_bounds

from external_start_phase import external_start_phase

from external_cold_start import external_cold_start

from external_started_handoff import external_started_handoff

from repeated_external_start import repeated_external_start

from acquisition_stop import acquisition_stop

from fast_acquisition import fast_acquisition

from master_clock import master_clock

from master_lifecycle import master_lifecycle

from master_multi_output import master_multi_output

from forwarded_clock import cold_forwarded_clock,warm_forwarded_clock

CASES={
 'M-SYNC-012':dict(run=cold_forwarded_clock,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Cold external clock on port1; Mosaic notes and forwarded port2 receiver align to original input, no input-port clock echo'),
 'M-SYNC-013':dict(run=warm_forwarded_clock,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Warmed external clock on port1; Mosaic and forwarded port2 receiver keep absolute input phase'),
 'M-SYNC-011':dict(run=master_multi_output,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Two clock outputs enabled through native menu: independent receiver note phase/count, disabled third port, no note-routing leakage'),
 'M-SYNC-010':dict(run=master_lifecycle,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Master pending/active Start cancellation at zero,1ms,25ms; clock continues, no late notes/Start, no held voices, independent restart phase'),
 'M-SYNC-009':dict(run=master_clock,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Mosaic master: native clock-output menu, Start/Clock/note ordering and independent24PPQN receiver phase across four local start delays'),
 'M-SYNC-008':dict(run=fast_acquisition,requirements=['CLOCK-MIDI-TRANSPORT-001','CH-TEMPO','MIDI-RELEASE-001'],description='Cold20BPM MIDI at x8: reconcile the one unknowable pre-acquisition step at Clock2, preserve subsequent absolute deadlines and balanced gates'),
 'M-SYNC-007':dict(run=acquisition_stop,requirements=['CLOCK-MIDI-TRANSPORT-001','MIDI-RELEASE-001'],description='Cold20BPM external Start then Stop before Clock2: timely first-note release and no restart as subsequent clocks acquire tempo'),
 'M-SYNC-006':dict(run=repeated_external_start,requirements=['CLOCK-MIDI-TRANSPORT-001','MIDI-RELEASE-001'],description='Repeated incoming Start during a held note resets to step1 at the next external Clock, releases the previous note and preserves absolute phase'),
 'M-SYNC-005':dict(run=external_started_handoff,requirements=['CLOCK-LIVE-HANDOFF-001','CLOCK-MIDI-TRANSPORT-001'],description='Incoming Start then MIDI-to-internal source switch preserves phrase order and prevents epoch-driven note bursts'),
 'M-SYNC-003':dict(run=lambda c:external_cold_start(c,bpm=20),requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Cold20BPM external clock: first note and all phrase deadlines through initial unknown-tempo acquisition'),
 'M-SYNC-004':dict(run=lambda c:external_cold_start(c,bpm=300),requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Cold300BPM external clock: absolute startup, phase and releases'),
 'M-SYNC-002':dict(run=external_cold_start,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Cold external Start followed by first-ever24PPQN clock: absolute beat origin, phrase timing and note releases'),
 'M-SYNC-001':dict(run=external_start_phase,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Warmed external24PPQN clock with four Start phases, absolute first-clock-to-note alignment, full phrase phase and releases'),
 'M-SONG-SETTINGS-002':dict(run=song_tempo_bounds,requirements=['SONG-SETTINGS','SONG-SLOTS'],description='Global tempo30/300 bounds and90 restoration persist across manually selected octave-fingerprinted slots, screen values and exact MIDI gates/phase'),
 'M-SONG-SETTINGS-001':dict(run=song_repetition_domain,requirements=['SONG-SETTINGS','SONG-LENGTH','SONG-ADVANCE','SONG-SLOTS'],description='All16 slot1 repetition counts with unchanged slot2 repeat1, octave fingerprints, exact transition indices, phase and MIDI releases'),
 'M-SONG-LENGTH-002':dict(run=sparse_song_lengths,requirements=['SONG-LENGTH','CH-RANGE'],description='Sparse four-trig full-range channel at global1/2/63/64 then shrink2, independent silent-gap/repeat timing and every MIDI release'),
 'M-SONG-LENGTH-001':dict(run=song_length_domain,requirements=['SONG-LENGTH','CH-RANGE'],description='All64 global fader values, lower/upper clamp attempts, shrink/full restoration through exact tooltip and all64 channel LEDs'),
 'M-SHUFFLE-009':dict(run=lambda c:shuffle_field_inheritance(c,'feel'),requirements=['CH-SHUFFLE','CH-CLOCK-INHERIT'],description='Inherited feel: untouched X, minimum/maximum local overrides and restored X under nondefault global Shuffle, exact MIDI phase and gates'),
 'M-SHUFFLE-010':dict(run=lambda c:shuffle_field_inheritance(c,'basis'),requirements=['CH-SHUFFLE','CH-CLOCK-INHERIT'],description='Inherited basis: untouched X, minimum/maximum local overrides and restored X under nondefault global Shuffle, exact MIDI phase and gates'),
 'M-SHUFFLE-011':dict(run=lambda c:shuffle_field_inheritance(c,'amount'),requirements=['CH-SHUFFLE','CH-CLOCK-INHERIT'],description='Inherited amount: untouched X, minimum/maximum local overrides and restored X under nondefault global Shuffle, exact MIDI phase and gates'),

 'M-SHUFFLE-008':dict(run=mixed_shuffle_inheritance,requirements=['CH-SHUFFLE','CH-CLOCK-INHERIT','CH-DEVICE'],description='Simultaneous inheriting and explicit Swing channels across global Shuffle/Swing/Shuffle edits, independent MIDI routing, phase and gates'),
 'M-SHUFFLE-007':dict(run=lambda c:live_shuffle_type_inheritance(c,override=True),requirements=['CH-SHUFFLE','CH-CLOCK-INHERIT'],description='Live explicit Swing override retains inherited Shuffle until the global boundary, then preserves straight phase and complete gates'),
 'M-SHUFFLE-006':dict(run=live_shuffle_type_inheritance,requirements=['CH-SHUFFLE','CH-CLOCK-INHERIT'],description='Live restoration of X waits for the global boundary rather than the shorter channel loop, with complete MIDI gates and exact phase'),
 'M-SHUFFLE-005':dict(run=shuffle_type_inheritance,requirements=['CH-SHUFFLE','CH-CLOCK-INHERIT'],description='Untouched and explicitly restored inheritance follow global Shuffle; local Swing and Shuffle overrides preserve exact MIDI gates and phase'),
 'M-SHUFFLE-001':dict(run=lambda c:shuffle_matrix(c,'Drunk'),requirements=['CH-SHUFFLE'],description='All six bases and amount boundary/midpoint/restoration for Drunk, exact MIDI phase and complete shuffled gates'),
 'M-SHUFFLE-002':dict(run=lambda c:shuffle_matrix(c,'Smooth'),requirements=['CH-SHUFFLE'],description='All six bases and amount boundary/midpoint/restoration for Smooth, exact MIDI phase and complete shuffled gates'),
 'M-SHUFFLE-003':dict(run=lambda c:shuffle_matrix(c,'Heavy'),requirements=['CH-SHUFFLE'],description='All six bases and amount boundary/midpoint/restoration for Heavy, exact MIDI phase and complete shuffled gates'),
 'M-SHUFFLE-004':dict(run=lambda c:shuffle_matrix(c,'Clave'),requirements=['CH-SHUFFLE'],description='All six bases and amount boundary/midpoint/restoration for Clave, exact MIDI phase and complete shuffled gates'),

 'M-MERGE-042':dict(run=lambda c:fractional_length_mask_merge(c,hierarchy=True),requirements=['MERGE-LENGTH','MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-PRECEDENCE'],description='Step length masks override channel masks; clearing either layer independently preserves and reveals the next duration source'),
 'M-MERGE-039':dict(run=lambda c:fractional_length_mask_merge(c,0),requirements=['MERGE-LENGTH','MASK-ATTRIBUTES'],description='Fractional channel length masks override changing merge modes; removal restores exact numeric duration including nonpositive gates'),
 'M-MERGE-040':dict(run=lambda c:fractional_length_mask_merge(c,1),requirements=['MERGE-LENGTH','MASK-ATTRIBUTES'],description='Fractional channel length masks override changing merge modes; removal restores exact numeric duration including nonpositive gates'),
 'M-MERGE-041':dict(run=lambda c:fractional_length_mask_merge(c,2),requirements=['MERGE-LENGTH','MASK-ATTRIBUTES'],description='Fractional channel length masks override changing merge modes; removal restores exact numeric duration including nonpositive gates'),
 'M-MERGE-035':dict(run=lambda c:numeric_length_merge(c,3,strum=True,simultaneous=True,same_pitch=False),requirements=['MERGE-LENGTH','CHORD-STRUM'],description='Simultaneous zero/negative ordinary voices preserve exact interleaved On/Off order, including identical MIDI pitches'),
 'M-MERGE-036':dict(run=lambda c:numeric_length_merge(c,4,strum=True,simultaneous=True,same_pitch=False),requirements=['MERGE-LENGTH','CHORD-STRUM'],description='Simultaneous zero/negative ordinary voices preserve exact interleaved On/Off order, including identical MIDI pitches'),
 'M-MERGE-037':dict(run=lambda c:numeric_length_merge(c,3,strum=True,simultaneous=True,same_pitch=True),requirements=['MERGE-LENGTH','CHORD-STRUM'],description='Simultaneous zero/negative ordinary voices preserve exact interleaved On/Off order, including identical MIDI pitches'),
 'M-MERGE-038':dict(run=lambda c:numeric_length_merge(c,4,strum=True,simultaneous=True,same_pitch=True),requirements=['MERGE-LENGTH','CHORD-STRUM'],description='Simultaneous zero/negative ordinary voices preserve exact interleaved On/Off order, including identical MIDI pitches'),
 'M-MERGE-033':dict(run=lambda c:numeric_length_merge(c,3,strum=True),requirements=['MERGE-LENGTH','CHORD-STRUM'],description='Nonpositive merged lengths release delayed strum voices without an extra scheduler pulse and retain balanced MIDI'),
 'M-MERGE-034':dict(run=lambda c:numeric_length_merge(c,4,strum=True),requirements=['MERGE-LENGTH','CHORD-STRUM'],description='Nonpositive merged lengths release delayed strum voices without an extra scheduler pulse and retain balanced MIDI'),
 'M-MERGE-031':dict(run=lambda c:numeric_length_merge(c,3,True),requirements=['MERGE-LENGTH','CHORD-ARP'],description='Zero or negative merged arp gate cancels future ratchets, releases initial note once, and survives repeated transport'),
 'M-MERGE-032':dict(run=lambda c:numeric_length_merge(c,4,True),requirements=['MERGE-LENGTH','CHORD-ARP'],description='Zero or negative merged arp gate cancels future ratchets, releases initial note once, and survives repeated transport'),
 'M-MERGE-028':dict(run=lambda c:numeric_length_merge(c,3),requirements=['MERGE-LENGTH'],description='Nonpositive numeric note lengths retain Note On followed by same-pulse release, exact ordering and no stuck notes'),
 'M-MERGE-029':dict(run=lambda c:numeric_length_merge(c,4),requirements=['MERGE-LENGTH'],description='Nonpositive numeric note lengths retain Note On followed by same-pulse release, exact ordering and no stuck notes'),
 'M-MERGE-030':dict(run=lambda c:numeric_length_merge(c,5),requirements=['MERGE-LENGTH'],description='Nonpositive numeric note lengths retain Note On followed by same-pulse release, exact ordering and no stuck notes'),
 'M-MERGE-025':dict(run=lambda c:numeric_length_merge(c,0),requirements=['MERGE-LENGTH'],description='Numeric length merging with literal rounded arithmetic, all modes and exact MIDI release timing'),
 'M-MERGE-026':dict(run=lambda c:numeric_length_merge(c,1),requirements=['MERGE-LENGTH'],description='Numeric length merging with literal rounded arithmetic, all modes and exact MIDI release timing'),
 'M-MERGE-027':dict(run=lambda c:numeric_length_merge(c,2),requirements=['MERGE-LENGTH'],description='Numeric length merging with literal rounded arithmetic, all modes and exact MIDI release timing'),
 'M-MERGE-024':dict(run=velocity_zero_boundary,requirements=['MERGE-VELOCITY'],description='Zero and negative numeric velocity results clamp without wrapping, with raw MIDI releases and exact timing'),
 'M-MERGE-043':dict(run=lambda c:numeric_note_merge(c,True,False,harmony=True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER','SCALE-EDIT','PAT-SCALE-RELATIVE','OPT-PENTATONIC-MERGED'],description='Merge modes across degree II, two-tone octave rotation, D root and restored C-major cache state; pentatonic False, exact MIDI gates and phase'),
 'M-MERGE-044':dict(run=lambda c:numeric_note_merge(c,True,True,harmony=True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER','SCALE-EDIT','PAT-SCALE-RELATIVE','OPT-PENTATONIC-MERGED'],description='Merge modes across degree II, two-tone octave rotation, D root and restored C-major cache state; pentatonic True, exact MIDI gates and phase'),
 'M-MERGE-023':dict(run=lambda c:numeric_note_merge(c,True,True,True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER','SCALE-EDIT','OPT-PENTATONIC-MERGED'],description='All ten reviewed modal pentatonic selections across numeric merge modes, negative degrees, exact MIDI and timing'),
 'M-MERGE-022':dict(run=lydian_octave_boundary,requirements=['MERGE-NOTE-AVERAGE','SCALE-EDIT'],description='Rootless Lydian pentatonic nearest-pitch snapping is octave-equivalent for merged degrees -7/0/7'),
 'M-MERGE-021':dict(run=lambda c:numeric_velocity_merge(c,True),requirements=['MERGE-VELOCITY','MERGE-NOTE-PATTERN'],description='Numeric velocity Average/Higher/Lower: rounded means, upper MIDI clamp and unassigned note-priority isolation'),
 'M-MERGE-020':dict(run=lambda c:numeric_velocity_merge(c,False),requirements=['MERGE-VELOCITY','MERGE-NOTE-PATTERN'],description='Numeric velocity Average/Higher/Lower: rounded means, upper MIDI clamp and unassigned note-priority isolation'),
 'M-MERGE-019':dict(run=lambda c:numeric_note_merge(c,True,False,True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER','SCALE-EDIT','PAT-SCALE-RELATIVE','OPT-PENTATONIC-MERGED'],description='All ten scale types across Average/Higher/Lower, negative degrees and exact MIDI timing with independent interval tables'),
 'M-MERGE-018':dict(run=lambda c:merge_rounding(c,extreme=False,pentatonic=True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER'],description='Signed/extreme note merging with pentatonic=True, exact output beyond editor input range and octave-crossing quantisation'),
 'M-MERGE-017':dict(run=lambda c:merge_rounding(c,extreme=True,pentatonic=True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER'],description='Signed/extreme note merging with pentatonic=True, exact output beyond editor input range and octave-crossing quantisation'),
 'M-MERGE-016':dict(run=lambda c:merge_rounding(c,extreme=True,pentatonic=False),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER','PAT-SCALE-RELATIVE'],description='Signed/extreme note merging with pentatonic=False, exact output beyond editor input range and octave-crossing quantisation'),
 'M-MERGE-015':dict(run=lambda c:merge_rounding(c,True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER'],description='Signed fractional means with 3 contributors, half ties, equal values, all numeric modes and assignment-order invariance'),
 'M-MERGE-014':dict(run=lambda c:merge_rounding(c,False),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-NOTE-LOWER'],description='Signed fractional means with 2 contributors, half ties, equal values, all numeric modes and assignment-order invariance'),
 'M-MERGE-013':dict(run=lambda c:merge_mode_cycle(c,'length'),requirements=['MERGE-LENGTH','MERGE-CONTROL'],description='Repeated Average/Higher/Lower/Average control cycles preserve displayed and audible length merge mode'),
 'M-MERGE-012':dict(run=lambda c:merge_mode_cycle(c,'velocity'),requirements=['MERGE-VELOCITY','MERGE-CONTROL'],description='Repeated Average/Higher/Lower/Average control cycles preserve displayed and audible velocity merge mode'),
 'M-MERGE-011':dict(run=lambda c:numeric_note_merge(c,True,True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','SCALE-EDIT','OPT-PENTATONIC-MERGED'],description='Numeric Average/Higher with pentatonic filtering across C major, D major, D minor and restored scale; unassigned velocity source stays isolated'),
 'M-MERGE-009':dict(run=numeric_note_merge,requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER'],description='Two assigned patterns: independent Average/Higher degree arithmetic, C-major pitches, velocity priority isolation and exact timing'),
 'M-MERGE-010':dict(run=lambda c:numeric_note_merge(c,True),requirements=['MERGE-NOTE-AVERAGE','MERGE-NOTE-HIGHER','MERGE-VELOCITY'],description='Unassigned velocity-priority source must not contribute notes to numeric merge'),
 'M-REC-PARAM-027':dict(run=lambda c:recording_lifetime(c,'persistence'),requirements=['REC-PARAM-AUTOMATION','MEMORY-RECORD','PERSIST-AUTO-001'],description='Recorded locks and undo position survive autosave and two fresh native processes; persisted redo restores recorded step after restart'),
 'M-REC-PARAM-026':dict(run=lambda c:recording_lifetime(c,'memory-branch'),requirements=['REC-PARAM-AUTOMATION','MEMORY-RECORD','MEMORY-NAV'],description='New lock edit after undo branches recorded automation history; latest/undo/redo/past-end preserve independent step2 and cannot resurrect abandoned step4'),
 'M-REC-PARAM-025':dict(run=lambda c:recording_lifetime(c,'memory'),requirements=['REC-PARAM-AUTOMATION','MEMORY-RECORD','MEMORY-NAV'],description='Undo and redo each of three recorded parameter steps: restore overwritten lock96 and unbound defaults, exact disarmed MIDI replay after every action'),
 'M-REC-PARAM-024':dict(run=recording_ten_slots,requirements=['REC-PARAM-AUTOMATION'],description='All ten recording slots: staggered odd zero/even one edits, untouched-slot isolation, exact MIDI deadlines and distinct-default disarmed replay'),
 'M-REC-PARAM-023':dict(run=lambda c:recording_lifetime(c,'mute'),requirements=['REC-PARAM-AUTOMATION','CH-MUTE'],description='Mute spans eligible recording steps: no MIDI during mute, correctly phased resume and distinct-default disarmed lock replay'),
 'M-REC-PARAM-022':dict(run=recording_stop_safety,requirements=['REC-PARAM-AUTOMATION','REC-ARM','NAV-TRANSPORT'],description='Long Stop under Shift press to stop clears pending parameter recording while retaining arm and previously recorded steps'),
 'M-PARAM-040':dict(run=lambda c:random_note_domains(c,pentatonic=True,mask='full'),requirements=['PARAM-RANDOM','PARAM-RANDOM-TWOS','OPT-PENTATONIC-RANDOM','MASK-SCALE'],description='Signed random and twos composition with full masks, exact seeded MIDI, zero restoration and musical timing'),
 'M-PARAM-041':dict(run=lambda c:random_note_domains(c,pentatonic=True,mask='snap'),requirements=['PARAM-RANDOM','PARAM-RANDOM-TWOS','OPT-PENTATONIC-RANDOM','MASK-SCALE'],description='Signed random and twos composition with snap masks, exact seeded MIDI, zero restoration and musical timing'),
 'M-PARAM-042':dict(run=lambda c:random_note_domains(c,pentatonic=True,mask='raw'),requirements=['PARAM-RANDOM','PARAM-RANDOM-TWOS','OPT-PENTATONIC-RANDOM','MASK-SCALE'],description='Signed random and twos composition with raw masks, exact seeded MIDI, zero restoration and musical timing'),
 'M-PARAM-039':dict(run=lambda c:random_note_domains(c,pentatonic=True),requirements=['PARAM-RANDOM','PARAM-RANDOM-TWOS','OPT-PENTATONIC-RANDOM'],description='Signed nonzero random offsets obey nearest pentatonic filtering; zero and disabled random retain original notes; Codex-arbitrated contract'),
 'M-PARAM-037':dict(run=lambda c:random_note_domains(c,twos=False),requirements=['PARAM-RANDOM','PARAM-RANDOM-TWOS'],description='Literal random offset domains0..4, separate seeded PRNG exact MIDI, random plus twos composition, zero restoration and full gates/phase; twos=False'),
 'M-PARAM-038':dict(run=lambda c:random_note_domains(c,twos=True),requirements=['PARAM-RANDOM','PARAM-RANDOM-TWOS'],description='Literal random offset domains0..4, separate seeded PRNG exact MIDI, random plus twos composition, zero restoration and full gates/phase; twos=True'),
 'M-PARAM-036':dict(run=lambda c:pitch_lock_isolation(c,reassign=True),requirements=['PARAM-SLOTS','PARAM-FIXED','PARAM-QUANTISED-FIXED','LOCK-PARAM-SET'],description='Fixed/quantised/None slot reassignment retains raw zero/tie/127 values, same-target confirmation preserves locks, dormant locks do not apply, second MIDI channel remains unchanged'),
 'M-PARAM-035':dict(run=lambda c:pitch_lock_isolation(c,history=True,persistence=True),requirements=['PARAM-SLOTS','PARAM-FIXED','PARAM-QUANTISED-FIXED','MEMORY-RECORD','PERSIST-AUTO-001'],description='Two cold starts preserve fixed/quantised extreme locks, channel-isolated branch history, saved undone position and redo via native Memory UI and exact MIDI'),
 'M-PARAM-034':dict(run=lambda c:pitch_lock_isolation(c,history=True),requirements=['PARAM-SLOTS','PARAM-FIXED','PARAM-QUANTISED-FIXED','MEMORY-TRUNCATE','MEMORY-RECORD'],description='Independent pitch-lock undo/redo on two MIDI channels, zero/127 restoration and new edit after undo discards only its channel redo history'),
 'M-PARAM-032':dict(run=pitch_lock_isolation,requirements=['PARAM-SLOTS','PARAM-FIXED','PARAM-QUANTISED-FIXED','LOCK-PARAM-SET'],description='Two MIDI channels: independent fixed/quantised zero and127 locks, clear/default/Off interactions, exact phrases/gates/phase'),
 'M-PARAM-033':dict(run=lambda c:pitch_lock_isolation(c,song_copy=True),requirements=['PARAM-SLOTS','PARAM-FIXED','PARAM-QUANTISED-FIXED','LOCK-PARAM-SET'],description='Copied song retains independent fixed/quantised locks; editing and clearing copy preserves original song including zero/127 extremes'),
 'M-PARAM-031':dict(run=lambda c:sparse_editor_domain(c,'NS6'),requirements=['PARAM-SLOTS','PARAM-OFF','LOCK-PARAM-SET'],description='Native NS6 sparse/singleton encoder range, alternating normal/fine input with both clamps, Off and exact emitted MIDI'),
 'M-PARAM-030':dict(run=lambda c:sparse_editor_domain(c,'NS0'),requirements=['PARAM-SLOTS','PARAM-OFF','LOCK-PARAM-SET'],description='Native NS0 sparse/singleton encoder range, alternating normal/fine input with both clamps, Off and exact emitted MIDI'),
 'M-PARAM-029':dict(run=lambda c:sparse_editor_domain(c,'SparseHigh'),requirements=['PARAM-SLOTS','PARAM-OFF','LOCK-PARAM-SET'],description='Native SparseHigh sparse/singleton encoder range, alternating normal/fine input with both clamps, Off and exact emitted MIDI'),
 'M-PARAM-028':dict(run=lambda c:sparse_editor_domain(c,'SparseLow'),requirements=['PARAM-SLOTS','PARAM-OFF','LOCK-PARAM-SET'],description='Native SparseLow sparse/singleton encoder range, alternating normal/fine input with both clamps, Off and exact emitted MIDI'),
 'M-REC-PARAM-021':dict(run=lambda c:recording_lifetime(c,'pending-configuration'),requirements=['REC-PARAM-AUTOMATION','PARAM-SLOTS','CH-DEVICE'],description='Keep pending-configuration unconfirmed across an eligible recording step, then cancel: original-route dirty MIDI and stored replay remain intact'),
 'M-REC-PARAM-020':dict(run=lambda c:recording_lifetime(c,'pending-assignment'),requirements=['REC-PARAM-AUTOMATION','PARAM-SLOTS','CH-DEVICE'],description='Keep pending-assignment unconfirmed across an eligible recording step, then cancel: original-route dirty MIDI and stored replay remain intact'),
 'M-PARAM-027':dict(run=lambda c:cc_encoder_domain(c,configured=False),requirements=['PARAM-SLOTS','PARAM-OFF','LOCK-PARAM-SET'],description='Every held-lock CC encoder detent emits exact MIDI0..127, upper clamp, Off and reentry; configured=False'),
 'M-PARAM-026':dict(run=lambda c:cc_encoder_domain(c,configured=True),requirements=['PARAM-SLOTS','PARAM-OFF','LOCK-PARAM-SET'],description='Every held-lock CC encoder detent emits exact MIDI0..127, upper clamp, Off and reentry; configured=True'),
 'M-REC-PARAM-019':dict(run=lambda c:recording_lifetime(c,'nonselected-wrap',scale_page=True),requirements=['REC-PARAM-AUTOMATION','CH-SELECT','NAV-PAGES'],description='Hold scale editor through global64-step wrap while recording; runtime remains live and paused MIDI automation resumes on return'),
 'M-REC-PARAM-018':dict(run=lambda c:recording_nrpn(c,-1),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'CH-DEVICE', 'PARAM-OFF'],description='Record NRPN -1 on port2/channel2 with exact standard bytes, timing, distinct-default replay and unchanged clean-slot CC lock'),
 'M-REC-PARAM-017':dict(run=lambda c:recording_nrpn(c,0),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'CH-DEVICE', 'PARAM-OFF'],description='Record NRPN 0 on port2/channel2 with exact standard bytes, timing, distinct-default replay and unchanged clean-slot CC lock'),
 'M-REC-PARAM-016':dict(run=lambda c:recording_nrpn(c,253),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'CH-DEVICE', 'PARAM-OFF'],description='Record NRPN 253 on port2/channel2 with exact standard bytes, timing, distinct-default replay and unchanged clean-slot CC lock'),
 'M-REC-PARAM-015':dict(run=lambda c:recording_lifetime(c,'slide-off'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'SLIDE-GLOBAL', 'PARAM-OFF'],description='Recording Off preserves a running slide to its endpoint while storing silent future locks'),
 'M-REC-PARAM-014':dict(run=lambda c:recording_lifetime(c,'slide-active'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'SLIDE-GLOBAL'],description='An active recorded value cancels the old slot slide silently at the next eligible step'),
 'M-REC-PARAM-013':dict(run=lambda c:recording_lifetime(c,'configuration'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'CH-DEVICE'],description='Changing MIDI channel and port resets defaults, device locks and assignments; reassigning before wrap cannot revive stale recording'),
 'M-REC-PARAM-012':dict(run=lambda c:recording_lifetime(c,'same-assignment'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS'],description='Confirming the same CC assignment preserves pending automation'),
 'M-REC-PARAM-011':dict(run=lambda c:recording_lifetime(c,'reassign'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS'],description='Changing CC assignment clears pending slot automation; existing locks follow new assignment without dirty-value leakage'),
 'M-REC-PARAM-010':dict(run=lambda c:recording_lifetime(c,'stop'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'NAV-TRANSPORT'],description='Grid Stop clears pending automation while arm remains enabled; restart preserves previously recorded steps'),
 'M-REC-PARAM-009':dict(run=lambda c:recording_lifetime(c,'disarm'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'REC-ARM'],description='Disarm and immediate rearm retire pending automation without rewriting untouched future steps'),
 'M-REC-PARAM-008':dict(run=lambda c:recording_lifetime(c,'nonselected-wrap'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'CH-SELECT'],description='Nonselected channel wrap preserves paused automation for resumption on a later eligible step'),
 'M-REC-PARAM-007':dict(run=lambda c:recording_lifetime(c,'selected-wrap'),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS', 'REC-ARM'],description='Selected channel wrap clears retained automation before its start lock sounds'),
 'M-REC-PARAM-006':dict(run=lambda c:live_parameter_recording(c,edit_value=-1),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS'],description='Recorded Off suppresses conflicting locks through the cycle and remains silent during distinct-default disarmed replay'),
 'M-REC-PARAM-005':dict(run=lambda c:live_parameter_recording(c,edit_value=0),requirements=['REC-PARAM-AUTOMATION', 'PARAM-SLOTS'],description='Recorded zero is active MIDI, replacing a conflicting lock and surviving distinct-default disarmed replay'),
 'M-REC-PARAM-004':dict(run=lambda c:live_parameter_recording(c,switch_return=True,scale_page=True),requirements=['REC-PARAM-AUTOMATION', 'CH-SELECT', 'NAV-PAGES'],description='Scale-page selection pauses channel recording; returning restores retained MIDI before note with unchanged paused locks'),
 'M-REC-PARAM-003':dict(run=lambda c:live_parameter_recording(c,empty_step=True),requirements=['REC-PARAM-AUTOMATION','OPT-TRIGLESS','PARAM-SLOTS'],description='Live CC recording crosses an empty trigless step; exact MIDI automation survives disarmed replay independently of changed patch default, with absent note and four-second deadlines'),
 'M-REC-PARAM-002':dict(run=lambda c:live_parameter_recording(c,switch_return=True),requirements=['REC-PARAM-AUTOMATION','CH-SELECT','PARAM-SLOTS'],description='Switch away during live parameter recording, hear old locks, return before step4; live value must match its stored disarmed replay while paused steps remain unchanged'),
 'M-REC-PARAM-001':dict(run=live_parameter_recording,requirements=['REC-PARAM-AUTOMATION','PARAM-SLOTS','CH-PATCH-SENTINEL'],description='Live encoder recording holds the edited CC value against old locks, records future steps, and replays exact locks before notes after disarming'),
 'M-PARAM-022':dict(run=lambda c:probability_midi_locks(c,trigless=True,nrpn=False),requirements=['OPT-TRIGLESS','PARAM-PROBABILITY','PARAM-SLOTS','CH-PATCH-SENTINEL'],description='Probability-rejected active trigs versus removed trigs with trigless=True, NRPN=False; exact lock bytes/timing and step100 lock-before-note'),
 'M-PARAM-023':dict(run=lambda c:probability_midi_locks(c,trigless=False,nrpn=False),requirements=['OPT-TRIGLESS','PARAM-PROBABILITY','PARAM-SLOTS','CH-PATCH-SENTINEL'],description='Probability-rejected active trigs versus removed trigs with trigless=False, NRPN=False; exact lock bytes/timing and step100 lock-before-note'),
 'M-PARAM-024':dict(run=lambda c:probability_midi_locks(c,trigless=True,nrpn=True),requirements=['OPT-TRIGLESS','PARAM-PROBABILITY','PARAM-SLOTS','CH-PATCH-SENTINEL'],description='Probability-rejected active trigs versus removed trigs with trigless=True, NRPN=True; exact lock bytes/timing and step100 lock-before-note'),
 'M-PARAM-025':dict(run=lambda c:probability_midi_locks(c,trigless=False,nrpn=True),requirements=['OPT-TRIGLESS','PARAM-PROBABILITY','PARAM-SLOTS','CH-PATCH-SENTINEL'],description='Probability-rejected active trigs versus removed trigs with trigless=False, NRPN=True; exact lock bytes/timing and step100 lock-before-note'),
 'M-PARAM-019':dict(run=lambda c:seeded_probability(c,probability=1,opportunities=320),requirements=['PARAM-PROBABILITY'],description='Seed42 probability1: independent native PRNG draws select exact note/velocity sequence aligned to a second MIDI channel through the rejected tail'),
 'M-PARAM-020':dict(run=lambda c:seeded_probability(c,probability=50,opportunities=208),requirements=['PARAM-PROBABILITY'],description='Seed42 probability50: independent native PRNG draws select exact note/velocity sequence aligned to a second MIDI channel through the rejected tail'),
 'M-PARAM-021':dict(run=lambda c:seeded_probability(c,probability=99,opportunities=64),requirements=['PARAM-PROBABILITY'],description='Seed42 probability99: independent native PRNG draws select exact note/velocity sequence aligned to a second MIDI channel through the rejected tail'),
 'M-PARAM-018':dict(run=probability_endpoint_locks,requirements=['PARAM-PROBABILITY','PARAM-SLOTS','PARAM-FIXED'],description='Probability0/100 and upper clamp with fixed pitch, per-step overrides, first/wrap rejected steps, clear restoration, exact sparse onsets and balanced releases'),
 'M-PARAM-017':dict(run=competing_pitch_locks,requirements=['PARAM-SLOTS','PARAM-FIXED','PARAM-QUANTISED-FIXED'],description='Competing fixed/quantised channel defaults and independent held-step locks: precedence, simultaneous zero locks, Off fallback and step-scoped clearing'),
 'M-PARAM-015':dict(run=lambda c:stock_pitch_lock_inheritance(c,quantised=True),requirements=['PARAM-SLOTS','PARAM-QUANTISED-FIXED'],description='Stock pitch held-step locks: zero, Off inheritance, default edits, clear and re-entry preserve exact phrase, velocity, releases and timing'),
 'M-PARAM-016':dict(run=lambda c:stock_pitch_lock_inheritance(c,quantised=False),requirements=['PARAM-SLOTS','PARAM-FIXED'],description='Stock pitch held-step locks: zero, Off inheritance, default edits, clear and re-entry preserve exact phrase, velocity, releases and timing'),
 'M-PARAM-012':dict(run=lambda c:quantised_fixed_table(c,profile='major'),requirements=['PARAM-QUANTISED-FIXED'],description='Quantised absolute MIDI pitch: major literal tie/root/upper-bound outputs with exact velocities, releases and step timing'),
 'M-PARAM-013':dict(run=lambda c:quantised_fixed_table(c,profile='d-major'),requirements=['PARAM-QUANTISED-FIXED'],description='Quantised absolute MIDI pitch: d-major literal tie/root/upper-bound outputs with exact velocities, releases and step timing'),
 'M-PARAM-014':dict(run=lambda c:quantised_fixed_table(c,profile='a-harmonic-minor'),requirements=['PARAM-QUANTISED-FIXED'],description='Quantised absolute MIDI pitch: a-harmonic-minor literal tie/root/upper-bound outputs with exact velocities, releases and step timing'),
 'M-PARAM-004':dict(run=lambda c:fixed_note_domain(c,start=0),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes0..15 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PARAM-005':dict(run=lambda c:fixed_note_domain(c,start=16),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes16..31 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PARAM-006':dict(run=lambda c:fixed_note_domain(c,start=32),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes32..47 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PARAM-007':dict(run=lambda c:fixed_note_domain(c,start=48),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes48..63 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PARAM-008':dict(run=lambda c:fixed_note_domain(c,start=64),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes64..79 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PARAM-009':dict(run=lambda c:fixed_note_domain(c,start=80),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes80..95 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PARAM-010':dict(run=lambda c:fixed_note_domain(c,start=96),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes96..111 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PARAM-011':dict(run=lambda c:fixed_note_domain(c,start=112),requirements=['PARAM-FIXED','PARAM-SLOTS'],description='Fixed MIDI notes112..127 override quantised/random/pattern sources, preserve velocities/releases/timing and restore the source phrase'),
 'M-PATCH-060':dict(run=lambda c:patch_configured_off_lock(c,default_kind='CCdefault'),requirements=['PARAM-OFF','CH-PATCH-SENTINEL'],description='Omitted off_value defaults to silent-1 for a CC step lock'),
 'M-PATCH-061':dict(run=lambda c:patch_configured_off_lock(c,default_kind='NRPNdef'),requirements=['PARAM-OFF','CH-PATCH-SENTINEL'],description='Omitted off_value defaults to silent-1 for an NRPN step lock, without Lua failure'),
 'M-PATCH-062':dict(run=lambda c:patch_slide_timing(c,off_middle=True,default_off=True),requirements=['PARAM-OFF','SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='Default-Off CC middle step does not cancel or become a destination of the active slide'),
 'M-PATCH-063':dict(run=lambda c:patch_nrpn_slide(c,default_off=True),requirements=['PARAM-OFF','SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='Default-Off NRPN middle step preserves the rollover curve and exact musical destination'),
 'M-PATCH-059':dict(run=lambda c:patch_nrpn_restart(c,legacy=True,convert=True),requirements=['CH-PATCH-SENTINEL'],description='Explicit old-project conversion writes a new copy with identical numeric PSET, preserves source, refuses overwrite, and emits standard bytes across native cold loads/edit/Play'),
 'M-PATCH-057':dict(run=patch_configured_off_lock,requirements=['PARAM-OFF','CH-PATCH-SENTINEL'],description='Configured NRPN Off below active range stays silent when authored as a held-step lock'),
 'M-PATCH-058':dict(run=lambda c:patch_configured_off_lock(c,high=True),requirements=['PARAM-OFF','CH-PATCH-SENTINEL'],description='Configured CC Off above active range stays silent when authored as a held-step lock'),
 'M-PATCH-053':dict(run=lambda c:patch_nrpn_slide(c,legacy=False,descending=False),requirements=['SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='NRPN slow rollover slide legacy=False descending=False: exact routing, value curve, endpoint-before-note and no Off tail'),
 'M-PATCH-054':dict(run=lambda c:patch_nrpn_slide(c,legacy=False,descending=True),requirements=['SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='NRPN slow rollover slide legacy=False descending=True: exact routing, value curve, endpoint-before-note and no Off tail'),
 'M-PATCH-055':dict(run=lambda c:patch_nrpn_slide(c,legacy=True,descending=False),requirements=['SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='NRPN slow rollover slide legacy=True descending=False: exact routing, value curve, endpoint-before-note and no Off tail'),
 'M-PATCH-056':dict(run=lambda c:patch_nrpn_slide(c,legacy=True,descending=True),requirements=['SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='NRPN slow rollover slide legacy=True descending=True: exact routing, value curve, endpoint-before-note and no Off tail'),
 'M-PATCH-052':dict(run=patch_nrpn_boundary_matrix,requirements=['CH-PATCH-SENTINEL'],description='Native NRPN0/1/126/127/128/129/16383 in both explicit modes, parameter channel overrides, Off silence and A/B/A switching'),
 'M-PATCH-050':dict(run=patch_nrpn_restart,requirements=['CH-PATCH-SENTINEL'],description='Standard NRPN edits, two cold loads, autosave and Play recall preserve126 then253 with exact bytes and melody'),
 'M-PATCH-051':dict(run=lambda c:patch_nrpn_restart(c,legacy=True),requirements=['CH-PATCH-SENTINEL'],description='Pre-policy NRPN project migrates stored control to historical mode and preserves even/odd bytes across edits, Play and second cold load'),
 'M-PATCH-029':dict(run=lambda c:patch_slide_trigless(c,True),requirements=['SLIDE-GLOBAL','OPT-TRIGLESS'],description='Slide reaches silent locked destination with trigless enabled and preserves note rests'),
 'M-PATCH-048':dict(run=patch_sparse_slide,requirements=['SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='Sparse active100..127 CC slide with Off below range keeps exact musical curve and stored recall'),
 'M-PATCH-049':dict(run=lambda c:patch_sparse_slide(c,high=True),requirements=['SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='Sparse active100..127 CC slide with Off above range never emits sentinel or gap and preserves endpoint timing'),
 'M-PATCH-047':dict(run=lambda c:patch_ten_slot_slides(c,remove_middle=True),requirements=['SLIDE-GLOBAL','PARAM-SLOTS'],description='Remove middle assignment during ten active slides; selected CC stops immediately while nine independent curves and note timing continue'),
 'M-PATCH-046':dict(run=patch_ten_slot_slides,requirements=['SLIDE-GLOBAL','PARAM-SLOTS'],description='All ten native parameter slots slide concurrently with distinct CC identities and exact independent trajectories/endpoints'),
 'M-PATCH-045':dict(run=lambda c:patch_slide_live_destination(c,unassign=True),requirements=['SLIDE-GLOBAL','PARAM-SLOTS'],description='Selecting None during active slide immediately retires CC output while preserving complete note sequence and timing'),
 'M-PATCH-044':dict(run=patch_channel_clear_isolation,requirements=['LOCK-PARAM-CLEAR','LOCK-OCTAVE','PARAM-SLOTS'],description='Repeated clear on channel1 preserves channel2 MIDI/octave locks on distinct port/channel, exact note times and lock values'),
 'M-PATCH-043':dict(run=lambda c:patch_clear_mask_boundary(c,copy_isolation=True),requirements=['LOCK-PARAM-CLEAR','SONG-SLOTS','LOCK-OCTAVE'],description='Copied song pattern lock clear stays isolated across repeated slot switching; original locks and both length masks remain correct'),
 'M-PATCH-042':dict(run=lambda c:patch_clear_mask_boundary(c,inverse=True,single=True),requirements=['LOCK-MASK','LOCK-CLEAR-PAGE','LOCK-OCTAVE'],description='Held-step K2 on Masks clears only step2 length mask while preserving other steps, octave and MIDI locks'),
 'M-PATCH-041':dict(run=lambda c:patch_clear_mask_boundary(c,inverse=True),requirements=['LOCK-MASK','LOCK-CLEAR-PAGE','LOCK-OCTAVE','LOCK-PARAM-CLEAR'],description='Mask-page channel clear removes held-step length masks while preserving MIDI parameter and octave locks with exact durations'),
 'M-PATCH-040':dict(run=patch_clear_mask_boundary,requirements=['LOCK-PARAM-CLEAR','LOCK-CLEAR-PAGE','LOCK-OCTAVE'],description='Channel lock clear removes parameter and octave locks while preserving the independent length mask and musical note timing'),
 'M-PATCH-039':dict(run=lambda c:patch_slide_live_destination(c,clear_all=True),requirements=['SLIDE-GLOBAL','LOCK-PARAM-CLEAR'],description='Live K1+K2 clears source and destination channel locks; subsequent cycles recall stored value at each unchanged note'),
 'M-PATCH-038':dict(run=lambda c:patch_slide_live_destination(c,reassign=True),requirements=['SLIDE-GLOBAL','PARAM-SLOTS'],description='Live CC1-to-CC2 reassignment sends new parameter destination despite old slide ownership and preserves next-cycle locks/timing'),
 'M-PATCH-037':dict(run=lambda c:patch_slide_live_destination(c,clear=True),requirements=['SLIDE-GLOBAL','LOCK-PARAM-CLEAR'],description='Held-step K2 clears live destination without disturbing source or notes; next cycle recalls stored patch without stale lock or slide'),
 'M-PATCH-036':dict(run=lambda c:patch_slide_live_destination(c,off=True),requirements=['PARAM-OFF','SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='Live Off destination preserves the captured slide to completion without sentinel emission and excludes it from subsequent cycles'),
 'M-PATCH-035':dict(run=patch_slide_live_destination,requirements=['SLIDE-GLOBAL','LOCK-PARAM-SET'],description='Editing destination during active slide applies new endpoint before its note and next cycle uses the new trajectory without stale tail'),
 'M-PATCH-034':dict(run=lambda c:patch_slide_timing(c,step_local=True,global_roundtrip=True),requirements=['SLIDE-STEP','SLIDE-GLOBAL'],description='Global slides enable later locks then switch off while preserving an existing local slide and its exact timing'),
 'M-PATCH-033':dict(run=lambda c:patch_slide_timing(c,step_local=True),requirements=['SLIDE-STEP'],description='Held-step K3 slides only source lock with exact trajectory and endpoint; later lock jumps directly without unwanted global interpolation'),
 'M-PATCH-032':dict(run=lambda c:patch_slide_live_division(c,repeated_edits=True),requirements=['SLIDE-GLOBAL','CH-TEMPO'],description='Repeated confirmed queued rate edits preserve pre-boundary timing and retime active slide continuously to final rate'),
 'M-PATCH-031':dict(run=lambda c:patch_slide_timing(c,stop_restarts=3),requirements=['SLIDE-GLOBAL','NAV-TRANSPORT'],description='Three active-slide stop/restarts leave no stale MIDI or outstanding notes and retain exact restarted slide timing'),
 'M-PATCH-030':dict(run=lambda c:patch_slide_trigless(c,False),requirements=['SLIDE-GLOBAL','OPT-TRIGLESS'],description='Disabled trigless excludes silent lock from slide destination and parameter emission'),
 'M-PATCH-028':dict(run=lambda c:patch_slide_timing(c,off_middle=True),requirements=['PARAM-OFF','SLIDE-GLOBAL','CH-PATCH-SENTINEL'],description='Explicit Off lock between active slide endpoints emits no sentinel/stored value and does not cancel or distort the MIDI trajectory'),
 'M-PATCH-027':dict(run=patch_slide_song_cutoff,requirements=['SLIDE-GLOBAL','SONG-ADVANCE','SONG-SLOTS'],description='Actual song transition without reset retires old active CC slide at global boundary; new octave fingerprint, phase and explicit lock remain correct'),
 'M-PATCH-026':dict(run=lambda c:patch_slide_live_division(c,reset=True),requirements=['SLIDE-GLOBAL','OPT-SLIDE-WRAP','CH-TEMPO','SONG-ADVANCE'],description='Same-pattern reset during queued rate edit preserves wrapped slide through unowned first step and retargets the actual third-step endpoint'),
 'M-PATCH-025':dict(run=lambda c:patch_slide_live_division(c,type_switch=True),requirements=['SLIDE-GLOBAL','CH-SWING'],description='Queued Swing-to-Heavy6 change crosses active /3 slide; exact global-boundary retiming, continuous CC and framebuffer readback'),
 'M-PATCH-024':dict(run=patch_slide_live_division,requirements=['SLIDE-GLOBAL','CH-TEMPO'],description='Queued /3-to-/6 edit applies at global pattern boundary during a slide; preserves continuous CC and independently retimed destination'),
 'M-PATCH-023':dict(run=lambda c:patch_slide_timing(c,wrap=True,shuffle=True),requirements=['SLIDE-GLOBAL','OPT-SLIDE-WRAP','CH-SWING'],description='Heavy basis6 full shuffle: independent16/16/16/48pulse onsets, one-gap outgoing slide and three-gap wrapped return'),
 'M-PATCH-021':dict(run=lambda c:patch_slide_timing(c,wrap=True,swing=50),requirements=['SLIDE-GLOBAL','OPT-SLIDE-WRAP','CH-SWING'],description='Positive50 swing CC slide over one gap and wrapped return over three gaps; independent36/12pulse onsets and endpoint ordering'),
 'M-PATCH-022':dict(run=lambda c:patch_slide_timing(c,wrap=True,swing=-50),requirements=['SLIDE-GLOBAL','OPT-SLIDE-WRAP','CH-SWING'],description='Negative50 swing CC slide over one short gap and wrapped return over three gaps; independent12/36pulse onsets and endpoint ordering'),
 'M-PATCH-020':dict(run=lambda c:patch_slide_timing(c,wrap=True,fractional=True),requirements=['SLIDE-GLOBAL','CH-TEMPO'],description='Fractional x5.3 native CC slides and wrapped endpoints follow independently rounded musical onsets'),
 'M-PATCH-019':dict(run=lambda c:patch_slide_timing(c,target=25),requirements=['SLIDE-GLOBAL','CH-PATCH-RECALL'],description='One-unit24to25 slide reaches rounded target early yet applies one explicit destination lock before its note, with no stale tail'),
 'M-XA-004-JF-OVERLAP':dict(run=jf_same_voice_overlap,requirements=['CH-DEVICE','MIDI-RELEASE-001','REC-LIVE-NOTES'],expansion_families=['XA-006','XA-008','XA-013'],description='All six mono JF voices: two sources hold same pitch on one player; both release orders, no premature gate-off, one final release, selection moved to channel16'),
 'M-XA-003-JF-OWNERSHIP':dict(run=jf_keyboard_ownership,requirements=['CH-DEVICE','MIDI-RELEASE-001','REC-LIVE-NOTES'],expansion_families=['XA-004','XA-006','XA-008','XA-013'],description='All six compatible JF mono voices paired on Mosaic channels1/16; same pitch from separate ports/input channels, both release orders, channel8 selected during release, no MIDI leakage'),
 'M-XA-002-AUDIO':dict(run=doubledecker_audition,requirements=['CH-DEVICE','SETUP-DEVICE-DISCOVERY'],expansion_families=['XA-001','XA-005','XA-013'],description='Native keyboard audition through visible Doubledecker selection; measured stereo C4/E4/G4 sustain, bounded release silence, no MIDI note leakage'),
 'M-XA-001-JF':dict(run=jf_mono_phrase,requirements=['CH-DEVICE','SETUP-DEVICE-DISCOVERY'],expansion_families=['XA-001','XA-005','XA-008'],description='Current Mosaic selects visible JF mono voice1, plays exactly two phrases, emits independently decoded pitches/velocity ordering/releases with no MIDI note leakage'),
 'M-PATCH-004':dict(run=patch_cc_matrix,requirements=['CH-PATCH-SENTINEL'],description='All127configured generic CC controls: sentinel, every declared boundary/interior value and saturation, exact MIDI and screen output'),

 'M-PATCH-001':dict(run=lambda c:patch_boundaries(c,False),requirements=['CH-PATCH-SENTINEL'],description='Generic CC stored parameter sentinel, boundary values and clamped edits via native params menu'),
 'M-PATCH-002':dict(run=lambda c:patch_boundaries(c,True),requirements=['CH-PATCH-SENTINEL'],description='Configured CC device supports documented minus-one sentinel and numeric boundary edits'),
 'M-PATCH-018':dict(run=lambda c:patch_slide_timing(c,True),requirements=['SLIDE-GLOBAL','OPT-SLIDE-WRAP','CH-RANGE'],description='Native Wrap param slides option:24to96 and96to24 span two musical steps inside active range1..4 across two loops, exact interpolated CCs and pre-note endpoints'),
 'M-PATCH-017':dict(run=patch_slide_timing,requirements=['SLIDE-GLOBAL','CH-PATCH-RECALL'],description='Two-step24to96 slide follows musical elapsed time across two loops, reaches destination before note and cannot send stale values afterward'),
 'M-PATCH-015':dict(run=patch_adjacent_locks,requirements=['CH-PATCH-RECALL'],description='Four adjacent distinct locks match their own note through three wraps; stored value unchanged and exact90BPM onset schedule'),
 'M-PATCH-016':dict(run=lambda c:patch_adjacent_locks(c,2),requirements=['CH-PATCH-RECALL','CH-RANGE'],description='Range2..4 starts with its own lock rather than step1 and wraps with distinct lock values before each musical onset'),
 'M-PATCH-013':dict(run=lambda c:patch_lock_precedence(c,63),requirements=['CH-PATCH-RECALL'],description='Equal stored and step-lock values preserve explicit recall and lock messages; verify full phrase ordering and stored value'),
 'M-PATCH-014':dict(run=lambda c:patch_lock_precedence(c,-1),requirements=['CH-PATCH-RECALL','CH-PATCH-SENTINEL'],description='First-step Off sends no lock CC and does not undo stored-patch recall; full phrases and menu readback'),
 'M-PATCH-012':dict(run=patch_lock_precedence,requirements=['CH-PATCH-RECALL'],description='Stored CC63 is recalled before first-step CC99 lock and note, while native menu readback retains stored63'),
 'M-PATCH-010':dict(run=patch_sparse_range,requirements=['CH-PATCH-SENTINEL'],description='All28 valid CC values100..127 with off-minus-one, no exposed/transmitted gap values, saturation and screen checks'),
 'M-PATCH-011':dict(run=lambda c:patch_sparse_range(c,True),requirements=['CH-PATCH-SENTINEL'],description='All28 valid CC values100..127 with custom Off200 above range, no gap values or Off MIDI transmission'),
 'M-PATCH-008':dict(run=patch_restart,requirements=['CH-PATCH-RECALL'],description='Store CC via native menu, actual autosave and fresh-process load; assert restored display, startup MIDI, Play recall and melody'),
 'M-PATCH-009':dict(run=lambda c:patch_restart(c,True),requirements=['CH-PATCH-RECALL','CH-PATCH-SENTINEL'],description='Persist an edited parameter returned to Off; cold load and Play preserve Off without unwanted CC'),
 'M-PATCH-007':dict(run=patch_nrpn_bytes,requirements=['CH-PATCH-SENTINEL'],description='Configured NRPN control sends independent address and 14-bit data bytes through native menu input'),
 'M-PATCH-006':dict(run=patch_muted_recall,requirements=['CH-PATCH-RECALL'],description='Muted channel recalls stored patch on Play while grid feedback and full MIDI trace prove note silence'),
 'M-PATCH-005':dict(run=lambda c:patch_play_recall(c,3),requirements=['CH-PATCH-RECALL'],description='Three actual grid Play/Stop cycles each recall exactly one stored unassigned CC before their first note'),
 'M-PATCH-003':dict(run=patch_play_recall,requirements=['CH-PATCH-RECALL'],description='Play recalls a stored CC that is not assigned to a trig-lock slot before the first note'),

 'M-PANIC-011':dict(run=lambda c:panic_hotplug(c,True,False),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Native MIDI removal before panic; reconnect after sweep; restored keyboard, fresh panic and melody'),
 'M-PANIC-012':dict(run=lambda c:panic_hotplug(c,True,True),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Native MIDI removal before panic; reconnect during sweep; restored keyboard, fresh panic and melody'),
 'M-PANIC-013':dict(run=lambda c:panic_hotplug(c,False,False),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Native MIDI removal during panic; reconnect after sweep; restored keyboard, fresh panic and melody'),
 'M-PANIC-014':dict(run=lambda c:panic_hotplug(c,False,True),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Native MIDI removal during panic; reconnect during sweep; restored keyboard, fresh panic and melody'),

 'M-PANIC-007':dict(run=lambda c:panic_pending_chord(c,False,1),requirements=['PANIC-GESTURE','CHORD-STRUM'],description='Panic sweep during active and pending chord voices; complete MIDI accounting and input-origin musical timing'),
 'M-PANIC-008':dict(run=lambda c:panic_pending_chord(c,False,2),requirements=['PANIC-GESTURE','CHORD-STRUM'],description='Panic sweep during active and pending chord voices; complete MIDI accounting and input-origin musical timing'),
 'M-PANIC-009':dict(run=lambda c:panic_pending_chord(c,True,1),requirements=['PANIC-GESTURE','CHORD-ARP'],description='Panic sweep during active and pending chord voices; complete MIDI accounting and input-origin musical timing'),
 'M-PANIC-010':dict(run=lambda c:panic_pending_chord(c,True,2),requirements=['PANIC-GESTURE','CHORD-ARP'],description='Panic sweep during active and pending chord voices; complete MIDI accounting and input-origin musical timing'),
 'M-PANIC-005':dict(run=lambda c:panic_overlapping_holds(c,2),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Two overlapping long holds restart all port sweeps mid-job, preserve page and melody'),
 'M-PANIC-006':dict(run=lambda c:panic_overlapping_holds(c,3),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Three overlapping long holds restart all port sweeps twice mid-job, preserve page and melody'),
 'M-PANIC-004':dict(run=panic_live_note_stop,requirements=['PANIC-GESTURE'],description='Keyboard note played behind an in-flight panic sweep remains owned by Stop; exact full MIDI trace'),
 'M-PANIC-003':dict(run=panic_hold_matrix,requirements=['PANIC-GESTURE','NAV-PAGES'],description='All24selected-page/held-menu combinations, repeated completed holds, selected-button silence and unchanged melody'),
 'M-PANIC-001':dict(run=lambda c:panic_navigation(c,3),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Hold non-selected channel navigation: all notes/channels/ports off and no navigation'),
 'M-PANIC-002':dict(run=lambda c:panic_navigation(c,5),requirements=['PANIC-GESTURE','NAV-PAGES'],description='Hold non-selected pattern navigation: complete per-port panic output and no navigation'),
 'M-NAV-001':dict(run=navigation_matrix,requirements=['NAV-PAGES'],description='All36page transitions, repeated pattern cycles, exact menu LEDs and unchanged MIDI after each transition'),
 'M-DASHBOARD-005':dict(run=lambda c:chord_shape_schedule(c,False,2,False,velocity=100,modifier=10,dashboard=True),requirements=['CH-DASHBOARD','CHORD-VELOCITY'],description='Rendered root pitch, clamped velocity boundary and length after exact native MIDI checks'),
 'M-DASHBOARD-006':dict(run=lambda c:chord_shape_schedule(c,False,2,False,velocity=20,modifier=-10,dashboard=True),requirements=['CH-DASHBOARD','CHORD-VELOCITY'],description='Rendered root pitch, clamped velocity boundary and length after exact native MIDI checks'),
 'M-DASHBOARD-007':dict(run=lambda c:chord_shape_schedule(c,False,4,False,velocity=100,modifier=10,dashboard=True),requirements=['CH-DASHBOARD','CHORD-VELOCITY'],description='Rendered root pitch, clamped velocity boundary and length after exact native MIDI checks'),
 'M-DASHBOARD-008':dict(run=lambda c:chord_shape_schedule(c,False,4,False,velocity=20,modifier=-10,dashboard=True),requirements=['CH-DASHBOARD','CHORD-VELOCITY'],description='Rendered root pitch, clamped velocity boundary and length after exact native MIDI checks'),
 'M-DASHBOARD-001':dict(run=lambda c:chord_shape_schedule(c,False,1,False,dashboard=True),requirements=['CH-DASHBOARD','CHORD-SHAPE'],description='Root pitch and velocity rendered after strum shape1; exact MIDI remains asserted'),
 'M-DASHBOARD-002':dict(run=lambda c:chord_shape_schedule(c,False,2,False,dashboard=True),requirements=['CH-DASHBOARD','CHORD-SHAPE'],description='Root pitch and velocity rendered after strum shape2; exact MIDI remains asserted'),
 'M-DASHBOARD-003':dict(run=lambda c:chord_shape_schedule(c,False,3,False,dashboard=True),requirements=['CH-DASHBOARD','CHORD-SHAPE'],description='Root pitch and velocity rendered after strum shape3; exact MIDI remains asserted'),
 'M-DASHBOARD-004':dict(run=lambda c:chord_shape_schedule(c,False,4,False,dashboard=True),requirements=['CH-DASHBOARD','CHORD-SHAPE'],description='Root pitch and velocity rendered after strum shape4; exact MIDI remains asserted'),
 'M-CHORDSHAPE-259':dict(run=lambda c:chord_shape_schedule(c,False,2,False,15,extra='early-stop'),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY'],description="Sparse reverse articulation boundary: negative termination, disabled strum or Stop before pending root"),
 'M-CHORDSHAPE-258':dict(run=lambda c:chord_shape_schedule(c,False,2,False,9,extra='disabled'),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY'],description="Sparse reverse articulation boundary: negative termination, disabled strum or Stop before pending root"),
 'M-CHORDSHAPE-257':dict(run=lambda c:chord_shape_schedule(c,False,2,False,9,extra='accelerating'),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-SPREAD', 'CHORD-ACCEL'],description="Sparse reverse articulation boundary: negative termination, disabled strum or Stop before pending root"),
 'M-CHORDVEL-004':dict(run=lambda c:chord_shape_schedule(c,False,4,False,15,velocity=20,modifier=-10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY'],description="Reverse-root velocity clamps to MIDI bounds, including explicit zero messages and complete Stop drain"),
 'M-CHORDVEL-003':dict(run=lambda c:chord_shape_schedule(c,False,4,False,15,velocity=100,modifier=10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY'],description="Reverse-root velocity clamps to MIDI bounds, including explicit zero messages and complete Stop drain"),
 'M-CHORDVEL-002':dict(run=lambda c:chord_shape_schedule(c,False,2,False,15,velocity=20,modifier=-10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY'],description="Reverse-root velocity clamps to MIDI bounds, including explicit zero messages and complete Stop drain"),
 'M-CHORDVEL-001':dict(run=lambda c:chord_shape_schedule(c,False,2,False,15,velocity=100,modifier=10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY'],description="Reverse-root velocity clamps to MIDI bounds, including explicit zero messages and complete Stop drain"),
 'M-CHORDSHAPE-256':dict(run=lambda c:chord_shape_schedule(c,True,4,True,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-255':dict(run=lambda c:chord_shape_schedule(c,True,4,True,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-254':dict(run=lambda c:chord_shape_schedule(c,True,4,True,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-253':dict(run=lambda c:chord_shape_schedule(c,True,4,True,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-252':dict(run=lambda c:chord_shape_schedule(c,True,4,True,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-251':dict(run=lambda c:chord_shape_schedule(c,True,4,True,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-250':dict(run=lambda c:chord_shape_schedule(c,True,4,True,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-249':dict(run=lambda c:chord_shape_schedule(c,True,4,True,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-248':dict(run=lambda c:chord_shape_schedule(c,True,4,True,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-247':dict(run=lambda c:chord_shape_schedule(c,True,4,True,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-246':dict(run=lambda c:chord_shape_schedule(c,True,4,True,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-245':dict(run=lambda c:chord_shape_schedule(c,True,4,True,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-244':dict(run=lambda c:chord_shape_schedule(c,True,4,True,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-243':dict(run=lambda c:chord_shape_schedule(c,True,4,True,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-242':dict(run=lambda c:chord_shape_schedule(c,True,4,True,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-241':dict(run=lambda c:chord_shape_schedule(c,True,4,False,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-240':dict(run=lambda c:chord_shape_schedule(c,True,4,False,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-239':dict(run=lambda c:chord_shape_schedule(c,True,4,False,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-238':dict(run=lambda c:chord_shape_schedule(c,True,4,False,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-237':dict(run=lambda c:chord_shape_schedule(c,True,4,False,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-236':dict(run=lambda c:chord_shape_schedule(c,True,4,False,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-235':dict(run=lambda c:chord_shape_schedule(c,True,4,False,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-234':dict(run=lambda c:chord_shape_schedule(c,True,4,False,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-233':dict(run=lambda c:chord_shape_schedule(c,True,4,False,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-232':dict(run=lambda c:chord_shape_schedule(c,True,4,False,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-231':dict(run=lambda c:chord_shape_schedule(c,True,4,False,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-230':dict(run=lambda c:chord_shape_schedule(c,True,4,False,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-229':dict(run=lambda c:chord_shape_schedule(c,True,4,False,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-228':dict(run=lambda c:chord_shape_schedule(c,True,4,False,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-227':dict(run=lambda c:chord_shape_schedule(c,True,4,False,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-226':dict(run=lambda c:chord_shape_schedule(c,True,3,True,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-225':dict(run=lambda c:chord_shape_schedule(c,True,3,True,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-224':dict(run=lambda c:chord_shape_schedule(c,True,3,True,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-223':dict(run=lambda c:chord_shape_schedule(c,True,3,True,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-222':dict(run=lambda c:chord_shape_schedule(c,True,3,True,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-221':dict(run=lambda c:chord_shape_schedule(c,True,3,True,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-220':dict(run=lambda c:chord_shape_schedule(c,True,3,True,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-219':dict(run=lambda c:chord_shape_schedule(c,True,3,True,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-218':dict(run=lambda c:chord_shape_schedule(c,True,3,True,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-217':dict(run=lambda c:chord_shape_schedule(c,True,3,True,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-216':dict(run=lambda c:chord_shape_schedule(c,True,3,True,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-215':dict(run=lambda c:chord_shape_schedule(c,True,3,True,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-214':dict(run=lambda c:chord_shape_schedule(c,True,3,True,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-213':dict(run=lambda c:chord_shape_schedule(c,True,3,True,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-212':dict(run=lambda c:chord_shape_schedule(c,True,3,True,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-211':dict(run=lambda c:chord_shape_schedule(c,True,3,False,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-210':dict(run=lambda c:chord_shape_schedule(c,True,3,False,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-209':dict(run=lambda c:chord_shape_schedule(c,True,3,False,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-208':dict(run=lambda c:chord_shape_schedule(c,True,3,False,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-207':dict(run=lambda c:chord_shape_schedule(c,True,3,False,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-206':dict(run=lambda c:chord_shape_schedule(c,True,3,False,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-205':dict(run=lambda c:chord_shape_schedule(c,True,3,False,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-204':dict(run=lambda c:chord_shape_schedule(c,True,3,False,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-203':dict(run=lambda c:chord_shape_schedule(c,True,3,False,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-202':dict(run=lambda c:chord_shape_schedule(c,True,3,False,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-201':dict(run=lambda c:chord_shape_schedule(c,True,3,False,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-200':dict(run=lambda c:chord_shape_schedule(c,True,3,False,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-199':dict(run=lambda c:chord_shape_schedule(c,True,3,False,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-198':dict(run=lambda c:chord_shape_schedule(c,True,3,False,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-197':dict(run=lambda c:chord_shape_schedule(c,True,3,False,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-196':dict(run=lambda c:chord_shape_schedule(c,True,2,True,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-195':dict(run=lambda c:chord_shape_schedule(c,True,2,True,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-194':dict(run=lambda c:chord_shape_schedule(c,True,2,True,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-193':dict(run=lambda c:chord_shape_schedule(c,True,2,True,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-192':dict(run=lambda c:chord_shape_schedule(c,True,2,True,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-191':dict(run=lambda c:chord_shape_schedule(c,True,2,True,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-190':dict(run=lambda c:chord_shape_schedule(c,True,2,True,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-189':dict(run=lambda c:chord_shape_schedule(c,True,2,True,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-188':dict(run=lambda c:chord_shape_schedule(c,True,2,True,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-187':dict(run=lambda c:chord_shape_schedule(c,True,2,True,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-186':dict(run=lambda c:chord_shape_schedule(c,True,2,True,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-185':dict(run=lambda c:chord_shape_schedule(c,True,2,True,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-184':dict(run=lambda c:chord_shape_schedule(c,True,2,True,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-183':dict(run=lambda c:chord_shape_schedule(c,True,2,True,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-182':dict(run=lambda c:chord_shape_schedule(c,True,2,True,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-181':dict(run=lambda c:chord_shape_schedule(c,True,2,False,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-180':dict(run=lambda c:chord_shape_schedule(c,True,2,False,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-179':dict(run=lambda c:chord_shape_schedule(c,True,2,False,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-178':dict(run=lambda c:chord_shape_schedule(c,True,2,False,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-177':dict(run=lambda c:chord_shape_schedule(c,True,2,False,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-176':dict(run=lambda c:chord_shape_schedule(c,True,2,False,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-175':dict(run=lambda c:chord_shape_schedule(c,True,2,False,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-174':dict(run=lambda c:chord_shape_schedule(c,True,2,False,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-173':dict(run=lambda c:chord_shape_schedule(c,True,2,False,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-172':dict(run=lambda c:chord_shape_schedule(c,True,2,False,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-171':dict(run=lambda c:chord_shape_schedule(c,True,2,False,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-170':dict(run=lambda c:chord_shape_schedule(c,True,2,False,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-169':dict(run=lambda c:chord_shape_schedule(c,True,2,False,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-168':dict(run=lambda c:chord_shape_schedule(c,True,2,False,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-167':dict(run=lambda c:chord_shape_schedule(c,True,2,False,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-166':dict(run=lambda c:chord_shape_schedule(c,True,1,True,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-165':dict(run=lambda c:chord_shape_schedule(c,True,1,True,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-164':dict(run=lambda c:chord_shape_schedule(c,True,1,True,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-163':dict(run=lambda c:chord_shape_schedule(c,True,1,True,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-162':dict(run=lambda c:chord_shape_schedule(c,True,1,True,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-161':dict(run=lambda c:chord_shape_schedule(c,True,1,True,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-160':dict(run=lambda c:chord_shape_schedule(c,True,1,True,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-159':dict(run=lambda c:chord_shape_schedule(c,True,1,True,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-158':dict(run=lambda c:chord_shape_schedule(c,True,1,True,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-157':dict(run=lambda c:chord_shape_schedule(c,True,1,True,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-156':dict(run=lambda c:chord_shape_schedule(c,True,1,True,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-155':dict(run=lambda c:chord_shape_schedule(c,True,1,True,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-154':dict(run=lambda c:chord_shape_schedule(c,True,1,True,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-153':dict(run=lambda c:chord_shape_schedule(c,True,1,True,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-152':dict(run=lambda c:chord_shape_schedule(c,True,1,True,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-151':dict(run=lambda c:chord_shape_schedule(c,True,1,False,14),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-150':dict(run=lambda c:chord_shape_schedule(c,True,1,False,13),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-149':dict(run=lambda c:chord_shape_schedule(c,True,1,False,12),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-148':dict(run=lambda c:chord_shape_schedule(c,True,1,False,11),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-147':dict(run=lambda c:chord_shape_schedule(c,True,1,False,10),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-146':dict(run=lambda c:chord_shape_schedule(c,True,1,False,9),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-145':dict(run=lambda c:chord_shape_schedule(c,True,1,False,8),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-144':dict(run=lambda c:chord_shape_schedule(c,True,1,False,7),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-143':dict(run=lambda c:chord_shape_schedule(c,True,1,False,6),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-142':dict(run=lambda c:chord_shape_schedule(c,True,1,False,5),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-141':dict(run=lambda c:chord_shape_schedule(c,True,1,False,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-140':dict(run=lambda c:chord_shape_schedule(c,True,1,False,3),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-139':dict(run=lambda c:chord_shape_schedule(c,True,1,False,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-138':dict(run=lambda c:chord_shape_schedule(c,True,1,False,1),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-137':dict(run=lambda c:chord_shape_schedule(c,True,1,False,0),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-136':dict(run=lambda c:chord_shape_schedule(c,False,4,True,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-135':dict(run=lambda c:chord_shape_schedule(c,False,4,True,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-134':dict(run=lambda c:chord_shape_schedule(c,False,4,True,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-133':dict(run=lambda c:chord_shape_schedule(c,False,4,True,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-132':dict(run=lambda c:chord_shape_schedule(c,False,4,True,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-131':dict(run=lambda c:chord_shape_schedule(c,False,4,True,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-130':dict(run=lambda c:chord_shape_schedule(c,False,4,True,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-129':dict(run=lambda c:chord_shape_schedule(c,False,4,True,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-128':dict(run=lambda c:chord_shape_schedule(c,False,4,True,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-127':dict(run=lambda c:chord_shape_schedule(c,False,4,True,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-126':dict(run=lambda c:chord_shape_schedule(c,False,4,True,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-125':dict(run=lambda c:chord_shape_schedule(c,False,4,True,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-124':dict(run=lambda c:chord_shape_schedule(c,False,4,True,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-123':dict(run=lambda c:chord_shape_schedule(c,False,4,True,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-122':dict(run=lambda c:chord_shape_schedule(c,False,4,True,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-121':dict(run=lambda c:chord_shape_schedule(c,False,4,False,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-120':dict(run=lambda c:chord_shape_schedule(c,False,4,False,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-119':dict(run=lambda c:chord_shape_schedule(c,False,4,False,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-118':dict(run=lambda c:chord_shape_schedule(c,False,4,False,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-117':dict(run=lambda c:chord_shape_schedule(c,False,4,False,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-116':dict(run=lambda c:chord_shape_schedule(c,False,4,False,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-115':dict(run=lambda c:chord_shape_schedule(c,False,4,False,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-114':dict(run=lambda c:chord_shape_schedule(c,False,4,False,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-113':dict(run=lambda c:chord_shape_schedule(c,False,4,False,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-112':dict(run=lambda c:chord_shape_schedule(c,False,4,False,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-111':dict(run=lambda c:chord_shape_schedule(c,False,4,False,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-110':dict(run=lambda c:chord_shape_schedule(c,False,4,False,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-109':dict(run=lambda c:chord_shape_schedule(c,False,4,False,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-108':dict(run=lambda c:chord_shape_schedule(c,False,3,True,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-107':dict(run=lambda c:chord_shape_schedule(c,False,3,True,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-106':dict(run=lambda c:chord_shape_schedule(c,False,3,True,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-105':dict(run=lambda c:chord_shape_schedule(c,False,3,True,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-104':dict(run=lambda c:chord_shape_schedule(c,False,3,True,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-103':dict(run=lambda c:chord_shape_schedule(c,False,3,True,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-102':dict(run=lambda c:chord_shape_schedule(c,False,3,True,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-101':dict(run=lambda c:chord_shape_schedule(c,False,3,True,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-100':dict(run=lambda c:chord_shape_schedule(c,False,3,True,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-099':dict(run=lambda c:chord_shape_schedule(c,False,3,True,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-098':dict(run=lambda c:chord_shape_schedule(c,False,3,True,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-097':dict(run=lambda c:chord_shape_schedule(c,False,3,True,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-096':dict(run=lambda c:chord_shape_schedule(c,False,3,True,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-095':dict(run=lambda c:chord_shape_schedule(c,False,3,True,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-094':dict(run=lambda c:chord_shape_schedule(c,False,3,True,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-093':dict(run=lambda c:chord_shape_schedule(c,False,3,False,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-092':dict(run=lambda c:chord_shape_schedule(c,False,3,False,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-091':dict(run=lambda c:chord_shape_schedule(c,False,3,False,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-090':dict(run=lambda c:chord_shape_schedule(c,False,3,False,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-089':dict(run=lambda c:chord_shape_schedule(c,False,3,False,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-088':dict(run=lambda c:chord_shape_schedule(c,False,3,False,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-087':dict(run=lambda c:chord_shape_schedule(c,False,3,False,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-086':dict(run=lambda c:chord_shape_schedule(c,False,3,False,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-085':dict(run=lambda c:chord_shape_schedule(c,False,3,False,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-084':dict(run=lambda c:chord_shape_schedule(c,False,3,False,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-083':dict(run=lambda c:chord_shape_schedule(c,False,3,False,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-082':dict(run=lambda c:chord_shape_schedule(c,False,3,False,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-081':dict(run=lambda c:chord_shape_schedule(c,False,3,False,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-080':dict(run=lambda c:chord_shape_schedule(c,False,2,True,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-079':dict(run=lambda c:chord_shape_schedule(c,False,2,True,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-078':dict(run=lambda c:chord_shape_schedule(c,False,2,True,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-077':dict(run=lambda c:chord_shape_schedule(c,False,2,True,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-076':dict(run=lambda c:chord_shape_schedule(c,False,2,True,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-075':dict(run=lambda c:chord_shape_schedule(c,False,2,True,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-074':dict(run=lambda c:chord_shape_schedule(c,False,2,True,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-073':dict(run=lambda c:chord_shape_schedule(c,False,2,True,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-072':dict(run=lambda c:chord_shape_schedule(c,False,2,True,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-071':dict(run=lambda c:chord_shape_schedule(c,False,2,True,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-070':dict(run=lambda c:chord_shape_schedule(c,False,2,True,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-069':dict(run=lambda c:chord_shape_schedule(c,False,2,True,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-068':dict(run=lambda c:chord_shape_schedule(c,False,2,True,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-067':dict(run=lambda c:chord_shape_schedule(c,False,2,True,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-066':dict(run=lambda c:chord_shape_schedule(c,False,2,True,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-065':dict(run=lambda c:chord_shape_schedule(c,False,2,False,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-064':dict(run=lambda c:chord_shape_schedule(c,False,2,False,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-063':dict(run=lambda c:chord_shape_schedule(c,False,2,False,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-062':dict(run=lambda c:chord_shape_schedule(c,False,2,False,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-061':dict(run=lambda c:chord_shape_schedule(c,False,2,False,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-060':dict(run=lambda c:chord_shape_schedule(c,False,2,False,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-059':dict(run=lambda c:chord_shape_schedule(c,False,2,False,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-058':dict(run=lambda c:chord_shape_schedule(c,False,2,False,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-057':dict(run=lambda c:chord_shape_schedule(c,False,2,False,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-056':dict(run=lambda c:chord_shape_schedule(c,False,2,False,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-055':dict(run=lambda c:chord_shape_schedule(c,False,2,False,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-054':dict(run=lambda c:chord_shape_schedule(c,False,2,False,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-053':dict(run=lambda c:chord_shape_schedule(c,False,2,False,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-052':dict(run=lambda c:chord_shape_schedule(c,False,1,True,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-051':dict(run=lambda c:chord_shape_schedule(c,False,1,True,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-050':dict(run=lambda c:chord_shape_schedule(c,False,1,True,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-049':dict(run=lambda c:chord_shape_schedule(c,False,1,True,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-048':dict(run=lambda c:chord_shape_schedule(c,False,1,True,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-047':dict(run=lambda c:chord_shape_schedule(c,False,1,True,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-046':dict(run=lambda c:chord_shape_schedule(c,False,1,True,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-045':dict(run=lambda c:chord_shape_schedule(c,False,1,True,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-044':dict(run=lambda c:chord_shape_schedule(c,False,1,True,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-043':dict(run=lambda c:chord_shape_schedule(c,False,1,True,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-042':dict(run=lambda c:chord_shape_schedule(c,False,1,True,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-041':dict(run=lambda c:chord_shape_schedule(c,False,1,True,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-040':dict(run=lambda c:chord_shape_schedule(c,False,1,True,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-039':dict(run=lambda c:chord_shape_schedule(c,False,1,True,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-038':dict(run=lambda c:chord_shape_schedule(c,False,1,True,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-037':dict(run=lambda c:chord_shape_schedule(c,False,1,False,14),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-036':dict(run=lambda c:chord_shape_schedule(c,False,1,False,13),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-035':dict(run=lambda c:chord_shape_schedule(c,False,1,False,12),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-034':dict(run=lambda c:chord_shape_schedule(c,False,1,False,11),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-033':dict(run=lambda c:chord_shape_schedule(c,False,1,False,10),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-032':dict(run=lambda c:chord_shape_schedule(c,False,1,False,9),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-031':dict(run=lambda c:chord_shape_schedule(c,False,1,False,7),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-030':dict(run=lambda c:chord_shape_schedule(c,False,1,False,6),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-029':dict(run=lambda c:chord_shape_schedule(c,False,1,False,5),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-028':dict(run=lambda c:chord_shape_schedule(c,False,1,False,4),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-027':dict(run=lambda c:chord_shape_schedule(c,False,1,False,3),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-026':dict(run=lambda c:chord_shape_schedule(c,False,1,False,2),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-025':dict(run=lambda c:chord_shape_schedule(c,False,1,False,0),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Finite chord-mask subset and shape matrix: exact slot timing, muted-root behavior and MIDI releases"),
 'M-CHORDSHAPE-024':dict(run=lambda c:chord_shape_schedule(c,False,4,False,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-023':dict(run=lambda c:chord_shape_schedule(c,False,4,False,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-022':dict(run=lambda c:chord_shape_schedule(c,False,3,False,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-021':dict(run=lambda c:chord_shape_schedule(c,False,3,False,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-020':dict(run=lambda c:chord_shape_schedule(c,False,2,False,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-019':dict(run=lambda c:chord_shape_schedule(c,False,2,False,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-018':dict(run=lambda c:chord_shape_schedule(c,False,1,False,8),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-017':dict(run=lambda c:chord_shape_schedule(c,False,1,False,1),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-016':dict(run=lambda c:chord_shape_schedule(c,True,4,True,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-015':dict(run=lambda c:chord_shape_schedule(c,True,4,False,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-014':dict(run=lambda c:chord_shape_schedule(c,True,3,True,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-013':dict(run=lambda c:chord_shape_schedule(c,True,3,False,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-012':dict(run=lambda c:chord_shape_schedule(c,True,2,True,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-011':dict(run=lambda c:chord_shape_schedule(c,True,2,False,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-010':dict(run=lambda c:chord_shape_schedule(c,True,1,True,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-009':dict(run=lambda c:chord_shape_schedule(c,True,1,False,15),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-008':dict(run=lambda c:chord_shape_schedule(c,False,4,True,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-007':dict(run=lambda c:chord_shape_schedule(c,False,4,False,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-006':dict(run=lambda c:chord_shape_schedule(c,False,3,True,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-005':dict(run=lambda c:chord_shape_schedule(c,False,3,False,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-004':dict(run=lambda c:chord_shape_schedule(c,False,2,True,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-003':dict(run=lambda c:chord_shape_schedule(c,False,2,False,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-002':dict(run=lambda c:chord_shape_schedule(c,False,1,True,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-CHORDSHAPE-001':dict(run=lambda c:chord_shape_schedule(c,False,1,False,15),requirements=['CHORD-STRUM', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Exact chord slot order, root muting, velocity ordinal and releases for a full or sparse chord"),
 'M-ARP-014':dict(run=arp_empty_muted_replacement,requirements=['CHORD-ARP', 'CHORD-MUTE-ROOT'],description='Empty-muted trigger cancels old arp onsets while preserving tails and replacement ownership through Stop'),
 'M-ARP-013':dict(run=lambda c:arp_rest_live_scale(c,True),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Rests consume acceleration and velocity ordinals; applied scale edits affect later arp notes through native controls"),
 'M-ARP-012':dict(run=lambda c:arp_rest_live_scale(c,False),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Rests consume acceleration and velocity ordinals; applied scale edits affect later arp notes through native controls"),
 'M-ARP-011':dict(run=lambda c:muted_sparse_reverse_arp(c,4),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Muted sparse reverse shape sounds at trigger, retains four rests and advances velocity through wrap"),
 'M-ARP-010':dict(run=lambda c:muted_sparse_reverse_arp(c,2),requirements=['CHORD-ARP', 'CHORD-SHAPE', 'CHORD-VELOCITY', 'CHORD-MUTE-ROOT'],description="Muted sparse reverse shape sounds at trigger, retains four rests and advances velocity through wrap"),
 'M-SPREAD-027':dict(run=lambda c:minimum_swung_gap_contract(c,50),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'CH-TEMPO'],description="Positive short swung gaps retain every onset and half-step releases before negative termination"),
 'M-SPREAD-026':dict(run=lambda c:minimum_swung_gap_contract(c,-50),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'CH-TEMPO'],description="Positive short swung gaps retain every onset and half-step releases before negative termination"),
 'M-SPREAD-025':dict(run=lambda c:spread_acceleration_contract(c,False,0,explicit_off=True),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'LOCK-PARAM-SET'],description='Explicit step Off overrides active global+2 acceleration while preserving constant Spread spacing'),
 'M-SPREAD-024':dict(run=lambda c:spread_acceleration_contract(c,True,0,explicit_off=True),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'LOCK-PARAM-SET'],description='Explicit step Off overrides active global+2 acceleration while preserving constant Spread spacing'),
 'M-SPREAD-023':dict(run=fractional_spread_contract,requirements=['CHORD-ARP','CHORD-SPREAD','CH-TEMPO'],description='Fractional x5 clock and constant Spread preserve exact18-pulse five-slot windows, bounded phase and all releases'),
 'M-ARP-009':dict(run=arp_rest_slots,requirements=['CHORD-ARP'],description='Explicit trailing empty masks occupy rest slots before arp wrap'),
 'M-ARP-008':dict(run=lambda c:arp_rest_slots(c,internal=True),requirements=['CHORD-ARP'],description='Explicit internal and trailing mask rests retain their timing slots'),
 'M-ARP-007':dict(run=lambda c:arp_empty_masks(c,muted=True),requirements=['CHORD-ARP', 'CHORD-MUTE-ROOT'],description='All-empty muted arp is silent and responsive, with bounded Stop cleanup'),
 'M-ARP-006':dict(run=arp_empty_masks,requirements=['CHORD-ARP'],description='No-mask arp remains a root ratchet with exact releases'),
 'M-SPREAD-022':dict(run=lambda c:spread_acceleration_contract(c,True,5),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel 5: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-021':dict(run=lambda c:spread_acceleration_contract(c,True,4),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel 4: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-020':dict(run=lambda c:spread_acceleration_contract(c,True,3),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel 3: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-019':dict(run=lambda c:spread_acceleration_contract(c,True,2),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel 2: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-018':dict(run=lambda c:spread_acceleration_contract(c,True,1),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel 1: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-017':dict(run=lambda c:spread_acceleration_contract(c,True,0),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel 0: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-016':dict(run=lambda c:spread_acceleration_contract(c,True,-1),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel -1: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-015':dict(run=lambda c:spread_acceleration_contract(c,True,-2),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel -2: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-014':dict(run=lambda c:spread_acceleration_contract(c,True,-3),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel -3: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-013':dict(run=lambda c:spread_acceleration_contract(c,True,-4),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel -4: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-012':dict(run=lambda c:spread_acceleration_contract(c,True,-5),requirements=['CHORD-ARP', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Arp with quarter-step Spread and Accel -5: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-011':dict(run=lambda c:spread_acceleration_contract(c,False,5),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel 5: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-010':dict(run=lambda c:spread_acceleration_contract(c,False,4),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel 4: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-009':dict(run=lambda c:spread_acceleration_contract(c,False,3),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel 3: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-008':dict(run=lambda c:spread_acceleration_contract(c,False,2),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel 2: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-007':dict(run=lambda c:spread_acceleration_contract(c,False,1),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel 1: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-006':dict(run=lambda c:spread_acceleration_contract(c,False,0),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel 0: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-005':dict(run=lambda c:spread_acceleration_contract(c,False,-1),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel -1: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-004':dict(run=lambda c:spread_acceleration_contract(c,False,-2),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel -2: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-003':dict(run=lambda c:spread_acceleration_contract(c,False,-3),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel -3: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-002':dict(run=lambda c:spread_acceleration_contract(c,False,-4),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel -4: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-SPREAD-001':dict(run=lambda c:spread_acceleration_contract(c,False,-5),requirements=['CHORD-STRUM', 'CHORD-SPREAD', 'CHORD-ACCEL', 'PARAM-SLOTS'],description='Strum with quarter-step Spread and Accel -5: independent new-contract gap table, nonpositive termination and Stop accounting'),
 'M-PARAM-003':dict(run=lambda c:parameter_division_bounds(c,'Chord Spread'),requirements=['PARAM-SLOTS', 'CHORD-SPREAD'],description='Chord Spread selector exposes only supported musical divisions, clamps both ends and returns to Off'),
 'M-PARAM-002':dict(run=lambda c:parameter_division_bounds(c,'Chord Note Arpeggio'),requirements=['PARAM-SLOTS', 'CHORD-ARP'],description='Chord Note Arpeggio selector exposes only supported musical divisions, clamps both ends and returns to Off'),
 'M-PARAM-001':dict(run=lambda c:parameter_division_bounds(c,'Chord Note Strum'),requirements=['PARAM-SLOTS', 'CHORD-STRUM'],description='Chord Note Strum selector exposes only supported musical divisions, clamps both ends and returns to Off'),
 'M-ARP-005':dict(run=lambda c:arp_basic_timing(c,fast=True),requirements=['CHORD-ARP','CH-TEMPO'],description='Controlled one-pulse1/24 arp: exact note releases through every parent-cycle boundary and Stop, using native UI/MIDI'),
 'M-ARP-004':dict(run=lambda c:arp_basic_timing(c,reset=True),requirements=['CHORD-ARP','OPT-REPEAT-RESET','CH-TEMPO'],description='Repeat resets replace a long arp while an identical-pitch tail is sounding; old gates must not cut replacement voices'),
 'M-ARP-002':dict(run=lambda c:arp_basic_timing(c,replacement=True),requirements=['CHORD-ARP','PARAM-SLOTS','CH-TEMPO'],description='Replacing two-step arpeggios each step must not let old termination release the new generation'),
 'M-ARP-003':dict(run=lambda c:arp_basic_timing(c,fractional_gate=True),requirements=['CHORD-ARP','MASK-ATTRIBUTES'],description='Half-step arp ends at a1.25-step gate, clips its final note and emits no extra final onset'),
 'M-ARP-001':dict(run=arp_basic_timing,requirements=['CHORD-ARP','PARAM-SLOTS','CH-TEMPO'],description='Half-step arpeggio loops root and third within a two-step gate; exact onset/release table and silence after Stop'),
 'M-TIME-012':dict(run=strum_reset_continuity,requirements=['CHORD-STRUM','PARAM-SLOTS','OPT-REPEAT-RESET','CH-TEMPO'],description='Assign a strum through native parameter UI, verify root/chord offsets and existing gate across resets, and reject deferred notes after Stop'),
 'M-TIME-010':dict(run=pending_mask_lengths,requirements=['MASK-ATTRIBUTES','CH-TEMPO','OPT-REPEAT-RESET'],description='Half-step and two-step note releases across repeat resets, including expected same-pitch overlaps and explicit stop accounting'),
 'M-TIME-011':dict(run=lambda c:pending_mask_lengths(c,True),requirements=['MASK-ATTRIBUTES','CH-TEMPO','OPT-REPEAT-RESET'],description='Maximum128-step notes span eighteen resets; complete initial releases precede coincident retriggers, and Stop drains remaining voices'),
 'M-MASK-013':dict(run=lambda c:mask_clear_attributes(c,'chord',True,chord_slot=2),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE','MASK-CHORD'],description='Chord mask slot2: held-step and channel clearing preserve nonempty defaults and neighbouring overrides with exact MIDI and durations'),
 'M-MASK-014':dict(run=lambda c:mask_clear_attributes(c,'chord',True,chord_slot=3),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE','MASK-CHORD'],description='Chord mask slot3: held-step and channel clearing preserve nonempty defaults and neighbouring overrides with exact MIDI and durations'),
 'M-RANGE-GLOBAL-002':dict(run=offset_range_clipping,requirements=['SONG-LENGTH','CH-RANGE'],description='Minimal offset2..4 capped at two steps must sustain D/E sequence across global boundaries with matching grid and gates'),
 'M-RANGE-GLOBAL-003':dict(run=offset_range_rates,requirements=['SONG-LENGTH','CH-RANGE','CH-TEMPO'],description='Offset2..4/G2 repeated D/E for ten loops at x3/x2/1/2/3, exact phase and gates beyond three global boundaries'),
 'M-RANGE-GLOBAL-004':dict(run=offset_scale_range_clipping,requirements=['SONG-LENGTH','CH-RANGE','LOCK-SCALE'],description='Scale17 offset2..4 D/E/C locks with global1/2/3 caps and restoration; actual dependent MIDI notes and timing'),
 'M-RANGE-LIVE-002':dict(run=queued_global_length_transitions,requirements=['SONG-LENGTH','CH-RANGE'],description='Queued global4-to2-to3 edits on offset2..4 apply at exact old boundaries, last queued fader value wins, step4 returns, exact uninterrupted MIDI phase/gates and queue tooltip'),
 'M-RANGE-SAVED-003':dict(run=lambda c:rejected_manual_range(c,recovery='save'),requirements=['CH-RANGE','SAVE-NAMED','SAVE-AUTO'],description='Rejected load preserves two-channel playback and files; explicit native named Save and reload retain edits and restart autosave'),
 'M-RANGE-SAVED-004':dict(run=lambda c:rejected_manual_range(c,recovery='new'),requirements=['CH-RANGE','SAVE-NAMED','SAVE-AUTO'],description='Rejected load preserves current playback and files; explicit New creates silent project and restarts autosave'),
 'M-RANGE-SAVED-005':dict(run=saved_range_compatibility,requirements=['CH-RANGE','SAVE-AUTO','PERSIST-AUTO-001'],description='User-authored slot96, valid stored one-step range, exact MIDI gates/phase and grid survive two cold-load/autosave generations'),
 'M-RANGE-SAVED-006':dict(run=lambda c:saved_range_compatibility(c,legacy=True),requirements=['CH-RANGE','SAVE-AUTO','PERSIST-AUTO-001'],description='Legacy sequencer_patterns alias in slot96 with valid one-step range migrates through two cold-load/autosave generations preserving MIDI/grid'),
 'M-PROJECT-LIVE-001':dict(run=lambda c:project_dialog_while_playing(c,'new'),requirements=['SAVE-NAMED','MIDI-RELEASE-001'],description='Native new while two MIDI channels play: pending releases and project-dialog lifetime'),
 'M-PROJECT-LIVE-002':dict(run=lambda c:project_dialog_while_playing(c,'cancel-save'),requirements=['SAVE-NAMED','MIDI-RELEASE-001'],description='Native cancel-save while two MIDI channels play: pending releases and project-dialog lifetime'),
 'M-PROJECT-LIVE-003':dict(run=lambda c:project_dialog_while_playing(c,'cancel-load'),requirements=['SAVE-NAMED','MIDI-RELEASE-001'],description='Native cancel-load while two MIDI channels play: pending releases and project-dialog lifetime'),
 'M-PROJECT-LIVE-004':dict(run=lambda c:project_dialog_while_playing(c,'accept-save'),requirements=['SAVE-NAMED','MIDI-RELEASE-001'],description='Native accept-save while two MIDI channels play: pending releases and project-dialog lifetime'),
 'M-RANGE-SAVED-002':dict(run=rejected_manual_range,requirements=['CH-RANGE','PERSIST-AUTO-001','SAVE-NAMED'],description='Reject malformed scale range via actual file picker during two-route playback, preserve phase/gates/current editing/files, recover autosave through valid load'),
 'M-RANGE-SAVED-001':dict(run=rejected_saved_range,requirements=['CH-RANGE','PERSIST-AUTO-001','SAVE-AUTO'],description='Actual autosave copied with reversed range: native cold rejection tooltip, two idle deadlines with inputs preserve both files, invalid phrase never plays'),
 'M-RANGE-LIVE-001':dict(run=accepted_live_range_transitions,requirements=['CH-RANGE'],description='Accepted range edits while playhead is inside/below/above new bounds: exact next note, three loops, unchanged phase, full releases and stopped range LEDs'),
 'M-RANGE-GLOBAL-001':dict(run=global_range_clipping,requirements=['SONG-LENGTH','CH-RANGE'],description='Global lengths1/2/3/4/64 cap channel1..4,2..4,63..64 by length, preserve endpoint LEDs, restore full range, exact notes/gates/phase'),
 'M-RANGE-REJECT-005':dict(run=rejected_range_channel_isolation,requirements=['CH-RANGE'],description='Reject range edit while two independent routed channels play four/three-step phrases with distinct notes, velocity and fractional lengths; preserve both schedules'),
 'M-RANGE-REJECT-004':dict(run=lambda c:rejected_range_while_playing(c,True),requirements=['CH-RANGE'],description='Reversed range attempts during playback on scale-pageTrue: rejection feedback, uninterrupted four-note order and exact musical timing/releases'),
 'M-RANGE-REJECT-003':dict(run=lambda c:rejected_range_while_playing(c,False),requirements=['CH-RANGE'],description='Reversed range attempts during playback on scale-pageFalse: rejection feedback, uninterrupted four-note order and exact musical timing/releases'),
 'M-RANGE-REJECT-002':dict(run=lambda c:rejected_range(c,True),requirements=['CH-RANGE'],description='Reject reversed endpoints on scale-pageTrue: both release sequences preserve prior range and MIDI, exact rejection framebuffer and subsequent valid recovery'),
 'M-RANGE-REJECT-001':dict(run=lambda c:rejected_range(c,False),requirements=['CH-RANGE'],description='Reject reversed endpoints on scale-pageFalse: both release sequences preserve prior range and MIDI, exact rejection framebuffer and subsequent valid recovery'),
 'M-MASK-031':dict(run=lambda c:multiheld_keyboard(c,False),requirements=['MASK-STEP-ENTRY','CH-RANGE'],description='Two held grid steps with MIDI edits before/after releasing firstFalse: range2..4, first-held target, remaining-held target and untouched middle step'),
 'M-MASK-030':dict(run=lambda c:multiheld_keyboard(c,True),requirements=['MASK-STEP-ENTRY','CH-RANGE'],description='Two held grid steps with MIDI edits before/after releasing firstTrue: range2..4, first-held target, remaining-held target and untouched middle step'),
 'M-MASK-029':dict(run=lambda c:held_keyboard_chord(c,True,False,True),requirements=['MASK-STEP-ENTRY','MASK-CHORD','MIDI-RELEASE-001'],description='Root release/repress while other chord voices remain held: balanced preview, preserved chord/velocity and clean replacement; grid-firstTrue release'),
 'M-MASK-028':dict(run=lambda c:held_keyboard_chord(c,False,False,True),requirements=['MASK-STEP-ENTRY','MASK-CHORD','MIDI-RELEASE-001'],description='Root release/repress while other chord voices remain held: balanced preview, preserved chord/velocity and clean replacement; grid-firstFalse release'),
 'M-MASK-027':dict(run=lambda c:held_keyboard_chord(c,True,True),requirements=['MASK-STEP-ENTRY','MASK-CHORD'],description='Sixth keyboard voice previews/releases but does not exceed four stored chord additions; grid-firstTrue release and later single-note replacement remain correct'),
 'M-MASK-026':dict(run=lambda c:held_keyboard_chord(c,False,True),requirements=['MASK-STEP-ENTRY','MASK-CHORD'],description='Sixth keyboard voice previews/releases but does not exceed four stored chord additions; grid-firstFalse release and later single-note replacement remain correct'),
 'M-MASK-025':dict(run=lambda c:held_keyboard_chord(c,True),requirements=['MASK-STEP-ENTRY','MASK-CHORD'],description='Held-step five-voice keyboard chord, grid-first releaseTrue, exact preview/replay and single-note replacement without stale voices'),
 'M-MASK-024':dict(run=lambda c:held_keyboard_chord(c,False),requirements=['MASK-STEP-ENTRY','MASK-CHORD'],description='Held-step five-voice keyboard chord, grid-first releaseFalse, exact preview/replay and single-note replacement without stale voices'),
 'M-MASK-023':dict(run=trig_gesture_all_steps,requirements=['MASK-TRIG-GESTURE','MASK-ATTRIBUTES'],description='K1-grid add/remove/restore all64 trig masks with no pattern: full-grid feedback, odd/even isolation and exact MIDI timing across wrap'),
 'M-MASK-022':dict(run=mask_full_chord_inheritance,requirements=['MASK-FULL-QUANTISE','MASK-CHORD'],description='Assigned quantisation X inheritance applies to masked root and chord voices across fresh assignment, Off, On and returned X with exact MIDI timing'),
 'M-MASK-021':dict(run=mask_full_quantisation,requirements=['MASK-SCALE','MASK-FULL-QUANTISE','OPT-MASK-SNAP','OPT-MASK-QUANTISE'],description='Degree/rotation independence and full-mask global/channel/step off-on-unset precedence with exact MIDI timing'),
 'M-MASK-020':dict(run=lambda c:mask_scale_snap(c,2),requirements=['MASK-SCALE','OPT-MASK-SNAP'],description='Root2 all ten scales: accidental note masks snap on, raw off, restored on with exact MIDI velocities and timing'),
 'M-MASK-019':dict(run=lambda c:mask_scale_snap(c,0),requirements=['MASK-SCALE','OPT-MASK-SNAP'],description='Root0 all ten scales: accidental note masks snap on, raw off, restored on with exact MIDI velocities and timing'),
 'M-MASK-018':dict(run=mask_clear_recorded_chord,requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','REC-LIVE-NOTES','MASK-STEP-ENTRY','MASK-CHORD'],description='Clear a real keyboard-recorded chord: restore source note velocity and gate, remove chord voices, preserve neighbour override, then restore original pattern with exact timing'),
 'M-MASK-017':dict(run=mask_clear_last_steps,requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE'],description='Steps63/64 mask clear boundary and neighbour isolation preserve channel defaults and exact MIDI timing'),
 'M-MASK-016':dict(run=mask_clear_combined_chords,requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE','MASK-CHORD'],description='All four populated chord mask slots clear together, preserve defaults and neighbour overrides, with exact polyphonic MIDI and timing'),
 'M-MASK-015':dict(run=lambda c:mask_clear_attributes(c,'chord',True,chord_slot=4),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE','MASK-CHORD'],description='Chord mask slot4: held-step and channel clearing preserve nonempty defaults and neighbouring overrides with exact MIDI and durations'),
 'M-MASK-012':dict(run=lambda c:mask_clear_attributes(c,'trig',True,True),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE'],description='Clearing forced-on step overrides restores a silent trig default while another routed channel proves transport continues'),
 'M-MASK-011':dict(run=lambda c:mask_clear_attributes(c,'note',True,True),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE'],description='Clearing selected-channel overrides preserves another routed channel with nonempty defaults and conflicting note/velocity/length step masks'),
 'M-MASK-007':dict(run=lambda c:mask_clear_attributes(c,'note',True),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE'],description='Clearing conflicting step overrides preserves nonempty channel defaults and restores their exact MIDI behavior'),
 'M-MASK-008':dict(run=lambda c:mask_clear_attributes(c,'velocity',True),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE'],description='Clearing conflicting step overrides preserves nonempty channel defaults and restores their exact MIDI behavior'),
 'M-MASK-009':dict(run=lambda c:mask_clear_attributes(c,'length',True),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE'],description='Clearing conflicting step overrides preserves nonempty channel defaults and restores their exact MIDI behavior'),
 'M-MASK-010':dict(run=lambda c:mask_clear_attributes(c,'chord',True),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-PRECEDENCE','MASK-CHORD'],description='Clearing conflicting step overrides preserves nonempty channel defaults and restores their exact MIDI behavior'),
 'M-MASK-002':dict(run=lambda c:mask_clear_attributes(c,'note'),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY'],description='Clear one step override without affecting its neighbour, repeat safely, then clear channel step overrides with exact MIDI and timing'),
 'M-MASK-003':dict(run=lambda c:mask_clear_attributes(c,'velocity'),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY'],description='Clear one step override without affecting its neighbour, repeat safely, then clear channel step overrides with exact MIDI and timing'),
 'M-MASK-004':dict(run=lambda c:mask_clear_attributes(c,'length'),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY'],description='Clear one step override without affecting its neighbour, repeat safely, then clear channel step overrides with exact MIDI and timing'),
 'M-MASK-005':dict(run=lambda c:mask_clear_attributes(c,'trig'),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY'],description='Clear one step override without affecting its neighbour, repeat safely, then clear channel step overrides with exact MIDI and timing'),
 'M-MASK-006':dict(run=lambda c:mask_clear_attributes(c,'chord'),requirements=['MASK-ATTRIBUTES','MASK-CLEAR-STEP','MASK-CLEAR-CHANNEL','MASK-STEP-ENTRY','MASK-CHORD'],description='Clear one step override without affecting its neighbour, repeat safely, then clear channel step overrides with exact MIDI and timing'),
 'M-MASK-001':dict(run=length_mask_boundaries,requirements=['MASK-ATTRIBUTES'],description='Length mask minimum/X, maximum128, repeated endpoint turns and representative fractional/multi-step values with exact screen assertions'),
 'M-TIME-008':dict(run=lambda c:repeated_pattern_reset_policy(c,True),requirements=['CH-TEMPO','OPT-REPEAT-RESET','OPT-SEQUENCE-RESET'],description='Repeat resets preserve pending /9 one-step release deadlines and complete MIDI lifecycle'),
 'M-TIME-009':dict(run=lambda c:song_transition_reset_policy(c,True),requirements=['CH-TEMPO','OPT-REPEAT-RESET','OPT-SEQUENCE-RESET','SONG-ADVANCE'],description='Song transitions preserve pending /9 release deadlines under every reset combination'),
 'M-TIME-007':dict(run=lambda c:inactive_shuffle_transition(c,True),requirements=['CH-TEMPO','CH-SWING','SONG-ADVANCE'],description='Inactive shuffle basis changes preserve Swing phase across song transitions'),
 'M-TIME-006':dict(run=inactive_shuffle_transition,requirements=['CH-TEMPO','CH-SWING','SONG-ADVANCE'],description='Stored inactive shuffle settings must not disturb x16 Swing timing across actual song transitions'),
 'M-TIME-005':dict(run=song_transition_reset_policy,requirements=['CH-TEMPO','OPT-SEQUENCE-RESET','OPT-REPEAT-RESET','SONG-SLOTS','SONG-ADVANCE'],description='Copy and alternate two song slots with octave fingerprints, all reset flag combinations and exact /9 phase across transitions'),
 'M-TIME-004':dict(run=fractional_clock_continuity,requirements=['CH-TEMPO','OPT-REPEAT-RESET'],description='Every fractional pulse ratio across four global boundaries: rational-window timing, bounded phase and same-pitch release ordering'),
 'M-TIME-003':dict(run=repeated_pattern_reset_policy,requirements=['CH-TEMPO','OPT-REPEAT-RESET','OPT-SEQUENCE-RESET','OPT-SONG-MODE'],description='Real menu reset-option combinations and song mode off at two repeat boundaries, /9 clock and three-note phase witness'),
 'M-TIME-001':dict(run=integral_clock_divisions,requirements=['CH-TEMPO','NAV-CONFIRM'],description='All integral-pulse clock ratios through /16 with exact full-phrase phase and duration checks'),
 'M-TIME-002':dict(run=lambda c:integral_clock_divisions(c,True),requirements=['CH-TEMPO','NAV-CONFIRM'],description='All slow clock ratios /17 through /128 with exact full-phrase phase and duration checks'),
 'M-OCT-003':dict(run=octave_all_positions,requirements=['CH-GLOBAL-OCTAVE','LOCK-OCTAVE','LOCK-CLEAR-PAGE'],description='All64 octave locks override both global extremes, held-grid feedback and channel-wide clear with full MIDI loops'),
 'M-OCT-001':dict(run=channel_octave_controls,requirements=['CH-GLOBAL-OCTAVE'],description='All five octave positions, repeated center and navigation retention with exact MIDI'),
 'M-OCT-002':dict(run=octave_lock_precedence,requirements=['CH-GLOBAL-OCTAVE','LOCK-OCTAVE'],description='Every global/step octave pair, K2 clear, explicit zero and repeated-selector removal with exact MIDI'),
 'M-MERGE-008':dict(run=all_note_priorities,requirements=['MERGE-NOTE-PATTERN','PAT-INACTIVE-NOTE'],description='All16 assigned/unassigned priority-note sources with unique musical fingerprints, durations and wrap-rest spacing'),
 'M-PAT-006':dict(run=inactive_note_positions,requirements=['PAT-INACTIVE-NOTE','MERGE-NOTE-PATTERN','PAT-STEP-PAGES'],description='All64 inactive notes: silent loops, assigned/unassigned priority source, later trig activation/removal and exact MIDI timing'),
 'M-MERGE-004':dict(run=lambda c:priority_field_isolation(c,'velocity',1),requirements=['MERGE-VELOCITY'],description='velocity priority from inactive slot1: exact MIDI, duration and independent K1/normal modes'),
 'M-MERGE-005':dict(run=lambda c:priority_field_isolation(c,'velocity',3),requirements=['MERGE-VELOCITY'],description='velocity priority from inactive slot3: exact MIDI, duration and independent K1/normal modes'),
 'M-MERGE-006':dict(run=lambda c:priority_field_isolation(c,'length',1),requirements=['MERGE-LENGTH'],description='length priority from inactive slot1: exact MIDI, duration and independent K1/normal modes'),
 'M-MERGE-007':dict(run=lambda c:priority_field_isolation(c,'length',3),requirements=['MERGE-LENGTH'],description='length priority from inactive slot3: exact MIDI, duration and independent K1/normal modes'),

 'M-MERGE-002':dict(run=inactive_note_priority,requirements=['PAT-INACTIVE-NOTE','MERGE-NOTE-PATTERN'],description='Inactive lower-numbered note source: silence, unassigned/assigned priority, later trig and removal'),
 'M-MERGE-003':dict(run=lambda c:inactive_note_priority(c,3),requirements=['PAT-INACTIVE-NOTE','MERGE-NOTE-PATTERN'],description='Inactive higher-numbered note source: silence, unassigned/assigned priority, later trig and removal'),
 'M-VIEW-001':dict(run=pattern_grid_viewer,requirements=['PAT-VIEWER'],description='Independent screen grid for wide/short channel ranges, all16 E2 selections, clamps and unchanged MIDI/pattern data'),
 'M-EDIT-005':dict(run=editor_hold_boundaries,requirements=['PAT-NOTE-RANGE','PAT-VELOCITY'],description='Note/velocity range holds immediately before/after1s and cancelled by a second grid press; exact MIDI and measured real-time margins'),
 'M-EDIT-004':dict(run=note_pattern_selectors,requirements=['PAT-NOTE-SELECT'],description='K1 and long-hold note-editor pattern selection across all16 slots, edit/playback and retained-pattern isolation'),
 'M-EDIT-001':dict(run=editor_note_ranges,requirements=['PAT-NOTE-RANGE'],description='Note range fine steps, held extrema, clamps and center reset'),
 'M-EDIT-002':dict(run=editor_velocity_ranges,requirements=['PAT-VELOCITY'],description='Every displayed velocity value, fine range steps, held extrema and clamps'),
 'M-EDIT-003':dict(run=editor_step_groups,requirements=['PAT-NOTE-SHIFT', 'PAT-STEP-PAGES', 'PAT-VELOCITY'],description='K1 copies note and velocity edits across all four step pages; each page replays exact MIDI'),

 'M-ALG-004':dict(run=rhythm_bank_workflow,requirements=['PAT-ALGORITHM','PAT-FADERS','PAT-PAINT'],description='All five drum banks and four numeric masks at literal selected patterns, including empty-bank silence and repaint'),
 'M-ALG-002':dict(run=tresillo_multipliers,requirements=['PAT-ALGORITHM','PAT-FADERS','PAT-PAINT'],description='All eight tresillo multipliers: full grid, repeated MIDI phrase, exact musical spacing and repaint erasure'),
 'M-ALG-003':dict(run=tresillo_drum_boundary,requirements=['PAT-ALGORITHM','PAT-PAINT'],description='Tresillo drum-bank 64-step boundary: full grid, MIDI spacing and repaint erasure'),
 'M-ALG-001':dict(run=euclidean_workflow,requirements=['PAT-ALGORITHM', 'PAT-FADERS', 'PAT-PREVIEW', 'PAT-PAINT', 'PAT-CANCEL', 'PAT-MOVE'],description='Euclidean3-in-8: full-grid two-phase preview, unchanged playback, cancel, shifted XOR paint/repaint, left/reset and dense-fill boundary'),
 'M-PAT-004':dict(run=pattern_duration_controls,requirements=['PAT-DURATION'],description='Length extension/reset and empty-step gestures preserve exact grid and MIDI phrase'),
 'M-PAT-005':dict(run=live_pattern_duration,requirements=['PAT-DURATION'],description='Shorten and extend during playback: pending release unchanged, following onsets use edited length, phrase timing preserved'),
 'M-LEN-004':dict(run=lambda c:pattern_duration_domain(c,(4,),4),requirements=['PAT-DURATION','MIDI-RELEASE-001'],description='Full-loop same-pitch retrigger must release the previous note before emitting the next note-on'),
 'M-PAT-003':dict(run=pattern_duration_domain,requirements=['PAT-DURATION'],description='All64 authored duration endpoints through grid gestures, full length LEDs and independent MIDI durations with stop cleanup'),
 'M-REC-032':dict(run=lambda c:live_record_placement(c,(1398000000,1698000000),(1,3),boundary_witness=True),requirements=['REC-LIVE-NOTES'],description='Two milliseconds before boundary: independent active-step MIDI witness, grid and replay'),
 'M-REC-033':dict(run=lambda c:live_record_placement(c,(1402000000,1702000000),(2,4),boundary_witness=True),requirements=['REC-LIVE-NOTES'],description='Two milliseconds after boundary: independent active-step MIDI witness, grid and replay'),
 'M-MIDI-005':dict(run=keyboard_pitch_range,requirements=['MIDI-RELEASE-001'],description='All128 MIDI pitches at minimum/maximum velocity with both release forms; exact preview and no outstanding notes'),
 'M-REC-030':dict(run=lambda c:recorded_chord_release(c,(72,76,79),(0,0,80000000),release_offsets=(40000000,400000000,500000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Add third voice after root release while second voice remains held; preserve chord and first onset'),
 'M-REC-031':dict(run=lambda c:recorded_chord_release(c,(76,72,79),(0,0,80000000),release_offsets=(40000000,400000000,500000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Add third voice after second voice release while root remains held; preserve all recorded voices'),
 'M-REC-028':dict(run=lambda c:recorded_chord_release(c,preview_release_ns=600000000),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Post-disarm preview outlasts a recorded chord without extending or losing its shared length'),
 'M-REC-029':dict(run=lambda c:recorded_chord_release(c,preview_release_ns=250000000),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Post-disarm preview releases before the recorded chord without altering replay'),
 'M-REC-026':dict(run=lambda c:recorded_chord_release(c,(72,76,79),(0,40000000,80000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Staggered chord with root released first spans first press to final release'),
 'M-REC-027':dict(run=lambda c:recorded_chord_release(c,(76,79,72),(0,40000000,80000000)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Staggered chord with root released last retains first-press to final-release shared length'),
 'M-REC-024':dict(run=recorded_input_sources,requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Two ports record the same pitch on distinct channels in the same step; independent replay and lengths'),
 'M-REC-025':dict(run=lambda c:recorded_input_sources(c,1,16),requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Two input channels record overlapping notes on distinct Mosaic channels; independent replay and lengths'),
 'M-REC-020':dict(run=lambda c:recorded_chord_release(c,(72, 79, 76)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (72, 79, 76) retains full shared length'),
 'M-REC-021':dict(run=lambda c:recorded_chord_release(c,(76, 72, 79)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (76, 72, 79) retains full shared length'),
 'M-REC-022':dict(run=lambda c:recorded_chord_release(c,(79, 72, 76)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (79, 72, 76) retains full shared length'),
 'M-REC-023':dict(run=lambda c:recorded_chord_release(c,(79, 76, 72)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord release order (79, 76, 72) retains full shared length'),

 'M-REC-018':dict(run=recorded_chord_release,requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord records complete shared length when root is released last'),
 'M-REC-019':dict(run=lambda c:recorded_chord_release(c,(72,76,79)),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarmed held chord records complete shared length when root is released first'),
 'M-MIDI-003':dict(run=overlapping_keyboard_sources,requirements=['MIDI-RELEASE-001'],description='Two input ports hold the same pitch on different Mosaic channels; both release orders preserve ownership'),
 'M-MIDI-004':dict(run=lambda c:overlapping_keyboard_sources(c,1,16),requirements=['MIDI-RELEASE-001'],description='Two input channels on one port hold the same pitch on different Mosaic channels; both release orders preserve ownership'),
 'M-REC-017':dict(run=lambda c:recorded_note_channel_switch(c,disarm_while_held=True),requirements=['REC-LIVE-NOTES','REC-ARM'],description='Disarm while holding a recorded keyboard note; release commits its full quantised length on the original channel'),
 'M-MIDI-002':dict(run=keyboard_input_channels,requirements=['MIDI-RELEASE-001','REC-LIVE-NOTES'],description='All16 keyboard input channels across both ports and both release forms produce exact selected-channel preview MIDI with no stuck notes'),
 'M-REC-016':dict(run=lambda c:recorded_note_channel_switch(c,input_channel=16),requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Keyboard on MIDI input channel16 records and releases on the selected Mosaic channel independently of its input channel'),
 'M-REC-015':dict(run=lambda c:recorded_note_channel_switch(c,release_status=144),requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Velocity-zero Note On releases the original held note and commits its recorded length after channel selection changes'),
 'M-UI-002':dict(run=lambda c:live_playhead_feedback(c,3),requirements=['CLOCK-PHRASE-001','NAV-TRANSPORT'],description='Twice-rate live grid playhead follows emitted MIDI within one redraw period across two loops'),
 'M-UI-001':dict(run=live_playhead_feedback,requirements=['CLOCK-PHRASE-001','NAV-TRANSPORT'],description='Live grid playhead follows independently checked emitted MIDI steps within one redraw period; two loops and stopped grid'),
 'M-REC-013':dict(run=lambda c:live_record_placement(c,(1355000000,1505000000),(16,18),15,3,.5),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Twice-rate channel records on its own steps across a grid row; absolute LEDs and independent replay gaps'),
 'M-REC-014':dict(run=lambda c:live_record_placement(c,(1580000000,2180000000),(62,64),61,-2,2),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Half-rate channel records on its own steps near step64; absolute LEDs and independent replay gaps'),
 'M-REC-011':dict(run=lambda c:live_record_placement(c,(1730000000,1880000000),(4,1),1),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard input across range1..4 wrap; absolute recorded cells and disarmed replay order/spacing'),
 'M-REC-012':dict(run=lambda c:live_record_placement(c,(1730000000,1880000000),(64,61),61),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard input across range61..64 wrap; absolute recorded cells and disarmed replay order/spacing'),
 'M-REC-008':dict(run=lambda c:live_record_placement(c,expected_steps=(3,5),range_start=2),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard notes target absolute steps3/5 in channel range2..5; all64 LEDs and disarmed MIDI replay'),
 'M-REC-009':dict(run=lambda c:live_record_placement(c,expected_steps=(16,18),range_start=15),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard notes target absolute steps16/18 in channel range15..18; all64 LEDs and disarmed MIDI replay'),
 'M-REC-010':dict(run=lambda c:live_record_placement(c,expected_steps=(62,64),range_start=61),requirements=['REC-LIVE-NOTES','CH-RANGE'],description='Live keyboard notes target absolute steps62/64 in channel range61..64; all64 LEDs and disarmed MIDI replay'),
 'M-REC-007':dict(run=lambda c:recorded_note_channel_switch(c,210000000,5/24),requirements=['REC-LIVE-NOTES'],description='A210ms keyboard hold quantises to1.25 steps at90BPM; replay lasts5/24s'),
 'M-REC-006':dict(run=lambda c:recorded_note_channel_switch(c,550000000,13/24),requirements=['REC-LIVE-NOTES'],description='A550ms keyboard hold at90BPM quantises to3.25 sixteenth steps; replay lasts13/24s on the origin channel'),
 'M-REC-005':dict(run=recorded_note_channel_switch,requirements=['REC-LIVE-NOTES','MIDI-RELEASE-001'],description='Switch selected channel while recording a held note; release route and recorded length remain on origin channel'),
 'M-REC-002':dict(run=lambda c:live_record_placement(c,(1398000000,1698000000),(1,3)),requirements=['REC-LIVE-NOTES'],description='Live notes2ms before step boundaries belong to preceding steps; recorded grid and replay'),
 'M-REC-003':dict(run=lambda c:live_record_placement(c,(1402000000,1702000000),(2,4)),requirements=['REC-LIVE-NOTES'],description='Live notes2ms after step boundaries belong to new steps; recorded grid and replay'),
 'M-REC-004':dict(run=lambda c:live_record_placement(c,(1400000000,1700000000),(1,3),boundary_witness=True),requirements=['REC-LIVE-NOTES'],description='Equal-deadline pulse/note uses current active step; transport-anchored independent MIDI witness, grid and disarmed replay'),
 'M-REC-001':dict(run=live_record_placement,requirements=['REC-LIVE-NOTES'],description='Queued keyboard notes land on independently planned steps under MIDI clock; exact recorded LEDs and disarmed replay MIDI'),
 'M-MEMORY-002':dict(run=memory_channel_isolation,requirements=['MEMORY-NAV','MEMORY-RECORD','REC-KEYBOARD-STEP'],description='Independent histories on two routed channels sharing a pattern; untouched channel navigation cannot alter either phrase'),
 'M-MEMORY-001':dict(run=memory_navigation,requirements=['MEMORY-NAV','MEMORY-RECORD','REC-KEYBOARD-STEP'],description='Held-step MIDI edits, visible memory counter, undo/redo bounds and history branching verified through exact musical output'),
 'M-CHANNEL-001':dict(run=channel_routing_isolation,requirements=['CH-SELECT','CH-DEVICE','CH-ASSIGN','CH-MUTE'],description='All16 independently routed MIDI channels across two ports; cumulative mute/unmute preserves other phrases and clock alignment'),
 'M-MUTE-001':dict(run=channel_mute_gestures,requirements=['CH-MUTE'],description='Below-threshold hold, long hold and K1 mute toggles; stopped/live silence, resumed phrase and releases'),
 'M-RANGE-002':dict(run=adjacent_channel_ranges,requirements=['CH-RANGE'],description='All63 adjacent channel ranges plus full64-step range: exact grid, complete MIDI loops and spacing'),
 'M-RANGE-001':dict(run=channel_long_hold,requirements=['CH-RANGE'],description='A lone long hold is inactive; a delayed end-step combination still selects the range with exact MIDI loop spacing'),
 'M-SCALE-004':dict(run=scale_slot_matrix,requirements=['SCALE-SELECT','SCALE-EDIT','LOCK-SCALE','SCALE-PRECEDENCE'],description='All16 scale slots edit-only isolation, forward/reverse application with screen/grid and exact MIDI, highest global/channel slot precedence and independent clearing'),
 'M-SCALE-003':dict(run=scale_stop_indicator,requirements=['SCALE-SELECT'],description='Applied scale stays brightly lit after transport stops'),
 'M-SCALE-001':dict(run=scale_edit_selection,requirements=['SCALE-SELECT', 'SCALE-EDIT'],description='Editing-only gestures, applying edited scales, global off and reentry through screen/grid/MIDI'),
 'M-SCALE-002':dict(run=scale_lock_lifetime,requirements=['LOCK-SCALE', 'OPT-SCALE-LIFETIME','SCALE-PRECEDENCE'],description='Channel hold on/off and independent global scale-lock persistence through emitted notes'),
 'M-MERGE-001':dict(run=trig_merge_sets,requirements=['MERGE-TRIG-ALL', 'MERGE-TRIG-SKIP', 'MERGE-TRIG-ONLY'],description='All/Skip/Only across two and three patterns; literal MIDI and rest spacing; silence without overlap'),
 'M-PAT-002':dict(run=all_pattern_slots,requirements=['PAT-SELECT', 'PAT-TRIG', 'PAT-NOTE-CELLS', 'CH-ASSIGN'],description='All16 pattern slots retain independent grid edits and produce expected assigned-channel MIDI'),
 'M-TIM-004':dict(run=live_clock_handoff,requirements=['CLOCK-LIVE-HANDOFF-001'],description='Switch both clock-source directions with a note pending; preserve release timing and selected transport semantics'),
 'M-TIM-003':dict(run=midi_clock_transport,requirements=['CLOCK-MIDI-TRANSPORT-001'],description='Native menu selects MIDI clock; physical MIDI starts/stops playback at100BPM; return to internal clock'),
 'M-TIM-002':dict(run=restart_phase_edges,requirements=['CLOCK-PHASE-EDGE-001'],description='Restart around96PPQN boundaries; preserve full MIDI durations at five start phases'),
 'M-TIM-001':dict(run=phrase_timing,requirements=['CLOCK-PHRASE-001'],description='Restart edited phrase; verify every onset and duration through20 complete phrases at90BPM'),
 'M-MOD-003':dict(run=held_macro_rebind,requirements=['MOD-HELD-001'],description='Rebind an already-held nonzero macro; MIDI must immediately reflect its current value without a new source event'),
 'M-MOD-001':dict(run=macro_route_clear,requirements=['MOD-ROUTE-001'],description='Route macro through native Matrix menu; assert affected MIDI pitches and restoration after clearing depth'),
 'M-MOD-002':dict(run=pulse_lfo,requirements=['MOD-LFO-001'],description='Configure a clocked4-beat pulse LFO through native menus and verify two complete modulation cycles of MIDI pitches'),
 'M-SAVE-001':dict(run=autosave_restart,requirements=['PERSIST-AUTO-001'],description='Create notes through the grid; idle autosave; boot a fresh native process from saved data and verify restored LEDs and MIDI'),
 'M-MIDI-001':dict(run=lambda c:wrapped_length(c,same_pitch=True),requirements=['MIDI-RELEASE-001'],description='Repeated pitch at wrapped duration boundary emits balanced note releases and drains after stop'),
 'M-LEN-003':dict(run=wrapped_length,requirements=['PAT-LENGTH-003','PAT-DURATION'],description='A length crossing step64 ends at the next trig on step1; verify complete64-step MIDI loops and LEDs'),
 'M-LEN-002':dict(run=restore_length,requirements=['PAT-LENGTH-002','PAT-DURATION'],description='Delete and reinsert an interrupting trig; MIDI duration and grid restore the authored length'),
 'M-PAT-001':dict(run=four_notes,requirements=['PAT-EDIT-001'],description='Create four notes; edit through grid; verify screen, LEDs and complete MIDI phrases'),
 'M-LEN-001':dict(run=next_trig_cutoff,requirements=['PAT-LENGTH-001','PAT-DURATION'],description='A later trig cuts off preceding MIDI duration, matching manual and grid')}
