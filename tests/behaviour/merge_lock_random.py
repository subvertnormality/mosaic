"""High-risk triple: scale merging x channel scale lock x seeded random trig param
(BEHAVIOUR_PLAN "Required stress combinations").

Patterns 1 and 2 trig steps 1-4 with degrees 0/1/2/3 and 2/3/4/5; trig All and
note Average merge them to degrees 1/2/3/4. Slot 1 is C major (applied); slot 3
E major is locked on channel step 3 and, with the default "Scales lock until
ptn end", holds through step 4. Random Note 1 adds 0 or +1 degree per step from
Lua's PRNG seeded 42 (the driver's native seed), drawn in a separate process.
Every step is merged, so "Lock merged to pent." (default On) snaps the result
to the active scale's README MAN-102 selection (major degrees 1/2/3/5/6).
"""
import subprocess
MAJOR=[0,2,4,5,7,9,11];SELECTION=[0,1,2,4,5]
ROOT={1:60,3:64}
MERGED=[1,2,3,4];SLOT=[1,1,3,3];VELOCITY=[127,117,107,97]

def pitch(slot,degree):
    value=ROOT[slot]+12*(degree//7)+MAJOR[degree%7]
    available=[ROOT[slot]-60+12*o+MAJOR[d] for o in range(11) for d in SELECTION]
    return min(available,key=lambda n:(abs(n-value),n))

def draws(count):
    code='math.randomseed(42);'+'for i=1,%d do print(({0,1})[math.random(1,2)]) end'%count
    out=subprocess.run(['lua5.3','-e',code],capture_output=True,text=True,check=True).stdout.split()
    return [int(x) for x in out]

def merge_lock_random(c):
    # Hand-worked anchors: C major F snaps to E; E major B stays; E major A snaps down to G#.
    assert pitch(1,3)==64 and pitch(3,4)==71 and pitch(3,3)==68 and pitch(1,1)==62
    c.configure()
    c.ui.pattern_editor();c.ui.tap_control('pattern_select',2)
    for x in range(1,5):c.ui.tap_step(x)
    c.ui.pattern_editor()
    for x,degree in enumerate([2,3,4,5],1):c.ui.tap_control('pattern_note_degree',(x,degree))
    c.ui.menu('channel_editor');c.ui.tap_control('pattern_slot',2) # both patterns on channel 1
    c.ui.tap_control('trig_merge_mode');c.ui.tap_control('trig_merge_mode');c.ui.expect_leds({('trig_merge_mode',None):'medium'}) # trig All; note Average is the default
    c.ui.hold_control_tap('velocity_merge_mode','pattern_slot',target_index=1) # velocity priority pattern 1
    c.ui.scale_editor();c.ui.tap_control('scale_slot',3);c.ui.turn(2,-1);c.ui.set_value(4);c.ui.press_key(3);c.ui.turn(2,1);c.ui.tap_control('scale_slot',1);c.ui.menu('channel_editor') # slot 3 E major; slot 1 applied
    with c.ui.hold_step(3):c.ui.tap_control('channel_scale_slot',3) # channel lock: step 3 -> slot 3
    plain=[pitch(SLOT[i],MERGED[i]) for i in range(4)]
    c.playback([(1,[144,n,v]) for n,v in zip(plain,VELOCITY)],cycles=2)
    c.results.append(dict(kind='merge-lock-random',stage='merge-and-lock',pitches=plain,passed=True))
    c.ui.channel_page('trig_locks',from_page='midi_config',confirm=False);c.ui.assign_trig_parameter('Random Note');c.ui.set_value(1) # assigned at 0; one detent -> 1
    count=12;shifts=draws(count)
    expected=[(1,[144,pitch(SLOT[i%4],MERGED[i%4]+shifts[i]),VELOCITY[i%4]]) for i in range(count)]
    before=c.snapshot()['midi_count'];c.ui.play()
    def onsets(s):return [m for m in s['midi'] if m['index']>before and m['bytes'][0]==144 and m['bytes'][2]>0]
    state=c.wait(lambda s:len(onsets(s))>=count,timeout=5)
    c.ui.stop();c.wait(lambda s:not s['midi_capture']['outstanding'])
    actual=[(m['port'],m['bytes']) for m in onsets(state)[:count]]
    assert actual==expected,dict(shifts=shifts,expected=expected,actual=actual)
    assert set(shifts)=={0,1},'Seed must exercise both random outcomes'
    c.results.append(dict(kind='merge-lock-random',stage='with-random',seed=42,shifts=shifts,pitches=[e[1][1] for e in expected],passed=True))
